# slides.md - full v2 deck content (transcribe into the pptx)

Order is final. Each slide block gives the header kicker, the title, and the
body. Follow the rules in README.md (Hebrew RTL, no long dashes, " - " only).

Legend:
- `[[SCREENSHOT: name]]` = empty image frame with the given caption.
- `[[DIAGRAM: name]]` = empty image frame for a rendered Mermaid diagram.
- Slides marked **ביקורת עמוקה** are honest weakness slides - keep that tone.
- Slides marked **תרגיל הבוחן** answer a question the teacher pre-announced.

---

## חלק א - יסוד · מה ולמה

---

### Slide 1 - שער (mirror the book cover)
Layout: institutional title page, centered.

- מקיף ה' דרכא אשקלון
- סמל מוסד: 644450
- פרויקט גמר בהנדסת תוכנה
- כותרת הפרויקט (גדול): **מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent**
- מגיש: אדם זבולון · ת.ז. 329441273
- מנחה: גל בראון
- שאלון: 714918 - הנדסת תוכנה י"ד
- שנת לימודים: תשפ"ו
- תאריך הגשה: 14.05.2026
- Footer קטן: מימוש מלא של BEP-3 · מנוע ב-Python + GUI ב-Java · ~5,960 שורות קוד · 226 בדיקות

---

### Slide 2 - מפת ההצגה
Header kicker: 02 · מפת ההצגה
Title: סיור מודרך - מהיסוד פנימה לעומק

- חלק א · יסוד - מה זה BitTorrent, מה הבעיה, ולמה דווקא P2P.
- חלק ב · ארכיטקטורה - שני תהליכים, גשר REST, וההפרדה למודולים בעלי אחריות יחידה.
- חלק ג · בחירת PIECE - Rarest-First שורה-שורה, סיבוכיות וביקורת.
- חלק ד · בחירת PEER - Tit-for-Tat (חלון, snubbing, seeding) וביקורת.
- חלק ה · פרוטוקול - Bencode, info_hash, handshake, ו-framing.
- חלק ו · אבטחה - SHA-1, blocks מול pieces, peer זדוני, מוניטין.
- חלק ז · מצב, scale, וכשל - resume, מיליון peers, נפילת tracker.
- חלק ח · שוברות-מערכת ותוצאות.
- נספח Q · מיקום בקוד לחמש שאלות הפסילה.

---

### Slide 3 - Divider A
Full blue divider.
- אות גדולה: A
- חלק א - יסוד · מה ולמה
- כיתוב משנה: מה זה BitTorrent, איזו בעיה הוא פותר, ולמה זה פרויקט י"ד ולא Torrent Client רגיל

---

### Slide 4 - רקע
Header kicker: 04 · רקע · BITTORRENT
Title: פרוטוקול P2P אחד פתר את בעיית התמרוץ של שיתוף קבצים

- Napster (1999) הוכיח את ה-P2P אבל נפל בגלל שרת מרכזי - נקודת כשל יחידה.
- Gnutella ו-Kazaa ניסו בלי שרת, אבל בלי מנגנון תמרוץ - אנשים הורידו ולא העלו.
- BitTorrent של Bram Cohen (2001) פתר את הבעיה המרכזית: איך לתמרץ peers לתרום upload bandwidth כשאין שום מנגנון אכיפה מרכזי. הפתרון - Tit-for-Tat - הפך לסטנדרט.
- BEP-3 הוא ~30 עמודים, אבל מאחוריו תורת משחקים, פרוטוקול רשת גולמי, קריפטוגרפיה וקונקורנציה - כולם נדרשים למימוש.

---

### Slide 5 - הבעיה האלגוריתמית
Header kicker: 05 · הבעיה
Title: שלוש תתי-בעיות שכולן חייבות להיפתר במקביל

- תת-בעיה 1 - **איזה piece לבקש?** בחירה גלובלית מתוך מאות עד אלפי חלקים. בחירה גרועה -> bottleneck כשה-seeder היחיד מתנתק. (Rarest-First מול Random)
- תת-בעיה 2 - **למי לפתוח choke?** בעיית תורת משחקים: איך לעודד peers לתרום bandwidth בלי אכיפה. (Tit-for-Tat מול Round-Robin)
- תת-בעיה 3 - **איך לאמת תוכן שמגיע מ-peer לא מהימן?** (אימות SHA-1 לכל piece + מערכת מוניטין)

הערה: שלוש הבעיות האלה הן לב הפרויקט לפי הספר. הן יחזרו בחלקים ג', ד', ו-ו'.

---

### Slide 6 - תרגיל הבוחן · 15
Header kicker: 06 · תרגיל 15 · למה י"ד
Title: למה זה פרויקט י"ד ולא Torrent Client רגיל

שאלה: למה זה בכלל פרויקט י"ד, ולא Torrent Client רגיל?

תשובה (אינטגרטיבית):
- רשתות תקשורת + TCP גולמי (לא HTTP מובן מאליו)
- פרוטוקול BitTorrent מלא (BEP-3) - לא ספריה מוכנה
- שני אלגוריתמים אמיתיים - Rarest-First (בעיית optimization) ו-Tit-for-Tat (תורת משחקים)
- Hash Verification + Reputation System
- שתי שפות (Python + Java), שני תהליכים, REST API ביניהם
- שלוש שכבות persistence: JSON state, SQLite history, קבצי הורדה
- בדיקות (226) כולל E2E על socket אמיתי
- ניסוי משוחזר עם CSV מחויב

המסקנה: זה לא "להוריד קבצים" - זו אינטגרציה של רשתות, אלגוריתמיקה, קריפטוגרפיה, קונקורנציה ו-UX במערכת אחת.

---

### Slide 7 - חלופות שנשקלו
Header kicker: 07 · חלופות שנשקלו
Title: למה דווקא P2P, ולא Client-Server או Cloud

Table:
| חלופה | איך עובד | חסרון מרכזי | החלטה |
|---|---|---|---|
| Client-Server (HTTP/CDN) | שרת מרכזי מארח את הקובץ, כולם מורידים ממנו | נקודת כשל יחידה, ניצולת bandwidth מוגבלת לקצב היציאה של השרת. פשוט מדי - אין אלגוריתמים מבוזרים | נדחה |
| Cloud / CDN (S3, edge) | edge nodes + load balancing מנוהל | תשלום per-bandwidth, הכל קופסה שחורה - אין מה להציג הנדסית | נדחה |
| P2P / BitTorrent | כל peer מוריד ומעלה במקביל, בלי שרת תוכן | מורכב למימוש (זה בדיוק האתגר) | **נבחר** |

