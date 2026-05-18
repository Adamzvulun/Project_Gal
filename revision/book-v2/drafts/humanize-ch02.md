# Humanization — chapter §2 (תקציר / מבוא)

Body idx range: 345–375. Headings and blank paragraphs are KEEP.
All inline `code`, BEP-N, §N, numeric measurements, citation
author/year/title strings are preserved character-for-character.

## Per-paragraph rewrites

### idx 347 (תקציר opener)
Old: עבודת גמר זו מציגה תכנון ופיתוח של מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent, המממשת את פרוטוקול BitTorrent (BEP-3) משכבת התעבורה ועד לממשק המשתמש. המערכת בנויה משני רכיבים עצמאיים: מנוע רשת ב-Python שמטפל בכל לוגיקת ה-P2P (פענוח Bencode, תקשורת tracker, חיבורי TCP ל-peers, בחירת pieces ואלגוריתמי choke/unchoke, אימות SHA-1, וניהול מצב), וממשק משתמש גרפי ב-Java Swing שמתקשר עם המנוע דרך REST API מקומי.

New: בעבודת הגמר הזו תכננתי ובניתי מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent, שמממשת את פרוטוקול BitTorrent (BEP-3) משכבת התעבורה ועד לממשק המשתמש. המערכת נחלקת לשני רכיבים עצמאיים. מנוע רשת ב-Python מטפל בכל לוגיקת ה-P2P — פענוח Bencode, תקשורת tracker, חיבורי TCP ל-peers, בחירת pieces ואלגוריתמי choke/unchoke, אימות SHA-1 וניהול מצב. ממשק משתמש גרפי ב-Java Swing מתקשר איתו דרך REST API מקומי.

### idx 348
Old: האתגר האלגוריתמי המרכזי הוא בחירת piece ובחירת peer תחת אילוצי רשת ופרוטוקול. מימשתי את שני האלגוריתמים הקלאסיים -rarest-first לבחירת piece ו-Tit-for-Tat + Optimistic Unchoke לבחירת peer -לצד baselines פשוטים (random, round-robin) להשוואה כמותית.

New: הבעיה האלגוריתמית המרכזית היא לבחור piece ולבחור peer תחת אילוצי הרשת והפרוטוקול. מימשתי את שני האלגוריתמים הקלאסיים: rarest-first לבחירת piece, ו-Tit-for-Tat + Optimistic Unchoke לבחירת peer. כדי שאוכל להשוות מספרית, הוספתי גם baselines פשוטים (random, round-robin).

### idx 349
Old: המערכת ממומשת ב-כ-5,360 שורות פרודקשן (3,718 Python + 1,641 Java), עם 212 unit tests + ניסוי E2E עם peer-mock ב-pytest. היא נבדקה על Linux (Ubuntu 22.04) ועל Windows 10. ביצועים אלגוריתמיים נמדדו ב-§24: ב-swarm סינתטי מקומי השלמת הורדה של 1 MB ב-כ-30 מילי-שניות עם 4 peers — מדידה שמתמקדת באלגוריתם בחירת ה-pieces (rarest-first מול random), לא ב-throughput במגה-בייט בשניה ב-swarm ציבורי.

New: בסך הכל המערכת מסתכמת בכ-5,360 שורות פרודקשן (3,718 Python + 1,641 Java), 212 unit tests, וניסוי E2E עם peer-mock ב-pytest. בדקתי אותה על Linux (Ubuntu 22.04) ועל Windows 10. את הביצועים האלגוריתמיים מדדתי ב-§24 — ב-swarm סינתטי מקומי, הורדה של 1 MB מסתיימת בכ-30 מילי-שניות עם 4 peers. המדידה מתמקדת באלגוריתם בחירת ה-pieces (rarest-first מול random), לא ב-throughput במגה-בייט בשניה ב-swarm ציבורי.

### idx 351
Old: תחום שיתוף הקבצים המבוזר עבר תהפוכות רבות מאז שנות ה-90. המהפכה החלה עם Napster (1999) שהוכיח את פוטנציאל ה-P2P, המשיכה ב-Gnutella ו-Kazaa (2000–2003) שניסו להיפטר מהשרת המרכזי, והגיעה לבגרות עם BitTorrent של Bram Cohen (2001) שפתר את הבעיה המרכזית: איך לתמרץ peers לתרום upload bandwidth כשאין מנגנון אכיפה. הפתרון של Cohen -Tit-for-Tat -הפך לסטנדרט דה-פקטו ועד היום BitTorrent הוא הפרוטוקול הדומיננטי לשיתוף קבצים פתוח.

