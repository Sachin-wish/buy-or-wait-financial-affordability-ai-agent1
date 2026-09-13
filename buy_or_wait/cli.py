from __future__ import annotations
import argparse, sys
from datetime import date
from pathlib import Path
from .api import evaluate, csv_output
from .evaluator import run_evaluation_pipeline, print_evaluation_summary

def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic and Multimodal Financial Affordability BUY OR WAIT Agent.")
    parser.add_argument("dataset", nargs="?", default=None, help="directory containing the CSV files and media files")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(), help="evaluation as-of date (YYYY-MM-DD)")
    parser.add_argument("--strategy", choices=["deterministic", "conservative", "optimistic", "multimodal_vlm"], default="deterministic", help="evaluation strategy")
    parser.add_argument("--output", "-o", type=Path, default=None, help="path to save output CSV file")
    parser.add_argument("--evaluate", "--benchmark", action="store_true", help="run evaluation workflow and multi-model benchmark")
    
    args = parser.parse_args(argv)
    
    if args.evaluate or (not args.dataset and not sys.stdin.isatty()):
        report = run_evaluation_pipeline()
        sys.stdout.write(print_evaluation_summary(report) + "\n")
        sys.stdout.flush()
        return

    if not args.dataset:
        parser.print_help()
        sys.exit(1)

    try:
        csv_text = csv_output(evaluate(args.dataset, args.as_of, strategy=args.strategy))
        if args.output:
            args.output.write_text(csv_text, encoding="utf-8")
        sys.stdout.write(csv_text)
        sys.stdout.flush()
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
