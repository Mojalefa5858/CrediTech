from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from decimal import Decimal
import requests
import base64
import json
import time
from .models import CustomUser, Loan, PayoutTransaction

logger = logging.getLogger(__name__)

# PayPal configuration
PAYPAL_BASE_URL = "https://api.sandbox.paypal.com" if getattr(settings, 'PAYPAL_SANDBOX', True) else "https://api.paypal.com"
PAYPAL_AUTH_URL = f"{PAYPAL_BASE_URL}/v1/oauth2/token"
PAYPAL_PAYOUT_URL = f"{PAYPAL_BASE_URL}/v1/payments/payouts"

# -------------------- Loan Admin --------------------
@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    def admin_actions(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<div style="display: flex; gap: 5px;">'
                '<a href="{}" class="button" style="'
                'padding: 5px 10px;'
                'background: #4CAF50;'
                'color: white;'
                'border-radius: 4px;'
                'text-decoration: none;'
                'font-weight: bold;'
                'border: none;'
                'cursor: pointer;'
                'transition: all 0.3s;'
                'box-shadow: 0 2px 5px rgba(0,0,0,0.2);'
                '">✓ Approve</a>'
                '<a href="{}" class="button" style="'
                'padding: 5px 10px;'
                'background: #f44336;'
                'color: white;'
                'border-radius: 4px;'
                'text-decoration: none;'
                'font-weight: bold;'
                'border: none;'
                'cursor: pointer;'
                'transition: all 0.3s;'
                'box-shadow: 0 2px 5px rgba(0,0,0,0.2);'
                '">✗ Decline</a>'
                '</div>',
                f"{obj.id}/approve/",
                f"{obj.id}/decline/"
            )
        return format_html(
            '<span style="color: #666; font-style: italic;">Processed</span>'
        )
    admin_actions.short_description = 'Actions'

    list_display = (
        'user_with_id_photo',
        'user_email',
        'formatted_amount',
        'purpose',
        'status',
        'date_applied',
        'admin_actions',
    )
    list_filter = ('status', 'purpose', 'date_applied')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    actions = ['approve_selected', 'decline_selected']
    readonly_fields = (
        'date_applied',
        'date_approved',
        'formatted_amount',
        'formatted_interest',
        'formatted_total',
        'user_info',
        'id_photo_preview',
        'payslip_preview',
    )

    fieldsets = (
        ('Loan Information', {
            'fields': ('user', 'amount', 'purpose', 'status', 'interest_rate')
        }),
        ('Dates', {
            'fields': ('date_applied', 'date_approved', 'deadline')
        }),
        ('Financial Details', {
            'fields': ('formatted_amount', 'formatted_interest', 'formatted_total')
        }),
        ('User Information', {
            'fields': ('user_info', 'id_photo_preview', 'payslip_preview')
        }),
    )

    def user_with_id_photo(self, obj):
        return format_html(
            '<div style="display:flex;align-items:center;">'
            '<img src="{}" style="height:30px;width:30px;border-radius:50%;margin-right:10px;"/>'
            '{} {}'
            '</div>',
            obj.user.id_photo.url if obj.user.id_photo else '/static/default.png',
            obj.user.first_name,
            obj.user.last_name
        )
    user_with_id_photo.short_description = 'User'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def formatted_amount(self, obj):
        return f"M{obj.amount:,.2f}"
    formatted_amount.short_description = 'Amount'

    def formatted_interest(self, obj):
        interest = obj.amount * obj.interest_rate / 100
        return f"M{interest:,.2f} ({obj.interest_rate}%)"
    formatted_interest.short_description = 'Interest'

    def formatted_total(self, obj):
        total = obj.amount + (obj.amount * obj.interest_rate / 100)
        return f"M{total:,.2f}"
    formatted_total.short_description = 'Total'

    def user_info(self, obj):
        return format_html(
            '<strong>Name:</strong> {} {}<br>'
            '<strong>Email:</strong> {}<br>'
            '<strong>Income:</strong> M{:,.2f}<br>'
            '<strong>Work:</strong> {}',
            obj.user.first_name,
            obj.user.last_name,
            obj.user.email,
            obj.user.monthly_income,
            obj.user.place_of_work
        )
    user_info.short_description = 'User Details'

    def id_photo_preview(self, obj):
        if obj.user.id_photo:
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:100%;border:1px solid #ddd;"/>',
                obj.user.id_photo.url
            )
        return "No ID photo uploaded"
    id_photo_preview.short_description = 'ID Photo'

    def payslip_preview(self, obj):
        if obj.user.payslip:
            if obj.user.payslip.name.lower().endswith('.pdf'):
                return format_html(
                    '''
                    <div style="border:1px solid #ddd;padding:10px;border-radius:5px;margin-bottom:10px;">
                        <a href="{}" target="_blank" style="display:block;margin-bottom:10px;">
                            <i class="fas fa-file-pdf fa-2x" style="color:#e74c3c;"></i>
                            <div>View PDF</div>
                        </a>
                        <a href="{}" download class="button" style="padding:5px 10px;background:#4CAF50;color:white;text-decoration:none;border-radius:4px;">
                            <i class="fas fa-download"></i> Download
                        </a>
                    </div>
                    ''',
                    obj.user.payslip.url,
                    obj.user.payslip.url
                )
            else:
                return format_html(
                    '''
                    <div style="border:1px solid #ddd;padding:10px;border-radius:5px;margin-bottom:10px;">
                        <a href="{}" target="_blank" style="display:block;margin-bottom:10px;">
                            <img src="{}" style="max-height:200px;max-width:100%;"/>
                        </a>
                        <a href="{}" download class="button" style="padding:5px 10px;background:#4CAF50;color:white;text-decoration:none;border-radius:4px;">
                            <i class="fas fa-download"></i> Download
                        </a>
                    </div>
                    ''',
                    obj.user.payslip.url,
                    obj.user.payslip.url,
                    obj.user.payslip.url
                )
        return "No payslip uploaded"
    payslip_preview.short_description = 'Payslip'
    payslip_preview.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:pk>/approve/', self.admin_site.admin_view(self.approve_loan)),
            path('<path:pk>/decline/', self.admin_site.admin_view(self.decline_loan)),
        ]
        return custom_urls + urls

    def _get_paypal_access_token(self):
        """Get PayPal access token using client credentials"""
        try:
            auth_string = f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_SECRET}"
            auth_bytes = auth_string.encode('ascii')
            auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_base64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {'grant_type': 'client_credentials'}
            
            response = requests.post(PAYPAL_AUTH_URL, headers=headers, data=data)
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            logger.error(f"Failed to get PayPal access token: {str(e)}")
            return None

    def _send_paypal_payment(self, loan, amount_usd):
        """Send payment via PayPal Payouts API"""
        try:
            access_token = self._get_paypal_access_token()
            if not access_token:
                return None
                
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            payload = {
                "sender_batch_header": {
                    "sender_batch_id": f"LOAN_{loan.id}_{int(time.time())}",
                    "email_subject": "Your loan has been approved",
                    "email_message": f"Your loan of M{loan.amount:,.2f} (${amount_usd:,.2f}) has been approved and disbursed."
                },
                "items": [
                    {
                        "recipient_type": "EMAIL",
                        "amount": {
                            "value": f"{amount_usd:.2f}",
                            "currency": "USD"
                        },
                        "receiver": loan.user.email,
                        "note": f"Loan #{loan.id} payout",
                        "sender_item_id": f"loan_{loan.id}"
                    }
                ]
            }
            
            response = requests.post(
                PAYPAL_PAYOUT_URL,
                headers=headers,
                data=json.dumps(payload)
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as err:
            logger.error(f"PayPal API error: {err}\nResponse: {err.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to send PayPal payment: {str(e)}")
            return None

    def approve_loan(self, request, pk):
        loan = self.get_object(request, pk)
        if loan.status != 'pending':
            self.message_user(request, 'Only pending loans can be approved', messages.ERROR)
            return HttpResponseRedirect('../..')
        
        # Convert LSL to USD (using approximate exchange rate)
        exchange_rate = Decimal('0.055')  # 1 LSL = 0.055 USD (adjust as needed)
        amount_usd = (loan.amount * exchange_rate).quantize(Decimal('0.01'))
        
        # Attempt PayPal payment
        payout_result = self._send_paypal_payment(loan, amount_usd)
        
        if not payout_result:
            self.message_user(request, 'Loan approval failed: PayPal payment could not be processed', messages.ERROR)
            return HttpResponseRedirect('../..')
        
        # Update loan status
        loan.status = 'approved'
        loan.date_approved = timezone.now().date()
        loan.deadline = loan.date_approved + timedelta(days=30)
        loan.save()
        
        # Create payout transaction record
        PayoutTransaction.objects.create(
            loan=loan,
            recipient_email=loan.user.email,
            amount_lsl=loan.amount,
            amount_usd=amount_usd,
            exchange_rate=exchange_rate,
            batch_id=payout_result['batch_header']['payout_batch_id'],
           # status=payout_result['batch_header']['batch_status'],
            paypal_response=payout_result
        )
        
        # Send approval email
        self._send_smtp_email(
            loan.user.email,
            f"Loan #{loan.id} Approved",
            self._generate_approval_email_body(loan, amount_usd, exchange_rate)
        )
        
        self.message_user(request, 'Loan approved, payment sent, and notification emailed')
        return HttpResponseRedirect('../..')

    def decline_loan(self, request, pk):
        loan = self.get_object(request, pk)
        if loan.status != 'pending':
            self.message_user(request, 'Only pending loans can be declined', messages.ERROR)
            return HttpResponseRedirect('../..')
        
        loan.status = 'declined'
        loan.save()
        
        self._send_smtp_email(
            loan.user.email,
            f"Loan #{loan.id} Declined",
            self._generate_decline_email_body(loan)
        )
        
        self.message_user(request, 'Loan declined and notification sent')
        return HttpResponseRedirect('../..')

    def approve_selected(self, request, queryset):
        success_count = 0
        exchange_rate = Decimal('0.055')  # 1 LSL = 0.055 USD
        
        for loan in queryset.filter(status='pending'):
            amount_usd = (loan.amount * exchange_rate).quantize(Decimal('0.01'))
            payout_result = self._send_paypal_payment(loan, amount_usd)
            
            if not payout_result:
                continue
                
            loan.status = 'approved'
            loan.date_approved = timezone.now().date()
            loan.deadline = loan.date_approved + timedelta(days=30)
            loan.save()
            
            PayoutTransaction.objects.create(
                loan=loan,
                recipient_email=loan.user.email,
                amount_lsl=loan.amount,
                amount_usd=amount_usd,
                exchange_rate=exchange_rate,
                batch_id=payout_result['batch_header']['payout_batch_id'],
                status=payout_result['batch_header']['batch_status'],
                paypal_response=payout_result
            )
            
            self._send_smtp_email(
                loan.user.email,
                f"Loan #{loan.id} Approved",
                self._generate_approval_email_body(loan, amount_usd, exchange_rate)
            )
            success_count += 1
        
        self.message_user(request, f"{success_count} loans approved, payments sent, and notifications emailed")

    def decline_selected(self, request, queryset):
        for loan in queryset.filter(status='pending'):
            loan.status = 'declined'
            loan.save()
            
            self._send_smtp_email(
                loan.user.email,
                f"Loan #{loan.id} Declined",
                self._generate_decline_email_body(loan)
            )
        
        self.message_user(request, f"{queryset.count()} loans declined and notifications sent")

    def _generate_approval_email_body(self, loan, amount_usd, exchange_rate):
        return f"""Dear {loan.user.first_name},

Your loan application has been APPROVED and the funds have been sent to your account.

Loan Details:
- Amount: M{loan.amount:,.2f} (${amount_usd:,.2f} USD)
- Exchange Rate: 1 LSL = {exchange_rate:.3f} USD
- Purpose: {loan.get_purpose_display()}
- Interest Rate: {loan.interest_rate}%
- Total Repayment: M{loan.amount + (loan.amount * loan.interest_rate / 100):,.2f}
- Due Date: {loan.deadline.strftime('%Y-%m-%d')}

The funds should appear in your account shortly. Please check your PayPal account.

Thank you for choosing our services.

Best regards,
Loan Administration Team
"""

    def _generate_decline_email_body(self, loan):
        return f"""Dear {loan.user.first_name},

We regret to inform you that your loan application has been DECLINED.

Application Details:
- Amount Requested: M{loan.amount:,.2f}
- Purpose: {loan.get_purpose_display()}
- Application Date: {loan.date_applied.strftime('%Y-%m-%d')}

For more information, please contact our customer service.

Best regards,
Loan Administration Team
"""

    def _send_smtp_email(self, recipient, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_HOST_USER
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                server.starttls()
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                server.send_message(msg)
                
            logger.info(f"Email sent to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False

# -------------------- Payout Transaction Admin --------------------
@admin.register(PayoutTransaction)
class PayoutTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'loan',
        'recipient_email',
        'amount_lsl',
        'amount_usd',
        'exchange_rate',
        'status',
        'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('loan__id', 'recipient_email', 'batch_id')
    readonly_fields = ('paypal_response_prettified',)

    def paypal_response_prettified(self, obj):
        return format_html(
            '<pre style="white-space: pre-wrap; word-wrap: break-word; background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>',
            json.dumps(obj.paypal_response, indent=2)
        )
    paypal_response_prettified.short_description = 'PayPal Response'

# -------------------- Loan Inline for UserAdmin --------------------
class LoanInline(admin.TabularInline):
    model = Loan
    extra = 0
    readonly_fields = (
        'formatted_amount',
        'status',
        'purpose',
        'formatted_interest',
        'formatted_total',
        'date_applied',
        'admin_actions',
    )
    fields = (
        'formatted_amount',
        'purpose',
        'status',
        'date_applied',
        'deadline',
        'formatted_interest',
        'formatted_total',
        'admin_actions',
    )

    def formatted_amount(self, obj):
        return f"M{obj.amount:.2f}" if obj.amount else "N/A"
    formatted_amount.short_description = 'Amount'

    def formatted_interest(self, obj):
        if obj.amount and obj.interest_rate:
            interest = (obj.amount * obj.interest_rate / Decimal('100')).quantize(Decimal('0.00'))
            return f"M{interest:.2f} (Rate: {obj.interest_rate}%)"
        return "N/A"
    formatted_interest.short_description = 'Interest'

    def formatted_total(self, obj):
        if obj.amount and obj.interest_rate:
            total = obj.amount + (obj.amount * obj.interest_rate / Decimal('100')).quantize(Decimal('0.00'))
            return f"M{total:.2f}"
        return "N/A"
    formatted_total.short_description = 'Total Owed'

    def admin_actions(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a class="button" href="../../loan/{}/approve/">Approve</a>&nbsp;'
                '<a class="button" href="../../loan/{}/decline/">Decline</a>',
                obj.id, obj.id
            )
        return "No action needed"
    admin_actions.short_description = 'Actions'

# -------------------- Custom User Admin --------------------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    inlines = [LoanInline]
    list_display = (
        'email',
        'first_name',
        'last_name',
        'monthly_income_display',
        'credit_score_display',
        'is_staff',
        'id_photo_preview',
        'payslip_status',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'national_id_number', 'phone_number')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions',)

    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal Information', {
            'fields': (
                'first_name',
                'last_name',
                'date_of_birth',
                'phone_number',
                'physical_address',
            )
        }),
        ('Employment Information', {
            'fields': (
                'place_of_work',
                'monthly_income',
            )
        }),
        ('Identification', {
            'fields': (
                'national_id_number',
                'id_photo',
                'id_photo_preview',
                'payslip',
                'payslip_preview',
            )
        }),
        ('Financial Information', {
            'fields': (
                'credit_score',
            ),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': (
                'last_login',
                'date_joined',
            ),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'password1',
                'password2',
                'first_name',
                'last_name',
                'date_of_birth',
                'phone_number',
                'monthly_income',
                'place_of_work',
                'physical_address',
                'national_id_number',
                'id_photo',
                'payslip',
            ),
        }),
    )

    def monthly_income_display(self, obj):
        return f"M{obj.monthly_income:,.2f}" if obj.monthly_income else "N/A"
    monthly_income_display.short_description = 'Monthly Income'

    def credit_score_display(self, obj):
        return f"{obj.credit_score} pts"
    credit_score_display.short_description = 'Credit Score'

    def id_photo_preview(self, obj):
        if obj.id_photo:
            return format_html(
                '''
                <div style="border:1px solid #ddd;padding:10px;border-radius:5px;margin-bottom:10px;">
                    <a href="{}" target="_blank" style="display:block;margin-bottom:10px;">
                        <img src="{}" style="max-height:200px;max-width:100%;"/>
                    </a>
                    <a href="{}" download class="button" style="padding:5px 10px;background:#4CAF50;color:white;text-decoration:none;border-radius:4px;">
                        <i class="fas fa-download"></i> Download
                    </a>
                </div>
                ''',
                obj.id_photo.url,
                obj.id_photo.url,
                obj.id_photo.url
            )
        return "No ID photo uploaded"
    id_photo_preview.short_description = 'ID Photo'
    id_photo_preview.allow_tags = True

    def payslip_preview(self, obj):
        if obj.payslip:
            if obj.payslip.name.lower().endswith('.pdf'):
                return format_html(
                    '''
                    <div style="border:1px solid #ddd;padding:10px;border-radius:5px;margin-bottom:10px;">
                        <a href="{}" target="_blank" style="display:block;margin-bottom:10px;">
                            <i class="fas fa-file-pdf fa-2x" style="color:#e74c3c;"></i>
                            <div>View PDF</div>
                        </a>
                        <a href="{}" download class="button" style="padding:5px 10px;background:#4CAF50;color:white;text-decoration:none;border-radius:4px;">
                            <i class="fas fa-download"></i> Download
                        </a>
                    </div>
                    ''',
                    obj.payslip.url,
                    obj.payslip.url
                )
            else:
                return format_html(
                    '''
                    <div style="border:1px solid #ddd;padding:10px;border-radius:5px;margin-bottom:10px;">
                        <a href="{}" target="_blank" style="display:block;margin-bottom:10px;">
                            <img src="{}" style="max-height:200px;max-width:100%;"/>
                        </a>
                        <a href="{}" download class="button" style="padding:5px 10px;background:#4CAF50;color:white;text-decoration:none;border-radius:4px;">
                            <i class="fas fa-download"></i> Download
                        </a>
                    </div>
                    ''',
                    obj.payslip.url,
                    obj.payslip.url,
                    obj.payslip.url
                )
        return "No payslip uploaded"
    payslip_preview.short_description = 'Payslip'
    payslip_preview.allow_tags = True

    def payslip_status(self, obj):
        if obj.payslip:
            return format_html(
                '<span style="color: #4CAF50;"><i class="fas fa-check-circle"></i> Uploaded</span>'
            )
        return format_html(
            '<span style="color: #f44336;"><i class="fas fa-times-circle"></i> Missing</span>'
        )
    payslip_status.short_description = 'Payslip Status'

    readonly_fields = (
        'id_photo_preview',
        'payslip_preview',
        'credit_score',
        'last_login',
        'date_joined',
    )

    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
                'css/admin_custom.css',
            )
        }
        
