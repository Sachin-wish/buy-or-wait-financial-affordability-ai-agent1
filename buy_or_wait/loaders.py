from __future__ import annotations
import csv
from pathlib import Path
from typing import Any, Iterable
from .models import Row, pick
from .media import read_local_media_file, scan_media_directory

FILES = ("requests.csv", "financial_profiles.csv", "financial_events.csv",
         "request_payment_options.csv", "messages.csv", "images.csv", "exchange_rates.csv")

def load_csv(path: str | Path) -> list[Row]:
    path = Path(path)
    if not path.exists(): return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [Row({str(k).strip(): (v or "").strip() for k, v in row.items()},
                     str(path), n) for n, row in enumerate(csv.DictReader(handle), 2)]

def load_dataset(directory: str | Path) -> dict[str, Any]:
    root = Path(directory)
    dataset: dict[str, Any] = {name: load_csv(root / name) for name in FILES}
    
    # Process and ingest local media files
    local_media: list[dict[str, Any]] = []
    
    # Check subdirectories like root/images, root/media if they exist
    for sub in ("images", "media", "receipts", "docs"):
        subpath = root / sub
        if subpath.is_dir():
            local_media.extend(scan_media_directory(subpath))
            
    # Also scan root directly for loose media files (excluding CSVs)
    if root.is_dir():
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".ocr"):
                local_media.append(read_local_media_file(p))

    # Inspect images.csv rows for file path references
    enriched_images: list[Row] = []
    for row in dataset.get("images.csv", []):
        row_vals = dict(row.values)
        file_ref = pick(row_vals, "path", "image_path", "file_path", "filename", "file", "media_path", "uri")
        if file_ref:
            # Resolve relative to dataset directory or absolute
            cand = Path(file_ref)
            if not cand.is_absolute():
                cand = root / file_ref
            if cand.exists():
                media_info = read_local_media_file(cand)
                local_media.append(media_info)
                # If description/ocr_text was missing in CSV, populate from media file
                if not pick(row_vals, "description", "ocr_text", "caption", "text") and media_info.get("text"):
                    row_vals["description"] = media_info["text"]
        enriched_images.append(Row(row_vals, row.source, row.line))

    dataset["images.csv"] = enriched_images
    dataset["media_files"] = local_media
    return dataset

def require_headers(rows: Iterable[Row], required: set[str], filename: str) -> None:
    rows = list(rows)
    if not rows: return
    actual = {k.lower() for k in rows[0].values}
    missing = required - actual
    if missing: raise ValueError(f"{filename}: missing columns {sorted(missing)}")