New: שיתוף קבצים מבוזר עבר כמה גלגולים מאז סוף שנות ה-90. Napster (1999) הראה לראשונה שאפשר לעבוד P2P; Gnutella ו-Kazaa (2000–2003) ניסו לוותר על השרת המרכזי בכלל; ואז הגיע BitTorrent של Bram Cohen (2001) ופתר את השאלה שאף אחד לא הצליח לפתור לפניו — איך מתמרצים peers לתרום upload bandwidth כשאין מנגנון אכיפה. הפתרון של Cohen, Tit-for-Tat, הפך מאז לסטנדרט דה-פקטו, ועד היום BitTorrent הוא הפרוטוקול הדומיננטי לשיתוף קבצים פתוח.

### idx 352
Old: הבחירה שלי לפתח מערכת כזו נבעה מהרצון להבין מבפנים איך פרוטוקול P2P שלם עובד -לא רק לקרוא מאמרים, אלא לממש כל שורה. הפרוטוקול נראה פשוט בקריאה (BEP-3 הוא 30 עמודי טקסט) אבל מערב לימוד מעמיק של רשתות (TCP בלי HTTP), קריפטוגרפיה (SHA-1), אלגוריתמים (rarest-first, Tit-for-Tat), קונקורנציה (asyncio + thread pool), ואבטחה (אימות peer-by-peer).

New: בחרתי לפתח את המערכת כי רציתי להבין מבפנים איך פרוטוקול P2P שלם עובד — לא רק לקרוא מאמרים עליו, אלא לממש אותו שורה אחרי שורה. בקריאה ראשונה הפרוטוקול נראה פשוט (BEP-3 הוא 30 עמודי טקסט), אבל בפועל הוא נוגע בכל מה שלמדתי: רשתות (TCP בלי HTTP), קריפטוגרפיה (SHA-1), אלגוריתמים (rarest-first, Tit-for-Tat), קונקורנציה (asyncio + thread pool) ואבטחה (אימות peer-by-peer).

### idx 354
Old: תהליך הלימוד שלי התחיל בקריאת ה-BEPs הרשמיים: BEP-3 (הפרוטוקול הליבה), BEP-23 (compact peer list), ו-BEP-5 (DHT, גם אם לא מומש בפרויקט). אחר כך עברתי על המאמר של Cohen מ-2003 וזה של Legout et al. מ-2006 שניתח אמפירית את הביצועים של rarest-first ושל choke algorithms.

New: התחלתי בקריאת ה-BEPs הרשמיים — BEP-3 (הפרוטוקול הליבה), BEP-23 (compact peer list), ו-BEP-5 (DHT, גם אם בסוף לא מימשתי אותו בפרויקט). משם עברתי למאמר של Cohen מ-2003, ולמאמר של Legout et al. מ-2006 שניתח אמפירית את הביצועים של rarest-first ושל choke algorithms.

### idx 355
Old: לאחר מכן בחנתי שלושה לקוחות פתוחים -qBittorrent (C++/Qt), Transmission (C), ו-libtorrent (C++) -כדי להבין איך הם בנויים בפועל. זה עזר לי להבחין בין דרישות הפרוטוקול לבין החלטות תכנון.

New: אחרי המאמרים פתחתי את הקוד של שלושה לקוחות פתוחים: qBittorrent (C++/Qt), Transmission (C) ו-libtorrent (C++). זה עזר לי להפריד בין דרישות הפרוטוקול לבין החלטות תכנון של המימוש הספציפי.

### idx 359
Old: המאמרים העיקריים שעליהם נשענתי הם Cohen (2003) “Incentives Build Robustness in BitTorrent” -מקור האלגוריתם של Tit-for-Tat; Legout et al. (IMC 2006) “Rarest First and Choke Algorithms Are Enough” -ניתוח אמפירי שמראה ש-rarest-first יעיל פי 1.5–2 מ-random; ו- Qiu & Srikant (SIGCOMM 2004) “Modeling and Performance Analysis of BitTorrent-Like P2P Networks” -מודל מתמטי של ביצועי swarm. רשימה מלאה ב-פרק 27.

New: שלושה מאמרים שימשו עוגן לעבודה: Cohen (2003) “Incentives Build Robustness in BitTorrent”, שממנו לקוח האלגוריתם המקורי של Tit-for-Tat; Legout et al. (IMC 2006) “Rarest First and Choke Algorithms Are Enough”, שמראה אמפירית ש-rarest-first יעיל פי 1.5–2 מ-random; ו-Qiu & Srikant (SIGCOMM 2004) “Modeling and Performance Analysis of BitTorrent-Like P2P Networks”, שמציע מודל מתמטי לביצועי swarm. הרשימה המלאה בפרק 27.

