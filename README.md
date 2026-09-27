# QuickFill

A fast, offline identity document parser and KYC form auto-filler for Indian ID cards (UIDAI Aadhaar and Income Tax PAN). All image processing and OCR operations execute entirely on the local device, ensuring complete data privacy without cloud transmission.

## Features

- **Document Processing**: Automatic classification and parsing for Aadhaar Card (Front and Back) and PAN Card.
- **Computer Vision Enhancement**: OpenCV pipeline handling soft-focus deblurring (unsharp masking), perspective rectification (4-point card contour detection), automated deskewing, and adaptive contrast equalization (CLAHE).
- **Offline OCR Engine**: Hardware-accelerated local text extraction via Windows Media OCR (`winocr`) with automatic fallback to Tesseract OCR.
- **Dynamic Age Calculation**: Extracts Date of Birth and computes exact chronological age (years, months) in real time.
- **Multi-Document Merging**: Progressively aggregates fields across multiple scans (e.g. name and DOB from Aadhaar Front, address and guardian from Aadhaar Back) without overwriting existing data.
- **Multiple Input Methods**: Supports direct file upload (drag-and-drop) and live webcam capture.
- **Responsive Web Interface**: Minimalist UI supporting AMOLED dark mode and light mode, optimized for desktop, tablet, and mobile browsers.
- **Data Export**: Export structured form data directly as JSON or copy to clipboard.

## Architecture

```
User Input (Upload / Camera)
         │
         ▼
FastAPI Backend (/api/extract)
         │
         ▼
OpenCV Preprocessor
  ├── 4-Point Perspective Warp (Card Detection)
  ├── Unsharp Masking & Edge Crisp (Deblur)
  ├── Rotational Deskewing
  └── Contrast Equalization (CLAHE)
         │
         ▼
Unified OCR Engine (Windows Media OCR / Tesseract)
         │
         ▼
Document Classifier & Dispatcher
  ├── Aadhaar Front Parser (Name, DOB, Gender, UID)
  ├── Aadhaar Back Parser (Care-of, Address, PIN, State)
  └── PAN Parser (Name, Father's Name, DOB, PAN)
         │
         ▼
Structured JSON -> Auto-Fill Form & Smart Merge
```

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI endpoints and static file serving
│   ├── ocr_engine.py        # OCR engine abstraction and orientation recovery
│   ├── preprocessor.py      # OpenCV enhancement (deblur, deskew, perspective warp)
│   ├── sample_generator.py  # Synthetic sample cards for verification
│   └── parsers/
│       ├── aadhaar_parser.py# UIDAI Aadhaar front & back parser
│       ├── pan_parser.py    # PAN card parser
│       ├── detector.py      # Document classifier
│       ├── date_util.py     # Date normalization and age calculation
│       └── common.py        # Validation patterns and regex utilities
├── frontend/
│   ├── index.html           # Minimalist interface layout
│   ├── styles.css           # AMOLED & Light theme styles
│   └── app.js               # Application logic and form population
├── run.py                   # Local development launcher
├── requirements.txt         # Python dependencies
├── .gitignore
├── LICENSE
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Windows 10/11 (for native Windows Media OCR) or Tesseract OCR installed

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/InzamamulQureshi/QuickFill.git
   cd QuickFill
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

Launch the application using the runner script:
```bash
python run.py
```

The application will start the local server on `http://127.0.0.1:8000` and open it in your default web browser.

Alternatively, launch with Uvicorn directly:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## API Documentation

When the server is running, interactive API documentation is available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Primary Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Returns operational status and available OCR engines |
| `POST` | `/api/extract` | Extracts and parses identity card data from uploaded image |
| `POST` | `/api/calculate-age` | Computes exact age from a given date string |
| `GET` | `/api/samples/{card_type}` | Returns synthetic test cards for testing (`aadhaar_front`, `aadhaar_back`, `pan`) |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
