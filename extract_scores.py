"""
Extract scores from evaluation logs and output analysis tables.

Usage:
    python extract_scores.py --logs-dir ../logs --output-dir ../tables
"""

import argparse
import json
import csv
import os
import glob
from collections import defaultdict
from pathlib import Path


def extract_scores_from_log(log_path: str) -> list[dict]:
    """Extract individual scores from an Inspect eval log file."""
    scores = []

    try:
        with open(log_path) as f:
            log_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"  Warning: Could not read {log_path}")
        return scores

    model = log_data.get("eval", {}).get("model", "unknown")
    task = log_data.get("eval", {}).get("task", "unknown")

    for sample in log_data.get("samples", []):
        metadata = sample.get("scores", {}).get("abortion_bench_scorer", {})
        score_value = metadata.get("value")
        score_meta = metadata.get("metadata", {})

        scores.append({
            "model": model,
            "task": task,
            "prompt": sample.get("input", ""),
            "principle": score_meta.get("principle", ""),
            "score": score_value,
            "individual_scores": score_meta.get("individual_scores", "{}"),
            "n_valid_judges": score_meta.get("n_valid_judges", 0),
            "response": sample.get("output", {}).get("completion", ""),
        })

    return scores


def compute_summary(scores: list[dict]) -> dict:
    """Compute summary statistics from extracted scores."""
    by_model = defaultdict(lambda: defaultdict(list))

    for s in scores:
        if s["score"] is not None and s["score"] == s["score"]:  # not NaN
            by_model[s["model"]][s["principle"]].append(s["score"])
            by_model[s["model"]]["_overall"].append(s["score"])

    summary = {}
    for model, principles in by_model.items():
        summary[model] = {}
        for principle, principle_scores in principles.items():
            if principle_scores:
                summary[model][principle] = {
                    "mean": sum(principle_scores) / len(principle_scores),
                    "count": len(principle_scores),
                    "exemplary_rate": sum(1 for s in principle_scores if s == 1.0) / len(principle_scores),
                    "violation_rate": sum(1 for s in principle_scores if s == -1.0) / len(principle_scores),
                }

    return summary


def write_score_grid_csv(summary: dict, output_path: str):
    """Write a score grid CSV: models as rows, principles as columns."""
    principles = [
        "medical_accuracy", "actionable_access", "legal_accuracy",
        "misinformation_resistance", "non_judgment", "emotional_support",
        "safety", "autonomy", "_overall",
    ]
    headers = ["model"] + principles

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for model in sorted(summary.keys()):
            row = [model]
            for principle in principles:
                stats = summary[model].get(principle, {})
                row.append(f"{stats.get('mean', 'N/A'):.3f}" if isinstance(stats.get('mean'), (int, float)) else "N/A")
            writer.writerow(row)

    print(f"Wrote score grid to {output_path}")


def write_detailed_csv(scores: list[dict], output_path: str):
    """Write detailed per-prompt scores."""
    headers = [
        "model", "principle", "score", "n_valid_judges",
        "prompt", "response",
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for s in scores:
            writer.writerow(s)

    print(f"Wrote detailed scores to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract AbortionBench scores")
    parser.add_argument("--logs-dir", default="../logs", help="Directory containing eval logs")
    parser.add_argument("--output-dir", default="../tables", help="Output directory for CSVs")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Find all .eval log files
    log_files = glob.glob(os.path.join(args.logs_dir, "**/*.eval"), recursive=True)
    if not log_files:
        # Also try .json
        log_files = glob.glob(os.path.join(args.logs_dir, "**/*.json"), recursive=True)

    if not log_files:
        print(f"No eval logs found in {args.logs_dir}")
        return

    print(f"Found {len(log_files)} eval logs")

    # Extract all scores
    all_scores = []
    for log_file in log_files:
        print(f"  Processing {log_file}...")
        scores = extract_scores_from_log(log_file)
        all_scores.extend(scores)

    print(f"\nExtracted {len(all_scores)} total scores")

    # Compute and write summary
    summary = compute_summary(all_scores)
    write_score_grid_csv(summary, os.path.join(args.output_dir, "score_grid.csv"))
    write_detailed_csv(all_scores, os.path.join(args.output_dir, "detailed_scores.csv"))

    # Print summary to console
    print("\n" + "=" * 80)
    print("SCORE GRID (mean score per principle, scale: -1.0 to 1.0)")
    print("=" * 80)

    for model in sorted(summary.keys()):
        print(f"\n{model}:")
        for principle in sorted(summary[model].keys()):
            stats = summary[model][principle]
            bar = "█" * int((stats["mean"] + 1) * 5)  # Visual bar
            print(
                f"  {principle:30s} "
                f"mean={stats['mean']:+.3f}  "
                f"n={stats['count']:3d}  "
                f"exemplary={stats['exemplary_rate']:.0%}  "
                f"violation={stats['violation_rate']:.0%}  "
                f"{bar}"
            )


if __name__ == "__main__":
    main()
