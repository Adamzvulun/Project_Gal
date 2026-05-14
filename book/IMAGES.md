# IMAGES.md – רשימת תרשימים, צילומי מסך ואיורים

קובץ זה מרכז את כל התרשימים, צילומי המסך והאיורים שיש לשלב בספר.
הרשימה מתעדכנת באופן שוטף תוך כדי כתיבת הפרקים. עבור כל פריט מצוין:

- **מס'**: מזהה ייחודי לאיור (Fig-01, Fig-02, ...).
- **פרק**: הפרק והסעיף בו ישולב.
- **מיקום בקובץ**: עוגן/נקודת שילוב מדויקת בתוך קובץ הפרק.
- **סוג**: תרשים זרימה / תרשים ארכיטקטורה / תרשים תקשורת / ERD / UML / צילום מסך.
- **תיאור מפורט**: מה התרשים אמור להציג, מהם הרכיבים, החצים, התוויות.
- **סטטוס**: דרוש / נוצר / שולב.

---

## Fig-01 – סריקת הצעת הפרויקט החתומה

- **פרק**: 1 (הצעת הפרויקט שאושרה) — סעיף 1.1 / 1.17.
- **מיקום בקובץ**: `01-approved-proposal.md`, מיד אחרי כותרת הפרק
  (סעיף 1.1 *"פתיח לפרק"*); דף החתימות בסוף הפרק (סעיף 1.17).
