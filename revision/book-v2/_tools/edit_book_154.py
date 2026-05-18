"""Book §15.4 (חישוב יעילות האלגוריתם) — algorithm depth.

The pristine source §15.4 (idx 891) discusses complexity at the right
level for the chapter, but doesn't reach the algorithmic depth the
teacher demanded. This pass appends four sub-subsections after the
existing §15.4 body (after idx 897, before the empty paragraphs that
precede §15.5):

  §15.4.1  Rarest-first — Thundering Herd + "מה לא מומש"
  §15.4.2  Sliding-window contribution metric
  §15.4.3  Snubbing — זיהוי peers שהשתתקו
  §15.4.4  מצב Seeding — אלגוריתם post-completion

NB. These were previously (and wrongly) inserted in the project
proposal area (idx 180–206). They are now in the book proper.
"""
from __future__ import annotations

from runs_builder import build_heading, build_paragraph


# --- §15.4.1 rarest-first depth + thundering herd ---------------------------

H_1541 = "15.4.1 Rarest-first — מה לא מומש, ונקודת כאב Thundering Herd"

PARAS_1541 = [
    (
        "**מה לא מומש (במכוון).** המימוש של rarest-first הוא "
        "**תת-קבוצה** של מה ש-BEP-3 ומימושי הפרודקשן עושים. הפערים, "
        "ולמה הם בכוונה: (א) **endgame mode** מפורש לא קיים — בפועל "
        "יש לזה תחליף דרך stale-piece reset כל 10 שניות (piece "
        "שעבר את ה-timeout שלו חוזר ל-MISSING וה-loop יבחר אותו "
        "שוב). endgame mode אמיתי דורש שליחת אותו request למספר "
        "peers במקביל ו-cancel ברגע ש-block מתקבל מאחד מהם — "
        "מורכבות שלא נצרכת בגדלי ה-swarms הצפויים. "
        "(ב) **priority/cancellation games** (העדפת חתיכות "
        "ספציפיות לקובץ נצפה) לא קיימות; אין תמיכה ב-selective "
        "download. (ג) **הגנה מ-peers שמשקרים על ה-bitfield שלהם** "
        "מסתכמת ב-SHA-1 verify על ה-piece שמתקבל; אין ניטור "
        "סטטיסטי של peers שמודיעים על pieces ולא מספקים אותם."
    ),
    (
        "**נקודת כאב — Thundering Herd.** בגרסה הראשונה של בחירת "
        "ה-piece הנדיר היה מימוש ישיר: "
        "`min(piece_counts.items(), key=lambda kv: kv[1])`. זה עבד "
        "מבחינה אלגוריתמית — מחזיר את ה-piece עם הספירה הנמוכה "
        "ביותר. הבעיה התגלתה בבדיקה עם 4 peers שמתחילים יחד "
        "ל-swarm: **כולם בחרו את אותו ה-piece הנדיר באותו רגע**, "
        "וכולם שלחו request ל-peer היחיד שמחזיק בו. ה-peer הזה "
        "נחנק (queue ארוך ב-`pending_requests`), ושלושת השאר חיכו "
        "במקום להעמיס בקשות על peers אחרים."
    ),
    (
        "**התיקון.** מעבר מ-`min()` ל-`random.choice` על הסט הנדיר: "
        "בכל סיבוב מחושב הערך המינימלי של `piece_counts`, נבנה list "
        "של *כל* ה-pieces שספירתם שווה למינימום (ה-tie set), ו-"
        "`random.choice` בוחר אחד. ראה `piece_manager.py:313` — "
        "שורה אחת ששוברת את התופעה. כשמספר peers מתחילים יחד, כל "
        "אחד בוחר piece שונה מתוך ה-tie set, וה-requests מתפזרות. "
        "ה-peer היחיד עם החצי הנדיר עדיין משרת את כל הבקשות "
        "שמגיעות, אבל ה-peers האחרים מסתעדכים מ-peers מקבילים על "
        "החצי השכיח."
    ),
    (
        "**הוכחה אמפירית** של התיקון נמצאת ב-§24: ב-swarm סינתטי "
        "שבו piece אחד נמצא רק אצל peer יחיד, ה-rarest-first מנתב "
        "אליו את כל בקשות החצי הנדיר באופן דטרמיניסטי על פני 5 הרצות, "
        "וה-`full` peer מספק בדיוק 512.0 KB (8 חתיכות × 64 KB) — "
        "החצי הנדיר במלואו, בלי בזבוז בקשות על חתיכות שכיחות."
    ),
]


