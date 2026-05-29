# slides.md - full deck content (transcribe into the pptx)

Order is final. Each slide block gives the header kicker, the title, and the
body. Follow the rules in README.md (Hebrew RTL, no long dashes, " - " only).

Legend: `[[SCREENSHOT: name]]` = empty image frame with the given caption.

---

## חלק א - רקע, בעיה, ומטרות

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
Title: מה נכסה ב-20 הדקות הבאות

- חלק א · 6 דק׳ - רקע, הבעיה, מטרות, וחלופות שנשקלו
- חלק ב · 10 דק׳ - ארכיטקטורה, אלגוריתמים (בחירת piece ובחירת peer), פרוטוקול, אבטחה, וקונקורנציה
- חלק ג · 4 דק׳ - שמירת מצב, תוצאות אמפיריות, ממשק, בדיקות, ומסקנות
- נספח - 10 שאלות עומק + 7 שאלות קוד (לקפיצה מהירה בזמן ההגנה)

---

### Slide 3 - Divider A
Full blue divider.
- אות גדולה: A
- חלק א - רקע, בעיה, ומטרות
- כיתוב משנה: מה זה BitTorrent, איזו בעיה הוא פותר, ולמה בחרתי בו

---

### Slide 4 - רקע
Header kicker: 04 · רקע · BITTORRENT
Title: פרוטוקול P2P אחד פתר את בעיית התמרוץ של שיתוף קבצים

- Napster (1999) הוכיח את ה-P2P אבל נפל בגלל שרת מרכזי - נקודת כשל יחידה.
- Gnutella ו-Kazaa ניסו בלי שרת, אבל בלי מנגנון תמרוץ.
- BitTorrent של Bram Cohen (2001) פתר את הבעיה המרכזית: איך לתמרץ peers לתרום upload bandwidth כשאין שום מנגנון אכיפה מרכזי.
- הפתרון - Tit-for-Tat - הפך לסטנדרט דה-פקטו. עד היום BitTorrent דומיננטי בשיתוף פתוח: הפצות לינוקס, Internet Archive, עדכוני משחקים.
- צד שמאל (highlight): BEP-3 הוא ~30 עמודים, אבל מאחוריו מסתתרים תורת משחקים, פרוטוקול רשת גולמי, קריפטוגרפיה, וקונקורנציה - כולם נדרשים למימוש.

---

### Slide 5 - הבעיה
Header kicker: 05 · הבעיה
Title: איך לתאם הורדת קובץ גדול מ-N peers בו-זמנית, בלי תיאום מרכזי

שלוש תתי-בעיות שכולן חייבות להיפתר במקביל:

- תת-בעיה 1 - איזה piece לבקש? בחירה גלובלית מתוך מאות עד אלפי חלקים. בחירה גרועה -> bottleneck כשה-seeder היחיד מתנתק. (Rarest-First מול Random)
- תת-בעיה 2 - למי לפתוח choke? בעיית תורת משחקים: איך לעודד peers לתרום bandwidth בלי אכיפה. (Tit-for-Tat מול Round-Robin)
- תת-בעיה 3 - איך לאמת תוכן שמגיע מ-peer לא מהימן? (אימות SHA-1 לכל piece)

---

### Slide 6 - מטרות הפרויקט
Header kicker: 06 · מטרות הפרויקט
Title: שש מטרות ספציפיות, כולן מומשו ונבדקו

- פענוח .torrent ותקשורת עם trackers - Bencode encoder/decoder, חישוב info_hash, פרסור compact peer list.
- תקשורת peer-to-peer מלאה - Peer Wire Protocol לפי BEP-3: handshake של 68 בתים, state machine, ו-10 סוגי הודעות.
- אלגוריתמי בחירה איכותיים - Rarest-First לבחירת piece, ו-Tit-for-Tat עם sliding window, snubbing, ומצב seeding לבחירת peer, לצד baselines (random, round-robin) להשוואה.
- העלאה אמיתית - שירות בקשות REQUEST מ-peers מחוברים (לא רק הורדה).
- אבטחה ושלמות - אימות SHA-1 per piece, ולידציית פרוטוקול, ומערכת מוניטין שמסמנת peers זדוניים.
- ממשק משתמש שלם - Java Swing עם טבלת הורדות חיה, יומן, היסטוריה, וגרפי סטטיסטיקה.

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

---

## חלק ב - ארכיטקטורה ואלגוריתמים

---

### Slide 8 - Divider B
Full blue divider.
- אות גדולה: B
- חלק ב - ארכיטקטורה ואלגוריתמים
- כיתוב משנה: איך המערכת בנויה, אילו אלגוריתמים בחרתי, ולמה - כולל הביקורת על הבחירות

---

### Slide 9 - ארכיטקטורה · מבט-על
Header kicker: 09 · ארכיטקטורה · מבט-על
Title: שני תהליכים, גשר REST, ומסד נתונים מקומי

`[[DIAGRAM: architecture]]`
Caption: תרשים ארכיטקטורה - Java GUI ⇄ Python Engine (REST), וה-Engine מול Tracker (HTTP) ומול Peers (TCP/BEP-3).
Note to Adam: render docs/Fig-02.md (רמה 1 - Top Level) at https://mermaid.live and paste the PNG/SVG here. It is the main visual of the slide.

