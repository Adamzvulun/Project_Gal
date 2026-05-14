# IMAGES — רשימת תרשימים, צילומי מסך ואיורים

קובץ זה מרכז את כל התרשימים והצילומים שיש לשלב בספר
הפרויקט הסופי. כל פריט מצוין עם:

- **מס'**: מזהה ייחודי (Fig-01, Fig-02, …).
- **פרק**: הפרק והסעיף בו ישולב.
- **סוג**: תרשים זרימה / ארכיטקטורה / UML / ERD / צילום מסך.
- **תיאור**: מה התרשים מציג ואיך לבנות אותו.

---

## Fig-01 — סריקת הצעת הפרויקט החתומה

- **פרק**: 1 (הצעת הפרויקט שאושרה).
- **סוג**: סריקת מסמך (PDF / תמונה).
- **תיאור**: יש לשלב את כל עמודי ה-PDF המקורי
  `הצעת פרוייקט - אדם זבולון 329441273 V2.2.pdf` —
  דף השער, תוכן העניינים של ההצעה, ולפחות עמוד החתימות
  האחרון (עמ' 23) שעליו שלוש החתימות: סטודנט, מנחה,
  רכז מגמה.

---

## Fig-02 — תרשים ארכיטקטורה (Top-Down Level Design)

- **פרק**: 11.1.
- **סוג**: תרשים ארכיטקטורה.
- **תיאור**: תרשים בשתי רמות. ברמה העליונה: שני מלבנים
  גדולים — `Java GUI` ו-`Python Engine` — מחוברים בחץ
  דו-כיווני עם תווית `HTTP/REST localhost:5000`. מימין
  ל-`Python Engine`, שני מלבנים חיצוניים: `Tracker`
  (חץ עם תווית `HTTP/HTTPS announce`) ו-`Peers (1..N)`
  (חצים מרובים עם תווית `TCP/BEP-3`).
  ברמה התחתונה, פנים ה-`Python Engine` מפורק ל-8 מודולים:
  `Flask REST API`, `DownloadManager`, `PieceManager`,
  `PeerConnection*`, `TrackerClient`, `SecurityManager`,
  `TorrentMetadata`, ו-`Bencode`. חצים בין המודולים
  מציגים את התלויות.

---

## Fig-03 — תרשים ארכיטקטורת רשת

- **פרק**: 11.4.
- **סוג**: תרשים זרימת רשת.
- **תיאור**: שלוש שכבות תקשורת בצבעים שונים:
  - **ירוק (Local IPC)**: חץ דו-כיווני בין תיבת
    `Java GUI` לתיבת `Python Engine`, תווית
    `HTTP/JSON · localhost:5000`.
  - **כחול (HTTP Tracker)**: חץ דו-כיווני בין
    `Python Engine` לתיבה חיצונית `Tracker`, תווית
    `Bencode response · port 80/443`.
  - **כתום (Peer Wire Protocol)**: חץ מ-`Python Engine`
    היוצא לקבוצה של ~5 תיבות `Peer 1..5` (mייצגות
    את ה-swarm), תווית `TCP/BEP-3 · port 6881 + dynamic`.

---

## Fig-04 — תרשים זרימה (Flowchart) של `_download_loop`

- **פרק**: 15.1.
- **סוג**: תרשים זרימה.
- **תיאור**: שרשרת תיבות:
  Start → `Init TrackerClient` → `Announce(event='started')` →
  `Add peers to _known_peers` → `Start _choke_loop / _keep_alive_loop / start_periodic_announce` →
  `kick off _connect_to_peers` (initial) →
  כניסה ללולאה ראשית (`while not piece_manager.is_complete and state == RUNNING`):
  `reset_stale_pieces(30s)` → `_request_pieces` → `await sleep(0.1)` →
  כל 15 שניות: `_cleanup_dead_peers + _connect_to_peers` →
  `_update_speed + tracker.update_stats`.
  ביציאה: `if is_complete → _complete_download`; תמיד
  `_save_state` ב-finally.

---

## Fig-05 — Sequence Diagram: קבלת PIECE מ-peer

- **פרק**: 15.9.
- **סוג**: Sequence Diagram (UML).
- **תיאור**: ששה lifelines אנכיים: `Peer`, `PeerConnection`,
  `Download`, `PieceManager`, `SecurityManager`,
  `ThreadPoolExecutor`. הזרימה:
  1. `Peer` → `PeerConnection`: PIECE message (TCP).
  2. `PeerConnection._read_message` (length + payload).
  3. `PeerConnection._handle_message`: עדכון
     `bytes_downloaded`.
  4. `PeerConnection.on_message` → `Download._on_peer_message`.
  5. `Download` → `PieceManager.submit_block(...)`.
  6. אם piece שלם: `Download` → `ThreadPoolExecutor.submit(verify_piece)`.
  7. ענף SUCCESS: `report_successful_piece` + `_write_piece_sync` + broadcast HAVE.
  8. ענף FAIL: `report_hash_failure` → אם `should_ban` → disconnect.

---

## Fig-06 — Use Case Diagram

- **פרק**: 15.7.
- **סוג**: Use Case Diagram (UML).
- **תיאור**: מלבן גדול במרכז (גבול המערכת "BitTorrent
  Client"). בתוכו 5 ביצים אופקיות: `Add Torrent` (UC-1),
  `Pause/Resume/Cancel` (UC-2), `Show History` (UC-3),
  `Show Statistics` (UC-4), `Exchange Data with Peer` (UC-5).
  בצד שמאל אקטור `User` מחובר ל-UC-1..4. בצד ימין שני
  אקטורים-מערכת: `Tracker` (מחובר ל-UC-1 ול-UC-5) ו-
  `Peer` (מחובר ל-UC-5).

---

## Fig-07 — Class Diagram

- **פרק**: 15.11.
- **סוג**: Class Diagram (UML).
- **תיאור**: שני swimlanes אופקיים — `Python Engine`
  למעלה ו-`Java GUI` למטה. החיבור ביניהם: חץ אופקי עם
  תווית `HTTP/JSON REST`.
  ב-Python: 15 מחלקות עיקריות עם הקשרים: `DownloadManager`
  ◇──► `Download` (אגרגציה); `Download` ◆──► `PieceManager`,
  `SecurityManager`, `ThreadPoolExecutor` (קומפוזיציה);
  `Download` ◇──► `TrackerClient`, `Dict<PeerConnection>`
  (אגרגציה); `PieceManager` ◆──► `Piece` ◆──► `Block`;
  `SecurityManager` ◆──► `PeerReputation`; `PeerConnection`
  ◆──► `PeerMessage`; `TrackerClient` ──► `Peer`,
  `TrackerResponse`.
  ב-Java: `TorrentClientGUI extends JFrame` ◆──► `ApiService`,
  `AlgorithmStatsDialog`; `ApiService` ──► `TorrentStatus`
  (nested); `AlgorithmStatsDialog extends JDialog` ◆──►
  `BarChartPanel extends JPanel`.

---

## Fig-08 — Screen Flow Diagram

- **פרק**: 16.
- **סוג**: Screen Flow Diagram.
- **תיאור**: 9 צמתים מלבניים (S1–S9) עם כל המעברים
  ביניהם, מתויגים בטריגר (לחיצה על כפתור / אישור /
  אוטומטי). S1 (Main Window) במרכז; S2/S3 (file
  choosers) מימין; S4 (confirm Cancel) למעלה ימין; S5
  (History) ו-S6 (Confirm Clear) למטה ימין; S7
  (Statistics) למטה במרכז; S8 (Completion) ו-S9 (Error)
  למעלה במרכז (auto-triggered). S5 ו-S7 מסומנים במסגרת
  מקווקוות לציון non-modal.

---

## Fig-09 — צילום מסך: Main Window

- **פרק**: 17.1.
- **סוג**: צילום מסך.
- **תיאור**: צילום של החלון הראשי במצב טיפוסי — 3 הורדות
  בטבלה: אחת `Running` עם ProgressBar כחול ב-~60%,
  אחת `Paused`, אחת `Completed` עם ProgressBar ירוק.
  Toolbar עליון נראה עם כל 6 הכפתורים + 2 ה-Combos
  על ערכי ברירת המחדל. אזור הלוג בתחתית מציג 5-8 שורות
  אירועים אחרונים. שורת הסטטוס למטה: "5 downloads
  (3 active)".

---

## Fig-10 — צילום מסך: History Dialog

- **פרק**: 17.5.
- **סוג**: צילום מסך.
- **תיאור**: `JDialog` בגודל 820×380 עם הכותרת
  `Download History`. הטבלה מציגה 4–5 שורות הורדות
  שהסתיימו עם 9 העמודות (Name, Size, Status, Avg
  Speed, Peak Speed, Time, Piece Algo, Peer Algo, Choke
  Cycles). בתחתית: כפתורי `Clear History` ו-`Close`.

---

## Fig-11 — צילום מסך: Algorithm Statistics (Tab 1)

- **פרק**: 17.7.
- **סוג**: צילום מסך.
- **תיאור**: ה-`JDialog` של Algorithm Statistics, לשונית
  Piece Selection (Rarest-First). חלק עליון: ComboBox
  + Refresh. אמצע: bar chart שמצויר ב-Java2D — ~15–30
  עמודות אופקיות, ציר X = piece index, ציר Y = מספר
  בחירות כ-rarest. תחתית: `summaryLabel` עם "Total
  pieces: 1024, total rarest selections: 837".

---

## Fig-12 — צילום מסך: Algorithm Statistics (Tab 2)

- **פרק**: 17.7.
- **סוג**: צילום מסך.
- **תיאור**: לשונית General Statistics. שני כפתורים
  (`Refresh`, `Clear History`) למעלה, ו-9 שדות מצרפיים
  בגוף החלון: Total Files Downloaded, Total Data
  Downloaded, Total Download Time, Average/Best
  Download Speed, Total Peers Connected, Total
  Choke/Unchoke Cycles, Largest File, Fastest Download.

---

## Fig-13 — ERD (Entity-Relationship Diagram) של מסד הנתונים

- **פרק**: 22.
- **סוג**: ERD (Crow's Foot notation).
- **תיאור**: 4 ישויות במלבנים מעוגלים:
  - `torrents` במרכז עליון עם 10 שדות (id PK,
    info_hash, name, size, started_at, completed_at,
    total_time_seconds, final_status, piece_algorithm,
    peer_algorithm).
  - `performance_stats` מימין למטה (id PK, torrent_id
    FK, avg_speed, peak_speed, avg_peers, choke_cycles).
  - `algorithm_stats` משמאל למטה (id PK, torrent_id
    FK, piece_index, selected_as_rarest, choke_count,
    unchoke_count).
  - `events` מתחת ל-torrents (id PK, torrent_id FK,
    timestamp, event_type, description).
  קשרי 1:N מ-`torrents` לשלוש האחרות בסימון Crow's
  Foot. תוויות קשרים: "has stats", "has piece stats",
  "has events".

---
