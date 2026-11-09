"""Model inference backends for Google Colab T4 GPU and local CPU simulation.

Supports:
- Hugging Face Transformers (`Qwen/Qwen2.5-7B-Instruct`, `meta-llama/Llama-3.1-8B-Instruct`
  with automatic fallback to `unsloth/Meta-Llama-3.1-8B-Instruct` if `HF_TOKEN` is
  not provided for gated Meta weights).
- Memory-efficient 4-bit NF4 (`bitsandbytes`) and FP16 execution tailored for a
  single 16GB NVIDIA T4 GPU on Google Colab.
- Deterministic `SimulatedModelBackend` for fast local CPU dry-runs, pipeline
  verification, and stress-testing.
"""

from __future__ import annotations

import hashlib
import math
import os
import random
from typing import Any

from src.prompts import PromptInstance
from src.scoring import score_run_output

MODEL_ALIASES: dict[str, str] = {
    "qwen": "Qwen/Qwen2.5-7B-Instruct",
    "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
    "qwen-2.5-7b-instruct": "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct": "Qwen/Qwen2.5-7B-Instruct",
    "llama": "meta-llama/Llama-3.1-8B-Instruct",
    "llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct",
    "llama-3.1-8b-instruct": "meta-llama/Llama-3.1-8B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct": "meta-llama/Llama-3.1-8B-Instruct",
}

LLAMA_FALLBACK_REPO = "unsloth/Meta-Llama-3.1-8B-Instruct"


def resolve_model_id(model_name: str) -> str:
    """Resolve short aliases ('qwen', 'llama') to full Hugging Face repo IDs."""
    key = model_name.strip()
    return MODEL_ALIASES.get(key, MODEL_ALIASES.get(key.lower(), key))


