---
name: research-slides
description: >-
  End-to-end workflow for turning a research proposal, academic paper, or technical report
  into a verified PowerPoint presentation deck (.pptx) with speaker notes and a backup Q&A slide.
  Use this skill when the user asks to create, refine, or prepare an academic or research
  presentation from a proposal, paper, or draft document.
---

# Research Slides Skill (`research-slides`)

This skill transforms an input research document into a classroom-ready PowerPoint presentation deck (`.pptx`), complete with extracted literature figures, visual self-verification rounds, timed speaker notes, and a `[Backup]` Q&A critique slide.

## Inputs (Described by Role, Not Fixed Paths)

Accept inputs dynamically based on what the user provides in the workspace:
- **Primary research source**: The user's research proposal, academic paper, manuscript draft (PDF, LaTeX, or Markdown), or experimental notes.
- **Cited literature**: Bibliography files (`.bib`), reference lists, or PDFs of cited papers (fetched via DOI/arXiv/ACL Anthology when needed for figure extraction).
- **Style reference (optional)**: An existing presentation deck, template, or user style preferences. If omitted, apply the default rules in [style-choices.md](./references/style-choices.md).

## Interaction & Confirmation Policy

> **CRITICAL RULE:** When this skill runs, **confirm ONLY the slide outline with the user in the question window (`ask_question`)**, then complete all remaining steps (building the deck, rendering images, running up to 3 visual check rounds, preparing speaker notes and the `[Backup]` slide, and saving the final `.pptx`) **autonomously on your own** without stopping to ask additional questions. Any unresolved critique answers that require author input not yet provided must be marked as `TBC` on the `[Backup]` slide.

---

## Workflow Steps & Criteria

### Step 1: Summarize (`summarize`)
Extract the core research narrative and audit internal consistency before designing slides.
1. Run [extract-claims-and-citations.py](./scripts/extract-claims-and-citations.py) on the user's primary research source (and optional `.bib` file) to inventory headings, candidate claims, numerical parameters, and cited papers.
2. Produce a structured Markdown summary (`proposal.md` or `summary.md`) containing:
   - **The Three Core Talk Pillars**:
     1. *Motivation* (why the problem matters + the specific gap in prior work)
     2. *Research Question*
     3. *Hypothesis* (plus explicit falsification conditions: what result would prove the hypothesis wrong)
     Quote verbatim where each comes from in the source document, or write `"missing"`.
   - **Research Loop Mapping**: Map the rest of the document onto *Prediction $\rightarrow$ Design $\rightarrow$ Planned Analysis $\rightarrow$ Expected Claim*.
   - **Cited Papers Table**: Every cited paper with *Authors, Year, Venue/DOI, and What the author claims it shows* (following [citation-check-rules.md](./references/citation-check-rules.md)).
   - **Internal Discrepancies & Scope Audit**: Flag numbers/combinatorics that disagree inside the document, and scope that is too vague, too big, or too small.

**Criteria for Step 1:**
- All three pillars have exact quotes or are explicitly flagged as `"missing"`.
- Every cited paper in the source text is accounted for with its claimed finding.
- Combinatorial ambiguities (e.g., items $\times$ conditions $\times$ runs) and scope limitations are explicitly calculated and listed for later use in the `[Backup]` slide.

---

### Step 2: Outline (`outline`) — *Single Question-Window Confirmation*
Propose the slide deck structure and confirm the outline once with the user.
1. Design 2–3 candidate presentation structures (e.g., *Hypothesis-Driven Research Loop*, *Concrete Failure Scenario First*, *Pipeline Walkthrough*), each with a one-line **Pro** and **Con**.
2. Call `ask_question` **once** to let the user pick the structure (and resolve any blocking outline preference).
3. For the selected structure, write the per-slide outline:
   - Place **Motivation**, **Research Question**, and **Hypothesis + What Would Prove Me Wrong** early on (Slides 2–3).
   - Provide for every slide: a **1-line short topic title**, a **claim-sentence subtitle**, and the **supporting evidence** (document section or cited paper figure/table).

**Criteria for Step 2:**
- Follows all structural principles in [presentation-checklist.md](./references/presentation-checklist.md) and [must-haves.md](./references/must-haves.md).
- Confirmed with the user via a single `ask_question` call before proceeding autonomously through Steps 3–6.

---

### Step 3: Build (`build`)
Build the initial PowerPoint presentation (`.pptx`) programmatically using `python-pptx`.
1. Extract only authentic figures/tables from the user's source document or cited papers (with source attribution), or generate clean diagrams of the planned setup explicitly labelled `(planned)`.
2. Apply all visual, typographic, and layout rules from [style-choices.md](./references/style-choices.md) and [must-haves.md](./references/must-haves.md):
   - Clean white background (`#FFFFFF`), one accent color (`#1D4ED8`), and flat modern cards (`shape.shadow.inherit = False`).
   - Short topic title as the **1-line main title** (`22pt bold #0F172A`, no leading numbers or blue pill boxes).
   - Full claim sentence as the **gray-ish, well-readable subtitle** (`14.5pt #475569`) directly below the main title.
   - Short source attribution line (`11pt`) at bottom-left and page number badge (`11.5pt bold`) at bottom-right on every slide.

