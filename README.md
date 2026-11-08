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
  - Scientific computing & testing (`scipy >= 1.11.0`, `numpy >= 1.24.0, < 2.5.0`, `pytest >= 8.0.0`)
- **Models Evaluated:**
  - `Qwen/Qwen2.5-7B-Instruct`
  - `meta-llama/Llama-3.1-8B-Instruct` (automatically falls back to the open-weights mirror `unsloth/Meta-Llama-3.1-8B-Instruct` if `HF_TOKEN` is not set)
- **Random Seed:** All dataset sampling, qualitative example selection, and evaluation runs use the fixed deterministic seed `--seed 42`.

## Running on Google Colab (T4 GPU)

The full GPU experiment is packaged in [`src/colab_runner.ipynb`](src/colab_runner.ipynb):

1. **Open the Notebook:** Go to [Google Colab](https://colab.research.google.com/), select **File → Open notebook → GitHub**, enter `https://github.com/iacantek/nlp-hw` (branch `feat/hw-2`), and open `src/colab_runner.ipynb` (or upload `src/colab_runner.ipynb` directly).
2. **Select the T4 GPU Runtime:** Click **Runtime → Change runtime type**, set **Hardware accelerator** to **T4 GPU**, and click **Save**.
3. **Optional `HF_TOKEN` Setup:** To use the gated `meta-llama/Llama-3.1-8B-Instruct` repository, add `HF_TOKEN` under Colab **Secrets** (key icon in the left sidebar) and enable notebook access. If omitted, the runner automatically uses the open mirror `unsloth/Meta-Llama-3.1-8B-Instruct`.
4. **Execute All Cells:** Click **Runtime → Run all**. The notebook clones the repository into `nlp-hw/`, installs dependencies via `nlp-hw/requirements.txt`, runs the test suite, evaluates both models with incremental checkpointing in `nlp-hw/results/`, updates `nlp-hw/docs/tex/tex/00_results_macros.tex`, and downloads `results_bundle.zip`.

## Local Quickstart & Updating the LaTeX Manuscript

### 1. Local Installation & Verification

```bash
git clone https://github.com/iacantek/nlp-hw.git
cd nlp-hw
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Rebuild and validate the 150-item MKQA Cross-Lingual Conflict dataset
python3 -m src.build_dataset

# Run the complete unit and stress test suite
pytest -v
```

### 2. Updating the Paper from `results_bundle.zip`

After downloading `results_bundle.zip` from Google Colab, extract `results/experiment_results.json` into the local repository and run:

```bash
# Export concrete experiment numbers into docs/tex/tex/00_results_macros.tex
python3 -m src.export_tex --results results/experiment_results.json

# Compile the ACL manuscript PDF
cd docs/tex
pdflatex -interaction=nonstopmode acl_latex.tex
bibtex acl_latex
pdflatex -interaction=nonstopmode acl_latex.tex
pdflatex -interaction=nonstopmode acl_latex.tex
```
