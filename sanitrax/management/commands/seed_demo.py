"""
Données de démonstration pour le tableau de bord épidémiologique.

Crée les 14 régions du Sénégal, leurs districts sanitaires, les 6 maladies
surveillées, puis génère des déclarations de cas réalistes en répartissant
les cas par région (pondération), par semaine (courbe épidémique sur
16 semaines) et par démographie (âge / sexe). Termine en (re)calculant les
alertes automatiques.

    python manage.py seed_demo
"""
import math
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from sanitrax import services
from sanitrax.models import (Alerte, Commune, DeclarationCas, District, Maladie,
                             Profil, Region, Structure)

DEMO_PWD = "sanitrax2026"
# (email, prénom, nom, rôle, code région, est_admin)
COMPTES_DEMO = [
    ("admin@sante.gouv.sn", "Admin", "Système", "admin", None, True),
    ("agent.thies@sante.gouv.sn", "Awa", "Ndiaye", "agent", "TH", False),
    ("epi@sante.gouv.sn", "Amadou", "Diallo", "epi", None, False),
    ("decideur@sante.gouv.sn", "Fatou", "Sow", "decideur", None, False),
]

# (code, nom, nom court, population en milliers)
REGIONS = [
    ("DK", "Dakar", "Dakar", 4000), ("TH", "Thiès", "Thiès", 2200),
    ("DB", "Diourbel", "Diourbel", 1900), ("FK", "Fatick", "Fatick", 950),
    ("KL", "Kaolack", "Kaolack", 1150), ("KF", "Kaffrine", "Kaffrine", 750),
    ("LG", "Louga", "Louga", 1050), ("SL", "Saint-Louis", "St-Louis", 1100),
    ("MT", "Matam", "Matam", 750), ("TC", "Tambacounda", "Tamba.", 950),
    ("KE", "Kédougou", "Kédougou", 200), ("KD", "Kolda", "Kolda", 850),
    ("SE", "Sédhiou", "Sédhiou", 600), ("ZG", "Ziguinchor", "Ziguin.", 700),
]

DISTRICTS = {
    "DK": ["Dakar-Centre", "Pikine", "Guédiawaye", "Rufisque", "Keur Massar"],
    "TH": ["Thiès", "Mbour", "Tivaouane", "Popenguine"],
    "DB": ["Diourbel", "Mbacké", "Bambey"],
    "FK": ["Fatick", "Foundiougne", "Gossas", "Niakhar"],
    "KL": ["Kaolack", "Guinguinéo", "Nioro du Rip"],
    "KF": ["Kaffrine", "Birkelane", "Koungheul", "Malem Hodar"],
    "LG": ["Louga", "Linguère", "Kébémer"],
    "SL": ["Saint-Louis", "Dagana", "Podor", "Richard-Toll"],
    "MT": ["Matam", "Kanel", "Ranérou"],
    "TC": ["Tambacounda", "Bakel", "Goudiry", "Koumpentoum"],
    "KE": ["Kédougou", "Salémata", "Saraya"],
    "KD": ["Kolda", "Vélingara", "Médina Yoro Foulah"],
    "SE": ["Sédhiou", "Bounkiling", "Goudomp"],
    "ZG": ["Ziguinchor", "Bignona", "Oussouye"],
}

DORDER = ["palu", "chol", "roug", "tb", "covid", "fj"]

