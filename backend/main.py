"""
Quick Fill (QF) - FastAPI Application Entry Point.
Provides RESTful endpoints for ID document text extraction, document classification,
real-time age calculation, and static web UI serving.
"""
import io
import re
import os
import base64
import time
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .ocr_engine import OCREngineManager
from .parsers.detector import DocumentDetector
from .parsers.date_util import calculate_age
from .pdf_processor import PDFProcessor
from .sample_generator import (
    generate_aadhaar_front_sample,
    generate_aadhaar_back_sample,
    generate_eaadhaar_full_sample,
    generate_pan_card_sample
)

app = FastAPI(
    title="Quick Fill (QF) - Intelligent ID Form Filler API",
    description="Automated text extraction, classification, and form auto-fill for Indian Identity Documents (Aadhaar & PAN)",
    version="1.0.0"
)

# Enable CORS for local testing and web frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgeRequest(BaseModel):
    dob: str


class Base64ExtractRequest(BaseModel):
    image_base64: str
    doc_hint: Optional[str] = "auto"
    engine: Optional[str] = "auto"


@app.get("/api/status")
async def get_system_status():
    """Returns the operational status of installed OCR engines and features."""
    engine_status = OCREngineManager.get_status()
    return {
        "status": "online",
        "app_name": "Quick Fill (QF)",
        "version": "1.0.0",
        "supported_documents": [
            "e-Aadhaar PDF (Full Document)",
            "Aadhaar PVC Card (Front & Back)",
            "Aadhaar Card (Front)",
            "Aadhaar Card (Back)",
            "PAN Card"
        ],
        "ocr_engines": engine_status,
        "features": {
            "pdf_support": True,
            "masked_aadhaar": True,
            "smart_merge": True
        }
    }


@app.post("/api/calculate-age")
async def api_calculate_age(req: AgeRequest):
    """Calculates exact age breakdown in real time for a given DOB."""
    if not req.dob:
        raise HTTPException(status_code=400, detail="Date of Birth is required")
    age_info = calculate_age(req.dob)
    return {"dob": req.dob, "age": age_info}


@app.get("/api/samples/{card_type}")
async def get_sample_card(card_type: str):
    """Provides synthetic demo ID card images for quick 1-click testing."""
    card_type = card_type.lower()
    if card_type in ("aadhaar_front", "aadhar_front"):
        data = generate_aadhaar_front_sample()
    elif card_type in ("aadhaar_back", "aadhar_back"):
        data = generate_aadhaar_back_sample()
    elif card_type in ("eaadhaar_full", "eaadhaar", "e_aadhaar", "aadhaar_full"):
        data = generate_eaadhaar_full_sample()
    elif card_type in ("pan", "pan_card"):
        data = generate_pan_card_sample()
    else:
        raise HTTPException(status_code=404, detail="Unknown sample card type")

    return Response(content=data, media_type="image/png")