class SimulatedModelBackend:
    """Deterministic simulation backend for local CPU testing and dry-runs.

    Models realistic parametric knowledge, cross-lingual English authority bias,
    query-language alignment, position bias, and script-dependent language drift.
    """

    def __init__(self, model_name: str = "Qwen/Qwen2.5-7B-Instruct", seed: int = 42):
        self.model_id = resolve_model_id(model_name)
        self.seed = int(seed)
        self.is_llama = "llama" in self.model_id.lower()

    def _rng_for_run(self, run_id: str) -> random.Random:
        digest = hashlib.sha256(
            f"{self.model_id}:{self.seed}:{run_id}".encode("utf-8")
        ).hexdigest()
        return random.Random(int(digest[:16], 16))

    def _item_parametric_known(self, item_id: int, query_lang: str) -> bool:
        digest = hashlib.sha256(
            f"{self.model_id}:{self.seed}:param:{item_id}:{query_lang}".encode("utf-8")
        ).hexdigest()
        u = (int(digest[:8], 16) % 10000) / 10000.0
        # Higher closed-book accuracy in EN (~64-68%) than KO (~42-48%), matching MKQA literature
        if query_lang == "en":
            thresh = 0.66 if not self.is_llama else 0.68
        else:
            thresh = 0.48 if not self.is_llama else 0.40
        # Make KO knowledge correlated with EN knowledge
        digest_base = hashlib.sha256(
            f"{self.model_id}:{self.seed}:param_base:{item_id}".encode("utf-8")
        ).hexdigest()
        u_base = (int(digest_base[:8], 16) % 10000) / 10000.0
        return (0.7 * u_base + 0.3 * u) < thresh

    def evaluate_prompt(self, prompt: PromptInstance) -> dict[str, Any]:
        rng = self._rng_for_run(prompt.run_id)
        meta = prompt.to_dict()

        known_en = self._item_parametric_known(prompt.item_id, "en")
        known_ko = self._item_parametric_known(prompt.item_id, "ko")
        known_in_query = known_en if prompt.query_lang == "en" else known_ko

        if prompt.condition == "closed_book":
            if known_in_query:
                lp_a = -0.35 + rng.gauss(0.0, 0.12)
                lp_b = -2.40 + rng.gauss(0.0, 0.25)
                gen = (
                    prompt.claim_a_en
                    if prompt.query_lang == "en"
                    else prompt.claim_a_ko
                )
            else:
                lp_a = -1.85 + rng.gauss(0.0, 0.25)
                lp_b = -1.75 + rng.gauss(0.0, 0.25)
                gen = "Unknown" if prompt.query_lang == "en" else "알 수 없음"

            return score_run_output(
                prompt_meta=meta,
                generated_text=gen,
                logprob_a_en=lp_a if prompt.query_lang == "en" else lp_a - 0.3,
                logprob_a_ko=lp_a if prompt.query_lang == "ko" else lp_a - 0.5,
                logprob_b_en=lp_b if prompt.query_lang == "en" else lp_b - 0.3,
                logprob_b_ko=lp_b if prompt.query_lang == "ko" else lp_b - 0.5,
            )

        if prompt.condition == "monolingual_baseline":
            # No cross-lingual asymmetry: driven by parametric truth + mild position bias
            truth_drive = 0.85 if known_in_query else 0.18
            pos_drive = 0.22 if prompt.first_doc_claim == "A" else -0.22
            margin = truth_drive + pos_drive + rng.gauss(0.0, 0.45)
            choice = "A" if margin >= 0.0 else "B"
            lp_a = -0.50 if choice == "A" else -1.50 - abs(margin)
            lp_b = -0.50 if choice == "B" else -1.50 - abs(margin)

            if rng.random() < 0.025:
                # Occasional hedging/abstention in free-form generation
                gen = (
                    f"The documents conflict between {prompt.claim_a_en} and {prompt.claim_b_en}."
                    if prompt.query_lang == "en"
                    else f"문서 간에 {prompt.claim_a_ko}와 {prompt.claim_b_ko}로 내용이 상충합니다."
                )
            else:
                if choice == "A":
                    gen = (
                        prompt.claim_a_en
                        if prompt.query_lang == "en"
                        else prompt.claim_a_ko
                    )
                else:
                    gen = (
                        prompt.claim_b_en
                        if prompt.query_lang == "en"
                        else prompt.claim_b_ko
                    )

            return score_run_output(
                prompt_meta=meta,
                generated_text=gen,
                logprob_a_en=lp_a if prompt.query_lang == "en" else lp_a - 0.4,
                logprob_a_ko=lp_a if prompt.query_lang == "ko" else lp_a - 0.4,
                logprob_b_en=lp_b if prompt.query_lang == "en" else lp_b - 0.4,
                logprob_b_ko=lp_b if prompt.query_lang == "ko" else lp_b - 0.4,
            )

        # Cross-lingual conflict condition
        # Competing forces:
        # 1. English document language authority (+en_weight toward whichever claim is in EN)
        # 2. Query language alignment (+q_weight toward whichever claim matches query_lang)
        # 3. Parametric prior knowledge (+truth_weight toward True Claim A if known)
        # 4. Document position (+pos_weight toward first_doc_claim)
        en_sign = 1.0 if prompt.english_claim == "A" else -1.0
        pos_sign = 1.0 if prompt.first_doc_claim == "A" else -1.0
        query_match_sign = (
            en_sign if prompt.query_lang == "en" else -en_sign
        )

        # Llama-3.1-8B is more English-centric; Qwen-2.5-7B has stronger multilingual alignment
        base_en_authority = 0.78 if self.is_llama else 0.56
        # Named entities with Latin vs Hangul script divergence exhibit stronger English attraction
        cat_boost = (
            0.18
            if prompt.category == "entity"
            else (0.04 if prompt.category == "date" else 0.0)
        )
        en_drive = (base_en_authority + cat_boost) * en_sign
        q_drive = (0.34 if not self.is_llama else 0.22) * query_match_sign
        truth_drive = (0.48 if known_in_query else 0.10)
        pos_drive = 0.16 * pos_sign

        net_margin = en_drive + q_drive + truth_drive + pos_drive + rng.gauss(0.0, 0.52)
        choice = "A" if net_margin >= 0.0 else "B"

        base_lp = -0.45
        other_lp = base_lp - max(0.08, abs(net_margin))
        lp_a = base_lp if choice == "A" else other_lp
        lp_b = base_lp if choice == "B" else other_lp

        # Simulate occasional hedging/abstention (~3%) and script drift on KO entity queries
        abstain_prob = 0.032 if not self.is_llama else 0.024
        if rng.random() < abstain_prob:
            gen = (
                f"Both {prompt.claim_a_en} and {prompt.claim_b_en} are stated."
                if prompt.query_lang == "en"
                else f"{prompt.claim_a_ko} 및 {prompt.claim_b_ko} 두 주장이 상충합니다."
            )
        else:
            drift_to_en = (
                prompt.query_lang == "ko"
                and prompt.category == "entity"
                and choice == prompt.english_claim
                and rng.random() < (0.24 if self.is_llama else 0.12)
            )
            use_en_surface = (prompt.query_lang == "en") or drift_to_en
            if choice == "A":
                gen = prompt.claim_a_en if use_en_surface else prompt.claim_a_ko
            else:
                gen = prompt.claim_b_en if use_en_surface else prompt.claim_b_ko

        return score_run_output(
            prompt_meta=meta,
            generated_text=gen,
            logprob_a_en=lp_a if prompt.query_lang == "en" else lp_a - 0.15,
            logprob_a_ko=lp_a if prompt.query_lang == "ko" else lp_a - 0.25,
            logprob_b_en=lp_b if prompt.query_lang == "en" else lp_b - 0.15,
            logprob_b_ko=lp_b if prompt.query_lang == "ko" else lp_b - 0.25,
        )


