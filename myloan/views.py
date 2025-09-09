from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt  # This is the crucial import
from django.http import JsonResponse
from .models import CustomUser
from datetime import datetime
from decimal import Decimal
import cv2
import pytesseract
import PyPDF2
import re
import os
import tempfile
import io

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

import os
import cv2
import re
import pytesseract
import tempfile
import PyPDF2
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import CustomUser
from datetime import datetime

# === UTILITIES ===

def clean_text(text):
    """Clean OCR text by removing common noise characters"""
    return re.sub(r'[|>]', '', text).strip()

def extract_fields_from_text(text):
    """Extract structured fields from OCR text with multiple fallback patterns"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    extracted = {
        "first_name": None,
        "surname": None,
        "date_of_birth": None,
        "id_number": None
    }

    for i, line in enumerate(lines):
        l = line.lower()

        # Surname extraction with multiple patterns
        if re.search(r'surname[:]?$', l) and i + 1 < len(lines):
            extracted['surname'] = lines[i + 1].strip()
        elif 'surname' in l:
            match = re.search(r'surname[:\-]?\s*(.+)', line, re.IGNORECASE)
            if match:
                extracted["surname"] = match.group(1).strip()

        # First name extraction with multiple patterns
        if re.search(r'(first name|first names?)[:]?$', l) and i + 1 < len(lines):
            extracted['first_name'] = lines[i + 1].strip()
        elif 'first name' in l or 'first names' in l:
            match = re.search(r'(first names?)[:\-]?\s*(.+)', line, re.IGNORECASE)
            if match:
                extracted["first_name"] = match.group(2).strip()

        # Date of birth extraction
        dob_match = re.search(r'date of birth[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})', l)
        if dob_match and not extracted["date_of_birth"]:
            extracted["date_of_birth"] = dob_match.group(1)

        # ID number extraction
        id_match = re.search(r'id\s*(?:no|number)?[:\-]?\s*([A-Z0-9\/\-]{6,})', l)
        if id_match and not extracted["id_number"]:
            extracted["id_number"] = id_match.group(1)

    # Second pass - full text search as fallback
    if not extracted["id_number"]:
        match = re.search(r'id\s*(?:no|number)?[:\-]?\s*([A-Z0-9\/\-]{6,})', text, re.IGNORECASE)
        if match:
            extracted["id_number"] = match.group(1)

    if not extracted["date_of_birth"]:
        match = re.search(r'date of birth[:\-]?\s*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4})', text, re.IGNORECASE)
        if match:
            extracted["date_of_birth"] = match.group(1)

    return {k: clean_text(v) if v else None for k, v in extracted.items()}

def check_name_match(text, first_name, surname):
    """Flexible name matching with OCR error tolerance"""
    if not first_name or not surname:
        return False, False
    
    # Create regex patterns with tolerance for OCR errors
    first_pattern = re.compile(r'\b' + re.sub(r'[^a-z]', '.?', first_name.lower()) + r'\b', re.IGNORECASE)
    surname_pattern = re.compile(r'\b' + re.sub(r'[^a-z]', '.?', surname.lower()) + r'\b', re.IGNORECASE)
    
    first_found = bool(first_pattern.search(text.lower()))
    last_found = bool(surname_pattern.search(text.lower()))
    
    return first_found, last_found

# === VALIDATION FUNCTIONS ===

def validate_lesotho_id(image_path):
    """Validate Lesotho ID document with improved OCR and field extraction"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {'is_valid': False, 'error': 'Could not read image file'}

        # Preprocess image for better OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # OCR extraction
        ocr_text = pytesseract.image_to_string(thresh)
        text_lower = ocr_text.lower()

        # Document validation criteria
        required_keywords = [
            'surname', 
            'first name', 
            'date of birth', 
            'id no', 
            'identity',
            'national'
        ]
        
        # Check for minimum required fields
        valid_count = sum(1 for keyword in required_keywords if keyword in text_lower)
        is_valid = valid_count >= 3

        # Extract structured data
        extracted = extract_fields_from_text(ocr_text)

        return {
            'is_valid': is_valid,
            'document_type': "National ID" if is_valid else None,
            'ocr_text': ocr_text,
            'first_name': extracted['first_name'],
            'surname': extracted['surname'],
            'id_number': extracted['id_number'],
            'date_of_birth': extracted['date_of_birth'],
            'error': None
        }
    except Exception as e:
        return {'is_valid': False, 'error': str(e)}

