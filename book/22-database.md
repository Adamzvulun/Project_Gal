# פרק 22 – תיאור מסד הנתונים

## פתיח

פרק זה מתאר את **שכבת הפרזיסטנציה** של המערכת — מבנה הנתונים
שנשמר על דיסק לטווח ארוך. בהתאם לסעיף 22 בנוהל ההגשה (עמ' 12)
מוצגים: תרשים DSD, תרשים ERD, סכמה כללית, ו**לכל טבלה**:
רשימת עמודות, תפקיד כל עמודה (PK/FK), טיפוס נתונים, חובה
או null, ותכונות נוספות.

המערכת משתמשת בשני סוגי אחסון מתמשך:

- **SQLite** (`data/history.db`) — היסטוריה, סטטיסטיקות,
  אירועים. **מסד נתונים יחסי קלאסי**. 4 טבלאות.
- **JSON state files** (`data/state/<id>.json`) — מצב
  ההורדות לשחזור אחרי סגירה. **לא DB יחסי, אלא serialization
  פר-הורדה.** נדון בקצרה בסעיף 22.5.

---

## 22.1 בחירת SQLite כ-DBMS

לפני הצגת הסכמה, ההצדקה לבחירה:

| שיקול | SQLite | חלופות (PostgreSQL/MySQL) |
|---|---|---|
| התקנה | אפס — `import sqlite3` בליבת Python | דורש server נפרד |
| תאימות מערכת הפעלה | אוניברסלי | תלוי package manager |
| מקביליות נדרשת | נמוכה (kostr קטן של כתיבות) | תומך עומסים גדולים |
| גודל data צפוי | < 1MB ל-1,000 הורדות | gigabytes |
| גיבוי | העתקת קובץ יחיד | dump utilities |
| **התאמה לפרויקט** | **מצוינת** | overkill |

SQLite נבחר כי: (1) זה DB **embedded** — אין צורך בהתקנה
או הפעלה של server נפרד; (2) הגישה היא ב-file API
(`data/history.db`), שמתאים למודל ה-deploy של הפרויקט;
(3) ספריית `sqlite3` כלולה ב-Python stdlib — אפס תלות חיצונית.

---

## 22.2 סכמה כללית של הישויות והקשרים

המערכת מכילה **4 ישויות** (טבלאות) הקשורות זו לזו ביחסים
של **One-to-Many** סביב ישות-מפתח אחת (`torrents`):

```
┌─────────────────────┐
│      torrents       │ ◄─── ישות-מפתח (1 שורה לכל הורדה)
│  ──────────────     │
│  id (PK)            │
│  info_hash          │
│  name, size         │
│  started_at, ...    │
│  piece_algorithm    │
│  peer_algorithm     │
└──────┬──────────────┘
       │ 1
       │
       │ N (per-torrent stats / events)
       │
       ├──────────────────────┐
       │                      │
┌──────▼──────────────┐  ┌────▼─────────────────┐
│ performance_stats   │  │   algorithm_stats    │
│ ──────────────────  │  │ ──────────────────── │
│ id (PK)             │  │ id (PK)              │
│ torrent_id (FK)     │  │ torrent_id (FK)      │
│ avg_speed           │  │ piece_index          │
│ peak_speed          │  │ selected_as_rarest   │
│ avg_peers           │  │ choke_count          │
│ choke_cycles        │  │ unchoke_count        │
└─────────────────────┘  └──────────────────────┘
       │ 1
       │
       │ N (אירועי מערכת)
       │
┌──────▼──────────────┐
│       events        │
│ ──────────────────  │
│ id (PK)             │
│ torrent_id (FK)     │
│ timestamp           │
│ event_type          │
│ description         │
└─────────────────────┘
```

**הסבר הקשרים**:

- `torrents` הוא טבלת ה**מפתח** — שורה אחת לכל torrent
  שהמערכת ניהלה אי-פעם.
- `performance_stats` הוא **1:1 לוגי** עם `torrents` (אגרגציה
  סופית של ביצועים) — אך מבחינת הסכמה אין `UNIQUE` על
  `torrent_id` ולכן יכולות להיווצר רשומות מרובות אם הקוד
  קורא ל-`INSERT OR REPLACE` (אפשרי תיאורטית — לא קורה
  בפועל). ה-`save_torrent_to_db` משתמש ב-`INSERT OR
  REPLACE INTO performance_stats` מבלי לציין PK ב-WHERE,
  לכן זה נוצר מחדש.
- `algorithm_stats` הוא **1:N** — שורה אחת **לכל piece**
  בכל torrent.
- `events` הוא **1:N** — שורה אחת לכל אירוע מערכת
  (download_started, download_paused, download_completed,
  וכו').

> **תרשים נדרש (Fig-28)**: תרשים ERD ויזואלי (Entity-
> Relationship Diagram) כפי שתואר. ראה רשומה ב-`IMAGES.md`.

> **תרשים נדרש (Fig-29)**: תרשים DSD (Data Structure
> Diagram) של ארבע הטבלאות עם עמודות מודגשות
> (PK/FK/regular). ראה רשומה ב-`IMAGES.md`.

---

## 22.3 פירוט הטבלאות

### 22.3.1 טבלה 1 — `torrents`

**תפקיד**: רישום מרכזי של כל torrent שהמערכת ניהלה.

**יצירה (CREATE TABLE)** מתוך `api_server.py:init_database`:

```sql
CREATE TABLE IF NOT EXISTS torrents (
    id TEXT PRIMARY KEY,
    info_hash TEXT,
    name TEXT,
    size INTEGER,
    started_at DATETIME,
    completed_at DATETIME,
    total_time_seconds INTEGER,
    final_status TEXT
);
-- + ALTER TABLE ALTER טוריאן הוספת piece_algorithm ו-peer_algorithm:
ALTER TABLE torrents ADD COLUMN piece_algorithm TEXT
    DEFAULT 'rarest_first';
ALTER TABLE torrents ADD COLUMN peer_algorithm TEXT
    DEFAULT 'tit_for_tat';
```

**עמודות**:

| # | שם | טיפוס | תפקיד | חובה? | הערות |
|---|---|---|---|---|---|
| 1 | `id` | `TEXT` | **PK** | כן | 8 תווי hex — `str(uuid.uuid4())[:8]` |
| 2 | `info_hash` | `TEXT` | מזהה גלובלי של ה-torrent (SHA-1 hex של ה-info dict) | כן בפועל | NULL אופציונלי בסכמה |
| 3 | `name` | `TEXT` | שם הקובץ/תיקייה כפי שמופיע ב-`.torrent` | כן בפועל | NULL אופציונלי |
| 4 | `size` | `INTEGER` | גודל מצרפי בבתים | כן בפועל | up to 2^63 - 1 |
| 5 | `started_at` | `DATETIME` | זמן התחלת ההורדה (ISO 8601) | אופציונלי | מומר מ-Unix timestamp |
| 6 | `completed_at` | `DATETIME` | זמן השלמת/עצירת ההורדה (ISO 8601) | אופציונלי | NULL אם עדיין רץ |
| 7 | `total_time_seconds` | `INTEGER` | משך הורדה בשניות (`stats.elapsed_time`) | אופציונלי | 0 אם לא רלוונטי |
| 8 | `final_status` | `TEXT` | ערך אחרון של `DownloadState.value` | כן בפועל | `Completed`/`Cancelled`/`Paused`/וכו' |
| 9 | `piece_algorithm` | `TEXT` | האלגוריתם שבחר המשתמש | אופציונלי | DEFAULT `'rarest_first'` |
| 10 | `peer_algorithm` | `TEXT` | האלגוריתם שבחר המשתמש | אופציונלי | DEFAULT `'tit_for_tat'` |

**תכונות נוספות**:
- **`id` כ-PRIMARY KEY** מאפשר lookups O(log N) בעת
  `INSERT OR REPLACE INTO torrents`.
- **אין `UNIQUE` על `info_hash`** — לכן ניתן (לכאורה) לרשום
  את אותו torrent פעמיים. בפועל זה לא קורה כי `id` ייחודי
  לכל הפעלת הורדה.
- **השדות `info_hash`, `name`, `size`, `final_status`**
  ללא NOT NULL — בסכמה כן ניתן NULL, אך בפועל קוד ה-
  `save_torrent_to_db` תמיד שולח ערכים תקפים.

### 22.3.2 טבלה 2 — `performance_stats`

**תפקיד**: סטטיסטיקות ביצועים מצרפיות לכל torrent.

**יצירה**:

```sql
CREATE TABLE IF NOT EXISTS performance_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    torrent_id TEXT,
    avg_speed REAL,
    peak_speed REAL,
    avg_peers INTEGER,
    FOREIGN KEY (torrent_id) REFERENCES torrents(id)
);
-- + migration:
ALTER TABLE performance_stats ADD COLUMN choke_cycles INTEGER DEFAULT 0;
```

**עמודות**:

| # | שם | טיפוס | תפקיד | חובה? | הערות |
|---|---|---|---|---|---|
| 1 | `id` | `INTEGER` | **PK auto-increment** | כן (אוטומטי) | מזהה רשומה פנימי |
| 2 | `torrent_id` | `TEXT` | **FK → `torrents(id)`** | כן בפועל | NULL מותר טכנית |
| 3 | `avg_speed` | `REAL` | מהירות ממוצעת ב-bytes/sec | אופציונלי | מ-`stats.average_speed` |
| 4 | `peak_speed` | `REAL` | מהירות שיא ב-bytes/sec | אופציונלי | מ-`stats.peak_speed` |
| 5 | `avg_peers` | `INTEGER` | ממוצע peers מחוברים | אופציונלי | מ-`stats.connected_peers` |
| 6 | `choke_cycles` | `INTEGER` | סך פעמים שאלגוריתם ה-choke רץ | אופציונלי | DEFAULT 0; מ-`stats.choke_cycles` |

**הערה על `FOREIGN KEY`**: SQLite **לא אוכפת FOREIGN KEY**
כברירת מחדל; יש להפעיל `PRAGMA foreign_keys = ON;` בכל
חיבור. במערכת הזו, ה-PRAGMA לא מופעלת, אך הקוד שומר על
תקפות ה-FK באמצעות שמירה ראשונה ל-`torrents` ורק אחר כך
ל-`performance_stats` (ב-`save_torrent_to_db`).

### 22.3.3 טבלה 3 — `algorithm_stats`

**תפקיד**: סטטיסטיקות אלגוריתמיות **per-piece** —
כמה פעמים piece ספציפי נבחר ע"י rarest-first, וכמה
choke/unchoke התרחשו בהקשר שלו.

**יצירה**:

```sql
CREATE TABLE IF NOT EXISTS algorithm_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    torrent_id TEXT,
    piece_index INTEGER,
    selected_as_rarest INTEGER DEFAULT 0,
    choke_count INTEGER DEFAULT 0,
    unchoke_count INTEGER DEFAULT 0,
    FOREIGN KEY (torrent_id) REFERENCES torrents(id)
);
```

**עמודות**:

| # | שם | טיפוס | תפקיד | חובה? | הערות |
|---|---|---|---|---|---|
| 1 | `id` | `INTEGER` | **PK auto-increment** | כן | פנימי |
| 2 | `torrent_id` | `TEXT` | **FK → `torrents(id)`** | כן בפועל | |
| 3 | `piece_index` | `INTEGER` | אינדקס ה-piece בתוך ה-torrent | כן בפועל | 0 עד `num_pieces-1` |
| 4 | `selected_as_rarest` | `INTEGER` | מספר פעמים נבחר ע"י rarest-first | אופציונלי | DEFAULT 0 |
| 5 | `choke_count` | `INTEGER` | מספר choke cycles ב-context | אופציונלי | DEFAULT 0 |
| 6 | `unchoke_count` | `INTEGER` | מספר unchoke cycles ב-context | אופציונלי | DEFAULT 0 |

**הערה חשובה**: השדות `choke_count`/`unchoke_count` נשמרים
ברמת ה-torrent (לא באמת per-piece) — הם משוכפלים בכל שורת
piece עבור אותו torrent. זוהי **חבלה מודעת** של נורמליזציה
לטובת פשטות ה-query ב-`/algorithm-stats/<id>` שמחזיר את
כל הנתונים בקריאה אחת.

### 22.3.4 טבלה 4 — `events`

**תפקיד**: יומן אירועים מערכתי לכל torrent.

**יצירה**:

```sql
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    torrent_id TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT,
    description TEXT,
    FOREIGN KEY (torrent_id) REFERENCES torrents(id)
);
```

**עמודות**:

| # | שם | טיפוס | תפקיד | חובה? | הערות |
|---|---|---|---|---|---|
| 1 | `id` | `INTEGER` | **PK auto-increment** | כן | |
| 2 | `torrent_id` | `TEXT` | **FK → `torrents(id)`** | אופציונלי | NULL אפשרי לאירועי מערכת כלליים |
| 3 | `timestamp` | `DATETIME` | זמן האירוע | כן | DEFAULT `CURRENT_TIMESTAMP` |
| 4 | `event_type` | `TEXT` | קטגוריה | כן בפועל | `download_started`, `download_paused`, `download_resumed`, `download_cancelled`, `download_completed` |
| 5 | `description` | `TEXT` | תיאור חופשי | אופציונלי | טקסט קריא לאדם |

**הערה**: `DEFAULT CURRENT_TIMESTAMP` נכתב אוטומטית ע"י
SQLite — אין צורך לשלוח timestamp מה-Python.

---

## 22.4 שאילתות ייצוגיות (Views אינן בשימוש)

המערכת **אינה משתמשת ב-`VIEW` או `STORED PROCEDURE`** — SQLite
תומך ב-views אך לא ב-procedures. כל ה-logic מוצב ב-Python.
**שאילתות נפוצות** שמופיעות בקוד:

### 22.4.1 `GET /history` — JOIN של 2 טבלאות

```sql
SELECT t.*, p.avg_speed, p.peak_speed, p.avg_peers,
       COALESCE(p.choke_cycles, 0) AS choke_cycles
FROM torrents t
LEFT JOIN performance_stats p ON t.id = p.torrent_id
ORDER BY t.started_at DESC
```

- `LEFT JOIN` כדי לכלול torrent גם אם אין לו עדיין
  performance_stats (הורדה שלא הסתיימה).
- `COALESCE(..., 0)` כדי להחזיר 0 (לא NULL) אם
  `choke_cycles` לא קיים (גרסת DB ישנה לפני ה-migration).

### 22.4.2 `GET /stats-summary` — תת-שאילתות מצרפיות

```sql
SELECT t.id, t.name, t.piece_algorithm, t.peer_algorithm,
       t.total_time_seconds, t.size, t.final_status,
       p.avg_speed, p.peak_speed, p.avg_peers,
       COALESCE(p.choke_cycles, 0) AS choke_cycles,
       (SELECT COUNT(*) FROM algorithm_stats a
        WHERE a.torrent_id = t.id) AS piece_count,
       (SELECT SUM(a.selected_as_rarest) FROM algorithm_stats a
        WHERE a.torrent_id = t.id) AS total_rarest_selections
FROM torrents t
LEFT JOIN performance_stats p ON t.id = p.torrent_id
ORDER BY t.started_at DESC
```

**הסבר**: עבור כל torrent, מצרפים את ה-perfornance_stats
ושני סיכומים אגרגטיביים על `algorithm_stats` (COUNT ו-SUM).
שתי תת-השאילתות הן `correlated subqueries` — מותר ביעילות
ב-SQLite עבור N קטן (typically < 1,000 שורות).

### 22.4.3 שאילתת מחיקה ב-`DELETE /history`

```sql
DELETE FROM algorithm_stats;
DELETE FROM performance_stats;
DELETE FROM events;
DELETE FROM torrents;
```

ב-4 משפטים נפרדים, מסודרים **מילדים להורה** — כדי שאם
PRAGMA foreign_keys תופעל בעתיד, הסדר יישאר חוקי. נעטף
ב-`_db_lock` כדי למנוע race condition עם בקשה מקבילה.

---

## 22.5 פרזיסטנציה משלימה — JSON state files

מעבר ל-SQLite, המערכת שומרת **state runtime** של כל הורדה
פעילה כקובץ JSON ב-`data/state/<torrent_id>.json`. תפקיד
הקבצים: לאפשר שחזור מצב לאחר crash או סגירה.

**מבנה הקובץ** (מתוך `Download._save_state`):

```json
{
  "id": "a1b2c3d4",
  "info_hash": "<hex string>",
  "name": "ubuntu-22.04.iso",
  "size": 4294967296,
  "state": "Running",
  "downloaded": 1073741824,
  "uploaded": 0,
  "piece_status": ["missing", "completed", "completed", "missing", ...],
  "piece_algorithm": "rarest_first",
  "peer_algorithm": "tit_for_tat",
  "download_path": "/home/user/Downloads/ubuntu-22.04.iso",
  ...
}
```

זה **לא** מסד נתונים יחסי — זה serialization-קבוע
פר-הורדה. הסיבה לבחירה: גודל ה-`piece_status` array הוא
פוטנציאלית ב-תכוף עדכון (כל piece שהושלם), ו-SQLite פחות
מתאים ל-overwrite שלם אחיד. עם JSON, כל piece שמושלם
מפעיל `_save_state` שכותב את כל הקובץ מחדש (write-then-rename
אטומי).

---

## 22.6 סיכום הפרק

הפרק תיאר את **שכבת הפרזיסטנציה** של המערכת:

- **בחירת SQLite** מוצדקת (embedded, אפס תלות, מתאים לעומס
  הצפוי).
- **4 טבלאות** עם 26 עמודות סך הכל; קשרי 1:N סביב טבלת
  `torrents` כמפתח.
- **תיעוד מלא לכל טבלה**: עמודות, טיפוסים, תפקיד (PK/FK/
  regular), nullability, ו-defaults.
- **3 שאילתות ייצוגיות** הוצגו: JOIN בסיסי, correlated
  subqueries מצרפיות, ומחיקת cascade ידנית.
- **JSON state files** משלימים כשכבת serialization
  פר-הורדה — נפרדים מ-SQLite.
- **שני תרשימים נדרשים** (Fig-28 ERD, Fig-29 DSD) הוגדרו
  ב-`IMAGES.md`.

המערכת **אינה משתמשת ב-views או stored procedures** —
SQLite תומך ב-views אך כל הלוגיקה מוצבת ב-Python ע"י
החלטה מודעת.

הפרק הבא (פרק 23) הוא **המדריך למשתמש** — איך להתקין,
להפעיל, ולהשתמש במערכת.
