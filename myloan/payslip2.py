import os
import re
import pytesseract
import cv2
from pdf2image import convert_from_path
import tempfile

def convert_pdf_to_image(pdf_path):
    """Convert first page of a PDF to image."""
    images = convert_from_path(pdf_path, dpi=300)
    if not images:
        raise ValueError("No pages found in PDF.")
    temp_img_path = os.path.join(tempfile.gettempdir(), "temp_payslip.jpg")
    images[0].save(temp_img_path, "JPEG")
    return temp_img_path

def preprocess_image(image_path):
    """Enhance image for OCR."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 11, 2)

def extract_net_pay(text):
    """Extract net pay (monthly earnings) from OCR text."""
    patterns = [
        r"net pay[:\s]*[mM]?\s*([0-9][0-9.,]*)",
        r"total\s+earnings[:\s]*[mM]?\s*([0-9][0-9.,]*)",
        r"monthly\s+income[:\s]*[mM]?\s*([0-9][0-9.,]*)",
        r"amount\s+paid[:\s]*[mM]?\s*([0-9][0-9.,]*)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = match.group(1).replace(",", "").replace(" ", "").strip()
            amount = re.sub(r"[^\d]", "", amount)  # Remove non-digit chars
            return amount if amount.isdigit() else None
    return None

def extract_full_name(text_lines):
    """Extract full name from OCR lines."""
    name_pattern = re.compile(r"(employee name|name of employee|employee)[:\s]*([a-zA-Z\s\-]+)", re.IGNORECASE)
    for line in text_lines:
        match = name_pattern.search(line)
        if match:
            name = match.group(2).strip()
            name = re.sub(r"[^a-zA-Z\s\-]", "", name)
            return " ".join(name.split())

    # Fallback: Try to find a likely name (first ALL CAPS line with 2+ words)
    for line in text_lines:
        if line.isupper() and len(line.split()) >= 2 and len(line.strip()) > 5:
            name = re.sub(r"[^A-Z\s\-]", "", line.strip())
            return name.title()
    return None

def extract_workplace(text_lines):
    """Extract workplace or company name from top few lines."""
    for line in text_lines[:6]:
        if re.search(r"(company|employer|organization|pty|ltd|inc|limited)", line, re.IGNORECASE):
            return line.strip().title()
        if line.strip().isupper() and len(line.strip()) > 5:
            return line.strip().title()
    return None

def process_payslip(pdf_path):
    """Main processing function."""
    image_path = convert_pdf_to_image(pdf_path)
    processed_img = preprocess_image(image_path)
    ocr_text = pytesseract.image_to_string(processed_img)
    lines = ocr_text.strip().splitlines()

    full_name = extract_full_name(lines)
    net_pay = extract_net_pay(ocr_text)
    workplace = extract_workplace(lines)

    if full_name and net_pay:
        return {
            "valid": True,
            "full_name": full_name,
            "net_pay": net_pay,
            "workplace": workplace or "Not found"
        }
    else:
        return {
            "valid": False,
            "ocr_text": ocr_text
        }

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_file = os.path.join(current_dir, "jeffpay.pdf")  # Replace with your file

        result = process_payslip(pdf_file)

        if result["valid"]:
            print("✅ Payslip Summary")
            print("----------------------")
            print(f"👤 Full Name    : {result['full_name']}")
            print(f"💰 Net Pay      : {result['net_pay']}")
            print(f"🏢 Workplace     : {result['workplace']}")
        else:
            print("❌ Could not extract valid payslip information.")
            print("\n--- OCR Preview ---")
            print(result["ocr_text"].strip())

    except Exception as e:
        print("❌ Error:", e)
