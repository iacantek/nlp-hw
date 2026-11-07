# Language Bias in Conflicting Multilingual RAG Evidence

This repository contains the benchmark dataset, evaluation pipeline, statistical analysis suite, Google Colab notebook, and ACL LaTeX manuscript for **"Language Bias in Conflicting Multilingual RAG Evidence"**.

## Repository Structure

```text
nlp-hw/
├── src/
│   ├── __init__.py
│   ├── korean_utils.py          # Korean particle resolution (은/는, 이/가, 을/를, 이라고/라고) & script detection
│   ├── build_dataset.py         # Deterministic builder for the 150-item MKQA conflict dataset
│   ├── dataset.py               # Dataset loader and integrity validator
│   ├── prompts.py               # Prompt combinatorics (Closed-Book, Cross-Lingual Conflict, Monolingual Baseline)
│   ├── models.py                # Hugging Face T4 GPU inference engine (4-bit NF4 / FP16) & simulation backend
│   ├── scoring.py               # Dual response scoring (exact entity extraction + concept log-probabilities)
│   ├── stats.py                 # EPR, McNemar's test, binomial test, Wilson 95% CIs, Wilcoxon test, ablations
│   ├── run_experiment.py        # Main CLI experiment runner with JSONL checkpointing & resume support
│   ├── export_tex.py            # Automated exporter from experiment_results.json to LaTeX macros
│   ├── colab_runner.ipynb       # Ready-to-run Google Colab T4 GPU notebook
│   ├── data/
│   │   └── mkqa_conflict_150.json  # Curated 150-item aligned EN-KO conflict benchmark from Apple MKQA
│   └── tests/
│       └── test_pipeline.py     # Unit, property, and stress test suite (1,800+ extraction & statistical checks)
├── docs/
│   └── tex/
│       ├── acl_latex.tex        # Main ACL LaTeX manuscript
│       ├── custom.bib           # Verified BibTeX bibliography
│       └── tex/                 # Modular section files and auto-generated results macros
├── requirements.txt             # Python package dependencies
└── pytest.ini                   # Pytest configuration
```

## Environment Specification

- **Hardware Environment (Full LLM Inference):** Google Colab (free tier) with a single NVIDIA T4 GPU (16 GB VRAM).
- **Software Environment:**
  - Python `3.10+`
  - PyTorch (`torch >= 2.1.0`)
  - Hugging Face (`transformers >= 4.44.0`, `accelerate >= 0.33.0`, `bitsandbytes >= 0.43.0`)
  - Scientific computing & testing (`scipy >= 1.11.0`, `numpy >= 1.24.0`, `pytest >= 8.0.0`)
- **Models Evaluated:**
  - `Qwen/Qwen2.5-7B-Instruct`
  - `meta-llama/Llama-3.1-8B-Instruct` (automatically falls back to the open weights mirror `unsloth/Meta-Llama-3.1-8B-Instruct` if `HF_TOKEN` is not set)
- **Random Seed:** All dataset sampling, qualitative example selection, and evaluation runs use the fixed deterministic seed `--seed 42`.

## Quickstart & Installation (Fresh Machine / Google Colab)

```bash
git clone https://github.com/iacantek/nlp-hw.git
cd nlp-hw
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1. Verify Dataset & Run Stress Tests

```bash
# Rebuild and validate the 150-item MKQA Cross-Lingual Conflict dataset
python3 -m src.build_dataset

# Run the complete unit and stress test suite
pytest -v
```

### 2. Reproducing Main Tables & Ablations on Google Colab (T4 GPU)

You can either open and run `src/colab_runner.ipynb` directly in Google Colab, or execute the following CLI commands to reproduce all tables in the paper (`Table 1`: Baselines & Main Cross-Lingual Conflict Results; `Table 2`: Pairwise Flip Regime Decomposition & McNemar's Tests; `Table 3`: Prior-Knowledge Stratification Ablation; `Table 4`: Entity Category & Document Order Ablations; `Table 5`: Qualitative Examples):

```bash
# Run full evaluation across Qwen-2.5-7B-Instruct and Llama-3.1-8B-Instruct
# (2,100 prompts/model: 300 closed-book + 1,200 cross-lingual conflict + 600 monolingual baseline)
python3 -m src.run_experiment \
    --backend hf \
    --models qwen llama \
    --quantization 4bit \
    --max-new-tokens 24 \
    --seed 42 \
    --output-dir results \
    --resume \
    --export-latex
```

- Incremental per-run checkpoints are written to `results/runs_Qwen__Qwen2.5-7B-Instruct.jsonl` and `results/runs_meta-llama__Llama-3.1-8B-Instruct.jsonl`.
- Aggregated metrics and statistical tests are saved to `results/experiment_results.json`.
- LaTeX macros for every table and inline statistic are automatically exported to `docs/tex/tex/00_results_macros.tex`.

### 3. Updating the LaTeX Manuscript from `experiment_results.json`

Once `results/experiment_results.json` is fetched from Google Colab:

```bash
# Export concrete experiment numbers into docs/tex/tex/00_results_macros.tex
python3 -m src.export_tex --results results/experiment_results.json

# Compile the ACL manuscript PDF
cd docs/tex
pdflatex -interaction=nonstopmode acl_latex.tex
biber acl_latex
pdflatex -interaction=nonstopmode acl_latex.tex
pdflatex -interaction=nonstopmode acl_latex.tex
```
