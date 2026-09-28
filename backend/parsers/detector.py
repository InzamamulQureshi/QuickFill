"""
Document Type Detector and Dispatcher for Quick Fill (QF).
Determines whether an image or document is:
- e-Aadhaar (Full Document with Front & Back together)
- Aadhaar Front (Physical Card or PVC Front)
- Aadhaar Back (Physical Card or PVC Back)
- PAN Card
"""
import re
from typing import Dict, Any, List, Tuple
from .common import (
    PAN_REGEX, AADHAAR_REGEX, MASKED_AADHAAR_REGEX, PINCODE_REGEX,
    extract_aadhaar_number
)
from .aadhaar_parser import AadhaarParser
from .pan_parser import PanParser


class DocumentDetector:
    """Classifies Indian Identity Document type and dispatches to appropriate parser."""

    @staticmethod
    def detect_type(raw_text: str) -> str:
        """
        Determines the document type from keywords and pattern signatures:
        Returns: 'aadhaar_combined' | 'aadhaar_front' | 'aadhaar_back' | 'pan_card' | 'unknown'
        """
        text_upper = raw_text.upper()

        # 1. Check for PAN Card indicators
        has_pan_number = bool(PAN_REGEX.search(raw_text))
        has_uidai_authority = any(h in text_upper for h in [
            "UNIQUE IDENTIFICATION", "AUTHORITY OF INDIA", "MERA AADHAAR", "UIDAI",
            "ENROLMENT NO", "विशिष्ट पहचान", "नोंदणी क्रमांक", "माझे आधार"
        ])

        # If a valid PAN number is present and document does NOT have UIDAI authority headers:
        # It is definitively a PAN Card (e-PAN PDFs often include applicant's linked Aadhaar)
        if has_pan_number and not has_uidai_authority:
            return "pan_card"

        pan_indicators = [
            "INCOME TAX", "PERMANENT ACCOUNT", "INCOMETAX",
            "GOVT. OF INDIA", "FATHER'S NAME"
        ]
        pan_score = sum(1 for ind in pan_indicators if ind in text_upper)
        if has_pan_number:
            pan_score += 4

        # 2. Check for Aadhaar Front indicators
        front_indicators = [
            "DOB", "DATE OF BIRTH", "YEAR OF BIRTH", "जन्म तिथि", "जन्म वर्ष",
            "MALE", "FEMALE", "TRANSGENDER", "पुरुष", "महिला",
            "UNIQUE IDENTIFICATION", "AUTHORITY OF INDIA", "GOVERNMENT OF INDIA", "BHARAT SARKAR"
        ]
        front_score = sum(1 for ind in front_indicators if ind in text_upper)
        if extract_aadhaar_number(raw_text):
            front_score += 3
        if re.search(r"VID\s*:", text_upper):
            front_score += 2

        # 3. Check for Aadhaar Back indicators
        back_indicators = [
            "ADDRESS", "पता", "C/O", "S/O", "W/O", "D/O", "H/O",
            "SIC", "DIC", "WIC", "CIC", "1947", "HELP@UIDAI"
        ]
        back_score = sum(1 for ind in back_indicators if ind in text_upper)
        if PINCODE_REGEX.search(raw_text):
            back_score += 3

        # If PAN indicators strongly dominate, it's a PAN Card
        if pan_score >= 4 and pan_score > front_score:
            return "pan_card"

        # 4. Check for Combined / e-Aadhaar Document
        # An e-Aadhaar contains BOTH front elements (DOB/Gender/Name) AND back elements (Address/Pincode/Care-of)
        has_dob_or_gender = bool(
            re.search(r"DOB|Birth|जन्म|MALE|FEMALE|पुरुष|महिला", text_upper)
        )
        has_address_or_pin = bool(
            PINCODE_REGEX.search(raw_text) and re.search(r"ADDRESS|पता|C/O|S/O|W/O|D/O", text_upper)
        )

        if has_dob_or_gender and has_address_or_pin:
            return "aadhaar_combined"

        if has_dob_or_gender and front_score >= 3 and back_score >= 3:
            return "aadhaar_combined"

        # 5. Front vs Back winner
        if back_score > front_score and back_score >= 2:
            return "aadhaar_back"
        elif back_score >= 2 and not has_dob_or_gender:
            return "aadhaar_back"
        elif front_score >= 2 and has_dob_or_gender:
            return "aadhaar_front"
        elif front_score >= 2:
            return "aadhaar_front"

        # Fallbacks
        if PAN_REGEX.search(raw_text):
            return "pan_card"
        if PINCODE_REGEX.search(raw_text) and ("ADDRESS" in text_upper or "पता" in text_upper):
            return "aadhaar_back"
        if "MALE" in text_upper or "FEMALE" in text_upper or "DOB" in text_upper:
            return "aadhaar_front"

        return "unknown"

    @classmethod
    def parse_document(cls, raw_text: str, lines: List[str], doc_hint: str = "auto") -> Dict[str, Any]:
        """
        Parses document text with either auto-detection or user-selected hint.
        doc_hint options: 'auto', 'aadhaar_combined', 'aadhaar_front', 'aadhaar_back', 'pan'
        """
        target_type = doc_hint.lower() if doc_hint and doc_hint != "auto" else cls.detect_type(raw_text)

        if target_type in ("pan", "pan_card"):
            res = PanParser.parse(raw_text, lines)
            res["detected_type"] = "PAN Card"
            return res
        elif target_type in ("aadhaar_combined", "eaadhaar", "e_aadhaar", "e-aadhaar", "aadhaar_full"):
            res = AadhaarParser.parse_combined(raw_text, lines)
            res["detected_type"] = "e-Aadhaar (Full Card)"
            return res
        elif target_type in ("aadhaar_back", "aadhar_back"):
            res = AadhaarParser.parse_back(raw_text, lines)
            res["detected_type"] = "Aadhaar Back"
            return res
        elif target_type in ("aadhaar_front", "aadhar_front"):
            res = AadhaarParser.parse_front(raw_text, lines)
            res["detected_type"] = "Aadhaar Front"
            return res
        else:
            # When unknown, evaluate combined, front, back, and pan candidates
            combined_res = AadhaarParser.parse_combined(raw_text, lines)
            pan_res = PanParser.parse(raw_text, lines)

            # Check how many fields were successfully populated
            combined_count = sum(1 for v in [
                combined_res["name"], combined_res["dob"], combined_res["gender"],
                combined_res["aadhaar_number"], combined_res["address"], combined_res["pincode"],
                combined_res["father_spouse_name"]
            ] if v)

            pan_count = sum(1 for v in [
                pan_res["pan_number"], pan_res["name"], pan_res["father_spouse_name"], pan_res["dob"]
            ] if v)

            if pan_count >= 2 and pan_count > combined_count:
                pan_res["detected_type"] = "PAN Card (Inferred)"
                return pan_res
            elif combined_count >= 3:
                # If both front and back fields are populated
                if combined_res["address"] and (combined_res["dob"] or combined_res["gender"]):
                    combined_res["detected_type"] = "e-Aadhaar (Full Card)"
                elif combined_res["address"]:
                    combined_res["detected_type"] = "Aadhaar Back (Inferred)"
                else:
                    combined_res["detected_type"] = "Aadhaar Front (Inferred)"
                return combined_res
            else:
                combined_res["detected_type"] = "Aadhaar Document"
                return combined_res
