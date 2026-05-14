# פרק 23 – מדריך למשתמש

## פתיח

פרק זה הוא **המדריך הרשמי למשתמש** של המערכת — מהתקנה ראשונית
ועד שימוש שוטף. הוא נכתב בצורה תכליתית ועצמאית, כך שמשתמש
שאינו מכיר את הפרויקט יוכל להפעיל אותו ולהתחיל להוריד
torrent ראשון תוך 5 דקות.

---

## 23.1 דרישות מינימליות

לפני התקנה, המשתמש צריך:

- **מערכת הפעלה**: Windows 10/11, macOS 10.15+, או Linux
  (Ubuntu/Debian/Fedora/Arch).
- **חיבור אינטרנט יציב** עם רוחב פס סביר (10 Mbps ומעלה
  מומלץ; 1 Mbps מינימום).
- **שטח דיסק פנוי**: 100 MB לפרויקט + מקום ל-payload
  שיורידו (תלוי בקבצים).
- **הרשאות התקנה** של חבילות (sudo / Administrator) —
  לפעם הראשונה בלבד.

לא נדרש להתקין מראש Python או Java — סקריפט ההפעלה
יעשה זאת אוטומטית במידת הצורך.

---

## 23.2 התקנה והפעלה ראשונה

### 23.2.1 הורדת קוד המקור

```bash
git clone <repo-url> Project_Gal
cd Project_Gal
```

לחלופין, הורדת ZIP מהריפו ופריסה לתיקייה.

### 23.2.2 הפעלה — Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

הסקריפט יבצע:
1. בדיקה והתקנה (אם חסר) של Python 3 + pip.
2. בדיקה והתקנה (אם חסר) של JDK.
3. התקנת חבילות Python: `flask`, `aiohttp`.
4. הורדה אוטומטית של ספריית `org.json` (`json.jar`).
5. קומפילציה של 3 קבצי ה-Java.
6. הפעלת ה-Python API server (ברקע, על
   `http://localhost:5000`).
7. הפעלת ה-Java GUI (חלון ראשי).

### 23.2.3 הפעלה — Windows

הקלקה כפולה על `start.bat`, או:

```cmd
start.bat
```

תהליך זהה: בדיקה והתקנה של Python ו-JDK (דרך winget),
התקנת תלויות, קומפילציה, והפעלה.

**הערה**: בפעם הראשונה, אם winget מתקין Python או JDK,
ייתכן שתידרש סגירת חלון Command Prompt ופתיחת חדש כדי שה-PATH
יתעדכן. הסקריפט מציג הוראה ברורה במקרה זה.

### 23.2.4 סגירה

סגירת חלון ה-GUI (X בפינה הימנית) → הסקריפט מזהה זאת
(WindowAdapter) → קורא ל-`shutdown()` → הורג את תהליך
Python ה-`api_server`. כל הנתונים נשמרים אוטומטית.

---

## 23.3 הוספת ההורדה הראשונה

### 23.3.1 השגת קובץ `.torrent`

לפני שמשתמשים במערכת, יש צורך בקובץ `.torrent` חוקי. ניתן
להוריד מ-source חוקי לבדיקה, למשל:

- ISO של הפצת Linux פתוחה (Ubuntu, Debian, Arch).
- ארכיב פתוח מ-Internet Archive.

> **הערה משפטית**: השתמשו רק ב-torrents שאתם מורשים להוריד.
> המערכת לא בודקת לגיטימיות תוכן.

### 23.3.2 שלבי ההוספה

1. **לחיצה על "Add Torrent"** ב-toolbar.
2. **בחירת קובץ `.torrent`** ב-`JFileChooser` שנפתח
   (מסונן ל-`*.torrent`).
3. **בחירת תיקיית יעד** ב-`JFileChooser` השני (תיקיות בלבד).
4. אופציונלית: לפני הצעד 1, בחירת אלגוריתמים ב-Combos
   של ה-toolbar (ברירת המחדל `Rarest First` +
   `Tit-for-Tat` היא המומלצת).
5. **המתנה** — שורה חדשה תופיע בטבלה הראשית במצב `Running`,
   ה-`JProgressBar` יתחיל לזוז.

### 23.3.3 מה לצפות לראות

בלוג ה-Event Log (חצי תחתון):

```
[14:23:01] Application started. Connecting to BitTorrent engine...
[14:23:02] Connected to BitTorrent engine.
[14:25:14] Download started: ubuntu-22.04.iso → /home/.../Downloads (ID: a1b2c3d4)
[14:25:15] [engine] Starting download: ubuntu-22.04.iso
[14:25:15] [engine] Size: 4294967296 bytes, Pieces: 16384, Tracker: ...
[14:25:16] [engine] Contacting tracker: ...
[14:25:17] [engine] Tracker responded: 47 peers found
[14:25:18] [engine] Connected to peer 91.189.91.42:6881
[14:25:19] [engine] Piece 1 verified OK (1/16384)
[14:25:20] [engine] Piece 2 verified OK (2/16384)
...
```

---

## 23.4 פעולות שוטפות

### 23.4.1 השהיית הורדה (Pause)

1. לחיצה על השורה בטבלה (לבחור את ההורדה).
2. כפתורי Pause/Resume/Cancel נדלקים בהתאם.
3. לחיצה על **Pause** → ה-state ישתנה ל-`Paused` תוך 500ms.
   מהירות → 0. חיבורי peers ייסגרו.

### 23.4.2 חידוש הורדה (Resume)

1. בחירת שורת הורדה במצב `Paused`.
2. לחיצה על **Resume** → ה-`_download_loop` יופעל מחדש;
   המערכת תעשה announce חדש ל-tracker, תקבל peers, ותמשיך
   מהמצב שנשמר ב-`data/state/<id>.json`.

