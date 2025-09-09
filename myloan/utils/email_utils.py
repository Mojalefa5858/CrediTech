# utils/email_utils.py

import dns.resolver
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Your existing DNS resolvers
DNS_RESOLVERS = [
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1",
    "208.67.222.222", "208.67.220.220",
    "192.168.121.130", "192.168.175.42", "192.168.82.183"
]

def validate_email_domain(email):
    """Validate the email domain using DNS checks"""
    try:
        local_part, domain = email.split('@')
        domain = domain.lower()
        
        # Check MX records
        if not check_dns_records(domain, 'MX'):
            raise ValidationError(f"No MX records found for {domain}")
            
        # Check if domain resolves to an IP
        if not (check_dns_records(domain, 'A') or check_dns_records(domain, 'AAAA')):
            raise ValidationError(f"Domain {domain} doesn't resolve to an IP address")
            
        return True
    except Exception as e:
        logger.error(f"Email domain validation failed: {str(e)}")
        raise ValidationError(f"Email validation error: {str(e)}")

def check_dns_records(domain, record_type):
    """Check DNS records with multiple resolvers"""
    for resolver_ip in DNS_RESOLVERS:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [resolver_ip]
            resolver.timeout = 2
            resolver.lifetime = 2
            answers = resolver.resolve(domain, record_type)
            if answers:
                return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
            continue
    return False

def send_loan_confirmation_email(user, loan):
    """Send loan confirmation email with robust error handling"""
    try:
        # Validate recipient email first
        validate_email_domain(user.email)
        
        subject = 'Loan Application Received'
        message = f"""
        Hello {user.first_name},
        
        Your loan application for M{loan.amount} has been received.
        
        Details:
        - Loan Amount: M{loan.amount}
        - Purpose: {loan.get_purpose_display()}
        - Status: Pending Review
        
        We'll contact you once your application is processed.
        
        Thank you,
        CrediTech Team
        """
        
        email_sent = send_mail(
            subject,
            message.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
        
        if email_sent:
            logger.info(f"Successfully sent loan confirmation to {user.email}")
            return True
        else:
            logger.warning(f"Email send returned 0 for {user.email}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send email to {user.email}: {str(e)}", exc_info=True)
        return False