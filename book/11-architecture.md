# 11. תיאור הארכיטקטורה

המערכת מורכבת משני תהליכי OS נפרדים שמתקשרים ביניהם דרך
loopback בלבד: **Python Engine** המבצע את כל הלוגיקה של
פרוטוקול BitTorrent, ו-**Java GUI** שמספק את ממשק המשתמש.
ההפרדה הזו אפשרה לי לבחור לכל תפקיד את השפה המתאימה ביותר
(asyncio של Python לתקשורת רשת קונקורנטית, Swing של Java
ל-UI), ולשמור על חוזה ברור ביניהם דרך REST/JSON.

## 11.1 הארכיטקטורה של הפתרון המוצע (Top-Down Level Design)

הצגתי את הארכיטקטורה בארבע רמות זום, מהמופשטת לקונקרטית.

**רמה 0 — Context Diagram**: המערכת היא תיבה שחורה
המתקשרת עם משתמש (User) דרך GUI, עם Tracker חיצוני (HTTP),
ועם N peers ב-swarm (TCP).

**רמה 1 — שני תהליכים**: בתוך גבולות המכונה המקומית, יש
שני תהליכים: `Java GUI` (תהליך JVM) שמתקשר דרך
`HTTP/REST` על `localhost:5000` עם `Python Engine` (תהליך
asyncio). ה-Engine הוא היחיד שמדבר עם הרשת החיצונית.

**רמה 2 — תת-מערכות**: בתוך ה-Engine פועלים שמונה מודולים
מרכזיים: Flask API server, `DownloadManager` (מנהל
המרכזי), `PieceManager` (ניהול pieces ובחירת piece),
`PeerConnection` (חיבור TCP יחיד ל-peer), `TrackerClient`
(תקשורת HTTP עם tracker), `Security` (אבטחה ומוניטין
peers), `TorrentMetadata` (פענוח `.torrent`), ו-`Bencode`
(encoder/decoder). מולם ב-GUI: `TorrentClientGUI` (חלון
ראשי), `ApiService` (HTTP client) ו-`AlgorithmStatsDialog`.

**רמה 3 — מחלקות פנימיות**: הרמה הזו מוצגת בפירוט בפרק 14
(UML).

## 11.2 תיאור הרכיבים בפתרון

לפי קטגוריות המחוון:

**Client (לקוח)** — `Java GUI` (Swing). הקובץ הראשי
`java_gui/src/TorrentClientGUI.java` הוא `JFrame` עם
`JTable` להורדות, toolbar עם כל הפעולות, `JTextArea`
ללוגים, ו-`ScheduledExecutorService` שמבצע polling של ה-API
כל 500ms. כל קריאה ל-API רצה ב-`Thread` נפרד כדי שה-EDT
(Event Dispatch Thread) לא ייחסם.

**Application Server (שרת יישום)** — `Python Engine` עם
Flask. נקודת הכניסה היא
`python -m python_engine.api_server`, שמאתחל את ה-SQLite,
מפעיל ב-thread יעודי את ה-event loop של asyncio, ומריץ את
Flask על `127.0.0.1:5000`.

**Communication Servers (שרתי תקשורת)** — המערכת מתקשרת
עם שני סוגי שרתים חיצוניים: HTTP Tracker (לקבלת רשימת
peers דרך announce), ו-peers ב-swarm (TCP ישיר על פי
Peer Wire Protocol של BEP-3). הפורט `6881` מוצהר ל-tracker
אך לא ממומש listen server, ולכן המערכת רק יוזמת חיבורים
יוצאים — מגבלה ידועה שמתועדת בפרק 26.

**DB Server (מסד נתונים)** — `SQLite` מקומי
(`data/history.db`) שמשמש לשמירת היסטוריית הורדות,
סטטיסטיקות אלגוריתמיות, ואירועי מערכת. במקביל, מצב ההורדה
החי נשמר ב-JSON state files תחת `data/state/<id>.json`.
פירוט הסכמה בפרק 22.

## 11.3 תיאור תהליכים של מערכת ההפעלה שמתבצעים בפרויקט

תהליך ה-Engine מחזיק שלושה סוגי thread:

