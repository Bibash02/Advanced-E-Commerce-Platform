from django import forms
from .models import *

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'image']

class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'image', 'content']

class DeliveryDocumentForm(forms.ModelForm): 
    class Meta:
        model = DeliveryDocument
        exclude = ['user']
