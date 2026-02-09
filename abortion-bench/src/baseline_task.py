"""
Baseline evaluation task for AbortionBench.

Evaluates models with no system prompt to assess default behavior
on abortion-related queries.
"""

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, MemoryDataset
from inspect_ai.solver import generate

from scorer import abortion_bench_scorer


def load_dataset(path: str = "data/abortion_bench.jsonl") -> MemoryDataset:
    """Load the AbortionBench dataset."""
    samples = []
    data_path = Path(__file__).parent.parent / path

    # Fall back to sample prompts if full dataset not yet generated
    if not data_path.exists():
        data_path = Path(__file__).parent.parent / "data" / "sample_prompts.jsonl"

    with open(data_path) as f:
        for line in f:
            item = json.loads(line)
            samples.append(
                Sample(
                    input=item["prompt"],
                    target="",  # No single correct answer; scored by rubric
                    metadata={
                        "principle": item["principle"],
                        "category": item.get("category", ""),
                    },
                )
            )

    return MemoryDataset(samples=samples, name="AbortionBench")


@task
def baseline_task() -> Task:
    """Baseline evaluation: no system prompt, tests default model behavior."""
    return Task(
        dataset=load_dataset(),
        solver=[generate()],
        scorer=abortion_bench_scorer(),
        name="abortion_bench_baseline",
    )
