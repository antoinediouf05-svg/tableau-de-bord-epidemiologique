from django import forms

from .models import Commune, DeclarationCas, District, Structure


class DeclarationForm(forms.ModelForm):
    """Formulaire de notification d'un cas ou foyer suspecté."""

    class Meta:
        model = DeclarationCas
        fields = ['region', 'district', 'commune', 'structure', 'maladie',
                  'sexe', 'age', 'nombre_cas', 'date_notification',
                  'statut', 'gravite', 'evolution', 'observations']
        widgets = {
            'region': forms.Select(attrs={'class': 'input'}),
            'district': forms.Select(attrs={'class': 'input'}),
            'commune': forms.Select(attrs={'class': 'input'}),
            'structure': forms.Select(attrs={'class': 'input'}),
            'maladie': forms.Select(attrs={'class': 'input'}),
            'sexe': forms.RadioSelect(),
            'statut': forms.RadioSelect(),
            'gravite': forms.RadioSelect(),
            'evolution': forms.RadioSelect(),
            'age': forms.NumberInput(attrs={'class': 'input', 'min': 0, 'placeholder': '—'}),
            'nombre_cas': forms.NumberInput(attrs={'class': 'input', 'min': 1}),
            'date_notification': forms.DateInput(attrs={'class': 'input', 'type': 'date'},
                                                 format='%Y-%m-%d'),
            'observations': forms.Textarea(attrs={'class': 'input', 'rows': 3,
                                                  'placeholder': 'Symptômes, contexte du foyer…'}),
        }

    def __init__(self, *args, agent_region=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['region'].empty_label = "Sélectionner…"
        self.fields['district'].empty_label = "Sélectionner…"
        self.fields['commune'].empty_label = "Sélectionner…"
        self.fields['structure'].empty_label = "Sélectionner…"
        # Commune / centre de santé : facultatifs (modèle agrégé)
        self.fields['commune'].required = False
        self.fields['structure'].required = False
        # Sexe : seulement M / F (pas d'option vide dans les boutons)
        self.fields['sexe'].choices = [('M', 'Masculin'), ('F', 'Féminin')]
        self.fields['sexe'].required = False
        # <input type="date"> envoie/attend le format ISO
        self.fields['date_notification'].input_formats = ['%Y-%m-%d', '%d/%m/%Y']
        # Les listes commune/centre sont remplies dynamiquement (cascade JS) :
        # on accepte toute valeur valide côté serveur sans pré-charger 500 options.
        self.fields['commune'].queryset = Commune.objects.all()
        self.fields['structure'].queryset = Structure.objects.all()
        # Agent régional : région verrouillée, départements limités à sa région
        if agent_region is not None:
            self.fields['region'].initial = agent_region
            self.fields['region'].disabled = True
            self.fields['region'].required = False
            self.fields['district'].queryset = District.objects.filter(region=agent_region)

    def clean(self):
        cleaned = super().clean()
        region = cleaned.get('region')
        district = cleaned.get('district')
        commune = cleaned.get('commune')
        structure = cleaned.get('structure')
        if region and district and district.region_id != region.id:
            self.add_error('district', "Ce département n'appartient pas à la région choisie.")
        if district and commune and commune.district_id != district.id:
            self.add_error('commune', "Cette commune n'appartient pas au département choisi.")
        if commune and structure and structure.commune_id != commune.id:
            self.add_error('structure', "Ce centre de santé n'appartient pas à la commune choisie.")
        return cleaned
