# Author Style Choices & Visual Design System

Apply these exact visual specifications when building or updating slides unless the user provides a different style reference.

## 1. Slide Dimensions & Canvas
- **Aspect Ratio**: 16:9 Widescreen (`13.333 inches` wide $\times$ `7.500 inches` high).
- **Slide Background**: Pure white (`#FFFFFF` / `RGBColor(255, 255, 255)`).
- **Flat Modern Shapes**: Always disable default PowerPoint drop shadows on every rectangle and rounded rectangle (`shape.shadow.inherit = False`).

## 2. Single-Accent Color Palette
Use a strict one-accent palette (Royal Cobalt Blue) paired with high-contrast slate neutrals:
- **Primary Accent (`ACCENT`)**: `#1D4ED8` (`RGBColor(29, 78, 216)`) — top accent bar, left vertical title anchor, primary card indicator bar, page number text.
- **Deep Accent Text (`ACCENT_DARK`)**: `#1E3A8A` (`RGBColor(30, 58, 138)`) — header titles on accent-tinted cards.
- **Accent Soft Fill (`ACCENT_LIGHT`)**: `#EFF6FF` (`RGBColor(239, 246, 255)`) — highlighted/accent card background and page badge fill.
- **Accent Border (`ACCENT_BORDER`)**: `#93C5FD` (`RGBColor(147, 197, 253)`) — border for accent-tinted cards and page badges (`1.0pt–1.4pt`).
- **Primary Ink (`SLATE_900`)**: `#0F172A` (`RGBColor(15, 23, 42)`) — main titles, neutral card headers, bold bullet lead-ins.
- **Readable Gray-ish Subtitle (`SLATE_600`)**: `#475569` (`RGBColor(71, 85, 105)`) — claim-sentence subtitles directly below the main title (and cover subtitle).
- **Body Text (`SLATE_700`)**: `#334155` (`RGBColor(51, 65, 85)`) — bullet descriptions and body copy.
- **Captions & Sources (`SLATE_500`)**: `#64748B` (`RGBColor(100, 116, 139)`) — figure captions and bottom-left source attribution lines.
- **Neutral Card Fill (`SLATE_100`)**: `#F8FAFC` (`RGBColor(248, 250, 252)`) — standard card background.
- **Neutral Divider & Border (`SLATE_200`)**: `#CBD5E1` (`RGBColor(203, 213, 225)`) — header/footer horizontal rules and neutral card/figure frames.

## 3. Header & Title Hierarchy
- **No Blue Section Pill on Content Slides**: Do not put short titles inside a numbered blue pill box (`01 · ...`).
- **Content Slide Main Title**:
  - Put the short topic title as the main title at `(left=0.65", top=0.13", width=12.183", height=0.44")`.
  - Anchor it on the left with a small vertical accent bar at `(left=0.50", top=0.17", width=0.07", height=0.36")` in `#1D4ED8`.
  - Font: `Arial`, `22.0pt Bold`, `#0F172A`. **Must fit strictly on 1 line.**
- **Content Slide Subtitle (Claim Sentence)**:
  - Place the full claim sentence directly below the main title at `(left=0.50", top=0.59", width=12.333", height=0.64")`.
  - Font: `Arial`, `14.5pt Regular`, `#475569` (well-readable gray-ish style). May wrap cleanly up to 2 lines above the `top=1.30"` header divider.
- **Cover Slide (Slide 1)**:
  - Cover main title must also fit on **1 line** (`28.5pt Bold #0F172A` across `11.85"` width), with the cover subtitle below it in matching gray-ish style (`17.0pt Regular #475569`).

## 4. Typography & Minimum Classroom Sizes
- **Font Family**: `Arial` (or `Helvetica` fallback) across all slide text and generated diagrams.
- **Minimum Font Sizes**:
  - Cover Title: `28.5pt Bold` (1 line)
  - Cover Subtitle: `17.0pt Regular` (`#475569`)
  - Content Slide Main Title: `22.0pt Bold` (1 line)
  - Content Slide Claim Subtitle: `14.5pt Regular` (`#475569`)
  - Bullet Card Header: `15.5pt Bold`
  - Bullet Card Body Text: `14.0pt` (bold lead-in label + regular description)
  - Tables: $\ge 12.0\text{pt}$
  - Figure Captions: `11.0pt Italic` (`#64748B`, centered single line inside frame)
  - Footer Source Line: `11.0pt Regular` (`#64748B`, bottom-left at `top=7.00"`)
  - Page Number Badge: `11.5pt Bold` (`#1D4ED8`, bottom-right at `left=11.78", top=7.01", width=1.05", height=0.34"`)

## 5. Content Zone & Card Geometry
- **Body Zone**: Between `top=1.42"` (below the `1.30"` header rule) and `bottom=6.82"` (above the `6.94"` footer rule), with `left=0.50"` and `right=12.833"` (`width=12.333"`).
- **Bullet Cards**: Rounded rectangles (`adjustments[0] = 0.035`, `border_pt = 1.4`) with a left vertical accent stripe (`width=0.08"`).
- **Figure Containers**: Framed rounded rectangles (`fill=WHITE`, `border=SLATE_200`, `border_pt=1.3`) that center the image while strictly preserving its native aspect ratio (`iw / ih`). Reserve `0.34"` at the bottom of the frame for a centered 1-line caption.
