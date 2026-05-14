# 23. מדריך למשתמש

## דרישות מינימליות

- מערכת הפעלה: Windows 10/11, macOS 10.15+, או Linux
  (Ubuntu/Debian/Fedora/Arch).
- חיבור אינטרנט יציב (1 Mbps מינימום).
- 100 MB דיסק לקוד + מקום ל-payload.

לא צריך להתקין מראש Python או Java — סקריפט ההפעלה
יעשה זאת אוטומטית במידת הצורך.

## התקנה והפעלה

לאחר חילוץ תיקיית הפרויקט למחשב:

**Linux / macOS**:

```bash
cd Project_Gal
chmod +x start.sh
./start.sh
```

**Windows**: הקלקה כפולה על `start.bat` שבתיקיית הפרויקט.

הסקריפט מבצע: בדיקה והתקנה אוטומטית של Python ו-JDK
(דרך apt / dnf / pacman / brew / winget בהתאם ל-OS),
התקנת `flask` ו-`aiohttp`, הורדה אוטומטית של `org.json`,
קומפילציה של ה-Java, הפעלת ה-API server ברקע, והפעלת
ה-GUI בחזית.

לסגירה: סגירת חלון ה-GUI (X בפינה). הסקריפט מזהה זאת
דרך `WindowAdapter` וקורא ל-`shutdown()` שמוריד את שני
התהליכים.

## הוספת torrent ראשון

1. השג קובץ `.torrent` חוקי (לדוגמה, ISO של הפצת Linux
   פתוחה — Ubuntu, Debian).
2. ב-GUI: לחץ "Add Torrent" בשורת הכלים העליונה.
3. בחר את הקובץ `.torrent` ב-`JFileChooser` הראשון.
4. בחר תיקיית יעד ב-`JFileChooser` השני.
5. אופציונלית: לפני שלב 2, שנה את ה-Combos של Piece /
   Peer Algorithm. ברירת המחדל (`Rarest First` +
   `Tit-for-Tat`) היא המומלצת.
6. שורה חדשה תופיע בטבלה במצב `Running`. ה-ProgressBar
   יתחיל לזוז.

ה-Event Log התחתון יציג את התקדמות החיבור ל-tracker
ולקבלת peers, ואת אימות ה-pieces ככל שהם מתקבלים.

## פעולות שוטפות

**Pause / Resume**: בחר שורה בטבלה (Pause נדלק רק כשמצב
"Running"); לחץ. ה-state מתעדכן תוך 500ms.

**Cancel**: בחר שורה → Cancel → אישור YES בחלון. ההורדה
מסומנת `Cancelled` ו-`event=stopped` נשלח ל-tracker.

**History**: לחיצה על "History" פותחת חלון עם רשימת כל
ההורדות שהסתיימו. לחיצה על "Clear History" מנקה את
הכל (אחרי אישור).

**Statistics**: פותח חלון עם שתי לשוניות — התפלגות בחירות
rarest-first ב-bar chart, וסטטיסטיקות מצרפיות (סך הורדות,
מהירויות ממוצעות וכו').

## פתרון בעיות

**"Cannot reach BitTorrent engine at localhost:5000"** —
ה-Python server לא רץ. נסה:

```bash
curl http://localhost:5000/health         # בדיקה
python -m python_engine.api_server        # הפעלה ידנית
```

**הורדה תקועה ב-0%** — אפשרויות: ה-tracker לא נגיש
(`Failed to connect to tracker`), אין peers ב-swarm (
ה-tracker החזיר 0), או כל ה-peers מאחורי NAT (המערכת
לא מקבלת חיבורים נכנסים).

**"Hash failed" חוזרת על עצמה** — peer זדוני או buggy.
אחרי 3 כשלים הוא נחסם אוטומטית (`Banned peer`). המערכת
ממשיכה עם peers אחרים.

**Java compile error** — ודא ש-JDK 11+ מותקן (`java
-version`, `javac -version`). ב-Windows ייתכן שצריך
להוסיף את `JAVA_HOME` ל-PATH ידנית.
