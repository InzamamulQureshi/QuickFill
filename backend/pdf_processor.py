"""
PDF Processing Engine for Quick Fill (QF).
Handles e-Aadhaar PDFs and scanned document PDFs.
Extracts digital text layers directly via pypdf and renders high-resolution
bitmaps via pypdfium2 for computer vision OCR.
"""
import io
import re
import base64
from typing import Dict, Any, List, Optional
from PIL import Image

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import pypdfium2
    PYPDFIUM2_AVAILABLE = True
except ImportError:
    PYPDFIUM2_AVAILABLE = False


class PDFProcessor:
    """Extracts text and renders raster images from PDF identity documents."""

    @staticmethod
    def is_pdf(data: bytes, filename: str = "") -> bool:
        """Determines whether raw bytes or filename represent a PDF file."""
        if not data:
            return False
        if filename.lower().endswith(".pdf"):
            return True
        # Check PDF magic bytes '%PDF-'
        return data[:5] == b"%PDF-" or b"%PDF-" in data[:1024]

    @classmethod
    def extract_pdf_data(cls, pdf_bytes: bytes, password: str = "") -> Dict[str, Any]:
        """
        Extracts embedded digital text and renders high-res page image(s).
        Returns a dict containing:
            - digital_text: str
            - digital_lines: List[str]
            - rendered_images: List[Image.Image]
            - preview_data_url: str
            - page_count: int
            - is_encrypted: bool
            - is_decrypted: bool
        """
        result = {
            "digital_text": "",
            "digital_lines": [],
            "rendered_images": [],
            "preview_data_url": "",
            "page_count": 0,
            "is_encrypted": False,
            "is_decrypted": True,
            "error": None
        }

        # Step 1: Digital text extraction using pypdf
        if PYPDF_AVAILABLE:
            try:
                reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                if reader.is_encrypted:
                    result["is_encrypted"] = True
                    result["is_decrypted"] = False

                    # Try passwords (user-provided, uppercase, or blank)
                    passwords_to_try = []
                    if password:
                        passwords_to_try.append(password)
                        if password.upper() != password:
                            passwords_to_try.append(password.upper())
                    passwords_to_try.append("")

                    for pwd in passwords_to_try:
                        try:
                            res = reader.decrypt(pwd)
                            if res > 0:
                                result["is_decrypted"] = True
                                break
                        except Exception:
                            continue

                if not result["is_encrypted"] or result["is_decrypted"]:
                    result["page_count"] = len(reader.pages)
                    extracted_chunks = []
                    for page in reader.pages:
                        try:
                            txt = page.extract_text()
                            if txt:
                                extracted_chunks.append(txt)
                        except Exception:
                            pass
                    result["digital_text"] = "\n".join(extracted_chunks).strip()
                    result["digital_lines"] = [
                        l.strip() for l in result["digital_text"].splitlines() if l.strip()
                    ]
            except Exception as e:
                err_msg = str(e).lower()
                if "decrypt" in err_msg or "password" in err_msg:
                    result["is_encrypted"] = True
                    result["is_decrypted"] = False
                result["error"] = f"pypdf extraction error: {e}"

        # Step 2: High-resolution raster rendering using pypdfium2
        if PYPDFIUM2_AVAILABLE:
            try:
                doc = None
                passwords_to_try = [None]
                if password:
                    passwords_to_try.insert(0, password)
                    passwords_to_try.insert(1, password.upper())
                passwords_to_try.append("")

                for pwd in passwords_to_try:
                    try:
                        doc = pypdfium2.PdfDocument(pdf_bytes, password=pwd)
                        break
                    except Exception:
                        continue

                if doc is not None:
                    result["page_count"] = max(result["page_count"], len(doc))

                    # Render up to first 2 pages
                    max_pages = min(2, len(doc))
                    for i in range(max_pages):
                        page = doc[i]
                        # Render at scale 2.5 (approx 200-250 DPI for sharp OCR)
                        pil_img = page.render(scale=2.5).to_pil().convert("RGB")
                        result["rendered_images"].append(pil_img)

                    # Generate base64 thumbnail preview for frontend
                    if result["rendered_images"]:
                        preview_img = result["rendered_images"][0].copy()
                        preview_img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                        buf = io.BytesIO()
                        preview_img.save(buf, format="JPEG", quality=85)
                        result["preview_data_url"] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

            except Exception as e:
                if not result.get("error"):
                    result["error"] = f"pypdfium2 render error: {e}"

        return result
