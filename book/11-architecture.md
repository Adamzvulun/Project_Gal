# פרק 11 – תיאור הארכיטקטורה

## פתיח

פרק זה מציג את **התכן הארכיטקטוני המפורט** של המערכת — המעבר
מ"מה" המערכת עושה (פרק 10) ל"איך" היא בנויה. הפרק עוקב אחר שבעת
תתי-הסעיפים הנדרשים בנוהל: ארכיטקטורה ב-Top-Down Level Design
(11.1), תיאור הרכיבים (11.2), תהליכי מערכת ההפעלה (11.3), ארכיטקטורת
רשת (11.4), תיאור ה-API (11.5), פרוטוקולי תקשורת (11.6), ומבנה
שרת-לקוח (11.7).

בכל סעיף משולבים קטעי קוד קצרים מהקוד בפועל (10–20 שורות), עם
ציון נתיב הקובץ. קטעי קוד ארוכים מופיעים בנספח א'.

---

## 11.1 הארכיטקטורה של הפתרון המוצע — Top-Down Level Design

תכן Top-Down מוצג בארבע רמות זום, מהמופשט לקונקרטי. כל רמה מציגה
מבט עמוק יותר על המערכת.

### 11.1.1 רמה 0 — תיבה שחורה (Context Diagram)

ברמה זו המערכת היא **תיבה שחורה יחידה** המתקשרת עם שחקנים חיצוניים:

```
                                  ┌─────────────────┐
              ┌───── User ────────┤                 │
                                  │                 │
              ┌─── Tracker ───────┤  BitTorrent     │
                                  │  Distributed    │
              ┌─── Peer 1 ────────┤  File Sharing   │
                                  │  System         │
              ┌─── Peer 2 ────────┤                 │
                                  │                 │
              ┌─── Peer N ────────┤                 │
                                  └─────────────────┘
```

**שחקנים**:

- **User** — המשתמש האנושי, מתקשר דרך GUI.
- **Tracker** — שרת HTTP חיצוני, מספק רשימת peers.
- **Peers** — לקוחות BitTorrent אחרים, חליפת חלקי הקובץ.

> **תרשים נדרש (Fig-05)**: תרשים Context ברמה 0 כפי שתואר. ראה
> רשומה ב-`IMAGES.md`.

### 11.1.2 רמה 1 — שני תהליכים

ברמה זו המערכת נחלקת ל-**שני תהליכי OS נפרדים**:

```
              ┌─────────────────────────────────────┐
              │ ┌─────────────┐    ┌──────────────┐ │
   User ─────►│ │  Java GUI   │◄──►│Python Engine │◄┼──► Tracker
              │ │  (JVM)      │HTTP│  (asyncio)   │ │
              │ └─────────────┘REST└──────────────┘◄┼──► Peers
              │       Process 1       Process 2     │
              └─────────────────────────────────────┘
                       (Single Machine: localhost)
```

**מאפיינים**:

- **Java GUI** — תהליך JVM אחד; מטפל בתצוגה ובאינטראקציה.
- **Python Engine** — תהליך Python אחד; מטפל בכל הלוגיקה
  הפרוטוקולית והרשתית.
- **תקשורת מקומית** — REST/JSON דרך `localhost:5000` בלבד; אין
  חשיפה לרשת חיצונית.

### 11.1.3 רמה 2 — תת-מערכות בתוך כל תהליך

```
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│       Java GUI Process           │   │      Python Engine Process       │
│                                  │   │                                  │
│  ┌────────────────────────────┐  │   │  ┌────────────────────────────┐  │
│  │  TorrentClientGUI (Main)   │  │   │  │  Flask REST API Server     │  │
│  └────────────────────────────┘  │   │  └────────────────────────────┘  │
│  ┌──────────┐  ┌──────────────┐  │   │  ┌────────────────────────────┐  │
│  │ApiService│  │AlgorithmStats│  │◄─►│  │  DownloadManager           │  │
│  └──────────┘  │   Dialog     │  │   │  └────────────────────────────┘  │
│                └──────────────┘  │   │  ┌────────┐ ┌──────┐ ┌────────┐  │
│                                  │   │  │ Piece  │ │ Peer │ │Tracker │  │
│                                  │   │  │Manager │ │ Conn │ │ Client │  │
│                                  │   │  └────────┘ └──────┘ └────────┘  │
│                                  │   │  ┌──────────┐    ┌─────────────┐ │
│                                  │   │  │ Security │    │ TorrentMeta │ │
│                                  │   │  └──────────┘    └─────────────┘ │
│                                  │   │  ┌────────────┐    ┌──────────┐ │
│                                  │   │  │JSON state  │    │ SQLite   │ │
│                                  │   │  └────────────┘    └──────────┘ │
└──────────────────────────────────┘   └──────────────────────────────────┘
```

