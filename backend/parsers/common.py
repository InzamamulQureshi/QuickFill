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

# Pincode 2-digit prefix to state mapping for resilient state recovery
PINCODE_PREFIX_MAP = {
    "11": "Delhi",
    "12": "Haryana", "13": "Haryana",
    "14": "Punjab", "15": "Punjab", "16": "Punjab",
    "17": "Himachal Pradesh",
    "18": "Jammu and Kashmir", "19": "Jammu and Kashmir",
    "20": "Uttar Pradesh", "21": "Uttar Pradesh", "22": "Uttar Pradesh",
    "23": "Uttar Pradesh", "24": "Uttar Pradesh", "25": "Uttar Pradesh",
    "26": "Uttarakhand", "27": "Uttar Pradesh", "28": "Uttar Pradesh",
    "30": "Rajasthan", "31": "Rajasthan", "32": "Rajasthan", "33": "Rajasthan", "34": "Rajasthan",
    "36": "Gujarat", "37": "Gujarat", "38": "Gujarat", "39": "Gujarat",
    "40": "Maharashtra", "41": "Maharashtra", "42": "Maharashtra", "43": "Maharashtra", "44": "Maharashtra",
    "45": "Madhya Pradesh", "46": "Madhya Pradesh", "47": "Madhya Pradesh", "48": "Madhya Pradesh",
    "49": "Chhattisgarh",
    "50": "Telangana", "51": "Andhra Pradesh", "52": "Andhra Pradesh", "53": "Andhra Pradesh",
    "56": "Karnataka", "57": "Karnataka", "58": "Karnataka", "59": "Karnataka",
    "60": "Tamil Nadu", "61": "Tamil Nadu", "62": "Tamil Nadu", "63": "Tamil Nadu", "64": "Tamil Nadu",
    "67": "Kerala", "68": "Kerala", "69": "Kerala",
    "70": "West Bengal", "71": "West Bengal", "72": "West Bengal", "73": "West Bengal", "74": "West Bengal",
    "75": "Odisha", "76": "Odisha", "77": "Odisha",
    "78": "Assam", "79": "Assam",
    "80": "Bihar", "81": "Bihar", "82": "Bihar", "83": "Jharkhand", "84": "Bihar", "85": "Bihar"
}

def get_state_from_pincode(pincode: str) -> str:
    """Infers Indian state from the 6-digit postal index number prefix."""
    if not pincode or len(pincode.strip()) < 2:
        return ""
    clean_p = re.sub(r"\D", "", pincode)
    return PINCODE_PREFIX_MAP.get(clean_p[:2], "")

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

# Words that should NEVER appear inside a candidate's personal name
FORBIDDEN_NAME_WORDS = {
    "DOWNLOAD", "DATE", "ISSUE", "PRINT", "ADDRESS", "AADHAAR", "UIDAI",
    "GOVERNMENT", "INDIA", "BHARAT", "MALE", "FEMALE", "TRANSGENDER", "YEAR", "BIRTH",
    "ENROLMENT", "VALID", "SIGNATURE", "HELP", "INFO", "INFORMATION",
    "BUNGLOW", "BUNGALOW", "FLAT", "FLOOR", "ROAD", "MARG", "STREET",
    "NAGAR", "HALL", "BUILDING", "BLDG", "HOUSE", "NEAR", "OPP", "VILLAGE",
    "POST", "DIST", "DISTRICT", "STATE", "PIN", "PINCODE", "MOBILE", "VTC",
    "SUB", "PO", "VID", "VIB", "VIRTUAL", "CARD", "AUTHORITY", "UNIQUE", "IDENTIFICATION",
    "IDENTITY", "CITIZENSHIP", "PROOF", "BENEFIT", "BENEFITS", "SERVICE", "SERVICES",
    "COMMUNICATION", "OFFLINE", "ONLINE", "AUTHENTICATION", "REPUBLIC", "DEPARTMENT",
    "DOCUMENTS", "SUPPORT", "UPDATED", "ENTITIES", "SEEKING", "CONSENT",
    "WEST", "EAST", "NORTH", "SOUTH", "CHAWL", "COMPOUND", "URBAN", "RURAL",
    "COLONY", "SECTOR", "BLOCK", "LANE", "GALI", "MOHALLA", "TALUKA", "TEHSIL",
    "YOUR", "YOURAADHAAR", "AADHAARNO", "NO", "GOV", "GOVIN", "GOVAM", "UIDAI", "EMAIL", "WWW", "HELP", "VERIFY", "SECURE", "QRCODE", "QR", "XML", "CODE", "ELECTRONICALLY", "GENERATED", "LETTER", "ISSUED",
    "CHILD", "CARE", "WIFE", "HUSBAND", "FATHER", "MOTHER", "DAUGHTER", "SON", "SPOUSE", "GUARDIAN"
}

