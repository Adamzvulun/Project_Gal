# slides.md - full v2 deck content (transcribe into the pptx)

Order is final. Each slide block gives the header kicker, the title, and the
body. Follow the rules in README.md (Hebrew RTL, no long dashes, " - " only).

Legend:
- `[[SCREENSHOT: name]]` = empty image frame with the given caption.
- `[[DIAGRAM: name]]` = empty image frame for a rendered Mermaid diagram.
- Slides marked **ביקורת עמוקה** are honest weakness slides - keep that tone.

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
- חלק ח · תרחישי קצה ותוצאות.
- נספח - מפת מיקום בקוד למרכיבים המרכזיים, לקפיצה מהירה בזמן ההגנה.

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
- Gnutella ו-Kazaa ניסו בלי שרת, אבל בלי מנגנון תמרוץ - אנשים הורידו ולא העלו, וה-swarms קרסו תוך זמן קצר.
- BitTorrent של Bram Cohen (2001) פתר את הבעיה המרכזית: איך לתמרץ peers לתרום upload bandwidth כשאין שום מנגנון אכיפה מרכזי. הפתרון - Tit-for-Tat - הפך לסטנדרט.
- BEP-3 הוא ~30 עמודים, אבל מאחוריו תורת משחקים, פרוטוקול רשת גולמי, קריפטוגרפיה וקונקורנציה - כולם נדרשים למימוש.

---

### Slide 5 - הבעיה האלגוריתמית
Header kicker: 05 · הבעיה
Title: שלוש תתי-בעיות שכולן חייבות להיפתר במקביל

- תת-בעיה 1 - **איזה piece לבקש?** בחירה גלובלית מתוך מאות עד אלפי חלקים. בחירה גרועה -> bottleneck כשה-seeder היחיד מתנתק. (Rarest-First מול Random)
- תת-בעיה 2 - **למי לפתוח choke?** בעיית תורת משחקים: איך לעודד peers לתרום bandwidth בלי אכיפה. (Tit-for-Tat מול Round-Robin)
- תת-בעיה 3 - **איך לאמת תוכן שמגיע מ-peer לא מהימן?** אימות SHA-1 לכל piece + מערכת מוניטין.

---

### Slide 6 - למה זה פרויקט י"ד
Header kicker: 06 · למה י"ד · אינטגרציה
Title: לא "להוריד קבצים" - אינטגרציה של עולמות שונים במערכת אחת

אם הייתי בונה רק "Torrent Client" שמוריד ומעלה קבצים, זה היה פרויקט נחמד אבל לא בקנה מידה של פרויקט גמר. מה שהופך את זה לפרויקט י"ד הוא ההצטלבות של עולמות:

- רשתות תקשורת ו-TCP גולמי - לא HTTP מוכן מאליו.
- מימוש מלא של BEP-3, בלי שום ספריית BitTorrent מוכנה.
- שני אלגוריתמים אמיתיים - Rarest-First (בעיית optimization) ו-Tit-for-Tat (תורת משחקים).
- אימות SHA-1 ומערכת מוניטין על peers.
- שתי שפות (Python ל-Engine, Java ל-GUI), שני תהליכים, REST API ביניהם.
- שלוש שכבות persistence: JSON state, SQLite history, וקבצי הורדה.
- 226 בדיקות כולל E2E על socket אמיתי, וניסוי אמפירי משוחזר עם CSV מחויב.

זה לא "להוריד קבצים" - זו אינטגרציה של רשתות, אלגוריתמיקה, קריפטוגרפיה, קונקורנציה ו-UX במערכת אחת.

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

הערה כנה: גם בבחירת P2P נשאר tracker מרכזי לגילוי peers ראשוני - זו לא דה-צנטרליזציה מלאה. בחלק ז' אדבר על DHT כצעד הבא.

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
- ה-Engine מדבר HTTP מול ה-tracker ו-TCP/BEP-3 מול ה-peers. SQLite מקומי ל-history, stats ו-events.

---

### Slide 10 - החלטת תכנון · Python + Java
Header kicker: 10 · החלטת תכנון · השפות
Title: למה דווקא Python ל-Engine ו-Java ל-GUI

דרישת הפרויקט הייתה שתי שפות - אבל הבחירה אילו שפות לא הייתה שרירותית.

Python מתאים ל-Engine - asyncio מצוין לעשרות חיבורי TCP מקבילים על thread אחד, hashlib נותן SHA-1 מובנה, struct מטפל בפענוח בינארי, וכל הספריות (sqlite3, hashlib, asyncio) נמצאות ב-stdlib.

Java מתאים ל-GUI - Swing הוא toolkit בוגר עם JTable ו-JProgressBar מובנים, ומודל ה-threading עם ה-EDT (Event Dispatch Thread) מסדר עדכוני UI בטוחים.

אילו הכול היה רץ ב-Java בלבד - Netty או NIO היו נותנים את אותו האסינכרון אבל מסורבל יותר, והייתי מאבד את היתרון של "כל צד נבדק לבד". האינטגרציה נעשית דרך REST API (שקופית הבאה).

---

### Slide 11 - החלטת תכנון · למה REST
Header kicker: 11 · החלטת תכנון · REST
Title: למה REST/JSON ולא קריאה ישירה Java ⇄ Python

שאלה הוגנת: למה לעשות את הסיבוב דרך HTTP מקומי, במקום לקרוא ישירות לפונקציות Python מ-Java?

התשובה היא הפרדת שכבות מוחלטת. REST/JSON הוא שפה-אגנוסטי - גם CLI ב-Python וגם curl יכולים לדבר עם אותו ה-API. בידוד שגיאות הופך לחד: אם ה-GUI קורס, ה-Engine ממשיך להוריד; אם ה-Engine קורס, ה-GUI מציג שגיאה ברורה במקום להתרסק יחד איתו. וברגע שהפרדתי לשתי תוכנות עצמאיות, יכולתי לבדוק את ה-Engine ב-pytest בלי שום קשר ל-Swing.

חלופות שנדחו - **JNI** מסבך deployment ומחייב קומפילציה native; **gRPC** כבד מדי לפרויקט בסקופ הזה; **Socket קבוע** דורש לתכנן פרוטוקול מאפס במקום לקבל HTTP בחינם; **named pipes** לא portable בין Linux ל-Windows.

מחיר ההחלטה (כנה): polling כל 500ms יוצר overhead - בריבוי הורדות זה מצטבר. WebSockets או SSE היו נכונים יותר בעולם אידיאלי, אבל ה-polling הספיק לסקופ.

---

### Slide 12 - זרימת הורדה · END-TO-END
Header kicker: 12 · ארכיטקטורה · הזרימה
Title: מה קורה מ-"Add Torrent" ועד קובץ שלם על הדיסק

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

הזרימה במילים - TorrentMetadata פותח את קובץ ה-.torrent ומבצע parsing של ה-Bencode, ומחשב את ה-info_hash שיהווה תעודת זהות לכל פעולה הבאה. TrackerClient שולח HTTP GET ל-tracker עם ה-info_hash הזה, וחוזר עם רשימת peers בפורמט compact (6 בתים ל-peer: 4 ל-IP ו-2 ל-port).

עבור כל peer ברשימה אני פותח TCP connection, מבצע handshake של 68 בתים, ומחליף הודעת BITFIELD שמספרת לי מה יש לכל אחד. כאן PieceManager נכנס לתמונה - הוא מתחזק את המונים של "כמה peers ב-swarm מחזיקים כל piece" ובוחר את הנדיר ביותר עם rarest-first.

