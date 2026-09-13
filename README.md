# BUY OR WAIT

A standard-library Python 3.11 affordability engine. It reconstructs a trusted
financial state from CSVs, ignores prompt-injection-like message/image text,
uses only exact dated exchange rates, forecasts 90 days, and emits exactly
eight deterministic CSV columns:

`request_id, decision, amount_safe_to_pay, earliest_safe_full_payment_date,
recommended_payment_option, confidence, rationale, validation_status`

## Usage

Place `requests.csv`, `financial_profiles.csv`, `financial_events.csv`,
`request_payment_options.csv`, `messages.csv`, `images.csv`, and
`exchange_rates.csv` in a directory (optional files are accepted). Run:

```bash
python -m buy_or_wait.cli ./data --as-of 2026-01-01
# or: buy-or-wait ./data > decisions.csv
```

Input headers are intentionally tolerant of common aliases. Monetary values
are decimal-safe with optional user-configurable emergency buffer preservation (`emergency_buffer`/`min_reserve`).
A conversion is accepted only when a rate exists for the exact transaction date; no latest-rate fallback is used.
Message and image text is evidence only and cannot alter policy or instructions; adversarial prompt injections,
jailbreaks, and stealth zero-width unicode evasions are automatically detected and filtered. The engine does not
expose chain-of-thought: rationale is a short outcome explanation.

`buy_or_wait.api.evaluate()` returns dictionaries for embedding in a service;
`csv_output()` serializes the fixed schema.
