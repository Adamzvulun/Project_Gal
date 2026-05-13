# פרק 10 – אפיון המערכת שהוגדרה / מוצעת

## פתיח

פרק זה מציג את **אפיון המערכת המוצעת**, מתוך הפרדה בין תכן
ארכיטקטוני (פרק 11) לבין **דרישות ויכולות** ברמת המוצר. הפרק עוקב
אחר חמשת תתי-הסעיפים שדורש הנוהל: ניתוח דרישות המערכת (10.1),
מודול המערכת (10.2), אפיון פונקציונלי (10.3), ביצועים עיקריים
(10.4), ואילוצים (10.5).

האפיון נשען על שלוש שכבות תיעוד שכבר הוצגו: היעדים המדידים מפרק 3,
מדדי ההצלחה מפרק 5, וההכרעות מפרקים 8–9. הפרק לוקח את כל אלה
ומציג אותם כ-**מפרט הנדסי פורמלי** של המערכת — מה היא חייבת
לעשות, איך היא בנויה ברמת המודולים, מהן יכולותיה הפונקציונליות,
מהן דרישות הביצועים שלה, ובאילו אילוצים היא פועלת.

---

## 10.1 ניתוח דרישות המערכת

הדרישות מסווגות לשתי קטגוריות: **דרישות פונקציונליות (FR)** —
מה המערכת חייבת לעשות; ו**דרישות לא-פונקציונליות (NFR)** — באילו
איכויות היא חייבת לעשות זאת.

### 10.1.1 דרישות פונקציונליות (Functional Requirements)

| מזהה | דרישה | תיאור | שיוך ליעד |
|---|---|---|---|
| FR-01 | פענוח קובץ `.torrent` | קריאת קובץ Bencode והפקת מטא-דאטה מלאה | M1 |
| FR-02 | חישוב info_hash | חישוב SHA-1 על מילון `info` המקודד מחדש | M1 |
| FR-03 | תקשורת HTTP עם tracker | שליחת announce עם פרמטרים מלאים וקבלת רשימת peers | M2 |
| FR-04 | פענוח peers בשני פורמטים | תמיכה ב-compact וב-dict format | M2 |
| FR-05 | חיבור TCP ל-peer | פתיחת חיבור עם handshake דו-כיווני | M3 |
| FR-06 | טיפול בכל הודעות BEP-3 | תמיכה ב-10 סוגי הודעות (choke, unchoke, interested, ...) | M4 |
| FR-07 | בקשת בלוקים מ-peer | שליחת `request` עם פרמטרי piece_index, begin, length | M5 |
| FR-08 | קבלת בלוקים מ-peer | קבלת `piece` והרכבת בלוקים | M5 |
| FR-09 | אימות SHA-1 לכל piece | חישוב hash והשוואה לחתימה הצפויה | M13 |
| FR-10 | כתיבת קובץ לדיסק | שמירת piece בקובץ הסופי לאחר אימות | M5 |
| FR-11 | אלגוריתם rarest-first | בחירת piece לפי תדירות peers | M6 |
| FR-12 | אלגוריתם Tit-for-Tat | בחירת peers ל-unchoke לפי תרומה | M7 |
| FR-13 | אלגוריתמי בסיס (random, round-robin) | אפשרות להחליף את אלגוריתם הבחירה | M9 |
| FR-14 | API REST מקומי | חשיפת פעולות הורדה ב-HTTP | M10 |
| FR-15 | GUI להוספת torrent | בחירת קובץ + תיקיית הורדה | M16 |
| FR-16 | GUI להצגת סטטוס | טבלת הורדות עם progress, speed, peers | M16 |
| FR-17 | GUI לשליטה בהורדה | pause, resume, cancel | M16 |
| FR-18 | GUI לצפייה בלוגים | תצוגת log real-time | M16 |
| FR-19 | GUI לצפייה בסטטיסטיקות אלגוריתמים | חלון מודאלי עם גרפים | M8 |
| FR-20 | GUI לצפייה בהיסטוריה | חלון מודאלי עם רשומות עבר | M17 |
| FR-21 | שמירת מצב לדיסק | JSON state file לכל torrent | M15 |
| FR-22 | תיעוד היסטוריה | SQLite עם torrents, performance, events | M17 |
| FR-23 | זיהוי peer זדוני | מעקב מוניטין + ניתוק | M14 |
| FR-24 | One-click install | start.sh / start.bat | M18 |