# UIDAI e-Aadhaar informational boilerplate bullet points
INSTRUCTION_TERMS = [
    "DOCUMENTS TO SUPPORT", "SHOULD BE UPDATED", "AVAIL OF VARIOUS",
    "GOVERNMENT BENEFITS", "KEEP YOUR MOBILE", "DOWNLOAD MAADHAAR",
    "LOCK/UNLOCK", "ENTITIES SEEKING", "OBLIGATED TO SEEK",
    "EITHER ONLINE", "AUTHENTICATION AGENCY", "QR SCANNER",
    "UNIQUE AND SECURE", "INFORMATION", "सूचना", "YEARS FROM DATE",
    "PROOF OF IDENTITY", "NOT OF CITIZENSHIP", "PROOF OF DOB",
    "AADHAAR IS PROOF", "NOT FOR TRAVEL", "BAAL AADHAAR",
    "BE USED WITH VERIFICATION", "SCANNING OF QR CODE", "HELP@UIDAI",
    "REGULATIONS", "SUBMITTED BY", "NUMBER HOLDER", "AADHAAR NUMBER HOLDER",
    "YEARS FROM DATE OF ENROLMENT", "ENTITIES SEEKING AADHAAR",
    "ओळखीचा पुरावा", "नागरिकत्व किंवा", "जन्मतारखेचा नाही", "पडताळणीसाठी",
    "माझे आधार", "माझी ओळख", "VALID THROUGHOUT THE COUNTRY", "CARRY AADHAAR",
    "ELECTRONICALLY GENERATED", "OFFLINE XML", "SECURE QR CODE",
    "VERIFY IDENTITY", "AUTHENTICATION", "SECURE QR", "QR CODE", "OFFLINE XML"
]


def refine_text_spacing(text: str) -> str:
    """
    Normalizes spacing between English words, names, punctuation, and numeric boundaries
    to ensure text produced by deep-learning OCR models (like RapidOCR) has natural inter-word spacing.
    """
    if not text:
        return ""
    # Normalize unicode spaces and tabs
    s = text.replace("\u00a0", " ").replace("\u200b", " ").replace("\t", " ")

    # Punctuation spacing: comma, colon, semicolon followed by letter/number without space
    s = re.sub(r"([,;:])(?=[A-Za-z0-9])", r"\1 ", s)

    # Parentheses spacing
    s = re.sub(r"([A-Za-z0-9])\(", r"\1 (", s)
    s = re.sub(r"\)(?=[A-Za-z0-9])", r") ", s)

    # Relationship slashes: keep 'C/O', 'S/O', 'D/O', 'W/O' clean
    s = re.sub(r"\b([CSDWH]/[Oic0])[:\s.-]*(?=[A-Za-z])", r"\1: ", s, flags=re.IGNORECASE)
    # Add spacing around '/' between full words (e.g. Male/MALE -> Male / MALE, Date of Birth/DOB -> Date of Birth / DOB)
    s = re.sub(r"(?<=[a-zA-Z]{2})/(?=[a-zA-Z]{2})", r" / ", s)

    # CamelCase: split lowercase followed by uppercase (e.g. 'MohammadFarid' -> 'Mohammad Farid')
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)

    # Number followed by word or label (e.g. 'HillNo3' -> 'Hill No 3')
    s = re.sub(r"\b(No|Room|R|Plot|Flat|Ward|Sector|Block|Hill)([0-9]+)\b", r"\1 \2", s, flags=re.IGNORECASE)

    # Common glued words on Indian IDs
    common_glued = [
        (r"\bGovernmentof\b", "Government of"),
        (r"\bAuthorityof\b", "Authority of"),
        (r"\bDateof\b", "Date of"),
        (r"\bproofof\b", "proof of"),
        (r"\bnotof\b", "not of"),
        (r"\bAadhaarno\b", "Aadhaar no"),
        (r"\bEnrolmentNo\b", "Enrolment No"),
        (r"\bYourAadhaarNo\b", "Your Aadhaar No"),
        (r"\bYourAadhaar\b", "Your Aadhaar"),
        (r"\bYearof\b", "Year of"),
        (r"\bshouldbe\b", "should be"),
        (r"\bnotfor\b", "not for"),
        (r"\bChildof\b", "Child of"),
        (r"\bCareof\b", "Care of"),
        (r"\bWifeof\b", "Wife of"),
        (r"\bSonof\b", "Son of"),
        (r"\bDaughterof\b", "Daughter of"),
        (r"\bHusbandof\b", "Husband of"),
    ]
    for pat, repl in common_glued:
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)

    # Letter followed by 6-digit pincode
    s = re.sub(r"([A-Za-z])(?=[1-9]\d{5}\b)", r"\1 ", s)

    # Collapse multiple spaces
    s = re.sub(r" +", " ", s).strip()
    return s


