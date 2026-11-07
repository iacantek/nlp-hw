# Citation Check & Attribution Rules

Follow these rules whenever summarizing cited literature, extracting figures from papers, or writing slide source lines.

## 1. Comprehensive Literature Inventory (Step 1)
- Extract **every paper** cited in the user's proposal or paper (cross-referencing in-text citations with the bibliography or `.bib` file).
- Present a complete table with four required columns:
  1. **Authors** (full first-author surname + co-authors or `et al.`)
  2. **Year** (publication or preprint year)
  3. **Venue (as cited)** (exact journal/conference/workshop venue; if the bibliography only lists an `arXiv` DOI or omits the conference name, explicitly note `arXiv preprint; conference/journal venue not listed` or note the missing venue field)
  4. **What the Author Claims It Shows** (summarize the exact finding, mechanism, or metric that the user's document attributes to that citation—do not substitute generic background knowledge)

## 2. Claim-to-Citation Verification
- Check whether the user's text stretches a cited paper beyond what it actually tests (e.g., citing a retrieval/reranking paper as proof of generator factual trust, or grouping competing biases together).
- Flag any tension between how a paper is cited in the hypothesis versus how it is used in the experimental design.

## 3. Slide Source Line Attribution Rules
- **Every content slide** must have a concise, single-line `Source:` footer at the bottom-left (`11.0pt`, `#64748B`).
- **Format**:
  - When a slide includes a figure or table from a cited paper:
    `Source: Figure X / Table Y from Author et al. (Year, arXiv:XXXX.XXXXX); Proposal §A.B.`
  - When a slide presents a `(planned)` experimental setup diagram:
    `Source: Proposal §A.B (Protocol Name, planned experimental setup).`
- **Figure Captions**:
  - Every extracted figure or table must also state its source in the centered caption directly below the image (`Figure X (Author et al., Year): concise 1-line takeaway.`).
  - Every custom diagram of the proposed methodology must include `(planned)` in both its internal banner title and its figure caption (`Planned ... (planned): concise 1-line takeaway.`).