Caption / talking points (small, under the diagram):
- מסגרת כחולה = רכיב פנימי (Java GUI, Python Engine); מסגרת כתומה = חיצוני (Tracker, Peers).
- הגשר GUI<->Engine: REST/JSON על 127.0.0.1:5000 (14 endpoints, polling כל 500ms). אין חשיפה לרשת חיצונית.
- ה-Engine מדבר עם ה-tracker ב-HTTP ועם ה-peers ב-TCP/BEP-3. מסד נתונים מקומי: SQLite (history, stats, events) בצד ה-Engine.

---

### Slide 10 - החלטת תכנון · ההפרדה
Header kicker: 10 · החלטת תכנון · ההפרדה
Title: למה שני תהליכים, ולמה דווקא REST

- Python ל-Engine - asyncio מצוין לעשרות חיבורי TCP מקבילים, hashlib ו-struct מתאימים לפרוטוקול בינארי, sqlite3 ב-stdlib.
- Java ל-GUI - Swing הוא toolkit בוגר עם JTable, JProgressBar, ו-EDT לעדכון בטוח של הממשק.
- למה REST/JSON כגשר - שפה-אגנוסטי (לא משנה באילו שפות שני הצדדים כתובים), קל לבדיקה עם curl, ובידוד שגיאות ברור.
- חלופות שנדחו: JNI (מסבך deployment), gRPC (כבד מדי לפרויקט), named pipes (לא portable).

---

### Slide 11 - רכיבי המערכת
Header kicker: 11 · רכיבי המערכת
Title: מודולים בעלי אחריות יחידה - Python Engine + Java GUI

Python Engine (~4,260 שורות):
| מודול | אחריות | שורות |
|---|---|---|
| bencode.py | קידוד/פענוח Bencode + ולידציית פורמט קנוני | ~230 |
| torrent_metadata.py | פענוח .torrent, חישוב info_hash | ~240 |
| tracker_client.py | תקשורת עם tracker (announce, compact peers) | ~340 |
| peer_connection.py | חיבור TCP בודד - handshake, framing, הודעות | ~620 |
| piece_manager.py | מעקב pieces/blocks, rarest-first | ~470 |
| download_manager.py | תיאום מרכזי - peers, choke/unchoke, upload, state | ~1,310 |
| security.py | מוניטין, אימות hash, ban | ~330 |
| api_server.py | שרת REST (Flask) | ~530 |

Java GUI (~1,700 שורות): TorrentClientGUI (חלון ראשי), ApiService (HTTP client), AlgorithmStatsDialog (גרפים).

---

### Slide 12 - זרימת הורדה · END-TO-END
Header kicker: 12 · זרימת הורדה
Title: מה קורה מ-"Add Torrent" ועד קובץ שלם על הדיסק

- בחירת קובץ - המשתמש בוחר .torrent ב-JFileChooser ואז תיקיית יעד.
- POST /torrents - ה-GUI שולח את הקובץ + האלגוריתמים שנבחרו.
- פענוח Metadata - המנוע מריץ TorrentMetadata.parse(), מחשב info_hash, יוצר אובייקט Download.
- announce ל-tracker - קבלת רשימת peers (compact).
- חיבור ל-peers - handshake, BITFIELD, ואז לולאת בקשות.
- בחירת pieces (rarest-first) -> בקשת blocks -> קבלת PIECE -> אימות SHA-1 -> כתיבה לדיסק.
- בסיום: COMPLETED, ואז מעבר ל-SEEDING (שירות peers).

---

### Slide 13 - אלגוריתם בחירת PIECE
Header kicker: 13 · אלגוריתם בחירת PIECE
Title: Rarest-First - להעדיף את ה-pieces הנדירים ביותר ב-swarm

- לכל piece מחזיקים מונה: כמה peers ב-swarm מחזיקים אותו. מתעדכן בכל הודעת HAVE ו-BITFIELD.
- בבחירה: לוקחים את המינימום מבין החסרים לי, בונים את כל ה-pieces עם אותה ספירה מינימלית (ה-tie set), ובוחרים אחד ב-random.choice.
- מבני נתונים: Dict[int,int] לתדירות (O(1) בכל HAVE) + Set[int] ל-pieces של כל peer.
- למה עדיף על Random: שומר על זמינות הנדירים, מונע bottleneck כשה-seeder היחיד עוזב.
- קוד: piece_manager.py (select_piece_rarest_first), בחירה אקראית בתוך ה-tie set. בספר §7.1.

---

### Slide 14 - ביקורת עמוקה · תרגיל 1
Header kicker: 14 · ביקורת עמוקה · תרגיל 1
Title: למה Rarest-First הוא בעצם בעיית אופטימיזציה גלובלית

- בעיה גלובלית מוסווית - המטרה האמיתית היא למקסם availability של כל piece בכל ה-swarm, לא רק את ה-throughput שלי. זו פונקציית מטרה משותפת שאף אחד לא מחשב במפורש.
- Survivability - אם piece נדיר קיים רק אצל seeder אחד, נפילתו = piece שאבד מה-swarm לנצח. rarest-first מפיץ את הנדירים קודם.
- סכנת ה-local view - כל peer רואה רק ~30 שכנים מתוך אלפים. piece שנראה לו "נדיר" עשוי להיות שכיח בחצי השני של ה-swarm. ההחלטה מבוססת תצפית מוטית.
- Contention מקבילי - אם כל ה-peers בוחרים דטרמיניסטית, כולם פונים לאותו seeder יחיד (thundering herd). ה-randomization בתוך ה-tie set שובר את הסימטריה.

