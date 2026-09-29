# QuickFill

A fast, offline identity document parser and KYC form auto-filler for Indian ID cards (UIDAI Aadhaar and Income Tax PAN). All image processing and OCR operations run entirely on the local device, ensuring complete data privacy without cloud transmission.

## Features

- **Document Support**: Automatic classification and parsing for UIDAI Aadhaar (Front, Back, PVC Card, e-Aadhaar PDF) and Income Tax PAN cards.
- **Encrypted PDF Handling**: In-browser password unlock workflow for password-protected UIDAI e-Aadhaar PDFs with format hints.
- **Computer Vision Pipeline**: OpenCV enhancement featuring soft-focus deblurring, 4-point perspective warp, deskewing, and adaptive contrast equalization (CLAHE).
- **Offline OCR Engine**: Local text extraction via RapidOCR / ONNX Runtime and Windows Media OCR (`winocr`) with automatic Tesseract OCR fallback.
- **Dynamic Age Calculation**: Real-time chronological age computation from extracted Date of Birth.
- **Smart Merge Confirmation**: Side-by-side diff preview modal allowing selective merging of supplementary cards into existing form details.
- **Modern Design System**:
  - Typography powered by **Geist & Geist Mono** by Vercel.
  - Harmonious **Dark Mode** (`#121212`) and **Light Mode** (`#ebe4da` linen canvas with `#ffffff` card surfaces and `#c4b39f` borders).
  - Fully responsive, fluid layout optimized across ultrawide monitors, laptops, tablets, and mobile devices.
- **Input Methods**: Drag-and-drop file upload, clipboard paste (Ctrl+V), and live camera stream capture.
- **Data Export**: Export structured form data as JSON or copy directly to clipboard.

## Getting Started

### Prerequisites

- Python 3.10+
- Windows 10/11 (for native Windows Media OCR) or Tesseract OCR installed

### Installation

```bash
git clone https://github.com/InzamamulQureshi/QuickFill.git
cd QuickFill
pip install -r requirements.txt
```

### Running the Application

Start the local server:
```bash
python run.py
```
The application will launch on `http://127.0.0.1:8000` and open automatically in your browser.

Alternatively, run with Uvicorn:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Operational status and active OCR engine |
| `POST` | `/api/extract` | Parse identity card image or PDF |
| `POST` | `/api/calculate-age` | Compute age from a date string |
| `GET` | `/api/samples/{card_type}` | Fetch test cards (`aadhaar_front`, `aadhaar_back`, `pan`) |

Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

## License

MIT License. See [LICENSE](LICENSE) for details.
