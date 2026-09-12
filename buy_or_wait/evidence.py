"""Evidence policy: data rows are trusted; message/image text is never executable."""
from __future__ import annotations
import re
from .models import Row, pick

INSTRUCTION = re.compile(r"\b(ignore|override|system prompt|developer message|reveal|chain[- ]of[- ]thought)\b", re.I)

def resolve(rows: list[Row], user_id: str, kind: str) -> tuple[list[dict[str, str]], int]:
    accepted, ignored = [], 0
    for row in rows:
        value = pick(row.values, "user_id", "customer_id", "account_id")
        if value and value != user_id: continue
        text = pick(row.values, "text", "message", "caption", "ocr_text", "content")
        if INSTRUCTION.search(text):
            ignored += 1
            continue
        accepted.append(row.values)
    return accepted, ignored
