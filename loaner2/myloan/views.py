from django.shortcuts import render

def welcome(request):  
    return render(request, 'welcome.html')  # Added app directory prefix

from django.contrib.auth import authenticate, login
from django.contrib import messages

def signin(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')  # Replace with your home URL name
        else:
            messages.error(request, 'Invalid email or password')
            return redirect('signin')
    
    return render(request, 'signin.html')

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .models import CustomUser
from datetime import datetime
from decimal import Decimal

def signup(request):
    if request.method == 'POST':
        try:
            # Create user with form data
            user = CustomUser.objects.create_user(
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name'],
                date_of_birth=datetime.strptime(request.POST['date_of_birth'], '%Y-%m-%d').date(),
                monthly_income=Decimal(request.POST['monthly_income']),
                place_of_work=request.POST['place_of_work'],
                national_id_number=request.POST['national_id_number'],
                id_photo=request.FILES.get('id_photo'),
                 payslip=request.FILES.get('payslip')  # Add this line
            )
            
            # Log the user in
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')  # Replace with your success URL

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('signup')

    return render(request, 'signup.html')

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Loan
from .forms import LoanApplicationForm
import subprocess
import os
from django.contrib import messages
#from emailer import send_loan_email
from myloan.emailer import send_loan_email
'''
@login_required
def apply(request):
    print('testing')
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.user = request.user
            loan.interest_rate = 30  # 30% interest
            loan.status = 'pending'
            print('testing...')
            loan.save()

            # ✅ Prepare email data
            sender_email = "mojalefajefff@gmail.com"
            app_password = "jcitebdrdlhsyklj"  # Gmail App Password, NOT your login password
            receiver_email = request.user.email  # Or form.cleaned_data.get('email') if you're collecting emails
            subject = "Loan Application Received"
            message = f"Dear {request.user.username},\n\nYour loan application for M{loan.amount} has been received and is currently being reviewed."

            # ✅ Send email
            send_loan_email(sender_email, receiver_email, subject, message, app_password)

            return redirect('loan_success')

        messages.error(request, 'Please correct the form errors')
    else:
        form = LoanApplicationForm(initial={'amount': 5000})

    return render(request, 'apply.html', {'form': form})
'''


from django.contrib.auth import logout
from django.shortcuts import redirect

def LogoutView(request):
    logout(request)
    return redirect('home')  # Redirect to home page after logout

@login_required
def home(request):
    loans = Loan.objects.filter(user=request.user).order_by('-date_applied')
    
    # Calculate total outstanding for approved loans
    approved_loans = loans.filter(status='approved')
    total_outstanding = sum(
        loan.total_owed for loan in approved_loans
    )
    
    context = {
        'loans': loans,
        'total_outstanding': total_outstanding,
        'credit_score': request.user.credit_score,
    }
    return render(request, 'home.html', context)
import requests
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
import smtplib

def check_central_bank_records(user):
    """Check for outstanding loans in other banks via mockAPI"""
    try:
        response = requests.get(
            'https://680fbece27f2fdac240f3f59.mockapi.io/api1/v1/Central_Bank_Of_Lesotho',
            timeout=5
        )
        response.raise_for_status()
        
        for record in response.json():
            if (str(record.get('id', '')).lower() == str(user.id).lower() or \
               (record.get('firstname', '').lower() == user.first_name.lower() and \
               record.get('lastname', '').lower() == user.last_name.lower())):
                loan_amount = Decimal(str(record.get('loanamount', 0)))
                if loan_amount > 0:
                    return {
                        'has_loan': True,
                        'amount': loan_amount,
                        'bank_record': record
                    }
        return {'has_loan': False, 'amount': Decimal('0.00')}
    
    except requests.RequestException as e:
        print(f"API Error: {e}")
        return {'has_loan': True, 'error': "Couldn't verify with Central Bank. Please try again later."}

def calculate_total_borrowed(user):
    """Calculate total borrowed amount including interest"""
    total = Decimal('0.00')
    for loan in user.loans.filter(status='approved'):
        total += loan.amount * (Decimal('1') + (loan.interest_rate/Decimal('100')))
    return total

def apply(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    form = LoanApplicationForm(request.POST or None)
    context = {
        'form': form,
        'loan_limit': Decimal('20000.00'),
        'central_bank_check': check_central_bank_records(request.user)
    }
    
    context = {
        'form': form,
        'loan_limit': Decimal('20000.00'),
        'central_bank_check': check_central_bank_records(request.user),
        'user_monthly_income': request.user.monthly_income  # Add this line
    }

    if request.method == 'POST' and form.is_valid():
        # Check Central Bank records first
        cb_check = check_central_bank_records(request.user)
        if cb_check.get('has_loan'):
            err_msg = cb_check.get('error') or f"You owe M{cb_check['amount']:.2f} to other banks. Settle this first."
            messages.error(request, err_msg)
            return render(request, 'apply.html', context)
        
        # Check existing loans
        existing_total = calculate_total_borrowed(request.user)
        proposed_amount = form.cleaned_data['amount']
        proposed_total = proposed_amount * (Decimal('1.30'))  # 30% interest
        
        if existing_total >= Decimal('20000.00'):
            messages.error(request, "You've reached your M20,000 limit. Pay existing loans first.")
            return render(request, 'apply.html', context)
        
        if (existing_total + proposed_total) > Decimal('20000.00'):
            messages.error(request,
                f"Current debt: M{existing_total:.2f}. With M{proposed_amount:.2f} loan (M{proposed_total:.2f} total), you'll exceed M20,000 limit.")
            return render(request, 'apply.html', context)
        
        # All checks passed - save loan
        loan = form.save(commit=False)
        loan.user = request.user
        loan.interest_rate = 30
        loan.save()

        # Send email
        try:
            email = EmailMessage(
                subject="Your Loan Application",
                body=f"""Hi {request.user.first_name},
                
Your M{loan.amount:.2f} loan application was received.
Total repayable: M{proposed_total:.2f} (30% interest)

We'll contact you shortly.
""",
                from_email="CrediTech <loans@creditech.com>",
                to=[request.user.email]
            )
            email.send()
            messages.success(request, "Application submitted! Check your email.")
        except Exception as e:
            messages.warning(request, "Application submitted but email failed.")
        
        return redirect('loan_success')
    
    # Add current loan total to context for GET requests
    context['current_loan_total'] = calculate_total_borrowed(request.user)
    return render(request, 'apply.html', context)

def loan_success(request):
    return render(request, 'loan_success.html')

@login_required
def record_payment(request, loan_id):
    if request.method == 'POST':
        try:
            loan = Loan.objects.get(id=loan_id, user=request.user)
            is_on_time = request.POST.get('on_time', 'false').lower() == 'true'
            
            loan.total_payments += 1
            if is_on_time:
                loan.payments_made_on_time += 1
            loan.save()
            
            messages.success(request, f"Payment recorded! Your new credit score is {request.user.credit_score}")
        except Exception as e:
            messages.error(request, f"Error recording payment: {str(e)}")
    
    return redirect('home')


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Loan

@login_required
def loan_history(request):
    loans = Loan.objects.filter(user=request.user).order_by('-date_applied')
    return render(request, 'history.html', {'loans': loans})

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm
from .models import CustomUser

@login_required
def settings_view(request):
    user = request.user
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            # Handle password change separately
            current_password = form.cleaned_data.get('current_password')
            new_password = form.cleaned_data.get('new_password')
            
            if current_password and new_password:
                if not user.check_password(current_password):
                    messages.error(request, 'Your current password was entered incorrectly')
                    return redirect('settings')
                user.set_password(new_password)
            
            form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('settings')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = UserUpdateForm(instance=user)
    
    return render(request, 'settings.html', {'form': form})

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserUpdateForm

@login_required
def settings(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Handle password change if provided
            current_password = form.cleaned_data.get('current_password')
            new_password = form.cleaned_data.get('new_password')
            
            if current_password and new_password:
                if request.user.check_password(current_password):
                    user.set_password(new_password)
                    messages.success(request, 'Your password has been updated!')
                else:
                    messages.error(request, 'Your current password was entered incorrectly.')
                    return redirect('settings')
            
            user.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('settings')
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'settings.html', {'form': form})