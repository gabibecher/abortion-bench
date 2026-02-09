"""
Run AbortionBench evaluations across multiple models in parallel.

Usage:
    python run_parallel_evals.py --max-workers 4
    python run_parallel_evals.py --max-workers 2 --models openrouter/openai/gpt-5 openrouter/anthropic/claude-sonnet-4-20250514
"""

import argparse
import subprocess
import concurrent.futures
import sys
from datetime import datetime

DEFAULT_MODELS = [
    "openrouter/openai/gpt-5",
    "openrouter/openai/gpt-4.1",
    "openrouter/openai/gpt-4o-2024-11-20",
    "openrouter/anthropic/claude-sonnet-4-20250514",
    "openrouter/anthropic/claude-opus-4-20250514",
    "openrouter/google/gemini-2.5-pro",
    "openrouter/google/gemini-2.5-flash",
    "openrouter/meta-llama/llama-4-maverick",
    "openrouter/meta-llama/llama-4-scout",
    "openrouter/deepseek/deepseek-chat-v3-0324",
    "openrouter/xai/grok-3",
    "openrouter/mistralai/mistral-large-latest",
    "openrouter/amazon/nova-pro-v1",
    "openrouter/cohere/command-r-plus",
]


def run_evaluation(model: str, task_file: str = "src/baseline_task.py") -> dict:
    """Run a single model evaluation and return results."""
    start = datetime.now()
    print(f"[{start.strftime('%H:%M:%S')}] Starting: {model}")

    try:
        result = subprocess.run(
            ["inspect", "eval", task_file, "--model", model],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout per model
        )

        end = datetime.now()
        duration = (end - start).total_seconds()

        return {
            "model": model,
            "success": result.returncode == 0,
            "duration_seconds": duration,
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "model": model,
            "success": False,
            "duration_seconds": 3600,
            "stdout": "",
            "stderr": "TIMEOUT after 1 hour",
        }
    except Exception as e:
        return {
            "model": model,
            "success": False,
            "duration_seconds": 0,
            "stdout": "",
            "stderr": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Run AbortionBench evaluations in parallel")
    parser.add_argument("--max-workers", type=int, default=4, help="Max parallel evaluations")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="Models to evaluate")
    parser.add_argument("--task", default="src/baseline_task.py", help="Task file to run")
    args = parser.parse_args()

    print(f"Running AbortionBench on {len(args.models)} models with {args.max_workers} workers")
    print(f"Task: {args.task}")
    print("=" * 60)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(run_evaluation, model, args.task): model
            for model in args.models
        }

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            status = "✓" if result["success"] else "✗"
            print(
                f"  {status} {result['model']} "
                f"({result['duration_seconds']:.0f}s)"
            )
            if not result["success"] and result["stderr"]:
                print(f"    Error: {result['stderr'][:200]}")

    # Summary
    print("\n" + "=" * 60)
    successes = sum(1 for r in results if r["success"])
    print(f"Completed: {successes}/{len(results)} succeeded")

    if successes < len(results):
        print("\nFailed models:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['model']}: {r['stderr'][:100]}")


if __name__ == "__main__":
    main()