DownloadManager לוקח את הבחירה הזו ושולח את בקשות ה-blocks ב-pipelining מקבילי לכמה peers, מקבל PIECE messages, ומעביר את הנתונים ל-thread executor כדי לאמת SHA-1 בלי לחסום את ה-event loop. רק אחרי שהאימות עבר, ה-piece נכתב לדיסק וההודעה HAVE משודרת לכל ה-peers האחרים, כדי שהם ידעו שיש לי אותו.

כשכל ה-pieces הושלמו, ה-state עובר ל-COMPLETED, וב-tick הבא של choke ה-_maybe_enter_seeding מקדם ל-SEEDING - מצב שבו אני רק מעלה ל-peers שמבקשים, וה-GUI מציג "Seeding".

כל חץ בתרשים הוא גבול בין שני מודולים. זה לא במקרה - כל מעבר תוכנן כך שכל מודול ניתן לבדיקה בנפרד (226 בדיקות, בסיס המעבר).

---

### Slide 13 - ארכיטקטורה · אחריות יחידה
Header kicker: 13 · ארכיטקטורה · אחריות יחידה
Title: למה כל מודול נפרד - ולא אחד גדול

עיקרון מנחה: לכל מודול יש אחריות אחת. שלוש דוגמאות מסבירות למה זה לא טריוויאלי.

**TorrentMetadata נפרד מ-DownloadManager** - כי TorrentMetadata קריא-בלבד ועצמאי. אפשר לפענח קובץ .torrent בלי להתחיל הורדה (חשוב לבדיקות יחידה ול-CLI). אילו DownloadManager היה מפענח בעצמו, הייתה זליגת אחריויות, ובלתי-אפשרי לבדוק parsing בלי להריץ event loop שלם.

**SecurityManager נפרד מ-PeerConnection** - כי מוניטין הוא state גלובלי על peer לאורך זמן וחיבורים. PeerConnection חי לאורך socket אחד; אם המוניטין היה בתוכו, peer שמתחבר מחדש היה מאבד את המוניטין שצבר ויכול לחזור לתקוף מאפס.

**PieceManager נפרד מ-DownloadManager** - כי הם פותרים בעיות שונות. PieceManager עונה על "מה יש לי, מה חסר לי, איזה piece נדיר?" - מודל נתונים טהור, ללא רשת. DownloadManager עונה על "ממי לבקש מה ומתי? למי להעלות?" - תזמורת של חיבורים. ההפרדה הזו היא בדיוק מה שאפשר ל-27 בדיקות של piece_manager לרוץ בלי שום socket.

---

### Slide 14 - Tracker מול Peer
Header kicker: 14 · ארכיטקטורה · Tracker מול Peer
Title: שני מודולים שונים לרשת - כי הם פותרים בעיות שונות

TrackerClient ו-PeerConnection הם שני מודולים נפרדים למרות ששניהם תקשורת רשת - והסיבה היא שהם מדברים פרוטוקולים שונים לחלוטין, ויש להם מחזורי חיים שונים.

TrackerClient מדבר HTTP - שולח announce עם info_hash, מקבל JSON או compact list של peers. הוא מתעורר פעם ב-30 דקות בערך (לפי ה-interval שה-tracker ביקש). PeerConnection מדבר TCP גולמי עם framing משלו, state machine של choke/unchoke ו-10 סוגי הודעות. הוא חי לאורך כל החיבור - לפעמים שעות.

אילו זה היה מודול אחד היינו מקבלים ספגטי - שתי שפות פרוטוקול שונות באותה מחלקה.

ההבדל המהותי בין tracker ל-peer: Tracker הוא ספריית טלפונים. שואלים אותו "מי מחזיק את ה-info_hash הזה?" ומקבלים IP:port. הוא **לא** מעביר את התוכן עצמו - אם הוא היה מעביר, היינו חוזרים למודל שרת מרכזי, וזה בדיוק מה ש-BitTorrent בא לעקוף. Peer הוא מי שבאמת שולח ומקבל pieces דרך BEP-3.

אותו עיקרון מסביר למה rarest-first ו-T4T נמצאים ב-DownloadManager ולא ב-PeerConnection: PeerConnection לא יודע כלום על תורת משחקים, הוא רק מדבר wire. רק DownloadManager רואה את כל ה-peers ואת כל ה-pieces, ולכן רק הוא יכול להחליט החלטות גלובליות.

---

### Slide 15 - שאלת הכרעה · GUI
Header kicker: 15 · שאלת הכרעה · GUI
Title: אם מוחקים את ה-GUI - מה נשאר?

שאלה טובה למבחן האם המערכת היא בעצם UI עם backend טריוויאלי, או הפוך. בואו נדמיין שמחקנו את כל קובצי ה-Java. מה ימשיך לעבוד?

נשארים:
- Torrent Parser (bencode + torrent_metadata)
- Tracker Client
- Peer Connections
- Piece Manager
- Download Manager
- First-Rarest (אלגוריתם בחירת piece)
- Tit-for-Tat (אלגוריתם בחירת peer)
- SHA-1 Validation
- Security / Reputation
- CLI מלא: `python -m python_engine path/to/file.torrent`

כל הליבה האלגוריתמית קיימת. ה-GUI הוא wrapper מעל ה-API, לא מקור הלוגיקה. כל 226 בדיקות היחידה רצות בלי שום GUI - וזו ראיה ניצחת לכך.

---

### Slide 16 - שאלת הכרעה הפוכה · האלגוריתמים
Header kicker: 16 · שאלת הכרעה הפוכה · האלגוריתמים
Title: אם מוחקים את rarest-first ו-tit-for-tat - מה נשאר?

זו השאלה ההפוכה והמעניינת יותר. נניח שמחקנו את rarest-first ו-tit-for-tat והשארנו רק בחירה רנדומלית של pieces ופתיחת choke לכולם. מה נשאר?

מבחינה טכנית - Torrent Downloader בסיסי שעובד. הוא עדיין מפענח .torrent, מדבר עם tracker, פותח חיבורים ומבקש pieces. אבל זה כבר לא מימוש BitTorrent איכותי, ולמעשה זה לא הרבה מעבר ל-Napster עם פרוטוקול בינארי.

בלי Rarest-First, ההורדה תיתקע ברגע שה-seeder היחיד שמחזיק piece נדיר עוזב - כי בחרתי דברים שכיחים קודם והשארתי את הנדיר לסוף. בלי Tit-for-Tat, אין שום מנגנון תמרוץ; כל peer יכול להסתפק רק בהורדה (free-riding) וכל ה-bandwidth של ה-swarm גוסס תוך זמן קצר - בדיוק הסיפור של Gnutella.

שני האלגוריתמים האלה הם מה שמייחד את BitTorrent משאר פרוטוקולי ה-P2P שקדמו לו. בלעדיהם, הפרויקט מאבד את הלב שלו.

---

### Slide 17 - Persistence · JSON ו-SQLite
Header kicker: 17 · Persistence · JSON ו-SQLite
Title: שתי שכבות persistence - לכל אחת תפקיד שונה

מתבקש לשאול - אם יש SQLite, למה להחזיק גם JSON? התשובה היא שכל אחד פותר בעיה אחרת.

| שכבה | מה נשמר | למה דווקא ככה |
|---|---|---|
| **JSON** (`data/state/<id>.json`) | מצב הורדה חי - אילו pieces הושלמו, אילו לא, מי ה-peers האחרונים | קריאה/כתיבה אטומית (write-then-rename), קל ל-debug ידני, אין סכימה קשיחה לתחזק |
| **SQLite** (`data/history.db`) | היסטוריה, סטטיסטיקות, אירועים | שאילתות אגרגציה (SUM, COUNT), אינדקסים על זמן, ACID לרשומות מצטברות |

