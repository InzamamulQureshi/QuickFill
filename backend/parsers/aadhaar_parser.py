"""
Aadhaar Card Parser for Quick Fill (QF).
Extracts fields from both Aadhaar Front and Aadhaar Back cards.
"""
import re
from typing import Dict, Any, List, Optional
from .common import (
    INDIAN_STATES, PINCODE_REGEX, AADHAAR_REGEX,
    clean_line, is_header_noise, format_aadhaar_number
)
from .date_util import calculate_age, normalize_date_string


class AadhaarParser:
    """Specialized extractor for UIDAI Aadhaar Cards (Front & Back)."""

    @staticmethod
    def parse_front(raw_text: str, lines: List[str]) -> Dict[str, Any]:
        result = {
            "card_type": "Aadhaar Front",
            "name": "",
            "dob": "",
            "age": {},
            "gender": "",
            "aadhaar_number": "",
            "father_spouse_name": "",
            "address": "",
            "pincode": "",
            "state": "",
            "confidence_scores": {}
        }

        # 1. Aadhaar Number
        num_match = AADHAAR_REGEX.search(raw_text)
        if num_match:
            result["aadhaar_number"] = format_aadhaar_number(num_match.group(1))
            result["confidence_scores"]["aadhaar_number"] = 0.95
        else:
            contig = re.search(r"\b([2-9]\d{11})\b", raw_text)
            if contig:
                result["aadhaar_number"] = format_aadhaar_number(contig.group(1))
                result["confidence_scores"]["aadhaar_number"] = 0.85

        # 2. DOB
        dob_patterns = [
            r"(?:DOB|D\.O\.B|Birth|Date\s*of\s*Birth|जन्म\s*तारीख)[\s:]*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{4})",
            r"(?:Year\s*of\s*Birth|YOB)[\s:]*([1-2][0-9]{3})",
            r"\b([0-3][0-9][/.-][0-1][0-9][/.-][1-2][0-9]{3})\b"
        ]
        for pat in dob_patterns:
            dob_m = re.search(pat, raw_text, re.IGNORECASE)
            if dob_m:
                raw_dob = dob_m.group(1)
                normalized = normalize_date_string(raw_dob)
                if normalized:
                    result["dob"] = normalized
                    result["age"] = calculate_age(normalized)
                    result["confidence_scores"]["dob"] = 0.95
                    result["confidence_scores"]["age"] = 0.95
                    break

        # 3. Gender
        if re.search(r"\b(FEMALE|WOMAN|महिला)\b", raw_text, re.IGNORECASE):
            result["gender"] = "Female"
            result["confidence_scores"]["gender"] = 0.95
        elif re.search(r"\b(MALE|PURUSH|पुरुष)\b", raw_text, re.IGNORECASE):
            result["gender"] = "Male"
            result["confidence_scores"]["gender"] = 0.95
        elif re.search(r"\b(TRANSGENDER)\b", raw_text, re.IGNORECASE):
            result["gender"] = "Transgender"
            result["confidence_scores"]["gender"] = 0.95

        # 4. Name extraction
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]
        dob_line_idx = -1
        for idx, line in enumerate(cleaned_lines):
            if re.search(r"DOB|Birth|D\.O\.B|[0-9]{2}/[0-9]{2}/[1-2][0-9]{3}", line, re.IGNORECASE):
                dob_line_idx = idx
                break

        candidate_name = ""
        if dob_line_idx > 0:
            for i in range(dob_line_idx - 1, -1, -1):
                line = cleaned_lines[i]
                if is_header_noise(line):
                    continue
                if re.search(r"\d", line):
                    continue
                if re.match(r"^[A-Za-z\s.]{3,40}$", line):
                    words = [w for w in line.split() if len(w) > 1]
                    if len(words) >= 1:
                        candidate_name = line
                        break

        if not candidate_name:
            for line in cleaned_lines:
                if is_header_noise(line):
                    continue
                if re.search(r"\d", line):
                    continue
                if re.match(r"^[A-Z][a-zA-Z\s.]{3,35}$", line):
                    words = line.split()
                    if 1 <= len(words) <= 4 and all(w.isalpha() for w in words):
                        candidate_name = line
                        break

        if candidate_name:
            result["name"] = candidate_name.title()
            result["confidence_scores"]["name"] = 0.90

        return result

    @staticmethod
    def parse_back(raw_text: str, lines: List[str]) -> Dict[str, Any]:
        result = {
            "card_type": "Aadhaar Back",
            "name": "",
            "dob": "",
            "age": {},
            "gender": "",
            "aadhaar_number": "",
            "father_spouse_name": "",
            "address": "",
            "pincode": "",
            "state": "",
            "confidence_scores": {}
        }

        # 1. Aadhaar Number
        num_match = AADHAAR_REGEX.search(raw_text)
        if num_match:
            result["aadhaar_number"] = format_aadhaar_number(num_match.group(1))

        # 2. Pincode
        pin_m = PINCODE_REGEX.search(raw_text)
        if pin_m:
            result["pincode"] = pin_m.group(1).replace(" ", "")
            result["confidence_scores"]["pincode"] = 0.95

        # 3. State
        for state in INDIAN_STATES:
            if re.search(rf"\b{re.escape(state)}\b", raw_text, re.IGNORECASE):
                result["state"] = state
                result["confidence_scores"]["state"] = 0.90
                break

        # 4. Father / Spouse / Guardian Name from Care of
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]
        co_prefix_pattern = re.compile(
            r"^(?:C/O|S/O|D/O|W/O|C\\O|S\\O|D\\O|W\\O|SIC\)?|DIC\)?|WIC\)?|CIC\)?|SO|DO|WO|CO|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of)[\s:.)-]*",
            re.IGNORECASE
        )

        for line in cleaned_lines:
            if co_prefix_pattern.search(line):
                # Strip the prefix to isolate the name
                extracted_name = co_prefix_pattern.sub("", line).strip()
                # Remove any trailing address parts if on same line (e.g. "Suresh Sharma, Flat 101")
                if "," in extracted_name:
                    extracted_name = extracted_name.split(",")[0].strip()
                words = [w for w in extracted_name.split() if w.isalpha()]
                if 1 <= len(words) <= 4:
                    result["father_spouse_name"] = " ".join(words).title()
                    result["confidence_scores"]["father_spouse_name"] = 0.92
                    break

        # Fallback regex across entire raw_text
        if not result["father_spouse_name"]:
            co_fallback = re.search(
                r"(?:C/O|S/O|D/O|W/O|SIC|DIC|WIC|CIC)[\s:.)-]*([A-Za-z\s.]+?)(?:,|\n|$|\d|Flat|H\.No)",
                raw_text, re.IGNORECASE
            )
            if co_fallback:
                val = co_fallback.group(1).strip()
                words = [w for w in val.split() if w.isalpha()]
                if 1 <= len(words) <= 4:
                    result["father_spouse_name"] = " ".join(words).title()
                    result["confidence_scores"]["father_spouse_name"] = 0.85

        # 5. Full Address Extraction
        address_parts = []
        capturing = False

        for line in cleaned_lines:
            upper = line.upper()
            if "QR CODE" in upper or "PHOTO" in upper or "HELP: 1947" in upper or "UIDAI.GOV.IN" in upper:
                continue

            # Start of address
            if re.search(r"Address|पता|C/O|S/O|D/O|W/O|SIC|DIC|WIC", line, re.IGNORECASE):
                capturing = True
                clean_l = re.sub(r"^(?:Address|पता)[\s:]*", "", line, flags=re.IGNORECASE).strip()
                if clean_l and not is_header_noise(clean_l):
                    address_parts.append(clean_l)
                continue

            if capturing:
                if is_header_noise(line):
                    continue
                if re.search(r"1947|uidai|help@|www\.|unique identification", line, re.IGNORECASE):
                    break
                # Skip standalone Aadhaar number line at bottom
                if re.search(r"^\d{4}\s\d{4}\s\d{4}$", line):
                    break
                address_parts.append(line)
                if PINCODE_REGEX.search(line):
                    break

        if address_parts:
            combined = ", ".join(address_parts)
            # Remove Care-Of line from beginning of address if present
            combined = re.sub(r"^(?:C/O|S/O|D/O|W/O|SIC|DIC|WIC|CIC)[^,]+,\s*", "", combined, flags=re.IGNORECASE).strip()
            # Remove redundant commas and clean whitespace
            combined = re.sub(r",\s*,+", ",", combined)
            combined = re.sub(r"\s+", " ", combined).strip()
            result["address"] = combined
            result["confidence_scores"]["address"] = 0.90

        return result
