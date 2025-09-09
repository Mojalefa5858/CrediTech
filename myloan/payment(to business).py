import requests
import base64
import json
import time

# Account details for multiple senders
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
        print("Access token obtained successfully.")
        return response.json()['access_token']
    except requests.exceptions.HTTPError as e:
        print(f"Failed to get access token: {str(e)}")
        if e.response:
            print(f"Response details: {e.response.text}")
            if e.response.status_code == 401:
                print("Error: Invalid client ID or secret. Verify credentials in the 'creditech' app at https://developer.paypal.com/developer/applications/.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Access token request failed: {str(e)}")
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
        print(f"Error checking payout status: {str(e)}")
        if e.response:
            print(f"Response details: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Payout status request failed: {str(e)}")
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
        print(f"Error sending payment: {str(e)}")
        if e.response:
            print(f"Response details: {e.response.text}")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"Payment request failed: {str(e)}")
        return None, None

def main():
    print("Initiating PayPal Sandbox transfer...")
    print("Transfers will be sent to: creditech2000@gmail.com")
    print("Available sender accounts:", ", ".join(accounts.keys()))
    
    while True:
        email = input("Enter your email (or 'exit' to quit): ").strip()
        if email.lower() == 'exit':
            print("Exiting...")
            return
        
        password = input("Enter your password: ").strip()
        
        if not validate_credentials(email, password):
            print("Error: Invalid email or password. Please try again.")
            continue
        
        print(f"Authenticated as: {email}")
        
        # Get client_id and client_secret based on entered email
        client_id = accounts[email]["clientId"]
        client_secret = accounts[email]["secret"]
        
        try:
            amount = float(input("Enter amount to transfer (e.g., 10.50): "))
            if amount <= 0:
                print("Error: Amount must be positive. Please try again.")
                continue
            
            result, batch_id = send_payment(email, amount, client_id, client_secret)
            
            if result:
                print("\nTransfer initiated!")
                print("Transaction details:")
                print(f"Batch ID: {result['batch_header']['payout_batch_id']}")
                print(f"Status: {result['batch_header']['batch_status']}")
                print(f"Amount: {amount:.2f} USD")
                if 'items' in result and result['items']:
                    payout_item_id = result['items'][0].get('payout_item_id')
                    if payout_item_id:
                        print(f"Payout Item ID (for reversal): {payout_item_id}")
                    else:
                        print("Warning: Could not retrieve Payout Item ID for reversal")
                
                # Check payout status
                print("\nChecking payout status...")
                status_result = check_payout_status(batch_id, client_id, client_secret)
                if status_result:
                    print("Payout status details:")
                    print(f"Batch ID: {status_result['batch_header']['payout_batch_id']}")
                    print(f"Status: {status_result['batch_header']['batch_status']}")
                    if 'items' in status_result and status_result['items']:
                        for item in status_result['items']:
                            print(f"Item Status: {item.get('transaction_status')}")
                            if item.get('errors'):
                                print(f"Item Errors: {item['errors']}")
                                if item['errors'].get('name') == 'INSUFFICIENT_FUNDS':
                                    print("Solution: Add funds to the sender account at https://developer.paypal.com/developer/accounts/.")
                                elif item['errors'].get('name') == 'INVALID_RECIPIENT':
                                    print("Solution: Verify the recipient account (creditech2000@gmail.com) at https://developer.paypal.com/developer/accounts/.")
                else:
                    print("Failed to retrieve payout status. Check error messages above.")
                
                # Ask if user wants to send another payment
                retry = input("\nWould you like to send another payment? (yes/no): ").strip().lower()
                if retry != 'yes':
                    print("Exiting...")
                    return
            else:
                print("\nTransfer failed. Check error messages above for details.")
                retry = input("\nWould you like to try again? (yes/no): ").strip().lower()
                if retry != 'yes':
                    print("Exiting...")
                    return
                
        except ValueError:
            print("Error: Invalid amount. Please enter a number.")
            retry = input("\nWould you like to try again? (yes/no): ").strip().lower()
            if retry != 'yes':
                print("Exiting...")
                return
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            retry = input("\nWould you like to try again? (yes/no): ").strip().lower()
            if retry != 'yes':
                print("Exiting...")
                return

if __name__ == "__main__":
    main()