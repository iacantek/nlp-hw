"""Response extraction and dual scoring (exact entity match + answer log-probabilities).

Handles numeric boundary matching (preventing substring collisions such as '100'
inside '1000'), abstention/hedging detection when models mention both conflicting
claims, concept-level log-probability marginalization across scripts, and surface
language consistency tracking.
"""

from __future__ import annotations

import math
import re
from typing import Any

from src.korean_utils import detect_output_language, is_language_consistent

_DOC_REF_RE = re.compile(
    r"\b(?:document|doc|passage|source)\s*[12]\b|문서\s*[12]",
    flags=re.IGNORECASE,
)
_PREFIX_STRIP_RE = re.compile(
    r"^\s*(?:answer|정답|답변|답)\s*[:：\-]?\s*",
    flags=re.IGNORECASE,
)


def logsumexp_pair(log_p1: float, log_p2: float) -> float:
    """Numerically stable log(exp(log_p1) + exp(log_p2))."""
    if math.isinf(log_p1) and log_p1 < 0:
        return log_p2
    if math.isinf(log_p2) and log_p2 < 0:
        return log_p1
    m = max(log_p1, log_p2)
    return m + math.log(math.exp(log_p1 - m) + math.exp(log_p2 - m))


def compute_concept_logprob(
    claim_en: str,
    claim_ko: str,
    logprob_en: float,
    logprob_ko: float,
) -> float:
    """Compute concept-level log-probability across English and Korean surface forms.

    If `claim_en` and `claim_ko` are identical surface strings (e.g., Arabic numerals
    '1935' or '8'), returns `logprob_en` directly without double-counting. Otherwise,
    marginalizes over both surface realizations via `logsumexp_pair`.
    """
    if claim_en.strip().lower() == claim_ko.strip().lower():
        return logprob_en
    return logsumexp_pair(logprob_en, logprob_ko)


def _contains_candidate(text: str, candidate: str) -> bool:
    """Return True if `candidate` appears in `text` with proper token boundaries.

    For numeric candidates (e.g., '100', '5', '1935'), enforces `(?<!\\d)...(?!\\d)`
    so that '100' does not match inside '1000' and '8' does not match inside '18'.
    """
    cand = candidate.strip()
    if not cand:
        return False

    # Purely numeric candidate
    if re.fullmatch(r"\d+(?:\.\d+)?", cand):
        # Also allow comma-formatted numbers in generated text (e.g. '3,407' for '3407')
        plain_text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
        pattern = rf"(?<!\d){re.escape(cand)}(?!\d)"
        return re.search(pattern, plain_text) is not None

    # Text entity candidate (case-insensitive)
    # If ASCII Latin word(s), enforce word boundaries at alphanumeric edges
    if re.fullmatch(r"[A-Za-z0-9 ,.'\-]+", cand):
        pattern = rf"(?<![A-Za-z0-9]){re.escape(cand)}(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None

    # Hangul or mixed candidate
    return cand.lower() in text.lower()


def extract_claim_from_generation(
    generated_text: str,
    claim_a_en: str,
    claim_a_ko: str,
    claim_b_en: str,
    claim_b_ko: str,
) -> dict[str, Any]:
    """Extract whether `generated_text` selects Claim A, Claim B, or abstains.

    Returns:
        Dictionary with keys:
        - `text_choice`: 'A', 'B', or 'abstain'
        - `matched_a`: bool
        - `matched_b`: bool
        - `matched_surface_lang`: 'en', 'ko', 'shared', or 'none'
    """
    cleaned = _PREFIX_STRIP_RE.sub("", generated_text.strip())
    # Remove "Document 1" / "문서 1" references before matching small integers like '1' or '2'
    cleaned_no_doc_ref = _DOC_REF_RE.sub(" ", cleaned)

    match_a_en = _contains_candidate(cleaned_no_doc_ref, claim_a_en)
    match_a_ko = _contains_candidate(cleaned_no_doc_ref, claim_a_ko)
    match_b_en = _contains_candidate(cleaned_no_doc_ref, claim_b_en)
    match_b_ko = _contains_candidate(cleaned_no_doc_ref, claim_b_ko)

    matched_a = match_a_en or match_a_ko
    matched_b = match_b_en or match_b_ko

    # If both A and B are mentioned (e.g., hedging / reporting conflict), mark as abstain
    if matched_a and matched_b:
        return {
            "text_choice": "abstain",
            "matched_a": True,
            "matched_b": True,
            "matched_surface_lang": "none",
        }
    if not matched_a and not matched_b:
        return {
            "text_choice": "abstain",
            "matched_a": False,
            "matched_b": False,
            "matched_surface_lang": "none",
        }

    choice = "A" if matched_a else "B"
    m_en = match_a_en if choice == "A" else match_b_en
    m_ko = match_a_ko if choice == "A" else match_b_ko

    if claim_a_en.strip().lower() == claim_a_ko.strip().lower():
        surf_lang = "shared"
    elif m_en and not m_ko:
        surf_lang = "en"
    elif m_ko and not m_en:
        surf_lang = "ko"
    else:
        surf_lang = "shared"

    return {
        "text_choice": choice,
        "matched_a": matched_a,
        "matched_b": matched_b,
        "matched_surface_lang": surf_lang,
    }


