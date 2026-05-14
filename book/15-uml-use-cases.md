# 15. ניתוח ותרשים Use Cases / UML של המערכת המוצעת

פרק זה מציג את ניתוח המערכת ברמת ה-Use Cases וה-UML —
האלגוריתם המרכזי, ה-UCs העיקריים, מבני הנתונים, חישוב
יעילות, ותיאור המחלקות.

## 15.1 תיאור ה-UC העיקריים של המערכת

האלגוריתם הראשי של המערכת הוא **לולאת ההורדה האסינכרונית**
(`Download._download_loop`) שרצה ב-Python Engine עבור כל
torrent פעיל. בפסאודו-קוד:

```
async _download_loop():
    1. אתחל TrackerClient + שלח announce(event='started')
    2. הוסף את ה-peers שהוחזרו ל-_known_peers
    3. הפעל ברקע: _choke_loop (כל 10s),
                  _keep_alive_loop (כל 60s),
                  start_periodic_announce
       + יזום _connect_to_peers
    4. while not piece_manager.is_complete and state == RUNNING:
         a. piece_manager.reset_stale_pieces(30s)
         b. _request_pieces — מבקש בלוקים מ-peers
         c. await asyncio.sleep(0.1)
         d. כל 15 שניות: cleanup + reconnect
         e. update_speed + tracker.update_stats
    5. אם is_complete: _complete_download
    6. finally: _save_state
```

הלולאה הזו אינה חוסמת — בכל מקום שבו נדרשת פעולה חוסמת
(SHA-1, כתיבה לדיסק) היא מועברת ל-`ThreadPoolExecutor`.

האלגוריתמים המישניים המרכזיים:

**rarest-first piece selection**: עוברים על כל ה-pieces
שעדיין חסרים שה-peer מציע, מוצאים את אלה עם המינימום של
`peer_frequency` (כמה peers מחזיקים בהם), ובוחרים אחד
מתוך הקבוצה הנדירה באקראי. הרעיון: pieces נדירים זוכים
לעדיפות כי הם הצוואר בקבוק העיקרי לסיום ההורדה.

**Tit-for-Tat unchoke**: כל 10 שניות, ממיינים את ה-peers
שמעוניינים לפי כמות הנתונים שתרמו לנו, ופותחים choke
ל-4 הטובים ביותר. בנוסף, optimistic unchoke לאחד אקראי
מבין השאר. peers שלא תרמו → choke. האלגוריתם הזה הופך את
ה-bandwidth שלנו ל"מטבע" שמעודד reciprocity.

**round-robin unchoke** (baseline להשוואה): פותחים choke
ל-peer הבא בתור, בלי קשר לתרומה. פחות יעיל מ-Tit-for-Tat
כי הוא לא מעודד תרומה — אבל פשוט יותר ומשמש כ-baseline
לטובת ההשוואה הניסויית בפרק 24.

## 15.2 הצגת Use Case עבור הפונקציות העיקריות

### UC-1: הוספת torrent חדש

- **שחקן**: משתמש קצה.
- **תנאי מקדים**: המערכת רצה והשרת זמין.
- **זרימה**: המשתמש לוחץ "Add Torrent" ב-toolbar →
  ה-GUI פותח JFileChooser לקובץ `.torrent` → JFileChooser
  שני לתיקיית יעד → ה-GUI שולח `POST /torrents` עם הקובץ
  ואלגוריתמים → ה-Engine מאתחל `TorrentMetadata`, יוצר
  `Download`, ומחזיר `id` → שורה חדשה בטבלה במצב `Running`.
- **חלופות**: קובץ פגום → 400 Bad Request → Alert למשתמש.

### UC-2: השהיה / חידוש / ביטול

- **שחקן**: משתמש קצה.
- **זרימה**: בוחר שורה בטבלה → לוחץ Pause / Resume /
  Cancel → GUI שולח את הקריאה המתאימה ל-API → ה-Engine
  מפעיל את `Download.pause/resume/cancel` → ה-state מתעדכן
  ב-polling הבא (תוך 500ms).
- **Cancel** דורש אישור (`JOptionPane.YES_NO`) כי הפעולה
  לא הפיכה.

### UC-3: צפייה בהיסטוריה

- **שחקן**: משתמש קצה.
- **זרימה**: לוחץ History → GUI שולח `GET /history` →
  ה-Engine שולף מ-SQLite (JOIN של `torrents` ו-
  `performance_stats`) → נפתח `JDialog` עם טבלה.
- **פעולה משלימה**: Clear History → `DELETE /history`.

### UC-4: צפייה בסטטיסטיקות אלגוריתמיות

- **שחקן**: משתמש קצה.
- **זרימה**: לוחץ Statistics → נפתח `AlgorithmStatsDialog`
  עם שתי לשוניות: bar chart של בחירות rarest-first
  (ב-Java2D) וסטטיסטיקות מצרפיות (9 שדות).

