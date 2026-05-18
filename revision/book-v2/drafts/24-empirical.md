# Draft — §24 בדיקות והערכה (rewrite)

Working file: `revision/book-v2/ספר פרוייקט אדם זבולון.docx`
Target paragraphs (current body indices):

* `1316` — "160 פונקציות בדיקה..." → update counts
* `1322` — "פערים מתועדים: ...אין end-to-end network tests" → remove the E2E gap; add a real E2E sentence
* `1324–1330` — "הערכה אמפירית" planned-experiment paragraphs → **replace** with real results

Source citations: `python_engine/experiments/run_comparison.py`, `python_engine/tests/test_e2e_peer.py`, `data/experiments/comparison_summary.csv`, `data/experiments/comparison_peers.csv`, `data/experiments/README.md`.

---

## (A) Replace paragraph 1316

> בתיקייה `python_engine/tests/` קיימות **212 פונקציות בדיקה** המכסות את כל מודולי ה-Engine: bencode, torrent_metadata, piece_manager, peer_connection, tracker_client, download_manager, security ו-API server. כל הבדיקות רצות תחת `pytest` (כולל `pytest-asyncio` עבור הקורוטינות), והסוויטה כולה נכנסת בפחות מ-10 שניות על המחשב הביתי שבו פותח הפרויקט.

*Notes for me, not for the book: 212 is the current count after steps 1–4 (was 172 originally → 185 after step 3 → 203 after 4a/4b → 212 after 4c). Sentence intentionally drops the "1,421 שורות קוד בדיקה" claim because the file/line count isn't an interesting number and is easy to attack — we substitute a meaningful claim (full-suite runtime).*

## (B) Add a new paragraph immediately after 1322 (before the §24 "הערכה אמפירית" heading at 1323)

> **תוספת end-to-end:** מאחר וה-unit tests בודקים כל מודול בנפרד, נוסף ניסוי E2E שבודק את **כל ה-Peer Wire Protocol stack בבת אחת**. ב-`python_engine/tests/test_e2e_peer.py` מוקם peer-mock אסינכרוני שעונה ב-handshake → bitfield → unchoke → piece על פי BEP-3, וה-`PeerConnection` שלנו מנהל מולו handshake, מפענח את ה-length-prefix framing, שולח `request`, מקבל `piece` ומאמת SHA-1. הניסוי הזה הוא הראיה הישירה ש-(handshake bytes ↔ framing ↔ state machine ↔ hash verification) עובדים יחד מקצה לקצה, ולא רק בנפרד.

*This addresses Step 2 explicitly. Cites `test_e2e_peer.py` by name as required by PLAN §2.*

## (C) Replace paragraphs 1324–1330 (the entire "הערכה אמפירית" subsection body — keep the H2 heading at 1323)

The replacement is one short methodology paragraph, one results table, one interpretation paragraph, and one honest-limitations paragraph. Total length comparable to the original (which was 7 short paragraphs), preserving the book's pacing.

### Paragraph 1 — methodology

> ההערכה האמפירית בודקת את אלגוריתם בחירת ה-pieces (`rarest_first` מול `random`) ב-swarm סינתטי על loopback, לא ב-swarm ציבורי. הסיבה לבחירה הזו היא **שחזוריות**: ב-swarm אמיתי, מספר ה-seeders ורוחב הפס משתנים מדקה לדקה, וההפרש בין שתי הרצות של אותה תצורה גדול יותר מההפרש האלגוריתמי שאנחנו רוצים למדוד. בהרצה המקומית הזו, היחיד שמשתנה בין הרצות הוא האלגוריתם הנבדק.

### Paragraph 2 — setup

> ה-payload הוא קובץ של 1 MB (16 חתיכות × 64 KB) שנוצר מ-seed קבוע. ה-tracker הוא שרת aiohttp מינימלי, וה-peers הם ארבעה mock peers שמדברים BEP-3 (handshake, bitfield, interested, unchoke, request, piece) — ראה `python_engine/experiments/mock_swarm.py`. הטופולוגיה תוכננה כך **שזמינות החתיכות איננה אחידה**, אחרת שני האלגוריתמים היו רואים את אותה התפלגות ובוחרים זהה: ה-peer בשם `full` מחזיק בכל 16 החתיכות, בעוד `low_a`, `low_b`, `low_c` מחזיקים רק בחתיכות 0..7 (החצי "השכיח"). חתיכות 8..15 נמצאות אך ורק אצל `full` — והן ה"חצי הנדיר".

### Paragraph 3 — results table (verbatim numbers from `data/experiments/comparison_peers.csv`, mean of 5 runs)