def validate_payslip(payslip_file):
    """Validate PDF payslip document with comprehensive checks"""
    try:
        # Check file extension first
        if not payslip_file.name.lower().endswith('.pdf'):
            return {
                'is_valid': False,
                'message': "Only PDF files are accepted for payslips",
                'full_text': "",
                'employee_name': None
            }

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            for chunk in payslip_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        # Extract text from PDF
        with open(tmp_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])

        # Clean up temp file
        os.unlink(tmp_path)

        if not text.strip():
            return {
                'is_valid': False,
                'message': "No text found in PDF document",
                'full_text': text,
                'employee_name': None
            }

        # Extract employee name
        employee_name = None
        name_patterns = [
            r'employee\s*(?:name|names?)\s*[:]?\s*([^\n]+)',
            r'name\s*of\s*employee\s*[:]?\s*([^\n]+)',
            r'staff\s*name\s*[:]?\s*([^\n]+)',
            r'pay\s*to\s*[:]?\s*([^\n]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                employee_name = match.group(1).strip()
                break

        # Basic validation - must have some financial data
        has_financial_data = bool(
            re.search(r'(net\s*pay|gross\s*pay|salary|payment|earnings|deductions|allowance|bonus|[mMrRuUsSdD\$£€]\s*\d+)', 
                     text, re.IGNORECASE)
        )

        is_valid = has_financial_data

        return {
            'is_valid': is_valid,
            'message': "Valid PDF payslip" if is_valid else "Invalid PDF payslip - missing financial data",
            'full_text': text,
            'employee_name': employee_name
        }
        
    except Exception as e:
        return {
            'is_valid': False,
            'message': f"PDF processing error: {str(e)}",
            'full_text': "",
            'employee_name': None
        }

# === VIEWS ===

@csrf_exempt
def extract_id_data(request):
    """API endpoint for auto-filling form data from ID"""
    if request.method == 'POST' and request.FILES.get('id_photo'):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                for chunk in request.FILES['id_photo'].chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name

            id_result = validate_lesotho_id(tmp_path)
            os.unlink(tmp_path)

            return JsonResponse({
                'success': id_result.get('is_valid', False),
                'first_name': id_result.get('first_name', ''),
                'last_name': id_result.get('surname', ''),
                'id_number': id_result.get('id_number', ''),
                'date_of_birth': id_result.get('date_of_birth', ''),
                'document_valid': id_result.get('is_valid', False),
                'ocr_text': id_result.get('ocr_text', '')[:500] + '...' if id_result.get('ocr_text') else '',
                'error': id_result.get('error', '')
            })

        except Exception as e:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'No ID photo provided'})

def signup(request):
    """User registration view with strict name matching validation"""
    if request.method == 'POST':
        try:
            # Validate required fields
            required_fields = [
                'first_name', 'last_name', 'email', 'password', 'confirm_password',
                'phone_number', 'monthly_income', 'place_of_work',
                'physical_address', 'national_id_number', 'date_of_birth'
            ]
            missing = [field for field in required_fields if not request.POST.get(field)]
            if missing:
                messages.error(request, f"Missing required fields: {', '.join(missing)}")
                return redirect('signup')

            # Password confirmation
            if request.POST['password'] != request.POST['confirm_password']:
                messages.error(request, 'Passwords do not match')
                return redirect('signup')

            # Document validation
            if not request.FILES.get('id_photo') or not request.FILES.get('payslip'):
                messages.error(request, 'Both ID photo and payslip are required')
                return redirect('signup')

            # Validate ID document
            with tempfile.NamedTemporaryFile(delete=False) as id_tmp:
                for chunk in request.FILES['id_photo'].chunks():
                    id_tmp.write(chunk)
                id_path = id_tmp.name

            id_result = validate_lesotho_id(id_path)
            os.unlink(id_path)
            
            if not id_result.get('is_valid'):
                messages.error(request, 'Invalid ID document. Please upload a valid Lesotho national ID.')
                return redirect('signup')

            # Validate PDF payslip
            payslip_result = validate_payslip(request.FILES['payslip'])
            
            if not payslip_result.get('is_valid'):
                messages.error(request, payslip_result['message'])
                return redirect('signup')

            # Get names from form and documents
            form_first_name = request.POST['first_name'].strip()
            form_last_name = request.POST['last_name'].strip()
            id_first_name = id_result.get('first_name', '').strip() if id_result.get('first_name') else None
            id_last_name = id_result.get('surname', '').strip() if id_result.get('surname') else None
            payslip_text = payslip_result['full_text']

            # Check if form names match ID names (if ID has names)
            id_name_match = True
            if id_first_name and id_last_name:
                id_first_match = form_first_name.lower() == id_first_name.lower()
                id_last_match = form_last_name.lower() == id_last_name.lower()
                
                if not (id_first_match and id_last_match):
                    messages.warning(request, 
                        f"Names on ID ({id_first_name} {id_last_name}) don't match form names ({form_first_name} {form_last_name})")
                    id_name_match = False

            # Check if form names match payslip names
            first_found, last_found = check_name_match(payslip_text, form_first_name, form_last_name)
            
            if not (first_found and last_found):
                # Try matching with ID names if form names didn't match
                if id_first_name and id_last_name:
                    first_found, last_found = check_name_match(payslip_text, id_first_name, id_last_name)
                    if first_found and last_found:
                        messages.info(request, 
                            f"Using names from ID document ({id_first_name} {id_last_name}) as they match the payslip")
                        form_first_name = id_first_name
                        form_last_name = id_last_name
                    else:
                        messages.error(request, 
                            "Your names don't match the payslip. Please upload your own documents.")
                        return redirect('signup')
                else:
                    messages.error(request, 
                        "Your names don't match the payslip. Please upload your own documents.")
                    return redirect('signup')

            # All validations passed - create account
            user = CustomUser.objects.create_user(
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=form_first_name,
                last_name=form_last_name,
                phone_number=request.POST['phone_number'],
                date_of_birth=datetime.strptime(request.POST['date_of_birth'], '%Y-%m-%d').date(),
                monthly_income=Decimal(request.POST['monthly_income']),
                place_of_work=request.POST['place_of_work'],
                physical_address=request.POST['physical_address'],
                national_id_number=request.POST['national_id_number'],
                id_photo=request.FILES['id_photo'],
                payslip=request.FILES['payslip']
            )

            # Log the user in
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to your account.')
            return redirect('home')

        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
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