**Criteria for Step 3:**
- Every content slide contains a 1-line main title, a gray-ish claim-sentence subtitle, a short source line, and a page number.
- Figures are strictly aspect-ratio preserved inside padded frames, with single-line captions (`11pt italic`).
- No fabricated empirical charts; all architecture/protocol diagrams of planned work are labelled `(planned)`.

---

### Step 4: Image Check (`image-check`)
Convert the generated `.pptx` deck into per-slide images and visually inspect every slide yourself for up to 3 rounds.
1. Run [render-slides-to-images.py](./scripts/render-slides-to-images.py) to export the `.pptx` to PDF and rasterize each slide to a high-resolution PNG (`slide_1.png`, `slide_2.png`, ...).
2. View every rendered slide image using `read_file` and check against [image-check-list.md](./references/image-check-list.md) and [things-to-watch.md](./references/things-to-watch.md):
   - **Consistency**: identical header positions, colors, fonts, and page number badges across all slides.
   - **Zero overflow, clipping, or overlap**: main titles fit strictly on 1 line; figure captions fit on 1 line inside their frames; custom diagram banners have ample left/right margin; cropped PDF tables/figures have no stray running headers or half-cropped text lines.
   - **Classroom readability**: body bullets $\ge 14\text{pt}$, card headers $\ge 15.5\text{pt}$, subtitles $\ge 14.5\text{pt}$, tables $\ge 12\text{pt}$.
3. Fix every defect found, re-render the changed slides, and inspect again (up to 3 rounds). Record a table of `round -> problem found -> fix`.

**Criteria for Step 4:**
- 100% of slides inspected visually as PNG images.
- Zero text overflow, border collision, or sub-14pt body text remaining.

---

### Step 5: User Edits (`your-edits`)
Apply any user-requested style or content adjustments across the deck.
1. Whenever applying an edit to one slide, check whether the change makes any other slide inconsistent and update all affected slides together.
2. Re-render **only the changed slides** using [render-slides-to-images.py](./scripts/render-slides-to-images.py) (`--slides` flag), verify them visually via `read_file`, and present a summary table of what changed.

**Criteria for Step 5:**
- Cross-slide visual consistency is preserved whenever any slide is modified.
- Only modified slides are re-rendered and verified, accompanied by a clear before/after table.

---

### Step 6: Talk Prep with Reviewer Critique (`talk-prep`)
Prepare the oral delivery script and the Q&A defense backup slide.
1. **Speaker Notes on Every Slide**:
   - Write **3–4 sentences** per slide in the `.pptx` speaker notes pane (`slide.notes_slide.notes_text_frame.text`).
   - Keep each slide **under 1 minute** ($\approx 75\text{--}110\text{ words}$ at a natural $135\text{ wpm}$ academic speaking pace) so the main talk totals **about 7 minutes**.
2. **`[Backup]` Slide with Reviewer Critique & Answers**:
   - Add a final slide titled `[Backup] Proposal Critique & Author Answers`.
   - Include the internal discrepancies, methodological gaps, and scope critiques identified during Step 1.
   - Pair each critique with the author's confirmed resolution, and **mark any answers not yet provided by the author as `TBC`**.
3. **Final Image & Timing Verification**:
   - Re-render the deck (or changed/new slides) with [render-slides-to-images.py](./scripts/render-slides-to-images.py), visually verify via `read_file` that nothing overflows on the `[Backup]` slide or updated page badges, and display a per-slide word-count and speaking-time table confirming the talk fits 7 minutes.

**Criteria for Step 6:**
- Every slide has 3–4 sentences of embedded speaker notes (<1 min/slide, total ~7 min).
- The `[Backup]` slide cleanly separates confirmed resolutions from open items marked `TBC`.
- Visual inspection of rendered PNGs confirms zero overflow across all slides including `[Backup]`.

---

## Reference Files & Automation Scripts

- **Reference Checklists & Rules**:
  - [presentation-checklist.md](./references/presentation-checklist.md) — Core academic presentation principles and narrative flow.
  - [must-haves.md](./references/must-haves.md) — Non-negotiable content and structural requirements.
  - [style-choices.md](./references/style-choices.md) — Exact typography, color palette, card geometry, and header hierarchy.
  - [image-check-list.md](./references/image-check-list.md) — Multi-round visual inspection rubric.
  - [citation-check-rules.md](./references/citation-check-rules.md) — Rules for verifying cited papers, venues, claims, and figure attributions.
  - [things-to-watch.md](./references/things-to-watch.md) — Specific layout pitfalls and fixes curated from prior presentation builds.
- **Executable Scripts**:
  - [render-slides-to-images.py](./scripts/render-slides-to-images.py) — Converts a `.pptx` file (all slides or selected slide numbers) into high-resolution PNG images for visual verification.
  - [extract-claims-and-citations.py](./scripts/extract-claims-and-citations.py) — Extracts sections, claims, numeric expressions, and citation entries from a proposal/paper (`.pdf`, `.tex`, `.md`) and `.bib` files.