### UC-5: החלפת נתונים עם peer (אוטומטי)

- **שחקן**: המערכת עצמה (system actor); peer חיצוני.
- **זרימה**: `_connect_to_peers` יוצר `PeerConnection` →
  TCP + handshake → BITFIELD exchange → INTERESTED אם
  ה-peer מציע piece שאנחנו צריכים → אם הוא שולח UNCHOKE,
  `select_piece_rarest_first` בוחר piece → שולחים REQUEST
  לכל בלוק → מקבלים PIECE → SHA-1 verify → אם OK: כתיבה
  לדיסק + HAVE broadcast.

## 15.3 מבני נתונים בשימוש

| מבנה | מודול | תפקיד | סיבה לבחירה |
|---|---|---|---|
| `Dict[str, Download]` | `DownloadManager.downloads` | מפתח לפי id | O(1) lookup |
| `Dict[str, PeerConnection]` | `Download._connections` | מפתח לפי `ip:port` | O(1) lookup |
| `Set[Peer]` | `Download._known_peers` | רשימת peers ידועים | מניעת כפילויות; `__hash__` ב-`Peer` |
| `deque(maxlen=200)` | `Download._log_buffer` | חוצץ לוגים | append O(1) + drop אוטומטי של הישנים |
| `List[Piece]` | `PieceManager.pieces` | pieces לפי index | O(1) random access |
| `Dict[int, int]` | `PieceManager._peer_frequency` | piece_idx → count | עדכון O(1) ב-HAVE |
| `Dict[str, Set[int]]` | `PieceManager._peer_pieces` | peer → set of indices | diff מהיר בעת ניתוק |
| `bytearray(length)` | `Piece._data` | מאגר נתונים mutable | יעיל לכתיבת בלוקים נפרדים |
| `Dict[str, PeerReputation]` | `SecurityManager._peer_reputations` | מוניטין | O(1) lookup |
| `Set[str]` | `SecurityManager._banned_peers` | peers מבוננים | O(1) `in` בדיקה |

לקונקורנציה: `threading.Lock` ב-`PieceManager._lock` מגן
על `_peer_frequency` ו-`_peer_pieces` שמתעדכנים גם מ-event
loop וגם מ-worker threads. `_db_lock` ב-`api_server` מגן
על גישה ל-SQLite מבקשות Flask מקבילות. `ThreadPoolExecutor`
(`max_workers=2`) מטפל בפעולות חוסמות בלבד.

## 15.4 חישוב יעילות האלגוריתם

| פעולה | סיבוכיות זמן | סיבוכיות מקום |
|---|---|---|
| `select_piece_rarest_first` | O(N) | O(N) |
| `select_piece_random` | O(N) | O(N) |
| `update_peer_have` (HAVE message) | O(1) | O(1) |
| `update_peer_pieces` (BITFIELD) | O(N) | O(N) |
| `_tit_for_tat_unchoke` | O(K log K) | O(K) |
| `_round_robin_unchoke` | O(K) | O(1) |
| `Piece.verify_hash` (SHA-1) | O(L) | O(1) |
| `bencode.decode` | O(M) | O(M) |

כאשר N = מספר ה-pieces (טיפוסית 16,384 עבור קובץ 4GB),
K = מספר ה-peers (≤ 50), L = גודל piece בבתים (256KB–1MB),
M = גודל הקובץ `.torrent` (≤ 1MB).

**הערה מרכזית**: rarest-first ו-random הם **שניהם O(N)**.
ההבדל ביניהם הוא איכותי (התפלגות הבחירה) ולא בסיבוכיות.
ב-rarest-first יש בנוסף `random.choice` על קבוצת
candidates (O(1)) שמתבצע אחרי החיפוש הליניארי. עבור
N=16,384, פעולה אחת אורכת ~1ms ב-Python — מתחת לסף של
"חוסם את ה-event loop".

Tit-for-Tat דורש O(K log K) בגלל המיון (`sort by
bytes_downloaded`), בעוד round-robin הוא O(K) פשוט. עבור
K=50, ההפרש זניח (~280 פעולות אריתמטיות מול ~50). מצדיק
את העלות הקטנה לטובת איכות אלגוריתמית טובה הרבה יותר.

חישוב SHA-1 על piece בגודל 1MB אורך ~2ms במעבד מודרני.
זה לא נראה הרבה, אבל **חסימה של ~2ms על שגרה תכופה**
שווה ל-10–20% מ-CPU שאבד אם זה רץ ב-event loop הראשי.
לכן ההעברה ל-`ThreadPoolExecutor` חיונית.

## 15.5 הקשרים בין היחידות השונות

זרימת תלות במודולי ה-Engine:

```
api_server  ──calls──►  DownloadManager
                              │
                              ├─uses─►  TorrentMetadata
                              ├─owns─►  Download (per torrent)
                                          │
                                          ├─owns─►  PieceManager
                                          ├─owns─►  SecurityManager
                                          ├─owns─►  TrackerClient
                                          └─owns─►  PeerConnection (per peer)
```

`TorrentMetadata` נצרך פעם אחת בעת `POST /torrents` כדי
לחלץ `info_hash`, `pieces`, ושאר השדות. `Download` הוא
ה-orchestrator המרכזי — הוא רושם את עצמו כ-`on_message`
callback של כל `PeerConnection`, ומקבל אירועים מכל
ה-peers. הוא מאציל ל-`PieceManager` (לבחירת piece הבא),
ל-`SecurityManager` (לאימות peers), ול-`TrackerClient`
(לקבלת רשימת peers מעודכנת).

הגשר בין שני התהליכים (GUI ↔ Engine) הוא REST/JSON על
loopback בלבד. אין ערוצים נוספים — לא shared memory, לא
pipes, לא file descriptors משותפים.

## 15.6 עץ מודולים

```
Project_Gal/
├── python_engine/                    Engine (Python 3.8+)
│   ├── api_server.py        (509)    Flask REST API + SQLite
│   ├── download_manager.py  (891)    Download + algorithms
│   ├── piece_manager.py     (473)    Piece + Block + PieceManager
│   ├── peer_connection.py   (520)    PeerConnection + state machine
│   ├── tracker_client.py    (337)    TrackerClient + Peer
│   ├── torrent_metadata.py  (241)    TorrentMetadata + FileInfo
│   ├── bencode.py           (231)    encode/decode
│   ├── security.py          (326)    SecurityManager + PeerReputation
│   ├── main.py              (190)    CLI mode
│   └── tests/                        160 pytest unit tests
│
└── java_gui/                         GUI (Java 11+, Swing)
    ├── src/
    │   ├── TorrentClientGUI.java     (649)  JFrame + toolbar + table
    │   ├── ApiService.java           (430)  HTTP client
    │   └── AlgorithmStatsDialog.java (562)  JDialog + bar chart
    └── lib/json.jar                  org.json
```

סך הכל ~5,360 שורות פרודקשן (3,718 Python + 1,641 Java).

## 15.7 Use Case Diagram

תרשים ה-Use Case מציג את חמשת ה-UCs (UC-1 עד UC-5)
כתיבות ביציות בתוך גבול המערכת, עם שלושה אקטורים: User,
Tracker, ו-Peer (external).

[Use Case Diagram יושלם בעת ההגשה הסופית]

## 15.8 רשימת Use Cases

| ID | שם | שחקן | תדירות |
|---|---|---|---|
| UC-1 | Add Torrent | User | פעמים בודדות |
| UC-2 | Pause/Resume/Cancel | User | לפי הצורך |
| UC-3 | Show History | User | פעמים בודדות |
| UC-4 | Show Stats | User | לפי הצורך |
| UC-5 | Exchange Data with Peer | System | רציף, עשרות בשנייה |

## 15.9 תרשים UML — Sequence Diagram

זרימת קבלת PIECE מ-peer:

```
Peer → PeerConnection: PIECE message (TCP)
PeerConnection → PeerConnection: _read_message (length + payload)
PeerConnection → PeerConnection: _handle_message (update bytes)
PeerConnection → Download: on_message callback
Download → PieceManager: submit_block(idx, offset, data)
[if piece complete]
  Download → ThreadPool: verify_piece (SHA-1)
  [if OK]
    Download → SecurityManager: report_successful_piece
    Download → ThreadPool: _write_piece_sync
    Download → all PeerConnections: broadcast HAVE
  [if FAIL]
    Download → SecurityManager: report_hash_failure
    [if banned] Download → PeerConnection: disconnect
```

## 15.10 Design Class Diagram

המחלקה המרכזית `Download` מכילה בקומפוזיציה את
`PieceManager`, `SecurityManager`, ו-`ThreadPoolExecutor`,
ובאגרגציה את `TrackerClient` ואת `Dict[str, PeerConnection]`.
המתודות הציבוריות שלה: `async start/pause/resume/cancel`,
`get_status()`, `get_logs(since_seq)`, `on_progress/complete/state_change`.

## 15.11 תרשים מחלקות