> **תרשים נדרש (Fig-06)**: תרשים Top-Down ברמה 2 כפי שמופיע ב-PDF
> ההצעה (עמ' 8), עם פירוט כל תת-המערכות. ראה רשומה ב-`IMAGES.md`.

### 11.1.4 רמה 3 — מחלקות פנימיות

ברמה הפנימית ביותר, כל מודול מורכב ממחלקות בודדות. הצגה מפורטת
ברמה זו מופיעה בפרק 15 (Use Cases ו-UML). דוגמה למודול `peer_connection.py`:

```
PeerConnection
├── PeerMessage         (Data class for parsed messages)
├── MessageType (Enum)  (10 message types)
├── _read_message()     (Async read with length prefix)
├── _handle_message()   (State machine logic)
├── _message_loop()     (Long-running task)
├── send_request()      (Send REQUEST message)
├── send_have()         (Send HAVE message)
└── ... (more methods)
```

---

## 11.2 תיאור הרכיבים בפתרון

תת-סעיף זה מפרט כל אחד מהרכיבים הראשיים, על פי הקטגוריה במחוון
(*"שרתי DB, שרתי תקשורת, שרת יישום, לקוח"*).

### 11.2.1 לקוח (Client) — Java GUI

- **קובץ ראשי**: `java_gui/src/TorrentClientGUI.java`
- **תפקיד**: אינטראקציה עם המשתמש; תצוגה של מצב הורדות; שליחת
  פעולות לשרת.
- **טכנולוגיה**: Java Swing.
- **תכונות מרכזיות**:
  - חלון ראשי עם טבלת הורדות (`JTable`) המוצגות בעמודות: שם
    קובץ, גודל, התקדמות (`JProgressBar` renderer), מהירות,
    peers, מצב, מיקום, מזהה.
  - Toolbar עם כפתורים: Add Torrent, Pause, Resume, Cancel,
    History, ו-ComboBox-ים לבחירת אלגוריתמים.
  - Split pane שמתחתיו `JTextArea` ללוגים בזמן אמת.
  - `ScheduledExecutorService` המבצע polling כל 500ms.
  - חלון `AlgorithmStatsDialog` מודאלי עם graphs ב-Java2D.

קטע קוד קצר המציג את הקמת ה-polling:

```java
// java_gui/src/TorrentClientGUI.java (קצור)
private void startStatusUpdater() {
    scheduler.scheduleAtFixedRate(() -> {
        try {
            SwingUtilities.invokeLater(this::refreshStatus);
        } catch (Exception e) {
            // Ignore refresh errors
        }
    }, 500, 500, TimeUnit.MILLISECONDS);
}

private void refreshStatus() {
    new Thread(() -> {
        try {
            List<ApiService.TorrentStatus> statuses = apiService.getStatus();
            SwingUtilities.invokeLater(() -> updateTable(statuses));
            for (ApiService.TorrentStatus s : statuses) {
                int since = logSeqTracker.getOrDefault(s.id, 0);
                JSONArray logs = apiService.getLogs(s.id, since);
                // ... appendLogs via SwingUtilities.invokeLater
            }
        } catch (Exception e) {
            // Server might not be running yet
        }
    }).start();
}
```

הקטע מציג את העיצוב הדו-שלבי: ה-scheduler רץ ב-EDT (דרך
`invokeLater`) ובכל טיק יוצר Thread חדש שמבצע את קריאות ה-HTTP
החוסמות, ואז חוזר ל-EDT דרך `invokeLater` כדי לעדכן את הטבלה
והלוגים.

### 11.2.2 שרת יישום (Application Server) — Python Engine

- **נקודת כניסה**: `python -m python_engine.api_server` (קריאת
  `run_server()` ב-`python_engine/api_server.py`, המאתחל את ה-DB,
  מפעיל את ה-event loop ברקע ומריץ את Flask על `127.0.0.1:5000`).
- **תפקיד**: ביצוע כל הלוגיקה של BitTorrent.
- **טכנולוגיה**: Python 3.8+ + asyncio + Flask.
- **רכיבים פנימיים** (פירוט בפרק 11.2.4):

| מודול | אחריות |
|---|---|
| `api_server.py` | חשיפת REST API |
| `download_manager.py` | תיאום הורדות |
| `piece_manager.py` | ניהול pieces ובחירת piece |
| `peer_connection.py` | חיבור TCP יחיד ל-peer |
| `tracker_client.py` | תקשורת HTTP עם tracker |
| `bencode.py` | קידוד/פענוח Bencode |
| `torrent_metadata.py` | פענוח קובץ `.torrent` |
| `security.py` | אבטחה ומוניטין peers |

### 11.2.3 שרתי תקשורת (Communication Servers)

המערכת מתקשרת עם שלושה סוגי "שרתים":

**(א) Tracker Server** (חיצוני):
- שרת HTTP/HTTPS עם endpoint `/announce`.
- המערכת היא **לקוח** מולו.
- תקשורת תיאורטית: בקשת GET עם פרמטרים, תגובה ב-Bencode.

**(ב) Peers as Servers** (חיצוני):
- כל peer הוא בו-זמנית שרת ולקוח (P2P).
- תקשורת: TCP עם Peer Wire Protocol.
- במצב הנוכחי, **המערכת מתחברת ל-peers ולא מקבלת חיבורים נכנסים**
  (אין מימוש *listen server*) — אילוץ ידוע, מוזכר בפרק 10.5.

**(ג) REST API Server** (פנימי):
- שרת Flask המקומי על `localhost:5000`.
- המערכת היא **שרת** מולו, וה-Java GUI הוא לקוח.

### 11.2.4 שרת DB (Database Server)

המערכת אינה משתמשת ב-DBMS חיצוני (לא PostgreSQL, לא MySQL). השכבה
הפרזיסטנטית מורכבת משני רכיבים:

**(א) JSON state files**:
- מיקום: `data/state/<torrent_id>.json` (`state_dir` ב-`DownloadManager`).
- שימוש: שחזור מצב לאחר סגירה.
- ניהול: `download_manager.py` — `Download._save_state()` נקרא
  בעת השלמת piece, pause ו-cancel; טעינה (כאשר תמומש בעתיד)
  תתבצע על בסיס אותו פורמט JSON.

**(ב) SQLite database**:
- מיקום: `data/history.db`.
- ניהול: `api_server.py` (`init_database()`) מכין את ה-schema
  בעת startup; שכבת ה-access מסונכרנת בעזרת `_db_lock` (mutex
  ברמת התהליך) כדי למנוע race conditions בין ה-Flask thread
  לקריאות מה-event loop.
- טבלאות:
  - `torrents` (`id`, `info_hash`, `name`, `size`, `started_at`,
    `completed_at`, `total_time_seconds`, `final_status`,
    `piece_algorithm`, `peer_algorithm`).
  - `performance_stats` (`id`, `torrent_id`, `avg_speed`,
    `peak_speed`, `avg_peers`, `choke_cycles`).
  - `algorithm_stats` (`id`, `torrent_id`, `piece_index`,
    `selected_as_rarest`, `choke_count`, `unchoke_count`).
  - `events` (`id`, `torrent_id`, `timestamp`, `event_type`,
    `description`).

קטע קוד של יצירת הסכמה:

```python
# python_engine/api_server.py (קצור)
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS torrents (
            id TEXT PRIMARY KEY,
            info_hash TEXT,
            name TEXT,
            size INTEGER,
            started_at DATETIME,
            completed_at DATETIME,
            total_time_seconds INTEGER,
            final_status TEXT
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torrent_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT,
            description TEXT,
            FOREIGN KEY (torrent_id) REFERENCES torrents(id)
        )""")
    # Migration: add algorithm columns when upgrading older DBs
    for col, col_def in [("piece_algorithm", "TEXT DEFAULT 'rarest_first'"),
                         ("peer_algorithm",  "TEXT DEFAULT 'tit_for_tat'")]:
        try:
            cursor.execute(f"ALTER TABLE torrents ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()
```

---

## 11.3 תיאור תהליכים של מערכת ההפעלה שמתבצעים בפרויקט

הפרויקט עושה שימוש מתוחכם ביכולות מערכת ההפעלה — תהליכים, חוטי
ביצוע (threads), event loops, ו-thread pools. תת-סעיף זה מפרט
את **מודל הקונקורנציה** המלא.

### 11.3.1 מודל התהליכים (Process Model)

המערכת רצה כשני תהליכי OS נפרדים:

- **Process 1: Python Engine** (PID-1).
- **Process 2: Java GUI** (PID-2).

שני התהליכים נוצרים ע"י `start.sh` / `start.bat`:

```bash
# start.sh (קצור — חלק ה-Launch בלבד)
# Launch Python API server in background
$PYTHON -m python_engine.api_server &
API_PID=$!

# Wait for the server to be ready
sleep 2

# Cleanup function — kills the engine when the GUI exits
cleanup() {
    kill $API_PID 2>/dev/null
    wait $API_PID 2>/dev/null
}
trap cleanup EXIT INT TERM

# Run Java GUI in foreground (blocks until window closes)
java -cp "java_gui/build:java_gui/lib/json.jar" TorrentClientGUI
```

### 11.3.2 מודל ה-Threading בתוך Python Engine

תהליך ה-Python אינו single-threaded. הוא מחזיק שלושה סוגי שרשורים:

**Thread 1: Flask Main Thread (+ Werkzeug worker threads)**
- שרת ה-development של Flask (Werkzeug) שמופעל ב-
  `app.run(host='127.0.0.1', port=5000)` מטפל בכל בקשה בשרשור
  עצמאי (`threaded=True` כברירת מחדל), כך שכל קריאת REST מ-
  Java GUI נחסמת רק בתוך השרשור שלה ולא חוסמת אחרות.
- הלוגיקה האסינכרונית נקראת מהשרשור הזה דרך גשר `_run_async`
  שמעביר את הקואורוטינה ל-event loop הייעודי וממתין לתוצאה.

**Thread 2: Asyncio Event Loop Thread (daemon)**
- מופעל בעת startup ב-`api_server.py`.
- מריץ `_loop.run_forever()`.
- כאן רצות כל הקואורוטינות: `_download_loop`, `_message_loop`,
  `_choke_loop`, `_keep_alive_loop`, `_periodic_announce_loop`.
- **חוק ברזל**: כל פעולה האסינכרונית מתבצעת **רק** בשרשור זה.

**Thread Pool Executor (2 workers)**
- חלק מ-`Download` ב-`download_manager.py`.
- מטפל בפעולות חוסמות: `verify_piece` (חישוב SHA-1) ו-
  `_write_piece_sync` (כתיבה לדיסק).

קטע קוד של אתחול ה-event loop ב-thread:

```python
# python_engine/api_server.py (קצור)
import asyncio, threading

_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None

def _start_event_loop():
    global _loop, _loop_thread
    if _loop is not None and _loop.is_running():
        return
    _loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    _loop_thread = threading.Thread(target=_run_loop, daemon=True)
    _loop_thread.start()

def _run_async(coro, timeout=60):
    """Bridge: call asyncio coroutine from Flask thread."""
    if _loop is None or not _loop.is_running():
        _start_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)
```

הקטע מציג את הגשר בין שני העולמות — Flask thread קורא ל-event
loop דרך `_run_async`.

### 11.3.3 מודל ה-Threading בתוך Java GUI

תהליך ה-Java מחזיק שלושה שרשורים עיקריים:

**Thread 1: Main Thread** — אתחול האפליקציה.

**Thread 2: EDT (Event Dispatch Thread של Swing)**
- אחראי על כל פעולות ה-UI.
- חוק ברזל ב-Swing: **רק EDT** משנה את ממשק המשתמש.
- כל קוד שרץ ב-thread אחר ורוצה לעדכן UI חייב לעבור דרך
  `SwingUtilities.invokeLater()`.

**Thread 3: ScheduledExecutorService**
- שרשור יחיד (`newSingleThreadScheduledExecutor`).
- מבצע polling של ה-API כל 500ms.
- ה-task המתוזמן רק מתזמן את `refreshStatus` על ה-EDT דרך
  `SwingUtilities.invokeLater`; קריאות ה-HTTP החוסמות בפועל
  מבוצעות ב-`Thread` חדש שנוצר בכל ריענון, כדי שה-EDT לא ייחסם.

### 11.3.4 מודל ה-Asyncio Event Loop

ה-event loop של asyncio הוא הלב של המערכת. הוא מריץ עשרות
קואורוטינות בו-זמנית באמצעות *cooperative multitasking*:

- **`_download_loop()`** — אחת לכל הורדה פעילה. מבצעת announce,
  מנהלת חיבורים, מבקשת בלוקים.
- **`_message_loop()`** — אחת לכל peer connection. קוראת הודעות
  בלולאה, מעבירה ל-`_handle_message()` ול-`on_message` callback.
- **`_choke_loop()`** — אחת לכל הורדה. מתעוררת כל 10 שניות
  לביצוע Tit-for-Tat.
- **`_keep_alive_loop()`** — אחת לכל הורדה. מתעוררת כל 60 שניות
  לשליחת keep-alive לכל peers.
- **`_periodic_announce_loop()`** — אחת לכל הורדה. מתעוררת
  לפי `interval` שמחזיר ה-tracker (טיפוסית 30 דקות).

עבור הורדה אחת עם 50 peers, ה-event loop מנהל ~55 קואורוטינות
פעילות בו-זמנית.

### 11.3.5 מודל ה-IPC (Inter-Process Communication)

התקשורת בין שני התהליכים מתבצעת **רק** דרך `localhost:5000`:

- אין shared memory.
- אין file descriptors משותפים.
- אין named pipes.
- TCP על loopback בלבד.

זה מבטיח: (1) בידוד שגיאות; (2) אפשרות להפריד את התהליכים על
מכונות שונות בעתיד; (3) פשטות דיבוג (`curl` יכול לבדוק את
ה-API).

---

## 11.4 ארכיטקטורת רשת

תת-סעיף זה מפרט את **רכיבי הרשת** של המערכת ואת זרימות התעבורה.

### 11.4.1 שלוש שכבות תקשורת רשתית

המערכת מקיימת שלוש שכבות תקשורת שונות:

**שכבה 1: Local IPC** (`localhost:5000`)
- בין Java GUI ל-Python Engine.
- פרוטוקול: HTTP/REST + JSON.
- אבטחה: לא נדרשת (loopback).
- קצב: עשרות בקשות בשנייה.

**שכבה 2: HTTP Tracker Protocol** (האינטרנט הציבורי)
- בין Python Engine ל-Tracker.
- פרוטוקול: HTTP/HTTPS GET.
- אבטחה: HTTPS אם נתמך ע"י ה-tracker.
- קצב: בקשה כל ~30 דקות (לפי `interval`).

**שכבה 3: Peer Wire Protocol** (האינטרנט הציבורי)
- בין Python Engine ל-Peers.
- פרוטוקול: TCP מקבוע עם הודעות מובנות לפי BEP-3.
- אבטחה: לא קיימת בגרסה זו (MSE/PE רשום כפיתוח עתידי).
- קצב: עשרות חיבורים פתוחים, כל אחד עם תעבורה משלו.

### 11.4.2 תרשים זרימת הרשת

```
┌────────┐ HTTP/JSON ┌────────┐ HTTP/Bencode ┌──────────┐
│Java GUI│◄─────────►│ Python │◄────────────►│ Tracker  │
└────────┘  :5000    │ Engine │   :80/443    └──────────┘
                     └────┬───┘
                          │ TCP (BEP-3)
                          ├────────────────►[Peer 1]
                          ├────────────────►[Peer 2]
                          ...
                          └────────────────►[Peer N]
                              (50 max)
```

> **תרשים נדרש (Fig-07)**: תרשים ארכיטקטורת רשת מפורטת כפי
> שתואר. ראה רשומה ב-`IMAGES.md`.

### 11.4.3 פורטים והגדרות רשת

| פורט | שימוש | כיוון |
|---|---|---|
| `5000` | Flask REST API (`127.0.0.1`) | נכנס מ-GUI מקומי בלבד |
| `6881` | BitTorrent peer port המוצהר ל-tracker | נכנס תיאורטי בלבד — אין מימוש *listen server* בגרסה זו |
| `80/443` | HTTP Tracker | יוצא ל-trackers |
| Dynamic | Outgoing TCP to peers | יוצא ל-peers |

### 11.4.4 התמודדות עם NAT

ברוב המקרים, ה-peer פועל מאחורי NAT (Network Address Translation).
המשמעות: ה-peer יכול **לבקש** חיבורים (לצאת) אך לא לקבל חיבורים
נכנסים בקלות. במצב NAT:

- המערכת **כן** מתחברת ל-peers אחרים → מורידה.
- המערכת **לא** מקבלת חיבורים → לא מעלה (פחות יעיל לrest of swarm).

זוהי מגבלה ידועה של BitTorrent ללא טכניקות NAT traversal (uPnP,
STUN). במערכת זו, הגישה: "תרומה ל-swarm כאשר אפשרי, גם אם
מוגבלת".

---

## 11.5 תיאור ה-API בארכיטקטורה

### 11.5.1 רשימת ה-endpoints

הטבלה הבאה מסכמת את כל endpoints של ה-REST API:

| מתודה | Endpoint | תיאור | פרמטרים |
|---|---|---|---|
| `POST` | `/torrents` | התחלת הורדה | multipart: `torrent_file`; form/JSON: `piece_algorithm`, `peer_algorithm`, `download_dir` (JSON חלופי: `torrent_path`) |
| `GET` | `/torrents` | רשימת כל ההורדות | — |
| `GET` | `/torrents/<id>` | סטטוס הורדה ספציפית | path: `id` |
| `POST` | `/torrents/<id>/pause` | עצירה | path: `id` |
| `POST` | `/torrents/<id>/resume` | חידוש | path: `id` |
| `POST` | `/torrents/<id>/cancel` | ביטול | path: `id` |
| `GET` | `/torrents/<id>/logs?since=N` | log polling | query: `since` (sequence) |
| `GET` | `/algorithm-stats/<id>` | סטטיסטיקות אלגוריתמים | path: `id` |
| `GET` | `/stats-summary` | טבלת השוואת אלגוריתמים מצרפית | — |
| `GET` | `/history` | היסטוריית הורדות | — |
| `DELETE` | `/history` | ניקוי היסטוריה | — |
| `GET` | `/events?limit=N` | אירועים | query: `limit`, `torrent_id` (אופציונלי) |
| `GET` | `/health` | בדיקת חיים | — |

### 11.5.2 פורמט תגובות

תגובה טיפוסית של `GET /torrents/<id>` (התוצאה של `Download.get_status()`):

```json
{
  "id": "a1b2c3d4",
  "name": "ubuntu-22.04.iso",
  "size": 4294967296,
  "progress": 25.0,
  "download_speed": 1048576.0,
  "upload_speed": 0.0,
  "connected_peers": 24,
  "state": "Running",
  "downloaded": 1073741824,
  "uploaded": 0,
  "elapsed_time": 142.7,
  "piece_algorithm": "rarest_first",
  "peer_algorithm": "tit_for_tat",
  "download_path": "/home/user/Downloads/ubuntu-22.04.iso"
}
```

הערה: `progress` מוחזר באחוזים (0–100) ולא כשבר; `state` הוא
ערך ה-`DownloadState` enum (`Queued`/`Running`/`Paused`/
`Completed`/`Cancelled`/`Error`); `download_speed` ו-
`upload_speed` ב-bytes/sec.

### 11.5.3 קטע קוד של endpoint

```python
# python_engine/api_server.py (קצור)
@app.route('/torrents/<torrent_id>', methods=['GET'])
def get_torrent_status(torrent_id: str):
    manager = get_manager()
    status = manager.get_download_status(torrent_id)
    if status is None:
        return jsonify({"error": "Torrent not found"}), 404
    return jsonify(status)

@app.route('/torrents/<torrent_id>/pause', methods=['POST'])
def pause_download(torrent_id: str):
    manager = get_manager()
    download = manager.get_download(torrent_id)
    if download is None:
        return jsonify({"error": "Torrent not found"}), 404
    _run_async(manager.pause_download(torrent_id))
    save_torrent_to_db(download)
    log_event_to_db(torrent_id, "download_paused", "Download paused")
    return jsonify({"id": torrent_id, "state": "Paused"})
```

הקטע מציג את הדפוס האחיד של ה-handlers: lookup דרך
`get_manager()`, גישור ל-event loop האסינכרוני דרך `_run_async`,
ופעולות לוואי (שמירה ל-DB ולוג אירועים) לפני החזרת ה-JSON.
הקטע המלא של כל ה-API ראוי לעיון בנספח א.1.

### 11.5.4 שמירת זהויות (Identity & Idempotency)

- כל torrent מקבל `id` ייחודי בן 8 תווים (UUID מקוצר).
- ה-`id` יציב לאורך כל מחזור החיים של ההורדה.
- פעולות pause/resume/cancel הן **idempotent** — קריאה כפולה
  לאותה פעולה לא משנה את התוצאה.

---

## 11.6 תיאור פרוטוקולי התקשורת

תת-סעיף זה מפרט את **שלושת הפרוטוקולים** המתקיימים במערכת.

### 11.6.1 פרוטוקול REST (פנימי)

- **שכבת תעבורה**: TCP/IP.
- **שכבת אפליקציה**: HTTP/1.1.
- **פורמט נתונים**: JSON ל-API; multipart/form-data להעלאת קובץ
  `.torrent`.
- **קודי תגובה**: 200/201 להצלחה; 400 לבקשה לא תקינה; 404 ל-ID
  לא קיים; 500 לשגיאת שרת.

### 11.6.2 HTTP Tracker Protocol (חיצוני)

- **שכבת תעבורה**: TCP/IP.
- **שכבת אפליקציה**: HTTP/1.1 או HTTPS.
- **בקשה**: GET ל-`<announce_url>?info_hash=...&peer_id=...&port=6881&uploaded=0&downloaded=0&left=N&event=started`.
- **תגובה**: Bencode dictionary.

קטע קוד של `announce`:

```python
# python_engine/tracker_client.py (קצור)
async def announce(self, event: Optional[str] = None,
                   uploaded: Optional[int] = None,
                   downloaded: Optional[int] = None,
                   left: Optional[int] = None) -> TrackerResponse:
    params = {
        'info_hash': self.info_hash,
        'peer_id': self.peer_id,
        'port': self.port,
        'uploaded': uploaded if uploaded is not None else self.uploaded,
        'downloaded': downloaded if downloaded is not None else self.downloaded,
        'left': left if left is not None else self.left,
        'compact': 1,
    }
    if event:
        params['event'] = event
    url = self._build_announce_url(params)        # URL-encoded
    session = await self._get_session()
    async with session.get(url) as resp:
        raw = await resp.read()
    decoded = bencode.decode(raw)
    return TrackerResponse(decoded)
```

### 11.6.3 Peer Wire Protocol (BEP-3, חיצוני)

- **שכבת תעבורה**: TCP/IP.
- **שכבת אפליקציה**: Custom binary protocol.
- **מבנה הודעה**:
  - Handshake: 68 בתים בדיוק.
  - יתר ההודעות: `<4-byte length><1-byte msg_id><payload>`.

קטע קוד של handshake:

```python
# python_engine/peer_connection.py (קצור)
PROTOCOL_STRING = b'BitTorrent protocol'
PROTOCOL_STRING_LEN = len(PROTOCOL_STRING)
HANDSHAKE_LEN = 1 + PROTOCOL_STRING_LEN + 8 + 20 + 20  # 68 bytes

async def _send_handshake(self):
    handshake = (
        bytes([PROTOCOL_STRING_LEN]) +
        PROTOCOL_STRING +
        b'\x00' * 8 +                # Reserved bytes
        self.info_hash +
        self.our_peer_id
    )
    self._writer.write(handshake)
    await self._writer.drain()

async def _receive_handshake(self):
    data = await asyncio.wait_for(
        self._reader.readexactly(HANDSHAKE_LEN),
        timeout=CONNECTION_TIMEOUT)
    pstrlen = data[0]
    if pstrlen != PROTOCOL_STRING_LEN:
        raise PeerConnectionError(f"Invalid protocol length: {pstrlen}")
    if data[1:1 + pstrlen] != PROTOCOL_STRING:
        raise PeerConnectionError("Invalid protocol string")
    received_info_hash = data[1 + pstrlen + 8: 1 + pstrlen + 8 + 20]
    self.remote_peer_id = data[1 + pstrlen + 8 + 20: 1 + pstrlen + 8 + 40]
    if received_info_hash != self.info_hash:
        raise PeerConnectionError("Info hash mismatch during handshake")
```

הקטע מציג את מבנה ה-handshake המדויק (68 בתים). אסור לסטות
ביט אחד — כל סטייה תוביל ל-`PeerConnectionError` ולסגירת
החיבור (בניגוד לדפוסים אחרים שמחזירים `bool`, המימוש שלנו זורק
חריגה מנומקת כדי שניתן יהיה לתעד את סיבת הכשל ב-logger).

### 11.6.4 השוואת הפרוטוקולים

| מאפיין | REST (פנימי) | HTTP Tracker | Peer Wire Protocol |
|---|---|---|---|
| שכבת תעבורה | TCP | TCP | TCP |
| פורמט | JSON | Bencode | Binary (length-prefixed) |
| Stateful? | לא | לא | כן (state machine) |
| Encryption | אופציונלי | אופציונלי (HTTPS) | לא בגרסה זו |
| תפקיד המערכת | שרת | לקוח | גם וגם |

---

## 11.7 שרת-לקוח (Client-Server)

תת-סעיף זה מפרט את **דפוסי שרת-לקוח** במערכת. ייחודיותו: המערכת
מקיימת **שני יחסי שרת-לקוח שונים** בו-זמנית.

### 11.7.1 יחס שרת-לקוח פנימי (Java ↔ Python)

ביחס הזה:

- **Java GUI** הוא **לקוח**.
- **Python Engine** הוא **שרת**.

זהו דפוס Client-Server קלאסי: הלקוח מבצע בקשות, השרת מטפל ומחזיר
תשובות. הקוד ב-`ApiService.java` מציג את הלקוח:

```java
// java_gui/src/ApiService.java (קצור)
public List<TorrentStatus> getStatus() throws IOException, ApiException {
    HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/torrents"))
            .GET()
            .build();

    HttpResponse<String> response = sendRequest(request);
    checkResponse(response, 200);

    JSONArray jsonArray = new JSONArray(response.body());
    List<TorrentStatus> statuses = new ArrayList<>();
    for (int i = 0; i < jsonArray.length(); i++) {
        statuses.add(TorrentStatus.fromJson(jsonArray.getJSONObject(i)));
    }
    return statuses;
}
```

### 11.7.2 יחסים מורכבים יותר עם peers (P2P)

מול peers, **המערכת היא בו-זמנית גם שרת וגם לקוח**:

- **כלקוח**: יוזמת חיבור TCP, שולחת `handshake`, מבקשת בלוקים.
- **כשרת**: מקבלת בקשות `request` מ-peers אחרים, שולחת בלוקים
  בחזרה (במצב מיועד — אבל בגרסה הנוכחית רק אם החיבור הופעל
  מ-direction שלנו).

זהו מאפיין יסודי של P2P: אין הבחנה קשיחה בין שרת ללקוח, אלא
**peers שווי-מעמד**.

### 11.7.3 יחסים מול tracker

מול ה-tracker, המערכת היא **רק לקוח**:

- שולחת announce requests.
- מקבלת תגובות.
- אינה מספקת שירות ל-tracker.

### 11.7.4 סיכום היחסים

| יישות מרוחקת | תפקיד המערכת | פרוטוקול |
|---|---|---|
| Java GUI (פנימי) | **שרת** | REST/HTTP |
| Tracker | **לקוח** | HTTP/HTTPS |
| Peers (BitTorrent) | **שרת+לקוח** (P2P) | TCP/BEP-3 |

המערכת ממלאת **שלושה תפקידי-תקשורת שונים בו-זמנית**. תכונה זו
דורשת עיצוב זהיר של ה-event loop: כל חיבור TCP חייב להתנהל
בקואורוטינה משלו, וה-Flask thread אינו יכול לחסום את ה-event
loop. הפתרונות לאתגרים אלה תוארו בפרקים 4.3 (קונקורנציה ו-OS).

---

## 11.8 קשרים בין הרכיבים — סיכום

הטבלה הבאה מסכמת את **כל הקשרים** במערכת:

| מ-(From) | אל-(To) | פרוטוקול | סוג קשר | תדירות |
|---|---|---|---|---|
| User | Java GUI | אינטראקציה | event-driven | לפי משתמש |
| Java GUI | ApiService | קריאת פונקציה | סינכרוני | לפי פעולה |
| ApiService | Python Engine | HTTP/REST | סינכרוני | ~30 ק/דקה |
| Python Engine (Flask) | DownloadManager | _run_async | async-bridge | לפי פעולה |
| DownloadManager | PieceManager | קריאת פונקציה | סינכרוני | תכוף |
| DownloadManager | PeerConnection | קואורוטינה | async | מתמשך |
| DownloadManager | TrackerClient | קואורוטינה | async | כל 30 דק' |
| DownloadManager | ThreadPoolExecutor | run_in_executor | async-bridge | לכל piece |
| TrackerClient | Tracker | HTTP/HTTPS | סינכרוני (async) | כל 30 דק' |
| PeerConnection | Peer | TCP/BEP-3 | סינכרוני (async) | מתמשך |
| DownloadManager | JSON state | I/O | סינכרוני | בכל שינוי |
| api_server | SQLite | I/O | סינכרוני | בכל אירוע |

---

## 11.9 סיכום הפרק

פרק זה הציג את **התכן הארכיטקטוני המפורט** של המערכת, ב-7
תת-סעיפים: Top-Down Level Design ב-4 רמות זום (Context, Two
Processes, Subsystems, Internal Classes); תיאור מפורט של 4
קטגוריות רכיבים (לקוח, שרת יישום, שרתי תקשורת, DB); מודל
מקיף של תהליכים ושרשורים כולל IPC; ארכיטקטורת רשת בשלוש שכבות
תקשורת עם פירוט פורטים ו-NAT; תיאור 13 endpoints של ה-REST API
עם דוגמאות; פירוט 3 פרוטוקולי תקשורת (REST, HTTP Tracker, Peer
Wire Protocol) עם קטעי קוד; ודיון בדפוס שרת-לקוח הכפול
שמאפיין את המערכת. הפרק נחתם בטבלת קשרים מקיפה.

הפרק הבא (פרק 12) יעמיק בנושא **אבטחת המידע** — וקטורי איום,
הגנות, אלגוריתמי hash, וטיפול ב-peers זדוניים.
