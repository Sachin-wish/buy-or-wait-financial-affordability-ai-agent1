from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

@dataclass(frozen=True)
class Row:
    values: dict[str, str]
    source: str
    line: int

def pick(row: dict[str, Any], *names: str, default: str = "") -> str:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default

def money(value: str | Decimal | None) -> Decimal:
    if value is None or str(value).strip() == "": return Decimal("0")
    cleaned = str(value).replace(",", "").replace("$", "").strip()
    try:
        result = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        raise ValueError(f"invalid monetary value: {value!r}") from None
    if not result.is_finite():
        raise ValueError(f"non-finite monetary value: {value!r}")
    return result

def iso_date(value: str, default: date | None = None) -> date | None:
    if not value: return default
    try: return date.fromisoformat(value[:10])
    except ValueError: return default

@dataclass
class FinancialState:
    user_id: str
    as_of: date
    currency: str = "USD"
    cash: Decimal = Decimal("0")
    income_monthly: Decimal = Decimal("0")
    recurring_spend_monthly: Decimal = Decimal("0")
    debt_payment_monthly: Decimal = Decimal("0")
    one_offs: list[tuple[date, Decimal]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    untrusted_ignored: int = 0
    emergency_buffer: Decimal = Decimal("0")

@dataclass(frozen=True)
class Option:
    name: str
    kind: str
    total: Decimal
    upfront: Decimal
    recurring: Decimal = Decimal("0")
    installments: int = 1
    due_date: date | None = None
    currency: str = "USD"

@dataclass(frozen=True)
class Decision:
    request_id: str
    decision: str
    amount_safe_to_pay: Decimal
    earliest_safe_full_payment_date: date | None
    recommended_payment_option: str
    confidence: str
    rationale: str
    validation_status: str
