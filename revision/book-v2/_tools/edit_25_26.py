"""§25 (מסקנות) + §26 (פיתוחים עתידיים) edit pass.

Closes the auto-resume admission. Specifically:

  * §25 — adds an insight paragraph describing the `_load_state`
    design (sidecar `.torrent`, re-hash from disk), and rewrites the
    "מה לא הצליח" paragraph to remove the auto-resume admission.
  * §26 — deletes the auto-resume future-work entry under "חוויית
    משתמש"; rewrites the priority order to drop "auto-resume + ".

Body indices are from the ORIGINAL source. Element references survive
mutations done by other passes (e.g. §24 inserting 2 elements earlier).
"""
from __future__ import annotations

from lxml import etree

from runs_builder import build_paragraph, replace_paragraph_text


# §25 — new insight describing the working auto-resume path.
PARA_25_NEW_INSIGHT = (
    "שחזור מצב הוא יותר מ-JSON dump. הגרסה הראשונה של `_save_state` "
    "כתבה JSON מינימלי — ב-restart, `_load_state` היה נכשל בלי "
    "המידע שדרוש לשחזור: `Download.__init__` זקוק ל-`TorrentMetadata` "
    "מלא, ל-`download_dir`, ולשמות האלגוריתמים. הפתרון: sidecar "
    "`{id}.torrent` (re-encoded דרך `bencode.encode` קנוני) ושלושה "
    "שדות חדשים ב-JSON. וחשוב יותר — ה-restore מאמת מחדש כל piece "
    "שה-JSON מסמן כ-COMPLETED, על ידי קריאת ה-bytes מהדיסק והרצת "
    "`Piece.verify_hash`. ה-JSON הוא רמז למה שהיה נכון בעת השמירה, "
    "לא האמת על מה שעל הדיסק עכשיו — הקובץ יכול להשתנות בין הפעלות. "
    "ראה `Download.from_state_file` ו-`DownloadManager.restore_state` "
    "ב-`download_manager.py`."
)

# §25 — replace the "מה לא הצליח" admission. Auto-resume is OUT of
# this list (now works); NAT and MSE/PE remain.
PARA_25_NOT_DONE = (
    "מה לא הצליח: NAT traversal לא מומש — המערכת לא מקבלת חיבורים "
    "נכנסים. ו-MSE/PE לא מומש — אין הצפנה בערוץ peers. שני הפערים "
    "מתועדים בפרק 26."
)

# §26 — rewritten priority paragraph (auto-resume dropped from month 2).
PARA_26_PRIORITIES = (
    "חודש 1: incoming server + NAT traversal. חודש 2: algorithm "
    "switching + single executable. חודש 3: DHT + PEX. חודש 4: "
    "MSE/PE + BEP-52. חודש 5+: UX polish, performance, operations."
)


# ORIGINAL-source body indices (from docs/ספר פרוייקט אדם זבולון.docx,
# pre any other edit pass). Verified via dump_source_range.py.
REPLACEMENTS = {
    1349: PARA_25_NOT_DONE,   # §25 "מה לא הצליח" — drop _load_state
    1377: PARA_26_PRIORITIES, # §26 "סדר עדיפויות מומלץ" — drop auto-resume
}
INSERT_PARA_AFTER = {1348: PARA_25_NEW_INSIGHT}  # after "Type hints" insight
REMOVE_INDICES = [1363]  # §26 auto-resume future-work entry — done now.


def apply(body: etree._Element, snapshot: list[etree._Element], W: str) -> None:
    WNS = f"{{{W}}}"

    for idx, prose in REPLACEMENTS.items():
        p = snapshot[idx]
        if p.tag != f"{WNS}p":
            raise RuntimeError(f"snapshot[{idx}] is not <w:p> (got {p.tag})")
        replace_paragraph_text(p, prose)

    for idx, prose in INSERT_PARA_AFTER.items():
        snapshot[idx].addnext(build_paragraph(prose))

    for idx in REMOVE_INDICES:
        elem = snapshot[idx]
        parent = elem.getparent()
        if parent is None:
            raise RuntimeError(f"snapshot[{idx}] has no parent (already removed?)")
        parent.remove(elem)