תרשים המחלקות מציג את 18 מחלקות המערכת. ב-Python: 15
מחלקות (`Download`, `DownloadManager`, `DownloadStats`,
`DownloadState`/`AlgorithmType` enums, `PieceManager`,
`Piece`, `Block`, `PieceStatus`, `PeerConnection`,
`PeerMessage`, `MessageType` enum, `TrackerClient`, `Peer`,
`TrackerResponse`, `TorrentMetadata`, `FileInfo`,
`SecurityManager`, `PeerReputation`, `SecurityEvent`).
ב-Java: 3 מחלקות ראשיות (`TorrentClientGUI`, `ApiService`,
`AlgorithmStatsDialog`) + 3 מקוננות (`TorrentStatus`,
`ApiException`, `BarChartPanel`).

הקשרים: composition (יהלום מלא) של `Download` עם הרכיבים
שלו; aggregation (יהלום ריק) של `Download` עם
`TrackerClient`; inheritance רק ב-`TorrentClientGUI extends
JFrame`, `AlgorithmStatsDialog extends JDialog`,
`BarChartPanel extends JPanel`, ובמחלקות ה-Exception.
הגשר בין שני ה-swimlanes (Python ↔ Java) הוא חץ אחד עם
תווית `HTTP/JSON REST`.

## 15.12 תיאור המחלקות המוצעות

### `TorrentMetadata`

- **תפקיד**: parser של קובץ `.torrent`.
- **קלטים**: path או bytes של קובץ `.torrent`.
- **פלטים**: `announce` URL, `info_hash` (SHA-1 על ה-info
  dict), `pieces` (רשימת hashים בני 20 בתים), `files`,
  `total_size`, `piece_length`.

### `PieceManager` (+ `Piece` + `Block`)

- **תפקיד**: ניהול מצב ההורדה ברמת piece. מי הושלם, מי
  בתהליך, מי חסר; בחירת piece הבא; חישוב SHA-1.
- **קלטים**: num_pieces, piece_length, total_size,
  piece_hashes (מה-`TorrentMetadata`). בזמן ריצה — BITFIELD
  ו-HAVE מ-peers, ובלוקים שהתקבלו.
- **פלטים**: `select_piece_rarest_first/random` מחזירות
  piece_index; `submit_block` מחזירה bool שהפיס שלם;
  `verify_piece` מחזירה bool של אימות SHA-1.

### `PeerConnection` (+ `PeerMessage` + `MessageType`)

- **תפקיד**: ניהול חיבור TCP יחיד ל-peer. handshake,
  parsing הודעות, state machine של choking/interest.
- **קלטים**: ip, port, info_hash, peer_id, num_pieces,
  on_message callback.
- **פלטים**: callback `on_message(self, message)`
  ל-`Download._on_peer_message`. שדות סטטוס:
  `connected`, `peer_choking`, `peer_pieces`,
  `download_rate`.

### `TrackerClient` (+ `Peer` + `TrackerResponse`)

- **תפקיד**: תקשורת HTTP/HTTPS עם ה-tracker.
- **קלטים**: announce_url, info_hash, peer_id, port.
  בזמן ריצה — uploaded, downloaded, left.
- **פלטים**: `TrackerResponse` עם רשימת `Peer` (ip, port),
  `interval`, `complete`/`incomplete` counts.

### `Download` (המחלקה המרכזית)

- **תפקיד**: ה-orchestrator של ההורדה. מתאם בין כל
  הרכיבים. מריץ את `_download_loop`. מבצע choke/unchoke.
  מבקש בלוקים מ-peers.
- **קלטים**: `TorrentMetadata`, download_dir, state_dir,
  שני אלגוריתמים, callbacks.
- **פלטים**: `async start/pause/resume/cancel`;
  `get_status() → dict`; `get_logs(since_seq)`.

### `DownloadManager`

- **תפקיד**: רישום של כל ההורדות הפעילות. כל הקריאות
  מ-Flask עוברות דרכו.
- **קלטים**: download_dir, state_dir.
- **פלטים**: `Download` instances; API:
  `add_torrent`, `pause/resume/cancel_download(id)`,
  `get_download_status(id)`, `get_all_status`.

### `SecurityManager` (+ `PeerReputation` + `SecurityEvent`)

- **תפקיד**: אבטחה — מוניטין peers, באנים, יומן אירועים.
  פירוט בפרק 12.
- **פלטים**: `is_peer_banned(peer_key) → bool` (משמש
  ב-`_connect_to_peers`); רשימת events ל-API; `trust_score`.

### Java GUI

- **`TorrentClientGUI`**: JFrame הראשי. JTable של הורדות,
  toolbar עם כפתורים, JTextArea ללוגים. polling כל 500ms.
- **`ApiService`**: HTTP client. שכבת אבסטרקציה מעל ה-
  REST API. כל פעולה ב-GUI עוברת דרכה.
- **`AlgorithmStatsDialog`**: JDialog עם JTabbedPane.
  Tab 1: bar chart ב-Java2D של בחירות rarest-first.
  Tab 2: 9 שדות סטטיסטיקה מצרפיים.
