"""§6.2 (Peer Wire Protocol) edit pass — add §6.2.1 + §6.2.2.

Inserts two new H4 sub-subsections after idx 166 (last existing
message-type bullet), before idx 167 (the image-bearing "תרשים רצף
הורדה" heading — never touched).

  §6.2.1  מבנה ה-Handshake בבייטים  — 68-byte hex breakdown table
  §6.2.2  TCP framing — למה זה לא טריוויאלי  — readexactly walkthrough
"""
from __future__ import annotations

from lxml import etree

from runs_builder import build_heading, build_paragraph
from table_builder import build_table


H_621 = "6.2.1 מבנה ה-Handshake בבייטים"

PARAS_621_BEFORE_TABLE = [
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


PARAS_621_AFTER_TABLE = [
    (
        "**ולידציה.** אחרי שליחת ה-handshake היוצא, ה-Engine קורא 68 "
        "בתים מהצד השני. אם `pstrlen != 19` או אם ה-`pstr` אינו "
        "`b'BitTorrent protocol'` — נסגר החיבור מיד (`peer_connection.py:206-216`). "
        "אם ה-`info_hash` שמתקבל אינו תואם ל-info_hash של ה-torrent הנדון, "
        "נסגר החיבור: ה-peer מנסה לדבר על torrent אחר. רק אז ה-state "
        "machine עוברת ל-`HANDSHAKE_COMPLETE` ומאפשרת לקבל הודעות "
        "length-prefixed."
    ),
    (
        "**למה info_hash ולא hash על כל ה-.torrent?** ה-`announce` URL "
        "ושאר השדות החיצוניים יכולים להשתנות בין trackers שונים של אותו "
        "torrent (BEP-12 announce-list). רק ה-`info` dict מזהה את התוכן "
        "עצמו, ולכן ה-hash מחושב על הקידוד הקנוני של ה-`info` בלבד — "
        "ראה §5.2 לדוגמת חישוב מלאה."
    ),
    (
        "**הקוד.** `peer_connection.py`: `_send_handshake` (שליחה — 68 "
        "בתים נבנים בלולאה ב-`bytes.fromhex` + concatenation), "
        "`_receive_handshake` (קריאה עם `reader.readexactly(68)` ואז "
        "ולידציה לכל שדה)."
    ),
]


H_622 = "6.2.2 TCP framing — למה זה לא טריוויאלי"

PARAS_622 = [
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
        "ההודעות יחד במנה אחת של 2013 בתים (4 + 5 ל-HAVE, 4 + 2000 "
        "ל-PIECE), או לחתוך אותן באמצע. ה-parser שלי לא יודע לזה: "
        "`readexactly(4)` תקבל `00 00 00 05`; `readexactly(5)` תקבל "
        "`04 00 00 00 0A` (msg_id=4=HAVE, payload=piece index 10); "
        "הסיבוב הבא של הלולאה יקרא 4 בתים נוספים — ה-length של "
        "ההודעה הבאה. אין remainder buffer לנהל, אין parser state — "
        "`readexactly` מקדם את הזרם בעצמו."
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


INSERT_AFTER_IDX = 166  # last message-bullet, just before image-bearing H4.


def apply(body, snapshot, W):
    anchor = snapshot[INSERT_AFTER_IDX]

    def insert(elem):
        nonlocal anchor
        anchor.addnext(elem)
        anchor = elem

    insert(build_heading(H_621, level=4))
    for prose in PARAS_621_BEFORE_TABLE:
        insert(build_paragraph(prose))
    insert(build_table(HANDSHAKE_TABLE_ROWS, HANDSHAKE_TABLE_WIDTHS, header=True))
    for prose in PARAS_621_AFTER_TABLE:
        insert(build_paragraph(prose))

    insert(build_heading(H_622, level=4))
    for prose in PARAS_622:
        insert(build_paragraph(prose))
