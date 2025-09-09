import requests
import time
from datetime import datetime, timedelta

# === PayPal Sandbox Credentials ===
CLIENT_ID = "AXI29ZzOA8LLHtCwDt6TmXHB3Y4GucxrzvBbzwKx8y1wyHCV4iBLqAWaWOGPZq29Hs8dP_9XHdWdF8KD"
CLIENT_SECRET = "EFVhURPj4u8fcaFUZ6LA4nL5ZZaa6u1CvOFBltmpD6HH-93LmhWmTtxYi2GwvGVa2jGkTjYHFxlIo0C5"

# === Get Access Token ===
def get_access_token():
    url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    headers = {"Accept": "application/json"}
    data = {"grant_type": "client_credentials"}
    r = requests.post(url, headers=headers, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    r.raise_for_status()
    return r.json()["access_token"]

# === Poll for Transactions ===
def check_payments(access_token, start_time):
    url = "https://api-m.sandbox.paypal.com/v1/reporting/transactions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    now = datetime.utcnow().isoformat() + "Z"
    params = {
        "start_date": start_time,
        "end_date": now,
        "fields": "all",
        "page_size": 10
    }

    r = requests.get(url, headers=headers, params=params)
    try:
        r.raise_for_status()
        data = r.json()
        transactions = data.get("transaction_details", [])
        print(f"\n✅ {len(transactions)} new transaction(s) found:")
        for txn in transactions:
            amount = txn['transaction_info']['transaction_amount']
            payer = txn['payer_info'].get('email_address', 'Unknown')
            print(f"- {payer} paid {amount['value']} {amount['currency_code']}")
    except Exception as e:
        print("❌ Error checking transactions:", r.text)

# === Main Polling Loop ===
def main():
    access_token = get_access_token()
    print("🔐 Access token obtained.")
    
    # Look back 10 minutes from now
    start_time = (datetime.utcnow() - timedelta(minutes=10)).isoformat() + "Z"

    print("🔍 Starting to poll for new payments...\n")
    while True:
        check_payments(access_token, start_time)
        start_time = datetime.utcnow().isoformat() + "Z"
        time.sleep(30)  # Wait 30 seconds before checking again

if __name__ == "__main__":
    main()