ב-JSON יחיד היה קשה לבצע שאילתת היסטוריה ("כמה הורדות מסיימות תוך פחות מ-10 דקות?"). ב-SQLite יחיד היה צריך migration כל פעם שמשנים שדה ב-state, ועריכה ידנית של state.db לצורכי debug היא סיוט. ההפרדה היא לא יומרה - היא תוצאה של שני סוגי שאלות שונים על הנתונים.

---

### Slide 18 - קונקורנציה · asyncio
Header kicker: 18 · קונקורנציה · asyncio
Title: למה asyncio ולא thread לכל peer

חלופה אינטואיטיבית הייתה להריץ thread נפרד לכל peer. למה דחיתי את זה?

ב-50 peers, thread-per-peer פירושו 50 threads של מערכת ההפעלה, כל אחד תופס בערך מגה זיכרון רק על ה-stack שלו. שינוי context בין threads יקר - ה-OS חייב לשמור registers וצורות זיכרון לכל אחד. ועיקר הזמן בכל thread כזה הוא פשוט המתנה לקלט מהרשת ("blocked on I/O"). זה בזבוז שלם.

asyncio הופך את המודל - thread אחד עם event loop. כל coroutine מוותרת על שליטה ב-await, וה-loop מטפל ב-50 חיבורים בו-זמנית. רק פעולות חוסמות אמיתיות (חישוב SHA-1 על piece שלם, כתיבת דיסק) עוברות ל-ThreadPoolExecutor.

בקוד ההבדל הוא מינימלי: `await reader.read()` במקום `socket.recv()`. תחבירית דומה, סמנטית הפוכה לחלוטין.

---

### Slide 19 - Reputation גם רכיב אלגוריתמי
Header kicker: 19 · ארכיטקטורה · Reputation
Title: למה Reputation אינו רק אבטחה - הוא משנה החלטות

נקודה ארכיטקטונית שכדאי להדגיש: Reputation הוא בעצם רכיב **אלגוריתמי**, לא רק רכיב אבטחה.

ניתן היה לחשוב על אבטחה כ"בודק פסיבי" - SHA-1 פוסל piece פגום ונגמר. אבל Reputation עושה משהו אחר: הוא משנה החלטות תזמון. peer חשוד מפסיק לקבל בקשות, גם אם הוא עדיין טכנית מחובר. זו לולאת משוב - ban של peer מצמצם את הזמינות של pieces מסוימים, ומשנה את הבחירה של rarest-first בסיבוב הבא.

מאותו עיקרון של הפרדת שכבות - rarest-first ו-tit-for-tat ממוקמים ב-DownloadManager ולא ב-PeerConnection. PeerConnection מדבר wire בלבד; הוא בודד מדי כדי לקחת החלטות גלובליות. רק DownloadManager רואה את **כל** ה-peers ואת **כל** ה-pieces, ולכן רק הוא יכול לאזן בין החלטות מקומיות לאיזון מערכתי.

בנוסף, ההפרדה הזו מאפשרת להחליף אלגוריתם (random/round-robin כ-baseline) בלי לגעת ב-PeerConnection.

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
- מבני נתונים מרכזיים: `_peer_frequency: Dict[int, int]` (O(1) עדכון בכל HAVE), ו-`_peer_pieces: Dict[str, Set[int]]` שמתחזק אילו pieces כל peer מחזיק.
- למה עדיף על Random: שומר על זמינות הנדירים, מונע bottleneck כשה-seeder היחיד עוזב.

המימוש העיקרי נמצא ב-piece_manager.py בפונקציה `select_piece_rarest_first`.

---

### Slide 22 - סימולציה · איזה piece ראשון
Header kicker: 22 · סימולציה · איזה piece ראשון
Title: בהינתן הטבלה - איזה piece יורד ראשון, ולמה?

סימולציה לדוגמה - בהינתן הטבלה הבאה של מספר ה-peers שמחזיקים כל piece, איזה ירד ראשון?

| Piece | מספר peers שמחזיקים |
|---|---|
| P1 | 10 |
| P2 | 2 |
| P3 | **1** |
| P4 | 7 |

התשובה היא **P3**. למה? כי ה-rarest-first בוחר את ה-piece עם הספירה הנמוכה ביותר מבין ה-pieces שאני חסר - וכאן P3 הוא הנדיר ביותר עם peer אחד בלבד שמחזיק אותו.

זה לא רק הגיוני - זה הכרחי. אם ה-peer היחיד שמחזיק את P3 מתנתק לפני שאספיק להוריד אותו, החתיכה הזו אבדה מה-swarm לחלוטין. לכן rarest-first שם אותו ראשון בתור.

שאלת המשך טבעית: מה אם שני pieces שווים בנדירות, נניח שגם P2 וגם P3 היו עם ספירה 1? כאן `random.choice` שובר את הסימטריה - כדי שכל ה-peers ב-swarm לא ירוצו על אותו seeder יחיד באותו רגע (thundering herd).

---

### Slide 23 - select_piece_rarest_first · קוד מלא
Header kicker: 23 · select_piece_rarest_first · קוד
Title: select_piece_rarest_first - מה הפונקציה עושה, שלב אחר שלב

זו הפונקציה במלואה. בארבע שורות אפקטיביות היא מצמצמת מאות pieces לבחירה אחת.

Code box (LTR):
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

במילים פשוטות: הפונקציה מקבלת רשימה של ה-pieces שה-peer הספציפי הזה מחזיק (לפי ה-BITFIELD שלו), ומחזירה את ה-index של ה-piece שצריך לבקש ממנו.

השלב הראשון מצמצם את הרשימה למועמדים - רק pieces שעוד לא הורדנו (status == MISSING). אם אין כאלה, אין שום דבר לבקש מ-peer הזה ומחזירים None.

השלב השני מחפש את הספירה הנמוכה ביותר מבין המועמדים. `_peer_frequency` הוא dictionary שמתחזק "כמה peers בכלל ה-swarm מחזיקים כל piece" - הוא מתעדכן ב-O(1) בכל הודעת HAVE ו-BITFIELD שמגיעה.

השלב השלישי בונה את ה-tie set - כל ה-pieces שיש להם את הספירה המינימלית הזו. למשל אם שלושה pieces כולם מוחזקים על-ידי 2 peers בלבד, וזה המינימום, יש שלושה מועמדים שווים.

השלב הרביעי הוא ה-`random.choice`. זו שורה קטנה עם משמעות גדולה - אילו תמיד הייתי מחזיר את הראשון, כל ה-peers שמחזיקים את אותו piece היו פונים לאותו seeder בו-זמנית. ה-randomization שובר את הסימטריה ומפזר את העומס על ה-swarm.

---

### Slide 24 - סיבוכיות · O(n)
Header kicker: 24 · סיבוכיות · O(n)
Title: O(n) - מה זה n, ואיך מורידים ל-O(log n)

הסיבוכיות של rarest-first היא O(n) - כאשר n הוא **מספר ה-pieces ב-torrent** (למשל 1,000 pieces ב-torrent של 256MB עם piece_length=256KB). זה נובע ישירות מהמימוש - כל בחירה סורקת את כל המועמדים כדי למצוא את המינימום ולבנות את ה-tie set.

איך היה אפשר להוריד את זה? שתי אופציות:

