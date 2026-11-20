"""Statistical aggregation, hypothesis testing, and ablation analysis for mRAG conflicts.

Implements:
- Counterbalanced English Preference Rate (EPR) and 4-regime pairwise breakdown:
  * English-Following Flip (A -> B)
  * Korean-Following Flip (B -> A)
  * Truth-Consistent (A -> A)
  * Counterfactual-Consistent (B -> B)
- McNemar's test (exact binomial + continuity-corrected chi2) on discordant flips
- Two-sided exact binomial test on EPR against 0.50 null
- Wilson 95% score confidence intervals for proportions
- Paired Wilcoxon signed-rank and paired t-test on cross-lingual log-probability shifts
- Prior-knowledge stratification (Known-Both, Known-EN-Only, Known-KO-Only, Unknown-Both)
- Truth Override Rate (TOR), Document Position Bias (FPR), and Language Consistency (LC).
"""

from __future__ import annotations

from collections import defaultdict
import math
from typing import Any

import numpy as np
from scipy import stats


def wilson_ci(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """Compute Wilson score confidence interval for a binomial proportion."""
    if total <= 0:
        return (0.0, 0.0)
    z = float(stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0))
    phat = successes / total
    denom = 1.0 + (z * z) / total
    center = (phat + (z * z) / (2.0 * total)) / denom
    half_width = (
        z
        * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * total)) / total)
        / denom
    )
    return (max(0.0, center - half_width), min(1.0, center + half_width))


def mcnemar_test(n_a_to_b: int, n_b_to_a: int) -> dict[str, float]:
    """Compute McNemar's test on discordant counterbalanced pairs (A->B vs B->A).

    Tests H0: P(A -> B) == P(B -> A), which is mathematically equivalent to
    testing H0: EPR == 0.50 while conditioning out concordant pairs (A->A, B->B).
    """
    b = int(n_a_to_b)
    c = int(n_b_to_a)
    n_disc = b + c
    if n_disc == 0:
        return {
            "discordant_total": 0,
            "chi2_cc": 0.0,
            "chi2_uncorrected": 0.0,
            "p_value_exact": 1.0,
            "p_value_chi2_cc": 1.0,
            "conditional_en_flip_rate": 0.5,
        }

    # Continuity-corrected and uncorrected McNemar chi2
    chi2_cc = ((abs(b - c) - 1.0) ** 2) / n_disc if abs(b - c) > 0 else 0.0
    chi2_uncorr = ((b - c) ** 2) / n_disc
    p_exact = float(stats.binomtest(b, n_disc, p=0.5, alternative="two-sided").pvalue)
    p_chi2 = float(stats.chi2.sf(chi2_cc, df=1))

    return {
        "discordant_total": n_disc,
        "chi2_cc": float(chi2_cc),
        "chi2_uncorrected": float(chi2_uncorr),
        "p_value_exact": p_exact,
        "p_value_chi2_cc": p_chi2,
        "conditional_en_flip_rate": b / n_disc,
    }


def compute_prior_knowledge_strata(
    scored_runs: list[dict[str, Any]],
) -> dict[int, str]:
    """Classify each item_id into prior-knowledge strata based on closed-book runs.

    Strata:
    - 'known_both': Correct (chose A via text match) in both EN and KO closed-book
    - 'known_en_only': Correct in EN closed-book, incorrect/abstained in KO closed-book
    - 'known_ko_only': Correct in KO closed-book, incorrect/abstained in EN closed-book
    - 'unknown_both': Incorrect/abstained in both EN and KO closed-book
    """
    cb_by_item: dict[int, dict[str, bool]] = defaultdict(dict)
    for r in scored_runs:
        if r.get("condition") == "closed_book":
            item_id = int(r["item_id"])
            q_lang = str(r["query_lang"])
            # In closed-book, knowing the fact requires generating Claim A (text_choice == 'A')
            known = r.get("text_choice") == "A"
            cb_by_item[item_id][q_lang] = known

    strata: dict[int, str] = {}
    for item_id, lang_map in cb_by_item.items():
        k_en = lang_map.get("en", False)
        k_ko = lang_map.get("ko", False)
        if k_en and k_ko:
            strata[item_id] = "known_both"
        elif k_en and not k_ko:
            strata[item_id] = "known_en_only"
        elif not k_en and k_ko:
            strata[item_id] = "known_ko_only"
        else:
            strata[item_id] = "unknown_both"
    return strata