### 23.4.3 ביטול הורדה (Cancel)

1. בחירת שורה.
2. לחיצה על **Cancel** → dialog אישור מופיע.
3. **Yes** → ה-state ישתנה ל-`Cancelled`; ה-tracker יקבל
   `event=stopped`; הקובץ החלקי שכבר הורד **לא** נמחק
   אוטומטית (המשתמש יכול למחוק ידנית).

### 23.4.4 צפייה בהיסטוריה

לחיצה על **History** ב-toolbar → פתיחת `JDialog` עם
טבלה של כל ההורדות שהסתיימו (גם מהפעלות קודמות, מה-SQLite).

לחיצה על **Clear History** מנקה את כל ההיסטוריה (אחרי
אישור). זוהי פעולה לא הפיכה.

### 23.4.5 צפייה בסטטיסטיקות אלגוריתמים

לחיצה על **Statistics** ב-toolbar → פתיחת `JDialog` עם
שתי לשוניות:

- **Tab 1: Piece Selection (Rarest-First)** — bar chart
  של בחירות rarest-first per-piece עבור torrent שייבחר
  ב-ComboBox.
- **Tab 2: General Statistics** — סטטיסטיקות מצרפיות (סך
  הורדות, סך נתונים, מהירויות, peers, choke cycles).

לחיצה על **Refresh** טוענת נתונים מחדש מ-SQLite.

---

## 23.5 פתרון בעיות

### 23.5.1 "Cannot reach BitTorrent engine at localhost:5000"

הודעה זו מופיעה בלוג אם ה-Python API server לא רץ.

**פתרון**:

```bash
# בדיקה אם השרת רץ:
curl http://localhost:5000/health

# אם לא — הפעלה ידנית:
python -m python_engine.api_server
```

אם הפקודה הידנית מצליחה — סביר ש-`start.sh` נכשל. בדקו
את הלוג של ה-`start.sh` (mainly: שגיאות `pip install`,
`javac`).

### 23.5.2 הורדה תקועה ב-0%

מספר סיבות אפשריות:

- **Tracker לא נגיש**: בלוג יופיע
  `Failed to connect to tracker: ...`. נסו torrent אחר.
- **NAT/Firewall**: המערכת לא מקבלת חיבורים נכנסים — ראה
  פרק 11.4.4. במצב הזה, אם כל ה-peers ב-swarm גם הם
  מאחורי NAT, התקשורת בלתי אפשרית.
- **0 peers הוחזרו ע"י ה-tracker**: ה-swarm ריק — נסו
  torrent פופולרי יותר.

### 23.5.3 "Hash failed" repeated

אם יש peer זדוני שמשובש בשמירה:

- בלוג: `Piece N HASH FAILED from <ip>:<port>`.
- אחרי 3 כשלים: `Banned peer <ip>:<port>` (פרק 12.1.5).
- המערכת תמשיך עם peers אחרים אוטומטית.

### 23.5.4 קומפילציית Java נכשלת

```
ERROR: javac: command not found
```

**פתרון**:
- ודאו ש-JDK 11+ מותקן: `java -version` + `javac -version`.
- ב-Windows, ייתכן שצריך להוסיף ידנית את `JAVA_HOME` ל-PATH.

### 23.5.5 שחזור הורדה לאחר crash

אם המערכת קרסה באמצע הורדה:

1. הפעל את `start.sh` מחדש.
2. הקובץ `data/state/<id>.json` נשמר בעת שינוי
   משמעותי (piece שהושלם, pause, וכו').
3. **גרסה נוכחית**: שחזור אוטומטי **לא ממומש** —
   המשתמש יראה את ההורדה ב-History אבל יידרש להתחיל
   אותה מחדש. שיפור מתועד בפרק 26.

---

## 23.6 קיצורי דרך וטיפים

- **Refresh ידני**: ה-GUI מבצע polling אוטומטי כל 500ms
  — אין צורך ב-refresh ידני.
- **חלונות מרובים**: ה-History וה-Statistics dialogs הם
  **non-modal** — אפשר להשאיר אותם פתוחים תוך כדי הוספת
  הורדות חדשות.
- **בחירת אלגוריתם פר-הורדה**: ה-Combo ב-toolbar קובע את
  האלגוריתם **של ההורדה הבאה** (ה-`POST /torrents`). הורדות
  קיימות **לא משתנות**. אפשר להריץ במקביל torrent אחד עם
  rarest-first ואחר עם random — כל אחד עם הסטטיסטיקות שלו.
- **ניטור ביצועים**: לאחר מספר הורדות, פתח Statistics →
  General Statistics לראות סך הנתונים שהורדת, מהירות
  ממוצעת, וכו'.

---

## 23.7 הסרת התוכנה

המערכת **לא דורשת הסרה רשמית** — כל הקוד ב-תיקיה אחת
(`Project_Gal/`). למחיקה:

```bash
# 1. סגור את ה-GUI.
# 2. מחק את התיקייה:
rm -rf Project_Gal/
```

ההתקנות של Python ו-JDK (שבוצעו ע"י `start.sh`) **לא יוסרו**
— הן נשארות במערכת לשימוש כלשהו אחר.

---

## 23.8 סיכום

המדריך תיאר את **שלושת המסלולים** למשתמש קצה:

1. **התקנה ראשונה** (5–10 דקות) — clone + `./start.sh` או
   `start.bat`.
2. **שימוש שוטף** (פעולות יומיומיות) — Add, Pause/Resume/
   Cancel, History, Statistics.
3. **פתרון בעיות** — 5 תרחישים נפוצים עם פתרונות.

הפרק הבא (פרק 24) הוא **בדיקות והערכה** — מבחנים שבוצעו
על המערכת, מתודולוגיית הניסויים, ותוצאות.
