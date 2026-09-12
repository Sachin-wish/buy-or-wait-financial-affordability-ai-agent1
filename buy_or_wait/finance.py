from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from .models import FinancialState, Option, pick, money, iso_date

def rates(rows) -> dict[tuple[str, str, date], Decimal]:
    out = {}
    for r in rows:
        d = iso_date(pick(r.values, "date", "rate_date"))
        if not d: continue
        base, quote = pick(r.values, "base_currency", "from_currency", "base").upper(), pick(r.values, "quote_currency", "to_currency", "quote").upper()
        try:
            value = money(pick(r.values, "rate", "exchange_rate"))
            if value > 0 and base and quote: out[(base, quote, d)] = value
        except (ValueError, TypeError): continue
    return out

def convert(amount: Decimal, source: str, target: str, on: date, table) -> Decimal:
    if source.upper() == target.upper(): return amount
    key = (source.upper(), target.upper(), on)
    if key not in table: raise ValueError(f"no exchange rate for {source}/{target} on {on.isoformat()}")
    return amount * table[key]

def reconstruct(user_id: str, profiles, events, messages, images, as_of: date, target_currency="USD", table=None) -> FinancialState:
    state = FinancialState(user_id=user_id, as_of=as_of, currency=target_currency)
    profile = next((r.values for r in profiles if pick(r.values, "user_id", "customer_id") == user_id), None)
    if profile:
        profile_currency = pick(profile, "currency", "base_currency", default=target_currency).upper()
        state.currency = target_currency.upper()
        def profile_money(value):
            amount = money(value)
            if profile_currency != state.currency:
                if not table:
                    state.conflicts.append("profile has no dated conversion rate")
                    return Decimal("0")
                return convert(amount, profile_currency, state.currency, as_of, table)
            return amount
        try:
            state.cash = profile_money(pick(profile, "cash", "balance", "available_cash"))
            state.income_monthly = profile_money(pick(profile, "monthly_income", "income"))
            state.recurring_spend_monthly = profile_money(pick(profile, "monthly_recurring_spend", "recurring_spend", "monthly_expenses"))
            state.debt_payment_monthly = profile_money(pick(profile, "monthly_debt_payment", "debt_payment"))
        except ValueError:
            state.conflicts.append("profile currency conversion unavailable")
    state.events = []
    for row in events:
        if pick(row.values, "user_id", "customer_id") != user_id: continue
        kind = pick(row.values, "type", "event_type", "category").lower()
        raw_date = pick(row.values, "date", "event_date")
        d = iso_date(raw_date)
        if raw_date and d is None:
            state.conflicts.append("invalid event date")
            continue
        d = d or as_of
        try:
            amount = money(pick(row.values, "amount", "value"))
        except ValueError:
            state.conflicts.append(f"invalid event amount on {d}")
            continue
        cur = pick(row.values, "currency", default=state.currency).upper()
        if cur != state.currency:
            try: amount = convert(amount, cur, state.currency, d, table)
            except ValueError: state.conflicts.append(f"unconverted event on {d}"); continue
        # Dated transactions are one-off cash flows.  Treating every income
        # event as monthly income permanently inflates the forecast.
        if "income" in kind: state.one_offs.append((d, -amount))
        elif "recurring" in kind: state.recurring_spend_monthly = max(Decimal("0"), amount)
        elif any(x in kind for x in ("expense", "spend", "debit", "debt")): state.one_offs.append((d, amount))
        elif "cash" in kind or "balance" in kind: state.cash = amount
        state.events.append(row.values)
    if state.cash < 0:
        state.conflicts.append("negative cash balance")
        state.cash = Decimal("0")
    return state

def forecast(state: FinancialState, start: date, days=90) -> dict[date, Decimal]:
    daily = (state.income_monthly - state.recurring_spend_monthly - state.debt_payment_monthly) / Decimal("30")
    result, balance = {}, state.cash
    oneoffs = {}
    for d, amount in state.one_offs: oneoffs[d] = oneoffs.get(d, Decimal("0")) + amount
    for i in range(days + 1):
        d = start + timedelta(days=i)
        if i: balance += daily
        balance -= oneoffs.get(d, Decimal("0"))
        result[d] = balance
    return result

def option_from(row, target, on, table) -> Option:
    cur = pick(row.values, "currency", default=target).upper()
    def cv(v): return convert(money(v), cur, target, on, table or {}) if cur != target else money(v)
    total = cv(pick(row.values, "total", "price", "amount"))
    upfront = cv(pick(row.values, "upfront", "down_payment", default=str(total)))
    try:
        recurring = cv(pick(row.values, "recurring", "installment_amount", default="0"))
        installments = int(pick(row.values, "installments", "number_of_payments", default="1"))
    except (ValueError, TypeError):
        raise ValueError("invalid payment option numeric field") from None
    if total < 0 or upfront < 0 or recurring < 0 or installments < 1:
        raise ValueError("payment option values must be non-negative and installments >= 1")
    raw_due = pick(row.values, "due_date", "date")
    due_date = iso_date(raw_due)
    if raw_due and due_date is None:
        raise ValueError("invalid payment option due date")
    return Option(pick(row.values, "option_name", "name", "payment_option", default="option"),
        pick(row.values, "kind", "type", default="full").lower(), total, upfront,
        recurring, installments,
        due_date, target)

def option_balances(option: Option, horizon: dict[date, Decimal], start: date):
    """Yield balances after an option's scheduled debits.

    Upfront is paid on ``start``; recurring payments are monthly from the
    due date (or 30 days after start when no due date is supplied).  This
    makes eligibility account for the purchase itself, not just the existing
    balance.
    """
    debits = {start: option.upfront}
    if option.installments <= 1:
        return horizon[start] >= option.upfront
    first = option.due_date or (start + timedelta(days=30))
    for n in range(option.installments):
        payment_date = first + timedelta(days=30 * n)
        if payment_date < start:
            payment_date = start
        if payment_date not in horizon:
            return False
        debits[payment_date] = debits.get(payment_date, Decimal("0")) + option.recurring
    cumulative = Decimal("0")
    for day, balance in horizon.items():
        cumulative += debits.get(day, Decimal("0"))
        if balance < cumulative:
            return False
    return True
