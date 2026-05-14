# 22. תיאור מסד הנתונים

המערכת משתמשת ב-**SQLite** מקומי (`data/history.db`)
לשמירת היסטוריה, סטטיסטיקות, ואירועים. בנוסף, מצב
ההורדה החי נשמר ב-JSON state files (`data/state/<id>.json`).

הבחירה ב-SQLite מוצדקת כי הפרויקט הוא embedded — אין
צורך ב-DB server נפרד; ספריית `sqlite3` כלולה ב-Python
stdlib; אפס תלות חיצונית; ומתאים לעומס שלנו (פחות
מ-1,000 רשומות צפויות).

## סכמה כללית

המסד מכיל ארבע טבלאות סביב טבלת-מפתח אחת (`torrents`):

```
                  ┌─────────────────┐
                  │     torrents    │
                  │  id PK          │
                  │  info_hash      │
                  │  name, size,    │
                  │  started_at,    │
                  │  completed_at,  │
                  │  final_status,  │
                  │  piece_algorithm,
                  │  peer_algorithm │
                  └────────┬────────┘
                           │ 1
                ┌──────────┼──────────┐
                │          │          │
                │ N        │ N        │ N
   ┌────────────▼──┐  ┌────▼─────┐ ┌──▼──────────┐
   │performance_   │  │algorithm_│ │   events    │
   │stats          │  │stats     │ │  id PK      │
   │ id PK         │  │ id PK    │ │  torrent_id │
   │ torrent_id FK │  │ torrent_ │ │  FK         │
   │ avg_speed,    │  │ id FK    │ │  timestamp, │
   │ peak_speed,   │  │ piece_   │ │  event_type,│
   │ avg_peers,    │  │ index,   │ │  description│
   │ choke_cycles  │  │ selected_│ └─────────────┘
   └───────────────┘  │ as_rar.. │
                      └──────────┘
```

הקשרים הם 1:N דרך FK (אם כי SQLite לא אוכפת FK בברירת
מחדל; הקוד שומר על תקפות שלהן בסדר שמירה).

## פירוט הטבלאות

### `torrents`

הטבלה המרכזית — שורה אחת לכל torrent שהמערכת ניהלה.

| עמודה | טיפוס | תפקיד | הערות |
|---|---|---|---|
| id | TEXT | **PK** | 8 תווי hex (UUID מקוצר) |
| info_hash | TEXT | מזהה גלובלי | SHA-1 hex של ה-info dict |
| name | TEXT | שם הקובץ | מתוך ה-`.torrent` |
| size | INTEGER | גודל מצרפי בבתים | |
| started_at | DATETIME | זמן התחלה | ISO 8601 |
| completed_at | DATETIME | זמן סיום | NULL אם רץ |
| total_time_seconds | INTEGER | משך בשניות | |
| final_status | TEXT | DownloadState value | Completed/Cancelled/Error/וכו' |
| piece_algorithm | TEXT | אלגוריתם piece | DEFAULT 'rarest_first' |
| peer_algorithm | TEXT | אלגוריתם peer | DEFAULT 'tit_for_tat' |

שתי העמודות האחרונות הוספו ב-migration עם `ALTER TABLE`.

### `performance_stats`

סטטיסטיקות ביצועים מצרפיות לכל torrent.

| עמודה | טיפוס | תפקיד |
|---|---|---|
| id | INTEGER | **PK** auto-increment |
| torrent_id | TEXT | **FK** → `torrents(id)` |
| avg_speed | REAL | מהירות ממוצעת ב-bytes/sec |
| peak_speed | REAL | מהירות שיא |
| avg_peers | INTEGER | ממוצע peers מחוברים |
| choke_cycles | INTEGER | סך פעמים שאלגוריתם ה-choke רץ |

### `algorithm_stats`

סטטיסטיקות per-piece — בעיקר התפלגות בחירות rarest-first.

| עמודה | טיפוס | תפקיד |
|---|---|---|
| id | INTEGER | **PK** auto-increment |
| torrent_id | TEXT | **FK** |
| piece_index | INTEGER | אינדקס ה-piece (0 עד num_pieces-1) |
| selected_as_rarest | INTEGER | מספר פעמים נבחר ע"י rarest-first |
| choke_count | INTEGER | choke cycles ב-context |
| unchoke_count | INTEGER | unchoke cycles ב-context |

### `events`

יומן אירועים — download_started, download_paused,
download_resumed, download_cancelled, download_completed.

| עמודה | טיפוס | תפקיד |
|---|---|---|
| id | INTEGER | **PK** auto-increment |
| torrent_id | TEXT | **FK** (NULL אפשרי לאירועים גלובליים) |
| timestamp | DATETIME | DEFAULT `CURRENT_TIMESTAMP` |
| event_type | TEXT | קטגוריה |
| description | TEXT | טקסט קריא לאדם |

## אין שימוש ב-Views או Stored Procedures

המערכת אינה משתמשת ב-`VIEW` או `STORED PROCEDURE`.
SQLite תומך ב-views אך כל הלוגיקה מוצבת ב-Python — זה
פשוט יותר לדיבוג ולשינוי.

## שאילתות מרכזיות

**`GET /history`** — JOIN של 2 טבלאות עם `LEFT JOIN`
לכלול torrents שעדיין לא נכתבו ל-performance_stats:

```sql
SELECT t.*, p.avg_speed, p.peak_speed, p.avg_peers,
       COALESCE(p.choke_cycles, 0) AS choke_cycles
FROM torrents t
LEFT JOIN performance_stats p ON t.id = p.torrent_id
ORDER BY t.started_at DESC
```

**`GET /stats-summary`** — מוסיף תת-שאילתות מצרפיות על
`algorithm_stats` (COUNT ו-SUM) כדי לקבל את ה-piece_count
ואת ה-total_rarest_selections לכל torrent בקריאה אחת.

**`DELETE /history`** — מתבצע ב-4 משפטים מסודרים
מילדים להורה (`algorithm_stats` → `performance_stats` →
`events` → `torrents`), בעטיפת `_db_lock` כדי למנוע race
מבקשה מקבילה.

## JSON state files

מעבר ל-SQLite, מצב כל הורדה פעילה נשמר ב-
`data/state/<id>.json`. תוכן: id, info_hash, name, size,
state, downloaded, uploaded, piece_status array (missing/
in_progress/completed לכל piece), אלגוריתמים, ו-
download_path.

הקבצים האלה נכתבים ע"י `Download._save_state` בכל שינוי
משמעותי (piece שהושלם, pause, cancel) דרך write-then-
rename אטומי. **תכלית עתידית**: לטעון אותם בעת startup
כדי לשחזר הורדות שנקטעו (לא ממומש בגרסה הנוכחית; מתועד
בפרק 26).
