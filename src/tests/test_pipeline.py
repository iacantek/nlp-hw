"""Comprehensive unit, property, and stress tests for the mRAG conflict pipeline."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from src.build_dataset import RAW_MKQA_ITEMS, build_dataset_records
from src.dataset import load_conflict_dataset, validate_dataset
from src.export_tex import generate_latex_macros
from src.korean_utils import (
    count_hangul_chars,
    count_latin_chars,
    detect_output_language,
    get_batchim_info,
    is_language_consistent,
    resolve_korean_particles,
    select_particle,
)
from src.models import SimulatedModelBackend, resolve_model_id
from src.prompts import build_all_prompts, build_prompts_for_example
from src.run_experiment import load_checkpoint, run_experiment_pipeline
from src.scoring import (
    compute_concept_logprob,
    extract_claim_from_generation,
    logsumexp_pair,
    score_run_output,
)
from src.stats import (
    analyze_model_runs,
    evaluate_counterbalanced_subset,
    mcnemar_test,
    wilson_ci,
)


class TestKoreanUtils:
    """Stress-test Korean morphosyntactic particle resolution and script detection."""

    def test_hangul_batchim_detection(self) -> None:
        # '이란' ends in ㄴ (batchim=True, rieul=False)
        assert get_batchim_info("이란") == (True, False)
        # '터키' ends in vowel ㅣ (batchim=False, rieul=False)
        assert get_batchim_info("터키") == (False, False)
        # '몬트리올' ends in ㄹ (batchim=True, rieul=True)
        assert get_batchim_info("몬트리올") == (True, True)

    def test_numeric_batchim_detection(self) -> None:
        # 1 (일), 7 (칠), 8 (팔) have rieul batchim
        assert get_batchim_info("1") == (True, True)
        assert get_batchim_info("7") == (True, True)
        assert get_batchim_info("8") == (True, True)
        # 3 (삼), 6 (육), 0 (영) have non-rieul batchim
        assert get_batchim_info("3") == (True, False)
        assert get_batchim_info("6") == (True, False)
        assert get_batchim_info("10") == (True, False)
        # 2 (이), 4 (사), 5 (오), 9 (구) have no batchim
        assert get_batchim_info("2") == (False, False)
        assert get_batchim_info("4") == (False, False)
        assert get_batchim_info("5") == (False, False)
        assert get_batchim_info("9") == (False, False)

    def test_particle_selection_all_types(self) -> None:
        assert select_particle("이란", "은/는") == "은"
        assert select_particle("터키", "은/는") == "는"
        assert select_particle("탄소", "이/가") == "가"
        assert select_particle("텅스텐", "이/가") == "이"
        assert select_particle("만사 무사", "을/를") == "를"
        assert select_particle("아우구스투스 카이사르", "을/를") == "를"
        assert select_particle("아이작 뉴턴", "을/를") == "을"
        # '으로/로' special rule for rieul batchim
        assert select_particle("서울", "으로/로") == "로"
        assert select_particle("부산", "으로/로") == "으로"
        assert select_particle("파리", "으로/로") == "로"

    def test_resolve_korean_particles_in_sentence(self) -> None:
        s1 = resolve_korean_particles("정답은 이란{이/가} 아니라 터키{이다/다}.")
        assert s1 == "정답은 이란이 아니라 터키다."
        s2 = resolve_korean_particles("생리학에서 확장기{이라고/라고} 불린다.")
        assert s2 == "생리학에서 확장기라고 불린다."

    def test_script_and_language_consistency(self) -> None:
        assert count_hangul_chars("타우포호") == 4
        assert count_latin_chars("Lake Taupo") == 9
        assert detect_output_language("타우포호", "ko") == "ko"
        assert detect_output_language("Lake Taupo", "ko") == "en"
        assert detect_output_language("1935", "ko") == "neutral"
        assert is_language_consistent("1935", "ko") is True
        assert is_language_consistent("1935", "en") is True
        assert is_language_consistent("타우포호", "ko") is True
        assert is_language_consistent("Lake Taupo", "ko") is False


class TestDatasetAndPrompts:
    """Stress-test the 150-item MKQA dataset and prompt combinatorics."""

    def test_dataset_150_structure_and_balance(self) -> None:
        assert len(RAW_MKQA_ITEMS) == 150
        records = build_dataset_records()
        assert len(records) == 150

        examples = load_conflict_dataset()
        assert len(examples) == 150
        validate_dataset(examples)

        cats = [ex.category for ex in examples]
        assert cats.count("entity") == 50
        assert cats.count("date") == 50
        assert cats.count("number") == 50

        # Ensure zero unresolved particle markers remain in any passage
        for ex in examples:
            for passage in (
                ex.passage_en_a,
                ex.passage_en_b,
                ex.passage_ko_a,
                ex.passage_ko_b,
            ):
                assert "{" not in passage and "}" not in passage

    def test_all_150_items_unambiguous_extraction(self) -> None:
        """Verify all 150 x 4 surface claims extract cleanly without cross-claim collisions."""
        examples = load_conflict_dataset()
        for ex in examples:
            for surf_a in (ex.claim_a_en, ex.claim_a_ko):
                for wrapped in (surf_a, f"Answer: {surf_a}.", f"정답: {surf_a}"):
                    r_a = extract_claim_from_generation(
                        wrapped,
                        ex.claim_a_en,
                        ex.claim_a_ko,
                        ex.claim_b_en,
                        ex.claim_b_ko,
                    )
                    assert r_a["text_choice"] == "A", (
                        f"Failed A extraction on item {ex.id} ({ex.query_en}): {wrapped!r} -> {r_a}"
                    )
            for surf_b in (ex.claim_b_en, ex.claim_b_ko):
                for wrapped in (surf_b, f"Answer: {surf_b}.", f"정답: {surf_b}"):
                    r_b = extract_claim_from_generation(
                        wrapped,
                        ex.claim_a_en,
                        ex.claim_a_ko,
                        ex.claim_b_en,
                        ex.claim_b_ko,
                    )
                    assert r_b["text_choice"] == "B", (
                        f"Failed B extraction on item {ex.id} ({ex.query_en}): {wrapped!r} -> {r_b}"
                    )

    def test_prompt_combinatorics_per_item_and_full_dataset(self) -> None:
        examples = load_conflict_dataset()
        ex0 = examples[0]

        p_core = build_prompts_for_example(ex0, include_monolingual_baseline=False)
        assert len(p_core) == 10  # 2 closed-book + 8 cross-lingual

        p_full = build_prompts_for_example(ex0, include_monolingual_baseline=True)
        assert len(p_full) == 14  # 2 closed-book + 8 cross-lingual + 4 monolingual

        all_core = build_all_prompts(examples, include_monolingual_baseline=False)
        assert len(all_core) == 1500

        all_full = build_all_prompts(examples, include_monolingual_baseline=True)
        assert len(all_full) == 2100

        # Check uniqueness of run_ids
        run_ids = [p.run_id for p in all_full]
        assert len(set(run_ids)) == 2100


class TestScoringAndNumerics:
    """Stress-test entity extraction, numeric boundary safety, and log-prob math."""

    def test_numeric_boundary_no_substring_collision(self) -> None:
        # '100' must NOT match inside '1000'
        res = extract_claim_from_generation(
            generated_text="1000",
            claim_a_en="1000",
            claim_a_ko="1000",
            claim_b_en="100",
            claim_b_ko="100",
        )
        assert res["text_choice"] == "A"
        assert res["matched_a"] is True
        assert res["matched_b"] is False

        # '8' must NOT match inside '18'
        res2 = extract_claim_from_generation(
            generated_text="18",
            claim_a_en="8",
            claim_a_ko="8",
            claim_b_en="18",
            claim_b_ko="18",
        )
        assert res2["text_choice"] == "B"

    def test_document_reference_number_stripping(self) -> None:
        # "Document 1: 2" should select "2" (B), not "1" (A) from "Document 1"
        res = extract_claim_from_generation(
            generated_text="According to Document 1, the answer is 2.",
            claim_a_en="1",
            claim_a_ko="1",
            claim_b_en="2",
            claim_b_ko="2",
        )
        assert res["text_choice"] == "B"

    def test_hedging_both_claims_marked_as_abstain(self) -> None:
        res = extract_claim_from_generation(
            generated_text="Document 1 states Iran while Document 2 states Turkey.",
            claim_a_en="Iran",
            claim_a_ko="이란",
            claim_b_en="Turkey",
            claim_b_ko="터키",
        )
        assert res["text_choice"] == "abstain"
        assert res["matched_a"] is True
        assert res["matched_b"] is True

    def test_concept_logprob_no_double_counting_on_shared_numerals(self) -> None:
        # When EN and KO surface strings are identical ('1935'), should return logprob_en directly
        lp_shared = compute_concept_logprob("1935", "1935", -0.5, -0.5)
        assert abs(lp_shared - (-0.5)) < 1e-9

        # When EN and KO differ ('Iran' vs '이란'), should return logsumexp
        lp_diff = compute_concept_logprob("Iran", "이란", -1.0, -1.0)
        assert abs(lp_diff - logsumexp_pair(-1.0, -1.0)) < 1e-9


class TestStatisticalProperties:
    """Verify mathematical identities of EPR, McNemar's test, and Wilson CIs."""

    def test_pure_truth_model_gives_50_percent_epr(self) -> None:
        # Construct synthetic runs where the model ALWAYS picks Claim A (truth-driven)
        examples = load_conflict_dataset(limit_per_category=5)
        prompts = build_all_prompts(examples, include_monolingual_baseline=False)
        runs = []
        for p in prompts:
            if p.condition == "cross_lingual":
                runs.append(
                    score_run_output(
                        prompt_meta=p.to_dict(),
                        generated_text=p.claim_a_en,
                        logprob_a_en=-0.1,
                        logprob_a_ko=-0.1,
                        logprob_b_en=-5.0,
                        logprob_b_ko=-5.0,
                    )
                )
        res = evaluate_counterbalanced_subset(runs)
        assert abs(res["epr"] - 0.50) < 1e-9
        assert res["regime_counts"]["truth_consistent_A_to_A"] == res["n_counterbalanced_pairs"]
        assert res["regime_counts"]["en_flip_A_to_B"] == 0
        assert res["mcnemar"]["p_value_exact"] == 1.0

    def test_pure_english_following_model_gives_100_percent_epr(self) -> None:
        examples = load_conflict_dataset(limit_per_category=5)
        prompts = build_all_prompts(examples, include_monolingual_baseline=False)
        runs = []
        for p in prompts:
            if p.condition == "cross_lingual":
                en_is_a = p.english_claim == "A"
                gen = p.claim_a_en if en_is_a else p.claim_b_en
                runs.append(
                    score_run_output(
                        prompt_meta=p.to_dict(),
                        generated_text=gen,
                        logprob_a_en=-0.1 if en_is_a else -5.0,
                        logprob_a_ko=-0.1 if en_is_a else -5.0,
                        logprob_b_en=-5.0 if en_is_a else -0.1,
                        logprob_b_ko=-5.0 if en_is_a else -0.1,
                    )
                )
        res = evaluate_counterbalanced_subset(runs)
        assert abs(res["epr"] - 1.0) < 1e-9
        assert res["regime_counts"]["en_flip_A_to_B"] == res["n_counterbalanced_pairs"]
        assert res["mcnemar"]["p_value_exact"] < 1e-10

    def test_end_to_end_pipeline_and_checkpoint_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary1 = run_experiment_pipeline(
                models=["qwen"],
                backend="simulate",
                seed=42,
                limit_per_category=4,
                output_dir=tmpdir,
                resume=False,
                export_latex=False,
            )
            summary2 = run_experiment_pipeline(
                models=["qwen"],
                backend="simulate",
                seed=42,
                limit_per_category=4,
                output_dir=tmpdir,
                resume=True,
                export_latex=False,
            )
            epr1 = summary1["models"]["Qwen/Qwen2.5-7B-Instruct"][
                "cross_lingual_by_query_lang"
            ]["all"]["combined"]["epr"]
            epr2 = summary2["models"]["Qwen/Qwen2.5-7B-Instruct"][
                "cross_lingual_by_query_lang"
            ]["all"]["combined"]["epr"]
            assert abs(epr1 - epr2) < 1e-12
            ckpt_file = Path(tmpdir) / "runs_Qwen__Qwen2.5-7B-Instruct.jsonl"
            assert len(load_checkpoint(ckpt_file, expected_backend="simulate")) > 0
            assert len(load_checkpoint(ckpt_file, expected_backend="hf")) == 0
            macros_tex = generate_latex_macros(summary1)
            assert "\\newcommand{\\qwenEPRAll}" in macros_tex

    def test_huggingface_backend_candidate_scoring_with_mock(self) -> None:
        """Verify HuggingFaceModelBackend._score_candidates and evaluate_prompt logic via a lightweight stub."""
        import math
        from typing import Any
        from src.models import HuggingFaceModelBackend

        class DummyTensor:
            def __init__(self, data: Any):
                self.data = data

            @property
            def device(self) -> str:
                return "cpu"

            def __getitem__(self, idx: Any) -> "DummyTensor":
                if isinstance(idx, tuple) and len(idx) == 3:
                    b_idx, s_slice, _ = idx
                    row = self.data[b_idx][s_slice]
                    return DummyTensor(row)
                if isinstance(idx, tuple) and len(idx) == 2:
                    b_idx, s_slice = idx
                    return DummyTensor(self.data[b_idx][s_slice])
                return DummyTensor(self.data[idx])

            def float(self) -> "DummyTensor":
                return self

            def unsqueeze(self, dim: int) -> "DummyTensor":
                return self

            def squeeze(self, dim: int) -> "DummyTensor":
                return self

            def gather(self, dim: int, index: "DummyTensor") -> "DummyTensor":
                gathered = [
                    step_dist[tok_id]
                    for step_dist, tok_id in zip(self.data, index.data)
                ]
                return DummyTensor(gathered)

            def mean(self) -> "DummyTensor":
                val = sum(self.data) / max(1, len(self.data))
                return DummyTensor(val)

            def item(self) -> float:
                return float(self.data)

        class DummyTorch:
            long = "long"

            @staticmethod
            def tensor(data: Any, dtype: Any = None, device: Any = None) -> DummyTensor:
                return DummyTensor(data)

            @staticmethod
            def ones_like(t: DummyTensor) -> DummyTensor:
                return DummyTensor([[1 for _ in row] for row in t.data])

            @staticmethod
            def log_softmax(logits: DummyTensor, dim: int = -1) -> DummyTensor:
                out = []
                for row in logits.data:
                    m = max(row)
                    exps = [math.exp(x - m) for x in row]
                    z = math.log(sum(exps))
                    out.append([x - m - z for x in row])
                return DummyTensor(out)

            class no_grad:
                def __enter__(self) -> None:
                    return None

                def __exit__(self, *args: Any) -> None:
                    return None

        class DummyTokenizer:
            pad_token_id = 0
            eos_token_id = 1

            def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
                return [min(15, (ord(ch) % 14) + 2) for ch in text]

            def decode(self, token_ids: DummyTensor, skip_special_tokens: bool = True) -> str:
                return "Iran"

        class DummyModel:
            def parameters(self) -> Any:
                yield DummyTensor([0.0])

            def __call__(self, input_ids: DummyTensor, attention_mask: DummyTensor) -> Any:
                batch = input_ids.data
                vocab_size = 16
                # Assign higher logits to token IDs corresponding to "Iran"
                logits = []
                for seq in batch:
                    seq_logits = []
                    for pos in range(len(seq)):
                        next_tok = seq[pos + 1] if pos + 1 < len(seq) else 0
                        step = [0.0] * vocab_size
                        if b"Iran"[0] % 14 + 2 == next_tok or pos >= 0:
                            step[next_tok] = 2.5 if len(seq) <= 30 else 0.5
                        seq_logits.append(step)
                    logits.append(seq_logits)

                class Out:
                    pass

                o = Out()
                o.logits = DummyTensor(logits)
                return o

            def generate(self, **kwargs: Any) -> DummyTensor:
                inp = kwargs["input_ids"].data[0]
                return DummyTensor([inp + [5, 6, 7]])

        backend = object.__new__(HuggingFaceModelBackend)
        backend.torch = DummyTorch()
        backend.tokenizer = DummyTokenizer()
        backend.model = DummyModel()
        backend.max_new_tokens = 8

        examples = load_conflict_dataset(limit_per_category=1)
        prompt = build_all_prompts(examples, include_monolingual_baseline=False)[2]
        result = backend.evaluate_prompt(prompt)
        assert result["combined_choice"] in ("A", "B")
        assert isinstance(result["logprob_margin_a_minus_b"], float)