- **Flask main thread + Werkzeug workers**: מטפלים בכל
  בקשת REST שמגיעה מה-GUI. Werkzeug רץ ב-`threaded=True`
  כברירת מחדל, כך שבקשות מקבילות לא נחסמות זו את זו.
- **asyncio event loop thread (daemon)**: מופעל בעת
  startup כ-`threading.Thread(target=_run_loop, daemon=True)`.
  בתוכו רצות כל הקואורוטינות של ההורדות — `_download_loop`,
  `_message_loop` של כל peer, `_choke_loop`, `_keep_alive_loop`,
  ו-`_periodic_announce_loop`. עבור הורדה אחת עם 50 peers,
  ה-event loop מנהל ~55 קואורוטינות פעילות בו-זמנית.
- **ThreadPoolExecutor (2 workers)**: מטפל בפעולות חוסמות
  בלבד — חישוב SHA-1 וכתיבה לדיסק. שני העומסים האלה
  מועברים אליו מה-event loop דרך `loop.run_in_executor`
  כדי שלא יחסמו את שאר הקואורוטינות.

הגשר בין Flask thread (שרץ סינכרונית) לבין ה-event loop
מתבצע ע"י פונקציה אחת:

```python
# python_engine/api_server.py
def _run_async(coro, timeout=60):
    """Bridge: call asyncio coroutine from Flask thread."""
    if _loop is None or not _loop.is_running():
        _start_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)
```

כל handler ב-Flask שצריך להפעיל פעולה אסינכרונית (כגון
`Download.pause()`) קורא ל-`_run_async` ומקבל את התוצאה
בחזרה כאילו זו פעולה רגילה.

תהליך ה-GUI מחזיק שני threads עיקריים: ה-EDT של Swing
(שמטפל בכל ה-rendering ובאירועי משתמש) וה-
`ScheduledExecutorService` שמתזמן את ה-polling. כל קריאת
HTTP חוסמת רצה ב-`Thread` חדש שנוצר בכל `refreshStatus`,
כדי שה-EDT לא ייחסם בזמן שהשרת איטי.

## 11.4 ארכיטקטורת הרשת

המערכת מקיימת שלוש שכבות תקשורת שונות:

1. **Local IPC** — בין Java GUI לבין Python Engine, על
   `localhost:5000` בלבד. פרוטוקול: HTTP/REST + JSON. אין
   חשיפה לרשת חיצונית, ולכן אין צורך ב-TLS.
2. **HTTP Tracker** — בין ה-Engine לבין ה-tracker, ב-HTTP
   או HTTPS לפי ה-URL בקובץ ה-`.torrent`. פורמט התגובה
   הוא Bencode. בקשה אחת כל ~30 דקות (לפי `interval` שה-
   tracker מחזיר).
3. **Peer Wire Protocol** — בין ה-Engine לבין peers,
   TCP גולמי לפי BEP-3. עשרות חיבורים פתוחים בו-זמנית,
   כל אחד עם תעבורה משלו.

טבלת הפורטים:

| פורט | שימוש | כיוון |
|---|---|---|
| `5000` | REST API (`127.0.0.1`) | נכנס מ-GUI מקומי בלבד |
| `6881` | פורט BitTorrent המוצהר ל-tracker | רק מוצהר; אין listen server |
| `80`/`443` | תקשורת ל-tracker | יוצא |
| Dynamic | חיבורי TCP ל-peers | יוצא |

המערכת **אינה מקבלת חיבורים נכנסים**. זו מגבלה של הגרסה
הנוכחית — המערכת תורמת ל-swarm רק כאשר היא יוזמת את החיבור
היוצא ה-peer בצד השני מאפשר reciprocal upload (במצב
Tit-for-Tat). שילוב NAT traversal (UPnP/STUN) ושרת listen
מתוכנן לעתיד (פרק 26).

## 11.5 תיאור ה-API בארכיטקטורה

ה-REST API חשוף ע"י Flask על `127.0.0.1:5000` ומכיל 13
endpoints:

