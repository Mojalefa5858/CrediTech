import cv2
import pytesseract
import os
import re

def is_valid_payslip(image_path):
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"❌ Could not open image at: {image_path}")

    # OCR text extraction
    ocr_text = pytesseract.image_to_string(img)
    lines = ocr_text.strip().splitlines()

    if not ocr_text.strip():
        return False, [], 0, ocr_text

    structured_lines = []
    for line in lines:
        line_clean = line.strip()
        if len(line_clean.split()) >= 2 and re.search(r"\d", line_clean) and re.search(r"[a-zA-Z]", line_clean):
            structured_lines.append(line_clean)

    # Currency detection
    currency_present = bool(re.search(r"[mM|rR|\$]\s*\d+", ocr_text))

    # Final rule: at least 2 well-structured lines with text + number
    is_payslip = len(structured_lines) >= 2

    return is_payslip, structured_lines, currency_present, ocr_text

# --- MAIN EXECUTION BLOCK ---

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "jeffpay.pdf")  # Update filename as needed


    try:
        result, good_lines, currency_found, ocr_text = is_valid_payslip(image_path)

        print("✅ This appears to be a VALID payslip." if result else "❌ This is NOT a valid payslip.")
        print(f"\nStructured Lines with Text & Numbers ({len(good_lines)} found):")
        for line in good_lines:
            print(f"  ✔️ {line}")

        print(f"\nCurrency Detected: {'✔️ Yes' if currency_found else '❌ No'}")

        print("\n--- OCR Text Preview ---")
        print(ocr_text.strip())

    except Exception as e:
        print("Error:", e)
