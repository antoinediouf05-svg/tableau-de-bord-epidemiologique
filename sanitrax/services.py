"""
Calculs épidémiologiques — le cœur « métier » du backend.

À partir des déclarations de cas brutes (modèle DeclarationCas), on agrège
par région et par semaine épidémiologique pour produire les indicateurs
affichés dans le tableau de bord : incidence pour 100 000 habitants,
niveau de gravité (par rapport au seuil épidémique de chaque maladie),
courbes hebdomadaires, démographie et alertes automatiques.
"""
from datetime import date, timedelta

from django.db.models import Sum

from .models import Alerte, DeclarationCas, Maladie, Region


# ─────────────────────────── Niveaux de gravité ───────────────────────────
# index = niveau + 1  (niveau va de -1 « Sous surveillance » à 3 « Critique »)
NIVEAU_LABELS = ["Sous surveillance", "Faible", "Modéré", "Élevé", "Critique"]
NIVEAU_FILL = ["#BCC9D8", "#F2D481", "#ECB24C", "#DD7B2E", "#C0392B"]   # remplissage
NIVEAU_TEXT = ["#7C8B83", "#C99A1E", "#D98214", "#DD5A1B", "#B43A24"]   # texte
NIVEAU_BG = ["#EEF1EF", "#FAF1D6", "#FBEAD0", "#FCE0CC", "#F6DAD3"]     # fond pastille

AGE_BUCKETS = [(0, 4, "0–4"), (5, 14, "5–14"), (15, 24, "15–24"),
               (25, 44, "25–44"), (45, 200, "45+")]


def niveau_pour_ratio(ratio):
    """Convertit un ratio incidence/seuil en niveau de gravité (-1 à 3)."""
    if ratio >= 2:
        return 3
    if ratio >= 1.5:
        return 2
    if ratio >= 1:
        return 1
    if ratio >= 0.5:
        return 0
    return -1


def niveau_meta(niveau):
    """Libellé et couleurs associés à un niveau de gravité."""
    i = niveau + 1
    return {
        "niveau": niveau,
        "label": NIVEAU_LABELS[i],
        "fill": NIVEAU_FILL[i],
        "color": NIVEAU_TEXT[i],
        "bg": NIVEAU_BG[i],
    }


def incidence(cas, population):
    """Incidence pour 100 000 habitants."""
    if not population:
        return 0.0
    return round(cas / population * 100000, 1)


# ─────────────────────────── Semaines épidémiologiques ───────────────────────────
def date_reference():
    """Dernière date de notification présente en base (sinon aujourd'hui)."""
    derniere = (DeclarationCas.objects
                .order_by('-date_notification')
                .values_list('date_notification', flat=True)
                .first())
    return derniere or date.today()


def fenetre_semaines(n=16, fin=None):
    """Liste de n semaines (lundi, dimanche), de la plus ancienne à la courante."""
    fin = fin or date_reference()
    lundi = fin - timedelta(days=fin.weekday())
    out = []
    for i in range(n - 1, -1, -1):
        m = lundi - timedelta(weeks=i)
        out.append((m, m + timedelta(days=6)))
    return out


def _cas_par_region(maladie, debut, fin):
    """{region_id: total de cas} pour une maladie sur une période."""
    qs = (DeclarationCas.objects
          .filter(maladie=maladie, date_notification__range=(debut, fin))
          .values('region')
          .annotate(total=Sum('nombre_cas')))
    return {r['region']: r['total'] for r in qs}


# ─────────────────────────── Agrégations régionales ───────────────────────────
def lignes_regions(maladie, fin=None, regions=None):
    """Une ligne d'indicateurs par région (semaine courante), triée par incidence.

    `regions` : queryset/itérable de régions à inclure (None = toutes). Permet de
    restreindre l'agrégation à la région d'un agent régional.
    """
    (pl, pd), (cl, cd) = fenetre_semaines(2, fin)   # précédente, courante
    cas_courant = _cas_par_region(maladie, cl, cd)
    cas_prec = _cas_par_region(maladie, pl, pd)

    lignes = []
    for r in (regions if regions is not None else Region.objects.all()):
        cas = cas_courant.get(r.id, 0)
        inc = incidence(cas, r.population)
        ratio = inc / maladie.seuil_incidence if maladie.seuil_incidence else 0

        inc_prec = incidence(cas_prec.get(r.id, 0), r.population)
        if inc_prec:
            tendance = round((inc - inc_prec) / inc_prec * 100)
        else:
            tendance = 100 if inc else 0

        niveau = niveau_pour_ratio(ratio)
        lignes.append({
            "region": r,
            "cases": cas,
            "cases_prec": cas_prec.get(r.id, 0),
            "incidence": inc,
            "ratio": round(ratio, 3),
            "tendance": tendance,
            "tendance_couleur": couleur_tendance(tendance),
            **niveau_meta(niveau),
        })
    lignes.sort(key=lambda x: x["incidence"], reverse=True)
    return lignes


def couleur_tendance(pct):
    """Vert si en recul, rouge si en hausse, gris si stable."""
    if pct > 3:
        return "#B43A24"
    if pct < -3:
        return "#2E8B6F"
    return "#8A99A1"