### 10.1.2 דרישות לא-פונקציונליות (Non-Functional Requirements)

| מזהה | קטגוריה | דרישה | סף |
|---|---|---|---|
| NFR-01 | **ביצועים** | תפוקה (Throughput) | ≥ 70% מקצב הקו |
| NFR-02 | **ביצועים** | זמן תגובה ל-API call | ≤ 200ms |
| NFR-03 | **ביצועים** | זמן עדכון GUI | ≤ 2000ms |
| NFR-04 | **משאבים** | זיכרון Python | ≤ 500MB |
| NFR-05 | **משאבים** | זיכרון Java | ≤ 300MB |
| NFR-06 | **משאבים** | CPU ממוצע | ≤ 30% |
| NFR-07 | **משאבים** | חיבורי TCP פעילים | ≤ 50 |
| NFR-08 | **אבטחה** | אימות piece לפני כתיבה | חובה 100% |
| NFR-09 | **אבטחה** | הגבלת גודל הודעה | 2MB |
| NFR-10 | **אבטחה** | timeout חיבור TCP | 30s |
| NFR-11 | **אבטחה** | חסימת peer אחרי הפרות | אחרי 3 hash_failures או 5 protocol_violations |
| NFR-12 | **מהימנות** | הצלחת הורדה מקצה-לקצה | ≥ 95% |
| NFR-13 | **מהימנות** | ריצה רציפה ללא קריסה | ≥ 24 שעות |
| NFR-14 | **תאימות** | מערכות הפעלה | Windows 10+, macOS 10.15+, Ubuntu 20.04+ |
| NFR-15 | **תאימות** | Python | 3.8+ |
| NFR-16 | **תאימות** | Java | JDK 11+ |
| NFR-17 | **תחזוקתיות** | כיסוי בדיקות | ≥ 75% line coverage |
| NFR-18 | **תחזוקתיות** | פונקציה ממוצעת | ≤ 50 שורות |
| NFR-19 | **UX** | זמן תגובה לפעולת משתמש | ≤ 100ms |
| NFR-20 | **UX** | תצוגת ממשק | RTL Hebrew + LTR English |

### 10.1.3 תקיפות / מקרי גבול

המערכת חייבת להתמודד עם המקרים הבאים מבלי לקרוס:

- קובץ `.torrent` פגום או חסר שדות.
- tracker שאינו זמין.
- tracker שמחזיר רשימת peers ריקה.
- peer שמסרב handshake.
- peer שמנותק באמצע piece.
- peer ששולח piece עם hash שגוי.
- peer ששולח הודעה ארוכה מדי.
- אובדן חיבור אינטרנט.
- מחסור במקום בדיסק.
- סגירה כפויה של ה-GUI.
- סגירה כפויה של המנוע (Ctrl+C).

---

## 10.2 מודול המערכת

### 10.2.1 חלוקה לתת-מערכות (Subsystems)

המערכת מחולקת ל-**5 תת-מערכות**, כל אחת עם אחריות מוגדרת:

```
┌─────────────────────────────────────────────────────────┐
│ Subsystem 1: Presentation (Java)                        │
│ - TorrentClientGUI, AlgorithmStatsDialog, ApiService    │
├─────────────────────────────────────────────────────────┤
│ Subsystem 2: Application API (Python/Flask)             │
│ - api_server.py                                          │
├─────────────────────────────────────────────────────────┤
│ Subsystem 3: Business Logic (Python/asyncio)            │
│ - download_manager.py, piece_manager.py, security.py    │
├─────────────────────────────────────────────────────────┤
│ Subsystem 4: Network & Protocol (Python/asyncio)        │
│ - tracker_client.py, peer_connection.py, bencode.py,    │
│   torrent_metadata.py                                    │
├─────────────────────────────────────────────────────────┤
│ Subsystem 5: Persistence (Python/stdlib)                │
│ - JSON state files, SQLite (history.db)                 │
└─────────────────────────────────────────────────────────┘
```

