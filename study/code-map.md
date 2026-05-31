<div dir="rtl">

# 🗺️ Code Map · מפת הקוד המאוחדת

> **המטרה:** קובץ אחד שאני פותח ב-VSCode במהלך הבחינה.
> כל פונקציה, כל קבוע, כל snippet קריטי — file\:line + הסבר בשורה.
> מסודר לפי **קריטיות** (⭐⭐⭐ = הבוחן בטוח ישאל).

---

## 📑 תוכן עניינים

1. [טבלת חיפוש מהיר — שאלה → קוד](#-1-טבלת-חיפוש-מהיר--שאלה--codeline)
2. [מפת הקבצים](#-2-מפת-הקבצים-במבט-על)
3. [Python Engine — כל פונקציה](#-3-python-engine--מפת-פונקציות-מלאה)
4. [Java GUI — כל פונקציה](#-4-java-gui--מפת-פונקציות)
5. [קבועים קריטיים — Cheat Sheet](#-5-קבועים-קריטיים--cheat-sheet)
6. [Snippets חובה — מקוצרים](#-6-snippets-חובה--מקוצרים)
7. [Data Flow — זרימות עיקריות](#-7-data-flow--זרימות-מרכזיות)
8. [מילון מונחים](#-8-מילון-מונחים--הגייה)
9. [תיקונים שעשיתי (Phases)](#-9-תיקונים-שעשיתי--ציר-זמן-של-phases)

---

## 🔍 1. טבלת חיפוש מהיר — שאלה → code\:line

| הבוחן שואל... | אני קופץ ל... | מה להגיד בשורה |
|---|---|---|
| "תראה לי handshake" | `peer_connection.py:207` `_send_handshake` | 68 בתים: 1+19+8+20+20 |
| "איך מאמתים handshake?" | `peer_connection.py:219` `_receive_handshake` | בודק pstrlen=19, info_hash תואם |
| "איך rarest-first?" | `piece_manager.py:279` `select_piece_rarest_first` | min freq + `random.choice` על tie set |
| "איך random selection?" | `piece_manager.py:319` `select_piece_random` | baseline להשוואה |
| "איך tit-for-tat?" | `download_manager.py:610` `_tit_for_tat_unchoke` | 5 שלבים, window 20s, top-4 |
| "Optimistic Unchoke?" | `download_manager.py:~687` בתוך tit-for-tat | `random.choice(non_snubbed_remaining)` |
| "Seeding mode?" | `download_manager.py:706` `_seed_mode_unchoke` | ממיין לפי upload rate, לא download |
| "Snubbing?" | `peer_connection.py:592` `is_snubbed` | unchoked + 60s שקט |
| "Sliding window?" | `peer_connection.py:552` `bytes_received_in_window` | deque של (t,bytes), sum מ-cutoff |
| "SHA-1 verification?" | `security.py:96` `verify_piece` + `piece_manager.py:395` | 2 שורות, hashlib.sha1 |
| "Hash failure → ban?" | `security.py:109` `report_hash_failure` | >=3 → `_ban_peer` |
| "info_hash computation" | `torrent_metadata.py:~100` בתוך `_parse_metadata` | re-encode info dict → SHA-1 |
| "Length-prefix framing?" | `peer_connection.py:271` `_read_message` | `readexactly(4)` → uint32 → readexactly(len) |
| "DoS protection?" | `peer_connection.py:~282` | `MAX_MESSAGE_SIZE = 2MB` cap |
| "Upload path?" | `download_manager.py:432` `_serve_block_request` | 4 ולידציות → executor → send_piece |
| "PIECE handler?" | `download_manager.py:~374` בתוך `_on_peer_message` | submit_block → SHA-1 → write → broadcast HAVE |
| "REQUEST handler?" | `download_manager.py:432` `_serve_block_request` | אותו דבר, upload side |
| "Flask ↔ asyncio?" | `api_server.py:61` `_run_async` | `run_coroutine_threadsafe` |
| "איפה ה-event loop?" | `api_server.py:44` `_start_event_loop` | daemon thread עם new_event_loop |
| "Compact peers parsing?" | `tracker_client.py:104` `_parse_compact_peers` | 6 בתים: 4 IP + 2 port (big-endian) |
| "Bencode dict canonical?" | `bencode.py:110` `_encode_dict` | sorted keys (UTF-8) |
| "Bencode int validation?" | `bencode.py:146` `_decode_int` | אין leading zero, אין -0 |
| "Choke loop?" | `download_manager.py:590` `_choke_loop` | כל 10s טריגר tit-for-tat |
| "Keep-alive?" | `download_manager.py:770` `_keep_alive_loop` | כל 60s |
| "Disk write async?" | `download_manager.py:804` `_write_piece_sync` | רץ ב-ThreadPoolExecutor(2) |
| "Endgame mode?" | `piece_manager.py:450` `find_in_progress_piece` | request חופף בסוף ההורדה |
| "Persistence?" | `download_manager.py:966` `_save_state` + `:1014` `from_state_file` | JSON ב-`data/state/` |
| "Tracker announce URL?" | `tracker_client.py:251` `_build_announce_url` | URL-encode info_hash + peer_id |
| "ה-GUI polling?" | `TorrentClientGUI.java` ScheduledExecutorService | כל 500ms `/torrents` |
| "התראת COMPLETED?" | `TorrentClientGUI.java` `previousStates` map | מעבר state → popup |

---

## 📂 2. מפת הקבצים במבט-על

### Python Engine — `python_engine/`

| קובץ | שורות | תפקיד | קריטיות |
|---|---|---|---|
| `download_manager.py` | 1,311 | המתאם המרכזי — כל החלטה עוברת פה | ⭐⭐⭐ |
| `peer_connection.py` | 620 | TCP + BEP-3 wire protocol | ⭐⭐⭐ |
| `api_server.py` | 530 | Flask REST + גשר asyncio + SQLite | ⭐⭐ |
| `piece_manager.py` | 473 | מעקב pieces + rarest-first | ⭐⭐⭐ |
| `tracker_client.py` | 337 | HTTP tracker + parsing peers | ⭐⭐ |
| `security.py` | 326 | מוניטין + SHA-1 + ban logic | ⭐⭐ |
| `torrent_metadata.py` | 241 | פענוח .torrent + info_hash | ⭐⭐ |
| `bencode.py` | 231 | קידוד/פענוח canonical | ⭐⭐ |
| `main.py` | 190 | CLI entry | ⭐ |
| `__main__.py` | 4 | `python -m python_engine` | ⭐ |

**סה"כ Python:** ~4,260 שורות

### Java GUI — `java_gui/src/`

| קובץ | תפקיד |
|---|---|
| `TorrentClientGUI.java` | חלון ראשי, JTable, toolbar, polling 500ms |
| `ApiService.java` | HTTP client → Python API |
| `AlgorithmStatsDialog.java` | חלון Algorithm Stats + bar chart Java2D |

---

## 🐍 3. Python Engine — מפת פונקציות מלאה

### `bencode.py` (231) — Serialization

| Line | Symbol | תפקיד |
|---|---|---|
| 15 | `class BencodeDecodeError` | exception לפענוח |
| 20 | `class BencodeEncodeError` | exception לקידוד |
| **25** | **`encode(data)`** | API ראשי — int/bytes/str/list/dict → bytes |
| **51** | **`decode(data)`** | API ראשי — bytes → Python obj |
| 74 | `decode_partial(data)` | מחזיר (value, remaining) לזרמים |
| 94 | `_encode_int` | `i42e` |
| 98 | `_encode_bytes` | `5:hello` |
| 102 | `_encode_list` | `l...e` |
| **110** | **`_encode_dict`** | `d...e` עם **sorted keys** (canonical) |
| 128 | `_decode_next` | dispatch לפי first byte |
| **146** | **`_decode_int`** | `i...e` + **דחיית leading zero ו--0** |
| 172 | `_decode_bytes` | `len:data` |
| 195 | `_decode_list` | רקורסיבי |
| **210** | **`_decode_dict`** | בודק **שמפתחות ממוינים** (אחרת error) |

**Validations חיוניות:** sorted keys / no leading zeros / no -0 / strict length.

---

### `torrent_metadata.py` (241) — .torrent parsing

| Line | Symbol | תפקיד |
|---|---|---|
| 15 | `TorrentMetadataError` | exception |
| 20 | `class FileInfo(path, size)` | קובץ במולטי-file |
| **31** | **`class TorrentMetadata`** | מחלקה ראשית |
| 49 | `__init__(torrent_path=, torrent_data=)` | טוען מ-path או מ-bytes |
| **79** | **`_parse_metadata()`** | bencode.decode → שולף שדות → **מחשב info_hash** |
| 155 | `info_hash_hex()` | להצגה |
| 159 | `info_hash_urlencoded()` | ל-tracker GET |
| 164 | `get_piece_hash(idx)` | 20 בתים מ-pieces |
| **180** | **`get_piece_length(idx)`** | ה-piece האחרון יכול להיות קצר |
| 199 | `get_file_offset(piece_idx)` | למולטי-file: `[(path, offset, length)]` |

**שדות מרכזיים:** `announce`, `announce_list`, `piece_length`, `pieces`, `info_hash`, `files`, `total_size`, `num_pieces`.

**ה-snippet הקריטי (בתוך `_parse_metadata`):**
```python
info_encoded = bencode.encode(info)        # re-encode canonical
self.info_hash = hashlib.sha1(info_encoded).digest()  # 20 bytes
```

---

### `tracker_client.py` (337) — Tracker HTTP

| Line | Symbol | תפקיד |
|---|---|---|
| **27** | **`generate_peer_id()`** | `b'-PG0001-' + 12 random` |
| 36 | `class Peer(ip, port, peer_id?)` | dataclass + `__hash__` ל-set |
| **56** | **`class TrackerResponse`** | parse של תשובת tracker |
| 71 | `_parse(data)` | dispatch compact / regular |
| **104** | **`_parse_compact_peers(data)`** | 6 בתים: 4 IP + 2 port `!H` |
| 121 | `_parse_regular_peers(data)` | dict format (פחות נפוץ) |
| **135** | **`class TrackerClient`** | מחלקה ראשית |
| 142 | `__init__(announce_url, info_hash, peer_id, port=6881)` | |
| 169 | `_get_session()` | aiohttp session lazy |
| **175** | **`announce(event=)`** | HTTP GET → TrackerResponse |
| **251** | **`_build_announce_url(params)`** | URL-encode info_hash + peer_id |
| 269 | `start_periodic_announce(callback)` | background task |
| 281 | `_periodic_announce_loop(callback)` | sleep(interval) loop |
| 305 | `stop()` | event=stopped |
| 324 | `completed()` | event=completed |
| 328 | `update_stats(up, down, left)` | לפני announce הבא |

**קבוע חשוב:** `PEER_ID_PREFIX = b'-PG0001-'`

---

### `peer_connection.py` (620) ⭐⭐⭐ — Peer Wire Protocol

| Line | Symbol | תפקיד |
|---|---|---|
| 43 | `class MessageType(IntEnum)` | CHOKE=0, UNCHOKE=1, INTERESTED=2, ... PIECE=7, CANCEL=8, KEEP_ALIVE=-1 |
| 57 | `class PeerMessage` | wrapper + parsed properties |
| 66 | `piece_index` property | unpack מ-payload |
| 75 | `block_offset` | |
| 84 | `block_length` | |
| 91 | `block_data` | payload[8:] |
| 98 | `bitfield_data` | |
| 108 | `PeerConnectionError` | exception |
| **113** | **`class PeerConnection`** | חיבור TCP יחיד |
| 125 | `__init__(ip, port, info_hash, peer_id, num_pieces, on_message)` | state init |
| 184 | `connected` property | bool |
| 187 | `connect()` | TCP + handshake |
| **207** | **`_send_handshake()`** ⭐ | 68 בתים |
| **219** | **`_receive_handshake()`** ⭐ | ולידציות (pstrlen, info_hash match) |
| 249 | `start_message_loop()` | יוצר asyncio task |
| 253 | `_message_loop()` | infinite read → handle |
| **271** | **`_read_message()`** ⭐ | length-prefix framing + DoS cap |
| **314** | **`_handle_message(msg)`** ⭐ | switch לפי type → updates state → on_message callback |
| 375 | `_parse_bitfield(data)` | bits → List[bool] |
| 386 | `send_message(type, payload)` | length prefix + write + drain |
| 409 | `send_interested()` | |
| 414 | `send_not_interested()` | |
| 419 | `send_choke()` | |
| 424 | `send_unchoke()` | |
| 429 | `send_have(piece_idx)` | |
| 434 | `send_bitfield(pieces)` | |
| 447 | `send_request(idx, begin, length)` | |
| **468** | **`send_piece(idx, begin, data)`** ⭐ | upload! |
| 488 | `send_cancel(idx, begin, length)` | endgame |
| 493 | `send_keep_alive()` | length=0 |
| 497 | `disconnect()` | close writer |
| 519 | `can_request` property | pending < MAX_PENDING |
| 536 | `request_capacity` | כמה עוד אפשר |
| 540 | `has_piece(idx)` | peer_pieces[idx] |
| 546 | `time_since_last_activity()` | |
| **552** | **`bytes_received_in_window(20)`** ⭐ | sum deque מ-cutoff |
| 572 | `bytes_sent_in_window(20)` | למוד seeding |
| **592** | **`is_snubbed(60)`** ⭐ | unchoked + 60s שקט |

**State המרכזי של PeerConnection:**
- `am_choking`, `am_interested` — מה אני עושה ל-peer
- `peer_choking`, `peer_interested` — מה הוא עושה לי
- `peer_pieces: List[bool]` — bitfield שלו
- `_download_samples: deque[(t, bytes)]` — לחלון נע

---

### `piece_manager.py` (473) ⭐⭐⭐ — Pieces + Algorithm

| Line | Symbol | תפקיד |
|---|---|---|
| 19 | `class PieceStatus(Enum)` | MISSING / IN_PROGRESS / COMPLETED |
| **26** | **`class Block(piece_index, offset, length)`** | block 16KB |
| 42 | `is_requestable` | bool — לא נמצא בבקשה כרגע |
| 51 | `mark_requested(peer_key)` | |
| 57 | `clear_request()` | |
| **67** | **`class Piece(index, length, expected_hash)`** | piece ~256KB = 16 blocks |
| 88 | `num_blocks` | length / BLOCK_SIZE עם ceil |
| 92 | `is_complete` | כל blocks הגיעו |
| **95** | **`submit_block(offset, data) → bool`** | True אם piece שלם |
| **114** | **`verify_hash() → bool`** | SHA-1(data) == expected |
| 120 | `data` property | concat blocks |
| 124 | `get_pending_blocks()` | לא הגיעו עדיין |
| 128 | `get_requestable_blocks()` | פנויים לבקשה |
| 132 | `clear_peer_requests(peer_key)` | על disconnect/choke |
| 138 | `reset()` | חזרה ל-MISSING (אחרי hash fail) |
| **148** | **`class PieceManager`** | מנהל הכל |
| 155 | `__init__(num_pieces, piece_length, total_size, piece_hashes)` | |
| 194 | `completed_pieces` | count |
| 199 | `bytes_downloaded` | מכפילה ע"י lengths |
| 204 | `bytes_remaining` | |
| 209 | `progress` | float 0..1 |
| 216 | `is_complete` | bool |
| **220** | **`update_peer_pieces(peer_key, pieces)`** | על BITFIELD — מעדכן _peer_frequency |
| **246** | **`update_peer_have(peer_key, piece_idx)`** | על HAVE — increment frequency |
| 265 | `remove_peer(peer_key)` | decrement frequencies |
| **279** | **`select_piece_rarest_first(peer_pieces)`** ⭐⭐⭐ | min freq + random.choice על tie |
| 319 | `select_piece_random(peer_pieces)` | baseline |
| **343** | **`start_piece(idx) → List[Block]`** | סימון IN_PROGRESS |
| 357 | `reset_stale_pieces(timeout)` | pieces תקועים → MISSING |
| **377** | **`submit_block(piece_idx, offset, data)`** | delegate ל-piece |
| **395** | **`verify_piece(piece_idx)`** | wrapper לhash check |
| 414 | `get_piece_data(piece_idx)` | לupload |
| 428 | `get_status_list()` | לAPI |
| 432 | `get_frequency(piece_idx)` | לAlgorithm Stats |
| 436 | `has_piece(piece_idx)` | |
| 440 | `clear_peer_requests(peer_key)` | |
| **450** | **`find_in_progress_piece(...)`** | endgame mode |
| 471 | `get_our_bitfield()` | |

**מבני נתונים פנימיים (חשוב לזכור!):**
```python
self._peer_frequency: Dict[int, int]    # piece i → כמה peers מחזיקים
self._peer_pieces: Dict[str, Set[int]]   # peer → set של pieces שלו
self._piece_start_times: Dict[int, float] # לtimeout של stale
self.rarest_selections: Dict[int, int]   # statistics לחלון GUI
self._lock = threading.Lock()            # thread-safety
```

---

### `download_manager.py` (1,311) ⭐⭐⭐ — Coordinator

| Line | Symbol | תפקיד |
|---|---|---|
| 42 | `class DownloadState(Enum)` | QUEUED, RUNNING, PAUSED, COMPLETED, SEEDING, CANCELLED, ERROR |
| 58 | `class AlgorithmType(Enum)` | RAREST_FIRST, RANDOM, TIT_FOR_TAT, ROUND_ROBIN |
| 66 | `class DownloadStats` | bytes_downloaded/uploaded, speeds, peer counts |
| **98** | **`class Download`** | מחלקה ראשית — הורדה יחידה |
| 105 | `__init__(torrent, download_dir, state_dir, piece_algo, peer_algo)` | |
| 166 | `_log(message)` | logging פנימי + seq_no |
| 177 | `get_logs(since_seq=0)` | לpolling מהGUI |
| 182 | `progress` | |
| 186 | `file_name` | |
| 190 | `file_size` | |
| 194 | `connected_peers` | |
| 197-203 | callbacks: on_progress / on_complete / on_state_change | |
| **206** | **`start()`** | יוצר tasks + announce |
| **219** | **`_download_loop()`** | הראשי: tracker → connect → request |
| 288 | `_cleanup_dead_peers()` | מסיר disconnected |
| 301 | `_connect_to_peers()` | concurrent gather |
| 320 | `_connect_peer(peer)` | TCP + handshake + start_message_loop |
| **349** | **`_on_peer_message(conn, message)`** ⭐⭐⭐ | switch: BITFIELD/HAVE/UNCHOKE/CHOKE/PIECE/REQUEST |
| **374** (בתוך) | **PIECE branch** | submit_block → SHA-1 (executor) → write → broadcast HAVE |
| **432** | **`_serve_block_request(conn, msg)`** ⭐ | upload path |
| 472 | `_peer_has_needed_pieces(conn)` | אם יש מה לרצות |
| 479 | `_request_pieces()` | לולאה על peers |
| **491** | **`_request_from_peer(peer_key, conn)`** | אסטרטגיית request לpeer יחיד |
| 547 | `_send_block_requests(conn, peer_key, ...)` | batch של REQUEST |
| 565 | `_is_seeding()` | bool |
| 578 | `_maybe_enter_seeding()` | COMPLETED → SEEDING |
| **590** | **`_choke_loop()`** | כל 10s → tit-for-tat |
| **610** | **`_tit_for_tat_unchoke()`** ⭐⭐⭐ | 5 שלבים, top-4, Optimistic |
| ~687 | (בתוך) Optimistic Unchoke | `random.choice(non_snubbed_remaining)` |
| **706** | **`_seed_mode_unchoke(interested)`** | ממיין לפי **upload** rate |
| 747 | `_round_robin_unchoke()` | אלגוריתם חלופי |
| **770** | **`_keep_alive_loop()`** | כל 60s |
| 785 | `_broadcast_have(piece_idx)` | concurrent send לכולם |
| 797 | `_safe_send_have(conn, idx)` | wrapper try/except |
| **804** | **`_write_piece_sync(piece_idx)`** | disk write — רץ ב-executor |
| 837 | `_write_piece(piece_idx)` | async wrapper |
| 842 | `_read_block_sync(piece_idx, begin, length)` | לupload — executor |
| 858 | `_complete_download()` | על סיום |
| 885 | `_on_tracker_response(response)` | מוסיף peers חדשים |
| 894 | `_update_speed()` | חישוב KB/s |
| 917 | `pause()` | state → PAUSED, ביטול tasks |
| 936 | `resume()` | החזרה ל-RUNNING |
| 946 | `cancel()` | event=stopped + ניקוי |
| **966** | **`_save_state()`** | JSON ל-`data/state/<id>.json` |
| **1014** | **`from_state_file(cls, file)`** | restore על startup |
| 1137 | `get_status() → dict` | לAPI |
| **1157** | **`class DownloadManager`** | מנהל את כל ה-Downloads |
| 1163 | `__init__(download_dir, state_dir, ...)` | |
| **1172** | **`add_torrent(torrent, ...)`** | creates Download instance |
| 1200 | `start_download(id)` | |
| 1205 | `pause_download(id)` | |
| 1210 | `resume_download(id)` | |
| 1215 | `cancel_download(id)` | |
| 1220 | `remove_download(id)` | gentle remove |
| 1246 | `_delete_state_files(id)` | |
| 1260 | `get_all_status() → List[dict]` | |
| 1264 | `get_download_status(id)` | |
| 1270 | `get_download(id)` | |
| **1274** | **`restore_state()`** | סריקת `data/state/*.json` |

**Loops (asyncio tasks שרצים במקביל):**
1. `_download_loop` — הראשי
2. `_choke_loop` — כל 10s
3. `_keep_alive_loop` — כל 60s
4. `_periodic_announce_loop` (ב-tracker_client) — לפי interval
5. `_message_loop` per peer (ב-PeerConnection)

**Subsystems:**
- `piece_manager: PieceManager` — pieces tracking
- `security: SecurityManager` — מוניטין
- `tracker: TrackerClient` — HTTP tracker
- `_executor: ThreadPoolExecutor(2)` — לhash + disk

---

### `security.py` (326) — Reputation + Validation

| Line | Symbol | תפקיד |
|---|---|---|
| 24 | `class SecurityEvent` | event לוג |
| **42** | **`class PeerReputation`** | dataclass per peer |
| 58 | `should_ban` property | hash>=3 OR violations>=5 |
| 66 | `trust_score` | 0..1 לפי success vs failures |
| **79** | **`class SecurityManager`** | המנהל המרכזי |
| 90 | `__init__()` | dicts ריקים |
| **96** | **`verify_piece(data, expected_hash)`** ⭐ | hashlib.sha1 == |
| **109** | **`report_hash_failure(peer_key, piece_idx)`** | >=3 → ban |
| 131 | `report_successful_piece(peer_key, idx)` | |
| 136 | `report_protocol_violation(peer_key, desc)` | >=5 → ban |
| 158 | `report_invalid_message(peer_key, desc)` | |
| 169 | `report_timeout(peer_key)` | |
| **181** | **`validate_message_length(peer_key, length)`** | <0 או >2MB → false |
| 202 | `validate_piece_index(peer_key, idx, num_pieces)` | בגבולות? |
| 213 | `is_peer_banned(peer_key)` | |
| 217 | `get_peer_reputation(peer_key)` | |
| 221 | `get_banned_peers()` | |
| 225 | `get_recent_events(limit=100)` | |
| 229 | `get_events_for_peer(peer_key)` | |
| 233 | `on_event(callback)` | |
| 237 | `_get_reputation(peer_key)` | get-or-create |
| 242 | `_ban_peer(peer_key, reason)` | |
| 257 | `_log_event(event)` | append + callback |

**קבועים:**
```python
MAX_HASH_FAILURES_PER_PEER = 3
MAX_PROTOCOL_VIOLATIONS_PER_PEER = 5
MAX_MESSAGE_LENGTH = 2 * 1024 * 1024  # 2MB
```

---

### `api_server.py` (530) ⭐⭐ — REST + Bridge

| Line | Symbol | תפקיד |
|---|---|---|
| **44** | **`_start_event_loop()`** | יוצר new_event_loop ב-daemon thread |
| 52 | `_run_loop()` (nested) | run_forever |
| **61** | **`_run_async(coro, timeout=60)`** ⭐ | `run_coroutine_threadsafe` |
| 77 | `get_manager() → DownloadManager` | singleton |
| **93** | **`init_database()`** | יוצר 4 tables ב-SQLite |
| 165 | `save_torrent_to_db(download)` | |
| 223 | `log_event_to_db(id, type, desc)` | |
| **239** | **`POST /torrents`** `start_download` | multipart upload + algorithms |
| 278 | `create_and_start()` (nested coro) | |
| 289 | `on_download_complete(dl)` (callback) | |
| 314 | `GET /torrents` `get_all_status` | |
| 322 | `GET /torrents/<id>` `get_torrent_status` | |
| 332 | `POST /torrents/<id>/pause` | |
| 348 | `POST /torrents/<id>/resume` | |
| 363 | `POST /torrents/<id>/cancel` | |
| 379 | `DELETE /torrents/<id>` | gentle (לא מוחק קובץ) |
| **399** | **`GET /history`** | מ-SQLite |
| 417 | `DELETE /history` | |
| 433 | `GET /events` | security events |
| 458 | `GET /algorithm-stats/<id>` | לחלון GUI |
| 473 | `GET /stats-summary` | aggregates |
| **495** | **`GET /torrents/<id>/logs?since=N`** | polling incremental מהGUI |
| 508 | `GET /health` | |
| 513 | `create_app()` | factory |
| 520 | `run_server(host, port, debug)` | entry point |

**Globals (חיוניים להבין!):**
```python
_loop: asyncio.AbstractEventLoop  # רץ ב-daemon thread
_loop_thread: threading.Thread
_manager: DownloadManager         # singleton
```

**SQLite (`data/history.db`):**
- `torrents` — completed downloads
- `performance_stats` — מהירויות
- `algorithm_stats` — rarest selections
- `events` — security log

---

### `main.py` (190) — CLI Entry

```bash
python -m python_engine path/to/file.torrent -o ./downloads \
  --piece-algorithm rarest_first --peer-algorithm tit_for_tat -v
```

- `argparse` + progress bar בreal-time
- `signal.SIGINT` handler לCtrl+C נקי
- שימוש ישיר ב-`DownloadManager` (לא דרך API)

---

## ☕ 4. Java GUI — מפת פונקציות

### `TorrentClientGUI.java` (~900) — Main Window

| תפקיד | מתודה / משתנה |
|---|---|
| חלון ראשי | `class TorrentClientGUI extends JFrame` |
| Polling | `ScheduledExecutorService.scheduleAtFixedRate(... 500ms)` |
| Log polling | `logSeqTracker: Map<String, Integer>` |
| מעבר COMPLETED | `previousStates: Map<String, String>` → popup |
| Toolbar | Add / Pause / Resume / Cancel / Delete / History / Algorithm Stats |
| Algorithm dropdown | בחירת `rarest_first`/`random` + `tit_for_tat`/`round_robin` |
| Download dir picker | `JFileChooser` |

### `ApiService.java` (~430) — HTTP Client

| Line | Method | תפקיד |
|---|---|---|
| 45 | `TorrentStatus.fromJson(json)` | factory מJSON |
| 98 | `startDownload(File)` | overload פשוט |
| **113** | **`startDownload(File, pieceAlgo, peerAlgo, downloadDir)`** | multipart POST |
| 176 | `getStatus() → List<TorrentStatus>` | |
| 201 | `getStatus(id) → TorrentStatus` | |
| 220 | `pause(id)` | |
| 237 | `resume(id)` | |
| 254 | `cancel(id)` | |
| 275 | `delete(id)` | |
| 292 | `getHistory()` | |
| 309 | `clearHistory()` | |
| 326 | `getAlgorithmStats(id)` | לbar chart |
| 343 | `getStatsSummary()` | |
| 361 | `getEvents(limit)` | |
| **381** | **`getLogs(id, sinceSeq)`** | incremental polling |
| 399 | `isServerAvailable()` | |
| 417 | `sendRequest(req)` | helper |
| 426 | `checkResponse(resp, expected)` | helper |

**Inner class `TorrentStatus`:** id, filename, state, progress, speed, peers, etc.

### `AlgorithmStatsDialog.java` (~400) — Stats Window

- 2 tabs: Piece Selection (bar chart) + General Statistics
- **Bar chart ב-Java2D ידני** — לא ספרייה (חשוב לציין!)
- Fetches `/algorithm-stats/<id>` כל פתיחה

---

## ⚙️ 5. קבועים קריטיים — Cheat Sheet

### `peer_connection.py`
```python
PROTOCOL_STRING = b"BitTorrent protocol"   # 19 bytes
PROTOCOL_STRING_LEN = 19
HANDSHAKE_LEN = 68                          # 1+19+8+20+20
BLOCK_SIZE = 16384                          # 16 KB - block standard
MAX_PENDING_REQUESTS = 50                   # pipeline depth
MAX_MESSAGE_SIZE = 2 * 1024 * 1024          # 2 MB - DoS cap
SNUB_THRESHOLD = 60.0                       # seconds
REQUEST_TIMEOUT = 30
KEEP_ALIVE_INTERVAL = 60
DOWNLOAD_SAMPLE_RETENTION = 30              # seconds in deque
```

### `download_manager.py`
```python
CHOKE_INTERVAL = 10                         # tit-for-tat round
MAX_UNCHOKED_PEERS = 4                      # top-K
MAX_CONNECTIONS = 50
KEEP_ALIVE_INTERVAL = 60
PIECE_REQUEST_TIMEOUT = 30
TIT_FOR_TAT_WINDOW = 20.0                   # sliding window
```

### `security.py`
```python
MAX_HASH_FAILURES_PER_PEER = 3              # → ban
MAX_PROTOCOL_VIOLATIONS_PER_PEER = 5        # → ban
MAX_MESSAGE_LENGTH = 2 * 1024 * 1024
```

### `tracker_client.py`
```python
PEER_ID_PREFIX = b'-PG0001-'                # client identifier
DEFAULT_PORT = 6881
```

### `piece_manager.py`
```python
# בדרך כלל piece = 256 KB = 16 blocks of 16 KB
# (מגיע מ-.torrent, לא קבוע במערכת)
```

---

## 📝 6. Snippets חובה — מקוצרים

### 🔴 #1 Handshake (`peer_connection.py:207`)
```python
handshake = (
    bytes([19]) + b"BitTorrent protocol" +  # 1+19
    b'\x00' * 8 +                            # 8 reserved
    self.info_hash +                         # 20
    self.our_peer_id                         # 20 = 68 total
)
```
**ולידציה (`:219`):** `pstrlen==19` ∧ `pstr=="BitTorrent protocol"` ∧ `info_hash match`.

### 🔴 #2 Rarest-First (`piece_manager.py:279`)
```python
for i in range(num_pieces):
    if piece.status != MISSING: continue
    if not peer_pieces[i]: continue
    freq = self._peer_frequency.get(i, 0)
    if freq < min_freq: candidates = [i]; min_freq = freq
    elif freq == min_freq: candidates.append(i)
return random.choice(candidates)  # ⭐ anti-thundering-herd
```

### 🔴 #3 Tit-for-Tat (`download_manager.py:610`)
```python
1. interested = [conn for conn if peer_interested]
2. if seeding: return _seed_mode_unchoke(...)
3. split snubbed / non_snubbed by is_snubbed()
4. non_snubbed.sort(by bytes_received_in_window(20s), reverse)
5. to_unchoke = top-4; fill from snubbed if short
6. Optimistic: random.choice(non_snubbed_remaining)
7. apply send_choke / send_unchoke
```

### 🔴 #4 Sliding Window (`peer_connection.py:552`)
```python
def bytes_received_in_window(window=20.0):
    cutoff = time.time() - window
    return sum(b for t, b in self._download_samples if t >= cutoff)
```

### 🔴 #5 SHA-1 (`security.py:96`)
```python
def verify_piece(piece_data, expected_hash):
    return hashlib.sha1(piece_data).digest() == expected_hash
```

### 🔴 #6 info_hash (`torrent_metadata.py` בתוך `_parse_metadata`)
```python
info_encoded = bencode.encode(info)          # canonical re-encode!
self.info_hash = hashlib.sha1(info_encoded).digest()
```

### 🔴 #7 Length-Prefix Framing (`peer_connection.py:271`)
```python
length_bytes = await reader.readexactly(4)
length, = struct.unpack('>I', length_bytes)
if length == 0: return KEEP_ALIVE
if length > 2*1024*1024: raise  # DoS cap
msg_data = await reader.readexactly(length)
```

### 🟡 #8 Async Bridge (`api_server.py:61`)
```python
def _run_async(coro, timeout=60):
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)
```

### 🟡 #9 Upload (`download_manager.py:432`)
```python
async def _serve_block_request(conn, msg):
    if conn.am_choking: return
    # bounds + length + piece COMPLETED checks
    block = await loop.run_in_executor(_executor, _read_block_sync, ...)
    await conn.send_piece(piece_idx, begin, block)
    self.stats.bytes_uploaded += len(block)
```

### 🟡 #10 PIECE Handler (`download_manager.py` בתוך `_on_peer_message`)
```python
is_complete = piece_manager.submit_block(idx, offset, data)
if is_complete:
    verified = await executor(verify_piece, idx)         # SHA-1
    if verified:
        await executor(_write_piece_sync, idx)           # disk
        asyncio.create_task(_broadcast_have(idx))        # fire-and-forget
        await _request_from_peer(...)                    # keep him busy
    else:
        security.report_hash_failure(peer_key, idx)
```

### 🟡 #11 Compact Peers (`tracker_client.py:104`)
```python
if len(data) % 6 != 0: return []  # validation
for i in range(0, len(data), 6):
    ip = '.'.join(str(b) for b in data[i:i+4])
    port, = struct.unpack('!H', data[i+4:i+6])
    peers.append(Peer(ip, port))
```

### 🟢 #12 Snubbing (`peer_connection.py:592`)
```python
def is_snubbed(threshold=60.0):
    if self.peer_choking: return False           # not snubbed if choked
    if self._last_request_time <= 0: return False
    last_signal = max(self._last_piece_time, self._connect_time)
    return (time.time() - last_signal) > threshold
```

### 🟢 #13 Bencode Canonical (`bencode.py:110`)
```python
def _encode_dict(value):
    sorted_keys = sorted(value.keys(), key=...)  # ⭐ חיוני ל-info_hash
    for key in sorted_keys: ...
```

---

## 🔁 7. Data Flow — זרימות מרכזיות

### A. הורדה חדשה (מהGUI עד דיסק)
```
User clicks "Add" in TorrentClientGUI
  → ApiService.startDownload(file, algos, dir)
  → POST /torrents (multipart) → api_server.py:239
  → _run_async(manager.add_torrent(...))                [bridge!]
  → DownloadManager.add_torrent() → creates Download
  → Download.start()
    → tracker_client.announce() → peers
    → for each peer: _connect_peer()
      → TCP + _send_handshake() + _receive_handshake()
      → start_message_loop()
    → _request_pieces() → _request_from_peer()
      → piece_manager.select_piece_rarest_first()
      → piece_manager.start_piece(idx)
      → conn.send_request(idx, begin, length)
```

### B. בלוק מגיע (PIECE message)
```
peer sends PIECE → _read_message() → _handle_message()
  → on_message callback → Download._on_peer_message()
  → PIECE branch:
    → piece_manager.submit_block(idx, offset, data)
    → if is_complete:
      → executor(verify_piece) → SHA-1
      → if verified:
        → executor(_write_piece_sync) → disk
        → create_task(_broadcast_have)  [HAVE לכולם]
        → _request_from_peer()          [תן עבודה חדשה]
      → else: security.report_hash_failure → maybe ban
```

### C. Choke decisions (Tit-for-Tat)
```
_choke_loop runs every 10s
  → _tit_for_tat_unchoke()
    → split snubbed/non_snubbed
    → sort by bytes_received_in_window(20)
    → top-4 + Optimistic (random)
  → for each connection: send_choke() or send_unchoke()
```

### D. REQUEST מ-peer (upload)
```
peer sends REQUEST → _handle_message() → on_message
  → Download._on_peer_message() → REQUEST branch
  → _serve_block_request(conn, msg)
    → checks: am_choking, bounds, piece COMPLETED
    → executor(_read_block_sync) → bytes
    → conn.send_piece(idx, begin, data)
    → stats.bytes_uploaded += len
```

### E. Polling מהGUI
```
ScheduledExecutorService every 500ms:
  → ApiService.getStatus() → GET /torrents
  → api_server: _run_async(manager.get_all_status())
  → update JTable
  → for each torrent: getLogs(id, lastSeq) → append to log area
  → detect state transition → popup if COMPLETED
```

---

## 📖 8. מילון מונחים — הגייה

| מונח | הגייה / שימוש |
|---|---|
| **BEP-3** | "בי-אי-פי-3" — BitTorrent Enhancement Proposal #3 |
| **bencode** | "בן-קוד" (לא ביי-אנקוד!) |
| **handshake** | תמיד 68 בתים — לא 67 ולא 69 |
| **info_hash** | תמיד SHA-1, 20 בתים |
| **piece** | בדרך כלל 256 KB = 16 blocks |
| **block** | תמיד 16 KB (BLOCK_SIZE) |
| **pstrlen** | אורך מחרוזת הפרוטוקול — תמיד 19 |
| **Tit-for-Tat** | טיט-פור-טאט מילה במילה |
| **Snubbing** | סנאבינג — peer ש-unchoked אבל לא שולח 60s |
| **Optimistic Unchoke** | בחירה אקראית של peer ל-unchoke (לא חישובית) |
| **Endgame mode** | בסוף ההורדה — request חופף מכמה peers |
| **Sliding window** | 20 שניות (TIT_FOR_TAT_WINDOW) |
| **SHAttered** | מתקפת collision על SHA-1 (2017) |
| **BitTyrant** | NSDI 2007 — מאמר על ניצול tit-for-tat |
| **BEP-52** | BitTorrent v2 — SHA-256 + Merkle Trees |
| **canonical bencode** | מפתחות ממוינים, no leading zeros — חיוני ל-info_hash |
| **thundering herd** | כולם רצים לאותו seeder — מנוטרל ע"י random.choice |

---

## 🔧 9. תיקונים שעשיתי — ציר זמן של Phases

| Phase | מה תיקנתי | הקובץ |
|---|---|---|
| **Phase 4a** | החלפת cumulative counter ב-sliding window | `peer_connection.py:552` `bytes_received_in_window` |
| **Phase 4b** | פיצול snubbed/non_snubbed ב-tit-for-tat | `download_manager.py:610` |
| **Phase 4c** | מטריקה הפוכה ב-seeding mode (לפי upload) | `download_manager.py:706` `_seed_mode_unchoke` |
| **Phase 6** | הוספת נתיב upload אמיתי | `download_manager.py:432` `_serve_block_request` |

**איך לדבר על תיקון Phase 4a:** "בגרסה הראשונה השתמשתי במונה cumulative — `bytes_downloaded` שגדל מאז ההתחלה. ראיתי peer ששתק שעות אבל נשאר בראש כי הסכום שלו היה גבוה. החלפתי ל-`bytes_received_in_window(20)` — deque של דגימות, סוכם רק את ה-20 שניות האחרונות. עכשיו peer ש-stalls יורד מהראש תוך 20s."

**איך לדבר על Phase 6:** "הקוד לא היה קיים בכלל. REQUEST הגיע, נכנס ל-`_handle_message`, ולא היה לו handler. הוספתי `_serve_block_request` עם 4 ולידציות (choking, bounds, piece COMPLETED, oversized), קריאה מהדיסק ב-executor כדי לא לחסום את ה-event loop, ו-send_piece. בלי זה, seeding היה meaningless כי `bytes_uploaded` תמיד היה 0 וה-seed-mode unchoke מיין הכל לפי 0."

---

## 🎯 טיפ אחרון לבחינה

1. **כל snippet — file:line מוכן בראש.**
2. **אם הבוחן שואל "איפה?":** נכנסים לטבלת §1 (top of file).
3. **אם הבוחן שואל "איך?":** §6 snippets המקוצרים.
4. **אם הבוחן שואל "למה?":** §9 התיקונים — תמיד יש סיפור.
5. **אם הבוחן שואל על קבוע:** §5 cheat sheet.

> בהצלחה 🚀

</div>
