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

# Regex for Aadhaar number - 12 digits
AADHAAR_REGEX = re.compile(r"\b([2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4})\b")

# Regex for PAN card number - 5 letters, 4 digits, 1 letter
PAN_REGEX = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b")

# Noise terms to filter out
HEADER_NOISE_TERMS = [
    "GOVERNMENT OF INDIA", "BHARAT SARKAR", "UNIQUE IDENTIFICATION",
    "AUTHORITY OF INDIA", "ENROLMENT", "DOWNLOAD DATE", "ISSUE DATE",
    "INCOME TAX DEPARTMENT", "GOVT OF INDIA", "GOVT. OF INDIA",
    "PERMANENT ACCOUNT NUMBER", "CARD", "MALE", "FEMALE", "TRANSGENDER",
    "DOB", "YEAR OF BIRTH", "ADDRESS", "AADHAAR", "MERAAADHAAR", "UIDAI",
    "HELP@UIDAI.GOV.IN", "WWW.UIDAI.GOV.IN", "1947", "SIGNATURE", "NOT FOR TRAVEL",
    "QR CODE", "PHOTO", "SIGN", "INCOME TAX"
]


def clean_line(text: str) -> str:
    """Removes stray symbols and trims whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9)]+$", "", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def is_header_noise(line: str) -> bool:
    """Checks if a line contains typical ID header noise or boilerplate."""
    line_upper = line.upper().strip()
    # Exactly matches noise words
    if line_upper in ["QR CODE", "PHOTO", "SIGNATURE", "NAME", "NAME /", "FATHER'S NAME", "DATE OF BIRTH"]:
        return True
    for term in HEADER_NOISE_TERMS:
        if term in line_upper and len(line_upper) < len(term) + 10:
            return True
    return False


def format_aadhaar_number(raw_num: str) -> str:
    """Formats 12 digit number as spaced 4-4-4."""
    digits = re.sub(r"\D", "", raw_num)
    if len(digits) == 12:
        return f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"
    return raw_num
