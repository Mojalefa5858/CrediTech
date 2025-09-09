import cv2
import pytesseract
import os
import re

def clean_text(text):
    return re.sub(r'[|>]', '', text).strip()

def extract_fields_from_lines(lines):
    extracted = {
        "full_name": None,
        "date_of_birth": None,
        "id_number": None
    }
    
    surname = ""
    first_names = ""

    for line in lines:
        line_clean = clean_text(line.lower())

        # Extract surname
        if "surname" in line_clean:
            match = re.search(r"surname[:\-]?\s*(.+)", line, re.IGNORECASE)
            if match:
                surname = match.group(1).strip()

        # Extract first names
        if "first name" in line_clean or "firstname" in line_clean:
            match = re.search(r"first ?names?[:\-]?\s*(.+)", line, re.IGNORECASE)
            if match:
                first_names = match.group(1).strip()

        # Extract DOB
        if "date of birth" in line_clean:
            match = re.search(r"date of birth[:\-]?\s*(\d{2}/\d{2}/\d{4})", line, re.IGNORECASE)
            if match:
                extracted["date_of_birth"] = match.group(1)

        # Extract ID number
        if "id number" in line_clean or "id no" in line_clean:
            match = re.search(r"id (?:number|no)[:\-]?\s*([0-9]{6,})", line, re.IGNORECASE)
            if match:
                extracted["id_number"] = match.group(1).strip()

    if first_names and surname:
        extracted["full_name"] = f"{first_names} {surname}"

    return extracted

def is_lesotho_national_id(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"❌ Could not open image at: {image_path}")

    ocr_text = pytesseract.image_to_string(img)
    lines = ocr_text.strip().splitlines()
    text_lower = ocr_text.lower()

    extracted_fields = extract_fields_from_lines(lines)

    national_id_checks = {
        "surname": "surname" in text_lower,
        "first_name": "first name" in text_lower or "firstname" in text_lower,
        "nationality_mosotho": "nationality mosotho" in text_lower,
        "dob": bool(extracted_fields["date_of_birth"]),
        "id_number": bool(extracted_fields["id_number"])
    }

    identity_card_checks = {
        "national_identity_card": "national identity card" in text_lower,
        "surname": "surname" in text_lower,
        "first_names": "first names" in text_lower or "firstname" in text_lower,
        "id_number": bool(extracted_fields["id_number"]),
        "dob": bool(extracted_fields["date_of_birth"])
    }

    national_id_matches = sum(national_id_checks.values())
    identity_card_matches = sum(identity_card_checks.values())

    is_valid = False
    document_type = None
    checks = {}

    if national_id_matches >= 2 or identity_card_matches >= 2:
        is_valid = True
        if national_id_matches >= identity_card_matches:
            document_type = "National ID"
            checks = national_id_checks
        else:
            document_type = "National Identity Card"
            checks = identity_card_checks

    return is_valid, document_type, checks, extracted_fields, ocr_text

# --- MAIN EXECUTION BLOCK ---

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "iddd.jpeg")  # Replace with your actual image filename

    try:
        is_valid, doc_type, field_matches, extracted, ocr_text = is_lesotho_national_id(image_path)

        if is_valid:
            print(f"✅ Valid Lesotho {doc_type} detected.")
        else:
            print("❌ This is NOT a valid Lesotho ID or Identity Card.")

        print("\n--- Extracted Information ---")
        print(f"👤 Full Name     : {extracted['full_name'] or 'Not found'}")
        print(f"🎂 Date of Birth : {extracted['date_of_birth'] or 'Not found'}")
        print(f"🆔 ID Number     : {extracted['id_number'] or 'Not found'}")

        print("\n--- Field Matches ---")
        for field, matched in field_matches.items():
            status = "✔️" if matched else "❌"
            print(f"  {field.replace('_', ' ').title()}: {status}")

        print("\n--- OCR Text Preview ---")
        print(ocr_text.strip())

    except Exception as e:
        print("❌ Error:", e)
