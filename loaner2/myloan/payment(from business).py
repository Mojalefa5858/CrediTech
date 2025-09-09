import requests
import base64
import json

# PayPal Sandbox API credentials
business_client_id = "AXI29ZzOA8LLHtCwDt6TmXHB3Y4GucxrzvBbzwKx8y1wyHCV4iBLqAWaWOGPZq29Hs8dP_9XHdWdF8KD"
business_secret = "EFVhURPj4u8fcaFUZ6LA4nL5ZZaa6u1CvOFBltmpD6HH-93LmhWmTtxYi2GwvGVa2jGkTjYHFxlIo0C5"

# Account details
business_email = "creditech2000@gmail.com"
personal_email = "mojalefajefff@gmail.com"

# PayPal API endpoints
base_url = "https://api.sandbox.paypal.com"
auth_url = f"{base_url}/v1/oauth2/token"
payout_url = f"{base_url}/v1/payments/payouts"

# Get access token
def get_access_token():
    auth_string = f"{business_client_id}:{business_secret}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials'}
    
    response = requests.post(auth_url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()['access_token']

# Send payment from business to personal account
def send_payment(amount, currency="USD"):
    access_token = get_access_token()
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    payload = {
        "sender_batch_header": {
            "sender_batch_id": "Payouts_" + str(int(time.time())),
            "email_subject": "You have a payment",
            "email_message": "You have received a payment. Thanks for using our service!"
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {
                    "value": str(amount),
                    "currency": currency
                },
                "receiver": personal_email,
                "note": "Payment for services",
                "sender_item_id": "item_" + str(int(time.time()))
            }
        ]
    }
    
    response = requests.post(payout_url, headers=headers, data=json.dumps(payload))
    
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"Error: {err}")
        print(f"Response: {response.text}")
        return None

# Example usage
if __name__ == "__main__":
    import time
    
    print("Initiating PayPal Sandbox transfer...")
    print(f"From business account: {business_email}")
    print(f"To personal account: {personal_email}")
    
    amount = float(input("Enter amount to transfer (e.g., 10.50): "))
    
    result = send_payment(amount)
    
    if result:
        print("\nTransfer successful!")
        print("Transaction details:")
        print(f"Batch ID: {result['batch_header']['payout_batch_id']}")
        print(f"Status: {result['batch_header']['batch_status']}")
        print(f"Amount: {amount} USD")
    else:
        print("\nTransfer failed. Check error messages above.")