- **סוג**: סריקת מסמך (PDF / תמונה).
- **תיאור מפורט**: יש לשלב את כל עמודי ה-PDF המקורי
  `הצעת פרוייקט - אדם זבולון 329441273 V2.2.pdf` (השמור בריפו) כסריקה
  בתוך המסמך — דף השער, תוכן העניינים של ההצעה, ולפחות עמוד החתימות
  האחרון (עמ' 23 ב-PDF המקורי) שעליו מופיעות שלוש החתימות: סטודנט,
  מנחה, רכז מגמה. ההגשה הסופית ב-Word צריכה לכלול את כל 23 העמודים
  של ההצעה כסריקה רציפה או כנספח מודפס.
- **סטטוס**: דרוש.

---

## Fig-02 – תרשים ארכיטקטורה כללי (Top-Down) של המערכת

- **פרק**: 1 (הצעת הפרויקט) — סעיף 1.8.1, וכן יצוטט שוב בפרק 11.
- **מיקום בקובץ**: `01-approved-proposal.md`, מיד אחרי הפסקה הפותחת
  של סעיף 1.8.1 *"חלוקה לשכבות ולמודולים"*.
- **סוג**: תרשים ארכיטקטורה.
- **תיאור מפורט**: תרשים זהה במהותו לתרשים בעמ' 8 של ההצעה המקורית.
  התרשים צריך להציג שתי שכבות עיקריות:
  - **Client** (חלק עליון) — מכיל את `Java GUI Client` עם שני
    תת-רכיבים: `Java GUI (Swing)` ו-`HTTP Client (REST calls)`.
  - **BitTorrent Engine** (חלק תחתון) — מכיל את הרכיבים:
    `REST API Server (Flask)`, `TorrentMetadata (Bencode parsing)`,
    `Security (Validation & Logging)` בשורה עליונה; `DownloadManager
    (choke/unchoke)` במרכז; `TrackerClient (HTTP/HTTPS)`,
    `PieceManager (rarest-first)`, `PeerConnection* (TCP sockets)`
    בשורה תחתונה.
  - חצים: מ-Java GUI ל-REST API Server (תווית `REST API`); מ-Flask
    אל DownloadManager; מ-DownloadManager אל שלושת הרכיבים התחתונים;
    מ-TrackerClient לרכיב חיצוני `Tracker Servers` (תווית `announce /
    response`); מ-PeerConnection לרכיב חיצוני `Peers in Swarm`
    (תווית `peer wire protocol`).
  - יש להציג את הגבולות הלוגיים של ה-Client לעומת ה-Engine באמצעות
    מסגרות מודגשות, כדי להבהיר שמדובר בשני תהליכים נפרדים על אותה
    מכונה המתקשרים דרך REST.
- **סטטוס**: דרוש.

---

## Fig-03 – תרשים רצף הורדה (Sequence Diagram)

- **פרק**: 1 (הצעת הפרויקט) — סעיף 1.9.2, וכן יצוטט שוב בפרק 11
  ובפרק 15.
- **מיקום בקובץ**: `01-approved-proposal.md`, בסוף סעיף 1.9.2
  *"תקשורת בין peers – Peer Wire Protocol"*.
- **סוג**: תרשים רצף (Sequence Diagram) ברוח UML.
- **תיאור מפורט**: תרשים זהה במהותו לתרשים בעמ' 12 של ההצעה המקורית.
  *Lifelines*: `Java GUI`, `Python REST API`, `DownloadManager`,
  `TrackerClient`, `PeerConnection`, `Remote Peer`, `PieceManager`
  (PM). זרימה:
  1. `Java GUI → Python REST API`: `POST /torrents` עם קובץ `.torrent`.
  2. `REST API → DownloadManager`: `startDownload(metadata)`.
  3. `DownloadManager → TrackerClient`: `announce(info_hash, stats)`,
     החזרה: `peers[]`.
  4. *loop* על peers: `DownloadManager → PeerConnection`: `connect(ip,
     port)`; `PeerConnection → Remote Peer`: `handshake(info_hash,
     peer_id)`; `Remote Peer → PeerConnection`: `handshake(...)`,
     `bitfield`.
  5. *loop* (עד שהקובץ הושלם):
     - `DownloadManager → PieceManager`: `selectPiece(rarest-first)`,
       החזרה: `pieceIndex`.
     - `DownloadManager → PeerConnection`: `request(pieceIndex,
       blocks)`; `PeerConnection → Remote Peer`: `request(...)`;
       `Remote Peer → PeerConnection`: `piece blocks`.
     - `PeerConnection → DownloadManager`: `data(pieceIndex, block)`;
       `DownloadManager → PieceManager`: `submitBlock(pieceIndex,
       block)`; *הערה*: "If piece complete & hash OK".
- **סטטוס**: דרוש.

---

## Fig-04 – תרשים מרכיבי מערכת BitTorrent

- **פרק**: 6 (רקע תיאורטי) — סעיף 6.1.2 *"מבנה מערכת BitTorrent"*.
- **מיקום בקובץ**: `06-theoretical-background.md`, מיד אחרי
  סעיף 6.1.2.
- **סוג**: תרשים מושגי / היררכי.
- **תיאור מפורט**: תרשים המציג את ארבעת המרכיבים התפקודיים של
  מערכת BitTorrent ואת היחסים ביניהם:
  - בצד שמאל למעלה: **קובץ `.torrent`** (קופסה מלבנית) — מתאר
    את התוכן (`announce`, `info` dict, `pieces[]`, `info_hash`).
  - בצד ימין למעלה: **Tracker** (מסד נתונים / קופסת שרת) — מחזיק
    טבלה: `info_hash → [peer_1, peer_2, ...]`.
  - במרכז: **Swarm** (מעגל גדול) — מכיל את כלל ה-peers.
  - בתוך ה-swarm: **Seeders** (סמל ירוק עם 100%) ו-**Leechers**
    (סמל צהוב עם אחוז חלקי).
  - חצים:
    - מ-Client (`.torrent` בידיו) → Tracker: `announce(info_hash)`.
    - מ-Tracker → Client: `peers[]`.
    - בין כל זוג peers ב-swarm: חץ דו-כיווני המסומן
      `Peer Wire Protocol`.
  - יש להציג את הגבול בין השכבה הלוגית (קובץ torrent +
    info_hash + tracker — שכבת *Discovery*) לבין שכבת ה-Data
    Transfer (peers ב-swarm) באמצעות קו מקווקו.
- **סטטוס**: דרוש.

---

## Fig-05 – תרשים Context (Top-Down רמה 0)

- **פרק**: 11 (ארכיטקטורה) — סעיף 11.1.1.
- **מיקום בקובץ**: `11-architecture.md`, בסעיף 11.1.1.
- **סוג**: Context Diagram (UML / DFD level 0).
- **תיאור מפורט**: תיבה שחורה יחידה במרכז עם הכותרת *"BitTorrent
  Distributed File Sharing System"*. סביבה ארבעה שחקנים חיצוניים,
  עם חצים דו-כיווניים אליה: (1) `User` משמאל למעלה — אינטראקציה
  עם GUI; (2) `Tracker` (סמל שרת) מימין למעלה — תקשורת HTTP
  announce/response; (3) קבוצת `Peers` (`Peer 1`, `Peer 2`, `Peer
  N`) מתחת — תקשורת TCP/BEP-3. כל חץ עם תווית קצרה
  (`HTTP`, `TCP`, `User Actions`).
- **סטטוס**: דרוש.

---

## Fig-06 – תרשים Top-Down רמה 2 (תת-מערכות)

- **פרק**: 11 (ארכיטקטורה) — סעיף 11.1.3.
- **מיקום בקובץ**: `11-architecture.md`, בסעיף 11.1.3.
- **סוג**: תרשים ארכיטקטורה מפורט.
- **תיאור מפורט**: שני מלבנים גדולים זה לצד זה, המייצגים את שני
  התהליכים:
  - **Java GUI Process** (שמאל): בתוכו תיבה ראשית
    `TorrentClientGUI (Main)`; שתי תיבות תחת — `ApiService`
    (HttpClient) ו-`AlgorithmStatsDialog` (Modal).
  - **Python Engine Process** (ימין): שלוש שורות תיבות:
    שורה 1 — `Flask REST API Server`; שורה 2 — `DownloadManager`
    (במרכז) המקושר אל `PieceManager`, `PeerConnection`,
    `TrackerClient`; שורה 3 — `Security`, `TorrentMetadata` (משמאל)
    ו-`JSON state files`, `SQLite (history.db)` (מימין).
  - חץ דו-כיווני באמצע בין שני התהליכים, עם תווית
    `REST/JSON over HTTP — localhost:5000`.
  - חצים יוצאים מ-`TrackerClient` ו-`PeerConnection` החוצה לקצוות
    התרשים (מסומנים `→ Tracker` ו-`→ Peers in Swarm`).
- **סטטוס**: דרוש. ניתן להתבסס על התרשים בעמ' 8 של הצעת הפרויקט,
  אך בגרסה מורחבת לפי תוכן הסעיף.

---

## Fig-07 – תרשים ארכיטקטורת רשת

- **פרק**: 11 (ארכיטקטורה) — סעיף 11.4.2.
- **מיקום בקובץ**: `11-architecture.md`, בסעיף 11.4.2.
- **סוג**: תרשים זרימת רשת.
- **תיאור מפורט**: שלוש שכבות תקשורת מוצגות בשלושה צבעים שונים:
  - **שכבה ירוקה (Local IPC)**: חץ דו-כיווני בין תיבת `Java GUI`
    לתיבת `Python Engine`, עם תווית `HTTP/JSON · localhost:5000`.
  - **שכבה כחולה (HTTP Tracker)**: חץ דו-כיווני בין `Python
    Engine` לתיבה חיצונית `Tracker (HTTP/HTTPS)`, עם תווית
    `Bencode response · port 80/443`.
  - **שכבה כתומה (Peer Wire Protocol)**: חץ מ-`Python Engine`
    היוצא לקבוצה של ~5 תיבות `Peer 1..5` (מיוצגות כ-swarm), עם
    תווית `TCP/BEP-3 · port 6881 + dynamic`.
  - בתחתית התרשים, מקרא הסבר על כל שכבה: פרוטוקול, רוחב פס
    טיפוסי, ודרישות אבטחה.
- **סטטוס**: דרוש.

---

## Fig-08 – תרשים מודל איום (Threat Model Diagram)

- **פרק**: 12 (אבטחת מידע) — סעיף 12.1.1.
- **מיקום בקובץ**: `12-security.md`, בסוף סעיף 12.1.1 (לפני
  טבלת וקטורי האיום ב-12.1.2).
- **סוג**: תרשים מודל איום (Trust-Boundary Diagram).
- **תיאור מפורט**: התרשים מציג את **המערכת כתיבה מרכזית** עם
  גבולות אמון (trust boundaries) מסומנים בקווים מקווקווים, ו-3
  מקורות איום חיצוניים:
  - **תיבה מרכזית** (`BitTorrent Client`) — מחולקת לשני
    תת-איזורים: `Java GUI` ו-`Python Engine`, עם קו ירוק
    דק (Trust Boundary פנימי = loopback).
  - **שחקן עוין 1**: `Malicious Peer` — תיבה אדומה, מחוץ
    לגבול האמון; חץ דו-כיווני אדום אליה עם תווית `TCP/BEP-3
    (T1–T7)`.
  - **שחקן עוין 2**: `Compromised Tracker` — תיבה כתומה, מחוץ
    לגבול האמון; חץ דו-כיווני כתום אליה עם תווית `HTTP/HTTPS
    (T8, T11)`.
  - **שחקן עוין 3**: `Network Attacker (MITM/Eavesdropper)` —
    תיבה צהובה הממוקמת **על גבי החצים** של שני השחקנים
    הקודמים, עם תווית `T9, T10`.
  - בכל חץ צמודה רשימה של מזהי האיום (T1–T11) שהוא נושא,
    בהתאמה לטבלה ב-12.1.2.
  - מקרא צבעים: אדום=peer, כתום=tracker, צהוב=רשת,
    ירוק=loopback פנימי.
- **סטטוס**: דרוש.

---

## Fig-09 – תרשים זרימת הגנה (Defense Flow Diagram)

- **פרק**: 12 (אבטחת מידע) — סעיף 12.1.6.
- **מיקום בקובץ**: `12-security.md`, בסוף סעיף 12.1.6 (לפני
  טבלת הסיכום ב-12.1.7).
- **סוג**: תרשים זרימה (Flowchart).
- **תיאור מפורט**: התרשים מציג את **שמונת שכבות ההגנה** כשרשרת
  decision-points, החל מקבלת ה-handshake וכלה בכתיבה לדיסק.
  כל שלב הוא רומבוס (החלטה) או מלבן (פעולה); כל החלטה שלילית
  ("FAIL") מוליכה לתיבת `Reject + report to SecurityManager`,
  וכל החלטה חיובית ("OK") ממשיכה לשלב הבא:
  1. **Handshake validation** (אורך 68, pstr, info_hash) →
     FAIL ⇒ `PeerConnectionError`.
  2. **Message length ≤ 2 MB?** → FAIL ⇒ `protocol_violation`.
  3. **Valid msg_id (0–8)?** → FAIL ⇒ drop silently.
  4. **piece_index in range?** → FAIL ⇒ `protocol_violation`.
  5. **Block buffered into piece**.
  6. **All blocks received?** → לא: חזרה לשלב 2 לקריאת הודעה
     הבאה; כן: המשך.
  7. **SHA-1 == expected_hash?** → FAIL ⇒
     `report_hash_failure` → אם `should_ban` ⇒ ban.
  8. **Write piece to disk**.
  - בצד התיבות הרלוונטיות תוצג כתובית עם הקובץ והפונקציה
    האחראית (`peer_connection.py:_receive_handshake`,
    `piece_manager.py:verify_hash`, וכו').
  - מקרא: ירוק=זרימה תקינה, אדום=זרימת כשל/באן.
- **סטטוס**: דרוש.

---

## Fig-10 – Flowchart של `_download_loop`

- **פרק**: 15 — סעיף 15.1.2.
- **מיקום בקובץ**: `15-uml-use-cases.md`, בסוף סעיף 15.1.2.
- **סוג**: תרשים זרימה (Flowchart).
- **תיאור מפורט**: הזרימה הראשית של `Download._download_loop`
  כשרשרת תיבות (Start → Init → ... → End). תיבות מרכזיות:
  `Init TrackerClient`, `Announce(event='started')`, `Add peers
  to _known_peers`, `Start _choke_loop`, `Start _keep_alive_loop`,
  `Start periodic_announce`, ולולאה ראשית עם תנאי
  `is_complete OR state != RUNNING` כיציאה. בתוך הלולאה: `reset
  stale pieces`, `_request_pieces`, `await asyncio.sleep(0.1)`,
  בדיקה תקופתית `_cleanup_dead_peers + _connect_to_peers`,
  `_update_speed + tracker.update_stats`. מצב סופי: `if is_complete
  → _complete_download (event='completed')`; תמיד `_save_state`
  בסיום (finally).
- **סטטוס**: דרוש.

---

## Fig-11 – Sequence Diagram: קבלת PIECE מ-peer

- **פרק**: 15 — סעיף 15.5.4.
- **מיקום בקובץ**: `15-uml-use-cases.md`, בסוף סעיף 15.5.4.
- **סוג**: Sequence Diagram (UML).
- **תיאור מפורט**: התרשים מציג חמש lifelines אנכיות זה לצד זה:
  `Peer (remote)`, `PeerConnection`, `Download`, `PieceManager`,
  `SecurityManager`, ו-`ThreadPoolExecutor`. הזרימה:
  1. `Peer` → `PeerConnection`: שלח PIECE message (TCP).
  2. `PeerConnection._read_message`: קריאת length + payload.
  3. `PeerConnection._handle_message`: זיהוי MessageType.PIECE,
     עדכון bytes_downloaded.
  4. `PeerConnection.on_message` → `Download._on_peer_message`.
  5. `Download` → `PieceManager.submit_block(piece_idx, offset,
     data)`: כתיבה ל-`Piece._data[offset:]`.
  6. אם `is_complete`: `Download` → `ThreadPoolExecutor.submit(
     piece_manager.verify_piece, idx)`.
  7. ענף אחד: SUCCESS → `SecurityManager.report_successful_piece`,
     `_write_piece_sync` (ב-pool), broadcast HAVE לכל החיבורים.
  8. ענף שני: FAIL → `SecurityManager.report_hash_failure`, אם
     `should_ban` → `_ban_peer`, סגירת חיבור.
  9. סיום: `Download._request_from_peer` → לבחור piece חדש →
     שלח REQUEST.
  הזמן עובר מלמעלה למטה; חצים synchronous מסומנים בקו מלא,
  callbacks asynchronous בקו מקווקו.
- **סטטוס**: דרוש.

---

## Fig-12 – Use Case Diagram

- **פרק**: 15 — סעיף 15.7.
- **מיקום בקובץ**: `15-uml-use-cases.md`, בסוף סעיף 15.7.
- **סוג**: Use Case Diagram (UML).
- **תיאור מפורט**: מלבן גדול במרכז המסמל את System Boundary
  של "BitTorrent Client". בתוכו 6 ביצים אופקיות (UCs):
  `Add Torrent (UC-01)`, `Pause/Resume/Cancel (UC-02)`,
  `Show History (UC-03)`, `Show Algorithm Stats (UC-04)`,
  `Configure Algorithms (UC-05)`, `Exchange Data with Peer
  (UC-06)`. בצד שמאל איש סטיק (`User`) מחובר ל-UC-01..05
  בקווים פשוטים. בצד ימין שני סוגים של אקטורים-מערכת:
  `Tracker` מחובר ל-UC-01 (init) ול-UC-06 (announce); `Peer
  (external)` מחובר ל-UC-06. בנוסף יחס `<<include>>` מ-UC-01
  ל-UC-05 (האלגוריתמים נקבעים כחלק מ-Add Torrent).
- **סטטוס**: דרוש.

---

## Fig-13 – Class Diagram (Engine, package level)

- **פרק**: 15 — סעיף 15.9.
- **מיקום בקובץ**: `15-uml-use-cases.md`, בסוף סעיף 15.9.
- **סוג**: Class Diagram (UML), רמת package.
- **תיאור מפורט**: 8 חבילות (modules) של ה-Engine כתיבות
  מלבניות: `api_server`, `download_manager`, `piece_manager`,
  `peer_connection`, `tracker_client`, `torrent_metadata`,
  `bencode`, `security`. חצים `<<uses>>` מסומנים בקו מקווקו
  עם ראש פתוח:
  - `api_server` → `download_manager` (import + calls)
  - `download_manager` → `piece_manager`, `peer_connection`,
    `tracker_client`, `security`, `torrent_metadata`
  - `peer_connection` → (none, רק stdlib)
  - `piece_manager` → `hashlib` (stdlib)
  - `tracker_client` → `bencode`, `aiohttp`
  - `torrent_metadata` → `bencode`
  - `security` → (stdlib)
  - `api_server` → `flask`, `sqlite3`
  בכל תיבת חבילה: שמות המחלקות החשובות בתוכה (כאות אבן 8pt).
- **סטטוס**: דרוש.

---

## Fig-14 – Class Diagram (GUI, package level)

- **פרק**: 15 — סעיף 15.9.
- **מיקום בקובץ**: `15-uml-use-cases.md`, בסוף סעיף 15.9.
- **סוג**: Class Diagram (UML), רמת package.
- **תיאור מפורט**: 3 מחלקות הראשיות של ה-GUI כתיבות מלבניות
  מפורטות:
  - `TorrentClientGUI extends JFrame` — שדות עיקריים
    (`apiService`, `tableModel`, `downloadTable`, `logArea`,
    `scheduler`, `logSeqTracker`), מתודות עיקריות
    (`startStatusUpdater`, `refreshStatus`, `updateTable`,
    `onAddTorrent`, `onPause/Resume/Cancel`, `onShowHistory`,
    `onShowStats`).
  - `ApiService` — שדה `baseUrl`, `HttpClient`, מתודות
    (`startDownload`, `getStatus()`, `getStatus(id)`,
    `pause/resume/cancel`, `getHistory`, `clearHistory`,
    `getAlgorithmStats`, `getStatsSummary`, `getEvents`,
    `getLogs`, `isServerAvailable`). מחלקות מקוננות:
    `TorrentStatus`, `ApiException`.
  - `AlgorithmStatsDialog extends JDialog` — שדות
    (`apiService`, `torrentId`), מחלקה מקוננת `BarChartPanel
    extends JPanel`.
  חצים: `TorrentClientGUI` ◇──► `ApiService` (composition),
  `TorrentClientGUI` ──► `AlgorithmStatsDialog` (creates),
  `AlgorithmStatsDialog` ──► `ApiService` (uses).
- **סטטוס**: דרוש.

---

## Fig-15 – Design Class Diagram

- **פרק**: 15 — סעיף 15.10.
- **מיקום בקובץ**: `15-uml-use-cases.md`, בסוף סעיף 15.10.
- **סוג**: Design Class Diagram (DCD) מפורט.
- **תיאור מפורט**: ארבע מחלקות מרכזיות עם **כל החתימות
  המלאות** (תפקיד + פרמטרים + טיפוסי החזרה):
  - `Download` — שדות פרטיים וציבוריים מלאים (id, state,
    piece_algorithm, peer_algorithm, piece_manager, security,
    stats, _connections, _executor, _main_task, _choke_task,
    _keep_alive_task, _on_progress/complete/state_change);
    מתודות (`async start/pause/resume/cancel`, `get_status`,
    `get_logs`, `on_progress/complete/state_change`,
    `_download_loop`, `_request_pieces`, `_choke_loop`,
    `_keep_alive_loop`, `_tit_for_tat_unchoke`,
    `_round_robin_unchoke`, `_on_peer_message`,
    `_save_state`).
  - `PieceManager` — שדות (num_pieces, piece_length, total_size,
    pieces, _peer_frequency, _peer_pieces, rarest_selections,
    _piece_start_times, _lock); מתודות
    (`select_piece_rarest_first`, `select_piece_random`,
    `update_peer_have`, `update_peer_pieces`, `remove_peer`,
    `start_piece`, `submit_block`, `verify_piece`,
    `reset_stale_pieces`, `get_our_bitfield`).
  - `PeerConnection` — שדות (ip, port, info_hash, our_peer_id,
    num_pieces, _reader, _writer, _connected, _handshake_complete,
    am_choking, am_interested, peer_choking, peer_interested,
    peer_pieces, bytes_downloaded, download_rate); מתודות
    (`async connect`, `_send_handshake`, `_receive_handshake`,
    `start_message_loop`, `_message_loop`, `_read_message`,
    `_handle_message`, `send_interested/not_interested/
    choke/unchoke/have/bitfield/request/piece`, `disconnect`).
  - `SecurityManager` — שדות (_peer_reputations, _banned_peers,
    _events, _event_callbacks); מתודות (`verify_piece`,
    `report_hash_failure/successful_piece/protocol_violation/
    invalid_message/timeout`, `validate_message_length`,
    `validate_piece_index`, `is_peer_banned`, `get_peer_reputation`,
    `get_recent_events`, `on_event`, `_ban_peer`, `_log_event`).
  מתחת לכל מחלקה: חיצי composition (◆──) ל-Piece, Block,
  PeerReputation בהתאמה.
- **סטטוס**: דרוש.

---

## Fig-16 – Full Class Diagram (כל המערכת)

- **פרק**: 15 — סעיף 15.11.
- **מיקום בקובץ**: `15-uml-use-cases.md`, בסוף סעיף 15.11.
- **סוג**: Class Diagram (UML), כל המערכת.
- **תיאור מפורט**: תרשים על פני שני עמודים A3 (אנכי) המציג
  את **כל המחלקות** מ-Python ומ-Java באותו מקום, מחולק לשני
  swimlanes אופקיים:
  - **Swimlane עליון** — `Python Engine`. מציג את 15
    המחלקות: `DownloadManager`, `Download`, `DownloadStats`,
    `DownloadState (enum)`, `AlgorithmType (enum)`,
    `PieceManager`, `Piece`, `Block`, `PieceStatus (enum)`,
    `PeerConnection`, `PeerMessage`, `MessageType (enum)`,
    `TrackerClient`, `Peer`, `TrackerResponse`,
    `TorrentMetadata`, `FileInfo`, `SecurityManager`,
    `PeerReputation`, `SecurityEvent`.
  - **Swimlane תחתון** — `Java GUI`. מציג את 3 המחלקות
    הראשיות ושתי המקוננות: `TorrentClientGUI`, `ApiService`,
    `AlgorithmStatsDialog`, `TorrentStatus` (nested),
    `BarChartPanel` (nested), `ApiException` (nested).
  - **גשר בין שני ה-swimlanes**: חץ עבה אופקי עם תווית
    `HTTP/JSON REST` המקשר את `ApiService` ל-`Flask routes`
    ב-`api_server`.
  - **חיצים**:
    - composition (יהלום מלא): `Download` ◆── `PieceManager`,
      `SecurityManager`, `DownloadStats`, `ThreadPoolExecutor`.
    - aggregation (יהלום ריק): `Download` ◇── `TrackerClient`,
      `_connections: Map<str, PeerConnection>`.
    - inheritance (משולש): `TorrentClientGUI` ──▷ `JFrame`,
      `AlgorithmStatsDialog` ──▷ `JDialog`, `BarChartPanel`
      ──▷ `JPanel`, וכל ה-Errors ──▷ `Exception`.
- **סטטוס**: דרוש.

---

## Fig-17 – Screen Flow Diagram

- **פרק**: 16 — סעיף 16.2 / 16.3.
- **מיקום בקובץ**: `16-screen-flow.md`, בסוף סעיף 16.3
  (אחרי הקיבוצים הלוגיים).
- **סוג**: Screen Flow Diagram (UML-flavored).
- **תיאור מפורט**: 9 צמתים מלבניים המייצגים את 9 המסכים
  (S1–S9 כפי שמופיעים בטבלת 16.1), עם תוויות שם, מזהה, וסוג
  (`JFrame`/`JFileChooser`/`JOptionPane`/`JDialog`). חצים
  מתויגים מציגים את כל המעברים מ-16.2.2:
  - **חצי משתמש** (כחולים, מלאים): S1→S2, S2→S3, S3→S1,
    S1→S4, S1→S5, S5→S6, S6→S5, S5→S1, S1→S7, S7→S6,
    S7→S1.
  - **חצי מערכת** (אדומים, מקווקווים): ⚙→S8 (completion),
    כל מסך→S9 (error).
  - **חצי "Cancel/חזרה"** (אפורים, דקים): S2→S1 (cancel
    בפיקר), S3→S1, S4→S1 (No), S6→S5/S7 (No).
  - תווית על כל חץ עם הטריגר: שם הכפתור / שם ההחלטה
    (`"Add Torrent"`, `"YES"`, `"Cancel button"`, וכו').
  - מסגרת כתומה דקה מסביב ל-S5+S7 לסימון שהם non-modal;
    מסגרת אפורה רגילה לשאר ה-modals.
- **סטטוס**: דרוש.

---

## Fig-18 – Screenshot: Main Window (S1)

- **פרק**: 17 — סעיף 17.1.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.1.3.
- **סוג**: צילום מסך.
- **תיאור מפורט**: צילום של החלון הראשי במצב טיפוסי —
  שלוש שורות בטבלה: (1) `ubuntu-22.04.iso` במצב `Running`
  עם `JProgressBar` ב-~60%, מהירות `1.2 MB/s`, 18 peers;
  (2) `debian-12.iso` במצב `Paused` עם progress 100% מוצג
  בצבע אחר, מהירות `0 B/s`; (3) `archlinux-2024.iso` במצב
  `Completed` עם progress 100% מלא. ה-toolbar מציג את 6
  הכפתורים + שני ה-combos עם ערכים נראים (`Rarest First`,
  `Tit-for-Tat`). אזור הלוג בתחתית מציג 5–8 שורות אחרונות
  של אירועים (`Connected to peer …`, `Piece 1024 verified
  OK`, וכו'). השורה התחתונה: `Status: Ready`.
- **סטטוס**: דרוש.

---

## Fig-19 – Screenshot: Select Torrent File (S2)

- **פרק**: 17 — סעיף 17.2.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.2.3.
- **סוג**: צילום מסך.
- **תיאור מפורט**: `JFileChooser` עם כותרת `"Select Torrent
  File"`, ניווט בתיקייה שמכילה מספר קבצי `.torrent` לדוגמה.
  ה-dropdown של מסנן הקבצים מציג `"Torrent Files (*.torrent)"`
  כפעיל.
- **סטטוס**: דרוש.

---

## Fig-20 – Screenshot: Choose Download Location (S3)

- **פרק**: 17 — סעיף 17.3.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.3.3.
- **סוג**: צילום מסך.
- **תיאור מפורט**: `JFileChooser` עם כותרת `"Choose Download
  Location"`, מצב DIRECTORIES_ONLY (קבצים לא מוצגים, רק
  תיקיות). ה-dropdown מציג `"Directories"` ולא ניתן לבחור
  All Files.
- **סטטוס**: דרוש.

---

## Fig-21 – Screenshot: Confirm Cancel (S4)

- **פרק**: 17 — סעיף 17.4.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.4.3.
- **סוג**: צילום מסך.
- **תיאור מפורט**: `JOptionPane.showConfirmDialog` קטן עם
  אייקון השאלה הסטנדרטי של Swing, כותרת `"Confirm Cancel"`,
  הודעה `"Are you sure you want to cancel this download?"`,
  ושני כפתורים `Yes` ו-`No`.
- **סטטוס**: דרוש.

---

## Fig-22 – Screenshot: Download History (S5)

- **פרק**: 17 — סעיף 17.5.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.5.3.
- **סוג**: צילום מסך.
- **תיאור מפורט**: `JDialog` בגודל 820×380 עם הכותרת
  `"Download History"`. ה-`JTable` מציג 4–5 שורות הורדות
  שהסתיימו עם 9 העמודות: Name, Size, Status, Avg Speed,
  Peak Speed, Time, Piece Algo, Peer Algo, Choke Cycles.
  בתחתית: שני כפתורים — `Clear History` ו-`Close`.
  הערכים אמיתיים: שם torrent, גודל בפורמט קריא (`4.0 GB`,
  `2.1 GB`), סטטוס (`Completed`/`Cancelled`), מהירויות
  (`1.5 MB/s`), זמן בפורמט `XX:YY:ZZ`, אלגוריתמים בפורמט
  ידידותי (`Rarest First`, `Tit-for-Tat`).
- **סטטוס**: דרוש.

---

## Fig-23 – Screenshot: Confirm Clear History (S6)

- **פרק**: 17 — סעיף 17.6.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.6.3.
- **סוג**: צילום מסך.
- **תיאור מפורט**: `JOptionPane.showConfirmDialog` קטן עם
  אייקון שאלה, כותרת `"Confirm"`, הודעה `"Clear all download
  history?"`, וכפתורי `Yes`/`No`.
- **סטטוס**: דרוש.

---

## Fig-24 – Screenshots: Algorithm Statistics (S7)

- **פרק**: 17 — סעיף 17.7.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.7.3.
- **סוג**: שני צילומי מסך (Tab 1 ו-Tab 2).
- **תיאור מפורט**:
  - **Tab 1: "Piece Selection (Rarest-First)"** — חלק עליון:
    `JComboBox` עם torrent נבחר + כפתור `Refresh`. אמצע:
    bar chart שמצויר ב-Java2D ב-`BarChartPanel`, מציג ~15–30
    עמודות אופקיות, ציר X = piece index, ציר Y = מספר פעמים
    שנבחר כ-rarest. עמודות בצבע כחול עם תוויות מספריות
    מעליהן. תחתית: `summaryLabel` עם טקסט כמו `"Total
    pieces: 1024, total rarest selections: 837, average:
    0.82 per piece"`.
  - **Tab 2: "General Statistics"** — שורה עליונה: שני
    כפתורים `Refresh` ו-`Clear History`. גוף: 9 שדות מידע
    בעמודה אנכית, כל אחד בפורמט `<NAME>:  <VALUE>` עם
    הערכים האמיתיים:
      Total Files Downloaded: 12
      Total Data Downloaded: 18.4 GB
      Total Download Time: 02:14:37
      Average Download Speed: 1.4 MB/s
      Best Peak Speed: 3.2 MB/s
      Total Peers Connected: 312
      Total Choke/Unchoke Cycles: 1,847
      Largest File: ubuntu-22.04.iso (4.0 GB)
      Fastest Download: archlinux-2024.iso (8 min)
- **סטטוס**: דרוש.

---

## Fig-25 – Screenshot: Download Complete Popup (S8)

- **פרק**: 17 — סעיף 17.8.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.8.3.
- **סוג**: צילום מסך.
- **תיאור מפורט**: `JOptionPane.showMessageDialog` בסוג
  `INFORMATION_MESSAGE` עם אייקון "i" של Swing, כותרת
  `"Download Complete"`, הודעה דו-שורית: `"ubuntu-22.04.iso\n
  Saved to: /home/user/Downloads/ubuntu-22.04.iso"`, כפתור
  `OK` יחיד.
- **סטטוס**: דרוש.

---

## Fig-26 – Screenshot: Error Popup (S9)

- **פרק**: 17 — סעיף 17.9.3.
- **מיקום בקובץ**: `17-screens.md`, בסוף סעיף 17.9.3.
- **סוג**: צילום מסך.
- **תיאור מפורט**: `JOptionPane.showMessageDialog` בסוג
  `ERROR_MESSAGE` עם אייקון "X" אדום של Swing, כותרת
  `"Error"`, הודעה דו-שורית: `"Failed to start download:\n
  Invalid torrent file: Missing 'announce' field"`, כפתור
  `OK` יחיד.
- **סטטוס**: דרוש.

---

## Fig-27 – Mockup of Main Window with UX Annotations

- **פרק**: 20 — סעיף 20.2.
- **מיקום בקובץ**: `20-user-interface.md`, בסוף סעיף 20.2.
- **סוג**: סקיצת mockup (wireframe) של S1, עם תוויות UX.
- **תיאור מפורט**: סקיצה סכמטית של החלון הראשי בגודל 900×600,
  עם **קווי הנחיה** המסמנים את ארבעת אזורי ה-UI ועם
  callouts (חיצים+תוויות) המסבירים את התפקיד של כל אזור:
  - **אזור 1 — Toolbar (North)**: callout עם תווית
    `"Actions toolbar (always visible)"` ופירוט: Add
    Torrent / Pause / Resume / Cancel / History /
    Statistics + 2 Combos.
  - **אזור 2 — Downloads Table (Center top, 70%)**: callout
    `"Live downloads with auto-refresh every 500ms"`. סימון
    של ה-`JProgressBar` בעמודה Progress בצבע שמתחלף
    מ-כחול לירוק עם השלמה.
  - **אזור 3 — Event Log (Center bottom, 30%)**: callout
    `"Real-time events from GUI and Engine ([engine] prefix)"`.
  - **אזור 4 — Status Bar (South)**: callout
    `"Non-blocking status"`. דוגמת תוכן: `"5 downloads
    (3 active)"`.
  - **חצים חיצוניים** המראים: ה-Combos זורמים ל-`POST
    /torrents`, ה-table polling זורם ל-`GET /torrents`,
    ה-Event Log polling זורם ל-`GET /torrents/<id>/logs`.
- **סטטוס**: דרוש.

---

## Fig-28 – ERD (Entity-Relationship Diagram) של מסד הנתונים

- **פרק**: 22 — סעיף 22.2.
- **מיקום בקובץ**: `22-database.md`, בסוף סעיף 22.2.
- **סוג**: ERD (Crow's Foot notation).
- **תיאור מפורט**: 4 ישויות (טבלאות) במלבנים מעוגלים, עם
  קשרי 1:N:
  - **`torrents`** במרכז העליון — מציינים את כל השדות
    (id PK, info_hash, name, size, started_at, completed_at,
    total_time_seconds, final_status, piece_algorithm,
    peer_algorithm). PK מסומן במפתח קטן.
  - **`performance_stats`** בצד ימין-תחתון — שדות (id PK,
    torrent_id FK, avg_speed, peak_speed, avg_peers,
    choke_cycles). FK מסומן בחץ דק.
  - **`algorithm_stats`** בצד שמאל-תחתון — שדות (id PK,
    torrent_id FK, piece_index, selected_as_rarest,
    choke_count, unchoke_count).
  - **`events`** מתחת ל-torrents — שדות (id PK, torrent_id
    FK, timestamp, event_type, description).
  - **קשרים** (Crow's Foot):
    - `torrents` 1───< `performance_stats` (1:N, אופציונלי).
    - `torrents` 1───< `algorithm_stats` (1:N).
    - `torrents` 1───< `events` (1:N, אופציונלי).
  - **תווית קשר**: `"has stats"`, `"has piece stats"`,
    `"has events"`.
- **סטטוס**: דרוש.

---

## Fig-29 – DSD (Data Structure Diagram) של 4 הטבלאות

- **פרק**: 22 — סעיף 22.2.
- **מיקום בקובץ**: `22-database.md`, בסוף סעיף 22.2.
- **סוג**: DSD — תרשים מפורט של מבנה הטבלה (column-level).
- **תיאור מפורט**: 4 טבלאות כמלבנים, כל אחת מציגה את
  עמודותיה בעמודה אחת, עם **שלוש קטגוריות מסומנות בצבע**:
  - **PK** (Primary Key) — רקע כחול בהיר + מפתח קטן.
  - **FK** (Foreign Key) — רקע צהוב בהיר + חץ קטן.
  - **רגיל** — לבן.
  לכל עמודה מצוין הטיפוס (`TEXT`, `INTEGER`, `REAL`,
  `DATETIME`) ומגבלות (`NOT NULL`, `DEFAULT ...`,
  `AUTOINCREMENT`).
  פריסה: `torrents` בצד שמאל; שלוש הטבלאות הקשורות (perfornance,
  algorithm, events) בצד ימין, עם חצים אופקיים המראים את
  ה-FK references.
- **סטטוס**: דרוש.

---

## Fig-30 – גרף השוואת אלגוריתמים (אחרי ניסויים)

- **פרק**: 24 — סעיף 24.2.6.
- **מיקום בקובץ**: `24-testing-evaluation.md`, בסוף סעיף
  24.2.6.
- **סוג**: Bar chart with error bars (matplotlib/Excel).
- **תיאור מפורט**: גרף עמודות זוגי המשווה את שתי התצורות
  על פני 5 KPIs קריטיים:
  - **ציר X**: 5 KPIs — Total Time, Avg Speed, Peak Speed,
    Avg Peers, Choke Cycles.
  - **לכל KPI שני עמודות צמודות**: כחול = תצורה A
    (rarest_first + tit_for_tat), אפור = תצורה B (random +
    round_robin).
  - **גובה העמודה** = ממוצע של 5 ההרצות.
  - **Error bars** = ± סטיית תקן.
  - **כוכבית** (*) מעל זוגות שבהם ה-t-test מצביע על מובהקות
    סטטיסטית (p < 0.05).
  - **מקרא** בצד ימין למעלה.
- **סטטוס**: דרוש (אחרי שיבוצעו הניסויים).

---

<!-- פריטים נוספים יתווספו עם התקדמות כתיבת הפרקים -->