### 10.2.2 פירוט תת-מערכות

**Subsystem 1: Presentation** (Java)
- שפה: Java + Swing + org.json
- אחריות: הצגת מצב, קליטת פעולות משתמש, polling סטטוס.
- תלות בלעדית ב-Subsystem 2 דרך REST/HTTP.

**Subsystem 2: Application API** (Python)
- שפה: Python + Flask
- אחריות: חשיפת REST endpoints, סדרון JSON, תיווך ל-Business
  Logic.
- תלות ב-Subsystem 3 (קריאת `_run_async`).

**Subsystem 3: Business Logic** (Python/asyncio)
- שפה: Python + asyncio
- אחריות: כל הלוגיקה של ניהול ההורדה — בחירת piece, choke/unchoke,
  ניהול peers, אבטחה.
- תלות ב-Subsystem 4 (PeerConnection, TrackerClient) ו-Subsystem 5
  (state files).

**Subsystem 4: Network & Protocol** (Python/asyncio)
- שפה: Python + asyncio + aiohttp
- אחריות: מימוש Bencode, פענוח `.torrent`, תקשורת tracker, חיבורי
  TCP ו-Peer Wire Protocol.

**Subsystem 5: Persistence** (Python)
- שפה: Python + stdlib (json, sqlite3)
- אחריות: שמירת מצב הורדה, היסטוריה, סטטיסטיקות.

### 10.2.3 דיאגרמת תלויות בין תת-מערכות

```
[1: Presentation] ───▶ [2: API] ───▶ [3: Business Logic]
                                          │
                            ┌─────────────┴─────────────┐
                            ▼                           ▼
                  [4: Network & Protocol]    [5: Persistence]
                            │
                            ▼
                  [External: Trackers, Peers]
```

החצים מציינים תלות (subsystem A תלוי ב-subsystem B). שים לב
שהקשרים הם **חד-כיווניים**: Presentation לא יודעת על Business
Logic ישירות; Business Logic לא יודעת על Presentation. זוהי
הפרדת אחריות נקייה.

### 10.2.4 רשימת מודולים מפורטת

נספח מלא של 11 המודולים (8 Python + 3 Java) עם הקובץ, האחריות,
ומבני הנתונים המרכזיים — מופיע בפרק 11.

---

## 10.3 אפיון פונקציונלי

תת-סעיף זה מתאר את **פעולות המערכת** כפי שהן מבוצעות בפועל,
תחת שלוש מצבי הפעלה.

### 10.3.1 תרחיש 1: התחלת הורדה חדשה

**שחקנים**: משתמש, GUI, API, Engine, Tracker, Peers.

**זרימה**:

1. המשתמש לוחץ על "Add Torrent" ב-GUI.
2. ה-GUI פותח File Chooser; המשתמש בוחר קובץ `.torrent`.
3. ה-GUI פותח Folder Chooser; המשתמש בוחר תיקיית הורדה.
4. ה-GUI שולח `POST /torrents` ל-API עם multipart המכיל את הקובץ
   ואת הפרמטרים (`piece_algorithm`, `peer_algorithm`,
   `download_dir`).
5. ה-API מפענח את הקובץ, יוצר `TorrentMetadata`, ומפעיל
   `DownloadManager.add_torrent()`.
6. `DownloadManager` יוצר `Download` חדש ומפעיל
   `Download.start()`.
7. `Download.start()` מפעיל `_download_loop()` כקואורוטינה
   ב-event loop.
8. ה-loop מבצע `TrackerClient.announce(event='started')`
   ומקבל רשימת peers.
