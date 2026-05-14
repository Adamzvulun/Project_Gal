# 3. מטרות / יעדים

## מטרה כללית

המטרה הכללית של הפרויקט היא **לפתח לקוח BitTorrent מלא
מקצה-לקצה, שמיישם את BEP-3 (פרוטוקול הליבה) ומאפשר השוואה
אמפירית בין אלגוריתמים שונים של בחירת piece ובחירת peer**.

## מטרות ספציפיות

הפרויקט מורכב משש מטרות ספציפיות:

**1. פענוח קובצי `.torrent` ותקשורת עם trackers**. מימוש
מלא של Bencode encoder/decoder, חישוב `info_hash` ע"י
SHA-1 על ה-info dict, ושליחת `announce requests`
ל-tracker עם פרסור תגובה (כולל פורמט compact).

**2. תקשורת peer-to-peer מלאה**. מימוש Peer Wire Protocol
ע"פ BEP-3: handshake של 68 בתים, state machine של
choking/interest, וכל 10 סוגי ההודעות (CHOKE, UNCHOKE,
INTERESTED, NOT_INTERESTED, HAVE, BITFIELD, REQUEST,
PIECE, CANCEL, KEEP_ALIVE).

**3. אלגוריתמי בחירה איכותיים**. מימוש **rarest-first**
לבחירת piece ו-**Tit-for-Tat + Optimistic Unchoke**
לבחירת peer, לצד baselines (random, round-robin) לטובת
השוואה אמפירית.

**4. אבטחה ושלמות**. אימות SHA-1 לכל piece לפני כתיבה
לדיסק, ולידציית פרוטוקול בכל הודעה (אורך, msg_id, piece
index), ומערכת מוניטין שמסמנת peers זדוניים אחרי 3 שגיאות
hash או 5 הפרות פרוטוקול.

**5. ממשק משתמש שלם**. GUI ב-Java Swing עם טבלת הורדות
מתעדכנת בזמן אמת, toolbar עם כל הפעולות, יומן אירועים חי,
ושני dialogs מורחבים (History ו-Algorithm Statistics).

**6. ארכיטקטורה מודולרית multi-language**. הפרדה ברורה
בין Engine (Python) ל-GUI (Java) דרך REST/JSON, כך
שאפשר להריץ את ה-Engine בלי GUI, ולהוסיף clients נוספים
בעתיד.

## יעדים מדידים

- **כיסוי בדיקות**: לפחות 150 unit tests ב-pytest שמכסים
  את כל המודולים של ה-Engine. *הושג*: 160 בדיקות.
- **תאימות**: הרצה ללא שגיאות על Linux ו-Windows מתוך
  סקריפט הפעלה יחיד. *הושג*: `start.sh` ו-`start.bat`.
- **רספונסיביות UI**: ה-GUI לא נחסם גם בעת קריאות API
  ארוכות. *הושג*: scheduler + thread-per-call.
- **בידוד שגיאות**: crash בצד אחד לא הורג את השני.
  *הושג*: שני תהליכי OS נפרדים.
- **אבטחה**: peers זדוניים נחסמים אוטומטית אחרי 3 שגיאות
  SHA-1. *הושג*: `SecurityManager` עם ספי `should_ban`.

## יעדי משנה

- **קוד נקי**: PEP 8 ב-Python, Oracle conventions ב-Java,
  type hints + docstrings בכל פונקציה ציבורית.
- **תיעוד**: ספר פרויקט מלא לפי המחוון + README ושני
  הסקריפטים מתועדים.
- **הפצה**: `start.sh`/`start.bat` שמתקינים אוטומטית את
  כל התלויות. אין צורך בידע מוקדם של Python/JDK.
