# פרק 3 – מטרות / יעדים

## פתיח

פרק זה מציג את היעדים שעל פיהם נבנה הפרויקט ושמולם נמדדת הצלחתו.
היעדים מאורגנים בהיררכיה משולשת: **מטרות-על** (3.1) — חזון
איכותני המתאר את התוצר ברמת המוצר השלם; **יעדים מדידים** (3.2) —
דרישות פונקציונליות ולא-פונקציונליות בעלות קריטריון הצלחה כמותי
ניתן לבדיקה; ו**יעדי משנה** (3.3) — דרישות נקודתיות ברמת המודול
המשמשות "אבני בניין" של היעדים המדידים. ההיררכיה הזו אינה רק
ארגונית: היא מבטיחה שכל יעד-משנה תורם ליעד מדיד אחד או יותר, וכל
יעד מדיד נשען על מטרת-על אחת או יותר, באופן ש**אין יעד "תלוי
באוויר"**.

המטרות מנוסחות בלשון פעולה (*"לממש"*, *"לאפשר"*, *"לעמוד ב-"*)
ומשקפות **הגדרת המוצר עם סיום הפרויקט**, ולא תהליך פיתוח. עמידה בכל
היעדים המפורטים בפרק זה תוכח אמפירית בפרק 24 (בדיקות והערכה),
ותעמוד מול המדדים הפורמליים שיוצגו בפרק 5 (מדדי הצלחה למערכת).

---

## 3.1 מטרות-על

ארבע מטרות-על מנחות את הפרויקט, וכולן מבטאות **תכונות מערכת** ולא
דרישות נקודתיות:

### מטרה G1 — מימוש פרוטוקול BitTorrent מאפס

לבנות מערכת תוכנה מלאה המממשת את פרוטוקול BitTorrent על פי
**BEP-3** משכבת התעבורה (TCP) ועד שכבת היישום (Peer Wire Protocol),
ללא תלות בספריות BitTorrent חיצוניות. המערכת תידע לפענח קבצי
`.torrent`, לתקשר עם trackers, להתחבר ל-peers, לקבל ולשלוח חלקי
קובץ, לאמת את שלמותם, ולכתוב את הקובץ המלא לדיסק.

### מטרה G2 — הצגת ליבה אלגוריתמית לא-טריוויאלית

