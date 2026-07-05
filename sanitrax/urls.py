from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Authentification
    path("connexion/", views.connexion, name="connexion"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),

    # Mot de passe oublié (vues intégrées Django ; e-mail affiché en console)
    path("mot-de-passe-oublie/", auth_views.PasswordResetView.as_view(
        template_name="auth/password_reset_form.html",
        email_template_name="auth/password_reset_email.html",
        subject_template_name="auth/password_reset_subject.txt"), name="password_reset"),
    path("mot-de-passe-oublie/envoye/", auth_views.PasswordResetDoneView.as_view(
        template_name="auth/password_reset_done.html"), name="password_reset_done"),
    path("reinitialiser/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="auth/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reinitialiser/termine/", auth_views.PasswordResetCompleteView.as_view(
        template_name="auth/password_reset_complete.html"), name="password_reset_complete"),

    # Tableau de bord
    path("", views.vue_ensemble, name="home"),
    path("carte/", views.carte, name="carte"),
    path("maladies/", views.maladies, name="maladies"),
    path("alertes/", views.alertes, name="alertes"),
    path("alertes/<int:pk>/prendre-en-charge/", views.prendre_en_charge, name="prendre_en_charge"),
    path("declaration/", views.declaration, name="declaration"),
    path("rapports/", views.rapports, name="rapports"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("export/excel/", views.export_excel, name="export_excel"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
]
