"""Dataset loading and validation for the MKQA Cross-Lingual Conflict Benchmark."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from src.build_dataset import DEFAULT_DATASET_PATH, save_dataset

VALID_CATEGORIES = ("entity", "date", "number")


@dataclass(frozen=True)
class ConflictExample:
    """A single aligned English-Korean factual conflict instance from MKQA."""

    id: int
    mkqa_example_id: int
    category: str
    query_en: str
    query_ko: str
    claim_a_en: str
    claim_a_ko: str
    claim_b_en: str
    claim_b_ko: str
    template_en: str
    template_ko: str
    passage_en_a: str
    passage_en_b: str
    passage_ko_a: str
    passage_ko_b: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConflictExample":
        return cls(
            id=int(data["id"]),
            mkqa_example_id=int(data["mkqa_example_id"]),
            category=str(data["category"]),
            query_en=str(data["query_en"]),
            query_ko=str(data["query_ko"]),
            claim_a_en=str(data["claim_a_en"]),
            claim_a_ko=str(data["claim_a_ko"]),
            claim_b_en=str(data["claim_b_en"]),
            claim_b_ko=str(data["claim_b_ko"]),
            template_en=str(data["template_en"]),
            template_ko=str(data["template_ko"]),
            passage_en_a=str(data["passage_en_a"]),
            passage_en_b=str(data["passage_en_b"]),
            passage_ko_a=str(data["passage_ko_a"]),
            passage_ko_b=str(data["passage_ko_b"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mkqa_example_id": self.mkqa_example_id,
            "category": self.category,
            "query_en": self.query_en,
            "query_ko": self.query_ko,
            "claim_a_en": self.claim_a_en,
            "claim_a_ko": self.claim_a_ko,
            "claim_b_en": self.claim_b_en,
            "claim_b_ko": self.claim_b_ko,
            "template_en": self.template_en,
            "template_ko": self.template_ko,
            "passage_en_a": self.passage_en_a,
            "passage_en_b": self.passage_en_b,
            "passage_ko_a": self.passage_ko_a,
            "passage_ko_b": self.passage_ko_b,
        }


def load_conflict_dataset(
    dataset_path: Path | str = DEFAULT_DATASET_PATH,
    categories: list[str] | None = None,
    limit_per_category: int | None = None,
) -> list[ConflictExample]:
    """Load and validate the 150-item MKQA Cross-Lingual Conflict dataset.

    If `dataset_path` does not exist yet, automatically builds it via
    `src.build_dataset.save_dataset`.
    """
    path = Path(dataset_path)
    if not path.exists():
        save_dataset(path)

    with open(path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    examples = [ConflictExample.from_dict(item) for item in raw_items]
    validate_dataset(examples)

    if categories is not None:
        allowed = set(categories)
        examples = [ex for ex in examples if ex.category in allowed]

    if limit_per_category is not None:
        if limit_per_category <= 0:
            raise ValueError("limit_per_category must be positive")
        counts: dict[str, int] = {}
        filtered: list[ConflictExample] = []
        for ex in examples:
            c = counts.get(ex.category, 0)
            if c < limit_per_category:
                filtered.append(ex)
                counts[ex.category] = c + 1
        examples = filtered

    return examples


def validate_dataset(examples: list[ConflictExample]) -> None:
    """Run integrity checks on a list of `ConflictExample` records."""
    if not examples:
        raise ValueError("Dataset cannot be empty")

    seen_ids: set[int] = set()
    seen_mkqa_ids: set[int] = set()

    for ex in examples:
        if ex.id in seen_ids:
            raise ValueError(f"Duplicate item id: {ex.id}")
        seen_ids.add(ex.id)

        if ex.mkqa_example_id in seen_mkqa_ids:
            raise ValueError(f"Duplicate mkqa_example_id: {ex.mkqa_example_id}")
        seen_mkqa_ids.add(ex.mkqa_example_id)

        if ex.category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category {ex.category!r} on item {ex.id}")

        if ex.claim_a_en.strip().lower() == ex.claim_b_en.strip().lower():
            raise ValueError(f"Identical EN claims on item {ex.id}")
        if ex.claim_a_ko.strip() == ex.claim_b_ko.strip():
            raise ValueError(f"Identical KO claims on item {ex.id}")

        if ex.claim_a_en not in ex.passage_en_a:
            raise ValueError(f"claim_a_en missing from passage_en_a on item {ex.id}")
        if ex.claim_b_en not in ex.passage_en_b:
            raise ValueError(f"claim_b_en missing from passage_en_b on item {ex.id}")
        if ex.claim_a_ko not in ex.passage_ko_a:
            raise ValueError(f"claim_a_ko missing from passage_ko_a on item {ex.id}")
        if ex.claim_b_ko not in ex.passage_ko_b:
            raise ValueError(f"claim_b_ko missing from passage_ko_b on item {ex.id}")