ליישם ולנתח את שני האלגוריתמים המרכזיים של BitTorrent —
**rarest-first** לבחירת חלקים ו-**Tit-for-Tat (choke/unchoke)**
לבחירת עמיתים — כליבה אלגוריתמית של המערכת, ולהשוות את ביצועיהם
לקווי בסיס פשוטים (*Random Piece Selection*, *Round-Robin Peer
Selection*). יעד זה ממקם את הפרויקט בקטגוריית *"פתרון בעיה
אלגוריתמית בטכנולוגיות הנדסה מתקדמות"* על פי המחוון, ונותן מענה
למחויבות המחוונית להימנע מ-*"שימוש מרובה ב-IF, רמת קינון גבוהה"*
(סעיף 6 בעמ' 2 של המחוון).

### מטרה G3 — מערכת רב-לשונית עם הפרדת אחריות ארכיטקטונית

לבנות את המערכת כצירוף של שני רכיבים בלתי-תלויים הכתובים בשפות שונות:
**מנוע רשת ב-Python** ו**ממשק משתמש גרפי ב-Java**, המתקשרים ביניהם
דרך **REST API מקומי**. הפרדה זו אינה דקורטיבית — כל שפה נבחרה
בהתאם ליתרונותיה (Python לאסינכרוניות ולגמישות; Java להידור,
לטיפוסיות חזקה ול-Swing הבוגר), והאינטגרציה ביניהן היא **אינטגרציה
פונקציונלית אמיתית** — לא קריאת ספרייה, אלא תקשורת בין שני תהליכים
עצמאיים.

### מטרה G4 — מערכת עמידה, מאובטחת ובעלת חוויית-משתמש מקצועית

לבנות את המערכת באופן שיהיה ברמת איכות "תעשייתית": **אבטחת מידע**
(אימות SHA-1, מוניטין peers, וולידציה של הפרוטוקול, *timeouts*,
הגבלת גודל הודעה); **עמידות לכשלים** (התאוששות מ-peers מנותקים,
שחזור מצב לאחר סגירה כפויה); ו**ממשק משתמש** שמאפשר שליטה מלאה
בהורדות, צפייה בסטטיסטיקות, וצפייה בהיסטוריה.

---

## 3.2 יעדים מדידים

טבלת היעדים המדידים מציגה את הדרישות הפורמליות שיש לעמוד בהן.
לכל יעד מצוין: מזהה ייחודי (`Mn`), שיוך למטרת-העל, קטגוריה
(*פונקציונלי* / *לא-פונקציונלי*), והקריטריון הכמותי לעמידה
מוצלחת (*Acceptance Criterion*).

| מזהה | שיוך | קטגוריה | יעד | קריטריון עמידה |
|---|---|---|---|---|
| **M1** | G1 | פונקציונלי | פענוח קובץ `.torrent` תקני | קריאה תקינה של 100% משדות ה-BEP-3 (`announce`, `info`, `pieces`, `piece length`, `length` / `files`) וחישוב `info_hash` זהה ל-bencode reference. |
| **M2** | G1 | פונקציונלי | תקשורת HTTP מול tracker אמיתי | ביצוע `announce` עם פרמטרים מלאים, פענוח התגובה (כולל פורמט *compact*) וקבלת רשימת peers שאינה ריקה ל-torrents עם seeders זמינים. |
| **M3** | G1 | פונקציונלי | מימוש מלא של handshake לפי BEP-3 | חיבור TCP מוצלח ל-peers אמיתיים והשלמת handshake דו-כיווני (פתיחת חיבור, החלפת 68 בתים, אימות `info_hash`). |
| **M4** | G1 | פונקציונלי | טיפול מלא בהודעות Peer Wire Protocol | תמיכה בשליחה ובקבלה של כל ההודעות התקניות: `keep_alive`, `choke`, `unchoke`, `interested`, `not_interested`, `have`, `bitfield`, `request`, `piece`, `cancel`. |
| **M5** | G1 | פונקציונלי | הורדה ושמירה תקינה של קובץ מלא | הורדה מקצה-לקצה של torrent עד ל-100% עם אימות hash מוצלח לכל piece וכתיבה תקינה של הקובץ הסופי לדיסק (תמיכה ב-single-file). |
| **M6** | G2 | פונקציונלי | מימוש אלגוריתם rarest-first | המודול `piece_manager.py` בוחר תמיד piece מתוך קבוצת המינימום של ה-*peer frequency*, עם פיזור אקראי בתוך הקבוצה (אימות בבדיקות יחידה ב-`test_piece_manager.py`). |
| **M7** | G2 | פונקציונלי | מימוש אלגוריתם Tit-for-Tat | ביצוע מחזור choke/unchoke כל 10 שניות בדיוק (`CHOKE_INTERVAL=10`), בחירת `MAX_UNCHOKED_PEERS=4` peers על פי שיעור ההעלאה, ו-*optimistic unchoke* אחד נוסף. |
| **M8** | G2 | לא-פונקציונלי | השוואת ביצועים בין אלגוריתמים | מערכת המדידה (`/algorithm-stats/<id>`) מספקת נתוני סטטיסטיקה עבור rarest-first מול random ועבור Tit-for-Tat מול round-robin, וניתן להציגם ב-`AlgorithmStatsDialog`. |
| **M9** | G2 | פונקציונלי | החלפה דינמית של אלגוריתם | ניתן לבחור אלגוריתם בחירת piece ואלגוריתם בחירת peer בעת הוספת torrent (פרמטרים `--piece-algorithm` ו-`--peer-algorithm` ב-CLI ו-ComboBox ב-GUI). |
| **M10** | G3 | פונקציונלי | אינטגרציה Java↔Python דרך REST | כל פעולה המבוצעת ב-GUI (הוספה, השהיה, חידוש, ביטול, צפייה בסטטוס, צפייה בלוגים) מתורגמת לבקשת HTTP תקנית למנוע ה-Python, ומחזירה תגובה בפורמט JSON. |
| **M11** | G3 | פונקציונלי | הפרדת שכבות תוכנתית | מבנה הקוד מקיים הפרדה ברורה בין שכבות: *Network* (`peer_connection`, `tracker_client`), *Business Logic* (`download_manager`, `piece_manager`), *API* (`api_server`), *Persistence* (state JSON + SQLite), ו-*Presentation* (`TorrentClientGUI`, `AlgorithmStatsDialog`). אין קריאות-צולבות בין שכבות לא-סמוכות. |
| **M12** | G3 | לא-פונקציונלי | תיאום Threading↔Asyncio נכון | Flask רץ בשרשור הראשי, ו-asyncio event loop בשרשור daemon ייעודי. כל קריאת חוצה-שרשורים עוברת דרך `asyncio.run_coroutine_threadsafe` עם timeout מוגדר. אין race conditions ידועים. |
| **M13** | G4 | לא-פונקציונלי | אימות שלמות נתונים | בדיקת SHA-1 לכל piece לפני כתיבה. piece עם hash שגוי **לא** ייכתב לדיסק, ויסומן ב-`PieceStatus.MISSING` לחזרה. |
| **M14** | G4 | לא-פונקציונלי | זיהוי וניתוק peers זדוניים | מעקב מוניטין דו-ערוצי (`hash_failures`, `protocol_violations`) עם ספים מוגדרים (`MAX_HASH_FAILURES_PER_PEER=3`, `MAX_PROTOCOL_VIOLATIONS_PER_PEER=5`). חציית הסף → ניתוק וחסימה. |
| **M15** | G4 | לא-פונקציונלי | שחזור מצב לאחר סגירה כפויה | קובץ JSON ב-`data/state/<torrent_id>.json` מאפשר שחזור מצב בסיסי (`info_hash`, אילו pieces הושלמו, סטטוס) לאחר הפעלה מחדש של המערכת. |
| **M16** | G4 | פונקציונלי | ממשק משתמש פעיל ועדכני | טבלת ההורדות ב-GUI מתעדכנת אחת ל-2 שניות לכל היותר; הודעות log זורמות ב-real time דרך *incremental polling*; קיימת popup על סיום הורדה עם נתיב הקובץ. |
| **M17** | G4 | פונקציונלי | תיעוד היסטוריה | כל הורדה שהסתיימה (בהצלחה, בכישלון או בביטול) נכתבת לטבלת `torrents` ב-SQLite, וניתן לצפות בה דרך כפתור "היסטוריה" ב-GUI. |
| **M18** | G4 | פונקציונלי | התקנה והפעלה בלחיצה אחת | קובצי `start.sh` (Linux/macOS) ו-`start.bat` (Windows) מבצעים אוטומטית: התקנת תלויות Python, הידור קבצי Java, הפעלת השרת ברקע, והפעלת ה-GUI. סגירת ה-GUI מסיימת את השרת. |

---

## 3.3 יעדי משנה

יעדי המשנה מתורגמים לאחריות נקודתית ברמת המודול. סעיף זה אינו רשימה
ממצה — הוא מציג את יעדי המשנה המרכזיים, המקשרים בין היעדים המדידים
לפרקי האפיון והמימוש שלהלן (פרקים 10, 11, 14, 15, 21).

### 3.3.1 יעדי משנה במנוע Python

| מזהה | תורם ליעד | יעד-משנה | קובץ אחראי |
|---|---|---|---|
| s1.1 | M1 | `encode` / `decode` תקני של Bencode עם וולידציות (מיון מילונים, ללא אפסים מובילים, ללא מינוס-אפס) | `python_engine/bencode.py` |
| s1.2 | M1 | חישוב `info_hash` נכון כ-SHA-1 על מילון ה-`info` המקודד מחדש | `python_engine/torrent_metadata.py` |
| s1.3 | M2 | יצירת `announce request` עם url-encoding של `info_hash` ושל `peer_id` כשדות בינאריים | `python_engine/tracker_client.py` |
| s1.4 | M2 | פענוח `peers` בפורמט רגיל ובפורמט *compact* (6 בתים לכל peer) | `python_engine/tracker_client.py` |
| s1.5 | M3 | שליחה וקבלה של 68 בתים בדיוק ב-handshake, עם וולידציה של `pstrlen=19` ו-`pstr="BitTorrent protocol"` | `python_engine/peer_connection.py` |
| s1.6 | M4 | מימוש `_message_loop` מבוסס asyncio הקורא הודעות בלולאה ומפעיל `on_message` callback | `python_engine/peer_connection.py` |
| s1.7 | M5 | כתיבת piece לדיסק לאחר אימות hash, באמצעות `ThreadPoolExecutor` להוצאת ה-I/O מה-event loop | `python_engine/download_manager.py` |
| s1.8 | M6 | `select_piece_rarest_first(peer_pieces)` מחזיר piece ממינימום `_peer_frequency` עם פיזור אקראי בתוך הקבוצה | `python_engine/piece_manager.py` |
| s1.9 | M7 | `_choke_loop` רץ כל 10 שניות, ממיין peers לפי `bytes_uploaded` בחלון זמן ובוחר את top-K + 1 optimistic | `python_engine/download_manager.py` |
| s1.10 | M13 | `verify_piece` משווה SHA-1 של הנתונים שהורדו ל-`expected_hash` ומחזיר `True`/`False` | `python_engine/piece_manager.py` |
| s1.11 | M14 | `SecurityManager` מקיים מילוני `PeerReputation` ומחזיר `is_peer_banned(peer_key)` | `python_engine/security.py` |
| s1.12 | M15 | סדרון מצב ההורדה לקובץ JSON עם `info_hash`, *bitfield* פנימי, וזמני התקדמות | `python_engine/download_manager.py` |

### 3.3.2 יעדי משנה ב-API

| מזהה | תורם ליעד | יעד-משנה | קובץ אחראי |
|---|---|---|---|
| s2.1 | M10 | חשיפת `POST /torrents` עם multipart upload של קובץ `.torrent` ופרמטרי אלגוריתם | `python_engine/api_server.py` |
| s2.2 | M10 | חשיפת `GET /torrents` המחזיר מערך של כל ההורדות הפעילות בפורמט JSON | `python_engine/api_server.py` |
| s2.3 | M10 | חשיפת `POST /torrents/<id>/{pause,resume,cancel}` לשליטה בהורדה | `python_engine/api_server.py` |
| s2.4 | M16 | חשיפת `GET /torrents/<id>/logs?since=N` לקריאה אינקרמנטלית של *log buffer* | `python_engine/api_server.py` |
| s2.5 | M8 | חשיפת `GET /algorithm-stats/<id>` עם נתוני התפלגות בחירות וביצועים | `python_engine/api_server.py` |
| s2.6 | M17 | חשיפת `GET /history` מטבלת `torrents` ב-SQLite | `python_engine/api_server.py` |
| s2.7 | M12 | `_run_async(coro, timeout=60)` מעביר קוראוטינות מ-Flask thread ל-event loop בבטחה | `python_engine/api_server.py` |

### 3.3.3 יעדי משנה ב-GUI Java

| מזהה | תורם ליעד | יעד-משנה | קובץ אחראי |
|---|---|---|---|
| s3.1 | M10 | לקוח HTTP מבוסס `java.net.http.HttpClient` המפעיל את כל ה-endpoints | `java_gui/src/ApiService.java` |
| s3.2 | M16 | רענון טבלת הסטטוס באמצעות `ScheduledExecutorService` במחזור של 2 שניות | `java_gui/src/TorrentClientGUI.java` |
| s3.3 | M16 | *incremental log polling* עם `logSeqTracker` לכל torrent | `java_gui/src/TorrentClientGUI.java` |
| s3.4 | M16 | זיהוי מעבר למצב *Completed* באמצעות `previousStates` והצגת popup | `java_gui/src/TorrentClientGUI.java` |
| s3.5 | M9 | ComboBox-ים לבחירת piece algorithm ו-peer algorithm | `java_gui/src/TorrentClientGUI.java` |
| s3.6 | M8 | חלון מודאלי `AlgorithmStatsDialog` עם שני tabs (Piece Selection, General Statistics) וגרפי Java2D | `java_gui/src/AlgorithmStatsDialog.java` |
| s3.7 | M17 | חלון היסטוריה הקורא את `/history` ומציג טבלה עם כפתור Clear History | `java_gui/src/TorrentClientGUI.java` |

### 3.3.4 יעדי משנה ב-Persistence ובסביבת ההפעלה

| מזהה | תורם ליעד | יעד-משנה | קובץ אחראי |
|---|---|---|---|
| s4.1 | M15 | יצירה אוטומטית של תיקיית `data/state/` במקרה שאינה קיימת | `python_engine/api_server.py`, `download_manager.py` |
| s4.2 | M17 | סכמת SQLite עם הטבלאות `torrents`, `performance_stats`, `algorithm_stats`, `events` | `python_engine/api_server.py` |
| s4.3 | M18 | התקנה אוטומטית של Python ו-Java במידת הצורך, דרך `apt`/`brew`/`dnf`/`winget` | `start.sh`, `start.bat` |
| s4.4 | M18 | הידור אוטומטי של קבצי `.java` ל-`build/` בעת ההפעלה | `start.sh`, `start.bat` |
| s4.5 | M18 | סגירה תקינה של תהליך ה-API כאשר ה-GUI נסגר (graceful shutdown) | `start.sh`, `start.bat` |

---

## 3.4 מטריצת התחקיב (Traceability Matrix)

מטריצת התחקיב מקשרת כל מטרת-על ליעדים המדידים המממשים אותה, ולפרקי
הספר שבהם ייבחנו:

| מטרת-על | יעדים מדידים | פרקי האפיון | פרק הבדיקה |
|---|---|---|---|
| G1 — מימוש BitTorrent מאפס | M1–M5 | פרק 11, 14, 15 | פרק 24 |
| G2 — ליבה אלגוריתמית | M6–M9 | פרק 15, 21 | פרק 24 |
| G3 — מערכת רב-לשונית | M10–M12 | פרק 11, 14 | פרק 24 |
| G4 — עמידה, אבטחה, UX | M13–M18 | פרק 12, 17, 18, 19, 20, 22 | פרק 24 |

המטריצה מבטיחה שאף יעד אינו "נשכח" בפרקי האפיון, ושאף יעד אינו
מועלה בפרקי המימוש מבלי שיובא תחילה כדרישה רשמית בפרק זה.

---

## סיכום הפרק

פרק זה הציג היררכיה תלת-מפלסית של יעדי הפרויקט: ארבע מטרות-על
איכותיות (G1–G4) — מימוש BitTorrent מאפס, ליבה אלגוריתמית
לא-טריוויאלית, מערכת רב-לשונית עם הפרדת אחריות, ועמידה+אבטחה+UX;
שמונה-עשר יעדים מדידים (M1–M18) בעלי קריטריוני עמידה כמותיים;
ושלושים ואחד יעדי משנה (s1.1–s4.5) המתמפים למודולים ספציפיים בקוד.
מטריצת התחקיב מקשרת בין המפלסים ומבטיחה רציפות אל פרקי האפיון
והבדיקה.

לאחר הצגת המטרות, פרק 4 (אתגרים) יציג את החסמים ההנדסיים בדרך
להשגתן, ופרק 5 (מדדי הצלחה) ימיר את היעדים המדידים שכאן למדדי הצלחה
כמותיים, חלקם פנימיים (ביצועי האלגוריתם) וחלקם חיצוניים (מהירות
הורדה, עמידות).
