from __future__ import annotations
import argparse, sys
from datetime import date
from .api import evaluate, csv_output

def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate purchase affordability.")
    parser.add_argument("dataset", help="directory containing the seven CSV files")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    try: sys.stdout.write(csv_output(evaluate(args.dataset, args.as_of)))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
