import requests

# Using the exact endpoint you provided
BASE_URL = "https://680fbece27f2fdac240f3f59.mockapi.io/api1/v1/Central_Of_Lesotho"

def fetch_loan_data():
    """Fetch loan data from the mockAPI endpoint"""
    try:
        print(f"Connecting to: {BASE_URL}")
        response = requests.get(BASE_URL)
        
        # Check if request was successful
        if response.status_code == 200:
            return response.json()
        else:
            print(f"\nAPI returned status code: {response.status_code}")
            print("Possible reasons:")
            print("1. The endpoint name is incorrect")
            print("2. The data hasn't been created in mockAPI yet")
            print(f"Response content: {response.text[:200]}...")  # Show first 200 chars of response
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\nFailed to connect to API: {e}")
        return None

def display_loan_data(loan_data):
    """Display loan data in a clean format"""
    if not loan_data:
        print("No loan data available to display")
        return
    
    print("\nCENTRAL BANK OF LESOTHO - LOAN APPLICATIONS")
    print("=" * 60)
    for loan in loan_data:
        print(f"\nApplication ID: {loan.get('id', 'N/A')}")
        print(f"Client: {loan.get('FirstName', 'N/A')} {loan.get('LastName', 'N/A')}")
        print(f"Loan Amount: ZAR {loan.get('loanAmaout', 'N/A'):,}")  # Format with commas
        print(f"Status: {'\033[92mAPPROVED\033[0m' if loan.get('LoanStatus') else '\033[91mPENDING\033[0m'}")
        print("-" * 60)

if __name__ == "__main__":
    print("Fetching loan applications from Central Bank of Lesotho...")
    loans = fetch_loan_data()
    
    if isinstance(loans, list):
        display_loan_data(loans)
    elif loans:
        # Handle case where single record is returned (not in a list)
        display_loan_data([loans])
    else:
        print("Unable to display loan data. Please check:")
        print("1. You have created records in your mockAPI dashboard")
        print("2. The endpoint name is exactly 'Central_Of_Lesotho'")
        print("3. Your internet connection is working")