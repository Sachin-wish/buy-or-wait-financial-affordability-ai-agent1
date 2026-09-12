from __future__ import annotations
import csv, io
from dataclasses import asdict, is_dataclass
from pathlib import Path
from .engine import AffordabilityEngine, HEADERS
from .loaders import load_dataset

def evaluate(directory: str | Path, as_of=None) -> list[dict]:
    return [asdict(x) for x in AffordabilityEngine(load_dataset(directory), as_of).evaluate()]

def csv_output(results) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=HEADERS, lineterminator="\n")
    writer.writeheader()
    for result in results:
        row = asdict(result) if is_dataclass(result) else dict(result)
        # Keep the public serialization contract closed even when callers
        # supply mapping-like results with internal metadata.
        row = {field: row.get(field, "") for field in HEADERS}
        row["amount_safe_to_pay"] = f"{row['amount_safe_to_pay']:.2f}"
        row["earliest_safe_full_payment_date"] = row["earliest_safe_full_payment_date"] or ""
        writer.writerow(row)
    return stream.getvalue()
