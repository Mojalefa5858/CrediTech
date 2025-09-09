from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import MinValueValidator
from .models import CustomUser, Loan
import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import MinValueValidator
import re

class CustomUserCreationForm(UserCreationForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'max': '2005-12-31'  # Ensures user is at least 18 years old
        }),
        required=True,
        help_text="You must be at least 18 years old"
    )
    
    monthly_income = forms.DecimalField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'placeholder': 'M',
            'class': 'form-control',
            'step': '100'
        }),
        validators=[MinValueValidator(0)],
        help_text="Your gross monthly income in M"
    )
    
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'placeholder': '+26650123456',
            'class': 'form-control',
            'pattern': '\+266[568]\d{7}',
            'title': 'Lesotho format: +266 followed by 8 digits starting with 5,6 or 8'
        }),
        help_text="Lesotho format: +266 followed by 8 digits (e.g. +26650123456)"
    )
    
    national_id_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'pattern': '[0-12]{12}',
            'title': '12-digit ID number',
            'class': 'form-control'
        }),
        help_text="Your 9-digit national ID number"
    )
    
    physical_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control'
        }),
        required=False
    )
    
    place_of_work = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    id_photo = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text="Upload a clear photo of your government-issued ID",
        required=True
    )

    class Meta:
        model = CustomUser
        fields = (
            'email', 'password1', 'password2',
            'first_name', 'last_name', 'date_of_birth',
            'monthly_income', 'phone_number', 
            'physical_address', 'place_of_work', 'national_id_number', 'id_photo'
        )
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


        payslip = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        help_text="Upload your most recent payslip (PDF or image)",
        required=True
    )



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = "Minimum 8 characters with at least one letter and one number"
        self.fields['password2'].label = "Confirm Password"
        
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not re.match(r'^\+266[568]\d{7}$', phone_number):
            raise forms.ValidationError(
                "Invalid Lesotho phone number. Must be +266 followed by 8 digits starting with 5, 6, or 8"
            )
        return phone_number

class LoanApplicationForm(forms.ModelForm):
    agree_to_terms = forms.BooleanField(
        required=True,
        label="I agree to the terms and conditions",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'agreeTerms'
        })
    )
    
    purpose = forms.ChoiceField(
        choices=Loan.LOAN_PURPOSE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'loanPurpose'
        }),
        initial='',  # Forces the empty label to show
        label="Loan Purpose",
        help_text="Select the primary purpose for this loan"
    )

    class Meta:
        model = Loan
        fields = ['amount', 'purpose', 'comments']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'min': '1000',
                'max': '50000',
                'step': '100',
                'id': 'loanAmount',
                'class': 'form-control',
                'placeholder': 'Enter amount between M1000 and M50000'
            }),
            'comments': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Optional additional information about your loan request',
                'style': 'resize: none;'
            }),
        }
        labels = {
            'amount': 'Loan Amount (M)',
            'comments': 'Additional Information'
        }
        help_texts = {
            'amount': 'Amount must be between M1000 and M50000',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['purpose'].empty_label = "--- Select Purpose ---"
        
        # Add form-control class to all fields automatically
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
                
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError("Please enter a valid loan amount")
            
        if amount <= 0:
            raise forms.ValidationError("Loan amount must be positive")
            
        if amount < 1000:
            raise forms.ValidationError("Minimum loan amount is M1000")
            
        if amount > 50000:
            raise forms.ValidationError("Maximum loan amount is M50000")
            
        return amount

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('agree_to_terms'):
            self.add_error('agree_to_terms', "You must agree to the terms and conditions")
        return cleaned_data


from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Loan

class CustomUserCreationForm(UserCreationForm):
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    monthly_income = forms.DecimalField(min_value=0, widget=forms.NumberInput(attrs={'placeholder': 'M'}))
    phone_number = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': '+26650123456'}))
    national_id_number = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'pattern': '[0-12]{12}'}))

    class Meta:
        model = CustomUser
        fields = ('email', 'password1', 'password2', 'first_name', 'last_name', 
                 'date_of_birth', 'monthly_income', 'phone_number',
                 'physical_address', 'place_of_work', 'national_id_number', 'id_photo')

class LoanApplicationForm(forms.ModelForm):
    agree_to_terms = forms.BooleanField(required=True, label="I agree to the terms and conditions")

    class Meta:
        model = Loan
        fields = ['amount', 'purpose', 'comments']
        widgets = {
            'amount': forms.NumberInput(attrs={'min': 1000, 'max': 50000, 'step': 100}),
            'purpose': forms.Select(attrs={'class': 'form-control'}),
            'comments': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and self.user and amount > self.user.monthly_income:
            raise forms.ValidationError(
                
            )
        return amount


from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import CustomUser

class UserUpdateForm(forms.ModelForm):
    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        required=False
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        required=False
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        required=False
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 
            'phone_number', 'date_of_birth', 'physical_address',
            'monthly_income', 'place_of_work', 'national_id_number',
            'id_photo', 'payslip'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        current_password = cleaned_data.get("current_password")

        if new_password or confirm_password or current_password:
            if not current_password:
                self.add_error('current_password', "Current password is required to change your password")
            if new_password != confirm_password:
                self.add_error('confirm_password', "The two password fields didn't match")
        
        return cleaned_data

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        pattern = r'^\+266[568]\d{7}$'
        if not re.match(pattern, phone_number):
            raise forms.ValidationError(
                'Invalid Lesotho phone number. Must be +266 followed by 8 digits starting with 5, 6, or 8'
            )
        return phone_number

    def clean_national_id_number(self):
        national_id = self.cleaned_data.get('national_id_number')
        if national_id and not national_id.isdigit() or len(national_id) != 12:
            raise forms.ValidationError('National ID must be 12 digits')
        return national_id


from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import CustomUser
import re

class UserUpdateForm(forms.ModelForm):
    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Required if changing password"
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Leave blank if you don't want to change password"
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 
            'phone_number', 'date_of_birth', 'physical_address',
            'monthly_income', 'place_of_work', 'national_id_number',
            'id_photo', 'payslip'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'physical_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'monthly_income': forms.NumberInput(attrs={'class': 'form-control'}),
            'place_of_work': forms.TextInput(attrs={'class': 'form-control'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'id_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'payslip': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        current_password = cleaned_data.get("current_password")

        if new_password or confirm_password or current_password:
            if not current_password:
                self.add_error('current_password', "Current password is required to change your password")
            elif new_password != confirm_password:
                self.add_error('confirm_password', "The two password fields didn't match")
        
        return cleaned_data

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        pattern = r'^\+266[568]\d{7}$'
        if phone_number and not re.match(pattern, phone_number):
            raise forms.ValidationError(
                'Invalid Lesotho phone number. Must be +266 followed by 8 digits starting with 5, 6, or 8'
            )
        return phone_number

    def clean_national_id_number(self):
        national_id = self.cleaned_data.get('national_id_number')
        if national_id and (not national_id.isdigit() or len(national_id) != 12):
            raise forms.ValidationError('National ID must be 12 digits')
        return national_id