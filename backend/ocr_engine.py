"""
Unified OCR Engine Manager for Quick Fill (QF).
Supports Windows Media OCR (winocr) as the zero-dependency, native offline engine,
with fallback to Tesseract OCR (pytesseract).
Includes multi-orientation recovery (handling 90°, 180°, 270° tilted smartphone captures).
"""
import io
import re
import time
import os
import shutil
import asyncio
from typing import Dict, Any, List, Optional
from PIL import Image

# Import preprocessor
from .preprocessor import ImagePreprocessor

# Check for Tesseract availability
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    default_tess_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
    ]
    if shutil.which("tesseract"):
        TESSERACT_AVAILABLE = True
    else:
        for p in default_tess_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                TESSERACT_AVAILABLE = True
                break
except Exception:
    TESSERACT_AVAILABLE = False

# Check for Windows Media OCR (winocr) availability
WINOCR_AVAILABLE = False
try:
    import winocr
    WINOCR_AVAILABLE = True
except Exception:
    WINOCR_AVAILABLE = False

# Keywords indicating recognizable Indian ID text
ID_KEYWORDS = [
    "GOVERNMENT", "INDIA", "BHARAT", "UIDAI", "DOB", "YEAR", "BIRTH",
    "MALE", "FEMALE", "INCOME", "TAX", "PERMANENT", "ACCOUNT", "FATHER",
    "ADDRESS", "PIN", "ENROLMENT", "CARD"
]


class OCREngineManager:
    """Manages OCR extraction across native Windows OCR and Tesseract."""

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns availability status of installed engines."""
        return {
            "winocr_available": WINOCR_AVAILABLE,
            "tesseract_available": TESSERACT_AVAILABLE,
            "primary_engine": "winocr" if WINOCR_AVAILABLE else ("tesseract" if TESSERACT_AVAILABLE else "none")
        }

    @classmethod
    def _score_extracted_text(cls, text: str) -> int:
        """Heuristic score to check if OCR extracted recognizable ID text."""
        score = 0
        upper = text.upper()
        for kw in ID_KEYWORDS:
            if kw in upper:
                score += 3
        # Aadhaar or PAN pattern check
        if re.search(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b", text):
            score += 6
        if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", upper):
            score += 6
        if re.search(r"\b\d{2}[/.-]\d{2}[/.-]\d{4}\b", text):
            score += 4
        # General word count
        words = text.split()
        score += min(len(words), 10)
        return score

    @classmethod
    async def extract_text_winocr(cls, pil_img: Image.Image) -> Dict[str, Any]:
        """Performs OCR using Windows Media Native OCR engine."""
        if not WINOCR_AVAILABLE:
            raise RuntimeError("Windows Media OCR (winocr) is not available.")

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        result = await winocr.recognize_pil(pil_img, "en")

        raw_text = result.text if hasattr(result, "text") else ""
        lines = []
        if hasattr(result, "lines"):
            for line_obj in result.lines:
                text = line_obj.text.strip()
                if text:
                    lines.append(text)

        if not lines and raw_text:
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

        return {
            "engine": "Windows Native OCR (WinOCR)",
            "raw_text": raw_text,
            "lines": lines
        }

    @classmethod
    def extract_text_tesseract(cls, pil_img: Image.Image) -> Dict[str, Any]:
        """Performs OCR using Tesseract OCR."""
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract OCR is not installed or not in PATH.")

        w, h = pil_img.size
        # Full documents/pages with height > width require PSM 3 (automatic page segmentation)
        # to prevent Tesseract from gluing multi-column text horizontally across lines.
        if h / float(w) > 1.15:
            custom_config = r"--oem 3 --psm 3"
        else:
            custom_config = r"--oem 3 --psm 6"

        raw_text = pytesseract.image_to_string(pil_img, config=custom_config, lang="eng")
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

        return {
            "engine": "Tesseract OCR",
            "raw_text": raw_text,
            "lines": lines
        }

    @classmethod
    async def _run_engine(cls, pil_img: Image.Image, engine: str) -> Dict[str, Any]:
        """Runs the chosen OCR engine on the image."""
        selected_engine = engine.lower()
        if selected_engine == "winocr" or (selected_engine == "auto" and WINOCR_AVAILABLE):
            try:
                return await cls.extract_text_winocr(pil_img)
            except Exception as e:
                if TESSERACT_AVAILABLE:
                    return cls.extract_text_tesseract(pil_img)
                raise e
        elif selected_engine == "tesseract" or (selected_engine == "auto" and TESSERACT_AVAILABLE):
            try:
                return cls.extract_text_tesseract(pil_img)
            except Exception as e:
                if WINOCR_AVAILABLE:
                    return await cls.extract_text_winocr(pil_img)
                raise e
        else:
            raise RuntimeError("No working OCR engine available on this system.")

    @classmethod
    async def recognize(cls, image_bytes: bytes, engine: str = "auto", apply_cv: bool = True) -> Dict[str, Any]:
        """
        Processes image bytes with computer vision enhancement,
        executes OCR, and falls back to multi-orientation checking if needed.
        """
        start_time = time.perf_counter()

        # Step 1: Computer Vision Preprocessing (Deblur, Deskew, Perspective Rectification)
        if apply_cv:
            processed_img, cv_meta = ImagePreprocessor.enhance_for_ocr(image_bytes)
        else:
            processed_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            cv_meta = {"upscaled": False}

        # Step 2: Primary OCR run
        result = await cls._run_engine(processed_img, engine)
        primary_score = cls._score_extracted_text(result.get("raw_text", ""))

        # Step 3: Multi-orientation check (if primary run has very poor confidence or was taken sideways)
        best_result = result
        best_score = primary_score
        best_rotation = 0

        if primary_score < 4 and apply_cv:
            # Test 90°, 180°, and 270° rotations
            for rot in [90, 180, 270]:
                rot_img = ImagePreprocessor.rotate_image(processed_img, rot)
                rot_res = await cls._run_engine(rot_img, engine)
                score = cls._score_extracted_text(rot_res.get("raw_text", ""))
                if score > best_score:
                    best_score = score
                    best_result = rot_res
                    best_rotation = rot
                    if score >= 6:
                        break

        cv_meta["orientation_rotation"] = best_rotation

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        best_result["processing_time_ms"] = elapsed_ms
        best_result["preprocessing"] = cv_meta
        return best_result
