# Presentation spec - oral-exam deck (for Claude Design)

This folder is the **content spec** for the oral-exam slide deck. Build the
final `.pptx` from `slides.md` in this folder. The goal: you do **layout**, not
authoring. The content is already decided here so it does not need to be
re-derived.

## How to use this folder

1. `slides.md` holds every slide in order, with the title, the small header
   kicker, the body (bullets / tables / code), and screenshot placeholders.
2. Transcribe each slide as written. Keep the wording. Do **not** invent extra
   claims, numbers, or slides, and do not "improve" the facts. If something is
   unclear, leave it as written rather than guessing.
3. Where a slide says `[[SCREENSHOT: ...]]` or `[[DIAGRAM: ...]]`, place an
   empty image frame with the caption already filled in, so the student only
   drops a PNG/SVG in later. Do not redraw these - they are pasted images.

## Hard rules

- **Language: Hebrew, RTL.** Technical terms stay in English in-line (handshake,
  bencode, asyncio, Tit-for-Tat, SHA-1, etc.).
- **No long dashes anywhere.** Use `" - "` (space hyphen space) when a dash is
  needed. This applies to titles, body, and captions.
- Numbers are final. Do not round differently or "refresh" them.

## Visual style - clean institutional (classic defense deck)

- White background, dark text, a single accent blue.
- Each content slide has a **blue header bar** carrying a slide number + short
  kicker, e.g. `15 · אלגוריתם בחירת PIECE`. Below it a one-line slide title.
- Section dividers (A / B / C / Q) are full-bleed blue with a large letter and
  the section name.
- Tables: thin lines, blue header row, generous padding.
- Code snippets: monospace, light-grey box, **LTR** direction, short (<= ~8
  lines). Syntax does not need coloring; readability first.
- "ביקורת עמוקה" (deep-critique) slides intentionally state weaknesses. Keep
  that framing - the honesty is deliberate and earns credit in the defense.
- Footer (optional, small): project name + "אדם זבולון · תשפ\"ו".

## Screenshots the student must paste (2 - 3)

Capture these from the running app (build the Java GUI first so the new
**Delete** button is visible):

1. **Main window** during a live download. Best case: one row mid-download and
   one row showing **Seeding**, with the full toolbar visible
   (Add Torrent / Pause / Resume / Cancel / Delete / History / Algorithm Stats).
   Goes on the slide marked `[[SCREENSHOT: main-window]]`.
2. **Algorithm Statistics** dialog - the rarest-first bar chart tab and the
   General tab. Goes on `[[SCREENSHOT: algorithm-stats]]`.
3. (Optional) **History** dialog. Goes on `[[SCREENSHOT: history]]` if used.

Two diagrams to render and paste (from the repo's Mermaid sources, via
https://mermaid.live - export PNG/SVG on a white background):
- **Architecture** - render `docs/Fig-02.md` (level 1). Goes on
  `[[DIAGRAM: architecture]]` (slide 9).
- **PIECE sequence (UML)** - render `docs/Fig-05.md`. Goes on
  `[[DIAGRAM: piece-sequence]]` (slide 19).

## Deck shape

~49 slides: a ~25-slide spoken walkthrough (3 parts, ~20 min) + an appendix
that answers all 17 of the teacher's prep questions (10 depth + 7 code, on
slides 36-49) for quick jump-to during the defense. Six core critiques are
also woven into the main flow as "ביקורת עמוקה" slides. Two diagrams have paste
placeholders (rendered by the student from the repo's Mermaid sources): the
architecture diagram (slide 9) and a UML PIECE sequence diagram (slide 19).
