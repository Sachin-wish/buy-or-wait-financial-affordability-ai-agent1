# BUY OR WAIT

A standard-library Python 3.11+ financial affordability engine and evaluation framework. It reconstructs a trusted financial state from CSV files and local media files (images, receipts, OCR), immunizes against adversarial prompt-injections, uses exact dated exchange rates, forecasts a 90-day cashflow horizon, preserves emergency buffers, and emits exactly eight deterministic CSV columns:

`request_id, decision, amount_safe_to_pay, earliest_safe_full_payment_date, recommended_payment_option, confidence, rationale, validation_status`

---

## Setup Instructions

### 1. Prerequisites
- **Python 3.11+** installed on your system.
- Git (optional, for cloning).

### 2. Clone and Setup Environment

#### On Windows (PowerShell):
```powershell
# Clone the repository (if applicable)
git clone <repo-url>
cd buy-or-wait-financial-affordability-ai-agent1

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install in editable mode
pip install -e .
```

#### On macOS / Linux (Bash / Zsh):
```bash
# Clone the repository (if applicable)
git clone <repo-url>
cd buy-or-wait-financial-affordability-ai-agent1

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

### 3. Run Automated Tests
```bash
# Run unit tests across engine, media loaders, and evaluation workflows
python -m unittest discover tests
```

---

## Usage

### Run Affordability Evaluation on Dataset
Place `requests.csv`, `financial_profiles.csv`, `financial_events.csv`, `request_payment_options.csv`, `messages.csv`, `images.csv`, and `exchange_rates.csv` in your data directory (e.g. `./data`).

```bash
# Run CLI with an evaluation as-of date
python -m buy_or_wait.cli ./data --as-of 2026-09-13

# Save output directly to output.csv
python -m buy_or_wait.cli ./data --as-of 2026-09-13 -o output.csv

# Or using the installed console script
buy-or-wait ./data > output.csv
```

### Run Evaluation Workflow & Multi-Model Benchmark
```bash
# Run comprehensive multi-strategy benchmark suite
python -m buy_or_wait.evaluator

# Or via the CLI benchmark flag
python -m buy_or_wait.cli --benchmark
```

---

## Features & Policy Guardrails

- **Local Media & Multimodal Evidence**: Ingests local image files (`.png`, `.jpg`, `.webp`) and OCR transcripts, extracting vendor names, amounts, currencies, and dates.
- **Header Tolerance**: Input headers are tolerant of common aliases (`customer_id`/`user_id`, `balance`/`cash`, `monthly_expenses`/`recurring_spend`).
- **Emergency Buffer Preservation**: Preserves user-configured reserve buffers (`emergency_buffer`/`min_reserve`).
- **Exact-Date Foreign Exchange**: Currencies convert strictly on exact dated rates; missing rates trigger `validation_status="conflict"`.
- **Adversarial Defense**: Immunized against direct prompt injection, jailbreaks, markdown tags, base64 payloads, and stealth zero-width unicode evasions (`\u200B`).
- **Closed Schema Serialization**: Emits strictly the 8 defined CSV columns with two-decimal monetary precision without exposing chain-of-thought internals.

### Python API Integration
```python
from buy_or_wait.api import evaluate, csv_output

# Evaluate a dataset directory
decisions = evaluate("./data", as_of="2026-09-13")

# Serialize to exact schema CSV string
csv_text = csv_output(decisions)
print(csv_text)
```
