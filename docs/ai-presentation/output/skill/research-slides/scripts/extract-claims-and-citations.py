#!/usr/bin/env python3
"""
extract-claims-and-citations.py

Automated helper for Step 1 (Summarize) of the `research-slides` skill.
Scans an input research proposal or paper (.tex, .md, .txt, or .pdf) and an
optional BibTeX (.bib) file to extract:
1. Document sections and candidate sentences for Motivation, Research Question,
   Hypothesis, Falsification, and Experimental Design.
2. Numeric expressions and experimental combinatorics to audit for internal
   discrepancies.
3. Every cited paper (author, year, title, venue/DOI, and in-text sentences
   showing what the author claims each paper demonstrates).

Usage:
  python3 extract-claims-and-citations.py --source <proposal_or_paper> [--bib <refs.bib>] [--out <report.json>]
"""

import argparse
import json
import os
import re
import sys


PILLAR_KEYWORDS = {
    "motivation_and_gap": [
        "however", "remains unclear", "gap", "not directly proven",
        "prior work", "recent studies", "risk", "preferentially", "bias"
    ],
    "research_question": [
        "research question", "does it", "do they", "when a", "whether", "?"
    ],
    "hypothesis_and_falsification": [
        "hypothesize", "hypothesis", "predict", "falsif", "disprove",
        "prove wrong", "if the model", "switch", "favor"
    ],
    "design_and_analysis": [
        "dataset", "baseline", "control", "evaluate", "model", "metric",
        "test", "template", "pair", "query"
    ],
}


def read_source_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(path)
            return "\n".join(page.get_text("text") for page in doc)
        except Exception:
            pass
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            sys.stderr.write(f"Warning: Could not parse PDF text directly ({e}); pass .tex or .md if available.\n")
            return ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def clean_latex(text):
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\(?:section|subsection|subsubsection)\*?\{([^}]+)\}", r"\n## \1\n", text)
    text = re.sub(r"\\textbf\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^}]+)\}", r"\1", text)
    return text


def parse_bibtex(bib_path):
    if not bib_path or not os.path.exists(bib_path):
        return {}
    with open(bib_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    entries = {}
    for match in re.finditer(r"@(\w+)\s*\{\s*([^,]+),([^@]+)", raw, re.DOTALL):
        entry_type, key, body = match.group(1), match.group(2).strip(), match.group(3)
        fields = {}
        for fmatch in re.finditer(r"(\w+)\s*=\s*[\{\"]([^\🎉\✨\}]+)[\}\"]", body):
            fields[fmatch.group(1).lower()] = " ".join(fmatch.group(2).split())
        venue = (
            fields.get("booktitle")
            or fields.get("journal")
            or fields.get("venue")
            or (f"DOI: {fields['doi']} (venue not listed)" if "doi" in fields else "Venue not listed")
        )
        entries[key] = {
            "key": key,
            "type": entry_type,
            "author": fields.get("author", "Unknown"),
            "year": fields.get("year", "Unknown"),
            "title": fields.get("title", "Unknown"),
            "venue": venue,
            "doi": fields.get("doi", ""),
            "url": fields.get("url", ""),
        }
    return entries


def extract_sentences(text):
    cleaned = clean_latex(text)
    raw_sents = re.split(r"(?<=[.?!])\s+", cleaned)
    return [" ".join(s.split()) for s in raw_sents if len(s.strip()) > 20]


def main():
    parser = argparse.ArgumentParser(description="Extract claims, numbers, and citations from a research document.")
    parser.add_argument("--source", required=True, help="Path to proposal or paper (.tex, .md, .txt, .pdf)")
    parser.add_argument("--bib", default="", help="Optional path to .bib file")
    parser.add_argument("--out", default="", help="Optional path to save JSON report")
    args = parser.parse_args()

    raw_text = read_source_text(args.source)
    sentences = extract_sentences(raw_text)
    bib_entries = parse_bibtex(args.bib)

    pillars = {k: [] for k in PILLAR_KEYWORDS}
    numbers_found = []
    citation_contexts = {k: [] for k in bib_entries}

    for sent in sentences:
        low = sent.lower()
        for pillar, kw_list in PILLAR_KEYWORDS.items():
            if any(kw in low for kw in kw_list):
                pillars[pillar].append(sent)
        if re.search(r"\b\d+\b", sent):
            numbers_found.append(sent)
        for key, meta in bib_entries.items():
            first_surname = meta["author"].split(",")[0].split()[0].lower()
            if key.lower() in low or (len(first_surname) > 2 and first_surname in low):
                citation_contexts[key].append(sent)

    report = {
        "source_file": args.source,
        "bib_file": args.bib,
        "candidate_pillars": pillars,
        "numeric_sentences_for_discrepancy_check": numbers_found,
        "cited_papers": [
            {
                **meta,
                "claimed_findings_in_text": citation_contexts.get(key, []),
            }
            for key, meta in bib_entries.items()
        ],
    }

    output_json = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Saved extracted claims & citations report to {args.out}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
