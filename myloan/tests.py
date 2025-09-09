import cv2
import pytesseract
import PyPDF2
import re
import os

# Configure Tesseract path if needed
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

def validate_lesotho_id(image_path):
    """Validate Lesotho ID with improved name extraction"""
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"❌ Could not open image at: {image_path}")

    # Preprocess image for better OCR
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    # OCR text extraction
    ocr_text = pytesseract.image_to_string(thresh)
    text_lower = ocr_text.lower()

    # Initialize variables
    document_type = None
    checks = {}
    is_valid = False
    first_name = None
    surname = None

    # Required fields for National ID
    national_id_checks = {
        "surname": "surname" in text_lower,
        "first_name": "first name" in text_lower,
        "nationality_mosotho": "nationality mosotho" in text_lower,
        "dob": bool(re.search(r"date of birth\s+\d{2}/\d{2}/", text_lower)),
        "id_number": bool(re.search(r"id no[.:]?\s*[0-9]", text_lower)),
        "identity": "identity" in text_lower
    }

    # Required fields for National Identity Card
    identity_card_checks = {
        "national_identity_card": "national identity card" in text_lower,
        "surname": "surname" in text_lower,
        "first_names": "first names" in text_lower,
        "id_number": bool(re.search(r"id no[.:]?\s*[0-9]", text_lower)),
        "dob": bool(re.search(r"date of birth\s+\d{2}/\d{2}/", text_lower)),
        "identity": "identity" in text_lower
    }

    # Count matches for each type
    national_id_matches = sum(national_id_checks.values())
    identity_card_matches = sum(identity_card_checks.values())

    # Determine document type
    if national_id_matches >= 2 or identity_card_matches >= 2:
        is_valid = True
        if national_id_matches >= identity_card_matches:
            document_type = "National ID"
            checks = national_id_checks
        else:
            document_type = "National Identity Card"
            checks = identity_card_checks

    # Improved name extraction
    lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
    
    # Pattern 1: Direct label matching
    for i, line in enumerate(lines):
        if re.search(r'first name[:]?$', line, re.IGNORECASE) and i+1 < len(lines):
            first_name = lines[i+1].strip()
        if re.search(r'surname[:]?$', line, re.IGNORECASE) and i+1 < len(lines):
            surname = lines[i+1].strip()

    # Pattern 2: Look for names after labels in same line
    if not first_name:
        name_match = re.search(r'first name[:]?\s*([^\n]+)', ocr_text, re.IGNORECASE)
        if name_match:
            first_name = name_match.group(1).strip()
    
    if not surname:
        surname_match = re.search(r'surname[:]?\s*([^\n]+)', ocr_text, re.IGNORECASE)
        if surname_match:
            surname = surname_match.group(1).strip()

    # Clean extracted names
    if first_name:
        first_name = ' '.join([word for word in first_name.split() if word.lower() not in ['first', 'name', ':']])
    if surname:
        surname = ' '.join([word for word in surname.split() if word.lower() not in ['surname', ':']])

    return is_valid, document_type, checks, ocr_text, first_name, surname

def validate_payslip(payslip_path):
    """Validate payslip with improved text extraction"""
    try:
        # Handle both PDF and image files
        if payslip_path.lower().endswith('.pdf'):
            with open(payslip_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
        else:
            img = cv2.imread(payslip_path)
            if img is None:
                return False, "Could not read payslip image", [], False, ""
            
            # Preprocess image
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            text = pytesseract.image_to_string(thresh)

        if not text.strip():
            return False, "No text found in document", [], False, text

        # Get structured lines
        lines = text.strip().splitlines()
        structured_lines = []
        for line in lines:
            line_clean = line.strip()
            if len(line_clean.split()) >= 2 and re.search(r"\d", line_clean) and re.search(r"[a-zA-Z]", line_clean):
                structured_lines.append(line_clean)

        # Currency detection
        currency_present = bool(re.search(r"[mM]\s*\d+|r\s*\d+|\$\s*\d+", text))

        # Extract employee name if available
        employee_name = None
        name_match = re.search(r'employee(name|:\s*)([^\n]+)', text, re.IGNORECASE)
        if name_match:
            employee_name = name_match.group(2).strip()

        # Final validation
        is_valid = len(structured_lines) >= 2

        return is_valid, text, structured_lines, currency_present, text, employee_name

    except Exception as e:
        return False, f"Error processing payslip: {str(e)}", [], False, "", None

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

def main():
    # File paths - update these
    id_path = "/home/bob/Desktop/Coding/loaner11/myloan/id2.jpg"
    payslip_path = "/home/bob/Desktop/Coding/loaner11/myloan/MONYOOE.pdf"

    try:
        # Validate ID
        id_valid, id_type, id_checks, id_text, first_name, surname = validate_lesotho_id(id_path)
        
        print("\n" + "="*50)
        print(" LESOTHO ID VALIDATION")
        print("="*50)
        if id_valid:
            print(f"✅ Valid {id_type} Detected")
            if first_name and surname:
                print(f"  👤 Name: {first_name} {surname}")
            else:
                print("  ❌ Could not extract complete name from ID")
            
            print("\nField Matches:")
            for field, present in id_checks.items():
                print(f"  {field.replace('_', ' ').title()}: {'✔️' if present else '❌'}")
            
            if id_text and len(id_text) < 1000:
                print("\nExtracted Text Preview:")
                print(id_text[:500] + ("..." if len(id_text) > 500 else ""))
        else:
            print("❌ Invalid Lesotho ID")
        
        # Validate Payslip
        print("\n" + "="*50)
        print(" PAYSLIP VALIDATION")
        print("="*50)
        payslip_valid, payslip_text, structured_lines, currency_found, full_text, employee_name = validate_payslip(payslip_path)
        
        if payslip_valid:
            print("✅ Valid Payslip Detected")
            print(f"\nStructured Lines Found ({len(structured_lines)}):")
            for line in structured_lines[:5]:
                print(f"  ✔️ {line}")
            print(f"\nCurrency Detected: {'✔️ Yes' if currency_found else '❌ No'}")
            
            if employee_name:
                print(f"\nEmployee Name from Payslip: {employee_name}")
            
            if id_valid and first_name and surname:
                first_found, last_found = check_name_match(payslip_text, first_name, surname)
                print("\nNAME VERIFICATION:")
                print(f"  First Name ({first_name}): {'✅ FOUND' if first_found else '❌ NOT FOUND'}")
                print(f"  Surname ({surname}): {'✅ FOUND' if last_found else '❌ NOT FOUND'}")
        else:
            print("❌ Invalid Payslip")
            print("\nValidation Details:")
            print(f"  Structured Lines Found: {len(structured_lines)} (Need at least 2)")
            print(f"  Currency Detected: {'✔️ Yes' if currency_found else '❌ No'}")
            if payslip_text and len(payslip_text) < 1000:
                print("\nExtracted Text Preview:")
                print(payslip_text[:500] + ("..." if len(payslip_text) > 500 else ""))
        
        print("\n" + "="*50)
        if id_valid and payslip_valid:
            if first_name and surname:
                first_found, last_found = check_name_match(payslip_text, first_name, surname)
                if first_found and last_found:
                    print("✅ VERIFICATION SUCCESS: Valid documents with matching names")
                else:
                    print("⚠️ VERIFICATION WARNING: Valid documents but names don't match")
            else:
                print("✅ VERIFICATION SUCCESS: Valid documents (names not checked)")
        else:
            print("❌ VERIFICATION FAILED: Invalid documents")
            
    except Exception as e:
        print(f"\n❌ SYSTEM ERROR: {str(e)}")

if __name__ == "__main__":
    main()