def score_run_output(
    prompt_meta: dict[str, Any],
    generated_text: str,
    logprob_a_en: float,
    logprob_a_ko: float,
    logprob_b_en: float,
    logprob_b_ko: float,
) -> dict[str, Any]:
    """Combine generation extraction and answer-token log-probabilities for a single run."""
    claim_a_en = str(prompt_meta["claim_a_en"])
    claim_a_ko = str(prompt_meta["claim_a_ko"])
    claim_b_en = str(prompt_meta["claim_b_en"])
    claim_b_ko = str(prompt_meta["claim_b_ko"])
    query_lang = str(prompt_meta["query_lang"])

    extraction = extract_claim_from_generation(
        generated_text=generated_text,
        claim_a_en=claim_a_en,
        claim_a_ko=claim_a_ko,
        claim_b_en=claim_b_en,
        claim_b_ko=claim_b_ko,
    )

    concept_lp_a = compute_concept_logprob(
        claim_a_en, claim_a_ko, logprob_a_en, logprob_a_ko
    )
    concept_lp_b = compute_concept_logprob(
        claim_b_en, claim_b_ko, logprob_b_en, logprob_b_ko
    )
    query_lp_a = logprob_a_en if query_lang == "en" else logprob_a_ko
    query_lp_b = logprob_b_en if query_lang == "en" else logprob_b_ko

    logprob_choice = "A" if concept_lp_a >= concept_lp_b else "B"
    query_logprob_choice = "A" if query_lp_a >= query_lp_b else "B"
    logprob_margin_a_minus_b = concept_lp_a - concept_lp_b

    text_choice = extraction["text_choice"]
    # Combined decision: use exact text match when unambiguous, fall back to logprob_choice
    combined_choice = text_choice if text_choice in ("A", "B") else logprob_choice

    output_lang = detect_output_language(generated_text, query_lang=query_lang)
    lang_consistent = is_language_consistent(generated_text, target_lang=query_lang)

    # Determine whether the model selected the English claim or Korean claim
    en_claim = prompt_meta.get("english_claim", "none")
    first_claim = prompt_meta.get("first_doc_claim", "none")

    chose_english_logprob = (
        (logprob_choice == en_claim) if en_claim in ("A", "B") else None
    )
    chose_english_combined = (
        (combined_choice == en_claim) if en_claim in ("A", "B") else None
    )
    chose_english_text = (
        (text_choice == en_claim)
        if (en_claim in ("A", "B") and text_choice in ("A", "B"))
        else None
    )
    chose_first_doc = (
        (combined_choice == first_claim) if first_claim in ("A", "B") else None
    )

    return {
        **prompt_meta,
        "generated_text": generated_text,
        "text_choice": text_choice,
        "logprob_choice": logprob_choice,
        "query_logprob_choice": query_logprob_choice,
        "combined_choice": combined_choice,
        "abstained": text_choice == "abstain",
        "logprob_a_en": float(logprob_a_en),
        "logprob_a_ko": float(logprob_a_ko),
        "logprob_b_en": float(logprob_b_en),
        "logprob_b_ko": float(logprob_b_ko),
        "concept_logprob_a": float(concept_lp_a),
        "concept_logprob_b": float(concept_lp_b),
        "logprob_margin_a_minus_b": float(logprob_margin_a_minus_b),
        "chose_english_logprob": chose_english_logprob,
        "chose_english_combined": chose_english_combined,
        "chose_english_text": chose_english_text,
        "chose_first_doc": chose_first_doc,
        "chose_true_claim": combined_choice == "A",
        "output_lang": output_lang,
        "lang_consistent": lang_consistent,
        "matched_surface_lang": extraction["matched_surface_lang"],
    }