**Bucket structure** - לתחזק `Dict[count, Set[piece_idx]]` שממפה ספירת נדירות לקבוצת pieces. בחירה הופכת ל-O(1) של חיפוש ה-bucket הנמוך ביותר שאינו ריק, ועדכון ב-HAVE הופך ל-O(1) של הוצאה מ-bucket וכניסה לאחר.

**Min-Heap** - O(log n) בחירה, O(log n) עדכון, אבל מסובך כי ערכים משתנים (decrease-key / increase-key לא מובן מאליו ב-heap).

למה לא יישמתי - ב-1,000 pieces ההפרש בין O(n) ל-O(log n) הוא בערך פי 10, על פעולה שרצה כמה פעמים בשנייה. זה pre-mature optimization שלא היה משפיע על ה-throughput בפועל. הוא מתועד כפיתוח עתידי בספר.

---

### Slide 25 - ביקורת עמוקה · Rarest-First
Header kicker: 25 · ביקורת · Rarest-First
Title: למה rarest-first הוא בעצם בעיית optimization גלובלית

מאחורי כל בחירה דטרמיניסטית מסתתרת בעיה עמוקה יותר. למה לבחור את הנדיר, ולא את הראשון או את האקראי? התשובה הקצרה היא "כי זה עובד יותר טוב" - אבל הסיבה הארוכה מעניינת.

**Survivability** - piece שקיים רק אצל peer אחד הוא piece שיאבד מה-swarm אם אותו peer יתנתק. rarest-first מפיץ אותו מהר כדי שיהיה לו replication, וזה מה שמונע מההורדה להיתקע ברגע שה-seeder יחיד עוזב. אם ה-peer האחרון שמחזיק piece נדיר באמת מתנתק לפני שהורדתי - ההורדה תחכה ל-announce הבא כדי לראות אם הצטרף peer חדש שמחזיק אותו. אם לא - ההורדה תקועה. זו מגבלה מובנית של P2P.

**גלובלי מוסווה כלוקאלי** - המטרה האמיתית של rarest-first היא למקסם availability של כל piece בכל ה-swarm. כל peer מקרב את המטרה הגלובלית הזו עם heuristic מקומי, בלי לתאם עם אחרים.

**Local view** - כל peer רואה רק כ-30 שכנים מתוך אלפים. piece שנראה לו "נדיר" עשוי להיות שכיח בחצי השני של ה-swarm. ההחלטה מבוססת תצפית מוטית, וזו מגבלה שאי-אפשר לעקוף בלי conductor מרכזי.

**Contention** - בלי `random.choice` בתוך ה-tie set, כל ה-peers בוחרים דטרמיניסטית את אותו piece, ונוצר thundering herd על seeder יחיד. ה-randomization שובר את הסימטריה הזו, וזה אחד הדברים הקטנים-אבל-קריטיים במימוש.

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

כל 10 שניות (CHOKE_INTERVAL) ה-_choke_loop רץ ומבצע ארבעה צעדים:

1. ממיין את ה-peers שמעוניינים (interested) לפי תרומתם בחלון 20 שניות.
2. פותח choke ל-top-4 (MAX_UNCHOKED_PEERS).
3. בנוסף - **Optimistic Unchoke** של peer אקראי אחד (גם אם לא תרם בכלל).
4. חוסם (choke) את כל השאר.

הרעיון של Bram Cohen: לוקאלית כל peer מתגמל את מי שתרם לו, וזה יוצר incentive גלובלי לתרומה.

המנגנון המקביל בקוד מפוצל בין שני קבצים - `_tit_for_tat_unchoke` ב-download_manager.py מבצע את המיון והבחירה, ו-`bytes_received_in_window` ב-peer_connection.py מספק את המדד.

---

### Slide 28 - סימולציה · מי מקבל unchoke
Header kicker: 28 · סימולציה · מי מקבל unchoke
Title: 5 peers עם תרומות שונות - מי נבחר ל-top-3?

סימולציה שמדגימה את ה-T4T בפעולה. יש לי 5 peers, וה-MAX_UNCHOKED_PEERS הוא 3. כמה bytes כל אחד מהם העלה אליי בחלון של 20 השניות האחרונות?

| Peer | bytes שהעלו אליי בחלון |
|---|---|
| A | 100 MB |
| B | 80 MB |
| C | 40 MB |
| D | 10 MB |
| E | 0 MB |

התשובה: **A, B, C** נבחרים.

ההיגיון פשוט - ממיינים יורד לפי תרומה: A > B > C > D > E. השלושה הראשונים נכנסים, השאר נחסמים (choke).

אבל יש פיתול: בנוסף ל-top-3 הקבוע, ה-Optimistic Unchoke פותח slot אחד נוסף ל-peer אקראי - לעתים D, לעתים E. וזה לא חוסר היגיון - זה הלב של איך המערכת מתחדשת, כפי שאסביר בשקופית הבאה.

---

### Slide 29 - Optimistic Unchoke
Header kicker: 29 · Optimistic Unchoke
Title: אם E לא תרם - למה בכלל לתת לו הזדמנות?

השאלה מרגישה לא הגיונית במבט ראשון. אם E לא תרם בכלל, למה לתת לו slot על חשבון מישהו שכן תרם?

התשובה היא הבעיה של **cold start**. כל peer חדש מתחיל ב-0. בלי Optimistic Unchoke, ציון 0 פירושו שלעולם לא ייכנס לדירוג, לעולם לא יקבל ממני data, ולעולם לא יתן לי data בחזרה. הוא נשאר ב-0 לנצח. זו lock-out מערכתית.

Optimistic Unchoke הוא **דלת הכניסה למערכת**. הוא בודק: "אולי ה-peer הזה דווקא חזק, אבל פשוט לא היה לו הזדמנות?" אם מתברר שהוא תורם - בסיבוב הבא הוא ייכלל ב-top-K באופן רגיל ויעבור לטרק הראשי. אם לא תורם - ה-slot שלו נסגר ועובר ל-peer אחר ב-tick הבא.

בלי המנגנון הזה המערכת הופכת ל-closed club - top-4 הראשונים שתפסו slot ישארו שם לנצח, וכל peer חדש (אפילו אם הוא חזק יותר מהם) לא יוכל להוכיח את עצמו. Optimistic Unchoke הוא mechanism של exploration לעומת ה-exploitation של ה-top-K.

---

### Slide 30 - Round Robin מול T4T
Header kicker: 30 · Round Robin מול T4T
Title: למה Round Robin גרוע יותר מ-Tit-for-Tat

חלופה תיאורטית ל-T4T היא Round Robin - פתיחת choke בתורות, כל peer מקבל את שלו בסבב.

זה נשמע "הוגן" - אבל זה בדיוק הבעיה. Round Robin מתייחס באופן שווה ל-peer שתורם 100MB ול-peer שלא תורם כלום. כל אחד מקבל את ה-slot בתורו, אז אין שום סיבה ל-peer לתרום - הוא ייפתח choke ממילא בסיבוב הבא.

זה מבטל את המנגנון שעליו BitTorrent כולו נשען. free-riders מצליחים, וכל ה-swarm נכנס בהדרגה למצב של "כולם מורידים, אף אחד לא מעלה" - בדיוק המצב ש-BitTorrent בא לפתור וש-Gnutella סבל ממנו.

T4T יוצר תחרות. peer שלא מעלה לי, לא מקבל ממני. זו תורת משחקים בפעולה.

במימוש שלי שני האלגוריתמים זמינים (`--peer-algorithm round_robin` כ-baseline) - בדיוק כדי שאוכל להראות אמפירית את ההבדל.

