# פרק 14 – תיאור התוכנה

## פתיח

פרק זה מתאר את **תיאור התוכנה** ברמת ההגדרות הטכניות
האופרטיביות שלה — כפי שדורש סעיף 14 בנוהל ההגשה (עמ' 11):

- **14.1** — פירוט מלא של ה-REST API: כל אחד מ-13 ה-endpoints,
  המתודה, הפרמטרים, פורמט הבקשה, פורמט התגובה, קודי הסטטוס,
  ושגיאות אפשריות.
- **14.2** — סביבת העבודה: גרסאות תוכנה נדרשות (Python, JDK),
  מערכות הפעלה נתמכות, דרישות חומרה, דרישות רשת ופורטים,
  ותלויות שלישית (pip, lib).
- **14.3** — נימוק בחירת שפות התכנות (Python + Java), כולל
  ניתוח חלופות.

הפרק קצר במהותו וקונקרטי. הוא נשען על ה-API שתואר ארכיטקטונית
בפרק 11 (סעיף 11.5) ומפרט אותו עד לרמת הפרמטר הבודד; ועל סעיף
*"שפות תכנות"* בהצעת הפרויקט המאושרת (פרק 1).

---

## 14.1 פירוט ה-API

ה-REST API חשוף ע"י Flask על `127.0.0.1:5000`. נכון לגרסה
הנוכחית קיימים **13 endpoints**, מאורגנים בארבע קבוצות
לוגיות: ניהול הורדות, היסטוריה, אירועים וסטטיסטיקה, ותחזוקה.
כל ה-endpoints מחזירים JSON; שגיאות חוזרות בקוד HTTP ≥ 400
עם גוף `{"error": "..."}`.

### 14.1.1 קבוצה 1 — ניהול הורדות

#### `POST /torrents` — התחלת הורדה

- **תפקיד**: יוצר ומאתחל הורדה חדשה.
- **Content-Type**: `multipart/form-data` או `application/json`.
- **גוף הבקשה — `multipart/form-data`**:
  | שדה | סוג | חובה | תיאור |
  |---|---|---|---|
  | `torrent_file` | file | כן (או `torrent_path` ב-JSON) | בייטים של קובץ `.torrent` |
  | `piece_algorithm` | string | לא | `"rarest_first"` (ברירת מחדל) / `"random"` |
  | `peer_algorithm` | string | לא | `"tit_for_tat"` (ברירת מחדל) / `"round_robin"` |
  | `download_dir` | string | לא | נתיב מלא לתיקיית יעד; ברירת מחדל: `data/downloads` |
- **גוף הבקשה — `application/json`**:
  | שדה | סוג | חובה | תיאור |
  |---|---|---|---|
  | `torrent_path` | string | כן | נתיב מקומי על השרת לקובץ `.torrent` |
  | `piece_algorithm` | string | לא | כנ"ל |
  | `peer_algorithm` | string | לא | כנ"ל |
  | `download_dir` | string | לא | כנ"ל |
- **תגובה (201)**:
  ```json
  {
    "id": "a1b2c3d4",
    "name": "ubuntu-22.04.iso",
    "size": 4294967296,
    "num_pieces": 16384,
    "state": "Queued"
  }
  ```
- **שגיאות**: `400` אם אין קובץ או הקובץ פגום; `500` אם
  אירעה שגיאה פנימית.

#### `GET /torrents` — רשימת כל ההורדות הפעילות

- **פרמטרים**: אין.
- **תגובה (200)**: מערך JSON של אובייקטי סטטוס (לפי הפורמט
  של `GET /torrents/<id>` להלן).

#### `GET /torrents/<id>` — סטטוס הורדה ספציפית

- **פרמטר נתיב**: `id` (8 תווים hex).
- **תגובה (200)** — תוצאת `Download.get_status()`:
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
- **שגיאות**: `404` אם ה-ID לא קיים.

#### `POST /torrents/<id>/pause` — עצירה

- **פרמטר נתיב**: `id`.
- **תגובה (200)**: `{"id": "<id>", "state": "Paused"}`.
- **תופעות לוואי**: שמירת מצב ל-`data/state/<id>.json`,
  הפסקת announce תקופתי, סגירת חיבורי peers.
- **שגיאות**: `404`.

#### `POST /torrents/<id>/resume` — חידוש

- **פרמטר נתיב**: `id`.
- **תגובה (200)**: `{"id": "<id>", "state": "Running"}`.
- **שגיאות**: `404`.

#### `POST /torrents/<id>/cancel` — ביטול

- **פרמטר נתיב**: `id`.
- **תגובה (200)**: `{"id": "<id>", "state": "Cancelled"}`.
- **תופעות לוואי**: שליחת `event=stopped` ל-tracker; שמירת
  סטטיסטיקות ל-SQLite; שחרור חיבורים.
- **שגיאות**: `404`.

### 14.1.2 קבוצה 2 — לוגים וסטטוס בזמן אמת

#### `GET /torrents/<id>/logs?since=N` — Polling של לוגים

- **פרמטר נתיב**: `id`.
- **פרמטר query**: `since` (מספר שלם; ברירת מחדל 0) — מזהה
  הסיקוונס האחרון שכבר התקבל. השרת יחזיר רק לוגים עם
  `seq > since`.
- **תגובה (200)**: `{"logs": [{"seq": N, "msg": "..."}, ...]}`.
- **שגיאות**: `404` אם ה-ID לא קיים.
- **שימוש טיפוסי**: ה-Java GUI מבצע polling כל 500ms ושומר
  את ה-`seq` המקסימלי שראה — כך אין כפילות לוגים.

### 14.1.3 קבוצה 3 — היסטוריה ואירועים (SQLite)

#### `GET /history` — היסטוריית הורדות

- **פרמטרים**: אין.
- **תגובה (200)**: מערך של רשומות JSON מאוחות מטבלאות
  `torrents` ו-`performance_stats`, כל רשומה מכילה:
  `id, info_hash, name, size, started_at, completed_at,
  total_time_seconds, final_status, piece_algorithm,
  peer_algorithm, avg_speed, peak_speed, avg_peers,
  choke_cycles`. הסידור: לפי `started_at DESC`.

#### `DELETE /history` — ניקוי היסטוריה

- **פרמטרים**: אין.
- **תופעות לוואי**: ביצוע `DELETE` על כל ארבע הטבלאות
  (`algorithm_stats`, `performance_stats`, `events`,
  `torrents`) בתוך `_db_lock`.
- **תגובה (200)**: `{"status": "ok"}`.

#### `GET /events?limit=N&torrent_id=ID` — אירועים

- **פרמטרי query**: `limit` (ברירת מחדל 100), `torrent_id`
  (אופציונלי — סינון לפי torrent).
- **תגובה (200)**: מערך של רשומות מטבלת `events`, ממוין
  `timestamp DESC`. כל רשומה: `id, torrent_id, timestamp,
  event_type, description`.

#### `GET /algorithm-stats/<id>` — סטטיסטיקות אלגוריתמים

- **פרמטר נתיב**: `id`.
- **תגובה (200)**: מערך של רשומות מטבלת `algorithm_stats`,
  ממוין לפי `piece_index`. כל רשומה: `id, torrent_id,
  piece_index, selected_as_rarest, choke_count, unchoke_count`.

#### `GET /stats-summary` — טבלת השוואה מצרפית

- **תפקיד**: שורה אחת לכל torrent עם כל המידע הנדרש לטבלת
  השוואת אלגוריתמים (rarest-first מול random,
  tit-for-tat מול round-robin).
- **תגובה (200)**: מערך של רשומות JSON, כל רשומה כוללת:
  `id, name, piece_algorithm, peer_algorithm,
  total_time_seconds, size, final_status, avg_speed,
  peak_speed, avg_peers, choke_cycles, piece_count,
  total_rarest_selections`.

### 14.1.4 קבוצה 4 — תחזוקה

#### `GET /health` — בדיקת חיים

- **פרמטרים**: אין.
- **תגובה (200)**: `{"status": "ok", "timestamp": <unix_time>}`.
- **שימוש**: ה-Java GUI יכול להשתמש בזה לאישור שהשרת קיים
  לפני הצגת מסך ראשי (לא ממומש כיום — נקודת polling רגילה
  של `/torrents` ממלאת את התפקיד).

### 14.1.5 קודי סטטוס מסכמים

| קוד | משמעות במערכת |
|---|---|
| `200` | OK — תגובה רגילה |
| `201` | Created — `POST /torrents` הצליח |
| `400` | Bad Request — קובץ torrent לא תקין / חסר parameter |
| `404` | Not Found — `id` של torrent לא קיים |
| `500` | Internal Server Error — חריגה לא מטופלת בצד השרת |

### 14.1.6 שגיאות וזליגת מידע

כל שגיאה מחזירה JSON מהפורמט `{"error": "<description>"}`.
לא נחשפים stack traces או נתיבים פנימיים של השרת. הלוגים
המלאים נשארים בצד השרת (stdout של Flask + ה-`logger`
הסטנדרטי), והם **לא** עוברים דרך ה-API.

---

## 14.2 סביבת עבודה

### 14.2.1 דרישות תוכנה מינימליות

| רכיב | גרסה מינימלית | סיבה |
|---|---|---|
| **Python** | 3.8+ | שימוש ב-`asyncio.run`, `asyncio.create_task`, type hints מודרני |
| **JDK** | 11+ | שימוש ב-`java.net.http.HttpClient` (חדש ב-Java 11) |
| **Flask** | 2.3+ | תאימות ל-`request.get_json()` המודרני |
| **aiohttp** | 3.8+ | תמיכה ב-`asyncio` של Python 3.8+ |
| **org.json (Java)** | 20240303 | parsing של תגובות JSON מה-API |

### 14.2.2 מערכות הפעלה נתמכות

המערכת נתמכת בשלושת ה-OSים העיקריים. ההתקנה והרצה דרך
סקריפט יחיד בכל פלטפורמה:

| OS | סקריפט | מנהל חבילות |
|---|---|---|
| **Linux** (Ubuntu/Debian) | `./start.sh` | `apt-get` (אוטומטי) |
| **Linux** (Fedora/RHEL) | `./start.sh` | `dnf` (אוטומטי) |
| **Linux** (Arch) | `./start.sh` | `pacman` (אוטומטי) |
| **macOS** | `./start.sh` | `brew` (אוטומטי) |
| **Windows** 10/11 | `start.bat` | `winget` (אוטומטי) |

הסקריפט בודק שיש Python ו-JDK; אם חסרים, מנסה להתקין מול
מנהל החבילות של ה-OS. לאחר מכן מתקין את ה-pip dependencies,
מקמפל את ה-Java, ומריץ. ראה פרק 23 (מדריך למשתמש) לפרטים
מלאים.

### 14.2.3 דרישות חומרה

| משאב | מינימום | מומלץ |
|---|---|---|
| **RAM** | 512 MB פנויים | 2 GB+ |
| **דיסק** | 100 MB לקוד + מקום ל-payload | SSD לביצועי piece writes טובים |
| **מעבד** | x86-64 / ARM64 single-core | dual-core (לחישוב SHA-1 ב-thread נפרד) |
| **רשת** | חיבור אינטרנט יציב | רוחב פס סימטרי לתרומה ל-swarm |

המערכת איננה memory-bound (היא לא טוענת torrent שלם לזיכרון —
פיסות נכתבות לדיסק לאחר אימות); הצוואר הוא **רוחב פס +
שביעות רצון peers**.

### 14.2.4 דרישות רשת ופורטים

| פורט | פרוטוקול | כיוון | תפקיד |
|---|---|---|---|
| `5000` (TCP) | HTTP | פנימי בלבד (`127.0.0.1`) | REST API |
| `6881` (TCP) | BEP-3 | מוצהר בלבד | פורט "האזנה" המוצהר ל-tracker |
| `80` / `443` (TCP) | HTTP/HTTPS | יוצא | תקשורת ל-tracker |
| Dynamic (TCP) | BEP-3 | יוצא | חיבורים ל-peers |

הערה חשובה: המערכת **אינה פותחת socket מאזין** על פורט 6881
(ראה פרק 11.4.4 + פרק 12). כל החיבורים ל-peers הם יוצאים
בלבד. לכן אין צורך ב-port forwarding או ב-UPnP, והמערכת
עובדת מאחורי NAT — ההגבלה היחידה היא שאחרים לא יוכלו להתחבר
אלינו. החלק של ה-NAT traversal מתוכנן לפיתוח עתידי (פרק 26).

### 14.2.5 תלויות חיצוניות (Dependencies)

**Python (קובץ `requirements.txt`)**:

```
flask>=2.3.0
aiohttp>=3.8.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

ארבע חבילות בלבד. `pytest` ו-`pytest-asyncio` רלוונטיות
לבדיקות פנימיות (פרק 24) ולא דרושות בזמן ריצה של המוצר.

**Java**:

```
java_gui/lib/json.jar — org.json 20240303
```

ספרייה יחידה (`org.json`), המורדת אוטומטית בעת קומפילציה
ע"י `start.sh`/`start.bat` מ-Maven Central. המקור היחיד
מחוץ ל-JDK הוא הספרייה הזאת, וגודלה ~70KB.

### 14.2.6 מבנה התיקיות בזמן ריצה

לאחר הפעלה ראשונה, נוצרים תחת תיקיית הפרויקט:

```
data/
├── downloads/          ← הקבצים שהורדו בפועל
├── state/              ← <torrent_id>.json — מצב כל הורדה
└── history.db          ← SQLite — היסטוריה ואירועים

java_gui/
├── build/              ← bytecode מקומפל (.class)
└── lib/json.jar        ← ספריית JSON (מורדת בקומפילציה)
```

---

## 14.3 שפות תכנות

### 14.3.1 בחירת השפות

המערכת ממומשת ב-**שתי שפות פיתוח**:

- **Python 3.8+** — לכל הליבה הפרוטוקולית: pארסר Bencode,
  מטא-דאטה של torrent, תקשורת tracker, ניהול peers, בחירת
  pieces, אלגוריתמי choke/unchoke, אבטחה, REST API.
- **Java 11+** — לממשק המשתמש הגרפי, התקשורת מולו עם
  ה-Engine, וטבלאות/גרפים סטטיסטיים.

זוהי מימוש מפורש של הדרישה במחוון (עמ' 3): *"שתי שפות עם
אינטגרציה פונקציונלית"* + *"שפה מהודרת"* — Python (מפורשת) +
Java (מהודרת ל-bytecode JVM).

### 14.3.2 נימוק בחירת Python ל-Engine

| שיקול | יתרון Python בהקשר זה |
|---|---|
| **`asyncio` בוגר ומלא** | ספריית I/O אסינכרונית מובנית בליבה; אידאלית לעשרות חיבורי TCP מקבילים ב-event loop אחד — בדיוק מה שצריך בלקוח BitTorrent |
| **`hashlib` מובנה** | SHA-1 ו-SHA-256 מהירים בליבה, ללא תלות חיצונית |
| **`struct` ל-binary I/O** | אריזה/פירוק של פורמטים בינאריים (Peer Wire Protocol הוא length-prefixed binary) טבעית ב-Python |
| **`sqlite3` בליבה** | מסד נתונים embedded ללא התקנה — מתאים מצוין למצב היסטוריה |
| **קוד מילולי וקצר** | קוד הפרוטוקול בעברית-טכנית קל לקריאה והבנה — חשוב בפרויקט גמר |
| **Bencode טריוויאלי לממש** | פורמט ה-`.torrent` (bencode) ממומש ב-~230 שורות Python אלגנטיות |

### 14.3.3 נימוק בחירת Java ל-GUI

| שיקול | יתרון Java בהקשר זה |
|---|---|
| **Swing הוא toolkit GUI בוגר** | תמיכה ב-`JTable`, `JProgressBar` renderer, `JSplitPane`, `JDialog` מודאלי — כל מה שצריך לאפליקציית BitTorrent טבלאית |
| **`HttpClient` (JEP 321, Java 11)** | client HTTP מודרני, תומך asynchronous + timeouts |
| **`ScheduledExecutorService`** | תזמון polling בקלות וביציבות, ללא timer rot |
| **`Graphics2D`** | ציור גרפי לחלון `AlgorithmStatsDialog` (bar charts ב-Java2D) |
| **דרישת *שפה מהודרת*** | במחוון יש דרישה מפורשת לשפה מהודרת — Java ממלאת אותה |
| **JVM cross-platform** | bytecode אחד רץ ב-Windows, macOS, Linux |

### 14.3.4 ניתוח חלופות שנשקלו

הצעת הפרויקט (פרק 1) שקלה שלוש קומבינציות; ההכרעה תוצג כאן
תמציתית מ"נקודת מבט של אחרי המימוש":

**חלופה A: Python בלבד (GUI ב-`tkinter` או `PyQt`)**

- *יתרון*: שפה אחת, deployment פשוט.
- *חסרון*: לא ממלא את דרישת המחוון לשפה מהודרת; `tkinter`
  לא מספק טבלה איכותית; `PyQt` תלות חיצונית כבדה (~50MB)
  ורישוי מורכב.

**חלופה B: Java בלבד**

- *יתרון*: שפה אחת מהודרת; טוב לבדיקות חוזה.
- *חסרון*: BitTorrent ב-Java הוא קוד שטחי הרבה יותר ארוך
  (`Netty` או `NIO`); אין `asyncio` נטיב — דורש בנייה ידנית
  של event loop על גבי `Selector`; כתיבת bencode parser ידני
  ארוכה משמעותית.

**חלופה C: Python (Engine) + Java (GUI) — הנבחרת**

- *יתרון*: לכל שפה התפקיד שבו היא מצטיינת; ממלא במלואו את
  דרישת *שתי שפות + שפה מהודרת*; אינטגרציה ברורה דרך REST
  (חוזה מתועד היטב, ניתן לבדיקה ב-`curl` בנפרד מה-GUI);
  פיתוח מקבילי של GUI ו-Engine.
- *חסרון*: שני תהליכים, שני סקריפטי deploy, שני תהליכי
  packaging. הוקל ע"י `start.sh`/`start.bat` שמטפלים בכל
  השלבים אוטומטית.

חלופה C מנצחת בשלושה מימדים מרכזיים: (1) ביצועי הפיתוח של
ליבת הפרוטוקול ב-Python; (2) איכות UI של Swing; (3) עמידה
פורמלית בדרישת המחוון.

### 14.3.5 גשר התקשורת בין השפות

החיבור בין שני התהליכים מתבצע דרך **REST/JSON על
`localhost:5000`** — פרוטוקול מתועד, שפה-אגנוסטי, וקל לבדיקה
ב-`curl`. בחירה זו (במקום למשל JNI, gRPC, או IPC עם named
pipes) מקלה דרמטית על:

- **דיבוג**: ניתן לסמלץ את ה-GUI ע"י `curl` בלי שום JVM.
- **הפרדה לוגית**: כל שגיאה ב-Engine לא תפיל את ה-GUI ולהפך.
- **גישת *future-proof***: אפשרות עתידית לפצל את ה-Engine
  למכונה נפרדת או לחשוף את ה-API ל-clients נוספים (CLI,
  אפליקציה ניידת) ללא שינוי קוד בצד ה-Engine.

---

## 14.4 סיכום הפרק

פרק זה הציג את התוכנה בשלוש רמות:

- **API** — 13 endpoints מתועדים מלאים עם פרמטרים, פורמט
  בקשה, פורמט תגובה וקודי שגיאה.
- **סביבת עבודה** — דרישות גרסה (Python 3.8+, JDK 11+),
  תמיכה ב-Linux/macOS/Windows, התקנה אוטומטית דרך
  `start.sh`/`start.bat`, ארבע תלויות Python ו-`org.json`
  היחידה ב-Java.
- **שפות תכנות** — נימוק החלוקה Python (Engine) + Java
  (GUI), ניתוח קצר של שלוש חלופות שנשקלו, וההצדקה לבחירת
  REST/JSON כגשר.

הפרק הבא (פרק 15) הוא הפרק הטכני המקיף ביותר בספר —
**ניתוח UML, Use Cases, מבני נתונים, יעילות אלגוריתמים
ומחלקות** — והוא יסתמך על כל מה שנכתב עד כה.