הרחבה (שאלת ארכיטקטורה 15): גם בבחירת P2P נשאר tracker מרכזי לגילוי peers ראשוני. זה לא דה-צנטרליזציה מלאה - לכן יש דיון בהמשך (חלק ז') על DHT כצעד הבא.

---

## חלק ב - ארכיטקטורה ושכבות

---

### Slide 8 - Divider B
Full blue divider.
- אות גדולה: B
- חלק ב - ארכיטקטורה ושכבות
- כיתוב משנה: שני תהליכים, גשר REST, ומודולים בעלי אחריות יחידה - וכל ההצדקות

---

### Slide 9 - ארכיטקטורה · מבט-על
Header kicker: 09 · ארכיטקטורה · מבט-על
Title: שני תהליכים, גשר REST, ומסד נתונים מקומי

`[[DIAGRAM: architecture]]`
Caption: תרשים ארכיטקטורה - Java GUI ⇄ Python Engine (REST), וה-Engine מול Tracker (HTTP) ומול Peers (TCP/BEP-3).
Note to Adam: render docs/Fig-02.md (רמה 1 - Top Level) at https://mermaid.live and paste the PNG/SVG here. זה הוויזואל המרכזי של השקופית.

Caption / talking points (small, under the diagram):
- מסגרת כחולה = רכיב פנימי (Java GUI, Python Engine); מסגרת כתומה = חיצוני (Tracker, Peers).
- הגשר GUI ⇄ Engine: REST/JSON על 127.0.0.1:5000 (14 endpoints, polling כל 500ms). אין חשיפה לרשת חיצונית.
- ה-Engine מדבר HTTP מול ה-tracker ו-TCP/BEP-3 מול ה-peers. SQLite מקומי לhistory/stats/events.

---

### Slide 10 - תרגיל הבוחן · 11 + שאלת ארכיטקטורה 1
Header kicker: 10 · תרגיל 11 · ההפרדה Python + Java
Title: למה דווקא Python ל-Engine ו-Java ל-GUI

שאלה: למה Python + Java? למה לא הכל Python? ומה היה קורה אם הכל היה רץ ב-Java בלבד?

תשובה:
- דרישת הפרויקט - שתי שפות, אבל הבחירה לא הייתה שרירותית:
- Python ל-Engine - asyncio מצוין לעשרות חיבורי TCP מקבילים על thread אחד; hashlib נותן SHA-1 מובנה; struct לפענוח בינארי; sqlite3 ב-stdlib.
- Java ל-GUI - Swing הוא toolkit בוגר עם JTable, JProgressBar, ו-EDT (Event Dispatch Thread) שמסדר עדכוני UI בטוחים.
- אילו הכול היה Java: Java NIO/Netty היה נותן את אותו האסינכרון אבל מסורבל יותר; ועדיין הייתי מאבד את היתרון של "כל צד נבדק לבד" כי הגבול בין הלוגיקה ל-UI היה מטשטש.
- האינטגרציה דרך REST API היא הגשר (שקופית הבאה).

---

### Slide 11 - תרגיל הבוחן · 12 + שאלת ארכיטקטורה 2
Header kicker: 11 · תרגיל 12 · למה REST
Title: למה REST/JSON ולא קריאה ישירה Java↔Python

שאלה: למה לא לקרוא ישירות לפונקציות Python מתוך Java (JNI)? למה לא Socket קבוע?

מה אני מחפש (לפי הבוחן):
- הפרדת שכבות (Separation of Concerns)
- Loose coupling
- Scalability
- API reusability

תשובה מפורטת:
- REST/JSON הוא **שפה-אגנוסטי** - לא משנה באילו שפות שני הצדדים כתובים. גם CLI ב-Python וגם curl יכולים לדבר עם אותו ה-API.
- בידוד שגיאות - אם ה-GUI קורס, ה-Engine ממשיך להוריד; אם ה-Engine קורס, ה-GUI מציג שגיאה ברורה.
- חלופות שנדחו ולמה: **JNI** מסבך deployment ומחייב קומפילציה native; **gRPC** כבד מדי לפרויקט בסקופ הזה; **Socket קבוע** דורש לתכנן פרוטוקול מאפס במקום להשתמש בסטנדרט HTTP; **named pipes** לא portable בין Linux ל-Windows.
- מחיר ההחלטה (כנות): polling כל 500ms יוצר overhead - בריבוי הורדות זה מצטבר. WebSockets/SSE היו נכונים יותר בעולם אידיאלי.

---

### Slide 12 - שאלת ארכיטקטורה 3 · הזרימה המלאה
Header kicker: 12 · ארכיטקטורה · הזרימה
Title: מ-.torrent ועד קובץ שלם על הדיסק - end-to-end

הזרימה (בדיוק כפי שהוצגה בשאלה):

```
Torrent File
   ↓
TorrentMetadata (פענוח Bencode, חישוב info_hash)
   ↓
TrackerClient (announce HTTP)
   ↓
Peer Discovery (compact peer list)
   ↓
PeerConnection (handshake 68B, BITFIELD, state machine)
   ↓
PieceManager (rarest-first, submit_block, verify SHA-1)
   ↓
DownloadManager (choke/unchoke, request scheduling, upload)
   ↓
File Reconstruction (כתיבה אטומית לדיסק)
```

כל חץ הוא גבול בין מודולים. הוא מומש כך כדי שכל מודול יהיה ניתן לבדיקה לבד (ראו slide 31 - 226 בדיקות).

---

### Slide 13 - שאלות ארכיטקטורה 4 + 7 + 8 · ההפרדה למודולים
Header kicker: 13 · ארכיטקטורה · אחריות יחידה
Title: למה כל מודול נפרד - ולא אחד גדול

שאלת ארכ' 4: למה TorrentMetadata לא נמצא בתוך DownloadManager?
- TorrentMetadata קריא-בלבד ועצמאי - אפשר לפענח .torrent מבלי להתחיל הורדה (חשוב לבדיקות יחידה).
- אם DownloadManager היה מפענח בעצמו: זליגת אחריויות, ובלתי-אפשרי לבדוק parsing בלי להריץ event loop שלם.

שאלת ארכ' 7: למה SecurityManager לא בתוך PeerConnection?
- מוניטין הוא state גלובלי על peer לאורך זמן וחיבורים. PeerConnection חי לאורך socket אחד.
- אם זה היה בתוך PeerConnection: peer שמתחבר מחדש היה מאבד את המוניטין שצבר.

שאלת ארכ' 8: למה PieceManager ≠ DownloadManager?
- PieceManager - "מה יש לי, מה חסר לי, איזה piece נדיר?". מודל נתונים טהור, ללא רשת.
- DownloadManager - "ממי לבקש מה ומתי? למי להעלות?". תזמורת של חיבורים. תלוי ב-PieceManager, לא הפוך.
- ההפרדה הזו היא מה שאפשר את 27 בדיקות ה-piece_manager לרוץ בלי שום socket.

---

### Slide 14 - שאלות ארכיטקטורה 5 + 6 · Tracker מול Peer
Header kicker: 14 · ארכיטקטורה · Tracker מול Peer
Title: שני מודולים שונים לרשת - כי הם פותרים בעיות שונות

שאלת ארכ' 5: למה TrackerClient ו-PeerConnection מודולים שונים?
- פרוטוקולים שונים: TrackerClient = **HTTP** עם announce ופרסור compact list. PeerConnection = **TCP גולמי** עם framing משלו ו-state machine של choke/unchoke.
- מחזורי חיים שונים: TrackerClient מתעורר פעם ב-30 דקות; PeerConnection חי כל החיבור.
- אם זה היה מודול אחד: ספגטי - שתי שפות פרוטוקול נפרדות באותה מחלקה.

שאלת ארכ' 6: מה ההבדל בין tracker ל-peer?
- **Tracker** = ספריית טלפונים בלבד. שואלים אותו "מי מחזיק את ה-info_hash הזה?" ומקבלים IP:port. הוא **לא** מעביר תוכן.
- **Peer** = שולח/מקבל pieces דרך BEP-3.
- למה tracker לא מעביר תוכן: זה היה הופך אותו לשרת מרכזי - בדיוק מה ש-BitTorrent בא לעקוף. Tracker מטפל רק ב-metadata של מי-מחובר.

הערה: שאלת ארכ' 16 (למה האלגוריתמים בשכבת הניהול ולא ברשת) נענית באותו עיקרון - PeerConnection לא יודע כלום על תורת משחקים; DownloadManager מחליט, PeerConnection רק מדבר wire.

---

### Slide 15 - תרגיל הבוחן · 1 · שאלת ההכרעה
Header kicker: 15 · תרגיל 1 · שאלת ההכרעה
Title: אם מוחקים את ה-GUI - מה נשאר?

שאלה: מה נשאר אם מוחקים את ה-Java GUI לחלוטין?

תשובה:
- Torrent Parser (bencode + torrent_metadata)
- Tracker Client
- Peer Connections
- Piece Manager
- Download Manager
- First-Rarest (אלגוריתם בחירת piece)
- Tit-for-Tat (אלגוריתם בחירת peer)
- SHA-1 Validation
- Security / Reputation
- CLI (`python -m python_engine path/to/file.torrent`)

המסקנה: כל הליבה האלגוריתמית קיימת. ה-GUI הוא wrapper מעל ה-API, לא מקור הלוגיקה. כל בדיקות היחידה (226) רצות בלי GUI.

---

### Slide 16 - תרגיל הבוחן · 2 · שאלת ההכרעה ההפוכה
Header kicker: 16 · תרגיל 2 · שאלת ההפך
Title: אם מוחקים את rarest-first ו-tit-for-tat - מה נשאר?

שאלה: מה נשאר אם מוחקים את שני האלגוריתמים המרכזיים?

תשובה כנה:
- נשאר **Torrent Downloader בסיסי** - הוא יכול לפענח .torrent, לדבר עם tracker, להתחבר ל-peers, לבקש pieces ולאמת אותם.
- אבל זה **לא** מימוש BitTorrent איכותי:
  - בלי Rarest-First: ההורדה תיתקע ברגע שה-seeder היחיד שמחזיק piece נדיר עוזב.
  - בלי Tit-for-Tat: אין שום מנגנון תמרוץ; כל peer יכול להסתפק רק בהורדה (free-riding). כל ה-bandwidth של ה-swarm גוסס.
- שני אלגוריתמים אלו הם **מה שמייחד את BitTorrent** משאר פרוטוקולי ה-P2P שקדמו לו. בלעדיהם זה כמו Napster בלי האינדקס המרכזי.

---

### Slide 17 - שאלות ארכיטקטורה 9 + 10 · JSON ו-SQLite
Header kicker: 17 · ארכיטקטורה · Persistence
Title: שתי שכבות persistence - לכל אחת תפקיד שונה

שאלת ארכ' 9: למה לא הכל ב-SQLite?
שאלת ארכ' 10: מה היתרון של JSON ל-state ו-SQLite ל-stats?

תשובה:
| שכבה | מה נשמר | למה דווקא ככה |
|---|---|---|
| **JSON** (`data/state/<id>.json`) | מצב הורדה חי - איזה pieces הושלמו, איזה לא, מי ה-peers האחרונים | קריאה/כתיבה אטומית (write-then-rename), קל ל-debug ידני, אין סכימה קשיחה לתחזק |
| **SQLite** (`data/history.db`) | היסטוריה, סטטיסטיקות, אירועים | שאילתות אגרגציה (SUM, COUNT), אינדקסים על זמן, ACID לרשומות מצטברות |

- ב-JSON יחיד היה קשה לבצע שאילתת היסטוריה ("כמה הורדות מסיימות תוך פחות מ-10 דקות?").
- ב-SQLite יחיד היה צריך migration כל פעם שמשנים שדה ב-state, ועריכה ידנית של state.db לצורכי debug היא סיוט.

---

### Slide 18 - שאלת ארכיטקטורה 11 · asyncio מול thread-per-peer
Header kicker: 18 · קונקורנציה · asyncio
Title: למה asyncio ולא thread לכל peer

שאלה: למה Thread לכל Peer אינו בהכרח פתרון טוב?

תשובה:
- thread לכל peer = ב-50 peers, 50 threads OS. כל אחד תופס ~1MB stack. שינוי context יקר.
- ברוב הזמן ה-thread פשוט מחכה לקלט מהרשת - "blocked on I/O". זה בזבוז שלם.
- asyncio - thread אחד עם event loop. כל coroutine "מוותרת על שליטה" ב-await, ה-loop מטפל ב-50 חיבורים בו-זמנית, ופעולות חוסמות אמיתיות (SHA-1, כתיבת דיסק) עוברות ל-ThreadPoolExecutor.
- ההבדל בקוד: `await reader.read()` במקום `socket.recv()` - תחבירית דומה, סמנטית שונה לגמרי.

---

### Slide 19 - שאלת ארכיטקטורה 16 + 18 · שכבות הקוד
Header kicker: 19 · ארכיטקטורה · Reputation גם אלגוריתם
Title: למה rarest-first/T4T בשכבת הניהול, ולמה Reputation הוא רכיב אלגוריתמי

שאלת ארכ' 16: מדוע rarest-first ו-Tit-for-Tat בשכבת הניהול ולא ברשת?
- PeerConnection מדבר wire בלבד - הוא לא יודע כלום על תורת משחקים או על נדירות.
- DownloadManager הוא הקאפיטן: הוא רואה את **כל** ה-peers ואת **כל** ה-pieces, לכן רק הוא יכול להחליט החלטות גלובליות.
- ההפרדה הזו מאפשרת להחליף אלגוריתם (random/round-robin) בלי לגעת ב-PeerConnection.

שאלת ארכ' 18: למה PeerReputation הוא רכיב אלגוריתמי ולא רק אבטחה?
- Reputation משנה החלטות תזמון - peer חשוד מפסיק לקבל בקשות, גם אם הוא טכנית מחובר.
- זו לולאת משוב: ban -> פחות peers זמינים -> rarest-first בוחר אחרת.
- אבטחה "פסיבית" (SHA-1) פוסלת piece בודד. Reputation "אקטיבי" משנה את ההתנהגות העתידית של ה-scheduler.

---

## חלק ג - בחירת PIECE · Rarest-First

---

### Slide 20 - Divider C
Full blue divider.
- אות גדולה: C
- חלק ג - בחירת PIECE · Rarest-First
- כיתוב משנה: איך בוחרים piece, סיבוכיות, וביקורת על "להעדיף את הנדיר"

---

### Slide 21 - Rarest-First · עיקרון ומבני נתונים
Header kicker: 21 · אלגוריתם בחירת PIECE
Title: Rarest-First - להעדיף את ה-pieces הנדירים ב-swarm

- לכל piece מחזיקים מונה: כמה peers ב-swarm מחזיקים אותו. מתעדכן בכל הודעת HAVE ו-BITFIELD.
- בבחירה: לוקחים את המינימום מבין החסרים לי, בונים את ה-tie set (כל ה-pieces עם אותה ספירה מינימלית), ובוחרים אחד ב-`random.choice`.
- מבני נתונים:
  - `Dict[int, int] _peer_frequency` - O(1) עדכון בכל HAVE.
  - `Dict[str, Set[int]] _peer_pieces` - אילו pieces כל peer מחזיק.
- למה עדיף על Random: שומר על זמינות הנדירים, מונע bottleneck כשה-seeder היחיד עוזב.
- *להצביע:* `piece_manager.py:select_piece_rarest_first`.

---

### Slide 22 - תרגיל הבוחן · 4 · סימולציה
Header kicker: 22 · תרגיל 4 · סימולציה
Title: בהינתן הטבלה - איזה piece יורד ראשון?

הנתונים:
| Piece | מספר peers שמחזיקים |
|---|---|
| P1 | 10 |
| P2 | 2 |
| P3 | **1** |
| P4 | 7 |

תשובה: **P3**.

הסבר:
- האלגוריתם בוחר את ה-piece עם הספירה הנמוכה ביותר מבין ה-pieces שאני **חסר**.
- P3 הוא הנדיר ביותר - יש לו רק peer אחד. אם ה-peer הזה יתנתק לפני שאספיק להוריד את P3, החתיכה אבדה מה-swarm.
- לכן rarest-first שם אותו ראשון בתור.
- אם יש שוויון (למשל שני pieces עם ספירה 1): `random.choice` שובר את הסימטריה כדי שכל ה-peers לא ירוצו על אותו seeder.

---

### Slide 23 - תרגיל הבוחן · 14 · קוד שורה-שורה
Header kicker: 23 · תרגיל 14 · select_piece_rarest_first
Title: select_piece_rarest_first - מהמבנים ועד הבחירה

Code box (LTR, מקוצר):
```python
# piece_manager.py
def select_piece_rarest_first(self, peer_pieces):
    candidates = [i for i in peer_pieces
                  if self.pieces[i].status == PieceStatus.MISSING]
    if not candidates:
        return None
    min_count = min(self._peer_frequency.get(i, 0)
                    for i in candidates)
    rarest = [i for i in candidates
              if self._peer_frequency.get(i, 0) == min_count]
    return random.choice(rarest)
```

הסבר שורה-שורה:
- `candidates` - רק pieces שה-peer הזה מחזיק **וגם** עוד לא הורדנו.
- `min_count` - הספירה המינימלית של מספר ה-peers שמחזיקים piece מבין המועמדים.
- `rarest` - ה-tie set: כל ה-pieces עם אותה ספירה מינימלית.
- `random.choice` - בחירה אקראית מתוך ה-tie set - שובר symmetry, מונע thundering herd על seeder יחיד.

---

### Slide 24 - תרגיל הבוחן · 5 + שאלות קוד 3, 4 · סיבוכיות
Header kicker: 24 · תרגיל 5 · סיבוכיות
Title: O(n) - מה זה n, ואיך מורידים את זה ל-O(log n)

שאלת קוד 3: סיבוכיות rarest-first היא O(n). מהו n?
- n = מספר ה-pieces ב-torrent (לדוגמה: 1,000 pieces ב-torrent של 256MB עם piece_length=256KB).
- כל בחירה סורקת את כל ה-pieces המועמדים כדי למצוא מינימום ולבנות את ה-tie set.

שאלת קוד 4: איך להוריד את זה?
- **Bucket structure** - לתחזק `Dict[count, Set[piece_idx]]` שממפה ספירת נדירות לקבוצת pieces.
  - בחירה הופכת ל-O(1) של חיפוש ה-bucket הנמוך ביותר שאינו ריק.
  - העדכון ב-HAVE הופך ל-O(1) של הוצאה מ-bucket וכניסה ל-bucket אחר.
- **Min-Heap** - O(log n) בחירה, O(log n) עדכון, אבל מסובך כי ערכים משתנים (decrease/increase-key).
- **למה לא יישמתי**: ב-1,000 pieces ההפרש בין O(n) ל-O(log n) הוא ~10x, על פעולה שרצה כמה פעמים בשנייה. זה pre-mature optimization. בתיעוד §הצעות לפיתוח עתידי.

---

### Slide 25 - ביקורת עמוקה · תרגיל 3 · Rarest-First Killer
Header kicker: 25 · ביקורת · Rarest-First
Title: למה rarest-first הוא בעצם בעיית optimization גלובלית

שאלה: למה לבחור את החלק הנדיר ביותר? למה לא חלק אקראי? **ומה יקרה אם ה-peer האחרון שמחזיק piece נדיר יתנתק?**

תשובה (deep critique):
- **Survivability** - piece שקיים רק אצל peer אחד = piece שאבד אם הוא מתנתק. rarest-first מפיץ אותו מהר כדי שיהיה לו replication באוסף ה-swarm. **בלי rarest-first, החצי הנדיר היה אובד ראשון.**
- **גלובלי מוסווה כלוקאלי** - המטרה האמיתית: למקסם availability של כל piece בכל ה-swarm. כל peer מקרב אותה עם heuristic מקומי.
- **Local view** - כל peer רואה רק ~30 שכנים מתוך אלפים. piece שנראה לו "נדיר" עשוי להיות שכיח בחצי השני. ההחלטה מבוססת תצפית מוטית.
- **Contention** - בלי `random.choice` בתוך ה-tie set, כל ה-peers בוחרים דטרמיניסטית את אותו piece -> thundering herd. ה-randomization שובר את הסימטריה.
- מה קורה אם ה-peer האחרון יתנתק *לפני* שהורדתי? - ה-piece נמחק מה-swarm; ההורדה תחכה ל-announce הבא כדי לראות אם הצטרף peer חדש שמחזיק אותו. אם לא - ההורדה תקועה. זו מגבלה מובנית של P2P.

---

## חלק ד - בחירת PEER · Tit-for-Tat

---

### Slide 26 - Divider D
Full blue divider.
- אות גדולה: D
- חלק ד - בחירת PEER · Tit-for-Tat
- כיתוב משנה: למי לפתוח choke, איך מודדים תרומה, ולמה optimistic unchoke הכרחי

---

### Slide 27 - Tit-for-Tat · עיקרון
Header kicker: 27 · אלגוריתם בחירת PEER
Title: כל 10 שניות - top-4 תורמים + 1 אקראי

- כל 10 שניות (CHOKE_INTERVAL) ה-_choke_loop רץ:
  1. ממיין את ה-peers שמעוניינים (interested) לפי תרומתם בחלון 20 שניות.
  2. פותח choke ל-top-4 (MAX_UNCHOKED_PEERS).
  3. בנוסף - **Optimistic Unchoke** של peer אקראי אחד (גם אם לא תרם בכלל).
  4. חוסם (choke) את כל השאר.
- הרעיון של Bram Cohen: לוקאלית כל peer מתגמל את מי שתרם לו - זה יוצר incentive גלובלי לתרומה.
- *להצביע:* `download_manager.py:_tit_for_tat_unchoke`, ו-`peer_connection.py:bytes_received_in_window`.

---

### Slide 28 - תרגיל הבוחן · 6 · סימולציית בחירת peers
Header kicker: 28 · תרגיל 6 · בחירת peers
Title: בהינתן 5 peers ותרומותיהם - מי מקבל unchoke?

הנתונים: יש 5 peers, אני יכול לבצע unchoke רק ל-3.
| Peer | bytes שהעלו אליי בחלון |
|---|---|
| A | 100 MB |
| B | 80 MB |
| C | 40 MB |
| D | 10 MB |
| E | 0 MB |

תשובה (לפי Tit-for-Tat): **A, B, C**.

הסבר:
- אני ממיין יורד לפי תרומה. A > B > C > D > E.
- ה-top-3 (אם זה ה-MAX_UNCHOKED_PEERS) הם A, B, C.
- D ו-E נחסמים (choke).
- אבל - בנוסף לפעם ב-30 שניות, ה-Optimistic Unchoke עשוי לפתוח slot ל-D או ל-E (ראו slide הבא).

---

### Slide 29 - תרגיל הבוחן · 7 · Optimistic Unchoke
Header kicker: 29 · תרגיל 7 · Optimistic Unchoke
Title: אם E לא תרם - למה בכלל לתת לו הזדמנות?

שאלה: למה לתת unchoke ל-peer שלא תרם בכלל?

תשובה:
- **Cold start problem** - כל peer חדש מתחיל ב-0. בלי optimistic unchoke, ציון 0 = לעולם לא נכנס לדירוג = לעולם לא נותן לי כלום = ישאר ב-0 לנצח. זו lock-out מערכתית.
- Optimistic Unchoke הוא **דלת הכניסה למערכת**. הוא בודק - "אולי ה-peer הזה דווקא חזק, אבל פשוט לא היה לו הזדמנות?"
- אם ה-peer האקראי שנפתח לו choke מתחיל לתרום - בסיבוב הבא הוא ייכלל ב-top-K באופן רגיל.
- בלי זה: המערכת תהיה closed club של top-4 הראשונים שתפסו slot.
- בהיבט נוסף - גילוי peers טובים יותר: אולי D בעצם יכול לתת יותר מ-C, אבל הוא נחסם כי הוא חדש. Optimistic Unchoke מאפשר exploration.

---

### Slide 30 - תרגיל הבוחן · 8 · Round Robin Attack
Header kicker: 30 · תרגיל 8 · Round Robin מול T4T
Title: למה Round Robin גרוע יותר מ-Tit-for-Tat

שאלה: למה Round Robin גרוע מ-T4T?

תשובה:
- Round Robin **מתייחס באופן שווה** ל-peer שתורם 100MB ול-peer שלא תורם כלום. כל אחד מקבל את ה-slot בתורו.
- זה מבטל את **מנגנון התמריצים** - אין שום סיבה ל-peer לתרום, כי הוא ייפתח choke ממילא בסיבוב הבא.
- התוצאה: free-riders מצליחים. כל ה-swarm נכנס למצב של "כולם מורידים, אף אחד לא מעלה" - בדיוק המצב ש-BitTorrent בא לפתור (וש-Gnutella סבל ממנו).
- T4T - לעומת זאת - יוצר תחרות. peer שלא מעלה לי, לא מקבל ממני. זה game theory בפעולה.
- במימוש שלי שני האלגוריתמים זמינים (`--peer-algorithm round_robin` כ-baseline) בדיוק כדי להוכיח את ההפרש אמפירית.

---

### Slide 31 - Tit-for-Tat לעומק · חלון, snubbing, seeding
Header kicker: 31 · T4T לעומק · שלוש שכבות
Title: Sliding Window + Snubbing + Seeding Mode

- **Sliding Window (20s)** - המדד הוא לא bytes_downloaded מצטבר, אלא כמה bytes ה-peer שלח לי ב-20 השניות האחרונות. למה: עם מונה מצטבר peer שתרם בהתחלה והשתתק שומר ציון גבוה לנצח. 20s = שני מחזורי choke -> מדד יציב. *להצביע:* `peer_connection.py:bytes_received_in_window`.
- **Snubbing (60s)** - peer ש-unchoked אותי אבל לא שלח data במשך 60 שניות מסומן snubbed, מקבל עדיפות נמוכה, ומפנה slot ל-peer אחר. בלי זה, peer באגי/זדוני תופס slot בלי לתת. *להצביע:* `peer_connection.py:is_snubbed`.
- **Seeding Mode** - T4T הוא אלגוריתם של leecher ("מי נותן לי?"). כש-seeder אין מה להוריד, אז המדד מתהפך: ממיינים לפי כמה אני **מעלה** לכל peer (bytes_sent_in_window) - "למי אני יכול לתת הכי מהר?". *להצביע:* `download_manager.py:_maybe_enter_seeding`.
- שלושת אלה ניתנים לבדיקה - ראו `test_download_manager.py` (44 בדיקות).

---

### Slide 32 - ביקורת עמוקה · קוד 5, 6, 7 + שאלת קוד 18
Header kicker: 32 · ביקורת · T4T
Title: T4T אינו "הוגן" - חולשות שצריך להכיר

שאלת קוד 5: איך מחושב דירוג ה-peer? -> bytes_received_in_window(20s). מיון יורד.
שאלת קוד 6: למה O(m log m) ל-m peers? -> מיון השוואתי (Timsort) של כל ה-peers בכל choke tick.
שאלת קוד 7: 500 peers - האם מיון מלא כל 10s יעיל?
- בפרקטיקה ב-500 peers זה ~9 פעולות log per element × 500 = 4,500 השוואות פעם ב-10 שניות. עוד pre-mature optimization להחליף ל-heap.
- אופטימיזציה אמיתית: לעדכן רק את ה-peers שתרומתם השתנתה מהסיבוב הקודם.

ביקורת עמוקה (לא בשאלה אבל חשוב):
- **Asymmetric bandwidth** - לקוח ביתי 100/10. peer עם upload חלש מוצף בבקשות שאינו יכול לעמוד בהן, ונראה "קמצן" גם אם נתן את המקסימום שלו.
- **BitTyrant (NSDI 2007)** - שולחים לכל peer את המינימום הנדרש כדי להישאר unchoked, וחוסכים upload להפצה ליותר peers. ההגנה: לא קיימת במימוש שלי.
- **Contribution measurement** - מודדים bytes, לא ערך. piece נדיר ששווה זהב נחשב כמו piece שכיח.

שאלת קוד 18 (תזכורת): announce ל-tracker שולח downloaded/uploaded/left כדי שה-tracker ידע מתי הסתיימה ההורדה (event=completed) ויוכל לסטטיסטיקה. גם זה ניתן לזיוף - ראו slide 41.

---

## חלק ה - פרוטוקול ו-Framing

---

### Slide 33 - Divider E
Full blue divider.
- אות גדולה: E
- חלק ה - פרוטוקול ו-Framing
- כיתוב משנה: Bencode, info_hash, handshake, ומה הופך TCP-stream לרצף הודעות

---

### Slide 34 - Bencode ו-info_hash
Header kicker: 34 · BENCODE · INFO_HASH
Title: השפה הבינארית של BitTorrent - וה-fingerprint של ה-torrent

- **Bencode** - פורמט סריאליזציה של 4 טיפוסים: מספר (`i42e`), מחרוזת (`4:spam`), רשימה (`l...e`), מילון (`d...e`).
- מילון בקידוד **קנוני** - מפתחות ממוינים, ללא zero-padding. זה קריטי עבור info_hash.
- **info_hash** - תעודת הזהות של ה-torrent. SHA-1 על ה-`info` dict אחרי **re-encode** ל-Bencode קנוני (לא על הבייטים המקוריים של הקובץ).
- למה re-encode: קובץ torrent שנוצר בתוכנה אחרת עשוי לסדר מפתחות אחרת; re-encode מבטיח hash זהה לכל ה-peers וה-trackers.
- למה רק על `info` ולא על כל הקובץ: שדות חיצוניים (announce, comment) משתנים בין trackers שונים של אותו torrent. רק `info` מזהה את התוכן.
- *להצביע:* `torrent_metadata.py:100-102` (info_hash), `bencode.py:113` (sort), `bencode.py:223` (validate sort).

---

### Slide 35 - שאלת קוד 13 + 14 · Handshake (68 בתים)
Header kicker: 35 · PEER WIRE · HANDSHAKE
Title: 68 בתים מדויקים - והבדיקה ל-info_hash תואם

- handshake = ההודעה הראשונה שכל peer שולח כשהוא פותח חיבור. 68 בתים בדיוק:

| אופסט | גודל | שדה | ערך |
|---|---|---|---|
| 0 | 1 | pstrlen | 19 |
| 1 | 19 | pstr | "BitTorrent protocol" |
| 20 | 8 | reserved | 0x00 × 8 |
| 28 | 20 | info_hash | SHA-1 של info dict |
| 48 | 20 | peer_id | מתחיל ב-"-PG0001-" |

- בדיקות handshake נכנס:
  1. pstrlen == 19 (אחרת לא BEP-3).
  2. pstr == "BitTorrent protocol".
  3. info_hash תואם לשלי - אם לא, מנתק (זה torrent אחר!).
- שאלת קוד 14: מה אם peer שולח info_hash שונה? -> ניתוק מיידי. אסור להמשיך כי שני הצדדים מצביעים על תוכן שונה לחלוטין.

Code box (LTR):
```python
# peer_connection.py
handshake = (
    bytes([19]) +              # pstrlen
    b"BitTorrent protocol" +   # pstr
    bytes(8) +                 # reserved
    self.info_hash +           # 20 bytes
    self.our_peer_id           # 20 bytes
)
```

---

### Slide 36 - שאלות קוד 15 + 16 · Length-Prefixed Framing
Header kicker: 36 · TCP · FRAMING
Title: TCP הוא stream - אנחנו ממציאים את גבולות ההודעה

- TCP מבטיח **סדר** ו**ללא אובדן**, אבל **אין** גבולות הודעה. `recv(1024)` עלול להחזיר חצי הודעה + שליש מהבאה.
- אחרי ה-handshake, כל הודעה ב-BEP-3 היא:

```
[4 bytes: length (big-endian)] [1 byte: msg_id] [payload...]
```

- length=0 -> keep-alive. length=N -> 1 + payload בגודל N-1 בתים.
- ה-parser:
  1. `await reader.readexactly(4)` -> אורך.
  2. ולידציה מול **MAX_MESSAGE_SIZE = 2MB** (חיוני - שאלת קוד 16).
  3. `await reader.readexactly(length)` -> ה-payload המלא (asyncio מטפל בפיצול).
- שאלת קוד 16 - מה אם תוקף שולח length = 4GB?
  - בלי בדיקה: הקצאת buffer של 4GB -> OOM crash של ה-Engine.
  - ההגנה: `if length > MAX_MESSAGE_SIZE: disconnect()`. *להצביע:* `peer_connection.py` (קבוע MAX_MESSAGE_SIZE).
- 10 סוגי הודעות: CHOKE(0), UNCHOKE(1), INTERESTED(2), NOT_INTERESTED(3), HAVE(4), BITFIELD(5), REQUEST(6), PIECE(7), CANCEL(8), KEEP_ALIVE(-1).

---

### Slide 37 - שאלת קוד 19 · asyncio vs blocking
Header kicker: 37 · asyncio · await
Title: await reader.read() מול socket.recv() - אותו תחביר, סמנטיקה הפוכה

שאלה: מה ההבדל בין `await reader.read()` ל-blocking `socket.recv()`?

תשובה:
- `socket.recv()` (blocking) - **חוסם את ה-thread** עד שיגיעו בתים. ה-CPU לא יכול לעשות שום דבר אחר ב-thread הזה.
- `await reader.read()` (asyncio) - **משחרר את ה-event loop**. אם אין בתים, ה-loop רץ קואורוטינות אחרות (peers אחרים, choke loop, keep-alive). כשהבתים מגיעים, ה-loop מחזיר שליטה לכאן.
- מסקנה: עם asyncio, thread יחיד מנהל **כל** ה-50 peers + scheduling, כי רוב הזמן כולם מחכים. בלי asyncio - היה צריך 50 threads.
- מלכודת: כל פעולה חוסמת ששוכחים להעביר ל-executor (כמו hashlib על piece שלם, או כתיבת דיסק) חוסמת את **כל** ה-loop -> כל ה-peers קופאים. לכן SHA-1 וכתיבה רצים ב-ThreadPoolExecutor.

---

## חלק ו - אבטחה ושלמות

---

### Slide 38 - Divider F
Full blue divider.
- אות גדולה: F
- חלק ו - אבטחה ושלמות
- כיתוב משנה: SHA-1, piece מול block, peer זדוני, ומערכת המוניטין

---

### Slide 39 - תרגיל הבוחן · 9 + שאלת קוד 9 · אימות SHA-1
Header kicker: 39 · תרגיל 9 · אימות PIECE
Title: הורדתי piece - מה בדיוק נבדק?

שאלה: הורדתי piece. מה בדיוק נבדק? למה Hash לכל piece בנפרד ולא לכל הקובץ?

תשובה:
1. כל ה-blocks של ה-piece התקבלו (`submit_block` מחזיר `is_complete=True`).
2. מחשבים `SHA-1` חדש על כל ה-bytes של ה-piece.
3. משווים מול ה-hash הצפוי שמופיע ב-`pieces` בקובץ ה-.torrent (20 בתים לכל piece).
4. אם שונה: **החלק נפסל** - blocks נמחקים, ה-piece חוזר ל-MISSING, וה-peer ששלח את ה-block האחרון מקבל hash_failure.

Code box (LTR):
```python
# piece_manager.py
def verify_hash(self) -> bool:
    actual = hashlib.sha1(self._data).digest()
    return actual == self.expected_hash
```

למה piece-by-piece ולא על כל הקובץ:
- **גילוי מוקדם** - piece פגום מתגלה מיד, לא רק בסוף ההורדה (אחרת היו נזרקים גיגות).
- **שיוך לאשם** - יודעים מי שלח את ה-block הפגום -> אפשר ל-ban אותו.
- **שחזור מקומי** - רק ה-piece המקולקל מתבקש מחדש, לא כל הקובץ.

*להצביע (שאלת פסילה 4):* `piece_manager.py` (verify_hash, ~שורה 240).

---

### Slide 40 - שאלות קוד 11 + 12 · Piece מול Block
Header kicker: 40 · PIECE מול BLOCK
Title: למה יש שני מושגים שונים - והקשר ל-submit_block

שאלת קוד 12: מה ההבדל בין Piece ל-Block, ולמה צריך שני מושגים?
- **Piece** - יחידת אימות. בגודל קבוע (לרוב 256KB) - מגיע מקובץ ה-.torrent. יש לו SHA-1 צפוי.
- **Block** - יחידת בקשה. בגודל 16KB (BLOCK_SIZE). זו הגדרה של ה-protocol - בקשה אחת לא יכולה להיות גדולה מ-16KB.
- לכן piece של 256KB = 16 blocks.
- למה לא לבקש piece שלם בבקשה אחת? - בקשת 256KB מ-peer יחיד = throughput שלי תלוי בו לבד. עם 16 בקשות של 16KB אפשר לפזר על כמה peers במקביל (pipelining).

שאלת קוד 11: איך submit_block יודע מתי piece שלם?
- כל Block יש לו `received: bool`.
- `Piece.submit_block(offset, data)` מסמן את ה-block הנכון כ-received ובודק: האם כל ה-blocks ב-piece מסומנים?
- אם כן - מחזיר `True` (signal ל-DownloadManager לעשות verify_hash).
- אחרת - מחזיר `False`; ממשיכים לחכות ל-blocks הנוספים.

---

### Slide 41 - תרגיל הבוחן · 10 + שאלת קוד 17 · Peer זדוני
Header kicker: 41 · תרגיל 10 · Peer שולח piece שגוי
Title: מה קורה כש-peer זדוני שולח piece פגום

שאלה (תרגיל 10): peer שולח לי piece שגוי. מה קורה?

תשובה:
1. **Reject** - SHA-1 לא תואם; ה-piece לא נכתב לדיסק; blocks נמחקים מהזיכרון; ה-piece חוזר ל-MISSING.
2. **Log** - אירוע נכתב ל-event log וב-SQLite ל-events table.
3. **Reputation Penalty** - `SecurityManager.report_hash_failure(peer_key, piece_idx)` מעלה את מונה הכשלים של ה-peer.
4. **Ban** - אחרי 3 כשלי hash (MAX_HASH_FAILURES_PER_PEER) או 5 הפרות פרוטוקול - ניתוק וחסימה קבועה.
5. ה-piece מתבקש שוב מ-peer אחר.

שאלת קוד 17: אילו אירועים מורידים את הציון?
- כישלון אימות SHA-1.
- הפרת פרוטוקול: handshake לא תקין, אורך הודעה > 2MB, HAVE עם index מחוץ לטווח, BITFIELD בגודל שגוי, REQUEST על piece שאין לי.
- timeout חוזר (אופציונלי - יותר חלש מהפרה).

*להצביע (שאלת פסילה 5):* `security.py:report_hash_failure`, `security.py:report_protocol_violation`, `download_manager.py` (קריאות אליהם בנתיבי PIECE ו-message handling).

---

### Slide 42 - ביקורת עמוקה · מוניטין ו-Sybil
Header kicker: 42 · ביקורת · Reputation
Title: למה מוניטין לא פותר Sybil - והגבולות של ההגנה

ביקורת עמוקה (חזרה לשאלות קוד 17, 18):
- **Sybil attack** - תוקף יוצר 1,000 peer_id שונים (כל אחד 20 בתים אקראיים). כל אחד נחסם אחרי 3 כשלי hash, אבל הבא מוכן. המוניטין הוא **per-identity**, לא **per-attacker**. אין לי דרך לזהות שכל ה-peer_id האלה שייכים לאותו תוקף.
- **New peer problem** - peer חוקי חדש מתחיל ב-reputation 0, בדיוק כמו peer חשוד. אין הבחנה.
- **False positives** - 3 timeouts מתקלת רשת זמנית = ban קבוע. אין decay או second chance.
- **Eclipse attack (קוד 5 בעקיפין)** - tracker זדוני יכול להחזיר רק peers שבשליטתו. אם כל ה-peers שלי מאותו attacker - rarest-first מקבל מידע מזויף, כל ה-bitfields שקריים. ההגנות שלי: ולידציית פורמט (compact = 6 × N בתים), אכיפת interval מינימלי. הפתרון האמיתי: DHT + multi-tracker (לא מומש).
- **למה זה לא חיסרון מבייש**: כל אלה ידועים מהמחקר (BitTyrant, Sybil), אף לקוח production לא פותר את כולם. ההכרה בהם מצביעה על הבנה עמוקה.

---

## חלק ז - מצב, scale, וכשל

---

### Slide 43 - Divider G
Full blue divider.
- אות גדולה: G
- חלק ז - מצב, scale, וכשל
- כיתוב משנה: resume, מיליון peers, נפילת tracker, ובאמת מבוזר?

---

### Slide 44 - שאלת ארכיטקטורה 13 · Resume
Header kicker: 44 · ארכיטקטורה · Pause / Resume
Title: אילו רכיבים חייבים לשמור State כדי לאפשר Resume אמיתי

שאלה: אילו רכיבים חייבים לשמור State כדי לאפשר Resume אמיתי?

תשובה:
1. **PieceManager** - אילו pieces COMPLETED, אילו IN_PROGRESS, אילו MISSING. נשמר ב-JSON.
2. **DownloadManager** - איזה download_dir, אילו אלגוריתמים נבחרו, ה-state (RUNNING/PAUSED/COMPLETED/SEEDING).
3. **Sidecar .torrent** - העתק של קובץ ה-.torrent המקורי, כדי שלא נצטרך לבקש אותו מהמשתמש שוב.

מה נעשה בפועל (התיקון לאחר ההגשה):
- `_save_state` קיים מההתחלה. מה שלא היה: `_load_state`.
- היום: `Download.from_state_file()` בונה download מ-JSON + sidecar .torrent, **קורא מהדיסק כל piece שהושלם ומאמת SHA-1 מחדש** לפני שסומכים עליו. piece פגום בדיסק חוזר ל-MISSING.
- `DownloadManager.restore_state()` סורק `data/state/*.json` ב-startup, ומשחזר הורדות במצב PAUSED. המשתמש מבקש Resume במפורש - לא אוטומטית.
- הורדות שכבר נגמרו (COMPLETED/SEEDING) או בוטלו (CANCELLED) **לא** משוחזרות - קבצי ה-state שלהן נמחקים. הקובץ בדיסק נשמר.
- *להצביע:* `download_manager.py:Download.from_state_file`, `download_manager.py:DownloadManager.restore_state`.

---

### Slide 45 - תרגיל הבוחן · 13 + שאלת קוד 20 · 1M peers
Header kicker: 45 · תרגיל 13 · מיליון peers
Title: מה נשבר ראשון בסקייל קיצוני

שאלה (תרגיל 13): 1,000,000 peers. מה נשבר קודם?
שאלה (קוד 20): 1,000 pieces × 200 peers. הערך את כמות המידע שצריך לעקוב.

תשובה - מה נשבר ראשון:
1. **TCP Connections** - מערכת ההפעלה מגבילה ~1024 file descriptors per process (ulimit). הרבה לפני 1M peers.
2. **זיכרון** - כל PeerConnection מחזיק buffers + bitfield. 1M × ~כמה KB = גיגות.
3. **Event Loop scheduling** - asyncio יעיל אבל לא קסם; 1M coroutines פעילים -> latency גבוה בכל context switch לוגי.
4. **Bandwidth** - גם אם הכל אופטימלי, ה-bandwidth שלי לא ישתנה.
5. **rarest-first עצמו** - **לא** נשבר. הוא O(num_pieces), לא O(num_peers).

לתרגיל 20 (סדר הגודל):
- `_peer_frequency`: 1,000 pieces × int = ~8KB.
- `_peer_pieces`: 200 peers × Set ~1,000 ints = ~200 × 1,000 × ~28B = ~5.6MB.
- כל peer מחזיק BITFIELD = 1,000 ביטים = 125 בתים.
- סך הכל: זיכרון של PieceManager בסדר גודל של MB ספורים. סביר לחלוטין.

---

### Slide 46 - שאלות ארכיטקטורה 14 + 15 + 17 · Tracker, DHT, מבוזר באמת?
Header kicker: 46 · ארכיטקטורה · מבוזר עד כמה?
Title: נפילת tracker, האם זה באמת מבוזר, ומה DHT היה משנה

שאלת ארכ' 14: מה אם tracker יחיד נופל?
- ה-tracker הוא **SPOF לגילוי peers ראשוני**. בלעדיו לא מוצאים swarm חדש.
- במימוש שלי: יש תמיכה ב-announce-list (רשימת trackers backup) - אם הראשון נופל, ננסה את השני.
- peers שכבר מחוברים ממשיכים לעבוד - ההורדה לא נופלת מיידית.

שאלת ארכ' 15: האם זה באמת מבוזר אם יש tracker מרכזי?
- כנה: **לא לחלוטין**. ה-content distribution מבוזר (כל peer מחזיק ומשרת חלק), אבל ה-peer discovery מרוכז ב-tracker.
- זה היה הביקורת המקורית על BEP-3.

שאלת ארכ' 17: אילו מודולים ישתנו אם נחבר DHT?
- ישתנו: `tracker_client.py` (יישלח l-DHT במקום HTTP), הוספת מודול `dht_client.py` חדש (Kademlia).
- **לא** ישתנו: `peer_connection.py` (אחרי שיש לי IP:port, לא משנה איך השגתי אותו), `piece_manager.py`, `download_manager.py`, `bencode.py`, `security.py`.
- זו ההצדקה ההנדסית להפרדה - DHT הוא decentralized peer discovery, וההפרדה הברורה בין discovery לבין connection מאפשרת להחליף ללא משבר.

---

## חלק ח - שוברות מערכת ותוצאות

---

### Slide 47 - שוברת מערכת 1 · Bitfield משקר
Header kicker: 47 · שוברת 1 · BITFIELD משקר
Title: מה אם 20% מה-peers משקרים על מה שיש להם

שאלה: כל מנגנון rarest-first מניח שה-bitfield ו-HAVE אמינים. נניח ש-20% מה-peers משקרים ומדווחים על pieces נדירים שאין להם.

תשובה (כנה):
- **כן**, האלגוריתם יכול להתחיל לקבל החלטות גרועות:
  - peer משקר מופיע בספירת ה-rarity של pieces נדירים -> הם נראים פחות נדירים -> rarest-first מורידן אותם פחות בעדיפות -> ה-survivability האמיתי שלהם יורד.
  - כשאני בוחר לבקש מ-peer ש"מחזיק" את ה-piece הנדיר - הוא לא יכול לשלוח -> timeout -> ספירת snubbing עולה -> ban (אופציונלי).
- ההגנה החלקית במימוש: snubbing ו-reputation מסמנים את ה-peer הזה כבעייתי תוך 60 שניות.
- **ההגנה הקריטית שחסרה**: ולידציה הדדית - לוודא ש-peer באמת מחזיק piece לפני שסומכים על ה-BITFIELD שלו. זה לא קיים ב-BEP-3 עצמו (תכן הפרוטוקול).
- מסקנה: BitTorrent מניח **אמון חלקי** - מאמת תוכן (SHA-1) אבל לא מאמת metadata (BITFIELD). זה ידוע ומקובל.

---

### Slide 48 - שוברת מערכת 2 · Peer שולח הרבה אבל פגום
Header kicker: 48 · שוברת 2 · תרומה פגומה
Title: peer זדוני ששולח data רב - האם T4T ידרג אותו גבוה?

שאלה: Tit-for-Tat מתגמל peers שתורמים יותר. נניח peer זדוני שולח נתונים רבים אך כולם פגומים. האם T4T ידרג אותו גבוה?

תשובה (זו נקודת תפר ארכיטקטונית חשובה):
- **בקוד הנוכחי** - `bytes_received_in_window` סופר bytes שהתקבלו, **לפני** אימות SHA-1.
- במונחי המדד, peer ששולח 100MB פגומים נראה זהה ל-peer ששולח 100MB תקינים -> T4T ידרג אותו גבוה.
- ההצלה: ה-`SecurityManager.report_hash_failure` חוסם אותו אחרי 3 כשלים -> מנותק -> מוצא מ-`_connections` -> לא יופיע בסיבוב הבא של T4T.
- **איפה לתקן בארכיטקטורה**: למדוד תרומה רק על blocks שעברו אימות SHA-1 (verified_bytes_received_in_window). זה דורש לחבר את ה-PieceManager (שיודע אם piece עבר verify) ל-PeerConnection (שמחזיק את ה-window).
- מצב נוכחי: ההגנה היא **timing-based** (ban מהיר), לא **measurement-based**. עובד בפועל כי 3 כשלים הם הרבה לפני שה-peer מספיק להגיע ל-top-4.

---

### Slide 49 - שוברת מערכת 3 · כל ה-trackers נופלים
Header kicker: 49 · שוברת 3 · כל ה-trackers נופלים
Title: BitTorrent בלי tracker - האם זה עדיין שווה משהו

שאלה: כל ה-trackers נופלים. עד כמה זה עדיין BitTorrent? האם rarest-first, choke, ו-piece verification עדיין שווים משהו?

תשובה (זו השאלה הכי עמוקה מהשלוש):
- **למשתמש חדש שמתחיל הורדה**: שווה אפס. בלי tracker אין peer discovery ראשוני. החיבור הראשון לא קורה. הכל מתחיל מ-"רשימת peers ריקה".
- **למשתמש שכבר באמצע הורדה**: שווה הכל. כל ה-peers ש**כבר** מחוברים ממשיכים לעבוד; rarest-first ממשיך לעבוד מולם; T4T ממשיך; SHA-1 ממשיך לאמת. ההורדה תסתיים, רק לא יצטרפו peers חדשים.
- **המסקנה**: ה-tracker הוא bootstrap, לא תזמורת. ברגע שיש לך swarm - הוא מתחזק את עצמו.
- **למה לא מתחזק לנצח**: peers מתנתקים (churn). בלי הצטרפויות חדשות ה-swarm דועך, ו-pieces נדירים עלולים להיעלם. ה-DHT (BEP-5) קיים בדיוק כדי לפתור את זה - peer discovery בלי tracker מרכזי.
- כנה: במימוש שלי אין DHT, כי הוא פרוטוקול נפרד בגודל BEP-3 לכל הפחות (~30 עמודים). מתועד כפיתוח עתידי.

---

### Slide 50 - הערכה אמפירית
Header kicker: 50 · אמפירי · ניסוי
Title: Rarest-First מול Random - ניסוי משוחזר

- הקמה: swarm סינתטי על loopback. קובץ 1MB (16 pieces × 64KB), tracker מינימלי, ו-4 mock peers. 5 הרצות לכל אלגוריתם (10 בסך הכול). ה-CSVs מחויבים ב-data/experiments/.
- טופולוגיה: peer בשם full מחזיק את כל 16 החתיכות; low_a/low_b/low_c מחזיקים רק 0 - 7. כלומר 8 - 15 הם "החצי הנדיר" וקיימים רק אצל full.

טבלת תוצאה (ממוצע bytes שהועלו):
| Peer | Rarest-First | Random |
|---|---|---|
| full | 512.0 KB | 576.0 KB |
| low_a | 153.6 KB | 128.0 KB |
| low_b | 166.4 KB | 153.6 KB |
| low_c | 192.0 KB | 166.4 KB |

- המסקנה: ב-rarest-first ה-full מספק בדיוק 512KB (8 חתיכות נדירות × 64KB) - בקשות החצי הנדיר מנותבות אליו באופן עקבי. ב-random הוא מספק ~12.5% יותר, כי הניתוב עיוור לנדירות.
- למה סינתטי ולא torrent ציבורי: שחזוריות. ב-swarm אמיתי הרעש (seeders, bandwidth) גדול מההפרש האלגוריתמי הנמדד.
- מה הניסוי לא מדד: speedup ב-swarm ציבורי, endgame/churn, והשוואת בחירת ה-peers (הושארה קבועה).

---

### Slide 51 - ממשק · המסך הראשי
Header kicker: 51 · ממשק · מסך ראשי
Title: Main Window - הציר של האפליקציה

`[[SCREENSHOT: main-window]]`
Caption: חלון ראשי - טבלת הורדות (Name, Size, Progress, Speed, Peers, State, Location), toolbar (Add Torrent / Pause / Resume / Cancel / Delete / History / Algorithm Stats), ויומן חי. שורה אחת במצב Seeding מודגמת.

Note to Adam: צלם בזמן הורדה פעילה, אם אפשר עם שורה אחת ב-Downloading ושורה אחת ב-Seeding.

---

### Slide 52 - בדיקות
Header kicker: 52 · בדיקות
Title: 226 בדיקות · 9 קבצים · כולל E2E על socket אמיתי

Table:
| קובץ בדיקה | # |
|---|---|
| test_bencode.py | 44 |
| test_download_manager.py | 44 |
| test_peer_connection.py | 39 |
| test_piece_manager.py | 27 |
| test_security.py | 26 |
| test_torrent_metadata.py | 14 |
| test_tracker_client.py | 14 |
| test_api_server.py | 13 |
| test_e2e_peer.py | 5 |
| **סה"כ** | **226** |

- בדיקת E2E (`test_e2e_peer.py`): mock peer אסינכרוני עונה handshake -> bitfield -> unchoke -> piece, וה-PeerConnection מנהל מולו את כל ה-stack (framing, state machine, אימות SHA-1). כולל בדיקה שמוכיחה גם העלאה אמיתית (`test_seeder_serves_block_to_requesting_peer`).

---

### Slide 53 - מסקנות
Header kicker: 53 · מסקנות
Title: מה למדתי מהפרויקט

- Rarest-first שווה את עלותו הזניחה - אותו O(n) כמו random, אבל איכות גבוהה יותר לבריאות ה-swarm.
- Tit-for-Tat דורש זהירות - חלון נע, snubbing, ומצב seeding הם ההבדל בין מיון נאיבי לבין אלגוריתם שמשקף את ההווה.
- TCP הוא stream - בלי framing מפורש (length-prefix + readexactly) שום דבר לא עובד.
- אבטחה היא שכבות - SHA-1, מוניטין, ban - כל אחת חלשה לבד, יחד הן יוצרות defense-in-depth.
- כנות עדיפה על התנפחות - לתעד מה לא מומש ולמה (Sybil, NAT, BEP-52, DHT) חזק יותר מלטעון שהכול עובד.
- ראיות > הצהרות - ניסוי משוחזר עם CSV מחויב, ו-226 בדיקות כולל E2E, מגבים כל טענה בקוד.

---

### Slide 54 - שאלת ארכיטקטורה 20 · מגבלות ופיתוחים עתידיים
Header kicker: 54 · ארכ' 20 · חולשה ארכיטקטונית
Title: זה מימוש Production או סימולציה חינוכית - האמת באמצע

שאלה: זו מערכת Production או סימולציה חינוכית של הרעיונות?

תשובה כנה:
- **מה זה כן**: מימוש BEP-3 אמיתי. כל הודעה רצה על socket TCP אמיתי. SHA-1 מאמת. הקובץ נכתב לדיסק. ההורדה עובדת מול clients אחרים שמדברים BEP-3 (נבדק).
- **מה זה לא**: לא Production. החסר:
  - אין קבלת חיבורים נכנסים / NAT traversal (start_server לא קיים).
  - אין DHT (BEP-5) - peer discovery בלי tracker מרכזי.
  - אין PEX (BEP-11) - החלפת רשימות peers בין peers.
  - אין הצפנת peers (MSE/PE) - ISP יכול לזהות תעבורת BitTorrent ב-DPI.
  - אין UDP tracker, אין IPv6, אין magnet links.
  - רק BEP-3 (v1) - לא BEP-52 (SHA-256 + Merkle Trees).
  - rarest-first הוא O(n) ולא Bucket/Heap - יספיק עד מאות pieces, לא מליונים.
- **למה זה מספיק לפרויקט י"ד**: הוכחת הבנה של כל מנגנון מרכזי, כולל ביקורת על הגבולות שלו. Production דורש שנים של עבודה.

---

### Slide 55 - תודה / שאלות
Layout: closing slide.
Title: תודה · שאלות?

- מגיש: אדם זבולון · מנחה: גל בראון
- פרויקט: מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent
- מעבר לכל שאלה שהבוחן מעוניין לראות בקוד -> נספח Q (2 שקופיות אחרונות).

---

## נספח Q - מיקום בקוד · 5 שאלות הפסילה

---

### Slide 56 - Divider Q
Full blue divider.
- אות גדולה: Q
- נספח · 5 שאלות הפסילה - להצביע על הקוד, לא על התיאוריה
- כיתוב משנה: 5 השאלות שהבוחן הזהיר במפורש שאם לא רואים בקוד = חיסרון משמעותי

---

### Slide 57 - 5 שאלות הפסילה · מפת הקוד
Header kicker: 57 · נספח Q · מיקום בקוד
Title: בדיוק איפה כל מנגנון נמצא בקוד

Table:
| # | שאלת הפסילה | קובץ | מקטע / שורה לציון |
|---|---|---|---|
| 1 | חישוב info_hash | `python_engine/torrent_metadata.py` | פונקציית `_compute_info_hash` (~שורה 100-102): `hashlib.sha1(bencode.encode(info_dict)).digest()` - אחרי re-encode קנוני |
| 2 | piece rarity count | `python_engine/piece_manager.py` | מבנה `_peer_frequency: Dict[int, int]` ועדכון ב-`add_peer_bitfield` / `record_have`; הקריאה ב-`select_piece_rarest_first` |
| 3 | peer sorting ב-Tit-for-Tat | `python_engine/download_manager.py` | `_tit_for_tat_unchoke` - `sorted(candidates, key=lambda p: p.bytes_received_in_window(20.0), reverse=True)` |
| 4 | SHA1(piece) verification | `python_engine/piece_manager.py` | `Piece.verify_hash`: `hashlib.sha1(self._data).digest() == self.expected_hash` |
| 5 | negative reputation ל-peer | `python_engine/security.py` | `SecurityManager.report_hash_failure` ו-`report_protocol_violation`; הקריאה אליהן מ-`download_manager.py` כש-SHA-1 נכשל או כשאורך הודעה > 2MB |

הערה ל-Adam: בזמן ההצגה, פתח את הקובץ ב-IDE עם split view (קוד משמאל, ההצגה מימין), כך שתוכל לקפוץ ל-grep ישיר אם הבוחן ביקש.