9. `_connect_to_peers()` פותח חיבורי TCP במקביל
   (`asyncio.gather()`).
10. כל חיבור מבצע handshake, מקבל bitfield, ומתחיל לקבל הודעות.
11. ה-loop נכנס למצב יציב: כל 0.1 שניות בודק אילו peers זמינים
    לבקש מהם בלוקים, ושולח `request` מתאימות.

### 10.3.2 תרחיש 2: ניהול שוטף של הורדה

**שחקנים**: Engine, Peers.

**זרימה תוך כדי הורדה**:

- בקבלת `BITFIELD` או `HAVE` — עדכון `_peer_pieces` ו-`_peer_frequency`.
- בקבלת `UNCHOKE` — שליחת בקשות מיידיות (immediate pipelining).
- בקבלת `CHOKE` — ניקוי block requests של ה-peer.
- בקבלת `PIECE` — בדיקה אם piece הושלם → `verify_piece()` ב-executor
  → אם תקין: `_write_piece()` ב-executor → `_broadcast_have()`
  כ-fire-and-forget task.
- כל 10 שניות — `_choke_loop()` מבצע מחזור Tit-for-Tat.
- כל 60 שניות — `_keep_alive_loop()` שולח keep-alive לכל peers.
- כל `interval` (לפי tracker) — `_periodic_announce_loop()` שולח
  announce חדש.

### 10.3.3 תרחיש 3: השלמת הורדה

**שחקנים**: Engine, GUI.

**זרימה**:

1. כש-`piece_manager.is_complete` הופך ל-`True`, `_complete_download()`
   מופעל.
2. `_complete_download()` משנה את `state` ל-`COMPLETED`, רושם
   ב-log "Completed: <path>", ושולח announce ל-tracker עם
   `event='completed'`.
3. ה-GUI, ב-poll הבא של `/torrents/<id>/logs`, מקבל את הודעת
   ה-`Completed`.
4. ה-GUI מזהה את המעבר `Running → Completed` ב-`previousStates`,
   ומציג popup למשתמש עם שם הקובץ והנתיב.
5. הרשומה נכנסת ל-`history.db` כ-`COMPLETED`.

### 10.3.4 תרחיש 4: שליטה במהלך ההורדה

**שחקנים**: משתמש, GUI, API, Engine.

**Pause**:
1. משתמש לוחץ "Pause" ב-GUI.
2. `POST /torrents/<id>/pause` נשלח.
3. ה-API קורא `Download.pause()`, שמסמן `_paused=True` ועוצר את
   שליחת ה-requests.

**Resume**: סימטרי ל-pause.

**Cancel**:
1. `POST /torrents/<id>/cancel`.
2. כל ה-tasks מבוטלים, כל ה-connections נסגרים, ה-state עובר
   ל-`CANCELLED`.

### 10.3.5 רשימת Use Cases (חלקית)

רשימה מלאה של Use Cases מופיעה בפרק 15.8. כאן רק כותרות:

- UC-01: הוספת torrent חדש
- UC-02: עצירת הורדה
- UC-03: חידוש הורדה
- UC-04: ביטול הורדה
- UC-05: צפייה בסטטוס הורדות
- UC-06: צפייה בלוגים
- UC-07: צפייה בסטטיסטיקות אלגוריתמים
- UC-08: צפייה בהיסטוריה
- UC-09: ניקוי היסטוריה
- UC-10: החלפת אלגוריתם בחירת piece
- UC-11: החלפת אלגוריתם בחירת peer
- UC-12: שחזור מצב לאחר סגירה

---

## 10.4 ביצועים עיקריים

### 10.4.1 מדדי ביצוע צפויים

הטבלה הבאה מסכמת את **הצפיות הכמותיות** מהמערכת. הערכים האמפיריים
בפועל יוצגו בפרק 24 (בדיקות והערכה).