# --- §15.4.2 sliding-window contribution ------------------------------------

H_1542 = "15.4.2 Tit-for-Tat — חלון זמן sliding"

PARAS_1542 = [
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
        "**למה דווקא 20 שניות?** `choke_interval` הוא 10 שניות. "
        "חלון קצר מדי (5s) ייצור מדד רועש שיניע החלטות שלא לצורך; "
        "חלון ארוך מדי (60s) יחזיר את הבעיה של ה-cumulative — peer "
        "שעבר ממהיר לאיטי לא ירגיש בשינוי במשך כמה מחזורים שלמים. "
        "שני מחזורי choke הם מינימום ההגיוני להחלקה."
    ),
    (
        "**הקוד.** `peer_connection.py`: קבועים "
        "`DOWNLOAD_SAMPLE_RETENTION = 30`, `TIT_FOR_TAT_WINDOW = 20.0`; "
        "deque `_download_samples` עם append+eviction ב-handler של "
        "PIECE; accessor `bytes_received_in_window(window)`. "
        "`download_manager.py`: ב-`_tit_for_tat_unchoke` המיון "
        "משתמש ב-`bytes_received_in_window` במקום ב-`bytes_downloaded`."
    ),
]


# --- §15.4.3 snubbing -------------------------------------------------------

H_1543 = "15.4.3 Snubbing — זיהוי peers שהשתתקו"

PARAS_1543 = [
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
        "ו-(ג) נשלחה אליו לפחות בקשה אחת — כדי לא לסמן peer חדש "
        "שעוד לא נבחנו ממנו blocks. שלושת התנאים יחדיו נבדקים ב-"
        "`PeerConnection.is_snubbed()`."
    ),
    (
        "**הטיפול.** ב-`_tit_for_tat_unchoke` נעשית partition של "
        "ה-peers ל-`non_snubbed` ול-`snubbed` *לפני* המיון. "
        "ה-non_snubbed מומיינים לפי חלון התרומה ונבחר מהם ה-top-K. "
        "peers snubbed נשקלים רק אם ה-non_snubbed דליל מ-4 "
        "candidates. בנוסף, ברגע שמזוהה לראשונה peer חדש כ-snubbed, "
        "מופעל optimistic unchoke מיידי במחזור הנוכחי — לא ממתינים "
        "למחזור הבא — כדי לנסות למצוא לו תחליף מבחוץ."
    ),
    (
        "**למה דווקא 60 שניות?** הסף מאזן בין שני כשלים: סף קצר "
        "מדי (30s) יסמן peers איטיים אבל אמיתיים כ-snubbed, פשוט "
        "כי תור הבקשות שלהם ארוך יותר. סף ארוך מדי (90s+) משאיר "
        "peer מת ב-top-K זמן רב מדי. 60 שניות הוא הסף הסטנדרטי "
        "במימושי BitTorrent ומשתלב טוב עם `choke_interval` של 10s — "
        "6 מחזורים שלמים בלי block הם סימן אמין למוות."
    ),
    (
        "**הקוד.** `peer_connection.py`: שדה `last_block_received_at` "
        "(מתעדכן בכל קבלת PIECE), שדה `last_request_sent_at`, "
        "ו-method `is_snubbed(threshold=60.0)`. `download_manager.py`: "
        "ה-partition + replacement-optimistic-unchoke ב-"
        "`_tit_for_tat_unchoke`."
    ),
]


# --- §15.4.4 seeding mode ---------------------------------------------------

H_1544 = "15.4.4 מצב Seeding — אלגוריתם post-completion"

PARAS_1544 = [
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
        "אין partition בין snubbed ל-non-snubbed; המיון מבוסס אך "
        "ורק על `bytes_sent_in_window`. ההפרדה הזו בין שני "
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


INSERT_AFTER_IDX = 897  # last content paragraph of §15.4 (SHA-1 / ThreadPool).


def apply(body, snapshot, W):
    anchor = snapshot[INSERT_AFTER_IDX]

    def insert(elem):
        nonlocal anchor
        anchor.addnext(elem)
        anchor = elem

    insert(build_heading(H_1541, level=3))
    for prose in PARAS_1541:
        insert(build_paragraph(prose))

    insert(build_heading(H_1542, level=3))
    for prose in PARAS_1542:
        insert(build_paragraph(prose))

    insert(build_heading(H_1543, level=3))
    for prose in PARAS_1543:
        insert(build_paragraph(prose))

    insert(build_heading(H_1544, level=3))
    for prose in PARAS_1544:
        insert(build_paragraph(prose))
