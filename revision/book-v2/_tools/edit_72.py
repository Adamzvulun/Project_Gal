"""§7.2 (Tit-for-Tat) edit pass — add three new sub-subsections.

Adds §7.2.1, §7.2.2, §7.2.3 immediately after the existing §7.2 body
(idx 206 in pristine source), before the "סיבוכיות" sub-section. Each
new sub-subsection is one Heading4 + several body paragraphs that
explain the why / how / where, citing file:line from the step 4a/4b/4c
code drops.
"""
from __future__ import annotations

from lxml import etree

from runs_builder import build_heading, build_paragraph


# --- §7.2.1 sliding-window contribution -------------------------------------

H_721 = "7.2.1 חלון זמן sliding — מדד תרומה מבוסס חלון"

PARAS_721 = [
    (
        "**הבעיה במדד המצטבר.** בגרסה הראשונה, מדד התרומה היה "
        "`bytes_downloaded` — מונה מצטבר של ה-bytes שכל peer העלה "
        "ל-Engine מתחילת ה-session. הבעיה: peer שתרם בכבדות בהתחלה "
        "ואחר כך השתתק שומר על ציון גבוה לנצח. אם peer חדש מצטרף "
        "ל-swarm או אם peer ותיק מתחיל לשלוח שוב, הציון המצטבר משקר "
        "על המצב הנוכחי וה-top-K לא מתעדכן עד שההפרש הופך לעצום."
    ),
    (
        "**הפתרון התואם לפרוטוקול.** BitTorrent מגדיר חלון זמן "
        "sliding של ~20 שניות לחישוב מדד התרומה. בכל קבלת PIECE "
        "message, נוסף sample `(timestamp, bytes_received)` ל-deque "
        "(`_download_samples` ב-`peer_connection.py`). ב-"
        "`_tit_for_tat_unchoke` המיון מבוסס על "
        "`PeerConnection.bytes_received_in_window(20.0)`, שמסכם "
        "דגימות שנכנסו ב-20 השניות האחרונות בלבד. דגימות ישנות מ-30 "
        "שניות מתפנות באופן עצל בכל קריאה — שני מחזורי choke (20s) "
        "מאוחסנים במלואם, עוד 10s מספקים margin לתזמון."
    ),
    (
        "**למה דווקא 20 שניות?** `choke_interval` הוא 10 שניות. חלון "
        "קצר מדי (5s) ייצור מדד רועש שיניע החלטות שלא לצורך; חלון "
        "ארוך מדי (60s) יחזיר את הבעיה של ה-cumulative — peer שעבר "
        "ממהיר לאיטי לא ירגיש בשינוי במשך כמה מחזורים שלמים. שני "
        "מחזורי choke הם מינימום ההגיוני להחלקה."
    ),
    (
        "**הקוד.** `peer_connection.py`: קבועים `DOWNLOAD_SAMPLE_RETENTION = 30`, "
        "`TIT_FOR_TAT_WINDOW = 20.0`; deque `_download_samples` עם "
        "append+eviction ב-handler של PIECE; accessor "
        "`bytes_received_in_window(window)`. `download_manager.py`: "
        "ב-`_tit_for_tat_unchoke` המיון משתמש ב-`bytes_received_in_window` "
        "במקום ב-`bytes_downloaded`."
    ),
]


# --- §7.2.2 snubbing --------------------------------------------------------

H_722 = "7.2.2 Snubbing — זיהוי peers שהשתתקו"

PARAS_722 = [
    (
        "**הבעיה.** peer שעשה unchoke (`peer_choking is False` — "
        "כלומר מסכים לשלוח blocks) אבל בפועל אינו שולח דבר תופס slot "
        "ב-top-K לפי המדד שלו מהעבר, ומונע מ-peer אחר לקבל הזדמנות. "
        "במצב הקיצוני, peer זדוני יכול לעשות unchoke ולא לשלוח כלום, "
        "וכך לזכות ב-bandwidth מתמיד מצד ה-Engine בלי שיתרום בעצמו. "
        "הפרוטוקול קורא לזה **snubbing**, ומגדיר טיפול: זיהוי + "
        "demotion."
    ),
    (
        "**ההגדרה.** peer נחשב snubbed אם מתקיימים בו-זמנית: "
        "(א) `peer_choking is False` (הוא הצהיר שיתן blocks), "
        "(ב) לא נקלט ממנו block של PIECE ב-60 השניות האחרונות "
        "(`time.time() - last_block_received_at > 60.0`), "
        "ו-(ג) נשלחה אליו לפחות בקשה אחת (`pending_requests` "
        "history is non-empty) — כדי לא לסמן peer חדש שעוד לא "
        "נבדק. שלושת התנאים יחדיו נבדקים ב-`PeerConnection.is_snubbed()`."
    ),
    (
        "**הטיפול.** ב-`_tit_for_tat_unchoke` נעשית partition של "
        "ה-peers ל-`non_snubbed` ול-`snubbed` *לפני* המיון. "
        "ה-non_snubbed מומיינים לפי חלון התרומה ונבחר מהם ה-top-K. "
        "peers snubbed נשקלים רק אם ה-non_snubbed דליל מ-4 candidates. "
        "בנוסף, ברגע שמזוהה לראשונה peer חדש כ-snubbed, מופעל "
        "optimistic unchoke מיידי במחזור הנוכחי — לא ממתינים למחזור "
        "הבא — כדי לנסות למצוא לו תחליף מבחוץ."
    ),
    (
        "**למה דווקא 60 שניות?** ספיציפית הסף הזה מאזן בין שני "
        "כשלים: סף קצר מדי (30s) יסמן peers איטיים אבל אמיתיים "
        "כ-snubbed, פשוט כי תור הבקשות שלהם ארוך יותר. סף ארוך מדי "
        "(90s+) משאיר peer מת ב-top-K זמן רב מדי. 60 שניות הוא הסף "
        "הסטנדרטי במימושי BitTorrent ומשתלב טוב עם `choke_interval` "
        "של 10s — 6 מחזורים שלמים בלי block הם סימן אמין למוות."
    ),
    (
        "**הקוד.** `peer_connection.py`: שדה `last_block_received_at` "
        "(מתעדכן בכל קבלת PIECE), שדה `last_request_sent_at`, "
        "ו-method `is_snubbed(threshold=60.0)`. `download_manager.py`: "
        "ה-partition + replacement-optimistic-unchoke ב-"
        "`_tit_for_tat_unchoke`."
    ),
]


