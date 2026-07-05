"""Variables disponibles dans tous les templates (barre du haut, sidebar)."""
from .models import Alerte, District
from .services import date_reference


def commun(request):
    d = date_reference()
    iso = d.isocalendar()

    role = role_label = ""
    peut_declarer = False
    initiales = ""
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        profil = getattr(user, "profil", None)
        if profil:
            role = profil.role
            role_label = profil.get_role_display()
            peut_declarer = profil.peut_declarer
        elif user.is_superuser:
            role, role_label, peut_declarer = "admin", "Administrateur", True
        nom = user.get_full_name() or user.username
        initiales = "".join(p[0] for p in nom.split()[:2]).upper() or nom[:2].upper()

    return {
        "nav_alertes_actives": Alerte.objects.exclude(statut="resolue").count(),
        "nb_districts": District.objects.count(),
        "epi_semaine": f"S{iso[1]} · {iso[0]}",
        "maj_label": d.strftime("%d/%m/%Y"),
        "user_role": role,
        "user_role_label": role_label,
        "peut_declarer": peut_declarer,
        "user_initiales": initiales,
    }
