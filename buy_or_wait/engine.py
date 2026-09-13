from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from .models import Decision, pick
from .finance import reconstruct, forecast, rates, option_from, option_balances
from .evidence import resolve

HEADERS = ("request_id", "decision", "amount_safe_to_pay", "earliest_safe_full_payment_date",
           "recommended_payment_option", "confidence", "rationale", "validation_status")

class AffordabilityEngine:
    def __init__(self, dataset, as_of: date | None = None, strategy: str = "deterministic"):
        self.data = dataset
        self.as_of = as_of or date.today()
        self.strategy = strategy.lower()
        self.rate_table = rates(dataset.get("exchange_rates.csv", []))

    def evaluate(self) -> list[Decision]:
        requests = self.data.get("requests.csv", [])
        out = []
        users = {pick(r.values, "user_id", "customer_id") for r in self.data.get("financial_profiles.csv", [])}
        for req in requests:
            rid, uid = pick(req.values, "request_id", "id"), pick(req.values, "user_id", "customer_id")
            if not rid or uid not in users:
                out.append(Decision(rid, "not_recommended", Decimal("0"), None, "", "low", "invalid request or unknown user", "invalid"))
                continue
            request_type = pick(req.values, "request_type", "type", "category").lower()
            if request_type in ("investment", "invest", "investment_request"):
                out.append(Decision(rid, "not_recommended", Decimal("0"), None, "", "high",
                                    "investment requests are outside purchase-affordability recommendations", "valid"))
                continue
            currency = pick(req.values, "currency", default="USD").upper()
            try:
                evidence = [resolve(self.data.get(x, []), uid, x) for x in ("messages.csv", "images.csv")]
                state = reconstruct(uid, self.data.get("financial_profiles.csv", []), self.data.get("financial_events.csv", []),
                                    evidence[0][0], evidence[1][0], self.as_of, currency, self.rate_table)
                state.untrusted_ignored = sum(item[1] for item in evidence)
            except (ValueError, TypeError, AttributeError):
                out.append(Decision(rid, "not_recommended", Decimal("0"), None, "", "low",
                                    "malformed financial input; no recommendation made", "invalid"))
                continue

            # Apply strategy adjustments if configured
            buffer_multiplier = Decimal("1.0")
            expense_stress = Decimal("1.0")
            if self.strategy == "conservative":
                buffer_multiplier = Decimal("1.25")
                expense_stress = Decimal("1.10")
            elif self.strategy == "optimistic":
                buffer_multiplier = Decimal("0.75")
                expense_stress = Decimal("0.95")

            effective_buffer = state.emergency_buffer * buffer_multiplier
            if expense_stress != Decimal("1.0"):
                state.recurring_spend_monthly *= expense_stress

            horizon = forecast(state, self.as_of)
            safe = max(Decimal("0"), min(horizon.values()) - effective_buffer)
            options, option_conflicts = [], 0
            for row in self.data.get("request_payment_options.csv", []):
                if pick(row.values, "request_id", "id") != rid: continue
                try:
                    options.append(option_from(row, currency, self.as_of, self.rate_table))
                except (ValueError, TypeError, AttributeError):
                    option_conflicts += 1
            def is_full(o):
                return o.kind in ("full", "full_payment", "cash") or o.installments == 1

            feasible = [
                o for o in options
                if (not is_full(o) or o.upfront >= o.total)
                and option_balances(o, horizon, self.as_of, buffer=effective_buffer)
            ]
            full = [o for o in feasible if is_full(o)]
            earliest = None
            if not full and not (option_conflicts and not options):
                full_options = [o for o in options if is_full(o)]
                for d, bal in horizon.items():
                    if any(bal >= (o.total + effective_buffer) and all(v - (o.total if day == d else Decimal("0")) >= effective_buffer
                                                   for day, v in horizon.items() if day >= d)
                               for o in full_options):
                        earliest = d
                        break
            chosen = min(feasible, key=lambda o: (o.kind not in ("full", "full_payment"), o.total), default=None)
            if chosen:
                decision = "buy" if chosen.kind in ("full", "full_payment", "cash") else "partial_payment" if chosen.kind == "partial" else "installments"
                rationale = "affordable within the 90-day forecast"
                confidence = "high" if not state.conflicts else "medium"
            elif earliest:
                decision, rationale, confidence = "wait", "full payment becomes affordable on the forecast date", "medium"
            else:
                decision, rationale, confidence = "not_recommended", "no payment option remains affordable in the 90-day forecast", "medium"
            ignored = f"; ignored {state.untrusted_ignored} untrusted evidence item(s)" if state.untrusted_ignored else ""
            conflict_count = len(state.conflicts) + option_conflicts
            if conflict_count:
                rationale += f"; {conflict_count} input conflict(s)" + ignored
            elif ignored:
                rationale += ignored
            out.append(Decision(rid, decision, safe, earliest, chosen.name if chosen else "", confidence, rationale,
                                "conflict" if conflict_count else "valid"))
        return out
