"""
Quick Fill (QF) - FastAPI Application Entry Point.
Provides RESTful endpoints for ID document text extraction, document classification,
real-time age calculation, and static web UI serving.
"""
import io
import os
import base64
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .ocr_engine import OCREngineManager
from .parsers.detector import DocumentDetector
from .parsers.date_util import calculate_age
from .sample_generator import (
    generate_aadhaar_front_sample,
    generate_aadhaar_back_sample,
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
            "Aadhaar Card (Front)",
            "Aadhaar Card (Back)",
            "PAN Card"
        ],
        "ocr_engines": engine_status
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
    engine: Optional[str] = Form("auto")
):
    """
    Main extraction endpoint. Accepts either:
    1. Multi-part file upload ('file')
    2. Base64 data URI string ('image_data') from webcam snapshot
    """
    image_bytes = None

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
        raise HTTPException(status_code=400, detail="No image provided. Please upload a file or capture via camera.")

    try:
        # Step 1: Run unified OCR with computer vision preprocessing
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
