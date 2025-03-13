from django import forms
from django.utils.translation import gettext_lazy as _

from oscar.core.loading import get_class, get_model
from django.contrib.gis.geos import Point

Branch = get_model("school", "Branch")
class BranchForm(forms.ModelForm):
    latitude = forms.DecimalField(
        max_digits=9, 
        decimal_places=6,
        help_text=_("Latitude coordinate (between -90 and 90)")
    )
    longitude = forms.DecimalField(
        max_digits=9, 
        decimal_places=6,
        help_text=_("Longitude coordinate (between -180 and 180)")
    )

    class Meta:
        model = Branch
        fields = ['name', 'reference', 'manager_name', 'phone', 'email', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter unique branch reference number')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
       # Add bootstrap classes to all fields except checkbox
        for field_name, field in self.fields.items():
            if field_name != 'is_active':  # Skip the is_active field
                field.widget.attrs['class'] = 'form-control'

        # Set initial values for lat/lng if instance exists
        if self.instance.pk and self.instance.location:
            self.fields['latitude'].initial = self.instance.location.y
            self.fields['longitude'].initial = self.instance.location.x
        else:
            # Set default values for new instances
            self.fields['latitude'].initial = 24.7136
            self.fields['longitude'].initial = 46.6753

    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('latitude')
        lng = cleaned_data.get('longitude')
        
        if lat is not None and (lat < -90 or lat > 90):
            self.add_error('latitude', _('Latitude must be between -90 and 90'))
            
        if lng is not None and (lng < -180 or lng > 180):
            self.add_error('longitude', _('Longitude must be between -180 and 180'))
            
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Create Point object from lat/lng
        lat = self.cleaned_data.get('latitude', 24.7136)
        lng = self.cleaned_data.get('longitude', 46.6753)
        print(lat, lng)
        instance.location = Point(float(lng), float(lat))
        
        if commit:
            instance.save()
        return instance
