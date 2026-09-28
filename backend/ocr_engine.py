"""
Unified OCR Engine Manager for Quick Fill (QF).
Supports:
1. RapidOCR (PP-OCRv4 ONNX Runtime): SOTA Deep Learning Neural OCR for Linux, Mac & Windows
2. Windows Media OCR (winocr): Native Windows 10/11 GPU/NPU accelerated engine
3. Tesseract OCR (pytesseract): Portable fallback
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
import numpy as np

# Import preprocessor
from .preprocessor import ImagePreprocessor

# 1. Check RapidOCR availability (Primary Neural OCR Engine)
RAPIDOCR_AVAILABLE = False
_rapid_ocr_engine = None

def get_rapid_ocr():
    global _rapid_ocr_engine, RAPIDOCR_AVAILABLE
    if _rapid_ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapid_ocr_engine = RapidOCR()
            RAPIDOCR_AVAILABLE = True
        except Exception as e:
            RAPIDOCR_AVAILABLE = False
    return _rapid_ocr_engine

# Eager initialization check
try:
    if get_rapid_ocr() is not None:
        RAPIDOCR_AVAILABLE = True
except Exception:
    RAPIDOCR_AVAILABLE = False

# 2. Check Windows Media OCR (winocr) availability
WINOCR_AVAILABLE = False
try:
    import winocr
    WINOCR_AVAILABLE = True
except Exception:
    WINOCR_AVAILABLE = False

# 3. Check Tesseract availability (Fallback)
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

# Keywords indicating recognizable Indian ID text
ID_KEYWORDS = [
    "GOVERNMENT", "INDIA", "BHARAT", "UIDAI", "DOB", "YEAR", "BIRTH",
    "MALE", "FEMALE", "INCOME", "TAX", "PERMANENT", "ACCOUNT", "FATHER",
    "ADDRESS", "PIN", "ENROLMENT", "CARD"
]


class OCREngineManager:
    """Manages OCR extraction across RapidOCR (Deep Learning), WinOCR, and Tesseract."""

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns availability status of installed engines."""
        rapid_ok = RAPIDOCR_AVAILABLE or (get_rapid_ocr() is not None)
        return {
            "rapidocr_available": rapid_ok,
            "winocr_available": WINOCR_AVAILABLE,
            "tesseract_available": TESSERACT_AVAILABLE,
            "primary_engine": "rapidocr" if rapid_ok else ("winocr" if WINOCR_AVAILABLE else ("tesseract" if TESSERACT_AVAILABLE else "none"))
        }

    @classmethod
    def _score_extracted_text(cls, text: str) -> int:
        """Heuristic score to check if OCR extracted recognizable ID text."""
        if not text:
            return 0
        score = 0
        upper = text.upper()
        for kw in ID_KEYWORDS:
            if kw in upper:
                score += 3
        # Aadhaar or PAN pattern check
        if re.search(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b", text):
            score += 8
        if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", upper):
            score += 8
        if re.search(r"\b\d{2}[/.-]\d{2}[/.-]\d{4}\b", text):
            score += 6
        # General word count
        words = text.split()
        score += min(len(words), 10)
        return score

    @classmethod
    def extract_text_rapidocr(cls, pil_img: Image.Image) -> Dict[str, Any]:
        """Performs deep-learning OCR using RapidOCR (PP-OCRv4 ONNX)."""
        engine = get_rapid_ocr()
        if engine is None:
            raise RuntimeError("RapidOCR is not available on this system.")

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        img_np = np.array(pil_img)
        ocr_result, elapse = engine(img_np)

        lines = []
        if ocr_result:
            for item in ocr_result:
                text = item[1].strip()
                if text:
                    # Only separate relationship prefixes attached to names (e.g. C/OHeesamuddin -> C/O Heesamuddin)
                    text = re.sub(r"\b([CSDWH]/[Oic])(?=[A-Za-z])", r"\1 ", text, flags=re.IGNORECASE)
                    # Automatically separate glued CamelCase words (e.g. MohammadFaridKhan -> Mohammad Farid Khan)
                    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
                    lines.append(text)

        raw_text = "\n".join(lines)
        return {
            "engine": "RapidOCR (Deep Learning Neural OCR)",
            "raw_text": raw_text,
            "lines": lines
        }

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

        if lines:
            raw_text = "\n".join(lines)
        elif raw_text:
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
        if h / float(w) > 1.15:
            custom_config = r"--oem 3 --psm 3"
        else:
            custom_config = r"--oem 3 --psm 6"

        # Try eng+hin if available
        try:
            raw_text = pytesseract.image_to_string(pil_img, config=custom_config, lang="eng+hin")
        except Exception:
            raw_text = pytesseract.image_to_string(pil_img, config=custom_config, lang="eng")

        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

        return {
            "engine": "Tesseract OCR",
            "raw_text": raw_text,
            "lines": lines
        }

    @classmethod
    async def _run_engine(cls, pil_img: Image.Image, engine: str) -> Dict[str, Any]:
        """Runs the chosen OCR engine or automatically selects the best available neural engine."""
        selected = engine.lower()

        # Explicit engine requests
        if selected == "rapidocr":
            return cls.extract_text_rapidocr(pil_img)
        elif selected == "winocr":
            return await cls.extract_text_winocr(pil_img)
        elif selected == "tesseract":
            return cls.extract_text_tesseract(pil_img)

        # Automatic mode: RapidOCR -> WinOCR -> Tesseract
        if RAPIDOCR_AVAILABLE or get_rapid_ocr() is not None:
            try:
                res = cls.extract_text_rapidocr(pil_img)
                if cls._score_extracted_text(res.get("raw_text", "")) >= 4:
                    return res
                # If score is modest but we also have WinOCR, try WinOCR to compare
                if WINOCR_AVAILABLE:
                    try:
                        win_res = await cls.extract_text_winocr(pil_img)
                        if cls._score_extracted_text(win_res.get("raw_text", "")) > cls._score_extracted_text(res.get("raw_text", "")):
                            return win_res
                    except Exception:
                        pass
                return res
            except Exception as e:
                print(f"[!] RapidOCR error in auto mode: {e}")

        if WINOCR_AVAILABLE:
            try:
                return await cls.extract_text_winocr(pil_img)
            except Exception as e:
                print(f"[!] WinOCR error in auto mode: {e}")

        if TESSERACT_AVAILABLE:
            return cls.extract_text_tesseract(pil_img)

        raise RuntimeError("No working OCR engine available on this system.")

    @classmethod
    async def recognize(cls, image_bytes: bytes, engine: str = "auto", apply_cv: bool = True) -> Dict[str, Any]:
        """
        Processes image bytes. Rapid neural networks run first on natural RGB image,
        with adaptive computer vision enhancement (CLAHE, deskew, rotation) if needed.
        """
        start_time = time.perf_counter()
        raw_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        cv_meta = {"upscaled": False, "enhanced": False, "orientation_rotation": 0}

        # Pass 1: Run on raw RGB image (preserves pure character glyphs for deep learning)
        result = await cls._run_engine(raw_img, engine)
        primary_score = cls._score_extracted_text(result.get("raw_text", ""))

        best_result = result
        best_score = primary_score
        best_rotation = 0

        # Pass 2: If primary score is low or modest (< 6), try computer vision enhancements
        if primary_score < 6 and apply_cv:
            try:
                enhanced_img, enh_meta = ImagePreprocessor.enhance_for_ocr(image_bytes)
                cv_meta.update(enh_meta)
                cv_meta["enhanced"] = True

                enh_result = await cls._run_engine(enhanced_img, engine)
                enh_score = cls._score_extracted_text(enh_result.get("raw_text", ""))
                if enh_score > best_score:
                    best_score = enh_score
                    best_result = enh_result
            except Exception as e:
                print(f"[!] CV enhancement skipped: {e}")

        # Pass 3: Multi-orientation check (if result is still very poor, try 90, 180, 270 rotations)
        if best_score < 4 and apply_cv:
            target_img = raw_img
            for rot in [90, 180, 270]:
                rot_img = ImagePreprocessor.rotate_image(target_img, rot)
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
