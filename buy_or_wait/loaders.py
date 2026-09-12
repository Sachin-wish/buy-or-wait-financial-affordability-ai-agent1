from __future__ import annotations
import csv
from pathlib import Path
from typing import Iterable
from .models import Row

FILES = ("requests.csv", "financial_profiles.csv", "financial_events.csv",
         "request_payment_options.csv", "messages.csv", "images.csv", "exchange_rates.csv")

def load_csv(path: str | Path) -> list[Row]:
    path = Path(path)
    if not path.exists(): return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [Row({str(k).strip(): (v or "").strip() for k, v in row.items()},
                     str(path), n) for n, row in enumerate(csv.DictReader(handle), 2)]

def load_dataset(directory: str | Path) -> dict[str, list[Row]]:
    root = Path(directory)
    return {name: load_csv(root / name) for name in FILES}

def require_headers(rows: Iterable[Row], required: set[str], filename: str) -> None:
    rows = list(rows)
    if not rows: return
    actual = {k.lower() for k in rows[0].values}
    missing = required - actual
    if missing: raise ValueError(f"{filename}: missing columns {sorted(missing)}")
