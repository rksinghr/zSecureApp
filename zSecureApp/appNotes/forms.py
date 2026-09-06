from django import forms

class ConfidentialNoteForm(forms.Form):
    comment = forms.CharField(
        max_length=10000,
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "autocomplete": "off",
                "class": "form-control",
                "placeholder": "Write your confidential note here..."
            }
        )
    )
