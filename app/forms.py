from django import forms
from .models import *
import re

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'stock', 'image']

class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'image', 'content']

class DeliveryDocumentForm(forms.ModelForm):
    
    class Meta:
        model = DeliveryDocument
        fields = '__all__'
        exclude = ["user"]

        widgets = {
            'vehicle_type': forms.Select(
                choices=[
                    ("Bike", "Bike"),
                    ("Car", "Car")
                ]
            ),
        }

        # phone number validation
        def clean_phone(self):
            phone = self.cleaned_data.get("phone")

            if not re.fullmatch(r"9/d{9}", phone):
                raise forms.ValidationError(
                    "Phone number must be valid 10-digit Nepal number."
                )
            return phone
        
        # address validation
        def clean_address(self):
            address = self.cleaned_data.get("address")

            if len(address) < 5:
                raise   forms.ValidationError("Please enter a valid address in Nepal.")
            return address
        
        # vehicle number validation
        def clean_vehicle_number(self):
            vehicle_number = self.cleaned_data.get("vehicle_number")

            pattern = r"^[A-Za-z]{1,3}-?\d{1,4}$"

            if not re.match(pattern, vehicle_number):
                raise forms.ValidationError("Enter valid vehicle number (Example: BA-1234)")
            return vehicle_number
        
        # image validation
        def validate_image(self, file):
            if file:
                ext = file.name.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png']:
                    raise forms.ValidationError("only image file (jpg, jpeg, png) are allowed.")
            return file
        
        def clean_government_id(self):
            return self.validate_image(self.cleaned_data.get("government_id"))
        
        def clean_driving_license(self):
            return self.validate_image(self.cleaned_data.get("driving_license"))
        
        def clean_vehicle_document(self):
            return self.validate_image(self.cleaned_data.get("vehicle_document"))
        
        # cv validation
        def clean_cv(self):
            cv = self.cleaned_data.get("cv")

            if cv:
                ext = cv.name.split('.')[-1].lower()
                if ext != 'pdf':
                    raise forms.ValidationError("CV must be a pdf file.")
            return cv
        


class DeliveryDocumentForm(forms.ModelForm): 
    class Meta:
        model = DeliveryDocument
        exclude = ['user', 'created_at', 'status']

class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']

        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Your Full Name'
            }),

            'email': forms.EmailInput(attrs={
                'placeholder': 'Your Email Address'
            }),

            'phone': forms.TextInput(attrs={
                'placeholder': 'Phone Number'
            }),

            'subject': forms.TextInput(attrs={
                'placeholder': 'Subject of your message'
            }),

            'message': forms.Textarea(attrs={
                'placeholder': 'Write your message here...',
                'rows': 4
            }),
        }