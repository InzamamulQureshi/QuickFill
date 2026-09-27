"""
Aadhaar Card Parser for Quick Fill (QF).
Extracts fields from:
- Old physical Aadhaar letters & cards
- New UIDAI PVC Aadhaar Cards (with new disclaimers & masked numbers)
- e-Aadhaar PDFs & full document cutouts containing front & back in one
- Masked Aadhaar cards & Baal Aadhaar
"""
import re
from typing import Dict, Any, List, Optional
from .common import (
    INDIAN_STATES, PINCODE_REGEX, AADHAAR_REGEX, MASKED_AADHAAR_REGEX,
    clean_line, is_header_noise, format_aadhaar_number,
    extract_aadhaar_number, extract_virtual_id
)
from .date_util import calculate_age, normalize_date_string


class AadhaarParser:
    """Specialized extractor for UIDAI Aadhaar Cards across all formats."""

    @classmethod
    def extract_dob_and_age(cls, raw_text: str, lines: List[str]) -> Tuple[str, Dict[str, Any], float]:
        """Extracts standard DD/MM/YYYY date of birth and calculates age."""
        dob_patterns = [
            # 1. Standard DOB prefixes with full date
            r"(?:DOB|D\.?O\.?B|Date\s*of\s*Birth|जन्म\s*तिथि|जन्म\s*तारीख)[\s:/.-]*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{4})",
            # 2. Year of Birth prefixes (New PVC & elderly citizen cards)
            r"(?:Year\s*of\s*Birth|जन्म\s*वर्ष|YOB|Birth)[^0-9\n]*([1-2][0-9]{3})",
            # 3. YYYY-MM-DD format
            r"\b(19\d{2}|20[0-2]\d)[/.-](0?[1-9]|1[0-2])[/.-](0?[1-9]|[12]\d|3[01])\b",
            # 4. Standalone DD/MM/YYYY
            r"\b([0-3]?[0-9][/.-][0-1]?[0-9][/.-][1-2][0-9]{3})\b"
        ]

        for pat in dob_patterns:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                raw_dob = m.group(1)
                normalized = normalize_date_string(raw_dob)
                if normalized:
                    age_dict = calculate_age(normalized)
                    return normalized, age_dict, 0.95

        return "", {}, 0.0

    @classmethod
    def extract_gender(cls, raw_text: str) -> Tuple[str, float]:
        """Extracts Gender from English or Hindi labels."""
        if re.search(r"\b(FEMALE|WOMAN|महिला)\b", raw_text, re.IGNORECASE):
            return "Female", 0.95
        if re.search(r"\b(TRANSGENDER|ट्रांसजेंडर)\b", raw_text, re.IGNORECASE):
            return "Transgender", 0.95
        if re.search(r"\b(MALE|PURUSH|पुरुष)\b", raw_text, re.IGNORECASE):
            return "Male", 0.95
        return "", 0.0

    @classmethod
    def extract_name(cls, raw_text: str, lines: List[str]) -> Tuple[str, float]:
        """
        Extracts resident's name across old cards, new PVC cards, and e-Aadhaar.
        Filters out disclaimer text ('Aadhaar is a proof of identity...'), slogans,
        and Hindi lines.
        """
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]

        # Strategy 1: In e-Aadhaar letters, look for line after "To"
        for idx, line in enumerate(cleaned_lines):
            if line.strip().upper() in ["TO", "TO :", "TO:"]:
                if idx + 1 < len(cleaned_lines):
                    next_line = cleaned_lines[idx + 1]
                    if not is_header_noise(next_line) and re.match(r"^[A-Za-z\s.]{3,40}$", next_line):
                        words = [w for w in next_line.split() if len(w) > 1 and w.isalpha()]
                        if len(words) >= 1:
                            return " ".join(words).title(), 0.94

        # Strategy 2: Explicit "Name:" or "Name of Resident:" label
        name_label_match = re.search(r"(?:Name|Resident\s*Name)[\s:]*([A-Za-z\s.]{3,40})", raw_text, re.IGNORECASE)
        if name_label_match:
            candidate = name_label_match.group(1).strip()
            if not is_header_noise(candidate):
                words = [w for w in candidate.split() if len(w) > 1 and w.isalpha()]
                if 1 <= len(words) <= 4:
                    return " ".join(words).title(), 0.93

        # Strategy 3: Line immediately above DOB or Year of Birth
        dob_line_idx = -1
        for idx, line in enumerate(cleaned_lines):
            if re.search(r"DOB|Birth|जन्म|Year\s*of|[0-9]{2}/[0-9]{2}/[1-2][0-9]{3}", line, re.IGNORECASE):
                dob_line_idx = idx
                break

        if dob_line_idx > 0:
            # Walk backwards from DOB line
            for i in range(dob_line_idx - 1, -1, -1):
                line = cleaned_lines[i]
                if is_header_noise(line):
                    continue
                if re.search(r"\d", line):
                    continue
                # Skip Hindi-only or non-Latin lines
                if not re.search(r"[A-Za-z]", line):
                    continue
                if re.match(r"^[A-Za-z\s.]{3,45}$", line):
                    words = [w for w in line.split() if len(w) > 1 and w.isalpha()]
                    if len(words) >= 1:
                        return " ".join(words).title(), 0.92

        # Strategy 4: Search for valid candidate lines in upper third of document
        for line in cleaned_lines[:15]:
            if is_header_noise(line):
                continue
            if re.search(r"\d", line):
                continue
            if not re.search(r"[A-Za-z]", line):
                continue
            if re.match(r"^[A-Z][a-zA-Z\s.]{3,35}$", line):
                words = [w for w in line.split() if len(w) > 1 and w.isalpha()]
                if 1 <= len(words) <= 4:
                    return " ".join(words).title(), 0.85

        return "", 0.0

    @classmethod
    def extract_father_spouse(cls, raw_text: str, lines: List[str]) -> Tuple[str, float]:
        """
        Extracts Father, Spouse, or Guardian name from Care-of (C/O, S/O, D/O, W/O, H/O).
        Handles both old 'S/O: ...' and new UIDAI 'Address: C/O: ...' formats.
        """
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]

        prefix_pattern = re.compile(
            r"(?:Address|पता)[\s:]*(?:C/O|S/O|D/O|W/O|H/O|SIC|DIC|WIC|CIC|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of|Husband\s*of|आत्मज|पुत्र|पुत्री|पत्नी)[\s:.)-]*"
            r"|^(?:C/O|S/O|D/O|W/O|H/O|SIC|DIC|WIC|CIC|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of|Husband\s*of|SO|DO|WO|CO|आत्मज|पुत्र|पुत्री|पत्नी)[\s:.)-]*",
            re.IGNORECASE
        )

        for line in cleaned_lines:
            m = prefix_pattern.search(line)
            if m:
                candidate = line[m.end():].strip()
                # Split at address delimiters if present on same line
                for delim in [",", " -", ";", "Flat", "H.No", "House", "Plot", "Ward", "Village", "Post", "Dist", "Near", "Street"]:
                    if delim.lower() in candidate.lower():
                        pos = candidate.lower().find(delim.lower())
                        candidate = candidate[:pos].strip()

                candidate = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z]+$", "", candidate).strip()
                words = [w for w in candidate.split() if w.isalpha() and len(w) > 1]
                if 1 <= len(words) <= 4:
                    return " ".join(words).title(), 0.94

        # Fallback regex across entire raw_text
        m_raw = re.search(
            r"(?:C/O|S/O|D/O|W/O|H/O|SIC|DIC|WIC|CIC|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of)[\s:.)-]*"
            r"([A-Za-z\s.]+?)(?:,|\n|$|\d|Flat|H\.No|House|Plot|Ward|Village|Post|Dist|Near)",
            raw_text, re.IGNORECASE
        )
        if m_raw:
            candidate = m_raw.group(1).strip()
            words = [w for w in candidate.split() if w.isalpha() and len(w) > 1]
            if 1 <= len(words) <= 4:
                return " ".join(words).title(), 0.88

        return "", 0.0

    @classmethod
    def extract_address_block(cls, raw_text: str, lines: List[str]) -> Tuple[str, str, str, float]:
        """
        Extracts Residential Address, PIN code, and State.
        Cleanly truncates helpline/UIDAI footer information and dates.
        Returns: (address_str, pincode_str, state_str, confidence)
        """
        # 1. Pincode
        pincode = ""
        pin_m = PINCODE_REGEX.search(raw_text)
        if pin_m:
            pincode = pin_m.group(1).replace(" ", "")

        # 2. State
        state = ""
        for st in INDIAN_STATES:
            if re.search(rf"\b{re.escape(st)}\b", raw_text, re.IGNORECASE):
                state = st
                break

        # 3. Address Lines
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]
        address_parts = []
        capturing = False

        for line in cleaned_lines:
            upper = line.upper()

            # Ignore noise lines
            if "QR CODE" in upper or "PHOTO" in upper or "HELP: 1947" in upper or "1947" == upper:
                continue

            # Start of address
            if re.search(r"\b(?:Address|पता)\b", line, re.IGNORECASE) or re.search(r"\b(?:C/O|S/O|D/O|W/O)\b", line, re.IGNORECASE):
                capturing = True
                clean_l = re.sub(r"^(?:Address|पता)[\s:]*", "", line, flags=re.IGNORECASE).strip()
                if clean_l and not is_header_noise(clean_l):
                    # Check if line contains pincode
                    if PINCODE_REGEX.search(clean_l):
                        p_match = PINCODE_REGEX.search(clean_l)
                        clean_l = clean_l[:p_match.end()].strip()
                        address_parts.append(clean_l)
                        break
                    address_parts.append(clean_l)
                continue

            if capturing:
                if is_header_noise(line):
                    continue
                # Stop conditions: UIDAI footer, helplines, issue/print dates
                if re.search(r"1947|uidai|help@|www\.|unique identification|issue date|print date|download date", line, re.IGNORECASE):
                    break
                # Stop if standalone Aadhaar or VID line
                if re.search(r"^\d{4}\s\d{4}\s\d{4}$", line) or re.search(r"^[X*•x]{4}\s[X*•x]{4}", line) or "VID" in line.upper():
                    break

                # If this line has the pincode, capture up to pincode and stop
                if PINCODE_REGEX.search(line):
                    p_match = PINCODE_REGEX.search(line)
                    truncated_line = line[:p_match.end()].strip()
                    if truncated_line:
                        address_parts.append(truncated_line)
                    break

                address_parts.append(line)

        address = ""
        if address_parts:
            combined = ", ".join(address_parts)
            # Remove Care-Of line from beginning of address if present
            combined = re.sub(
                r"^(?:C/O|S/O|D/O|W/O|H/O|SIC|DIC|WIC|CIC|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of)[\s:.)-]*[^,]+,\s*",
                "", combined, flags=re.IGNORECASE
            ).strip()
            # Clean up double commas and whitespace
            combined = re.sub(r",\s*,+", ",", combined)
            combined = re.sub(r"\s+", " ", combined).strip()
            address = combined

        conf = 0.90 if address else 0.0
        return address, pincode, state, conf

    @classmethod
    def parse_front(cls, raw_text: str, lines: List[str]) -> Dict[str, Any]:
        """Extracts fields from front side of Aadhaar card (physical or PVC)."""
        result = {
            "card_type": "Aadhaar Front",
            "name": "",
            "dob": "",
            "age": {},
            "gender": "",
            "aadhaar_number": "",
            "virtual_id": "",
            "father_spouse_name": "",
            "address": "",
            "pincode": "",
            "state": "",
            "confidence_scores": {}
        }

        # 1. Aadhaar Number & VID
        aadhaar_num = extract_aadhaar_number(raw_text)
        if aadhaar_num:
            result["aadhaar_number"] = format_aadhaar_number(aadhaar_num)
            result["confidence_scores"]["aadhaar_number"] = 0.95

        vid = extract_virtual_id(raw_text)
        if vid:
            result["virtual_id"] = vid

        # 2. DOB and Age
        dob, age_dict, dob_conf = cls.extract_dob_and_age(raw_text, lines)
        if dob:
            result["dob"] = dob
            result["age"] = age_dict
            result["confidence_scores"]["dob"] = dob_conf
            result["confidence_scores"]["age"] = dob_conf

        # 3. Gender
        gender, gender_conf = cls.extract_gender(raw_text)
        if gender:
            result["gender"] = gender
            result["confidence_scores"]["gender"] = gender_conf

        # 4. Name
        name, name_conf = cls.extract_name(raw_text, lines)
        if name:
            result["name"] = name
            result["confidence_scores"]["name"] = name_conf

        return result

    @classmethod
    def parse_back(cls, raw_text: str, lines: List[str]) -> Dict[str, Any]:
        """Extracts fields from back side of Aadhaar card (physical or PVC)."""
        result = {
            "card_type": "Aadhaar Back",
            "name": "",
            "dob": "",
            "age": {},
            "gender": "",
            "aadhaar_number": "",
            "virtual_id": "",
            "father_spouse_name": "",
            "address": "",
            "pincode": "",
            "state": "",
            "confidence_scores": {}
        }

        # 1. Aadhaar Number (sometimes printed on back)
        aadhaar_num = extract_aadhaar_number(raw_text)
        if aadhaar_num:
            result["aadhaar_number"] = format_aadhaar_number(aadhaar_num)

        # 2. Father / Spouse Name
        father_spouse, fs_conf = cls.extract_father_spouse(raw_text, lines)
        if father_spouse:
            result["father_spouse_name"] = father_spouse
            result["confidence_scores"]["father_spouse_name"] = fs_conf

        # 3. Address, Pincode, State
        address, pincode, state, addr_conf = cls.extract_address_block(raw_text, lines)
        if address:
            result["address"] = address
            result["confidence_scores"]["address"] = addr_conf
        if pincode:
            result["pincode"] = pincode
            result["confidence_scores"]["pincode"] = 0.95
        if state:
            result["state"] = state
            result["confidence_scores"]["state"] = 0.90

        return result

    @classmethod
    def parse_combined(cls, raw_text: str, lines: List[str]) -> Dict[str, Any]:
        """
        Extracts ALL fields simultaneously for e-Aadhaar PDFs, Aadhaar letters,
        and combined front+back image scans.
        """
        result = {
            "card_type": "e-Aadhaar (Full Card)",
            "name": "",
            "dob": "",
            "age": {},
            "gender": "",
            "aadhaar_number": "",
            "virtual_id": "",
            "father_spouse_name": "",
            "address": "",
            "pincode": "",
            "state": "",
            "confidence_scores": {}
        }

        # 1. Aadhaar Number & VID
        aadhaar_num = extract_aadhaar_number(raw_text)
        if aadhaar_num:
            result["aadhaar_number"] = format_aadhaar_number(aadhaar_num)
            result["confidence_scores"]["aadhaar_number"] = 0.95

        vid = extract_virtual_id(raw_text)
        if vid:
            result["virtual_id"] = vid

        # 2. DOB and Age
        dob, age_dict, dob_conf = cls.extract_dob_and_age(raw_text, lines)
        if dob:
            result["dob"] = dob
            result["age"] = age_dict
            result["confidence_scores"]["dob"] = dob_conf
            result["confidence_scores"]["age"] = dob_conf

        # 3. Gender
        gender, gender_conf = cls.extract_gender(raw_text)
        if gender:
            result["gender"] = gender
            result["confidence_scores"]["gender"] = gender_conf

        # 4. Name
        name, name_conf = cls.extract_name(raw_text, lines)
        if name:
            result["name"] = name
            result["confidence_scores"]["name"] = name_conf

        # 5. Father / Spouse Name
        father_spouse, fs_conf = cls.extract_father_spouse(raw_text, lines)
        if father_spouse:
            result["father_spouse_name"] = father_spouse
            result["confidence_scores"]["father_spouse_name"] = fs_conf

        # 6. Address, Pincode, State
        address, pincode, state, addr_conf = cls.extract_address_block(raw_text, lines)
        if address:
            result["address"] = address
            result["confidence_scores"]["address"] = addr_conf
        if pincode:
            result["pincode"] = pincode
            result["confidence_scores"]["pincode"] = 0.95
        if state:
            result["state"] = state
            result["confidence_scores"]["state"] = 0.90

        return result