@app.post("/api/extract")
async def extract_from_upload(
    file: Optional[UploadFile] = File(None),
    image_data: Optional[str] = Form(None),
    doc_hint: Optional[str] = Form("auto"),
    engine: Optional[str] = Form("auto"),
    password: Optional[str] = Form("")
):
    """
    Main extraction endpoint. Accepts:
    1. Multi-part file upload ('file') - PNG, JPG, WEBP, or PDF
    2. Base64 data URI string ('image_data') from webcam snapshot or clipboard
    3. Optional 'password' for password-protected e-Aadhaar PDFs
    """
    image_bytes = None
    filename = file.filename if file else ""

    if file:
        image_bytes = await file.read()
    elif image_data:
        # Strip header if data URI: 'data:image/jpeg;base64,...'
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="No document provided. Please upload a file, paste an image, or use camera.")

    try:
        # Handle PDF documents (e-Aadhaar or scanned multi-page PDF)
        if PDFProcessor.is_pdf(image_bytes, filename=filename):
            start_time = time.perf_counter()
            pdf_data = PDFProcessor.extract_pdf_data(image_bytes, password=password or "")

            if pdf_data.get("is_encrypted") and not pdf_data.get("is_decrypted"):
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "needs_password": True,
                        "error": "Password Protected PDF",
                        "message": "This e-Aadhaar PDF is password-protected. UIDAI password format is: First 4 letters of your Name in CAPITAL letters followed by 4-digit Year of Birth (e.g. AARA1995)."
                    }
                )

            preview_url = pdf_data.get("preview_data_url", "")
            rendered_images = pdf_data.get("rendered_images", [])

            digital_text = pdf_data.get("digital_text", "")
            digital_lines = pdf_data.get("digital_lines", [])

            ocr_text = ""
            ocr_lines = []
            engine_used = "Digital PDF Parser"

            # Check if digital vector text is already rich (e.g. direct e-Aadhaar or e-PAN download)
            has_rich_digital_text = (
                len(digital_text.strip()) > 25 and
                (
                    bool(re.search(r"[A-Z]{5}[0-9]{4}[A-Z]", digital_text)) or
                    bool(re.search(r"[2-9]\d{3}\s?\d{4}\s?\d{4}", digital_text)) or
                    bool(re.search(r"\d{2}[/.-]\d{2}[/.-]\d{4}", digital_text)) or
                    any(kw in digital_text.upper() for kw in ["AADHAAR", "PAN", "INCOME TAX", "ACCOUNT NUMBER", "DOB", "YEAR OF BIRTH", "GOVERNMENT", "INDIA", "MALE", "FEMALE"])
                )
            )

            # Only run computer vision OCR if digital vector text is missing or sparse (scanned PDF)
            if not has_rich_digital_text and rendered_images:
                try:
                    buf = io.BytesIO()
                    rendered_images[0].save(buf, format="PNG")
                    page_ocr = await OCREngineManager.recognize(buf.getvalue(), engine=engine or "auto")
                    ocr_text = page_ocr.get("raw_text", "")
                    ocr_lines = page_ocr.get("lines", [])
                    engine_used = f"{page_ocr.get('engine', 'OCR')} (Scanned PDF)"
                except Exception as e:
                    print(f"[!] Warning during PDF page OCR: {e}")

            all_lines = []
            source_lines = digital_lines if has_rich_digital_text else (ocr_lines + digital_lines)
            for l in source_lines:
                cleaned = l.strip()
                if cleaned:
                    all_lines.append(cleaned)

            if all_lines:
                combined_text = "\n".join(all_lines)
            else:
                combined_text = digital_text if has_rich_digital_text else (ocr_text or digital_text)

            parsed_data = DocumentDetector.parse_document(
                raw_text=combined_text,
                lines=all_lines,
                doc_hint=doc_hint or "auto"
            )

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)

            return {
                "success": True,
                "detected_type": parsed_data.get("detected_type", "e-Aadhaar (Full Card)"),
                "data": parsed_data,
                "preview_image": preview_url,
                "ocr_meta": {
                    "engine": engine_used,
                    "processing_time_ms": elapsed_ms,
                    "preprocessing": {"pdf_pages": pdf_data.get("page_count", 1)},
                    "raw_text": combined_text,
                    "lines_count": len(all_lines)
                }
            }

        # Step 1: Run unified OCR with computer vision preprocessing for image
        ocr_result = await OCREngineManager.recognize(image_bytes, engine=engine or "auto")

        # Step 2: Parse and classify document
        parsed_data = DocumentDetector.parse_document(
            raw_text=ocr_result["raw_text"],
            lines=ocr_result["lines"],
            doc_hint=doc_hint or "auto"
        )

        return {
            "success": True,
            "detected_type": parsed_data.get("detected_type", "Unknown"),
            "data": parsed_data,
            "ocr_meta": {
                "engine": ocr_result.get("engine", "OCR"),
                "processing_time_ms": ocr_result.get("processing_time_ms", 0),
                "preprocessing": ocr_result.get("preprocessing", {}),
                "raw_text": ocr_result.get("raw_text", ""),
                "lines_count": len(ocr_result.get("lines", []))
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Error occurred during text extraction."
            }
        )


# Mount static files directory for frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/favicon.ico")
    async def serve_favicon_ico():
        fav_ico = os.path.join(frontend_dir, "favicon.ico")
        if os.path.exists(fav_ico):
            return FileResponse(fav_ico, media_type="image/x-icon")
        logo_path = os.path.join(frontend_dir, "logo.webp")
        if os.path.exists(logo_path):
            return FileResponse(logo_path, media_type="image/webp")
        return Response(status_code=404)

    @app.get("/logo.webp")
    async def serve_logo_webp():
        logo_path = os.path.join(frontend_dir, "logo.webp")
        if os.path.exists(logo_path):
            return FileResponse(logo_path, media_type="image/webp")
        return Response(status_code=404)

    @app.get("/og-image.png")
    async def serve_og_image():
        og_path = os.path.join(frontend_dir, "og-image.png")
        if os.path.exists(og_path):
            return FileResponse(og_path, media_type="image/png")
        return Response(status_code=404)