### idx 362
Old: הבעיה האלגוריתמית המרכזית: איך לתאם הורדה של קובץ גדול מ-N peers בו-זמנית, כך שההורדה תהיה מהירה, חסכונית ב-bandwidth, ועמידה ל-peers זדוניים/נופלים. הבעיה מתחלקת לשלוש תתי-בעיות: איזה piece לבקש (rarest-first מול random), למי לפתוח choke (Tit-for-Tat מול round- robin), ו-איך לאמת את התוכן (SHA-1 per piece).

New: הבעיה האלגוריתמית המרכזית: איך לתאם הורדה של קובץ גדול מ-N peers בו-זמנית, כך שתהיה מהירה, חסכונית ב-bandwidth ועמידה ל-peers זדוניים או נופלים. היא מתחלקת לשלוש תתי-בעיות — איזה piece לבקש (rarest-first מול random), למי לפתוח choke (Tit-for-Tat מול round- robin), ואיך לאמת את התוכן (SHA-1 per piece).

### idx 364
Old: בחרתי ב-BitTorrent כי הוא משלב את ארבע התחומים שאני אוהב: רשתות תקשורת (TCP, HTTP), אלגוריתמים (rarest-first, choke logic, תורת המשחקים), מערכות הפעלה (asyncio, thread pool), ואבטחת מידע (אימות SHA-1, מערכת מוניטין). זה נושא שמאחד בתוכו את כל מה שלמדתי בשנתיים האחרונות.

New: בחרתי ב-BitTorrent כי הוא מאגד בתוכו את ארבעת התחומים שהכי מעניינים אותי: רשתות תקשורת (TCP, HTTP), אלגוריתמים (rarest-first, choke logic, תורת המשחקים), מערכות הפעלה (asyncio, thread pool) ואבטחת מידע (אימות SHA-1, מערכת מוניטין). פרויקט אחד שמרכז את כל מה שלמדתי בשנתיים האחרונות.

### idx 366
Old: המוטיבציה הייתה להבין מבפנים איך מערכת מבוזרת עובדת בפועל. אחרי לימוד אקדמי של פרוטוקולים, רציתי לכתוב כזה שלם עם כל הקצוות -לראות מה קורה כשפיר זדוני שולח SHA-1 שגוי, מה קורה כשה-event loop מתעמס, ואיך פותרים את זה בקוד.

New: רציתי להבין איך מערכת מבוזרת עובדת באמת, ולא רק לקרוא עליה. אחרי שנתיים של לימוד תאורטי של פרוטוקולים, חיפשתי הזדמנות לכתוב אחד שלם בעצמי, עם כל הפינות הלא נעימות — מה קורה כש-peer זדוני שולח SHA-1 שגוי, מה קורה כשה-event loop נחנק, ואיך מסדרים את זה בקוד.

### idx 368
Old: הפרויקט הוא בעיקר חינוכי -הוא לא מתחרה ב-qBittorrent ב-features. אבל הוא כן משמש פלטפורמה ללימוד והשוואה: המערכת מאפשרת להריץ את אותו קובץ עם שני אלגוריתמים שונים (rarest-first מול random) ולמדוד את ההפרש בביצועים. זה מבחן אמפירי שלא קל למצוא בקליינטים מסחריים.

New: הפרויקט הוא בראש ובראשונה חינוכי, ואין לו שאיפה להתחרות ב-qBittorrent על features. אבל כן יש לו ערך אחד שלא קל למצוא בלקוחות מסחריים: אפשר להריץ איתו את אותו קובץ פעמיים, עם שני אלגוריתמים שונים (rarest-first מול random), ולמדוד את ההפרש בביצועים בצורה מבוקרת.

### idx 370
Old: בחנתי שלושה פתרונות אלטרנטיביים:

New: בדרך השוויתי לשלוש חלופות:

### idx 371
Old: Client-server מרכזי (HTTP/CDN). פשוט אבל יקר -כל המשתמשים נופלים על אותו שרת.

New: Client-server מרכזי (HTTP/CDN). פשוט, אבל יקר — כל המשתמשים נופלים על אותו שרת.

### idx 372
Old: Cloud distribution (S3, BunnyCDN). עובד טוב אבל דורש תשלום per-bandwidth.

New: Cloud distribution (S3, BunnyCDN). עובד טוב, אבל דורש תשלום per-bandwidth.

### idx 373
Old: P2P (BitTorrent). עומד בקנה אחד עם המטרה האקדמית של הפרויקט ומחלק את העומס בין כל המשתתפים.

New: P2P (BitTorrent). מתאים למטרה האקדמית של הפרויקט, ומחלק את העומס בין כל המשתתפים.

### idx 374
Old: בחרתי באפשרות 3. הניתוח המלא בפרק 8.

New: בחרתי בחלופה 3. הניתוח המלא בפרק 8.
