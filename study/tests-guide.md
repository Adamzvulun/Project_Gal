<div dir="rtl">

# מדריך לימוד · הבדיקות (226 בדיקות / 9 קבצים)

מסמך לימוד: מה כל בדיקה עושה, איזה נתיב בקוד היא מפעילה, ולמה היא קיימת. הסדר הוא לפי החשיבות לדיון - בדיקת ה-E2E ראשונה כי היא ה-flagship.

איך מריצים: `python -m pytest python_engine/tests/ -v` מהבסיס של הפרויקט. `-q` לסיכום קצר. `-k <שם>` להפעלת מקבץ ספציפי.

> טיפ למבחן: אם הבוחן שואל "איך אתה יודע שזה עובד?" - לכל טענה יש בדיקה, וכל בדיקה היא ב-`python_engine/tests/test_*.py`. אני יכול להראות את הסקריפט בכל רגע.

---

## ⭐ test_e2e_peer.py · בדיקה אינטגרטיבית · 5 בדיקות

**זאת ה-flagship.** היא לא mock object - היא mock peer אמיתי שעולה על loopback socket ומדבר את הפרוטוקול. הבוחן ביקש בדיוק את זה: end-to-end על socket אמיתי.

| # | שם הבדיקה | מה היא מוכיחה |
|---|---|---|
| 1 | `test_handshake_roundtrip_succeeds` | MockPeer עולה על פורט, ה-`PeerConnection` שלי מתחבר אליו דרך TCP אמיתי, שולח 68 בתי handshake ומקבל 68 בחזרה. מוכיח: framing handshake + readexactly + פענוח peer_id. |
| 2 | `test_handshake_rejects_wrong_info_hash` | MockPeer מחזיר handshake עם info_hash שגוי - ה-PeerConnection חייב לזרוק `PeerConnectionError`. מוכיח: הולידציה ב-handshake היא ערנית, לא קוסמטית. |
| 3 | `test_one_piece_download_via_peer_connection` | זרימה מלאה של piece אחת על socket: BITFIELD → INTERESTED → UNCHOKE → 4 REQUEST של 16KB → 4 PIECE → submit_block × 4 → verify_hash. מוכיח: כל ה-state machine, length-prefix framing, block assembly, ו-SHA-1 verification עובדים end-to-end. |
| 4 | `test_full_download_byte_identical` | הקצה הקיצוני: `Download` שלם מול MockTracker + MockPeer-seeder עם כל ה-pieces. ההורדה רצה לסוף, וקובץ הפלט בדיסק חייב להיות **byte-identical** למקור. מוכיח: tracker → connect → rarest-first → blocks → verify → write כולם עובדים מרוכבים. |
| 5 | `test_seeder_serves_block_to_requesting_peer` | ההפך: *אני* הסיידר, MockPeer מתחבר אליי ושולח REQUEST. אני חייב להחזיר PIECE עם ה-bytes הנכונים בדיוק, ו-`bytes_uploaded` חייב לעלות. מוכיח: נתיב ה-upload (REQUEST → `_serve_block_request` → `send_piece`) עובד באמת, ולא dead code כמו שהיה בגרסה הראשונה. |

**למה זה הסיפור הגדול:** הבוחן אמר במפורש "אין בדיקת end-to-end עם peer". יש - חמש כאלה, כולל אחת שמוכיחה upload אמיתי שזה היה הבאג הכי גדול שלי.

---

## test_bencode.py · 44 בדיקות

הבסיס. **bencode הוא הקלט הראשון מהרשת**, כל באג בו = attack surface. כל הבדיקות פה חיוניות.

| מקבץ | מה הוא מאמת |
|---|---|
| `TestEncodeIntegers` (4) | קידוד שלילי, חיובי, אפס, מספרים גדולים. |
| `TestEncodeStrings` (4) | bytes ריק, bytes רגיל, str שעובר utf-8, יוניקוד רב-בייטי. |
| `TestEncodeLists` (3) | רשימה ריקה, רגילה, וקינון. |
| `TestEncodeDicts` (5) | dict ריק, רגיל, **מיון מפתחות** (canonical), מפתחות מסוג str, וקינון. |
| `TestDecodeIntegers` (6) | פענוח **+ דחיית `i00e`** (leading zero), **דחיית `i-0e`** (negative zero), ו-empty integer. |
| `TestDecodeStrings` (4) | פענוח רגיל + bytes בינארי + **דחיית string חסר** (length גדול מהקלט). |
| `TestDecodeLists` (3) | פענוח ריק, רגיל, מקונן. |
| `TestDecodeDicts` (4) | פענוח + **דחיית מפתחות לא ממוינים**. זה קריטי כי info_hash תלוי בקידוד canonical. |
| `TestRoundTrip` (5) | `decode(encode(x)) == x` לכל הטיפוסים. ההוכחה שאין מידע אובד. |
| `TestDecodePartial` (1) | `decode_partial` מחזיר value + remainder, לפענוח של streams. |
| `TestEdgeCases` (5) | סוגים לא נתמכים, קלט ריק, קלט שאינו bytes, trailing data, prefix לא חוקי. |

**למה זה חשוב לבוחן:** אם info_hash מחושב על dict לא canonical, **הזהות של ה-torrent שונה**. כל ה-handshake נשבר. הבדיקה של "unsorted keys rejected" היא ההוכחה שזה לא יקרה.

---

## test_torrent_metadata.py · 14 בדיקות

מאמת את הפענוח של `.torrent` וחישוב info_hash.

| בדיקה | מה היא מאמתת |
|---|---|
| `test_parse_single_file` | torrent של קובץ יחיד נפענח עם announce, name, size, pieces. |
| **`test_info_hash_computed`** | **SHA-1 על ה-info dict המקודד-מחדש = 20 בתים, מתאים לערך צפוי**. זאת ההוכחה שחישוב info_hash שלי נכון. |
| `test_info_hash_hex` | hexadecimal של info_hash הוא 40 תווים. |
| `test_multi_file_torrent` | torrent עם כמה קבצים: כל ה-path מורכב נכון, ה-offsets מחושבים נכון. |
| `test_get_piece_length_last_piece` | ה-piece האחרון יכול להיות קצר מ-piece_length. |
| `test_get_piece_hash` + `_out_of_range` | חילוץ hash של piece ספציפי, IndexError אם מחוץ לטווח. |
| `test_missing_announce` / `_info` / `_invalid_bencode` / `_file_not_found` / `_no_arguments` | כל הצורות של קלט שבור → `TorrentMetadataError` ייעודי, לא crash שקט. |
| `test_optional_fields` | comment, created_by, creation_date נקראים אם קיימים. |
| `test_repr` | `__repr__` מכיל את שם הקובץ והגודל. |

**הנקודה הקריטית:** `test_info_hash_computed` - אם זאת לא עוברת, כל הפרוטוקול שבור. info_hash הוא הזהות של ה-torrent בכל מקום בקוד.

---

## test_tracker_client.py · 14 בדיקות

תקשורת HTTP מול tracker + פענוח peer list בשני פורמטים.

| מקבץ | מה הוא מאמת |
|---|---|
| `TestPeerId` (3) | peer_id באורך 20 בתים, מתחיל ב-`-PG0001-`, ייחודי בכל קריאה. |
| `TestPeer` (4) | namedtuple-like: equality, hashability (לשימוש ב-set), repr. |
| `TestTrackerResponse` (5) | **compact peer format (6 בתים = 4 IP + 2 port)** + פורמט dict רגיל; failure_reason; warning_message; דחיית compact באורך לא תקין. |
| `TestTrackerClient` (2) | בניית URL ה-announce עם כל הפרמטרים url-encoded; עדכון stats לקראת announce הבא. |

**מה הבוחן ישאל:** "איך אתה מפענח compact peers?" → `_parse_compact_peers` ב-tracker_client.py:104, ויש בדיקה ש-bad length נדחה.

---

## test_peer_connection.py · 39 בדיקות

זה ה-bulk של בדיקות הפרוטוקול. ההכי הרבה בדיקות יחידה אחרי download_manager, כי PeerConnection הוא הקוד הכי קריטי לרשת.

| מקבץ | מה הוא מאמת |
|---|---|
| `TestPeerMessage` (6) | כל סוג הודעה נפענח נכון לשדות (piece_index, block_offset, block_length, block_data, bitfield_data). |
| `TestPeerConnectionInit` (3) | initial state נכון: am_choking=True, am_interested=False, וכו'. has_piece לא קורס באינדקס מחוץ לטווח. |
| `TestBitfieldParsing` (2) | פענוח BITFIELD לרשימת bool. כולל מקרה של partial byte (אם num_pieces לא חלוקה ב-8). |
| **`TestHandshake`** (1) | **handshake הוא בדיוק 68 בתים בפורמט הנכון**: pstrlen + pstr + 8 reserved + 20 info_hash + 20 peer_id. |
| `TestMessageTypes` (2) | values של MessageType enum נכונים (CHOKE=0, UNCHOKE=1, ...). |
| `TestMessageHandling` (7) | כל message type מעדכן state כצפוי: CHOKE → peer_choking=True; HAVE עם אינדקס לא חוקי → דווח כהפרת פרוטוקול; PIECE → bytes_downloaded עולה. |
| **`TestSlidingWindow`** (6) | **חלון נע של 20s להורדה**: empty=0, sums recent, evicts old, doesn't mutate on read, eviction בזמן submit, ה-cumulative counter ממשיך לעבוד נפרד. זאת ההוכחה שתיקון ה-tit-for-tat עובד. |
| **`TestSnubbing`** (6) | **snubbing**: לא מסומן אם הם choking, לא אם לא ביקשתי, מסומן אחרי 60s שקט, מנוקה כשמגיע PIECE, סף מתכוונן, ו-fallback לזמן הconnect מגן על peer טרי. |
| `TestUploadSlidingWindow` (6) | אותו דבר ל-bytes_sent_in_window - חלון העלאה ל-seeding mode. |

**הסיפור פה:** שלושת המקבצים האחרונים (sliding window, snubbing, upload window) הם הוכחה ש-3 המנגנונים שהוספתי ברביזיה (Phase 4a/4b/4c) באמת עובדים.

---

## test_piece_manager.py · 27 בדיקות

ניהול חתיכות + אלגוריתם בחירה.

| מקבץ | מה הוא מאמת |
|---|---|
| `TestBlock` (2) | יצירה ו-repr של בלוק 16KB. |
| `TestPiece` (8) | יצירת piece, חלוקה ל-blocks, last block קטן יותר, submit_block, **verify_hash מצליח** ו**verify_hash נכשל**, reset_piece, get_pending_blocks. |
| `TestPieceManager` (4) | initial state, update_peer_pieces (BITFIELD), update_peer_have (HAVE), remove_peer (cleanup). |
| **`test_select_piece_rarest_first`** | **בוחר piece עם תדירות מינימלית מבין ה-MISSING שה-peer מחזיק**. |
| `test_select_piece_rarest_first_no_candidates` | מחזיר None אם אין pieces מתאימים. |
| `test_select_piece_rarest_first_peer_missing` | לא בוחר pieces שה-peer לא מחזיק. |
| `test_select_piece_random` + `_no_candidates` | אלגוריתם baseline. |
| `test_start_piece` | מסמן IN_PROGRESS ורושם זמן. |
| `test_submit_and_verify` | זרימה מלאה: blocks → piece שלם → verify OK → COMPLETED. |
| `test_submit_bad_hash` | hash שגוי → reset → חזרה ל-MISSING. |
| `test_get_status_list` / `_our_bitfield` / `_has_piece` / `_progress_after_completion` | accessors. |
| `test_frequency_multiple_peers` | counter עולה ויורד נכון עם כמה peers. |

**מה הבוחן ירצה לראות:** `test_select_piece_rarest_first` עם הקוד שלצידו. מקבץ הוכחות לאלגוריתם הראשי.

---

## test_security.py · 26 בדיקות

מערכת המוניטין והוולידציה.

| מקבץ | מה הוא מאמת |
|---|---|
| `TestPeerReputation` (5) | reputation מתחיל מאפס, sho_ban אחרי 3 hash failures, sho_ban אחרי 5 protocol violations, trust_score של peer טוב/רע. |
| `TestSecurityManager.test_verify_piece_success/_failure` | **SHA-1 חישוב והשוואה**. שתי הבדיקות הקריטיות שמחזיקות את "trust במערכת". |
| `test_report_hash_failure` + `_ban_after_hash_failures` | אחרי 3 כשלים → ban אוטומטי. |
| `test_report_protocol_violation` + `_ban_after_protocol_violations` | אחרי 5 הפרות → ban. |
| `test_report_successful_piece` | מונה הצלחות עולה (משפיע על trust_score). |
| `test_validate_message_length_*` (3) | אורך תקין, שלילי (זרוק), גדול מ-2MB (זרוק). |
| `test_validate_piece_index_*` (3) | piece_index בטווח, שלילי, מעל num_pieces. |
| `test_get_banned_peers` / `_recent_events` / `_events_for_peer` | accessors היסטוריים. |
| `test_report_timeout` / `_invalid_message` | סוגי אירועים נוספים. |
| `test_event_callback` | callback registration עובד (לעדכון GUI בעתיד). |
| `TestSecurityEvent` (2) | יצירת event ו-repr. |

**הנקודה:** `verify_piece` עצמו הוא 2 שורות (`hashlib.sha1(data).digest() == expected`), אבל הבדיקות מוכיחות שכל ההגנות *סביבו* עובדות.

---

## test_download_manager.py · 44 בדיקות

הקובץ הגדול ביותר. מכיל את כל הבדיקות של הרכיב המרכזי + כל ההוספות מהרביזיה.

| מקבץ | מה הוא מאמת |
|---|---|
| `TestDownloadStats` (2) | חישוב מהירות ממוצעת. |
| `TestDownload` (4) | יצירת download, איך נשמרים האלגוריתמים, get_status, peer_id נוצר. |
| `TestDownloadManager` (5) | add_torrent, get_all_status, get_download_status, get_nonexistent (None), multiple downloads. |
| `TestAlgorithmType` + `TestDownloadState` | enum values נכונים. |
| **`TestLoadState`** (6) | **שחזור מצב**: round-trip, COMPLETED נשמר במצבו, JSON שבור → None, sidecar חסר → None, bytes על דיסק שונים מהציפייה → marks missing, info_hash mismatch → None. כל מקרי הקצה של resume. |
| **`TestManagerRestoreState`** (5) | סריקת תיקייה: ריק → 0, קבצים שבורים → דילוג, **הורדות שהסתיימו → דילוג**, **הורדות שבוטלו → דילוג**. תיקון Phase 7. |
| `TestManagerRemoveDownload` (2) | DELETE מסיר state אבל לא את הקובץ; remove על id לא קיים → False. |
| **`TestTitForTatSlidingWindow`** (2) | peer ששתק demoted בעדיפות peer פעיל; מפתח המיון הוא ה-window, לא ה-cumulative. **תיקון Phase 4a.** |
| **`TestSnubbingPartition`** (4) | snubbed peer demoted כשיש אלטרנטיבות, נשמר כשהוא הברירה היחידה, optimistic מעדיף non-snubbed, logging פעם אחת לאפיזודה. **תיקון Phase 4b.** |
| **`TestSeedingMode`** (3) | `_is_seeding` דורש completion + terminal state; seeding ממיין לפי upload window; leech mode לא משתנה כשלא complete. **תיקון Phase 4c.** |
| **`TestUploadServing`** (6) | מגיש block נכון ו-counter עולה; partial offset; choking peer לא משורת; request לpiece שאין לנו מתעלם; oversized rejected; out of bounds rejected. **תיקון Phase 6 - האג של ה-upload האמיתי.** |
| **`TestSeedingTransition`** (3) | COMPLETED → SEEDING ב-`_maybe_enter_seeding`; no-op בזמן RUNNING; no-op כשלא complete. |

**הסיפור:** רבע מהבדיקות פה תיעדו ישירות באגים שתפסתי ותיקנתי. כל אחת מהן היא ראיה ל-Phase ספציפי מ-CHANGELOG.

---

## test_api_server.py · 13 בדיקות

ה-Flask REST API. בדיקות אלה לא מפעילות את ה-engine האמיתי - הן בודקות את שכבת ה-HTTP.

| מקבץ | מה הוא מאמת |
|---|---|
| `test_health` | `GET /health` → 200 + status:ok. |
| `test_get_all_empty` | `GET /torrents` כשאין הורדות → רשימה ריקה. |
| `test_get_nonexistent_torrent` | `GET /torrents/<id>` כשלא קיים → 404. |
| `test_start_no_file` | `POST /torrents` בלי קובץ → 400. |
| `test_pause/resume/cancel_nonexistent` | פעולות על id לא קיים → 404. |
| `test_get_history` / `_events` / `_events_with_limit` / `_with_torrent_id` | endpoints היסטוריים עם פילטרים. |
| `test_get_algorithm_stats` | `/algorithm-stats/<id>` מחזיר מבנה תקין. |
| `test_init_creates_tables` | DB schema (torrents, events, performance_stats, algorithm_stats) נוצר ב-init. |

**הערה:** ה-API נבדק בעיקר כקופסה שחורה ברמת ה-HTTP. הבדיקות העמוקות של ה-engine עצמו הן ב-test_download_manager.

---

## איך לדבר על הבדיקות במבחן

1. **"איך אתה יודע שזה עובד?"** → `python -m pytest python_engine/tests/ -v` → 226 עוברות. אם יש זמן, מריץ חי במחשב.
2. **"איפה ה-end-to-end?"** → `test_e2e_peer.py`. mock peer אמיתי על socket. 5 בדיקות - מההanדeshake הבסיסי ועד `test_full_download_byte_identical`.
3. **"איפה ההוכחה ש-X עובד?"** → לכל feature יש בדיקה ספציפית. רביזיות Phase 4a/4b/4c/6/7 מסומנות במפורש ב-`test_download_manager.py` בכותרות של מקבצים.
4. **"בדיקות אינטגרציה אמיתיות?"** → test_e2e_peer יוצרת `asyncio.start_server` על loopback, מדברת BEP-3 בפועל. זה לא Mock - זה real socket.
5. **"חולשות בבדיקות?"** → אין בדיקות עומס/ביצועים, אין fuzzing על ה-parser של bencode, אין בדיקות נגד התקפות (Sybil, Eclipse). מתועדים כפיתוח עתידי.

</div>