---

### Slide 31 - T4T לעומק · שלוש שכבות
Header kicker: 31 · T4T לעומק · שלוש שכבות
Title: Sliding Window + Snubbing + Seeding Mode

- **Sliding Window (20s)** - המדד הוא לא bytes_downloaded מצטבר, אלא כמה bytes ה-peer שלח לי ב-20 השניות האחרונות. למה: עם מונה מצטבר, peer שתרם בהתחלה והשתתק שומר ציון גבוה לנצח. 20 שניות = שני מחזורי choke -> מדד יציב ולא מרצד. ממומש ב-`bytes_received_in_window` ב-peer_connection.py.

- **Snubbing (60s)** - peer ש-unchoked אותי אבל לא שלח data במשך 60 שניות מסומן snubbed, מקבל עדיפות נמוכה, ומפנה slot ל-peer אחר. בלי זה, peer באגי או זדוני תופס slot בלי לתת. ממומש ב-`is_snubbed` ב-peer_connection.py, וההפרדה ל-snubbed/non-snubbed נמצאת ב-tit-for-tat ב-download_manager.py.

- **Seeding Mode** - T4T הוא אלגוריתם של leecher ("מי נותן לי?"). כש-seeder אין מה להוריד, אז המדד מתהפך: ממיינים לפי כמה אני **מעלה** לכל peer (bytes_sent_in_window) - "למי אני יכול לתת הכי מהר?". ממומש ב-`_maybe_enter_seeding` ב-download_manager.py.

שלושת אלה ניתנים לבדיקה - 44 בדיקות ב-test_download_manager.py מכסות אותם.

---

### Slide 32 - ביקורת עמוקה · T4T
Header kicker: 32 · ביקורת · T4T
Title: T4T אינו "הוגן" - חולשות שצריך להכיר

T4T עובד בפרקטיקה, אבל הוא רחוק מ"הוגן". כמה מקומות שהוא נשבר:

**סיבוכיות במיון** - O(m log m) ל-m peers, כי זה מיון השוואתי (Timsort) של כל ה-peers בכל choke tick. ב-500 peers זה כ-4,500 השוואות פעם ב-10 שניות - לא נורא, אבל אופטימיזציה אמיתית הייתה לעדכן רק את ה-peers שתרומתם השתנתה מהסיבוב הקודם, או heap מותאם לבעיית decrease-key.

**Asymmetric bandwidth** - לקוח ביתי 100/10 (download/upload). peer עם upload חלש מוצף בבקשות שאינו יכול להחזיר reciprocally, ונראה "קמצן" גם אם נתן את המקסימום שלו. ה-window וה-optimistic unchoke ממתנים את זה, אבל לא פותרים לחלוטין.

**BitTyrant (NSDI 2007)** - לקוח אקדמי שמראה איך מנצלים: שולחים לכל peer את המינימום הנדרש כדי להישאר unchoked, וחוסכים upload כדי להפיץ ליותר peers בו-זמנית. הגנה מ-BitTyrant לא קיימת במימוש שלי, כמו ברוב הלקוחות.

**Contribution measurement** - מודדים bytes, לא ערך. piece נדיר ששווה זהב נחשב כמו piece שכיח. תיקון לכך היה דורש מערכת ערך-אינפורמטיבית של pieces, שלא קיימת ב-BEP-3.

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

**Bencode** - פורמט סריאליזציה של 4 טיפוסים: מספר (`i42e`), מחרוזת (`4:spam`), רשימה (`l...e`), מילון (`d...e`).

מילון בקידוד **קנוני** - מפתחות ממוינים, ללא zero-padding במספרים. זה קריטי עבור info_hash.

**info_hash** - תעודת הזהות של ה-torrent. SHA-1 על ה-`info` dict אחרי **re-encode** ל-Bencode קנוני (לא על הבייטים המקוריים של הקובץ).

למה re-encode: קובץ torrent שנוצר בתוכנה אחרת עשוי לסדר מפתחות אחרת; re-encode מבטיח hash זהה לכל ה-peers וה-trackers בעולם.

למה רק על `info` ולא על כל הקובץ: שדות חיצוניים (announce, comment, created_by) משתנים בין trackers שונים של אותו torrent. רק `info` מזהה את התוכן עצמו.

חישוב ה-info_hash נמצא ב-torrent_metadata.py בפונקציה `_compute_info_hash`. המיון של מילונים ב-Bencode נמצא ב-bencode.py, ולצדו אכיפה של סדר ממוין בפענוח (כדי לפסול קלט שאינו קנוני).

---

### Slide 35 - PEER WIRE · Handshake (68 בתים)
Header kicker: 35 · PEER WIRE · HANDSHAKE
Title: 68 בתים מדויקים - והבדיקה ל-info_hash תואם

ה-handshake הוא ההודעה הראשונה שכל peer שולח כשהוא פותח חיבור - 68 בתים בדיוק, ומבנה קשיח:

| אופסט | גודל | שדה | ערך |
|---|---|---|---|
| 0 | 1 | pstrlen | 19 |
| 1 | 19 | pstr | "BitTorrent protocol" |
| 20 | 8 | reserved | 0x00 × 8 |
| 28 | 20 | info_hash | SHA-1 של info dict |
| 48 | 20 | peer_id | מתחיל ב-"-PG0001-" |

שלוש בדיקות מתבצעות על handshake נכנס: pstrlen חייב להיות 19, ה-pstr חייב להיות בדיוק "BitTorrent protocol", וה-info_hash חייב להיות זהה לשלי.

מה קורה אם peer שולח info_hash שונה? - ניתוק מיידי. אסור להמשיך, כי שני הצדדים מצביעים על תוכן שונה לחלוטין. זה לא רק "torrent אחר" - זה גם מתאר peer שלא צריך להיות באותו swarm.

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

### Slide 36 - TCP · Length-Prefixed Framing
Header kicker: 36 · TCP · FRAMING
Title: TCP הוא stream - אנחנו ממציאים את גבולות ההודעה

TCP מבטיח **סדר** ו**ללא אובדן**, אבל אין לו שום מושג של "גבולות הודעה". `recv(1024)` עלול להחזיר חצי הודעה ועוד שליש מהבאה - או רק 100 בתים מתוך 1024 שביקשתי. הפרוטוקול חייב להמציא את הגבולות בעצמו.

אחרי ה-handshake, כל הודעה ב-BEP-3 היא:

```
[4 bytes: length (big-endian)] [1 byte: msg_id] [payload...]
```

length=0 פירושו keep-alive. length=N פירושו 1 byte של msg_id ועוד N-1 בתים של payload.

ה-parser עובד בשלושה שלבים: קורא 4 בתים שהם האורך (`readexactly(4)`), בודק שהאורך לא מטורף (MAX_MESSAGE_SIZE = 2MB), ואז קורא את ה-payload המלא (`readexactly(length)`) - asyncio מטפל בפיצול הפנימי לבד.

הבדיקה ל-MAX_MESSAGE_SIZE היא הגנה קריטית. מה אם תוקף שולח length = 4GB? בלי בדיקה, ה-Engine מנסה להקצות buffer של 4GB ונופל ב-OOM crash. עם הבדיקה - מנותקים מיידית. הקבוע MAX_MESSAGE_SIZE נמצא בראש peer_connection.py.

בסך הכול יש 10 סוגי הודעות: CHOKE(0), UNCHOKE(1), INTERESTED(2), NOT_INTERESTED(3), HAVE(4), BITFIELD(5), REQUEST(6), PIECE(7), CANCEL(8), KEEP_ALIVE(-1).

