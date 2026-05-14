# פרק 19 – הודעות למשתמש (Alerts)

## פתיח

פרק זה מקטלג את **כל ההודעות שמופנות למשתמש** — popup-ים
מודאליים, אישורי פעולה, הודעות סטטוס, ולוג חי — כפי שדורש
סעיף 19 בנוהל ההגשה (עמ' 12, *"הודעות למשתמש (alert)
למיניהם"*).

המערכת מבדילה בין **ארבעה ערוצי הודעה** למשתמש:

1. **Popups מודאליים** (`JOptionPane`) — דורשים תגובה מיידית.
2. **Status bar** (`JLabel` ב-S1) — מציג מצב כללי לא-חוסם.
3. **Event log** (`JTextArea` ב-S1) — היסטוריית כל האירועים.
4. **תוויות תוכן** (`JLabel` ב-S7) — מסכמים נתונים.

---

## 19.1 Popups מודאליים (`JOptionPane`)

ארבעה סוגי popup קיימים במערכת, מקובצים לפי **חומרת השימוש**:

### 19.1.1 הודעות אישור (`showConfirmDialog`)

הודעות אלה דורשות מהמשתמש Yes/No לפני ביצוע פעולה הרסנית או
לא הפיכה.

| הודעה | מסך | טריגר | אופציות | פעולה ב-YES |
|---|---|---|---|---|
| `"Are you sure you want to cancel this download?"` | S4 | לחיצת Cancel ב-S1 | YES/NO | `apiService.cancel(id)` בthread נפרד |
| `"Clear all download history?"` | S6 | לחיצת Clear History ב-S5 או ב-S7 Tab 2 | YES/NO | `apiService.clearHistory()` (`DELETE /history`) |

**מאפיינים משותפים**:
- כותרת קצרה: `"Confirm Cancel"` או `"Confirm"`.
- אייקון "שאלה" סטנדרטי של Swing.
- כפתור ברירת מחדל: ב-Java Swing זה ה-`YES`, אך **אין
  בקוד** הגדרה מפורשת של `JOptionPane.NO_OPTION` כ-default
  — כלומר אם המשתמש לוחץ ENTER בלי לקרוא, הפעולה תקרה.
  זוהי **נקודה לשיפור עתידי** (פרק 26).

### 19.1.2 הודעות מידע (`showMessageDialog` עם `INFORMATION_MESSAGE`)

| הודעה | מסך | טריגר | פעולה ב-OK |
|---|---|---|---|
| `"<name>\nSaved to: <path>"` | S8 | זיהוי אוטומטי של מעבר state ל-`Completed` | סגירה |

- כותרת: `"Download Complete"`.
- אייקון "i" כחול של Swing.
- ההודעה מוצגת **פעם אחת בלבד** עבור כל torrent — מנגנון
  ה-`previousStates` Map מבטיח שמעבר state יחיד מייצר popup
  יחיד (וגם אם המשתמש סוגר את האפליקציה ופותח מחדש —
  ה-state יקרא מחדש מ-`previousStates.get(id)` כברירת מחדל
  null, מה שיגרום ל-popup לעבוד שוב; זוהי החלטה מודעת).

### 19.1.3 הודעות שגיאה (`showMessageDialog` עם `ERROR_MESSAGE`)

| הודעה | מסך | טריגר |
|---|---|---|
| `"Failed to start download:\n<ex.getMessage()>"` | S9 | `apiService.startDownload(...)` זרק חריגה |

- כותרת: `"Error"`.
- אייקון "X" אדום של Swing.
- ההודעה דינמית — מציגה את `<ex.getMessage()>` מ-Java
  או מ-Python. דוגמאות אופייניות לתוכן:
  - `"Invalid torrent file: Missing 'announce' field"`
    (מקור: `TorrentMetadataError` ב-Python).
  - `"Connection refused"` (אם השרת לא רץ).
  - `"Timeout"` (אם השרת תקוע).

**הערה חשובה**: שגיאות בפעולות Pause/Resume/Cancel/History/
Stats אינן מציגות popup; הן נכתבות ל-Event Log בלבד (סעיף
19.3.1). הגישה: רק שגיאה בפעולה היוזמת ביותר (Start Download)
מצדיקה הפרעה מודאלית.

---

## 19.2 Status Bar — הודעות מצב לא-חוסמות (S1)

ה-`statusLabel` בתחתית S1 משמש לסטטוס כללי, שאין צורך
לאשר אותו ולא חוסם את המשתמש. כל ההודעות הנכתבות אליו ע"י
`setStatus(text)`:

| הודעה | מתי |
|---|---|
| `"Ready"` | בעת יצירת חלון לפני כל פעולה |
| `"Connected to engine"` | אחרי ש-`checkServerConnection` החזיר זמין |
| `"Engine not available"` | אם הסרבר לא מגיב ב-`/health` |
| `"Starting download: <name>"` | בעת לחיצה על Add Torrent → קריאת `startDownload` |
| `"<N> downloads (<M> active)"` | אחרי כל ריענון (`refreshStatus`) — מציג סך הכל + פעילים |

ה-Status Bar **מתחלף בלי לחסום** את המשתמש; אם הוא לא רואה
שינוי, אין נזק.

---

## 19.3 Event Log — היסטוריית פעולות (S1)

ה-`logArea` (JTextArea במחצית התחתונה של S1) מקבל כל
הודעה דרך הפונקציה `log(message)`. כל שורה מקבלת חותמת זמן
בפורמט `[HH:mm:ss]` בתחילתה.

### 19.3.1 הודעות log אופייניות

הטבלה מסכמת את **כל הודעות ה-log** שמופיעות בקוד ה-GUI
(לפי הסדר בקובץ):

| הודעה | טריגר |
|---|---|
| `"Application started. Connecting to BitTorrent engine..."` | בעת יצירת `TorrentClientGUI` |
| `"Connected to BitTorrent engine."` | `isServerAvailable` החזיר true |
| `"WARNING: Cannot reach BitTorrent engine at localhost:5000"` | `isServerAvailable` החזיר false |
| `"Make sure the Python server is running: python -m python_engine.api_server"` | בעקבות הקודמת (הוראת הפעלה) |
| `"Download started: <name> → <dir> (ID: <id>)"` | קריאת `startDownload` הצליחה |
| `"ERROR: Failed to start download: <message>"` | חריגה ב-`startDownload` |
| `"Paused download: <id>"` | קריאת `pause` הצליחה |
| `"ERROR: Failed to pause: <message>"` | חריגה ב-`pause` |
| `"Resumed download: <id>"` | קריאת `resume` הצליחה |
| `"ERROR: Failed to resume: <message>"` | חריגה ב-`resume` |
| `"Cancelled download: <id>"` | קריאת `cancel` הצליחה |
| `"ERROR: Failed to cancel: <message>"` | חריגה ב-`cancel` |
| `"History cleared."` | קריאת `clearHistory` הצליחה (מתוך S5) |
| `"ERROR clearing history: <message>"` | חריגה ב-`clearHistory` |
| `"ERROR: Failed to load history: <message>"` | חריגה ב-`getHistory` |
| `"[engine] <msg>"` | שורת לוג שהגיעה דרך `/torrents/<id>/logs` |

### 19.3.2 שורות log שמגיעות מה-Engine

הקידומת `[engine]` מבדילה בין הודעות שמקורן ב-GUI עצמו לבין
הודעות שנשלפו מ-`apiService.getLogs(id, since)` — כלומר
הודעות שה-Python Engine רשם ב-`Download._log()`. דוגמאות
טיפוסיות לתוכן `[engine]`:

- `[engine] Starting download: ubuntu-22.04.iso`
- `[engine] Size: 4294967296 bytes, Pieces: 16384, Tracker: ...`
- `[engine] Contacting tracker: <url>`
- `[engine] Tracker responded: 50 peers found`
- `[engine] Connected to peer 91.189.91.42:6881`
- `[engine] Piece 1024 verified OK (1024/16384)`
- `[engine] Piece 2048 HASH FAILED from 1.2.3.4:6881`
- `[engine] Banned peer 1.2.3.4:6881 (too many hash failures)`

הודעות אלה נחתכות ע"י ה-`logSeqTracker` (Map<id, lastSeq>)
כדי שכל הודעה תוצג רק פעם אחת — גם אם ה-polling רץ כל 500ms.

### 19.3.3 ניהול תוקף הלוג

- **ב-Engine**: `_log_buffer = collections.deque(maxlen=200)` —
  עד 200 הודעות אחרונות לכל torrent (אחר כך הישנות נופלות).
- **ב-GUI**: `JTextArea` ללא מגבלה — מצטבר לאורך כל הסשן.
  בסשנים ארוכים עלול להיות גדל; **לא ממומש ניקוי אוטומטי**
  ב-GUI (נקודה לשיפור — פרק 26).
- **בעת הפעלה חדשה**: הלוג ריק; שורת ה-`"Application started..."`
  מופיעה ראשונה.

---

## 19.4 הודעות בתוויות גוף (Body Labels)

מעבר ל-status bar, יש 2 מקומות שבהם תוויות בודדות מציגות
מצב:

### 19.4.1 `summaryLabel` ב-S7 Tab 1

הצגה חד-שורתית מתחת ל-bar chart:
- אם יש נתונים: `"Total pieces: <N>, selections: <M>"` (או דומה).
- אם אין torrent עם נתונים: `"No data available."`.

### 19.4.2 שדות `statValueLabels[]` ב-S7 Tab 2

תשעת השדות מציגים `"—"` כברירת מחדל. בעת טעינת נתונים
מהצלחת `getStatsSummary`, הם מתעדכנים בערכים מצרפיים.

---

## 19.5 סיכום הפרק

הפרק קטלג את כל ההודעות למשתמש לפי 4 ערוצים:

1. **3 popup-ים מודאליים** (Confirm Cancel, Confirm Clear
   History, Download Complete) ו-**1 Error popup** —
   סך 4 סוגי popup פעילים.
2. **5 הודעות סטטוס** ב-status bar (`Ready`, Connected,
   Not Available, Starting download, סיכום פעיל).
3. **16 סוגי הודעות log** + log משוכפל מה-Engine
   (`[engine] ...`).
4. **2 תוויות גוף** ב-S7 (summaryLabel + שדות סטטיסטיקה).

**הגישה הכוללת**: רק פעולות שגיאה ביוזמת המשתמש (Start
Download) או הודעות הצלחה משמעותיות (Completion) מצדיקות
popup; שגיאות תקופתיות (failed pause/resume) רק נרשמות ב-log
כדי לא להפריע למשתמש. זוהי בחירה מודעת לטובת UX שקט.

הפרק הבא (פרק 20) יעבור לדיון רחב יותר על **ממשק המשתמש**
ככלל — עקרונות עיצוב, נגישות, ויעילות.