from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import JsonResponse
from .models import CentralBankOfLesotho

def apply(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to apply for a loan')
        return redirect('login')
    
    form = LoanApplicationForm(request.POST or None)
    
    # Get salary-based principal limit (not including interest)
    def get_principal_limit(salary):
        salary = salary or Decimal('0.00')
        if salary < Decimal('2000'): return Decimal('20000.00')
        if salary < Decimal('5000'): return Decimal('20000.00')
        if salary < Decimal('10000'): return Decimal('50000.00')
        if salary < Decimal('20000'): return Decimal('100000.00')
        if salary < Decimal('30000'): return Decimal('150000.00')
        return Decimal('250000.00')
    
    # Check Central Bank records with credit bureau rules
    def check_central_bank_records(user):
        try:
            record = CentralBankOfLesotho.objects.filter(national_id=user.national_id_number).first()
            if not record:
                return {'has_loan': False}
            
            # Credit bureau rules based on salary brackets
            salary = user.monthly_income or Decimal('0.00')
            current_debt = record.loan_amount
            
            # Define maximum allowed debt for each salary bracket
            if salary < Decimal('5000'):
                max_allowed = Decimal('20000.00')
                bracket = "2K-5K"
            elif salary < Decimal('10000'):
                max_allowed = Decimal('40000.00')
                bracket = "5K-10K"
            elif salary < Decimal('20000'):
                max_allowed = Decimal('50000.00')
                bracket = "10K-20K"
            elif salary < Decimal('30000'):
                max_allowed = Decimal('100000.00')
                bracket = "20K-30K"
            else:
                max_allowed = Decimal('125000.00')
                bracket = "30K+"
            
            if current_debt > max_allowed:
                return {
                    'has_loan': True,
                    'amount': current_debt,
                    'error': (
                        f"Credit Bureau Alert: Your salary bracket ({bracket}) allows maximum "
                        f"debt of M{max_allowed:.2f} with other banks. You currently owe "
                        f"M{current_debt:.2f}. Please settle existing loans first."
                    )
                }
            
            return {
                'has_loan': True,
                'amount': current_debt,
                'warning': (
                    f"Note: You currently owe M{current_debt:.2f} to other banks. "
                    f"Your salary bracket allows up to M{max_allowed:.2f} in total."
                )
            }
            
        except Exception as e:
            # If there's any error checking Central Bank records, assume no record
            return {'has_loan': False}
    
    principal_limit = get_principal_limit(request.user.monthly_income)
    current_principal_debt = calculate_total_borrowed(request.user) / Decimal('1.30')
    
    context = {
        'form': form,
        'loan_limit': principal_limit,
        'central_bank_check': check_central_bank_records(request.user),
        'user_monthly_income': request.user.monthly_income,
        'current_loan_total': calculate_total_borrowed(request.user)
    }

    if request.method == 'POST':
        if form.is_valid():
            # Check Central Bank records first with credit bureau rules
            cb_check = check_central_bank_records(request.user)
            if cb_check.get('has_loan') and cb_check.get('error'):
                messages.error(request, cb_check['error'])
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'messages': [{'text': cb_check['error'], 'tags': 'error'}]
                    })
                return render(request, 'apply.html', context)
            
            # Show warning if they have existing debt but still qualify
            if cb_check.get('has_loan') and cb_check.get('warning'):
                messages.warning(request, cb_check['warning'])
            
            proposed_amount = form.cleaned_data['amount']
            proposed_total = proposed_amount * Decimal('1.30')  # 30% interest
            
            # Check against principal limit (not including interest)
            if (current_principal_debt + proposed_amount) > principal_limit:
                remaining = principal_limit - current_principal_debt
                error_msg = (
                    f"Current principal debt: M{current_principal_debt:.2f}. " +
                    f"With M{proposed_amount:.2f} loan, you'll exceed your M{principal_limit:.2f} principal limit. " +
                    f"Maximum you can borrow now: M{remaining:.2f}"
                )
                messages.error(request, error_msg)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'messages': [{'text': error_msg, 'tags': 'error'}]
                    })
                return render(request, 'apply.html', context)
            
            # All checks passed - save loan
            loan = form.save(commit=False)
            loan.user = request.user
            loan.interest_rate = 30
            loan.status = 'pending'
            loan.save()

            # Send email
            email_sent = True
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
                email_sent = False
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'success': True,
                    'redirect_url': 'loan_success',
                    'messages': [
                        {
                            'text': "Application submitted! Check your email." if email_sent 
                                    else "Application submitted but email failed.",
                            'tags': 'success' if email_sent else 'warning'
                        }
                    ]
                }
                return JsonResponse(response_data)
            
            return redirect('loan_success')
        
        # Form is not valid
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {field: error.get_json_data() for field, error in form.errors.items()}
            return JsonResponse({
                'success': False,
                'errors': errors,
                'messages': [{'text': 'Please correct the errors below.', 'tags': 'error'}]
            })
    
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