---

### Slide 15 - אלגוריתם בחירת PEER
Header kicker: 15 · אלגוריתם בחירת PEER
Title: Tit-for-Tat - לתגמל את ה-peers שתורמים לי עכשיו (sliding window)

- כל 10 שניות (CHOKE_INTERVAL) ממיינים peers ופותחים choke ל-top-4 התורמים + peer אקראי אחד (Optimistic Unchoke) לגילוי peers חדשים.
- המדד הוא **חלון נע של 20 שניות** (TIT_FOR_TAT_WINDOW): כמה bytes ה-peer שלח לי לאחרונה - לא מונה מצטבר מתחילת ה-session.
- למה window ולא מצטבר: מונה מצטבר משקר - peer שתרם בהתחלה והשתתק שומר ציון גבוה לנצח. 20 שניות = שני מחזורי choke, כך שהמדד יציב ולא מרצד.
- קוד: bytes_received_in_window (peer_connection.py), _tit_for_tat_unchoke (download_manager.py). בספר §15.4.2.

---

### Slide 16 - Tit-for-Tat לעומק · Snubbing + Seeding
Header kicker: 16 · Tit-for-Tat לעומק
Title: Snubbing ומצב Seeding - מעבר ל-bytes_downloaded השטחי

- Snubbing - peer ש-unchoked אותי אבל הפסיק לשלוח data במשך 60 שניות (SNUB_THRESHOLD) מסומן snubbed, מקבל עדיפות נמוכה, ומפנה מקום ל-peer אחר. בלי זה, peer באגי/זדוני תופס slot בלי לתת כלום. בספר §15.4.3.
- מצב Seeding - Tit-for-Tat הוא אלגוריתם של leecher ("מי נותן לי הכי הרבה?"). כש-seeder אין מה להוריד, אז המדד מתהפך: ממיינים לפי כמה אני מעלה לכל peer (bytes_sent_in_window) - "למי אני יכול לתת הכי מהר?". בספר §15.4.4.
- נקודת כאב אמיתית: בגרסה הראשונה לא היה seeding mode וכל ה-peers נראו שווים אחרי השלמה. הוספת המדד ההפוך פתרה זאת.

---

### Slide 17 - ביקורת עמוקה · תרגיל 2
Header kicker: 17 · ביקורת עמוקה · תרגיל 2
Title: Tit-for-Tat אינו באמת "הוגן" - חולשות בעולם האמיתי

- Asymmetric bandwidth - לקוח ביתי: 100 מגה הורדה, 10 מגה העלאה. peer עם upload חזק מוצף בבקשות שאינו יכול להחזיר reciprocally, והאלגוריתם "מעניש" אותו כאילו לא תרם.
- BitTyrant (NSDI 2007) - לקוח אקדמי שמראה איך לנצל: שולחים לכל peer את המינימום הנדרש כדי להישאר unchoked, וחוסכים upload להפצה ליותר peers בו-זמנית.
- Contribution measurement - מודדים bytes, לא ערך. piece נדיר ששווה זהב נחשב כמו piece שכיח. ה-incentive לא מיושר עם השווי.
- מה Optimistic Unchoke כן נותן: בלי האקראיות, peer חדש = ציון 0 = לעולם לא נכנס. זו דלת הכניסה למערכת.

---

### Slide 18 - Peer Wire Protocol · BEP-3
Header kicker: 18 · PEER WIRE PROTOCOL · BEP-3
Title: TCP גולמי, handshake של 68 בתים, 10 סוגי הודעות

- handshake (68 בתים) = 1 (pstrlen=19) + 19 ("BitTorrent protocol") + 8 reserved + 20 info_hash + 20 peer_id. ה-peer_id מתחיל ב-"-PG0001-".
- 10 הודעות: CHOKE, UNCHOKE, INTERESTED, NOT_INTERESTED, HAVE, BITFIELD, REQUEST, PIECE, CANCEL, KEEP_ALIVE.
- בדיקת handshake נכנס: pstrlen=19, pstr נכון, ו-info_hash תואם - אחרת מנתקים.

