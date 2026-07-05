from django.contrib.auth.models import User
from django.db import models


# ─────────────────────────────────────────────
# RÉGION — Une région sanitaire du Sénégal (14)
# ─────────────────────────────────────────────
class Region(models.Model):

    code = models.CharField(max_length=2, unique=True,
                            help_text="Code court de la région, ex. DK pour Dakar.")
    nom = models.CharField(max_length=80)
    nom_court = models.CharField(max_length=20, blank=True)
    population = models.PositiveIntegerField(help_text="Population totale de la région.")
    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Région"
        verbose_name_plural = "Régions"
        ordering = ['nom']


# ─────────────────────────────────────────────
# DÉPARTEMENT — rattaché à une région (niveau 2)
# (modèle historiquement nommé « District » : on le
#  conserve comme niveau « Département » de la hiérarchie)
# Association 1→N : une Région contient plusieurs Départements
# ─────────────────────────────────────────────
class District(models.Model):

    region = models.ForeignKey(Region, on_delete=models.CASCADE,
                               related_name='districts')
    nom = models.CharField(max_length=80)

    def __str__(self):
        return f"{self.nom} ({self.region.code})"

    class Meta:
        unique_together = ['region', 'nom']
        verbose_name = "Département"
        verbose_name_plural = "Départements"
        ordering = ['region', 'nom']


# ─────────────────────────────────────────────
# COMMUNE — rattachée à un département (niveau 3)
# Association 1→N : un Département contient plusieurs Communes
# ─────────────────────────────────────────────
class Commune(models.Model):

    district = models.ForeignKey(District, on_delete=models.CASCADE,
                                 related_name='communes', verbose_name="département")
    nom = models.CharField(max_length=80)

    def __str__(self):
        return self.nom

    class Meta:
        unique_together = ['district', 'nom']
        verbose_name = "Commune"
        verbose_name_plural = "Communes"
        ordering = ['district', 'nom']


# ─────────────────────────────────────────────
# CENTRE DE SANTÉ — structure déclarante (niveau 4, bas de la pyramide)
# Association N→1 vers Commune. C'est l'entité qui notifie les cas.
# ─────────────────────────────────────────────
class Structure(models.Model):

    TYPE_CHOICES = [
        ('hopital', 'Hôpital'),
        ('centre', 'Centre de santé'),
        ('poste', 'Poste de santé'),
    ]

    commune = models.ForeignKey(Commune, on_delete=models.CASCADE,
                                related_name='structures')
    nom = models.CharField(max_length=120)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='centre')

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Centre de santé"
        verbose_name_plural = "Centres de santé"
        ordering = ['commune', 'nom']


# ─────────────────────────────────────────────
# MALADIE — Maladie sous surveillance (6)
# Porte son propre seuil épidémique d'incidence
# ─────────────────────────────────────────────
class Maladie(models.Model):

    code = models.CharField(max_length=10, unique=True,
                            help_text="Code court, ex. palu, chol, covid.")
    nom = models.CharField(max_length=60)
    nom_en = models.CharField("nom (anglais)", max_length=60, blank=True)
    couleur = models.CharField(max_length=7, default="#1763C6",
                               help_text="Couleur d'accent (hex) utilisée dans les graphiques.")
    seuil_incidence = models.FloatField(
        "seuil épidémique",
        help_text="Seuil d'incidence pour 100 000 habitants au-delà duquel une alerte est déclenchée.",
    )
    cfr = models.FloatField("létalité (%)", default=0,
                            help_text="Case Fatality Rate : pourcentage de cas mortels.")
    rt = models.FloatField("taux de reproduction (Rt)", default=1.0)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Maladie"
        verbose_name_plural = "Maladies"
        ordering = ['nom']


# ─────────────────────────────────────────────
# DÉCLARATION DE CAS — Notification d'un cas / foyer
# Association N→1 vers Maladie, Région et District
# C'est la donnée brute que le backend agrège.
# ─────────────────────────────────────────────
class DeclarationCas(models.Model):

    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    STATUT_CHOICES = [
        ('suspecte', 'Suspecté'),
        ('probable', 'Probable'),
        ('confirme', 'Confirmé'),
    ]
    GRAVITE_CHOICES = [
        ('modere', 'Modéré'),
        ('severe', 'Sévère'),
        ('critique', 'Critique'),
    ]
    # Évolution clinique du cas (issue) — distincte de la gravité (sévérité)
    EVOLUTION_CHOICES = [
        ('en_cours', 'En cours'),
        ('gueri', 'Guéri'),
        ('decede', 'Décédé'),
    ]

    maladie = models.ForeignKey(Maladie, on_delete=models.CASCADE,
                                related_name='declarations')
    region = models.ForeignKey(Region, on_delete=models.CASCADE,
                               related_name='declarations')
    district = models.ForeignKey(District, on_delete=models.CASCADE,
                                 related_name='declarations', verbose_name="département")
    commune = models.ForeignKey(Commune, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='declarations')
    structure = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='declarations', verbose_name="centre de santé")
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES, blank=True)
    age = models.PositiveSmallIntegerField("âge", null=True, blank=True)
    nombre_cas = models.PositiveIntegerField("nombre de cas", default=1)
    date_notification = models.DateField()
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES,
                              default='suspecte')
    gravite = models.CharField("gravité", max_length=10, choices=GRAVITE_CHOICES,
                               default='modere')
    evolution = models.CharField("évolution", max_length=10, choices=EVOLUTION_CHOICES,
                                 default='en_cours')
    observations = models.TextField("observations cliniques", blank=True)
    declare_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='declarations', verbose_name="déclaré par")
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.maladie.code} · {self.region.code} · {self.nombre_cas} cas ({self.date_notification})"

    class Meta:
        verbose_name = "Déclaration de cas"
        verbose_name_plural = "Déclarations de cas"
        ordering = ['-date_notification', '-date_creation']


