"""§5.2 (Python modules) — append a bencode + info_hash worked example.

Inserts a new H4 sub-subsection at the end of §5.2 (after idx 127),
just before the §5.3 heading. Title and three body paragraphs walk
through how `bencode.encode` serialises an `info` dict in canonical
form and how SHA-1 over those exact bytes yields the `info_hash`.
"""
from __future__ import annotations

from runs_builder import build_heading, build_paragraph


H = "5.2.1 דוגמה מעובדת — Bencode + info_hash"

PARAS = [
    (
        "**ה-bencode בקצרה.** ה-format מקודד 4 טיפוסים: מספר שלם "
        "(`i42e`), מחרוזת בתים (`5:hello` — אורך, נקודתיים, בתים), "
        "רשימה (`l...e`), ומילון (`d...e` — זוגות מפתח-ערך). הסדר "
        "החובה: מפתחות במילון מסודרים *לקסיקוגרפית כבתים*, לא "
        "כמחרוזות UTF-8. הקידוד הוא **קנוני** — לאותה תוכן יש בדיוק "
        "בייטים אחד."
    ),
    (
        "**דוגמה.** ניקח info dict מינימלי: "
        "`{ b'length': 4, b'name': b'a', b'piece length': 16384, "
        "b'pieces': <20 bytes> }`. המפתחות הממוינים כבתים: "
        "`length` < `name` < `piece length` < `pieces`. הקידוד "
        "ה-bencoded יוצא: "
        "`d6:lengthi4e4:name1:a12:piece lengthi16384e6:pieces20:<...>e`. "
        "ה-`info_hash` הוא פשוט `hashlib.sha1(...).digest()` על "
        "הבייטים האלה — 20 בתים בדיוק."
    ),
    (
        "**למה הקידוד חייב להיות קנוני?** אם נסדר את המפתחות "
        "אחרת — למשל `name` לפני `length` — נקבל hash אחר. ה-peer "
        "השני, שמחשב hash על אותו .torrent, יקבל את ה-hash הקנוני; "
        "אם הקידוד שלנו אינו קנוני, ה-handshake יידחה כ-info_hash "
        "mismatch. לכן `bencode.py:110-123` ממיין מפתחות לפני הקידוד, "
        "ו-`bencode.py:51-71` *דוחה* mפתחות לא ממוינים בעת הפענוח — "
        "שני הצדדים של אותה אחריות."
    ),
    (
        "**Round-trip עצמי.** `torrent_metadata.py:100-102` ממש את "
        "החישוב: קורא את ה-bencoded `info` dict הגולמי מתוך קובץ "
        "ה-.torrent (לא משחזר אותו מ-Python dict — שומר את ה-bytes "
        "המקוריים בדיוק כפי שהם), ועליו מריץ SHA-1. כך נמנעים תרחישי "
        "round-trip שבו פענוח + הקודוד-מחדש משנה את הסדר וגורם "
        "ל-hash אחר."
    ),
    (
        "**Edge cases.** `bencode.py` דוחה גם: מספרים עם leading "
        "zeros (`i07e`), מספרים שליליים זרים (`i-0e`), ומחרוזות "
        "באורך לא תקין. הדחיות האלה אינן \"קוסמטיות\" — peer זדוני "
        "יכול לנסות לעקוף ולידציה דרך קידוד לא קנוני שעדיין מתפענח "
        "לאותו ערך לוגי."
    ),
]


INSERT_AFTER_IDX = 127  # last bullet of §5.2 (api_server.py).


def apply(body, snapshot, W):
    anchor = snapshot[INSERT_AFTER_IDX]

    def insert(elem):
        nonlocal anchor
        anchor.addnext(elem)
        anchor = elem

    insert(build_heading(H, level=4))
    for prose in PARAS:
        insert(build_paragraph(prose))
