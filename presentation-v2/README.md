# Presentation v2 - oral-exam deck (for Claude Design)

This folder is the **content spec** for the v2 oral-exam slide deck. It was
written *after* the teacher sent a second list of questions (43 new ones across
two PDFs: 15 תרגילי עומק + 5 שאלות פסילה, and 20 ארכיטקטורה + 20 קוד/אלגוריתמים
+ 3 שוברות-מערכת). The deck is a **walkthrough** - Adam leads the examiner
through the project from base info into the deep details, and every question
the teacher pre-announced gets answered *in place* during the walk, not as a
detached Q&A appendix.

Build the final `.pptx` from `slides.md` in this folder. Layout only - the
content is decided here. Do not add slides, do not invent claims or numbers,
do not "improve" facts.

## How to use this folder

1. `slides.md` holds every slide in order, with the title, the small header
   kicker, the body (bullets / tables / code), and screenshot placeholders.
2. Transcribe each slide as written. Keep the wording. Where a slide cites a
   teacher question (e.g. `שאלה ארכיטקטורה 3`, `תרגיל 14`, `שאלת פסילה 1`,
   `שוברת מערכת 2`), keep the citation - it is intentional, so Adam can flip
   straight to the matching slide if the examiner asks the question verbatim.
3. Where a slide says `[[SCREENSHOT: ...]]` or `[[DIAGRAM: ...]]`, place an
   empty image frame with the caption already filled in, so the student only
   drops a PNG/SVG in later. Do not redraw these - they are pasted images.

## Hard rules (identical to v1)

- **Language: Hebrew, RTL.** Technical terms stay in English in-line
  (handshake, bencode, asyncio, Tit-for-Tat, SHA-1, etc.).
- **No long dashes anywhere.** Use `" - "` (space hyphen space) when a dash is
  needed. This applies to titles, body, and captions.
- Numbers are final. Do not round differently or "refresh" them.

## Visual style - identical to v1 deck

Match the v1 deck (`../presentation/`) one-to-one:

- White background, dark text, single accent blue.
- Each content slide has a **blue header bar** carrying a slide number + short
  kicker, e.g. `22 · אלגוריתם בחירת PIECE`. Below it a one-line slide title.
- Section dividers (A / B / C / D / E / F / G / H / Q) are full-bleed blue
  with a large letter and the section name.
- Tables: thin lines, blue header row, generous padding.
- Code snippets: monospace, light-grey box, **LTR** direction, short (<= ~12
  lines). Syntax does not need coloring; readability first.
- "ביקורת עמוקה" (deep-critique) slides intentionally state weaknesses. Keep
  that framing - the honesty is deliberate and earns credit in the defense.
- "תרגיל הבוחן" (examiner-exercise) slides answer a specific pre-announced
  question. Mark them with the matching kicker (e.g. `תרגיל 4 · סימולציה`).
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
  `[[DIAGRAM: architecture]]`.
- **PIECE sequence (UML)** - render `docs/Fig-05.md`. Goes on
  `[[DIAGRAM: piece-sequence]]`.

## Deck shape

~55 slides organized as a single walkthrough in 8 parts (A - H) plus a short
appendix (Q) with the 5 code-location pointers (the teacher's "שאלות פסילה" -
disqualification questions that demand pointing at exact file:line in code).

The flow is **base info -> deeper**, so the same examiner question never
appears twice: every question is answered the first time its topic comes up
naturally.

| Part | Slides | Theme | Teacher questions answered here |
| --- | --- | --- | --- |
| A | 1 - 7 | יסוד · מה ולמה | תרגיל 15, שאלת ארכיטקטורה 15 |
| B | 8 - 19 | ארכיטקטורה ושכבות | ארכ' 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 18; תרגיל 1, 2, 11, 12 |
| C | 20 - 25 | בחירת PIECE · Rarest-First | תרגיל 3, 4, 5, 14; קוד 1, 2, 3, 4 |
| D | 26 - 32 | בחירת PEER · Tit-for-Tat | תרגיל 6, 7, 8; קוד 5, 6, 7, 8 |
| E | 33 - 37 | פרוטוקול ו-Framing | קוד 13, 14, 15, 16, 18 |
| F | 38 - 42 | אבטחה ושלמות | תרגיל 9, 10; קוד 9, 10, 11, 12, 17; פסילה (preview) |
| G | 43 - 46 | מצב, scale, וכשל | תרגיל 13; ארכ' 13, 14, 15, 17, 19; קוד 19, 20 |
| H | 47 - 52 | שוברות-מערכת ותוצאות | שוברת 1, 2, 3; ארכ' 20 |
| End | 53 - 55 | מסקנות, מגבלות, תודה |  |
| Appendix Q | 56 - 57 | מיקום בקוד · 5 שאלות הפסילה | פסילה 1, 2, 3, 4, 5 |

Total: 57 slides. The walkthrough body is 1 - 55 (~25 min spoken). The Q
appendix is 2 slides for instant jumping if the examiner asks "show me where
in the code...".