---

### Slide 37 - asyncio · await
Header kicker: 37 · asyncio · await
Title: await reader.read() מול socket.recv() - אותו תחביר, סמנטיקה הפוכה

ההבדל בין `await reader.read()` ל-`socket.recv()` הוא תחבירית קטן וסמנטית עצום.

`socket.recv()` חוסם את ה-thread עד שיגיעו בתים. ה-CPU לא יכול לעשות שום דבר אחר ב-thread הזה. אם יש 50 peers, צריך 50 threads.

`await reader.read()` משחרר את ה-event loop. אם אין בתים זמינים, ה-loop רץ קואורוטינות אחרות (peers אחרים, choke loop, keep-alive). כשהבתים מגיעים, ה-loop מחזיר שליטה לכאן.

המסקנה: עם asyncio, thread יחיד מנהל את כל ה-50 peers וגם את ה-scheduling - כי רוב הזמן כולם מחכים. בלי asyncio - היה צריך 50 threads.

מלכודת מסוכנת: כל פעולה חוסמת ששוכחים להעביר ל-executor (כמו `hashlib.sha1` על piece שלם, או כתיבת דיסק עם `open().write()`) חוסמת את **כל** ה-loop, וכל ה-peers קופאים יחד. בדיוק לכן אימות SHA-1 וכתיבה לדיסק רצים אצלי ב-ThreadPoolExecutor.

---

## חלק ו - אבטחה ושלמות

---

### Slide 38 - Divider F
Full blue divider.
- אות גדולה: F
- חלק ו - אבטחה ושלמות
- כיתוב משנה: SHA-1, piece מול block, peer זדוני, ומערכת המוניטין

---

### Slide 39 - אימות PIECE · SHA-1
Header kicker: 39 · אימות · SHA-1
Title: הורדתי piece - מה בדיוק נבדק?

נקודה חשובה לבחינה: מה בדיוק קורה כשגומרים להוריד piece? התהליך הוא ארבעה שלבים מסודרים.

ראשון - כל ה-blocks של ה-piece התקבלו. ה-`submit_block` מחזיר `is_complete=True` כשכל ה-blocks סומנו כ-received. שני - מחשבים `SHA-1` חדש על כל ה-bytes של ה-piece שהורכבו. שלישי - משווים מול ה-hash הצפוי שמופיע בשדה `pieces` בקובץ ה-.torrent (20 בתים לכל piece). רביעי - אם שונה: ה-piece נפסל. blocks נמחקים מהזיכרון, ה-piece חוזר למצב MISSING, וה-peer ששלח את ה-block האחרון מקבל hash_failure במערכת המוניטין.

Code box (LTR):
```python
# piece_manager.py
def verify_hash(self) -> bool:
    actual = hashlib.sha1(self._data).digest()
    return actual == self.expected_hash
```

למה לעשות hash piece-by-piece ולא על כל הקובץ בסוף? שלוש סיבות. גילוי מוקדם - piece פגום מתגלה מיד, לא רק בסוף ההורדה אחרי שהשקעתי בו גיגות. שיוך לאשם - יודעים מי שלח את ה-block הפגום, אז אפשר ל-ban אותו. שחזור מקומי - רק ה-piece המקולקל מתבקש מחדש, לא כל הקובץ.

פונקציית `verify_hash` נמצאת ב-piece_manager.py.

---

### Slide 40 - PIECE מול BLOCK
Header kicker: 40 · PIECE מול BLOCK
Title: למה יש שני מושגים שונים - והקשר ל-submit_block

שני מושגים שקל לבלבל ביניהם, אבל הם פותרים שתי בעיות שונות.

**Piece** הוא יחידת אימות. הוא מגיע בגודל קבוע מקובץ ה-.torrent (לרוב 256KB) ויש לו SHA-1 צפוי שהוגדר מראש. **Block** הוא יחידת בקשה. הוא בגודל 16KB (BLOCK_SIZE), וזו הגדרה של ה-protocol עצמו - בקשת REQUEST אחת לא יכולה להיות גדולה מ-16KB. לכן piece של 256KB מורכב מ-16 blocks.

השאלה המתבקשת: למה לא לבקש piece שלם בבקשה אחת? - כי בקשת 256KB מ-peer יחיד פירושה ש-throughput שלי תלוי בו לבד. עם 16 בקשות של 16KB אפשר לפזר על כמה peers במקביל - וזה pipelining שמכפיל מהירות.

איך submit_block יודע מתי piece שלם? כל Block מחזיק שדה `received: bool`. כש-`Piece.submit_block(offset, data)` מסמן את ה-block הנכון כ-received, הוא בודק האם **כל** ה-blocks ב-piece מסומנים. אם כן, מחזיר True (סיגנל ל-DownloadManager להפעיל verify_hash). אם לא, מחזיר False וממשיכים לחכות.

---

### Slide 41 - Peer זדוני · מה קורה
Header kicker: 41 · Peer זדוני · מה קורה
Title: peer שולח לי piece שגוי - חמישה שלבים אוטומטיים

תרחיש קלאסי - peer שולח לי piece שגוי. מה בדיוק קורה?

חמישה שלבים אוטומטיים מתבצעים בזה אחר זה.

**Reject** - ה-SHA-1 לא תואם, ה-piece לא נכתב לדיסק, blocks נמחקים מהזיכרון, וה-piece חוזר למצב MISSING.

**Log** - אירוע נכתב ל-event log וב-SQLite ל-events table.

**Reputation Penalty** - `SecurityManager.report_hash_failure` מעלה את מונה הכשלים של ה-peer.

**Ban** - אחרי 3 כשלי hash (MAX_HASH_FAILURES_PER_PEER) או 5 הפרות פרוטוקול - ניתוק וחסימה קבועה.

**Re-request** - רק אז ה-piece מתבקש שוב מ-peer אחר.

אלו האירועים שמורידים את הציון של peer במערכת המוניטין:
- כישלון אימות SHA-1.
- הפרת פרוטוקול: handshake לא תקין, אורך הודעה > 2MB, HAVE עם index מחוץ לטווח, BITFIELD בגודל שגוי, REQUEST על piece שאין לי.
- timeout חוזר (אופציונלי - יותר חלש מהפרה).

המנגנון המלא מפוצל בין כמה קבצים - `report_hash_failure` ו-`report_protocol_violation` ב-security.py, והקריאות אליהן מ-download_manager.py בנתיבי ה-PIECE וה-message handling.

---

### Slide 42 - ביקורת עמוקה · Reputation ו-Sybil
Header kicker: 42 · ביקורת · Reputation
Title: למה מוניטין לא פותר Sybil - והגבולות של ההגנה

מערכת המוניטין נראית רובוסטית - אבל יש לה חולשות יסודיות שכדאי להכיר לפני שהבוחן ישאל.

**Sybil attack** - תוקף יוצר 1,000 peer_id שונים (כל אחד 20 בתים אקראיים בלבד). כל אחד נחסם אחרי 3 כשלי hash, אבל הבא מוכן. המוניטין הוא **per-identity**, לא **per-attacker**. אין לי דרך לזהות שכל ה-peer_id האלה שייכים לאותו תוקף.

**New peer problem** - peer חוקי חדש מתחיל ב-reputation 0, בדיוק כמו peer חשוד. אין שום הבחנה ביניהם, וזה עלול לעכב peers טובים בשלב המוקדם.

**False positives** - 3 timeouts מתקלת רשת זמנית = ban קבוע. אין decay (התאוששות עם הזמן) או second chance. peer חוקי שסבל מ-3 דקות של רשת רעועה - חסום לעולם.

