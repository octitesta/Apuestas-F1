from django import forms
from .models import Apuesta

class ApuestaForm(forms.ModelForm):
    class Meta:
        model = Apuesta
        fields = ["piloto"]
        widgets = {
            'piloto': forms.Select(attrs={'class': 'form-select'})
            }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop("usuario", None)
        self.carrera = kwargs.pop("carrera", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if self.usuario and self.carrera:
            if Apuesta.objects.filter(
                usuario=self.usuario,
                carrera=self.carrera
            ).exists():
                raise forms.ValidationError("Ya apostaste en esta carrera.")

        return cleaned_data