def clean_line(text: str) -> str:
    """Removes stray symbols, normalizes unicode punctuation, and refines inter-word spacing."""
    if not text:
        return ""
    # Normalize unicode fullwidth punctuation to standard ASCII equivalents
    text = text.replace("，", ",").replace("：", ":").replace("；", ";").replace("（", "(").replace("）", ")").replace("—", "-")
    # Apply natural spacing refinement
    text = refine_text_spacing(text)
    cleaned = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9)]+$", "", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def is_instruction_noise(line: str) -> bool:
    """Detects UIDAI informational boilerplate, instruction tables, and disclaimers."""
    if not line:
        return True
    u = line.upper()
    for term in INSTRUCTION_TERMS:
        if term in u:
            return True
    return False


def is_header_noise(line: str) -> bool:
    """Checks if a line contains typical ID header noise, instructions, or boilerplate."""
    if not line:
        return True
    if is_instruction_noise(line):
        return True

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


def is_valid_person_name(cand: str) -> bool:
    """Validates whether a candidate string is genuinely a person's name and not address/noise."""
    if not cand or len(cand.strip()) < 3:
        return False
    # Person names on ID cards never contain multi-digit numbers (Aadhaar/VID/dates/phones)
    if re.search(r"\d{2,}", cand):
        return False
    words = [w for w in re.findall(r"[A-Za-z]+", cand) if len(w) > 1]
    if not words:
        return False
    # If any word is forbidden or line is noise
    for w in words:
        if w.upper() in FORBIDDEN_NAME_WORDS:
            return False
    if is_header_noise(cand) or is_instruction_noise(cand):
        return False
    # Person name should be 1 to 6 words
    if not (1 <= len(words) <= 6):
        return False
    # If single word, must be at least 3 letters (e.g. 'Ram', 'Raj', 'Dev', 'Ali', 'Amit')
    if len(words) == 1 and len(words[0]) < 3:
        return False
    return True


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
    Extracts an Aadhaar number from text supporting standard, masked, contiguous,
    unevenly spaced, and common OCR-corrupted formats (e.g. O->0, I/l->1).
    Carefully isolates from 16-digit Virtual IDs (VID), 10-digit mobiles, 14-digit enrolment numbers,
    and the 1947 UIDAI helpline.
    """
    if not text:
        return None

    # Step 1: Strip 1947 helpline noise
    clean_text = re.sub(r"[@#]?\b1947\b", "", text)

    # Step 2: Strip explicit VID lines (16 digits starting with 9 or labeled VID)
    clean_text = re.sub(r"\bVID\s*[:\s]*[0-9IlO\s-]{16,22}\b", "", clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"\b9\d{3}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b", "", clean_text)
    clean_text = re.sub(r"(?<!\d)9\d{15}(?!\d)", "", clean_text)

    # Step 3: Match standard 4-4-4 format with flexible whitespace (1 or more spaces, tabs, dashes, dots)
    std_m = re.search(r"(?<!\d)([2-9]\d{3})[\s.-]+(\d{4})[\s.-]+(\d{4})(?!\d)", clean_text)
    if std_m:
        return f"{std_m.group(1)} {std_m.group(2)} {std_m.group(3)}"

    # Step 4: Masked formats (XXXX XXXX 1234 or XXXXXXXX1234 or •••• •••• 1234)
    masked_m = re.search(r"(?<![A-Za-z0-9])([X*•x]{4})[\s.-]*([X*•x]{4})[\s.-]*(\d{4})(?!\d)", clean_text)
    if masked_m:
        return f"{masked_m.group(1).upper()} {masked_m.group(2).upper()} {masked_m.group(3)}"

    # Step 5: Contiguous 12 digits (strictly 12 digits starting 2-9, not part of longer number)
    contig_m = re.search(r"(?<!\d)([2-9]\d{11})(?!\d)", clean_text)
    if contig_m:
        d = contig_m.group(1)
        return f"{d[0:4]} {d[4:8]} {d[8:12]}"

    # Step 6: Unevenly grouped 12 digits (e.g. 4-8 or 8-4 or 3-5-4)
    for line in clean_text.splitlines():
        # Strip enrolment numbers like 2821/27092/02859 or dates like 20/05/1979
        line_no_slash = re.sub(r"\d+/\d+(?:/\d+)?", "", line)
        digits_only = re.sub(r"\D", "", line_no_slash)
        if len(digits_only) == 12 and digits_only[0] in "23456789":
            return f"{digits_only[0:4]} {digits_only[4:8]} {digits_only[8:12]}"

    # Step 7: OCR typo correction on 12-character blocks (O->0, I/l->1, B->8, S->5)
    char_map = str.maketrans("OIlBS", "01185", " ")
    for line in clean_text.splitlines():
        typo_m = re.search(r"(?<![A-Za-z0-9])([2-9][0-9OIlBS]{3})[\s.-]+([0-9OIlBS]{4})[\s.-]+([0-9OIlBS]{4})(?![A-Za-z0-9])", line)
        if typo_m:
            raw_cand = typo_m.group(1) + typo_m.group(2) + typo_m.group(3)
            fixed_digits = raw_cand.translate(char_map)
            if len(fixed_digits) == 12 and fixed_digits[0] in "23456789":
                return f"{fixed_digits[0:4]} {fixed_digits[4:8]} {fixed_digits[8:12]}"

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