| מדד | ערך צפוי | תנאי |
|---|---|---|
| תפוקה ממוצעת | ≥ 70% מקצב הקו | swarm פעיל עם ≥ 10 seeders |
| תפוקה שיא | ≥ 90% מקצב הקו | swarm רחב |
| חיבורי TCP במקביל | עד 50 | פר torrent |
| pieces / שנייה (מקבלים) | תלוי בקצב | למשל ב-10 Mbps + 256KB piece → ~5 pieces/s |
| בקשות בלוקים בזרימה | עד 50 / peer | per-peer pipelining |
| latency: announce → peer list | ≤ 5 שניות | תלוי ב-tracker |
| latency: UNCHOKE → request | ≤ 100ms | immediate pipelining |
| latency: hash verify | ≤ 50ms / piece | ב-thread executor |
| latency: disk write | ≤ 50ms / piece | תלוי בדיסק |

### 10.4.2 צווארי בקבוק צפויים

הניתוח מקדים שלושה צווארי בקבוק פוטנציאליים:

1. **רוחב פס של הקו** — ברוב המקרים זה הגורם המגביל. המערכת
   מתוכננת להגיע אל 90%+ מקצב הקו.
2. **דיסק I/O** — כתיבת piece של 256KB אורכת מילישניות. במצבים
   של דיסק איטי (HDD ישן, SSD מלא), זה עלול להגביל. הוצאת
   הכתיבה ל-ThreadPoolExecutor מפחיתה את ההשפעה על ה-event loop,
   אך לא על קצב ההורדה הכולל.
3. **CPU עבור SHA-1** — חישוב hash של piece של 256KB אורך
   ~20-30ms. ב-Python pure זה משמעותי; שימוש ב-`hashlib` (שמומש
   ב-C) מקטין משמעותית.

ה-CPU של event loop **לא** מגביל — כל הפעולות הכבדות מועברות
ל-thread executor.

### 10.4.3 התנהגות בעומסים שונים

| מצב | תיאור | התנהגות צפויה |
|---|---|---|
| **swarm קטן** (≤5 peers) | מעט peers, swarm "חולשני" | תפוקה נמוכה. rarest-first עוזר לסיים בכל זאת. |
| **swarm בינוני** (20-50 peers) | התרחיש הרגיל | תפוקה מלאה, ניצול אופטימלי |
| **swarm גדול** (>50 peers) | המערכת מגבילה ב-`MAX_CONNECTIONS` | מאזנת בין top peers ל-optimistic unchoke |
| **רק seeders** | אין leechers | המערכת מורידה מ-seeders ללא Tit-for-Tat אקטיבי |
| **רק leechers** (אין seeders) | torrent "מת" | המערכת תנסה אך לא תצליח להוריד |

---

## 10.5 אילוצים

### 10.5.1 אילוצים טכנולוגיים

- **שפות**: Python 3.8+ ו-Java JDK 11+ בלבד.
- **מערכת הפעלה**: Windows 10+, macOS 10.15+, Ubuntu 20.04+ (או
  מקבילים).
- **רוחב פס**: לפחות 1 Mbps להורדה (פחות מזה — הביצועים יורדים
  משמעותית).
- **גישת אינטרנט**: גישה ל-HTTP/HTTPS (ל-tracker) ול-TCP יוצא
  (ל-peers).
- **פורט נכנס**: לקבלת חיבורים מ-peers — מוגדר 6881 לפי BEP-3.
  במידה והפורט חסום, המערכת תעבוד אך עם רוחב פס מופחת.

### 10.5.2 אילוצים פונקציונליים

- **קבצים בודדים בלבד** (single-file torrents): המערכת תומכת
  ב-`length` בודד ב-`info`. multi-file torrents עם `files` רשימה
  אינם נתמכים בגרסה זו (רשום כפיתוח עתידי בפרק 26).
- **BEP-3 בלבד**: אין תמיכה ב-BitTorrent v2 (SHA-256, merkle
  trees).
- **HTTP trackers בלבד**: אין תמיכה ב-UDP trackers (BEP-15).
- **אין DHT, אין PEX, אין MSE**: התמיכה מוגבלת לפרוטוקול הקלאסי
  בלבד.