from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Loan, PaidAccounts
from datetime import datetime, date

@login_required
def loan_history(request):
    # Fetch all loans for the user, including fully paid ones
    loans = Loan.objects.filter(user=request.user).order_by('-date_applied')
    
    # Fetch all payment activities for the user
    payments = PaidAccounts.objects.filter(loan__user=request.user).order_by('-created_at')
    
    # Combine loans and payments into a single activity list
    activities = []
    
    # Add loans to activities
    for loan in loans:
        # Debug: Print the type and value of date_applied
        print(f"loan.date_applied type: {type(loan.date_applied)}, value: {loan.date_applied}")
        
        # Convert date_applied to datetime
        try:
            if isinstance(loan.date_applied, date) and not isinstance(loan.date_applied, datetime):
                date_applied = datetime.combine(loan.date_applied, datetime.time(0, 0))
            else:
                # If it's already a datetime or unexpected type, use it or handle
                date_applied = loan.date_applied if isinstance(loan.date_applied, datetime) else datetime.now()
        except Exception as e:
            print(f"Error converting date_applied: {loan.date_applied}, error: {e}")
            date_applied = datetime.now()  # Fallback to current time
        
        activities.append({
            'type': 'loan',
            'date': date_applied,
            'description': f"{loan.get_purpose_display()} Loan Application",
            'amount': loan.amount,
            'status': loan.get_status_display(),
            'details': {
                'total_owed': loan.total_owed,
                'payment_percentage': loan.payment_percentage if loan.payments_made > 0 else 0,
                'comments': loan.comments,
                'loan_id': loan.id,
                'is_paid': loan.total_owed <= 0  # Mark as paid if total_owed is 0
            }
        })
    
    # Add payments to activities
    for payment in payments:
        # Debug: Print the type and value of created_at
        print(f"payment.created_at type: {type(payment.created_at)}, value: {payment.created_at}")
        
        activities.append({
            'type': 'payment',
            'date': payment.created_at,  # Already a datetime
            'description': f"Payment for Loan #{payment.loan_id}",
            'amount': payment.amount_lsl,
            'status': payment.status,  # Will be 'PAID' due to model
            'details': {
                'amount_usd': payment.amount_usd,
                'recipient_email': payment.recipient_email,
                'batch_id': payment.batch_id,
            }
        })
    
    # Sort activities by date (descending)
    try:
        activities.sort(key=lambda x: x['date'], reverse=True)
    except TypeError as e:
        print(f"Sorting error: {e}")
        # Fallback sorting if types are incompatible
        activities.sort(key=lambda x: x['date'].isoformat() if isinstance(x['date'], (datetime, date)) else str(x['date']), reverse=True)
    
    return render(request, 'history.html', {
        'activities': activities,
        'loans': loans  # For backward compatibility
    })






