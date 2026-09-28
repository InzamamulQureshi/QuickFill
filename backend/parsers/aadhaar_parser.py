"""
Aadhaar Card Parser for Quick Fill (QF).
Extracts fields from:
- Old physical Aadhaar letters & cards
- New UIDAI PVC Aadhaar Cards (with new disclaimers & masked numbers)
- e-Aadhaar PDFs & full document cutouts containing front & back in one
- Masked Aadhaar cards & Baal Aadhaar
"""
from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple
from .common import (
    INDIAN_STATES, PINCODE_REGEX, AADHAAR_REGEX, MASKED_AADHAAR_REGEX,
    clean_line, is_header_noise, is_instruction_noise, is_valid_person_name,
    format_aadhaar_number, extract_aadhaar_number, extract_virtual_id,
    FORBIDDEN_NAME_WORDS, get_state_from_pincode
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
        instruction boilerplate, and noise words.
        """
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]

        # Strategy 1: Look for line immediately after To/Po in e-Aadhaar letter section (highest precision)
        for idx, line in enumerate(cleaned_lines):
            if re.match(r"^(?:To|Po|Io|T0)[\s:.]*$", line.strip(), re.IGNORECASE):
                for offset in range(1, 4):
                    if idx + offset < len(cleaned_lines):
                        cand = cleaned_lines[idx + offset]
                        if is_instruction_noise(cand) or is_header_noise(cand):
                            continue
                        cand_clean = re.sub(r"^[\d\s.,|:;~*\"'#/-]+", "", cand).strip()
                        cand_name = re.split(r"\b(?:Address|पता|D/O|S/O|W/O|C/O)\b|[\"|~]", cand_clean)[0].strip()
                        if is_valid_person_name(cand_name):
                            words = [w for w in re.findall(r"[A-Za-z]+", cand_name) if len(w) > 1 and w.upper() not in FORBIDDEN_NAME_WORDS]
                            if len(words) >= 2:
                                return " ".join(words).title(), 0.96

        # Strategy 2: Real DOB line (must contain an actual date or 4-digit year, NOT disclaimer)
        dob_line_idx = -1
        for idx, line in enumerate(cleaned_lines):
            if is_instruction_noise(line):
                continue
            # Avoid matching disclaimer: "date of birth (DOB). DOB is based on..."
            if "PROOF OF DOB" in line.upper() or "DATE OF BIRTH (DOB)" in line.upper() or "NOT OF CITIZENSHIP" in line.upper():
                continue
            if re.search(r"\b([0-3]?[0-9][/.-][0-1]?[0-9][/.-][1-2][0-9]{3})\b", line) or re.search(r"(?:DOB|Birth|जन्म)[\s:/.-]*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{4})", line, re.IGNORECASE):
                dob_line_idx = idx
                break

        if dob_line_idx > 0:
            for i in range(dob_line_idx - 1, max(-1, dob_line_idx - 4), -1):
                line = cleaned_lines[i]
                if is_instruction_noise(line) or is_header_noise(line):
                    continue
                cand_clean = re.sub(r"^[\d\s.,|:;~*\"'#/-]+", "", line).strip()
                cand_clean = re.split(r"\b(?:Address|पता|D/O|S/O|W/O|C/O)\b|[\"|~]", cand_clean)[0].strip()
                if is_valid_person_name(cand_clean):
                    words = [w for w in re.findall(r"[A-Za-z]+", cand_clean) if len(w) > 1 and w.upper() not in FORBIDDEN_NAME_WORDS]
                    if len(words) >= 2:
                        return " ".join(words).title(), 0.94

        # Strategy 3: Explicit Name: label
        name_label_match = re.search(r"(?:Name|Resident\s*Name)[\s:]*([A-Za-z\s.]{3,40})", raw_text, re.IGNORECASE)
        if name_label_match:
            candidate = name_label_match.group(1).strip()
            if is_valid_person_name(candidate):
                words = [w for w in re.findall(r"[A-Za-z]+", candidate) if len(w) > 1 and w.upper() not in FORBIDDEN_NAME_WORDS]
                if len(words) >= 2:
                    return " ".join(words).title(), 0.93

        # Strategy 4: Fallback search in upper lines
        for line in cleaned_lines[:25]:
            if is_instruction_noise(line) or is_header_noise(line):
                continue
            cand_clean = re.sub(r"^[\d\s.,|:;~*\"'#/-]+", "", line).strip()
            cand_clean = re.split(r"\b(?:Address|पता|D/O|S/O|W/O|C/O)\b|[\"|~]", cand_clean)[0].strip()
            if is_valid_person_name(cand_clean):
                words = [w for w in re.findall(r"[A-Za-z]+", cand_clean) if len(w) > 1 and w.upper() not in FORBIDDEN_NAME_WORDS]
                if len(words) >= 2:
                    return " ".join(words).title(), 0.85

        return "", 0.0

    @classmethod
    def extract_father_spouse(cls, raw_text: str, lines: List[str]) -> Tuple[str, float]:
        """
        Extracts Father, Spouse, or Guardian name from Care-of (C/O, S/O, D/O, W/O, H/O).
        Strictly enforces word boundaries to avoid matching 'Download Date', 'South', etc.
        """
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]

        prefix_pattern = re.compile(
            r"(?:Address|पता)[\s:]*(?:C/O|S/O|D/O|W/O|H/O|SIC|DIC|WIC|CIC|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of|Husband\s*of|आत्मज|पुत्र|पुत्री|पत्नी)[\s:.)-]+(?=[A-Za-z])"
            r"|(?:\b(?:C/O|S/O|D/O|W/O|H/O|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of|Husband\s*of|आत्मज|पुत्र|पुत्री|पत्नी)\b[\s:.)-]+)"
            r"|(?:\b(?:SO|DO|WO|CO|HO)\b[\s:.-]+(?=[A-Za-z]))"
            r"|(?:\"?1/[80o]\s*[JjDdCcSs][Oo][\s:.-]+)",
            re.IGNORECASE
        )

        for line in cleaned_lines:
            if is_instruction_noise(line):
                continue
            m = prefix_pattern.search(line)
            if m:
                candidate = line[m.end():].strip()
                # Split at address delimiters if present on same line
                for delim in [",", " -", ";", "Flat", "H.No", "House", "Plot", "Ward", "Village", "Post", "Dist", "Near", "Street", "Floor"]:
                    if delim.lower() in candidate.lower():
                        pos = candidate.lower().find(delim.lower())
                        candidate = candidate[:pos].strip()

                candidate = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z]+$", "", candidate).strip()
                if is_valid_person_name(candidate):
                    words = [w for w in candidate.split() if w.isalpha() and len(w) > 1]
                    return " ".join(words).title(), 0.94

        # Fallback regex across entire raw_text
        m_raw = re.search(
            r"(?:\b(?:C/O|S/O|D/O|W/O|H/O|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of)\b[\s:.)-]+)"
            r"([A-Za-z\s.]+?)(?:,|\n|$|\d|Flat|H\.No|House|Plot|Ward|Village|Post|Dist|Near)",
            raw_text, re.IGNORECASE
        )
        if m_raw:
            candidate = m_raw.group(1).strip()
            if is_valid_person_name(candidate):
                words = [w for w in candidate.split() if w.isalpha() and len(w) > 1]
                return " ".join(words).title(), 0.88

        return "", 0.0

    @classmethod
    def _clean_address_line(cls, clean_l: str) -> str:
        """Strips horizontal column bleed (DOB, gender, card headers) from address lines."""
        if not clean_l:
            return ""

        # If line contains DOB on left and Address on right
        if re.search(r"DOB|Date of Birth", clean_l, re.IGNORECASE):
            m = re.search(r"(?:\"?1/[80o]\s*[JjDdCcSs][Oo][\s:.-]+|D/O|S/O|W/O|C/O|Address)[\s:.-]*", clean_l, re.IGNORECASE)
            if m:
                clean_l = clean_l[m.end():].strip()
            else:
                m_kw = re.search(r"\b(?:Floor|Flat|House|H\.No|Plot|Nagar|Marg|Bldg|Road)\b", clean_l, re.IGNORECASE)
                if m_kw:
                    clean_l = clean_l[m_kw.start():].strip()
                else:
                    return ""

        # If line contains Gender on left and Address on right
        if re.search(r"\b(?:Female|Male|Transgender)\b", clean_l, re.IGNORECASE):
            clean_l = re.sub(
                r"^.*?\b(?:Female|Male|Transgender)(?:\s*/\s*[A-Za-z]+)?\b\s*[=\s:]*",
                "", clean_l, flags=re.IGNORECASE
            )

        # Strip leading stray single chars, numbers, and symbols: e.g. 'd $ ', '8 3 ', '3 '
        clean_l = re.sub(r"^(?:[a-zA-Z0-9]\s*[$|•*~=+\-#]+\s*)+", "", clean_l)
        clean_l = re.sub(r"^(?:\d\s+)+(?=[A-Za-z])", "", clean_l)

        # Normalize OCR misreads of slashes in flat/building numbers (e.g. A}14 -> A/14)
        clean_l = re.sub(r"([A-Za-z0-9])[\}\{]([A-Za-z0-9])", r"\1/\2", clean_l)

        # Strip leading / trailing OCR artifacts (do not strip trailing digits so pincodes and house numbers are preserved)
        clean_l = re.sub(r"^[^\w]+|[^\w)]+$", "", clean_l).strip()
        return clean_l

    @classmethod
    def extract_address_block(cls, raw_text: str, lines: List[str]) -> Tuple[str, str, str, float]:
        """
        Extracts Residential Address, PIN code, and State.
        Strictly prevents capturing UIDAI instruction boilerplate tables.
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

        if not state and pincode:
            state = get_state_from_pincode(pincode)

        # 3. Address Lines
        cleaned_lines = [clean_line(l) for l in lines if clean_line(l)]

        # Check if document has an explicit Address: / पता: label
        has_explicit_address_label = any(
            re.search(r"\b(?:Address|पता)\b[\s:]*", l, re.IGNORECASE)
            for l in cleaned_lines if not is_instruction_noise(l)
        )

        address_parts = []
        capturing = False

        for line in cleaned_lines:
            if is_instruction_noise(line):
                continue

            upper = line.upper()
            if "QR CODE" in upper or "PHOTO" in upper or "1947" in upper or "SIGNATURE" in upper:
                continue

            # Look for explicit Address:
            addr_match = re.search(r"(?:^|[:\s|])(?:Address|पता)[\s:]*", line, re.IGNORECASE)
            co_strict = None if has_explicit_address_label else re.search(r"(?:^|[:\s|])(?:C/O|S/O|D/O|W/O|H/O)[\s:.)-]+[A-Za-z]+", line, re.IGNORECASE)
            ocr_co = None if has_explicit_address_label else re.search(r"(?:\"?1/[80o]\s*[JjDdCcSs][Oo][\s:.-]+[A-Za-z]+)", line, re.IGNORECASE)

            if not capturing and (addr_match or co_strict or ocr_co):
                clean_l = line
                if addr_match:
                    clean_l = clean_l[addr_match.end():].strip()
                elif ocr_co:
                    clean_l = clean_l[ocr_co.end():].strip()
                elif co_strict:
                    clean_l = clean_l[co_strict.end():].strip()

                clean_l = cls._clean_address_line(clean_l)
                if clean_l and not is_instruction_noise(clean_l) and not is_header_noise(clean_l):
                    capturing = True
                    if PINCODE_REGEX.search(clean_l):
                        p_match = PINCODE_REGEX.search(clean_l)
                        clean_l = clean_l[:p_match.end()].strip()
                        address_parts.append(clean_l)
                        break
                    address_parts.append(clean_l)
                    continue
                elif addr_match:
                    capturing = True
                    continue

            if capturing:
                if is_instruction_noise(line):
                    continue
                # Stop conditions: UIDAI footer, helplines, issue/print dates
                if re.search(r"1947|uidai|help@|www\.|unique identification|issue date|print date|download date", line, re.IGNORECASE):
                    break
                # Stop if standalone Aadhaar or VID line
                if re.search(r"^\d{4}\s\d{4}\s\d{4}$", line) or re.search(r"^[X*•x]{4}\s[X*•x]{4}", line) or "VID" in line.upper():
                    break

                clean_l = cls._clean_address_line(line)
                if is_header_noise(clean_l) or "SIGNATURE" in clean_l.upper():
                    break

                if PINCODE_REGEX.search(clean_l):
                    p_match = PINCODE_REGEX.search(clean_l)
                    truncated = clean_l[:p_match.end()].strip()
                    if truncated:
                        address_parts.append(truncated)
                    break

                if clean_l:
                    address_parts.append(clean_l)

        # Check if letter address exists in e-Aadhaar documents
        letter_parts = []
        for idx, line in enumerate(cleaned_lines):
            if re.search(r"Enrolment|Enrollment|नोंदणी|To\b", line, re.IGNORECASE):
                for offset in range(1, 10):
                    if idx + offset < len(cleaned_lines):
                        cand = cleaned_lines[idx + offset]
                        if re.search(r"Signature|Aadhaar No|VID\b|DOB|Birth|Male|Female|महिला|पुरुष|INFORMATION|सूचना", cand, re.IGNORECASE):
                            break
                        if is_instruction_noise(cand) or is_header_noise(cand):
                            continue
                        if re.match(r"^\d{10}$", cand.strip()):
                            continue
                        if offset <= 2 and is_valid_person_name(cand):
                            continue
                        clean_l = cls._clean_address_line(cand)
                        if clean_l:
                            letter_parts.append(clean_l)
                            if PINCODE_REGEX.search(clean_l):
                                break
                if any(PINCODE_REGEX.search(p) for p in letter_parts):
                    break

        # If no address captured yet, or if card address is corrupted/noisy (&, ;) while letter address is clean
        if not address_parts:
            if letter_parts:
                address_parts = letter_parts
        elif letter_parts and any(PINCODE_REGEX.search(p) for p in letter_parts):
            card_addr_str = " ".join(address_parts)
            letter_addr_str = " ".join(letter_parts)
            has_letter_state = any(st.lower() in letter_addr_str.lower() for st in INDIAN_STATES)
            has_card_state = any(st.lower() in card_addr_str.lower() for st in INDIAN_STATES)
            has_card_symbols = bool(re.search(r"[&;~*^$]", card_addr_str))
            if (not has_card_state and has_letter_state) or (has_card_symbols and not re.search(r"[&;~*^$]", letter_addr_str)):
                address_parts = letter_parts

        address = ""
        if address_parts:
            combined = ", ".join(address_parts)
            # Remove Care-Of line or guardian from beginning of address if present
            combined = re.sub(
                r"^(?:C/O|S/O|D/O|W/O|H/O|SIC|DIC|WIC|CIC|Care\s*of|Son\s*of|Daughter\s*of|Wife\s*of)[\s:.)-]*[^,]+,\s*",
                "", combined, flags=re.IGNORECASE
            ).strip()
            # If line starts with residual guardian name words followed by a comma
            combined = re.sub(r"^[A-Za-z\s]+,\s*(?=(?:Flat|H\.No|House|Plot|Ward|Village|Post|Dist|Near|Street|Floor|Bldg|Bunglow|[A-Z0-9/]+(?:\s|/|-)))", "", combined).strip()
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
            if father_spouse:
                address = re.sub(r"^(?:" + re.escape(father_spouse) + r"|" + re.escape(father_spouse.split()[-1]) + r")[\s,.-]*", "", address, flags=re.IGNORECASE).strip()
            result["address"] = address
            result["confidence_scores"]["address"] = addr_conf
        if pincode:
            result["pincode"] = pincode
            result["confidence_scores"]["pincode"] = 0.95
        if state:
            result["state"] = state
            result["confidence_scores"]["state"] = 0.90

        return result