Code box (LTR):
```
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

### Slide 19 - קבלת PIECE · Sequence Diagram (UML)
Header kicker: 19 · קבלת PIECE · UML SEQUENCE
Title: זרימת הודעת PIECE - קבלה, אימות SHA-1, ו-ban

`[[DIAGRAM: piece-sequence]]`
Caption: Sequence Diagram (UML) - זרימת הודעת PIECE: קבלה ב-PeerConnection, submit_block ב-PieceManager, אימות SHA-1 ב-ThreadPoolExecutor, ואז HAVE לכולם או ban אחרי כשל.
Note to Adam: render docs/Fig-05.md at https://mermaid.live and paste the PNG/SVG here (sequence diagrams יוצאים רחבים - שקול עמוד landscape). זה הוויזואל המרכזי של השקופית.

Caption / talking points (small, under the diagram):
- PIECE היא ההודעה היחידה ב-BEP-3 שנושאת נתוני קובץ.
- אחרי שכל ה-blocks הגיעו (submit_block מחזיר is_complete), אימות ה-SHA-1 והכתיבה לדיסק רצים ב-ThreadPoolExecutor כדי לא לחסום את ה-event loop.
- piece שעבר אימות -> broadcast של HAVE לכל ה-peers. piece שנכשל -> report_hash_failure, ו-ban אחרי 3 כשלים.

---

### Slide 20 - ביקורת עמוקה · תרגיל 3
Header kicker: 20 · ביקורת עמוקה · תרגיל 3
Title: TCP הוא stream ולא message - וזה יוצר מורכבות עצומה

- Stream != Messages - TCP מבטיח סדר ובלי אובדן, אבל לא גבולות הודעה. recv(1024) עלול להחזיר חצי הודעה + שליש מהבאה.
- Packet fragmentation - הודעה אחת נשברת לכמה IP packets ומגיעה בחתיכות לא עקביות.
- Partial reads - אם ביקשנו block של 16KB וקיבלנו 4KB, אסור לפענח עכשיו ואסור לאבד את מה שכבר הגיע.
- הפתרון - Length-Prefixed Framing: 4 בתי אורך (big-endian), ולידציה מול MAX_MESSAGE_SIZE (2MB), ואז readexactly(length) שמחזיר הודעה שלמה (מטפל בפיצול לבד).
- Head-of-line blocking - peer איטי על אותו socket מעכב את מה שמאחוריו. תשובה: כל peer הוא coroutine נפרד, אז peer איטי לא חוסם אחרים.

---

### Slide 21 - העלאה ומצב Seeding
Header kicker: 21 · העלאה · SEEDING
Title: הלקוח גם מעלה - לא רק מוריד (נקודת כאב אמיתית)

- חיבור TCP דו-כיווני: גם אם אני יזמתי את החיבור כדי להוריד, ה-peer יכול לשלוח לי REQUEST על אותו socket.
- נתיב ההעלאה: REQUEST -> _serve_block_request (בדיקות: לא choking, piece קיים ושלם, אורך <= BLOCK_SIZE, בתוך הגבולות) -> send_piece.
- מצב גלוי: בסיום ההורדה ה-state עובר COMPLETED, וב-choke tick הבא _maybe_enter_seeding מקדם ל-SEEDING, וה-GUI מציג "Seeding".
- נקודת הכאב: בהתחלה send_piece היה dead code (אף אחד לא קרא לו) ו-REQUEST נזרק בשקט, אז bytes_uploaded היה אפס תמיד ו-seed mode מיין הכול לפי אפס. חיווט ה-REQUEST הפך את ההעלאה לאמיתית.
- הוכחה end-to-end: test_seeder_serves_block_to_requesting_peer - peer אמיתי על socket loopback מקבל בדיוק את ה-bytes של המקור.

---

### Slide 22 - אימות שלמות
Header kicker: 22 · אימות שלמות
Title: SHA-1 על כל piece - לפני שמילה אחת נכתבת לדיסק

- שימוש 1 · info_hash - SHA-1 על ה-info dict ב-bencode = מזהה גלובלי של ה-torrent, משמש ב-handshake מול tracker ומול peers.
- שימוש 2 · אימות piece - קובץ ה-.torrent מכיל hash של 20 בתים לכל piece. אחרי שכל ה-blocks התקבלו: חישוב SHA-1 והשוואה. piece פגום לא נכתב.

Code box (LTR):
```
# piece_manager.py
def verify_hash(self) -> bool:
    actual = hashlib.sha1(self._data).digest()
    return actual == self.expected_hash
