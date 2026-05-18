"""Book §11.6 (תיאור פרוטוקולי התקשורת) — handshake / framing / bencode depth.

The pristine source §11.6 (idx 705) already lists protocols at a
high level but lacks the byte-level depth the teacher asked for.
This pass appends three H3 sub-subsections after the existing §11.6
body, before §11.7 (idx 711):

  §11.6.1  מבנה ה-Handshake בבייטים  — 68-byte hex breakdown table
  §11.6.2  TCP framing — readexactly walkthrough
  §11.6.3  Bencode + info_hash worked example

NB. These were previously (and wrongly) inserted in the project
proposal area (idx 155–166). They are now in the book proper.
The proposal area (idx 0–304) is left untouched.
"""
from __future__ import annotations

from runs_builder import build_heading, build_paragraph
from table_builder import build_table


# --- §11.6.1 handshake ------------------------------------------------------

H_1161 = "11.6.1 מבנה ה-Handshake בבייטים"

PARAS_1161_BEFORE_TABLE = [
    (
        "ה-handshake הוא חבילה של **68 בתים בדיוק** שכל peer חייב לשלוח "
        "ולקבל מיד אחרי פתיחת חיבור ה-TCP, *לפני* כל הודעת BitTorrent "
        "אחרת. אורך קבוע, מבנה קבוע — ה-peer הצד-שני מסרב לדבר בלעדיו. "
        "הטבלה הבאה מציגה את 68 הבתים מ-offset 0 עד 67:"
    ),
]

HANDSHAKE_TABLE_ROWS = [
    ["Offset", "Size", "Field", "Example bytes"],
    ["0", "1", "pstrlen", "`13` (decimal 19 — אורך המחרוזת הבאה)"],
    [
        "1",
        "19",
        "pstr",
        "`42 69 74 54 6f 72 72 65 6e 74 20 70 72 6f 74 6f 63 6f 6c` "
        "(\"BitTorrent protocol\")",
    ],
    ["20", "8", "reserved", "`00 00 00 00 00 00 00 00` (לא בשימוש ב-BEP-3)"],
    ["28", "20", "info_hash", "SHA-1 של ה-bencoded info dict"],
    ["48", "20", "peer_id", "`-PG0001-` + 12 בתים אקראיים"],
]
HANDSHAKE_TABLE_WIDTHS = [880, 880, 1320, 4840]

PARAS_1161_AFTER_TABLE = [
    (
        "**ולידציה.** אחרי שליחת ה-handshake היוצא, ה-Engine קורא 68 "
        "בתים מהצד השני. אם `pstrlen != 19` או אם ה-`pstr` אינו "
        "`b'BitTorrent protocol'` — נסגר החיבור מיד "
        "(`peer_connection.py:206-216`). אם ה-`info_hash` שמתקבל אינו "
        "תואם ל-info_hash של ה-torrent הנדון, נסגר החיבור: ה-peer "
        "מנסה לדבר על torrent אחר. רק אז ה-state machine עוברת "
        "ל-HANDSHAKE_COMPLETE ומאפשרת לקבל הודעות length-prefixed."
    ),
    (
        "**למה info_hash ולא hash על כל ה-.torrent?** ה-`announce` URL "
        "ושאר השדות החיצוניים יכולים להשתנות בין trackers שונים של אותו "
        "torrent (BEP-12 announce-list). רק ה-`info` dict מזהה את התוכן "
        "עצמו, ולכן ה-hash מחושב על הקידוד הקנוני של ה-`info` בלבד — "
        "ראה §11.6.3 לדוגמת חישוב מלאה."
    ),
    (
        "**הקוד.** `peer_connection.py`: `_send_handshake` (שליחה — 68 "
        "בתים נבנים כ-concatenation של `bytes([19]) + PROTOCOL_STRING + "
        "b'\\x00'*8 + info_hash + peer_id`), `_receive_handshake` "
        "(קריאה עם `reader.readexactly(68)` ואז ולידציה לכל שדה)."
    ),
]


# --- §11.6.2 TCP framing ----------------------------------------------------

H_1162 = "11.6.2 TCP framing — למה זה לא טריוויאלי"

