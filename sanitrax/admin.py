from django.contrib import admin

from .models import (Alerte, Commune, DeclarationCas, District,
                     JournalConnexion, Maladie, Profil, Region, Structure)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'population')
    search_fields = ('nom', 'code')


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('nom', 'region')
    list_filter = ('region',)
    search_fields = ('nom',)


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ('nom', 'district')
    list_filter = ('district__region',)
    search_fields = ('nom',)


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type', 'commune')
    list_filter = ('type', 'commune__district__region')
    search_fields = ('nom',)


@admin.register(Maladie)
class MaladieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'seuil_incidence', 'cfr', 'rt')
    search_fields = ('nom', 'code')


@admin.register(DeclarationCas)
class DeclarationCasAdmin(admin.ModelAdmin):
    list_display = ('date_notification', 'maladie', 'region', 'district', 'commune',
                    'structure', 'nombre_cas', 'gravite', 'evolution', 'statut',
                    'sexe', 'age', 'declare_par')
    list_filter = ('maladie', 'region', 'gravite', 'evolution', 'statut', 'sexe')
    date_hierarchy = 'date_notification'
    search_fields = ('observations',)


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'region')
    list_filter = ('role', 'region')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')


@admin.register(JournalConnexion)
class JournalConnexionAdmin(admin.ModelAdmin):
    list_display = ('date', 'evenement', 'user', 'email_saisi')
    list_filter = ('evenement',)
    search_fields = ('email_saisi', 'user__username', 'user__email')
    date_hierarchy = 'date'

    # Journal d'audit : lecture seule (aucun ajout ni modification manuelle)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ('maladie', 'region', 'incidence', 'seuil', 'ratio', 'pic_24h',
                    'declencheur', 'niveau', 'statut', 'date_detection')
    list_filter = ('statut', 'niveau', 'declencheur', 'maladie')
