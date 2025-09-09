import requests
import base64
import time
from datetime import datetime, timedelta

# Sandbox API credentials
CLIENT_ID = "AXI29ZzOA8LLHtCwDt6TmXHB3Y4GucxrzvBbzwKx8y1wyHCV4iBLqAWaWOGPZq29Hs8dP_9XHdWdF8KD"
CLIENT_SECRET = "EFVhURPj4u8fcaFUZ6LA4nL5ZZaa6u1CvOFBltmpD6HH-93LmhWmTtxYi2GwvGVa2jGkTjYHFxlIo0C5"

# Your sandbox business account email
BUSINESS_EMAIL = "creditech2000@gmail.com"

def get_access_token():
    """Get OAuth2 access token"""
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    response = requests.post(
        'https://api.sandbox.paypal.com/v1/oauth2/token',
        headers=headers,
        data=data
    )
    return response.json()['access_token']

def get_recent_payments():
    """Get recent payments to the business account"""
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Get payments from last 24 hours
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    params = {
        'count': 20,
        'sort_by': 'create_time',
        'sort_order': 'desc'
    }
    
    response = requests.get(
        'https://api.sandbox.paypal.com/v1/payments/payment',
        headers=headers,
        params=params
    )
    
    if response.status_code == 200:
        payments = []
        for payment in response.json().get('payments', []):
            # Filter for completed payments to our business account
            if (payment.get('state') == 'approved' and 
                payment.get('transactions', [{}])[0].get('payee', {}).get('email') == BUSINESS_EMAIL):
                payments.append(payment)
        return payments
    else:
        print(f"Error fetching payments: {response.text}")
        return []

def monitor_payments():
    """Monitor for new payments to the business account"""
    print(f"Monitoring payments for business account: {BUSINESS_EMAIL}")
    print("Press Ctrl+C to stop monitoring...")
    print("-" * 50)
    
    seen_payments = set()
    
    try:
        while True:
            payments = get_recent_payments()
            
            for payment in payments:
                payment_id = payment.get('id')
                payer_email = payment.get('payer', {}).get('payer_info', {}).get('email')
                amount = payment.get('transactions', [{}])[0].get('amount', {}).get('total')
                currency = payment.get('transactions', [{}])[0].get('amount', {}).get('currency')
                
                if payment_id and payment_id not in seen_payments:
                    seen_payments.add(payment_id)
                    print(f"\nNew payment detected!")
                    print(f"Payer Email: {payer_email}")
                    print(f"Amount: {amount} {currency}")
                    print(f"Payment ID: {payment_id}")
                    print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("-" * 50)
            
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    monitor_payments()