from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Loan, PaidAccounts
from decimal import Decimal

@login_required
@csrf_exempt
def record_payment(request, loan_id):
    try:
        loan = Loan.objects.get(id=loan_id, user=request.user)
        if request.method == 'POST':
            data = json.loads(request.body)
            on_time = data.get('on_time', False)
            # Example: Record a dummy payment (adjust as needed)
            payment_amount = Decimal('100.00')  # Replace with actual amount
            exchange_rate = Decimal('0.054')
            PaidAccounts.objects.create(
                loan=loan,
                recipient_email=request.user.email,
                amount_lsl=payment_amount,
                amount_usd=payment_amount * exchange_rate,
                exchange_rate=exchange_rate,
                batch_id='manual_' + str(loan_id),
                status='SUCCESS',
                paypal_response={}
            )
            loan.payments_made += 1
            if on_time:
                loan.payments_made_on_time += 1
            interest_factor = Decimal('1') + (loan.interest_rate / Decimal('100'))
            loan.amount -= payment_amount / interest_factor
            loan.save()
            request.user.credit_score = request.user.calculate_credit_score()
            request.user.save()
            return JsonResponse({'success': True})
    except Loan.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Loan not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

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

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Loan, PayoutTransaction, CustomUser
from decimal import Decimal
import requests
import base64
import json
import time
import logging

logger = logging.getLogger(__name__)

# PayPal sandbox accounts
accounts = {
    "tebohomojiishmael@gmail.com": {
        "password": "tebohomojiishmael",
        "clientId": "AYANZYjYvmyPKZ5DEaZx8e3WCWYb2Miuc6h0N6uXScmqgugnElT-87woQjmp0DvSYxfYesH7-Wm3vNez",
        "secret": "EP6wJSVPXgkkCGQpM6jPGFoOUYkA1clW_bGIz9y_bcopMGRk_SpzD15YJ6yTFoGcK4Uj8PFB0aL8s-kL"
    },
    "mojalefajefff@gmail.com": {
        "password": "oneonetwo",
        "clientId": "AdBHcdS80CfNSbEpELYWk3d-lXIW-8Ck1inRb3C1nWDQAQwKzm-x98dwk2kod1HQOsDOVQD99CrvcjLk",
        "secret": "EAE9fWnALbSHsIKtdhTa6u0pAoDGMky8K2WIYQWXy8okRaEhVhjkbqmgpfDobTDIEBIgyCZvKj5qmE7l"
    },
    "mahokoselina8@gmail.com": {
        "password": "mahokoselina8",
        "clientId": "AcKaBsku9YX3q_S1UDvetlskO65oW3y1-ZzQeqiwwMzvAldalyt81w2-ho7_g1WIbsuGbcXBvM0zi3zH",
        "secret": "EGH8qBCJv8DxVdQFpkOP34GZvBqjaf6Hf4FGugnMvbmn8ktUPAhfBuxU-nmxsOvktbvntjoL-jyOKfMO"
    },
}

# PayPal API endpoints
base_url = "https://api.sandbox.paypal.com"
auth_url = f"{base_url}/v1/oauth2/token"
payout_url = f"{base_url}/v1/payments/payouts"

def validate_credentials(email, password):
    """Validate user credentials against hardcoded accounts."""
    return email in accounts and accounts[email]["password"] == password

