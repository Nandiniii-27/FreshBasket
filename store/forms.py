from django import forms
from .models import DeliveryAddress


class DeliveryAddressForm(forms.ModelForm):

    class Meta:
        model = DeliveryAddress

        fields = [
            'full_name',
            'mobile',
            'address',
            'city',
            'pincode'
        ]

        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }