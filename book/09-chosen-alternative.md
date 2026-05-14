# 9. תיאור החלופה הנבחרת

החלופה הנבחרת היא **לקוח BitTorrent מלא לפי BEP-3**,
ממומש כשני תהליכים: Python Engine לכל לוגיקת הפרוטוקול,
ו-Java GUI לממשק המשתמש. שני התהליכים מתקשרים דרך
REST/JSON על loopback.

## למה דווקא הארכיטקטורה הזו

**הפרדה לתהליכים שונים**. ה-Engine רץ ב-Python (asyncio
מצוין לעשרות חיבורי TCP מקבילים), וה-GUI רץ ב-Java
(Swing הוא toolkit בוגר וקבוע). כל אחד נבחר לפי החוזקות
שלו. ההפרדה הזו מאפשרת:

- **בידוד שגיאות**: crash ב-Java לא הורג את ההורדות
  שב-Python.
- **דיבוג קל**: ניתן להפעיל את ה-Engine בלי GUI ולבדוק
  אותו עם `curl`.
- **הרחבה עתידית**: אפשר להוסיף CLI client או mobile
  app ללא שינוי ב-Engine.

**REST/JSON כגשר**. שפה-אגנוסטי, מתועד, וקל לבדיקה.
החלופות שנדחו: JNI (מסבך deployment), gRPC (overkill
לפרויקט בקנה מידה הזה), named pipes (לא portable).

**אלגוריתמיקה כפולה**. המערכת מאפשרת לבחור בין שני
אלגוריתמים של בחירת piece (`rarest_first` / `random`)
ושני אלגוריתמים של בחירת peer (`tit_for_tat` /
`round_robin`). זה מאפשר השוואה אמפירית בין הגישות.

## רכיבים מרכזיים

הרכיבים העיקריים שיהיו במערכת:

- **Bencode encoder/decoder** — לפרסור קובצי `.torrent`
  וקבלת תגובות מ-tracker.
- **TorrentMetadata** — שמירת המידע מהקובץ (`info_hash`,
  pieces, files).
- **TrackerClient** — תקשורת HTTP/HTTPS עם ה-tracker
  (announce, parsing compact peer list).
- **PeerConnection** — חיבור TCP יחיד ל-peer; handshake,
  parsing הודעות, state machine.
- **PieceManager** — ניהול pieces ובחירת piece לפי
  rarest-first או random.
- **DownloadManager + Download** — תיאום כל ההורדה; לב
  המערכת.
- **SecurityManager** — אבטחה (אימות SHA-1, מערכת מוניטין,
  באנים).
- **Flask REST API** — חשיפת הפעולות ל-GUI.
- **SQLite** — שמירת היסטוריה וסטטיסטיקות.
- **Java GUI** עם 3 מחלקות ראשיות: `TorrentClientGUI`
  (חלון ראשי), `ApiService` (HTTP client), ו-
  `AlgorithmStatsDialog`.

## נימוקי בחירה לפי המחוון

- **Client + Server + DB + תקשורת**: ה-Engine הוא application
  server, ה-GUI הוא client, יש לנו SQLite כ-DB, ושלוש
  שכבות תקשורת (Local IPC, HTTP tracker, Peer Wire
  Protocol).
- **SWOT לבחירה**: מוצג בפרק 8 (3 חלופות).
- **שתי שפות + שפה מהודרת**: Python (מפורשת) + Java
  (מהודרת) — מתקיים.
- **אבטחת מידע**: פרק 12 (SecurityManager, SHA-1, מערכת
  מוניטין).
- **אלגוריתמים מתקדמים**: rarest-first, Tit-for-Tat,
  state machines (פרק 15.4).
- **מבני נתונים מתקדמים**: `Dict`, `Set`, `deque`,
  `ThreadPoolExecutor` (פרק 15.3).
