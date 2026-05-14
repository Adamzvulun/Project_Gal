# 18. תיאור אלמנטי תצוגה

## כפתורים

| כפתור | מסך | תפקיד | מצב Enabled |
|---|---|---|---|
| Add Torrent | S1 toolbar | פותח את S2 → S3 לבחירת קובץ ויעד | תמיד פעיל |
| Pause | S1 toolbar | משהה הורדה | רק כשה-state = "Running" |
| Resume | S1 toolbar | מחדש הורדה | רק כשה-state = "Paused" |
| Cancel | S1 toolbar | פותח את S4 לאישור | רק כשה-state ∈ {Running, Paused} |
| History | S1 toolbar | פותח את S5 | תמיד פעיל |
| Statistics | S1 toolbar | פותח את S7 | תמיד פעיל |
| Clear History | S5, S7 Tab 2 | פותח את S6 | תמיד פעיל |
| Close | S5, S7 | סוגר את ה-Dialog | תמיד פעיל |
| Refresh | S7 | טוען מחדש נתונים | תמיד פעיל |

המנגנון להפעלה/השבתה דינמית של Pause/Resume/Cancel
מתבצע ע"י `ListSelectionListener` על
`downloadTable.getSelectionModel()` שקורא ל-
`updateButtonStates()` בכל שינוי בחירה.

## רכיבי בחירה (JComboBox)

- **Piece Algorithm** (S1 toolbar): "Rarest First" /
  "Random". הערך שמוצג שונה מערך ה-API ("rarest_first" /
  "random") — ההמרה ב-`addTorrent` היא
  `.toLowerCase().replace(" ", "_").replace("-", "_")`.
- **Peer Algorithm** (S1 toolbar): "Tit-for-Tat" / "Round
  Robin".
- **Torrent Picker** (S7 Tab 1): רשימה דינמית של torrents
  שיש להם נתוני algorithm_stats.

## טבלת ההורדות הראשית (S1)

`JTable` עם 8 עמודות:

| # | שם | רוחב | סוג | פורמט |
|---|---|---|---|---|
| 0 | Name | 200 | String | טקסט |
| 1 | Size | 80 | String | `formatSize` (KB/MB/GB) |
| 2 | Progress | 120 | Double | `ProgressBarRenderer` (כחול→ירוק) |
| 3 | Speed | 100 | String | `formatSpeed` |
| 4 | Peers | 60 | String | מספר |
| 5 | State | 80 | String | enum value |
| 6 | Location | 200 | String | נתיב |
| 7 | ID | 70 | String | 8 תווים hex |

הטבלה היא `isCellEditable=false` (read-only),
`SINGLE_SELECTION`, ועם `reorderingAllowed=false`. בכל
ריענון השורה הנבחרת נשמרת ומשוחזרת אחרי טעינת הנתונים
החדשים. `ProgressBarRenderer` מצייר `JProgressBar` עם
`setStringPainted(true)` שמציג את האחוז בתוך הבר.

## טבלת ההיסטוריה (S5)

9 עמודות: Name, Size, Status, Avg Speed, Peak Speed,
Time, Piece Algo, Peer Algo, Choke Cycles. הנתונים
מגיעים מ-JOIN של `torrents` ו-`performance_stats` ב-
SQLite. פורמטינג: `formatSize`, `formatSpeed`,
`formatDuration` (`HH:MM:SS`), ו-`friendlyAlgo`
(`rarest_first` → "Rarest First"). הטבלה משתמשת ב-
`AUTO_RESIZE_ALL_COLUMNS`.

## רכיבי טקסט

- **`JTextArea` ב-Event Log (S1)**: `setEditable(false)`,
  פונט monospace 12, גלילה אוטומטית לתחתית עם
  `setCaretPosition(getLength())`. כל שורה מתחילה
  ב-`[HH:mm:ss]`.
- **`JLabel` ב-Status Bar (S1)**: עם `LoweredBevelBorder`.
  תוכן דינמי: "Ready" / "Connected to engine" /
  "Engine not available" / "Starting download: …" /
  "N downloads (M active)".
- **`summaryLabel` ב-S7 Tab 1**: שורת סיכום מתחת ל-bar
  chart.
- **9 שדות `statValueLabels[]` ב-S7 Tab 2**: כל אחד
  בפורמט `<NAME>:  <VALUE>`.

## גרפיקה ב-Java2D — BarChartPanel

`BarChartPanel extends JPanel` ב-`AlgorithmStatsDialog`.
`paintComponent` מקבל `Graphics2D` ומפעיל
`KEY_ANTIALIASING`. הרוחב של כל עמודה מחושב מ-
`getWidth() / num_bars` כך שכל הנתונים נכנסים בלי גלילה.

## רכיבי המבנה

`JToolBar` עם `setFloatable(false)` ב-S1; `JSplitPane`
אנכי עם `resizeWeight=0.7` בין הטבלה ללוג; `JScrollPane`
לטבלאות וללוג; `JTabbedPane` ב-S7; `JPanel` עם
`FlowLayout.RIGHT` לכפתורים בתחתית של S5/S7;
`EmptyBorder` למרווחים פנימיים.
