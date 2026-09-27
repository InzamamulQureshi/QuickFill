"""
Shared utilities, regexes, and constants for Indian Identity Documents.
"""
import re
from typing import List, Optional

# List of 28 Indian States and 8 Union Territories
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

# Regex for Indian Postal Index Number (PIN Code) - 6 digits
PINCODE_REGEX = re.compile(r"\b([1-9][0-9]{2}\s?[0-9]{3})\b")

# Regex for Aadhaar number - standard 12 digits
AADHAAR_REGEX = re.compile(r"\b([2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4})\b")

# Regex for Masked Aadhaar (e.g. XXXX XXXX 1234 or •••• •••• 1234)
MASKED_AADHAAR_REGEX = re.compile(r"\b([X*•x]{4}\s?[X*•x]{4}\s?[0-9]{4})\b")

# Regex for PAN card number - 5 letters, 4 digits, 1 letter
PAN_REGEX = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b")

# Noise terms to filter out across all types of Aadhaar & PAN cards
HEADER_NOISE_TERMS = [
    "GOVERNMENT OF INDIA", "BHARAT SARKAR", "BHARAT", "UNIQUE IDENTIFICATION",
    "AUTHORITY OF INDIA", "ENROLMENT", "DOWNLOAD DATE", "ISSUE DATE", "PRINT DATE",
    "INCOME TAX DEPARTMENT", "GOVT OF INDIA", "GOVT. OF INDIA",
    "PERMANENT ACCOUNT NUMBER", "CARD", "MALE", "FEMALE", "TRANSGENDER",
    "DOB", "YEAR OF BIRTH", "ADDRESS", "AADHAAR", "MERAAADHAAR", "UIDAI",
    "HELP@UIDAI.GOV.IN", "WWW.UIDAI.GOV.IN", "1947", "SIGNATURE", "NOT FOR TRAVEL",
    "QR CODE", "PHOTO", "SIGN", "INCOME TAX", "PROOF OF IDENTITY",
    "NOT OF CITIZENSHIP", "CITIZENSHIP OR DATE OF BIRTH", "MERA AADHAAR",
    "MERI PEHCHAN", "MY AADHAAR", "MY IDENTITY", "VIRTUAL ID", "VID",
    "TO", "DETAILS", "VALID TILL", "BAAL AADHAAR", "DIGITALLY SIGNED",
    "SIGNATURE VALID", "ELECTRONICALLY GENERATED"
]


def clean_line(text: str) -> str:
    """Removes stray symbols and trims whitespace."""
    if not text:
        return ""
    # Strip symbols at boundaries but keep alphanumeric, dots, hyphens, and slashes
    cleaned = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9)]+$", "", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def is_header_noise(line: str) -> bool:
    """Checks if a line contains typical ID header noise or boilerplate."""
    line_upper = line.upper().strip()
    # Exactly matches noise words
    exact_noise = [
        "QR CODE", "PHOTO", "SIGNATURE", "NAME", "NAME /", "FATHER'S NAME",
        "DATE OF BIRTH", "TO", "DETAILS", "SIGNATURE VALID", "VALID"
    ]
    if line_upper in exact_noise:
        return True

    # Disclaimer on new Aadhaar cards: "Aadhaar is a proof of identity, not of citizenship..."
    if "PROOF OF IDENTITY" in line_upper or "NOT OF CITIZENSHIP" in line_upper:
        return True
    if "MERA AADHAAR" in line_upper or "MERI PEHCHAN" in line_upper:
        return True
    if "UNIQUE IDENTIFICATION" in line_upper or "AUTHORITY OF INDIA" in line_upper:
        return True
    if "GOVERNMENT OF INDIA" in line_upper or "BHARAT SARKAR" in line_upper:
        return True

    for term in HEADER_NOISE_TERMS:
        if term in line_upper and len(line_upper) < len(term) + 12:
            return True
    return False


def format_aadhaar_number(raw_num: str) -> str:
    """Formats 12 digit number as spaced 4-4-4, or formats masked format."""
    if not raw_num:
        return ""
    cleaned = raw_num.strip()
    # Check if masked format
    masked_m = MASKED_AADHAAR_REGEX.search(cleaned)
    if masked_m:
        parts = re.split(r"\s+", masked_m.group(1).strip())
        if len(parts) == 3:
            return f"{parts[0].upper()} {parts[1].upper()} {parts[2]}"
        # Contiguous masked
        raw = masked_m.group(1).replace(" ", "")
        if len(raw) == 12:
            return f"{raw[:4].upper()} {raw[4:8].upper()} {raw[8:]}"

    digits = re.sub(r"\D", "", cleaned)
    if len(digits) == 12:
        return f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"
    return raw_num


def extract_aadhaar_number(text: str) -> Optional[str]:
    """
    Extracts an Aadhaar number from text supporting standard, masked, and contiguous formats.
    Avoids accidentally capturing 16-digit Virtual IDs (VID).
    """
    if not text:
        return None

    # Strip any 16-digit Virtual ID (VID) lines first so they are not misread as a 12-digit Aadhaar
    clean_text = re.sub(r"\bVID\s*[:\s]*\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b", "", text, flags=re.IGNORECASE)
    clean_text = re.sub(r"\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b", "", clean_text)

    # 1. Standard 12 digits: 2345 6789 0123
    std_m = re.search(r"\b([2-9]\d{3}\s\d{4}\s\d{4})\b", clean_text)
    if std_m:
        return std_m.group(1)

    # 2. Masked format: XXXX XXXX 1234 or •••• •••• 1234
    masked_m = re.search(r"\b([X*•x]{4}\s[X*•x]{4}\s\d{4})\b", clean_text)
    if masked_m:
        return masked_m.group(1).upper()

    # 3. Contiguous masked: XXXXXXXX1234
    contig_masked = re.search(r"\b([X*•x]{8}\d{4})\b", clean_text)
    if contig_masked:
        s = contig_masked.group(1).upper()
        return f"{s[0:4]} {s[4:8]} {s[8:12]}"

    # 4. Contiguous 12 digits (ensure not part of a longer number like 16-digit VID)
    contig_m = re.search(r"(?<!\d)([2-9]\d{11})(?!\d)", clean_text)
    if contig_m:
        d = contig_m.group(1)
        return f"{d[0:4]} {d[4:8]} {d[8:12]}"

    # 5. Dashed format: 2345-6789-0123
    dash_m = re.search(r"\b([2-9]\d{3}[-]\d{4}[-]\d{4})\b", clean_text)
    if dash_m:
        d = re.sub(r"\D", "", dash_m.group(1))
        return f"{d[0:4]} {d[4:8]} {d[8:12]}"

    return None


def extract_virtual_id(text: str) -> Optional[str]:
    """Extracts 16-digit Virtual ID (VID) if printed on document."""
    if not text:
        return None
    vid_m = re.search(r"\bVID\s*[:\s]*(\d{4}\s?\d{4}\s?\d{4}\s?\d{4})\b", text, re.IGNORECASE)
    if vid_m:
        digits = re.sub(r"\D", "", vid_m.group(1))
        if len(digits) == 16:
            return f"{digits[0:4]} {digits[4:8]} {digits[8:12]} {digits[12:16]}"
    return None

