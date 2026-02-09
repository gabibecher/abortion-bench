"""
Golden Questions evaluation task for AbortionBench.

Uses a subset of prompts that have been scored by human expert validators.
Used to validate the LLM-as-judge ensemble against human ground truth.
"""

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, MemoryDataset
from inspect_ai.solver import generate

from scorer import abortion_bench_scorer


def load_golden_dataset(
    path: str = "golden_questions/golden_questions.jsonl",
) -> MemoryDataset:
    """Load the human-validated golden questions dataset."""
    samples = []
    data_path = Path(__file__).parent.parent / path

    if not data_path.exists():
        raise FileNotFoundError(
            f"Golden questions dataset not found at {data_path}. "
            "Run the human validation process first. See golden_questions/README.md"
        )

    with open(data_path) as f:
        for line in f:
            item = json.loads(line)
            samples.append(
                Sample(
                    input=item["prompt"],
                    target="",
                    metadata={
                        "principle": item["principle"],
                        "human_scores": item.get("human_scores", {}),
                        "human_consensus_score": item.get("consensus_score"),
                    },
                )
            )

    return MemoryDataset(samples=samples, name="AbortionBench-Golden")


@task
def golden_questions_task() -> Task:
    """Evaluate on human-validated subset to calibrate LLM judges."""
    return Task(
        dataset=load_golden_dataset(),
        solver=[generate()],
        scorer=abortion_bench_scorer(),
        name="abortion_bench_golden",
    )
