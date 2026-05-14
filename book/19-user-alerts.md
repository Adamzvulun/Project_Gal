# 19. הודעות למשתמש

המערכת מפנה למשתמש הודעות דרך ארבעה ערוצים: popups
מודאליים (`JOptionPane`), שורת סטטוס בתחתית החלון
הראשי, יומן אירועים חי (`JTextArea`), ותוויות גוף בחלון
הסטטיסטיקות.

## Popups מודאליים

**הודעות אישור** (`JOptionPane.showConfirmDialog`,
YES/NO) — לפני פעולות לא הפיכות:

| הודעה | כותרת | טריגר | פעולה ב-YES |
|---|---|---|---|
| "Are you sure you want to cancel this download?" | Confirm Cancel | לחיצת Cancel | `apiService.cancel(id)` |
| "Clear all download history?" | Confirm | לחיצת Clear History | `apiService.clearHistory()` |

**הודעת מידע** (`INFORMATION_MESSAGE`) — Download Complete:
מופיעה אוטומטית כשמתגלה מעבר state ל-`Completed`. הודעה
דו-שורית: `"<name>\nSaved to: <path>"`. ה-Map
`previousStates` מבטיח שזה יקרה פעם אחת לכל torrent.

**הודעת שגיאה** (`ERROR_MESSAGE`) — מופיעה רק בכשל של
`startDownload`. הודעה דינמית בפורמט `"Failed to <action>:\n<message>"`.
שגיאות בפעולות אחרות (pause/resume/cancel) נרשמות
ב-Event Log בלבד כדי לא להפריע בהפרעות מיותרות.

## שורת סטטוס (S1)

הודעות שמופיעות ב-`statusLabel`:

- "Ready" — מצב התחלתי.
- "Connected to engine" — אחרי אישור שהשרת זמין.
- "Engine not available" — אם השרת לא מגיב.
- "Starting download: <name>" — בעת לחיצת Add Torrent.
- "N downloads (M active)" — סיכום בכל ריענון.

## Event Log (S1)

כל הודעה נכתבת עם חותמת זמן `[HH:mm:ss]` ע"י הפונקציה
`log(message)`. דוגמאות:

```
[14:23:01] Application started. Connecting to BitTorrent engine...
[14:23:02] Connected to BitTorrent engine.
[14:25:14] Download started: ubuntu-22.04.iso → /home/user/Downloads (ID: a1b2c3d4)
[14:25:18] [engine] Connected to peer 91.189.91.42:6881
[14:25:19] [engine] Piece 1 verified OK (1/16384)
[14:30:02] Paused download: a1b2c3d4
[14:31:15] [engine] Banned peer 1.2.3.4:6881 (too many hash failures)
[14:35:18] ERROR: Failed to start download: Invalid torrent file
```

הקידומת `[engine]` מבדילה בין הודעות שמקורן ב-GUI לבין
הודעות שנשלפו מ-`apiService.getLogs(id, since)` —
הודעות שה-Python Engine רשם ב-`Download._log()`. ה-Map
`logSeqTracker` (id → lastSeq) מבטיח שכל הודעה תוצג רק
פעם אחת.

הניהול: ה-buffer ב-Engine הוא
`collections.deque(maxlen=200)` — עד 200 הודעות אחרונות
לכל torrent. ה-`JTextArea` ב-GUI אינו מוגבל ומצטבר
לאורך הסשן.

## תוויות גוף ב-S7

**`summaryLabel`** (Tab 1) מציג שורה אחת מתחת ל-bar
chart, למשל "Total pieces: 1024, selections: 837,
average: 0.82". אם אין נתונים: "No statistics available."

**`statValueLabels[]`** (Tab 2) הם 9 שדות שמוצגים
בפורמט `<NAME>:  <VALUE>`. כברירת מחדל כל ערך הוא "—".
אחרי טעינה מ-`/stats-summary` הם מתעדכנים בערכים
המצרפיים.
