"""Real upload-serving path + visible SEEDING state.

Follow-on session after book-v4. The engine gained a real upload path
(the REQUEST handler -> _serve_block_request -> send_piece, previously
never wired) and a visible COMPLETED -> SEEDING transition. This pass
brings the book in line with that:

  * §15.4.4 (seeding) — rewrite the implementation paragraph, insert the
    upload-path + visible-state paragraphs, and rewrite the pain point to
    the real one found this session (send_piece was dead code) and the
    code-locations list.
  * §24 (testing) — bump the unit-test count and mention the upload E2E.
  * §25.5 (limitations) — refine the NAT bullet: uploading to already-
    connected peers works; only accepting new inbound connections does not.

Runs as the LAST pass in apply_all, AFTER edit_book_154 / edit_24 /
edit_255, so it locates paragraphs in the live body by text content
rather than by the pristine-source snapshot index.
"""
from __future__ import annotations

from runs_builder import build_paragraph, replace_paragraph_text

WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _text_of(p) -> str:
    return "".join(t.text or "" for t in p.iter(f"{WNS}t"))


def _find(body, needle: str):
    for child in body:
        if child.tag == f"{WNS}p" and needle in _text_of(child):
            return child
    raise RuntimeError(f"paragraph not found for needle: {needle!r}")


# ── §24 ────────────────────────────────────────────────────────────────────

S24_COUNT = (
    "בתיקייה `python_engine/tests/` קיימות 222 פונקציות בדיקה המכסות את כל "
    "מודולי ה-Engine: bencode, torrent_metadata, piece_manager, "
    "peer_connection, tracker_client, download_manager, security ו-API "
    "server. כל הבדיקות רצות תחת pytest (כולל pytest-asyncio עבור "
    "הקורוטינות), והסוויטה כולה נכנסת בפחות מ-10 שניות על המחשב הביתי שבו "
    "פותח הפרויקט."
)

S24_E2E = (
    "תוספת end-to-end: מאחר וה-unit tests בודקים כל מודול בנפרד, נוסף ניסוי "
    "E2E שבודק את כל ה-Peer Wire Protocol stack בבת אחת. ב-"
    "`python_engine/tests/test_e2e_peer.py` מוקם peer-mock אסינכרוני שעונה "
    "ב-handshake → bitfield → unchoke → piece על פי BEP-3, וה-PeerConnection "
    "מנהל מולו handshake, מפענח את ה-length-prefix framing, שולח request, "
    "מקבל piece ומאמת SHA-1. הניסוי הזה הוא הראיה הישירה ש-handshake bytes, "
    "framing, state machine ו-hash verification עובדים יחד מקצה לקצה, ולא רק "
    "בנפרד. בנוסף, נוסף ניסוי E2E להוכחת נתיב ה-**העלאה** (upload): ב-"
    "`test_seeder_serves_block_to_requesting_peer` peer מתחבר, שולח "
    "`request`, וה-Engine מגיש לו את ה-block המדויק חזרה דרך `send_piece`; "
    "הבדיקה מאמתת שה-bytes שחצו את ה-socket זהים למקור ושה-`bytes_uploaded` "
    "עולה — הראיה ש-`send_piece` אכן מופעל ושהלקוח מעלה נתונים בפועל, ולא רק "
    "מוריד."
)


# ── §15.4.4 ──────────────────────────────────────────────────────────────────

S1544_IMPL = (
    "**המימוש.** ב-`peer_connection.py` נוסף deque סימטרי `_upload_samples` "
    "שמתעדכן בכל `send_piece`, ו-accessor `bytes_sent_in_window(window)`. "
    "ב-`download_manager.py` נוסף `DownloadState.SEEDING` ב-enum, predicate "
    "`_is_seeding()` (שמחזיר True כאשר `piece_manager.is_complete` *וגם* "
    "ה-state ב-{COMPLETED, SEEDING}), ו-`_seed_mode_unchoke` שממיין לפי "
    "`bytes_sent_in_window` ושומר על optimistic unchoke. ה-`_choke_loop` "
    "בודק `while RUNNING or _is_seeding()` כך שה-algorithm ממשיך להריץ "
    "decisions גם אחרי השלמת ההורדה."
)

S1544_UPLOAD = (
    "**נתיב ההעלאה עצמו.** כדי שמדד ה-seed-mode יהיה משמעותי חייב להיות מי "
    "שמגיש את ה-blocks בפועל. חיבורי BitTorrent הם דו-כיווניים: peer שאליו "
    "נפתח חיבור יוצא יכול לבקש ממנו blocks על אותו ה-socket. הטיפול בהודעת "
    "`REQUEST` ב-`_on_peer_message` מנתב ל-`_serve_block_request`, שבודק "
    "שה-peer אינו choked, שה-piece קיים ו-COMPLETED, ושה-bounds תקינים "
    "(גודל ≤ `BLOCK_SIZE`, בתוך גבולות ה-piece), קורא את ה-block מהזיכרון "
    "דרך `_read_block_sync`, ושולח אותו ב-`send_piece`. זהו המקום היחיד שבו "
    "`send_piece` נקרא, ולכן הוא מה שהופך את הלקוח למעלה נתונים בפועל ומזין "
    "את ה-sliding window של ה-seed-mode."
)