PARAS_1162 = [
    (
        "**הבעיה.** TCP הוא byte stream, לא message stream. "
        "`socket.recv(1024)` עלולה להחזיר חלק מהודעה, או שתי הודעות "
        "מודבקות, או הודעה וחצי. מערכת ההפעלה לא שומרת על גבולות "
        "ההודעות — היא רק מספקת זרם בייטים מסודר. כל פרוטוקול שמדבר "
        "על TCP חייב להגדיר framing משלו."
    ),
    (
        "**הפתרון של BitTorrent.** כל הודעה אחרי ה-handshake היא "
        "`4-byte big-endian length prefix` ואז `length bytes של "
        "payload`. הגישה במימוש: `reader.readexactly(4)` קוראת בדיוק "
        "4 בתים (ממתינה אם פחות הגיע); ממירה ל-`int` עם "
        "`int.from_bytes(buf, 'big')`; ואז `reader.readexactly(length)` "
        "קוראת בדיוק את ה-payload. `readexactly` כשלעצמה ממתינה בלולאה "
        "פנימית על kernel buffer עד שיש את כמות הבתים המבוקשת, ומחזירה "
        "buffer נקי בלי חצאי-הודעות."
    ),
    (
        "**דוגמה.** נניח שה-peer שולח HAVE(piece=10) ואחריו מיד "
        "PIECE(piece=3, offset=0, 2000 בתים). TCP יכול למסור את שתי "
        "ההודעות יחד במנה אחת של 2013 בתים (4+5 ל-HAVE, 4+2000 ל-PIECE), "
        "או לחתוך אותן באמצע. ה-parser אינו רגיש לזה: `readexactly(4)` "
        "תקבל `00 00 00 05`; `readexactly(5)` תקבל `04 00 00 00 0A` "
        "(msg_id=4=HAVE, payload=piece index 10); הסיבוב הבא של הלולאה "
        "יקרא 4 בתים נוספים — ה-length של ההודעה הבאה. אין remainder "
        "buffer לנהל, אין parser state — `readexactly` מקדם את הזרם "
        "בעצמו."
    ),
    (
        "**Edge cases שטופלו מפורש.** (א) `length=0` נחשב keep-alive — "
        "אין msg_id ואין payload; פשוט קריאה ל-4 בתים הבאים. "
        "(ב) `length > MAX_MESSAGE_SIZE` (16 KB + slack) דוחה את ה-peer; "
        "מונע OOM מ-peer זדוני. (ג) קריאה שמסתיימת ב-EOF באמצע "
        "(`asyncio.IncompleteReadError`) נסגרת בנקיון."
    ),
    (
        "**הקוד.** `peer_connection.py`: `_read_message` (הלולאה "
        "המרכזית — `readexactly(4)` → length → `readexactly(length)` "
        "→ דיספטץ לפי msg_id); `MAX_MESSAGE_SIZE` קבוע; הטיפול "
        "ב-IncompleteReadError ב-`run()`."
    ),
]


# --- §11.6.3 bencode + info_hash --------------------------------------------

H_1163 = "11.6.3 דוגמה מעובדת — Bencode + info_hash"

PARAS_1163 = [
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
        "קידוד לא קנוני יידחה כ-info_hash mismatch ב-handshake. לכן "
        "`bencode.py:110-123` ממיין מפתחות לפני הקידוד, ו-"
        "`bencode.py:51-71` *דוחה* מפתחות לא ממוינים בעת הפענוח — "
        "שני הצדדים של אותה אחריות."
    ),
    (
        "**Round-trip עצמי.** `torrent_metadata.py:100-102` ממש את "
        "החישוב: קורא את ה-bencoded `info` dict הגולמי מתוך קובץ "
        "ה-.torrent (לא משחזר אותו מ-Python dict — שומר את ה-bytes "
        "המקוריים בדיוק כפי שהם), ועליו מריץ SHA-1. כך נמנעים תרחישי "
        "round-trip שבו פענוח + קידוד-מחדש משנה את הסדר וגורם "
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


INSERT_AFTER_IDX = 710  # last paragraph of §11.6 in pristine source.


def apply(body, snapshot, W):
    anchor = snapshot[INSERT_AFTER_IDX]

    def insert(elem):
        nonlocal anchor
        anchor.addnext(elem)
        anchor = elem

    insert(build_heading(H_1161, level=3))
    for prose in PARAS_1161_BEFORE_TABLE:
        insert(build_paragraph(prose))
    insert(build_table(HANDSHAKE_TABLE_ROWS, HANDSHAKE_TABLE_WIDTHS, header=True))
    for prose in PARAS_1161_AFTER_TABLE:
        insert(build_paragraph(prose))

    insert(build_heading(H_1162, level=3))
    for prose in PARAS_1162:
        insert(build_paragraph(prose))

    insert(build_heading(H_1163, level=3))
    for prose in PARAS_1163:
        insert(build_paragraph(prose))