DISEASES = {
    "palu": dict(
        fr="Paludisme", en="Malaria", color="#B43A24", base=115, thr=100,
        cfr=0.4, rt=1.18, age=[.30, .26, .15, .18, .11], sex=[52, 48],
        w={"KE": 1, "TC": .95, "KD": .9, "SE": .85, "ZG": .8, "KL": .55, "KF": .6,
           "FK": .5, "MT": .45, "SL": .3, "LG": .3, "DB": .35, "TH": .25, "DK": .15},
        shape=[.30, .31, .34, .33, .38, .40, .44, .48, .52, .58, .64, .71, .80, .87, .94, 1]),
    "chol": dict(
        fr="Choléra", en="Cholera", color="#1D6F8B", base=6, thr=5,
        cfr=1.8, rt=1.42, age=[.22, .20, .18, .24, .16], sex=[50, 50],
        w={"SL": .9, "DK": .5, "KL": .7, "TC": .2, "MT": .45, "ZG": .3, "FK": .25,
           "KF": .2, "LG": .15, "DB": .1, "TH": .12, "KE": .08, "KD": .1, "SE": .1},
        shape=[.12, .10, .14, .11, .20, .16, .26, .22, .32, .42, .56, .70, .82, .90, .96, 1]),
    "roug": dict(
        fr="Rougeole", en="Measles", color="#C6862A", base=4.2, thr=5,
        cfr=0.9, rt=0.86, age=[.48, .34, .10, .05, .03], sex=[51, 49],
        w={"TC": .8, "MT": .9, "DB": .6, "KF": .5, "KE": .4, "LG": .45, "KD": .35,
           "SE": .3, "KL": .3, "FK": .25, "SL": .3, "TH": .25, "DK": .35, "ZG": .2},
        shape=[.55, .62, .74, .88, 1, .94, .82, .70, .60, .55, .50, .48, .46, .45, .44, .43]),
    "tb": dict(
        fr="Tuberculose", en="Tuberculosis", color="#6E5AA8", base=13.5, thr=25,
        cfr=5.2, rt=0.98, age=[.04, .08, .22, .40, .26], sex=[62, 38],
        w={"DK": 1, "TH": .7, "DB": .5, "KL": .45, "SL": .4, "ZG": .42, "TC": .35,
           "MT": .3, "LG": .32, "FK": .3, "KF": .28, "KE": .25, "KD": .3, "SE": .28},
        shape=[.92, .95, .90, .96, .93, .98, .94, .97, .95, 1, .96, .99, .97, 1, .98, .99]),
    "covid": dict(
        fr="COVID-19", en="COVID-19", color="#2E8B6F", base=2.6, thr=8,
        cfr=1.1, rt=0.74, age=[.05, .10, .20, .35, .30], sex=[55, 45],
        w={"DK": 1, "TH": .6, "DB": .25, "SL": .3, "KL": .22, "ZG": .25, "TC": .15,
           "MT": .12, "LG": .15, "FK": .14, "KF": .12, "KE": .1, "KD": .12, "SE": .1},
        shape=[1, .92, .80, .70, .60, .52, .46, .42, .38, .36, .34, .33, .34, .36, .38, .40]),
    "fj": dict(
        fr="Fièvre jaune", en="Yellow fever", color="#B8932E", base=.45, thr=.5,
        cfr=6.5, rt=1.05, age=[.15, .22, .25, .25, .13], sex=[60, 40],
        w={"KE": .9, "TC": .7, "KD": .45, "SE": .35, "ZG": .25, "KL": .12, "FK": .1,
           "MT": .15, "LG": .08, "DB": .06, "SL": .08, "TH": .05, "DK": .04, "KF": .1},
        shape=[.20, .18, .30, .22, .40, .35, .55, .48, .62, .70, .78, .84, .90, .92, .96, 1]),
}

# Coordonnées (latitude, longitude) du chef-lieu de chaque région
LATLNG = {
    "DK": (14.75, -17.18), "TH": (14.83, -16.78), "DB": (14.73, -16.18),
    "FK": (14.10, -16.28), "KL": (14.05, -16.00), "KF": (14.05, -15.40),
    "LG": (15.45, -15.75), "SL": (16.30, -15.60), "MT": (15.45, -13.40),
    "TC": (13.60, -13.30), "KE": (12.70, -12.45), "KD": (13.00, -14.70),
    "SE": (12.82, -15.45), "ZG": (12.70, -16.20),
}

AGE_MID = [2, 10, 20, 35, 55]          # âge représentatif par tranche
STATUTS = ["suspecte", "probable", "confirme"]
# Répartition des gravités/sévérités (majorité de cas modérés)
GRAVITES = (["modere"] * 6) + (["severe"] * 3) + (["critique"] * 1)


def _evolution(i, wk, bi, dz):
    """Évolution d'un cas : anciens plutôt guéris, récents en cours, décès rares (~6 %)."""
    if (i * 7 + wk * 3 + bi + dz) % 16 == 0:
        return "decede"
    if wk >= 13:                      # 3 dernières semaines : cas encore actifs
        return "en_cours"
    if wk >= 9:
        return "en_cours" if (i + bi) % 2 == 0 else "gueri"
    return "gueri"                    # cas anciens : majoritairement rétablis
# Deux communes par département (suffixe géographique) ; un centre de santé par commune
COMMUNE_SUFFIXES = ["Nord", "Sud"]
STRUCTURE_TYPES = ["hopital", "centre", "poste"]
DERNIER_LUNDI = date(2026, 6, 22)      # lundi de la semaine épidémiologique courante (S25)


def _frac(x):
    return x - math.floor(x)


def _bruit(i, dz):
    """Bruit pseudo-aléatoire déterministe (reproduit la simulation du design)."""
    return 0.78 + 0.44 * _frac(math.sin((i * 7 + dz * 53) * 127.1 + 311.7) * 43758.5453)


