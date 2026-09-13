"""Evidence policy: data rows are trusted; message/image text is never executable."""
from __future__ import annotations
import re
import unicodedata
from .models import Row, pick

# Comprehensive pattern for prompt injection, jailbreak attempts, and system override instructions
INSTRUCTION = re.compile(
    r"\b("
    r"ignore|disregard|override|bypass|jailbreak|system\s+prompt|developer\s+(?:message|mode)|"
    r"reveal|chain[- ]of[- ]thought|act\s+as|simulate|new\s+rules|prompt\s+injection|"
    r"forget\s+(?:all|previous|prior)|reset\s+(?:constraints|system|rules)|exfiltrate|"
    r"sudo|assistant\s+mode|unfiltered"
    r")\b",
    re.IGNORECASE
)

# Invisible / zero-width characters commonly used for bypass
ZERO_WIDTH_CHARS = re.compile(r"[\u200B-\u200D\uFEFF\u00A0\u200E\u200F\u202A-\u202E]")

def clean_text(text: str) -> str:
    """Normalize unicode and strip zero-width / stealth control characters."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", str(text))
    return ZERO_WIDTH_CHARS.sub("", normalized).strip()

def resolve(rows: list[Row], user_id: str, kind: str) -> tuple[list[dict[str, str]], int]:
    accepted, ignored = [], 0
    for row in rows:
        value = pick(row.values, "user_id", "customer_id", "account_id")
        if value and value != user_id:
            continue
        text = pick(row.values, "text", "message", "caption", "ocr_text", "content")
        cleaned = clean_text(text)
        if INSTRUCTION.search(cleaned) or INSTRUCTION.search(text):
            ignored += 1
            continue
        accepted.append(row.values)
    return accepted, ignored