| מתודה | Endpoint | תפקיד |
|---|---|---|
| `POST` | `/torrents` | התחלת הורדה חדשה |
| `GET` | `/torrents` | רשימת כל ההורדות |
| `GET` | `/torrents/<id>` | סטטוס הורדה ספציפית |
| `POST` | `/torrents/<id>/pause` | השהיה |
| `POST` | `/torrents/<id>/resume` | חידוש |
| `POST` | `/torrents/<id>/cancel` | ביטול |
| `GET` | `/torrents/<id>/logs?since=N` | polling של לוגים |
| `GET` | `/algorithm-stats/<id>` | סטטיסטיקות אלגוריתמיות |
| `GET` | `/stats-summary` | טבלת השוואה מצרפית |
| `GET` | `/history` | היסטוריית הורדות |
| `DELETE` | `/history` | ניקוי היסטוריה |
| `GET` | `/events?limit=N` | יומן אירועים |
| `GET` | `/health` | בדיקת חיים |

תגובה טיפוסית של `GET /torrents/<id>`:

```json
{
  "id": "a1b2c3d4", "name": "ubuntu-22.04.iso",
  "size": 4294967296, "progress": 25.0,
  "download_speed": 1048576.0, "connected_peers": 24,
  "state": "Running", "downloaded": 1073741824,
  "piece_algorithm": "rarest_first",
  "peer_algorithm": "tit_for_tat"
}
```

פירוט מלא של הפרמטרים והפלטים מופיע בפרק 17 (תיאור התוכנה).

## 11.6 תיאור פרוטוקולי התקשורת

**HTTP/REST (פנימי)**: בקשת שגרתית עם פרמטרים בפורמט
multipart/form-data (להעלאת קובץ `.torrent`) או JSON.
תגובות JSON עם קודי HTTP סטנדרטיים (200, 201, 400, 404,
500).

**HTTP Tracker Protocol**: בקשת GET ל-`announce URL` עם
פרמטרי URL (`info_hash`, `peer_id`, `port`, `uploaded`,
`downloaded`, `left`, `event`, `compact=1`). התגובה היא
Bencode עם `interval`, `peers` (במצב compact, 6 בתים לכל
peer = 4 בתים IP + 2 בתים port), `complete` ו-`incomplete`.

**Peer Wire Protocol (BEP-3)**: TCP גולמי. כל חיבור מתחיל
ב-handshake של 68 בתים: בית אחד עם אורך מחרוזת הפרוטוקול
(19), המחרוזת `"BitTorrent protocol"`, 8 בתים reserved,
ה-`info_hash` של ה-torrent (20 בתים), ו-`peer_id` (20
בתים). לאחר ה-handshake, כל הודעה מתחילה בקידומת אורך של
4 בתים, ואחריה msg_id ו-payload.

```python
# python_engine/peer_connection.py
async def _send_handshake(self):
    handshake = (
        bytes([PROTOCOL_STRING_LEN]) +
        PROTOCOL_STRING +
        b'\x00' * 8 +
        self.info_hash +
        self.our_peer_id
    )
    self._writer.write(handshake)
    await self._writer.drain()
```

הודעות הפרוטוקול: `CHOKE`, `UNCHOKE`, `INTERESTED`,
`NOT_INTERESTED`, `HAVE`, `BITFIELD`, `REQUEST`, `PIECE`,
`CANCEL`, ו-`KEEP_ALIVE` (length=0).

## 11.7 שרת-לקוח

המערכת מקיימת **שלושה יחסי שרת-לקוח שונים בו-זמנית**:

| יישות מרוחקת | תפקיד המערכת | פרוטוקול |
|---|---|---|
| Java GUI (פנימי) | **שרת** | REST/HTTP |
| Tracker | **לקוח** | HTTP/HTTPS |
| Peers ב-swarm | **שרת+לקוח** (P2P) | TCP/BEP-3 |

הריבוי הזה הוא מאפיין יסודי של P2P — אין הבחנה קשיחה
בין שרת ללקוח. כל peer הוא בו-זמנית יוזם חיבורים (כלקוח)
ומקבל בקשות (כשרת). במצב הנוכחי, מאחר שאין listen server,
המערכת רק יוזמת חיבורים, אך הצד השני יכול לבקש blocks
ממנה דרך הודעות `REQUEST` באותו חיבור.
