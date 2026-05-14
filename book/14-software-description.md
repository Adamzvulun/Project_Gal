# 14. תיאור התוכנה

## 14.1 פירוט API

ה-REST API חשוף ע"י Flask על `127.0.0.1:5000`. הטבלה
מסכמת את 13 ה-endpoints, פרמטרים, ופורמט תגובה.

| מתודה | Endpoint | פרמטרים | תגובה |
|---|---|---|---|
| `POST` | `/torrents` | multipart: `torrent_file` (קובץ); form/JSON: `piece_algorithm`, `peer_algorithm`, `download_dir` | 201 + `{id, name, size, num_pieces, state}` |
| `GET` | `/torrents` | — | 200 + מערך של statuses |
| `GET` | `/torrents/<id>` | path: id | 200 + status object |
| `POST` | `/torrents/<id>/pause` | path: id | 200 + `{id, state: "Paused"}` |
| `POST` | `/torrents/<id>/resume` | path: id | 200 + `{id, state: "Running"}` |
| `POST` | `/torrents/<id>/cancel` | path: id | 200 + `{id, state: "Cancelled"}` |
| `GET` | `/torrents/<id>/logs?since=N` | query: `since` | 200 + `{logs: [{seq, msg}]}` |
| `GET` | `/algorithm-stats/<id>` | path: id | 200 + מערך רשומות algorithm_stats |
| `GET` | `/stats-summary` | — | 200 + טבלת השוואה מצרפית |
| `GET` | `/history` | — | 200 + מערך torrents JOIN performance_stats |
| `DELETE` | `/history` | — | 200 + `{status: "ok"}` |
| `GET` | `/events?limit=N` | query: `limit`, `torrent_id` | 200 + מערך events |
| `GET` | `/health` | — | 200 + `{status: "ok", timestamp}` |

תגובה טיפוסית של `GET /torrents/<id>` (`Download.get_status()`):

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

`progress` מוחזר באחוזים (0–100); `state` הוא ערך
`DownloadState` enum; `download_speed` ב-bytes/sec. קודי
שגיאה: `400` לקלט פגום, `404` ל-ID לא קיים, `500` לחריגה
פנימית. כל שגיאה חוזרת כ-`{"error": "<description>"}`.

## 14.2 סביבת עבודה

### דרישות תוכנה מינימליות

| רכיב | גרסה מינימלית | סיבה |
|---|---|---|
| Python | 3.8+ | `asyncio.run`, type hints מודרני |
| JDK | 11+ | `java.net.http.HttpClient` |
| Flask | 2.3+ | תאימות `request.get_json()` |
| aiohttp | 3.8+ | תמיכה ב-asyncio |
| org.json | 20240303 | parsing JSON ב-Java |

### מערכות הפעלה נתמכות

הסקריפט `start.sh` תומך ב-Linux (apt/dnf/pacman) וב-
macOS (brew); `start.bat` תומך ב-Windows (winget). שני
הסקריפטים מתקינים אוטומטית את Python ו-JDK אם חסרים,
מקמפלים את ה-Java, ומריצים את שני התהליכים.

### דרישות חומרה

- RAM: 512 MB פנויים (מומלץ 2 GB+).
- דיסק: 100 MB לקוד + מקום ל-payload.
- מעבד: x86-64 / ARM64; מומלץ dual-core לטובת חישוב
  SHA-1 ב-thread נפרד.
- רשת: חיבור אינטרנט יציב.

### פורטים

`5000` (TCP, פנימי) ל-REST API; `6881` (TCP) מוצהר ל-
tracker (לא ממומש listen); `80`/`443` יוצא ל-tracker;
TCP דינמי יוצא ל-peers. המערכת עובדת מאחורי NAT — היא
רק יוזמת חיבורים יוצאים.

### מבנה תיקיות בזמן ריצה

```
data/
├── downloads/          הקבצים שהורדו
├── state/              <id>.json לכל הורדה פעילה
└── history.db          SQLite — היסטוריה + events
```

## 14.3 שפות תכנות

המערכת ממומשת ב-**Python 3.8+** (Engine) וב-**Java 11+**
(GUI). זוהי מימוש מפורש של דרישת המחוון: שתי שפות עם
אינטגרציה פונקציונלית + שפה מהודרת (Java).

**Python** נבחר ל-Engine כי `asyncio` הוא מודל מעולה
לעשרות חיבורי TCP מקבילים ב-event loop אחד, `hashlib`
ו-`struct` מאפשרים עבודה ישירה עם פרוטוקול בינארי כמו
Peer Wire Protocol, ו-`sqlite3` בליבה מבטל תלות חיצונית
ב-DB server. Bencode parser מומש ב-~230 שורות Python
אלגנטיות.

**Java** נבחר ל-GUI כי Swing הוא toolkit בוגר עם `JTable`,
`JProgressBar` renderer, `JDialog`, ו-`Graphics2D` — בדיוק
מה שצריך לאפליקציית BitTorrent טבלאית. `HttpClient`
(JEP 321, Java 11) הוא client HTTP מודרני עם תמיכה
ב-timeouts ו-async. `ScheduledExecutorService` מספק
תזמון יציב ל-polling. בנוסף, Java מהודרת — עונה לדרישת
המחוון מבחינה פורמלית.

**הגשר**: REST/JSON על `localhost:5000` — פרוטוקול
שפה-אגנוסטי, קל לבדיקה ב-`curl` בנפרד מה-GUI. החלופות
שנשקלו (JNI, gRPC, named pipes) נדחו: JNI מסבך deployment,
gRPC הוא overkill, ו-named pipes לא portable.
