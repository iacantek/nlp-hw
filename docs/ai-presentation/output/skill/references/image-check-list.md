# Multi-Round Image Verification Checklist

Never trust raw coordinates alone. After building or editing the `.pptx` deck, convert slides to PNG images using [render-slides-to-images.py](../scripts/render-slides-to-images.py) and inspect every slide image visually via `read_file` for **up to 3 rounds**.

## Inspection Rubric (Check Every Slide Image)

### 1. Cross-Slide Consistency
- [ ] **Header Alignment**: Top accent bar, left vertical title bar, 1-line main title (`22pt bold #0F172A`), gray-ish claim subtitle (`14.5pt #475569`), and `top=1.30"` divider line sit at identical vertical/horizontal positions across all content slides.
- [ ] **Color Discipline**: Only white background, slate neutrals, and the single cobalt blue accent (`#1D4ED8` / `#EFF6FF`) are used in slide chrome and custom diagrams.
- [ ] **Footer & Page Numbers**: Bottom divider (`top=6.94"`), source line (`11pt`), and page number badge (`1 / N` .. `N / N`) are present and aligned on every slide.
- [ ] **No Drop Shadows**: All cards, badges, and frames render completely flat with no gray drop shadows.

### 2. Overflow, Clipping, and Overlap
- [ ] **One-Line Main Titles**: Every slide's main title (including Slide 1's cover title and all content slides) fits on **strictly 1 line** without wrapping.
- [ ] **Subtitle Clearance**: The gray-ish claim subtitle wraps to at most 2 lines and never touches or crosses the `top=1.30"` horizontal divider.
- [ ] **Card Bottom Clearance**: The last bullet line inside every card has visible bottom padding above the card's bottom border.
- [ ] **Single-Line Figure Captions**: Every figure caption fits on a single centered line inside the bottom of its figure frame without wrapping onto the border.
- [ ] **Diagram Banner Margins**: Inside `(planned)` matplotlib/vector diagrams, text inside dark or tinted banners has generous left and right margins and never clips against box edges.
- [ ] **Clean PDF Figure/Table Crops**: Figures and tables cropped from cited papers have zero stray running headers above the top rule and zero half-cropped caption lines below the bottom rule.

### 3. Classroom Readability (Back-of-the-Room Check)
- [ ] **Body Text $\ge 14\text{pt}$**: All bullet card text is visibly large and crisp (`14pt` body, `15.5pt` headers).
- [ ] **Tables & Diagrams $\ge 12\text{pt}$**: Cropped tables and custom `(planned)` diagrams use large, bold, high-contrast typography without cramped multi-column text blocks.

### 4. Reporting Format
- After completing the visual inspection rounds (up to 3 rounds), output a summary table:
  `Round -> Slide(s) -> Problem Found -> Fix Applied`
- When re-rendering after user-requested edits, **re-render only the changed slides** and output a table summarizing what changed on each slide.