```

---

### Slide 23 - ביקורת עמוקה · תרגיל 4
Header kicker: 23 · ביקורת עמוקה · תרגיל 4
Title: SHA-1 - SWOT וגבולות ההגנה בעידן ה-collision attacks

- Strengths - מהיר, קצר (20 בתים), תאימות מלאה ל-BEP-3, מגן מ-corruption אקראי.
- Weaknesses - SHAttered (2017) הראה צמד collisions מעשי. אימות הוא piece-level בלבד: block פגום בודד פוסל piece שלם (תקיפת DoS בלי collision).
- Opportunities - BEP-52 (BitTorrent v2) מציע SHA-256 + Merkle Trees לאימות חלקי piece, עם hybrid mode לתאימות לאחור. מתועד כפיתוח עתידי.
- Threats - תאורטית תוקף עם משאבים אדירים יכול לייצר collision ל-info_hash. סיכון נמוך, לא אפסי.
- למה בכל זאת SHA-1: תאימות לפרוטוקול הקיים - כל ה-trackers, הלקוחות, וקבצי ה-.torrent בעולם מבוססים SHA-1. מעבר ל-SHA-256 דורש מימוש מלא של BEP-52, מחוץ לסקופ.

---

### Slide 24 - אבטחה · הגנה בעומק + Sybil
Header kicker: 24 · אבטחה · DEFENSE-IN-DEPTH
Title: שכבות הגנה זולות - ולמה מוניטין לא פותר Sybil (תרגיל 5)

שכבות הגנה:
- ולידציית handshake - פוסל peers עם info_hash שגוי או פרוטוקול לא נכון. O(1).
- ולידציית אורך הודעה מול MAX_MESSAGE_SIZE - מונע flooding (length=0xFFFFFFFF). O(1).
- אימות SHA-1 per piece - piece פגום לא נכתב.
- מערכת מוניטין - ban אחרי 3 כשלי hash או 5 הפרות פרוטוקול.

ביקורת עמוקה (תרגיל 5) - למה זה לא פותר Sybil:
- Sybil - תוקף יוצר 1,000 peer_id שונים. כל אחד נחסם אחרי 3, אבל הבא מוכן. המוניטין הוא per-identity, לא per-attacker.
- New peer problem - peer חוקי חדש מתחיל ב-reputation 0, בדיוק כמו peer חשוד.
- False reputation - 3 timeouts מתקלת רשת זמנית = ban קבוע. אין decay או second chance.

---

### Slide 25 - קונקורנציה · הגשר
Header kicker: 25 · קונקורנציה · הגשר
Title: איך Flask סינכרוני מדבר עם asyncio - וההסתייגות (תרגיל 6)

- Flask workers (threaded) - מטפלים בבקשות REST במקביל.
- asyncio event loop ב-thread רקע (daemon) - כל הקואורוטינות של ההורדות: _download_loop, _message_loop לכל peer, _choke_loop, _keep_alive_loop.
- ThreadPoolExecutor - לפעולות חוסמות (כתיבת דיסק, חישוב SHA-1) כדי לא לחסום את ה-loop.
- הגשר: כל endpoint מריץ coroutine דרך asyncio.run_coroutine_threadsafe(coro, loop).result().

ביקורת עמוקה (תרגיל 6):
- Event-loop starvation - פעולה חוסמת אחת ששוכחים להעביר ל-executor (time.sleep במקום asyncio.sleep) חוסמת את כל הקואורוטינות.
- REST polling overhead - GUI פונה כל 500ms. בריבוי הורדות זה מצטבר; WebSockets/SSE היה נכון יותר.
- Race conditions - Flask קורא get_status() בעוד ה-loop משנה את אותו state. נדרש זהירות עם נעילות.

---

## חלק ג - תוצאות, ממשק, ומסקנות

---

### Slide 26 - Divider C
Full blue divider.
- אות גדולה: C
- חלק ג - תוצאות, ממשק, ומסקנות
- כיתוב משנה: שמירת מצב, תוצאות אמפיריות, מסכי GUI, בדיקות, ומה למדתי

---

### Slide 27 - שמירה ושחזור מצב
Header kicker: 27 · שמירה ושחזור מצב
Title: Resume שעובד - ושליטה ברשימת ההורדות

- שמירת מצב: כל הורדה נשמרת ל-data/state/<id>.json + sidecar .torrent (כתיבה אטומית write-then-rename).
- שחזור (חדש - תוקן): restore_state סורק את התיקייה ומשחזר הורדות במצב PAUSED. כל piece שהושלם נקרא מהדיסק ומאומת SHA-1 מחדש לפני שסומכים עליו (from_state_file).
- ניקוי אוטומטי: הורדות שכבר נגמרו (Completed/Seeding) או בוטלו (Cancelled) לא משוחזרות, וקבצי ה-state שלהן נמחקים. הקובץ עצמו בדיסק נשמר.
- כפתור Delete (חדש): מסיר שורה מהרשימה (עוצר אם פעיל) דרך DELETE /torrents/<id>, בלי למחוק את הקובץ.
- הערה: בגרסה הקודמת של הספר זה הופיע כמגבלה ("אין _load_state"). היום זו תכונה עובדת ובדוקה.

---

### Slide 28 - הערכה אמפירית
Header kicker: 28 · הערכה אמפירית
Title: Rarest-First מול Random - ניסוי משוחזר

- הקמה: swarm סינתטי על loopback. קובץ 1MB (16 pieces × 64KB), tracker מינימלי, ו-4 mock peers. 5 הרצות לכל אלגוריתם (10 בסך הכול). ה-CSVs מחויבים ב-data/experiments/.
- טופולוגיה: peer בשם full מחזיק את כל 16 החתיכות; low_a/low_b/low_c מחזיקים רק 0-7. כלומר 8-15 הם "החצי הנדיר" וקיימים רק אצל full.

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

### Slide 29 - ממשק · המסך הראשי
Header kicker: 29 · ממשק משתמש · המסך הראשי
Title: Main Window - הציר של האפליקציה

`[[SCREENSHOT: main-window]]`
Caption: חלון ראשי - טבלת הורדות (Name, Size, Progress, Speed, Peers, State), toolbar (Add Torrent / Pause / Resume / Cancel / Delete / History / Algorithm Stats), ויומן חי. שימו לב לשורה במצב Seeding ולכפתור Delete.

Note to Adam: צלם בזמן הורדה פעילה, אם אפשר עם שורה אחת ב-Downloading ושורה אחת ב-Seeding.

---

### Slide 30 - ממשק · חלון הסטטיסטיקה
Header kicker: 30 · ממשק משתמש · סטטיסטיקה
Title: Algorithm Statistics - השוואה אמפירית בין הריצות

`[[SCREENSHOT: algorithm-stats]]`
Caption: חלון Algorithm Statistics - bar chart של בחירות rarest-first per piece (Java2D), ולשונית General עם מדדים מצרפיים (Total Data, Avg Speed, Peak Speed, Total Peers, Choke Cycles).

---

### Slide 31 - בדיקות והערכה
Header kicker: 31 · בדיקות
Title: 226 בדיקות · 9 קבצים · כולל בדיקת E2E על socket אמיתי

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

- בדיקת E2E (test_e2e_peer.py): mock peer אסינכרוני עונה handshake -> bitfield -> unchoke -> piece, וה-PeerConnection מנהל מולו את כל ה-stack (framing, state machine, אימות SHA-1). כולל בדיקה שמוכיחה גם העלאה אמיתית.

---

### Slide 32 - מסקנות מרכזיות
Header kicker: 32 · מסקנות
Title: מה למדתי מהפרויקט

- Rarest-first שווה את עלותו הזניחה - אותו O(N) כמו random, אבל איכות הרבה יותר טובה לבריאות ה-swarm.
- Tit-for-Tat דורש זהירות - חלון נע, snubbing, ומצב seeding הם ההבדל בין "מיון לפי מספר" לבין אלגוריתם שמשקף את ההווה.
- TCP הוא stream - בלי framing מפורש (length-prefix + readexactly) שום דבר לא עובד.
- כנות עדיפה על התנפחות - לתעד מה לא מומש ולמה (Sybil, NAT, BEP-52) חזק יותר מלטעון שהכול עובד.
- ראיות > הצהרות - ניסוי משוחזר עם CSV מחויב, ו-226 בדיקות כולל E2E, מגבים כל טענה בקוד.

---

### Slide 33 - מגבלות ופיתוחים עתידיים
Header kicker: 33 · מגבלות ופיתוחים עתידיים
Title: מה לא נכלל - בכוונה ובכנות

- אין קבלת חיבורים נכנסים / NAT traversal - מעלים ל-peers מחוברים (חיבורים יוצאים), אבל אין start_server לחיבורים חדשים.
- אין DHT - מציאת peers בלי tracker מרכזי.
- אין PEX - החלפת רשימות peers בין peers.
- אין הצפנת peers (MSE/PE) - ISP יכול לזהות תעבורת BitTorrent ב-DPI.
- אין UDP tracker, אין IPv6 (compact peer parsing הוא 6 בתים בלבד), אין magnet links.
- רק BEP-3 (v1) - לא BEP-52 (SHA-256 + Merkle Trees).
- הערה: auto-resume כבר אינו מגבלה - מומש (ראו שקופית 26).

---

### Slide 34 - תודה / שאלות
Layout: closing slide.
Title: תודה · שאלות?

- מגיש: אדם זבולון · מנחה: גל בראון
- פרויקט: מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent
- 17 שאלות הכנה מכוסות בנספח שמיד אחרי - 10 שאלות עומק + 7 שאלות קוד, לקפיצה מהירה.

---

## נספח - שאלות הכנה

---

### Slide 35 - Divider Q
Full blue divider.
- אות גדולה: Q
- נספח · שאלות הכנה
- כיתוב משנה: 10 שאלות עומק + 7 שאלות קוד, מתועדות לעיון מהיר בזמן ההגנה

---

### Slide 36 - שאלת עומק 1 · RAREST-FIRST
Header kicker: 36 · שאלת עומק 1
Title: למה Rarest-First הוא הרבה יותר מ"בחירת החלק הנדיר"

שאלה: מדוע rarest-first הוא בעצם בעיית optimization גלובלית? איך rarity distribution משפיעה על survivability? למה local view מטעה? איך simultaneous rare-piece requests יוצרים contention? למה randomization הכרחי?

תשובה:
- גלובלי, לא לוקאלי - המטרה האמיתית: שלכל piece יישארו עותקים גם אחרי שה-seeders עוזבים. כל peer מקרב את המטרה הגלובלית עם heuristic מקומי.
- Survivability - piece נדיר אצל seeder יחיד = piece שאבד אם הוא נופל. rarest-first מפיץ נדירים קודם.
- Local view - רואים ~30 שכנים מתוך אלפים, כך שה-rarity היא מקומית ומוטית.
- Contention - peers זהים בוחרים אותו piece -> thundering herd. randomization בתוך ה-rarest set שובר את הסימטריה.

---

### Slide 37 - שאלת עומק 2 · TIT-FOR-TAT
Header kicker: 37 · שאלת עומק 2
Title: ביקורת עמוקה על Tit-for-Tat

שאלה: מדוע Tit-for-Tat אינו באמת "הוגן"? איך asymmetric bandwidth פוגע? למה optimistic unchoke הכרחי? איך BitTyrant מנצל את האלגוריתם? למה contribution measurement בעייתי?

תשובה:
- הוגנות-לכאורה - מודד bytes, לא ערך. piece נדיר נחשב כמו piece שכיח.
- Asymmetric BW - ADSL ביתי 100/10. peer מוצף בבקשות שלא יכול לעמוד בהן, ונראה "קמצן".
- Optimistic Unchoke - בלי אקראיות, peer חדש (ציון 0) לעולם לא נכנס לדירוג. זו דלת הכניסה.
- BitTyrant (NSDI 2007) - שולח לכל peer את המינימום להישאר unchoked, וחוסך upload ליותר peers.

---

### Slide 38 - שאלת עומק 3 · TCP מעל P2P
Header kicker: 38 · שאלת עומק 3
Title: למה TCP מעל P2P יוצר מורכבות עצומה

שאלה: מדוע TCP stream אינו message protocol? איך packet fragmentation משפיע על parsing? למה partial reads מסוכנים? איך concurrent communication מסבך synchronization? איך slow peers יוצרים HOL blocking?

תשובה:
- Stream != Messages - TCP מבטיח סדר ובלי אובדן, אבל לא גבולות. recv מחזיר חתיכה שרירותית, אז צריך framing משלנו (length-prefix).
- Partial reads - block של 16KB יכול להגיע ב-3 קריאות. הפתרון: readexactly.
- Sync - הרבה חיבורים -> הרבה coroutines -> state משותף (PieceManager) -> נדרשת נעילה.
- HOL blocking - peer איטי על socket מעכב את מה שמאחוריו; כל peer הוא coroutine נפרד.

---

### Slide 39 - שאלת עומק 4 · אימות SHA-1
Header kicker: 39 · שאלת עומק 4
Title: ביקורת עמוקה על piece hash verification

שאלה: מדוע piece-level hashing לא מגן מכל תקיפה? איך collision attacks על SHA-1 רלוונטיים? איך malicious peers עדיין יכולים לפגוע? איך corrupted blocks משפיעים על throughput? איך verification latency משפיע?

תשובה:
- Piece-level != block-level - אימות רק אחרי שכל ה-blocks הגיעו. block פגום בודד פוסל piece שלם (16 blocks מחדש) - DoS בלי collision.
- SHAttered (2017) - אפשר לייצר collision; רלוונטי תאורטית ל-.torrent, פחות ל-piece בודד בהורדה.
- Malicious throughput - peer ששולח pieces פגומים מבזבז לי זמן, גם אם נחסם אחרי 3.
- Latency - חישוב SHA-1 חוסם, לכן מועבר ל-ThreadPoolExecutor.

---

### Slide 40 - שאלת עומק 5 · PEER REPUTATION
Header kicker: 40 · שאלת עומק 5
Title: הבעיה האמיתית במערכות מוניטין מבוזרות

שאלה: מדוע reputation אינו מדד אמין? איך Sybil attacks משפיעים? למה peers חדשים נפגעים? איך network failures יוצרים false reputation? למה distributed trust קשה?

תשובה:
- Per-identity - מבוסס peer_id שמיוצר עצמאית, אז תוקף יכול ליצור אינסוף (Sybil מנצח).
- Cold start - peer חוקי חדש מתחיל ב-0, "חשוד" כמו זדוני.
- False positives - 3 timeouts מתקלת רשת = ban קבוע, בלי decay או forgiveness.
- Distributed trust - אמון אמיתי דורש זהות מאומתת או מקור אמין מרכזי, שסותר את ה-decentralization.

---

### Slide 41 - שאלת עומק 6 · ASYNCIO + REST
Header kicker: 41 · שאלת עומק 6
Title: ביקורת עמוקה על asyncio + REST Bridge

שאלה: למה asyncio מסובך ב-multi-peer? איך blocking operations שוברים concurrency? למה REST polling יוצר overhead? איך synchronization בין Java ל-Python מסובך? למה race conditions עדיין אפשריים?

תשובה:
- Cooperative scheduling - כל coroutine חייבת לוותר על שליטה ב-await; פעולה CPU-bound אחת חוסמת את כל ה-loop.
- Blocking break - time.sleep במקום asyncio.sleep, או socket.recv במקום reader.read, מקפיא הכול.
- Polling overhead - GUI כל 500ms, מצטבר בריבוי הורדות.
- Sync - שני thread (Flask + loop) נוגעים באותו state; נדרשת נעילה למניעת race.

---

### Slide 42 - שאלת עומק 7 · DISTRIBUTED SYSTEMS
Header kicker: 42 · שאלת עומק 7
Title: BitTorrent הוא בעצם בעיית Distributed Systems

שאלה: מדוע swarm אינו יציב? איך churn משפיע על availability? מדוע decentralized coordination קשה? איך partial knowledge משפיע? למה eventual consistency מופיעה?

תשובה:
- Swarm לא יציב - peers מתחברים, מתנתקים, מבאנים, חוזרים. אין "מצב יציב".
- Churn - seeder מתנתק -> piece מצוי הופך נדיר; ההסתברות להשלים יורדת ככל ש-churn עולה.
- Decentralized coordination - אין conductor; ה-tracker רק מספק רשימת peers. הקרבה לאופטימום גלובלי היא אמרג'נטית.
- Partial knowledge - רואים BITFIELD של שכנים בלבד, rarity מקומי.
- Eventual consistency - כל piece בסוף מגיע לכל מי שרוצה, אבל אין הסכמה על מתי.

---

### Slide 43 - שאלת עומק 8 · BENCODE
Header kicker: 43 · שאלת עומק 8
Title: ביקורת עמוקה על Bencode parser

שאלה: למה recursive parsing מסוכן? איך malformed torrents עלולים לקרוס parser? למה deeply nested בעייתי? איך integer overflows אפשריים? למה parser validation הוא attack surface?

תשובה:
- Recursion depth - torrent עם nesting עמוק -> RecursionError ב-Python (~1,000). תוקף שולח lllll... ל-stack overflow. פתרון: limit על depth.
- Malformed input - i00e (zero padding) אסור ב-canonical bencode; אכיפת מפתחות ממוינים חיונית, אחרת info_hash שגוי.
- Integer overflow - Python int הוא arbitrary-precision (מוגן), אבל גבול עדיין צריך אכיפה.
- Validation = attack surface - ה-parser הוא הקלט הראשון מהרשת, אז כל באג בו הוא נקודת תקיפה.

---

### Slide 44 - שאלת עומק 9 · DOWNLOADMANAGER
Header kicker: 44 · שאלת עומק 9
Title: הבעיה האמיתית ב-DownloadManager Orchestration

שאלה: למה scheduling requests קשה? איך concurrent requests יוצרים race? איך peer failures משפיעים על כל הזרימה? איך request queues מתפוצצות? למה timeout tuning הוא tradeoff?

תשובה:
- Scheduling - הרבה peers × כמה בקשות פתוחות = תור גדול; צריך לוודא שאותו block לא נשאל משני peers.
- Race - שני peers משלימים piece בו-זמנית; אימות SHA-1 idempotent מגן.
- Peer failures - חצי ה-swarm מתנתק -> פחות bandwidth ופחות pieces; re-announce תקופתי.
- Timeout tuning - קצר מדי = ניתוקים מיותרים; ארוך מדי = slots תקועים. ה-snubbing (60s) הוא חלק מהאיזון.

---

### Slide 45 - שאלת עומק 10 · הבעיה האמיתית
Header kicker: 45 · שאלת עומק 10
Title: "להוריד קבצים" הוא ה-outcome - הבעיה האמיתית אחרת

שאלה: המערכת מתיימרת "לממש לקוח BitTorrent". הסבר למה בפועל מדובר בבעיית distributed optimization, asynchronous coordination, probabilistic peer behavior, transport uncertainty, ו-adversarial networking.

תשובה:
- Distributed optimization - rarest-first הוא קירוב לוקאלי לכיסוי גלובלי מינימלי.
- Async coordination - Tit-for-Tat הוא משחק חוזר בלי תקשורת ישירה בין שחקנים.
- Probabilistic behavior - optimistic unchoke + randomization -> התנהגות סטוכסטית הכרחית.
- Transport uncertainty - TCP נותן אמינות אבל לא גבולות ולא זמן; framing וזמנים הם באחריותי.
- Adversarial networking - peers ו-trackers עלולים לשקר; אימות ומוניטין הם הכרח.

---

### Slide 46 - שאלות קוד · 1 ו-2
Header kicker: 46 · שאלות קוד · 1-2
Title: select_piece_rarest_first · _tit_for_tat_unchoke

קוד 1 · Stale peer state (select_piece_rarest_first):
- אם peer מתנתק ולא מנקים את רשומת ה-pieces שלו, ממשיכים לספור piece כזמין. piece "שכיח" לכאורה הוא בעצם נדיר -> נבחר אחרון -> starvation.
- פתרון: on_peer_disconnect מנקה ומחשב frequency מחדש.

קוד 2 · Bandwidth asymmetry (_tit_for_tat_unchoke, download_manager.py:610):
- הציון מבוסס על כמה ה-peer שלח לי בחלון (bytes_received_in_window). peer עם upload חלש נראה "קמצן" גם אם נתן את המקסימום שלו.
- ה-window וה-optimistic unchoke ממתנים, אבל לא פותרים לחלוטין.

---

### Slide 47 - שאלות קוד · 3 ו-4
Header kicker: 47 · שאלות קוד · 3-4
Title: read_message · submit_block + verify_hash

קוד 3 · State machine (PeerConnection.read_message):
- אם peer שולח UNCHOKE לפני BITFIELD, איני יודע אילו pieces יש לו. HAVE עם index מעבר ל-num_pieces -> IndexError.
- פתרון: ולידציה לכל הודעה לפני עדכון state + מונה הפרות שמפנה ל-ban.

קוד 4 · Resource exhaustion (Piece.submit_block + verify_hash):
- block flooding או blocks חופפים עלולים לנפח זיכרון; אימות SHA-1 רק על piece שלם, ו-block מחוץ לגבולות נדחה.
- send_piece מוגבל ל-BLOCK_SIZE כדי לא לשרת קריאות ענק.

---

### Slide 48 - שאלות קוד · 5 ו-6
Header kicker: 48 · שאלות קוד · 5-6
Title: TrackerClient.announce · SecurityManager + PeerReputation

קוד 5 · Malicious tracker (TrackerClient.announce):
- tracker יכול להחזיר רק peers שבשליטתו (eclipse attack) - כל ה-peers שלי שלו.
- הגנות במימוש: ולידציית פורמט (compact peer = 6×N בתים), אכיפת interval מינימלי (מניעת DoS עצמי), ו-fallback בכשל tracker. פתרון אמיתי: DHT + multi-tracker.

קוד 6 · Sybil rotation (SecurityManager + PeerReputation):
- ban אחרי 3 כשלי hash / 5 הפרות - per peer_id. תוקף מסובב זהויות ועוקף.
- מיטיגציה חלקית: ban מהיר וזול; פתרון אמיתי דורש זהות מאומתת.

---

### Slide 49 - שאלת קוד 7 · ASYNC BRIDGE
Header kicker: 49 · שאלת קוד 7
Title: start_event_loop + _run_async - Event-loop starvation

קוד 7 · Event-loop starvation:
- תרחיש: Flask handler קורא _run_async(download.get_status()). אם בתוך get_status יש time.sleep(2) במקום await asyncio.sleep(2), ה-event loop נחסם ל-2 שניות.
- ההשפעה: כל הקואורוטינות מחכות -> חיבורי TCP לא קוראים מהסוקטים -> buffers של ה-OS מתמלאים -> peers שולחים RST -> ניתוקים המוניים.
- הכלל: כל פעולה חוסמת חייבת לעבור ל-ThreadPoolExecutor (כמו כתיבת דיסק ואימות SHA-1).