def tableau_bord(regions=None):
    """KPIs nationaux cumulés (toutes maladies) : total, actifs, guéris, décès,
    maladie dominante et région la plus touchée. Respecte le périmètre `regions`."""
    decl = DeclarationCas.objects.all()
    if regions is not None:
        decl = decl.filter(region__in=regions)

    total = decl.aggregate(t=Sum('nombre_cas'))['t'] or 0
    par_evo = {e: (decl.filter(evolution=e).aggregate(t=Sum('nombre_cas'))['t'] or 0)
               for e in ('en_cours', 'gueri', 'decede')}

    dom = (decl.values('maladie__nom', 'maladie__couleur')
           .annotate(t=Sum('nombre_cas')).order_by('-t').first())
    reg = (decl.values('region__nom')
           .annotate(t=Sum('nombre_cas')).order_by('-t').first())

    pct = lambda n: round(n / total * 100) if total else 0
    return {
        'total': total,
        'actifs': par_evo['en_cours'],
        'gueris': par_evo['gueri'],
        'deces': par_evo['decede'],
        'pct_actifs': pct(par_evo['en_cours']),
        'pct_gueris': pct(par_evo['gueri']),
        'pct_deces': pct(par_evo['decede']),
        'maladie_dominante': dom['maladie__nom'] if dom else '—',
        'maladie_dominante_couleur': dom['maladie__couleur'] if dom else '#8A99A1',
        'maladie_dominante_cas': dom['t'] if dom else 0,
        'region_plus_touchee': reg['region__nom'] if reg else '—',
        'region_plus_touchee_cas': reg['t'] if reg else 0,
    }


def resume_national(maladie, fin=None, regions=None):
    """Indicateurs nationaux agrégés pour une maladie (semaine courante).

    `regions` restreint le périmètre (None = national, sinon les régions visibles).
    """
    lignes = lignes_regions(maladie, fin, regions)
    total = sum(l["cases"] for l in lignes)
    total_prec = sum(l["cases_prec"] for l in lignes)
    population = sum(l["region"].population for l in lignes)
    delta = round((total - total_prec) / total_prec * 100) if total_prec else 0
    regions_en_alerte = sum(1 for l in lignes if l["ratio"] >= 1)
    return {
        "lignes": lignes,
        "total_cas": total,
        "total_prec": total_prec,
        "delta": delta,
        "delta_couleur": couleur_tendance(delta),
        "incidence_nationale": incidence(total, population),
        "regions_en_alerte": regions_en_alerte,
        "population": population,
    }


def serie_hebdomadaire(maladie, n=16, fin=None):
    """Total de cas par semaine sur les n dernières semaines (pour la courbe)."""
    out = []
    for (lundi, dimanche) in fenetre_semaines(n, fin):
        total = (DeclarationCas.objects
                 .filter(maladie=maladie, date_notification__range=(lundi, dimanche))
                 .aggregate(t=Sum('nombre_cas'))['t']) or 0
        out.append({
            "lundi": lundi,
            "cases": total,
            "label": "S%d" % lundi.isocalendar()[1],
        })
    return out


def demographie(maladie, n=16, fin=None):
    """Répartition par tranche d'âge et par sexe (cumul sur n semaines)."""
    semaines = fenetre_semaines(n, fin)
    debut, terme = semaines[0][0], semaines[-1][1]
    qs = (DeclarationCas.objects
          .filter(maladie=maladie, date_notification__range=(debut, terme))
          .values('sexe', 'age', 'nombre_cas'))

    sexe = {'M': 0, 'F': 0}
    tranches = [0] * len(AGE_BUCKETS)
    for d in qs:
        if d['sexe'] in sexe:
            sexe[d['sexe']] += d['nombre_cas']
        age = d['age']
        if age is not None:
            for i, (lo, hi, _) in enumerate(AGE_BUCKETS):
                if lo <= age <= hi:
                    tranches[i] += d['nombre_cas']
                    break

    total_age = sum(tranches) or 1
    total_sexe = (sexe['M'] + sexe['F']) or 1
    age_max = max(tranches) or 1
    return {
        "tranches": [
            {"label": AGE_BUCKETS[i][2],
             "cases": tranches[i],
             "pct": round(tranches[i] / total_age * 100),
             "hauteur": round(tranches[i] / age_max * 100)}
            for i in range(len(AGE_BUCKETS))
        ],
        "sexe_m": round(sexe['M'] / total_sexe * 100),
        "sexe_f": round(sexe['F'] / total_sexe * 100),
    }


def cas_cumules(maladie, n=16, fin=None):
    """Total de cas cumulés sur les n dernières semaines."""
    return sum(s["cases"] for s in serie_hebdomadaire(maladie, n, fin))