def evaluate_counterbalanced_subset(
    xling_runs: list[dict[str, Any]],
    choice_field: str = "combined_choice",
) -> dict[str, Any]:
    """Compute counterbalanced conflict metrics on a subset of `cross_lingual` runs.

    Pairs each `pair1_enA_koB` run with its matched `pair2_koA_enB` run having the
    same `(item_id, query_lang, doc_order)`.
    """
    grouped: dict[tuple[int, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in xling_runs:
        if r.get("condition") != "cross_lingual":
            continue
        key = (int(r["item_id"]), str(r["query_lang"]), str(r["doc_order"]))
        grouped[key][str(r["pair_type"])] = r

    n_pairs = 0
    n_a_to_b = 0  # English-following flip: Pair1=A (EN), Pair2=B (EN)
    n_b_to_a = 0  # Korean-following flip:  Pair1=B (KO), Pair2=A (KO)
    n_a_to_a = 0  # Truth-consistent:       Pair1=A,      Pair2=A
    n_b_to_b = 0  # False-consistent:       Pair1=B,      Pair2=B
    n_abstain_pairs = 0

    total_en_choices = 0
    total_valid_single_runs = 0
    total_true_choices = 0
    total_first_doc_choices = 0
    total_abstain_runs = 0
    total_lang_consistent = 0
    total_runs = 0

    pair1_true_count = 0
    pair1_total = 0
    pair2_false_en_override_count = 0
    pair2_total = 0

    lp_shifts: list[float] = []

    for key, pair_dict in sorted(grouped.items()):
        r1 = pair_dict.get("pair1_enA_koB")
        r2 = pair_dict.get("pair2_koA_enB")
        if r1 is None or r2 is None:
            continue

        for r in (r1, r2):
            total_runs += 1
            if r.get("abstained", False):
                total_abstain_runs += 1
            if r.get("lang_consistent", False):
                total_lang_consistent += 1

            c = r.get(choice_field)
            if c in ("A", "B"):
                total_valid_single_runs += 1
                if c == r.get("english_claim"):
                    total_en_choices += 1
                if c == "A":
                    total_true_choices += 1
                if c == r.get("first_doc_claim"):
                    total_first_doc_choices += 1

        c1 = r1.get(choice_field)
        c2 = r2.get(choice_field)

        if c1 in ("A", "B"):
            pair1_total += 1
            if c1 == "A":
                pair1_true_count += 1
        if c2 in ("A", "B"):
            pair2_total += 1
            if c2 == "B":  # False English claim B overrides True Korean claim A
                pair2_false_en_override_count += 1

        # Continuous cross-lingual log-prob shift:
        # delta_lang = ((logP(A|Pair1) - logP(B|Pair1)) - (logP(A|Pair2) - logP(B|Pair2))) / 2
        m1 = float(r1.get("logprob_margin_a_minus_b", 0.0))
        m2 = float(r2.get("logprob_margin_a_minus_b", 0.0))
        lp_shifts.append((m1 - m2) / 2.0)

        if c1 not in ("A", "B") or c2 not in ("A", "B"):
            n_abstain_pairs += 1
            continue

        n_pairs += 1
        if c1 == "A" and c2 == "B":
            n_a_to_b += 1
        elif c1 == "B" and c2 == "A":
            n_b_to_a += 1
        elif c1 == "A" and c2 == "A":
            n_a_to_a += 1
        elif c1 == "B" and c2 == "B":
            n_b_to_b += 1

    # Marginal EPR over valid counterbalanced pairs:
    # Each (A->B) contributes 2 English choices; (A->A) and (B->B) contribute 1 each; (B->A) contributes 0.
    pair_en_successes = 2 * n_a_to_b + n_a_to_a + n_b_to_b
    pair_en_trials = 2 * n_pairs
    epr = (pair_en_successes / pair_en_trials) if pair_en_trials > 0 else 0.0
    epr_ci_low, epr_ci_high = wilson_ci(pair_en_successes, pair_en_trials)

    binom_p = (
        float(
            stats.binomtest(
                pair_en_successes, pair_en_trials, p=0.5, alternative="two-sided"
            ).pvalue
        )
        if pair_en_trials > 0
        else 1.0
    )

    mcnemar = mcnemar_test(n_a_to_b, n_b_to_a)

    # Continuous logprob shift test
    if len(lp_shifts) >= 2 and np.std(lp_shifts) > 1e-12:
        t_res = stats.ttest_1samp(lp_shifts, popmean=0.0)
        t_stat, t_pval = float(t_res.statistic), float(t_res.pvalue)
        try:
            w_res = stats.wilcoxon(lp_shifts)
            w_stat, w_pval = float(w_res.statistic), float(w_res.pvalue)
        except ValueError:
            w_stat, w_pval = 0.0, 1.0
    else:
        t_stat, t_pval = 0.0, 1.0
        w_stat, w_pval = 0.0, 1.0

    return {
        "n_counterbalanced_pairs": n_pairs,
        "n_abstain_pairs": n_abstain_pairs,
        "n_runs": total_runs,
        "epr": float(epr),
        "epr_ci_95": [float(epr_ci_low), float(epr_ci_high)],
        "epr_binom_p": binom_p,
        "regime_counts": {
            "en_flip_A_to_B": n_a_to_b,
            "ko_flip_B_to_A": n_b_to_a,
            "truth_consistent_A_to_A": n_a_to_a,
            "false_consistent_B_to_B": n_b_to_b,
        },
        "regime_rates": {
            "en_flip_A_to_B": (n_a_to_b / n_pairs) if n_pairs > 0 else 0.0,
            "ko_flip_B_to_A": (n_b_to_a / n_pairs) if n_pairs > 0 else 0.0,
            "truth_consistent_A_to_A": (n_a_to_a / n_pairs) if n_pairs > 0 else 0.0,
            "false_consistent_B_to_B": (n_b_to_b / n_pairs) if n_pairs > 0 else 0.0,
        },
        "mcnemar": mcnemar,
        "factual_accuracy": (
            (total_true_choices / total_valid_single_runs)
            if total_valid_single_runs > 0
            else 0.0
        ),
        "pair1_en_truth_accuracy": (
            (pair1_true_count / pair1_total) if pair1_total > 0 else 0.0
        ),
        "pair2_en_false_override_rate": (
            (pair2_false_en_override_count / pair2_total) if pair2_total > 0 else 0.0
        ),
        "first_doc_preference_rate": (
            (total_first_doc_choices / total_valid_single_runs)
            if total_valid_single_runs > 0
            else 0.0
        ),
        "abstention_rate": (
            (total_abstain_runs / total_runs) if total_runs > 0 else 0.0
        ),
        "language_consistency_rate": (
            (total_lang_consistent / total_runs) if total_runs > 0 else 0.0
        ),
        "logprob_shift": {
            "mean": float(np.mean(lp_shifts)) if lp_shifts else 0.0,
            "std": float(np.std(lp_shifts)) if lp_shifts else 0.0,
            "median": float(np.median(lp_shifts)) if lp_shifts else 0.0,
            "t_stat": t_stat,
            "t_pvalue": t_pval,
            "wilcoxon_stat": w_stat,
            "wilcoxon_pvalue": w_pval,
        },
    }


def evaluate_monolingual_baseline(
    mono_runs: list[dict[str, Any]],
    choice_field: str = "combined_choice",
) -> dict[str, Any]:
    """Evaluate the Monolingual Translated-Context Conflict Baseline."""
    by_lang: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in mono_runs:
        if r.get("condition") == "monolingual_baseline":
            by_lang[str(r["query_lang"])].append(r)

    summary: dict[str, Any] = {}
    for lang in ("en", "ko", "all"):
        subset = (
            mono_runs
            if lang == "all"
            else by_lang.get(lang, [])
        )
        subset = [r for r in subset if r.get("condition") == "monolingual_baseline"]
        n_total = len(subset)
        valid = [r for r in subset if r.get(choice_field) in ("A", "B")]
        n_valid = len(valid)
        n_true = sum(1 for r in valid if r.get(choice_field) == "A")
        n_false_override = sum(1 for r in valid if r.get(choice_field) == "B")
        n_first = sum(
            1 for r in valid if r.get(choice_field) == r.get("first_doc_claim")
        )
        n_abstain = sum(1 for r in subset if r.get("abstained", False))
        n_lc = sum(1 for r in subset if r.get("lang_consistent", False))

        acc = (n_true / n_valid) if n_valid > 0 else 0.0
        ci_low, ci_high = wilson_ci(n_true, n_valid)
        summary[lang] = {
            "n_runs": n_total,
            "n_valid": n_valid,
            "factual_accuracy": acc,
            "factual_accuracy_ci_95": [ci_low, ci_high],
            "false_override_rate": (n_false_override / n_valid) if n_valid > 0 else 0.0,
            "first_doc_preference_rate": (n_first / n_valid) if n_valid > 0 else 0.0,
            "abstention_rate": (n_abstain / n_total) if n_total > 0 else 0.0,
            "language_consistency_rate": (n_lc / n_total) if n_total > 0 else 0.0,
        }
    return summary


def evaluate_closed_book_baseline(
    scored_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate closed-book parametric accuracy in English and Korean."""
    cb_runs = [r for r in scored_runs if r.get("condition") == "closed_book"]
    strata = compute_prior_knowledge_strata(scored_runs)
    strata_counts: dict[str, int] = defaultdict(int)
    for s in strata.values():
        strata_counts[s] += 1

    by_lang: dict[str, Any] = {}
    for lang in ("en", "ko"):
        sub = [r for r in cb_runs if r.get("query_lang") == lang]
        n = len(sub)
        n_correct_text = sum(1 for r in sub if r.get("text_choice") == "A")
        n_correct_lp = sum(1 for r in sub if r.get("logprob_choice") == "A")
        n_lc = sum(1 for r in sub if r.get("lang_consistent", False))
        ci_low, ci_high = wilson_ci(n_correct_text, n)
        by_lang[lang] = {
            "n_items": n,
            "exact_accuracy": (n_correct_text / n) if n > 0 else 0.0,
            "exact_accuracy_ci_95": [ci_low, ci_high],
            "logprob_accuracy": (n_correct_lp / n) if n > 0 else 0.0,
            "language_consistency_rate": (n_lc / n) if n > 0 else 0.0,
        }

    n_items = len(strata)
    return {
        "by_query_lang": by_lang,
        "strata_counts": {
            "known_both": strata_counts.get("known_both", 0),
            "known_en_only": strata_counts.get("known_en_only", 0),
            "known_ko_only": strata_counts.get("known_ko_only", 0),
            "unknown_both": strata_counts.get("unknown_both", 0),
            "total_items": n_items,
        },
    }


def analyze_model_runs(
    scored_runs: list[dict[str, Any]],
    model_name: str = "model",
) -> dict[str, Any]:
    """Run the complete suite of main, baseline, and ablation analyses for a model."""
    xling_runs = [r for r in scored_runs if r.get("condition") == "cross_lingual"]
    mono_runs = [r for r in scored_runs if r.get("condition") == "monolingual_baseline"]
    strata_by_item = compute_prior_knowledge_strata(scored_runs)

    # 1. Overall & By Query Language (Combined, LogProb-only, Text-only)
    by_query_lang: dict[str, Any] = {}
    for q_lang in ("en", "ko", "all"):
        sub = (
            xling_runs
            if q_lang == "all"
            else [r for r in xling_runs if r.get("query_lang") == q_lang]
        )
        by_query_lang[q_lang] = {
            "combined": evaluate_counterbalanced_subset(sub, "combined_choice"),
            "logprob": evaluate_counterbalanced_subset(sub, "logprob_choice"),
            "text_only": evaluate_counterbalanced_subset(sub, "text_choice"),
        }

    # 2. Ablation 1: By Prior Knowledge Stratum (Known vs Unknown, and 4-way strata)
    by_prior_knowledge: dict[str, Any] = {}
    for stratum in (
        "known_both",
        "known_en_only",
        "known_ko_only",
        "unknown_both",
        "any_known",
    ):
        if stratum == "any_known":
            sub = [
                r
                for r in xling_runs
                if strata_by_item.get(int(r["item_id"])) != "unknown_both"
            ]
        else:
            sub = [
                r
                for r in xling_runs
                if strata_by_item.get(int(r["item_id"])) == stratum
            ]
        by_prior_knowledge[stratum] = {
            "all": evaluate_counterbalanced_subset(sub, "combined_choice"),
            "en": evaluate_counterbalanced_subset(
                [r for r in sub if r.get("query_lang") == "en"], "combined_choice"
            ),
            "ko": evaluate_counterbalanced_subset(
                [r for r in sub if r.get("query_lang") == "ko"], "combined_choice"
            ),
        }

    # 3. Ablation 2: By Answer Category / Script Divergence (entity vs date vs number)
    by_category: dict[str, Any] = {}
    for cat in ("entity", "date", "number"):
        sub = [r for r in xling_runs if r.get("category") == cat]
        by_category[cat] = {
            "all": evaluate_counterbalanced_subset(sub, "combined_choice"),
            "en": evaluate_counterbalanced_subset(
                [r for r in sub if r.get("query_lang") == "en"], "combined_choice"
            ),
            "ko": evaluate_counterbalanced_subset(
                [r for r in sub if r.get("query_lang") == "ko"], "combined_choice"
            ),
        }

    # 4. Ablation 3: By Document Order (en_first vs ko_first)
    by_doc_order: dict[str, Any] = {}
    for order in ("en_first", "ko_first"):
        sub = [r for r in xling_runs if r.get("doc_order") == order]
        by_doc_order[order] = {
            "all": evaluate_counterbalanced_subset(sub, "combined_choice"),
            "en": evaluate_counterbalanced_subset(
                [r for r in sub if r.get("query_lang") == "en"], "combined_choice"
            ),
            "ko": evaluate_counterbalanced_subset(
                [r for r in sub if r.get("query_lang") == "ko"], "combined_choice"
            ),
        }

    return {
        "model_name": model_name,
        "closed_book": evaluate_closed_book_baseline(scored_runs),
        "monolingual_baseline": evaluate_monolingual_baseline(
            mono_runs, "combined_choice"
        ),
        "cross_lingual_by_query_lang": by_query_lang,
        "ablation_by_prior_knowledge": by_prior_knowledge,
        "ablation_by_category": by_category,
        "ablation_by_doc_order": by_doc_order,
    }