**Eclipse attack** - tracker זדוני יכול להחזיר רק peers שבשליטתו. אם כל ה-peers שלי מאותו attacker, אז rarest-first מקבל מידע מזויף וכל ה-bitfields שקריים. ההגנות החלקיות במימוש: ולידציית פורמט (compact = 6×N בתים), אכיפת interval מינימלי. הפתרון האמיתי הוא DHT + multi-tracker, ולא קיים אצלי.

למה זה בכל זאת לא חיסרון מבייש - כל אלה ידועים מהמחקר (BitTyrant, Sybil), אף לקוח production לא פותר את כולם. ההכרה בהם מצביעה על הבנה עמוקה ולא על הסתרה.

---

## חלק ז - מצב, scale, וכשל

---

### Slide 43 - Divider G
Full blue divider.
- אות גדולה: G
- חלק ז - מצב, scale, וכשל
- כיתוב משנה: resume, מיליון peers, נפילת tracker, ובאמת מבוזר?

---

### Slide 44 - Pause / Resume · שמירת מצב
Header kicker: 44 · Pause / Resume · שמירת מצב
Title: אילו רכיבים חייבים לשמור State כדי לאפשר Resume אמיתי

Resume אמיתי דורש לשמור state של שלושה רכיבים שונים.

**PieceManager** - אילו pieces COMPLETED, אילו IN_PROGRESS, אילו MISSING. נשמר ב-JSON.

**DownloadManager** - איזה download_dir, אילו אלגוריתמים נבחרו, מהו ה-state (RUNNING/PAUSED/COMPLETED/SEEDING).

**Sidecar .torrent** - העתק של קובץ ה-.torrent המקורי, כדי שלא נצטרך לבקש אותו מהמשתמש שוב.

הסיפור המלא: `_save_state` קיים מההתחלה. מה שלא היה במימוש המקורי הוא `_load_state` - וזה היה נקודת ביקורת בספר. התיקון: `Download.from_state_file()` בונה download מ-JSON + sidecar .torrent, וקריטית - **קורא מהדיסק כל piece שהושלם ומאמת SHA-1 מחדש** לפני שסומכים עליו. piece פגום בדיסק חוזר ל-MISSING.

ב-startup, `DownloadManager.restore_state()` סורק את כל קבצי ה-JSON ב-`data/state/` ומשחזר הורדות במצב PAUSED. המשתמש מבקש Resume במפורש - לא אוטומטית.

הורדות שכבר נגמרו (COMPLETED/SEEDING) או בוטלו (CANCELLED) לא משוחזרות - קבצי ה-state שלהן נמחקים. הקובץ עצמו בדיסק נשמר.

המימוש מפוזר בין `Download.from_state_file` ו-`DownloadManager.restore_state` ב-download_manager.py.

---

### Slide 45 - Scale · 1M peers
Header kicker: 45 · Scale · 1M peers
Title: מה נשבר ראשון בסקייל קיצוני

תרגיל מחשבתי - אם הייתי מתחיל הורדה עם מיליון peers, מה היה נשבר ראשון?

**TCP Connections** - מערכת ההפעלה מגבילה את מספר ה-file descriptors הפתוחים לתהליך, בדרך כלל ב-1024 (ulimit). זה הראשון שנשבר, הרבה לפני 1M peers.

**זיכרון** - כל PeerConnection מחזיק buffers, bitfield ומבני state. 1M × ~כמה KB = גיגות.

**Event Loop scheduling** - asyncio יעיל אבל לא קסם. 1M coroutines פעילים יוצרים latency גבוה בכל context switch לוגי.

**Bandwidth** - גם אם הכל היה אופטימלי, ה-bandwidth שלי לא משתנה בגלל מספר ה-peers.

מה שמעניין הוא מה **לא** נשבר - rarest-first עצמו. הוא O(num_pieces), לא O(num_peers). כל הוספת peer רק מעדכנת את `_peer_frequency` ב-O(num_pieces_of_that_peer), שזה למעשה O(1) ל-bitfield update בודד.

בסקייל יותר מציאותי - 1,000 pieces × 200 peers, כמה זיכרון PieceManager צריך?
- `_peer_frequency`: 1,000 pieces × int = ~8KB.
- `_peer_pieces`: 200 peers × Set של ~1,000 ints = ~5.6MB.
- כל peer מחזיק BITFIELD של 1,000 ביטים = 125 בתים.

סך הכול: זיכרון בסדר גודל של MB ספורים. לחלוטין סביר.

---

### Slide 46 - ארכיטקטורה · עד כמה מבוזר
Header kicker: 46 · ארכיטקטורה · עד כמה מבוזר
Title: נפילת tracker, האם זה באמת מבוזר, ומה DHT היה משנה

שלוש שאלות שמתחברות. מה אם tracker יחיד נופל? האם זה באמת מבוזר אם יש tracker מרכזי? ומה DHT היה משנה?

ה-tracker הוא SPOF (Single Point of Failure) לגילוי peers ראשוני. בלעדיו לא מוצאים swarm חדש. במימוש שלי יש תמיכה ב-announce-list (רשימת trackers backup) - אם הראשון נופל, ננסה את השני. peers שכבר מחוברים ממשיכים לעבוד גם כש-tracker מת, אז ההורדה לא נופלת מיידית.

כנה - זה לא מבוזר לחלוטין. ה-content distribution מבוזר (כל peer מחזיק ומשרת חלק), אבל ה-peer discovery מרוכז ב-tracker. זו הייתה הביקורת המקורית על BEP-3 מההתחלה.

מה היה משתנה עם DHT? יישתנו: `tracker_client.py` (שאילתות DHT במקום HTTP), והוספת מודול חדש כמו `dht_client.py` שמיישם Kademlia. **לא** יישתנו: `peer_connection.py` (אחרי שיש לי IP:port, לא משנה איך השגתי אותו), `piece_manager.py`, `download_manager.py`, `bencode.py`, `security.py`.

זו ההצדקה ההנדסית להפרדה - DHT הוא decentralized peer discovery, וההפרדה הברורה בין discovery לבין connection מאפשרת להחליף את הראשון בלי לגעת בשני.

---

## חלק ח - תרחישי קצה ותוצאות

---

### Slide 47 - תרחיש קצה · Bitfields משקרים
Header kicker: 47 · קצה · Bitfields משקרים
Title: מה אם 20% מה-peers משקרים על מה שיש להם

תרחיש קצה שכדאי לחשוב עליו. כל מנגנון rarest-first מניח שה-bitfield וה-HAVE שמגיעים מ-peers הם אמינים. מה אם 20% מה-peers משקרים ומדווחים על pieces נדירים שאין להם בכלל?

התשובה הכנה: כן, האלגוריתם יכול להתחיל לקבל החלטות גרועות. peer משקר מופיע בספירת ה-rarity של pieces נדירים, ובכך הם נראים פחות נדירים - ה-rarest-first מוריד אותם פחות בעדיפות, וה-survivability האמיתי שלהם יורד. וכשאני בוחר לבקש מ-peer ש"מחזיק" את ה-piece הנדיר - הוא לא יכול לשלוח, אז יש timeout, ספירת ה-snubbing עולה, ולבסוף ban.

ההגנה החלקית במימוש: snubbing ו-reputation מסמנים את ה-peer הזה כבעייתי תוך 60 שניות.