class Command(BaseCommand):
    help = "Crée des données de démonstration (régions, districts, maladies, déclarations, alertes)."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1) Nettoyage (commande ré-exécutable)
        DeclarationCas.objects.all().delete()
        Alerte.objects.all().delete()
        Structure.objects.all().delete()
        Commune.objects.all().delete()
        District.objects.all().delete()
        Maladie.objects.all().delete()
        Region.objects.all().delete()

        # 2) Régions
        regions = {code: Region.objects.create(code=code, nom=nom, nom_court=court,
                                               population=popk * 1000,
                                               latitude=LATLNG[code][0],
                                               longitude=LATLNG[code][1])
                   for (code, nom, court, popk) in REGIONS}

        # 3) Départements (modèle District) + Communes + Centres de santé
        districts = {code: [District.objects.create(region=regions[code], nom=n) for n in noms]
                     for code, noms in DISTRICTS.items()}

        # Pour chaque département : 2 communes ; pour chaque commune : 1 centre de santé.
        communes_par_district = {}   # district_id -> [Commune, ...]
        structures_par_commune = {}  # commune_id  -> [Structure, ...]
        t = 0
        for dlist in districts.values():
            for d in dlist:
                communes = []
                for suffixe in COMMUNE_SUFFIXES:
                    c = Commune.objects.create(district=d, nom=f"{d.nom} {suffixe}")
                    typ = STRUCTURE_TYPES[t % len(STRUCTURE_TYPES)]
                    t += 1
                    libelle = {"hopital": "Hôpital", "centre": "Centre de santé",
                               "poste": "Poste de santé"}[typ]
                    s = Structure.objects.create(commune=c, type=typ,
                                                 nom=f"{libelle} de {c.nom}")
                    structures_par_commune[c.id] = [s]
                    communes.append(c)
                communes_par_district[d.id] = communes

        # 4) Maladies
        maladies = {code: Maladie.objects.create(
            code=code, nom=d["fr"], nom_en=d["en"], couleur=d["color"],
            seuil_incidence=d["thr"], cfr=d["cfr"], rt=d["rt"])
            for code, d in ((c, DISEASES[c]) for c in DORDER)}

        # 5) Déclarations de cas
        lignes = []
        for dz, code in enumerate(DORDER):
            d = DISEASES[code]
            maladie = maladies[code]
            sm, sf = d["sex"]
            for i, (rcode, nom, court, popk) in enumerate(REGIONS):
                poids = d["w"].get(rcode, 0.1)
                inc = d["base"] * poids * _bruit(i, dz)
                base_cas = round(inc * popk / 100)         # cas de la semaine courante
                if base_cas <= 0:
                    continue
                region = regions[rcode]
                dists = districts[rcode]
                for wk in range(16):
                    cas_sem = round(base_cas * d["shape"][wk])
                    if cas_sem <= 0:
                        continue
                    lundi = DERNIER_LUNDI - timedelta(weeks=15 - wk)
                    jour = lundi + timedelta(days=2)
                    district = dists[wk % len(dists)]
                    commune = communes_par_district[district.id][wk % 2]
                    structure = structures_par_commune[commune.id][0]
                    statut = STATUTS[(wk + i) % 3]
                    for bi, p in enumerate(d["age"]):
                        n = round(cas_sem * p)
                        if n <= 0:
                            continue
                        grav = GRAVITES[(i + wk + bi + dz) % len(GRAVITES)]
                        evo = _evolution(i, wk, bi, dz)
                        nb_m = round(n * sm / 100)
                        nb_f = n - nb_m
                        if nb_m > 0:
                            lignes.append(DeclarationCas(
                                maladie=maladie, region=region, district=district,
                                commune=commune, structure=structure,
                                sexe="M", age=AGE_MID[bi], nombre_cas=nb_m,
                                date_notification=jour, statut=statut,
                                gravite=grav, evolution=evo))
                        if nb_f > 0:
                            lignes.append(DeclarationCas(
                                maladie=maladie, region=region, district=district,
                                commune=commune, structure=structure,
                                sexe="F", age=AGE_MID[bi], nombre_cas=nb_f,
                                date_notification=jour, statut=statut,
                                gravite=grav, evolution=evo))
        DeclarationCas.objects.bulk_create(lignes, batch_size=1000)

        # 6) Alertes automatiques
        nb_alertes = services.regenerer_alertes()

        # 7) Comptes de démonstration (un par rôle)
        User.objects.filter(username__in=[c[0] for c in COMPTES_DEMO]).delete()
        for email, prenom, nom, role, rcode, est_admin in COMPTES_DEMO:
            u = User(username=email, email=email, first_name=prenom, last_name=nom,
                     is_staff=est_admin, is_superuser=est_admin)
            u.set_password(DEMO_PWD)
            u.save()
            Profil.objects.create(user=u, role=role,
                                  region=regions[rcode] if rcode else None)

        self.stdout.write(self.style.SUCCESS(
            f"OK — {Region.objects.count()} régions, {District.objects.count()} départements, "
            f"{Commune.objects.count()} communes, {Structure.objects.count()} centres de santé, "
            f"{Maladie.objects.count()} maladies, {DeclarationCas.objects.count()} déclarations, "
            f"{nb_alertes} alertes, {len(COMPTES_DEMO)} comptes démo (mdp : {DEMO_PWD})."))
