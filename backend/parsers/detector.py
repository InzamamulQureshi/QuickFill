"""
Document Type Detector and Dispatcher for Quick Fill (QF).
Determines whether an image is Aadhaar Front, Aadhaar Back, or PAN Card.
"""
import re
from typing import Dict, Any, List, Tuple
from .common import PAN_REGEX, AADHAAR_REGEX, PINCODE_REGEX
from .aadhaar_parser import AadhaarParser
from .pan_parser import PanParser


class DocumentDetector:
    """Classifies Indian Identity Document type and dispatches to appropriate parser."""

    @staticmethod
    def detect_type(raw_text: str) -> str:
        """
        Determines the card type from keywords and pattern signatures:
        Returns: 'aadhaar_front' | 'aadhaar_back' | 'pan_card' | 'unknown'
        """
        text_upper = raw_text.upper()

        # Check for PAN Card indicators
        pan_indicators = [
            "INCOME TAX", "PERMANENT ACCOUNT", "INCOMETAX",
            "GOVT. OF INDIA", "FATHER'S NAME"
        ]
        pan_score = sum(1 for ind in pan_indicators if ind in text_upper)
        if PAN_REGEX.search(raw_text):
            pan_score += 3

        # Check for Aadhaar Back indicators
        back_indicators = [
            "ADDRESS", "पता", "C/O", "S/O", "W/O", "D/O",
            "SIC", "HELP@UIDAI", "WWW.UIDAI.GOV.IN", "1947", "ENROLMENT"
        ]
        back_score = sum(1 for ind in back_indicators if ind in text_upper)
        if PINCODE_REGEX.search(raw_text):
            back_score += 2

        # Check for Aadhaar Front indicators
        front_indicators = [
            "UNIQUE IDENTIFICATION", "AUTHORITY OF INDIA", "DOB",
            "YEAR OF BIRTH", "MALE", "FEMALE", "TRANSGENDER", "GOVERNMENT OF INDIA"
        ]
        front_score = sum(1 for ind in front_indicators if ind in text_upper)
        if AADHAAR_REGEX.search(raw_text):
            front_score += 2

        # Determine winner
        scores = {
            "pan_card": pan_score,
            "aadhaar_back": back_score,
            "aadhaar_front": front_score
        }

        best_type = max(scores, key=scores.get)
        if scores[best_type] >= 2:
            return best_type

        # Fallback heuristic
        if PAN_REGEX.search(raw_text):
            return "pan_card"
        if PINCODE_REGEX.search(raw_text) and ("ADDRESS" in text_upper or "C/O" in text_upper or "S/O" in text_upper):
            return "aadhaar_back"
        if "MALE" in text_upper or "FEMALE" in text_upper or "DOB" in text_upper:
            return "aadhaar_front"

        return "unknown"

    @classmethod
    def parse_document(cls, raw_text: str, lines: List[str], doc_hint: str = "auto") -> Dict[str, Any]:
        """
        Parses document text with either auto-detection or user-selected hint.
        doc_hint options: 'auto', 'aadhaar_front', 'aadhaar_back', 'pan'
        """
        target_type = doc_hint.lower() if doc_hint and doc_hint != "auto" else cls.detect_type(raw_text)

        if target_type in ("pan", "pan_card"):
            res = PanParser.parse(raw_text, lines)
            res["detected_type"] = "PAN Card"
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
            # When unknown, try both Aadhaar front and back heuristic merging
            front_res = AadhaarParser.parse_front(raw_text, lines)
            back_res = AadhaarParser.parse_back(raw_text, lines)
            pan_res = PanParser.parse(raw_text, lines)

            # Pick whichever parsed the most fields
            front_count = sum(1 for v in [front_res["name"], front_res["dob"], front_res["gender"], front_res["aadhaar_number"]] if v)
            back_count = sum(1 for v in [back_res["address"], back_res["father_spouse_name"], back_res["pincode"]] if v)
            pan_count = sum(1 for v in [pan_res["pan_number"], pan_res["name"], pan_res["father_spouse_name"], pan_res["dob"]] if v)

            if pan_count >= 2:
                pan_res["detected_type"] = "PAN Card (Inferred)"
                return pan_res
            elif back_count >= 2:
                back_res["detected_type"] = "Aadhaar Back (Inferred)"
                return back_res
            else:
                front_res["detected_type"] = "Aadhaar Front (Inferred)"
                return front_res
