from __future__ import annotations
import csv, io
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any
from .engine import AffordabilityEngine, HEADERS
from .loaders import load_dataset
from .evaluator import run_evaluation_pipeline, print_evaluation_summary

def evaluate(directory: str | Path, as_of=None, strategy: str = "deterministic") -> list[dict]:
    return [asdict(x) for x in AffordabilityEngine(load_dataset(directory), as_of, strategy=strategy).evaluate()]

def evaluate_and_format(directory: str | Path, as_of=None, strategy: str = "deterministic") -> str:
    return csv_output(evaluate(directory, as_of, strategy=strategy))

def run_evaluation() -> dict[str, Any]:
    return run_evaluation_pipeline()

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