from django.contrib import admin
from .models import CustomUser, Loan, PaidAccounts, PayoutTransaction, CentralBankOfLesotho
        
@admin.register(PaidAccounts)
class PaidAccountsAdmin(admin.ModelAdmin):
    list_display = ('loan', 'recipient_email', 'amount_lsl', 'amount_usd', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('recipient_email', 'batch_id', 'loan__id')
    readonly_fields = ('created_at', 'paypal_response')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def get_queryset(self, request):
        # Optimize query by selecting related loan data
        return super().get_queryset(request).select_related('loan')
        
from django.contrib import admin
from .models import CentralBankOfLesotho
from django.utils import timezone
from django.db.models import Case, When, Value, BooleanField, Q
from django.utils.html import format_html

@admin.register(CentralBankOfLesotho)
class CentralBankOfLesothoAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'national_id',
        'formatted_loan_amount',
        'date_issued',
        'due_date',
        'status',
        'overdue_status',
    )
    list_filter = (
        'status',
        ('date_issued', admin.DateFieldListFilter),
        ('due_date', admin.DateFieldListFilter),
    )
    search_fields = (
        'first_name',
        'last_name',
        'national_id',
    )
    readonly_fields = (
        'last_updated',
        'overdue_status',
        'days_remaining',
    )
    actions = [
        'mark_as_paid',
        'mark_as_defaulted',
        'send_reminder_notifications',
    ]
    date_hierarchy = 'date_issued'
    list_per_page = 50

    fieldsets = (
        ('Debtor Information', {
            'fields': (
                'first_name',
                'last_name',
                'national_id',
            )
        }),
        ('Loan Details', {
            'fields': (
                'loan_amount',
                'date_issued',
                'due_date',
                'status',
            )
        }),
        ('Status Information', {
            'fields': (
                'last_updated',
                'overdue_status',
                'days_remaining',
            ),
            'classes': ('collapse',)
        }),
    )

    def formatted_loan_amount(self, obj):
        return f"M{obj.loan_amount:,.2f}"
    formatted_loan_amount.short_description = 'Loan Amount'
    formatted_loan_amount.admin_order_field = 'loan_amount'

    def overdue_status(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color: red; font-weight: bold;">OVERDUE</span>'
            )
        return format_html(
            '<span style="color: green;">Current</span>'
        )
    overdue_status.short_description = 'Payment Status'

    def days_remaining(self, obj):
        if obj.status != 'active' or not obj.due_date:
            return "N/A"
        
        remaining = (obj.due_date - timezone.now().date()).days
        if remaining < 0:
            return f"{abs(remaining)} days overdue"
        return f"{remaining} days remaining"
    days_remaining.short_description = 'Days Remaining'

    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='paid')
        self.message_user(
            request,
            f"Successfully marked {updated} loan(s) as paid",
            messages.SUCCESS
        )
    mark_as_paid.short_description = "Mark selected loans as paid"

    def mark_as_defaulted(self, request, queryset):
        updated = queryset.update(status='defaulted')
        self.message_user(
            request,
            f"Successfully marked {updated} loan(s) as defaulted",
            messages.SUCCESS
        )
    mark_as_defaulted.short_description = "Mark selected loans as defaulted"

    def send_reminder_notifications(self, request, queryset):
        count = 0
        for loan in queryset.filter(status='active'):
            count += 1
        
        self.message_user(
            request,
            f"Reminder notifications sent for {count} active loans",
            messages.SUCCESS
        )
    send_reminder_notifications.short_description = "Send reminder notifications"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            is_overdue=Case(
                When(
                    Q(status='active') & Q(due_date__lt=timezone.now().date()),
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            )
        )

    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }