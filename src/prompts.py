"""Prompt construction and combinatorics for cross-lingual conflict evaluation.

Generates all experimental prompt conditions for each MKQA conflict item:
1. `closed_book`: Parametric prior probe (2 query languages = 2 runs/item).
2. `cross_lingual`: Counterbalanced cross-lingual conflict (2 language swaps
   x 2 query languages x 2 document orders = 8 runs/item).
3. `monolingual_baseline`: Translate-to-query-language conflict baseline
   (2 query languages x 2 document orders = 4 runs/item).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.dataset import ConflictExample

SYSTEM_PROMPT_EN = (
    "You are a factual question-answering assistant. "
    "Answer the question with ONLY the exact entity, year, or number. "
    "Do not explain or mention conflicting sources."
)

SYSTEM_PROMPT_KO = (
    "당신은 사실 기반 질의응답 도우미입니다. "
    "질문에 대해 부연 설명이나 문서 간 모순에 대한 언급 없이 오직 정답 개체명, 연도, 또는 숫자만 간결하게 답하세요."
)

SYSTEM_PROMPT_CLOSED_BOOK_EN = (
    "You are a factual question-answering assistant. "
    "Answer the question concisely with ONLY the exact entity, year, or number."
)

SYSTEM_PROMPT_CLOSED_BOOK_KO = (
    "당신은 사실 기반 질의응답 도우미입니다. "
    "질문에 대해 부연 설명 없이 오직 정답 개체명, 연도, 또는 숫자만 간결하게 답하세요."
)


@dataclass(frozen=True)
class PromptInstance:
    """A single fully specified inference prompt and its metadata."""

    run_id: str
    item_id: int
    mkqa_example_id: int
    category: str
    condition: str  # 'closed_book', 'cross_lingual', 'monolingual_baseline'
    query_lang: str  # 'en' or 'ko'
    pair_type: str  # 'none', 'pair1_enA_koB', 'pair2_koA_enB', 'mono_en', 'mono_ko'
    doc_order: str  # 'none', 'en_first', 'ko_first', 'a_first', 'b_first'
    english_claim: str  # 'A', 'B', or 'none'
    korean_claim: str  # 'A', 'B', or 'none'
    first_doc_claim: str  # 'A', 'B', or 'none'
    system_prompt: str
    user_prompt: str
    query_text: str
    doc1_text: str
    doc2_text: str
    claim_a_en: str
    claim_a_ko: str
    claim_b_en: str
    claim_b_ko: str

    def to_messages(self) -> list[dict[str, str]]:
        """Format as standard chat messages for instruction-tuned LLMs."""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "item_id": self.item_id,
            "mkqa_example_id": self.mkqa_example_id,
            "category": self.category,
            "condition": self.condition,
            "query_lang": self.query_lang,
            "pair_type": self.pair_type,
            "doc_order": self.doc_order,
            "english_claim": self.english_claim,
            "korean_claim": self.korean_claim,
            "first_doc_claim": self.first_doc_claim,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "query_text": self.query_text,
            "doc1_text": self.doc1_text,
            "doc2_text": self.doc2_text,
            "claim_a_en": self.claim_a_en,
            "claim_a_ko": self.claim_a_ko,
            "claim_b_en": self.claim_b_en,
            "claim_b_ko": self.claim_b_ko,
        }


def _format_context_user_prompt(
    query_lang: str,
    query_text: str,
    doc1_text: str,
    doc2_text: str,
    claim_a_target: str,
    claim_b_target: str,
    first_doc_claim: str,
) -> str:
    """Format the 2-document RAG prompt in either English or Korean.

    The candidate options are ordered to match `doc1` then `doc2` so that option
    ordering does not introduce an unmeasured positional confound.
    """
    if first_doc_claim == "A":
        opt1, opt2 = claim_a_target, claim_b_target
    else:
        opt1, opt2 = claim_b_target, claim_a_target

    if query_lang == "en":
        return (
            f"Document 1: {doc1_text}\n"
            f"Document 2: {doc2_text}\n\n"
            f"Question: {query_text}?\n"
            f"Based on the documents above, select the single correct answer "
            f"({opt1} or {opt2}) and output ONLY the answer:\n"
            f"Answer:"
        )
    if query_lang == "ko":
        q_clean = query_text.rstrip("?") + "?"
        return (
            f"문서 1: {doc1_text}\n"
            f"문서 2: {doc2_text}\n\n"
            f"질문: {q_clean}\n"
            f"위 문서들을 바탕으로 올바른 정답 하나({opt1} 또는 {opt2})를 선택하여 "
            f"오직 정답만 출력하세요:\n"
            f"정답:"
        )
    raise ValueError(f"Unsupported query_lang: {query_lang!r}")


def _format_closed_book_user_prompt(query_lang: str, query_text: str) -> str:
    """Format the closed-book prompt (no retrieved passages)."""
    if query_lang == "en":
        return (
            f"Question: {query_text}?\n"
            f"Output ONLY the exact entity, year, or number:\n"
            f"Answer:"
        )
    if query_lang == "ko":
        q_clean = query_text.rstrip("?") + "?"
        return (
            f"질문: {q_clean}\n"
            f"오직 정확한 개체명, 연도, 또는 숫자만 출력하세요:\n"
            f"정답:"
        )
    raise ValueError(f"Unsupported query_lang: {query_lang!r}")


def build_prompts_for_example(
    ex: ConflictExample,
    include_monolingual_baseline: bool = True,
) -> list[PromptInstance]:
    """Generate all prompt runs for a single `ConflictExample`.

    Args:
        ex: The `ConflictExample` item.
        include_monolingual_baseline: Whether to include the 4 monolingual
            conflict baseline runs in addition to the 10 core runs (2 closed-book
            + 8 cross-lingual conflict).

    Returns:
        List of 10 (or 14) `PromptInstance` objects.
    """
    prompts: list[PromptInstance] = []

    # 1. Closed-Book Baseline (2 runs: en, ko)
    for q_lang in ("en", "ko"):
        q_text = ex.query_en if q_lang == "en" else ex.query_ko
        sys_prompt = (
            SYSTEM_PROMPT_CLOSED_BOOK_EN
            if q_lang == "en"
            else SYSTEM_PROMPT_CLOSED_BOOK_KO
        )
        user_prompt = _format_closed_book_user_prompt(q_lang, q_text)
        prompts.append(
            PromptInstance(
                run_id=f"item{ex.id:03d}_closed_book_{q_lang}",
                item_id=ex.id,
                mkqa_example_id=ex.mkqa_example_id,
                category=ex.category,
                condition="closed_book",
                query_lang=q_lang,
                pair_type="none",
                doc_order="none",
                english_claim="none",
                korean_claim="none",
                first_doc_claim="none",
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                query_text=q_text,
                doc1_text="",
                doc2_text="",
                claim_a_en=ex.claim_a_en,
                claim_a_ko=ex.claim_a_ko,
                claim_b_en=ex.claim_b_en,
                claim_b_ko=ex.claim_b_ko,
            )
        )

    # 2. Cross-Lingual Conflict (2 pairs x 2 query_langs x 2 doc_orders = 8 runs)
    pair_specs = [
        # (pair_type, en_passage, ko_passage, english_claim, korean_claim)
        ("pair1_enA_koB", ex.passage_en_a, ex.passage_ko_b, "A", "B"),
        ("pair2_koA_enB", ex.passage_en_b, ex.passage_ko_a, "B", "A"),
    ]
    for pair_type, en_doc, ko_doc, en_claim, ko_claim in pair_specs:
        for q_lang in ("en", "ko"):
            q_text = ex.query_en if q_lang == "en" else ex.query_ko
            sys_prompt = SYSTEM_PROMPT_EN if q_lang == "en" else SYSTEM_PROMPT_KO
            claim_a_tgt = ex.claim_a_en if q_lang == "en" else ex.claim_a_ko
            claim_b_tgt = ex.claim_b_en if q_lang == "en" else ex.claim_b_ko

            for doc_order in ("en_first", "ko_first"):
                if doc_order == "en_first":
                    doc1, doc2 = en_doc, ko_doc
                    first_claim = en_claim
                else:
                    doc1, doc2 = ko_doc, en_doc
                    first_claim = ko_claim

                user_prompt = _format_context_user_prompt(
                    query_lang=q_lang,
                    query_text=q_text,
                    doc1_text=doc1,
                    doc2_text=doc2,
                    claim_a_target=claim_a_tgt,
                    claim_b_target=claim_b_tgt,
                    first_doc_claim=first_claim,
                )
                prompts.append(
                    PromptInstance(
                        run_id=f"item{ex.id:03d}_xling_{pair_type}_{q_lang}_{doc_order}",
                        item_id=ex.id,
                        mkqa_example_id=ex.mkqa_example_id,
                        category=ex.category,
                        condition="cross_lingual",
                        query_lang=q_lang,
                        pair_type=pair_type,
                        doc_order=doc_order,
                        english_claim=en_claim,
                        korean_claim=ko_claim,
                        first_doc_claim=first_claim,
                        system_prompt=sys_prompt,
                        user_prompt=user_prompt,
                        query_text=q_text,
                        doc1_text=doc1,
                        doc2_text=doc2,
                        claim_a_en=ex.claim_a_en,
                        claim_a_ko=ex.claim_a_ko,
                        claim_b_en=ex.claim_b_en,
                        claim_b_ko=ex.claim_b_ko,
                    )
                )

    # 3. Monolingual Translated-Context Conflict Baseline (2 query_langs x 2 orders = 4 runs)
    if include_monolingual_baseline:
        for q_lang in ("en", "ko"):
            q_text = ex.query_en if q_lang == "en" else ex.query_ko
            sys_prompt = SYSTEM_PROMPT_EN if q_lang == "en" else SYSTEM_PROMPT_KO
            claim_a_tgt = ex.claim_a_en if q_lang == "en" else ex.claim_a_ko
            claim_b_tgt = ex.claim_b_en if q_lang == "en" else ex.claim_b_ko
            doc_a = ex.passage_en_a if q_lang == "en" else ex.passage_ko_a
            doc_b = ex.passage_en_b if q_lang == "en" else ex.passage_ko_b
            pair_type = f"mono_{q_lang}"

            for doc_order in ("a_first", "b_first"):
                if doc_order == "a_first":
                    doc1, doc2 = doc_a, doc_b
                    first_claim = "A"
                else:
                    doc1, doc2 = doc_b, doc_a
                    first_claim = "B"

                user_prompt = _format_context_user_prompt(
                    query_lang=q_lang,
                    query_text=q_text,
                    doc1_text=doc1,
                    doc2_text=doc2,
                    claim_a_target=claim_a_tgt,
                    claim_b_target=claim_b_tgt,
                    first_doc_claim=first_claim,
                )
                prompts.append(
                    PromptInstance(
                        run_id=f"item{ex.id:03d}_mono_{q_lang}_{doc_order}",
                        item_id=ex.id,
                        mkqa_example_id=ex.mkqa_example_id,
                        category=ex.category,
                        condition="monolingual_baseline",
                        query_lang=q_lang,
                        pair_type=pair_type,
                        doc_order=doc_order,
                        english_claim="none",
                        korean_claim="none",
                        first_doc_claim=first_claim,
                        system_prompt=sys_prompt,
                        user_prompt=user_prompt,
                        query_text=q_text,
                        doc1_text=doc1,
                        doc2_text=doc2,
                        claim_a_en=ex.claim_a_en,
                        claim_a_ko=ex.claim_a_ko,
                        claim_b_en=ex.claim_b_en,
                        claim_b_ko=ex.claim_b_ko,
                    )
                )

    return prompts


def build_all_prompts(
    examples: list[ConflictExample],
    include_monolingual_baseline: bool = True,
) -> list[PromptInstance]:
    """Generate all prompt instances across the entire dataset."""
    all_prompts: list[PromptInstance] = []
    for ex in examples:
        all_prompts.extend(
            build_prompts_for_example(
                ex, include_monolingual_baseline=include_monolingual_baseline
            )
        )
    return all_prompts
