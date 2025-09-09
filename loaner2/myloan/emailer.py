import smtplib
from django.conf import settings
from email.message import EmailMessage

def send_loan_email(request, loan):
    sender_email = 'mojalefajefff@gmail.com'
    receiver_email = request.user.email  # Send to the registered user
    subject = 'Loan Application Received'
    
    # Personalized message with user's name and loan details
    message = f"""
    Dear {request.user.first_name} {request.user.last_name},
    
    Thank you for your loan application with us. Here are your application details:
    
    - Loan Amount: M{loan.amount}
    - Purpose: {loan.get_purpose_display()}
    - Interest Rate: {loan.interest_rate}%
    - Total Amount Owed: M{loan.total_owed}
    - Application Status: {loan.get_status_display()}
    
    Your application is currently being reviewed. We'll notify you once a decision has been made.
    
    Best regards,
    The Loan Team
    """
    
    try:
        # Create the email message
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email
        
        # Connect to Gmail's SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, settings.EMAIL_APP_PASSWORD)  # Better to use settings
            server.send_message(msg)
            
        print("✅ Email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
    
if __name__ == "__main__":
    send_loan_email()
    