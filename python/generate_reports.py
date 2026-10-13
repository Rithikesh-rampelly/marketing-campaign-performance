"""Generate shareable CSV and JSON reports without opening the dashboard.

Example from the repository root::

    py -3.13 python/generate_reports.py --output-dir reports/generated

The output directory is intentionally ignored by Git so a local analyst can
regenerate reports without creating noisy commits.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


if __package__ in (None, ""):
    # Allow ``python python/generate_reports.py`` as well as ``python -m``.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import grouped_summaries, health_summary, load_data


def build_reports(output_dir: Path) -> dict[str, Path]:
    """Write all standard summaries and return their paths."""
    data = load_data()
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = grouped_summaries(data)
    outputs: dict[str, Path] = {}
    for name, summary in summaries.items():
        path = output_dir / f"{name}_performance.csv"
        summary.to_csv(path, index=False)
        outputs[name] = path

    health_path = output_dir / "health_report.json"
    health_path.write_text(
        json.dumps(health_summary(data), indent=2, allow_nan=False),
        encoding="utf-8",
    )
    outputs["health"] = health_path
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate marketing campaign analysis reports.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/generated"),
        help="Directory for generated CSV and JSON files (default: reports/generated)",
    )
    args = parser.parse_args()
    outputs = build_reports(args.output_dir)
    print(f"Generated {len(outputs)} reports in {args.output_dir.resolve()}")
    for path in outputs.values():
        print(f"- {path}")


if __name__ == "__main__":
    main()
