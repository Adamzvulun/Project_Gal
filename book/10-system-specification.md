# 10. אפיון המערכת שהוגדרה / מוצעת

## 10.1 ניתוח דרישות המערכת

**דרישות פונקציונליות**:

- F1. המערכת מקבלת קובץ `.torrent` מהמשתמש ומתחילה הורדה
  למחשב המקומי.
- F2. המערכת מתקשרת עם tracker בפרוטוקול HTTP/HTTPS לקבלת
  רשימת peers.
- F3. המערכת יוצרת חיבורי TCP ל-peers ומבצעת עמם handshake
  של BEP-3.
- F4. המערכת בוחרת piece הבא להוריד באלגוריתם בר-בחירה
  (rarest-first או random).
- F5. המערכת מאמתת כל piece שמתקבל ע"י SHA-1 לפני כתיבה
  לדיסק.
- F6. המערכת מנהלת choke/unchoke ל-peers באלגוריתם
  בר-בחירה (Tit-for-Tat או round-robin).
- F7. המערכת מציגה את התקדמות ההורדה ב-GUI עם מהירות,
  אחוז, ומספר peers.
- F8. המערכת מאפשרת השהיה, חידוש, וביטול של הורדות.
- F9. המערכת שומרת היסטוריה וסטטיסטיקות ב-SQLite.
- F10. המערכת מציגה גרפים של בחירות rarest-first
  וסטטיסטיקות מצרפיות.

**דרישות לא-פונקציונליות**:

- N1. **ביצועים**: ניצולת CPU < 10% בעת הורדה של 1MB/s.
- N2. **רספונסיביות**: ה-GUI לא נחסם בעת קריאות API ארוכות.
- N3. **אבטחה**: peers שנשלחים pieces פגומים נחסמים אחרי
  3 כשלים.
- N4. **תאימות OS**: רץ על Linux, macOS, ו-Windows.
- N5. **קוד**: PEP 8 + type hints + 150+ unit tests.
- N6. **תיעוד**: ספר פרויקט מלא + README + סקריפטי הפעלה
  אוטומטיים.

## 10.2 מודול המערכת

המערכת מורכבת משני תהליכי OS:

**תהליך 1 — Python Engine** (process 1, port 5000):
- `api_server.py` — Flask routes + SQLite + bridge
- `download_manager.py` — Download class + algorithms
- `piece_manager.py` — Piece tracking + selection
- `peer_connection.py` — TCP per peer + state machine
- `tracker_client.py` — HTTP/HTTPS tracker
- `torrent_metadata.py` — `.torrent` parsing
- `bencode.py` — encoder/decoder
- `security.py` — אבטחה ומוניטין peers

**תהליך 2 — Java GUI**:
- `TorrentClientGUI.java` — JFrame ראשי
- `ApiService.java` — HTTP client ל-Engine
- `AlgorithmStatsDialog.java` — JDialog לסטטיסטיקות

## 10.3 אפיון פונקציונלי

הזרימה הראשית: המשתמש לוחץ "Add Torrent" → ה-GUI שולח
`POST /torrents` → ה-Engine מאתחל `TorrentMetadata`,
יוצר `Download`, פונה ל-tracker, ומתחיל לבחור pieces
מ-peers שב-swarm. כל piece שעובר אימות SHA-1 נכתב לדיסק.
ה-GUI מבצע polling כל 500ms ומציג את הסטטוס בטבלה.

זרימת ההשהיה: המשתמש לוחץ "Pause" → `POST /torrents/<id>/pause`
→ ה-state עובר ל-`Paused`, חיבורי peers נסגרים, וה-state
נשמר ב-JSON. ב-Resume המנגנון מופעל מחדש.

זרימת ביטול: דורש אישור (`JOptionPane`). שולח
`event=stopped` ל-tracker, מסמן `Cancelled`, שומר ל-SQLite.

## 10.4 ביצועים עיקריים

- **קצב הורדה תיאורטי**: עד ניצולת מלאה של ה-bandwidth
  היוצא של ה-peers ב-swarm. ב-swarm פעיל עם 50 peers
  המערכת מגיעה ל-5–10 MB/s.
- **קונקורנציה**: עד 50 חיבורי TCP בו-זמנית
  (`MAX_CONNECTIONS=50`).
- **חישוב SHA-1**: ~500 MB/s במעבד מודרני; רץ ב-
  `ThreadPoolExecutor(max_workers=2)` כדי לא לחסום את
  ה-event loop.
- **polling latency**: ה-GUI רואה את ה-state החדש תוך
  ≤ 500ms (בקצב ה-`ScheduledExecutorService`).

## 10.5 אילוצים

- **אין מימוש listen server**: המערכת רק יוזמת חיבורים
  יוצאים, לא מקבלת חיבורים נכנסים. מגביל את התרומה
  ל-swarm. תיקון מתוכנן בפרק 26 (NAT traversal).
- **אין הצפנה ב-peer wire protocol**: אין MSE/PE.
  ערוץ ה-peers הוא TCP גולמי. ניתן ל-ISP לזהות תעבורת
  BitTorrent דרך DPI. תיקון מתוכנן בפרק 26.
- **רק BEP-3 (BitTorrent v1)**: לא תומך ב-BEP-52
  (v2 עם SHA-256 ו-Merkle Trees). תיקון מתוכנן בפרק 26.
- **רק IPv4**: parsing compact peer הוא 6 בתים לכל peer
  (4 בתים IP + 2 בתים port). תמיכה ב-IPv6 (BEP-7,
  compact6 = 18 בתים) מתוכננת.
- **שחזור אוטומטי אחרי crash לא ממומש**: `_save_state`
  כותב את ה-state ב-JSON, אבל אין `_load_state` בעת
  startup.
