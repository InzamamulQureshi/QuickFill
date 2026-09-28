"""
Date and Age Calculation Utilities for Quick Fill (QF).
Handles various Indian ID date formats, OCR symbol cleaning,
and exact age computation.
"""
from datetime import datetime, date
import re
from typing import Optional, Dict, Any, Tuple


def normalize_date_string(raw_date: str) -> Optional[str]:
    """
    Cleans OCR artifacts from date strings and returns standard DD/MM/YYYY.
    Examples:
        '15'08/2001' -> '15/08/2001'
        '15-08-2001' -> '15/08/2001'
        '15.08.2001' -> '15/08/2001'
        '2001-08-15' -> '15/08/2001'
        '1995'       -> '01/01/1995'
    """
    if not raw_date:
        return None

    cleaned = raw_date.strip()

    # 1. Search for YYYY-MM-DD or YYYY/MM/DD
    iso_match = re.search(r"\b(19\d{2}|20[0-2]\d)[/.-](\d{1,2})[/.-](\d{1,2})\b", cleaned)
    if iso_match:
        y, m, d = iso_match.group(1), int(iso_match.group(2)), int(iso_match.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return f"{d:02d}/{m:02d}/{y}"

    # Replace common OCR misreads of slashes/delimiters
    cleaned_delims = re.sub(r"['\"`|\\.]", "/", cleaned)
    cleaned_delims = re.sub(r"[-_]", "/", cleaned_delims)
    cleaned_delims = re.sub(r"\s+", "/", cleaned_delims)

    # 2. Search for full DD/MM/YYYY
    match = re.search(r"\b(\d{1,2})[/](\d{1,2})[/](\d{4})\b", cleaned_delims)
    if match:
        p1, p2, y = int(match.group(1)), int(match.group(2)), match.group(3)
        # Check if p1 is day and p2 is month, or p1 is month and p2 is day
        if 1 <= p1 <= 31 and 1 <= p2 <= 12:
            return f"{p1:02d}/{p2:02d}/{y}"
        elif 1 <= p1 <= 12 and 1 <= p2 <= 31:
            return f"{p2:02d}/{p1:02d}/{y}"

    # 2b. Search with OCR character confusion recovery (B->8, O/o->0, I/l->1, S->5)
    m_sub = re.search(r"\b([0-9BOISlo]{1,2})[/]([0-9BOISlo]{1,2})[/]([0-9BOISlo]{4})\b", cleaned_delims)
    if m_sub:
        table = str.maketrans("BOISlo", "801510")
        p1 = m_sub.group(1).translate(table)
        p2 = m_sub.group(2).translate(table)
        y = m_sub.group(3).translate(table)
        if p1.isdigit() and p2.isdigit() and y.isdigit() and len(y) == 4:
            d, m = int(p1), int(p2)
            if 1 <= d <= 31 and 1 <= m <= 12:
                return f"{d:02d}/{m:02d}/{y}"
            elif 1 <= d <= 12 and 1 <= m <= 31:
                return f"{m:02d}/{d:02d}/{y}"

    # 3. Search for Year only (common on Aadhaar: 'Year of Birth: 1978' or 'जन्म वर्ष: 1954')
    year_match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", cleaned)
    if year_match:
        return f"01/01/{year_match.group(1)}"

    return None


def calculate_age(dob_str: str, ref_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Calculates exact age (years, months, days) given a DOB string.
    Supports formats: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, etc.
    Returns:
        {
            "years": int,
            "months": int,
            "days": int,
            "formatted": str (e.g., '24 Years, 7 Months'),
            "iso_dob": str (e.g., '2001-08-15'),
            "display_dob": str (e.g., '15/08/2001')
        }
    """
    if not dob_str:
        return {"years": None, "months": None, "days": None, "formatted": "", "iso_dob": "", "display_dob": ""}

    if ref_date is None:
        ref_date = date.today()

    parsed_date: Optional[date] = None
    clean_dob = normalize_date_string(dob_str) or dob_str.strip()

    # Try different format patterns
    patterns = [
        ("%d/%m/%Y", clean_dob),
        ("%Y-%m-%d", clean_dob),
        ("%d-%m-%Y", clean_dob),
        ("%d.%m.%Y", clean_dob),
    ]

    for fmt, val in patterns:
        try:
            parsed_date = datetime.strptime(val, fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        # Fallback regex for Year only
        year_m = re.search(r"\b(19\d{2}|20[0-2]\d)\b", dob_str)
        if year_m:
            try:
                parsed_date = date(int(year_m.group(1)), 1, 1)
            except ValueError:
                pass

    if not parsed_date:
        return {
            "years": None,
            "months": None,
            "days": None,
            "formatted": "Invalid DOB",
            "iso_dob": "",
            "display_dob": dob_str
        }

    # Precise age calculation
    years = ref_date.year - parsed_date.year
    months = ref_date.month - parsed_date.month
    days = ref_date.day - parsed_date.day

    if days < 0:
        months -= 1
        # Borrow days from previous month
        prev_month = (ref_date.month - 1) or 12
        prev_year = ref_date.year if prev_month != 12 else ref_date.year - 1
        days_in_prev_month = (date(ref_date.year, ref_date.month, 1) - date(prev_year, prev_month, 1)).days
        days += days_in_prev_month

    if months < 0:
        years -= 1
        months += 12

    # Formatting human-readable age
    if years > 0:
        formatted = f"{years} Years"
        if months > 0:
            formatted += f", {months} Months"
    else:
        formatted = f"{months} Months, {days} Days"

    return {
        "years": max(0, years),
        "months": max(0, months),
        "days": max(0, days),
        "formatted": formatted,
        "iso_dob": parsed_date.isoformat(),
        "display_dob": parsed_date.strftime("%d/%m/%Y")
    }
