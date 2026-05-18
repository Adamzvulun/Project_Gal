"""§25.5 (NEW) — Honest limitations chapter (PLAN §4g).

Adds a new H2 sub-section at the end of §25 (conclusions), before the
§26 H1 heading. Lists explicitly what the system does NOT do, each
item with one line + future-work pointer. Pattern: pure honesty,
zero bravado.
"""
from __future__ import annotations

from runs_builder import build_heading, build_paragraph


H = "25.5 מה המערכת אינה עושה — רשימה גלויה"

INTRO = (
    "התיאור עד כאן מתמקד במה שעובד. כאן מרוכז במכוון מה שאינו "
    "כלול — כדי שלכל קורא יהיה ברור הגבול בין מה שהפרויקט מצהיר "
    "עליו לבין מה שלקוח BitTorrent מסחרי מספק. כל פריט מקושר "
    "ל-§26 (פיתוחים עתידיים) שם מפורט אומדן המאמץ למימוש."
)


BULLETS = [
    "**חיבורים נכנסים / NAT traversal.** אין `asyncio.start_server` "
    "על פורט 6881; אין UPnP או STUN; המערכת רק יוזמת חיבורים יוצאים. "
    "המשמעות: מאחורי NAT, התרומה ל-swarm מוגבלת ל-peers שמסוגלים "
    "לפתוח חיבור כלפי המכונה הזו. ראה §26 → \"שרת listen נכנס\" + "
    "\"NAT Traversal\".",

    "**DHT (BEP-5).** המערכת תלויה לחלוטין ב-tracker שמוגדר "
    "בקובץ ה-.torrent. אם ה-tracker נופל אין דרך אלטרנטיבית "
    "לגלות peers. Kademlia DHT לא ממומש. ראה §26 → \"DHT\".",

    "**Peer Exchange (BEP-11).** אין הודעת `ut_pex` שמחליפה "
    "רשימות peers בין peers ישירות; הצטרפות peers חדשים תלויה "
    "כולה ב-announce הבא ל-tracker. ראה §26 → \"Peer Exchange\".",

    "**MSE/PE — הצפנת הזרם.** אין `Message Stream Encryption` "
    "מבוסס Diffie-Hellman/RC4; DPI של ISPs יכול לזהות תעבורת "
    "BitTorrent. ראה §26 → \"MSE/PE\".",

    "**UDP Tracker (BEP-15).** רק HTTP/HTTPS tracker נתמכים; "
    "trackers מבוססי UDP — שהם דווקא הנפוצים יותר ב-public "
    "trackers — לא מטופלים. הקובץ ה-.torrent חייב לכלול לפחות "
    "tracker HTTP אחד.",

    "**IPv6.** ה-`compact peer parsing` תומך רק ב-IPv4 (6 בתים "
    "לכל peer). הרחבת `compact6` (18 בתים) לפי BEP-7 לא ממומשת. "
    "ראה §26 → \"IPv6\".",

    "**BEP-10 Extension Protocol.** הודעת `id=20` שמאפשרת הוספת "
    "extensions בלי לשבור תאימות (PEX, metadata-via-peers, "
    "holepunching) — לא ממומשת. כל המבנה החיבורים נותר ב-BEP-3 "
    "בלבד.",

    "**Magnet links.** הזנת torrent דורשת קובץ `.torrent` עם "
    "ה-info dict מלא; אין `bep_0009` שמאפשר משיכת metadata "
    "מ-peers על בסיס info_hash בלבד.",

    "**BitTorrent v2 (BEP-52).** SHA-1 בלבד; אין SHA-256 ואין "
    "Merkle Trees לאימות חלקי piece. v1 ו-hybrid mode לא נתמכים. "
    "ראה §26 → \"BitTorrent v2\".",
]


OUTRO = (
    "**מפורש לא ברשימה הזו** (כי בגרסה הנוכחית הם **כן** "
    "ממומשים): sliding-window contribution, snubbing detection, "
    "seeding-mode unchoke, ו-`_load_state` שמשחזר הורדה אחרי "
    "crash. שלושה הראשונים מתוארים ב-§7.2.1, §7.2.2, §7.2.3; "
    "ה-`_load_state` ב-§25 ובקוד `Download.from_state_file`."
)


INSERT_AFTER_IDX = 1349  # the "מה לא הצליח" paragraph in pristine source.


def apply(body, snapshot, W):
    anchor = snapshot[INSERT_AFTER_IDX]

    def insert(elem):
        nonlocal anchor
        anchor.addnext(elem)
        anchor = elem

    insert(build_heading(H, level=2))
    insert(build_paragraph(INTRO))
    for b in BULLETS:
        insert(build_paragraph(b))
    insert(build_paragraph(OUTRO))
