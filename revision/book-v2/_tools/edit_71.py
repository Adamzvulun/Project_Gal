"""§7.1 rarest-first — deepening + pain-point insert.

Inserts depth between the existing implementation description
(ends at idx 180) and the complexity sub-section (starts idx 181).
Two short paragraphs: what's NOT implemented (intentionally), and the
thundering-herd pain story that motivated the random tie-break.
"""
from __future__ import annotations

from runs_builder import build_heading, build_paragraph


H_NOT_IMPL = "7.1.1 מה לא מומש (במכוון)"

PARAS_NOT_IMPL = [
    (
        "המימוש של rarest-first בפרויקט הוא **תת-קבוצה** של מה "
        "ש-BEP-3 ומימושי הפרודקשן עושים. הפערים, ולמה הם בכוונה: "
        "(א) **endgame mode** מפורש לא קיים — בפועל יש לזה תחליף "
        "באמצעות stale-piece reset כל 10 שניות (piece שעבר את "
        "ה-timeout שלו חוזר ל-MISSING, וה-loop יבחר אותו שוב). "
        "endgame mode אמיתי דורש שליחת אותו request למספר peers "
        "במקביל ו-cancel ברגע ש-block מתקבל מאחד מהם — מורכבות "
        "שלא נצרכת בגדלי ה-swarms הצפויים. "
        "(ב) **priority / cancellation games** (העדפת חתיכות "
        "ספציפיות לקובץ נצפה) לא קיימות; הפרויקט אינו תומך ב-"
        "selective download. (ג) **הגנה מ-peers שמשקרים על "
        "ה-bitfield שלהם** מסתכמת ב-SHA-1 verify על ה-piece שמתקבל; "
        "אין ניטור סטטיסטי של peers שמודיעים על pieces ולא מספקים "
        "אותם."
    ),
]


H_THUNDER = "7.1.2 נקודת כאב — Thundering Herd"

PARAS_THUNDER = [
    (
        "בגרסה הראשונה של בחירת ה-piece הנדיר ביותר היה מימוש "
        "ישיר: `min(piece_counts.items(), key=lambda kv: kv[1])`. "
        "זה עבד מבחינה אלגוריתמית — מחזיר את ה-piece עם הספירה "
        "הנמוכה ביותר. הבעיה התגלתה בבדיקה עם 4 peers שמתחילים "
        "יחד ל-swarm: **כולם בחרו את אותו ה-piece הנדיר באותו רגע**, "
        "וכולם שלחו request ל-peer היחיד שמחזיק בו. ה-peer הזה "
        "נחנק (queue ארוך ב-`pending_requests`), ושלושת השאר חיכו "
        "במקום להעמיס בקשות על peers אחרים. הסיבוב הבא חזר על "
        "התופעה."
    ),
    (
        "התיקון, שהוא מעבר מ-`min()` ל-`random.choice` על הסט "
        "הנדיר: בכל סיבוב מחושב מהו ערך המינימום של "
        "`piece_counts`, נבנה list של *כל* ה-pieces שספירתם שווה "
        "למינימום הזה (ה-tie set), ואז `random.choice` בוחר אחד. "
        "ל-piece_manager.py:313 — שורה אחת ששוברת את התופעה. "
        "כשמספר peers מתחילים יחד, כל אחד בוחר piece שונה מתוך "
        "ה-tie set, וה-requests מתפזרות. ה-peer היחיד עם החצי "
        "הנדיר עדיין משרת את כל הבקשות שמגיעות, אבל ה-peers האחרים "
        "מסתעדכים מ-peers מקבילים על החצי השכיח."
    ),
    (
        "ראה `piece_manager.py:279-317` למימוש מלא — "
        "`select_piece_rarest_first`."
    ),
]


INSERT_AFTER_IDX = 180  # last "bullet" of selection description.


def apply(body, snapshot, W):
    anchor = snapshot[INSERT_AFTER_IDX]

    def insert(elem):
        nonlocal anchor
        anchor.addnext(elem)
        anchor = elem

    insert(build_heading(H_NOT_IMPL, level=4))
    for prose in PARAS_NOT_IMPL:
        insert(build_paragraph(prose))
    insert(build_heading(H_THUNDER, level=4))
    for prose in PARAS_THUNDER:
        insert(build_paragraph(prose))
