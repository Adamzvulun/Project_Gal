# 16. תרשים מסכים (Screen Flow Diagram)

## רשימת המסכים

המערכת כוללת תשעה מסכים, כולם ב-Swing:

| מס' | שם | סוג | קוד |
|---|---|---|---|
| S1 | Main Window | `JFrame` | `TorrentClientGUI.java` |
| S2 | Select Torrent File | `JFileChooser` | `onAddTorrent` |
| S3 | Choose Download Location | `JFileChooser` (DIRS) | `onAddTorrent` |
| S4 | Confirm Cancel | `JOptionPane` (YES/NO) | `onCancel` |
| S5 | Download History | `JDialog` + `JTable` | `onShowHistory` |
| S6 | Confirm Clear History | `JOptionPane` (YES/NO) | `onShowHistory` |
| S7 | Algorithm Statistics | `JDialog` + `JTabbedPane` | `AlgorithmStatsDialog.java` |
| S8 | Download Complete | `JOptionPane` (INFO) | `updateTable` |
| S9 | Error Popup | `JOptionPane` (ERROR) | מקומות מרובים |

## היררכיית המסכים והמעברים

```
                    [S1] Main Window
                    (always open, JFrame)
                  ┌────┬────┬────┬────┐
                  │    │    │    │    │
              Add  Cancel History Stats   ⚙ auto
                 │    │    │    │    │
                 ▼    ▼    ▼    ▼    ▼
              ┌────┐┌────┐┌────┐┌────┐┌────┐
              │ S2 ││ S4 ││ S5 ││ S7 ││ S8 │
              │File││Conf││Hist││Algo││Done│
              └─┬──┘└────┘└─┬──┘└─┬──┘└────┘
                │           │     │
                ▼           ▼     ▼
              ┌────┐      ┌────┐┌────┐
              │ S3 │      │ S6 ││ S6 │
              │Dir │      │Clr ││Clr │
              └────┘      └────┘└────┘
```

המסך הראשי (S1) הוא היחיד שאינו מודאלי. S5 ו-S7 הם
`JDialog(modal=false)` — ניתן להשאיר אותם פתוחים תוך
שימוש ב-S1. שאר ה-popups מודאליים. S8 (Completion) ו-S9
(Error) מופעלים אוטומטית — S8 ב-`updateTable` כשמתגלה
מעבר state ל-`Completed`, S9 בכשל של פעולה יוזמת
משתמש (בעיקר `startDownload`).

זרימה אופיינית של "להוריד torrent": S1 → S2 → S3 →
חזרה ל-S1 עם שורה חדשה בטבלה. זרימה של "לבטל הורדה":
S1 → S4 → אישור → חזרה ל-S1. זרימה של "לראות
היסטוריה": S1 → S5 (אופציונלית: S5 → S6 → S5 אם
המשתמש מנקה).
