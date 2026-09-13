"""Evidence policy: data rows are trusted; message/image text is never executable.

Implements multi-layer defensive sanitization, zero-width stripping,
and adversarial prompt-injection / jailbreak detection for text and multimodal OCR inputs.
"""
from __future__ import annotations
import base64
import binascii
import re
import unicodedata
from typing import Any
from .models import Row, pick

# Comprehensive pattern for direct and indirect prompt injection, jailbreak attempts,
# system overrides, roleplaying, and markdown/tag exploits
INSTRUCTION = re.compile(
    r"\b("
    r"ignore|disregard|override|bypass|jailbreak|system\s+prompt|developer\s+(?:message|mode)|"
    r"reveal|chain[- ]of[- ]thought|act\s+as|simulate|new\s+rules|prompt\s+injection|"
    r"forget\s+(?:all|previous|prior|everything)|reset\s+(?:constraints|system|rules)|exfiltrate|"
    r"sudo|assistant\s+mode|unfiltered|always\s+approve|force\s+buy|mark\s+as\s+safe|"
    r"output\s+decision\s*=\s*buy|secret\s+key|admin\s+override"
    r")\b|"
    r"(?:<\s*(?:system|admin|eval|instruction|override)\s*>)|"
    r"(?:\[\s*(?:system|override|admin)\s*\])",
    re.IGNORECASE
)

# Invisible / zero-width characters commonly used for evasion and stealth injection
ZERO_WIDTH_CHARS = re.compile(r"[\u200B-\u200D\uFEFF\u00A0\u200E\u200F\u202A-\u202E\u0000-\u0008\u000B\u000C\u000E-\u001F]")

def clean_text(text: str) -> str:
    """Normalize unicode (NFKC) and strip zero-width and stealth control characters."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", str(text))
    cleaned = ZERO_WIDTH_CHARS.sub("", normalized)
    return cleaned.strip()

def check_disguised_payload(text: str) -> bool:
    """Check if the text contains encoded payloads (e.g. base64) that decode to instructions."""
    # Look for base64-like words of reasonable length
    for token in re.findall(r"\b[A-Za-z0-9+/=]{16,}\b", text):
        try:
            decoded = base64.b64decode(token.encode("ascii"), validate=True).decode("utf-8", errors="ignore")
            if INSTRUCTION.search(clean_text(decoded)):
                return True
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
    return False

def is_adversarial(text: str) -> bool:
    """Determine if a text snippet from messages or images contains adversarial content."""
    if not text:
        return False
    cleaned = clean_text(text)
    if INSTRUCTION.search(cleaned) or INSTRUCTION.search(text):
        return True
    if check_disguised_payload(text):
        return True
    return False

def resolve(rows: list[Row], user_id: str, kind: str) -> tuple[list[dict[str, str]], int]:
    """Filter and sanitize untrusted evidence rows (messages, OCR images, captions)."""
    accepted, ignored = [], 0
    for row in rows:
        value = pick(row.values, "user_id", "customer_id", "account_id")
        if value and value != user_id:
            continue
        text = pick(row.values, "text", "message", "caption", "ocr_text", "content", "description")
        if is_adversarial(text):
            ignored += 1
            continue
        accepted.append(row.values)
    return accepted, ignored
