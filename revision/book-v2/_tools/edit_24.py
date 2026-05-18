"""Apply the §24 (בדיקות והערכה) rewrite to the working docx.

Operates on body-child indices captured from the source:
  1316  -> replace text       (counts: 160 -> 212)
  1322  -> replace text       (drop the E2E-gap admission)
  after 1322 -> insert new <w:p>  (E2E test description)
  1324  -> replace text       (methodology)
  1325  -> replace text       (setup)
  1326  -> replace text       (results - prose, no table for now)
  1327  -> replace text       (wall-clock interpretation)
  1328  -> replace text       (what the experiment proves)
  1329  -> replace text       (honest limits)
  1330  -> replace text       (reproducibility)

Run from repo root: `python3 revision/book-v2/_tools/edit_24.py`.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Ensure local modules import.
sys.path.insert(0, str(Path(__file__).parent))

from lxml import etree  # noqa: E402

from docx_patcher import patch_docx, verify_non_document_identical, W  # noqa: E402
from runs_builder import build_paragraph, replace_paragraph_text  # noqa: E402
from table_builder import build_table  # noqa: E402

DOCX = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
SOURCE = Path("docs/ספר פרוייקט אדם זבולון.docx")
BACKUP = Path("revision/book-v2/_tools/before_24.docx")


# --- prose ------------------------------------------------------------------

PARA_1316 = (
    "בתיקייה `python_engine/tests/` קיימות **212 פונקציות בדיקה** המכסות "
    "את כל מודולי ה-Engine: bencode, torrent_metadata, piece_manager, "
    "peer_connection, tracker_client, download_manager, security ו-API "
    "server. כל הבדיקות רצות תחת `pytest` (כולל `pytest-asyncio` עבור "
    "הקורוטינות), והסוויטה כולה נכנסת בפחות מ-10 שניות על המחשב הביתי "
    "שבו פותח הפרויקט."
)

PARA_1322 = (
    "פערים מתועדים: אין בדיקות ל-Swing components ב-Java "
    "(headless GUI testing מסובך)."
)

PARA_E2E = (
    "**תוספת end-to-end:** מאחר וה-unit tests בודקים כל מודול בנפרד, "
    "נוסף ניסוי E2E שבודק את **כל ה-Peer Wire Protocol stack בבת אחת**. "
    "ב-`python_engine/tests/test_e2e_peer.py` מוקם peer-mock אסינכרוני "
    "שעונה ב-handshake → bitfield → unchoke → piece על פי BEP-3, "
    "וה-`PeerConnection` מנהל מולו handshake, מפענח את ה-length-prefix "
    "framing, שולח `request`, מקבל `piece` ומאמת SHA-1. הניסוי הזה הוא "
    "הראיה הישירה ש-handshake bytes, framing, state machine ו-hash "
    "verification עובדים יחד מקצה לקצה, ולא רק בנפרד."
)

PARA_1324 = (
    "ההערכה האמפירית בודקת את אלגוריתם בחירת ה-pieces (`rarest_first` "
    "מול `random`) ב-swarm סינתטי על loopback, לא ב-swarm ציבורי. "
    "הסיבה לבחירה הזו היא **שחזוריות**: ב-swarm אמיתי, מספר ה-seeders "
    "ורוחב הפס משתנים מדקה לדקה, וההפרש בין שתי הרצות של אותה תצורה "
    "גדול יותר מההפרש האלגוריתמי הנמדד. בהרצה המקומית הזו, היחיד "
    "שמשתנה בין הרצות הוא האלגוריתם הנבדק."
)

PARA_1325 = (
    "ה-payload הוא קובץ של 1 MB (16 חתיכות × 64 KB) שנוצר מ-seed קבוע. "
    "ה-tracker הוא שרת aiohttp מינימלי, וה-peers הם ארבעה mock peers "
    "שמדברים BEP-3 (handshake, bitfield, interested, unchoke, request, "
    "piece) — ראה `python_engine/experiments/mock_swarm.py`. הטופולוגיה "
    "תוכננה כך **שזמינות החתיכות איננה אחידה**, אחרת שני האלגוריתמים "
    "היו רואים את אותה התפלגות ובוחרים זהה: ה-peer בשם `full` מחזיק "
    "בכל 16 החתיכות, בעוד `low_a`, `low_b`, `low_c` מחזיקים רק "
    "בחתיכות 0..7 (החצי \"השכיח\"). חתיכות 8..15 נמצאות אך ורק אצל "
    "`full` — והן ה\"חצי הנדיר\"."
)

PARA_1326 = (
    "חמש הרצות עצמאיות לכל אלגוריתם, סך הכל 10 הרצות. הטבלה הבאה "
    "היא הסיגנל הברור ביותר — כמה bytes כל peer העלה ל-Engine בכל "
    "אלגוריתם (ממוצע 5 הרצות):"
)

# Headline table inserted immediately after paragraph 1326.
# Columns (visual order under bidiVisual=1 — first cell renders on the
# right): Peer, rarest-first, random, פרשנות.
TABLE_ROWS = [
    ["Peer", "rarest-first", "random", "פרשנות"],
    [
        "`full`",
        "**512.0 KB**",
        "**576.0 KB**",
        "תחת rarest-first, `full` מספק בדיוק את החצי הנדיר "
        "(8 × 64 KB). תחת random הוא מספק גם כמה חתיכות \"שכיחות\" "
        "מיותרות.",
    ],
    ["`low_a`", "153.6 KB", "128.0 KB", "חולק את עומס החצי השכיח."],
    ["`low_b`", "166.4 KB", "153.6 KB", "חולק את עומס החצי השכיח."],
    ["`low_c`", "192.0 KB", "166.4 KB", "חולק את עומס החצי השכיח."],
    [
        "**סה\"כ**",
        "1024 KB",
        "1024 KB",
        "זהה — כל ה-payload הורד מקצה לקצה בשתי התצורות.",
    ],
]
TABLE_COL_WIDTHS = [1320, 1760, 1760, 3080]  # twentieths of a point; sums to 7920

PARA_1327 = (
    "ההפרש של 12.5% הוא לא דרמטי, ואין הפרש מובהק ב-wall-clock time: "
    "שתי התצורות מסיימות ב-כ-30 מילי-שניות, כי על loopback צוואר "
    "הבקבוק הוא ה-asyncio event loop ולא רוחב הפס."
)

PARA_1328 = (
    "מה שהניסוי **כן** מוכיח, באופן דטרמיניסטי על פני 5 הרצות, הוא "
    "שמימוש ה-rarest-first אכן מרכז את הביקוש לחתיכות הנדירות "
    "ב-peer היחיד שמחזיק בהן, ופורק את החצי השכיח על פני שלושת "
    "ה-peers האחרים במקביל. תחת random, ה-Engine מבזבז חלק "
    "מהבקשות ל-`full` על חתיכות שכיחות ש-`low_a/b/c` יכולים לספק."
)

PARA_1329 = (
    "מה הניסוי **אינו** מודד: (א) speedup ב-swarm ציבורי אמיתי — "
    "מדידה כזו דורשת התחברות ל-swarm חי, התמודדות עם רעש הרשת, "
    "ופתרון NAT; (ב) את endgame mode שמצדיק את rarest-first "
    "בפרודקשן (peer churn מאמצע ההורדה) — סימולציית churn דורשת "
    "תשתית נוספת שאינה כלולה בפרויקט; (ג) השוואה של בחירת ה-peers "
    "(tit-for-tat מול round-robin) — הניסוי משאיר את האלגוריתם הזה "
    "קבוע ובודק רק את בחירת ה-pieces."
)

PARA_1330 = (
    "ההרצה מבוצעת בפקודה אחת: "
    "`python3 -m python_engine.experiments.run_comparison`. הסקריפט "
    "יוצר את ה-CSVs מחדש בכל הרצה. שלושת הקבצים — "
    "`comparison_summary.csv` (10 שורות), `comparison_peers.csv` "
    "(40 שורות), `comparison_timeline.csv` (160 שורות) — נמצאים תחת "
    "`data/experiments/` ומחויבים לרפו כראייה. המתודולוגיה המלאה "
    "ופירוט העמודות נמצאים ב-`data/experiments/README.md`."
)


REPLACEMENTS_BY_IDX = {
    1316: PARA_1316,
    1322: PARA_1322,
    1324: PARA_1324,
    1325: PARA_1325,
    1326: PARA_1326,
    1327: PARA_1327,
    1328: PARA_1328,
    1329: PARA_1329,
    1330: PARA_1330,
}
INSERT_PARA_AFTER_IDX = {1322: PARA_E2E}
INSERT_TABLE_AFTER_IDX = 1326


def edit(root, body, W):  # noqa: ARG001
    children = list(body)
    # Capture element references by ORIGINAL index before any mutation.
    targets = {idx: children[idx] for idx in REPLACEMENTS_BY_IDX}
    para_inserts = {idx: children[idx] for idx in INSERT_PARA_AFTER_IDX}
    table_anchor = children[INSERT_TABLE_AFTER_IDX]

    # Phase 1: text replacements (in-place; does not shift indices).
    for idx, prose in REPLACEMENTS_BY_IDX.items():
        p = targets[idx]
        if p.tag != f"{{{W}}}p":
            raise RuntimeError(f"body[{idx}] is not <w:p> (got {p.tag})")
        replace_paragraph_text(p, prose)

    # Phase 2: insert new paragraphs after specific elements.
    for idx, prose in INSERT_PARA_AFTER_IDX.items():
        anchor = para_inserts[idx]
        new_p = build_paragraph(prose)
        anchor.addnext(new_p)

    # Phase 3: insert the headline table after paragraph 1326 (lead-in).
    tbl = build_table(TABLE_ROWS, TABLE_COL_WIDTHS, header=True)
    table_anchor.addnext(tbl)


def main() -> int:
    if not SOURCE.exists():
        print(f"missing source: {SOURCE}", file=sys.stderr)
        return 1
    # Idempotent: always start from the pristine source so the body
    # indices in REPLACEMENTS_BY_IDX line up.
    shutil.copy2(SOURCE, DOCX)
    shutil.copy2(SOURCE, BACKUP)
    patch_docx(BACKUP, DOCX, edit)
    ok, diffs = verify_non_document_identical(BACKUP, DOCX)
    if not ok:
        print(f"FAIL: post-edit non-document.xml diff ({len(diffs)} entries):")
        for d in diffs:
            print(" -", d)
        # Restore.
        shutil.copy2(SOURCE, DOCX)
        return 1
    print("OK: §24 edits applied; non-document.xml parts byte-identical.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
