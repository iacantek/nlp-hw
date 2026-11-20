# Must-Haves for Every Research Presentation

These requirements are non-negotiable across the summarization, outline, slide generation, and talk preparation phases. Conflict with any must-have must be resolved explicitly before finalizing the deck.

## 1. Content & Scientific Rigor Must-Haves
1. **Verbatim Grounding in the Source Document**:
   - In the initial summary, quote verbatim where the **Motivation**, **Research Question**, and **Hypothesis** come from in the user's proposal or paper, or write `"missing"` if absent.
2. **Explicit Falsifiability ("What Would Prove Me Wrong")**:
   - The presentation must state early on what specific experimental results would **falsify** the primary hypothesis (e.g., accuracy/prior knowledge dominating, or query-language matching dominating).
3. **Strict Figure Authenticity**:
   - Figures and tables may **only** come from the user's source document or from papers cited in the source document (with explicit citation in the caption and footer).
   - Never fabricate fake empirical result plots.
   - Diagrams illustrating the planned experimental setup, confound controls, factorial matrix, or analysis pipeline are encouraged **only if explicitly labelled `(planned)`** in both the diagram header and the figure caption.
4. **Internal Discrepancy & Scope Audit**:
   - Flag any numbers or combinatorics that disagree or are underspecified inside the source document, and flag scope that is too vague, too big, or too small.

## 2. Per-Slide Structural Must-Haves
Every content slide must include:
1. **One-Line Main Title**: The short topic title (with no leading section numbers like `01 ·`), fitting strictly on **one line**.
2. **Gray-ish Claim-Sentence Subtitle**: The full declarative claim sentence directly below the main title in a well-readable slate-gray style (`#475569`, $\ge 14\text{pt}$).
3. **Short Source Line**: A bottom-left footer (`11pt`) citing the exact proposal section(s) and/or cited paper(s) (with author, year, and identifier) supporting that slide.
4. **Page Number Badge**: A consistent bottom-right page indicator (`1 / N`, `2 / N`, ...).

## 3. Talk Prep & Backup Slide Must-Haves
1. **Speaker Notes on Every Slide**:
   - 3–4 sentences per slide, under 1 minute each, totaling approximately 7 minutes across the main presentation.
2. **`[Backup]` Critique & Answers Slide**:
   - A dedicated `[Backup]` slide at the end of the deck pairing the reviewer/audit critiques with the author's answers, marking any answers the author does not have yet as `TBC`.
