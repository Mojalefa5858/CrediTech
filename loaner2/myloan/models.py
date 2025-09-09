from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import re

def validate_lesotho_phone(value):
    pattern = r'^\+266[568]\d{7}$'
    if not re.match(pattern, value):
        raise ValidationError(
            'Invalid Lesotho phone number. Must be +266 followed by 8 digits starting with 5, 6, or 8.'
        )

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        # Calculate initial credit score
        user.credit_score = user.calculate_credit_score()
        user.save()
        
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email=email)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    date_of_birth = models.DateField(null=True, blank=True)
    monthly_income = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    phone_number = models.CharField(
        max_length=15,
        unique=False,
        validators=[validate_lesotho_phone],
        help_text="Lesotho format: +266 followed by 8 digits (e.g. +26650123456)"
    )
    


    physical_address = models.CharField(max_length=200, blank=True)
    place_of_work = models.CharField(max_length=100, blank=True)
    national_id_number = models.CharField(max_length=20, unique=False, blank=True)
    id_photo = models.ImageField(upload_to='id_photos/', blank=True)

    payslip = models.FileField(upload_to='payslips/', blank=True, null=True)
    credit_score = models.PositiveIntegerField(default=600)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)



    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name



    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def calculate_credit_score(self):
        """Calculate credit score based on various factors"""
        score = 600  # Base score

        # Government employment bonus
        if "government" in (self.place_of_work or "").lower():
            score += 50

        # Income-based score
        if self.monthly_income > 20000:
            score += 100
        elif self.monthly_income > 10000:
            score += 50
        elif self.monthly_income > 5000:
            score += 25

        # Loan history impact
        active_loans = self.loans.filter(status='approved')  # FIXED HERE
        if active_loans.exists():
            score += 30  # Good to have some credit history

            # Penalty for high debt-to-income ratio
            total_debt = sum(loan.total_owed for loan in active_loans)
            debt_ratio = total_debt / (self.monthly_income * 12) if self.monthly_income > 0 else 0
            if debt_ratio > 0.5:
                score -= 50
            elif debt_ratio > 0.3:
                score -= 25

        return min(850, max(300, score))

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

class Loan(models.Model):
    from django.core.mail import send_mail
from django.conf import settings

class Loan(models.Model):

    def approve(self):
        """Admin approval method with email notification"""
        self.status = 'approved'
        self.date_approved = timezone.now().date()
        if not self.deadline:
            self.deadline = self.date_approved + timedelta(days=30)
        self.comments = 'Approved by admin'
        self.save()
        
        # Send approval email
        subject = "Your Loan Application Has Been Approved"
        message = f"""
Dear {self.user.first_name},

We're pleased to inform you that your loan application for M{self.amount:,.2f} has been approved.

Loan Details:
- Amount: M{self.amount:,.2f}
- Interest Rate: {self.interest_rate}%
- Total Amount Owed: M{self.total_owed:,.2f}
- Repayment Deadline: {self.deadline.strftime('%Y-%m-%d')}
- Admin Comments: {self.comments}

Please ensure you make your payments on time to maintain a good credit score.

Best regards,
The Loan Team
"""
        self.send_notification_email(subject, message)

    def decline(self):
        """Admin decline method with email notification"""
        self.status = 'declined'
        self.comments = 'Declined by admin' if not self.comments else self.comments
        self.save()
        
        # Send decline email
        subject = "Your Loan Application Has Been Declined"
        message = f"""
Dear {self.user.first_name},

We regret to inform you that your loan application for M{self.amount:,.2f} has been declined.

Reason for decline: {self.comments}

If you have any questions, please don't hesitate to contact us.

Best regards,
The Loan Team
"""
        self.send_notification_email(subject, message)

    def send_notification_email(self, subject, message):
        """Helper method to send email notifications"""
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,  # or your specific email
                [self.user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Log the error if email sending fails
            from django.utils.log import log_exception
            log_exception(Exception(f"Failed to send loan notification email to {self.user.email}: {str(e)}"))





    LOAN_STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('declined', 'Declined'),
    ]
    
    LOAN_PURPOSE_CHOICES = [
        ('personal', 'Personal'),
        ('business', 'Business'),
        ('education', 'Education'),
        ('emergency', 'Emergency'),
    ]

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,  # 30% default interest rate
        help_text="Interest rate in percentage"
    )
    deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Repayment deadline date"
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.CharField(max_length=20, choices=LOAN_PURPOSE_CHOICES)
    status = models.CharField(max_length=10, choices=LOAN_STATUS_CHOICES, default='pending')
    comments = models.TextField(blank=True)
    date_applied = models.DateField(auto_now_add=True)
    date_approved = models.DateField(null=True, blank=True)
    payments_made = models.PositiveIntegerField(default=0)
    payments_made_on_time = models.PositiveIntegerField(default=0)

    def approve(self):
        """Admin approval method"""
        self.status = 'approved'
        self.date_approved = timezone.now().date()
        if not self.deadline:
            self.deadline = self.date_approved + timedelta(days=30)
        self.comments = 'Approved by admin'
        self.save()

    def decline(self):
        """Admin decline method"""
        self.status = 'declined'
        self.comments = 'Declined by admin'
        self.save()

    def save(self, *args, **kwargs):
        """Save method - removed all automatic approval/decline logic"""
        # Only set default values for new loans
        if not self.pk:
            self.status = 'pending'  # All new loans start as pending
            self.comments = 'Application submitted'  # Default comment
        
        super().save(*args, **kwargs)

    @property
    def interest(self):
        """Calculate interest amount"""
        return (self.amount * self.interest_rate / 100).quantize(Decimal('0.00'))
    
    @property
    def total_owed(self):
        """Calculate total owed (principal + interest)"""
        return (self.amount + self.interest).quantize(Decimal('0.00'))

    @property
    def payment_percentage(self):
        """Calculate percentage of payments made on time"""
        if self.payments_made == 0:
            return 0
        return (self.payments_made_on_time / self.payments_made) * 100

    def clean(self):
        """Additional validation"""
        if self.amount <= 0:
            raise ValidationError("Loan amount must be greater than zero")
        
        if self.interest_rate <= 0:
            raise ValidationError("Interest rate must be positive")

    def __str__(self):
        return f"{self.get_purpose_display()} Loan - {self.user} ({self.get_status_display()})"

    class Meta:
        ordering = ['-date_applied']
        verbose_name = 'Loan Application'
        verbose_name_plural = 'Loan Applications'



from django.db import models
from django.conf import settings

class PayoutTransaction(models.Model):
    loan = models.OneToOneField('Loan', on_delete=models.PROTECT)
    recipient_email = models.EmailField()
    amount_lsl = models.DecimalField(max_digits=10, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6)
    batch_id = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    paypal_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payout for Loan #{self.loan_id}"

class PayoutTransaction(models.Model):
    loan = models.OneToOneField('Loan', on_delete=models.PROTECT, related_name='payout_transaction')
    recipient_email = models.EmailField()
    amount_lsl = models.DecimalField(max_digits=10, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6)
    batch_id = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    paypal_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payout for Loan #{self.loan_id} - {self.status}"

    class Meta:
        verbose_name = 'Payout Transaction'
        verbose_name_plural = 'Payout Transactions'
        ordering = ['-created_at']