- **אין NAT traversal**: peers מאחורי NAT נכנס יכולים להוריד אך
  לא לפעול כ-seeders אפקטיביים.

### 10.5.3 אילוצי משאבים

- **זיכרון**: בכל זמן נתון, המערכת לא מחזיקה את כל הקובץ בזיכרון
  — רק את ה-piece הנוכחי שמתבצע (256KB) ואת המטא-דאטה. זיכרון
  כולל ≤ 500MB.
- **דיסק**: לקובץ כפול הגודל שלו (אחד עבור הקובץ הסופי, ופחות
  עבור JSON state ו-SQLite). אין שימוש בקובצי `.tmp` נפרדים.
- **CPU**: עיקרי בעת חישוב SHA-1. ב-thread pool עם 2 workers.

### 10.5.4 אילוצי אבטחה

- **לא מוצפנת תעבורת peer wire**: BEP-3 הקלאסי אינו תומך
  בהצפנה. הרחבת MSE/PE רשומה כפיתוח עתידי.
- **אין אימות זהות**: peer יכול לטעון לכל peer_id. אין תעודות.
- **חשיפה ל-tracker**: ה-IP של הלקוח חשוף ל-tracker בעת
  announce.

### 10.5.5 אילוצי לוח זמנים

הפרויקט פותח לפי לוח הזמנים בסעיף 1.14:

- שלב 1 (ינואר–פברואר 2026): מחקר.
- שלב 2 (פברואר–מרץ 2026): תכנון.
- שלב 3 (מרץ–אפריל 2026): מימוש מנוע.
- שלב 4 (אפריל 2026): API ו-Persistence.
- שלב 5 (אפריל 2026): GUI.
- שלב 6 (אפריל–מאי 2026): בדיקות.
- שלב 7 (מאי 2026): כתיבת הספר.

לוח הזמנים מהווה אילוץ ממשי על ההיקף הפרויקט — לכן הוחלט להעמיק
במימוש BEP-3 ושני האלגוריתמים הקלאסיים, ולהשאיר את ההרחבות
המתקדמות (DHT, PEX, BT-v2, NAT traversal) לפיתוח עתידי.

### 10.5.6 אילוצי תכן ותחזוקתיות

- **קוד פתוח**: כל הקוד פתוח ונגיש ב-GitHub.
- **בדיקות יחידה**: כל מודול מרכזי מחויב לבדיקות יחידה.
- **תיעוד**: README + ספר פרויקט מלא.
- **תאימות לסטנדרטים**: PEP-8 ל-Python, Java Conventions ל-Java.

---

## 10.6 סיכום הפרק

פרק זה הציג את **אפיון המערכת** ב-5 תת-סעיפים מובנים: 24 דרישות
פונקציונליות (FR-01–FR-24) ו-20 דרישות לא-פונקציונליות
(NFR-01–NFR-20), כולל מקרי גבול נדרשים; חלוקה ל-5 תת-מערכות
עם תרשים תלויות חד-כיווני; אפיון פונקציונלי דרך 4 תרחישי הפעלה
(הוספה, ניהול שוטף, השלמה, שליטה) ורשימת 12 Use Cases; מדדי
ביצוע צפויים, צווארי בקבוק, והתנהגות בעומסים שונים; ו-6 קטגוריות
אילוצים (טכנולוגיים, פונקציונליים, משאבים, אבטחה, לוח זמנים,
תכן).

הפרק מציב את **הגבולות** של המערכת — מה היא עושה, מה היא לא
עושה, ובאילו תנאים. אלה ישמשו "חוזה" לבחינה בפרקים שלהלן.

הפרק הבא (פרק 11) יעבור מתחום ה**מה** ל**איך**: תיאור הארכיטקטורה
המפורט בפורמט Top-Down Level Design, פירוט הרכיבים, התהליכים
ופרוטוקולי התקשורת.
