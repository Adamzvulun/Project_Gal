# פרק 16 – תרשים מסכים (Screen Flow Diagram)

## פתיח

פרק זה מתאר את **היררכיית המסכים** של אפליקציית ה-GUI ואת
המעברים ביניהם, כפי שדורש סעיף 16 בנוהל ההגשה (עמ' 12).

כל המסכים ממומשים ב-Swing (Java 11+) ומופיעים מתוך
**שלושת קבצי המקור** של ה-GUI:

- `java_gui/src/TorrentClientGUI.java` — חלון ראשי + כל ה-
  popups ו-dialogs שנוצרים ישירות ממנו.
- `java_gui/src/AlgorithmStatsDialog.java` — חלון
  הסטטיסטיקות (`JDialog` עם `JTabbedPane`).
- (`ApiService.java` — אינו מסך, אלא שכבת תקשורת; לכן לא
  מופיע בתרשים.)

---

## 16.1 רשימת המסכים במערכת

הטבלה הבאה מסכמת את **תשעת המסכים** המופיעים באפליקציה, מסודרים
לפי סדר ההופעה הטיפוסי בזרימת המשתמש:

| מס' | שם המסך | סוג Swing | קוד מקור |
|---|---|---|---|
| S1 | Main Window | `JFrame` | `TorrentClientGUI.java` |
| S2 | Select Torrent File | `JFileChooser` (OpenDialog) | `TorrentClientGUI.onAddTorrent` |
| S3 | Choose Download Location | `JFileChooser` (DIRECTORIES_ONLY) | `TorrentClientGUI.onAddTorrent` |
| S4 | Confirm Cancel | `JOptionPane.showConfirmDialog` | `TorrentClientGUI.onCancel` |
| S5 | Download History | `JDialog` עם `JTable` | `TorrentClientGUI.onShowHistory` |
| S6 | Confirm Clear History | `JOptionPane.showConfirmDialog` | `TorrentClientGUI.onShowHistory` (lambda) |
| S7 | Algorithm Statistics | `JDialog` עם `JTabbedPane` (2 לשוניות) | `AlgorithmStatsDialog.java` |
| S8 | Download Complete | `JOptionPane.showMessageDialog` (INFO) | `TorrentClientGUI.updateTable` |
| S9 | Error Popup | `JOptionPane.showMessageDialog` (ERROR) | מקומות מרובים |

---

## 16.2 היררכיית המסכים והמעברים

### 16.2.1 תרשים ASCII של זרימת המסכים

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│                    [S1] Main Window                      │
│                    (JFrame, 900×600)                     │
│                                                          │
│   Toolbar: Add | Pause Resume Cancel | History  Stats |  │
│            Piece-Algo, Peer-Algo Combos                  │
│                                                          │
│   Center: JSplitPane                                     │
│      ┌── Top: JTable (downloads) ───────────────────┐    │
│      └── Bottom: JTextArea (event log) ─────────────┘    │
│                                                          │
│   Bottom: Status JLabel ("Ready" / "Starting...")        │
│                                                          │
└──────────────────────────────────────────────────────────┘
        │           │           │           │           │
        │           │           │           │           │
   [Add Torrent]  [Cancel]  [History]   [Stats]   [Auto:
        │           │           │           │      completion
        ▼           ▼           ▼           ▼      detected]
   ┌────────┐   ┌──────┐   ┌────────┐   ┌──────┐      │
   │ [S2]   │   │ [S4] │   │ [S5]   │   │ [S7] │      │
   │ Choose │   │Confir│   │History │   │ Algo │      │
   │.torrent│   │Cancel│   │ Dialog │   │Stats │      ▼
   │file    │   │      │   │        │   │Dialog│   ┌──────┐
   └────────┘   └──────┘   └────────┘   └──────┘   │ [S8] │
        │           │           │                  │ Done │
        ▼           ▼           ▼                  │popup │
   ┌────────┐   (yes →     ┌────────┐              └──────┘
   │ [S3]   │    cancel,    │ [S6]   │
   │ Choose │    no → back) │ Confirm│
   │ folder │               │ Clear  │
   └────────┘               └────────┘
        │                       │
   (server         (yes → clear, no → back to S5)
    request)
        │
   ┌─────────────┐  (on failure, any screen)
   │  [S9] Error │◄──────────────────────────────────
   │   Popup     │
   └─────────────┘
```

### 16.2.2 פירוט המעברים

הטבלה הבאה מתעדת **כל מעבר** בין מסכים, כולל המעבר ההפוך (חזרה):

| ממסך | אל מסך | טריגר | פעולה אחורית |
|---|---|---|---|
| S1 | S2 | לחיצה על "Add Torrent" | Cancel ב-FileChooser → חזרה ל-S1 |
| S2 | S3 | אישור קובץ ב-FileChooser | Cancel ב-FileChooser → חזרה ל-S1 |
| S3 | S1 | אישור תיקייה → קריאה ל-API → חזרה ל-S1 (סטטוס מעודכן) | Cancel → חזרה ל-S1 בלי שינוי |
| S1 | S4 | לחיצה על "Cancel" עם torrent נבחר | "No" → חזרה ל-S1 |
| S4 | S1 | "Yes" → קריאה ל-API → חזרה ל-S1 | — |
| S1 | S5 | לחיצה על "History" | סגירת `JDialog` → חזרה ל-S1 |
| S5 | S6 | לחיצה על "Clear History" | "No" → חזרה ל-S5 |
| S6 | S5 | "Yes" → קריאה ל-API → חזרה ל-S5 (מרוקן) | — |
| S5 | S1 | לחיצה על "Close" | — |
| S1 | S7 | לחיצה על "Statistics" | סגירת `JDialog` → חזרה ל-S1 |
| S7 | S6 | בלשונית "General Statistics" → "Clear History" | "No" → חזרה ל-S7 |
| S7 | S1 | לחיצה על "Close" | — |
| ⚙ | S8 | זיהוי אוטומטי של מעבר state ל-`Completed` ב-`updateTable` | OK → חזרה ל-S1 |
| ⚙ | S9 | כל חריגה ב-`apiService.*` שנתפסת | OK → חזרה למסך הקודם |

הסבר ל-⚙: מעברים המסומנים ב-⚙ הם **אוטומטיים**, לא יזומים
ע"י המשתמש. ה-`ScheduledExecutorService` שרץ כל 500ms זה זה
שמזהה את המעבר ל-`Completed` ומעיר את ה-popup.

---

## 16.3 קיבוצים לוגיים של מסכים

המסכים מתחלקים לארבע משפחות לוגיות:

### משפחה 1 — המסך הראשי
- S1 בלבד. **המסך היחיד שאינו מודאלי**; כל היתר נפתחים מעליו.

### משפחה 2 — File/Folder Choosers
- S2, S3. שניהם `JFileChooser` סטנדרטיים. שניהם מודאליים מול
  S1. אחד אחרי השני בזרימת *Add Torrent*.

### משפחה 3 — Confirmation/Info popups (קלים)
- S4 (Confirm Cancel), S6 (Confirm Clear History), S8
  (Completion Info), S9 (Error). ארבעתם מבוססים על
  `JOptionPane` — חלון קטן עם הודעה וכפתור/ים. הם **לא** שומרים
  מצב; הם משמשים רק לאישור/מידע מיידי.

### משפחה 4 — Tools / Information Dialogs (כבדים)
- S5 (History), S7 (Algorithm Stats). שניהם `JDialog` עם
  `JTable`/`JTabbedPane` ותוכן עשיר. שניהם **non-modal** (פרמטר
  `false` ב-קונסטרקטור), כלומר אפשר להשאיר אותם פתוחים תוך
  כדי שימוש בחלון הראשי.

> **תרשים נדרש (Fig-17)**: Screen Flow Diagram ויזואלי שמציג
> את כל 9 המסכים כצמתים ואת כל המעברים כחיצים מתויגים.
> ראה רשומה ב-`IMAGES.md`.

---

## 16.4 סיכום הפרק

הפרק הציג היררכיית מסכים מלאה: **9 מסכים בשלוש רמות מודאליות**
(S1 לא-מודאלי, S5/S7 דיאלוגים non-modal, היתר מודאליים), עם
13 מעברים מתועדים ביניהם — מהם 11 יזומים ע"י המשתמש ושניים
אוטומטיים (popup completion ו-error popups). הפרק הבא (פרק 17)
מפרט כל מסך לעומק: תפקיד, תיאור מלא של רכיביו, ודרישת צילום
מסך.
