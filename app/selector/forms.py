from django import forms
from django.forms.widgets import RadioSelect


class Authorize(forms.Form):
    """
    """
    login = forms.CharField(label=u'Login :', max_length=50, min_length=1)
    password = forms.CharField(label=u'Password :', max_length=50, min_length=5)
    redirect = forms.CharField(required=False)