ההגנה הקריטית שחסרה: ולידציה הדדית - לוודא ש-peer באמת מחזיק piece לפני שסומכים על ה-BITFIELD שלו. זה לא קיים ב-BEP-3 עצמו - זו מגבלת הפרוטוקול, לא של המימוש.

מסקנה כללית: BitTorrent מניח **אמון חלקי** - מאמת תוכן (SHA-1) אבל לא מאמת metadata (BITFIELD). זה ידוע ומקובל.

---

### Slide 48 - תרחיש קצה · תרומה פגומה
Header kicker: 48 · קצה · תרומה פגומה
Title: peer זדוני ששולח data רב - האם T4T ידרג אותו גבוה?

זו נקודת תפר ארכיטקטונית עדינה. Tit-for-Tat מתגמל peers שתורמים יותר. נניח peer זדוני ששולח data רב, אבל הכול פגום. האם T4T ידרג אותו גבוה?

בקוד הנוכחי - `bytes_received_in_window` סופר bytes שהתקבלו, **לפני** אימות SHA-1. מבחינת המדד, peer ששולח 100MB פגומים נראה זהה ל-peer ששולח 100MB תקינים. כן, T4T ידרג אותו גבוה - באופן זמני.

ההצלה היא ש-`SecurityManager.report_hash_failure` חוסם אותו אחרי 3 כשלים. ברגע שהוא מנותק, הוא נעלם מ-`_connections` ולא יופיע בסיבוב הבא של T4T. בפועל ההגנה היא timing-based: 3 כשלים מתרחשים הרבה לפני שה-peer מספיק להגיע ל-top-4.

איפה היה צריך לתקן את הארכיטקטורה? למדוד תרומה רק על blocks שעברו אימות SHA-1 (verified_bytes_received_in_window). זה דורש לחבר את ה-PieceManager (שיודע אם piece עבר verify) ל-PeerConnection (שמחזיק את ה-window). תיקון אפשרי, לא קריטי - אבל זה בדיוק סוג השאלה שמראה מודעות ארכיטקטונית.

---

### Slide 49 - תרחיש קצה · נפילת trackers
Header kicker: 49 · קצה · נפילת trackers
Title: כל ה-trackers נופלים - האם זה עדיין BitTorrent?

השאלה הכי עמוקה משלושת תרחישי הקצה. כל ה-trackers בעולם נופלים. עד כמה זה עדיין BitTorrent? האם rarest-first, choke ו-piece verification עדיין שווים משהו?

התשובה תלויה במי שואלים. למשתמש חדש שמתחיל הורדה - שווה אפס. בלי tracker אין peer discovery ראשוני, החיבור הראשון לא קורה, הכל מתחיל מ"רשימת peers ריקה" ותקוע.

אבל למשתמש שכבר באמצע הורדה - שווה הכל. כל ה-peers ש**כבר** מחוברים ממשיכים לעבוד; rarest-first ממשיך לעבוד מולם; T4T ממשיך; SHA-1 ממשיך לאמת. ההורדה תסתיים, רק לא יצטרפו peers חדשים.

ההבנה: ה-tracker הוא bootstrap, לא תזמורת. ברגע שיש לך swarm - הוא מתחזק את עצמו לזמן מסוים. אבל לא לנצח - peers מתנתקים (churn), ובלי הצטרפויות חדשות ה-swarm דועך בהדרגה, ו-pieces נדירים עלולים להיעלם.

ה-DHT (BEP-5) קיים בדיוק כדי לפתור את זה - peer discovery בלי tracker מרכזי, כל peer גם משמש בעצמו כצומת ב-distributed hash table. אצלי DHT לא מומש, כי הוא פרוטוקול נפרד בגודל BEP-3 לכל הפחות. מתועד כפיתוח עתידי.

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

### Slide 54 - חולשה ארכיטקטונית · האמת באמצע
Header kicker: 54 · חולשה ארכיטקטונית · האמת באמצע
Title: מימוש Production או סימולציה חינוכית

שאלה לגיטימית לשאול בסוף: זו מערכת Production או סימולציה חינוכית של הרעיונות?

התשובה הכנה - האמת באמצע, נוטה לחינוכית.

**מה זה כן** - מימוש BEP-3 אמיתי. כל הודעה רצה על socket TCP אמיתי. SHA-1 מאמת. הקובץ נכתב לדיסק. ההורדה עובדת מול clients אחרים שמדברים BEP-3 (נבדק).

**מה זה לא** - לא Production. החסר מתועד:
- אין קבלת חיבורים נכנסים / NAT traversal (start_server לא קיים).
- אין DHT (BEP-5) - peer discovery בלי tracker מרכזי.
- אין PEX (BEP-11) - החלפת רשימות peers בין peers.
- אין הצפנת peers (MSE/PE) - ISP יכול לזהות תעבורת BitTorrent ב-DPI.
- אין UDP tracker, אין IPv6, אין magnet links.
- רק BEP-3 (v1) - לא BEP-52 (SHA-256 + Merkle Trees).
- rarest-first הוא O(n) ולא Bucket/Heap - יספיק עד מאות pieces, לא מליונים.

למה זה מספיק לפרויקט י"ד - הוכחת הבנה של כל מנגנון מרכזי, כולל ביקורת על הגבולות שלו. Production דורש שנים של עבודה ו-team שלם.

---

### Slide 55 - תודה / שאלות
Layout: closing slide.
Title: תודה · שאלות?

- מגיש: אדם זבולון · מנחה: גל בראון
- פרויקט: מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent
- מעבר לשקופית הבאה כדי להראות איפה כל מנגנון מרכזי נמצא בקוד.

---

## נספח - מיקום בקוד

---

### Slide 56 - Divider · מיקום בקוד
Full blue divider.
- אות גדולה: Q
- נספח · מיקום בקוד
- כיתוב משנה: היכן כל מנגנון מרכזי נמצא בקוד, לקפיצה מהירה בזמן ההגנה

---

### Slide 57 - מפת מיקום בקוד
Header kicker: 57 · נספח · מיקום בקוד
Title: בדיוק איפה כל מנגנון נמצא בקוד

טבלה לקפיצה ישירה מתוך IDE בזמן ההצגה.

| # | המנגנון | קובץ | מקטע / שורה לציון |
|---|---|---|---|
| 1 | חישוב info_hash | `python_engine/torrent_metadata.py` | פונקציית `_compute_info_hash` (~שורה 100-102): `hashlib.sha1(bencode.encode(info_dict)).digest()` - אחרי re-encode קנוני |
| 2 | piece rarity count | `python_engine/piece_manager.py` | מבנה `_peer_frequency: Dict[int, int]` ועדכון ב-`add_peer_bitfield` / `record_have`; הקריאה ב-`select_piece_rarest_first` |
| 3 | peer sorting ב-Tit-for-Tat | `python_engine/download_manager.py` | `_tit_for_tat_unchoke` - `sorted(candidates, key=lambda p: p.bytes_received_in_window(20.0), reverse=True)` |
| 4 | SHA1(piece) verification | `python_engine/piece_manager.py` | `Piece.verify_hash`: `hashlib.sha1(self._data).digest() == self.expected_hash` |
| 5 | negative reputation ל-peer | `python_engine/security.py` | `SecurityManager.report_hash_failure` ו-`report_protocol_violation`; הקריאה אליהן מ-`download_manager.py` כש-SHA-1 נכשל או כשאורך הודעה > 2MB |

הערה ל-Adam: בזמן ההצגה, פתח את הקובץ ב-IDE עם split view (קוד משמאל, ההצגה מימין), כך שתוכל לקפוץ ל-grep ישיר אם הבוחן ביקש.
