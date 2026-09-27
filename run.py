"""
Quick Fill (QF) - Application Launcher.
Starts the FastAPI server with Uvicorn and automatically launches the web interface.
"""
import sys
import time
import webbrowser
import threading
import uvicorn


def open_browser():
    """Waits for server to initialize then opens default web browser."""
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n[Quick Fill] Launching browser at: {url}\n")
    webbrowser.open(url)


def main():
    print("=" * 65)
    print("  🚀 QUICK FILL (QF) - Intelligent ID Form Auto-Filler")
    print("  Course Project: 2nd Year MPL (Modern Programming Language - Python)")
    print("=" * 65)

    # Check primary modules
    try:
        from backend.ocr_engine import OCREngineManager
        status = OCREngineManager.get_status()
        print(f"[*] OCR Engine Status: {status['primary_engine'].upper()}")
        print(f"[*] Windows Native OCR available: {status['winocr_available']}")
        print(f"[*] Tesseract OCR available: {status['tesseract_available']}")
    except Exception as e:
        print(f"[!] Warning checking OCR engines: {e}")

    print("\n[*] Starting Uvicorn Server at http://127.0.0.1:8000")
    print("[*] Press Ctrl+C to stop the server.\n")

    # Launch browser in separate background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run FastAPI app
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