def get_access_token(client_id, client_secret):
    """Get a fresh access token using provided client_id and client_secret."""
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials'}
    
    try:
        response = requests.post(auth_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        logger.info("Access token obtained successfully.")
        return response.json()['access_token']
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to get access token: {str(e)}")
        if e.response:
            logger.error(f"Response details: {e.response.text}")
            if e.response.status_code == 401:
                logger.error("Invalid client ID or secret. Verify credentials in the 'creditech' app at https://developer.paypal.com/developer/applications/.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Access token request failed: {str(e)}")
        return None

def check_payout_status(batch_id, client_id, client_secret):
    """Check the status of a payout batch."""
    access_token = get_access_token(client_id, client_secret)
    if not access_token:
        return None
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        response = requests.get(f"{payout_url}/{batch_id}", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error checking payout status: {str(e)}")
        if e.response:
            logger.error(f"Response details: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Payout status request failed: {str(e)}")
        return None

def send_payment(sender_email, amount, client_id, client_secret, currency="USD"):
    """Send payment from sender_email to creditech2000@gmail.com."""
    access_token = get_access_token(client_id, client_secret)
    if not access_token:
        return None, None
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    payload = {
        "sender_batch_header": {
            "sender_batch_id": "Payouts_" + str(int(time.time())),
            "email_subject": "You have a payment",
            "email_message": f"You have received a payment from {sender_email}. Thanks for using our service!"
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": currency
                },
                "receiver": "creditech2000@gmail.com",
                "note": "Payment for services",
                "sender_item_id": "item_" + str(int(time.time()))
            }
        ]
    }
    
    try:
        response = requests.post(payout_url, headers=headers, data=json.dumps(payload), timeout=15)
        response.raise_for_status()
        result = response.json()
        batch_id = result['batch_header']['payout_batch_id']
        return result, batch_id
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error sending payment: {str(e)}")
        if e.response:
            logger.error(f"Response details: {e.response.text}")
        return None, None
    except requests.exceptions.RequestException as e:
        logger.error(f"Payment request failed: {str(e)}")
        return None, None
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from .models import Loan, PaidAccounts, CustomUser
from .forms import LoanApplicationForm
from decimal import Decimal
import requests
import base64
import json
import time
import logging
import threading

logger = logging.getLogger(__name__)

# PayPal sandbox accounts
accounts = {
    "tebohomojiishmael@gmail.com": {
        "password": "tebohomojiishmael",
        "clientId": "AYANZYjYvmyPKZ5DEaZx8e3WCWYb2Miuc6h0N6uXScmqgugnElT-87woQjmp0DvSYxfYesH7-Wm3vNez",
        "secret": "EP6wJSVPXgkkCGQpM6jPGFoOUYkA1clW_bGIz9y_bcopMGRk_SpzD15YJ6yTFoGcK4Uj8PFB0aL8s-kL"
    },
    "mojalefajefff@gmail.com": {
        "password": "oneonetwo",
        "clientId": "AdBHcdS80CfNSbEpELYWk3d-lXIW-8Ck1inRb3C1nWDQAQwKzm-x98dwk2kod1HQOsDOVQD99CrvcjLk",
        "secret": "EAE9fWnALbSHsIKtdhTa6u0pAoDGMky8K2WIYQWXy8okRaEhVhjkbqmgpfDobTDIEBIgyCZvKj5qmE7l"
    },
    "mahokoselina8@gmail.com": {
        "password": "mahokoselina8",
        "clientId": "AcKaBsku9YX3q_S1UDvetlskO65oW3y1-ZzQeqiwwMzvAldalyt81w2-ho7_g1WIbsuGbcXBvM0zi3zH",
        "secret": "EGH8qBCJv8DxVdQFpkOP34GZvBqjaf6Hf4FGugnMvbmn8ktUPAhfBuxU-nmxsOvktbvntjoL-jyOKfMO"
    },
}

# PayPal API endpoints
base_url = "https://api.sandbox.paypal.com"
auth_url = f"{base_url}/v1/oauth2/token"
payout_url = f"{base_url}/v1/payments/payouts"

def validate_credentials(email, password):
    """Validate user credentials against hardcoded accounts."""
    return email in accounts and accounts[email]["password"] == password

def get_access_token(client_id, client_secret):
    """Get a fresh access token using provided client_id and client_secret."""
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials'}
    
    try:
        response = requests.post(auth_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        logger.info("Access token obtained successfully.")
        return response.json()['access_token']
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to get access token: {str(e)}")
        if e.response:
            logger.error(f"Response details: {e.response.text}")
            if e.response.status_code == 401:
                logger.error("Invalid client ID or secret. Verify credentials in the 'creditech' app at https://developer.paypal.com/developer/applications/.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Access token request failed: {str(e)}")
        return None

def check_payout_status(batch_id, client_id, client_secret):
    """Check the status of a payout batch."""
    access_token = get_access_token(client_id, client_secret)
    if not access_token:
        return None
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        response = requests.get(f"{payout_url}/{batch_id}", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error checking payout status: {str(e)}")
        if e.response:
            logger.error(f"Response details: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Payout status request failed: {str(e)}")
        return None

def send_payment(sender_email, amount, client_id, client_secret, currency="USD"):
    """Send payment from sender_email to creditech2000@gmail.com."""
    access_token = get_access_token(client_id, client_secret)
    if not access_token:
        return None, None
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    payload = {
        "sender_batch_header": {
            "sender_batch_id": "Payouts_" + str(int(time.time())),
            "email_subject": "You have a payment",
            "email_message": f"You have received a payment from {sender_email}. Thanks for our service!"
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": currency
                },
                "receiver": "creditech2000@gmail.com",
                "note": "Payment for services",
                "sender_item_id": "item_" + str(int(time.time()))
            }
        ]
    }
    
    try:
        response = requests.post(payout_url, headers=headers, data=json.dumps(payload), timeout=15)
        response.raise_for_status()
        result = response.json()
        batch_id = result['batch_header']['payout_batch_id']
        return result, batch_id
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error sending payment: {str(e)}")
        if e.response:
            logger.error(f"Response details: {e.response.text}")
        return None, None
    except requests.exceptions.RequestException as e:
        logger.error(f"Payment request failed: {str(e)}")
        return None, None

