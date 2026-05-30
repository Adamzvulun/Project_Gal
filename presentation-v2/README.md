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
2. Transcribe each slide as written. Keep the wording. The slides intentionally
   present each teacher-pre-announced question **in natural flow** without
   citing a question number - the goal is a walkthrough, not a Q&A. Do not add
   citations or "תרגיל X" labels of your own.
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

57 slides organized as a single walkthrough in 8 parts (A - H) plus a short
2-slide appendix mapping the core mechanisms to their file:function in code
(useful when the examiner asks "show me where in the code...").

The flow is **base info -> deeper**, and the same topic never appears twice:
every pre-announced question the teacher sent is answered the first time its
topic comes up naturally during the walk. The walkthrough does not name or
number the questions inside the slides themselves.

| Part | Slides | Theme |
| --- | --- | --- |
| A | 1 - 7 | יסוד · מה ולמה |
| B | 8 - 19 | ארכיטקטורה ושכבות (כולל שתי "שאלות הכרעה") |
| C | 20 - 25 | בחירת PIECE · Rarest-First (סימולציה + קוד שורה-שורה + ביקורת) |
| D | 26 - 32 | בחירת PEER · Tit-for-Tat (סימולציה + שלוש שכבות + ביקורת) |
| E | 33 - 37 | פרוטוקול ו-Framing |
| F | 38 - 42 | אבטחה ושלמות |
| G | 43 - 46 | מצב, scale, וכשל |
| H | 47 - 52 | תרחישי קצה ותוצאות אמפיריות |
| End | 53 - 55 | מסקנות, מגבלות, תודה |
| Appendix | 56 - 57 | מיקום בקוד למרכיבים המרכזיים |

The walkthrough body is slides 1 - 55 (~25 min spoken). The appendix is 2
slides for instant jumping if needed during defense.
