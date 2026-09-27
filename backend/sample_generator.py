"""
Synthetic Sample ID Card Generator for Quick Fill (QF).
Generates realistic, privacy-safe demo images for Aadhaar Front, Aadhaar Back,
and PAN Card for 1-click testing, project presentation, and viva demonstration.
"""
import io
import os
from PIL import Image, ImageDraw, ImageFont


def get_font(size: int, bold: bool = False):
    """Loads system Arial/Segoe font or falls back to default."""
    font_names = [
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\calibrib.ttf" if bold else "C:\\Windows\\Fonts\\calibri.ttf"
    ]
    for fn in font_names:
        if os.path.exists(fn):
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_aadhaar_front_sample() -> bytes:
    """Generates a demo Aadhaar Card Front image."""
    w, h = 900, 560
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Outer border & header bar
    draw.rectangle([(10, 10), (w - 10, h - 10)], outline=(200, 200, 210), width=3)
    draw.rectangle([(12, 12), (w - 12, 85)], fill=(244, 246, 250))

    # Top emblem text
    f_header = get_font(20, bold=True)
    f_sub = get_font(14, bold=False)
    draw.text((280, 22), "GOVERNMENT OF INDIA", font=f_header, fill=(30, 41, 59))
    draw.text((220, 52), "Unique Identification Authority of India", font=f_sub, fill=(71, 85, 105))

    # Photo placeholder on left
    draw.rectangle([(50, 130), (220, 350)], fill=(226, 232, 240), outline=(148, 163, 184), width=2)
    f_placeholder = get_font(14, bold=True)
    draw.text((85, 230), "PHOTO", font=f_placeholder, fill=(100, 116, 139))

    # Details on right
    f_name = get_font(24, bold=True)
    f_detail = get_font(20, bold=False)
    f_uid = get_font(28, bold=True)

    draw.text((270, 140), "Aarav Suresh Sharma", font=f_name, fill=(15, 23, 42))
    draw.text((270, 200), "DOB: 15/08/2001", font=f_detail, fill=(30, 41, 59))
    draw.text((270, 250), "Gender: MALE / PURUSH", font=f_detail, fill=(30, 41, 59))

    # Aadhaar Number row
    draw.line([(30, 430), (w - 30, 430)], fill=(226, 232, 240), width=2)
    draw.text((310, 455), "4521 8904 7623", font=f_uid, fill=(15, 23, 42))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_aadhaar_back_sample() -> bytes:
    """Generates a demo Aadhaar Card Back image with Address and Care-of."""
    w, h = 900, 560
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Outer border & header bar
    draw.rectangle([(10, 10), (w - 10, h - 10)], outline=(200, 200, 210), width=3)
    draw.rectangle([(12, 12), (w - 12, 75)], fill=(244, 246, 250))

    f_header = get_font(18, bold=True)
    draw.text((220, 28), "Unique Identification Authority of India", font=f_header, fill=(30, 41, 59))

    # Address block
    f_lbl = get_font(20, bold=True)
    f_txt = get_font(18, bold=False)

    draw.text((50, 110), "Address:", font=f_lbl, fill=(15, 23, 42))
    draw.text((50, 150), "S/O: Suresh Ram Sharma", font=f_txt, fill=(30, 41, 59))
    draw.text((50, 190), "Flat No. 402, Sunshine Heights, 12th Main Road", font=f_txt, fill=(30, 41, 59))
    draw.text((50, 230), "4th Cross, Indiranagar, Near Metro Station", font=f_txt, fill=(30, 41, 59))
    draw.text((50, 270), "Bengaluru, Karnataka - 560038", font=f_txt, fill=(30, 41, 59))

    # QR Code placeholder
    draw.rectangle([(640, 120), (840, 320)], fill=(241, 245, 249), outline=(148, 163, 184), width=2)
    f_qr = get_font(14, bold=True)
    draw.text((700, 210), "QR CODE", font=f_qr, fill=(100, 116, 139))

    # Help info at bottom
    draw.line([(30, 420), (w - 30, 420)], fill=(226, 232, 240), width=2)
    f_help = get_font(16, bold=False)
    draw.text((280, 445), "www.uidai.gov.in | Help: 1947", font=f_help, fill=(100, 116, 139))
    f_uid = get_font(22, bold=True)
    draw.text((330, 485), "4521 8904 7623", font=f_uid, fill=(30, 41, 59))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_pan_card_sample() -> bytes:
    """Generates a demo PAN Card image."""
    w, h = 900, 560
    img = Image.new("RGB", (w, h), color=(250, 252, 255))
    draw = ImageDraw.Draw(img)

    # Outer border with blue accent
    draw.rectangle([(10, 10), (w - 10, h - 10)], outline=(186, 215, 245), width=3)
    draw.rectangle([(12, 12), (w - 12, 85)], fill=(224, 242, 254))

    f_top = get_font(20, bold=True)
    f_top_r = get_font(18, bold=True)
    draw.text((50, 25), "INCOME TAX DEPARTMENT", font=f_top, fill=(14, 116, 144))
    draw.text((630, 25), "GOVT. OF INDIA", font=f_top_r, fill=(15, 23, 42))

    # Photo & signature placeholders
    draw.rectangle([(660, 120), (830, 310)], fill=(226, 232, 240), outline=(148, 163, 184), width=2)
    f_ph = get_font(14, bold=True)
    draw.text((710, 205), "PHOTO", font=f_ph, fill=(100, 116, 139))

    # Field labels and values
    f_label = get_font(14, bold=False)
    f_val = get_font(20, bold=True)
    f_pan = get_font(28, bold=True)

    # Name
    draw.text((60, 120), "Name / नाम", font=f_label, fill=(100, 116, 139))
    draw.text((60, 145), "AARAV SURESH SHARMA", font=f_val, fill=(15, 23, 42))

    # Father's Name
    draw.text((60, 200), "Father's Name / पिता का नाम", font=f_label, fill=(100, 116, 139))
    draw.text((60, 225), "SURESH RAM SHARMA", font=f_val, fill=(15, 23, 42))

    # Date of Birth
    draw.text((60, 280), "Date of Birth / जन्म की तारीख", font=f_label, fill=(100, 116, 139))
    draw.text((60, 305), "15/08/2001", font=f_val, fill=(15, 23, 42))

    # PAN Number
    draw.line([(30, 385), (w - 30, 385)], fill=(224, 242, 254), width=2)
    draw.text((60, 405), "Permanent Account Number Card", font=f_label, fill=(100, 116, 139))
    draw.text((60, 435), "ABCDE1234F", font=f_pan, fill=(14, 116, 144))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
