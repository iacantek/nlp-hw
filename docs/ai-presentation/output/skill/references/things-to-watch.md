# Things to Watch (Curated Pitfalls & Fixes)

These seven high-priority pitfalls were collected from real visual audit rounds and user reviews. Check every presentation build against all seven items before declaring a deck complete.

## 1. One-Line Main Title + Gray-ish Claim Subtitle Hierarchy
- **What Goes Wrong**: Putting short section titles inside numbered blue pill badges (`01 · ...`) and wrapping long 2-line claim sentences as the main `20.5pt` title makes headers look crowded, causes narrow blue pills to overflow onto 2 lines, and weakens visual scannability.
- **How to Fix It**:
  - Put the short topic title as the **main title** (`22pt Bold #0F172A`, anchored by a thin `0.07"` left vertical accent bar in `#1D4ED8`), removing any leading numbers (`01 ·`).
  - Ensure the main title on **every slide** (including Slide 1's cover title at `28.5pt Bold`) fits strictly on **1 line**.
  - Place the full declarative claim sentence directly below as a **well-readable gray-ish subtitle** (`14.5pt Regular #475569` on content slides; `17.0pt #475569` on Slide 1).

## 2. Classroom Minimum Font Sizes
- **What Goes Wrong**: Defaulting to `10.5pt–12pt` card bullets, `12.5pt–13.5pt` card headers, or `9.5pt` captions/footers makes slides unreadable from the back of a classroom. Long verbatim quotes on early slides also force smaller fonts or cramped cards.
- **How to Fix It**:
  - Enforce strict minimums: **body bullets $\ge 14.0\text{pt}$**, **card headers $\ge 15.5\text{pt bold}$**, **subtitles $\ge 14.5\text{pt}$**, **tables $\ge 12.0\text{pt}$**, **captions & source footers $\ge 11.0\text{pt}$**, and **page badges $\ge 11.5\text{pt bold}$**.
  - Tighten bullet wording to 2–3 crisp points per card so `14pt` text fits with generous bottom padding.

## 3. Disable Default PowerPoint Shape Drop Shadows
- **What Goes Wrong**: `python-pptx` shapes inherit default PowerPoint theme drop shadows, rendering blurry gray shadows under flat cards, badges, and thin divider lines.
- **How to Fix It**:
  - Explicitly set `shape.shadow.inherit = False` on **every** shape created via `slide.shapes.add_shape(...)`.

## 4. Single-Line Figure Captions & Tight PDF Table/Figure Cropping
- **What Goes Wrong**:
  1. Long figure captions wrap onto 2 lines and collide with the bottom border of the figure container frame.
  2. Cropping a table or figure from a paper PDF with loose vertical bounds captures the bottom pixels of the page running header above the table or slices halfway through the paper's original caption below the table.
- **How to Fix It**:
  - Trim every figure caption so it fits cleanly on **one centered line** (`11pt italic`) inside its `0.34"` caption band.
  - Inspect every cropped paper figure/table at high zoom to verify crop bounds sit tightly outside the top and bottom table/figure rules with zero stray running headers or partial text lines.

## 5. Diagram Internal Banner Padding & Font Scaling
- **What Goes Wrong**: When increasing font sizes inside custom `(planned)` matplotlib diagrams for classroom readability, bold summary strings inside bottom banners can overflow or clip against the left/right edges of the banner box.
- **How to Fix It**:
  - Keep bottom banner summary strings concise and calibrate banner font sizes (`10.8pt–11.5pt bold`) so text stays centered with wide horizontal margins inside the rounded box.

## 6. Strict Aspect-Ratio Image Fitting Inside Framed Containers
- **What Goes Wrong**: Passing both `width` and `height` directly to `slide.shapes.add_picture(...)` without computing the native image aspect ratio (`iw / ih`) stretches or squashes paper plots and tables.
- **How to Fix It**:
  - Always read the image dimensions via `PIL.Image.open(img_path).size`, compute the available padded bounding box (`avail_w`, `avail_h` excluding the caption band), scale by `min(avail_w / iw, avail_h / ih)`, and center the image inside the framed container.

## 7. Speaker Notes Pacing & `[Backup]` Slide Q&A Prep
- **What Goes Wrong**: Writing overly long speaker notes (`>150 words/slide`) pushes a 9-slide talk past 10 minutes, while leaving methodological critiques unaddressed leaves the presenter vulnerable during Q&A.
- **How to Fix It**:
  - Write **3–4 spoken sentences per slide** (`~75–110 words`, `< 1 minute` per slide at `~135 wpm`) so the main talk totals **~6.5–7.0 minutes**.
  - Always append a `[Backup]` slide (`[Backup] Proposal Critique & Author Answers`) that pairs reviewer/audit critiques with confirmed author answers on the left card and open scope items marked **`TBC`** on the right card.
