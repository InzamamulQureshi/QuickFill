"""
PAN Card Parser for Quick Fill (QF).
Extracts fields from Indian Permanent Account Number (PAN) cards.
"""
import re
from typing import Dict, Any, List
from .common import PAN_REGEX, clean_line, is_header_noise
from .date_util import calculate_age, normalize_date_string


class PanParser:
    """Specialized extractor for Income Tax Department PAN Cards."""

    @staticmethod
    def parse(raw_text: str, lines: List[str]) -> Dict[str, Any]:
        result = {
            "card_type": "PAN Card",
            "name": "",
            "dob": "",
            "age": {},
            "gender": "",
            "pan_number": "",
            "aadhaar_number": "",
            "father_spouse_name": "",
            "address": "",
            "pincode": "",
            "state": "",
            "confidence_scores": {}
        }

        # 1. PAN Number (5 letters, 4 digits, 1 letter)
        pan_match = PAN_REGEX.search(raw_text)
        if pan_match:
            result["pan_number"] = pan_match.group(1).upper()
            result["confidence_scores"]["pan_number"] = 0.98

        # 2. Date of Birth (DOB)
        dob_m = re.search(r"\b([0-3][0-9][/.-][0-1][0-9][/.-][1-2][0-9]{3})\b", raw_text)
        if dob_m:
            raw_dob = dob_m.group(1)
            normalized = normalize_date_string(raw_dob)
            if normalized:
                result["dob"] = normalized
                result["age"] = calculate_age(normalized)
                result["confidence_scores"]["dob"] = 0.95
                result["confidence_scores"]["age"] = 0.95

        # 3. Gender
        if re.search(r"\b(FEMALE|WOMAN|महिला)\b", raw_text, re.IGNORECASE):
            result["gender"] = "Female"
            result["confidence_scores"]["gender"] = 0.95
        elif re.search(r"\b(MALE|PURUSH|पुरुष)\b", raw_text, re.IGNORECASE):
            result["gender"] = "Male"
            result["confidence_scores"]["gender"] = 0.95

        # 4. Linked Aadhaar (common on modern e-PAN cards)
        from .common import extract_aadhaar_number, format_aadhaar_number
        aadhaar_num = extract_aadhaar_number(raw_text)
        if aadhaar_num:
            result["aadhaar_number"] = format_aadhaar_number(aadhaar_num)

        # 5. Clean lines
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]

        cardholder_name = ""
        father_name = ""

        # Strategy A: Label-following line search
        for idx, line in enumerate(cleaned_lines):
            # Check for Name label: contains 'Name' or 'नाम' but NOT 'Father'
            if re.search(r"\bName\b|नाम", line, re.IGNORECASE) and not re.search(r"Father|पिता", line, re.IGNORECASE):
                if idx + 1 < len(cleaned_lines):
                    next_l = cleaned_lines[idx + 1]
                    if not is_header_noise(next_l) and not re.search(r"Father|DOB|Date|Permanent", next_l, re.IGNORECASE):
                        words = [w for w in next_l.split() if w.isalpha()]
                        if 1 <= len(words) <= 6:
                            cardholder_name = " ".join(words).title()

            # Check for Father's Name label
            if re.search(r"Father|पिता", line, re.IGNORECASE):
                if idx + 1 < len(cleaned_lines):
                    next_l = cleaned_lines[idx + 1]
                    if not is_header_noise(next_l) and not re.search(r"Date|DOB|Birth|Permanent", next_l, re.IGNORECASE):
                        words = [w for w in next_l.split() if w.isalpha()]
                        if 1 <= len(words) <= 6:
                            father_name = " ".join(words).title()

        # Strategy B: Line immediately following PAN number (very common in e-PAN PDFs)
        if not cardholder_name:
            for idx, line in enumerate(cleaned_lines):
                if PAN_REGEX.search(line):
                    for offset in [1, 2]:
                        if idx + offset < len(cleaned_lines):
                            cand = cleaned_lines[idx + offset]
                            if re.search(r"\d", cand) or re.search(r"\b(Male|Female|Income|Tax|Permanent|Account|Department)\b", cand, re.IGNORECASE):
                                continue
                            words = [w for w in cand.split() if w.isalpha()]
                            if 1 <= len(words) <= 6 and all(len(w) > 1 for w in words):
                                cardholder_name = " ".join(words).title()
                                break
                    if cardholder_name:
                        break

        # Strategy C: Alphabetic candidate lines
        if not cardholder_name or not father_name:
            candidates = []
            for line in cleaned_lines:
                if is_header_noise(line):
                    continue
                if PAN_REGEX.search(line) or re.search(r"\d", line):
                    continue
                if re.search(r"\b(Male|Female|Income|Tax|Permanent|Account|Department|Govt|Government)\b", line, re.IGNORECASE):
                    continue
                words = [w for w in line.split() if w.isalpha()]
                if 2 <= len(words) <= 6 and all(len(w) > 1 for w in words):
                    candidates.append(" ".join(words).title())

            if candidates:
                if not cardholder_name and len(candidates) >= 1:
                    cardholder_name = candidates[0]
                if not father_name and len(candidates) >= 2:
                    if candidates[1].upper() != cardholder_name.upper():
                        father_name = candidates[1]

        if cardholder_name:
            result["name"] = cardholder_name
            result["confidence_scores"]["name"] = 0.95

        if father_name:
            result["father_spouse_name"] = father_name
            result["confidence_scores"]["father_spouse_name"] = 0.90

        return result