# ─────────────────────────────────────────────
# ALERTE — Générée automatiquement quand l'incidence
# d'une (Maladie, Région) dépasse le seuil épidémique.
# Calculée par les services à partir des déclarations.
# ─────────────────────────────────────────────
class Alerte(models.Model):

    NIVEAU_CHOICES = [
        (1, 'Modéré'),
        (2, 'Élevé'),
        (3, 'Critique'),
    ]
    STATUT_CHOICES = [
        ('active', 'Active'),
        ('prise_en_charge', 'Prise en charge'),
        ('resolue', 'Résolue'),
    ]
    # Quelle règle a déclenché l'alerte (cf. services.regenerer_alertes)
    DECLENCHEUR_CHOICES = [
        ('incidence', "Seuil d'incidence hebdomadaire"),
        ('cas_24h', "Seuil de cas en 24h"),
        ('les_deux', "Incidence + cas 24h"),
    ]

    maladie = models.ForeignKey(Maladie, on_delete=models.CASCADE,
                                related_name='alertes')
    region = models.ForeignKey(Region, on_delete=models.CASCADE,
                               related_name='alertes')
    incidence = models.FloatField(help_text="Incidence observée pour 100 000 hab.")
    seuil = models.FloatField(help_text="Seuil épidémique de la maladie au moment de la détection.")
    ratio = models.FloatField(help_text="incidence / seuil (≥ 1 = dépassement).")
    pic_24h = models.PositiveIntegerField("pic de cas en 24h", default=0,
                                          help_text="Plus grand nombre de cas notifiés en une journée sur la semaine.")
    declencheur = models.CharField(max_length=10, choices=DECLENCHEUR_CHOICES, default='incidence',
                                   help_text="Règle qui a déclenché l'alerte.")
    niveau = models.IntegerField(choices=NIVEAU_CHOICES, default=1)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='active')
    date_detection = models.DateTimeField(auto_now_add=True)

    @property
    def depassement(self):
        """Pourcentage de dépassement du seuil (ex. +35 %)."""
        return round((self.ratio - 1) * 100)

    def __str__(self):
        return f"{self.maladie.nom} — {self.region.nom} ({self.get_niveau_display()})"

    class Meta:
        # Une seule alerte courante par couple (maladie, région)
        unique_together = ['maladie', 'region']
        verbose_name = "Alerte"
        verbose_name_plural = "Alertes"
        ordering = ['-ratio']


# ─────────────────────────────────────────────
# PROFIL — Extension du User Django (1:1)
# Porte le rôle de l'utilisateur et sa région de
# rattachement (pour les agents régionaux).
# ─────────────────────────────────────────────
class Profil(models.Model):

    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('agent', 'Agent régional'),
        ('epi', 'Épidémiologiste'),
        ('decideur', 'Décideur ministériel'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='epi')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='agents',
                               help_text="Région de rattachement (pour les agents régionaux).")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.get_role_display()}"

    @property
    def peut_declarer(self):
        return self.role in ('admin', 'agent')

    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"


# ─────────────────────────────────────────────
# JOURNAL DE CONNEXION — audit de sécurité
# Alimenté automatiquement par les signaux d'authentification
# (cf. sanitrax/signals.py). Consultable uniquement dans l'admin.
# ─────────────────────────────────────────────
class JournalConnexion(models.Model):

    EVENEMENT_CHOICES = [
        ('connexion', 'Connexion'),
        ('deconnexion', 'Déconnexion'),
        ('echec', 'Échec de connexion'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='connexions', verbose_name="utilisateur")
    email_saisi = models.CharField("e-mail saisi", max_length=254, blank=True)
    evenement = models.CharField("événement", max_length=12, choices=EVENEMENT_CHOICES)
    date = models.DateTimeField("date et heure", auto_now_add=True)

    def __str__(self):
        qui = self.user.get_username() if self.user else (self.email_saisi or "—")
        return f"{self.get_evenement_display()} · {qui} · {self.date:%d/%m/%Y %H:%M}"

    class Meta:
        verbose_name = "Journal de connexion"
        verbose_name_plural = "Journal des connexions"
        ordering = ['-date']