# --- §7.2.3 seeding mode ----------------------------------------------------

H_723 = "7.2.3 מצב Seeding — אלגוריתם post-completion"

PARAS_723 = [
    (
        "**המקרה הקיצוני.** tit-for-tat הוא מטבעו אלגוריתם של leecher: "
        "הוא ממיין peers לפי \"כמה הם שלחו לי לאחרונה\". ברגע "
        "ש-`piece_manager.is_complete` הופך ל-True, ה-Engine לא מבקש "
        "blocks. ה-`bytes_received_in_window` הוא קבוע אפס לכל peer — "
        "לא כי הם אינם רוצים לשלוח, אלא כי אין מה לבקש. המיון "
        "מתפרק: כל peers שווים, וה-top-K הוא בעצם הסדר הראשוני של "
        "Python's `sorted` על ערכים שווים."
    ),
    (
        "**המדיניות הסטנדרטית.** מימושי BitTorrent (libtorrent, "
        "mainline) הופכים את כיוון המדד post-completion: לא \"מי "
        "שלח לי הכי הרבה\" אלא \"מי שאני שלחתי אליו הכי הרבה\". "
        "ה-peers שמושכים נתונים מהר מ-`send_piece` הם אלה עם "
        "downstream pipes טובים, ושירות עדיף שלהם תורם הכי הרבה "
        "ל-swarm. זוהי האסימטריה הטבעית של tit-for-tat — בהורדה "
        "המדד הוא inbound, בהפצה המדד הוא outbound."
    ),
    (
        "**המימוש.** ב-`peer_connection.py` נוסף deque סימטרי "
        "`_upload_samples` שמתעדכן בכל `send_piece`, ו-accessor "
        "`bytes_sent_in_window(window)`. ב-`download_manager.py` "
        "נוסף `DownloadState.SEEDING` ב-enum, predicate "
        "`_is_seeding()` (שמחזיר True כאשר `piece_manager.is_complete` "
        "*וגם* ה-state ב-`{COMPLETED, SEEDING}`), ו-"
        "`_seed_mode_unchoke` שממיין לפי `bytes_sent_in_window` "
        "ושומר על optimistic unchoke. ה-`_choke_loop` הראשי בודק "
        "`while RUNNING or _is_seeding()` כך שה-algorithm ממשיך "
        "להריץ decisions גם אחרי השלמת ההורדה."
    ),
    (
        "**מה לא קיים ב-seed mode.** snubbing אינו רלוונטי — peer "
        "שלא שולח blocks ל-Engine הוא הנורמלי בכל ה-seed mode (אין "
        "מה לשלוח כי לא מבוקש כלום ממנו, ה-Engine הוא המקור). לכן "
        "אין partition בין snubbed ל-non-snubbed; המיון מבוסס "
        "אך ורק על `bytes_sent_in_window`. ההפרדה הזו בין שני "
        "המנגנונים נשמרת מפורש בקוד דרך ה-branch ב-"
        "`_tit_for_tat_unchoke`."
    ),
    (
        "**נקודת כאב מתוך הפיתוח.** בגרסה הראשונה לא היה seed-mode "
        "branch בכלל. בדיקה הראתה ש-download שמסתיים מותיר את "
        "ה-`choke_loop` \"תקוע\" — כל peer מקבל ציון 0 ב-"
        "`bytes_received_in_window`, וה-top-K משתנה בעיקר עם "
        "optimistic unchoke. ההוספה של ה-branch ושל "
        "`bytes_sent_in_window` הוסיפה ~90 שורות, אבל בלעדיה המנגנון "
        "מתפרק בדיוק ברגע שבו ההפצה מתחילה."
    ),
    (
        "**הקוד.** `peer_connection.py`: `UPLOAD_SAMPLE_RETENTION = 30`, "
        "deque `_upload_samples`, append+eviction ב-`send_piece`, "
        "accessor `bytes_sent_in_window`. `download_manager.py`: "
        "`DownloadState.SEEDING`, `_is_seeding()` predicate, "
        "`_seed_mode_unchoke` method, ה-branch ב-"
        "`_tit_for_tat_unchoke`, וה-loop-condition המורחב ב-"
        "`_choke_loop`."
    ),
]


INSERT_AFTER_IDX = 206  # last empty paragraph before the existing "סיבוכיות".


def apply(body: etree._Element, snapshot: list[etree._Element], W: str) -> None:
    anchor = snapshot[INSERT_AFTER_IDX]

    def insert_block(heading_text: str, body_texts: list[str]) -> etree._Element:
        nonlocal anchor
        h = build_heading(heading_text, level=4)
        anchor.addnext(h)
        anchor = h
        for prose in body_texts:
            p = build_paragraph(prose)
            anchor.addnext(p)
            anchor = p
        return anchor

    insert_block(H_721, PARAS_721)
    insert_block(H_722, PARAS_722)
    insert_block(H_723, PARAS_723)