@login_required
def dashboard(request):
    """Display user's loan dashboard."""
    loans = Loan.objects.filter(user=request.user).order_by('-application_date')
    total_outstanding = sum(loan.total_owed for loan in loans.filter(status='approved'))
    context = {
        'loans': loans,
        'total_outstanding': total_outstanding,
        'user': request.user,
    }
    return render(request, 'dashboard.html', context)

@login_required
def loan_detail(request, loan_id):
    """Display details of a specific loan."""
    loan = get_object_or_404(Loan, id=loan_id, user=request.user)
    transactions = PaidAccounts.objects.filter(loan=loan)
    context = {
        'loan': loan,
        'transactions': transactions,
    }
    return render(request, 'loan_detail.html', context)

@login_required
def payment(request):
    """Handle payment page rendering and processing."""
    approved_loans = Loan.objects.filter(user=request.user, status='approved')
    if not approved_loans.exists():
        messages.error(request, "No approved loans found.")
        return redirect('home')

    total_outstanding = sum(loan.total_owed for loan in approved_loans)
    minimum_payment_due = total_outstanding * Decimal('0.20')
    exchange_rate = Decimal('0.054')

    def process_automatic_payment(email, client_id, client_secret, payment_amount, delay, payment_label):
        """Helper function to process a scheduled payment after a delay."""
        def task():
            try:
                usd_amount = payment_amount * exchange_rate
                result, batch_id = send_payment(email, usd_amount, client_id, client_secret)
                if result and batch_id:
                    status_result = check_payout_status(batch_id, client_id, client_secret)
                    if status_result and status_result['batch_header']['batch_status'] in ['SUCCESS', 'PENDING']:
                        total_owed_sum = sum(loan.total_owed for loan in approved_loans)
                        for loan in approved_loans:
                            proportion = loan.total_owed / total_owed_sum if total_owed_sum else Decimal('0')
                            loan_payment = payment_amount * proportion
                            PaidAccounts.objects.create(
                                loan=loan,
                                recipient_email=email,
                                amount_lsl=loan_payment,
                                amount_usd=loan_payment * exchange_rate,
                                exchange_rate=exchange_rate,
                                batch_id=batch_id,
                                status=status_result['batch_header']['batch_status'],
                                paypal_response=status_result
                            )
                            loan.payments_made += 1
                            loan.payments_made_on_time += 1
                            interest_factor = Decimal('1') + (loan.interest_rate / Decimal('100'))
                            loan.amount -= loan_payment / interest_factor
                            loan.save()
                        request.user.credit_score = request.user.calculate_credit_score()
                        request.user.save()
                        logger.info(f"Automatic {payment_label} of M{payment_amount:,.2f} processed successfully.")
                    else:
                        logger.error(f"Automatic {payment_label} failed due to invalid payout status.")
                        if status_result and 'items' in status_result:
                            for item in status_result['items']:
                                if item.get('errors'):
                                    if item['errors'].get('name') == 'INSUFFICIENT_FUNDS':
                                        logger.error("Insufficient funds in sender account for automatic payment.")
                                    elif item['errors'].get('name') == 'INVALID_RECIPIENT':
                                        logger.error("Invalid recipient account for automatic payment.")
                else:
                    logger.error(f"Failed to process automatic {payment_label}. Check PayPal credentials or account status.")
            except Exception as e:
                logger.error(f"Unexpected error in automatic {payment_label}: {str(e)}")
        
        threading.Timer(delay, task).start()

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        payment_amount = request.POST.get('paymentAmount')

        if not validate_credentials(email, password):
            messages.error(request, "Invalid email or password.")
            return render(request, 'payment.html', {
                'total_outstanding': total_outstanding,
                'minimum_payment_due': minimum_payment_due,
                'exchange_rate': exchange_rate,
                'user': request.user,
                'request': request,
            })

        client_id = accounts[email]["clientId"]
        client_secret = accounts[email]["secret"]

        try:
            payment_amount = Decimal(payment_amount)
            if payment_amount < minimum_payment_due or payment_amount > total_outstanding:
                messages.error(request, f"Amount must be between M{minimum_payment_due:,.2f} and M{total_outstanding:,.2f}.")
                return render(request, 'payment.html', {
                    'total_outstanding': total_outstanding,
                    'minimum_payment_due': minimum_payment_due,
                    'exchange_rate': exchange_rate,
                    'user': request.user,
                    'request': request,
                })

            usd_amount = payment_amount * exchange_rate
            result, batch_id = send_payment(email, usd_amount, client_id, client_secret)

            if result and batch_id:
                status_result = check_payout_status(batch_id, client_id, client_secret)
                if status_result and status_result['batch_header']['batch_status'] in ['SUCCESS', 'PENDING']:
                    total_owed_sum = sum(loan.total_owed for loan in approved_loans)
                    for loan in approved_loans:
                        proportion = loan.total_owed / total_owed_sum if total_owed_sum else Decimal('0')
                        loan_payment = payment_amount * proportion
                        PaidAccounts.objects.create(
                            loan=loan,
                            recipient_email=email,
                            amount_lsl=loan_payment,
                            amount_usd=loan_payment * exchange_rate,
                            exchange_rate=exchange_rate,
                            batch_id=batch_id,
                            status=status_result['batch_header']['batch_status'],
                            paypal_response=status_result
                        )
                        loan.payments_made += 1
                        loan.payments_made_on_time += 1
                        interest_factor = Decimal('1') + (loan.interest_rate / Decimal('100'))
                        loan.amount -= loan_payment / interest_factor
                        loan.save()
                    request.user.credit_score = request.user.calculate_credit_score()
                    request.user.save()
                    messages.success(request, f"Payment of M{payment_amount:,.2f} processed successfully!")

                    # Schedule automatic payments
                    remaining_balance = sum(loan.total_owed for loan in Loan.objects.filter(user=request.user, status='approved'))
                    if remaining_balance > 0:
                        # First automatic payment: 50% of remaining balance after 30 seconds
                        first_auto_payment = remaining_balance * Decimal('0.50')
                        process_automatic_payment(email, client_id, client_secret, first_auto_payment, 30, "first automatic payment")
                        # Second automatic payment: remaining balance after 90 seconds (1 minute after first auto payment)
                        second_auto_payment = remaining_balance - first_auto_payment
                        if second_auto_payment > 0:
                            process_automatic_payment(email, client_id, client_secret, second_auto_payment, 90, "second automatic payment")

                    return redirect('payment_success')
                else:
                    messages.error(request, "Payment failed due to invalid payout status.")
                    if status_result and 'items' in status_result:
                        for item in status_result['items']:
                            if item.get('errors'):
                                if item['errors'].get('name') == 'INSUFFICIENT_FUNDS':
                                    messages.error(request, "Insufficient funds in sender account. Add funds at https://developer.paypal.com/developer/accounts/.")
                                elif item['errors'].get('name') == 'INVALID_RECIPIENT':
                                    messages.error(request, "Invalid recipient account. Verify creditech2000@gmail.com at https://developer.paypal.com/developer/accounts/.")
            else:
                messages.error(request, "Failed to process payment. Check PayPal credentials or account status.")
        except ValueError as ve:
            logger.error(f"Invalid payment amount: {str(ve)}")
            messages.error(request, "Invalid payment amount format.")
        except AttributeError as ae:
            logger.error(f"Model attribute error: {str(ae)}")
            messages.error(request, f"Model error: {str(ae)}")
        except requests.exceptions.RequestException as re:
            logger.error(f"PayPal API error: {str(re)}")
            messages.error(request, f"PayPal API error: {str(re)}")
        except Exception as e:
            logger.error(f"Unexpected payment processing error: {str(e)}")
            messages.error(request, f"Unexpected error: {str(e)}")

    return render(request, 'payment.html', {
        'total_outstanding': total_outstanding,
        'minimum_payment_due': minimum_payment_due,
        'exchange_rate': exchange_rate,
        'user': request.user,
        'request': request,
    })

@login_required
def payment_success(request):
    """Render payment success page."""
    return render(request, 'payment_success.html', {'message': 'Payment processed successfully!'})

@login_required
def payment_cancel(request):
    """Handle payment cancellation."""
    messages.warning(request, "Payment was cancelled.")
    return redirect('payment')