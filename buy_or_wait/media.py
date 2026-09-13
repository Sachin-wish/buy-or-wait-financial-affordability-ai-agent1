"""Multimodal local media loader and financial evidence parser.

Reads local media files (images, receipts, invoices, documents) and extracts
financial context, OCR text, metadata, and amounts with defensive sanitization.
"""
from __future__ import annotations
import base64
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any
from .models import Row, iso_date, money

# Regex patterns for extracting financial data from media text / receipts
CURRENCY_SYMBOLS = {
    "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR", "C$": "CAD", "A$": "AUD"
}

AMOUNT_PATTERN = re.compile(
    r"(?:(?:total|amount|subtotal|balance|due|paid|charge|price)[\s:]*)?"
    r"([$€£¥₹]|USD|EUR|GBP|JPY|INR|CAD|AUD)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
    re.IGNORECASE
)

DATE_PATTERN = re.compile(
    r"\b(\d{4}[-/.]\d{2}[-/.]\d{2}|\d{2}[-/.]\d{2}[-/.]\d{4})\b"
)

def parse_media_text(content: str) -> dict[str, Any]:
    """Parse text extracted from a media file (OCR or caption) into structured financial evidence."""
    extracted: dict[str, Any] = {
        "raw_text": content.strip(),
        "amounts": [],
        "dates": [],
        "currency": "USD",
        "vendor": "",
        "category": "expense",
    }
    
    # Search for dates
    for match in DATE_PATTERN.finditer(content):
        raw_date = match.group(1).replace(".", "-").replace("/", "-")
        # If MM-DD-YYYY or DD-MM-YYYY format
        parts = raw_date.split("-")
        if len(parts[0]) == 4:
            iso_d = iso_date(raw_date)
        elif len(parts[2]) == 4:
            # Reorder to YYYY-MM-DD
            iso_d = iso_date(f"{parts[2]}-{parts[0]:0>2}-{parts[1]:0>2}")
        else:
            iso_d = None
        if iso_d:
            extracted["dates"].append(iso_d)

    # Search for amounts and currencies
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # Vendor heuristic: First non-amount line that looks like a title
        if not extracted["vendor"] and not any(kw in line.lower() for kw in ("total", "subtotal", "tax", "date", "receipt", "invoice")):
            if len(line) < 40 and not line.startswith(("$", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
                extracted["vendor"] = line

        # Search amounts
        for match in AMOUNT_PATTERN.finditer(line):
            curr_str, amt_str = match.groups()
            try:
                amt = money(amt_str)
                if amt > 0:
                    curr = CURRENCY_SYMBOLS.get(curr_str, curr_str if curr_str else "USD")
                    extracted["amounts"].append((amt, curr))
                    extracted["currency"] = curr
            except (ValueError, InvalidOperation):
                continue

    return extracted

def read_local_media_file(file_path: str | Path) -> dict[str, Any]:
    """Read a local media file from disk, inspect its format, and extract textual/visual evidence.
    
    Supports:
    - Text files / markdown transcripts / mock OCR (.txt, .md, .json, .log, .ocr)
    - Image files (.png, .jpg, .jpeg, .webp, .gif, .bmp)
    - Metadata and receipt parsing
    """
    path = Path(file_path)
    if not path.exists():
        return {"path": str(file_path), "exists": False, "error": "file not found", "text": ""}

    size_bytes = path.stat().st_size
    suffix = path.suffix.lower()

    # If it's a text-based media dump or OCR output
    if suffix in (".txt", ".md", ".json", ".csv", ".log", ".ocr"):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            parsed = parse_media_text(content)
            return {
                "path": str(path),
                "exists": True,
                "media_type": "text/ocr",
                "size_bytes": size_bytes,
                "text": content,
                "structured": parsed,
            }
        except Exception as e:
            return {"path": str(path), "exists": True, "error": str(e), "text": ""}

    # If it's a binary image format
    if suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"):
        try:
            header_bytes = path.read_bytes()[:2048]
            # Extract ASCII strings safely from header
            decoded_ascii = header_bytes.decode("latin1", errors="ignore")
            printable_strings = re.findall(r"[A-Za-z0-9\s,.:/$\-+=\\(\)]{4,}", decoded_ascii)
            text_chunks = [s.strip() for s in printable_strings if len(s.strip()) > 5]
            
            synthetic_ocr = " ".join(text_chunks)
            parsed = parse_media_text(synthetic_ocr)
            
            return {
                "path": str(path),
                "exists": True,
                "media_type": f"image/{suffix.lstrip('.')}",
                "size_bytes": size_bytes,
                "text": synthetic_ocr,
                "structured": parsed,
                "b64_sample": base64.b64encode(header_bytes[:64]).decode("ascii"),
            }
        except Exception as e:
            return {"path": str(path), "exists": True, "error": str(e), "text": ""}

    return {
        "path": str(path),
        "exists": True,
        "media_type": "unknown",
        "size_bytes": size_bytes,
        "text": "",
    }

def scan_media_directory(directory: str | Path) -> list[dict[str, Any]]:
    """Scan a directory for local media files (images, receipts, transcripts)."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return []
    
    media_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".txt", ".ocr"}
    media_files = []
    for p in dir_path.iterdir():
        if p.is_file() and p.suffix.lower() in media_extensions:
            media_files.append(read_local_media_file(p))
    return media_files