class HuggingFaceModelBackend:
    """Hugging Face Transformers backend optimized for Google Colab T4 GPUs."""

    def __init__(
        self,
        model_name: str,
        quantization: str = "4bit",
        max_new_tokens: int = 12,
        device_map: str = "auto",
    ):
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        transformers.logging.set_verbosity_error()

        self.torch = torch
        self.model_id = resolve_model_id(model_name)
        self.quantization = quantization.lower()
        self.max_new_tokens = int(max_new_tokens)

        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

        load_kwargs: dict[str, Any] = {
            "device_map": device_map,
            "trust_remote_code": True,
        }
        if hf_token:
            load_kwargs["token"] = hf_token

        if torch.cuda.is_available():
            if self.quantization == "4bit":
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
            elif self.quantization == "8bit":
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_8bit=True,
                )
            else:
                load_kwargs["torch_dtype"] = torch.float16
        else:
            load_kwargs["torch_dtype"] = torch.float32

        loaded_repo = self.model_id
        if "meta-llama/Llama-3.1-8B-Instruct" in loaded_repo and not hf_token:
            print(
                f"[Info] HF_TOKEN not set for gated repo {loaded_repo}; "
                f"loading open mirror {LLAMA_FALLBACK_REPO}..."
            )
            loaded_repo = LLAMA_FALLBACK_REPO

        tokenizer_kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "clean_up_tokenization_spaces": False,
        }
        if hf_token:
            tokenizer_kwargs["token"] = hf_token

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                loaded_repo, **tokenizer_kwargs
            )
            self.model = AutoModelForCausalLM.from_pretrained(loaded_repo, **load_kwargs)
        except Exception as exc:
            if "meta-llama/Llama-3.1-8B-Instruct" in loaded_repo:
                print(
                    f"[Warning] Could not load gated repo {loaded_repo} ({exc}). "
                    f"Falling back to open mirror {LLAMA_FALLBACK_REPO}..."
                )
                loaded_repo = LLAMA_FALLBACK_REPO
                self.tokenizer = AutoTokenizer.from_pretrained(
                    loaded_repo, **tokenizer_kwargs
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    loaded_repo, **load_kwargs
                )
            else:
                raise

        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        self.tokenizer.padding_side = "left"
        self.tokenizer.clean_up_tokenization_spaces = False

        stop_ids: list[int] = []
        gen_cfg = getattr(self.model, "generation_config", None)
        if gen_cfg is not None:
            default_max_len = getattr(
                getattr(self.model, "config", None), "max_length", 20
            )
            gen_cfg.max_length = default_max_len
            gen_cfg.max_new_tokens = None
            if gen_cfg.eos_token_id is not None:
                if isinstance(gen_cfg.eos_token_id, int):
                    stop_ids.append(int(gen_cfg.eos_token_id))
                elif isinstance(gen_cfg.eos_token_id, (list, tuple)):
                    stop_ids.extend(int(x) for x in gen_cfg.eos_token_id)

        if self.tokenizer.eos_token_id is not None:
            if isinstance(self.tokenizer.eos_token_id, int):
                if int(self.tokenizer.eos_token_id) not in stop_ids:
                    stop_ids.append(int(self.tokenizer.eos_token_id))
            elif isinstance(self.tokenizer.eos_token_id, (list, tuple)):
                for x in self.tokenizer.eos_token_id:
                    if int(x) not in stop_ids:
                        stop_ids.append(int(x))

        for nl in ("\n", "\n\n"):
            nl_ids = self.tokenizer.encode(nl, add_special_tokens=False)
            if len(nl_ids) == 1 and int(nl_ids[0]) not in stop_ids:
                stop_ids.append(int(nl_ids[0]))

        self._stop_token_ids: list[int] | None = stop_ids if stop_ids else None
        self.model.eval()

    def _format_prompt_text(self, prompt: PromptInstance) -> str:
        messages = prompt.to_messages()
        if hasattr(self.tokenizer, "apply_chat_template"):
            try:
                return str(
                    self.tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                    )
                )
            except Exception:
                pass
        return f"{prompt.system_prompt}\n\n{prompt.user_prompt}\n"

    def _decode_tokens(self, token_ids: Any) -> str:
        try:
            return str(
                self.tokenizer.decode(
                    token_ids,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )
            )
        except TypeError:
            return str(self.tokenizer.decode(token_ids, skip_special_tokens=True))

    @staticmethod
    def _extract_first_line(generated_text: str) -> str:
        for line in generated_text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    def _score_candidates(
        self, prompt_text: str, prompt_ids: list[int], candidates: list[str]
    ) -> dict[str, float]:
        """Compute length-normalized teacher-forced log-probabilities for a single prompt."""
        torch = self.torch
        unique_cands = list(dict.fromkeys(c.strip() for c in candidates if c.strip()))
        results: dict[str, float] = {}
        if not unique_cands:
            return results

        device = next(self.model.parameters()).device
        n_prefix = len(prompt_ids)
        pad_id = (
            self.tokenizer.pad_token_id
            if self.tokenizer.pad_token_id is not None
            else 0
        )

        seqs: list[list[int]] = []
        valid_cands: list[str] = []
        for cand in unique_cands:
            full_ids = self.tokenizer.encode(
                prompt_text + cand, add_special_tokens=False
            )
            if len(full_ids) <= n_prefix or full_ids[:n_prefix] != prompt_ids:
                cand_ids = self.tokenizer.encode(cand, add_special_tokens=False)
                full_ids = prompt_ids + cand_ids
            if len(full_ids) > n_prefix:
                seqs.append(full_ids)
                valid_cands.append(cand)
            else:
                results[cand] = -20.0

        if not seqs:
            return results

        max_len = max(len(s) for s in seqs)
        batch_ids = [s + [pad_id] * (max_len - len(s)) for s in seqs]
        batch_mask = [[1] * len(s) + [0] * (max_len - len(s)) for s in seqs]

        input_tensor = torch.tensor(batch_ids, dtype=torch.long, device=device)
        mask_tensor = torch.tensor(batch_mask, dtype=torch.long, device=device)

        with torch.no_grad():
            if hasattr(self.model, "config"):
                outputs = self.model(
                    input_ids=input_tensor,
                    attention_mask=mask_tensor,
                    use_cache=False,
                )
            else:
                outputs = self.model(
                    input_ids=input_tensor,
                    attention_mask=mask_tensor,
                )
            logits = outputs.logits

        for b_idx, (cand, full_ids) in enumerate(zip(valid_cands, seqs)):
            seq_len = len(full_ids)
            step_logits = logits[b_idx, n_prefix - 1 : seq_len - 1, :].float()
            log_probs = torch.log_softmax(step_logits, dim=-1)
            target_ids = torch.tensor(
                full_ids[n_prefix:seq_len], dtype=torch.long, device=device
            )
            token_lps = log_probs.gather(
                dim=-1, index=target_ids.unsqueeze(-1)
            ).squeeze(-1)
            mean_lp = float(token_lps.mean().item())
            results[cand] = mean_lp if not math.isinf(mean_lp) else -20.0

        return results

    def _score_candidates_batch(
        self,
        prompts: list[PromptInstance],
        prompt_texts: list[str],
        prompt_ids_list: list[list[int]],
        cand_chunk_size: int = 16,
    ) -> list[dict[str, float]]:
        """Compute length-normalized teacher-forced candidate log-probabilities across a batch of prompts."""
        torch = self.torch
        lp_maps: list[dict[str, float]] = [{} for _ in prompts]
        if not prompts:
            return lp_maps

        device = next(self.model.parameters()).device
        pad_id = (
            self.tokenizer.pad_token_id
            if self.tokenizer.pad_token_id is not None
            else 0
        )

        flat_items: list[tuple[int, str, int, list[int]]] = []
        for p_idx, (prompt, prompt_text, prompt_ids) in enumerate(
            zip(prompts, prompt_texts, prompt_ids_list)
        ):
            n_prefix = len(prompt_ids)
            cands = [
                prompt.claim_a_en,
                prompt.claim_a_ko,
                prompt.claim_b_en,
                prompt.claim_b_ko,
            ]
            unique_cands = list(dict.fromkeys(c.strip() for c in cands if c.strip()))
            for cand in unique_cands:
                full_ids = self.tokenizer.encode(
                    prompt_text + cand, add_special_tokens=False
                )
                if len(full_ids) <= n_prefix or full_ids[:n_prefix] != prompt_ids:
                    cand_ids = self.tokenizer.encode(cand, add_special_tokens=False)
                    full_ids = prompt_ids + cand_ids
                if len(full_ids) > n_prefix:
                    flat_items.append((p_idx, cand, n_prefix, full_ids))
                else:
                    lp_maps[p_idx][cand] = -20.0

        for start in range(0, len(flat_items), cand_chunk_size):
            chunk = flat_items[start : start + cand_chunk_size]
            seqs = [item[3] for item in chunk]
            max_len = max(len(s) for s in seqs)
            batch_ids = [s + [pad_id] * (max_len - len(s)) for s in seqs]
            batch_mask = [[1] * len(s) + [0] * (max_len - len(s)) for s in seqs]

            input_tensor = torch.tensor(batch_ids, dtype=torch.long, device=device)
            mask_tensor = torch.tensor(batch_mask, dtype=torch.long, device=device)

            with torch.no_grad():
                if hasattr(self.model, "config"):
                    outputs = self.model(
                        input_ids=input_tensor,
                        attention_mask=mask_tensor,
                        use_cache=False,
                    )
                else:
                    outputs = self.model(
                        input_ids=input_tensor,
                        attention_mask=mask_tensor,
                    )
                logits = outputs.logits

            for b_idx, (p_idx, cand, n_prefix, full_ids) in enumerate(chunk):
                seq_len = len(full_ids)
                step_logits = logits[b_idx, n_prefix - 1 : seq_len - 1, :].float()
                log_probs = torch.log_softmax(step_logits, dim=-1)
                target_ids = torch.tensor(
                    full_ids[n_prefix:seq_len], dtype=torch.long, device=device
                )
                token_lps = log_probs.gather(
                    dim=-1, index=target_ids.unsqueeze(-1)
                ).squeeze(-1)
                mean_lp = float(token_lps.mean().item())
                lp_maps[p_idx][cand] = mean_lp if not math.isinf(mean_lp) else -20.0

        return lp_maps

    def evaluate_batch(self, prompts: list[PromptInstance]) -> list[dict[str, Any]]:
        """Evaluate a batch of prompts in parallel (batched generation + batched candidate scoring)."""
        if not prompts:
            return []
        torch = self.torch
        device = next(self.model.parameters()).device
        pad_id = (
            self.tokenizer.pad_token_id
            if self.tokenizer.pad_token_id is not None
            else 0
        )

        prompt_texts = [self._format_prompt_text(p) for p in prompts]
        prompt_ids_list = [
            self.tokenizer.encode(txt, add_special_tokens=False)
            for txt in prompt_texts
        ]

        max_prompt_len = max(len(ids) for ids in prompt_ids_list)
        batch_input_ids = [
            [pad_id] * (max_prompt_len - len(ids)) + ids for ids in prompt_ids_list
        ]
        batch_attn_mask = [
            [0] * (max_prompt_len - len(ids)) + [1] * len(ids)
            for ids in prompt_ids_list
        ]

        input_tensor = torch.tensor(batch_input_ids, dtype=torch.long, device=device)
        attention_mask = torch.tensor(batch_attn_mask, dtype=torch.long, device=device)

        gen_kwargs: dict[str, Any] = {
            "input_ids": input_tensor,
            "attention_mask": attention_mask,
            "max_new_tokens": self.max_new_tokens,
            "do_sample": False,
            "pad_token_id": pad_id,
        }
        stop_ids = getattr(self, "_stop_token_ids", None)
        if stop_ids:
            gen_kwargs["eos_token_id"] = stop_ids

        with torch.no_grad():
            gen_ids = self.model.generate(**gen_kwargs)

        first_lines: list[str] = []
        for b_idx in range(len(prompts)):
            new_tokens = gen_ids[b_idx, max_prompt_len:]
            generated_text = self._decode_tokens(new_tokens).strip()
            first_lines.append(self._extract_first_line(generated_text))

        lp_maps = self._score_candidates_batch(prompts, prompt_texts, prompt_ids_list)

        scored_batch: list[dict[str, Any]] = []
        for prompt, first_line, lp_map in zip(prompts, first_lines, lp_maps):
            scored_batch.append(
                score_run_output(
                    prompt_meta=prompt.to_dict(),
                    generated_text=first_line,
                    logprob_a_en=lp_map.get(prompt.claim_a_en.strip(), -20.0),
                    logprob_a_ko=lp_map.get(prompt.claim_a_ko.strip(), -20.0),
                    logprob_b_en=lp_map.get(prompt.claim_b_en.strip(), -20.0),
                    logprob_b_ko=lp_map.get(prompt.claim_b_ko.strip(), -20.0),
                )
            )
        return scored_batch

    def evaluate_prompt(self, prompt: PromptInstance) -> dict[str, Any]:
        return self.evaluate_batch([prompt])[0]