> חמש הרצות עצמאיות לכל אלגוריתם, סך הכל 10 הרצות. הטבלה הבאה היא הסיגנל הברור ביותר — כמה bytes כל peer העלה ל-Engine בכל אלגוריתם (ממוצע 5 הרצות):

| Peer    | rarest-first | random   | פרשנות |
|---------|---|---|---|
| `full`  | **512.0 KB** | **576.0 KB** | תחת rarest-first, `full` מספק בדיוק את החצי הנדיר (8 × 64 KB). תחת random הוא מספק גם כמה חתיכות "שכיחות" מיותרות. |
| `low_a` | 153.6 KB | 128.0 KB | חולק את עומס החצי השכיח. |
| `low_b` | 166.4 KB | 153.6 KB | חולק את עומס החצי השכיח. |
| `low_c` | 192.0 KB | 166.4 KB | חולק את עומס החצי השכיח. |
| **סה"כ** | 1024 KB | 1024 KB | זהה — כל ה-payload הורד מקצה לקצה בשתי התצורות. |

### Paragraph 4 — interpretation (honest, not bravado)

> ההפרש הוא **12.5%** ב-`full` (512 KB מול 576 KB). זה לא הפרש דרמטי, ואין הפרש מובהק ב-wall-clock time: שתי התצורות מסיימות ב-~30 מילי-שניות, כי על loopback צוואר הבקבוק הוא ה-asyncio event loop ולא רוחב הפס. אבל מה שהניסוי **כן** מוכיח, באופן דטרמיניסטי על פני 5 הרצות, הוא שה-rarest-first שלנו אכן מרכז את הביקוש לחתיכות הנדירות ב-peer היחיד שמחזיק בהן, ופורק את החצי השכיח על פני שלושת ה-peers האחרים במקביל. תחת random, ה-Engine "מבזבז" חלק מהבקשות ל-`full` על חתיכות שכיחות ש-`low_*` יכולים לספק.

### Paragraph 5 — honest limitations (the chapter explicitly admits what it doesn't test)

> מה הניסוי הזה **אינו** מודד: (א) speedup ב-swarm ציבורי אמיתי — כדי לעשות זאת היינו צריכים להתחבר ל-swarm חי ולסבול את רעש הרשת, וזה דורש פתרון NAT; (ב) את ה"endgame mode" שמצדיק את rarest-first בפרודקשן (peer churn מאמצע ההורדה) — סימולציית churn דורשת תשתית נוספת שלא נבנתה; (ג) השוואה של בחירת ה-peers (tit-for-tat מול round-robin) — הניסוי משאיר את האלגוריתם הזה קבוע ובודק רק את בחירת ה-pieces. הניסוי **כן** עונה על השאלה המצומצמת הבאה: "בהינתן swarm שבו זמינות החתיכות איננה אחידה — האם המימוש שלנו של rarest-first אכן מרכז את הביקוש לחתיכות הנדירות?". התשובה, על פי הנתונים: כן, באופן דטרמיניסטי.

### Paragraph 6 — reproducibility

> ההרצה מבוצעת בפקודה אחת:
>
> ```
> python3 -m python_engine.experiments.run_comparison
> ```
>
> הסקריפט יוצר את ה-CSVs מחדש בכל הרצה. שלושת הקבצים — `comparison_summary.csv` (10 שורות, אחת לכל הרצה), `comparison_peers.csv` (40 שורות, 4 peers × 10 הרצות), ו-`comparison_timeline.csv` (160 שורות, חותמת זמן לכל בחירת piece ולכל אימות SHA-1) — נמצאים תחת `data/experiments/` ומחויבים לרפו כראייה. המתודולוגיה המלאה ופירוט העמודות נמצאים ב-`data/experiments/README.md`.

---

## Editing operation summary

| Action | Body idx | Result |
|---|---|---|
| Replace text of `<w:p>` | 1316 | New counts paragraph (A) |
| Insert new `<w:p>` AFTER | 1322 | E2E test mention (B) |
| Replace text of `<w:p>` × 7 | 1324–1330 | New methodology + table + interpretation + limits + reproducibility (C, paragraphs 1–6 above) |

The H2 heading at 1323 ("הערכה אמפירית") stays. The H2 at 1331 ("בדיקות איכות נוספות") stays. The §25 heading at 1337 stays.

Image preservation: there are **no `<w:drawing>` elements** in body indices 1314–1340 per the structure map. Edit is text-only.

Awaiting Adam's approval of Hebrew prose voice and content before applying to the docx.
