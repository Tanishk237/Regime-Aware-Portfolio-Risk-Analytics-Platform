from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.regime.evaluation import evaluate_walk_forward_predictions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate leakage-safe, time-ordered regime predictions against independent labels."
    )
    parser.add_argument("input_csv", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/regime_validation_report.json"),
    )
    parser.add_argument("--fold-size", type=int, default=30)
    parser.add_argument("--minimum-samples", type=int, default=120)
    parser.add_argument("--minimum-folds", type=int, default=3)
    parser.add_argument("--minimum-balanced-accuracy", type=float, default=0.55)
    args = parser.parse_args()

    report = evaluate_walk_forward_predictions(
        pd.read_csv(args.input_csv),
        fold_size=args.fold_size,
        minimum_samples=args.minimum_samples,
        minimum_folds=args.minimum_folds,
        minimum_balanced_accuracy=args.minimum_balanced_accuracy,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(f"{args.output.suffix}.tmp")
    temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output), "validated": report["validated"]}))
    if not report["validated"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
