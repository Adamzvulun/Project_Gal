# פרק 18 – תיאור אלמנטי תצוגה

## פתיח

פרק זה מסכם את **כל אלמנטי התצוגה** (כפתורים, שדות, רכיבי
טבלה, JComboBox, JProgressBar, JTextArea, JLabel, וכו') —
תפקידם, התנהגותם, ומיקומם במסכים, כפי שדורש סעיף 18 בנוהל
ההגשה (עמ' 12, *"עבור כל אלמנט תצוגה — כפתור, תיבת טקסט וכו'
— יש להסביר את תפקידם"*).

הסעיפים מאורגנים לפי **סוג אלמנט** (כפתורים, combo boxes,
טבלאות וכו') כדי שיהיה קל למצוא כל אלמנט. בכל ערך מצוין
המסך שבו מופיע (S1–S9 לפי פרק 16) והקובץ ושורת המקור.

---

## 18.1 כפתורים (`JButton`)

הטבלה הבאה מסכמת את **כל הכפתורים** באפליקציה:

| כפתור | מסך | תפקיד | מצב Enabled |
|---|---|---|---|
| **Add Torrent** | S1 (toolbar) | פותח את S2/S3 לבחירת קובץ ויעד | תמיד פעיל |
| **Pause** | S1 (toolbar) | משהה את ההורדה הנבחרת | רק כאשר state="Running" |
| **Resume** | S1 (toolbar) | מחדש הורדה שהושהתה | רק כאשר state="Paused" |
| **Cancel** | S1 (toolbar) | פותח את S4 לאישור ביטול | רק כאשר state ∈ {"Running","Paused"} |
| **History** | S1 (toolbar) | פותח את S5 (History Dialog) | תמיד פעיל |
| **Statistics** | S1 (toolbar) | פותח את S7 (Algorithm Stats) | תמיד פעיל |
| **Clear History** | S5, S7 (Tab 2) | פותח את S6 לאישור ניקוי | תמיד פעיל |
| **Close** | S5, S7 | סוגר את ה-Dialog (`dispose()`) | תמיד פעיל |
| **Refresh** | S7 (שתי הלשוניות) | טוען מחדש נתונים מה-API | תמיד פעיל |
| **Yes / No** | S4, S6 | אישור/ביטול ב-`JOptionPane` | תמיד פעיל |
| **OK** | S8, S9 | סגירת popup ה-information/error | תמיד פעיל |

**מנגנון הפעלה/השבתה (S1)**: ה-`ListSelectionListener` על
`downloadTable.getSelectionModel()` קורא ל-`updateButtonStates()`
בכל שינוי בחירה; הפונקציה בודקת את ה-state של ההורדה הנבחרת
ומעדכנת את ה-`setEnabled(true/false)` של Pause/Resume/Cancel
לפי כללי ה-state machine.

**Tooltips**: ארבעת הכפתורים הראשיים מקבלים `setToolTipText`
המסביר את פעולתם:
- Add Torrent: `"Select a .torrent file to download"`.
- Pause: `"Pause selected download"`.
- Resume: `"Resume selected download"`.
- Cancel: `"Cancel selected download"`.
- History: `"View download history"`.
- Statistics: `"Algorithm statistics visualization"`.

---

## 18.2 רכיבי בחירה (`JComboBox`)

| Combo | מסך | אפשרויות | תפקיד |
|---|---|---|---|
| **Piece Algorithm** | S1 (toolbar) | `"Rarest First"`, `"Random"` | בחירת אלגוריתם בחירת piece להורדה הבאה |
| **Peer Algorithm** | S1 (toolbar) | `"Tit-for-Tat"`, `"Round Robin"` | בחירת אלגוריתם choke/unchoke להורדה הבאה |
| **Torrent picker** | S7 (Tab 1) | רשימת torrents שיש להם נתוני algorithm_stats | בחירת torrent להצגת bar chart שלו |

הערה חשובה לגבי שני ה-Combos ב-S1: ה-string שמופיע ב-UI
("Rarest First", "Tit-for-Tat") שונה מערך ה-API
("rarest_first", "tit_for_tat"). ההמרה מתבצעת ב-`addTorrent`
דרך `.toLowerCase().replace(" ", "_").replace("-", "_")` —
כך ה-GUI מציג שמות ידידותיים בעוד ה-API מקבל מזהים תקניים.

הגודל המקסימלי של ה-Combos נקבע ל-`Dimension(120, 30)` כדי
שלא יתפסו רוחב יתר ב-toolbar.

---

## 18.3 טבלת ההורדות (`JTable` ראשי, S1)

הטבלה היא רכיב התצוגה הראשי בחלון הראשי, ומציגה את כל
ההורדות הפעילות. שמונה עמודות:

| # | שם עמודה | רוחב מועדף | סוג Java | תוכן | פורמט |
|---|---|---|---|---|---|
| 0 | **Name** | 200 | `String` | שם הקובץ מתוך `.torrent` | טקסט גולמי |
| 1 | **Size** | 80 | `String` | גודל מצרפי בבתים | `formatSize`: `4.0 GB`, `512.0 MB`, וכו' |
| 2 | **Progress** | 120 | `Double` | אחוז התקדמות 0–100 | מוצג ע"י `ProgressBarRenderer` (`JProgressBar`) |
| 3 | **Speed** | 100 | `String` | מהירות הורדה ב-`bytes/sec` | `formatSpeed`: `1.2 MB/s`, `512.0 KB/s` |
| 4 | **Peers** | 60 | `String` | מספר peers מחוברים | `String.valueOf(int)` |
| 5 | **State** | 80 | `String` | ערך ה-`DownloadState` enum | `Queued/Running/Paused/Completed/Cancelled/Error` |
| 6 | **Location** | 200 | `String` | נתיב מלא של הקובץ שמורד | טקסט |
| 7 | **ID** | 70 | `String` | 8 תווי hex המזהים את ההורדה | טקסט |

**הגדרות מודל**:
- `DefaultTableModel(COLUMN_NAMES, 0)`: 0 שורות התחלתי;
  שורות מתווספות ב-`updateTable` אחרי כל polling.
- `isCellEditable(row, column) → false`: **כל התאים read-only**
  — המשתמש לא יכול לערוך ערכים בטבלה.
- `getColumnClass(col)`: רק עמודה 2 (Progress) היא `Double.class`,
  כל היתר `String.class` — כדי שה-`ProgressBarRenderer` יקבל
  את הערך כ-Double.

**מנגנון רענון בלי לאבד בחירה**: לפני `setRowCount(0)`
ההורדה הנבחרת נשמרת ב-`selectedId`; לאחר טעינת הנתונים החדשים,
לולאה ב-`updateTable` מאתרת את ה-ID ומבצעת
`setRowSelectionInterval(i, i)` כדי לשחזר את הבחירה.

**הגדרות מראה**:
- `SINGLE_SELECTION` — אפשר לבחור רק שורה אחת בכל פעם.
- `setRowHeight(25)` — מאפשר ל-`JProgressBar` להתאים בגובה.
- `getTableHeader().setReorderingAllowed(false)` — סדר עמודות
  קבוע (חשוב כי ה-`updateTable` מסתמך על מיקום עמודת ID).

### 18.3.1 `ProgressBarRenderer` (renderer מותאם)

`static class ProgressBarRenderer extends DefaultTableCellRenderer`
— מימוש מותאם של `getTableCellRendererComponent` המחזיר
`JProgressBar`:

- `progressBar = new JProgressBar(0, 100)` עם
  `setStringPainted(true)` כך שהאחוז מודפס בתוך הבר עצמו.
- `progressBar.setString(String.format("%.1f%%", progress))`
  — מציג תווית כמו `"73.4%"`.
- **צבע דינמי**:
  - `progress < 100` → כחול בהיר `Color(60, 120, 200)`.
  - `progress = 100` → ירוק `Color(50, 150, 50)`.

זוהי **הזרת ה-Java2D היחידה ב-S1** — שאר התאים הם טקסט פשוט.

---

## 18.4 טבלת ההיסטוריה (`JTable` ב-S5)

ל-S5 יש `JTable` משלה (לא חולקת מודל עם ה-S1) — תשע עמודות:

| # | שם | תוכן | מקור JSON | פורמט |
|---|---|---|---|---|
| 0 | Name | שם torrent | `name` | טקסט |
| 1 | Size | גודל | `size` (long) | `formatSize` |
| 2 | Status | סטטוס סופי | `final_status` | טקסט (`Completed`/`Cancelled`/`Error`) |
| 3 | Avg Speed | מהירות ממוצעת | `avg_speed` (double) | `formatSpeed` |
| 4 | Peak Speed | מהירות שיא | `peak_speed` (double) | `formatSpeed` |
| 5 | Time | משך הורדה | `total_time_seconds` (int) | `formatDuration` → `HH:MM:SS` |
| 6 | Piece Algo | אלגוריתם piece | `piece_algorithm` | `friendlyAlgo`: `rarest_first`→`Rarest First` |
| 7 | Peer Algo | אלגוריתם peer | `peer_algorithm` | `friendlyAlgo`: `tit_for_tat`→`Tit-for-Tat` |
| 8 | Choke Cycles | מעגלי choke/unchoke | `choke_cycles` (int) | `String.valueOf` |

**הגדרות**:
- `AUTO_RESIZE_ALL_COLUMNS` — עמודות מתפרשות לכל רוחב החלון.
- `reorderingAllowed = false`.
- `isCellEditable = false` — read-only.

---

## 18.5 רכיבי טקסט גלוי

### 18.5.1 `JTextArea` (S1 — Event Log)

- **מיקום**: חצי תחתון של ה-`JSplitPane` ב-S1.
- **הגדרות**:
  - `setEditable(false)` — לא ניתן להקליד.
  - `setFont(Font.MONOSPACED, PLAIN, 12)` — פונט קבוע-רוחב
    לקריאת הודעות מערכת.
- **מנגנון log**: כל קריאה ל-`log(message)` מוסיפה שורה עם
  חותמת זמן `[HH:mm:ss]` בתחילתה, ולאחר מכן עושה
  `setCaretPosition(getDocument().getLength())` כדי לגלול
  אוטומטית לתחתית.
- **תוכן טיפוסי**: `[14:23:01] Download started: ubuntu-22.04.iso → /home/user/Downloads`, `[14:23:04] [engine] Connected to peer 91.189.91.42:6881`, `[14:25:18] Piece 1024 verified OK (1024/16384)`.

### 18.5.2 `JLabel` סטטוס (S1 — Status Bar)

- **מיקום**: BorderLayout.SOUTH של S1.
- **גבול**: `LoweredBevelBorder` — נראה ובהיר שזהו status bar
  בתחתית החלון.
- **תוכן דינמי**: `setStatus("...")` מעדכן את הטקסט. דוגמאות:
  - `"Ready"` — מצב התחלתי.
  - `"Connected to engine"` — לאחר אישור server reachable.
  - `"Engine not available"` — אם הסרבר לא מגיב.
  - `"Starting download: <name>"` — בעת אתחול הורדה חדשה.
  - `"5 downloads (3 active)"` — סיכום פעילות בכל ריענון.

### 18.5.3 `JLabel` בתוך S7 (`summaryLabel`)

- **מיקום**: BorderLayout.SOUTH של Tab 1 ב-S7.
- **גבול**: `EmptyBorder(4, 4, 0, 0)` — מרווח קל משמאל
  ולמעלה.
- **תוכן**: מציג שורה אחת שמסכמת את ה-bar chart — למשל
  `"Total pieces: 1024, selections: 837, average: 0.82"`.
  כאשר אין נתונים: `"No statistics available."`.

### 18.5.4 שדות הסטטיסטיקה ב-S7 Tab 2 (`statValueLabels[]`)

- 9 שדות מסוג `JLabel`, אחד לכל פריט ב-`STAT_NAMES`.
- כל שדה בפורמט `<NAME>:  <VALUE>` כאשר NAME מודגש.
- ה-VALUE מתעדכן ב-`loadData()` — אם אין נתונים, `"—"`.

---

## 18.6 רכיבי גרפיקה (Java2D)

### 18.6.1 `BarChartPanel` (`AlgorithmStatsDialog`)

`static class BarChartPanel extends JPanel` — צייר custom
לבר-צ'רט אופקי של בחירות rarest-first:

- **`paintComponent(Graphics g)`** מקבל `Graphics2D g2`
  ומפעיל **anti-aliasing** (`KEY_ANTIALIASING`).
- **`setData(int[] indices, int[] selections)`** מעדכן את
  הנתונים; `repaint()` מצויר מחדש.
- **התאמת רוחב אוטומטית**: רוחב כל עמודה מחושב מ-
  `getWidth() / num_bars` עם רווח קבוע ביניהן, כך שכל
  הנתונים נכנסים בחלון בלי גלילה.
- **תוויות**: ציר X מציג מקבץ piece indices (כל k-י); ציר Y
  מציג scale עם ערכים.

---

## 18.7 רכיבי המבנה והפריסה

| רכיב | מסך | תפקיד |
|---|---|---|
| **`JToolBar`** | S1 (North) | מסגרת לכפתורים וקומבואקסים; `setFloatable(false)` כדי שלא יוצא מהחלון |
| **`JSplitPane`** | S1 (Center) | חלוקה בין טבלה (top) ולוג (bottom); `resizeWeight=0.7` |
| **`JScrollPane`** | S1×2, S5 | גלילה לטבלאות ולאזור הלוג |
| **`JTabbedPane`** | S7 | מעבר בין Tab 1 (Piece Selection) ל-Tab 2 (General Stats) |
| **`JPanel`** (FlowLayout) | S5, S7 (bottom) | מסגרת לכפתורים בתחתית — מיושר ימינה |
| **`EmptyBorder`** | S7, mainPanel | מרווחים פנימיים (לא רואים אותו, רק את המרווח שהוא יוצר) |
| **`LoweredBevelBorder`** | S1 status bar | אפקט "שקוע" לסרגל הסטטוס |

---

## 18.8 סיכום הפרק

הפרק קטלג **6 קטגוריות של אלמנטי תצוגה** — כפתורים (11),
combo boxes (3), טבלאות (2 — ראשית והיסטוריה), רכיבי טקסט
גלוי (4 סוגים), רכיבי גרפיקה (BarChartPanel), ורכיבי
פריסה (7 סוגים). לכל אחד צוין תפקיד, מסך, ו-source location
מדויק.

**הדגשים מרכזיים**:
- כל הטבלאות **read-only** (`isCellEditable=false`).
- כפתורי הפעולה **מקבלים enabled/disabled דינמי** לפי state
  של ההורדה הנבחרת.
- ה-`ProgressBarRenderer` הוא **הרכיב היחיד עם render
  מותאם** ב-S1; `BarChartPanel` הוא היחיד עם ציור Java2D
  ב-S7.
- כל ה-Combo boxes משתמשים ב-string conversion (`friendlyAlgo`
  ו-ה-`.toLowerCase().replace(...)`) כדי להפריד בין תצוגה
  ידידותית לזהות מזהי ה-API.

הפרק הבא (פרק 19) יפרט את **הודעות המשתמש** — popup-ים,
log lines, ושורות סטטוס.
