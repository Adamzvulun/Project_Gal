# פרק 17 – תיאור פרטני של כל מסך באפליקציה

## פתיח

פרק זה מפרט, **עבור כל אחד מתשעת המסכים** של האפליקציה, את
שלוש הדרישות הקבועות בנוהל ההגשה (סעיף 17, עמ' 12):

- **17.x.1 — תפקיד המסך**: לאיזו פעולה הוא נועד.
- **17.x.2 — תיאור המסך**: רכיבי ה-UI, פריסה, התנהגות.
- **17.x.3 — צילום מסך**: הפניה ל-`IMAGES.md`.

המסכים ממוספרים S1–S9, באותו מספור של פרק 16 (תרשים המסכים).
תיאורי האלמנטים הספציפיים (כפתורים, שדות, רכיבי טבלה) מועברים
לפרק 18; הודעות שמופיעות למשתמש מועברות לפרק 19; היבטי
UX/UI כלליים — לפרק 20.

---

## 17.1 S1 — Main Window (חלון ראשי)

### 17.1.1 תפקיד המסך
**הציר המרכזי של האפליקציה** — כל פעולת המשתמש מתחילה ממנו.
המסך מציג את כל ההורדות הפעילות בטבלה, את הלוג החי של אירועי
האפליקציה, ומספק toolbar עם **כל הפקודות הציבוריות** (Add,
Pause, Resume, Cancel, History, Statistics) ושני `JComboBox`
לבחירת אלגוריתמים בזמן הוספת torrent.

### 17.1.2 תיאור המסך
- **קלאס**: `TorrentClientGUI extends JFrame`.
- **כותרת**: `"מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent"`
  (Hebrew RTL).
- **גודל**: 900×600 פיקסלים; מינימום 700×400; מתמקם במרכז
  המסך (`setLocationRelativeTo(null)`).
- **התנהגות סגירה**: `DO_NOTHING_ON_CLOSE` עם
  `WindowAdapter.windowClosing` שקורא ל-`shutdown()` — סוגר
  את ה-`ScheduledExecutorService` בצורה מסודרת.
- **פריסה (BorderLayout)**:
  - **North** — `JToolBar` לא-floatable עם שמונה כפתורים
    ושני קומבואקסים (פירוט בפרק 18).
  - **Center** — `JSplitPane` אנכי (`VERTICAL_SPLIT`) עם
    `resizeWeight=0.7`:
    - **Top**: `JScrollPane` עם `JTable` של ההורדות —
      שמונה עמודות (Name, Size, Progress, Speed, Peers, State,
      Location, ID). העמודה Progress משתמשת ב-
      `ProgressBarRenderer` מותאם המציג `JProgressBar`.
    - **Bottom**: `JPanel` עם `JLabel` "Event Log:" מעל
      `JScrollPane`+`JTextArea` (לא editable, פונט מונוספייס
      בגודל 12).
  - **South** — `JLabel` סטטוס עם BevelBorder נמוך, מציג
    טקסט מצב כללי (`"Ready"` / `"Starting download: ..."`).
- **עדכון אוטומטי**: `ScheduledExecutorService` יחיד מבצע
  `refreshStatus` כל 500ms — שולח `apiService.getStatus()`
  ב-Thread נפרד ומעדכן את הטבלה ב-EDT דרך
  `SwingUtilities.invokeLater`.
- **בחירת שורה**: `ListSelectionListener` מאזין ל-
  `getSelectionModel`, וקורא ל-`updateButtonStates` שמפעיל/מנטרל
  Pause/Resume/Cancel לפי ה-state של ההורדה הנבחרת.

### 17.1.3 צילום מסך
> **תרשים נדרש (Fig-18)**: צילום מסך של החלון הראשי במצב
> טיפוסי — שתי-שלוש הורדות פעילות בטבלה (אחת `Running`, אחת
> `Paused`, אחת `Completed`), `JProgressBar` נראה לעין,
> ולוג חי באזור התחתון. ראה רשומה ב-`IMAGES.md`.

---

## 17.2 S2 — Select Torrent File (`JFileChooser`)

### 17.2.1 תפקיד המסך
לאפשר למשתמש **לבחור קובץ `.torrent`** מתוך מערכת הקבצים
המקומית, לפני שמתחילים הורדה. זהו **הצעד הראשון** ב-UC-01
(Add Torrent — פרק 15.2).

### 17.2.2 תיאור המסך
- **קלאס**: `JFileChooser` סטנדרטי של Swing.
- **כותרת**: `"Select Torrent File"`.
- **מסנן קבצים**: `FileNameExtensionFilter("Torrent Files
  (*.torrent)", "torrent")` — קבצים אחרים מוסתרים מברירת מחדל.
- **מודאליות**: מודאלי מול ה-Main Window (`showOpenDialog(this)`).
- **פעולה ב-OK**: אם המשתמש בחר קובץ, מתקדמים ל-S3 (Choose
  Download Location). אחרת — `return` שקט וחזרה ל-S1.

### 17.2.3 צילום מסך
> **תרשים נדרש (Fig-19)**: צילום מסך של `JFileChooser` עם
> מסנן `*.torrent` פעיל, מציג קובץ דוגמה. ראה רשומה
> ב-`IMAGES.md`.

---

## 17.3 S3 — Choose Download Location (`JFileChooser`)

### 17.3.1 תפקיד המסך
לאפשר למשתמש **לבחור תיקיית יעד** שאליה תישמר ההורדה. זהו
הצעד השני (והאחרון) ב-UC-01.

### 17.3.2 תיאור המסך
- **קלאס**: `JFileChooser`.
- **כותרת**: `"Choose Download Location"`.
- **מצב בחירה**: `setFileSelectionMode(DIRECTORIES_ONLY)` —
  בחירת תיקיות בלבד.
- **filter "All Files"** מבוטל: `setAcceptAllFileFilterUsed(false)`.
- **פעולה ב-OK**: ה-GUI שולח את הקובץ + הנתיב ל-
  `apiService.startDownload(...)` ב-Thread נפרד; חוזר ל-S1
  ומציג סטטוס "Starting download: <name>".

### 17.3.3 צילום מסך
> **תרשים נדרש (Fig-20)**: צילום מסך של `JFileChooser`
> במצב DIRECTORIES_ONLY. ראה רשומה ב-`IMAGES.md`.

---

## 17.4 S4 — Confirm Cancel (`JOptionPane`)

### 17.4.1 תפקיד המסך
**אישור הרסני** — לוודא שהמשתמש באמת רוצה לבטל את ההורדה
(`Cancel` שלא ניתן לשחזור — ההורדה תיכבה, ה-tracker יקבל
`event=stopped`, וה-state יסומן `Cancelled` ב-SQLite).

### 17.4.2 תיאור המסך
- **קלאס**: `JOptionPane.showConfirmDialog`.
- **הודעה**: `"Are you sure you want to cancel this download?"`.
- **כותרת**: `"Confirm Cancel"`.
- **כפתורים**: `YES_NO_OPTION` (כן/לא).
- **פעולה**: ב-`YES_OPTION` נקראת `apiService.cancel(id)`
  ב-Thread נפרד; אחרת `return` שקט.

### 17.4.3 צילום מסך
> **תרשים נדרש (Fig-21)**: צילום מסך של dialog האישור עם
> ההודעה "Are you sure...". ראה רשומה ב-`IMAGES.md`.

---

## 17.5 S5 — Download History (`JDialog`)

### 17.5.1 תפקיד המסך
להציג את **כל ההורדות שהסתיימו** (גם מהפעלות קודמות, כי הנתונים
שמורים ב-SQLite מתמשך), עם סטטיסטיקות ביצוע מצרפיות לכל אחת.
מאפשר גם **לרוקן** את ההיסטוריה.

### 17.5.2 תיאור המסך
- **קלאס**: `JDialog` (לא-מודאלי, `false` ב-constructor) עם
  כותרת `"Download History"`.
- **גודל**: 820×380 פיקסלים; מתמקם יחסית לחלון הראשי.
- **פריסה (BorderLayout)**:
  - **Center** — `JScrollPane` עם `JTable` של 9 עמודות:
    Name, Size, Status, Avg Speed, Peak Speed, Time,
    Piece Algo, Peer Algo, Choke Cycles.
  - **South** — `JPanel` עם FlowLayout, שני כפתורים:
    `"Clear History"` ו-`"Close"`.
- **מקור נתונים**: `apiService.getHistory()` →
  `GET /history` → JOIN של `torrents` ו-`performance_stats`
  ב-SQLite.
- **התנהגות "Clear History"**: פותח S6 (Confirm Clear);
  ב-Yes — קריאה ל-`apiService.clearHistory()` →
  `DELETE /history`, ואז `model.setRowCount(0)` מרוקן את
  ה-JTable מבלי לסגור את ה-Dialog.
- **התנהגות "Close"**: `dlg.dispose()` — סוגר את החלון.
- **`autoResizeMode = AUTO_RESIZE_ALL_COLUMNS`**: עמודות
  מתמתחות אוטומטית לרוחב הזמין.
- **`reorderingAllowed = false`**: סדר העמודות קבוע.

### 17.5.3 צילום מסך
> **תרשים נדרש (Fig-22)**: צילום מסך של History Dialog עם
> 3–5 הורדות שהסתיימו, מציג ערכי מהירות וזמן. ראה רשומה
> ב-`IMAGES.md`.

---

## 17.6 S6 — Confirm Clear History (`JOptionPane`)

### 17.6.1 תפקיד המסך
**אישור הרסני** — לוודא שהמשתמש באמת רוצה למחוק את כל
ההיסטוריה (פעולה לא הפיכה — ב-`DELETE /history` כל ארבע
הטבלאות `torrents`, `performance_stats`, `algorithm_stats`,
`events` מתרוקנות).

### 17.6.2 תיאור המסך
- **קלאס**: `JOptionPane.showConfirmDialog`.
- **הודעה**: `"Clear all download history?"`.
- **כותרת**: `"Confirm"`.
- **כפתורים**: `YES_NO_OPTION`.
- **owner**: יכול להיות S5 (history dialog) או S7 (stats
  dialog, בלשונית General Statistics — שני המקומות שיש בהם
  "Clear History").

### 17.6.3 צילום מסך
> **תרשים נדרש (Fig-23)**: צילום מסך של dialog "Clear all
> download history?". ראה רשומה ב-`IMAGES.md`.

---

## 17.7 S7 — Algorithm Statistics (`JDialog` עם `JTabbedPane`)

### 17.7.1 תפקיד המסך
להציג **ניתוח גרפי וכמותי** של ביצועי האלגוריתמים: התפלגות
בחירות *rarest-first* בהורדה ספציפית (Tab 1), וסטטיסטיקות
מצרפיות על כל ההורדות (Tab 2). זה המסך שבו רואים בעצם את
ערך הניסויים האמפיריים שמתואר בפרק 24.

### 17.7.2 תיאור המסך
- **קלאס**: `AlgorithmStatsDialog extends JDialog` (לא-
  מודאלי).
- **כותרת**: `"Algorithm Statistics"`.
- **גודל**: 800×560 פיקסלים; מינימום 640×440.
- **פריסה (BorderLayout)**:
  - **Center** — `JTabbedPane` עם שתי לשוניות:
    - **Tab 1: "Piece Selection (Rarest-First)"**
      - **North**: `JPanel` עם `JLabel "Torrent:"` +
        `JComboBox` של torrents שיש להם נתוני algorithm_stats
        + כפתור `"Refresh"`.
      - **Center**: `BarChartPanel` (`JPanel` מותאם שעובד
        עם `Graphics2D`) — מצייר עמודות אופקיות של בחירות
        rarest-first per-piece.
      - **South**: `JLabel summaryLabel` עם שורת סיכום.
    - **Tab 2: "General Statistics"**
      - **North**: `JPanel` עם כפתורי `"Refresh"` +
        `"Clear History"`.
      - **Center**: 9 שדות מידע (`STAT_NAMES`):
        Total Files Downloaded, Total Data Downloaded,
        Total Download Time, Average Download Speed,
        Best Peak Speed, Total Peers Connected,
        Total Choke/Unchoke Cycles, Largest File,
        Fastest Download.
  - **South** — `JPanel` עם כפתור `"Close"` יחיד
    (FlowLayout מיושר ימינה).
- **מקור נתונים**:
  - Tab 1: `apiService.getAlgorithmStats(id)` → רשומות
    `algorithm_stats` ל-torrent שנבחר.
  - Tab 2: `apiService.getStatsSummary()` → אגרגציה
    מצרפית.
- **טעינה אסינכרונית**: `loadData()` רץ ב-Thread נפרד; אם
  אין נתונים, השדות מציגים `"—"` ו-`summaryLabel` מציג
  הודעה ידידותית.

### 17.7.3 צילום מסך
> **תרשים נדרש (Fig-24)**: שני צילומי מסך של ה-Dialog —
> אחד של Tab 1 (Piece Selection) עם bar chart נראה, ואחד
> של Tab 2 (General Statistics) עם 9 השדות מאוכלסים. ראה
> רשומה ב-`IMAGES.md`.

---

## 17.8 S8 — Download Complete Popup (`JOptionPane`)

### 17.8.1 תפקיד המסך
**להודיע למשתמש** שהורדה הסתיימה בהצלחה. זוהי הודעה שמופיעה
**אוטומטית** — לא יזומה ע"י המשתמש — ברגע שה-`updateTable`
מזהה מעבר state מ-`Running` (או כל מצב אחר) ל-`Completed`.

### 17.8.2 תיאור המסך
- **קלאס**: `JOptionPane.showMessageDialog`.
- **סוג**: `INFORMATION_MESSAGE`.
- **כותרת**: `"Download Complete"`.
- **הודעה**: שתי שורות —
  ```
  <torrent.name>
  Saved to: <download_path>
  ```
- **מנגנון הפעלה**: ב-`updateTable`, לכל torrent ב-statuses,
  בודקים אם `previousStates.get(id)` היה שונה מ-`"Completed"`
  ו-`status.state` החדש הוא `"Completed"`. אם כן —
  `JOptionPane.showMessageDialog(...)` ב-EDT דרך
  `SwingUtilities.invokeLater`. אחרי הצגה, `previousStates.put`
  מעדכן את המצב כדי שה-popup לא יופיע שוב.

### 17.8.3 צילום מסך
> **תרשים נדרש (Fig-25)**: צילום מסך של popup "Download
> Complete" עם שם קובץ דוגמה ונתיב. ראה רשומה ב-`IMAGES.md`.

---

## 17.9 S9 — Error Popup (`JOptionPane`)

### 17.9.1 תפקיד המסך
**להודיע למשתמש** על שגיאה שדורשת התייחסות מיידית. בולט מבחינה
ויזואלית — מציג אייקון "Error" של Swing ועוצר את הזרימה עד
שהמשתמש לוחץ OK.

### 17.9.2 תיאור המסך
- **קלאס**: `JOptionPane.showMessageDialog`.
- **סוג**: `ERROR_MESSAGE`.
- **כותרת**: `"Error"`.
- **הודעה**: דינמית — נוסחה כללית
  `"Failed to <action>:\n<ex.getMessage()>"`, כאשר
  `<action>` הוא "start download" / "pause" / "resume" / וכו'.
- **מקרים בהם מופיע**:
  - `addTorrent` (S3 → API call): כשל בקריאת
    `apiService.startDownload`.
  - שאר ההודעות (`onPause`, `onResume`, `onCancel`,
    `onShowHistory`, `onShowStats`) רושמות שגיאה ל-log
    בלבד, ללא popup — כדי לא להציף את המשתמש בחלונות
    אם השרת מנותק לרגע (`refreshStatus` יחזיר אותו אוטומטית
    בריענון הבא).

### 17.9.3 צילום מסך
> **תרשים נדרש (Fig-26)**: צילום מסך של popup שגיאה
> טיפוסי — לדוגמה "Failed to start download: Invalid torrent
> file". ראה רשומה ב-`IMAGES.md`.

---

## 17.10 סיכום הפרק

הפרק תיאר את **9 המסכים** במלואם, לפי תבנית הנוהל
(תפקיד · תיאור · צילום מסך). תשעה הפניות חדשות נוספו ל-
`IMAGES.md` (Fig-18 עד Fig-26) — אחת לכל מסך פרט ל-S7 שמקבל
שתיים (אחת לכל לשונית).

הפרק הבא (פרק 18) מפרט את **אלמנטי התצוגה הספציפיים**
(כפתורים, JComboBoxים, רכיבי הטבלה, ProgressBar, וכו') בכל
מסך — מה תפקידם וכיצד הם מתנהגים.