def courbe(maladie, n=16, largeur=700, hauteur=240, fin=None):
    """Géométrie SVG de la courbe épidémiologique (tracé prêt pour le template)."""
    serie = serie_hebdomadaire(maladie, n, fin)
    vals = [s["cases"] for s in serie]
    n_pts = len(vals)
    maxy = (max(vals) if vals else 0) * 1.1 or 1
    pl, pr, pt, pb = 44, 12, 14, 24

    def x(i):
        return round(pl + (largeur - pl - pr) * (i / (n_pts - 1 or 1)), 1)

    def y(v):
        return round(pt + (hauteur - pt - pb) * (1 - v / maxy), 1)

    pts = [(x(i), y(v)) for i, v in enumerate(vals)]
    line = "M" + "L".join(f"{px} {py}" for px, py in pts)
    area = f"{line}L{x(n_pts - 1)} {y(0)}L{x(0)} {y(0)}Z"
    yticks = [{"y": y(maxy * f), "v": round(maxy * f)} for f in (0, .25, .5, .75, 1)]
    xticks = [{"x": x(i), "label": serie[i]["label"]} for i in range(0, n_pts, 3)]
    return {
        "serie": serie, "largeur": largeur, "hauteur": hauteur,
        "line": line, "area": area, "points": pts,
        "yticks": yticks, "xticks": xticks,
        "dernier": pts[-1] if pts else (0, 0),
        "couleur": maladie.couleur,
    }


# ─────────────────────────── Alertes automatiques ───────────────────────────
# Deux règles déclenchent une alerte pour un couple (maladie, région) :
#   R1 — incidence hebdomadaire ≥ seuil épidémique de la maladie (niveau selon ratio)
#   R4 — pic de ≥ 30 cas en une journée (24h), gradué 30 / 60 / 100 cas
# Le niveau retenu est le plus élevé des deux règles déclenchées.
SEUIL_CAS_24H = 30


def niveau_pour_cas24h(pic):
    """Niveau de gravité (1 à 3) selon le pic de cas en 24h, ou None sous le seuil."""
    if pic >= 100:
        return 3
    if pic >= 60:
        return 2
    if pic >= SEUIL_CAS_24H:
        return 1
    return None


def pic_journalier(maladie, region, debut, fin):
    """Plus grand nombre de cas notifiés en une seule journée (24h) sur la période."""
    qs = (DeclarationCas.objects
          .filter(maladie=maladie, region=region, date_notification__range=(debut, fin))
          .values('date_notification')
          .annotate(total=Sum('nombre_cas'))
          .order_by('-total'))
    premier = qs.first()
    return premier['total'] if premier else 0


def regenerer_alertes(fin=None):
    """Recalcule toutes les alertes selon les règles R1 (incidence) et R4 (cas 24h)."""
    Alerte.objects.all().delete()
    (cl, cd) = fenetre_semaines(1, fin)[0]   # bornes de la semaine courante
    nb = 0
    for maladie in Maladie.objects.all():
        for l in lignes_regions(maladie, fin):
            region = l["region"]
            # R1 — dépassement du seuil d'incidence hebdomadaire
            niveau_inc = l["niveau"] if l["ratio"] >= 1 else None
            # R4 — pic de cas en 24h
            pic = pic_journalier(maladie, region, cl, cd)
            niveau_cas = niveau_pour_cas24h(pic)

            if niveau_inc is None and niveau_cas is None:
                continue
            if niveau_inc is not None and niveau_cas is not None:
                declencheur = "les_deux"
            elif niveau_cas is not None:
                declencheur = "cas_24h"
            else:
                declencheur = "incidence"
            niveau = max(n for n in (niveau_inc, niveau_cas) if n is not None)

            Alerte.objects.create(
                maladie=maladie,
                region=region,
                incidence=l["incidence"],
                seuil=maladie.seuil_incidence,
                ratio=l["ratio"],
                pic_24h=pic,
                declencheur=declencheur,
                niveau=niveau,
            )
            nb += 1
    return nb


# ─────────────────────────── Bulletin / rapports par période ───────────────────────────
def plage_periode(periode, fin=None):
    """Bornes (début, fin) et libellé selon la périodicité demandée ('semaine' ou 'mois')."""
    fin = fin or date_reference()
    if periode == "mois":
        debut = fin.replace(day=1)
        return debut, fin, "Mensuel"
    (lundi, dimanche) = fenetre_semaines(1, fin)[0]
    return lundi, dimanche, "Hebdomadaire"


def bulletin_donnees(periode="semaine", fin=None):
    """Agrégation globale (toutes maladies × toutes régions) sur la période choisie.

    Renvoie (lignes, contexte) — chaque ligne = une combinaison maladie × région.
    """
    debut, terme, label = plage_periode(periode, fin)
    lignes = []
    for maladie in Maladie.objects.all().order_by("nom"):
        cas_map = _cas_par_region(maladie, debut, terme)
        for r in Region.objects.all():
            cas = cas_map.get(r.id, 0)
            inc = incidence(cas, r.population)
            ratio = inc / maladie.seuil_incidence if maladie.seuil_incidence else 0
            lignes.append({
                "maladie": maladie.nom,
                "region": r.nom,
                "cas": cas,
                "incidence": inc,
                "seuil": maladie.seuil_incidence,
                "niveau": niveau_meta(niveau_pour_ratio(ratio))["label"],
            })
    contexte = {"periode": label, "debut": debut, "terme": terme}
    return lignes, contexte
