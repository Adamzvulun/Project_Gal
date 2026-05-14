# 17. תיאור פרטני של כל מסך באפליקציה

המערכת כוללת תשעה מסכים. עבור כל אחד מצוין תפקיד, תיאור,
ומיקום בקוד.

## 17.1 Main Window (S1)

**תפקיד**: הציר המרכזי של האפליקציה — כל פעולה מתחילה
ממנו.

**תיאור**: `JFrame` בגודל 900×600 (מינימום 700×400) עם
כותרת `"מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent"`.
פריסה ב-BorderLayout: toolbar למעלה, `JSplitPane` אנכי
במרכז (`resizeWeight=0.7`), ו-`statusLabel` למטה. ב-
SplitPane: `JTable` של ההורדות עם 8 עמודות (Name, Size,
Progress, Speed, Peers, State, Location, ID), ו-
`JTextArea` של Event Log בפונט monospace. `ProgressBar­Renderer`
מצייר את עמודת ה-Progress כ-`JProgressBar` שצובע מ-כחול
לירוק ב-100%. `ScheduledExecutorService` מבצע polling
של ה-API כל 500ms.

## 17.2 Select Torrent File (S2)

**תפקיד**: בחירת קובץ `.torrent` מתוך מערכת הקבצים.

**תיאור**: `JFileChooser` עם כותרת `"Select Torrent
File"` ומסנן `FileNameExtensionFilter("Torrent Files
(*.torrent)", "torrent")`. מודאלי מול ה-Main Window. אם
המשתמש לוחץ Cancel, חוזרים ל-Main Window בלי שינוי.

## 17.3 Choose Download Location (S3)

**תפקיד**: בחירת תיקיית יעד.

**תיאור**: `JFileChooser` עם כותרת `"Choose Download
Location"`, `FileSelectionMode=DIRECTORIES_ONLY`,
`setAcceptAllFileFilterUsed(false)`. נפתח אחרי שהמשתמש
בחר קובץ ב-S2. עם OK, ה-GUI שולח `POST /torrents` עם
שני הקבצים.

## 17.4 Confirm Cancel (S4)

**תפקיד**: אישור לפני ביטול הורדה.

**תיאור**: `JOptionPane.showConfirmDialog` עם הודעה
`"Are you sure you want to cancel this download?"`,
כותרת `"Confirm Cancel"`, וכפתורי YES/NO. ב-YES נשלחת
קריאה ל-`apiService.cancel(id)`.

## 17.5 Download History (S5)

**תפקיד**: צפייה בכל ההורדות שהסתיימו (כולל מהפעלות
קודמות, מ-SQLite).

**תיאור**: `JDialog` non-modal בגודל 820×380 עם כותרת
`"Download History"`. מכיל `JTable` עם 9 עמודות (Name,
Size, Status, Avg Speed, Peak Speed, Time, Piece Algo,
Peer Algo, Choke Cycles) ושני כפתורים בתחתית: `Clear
History` ו-`Close`. מקור הנתונים: `GET /history` (JOIN
של `torrents` ו-`performance_stats`).

## 17.6 Confirm Clear History (S6)

**תפקיד**: אישור לפני ניקוי כל ההיסטוריה.

**תיאור**: `JOptionPane.showConfirmDialog` עם הודעה
`"Clear all download history?"`. ב-YES נשלחת קריאה
ל-`apiService.clearHistory()` (`DELETE /history`),
שמרוקנת את כל ארבע הטבלאות ב-SQLite.

## 17.7 Algorithm Statistics (S7)

**תפקיד**: ניתוח גרפי וכמותי של ביצועי האלגוריתמים.

**תיאור**: `JDialog` non-modal בגודל 800×560 עם
`JTabbedPane` של שתי לשוניות:

- **Tab 1 — Piece Selection (Rarest-First)**: ComboBox
  לבחירת torrent + bar chart שמצויר ב-Java2D ב-
  `BarChartPanel` (התפלגות בחירות rarest-first per-piece)
  + `summaryLabel` עם שורת סיכום.
- **Tab 2 — General Statistics**: 9 שדות מצרפיים: Total
  Files Downloaded, Total Data Downloaded, Total Download
  Time, Average Download Speed, Best Peak Speed, Total
  Peers Connected, Total Choke/Unchoke Cycles, Largest
  File, Fastest Download. נטענים מ-`/stats-summary`.

## 17.8 Download Complete Popup (S8)

**תפקיד**: הודעה אוטומטית על השלמת הורדה.

**תיאור**: `JOptionPane.INFORMATION_MESSAGE` עם הודעה
`"<name>\nSaved to: <path>"` וכותרת `"Download Complete"`.
מופעל אוטומטית ב-`updateTable` כשמתגלה מעבר state ל-
`Completed`. ה-Map `previousStates` מבטיח שיופיע פעם
אחת לכל torrent.

## 17.9 Error Popup (S9)

**תפקיד**: הודעה על שגיאה שדורשת התייחסות.

**תיאור**: `JOptionPane.ERROR_MESSAGE` עם כותרת `"Error"`.
מופיע רק בכשל של `apiService.startDownload(...)` —
שגיאות pause/resume/cancel/history נרשמות ב-log בלבד
כדי לא להציף את המשתמש בהפרעות מודאליות מיותרות.
