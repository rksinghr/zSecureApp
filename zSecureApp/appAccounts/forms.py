# form.py
from django import forms

class EmailForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
        }))

class OTPForm(forms.Form):
    otp = forms.CharField(
        min_length=6,
        max_length=6
    )

    def clean_otp(self):
        otp = self.cleaned_data["otp"]

        if not otp.isdigit():
            raise forms.ValidationError(
                "Enter a valid verification code."
            )

        return otp

