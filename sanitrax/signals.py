"""
Journal de connexion — branché sur les signaux d'authentification Django.

Chaque connexion réussie, déconnexion ou tentative échouée crée une entrée
dans JournalConnexion. Couvre aussi bien la page de login de l'application que
l'interface d'administration, puisque tout passe par ces signaux.
"""
from django.contrib.auth.signals import (user_logged_in, user_logged_out,
                                         user_login_failed)
from django.dispatch import receiver

from .models import JournalConnexion


@receiver(user_logged_in)
def journaliser_connexion(sender, request, user, **kwargs):
    JournalConnexion.objects.create(
        user=user,
        email_saisi=user.email or user.get_username(),
        evenement='connexion',
    )


@receiver(user_logged_out)
def journaliser_deconnexion(sender, request, user, **kwargs):
    if user is None:           # déconnexion d'une session déjà anonyme
        return
    JournalConnexion.objects.create(
        user=user,
        email_saisi=user.email or user.get_username(),
        evenement='deconnexion',
    )


@receiver(user_login_failed)
def journaliser_echec(sender, credentials, request=None, **kwargs):
    JournalConnexion.objects.create(
        email_saisi=credentials.get('username', '') or credentials.get('email', ''),
        evenement='echec',
    )