S1544_STATE = (
    "**מצב גלוי למשתמש.** סיום ההורדה מסמן את ה-state תחילה כ-`COMPLETED` "
    "(כך שה-popup וההיסטוריה ב-GUI נרשמים על פי המצב הזה), ובתחילת ה-choke "
    "tick הבא `_maybe_enter_seeding` מקדם את ה-state ל-`SEEDING` — כך שטבלת "
    "ההורדות מציגה \"Seeding\" במקום \"Completed\". ה-`_keep_alive_loop` "
    "הורחב לרוץ גם תחת `_is_seeding()`, אחרת חיבורים שמשרתים peers היו "
    "מתנתקים ב-timeout מיד אחרי סיום ההורדה."
)

S1544_PAIN = (
    "**נקודת כאב מתוך הפיתוח.** ה-seed-mode branch וה-`bytes_sent_in_window` "
    "היו קיימים, אך בבדיקה התברר ש-`send_piece` לא נקרא מעולם: הודעת "
    "`REQUEST` הנכנסת נזרקה בשקט (ב-`peer_connection.py` היא סומנה כ\"תטופל "
    "ב-download manager\", אך ה-download manager לא טיפל בה). התוצאה: "
    "`bytes_uploaded` נשאר אפס תמיד, וה-seed-mode מיין כל peer לפי מדד שערכו "
    "אפס — בדיוק ה-degenerate case שהוא נועד למנוע, רק עם מדד אחר. התיקון "
    "היה חיווט הטיפול ב-`REQUEST` אל `_serve_block_request`; רק אז ההעלאה "
    "הפכה אמיתית וה-`bytes_sent_in_window` קיבל ערכים חיוביים."
)

S1544_CODE = (
    "**הקוד.** `peer_connection.py`: `UPLOAD_SAMPLE_RETENTION = 30`, deque "
    "`_upload_samples`, append+eviction ב-`send_piece`, accessor "
    "`bytes_sent_in_window`. `download_manager.py`: `DownloadState.SEEDING`, "
    "predicate `_is_seeding()`, method `_seed_mode_unchoke`, וה-branch ב-"
    "`_tit_for_tat_unchoke`; ובתוספת הגרסה הנוכחית — ה-branch ל-`REQUEST` "
    "ב-`_on_peer_message`, method `_serve_block_request`, helper "
    "`_read_block_sync`, method `_maybe_enter_seeding`, וה-loop-conditions "
    "המורחבים ב-`_choke_loop` וב-`_keep_alive_loop`."
)


# ── §25.5 ────────────────────────────────────────────────────────────────────

S255_NAT = (
    "**חיבורים נכנסים / NAT traversal.** אין `asyncio.start_server` על פורט "
    "6881; אין UPnP או STUN; המערכת רק יוזמת חיבורים יוצאים. העלאת blocks "
    "ל-peers שאליהם כבר נפתח חיבור יוצא **כן** עובדת (ראה §15.4.4), אך אין "
    "קבלת חיבורים נכנסים חדשים — ולכן מאחורי NAT, התרומה ל-swarm מוגבלת "
    "ל-peers שאליהם הלקוח הצליח להתחבר ביוזמתו. ראה §26 → \"שרת listen "
    "נכנס\" + \"NAT Traversal\"."
)


def apply(body, snapshot, W):  # noqa: ARG001  (snapshot unused: search live body)
    # §24 — unit-test count and upload E2E.
    replace_paragraph_text(_find(body, "פונקציות בדיקה המכסות את כל"), S24_COUNT)
    replace_paragraph_text(_find(body, "test_e2e_peer.py"), S24_E2E)

    # §15.4.4 — implementation paragraph, then insert two new paragraphs.
    p_impl = _find(body, "predicate _is_seeding() (שמחזיר True")
    replace_paragraph_text(p_impl, S1544_IMPL)
    # addnext inserts immediately after p_impl; do in reverse so final order
    # is: impl -> upload-path -> visible-state.
    p_impl.addnext(build_paragraph(S1544_STATE))
    p_impl.addnext(build_paragraph(S1544_UPLOAD))

    # §15.4.4 — pain point and code list.
    replace_paragraph_text(_find(body, "נקודת כאב מתוך הפיתוח"), S1544_PAIN)
    replace_paragraph_text(_find(body, "UPLOAD_SAMPLE_RETENTION"), S1544_CODE)

    # §25.5 — NAT bullet wording.
    replace_paragraph_text(_find(body, "חיבורים נכנסים / NAT traversal"), S255_NAT)
