# Fig-04 — תרשים זרימה (Flowchart) של `_download_loop`

**פרק בספר**: 15.1 (האלגוריתם המרכזי).
**סוג**: תרשים זרימה (Flowchart) — מפוצל לשני חלקים בנקודה הגיונית.
**מקור הקוד**: `python_engine/download_manager.py:203-270`.

> התרשים פוצל לשני חלקים כדי להתאים בנוחות לעמוד A4 בודד.
> כל חלק עומד בפני עצמו עם מקרא משלו.

---

## חלק א' — אתחול (Initialization)

קטע זה מציג את ה-setup הראשוני שמתבצע לפני כניסה ללולאה הראשית.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'background':'#FFFFFF', 'primaryColor':'#FFFFFF', 'primaryBorderColor':'#000000', 'primaryTextColor':'#000000', 'lineColor':'#000000', 'edgeLabelBackground':'#FFFFFF', 'tertiaryColor':'#FFFFFF'}}}%%
flowchart TB
    START(["Start<br/><i>_download_loop()</i>"])

    INIT["<b>Init TrackerClient</b><br/>announce_url, info_hash<br/>peer_id, port=6881"]
    ANNOUNCE["<b>Initial announce</b><br/>tracker.announce(event='started')"]
    ADDPEERS["<b>Add peers to _known_peers</b><br/>stats.total_peers_seen ← len(...)"]

    BG["<b>Start background tasks</b><br/>• _choke_loop (every 10s)<br/>• _keep_alive_loop (every 60s)<br/>• start_periodic_announce"]
    KICKCONN["<b>kick off _connect_to_peers</b><br/>(initial, non-blocking)"]

    NEXT(["Continue to Part B<br/><b>Main Loop</b>"])

    EXC_A["<i>except CancelledError<br/>or Exception</i><br/>→ log + state=ERROR"]
    FIN_A["<b>finally:</b> _save_state() → End"]

    START --> INIT --> ANNOUNCE --> ADDPEERS --> BG --> KICKCONN --> NEXT
    INIT     -.-> EXC_A
    ANNOUNCE -.-> EXC_A
    EXC_A    --> FIN_A

    classDef startend fill:#FFFFFF,stroke:#188038,stroke-width:2.5px,color:#000;
    classDef proc     fill:#FFFFFF,stroke:#1A73E8,stroke-width:1.8px,color:#000;
    classDef link     fill:#FFFFFF,stroke:#673AB7,stroke-width:2.5px,color:#000;
    classDef error    fill:#FFFFFF,stroke:#C5221F,stroke-width:1.8px,color:#000;
    class START startend;
    class INIT,ANNOUNCE,ADDPEERS,BG,KICKCONN proc;
    class NEXT link;
    class EXC_A,FIN_A error;

    linkStyle 6,7 stroke:#C5221F,stroke-dasharray:5 5;
```

### מקרא לחלק א'

<table dir="rtl" style="border-collapse:collapse;border:1pt solid #333333;font-family:'David','Times New Roman',serif;font-size:12pt;background:#FFFFFF;">
  <thead>
    <tr style="background-color:#DCE6F1;">
      <th style="border:1pt solid #333333;padding:4px 10px;font-weight:bold;text-align:right;">צורה</th>
      <th style="border:1pt solid #333333;padding:4px 10px;font-weight:bold;text-align:right;">משמעות</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">אובאל ירוק</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">התחלה</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">מלבן כחול</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">פעולה / קריאת מתודה</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">אובאל סגול</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">קישור לחלק הבא</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">מלבן אדום (חץ מקווקו)</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">טיפול בחריגה</td>
    </tr>
  </tbody>
</table>

---

## חלק ב' — לולאה ראשית ויציאה (Main Loop & Exit)

קטע זה מציג את הלולאה המרכזית, ההתפצלות בכל איטרציה, ושלוש דרכי היציאה האפשריות.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'background':'#FFFFFF', 'primaryColor':'#FFFFFF', 'primaryBorderColor':'#000000', 'primaryTextColor':'#000000', 'lineColor':'#000000', 'edgeLabelBackground':'#FFFFFF', 'tertiaryColor':'#FFFFFF'}}}%%
flowchart TB
    PREV(["From Part A<br/><b>Initialization complete</b>"])

    LOOP{"<b>Main loop</b><br/>while not piece_manager.is_complete<br/>and state == RUNNING"}

    RESET["reset_stale_pieces(30s)"]
    REQ["_request_pieces()"]
    SLEEP["await asyncio.sleep(0.1)"]

    CLEANCHK{"now − last_cleanup<br/>> 15s ?"}
    CLEAN["_cleanup_dead_peers()<br/>+ await _connect_to_peers()<br/>+ last_cleanup ← now"]

    UPDATE["_update_speed()<br/>tracker.update_stats(<br/>uploaded, downloaded, left)"]

    COMPCHK{"piece_manager<br/>.is_complete ?"}
    COMPLETE["await _complete_download()"]

    EXC["<i>except CancelledError<br/>or Exception</i><br/>→ log + state=ERROR"]
    FIN["<b>finally:</b> _save_state()"]
    END(["End"])

    PREV --> LOOP
    LOOP -- "True"  --> RESET --> REQ --> SLEEP --> CLEANCHK
    CLEANCHK -- "Yes" --> CLEAN --> UPDATE
    CLEANCHK -- "No"  --> UPDATE
    UPDATE --> LOOP
    LOOP -- "False" --> COMPCHK
    COMPCHK -- "Yes" --> COMPLETE --> FIN
    COMPCHK -- "No"  --> FIN
    LOOP -.-> EXC
    EXC  --> FIN
    FIN  --> END

    classDef startend fill:#FFFFFF,stroke:#188038,stroke-width:2.5px,color:#000;
    classDef proc     fill:#FFFFFF,stroke:#1A73E8,stroke-width:1.8px,color:#000;
    classDef decision fill:#FFFFFF,stroke:#E37400,stroke-width:2px,color:#000;
    classDef link     fill:#FFFFFF,stroke:#673AB7,stroke-width:2.5px,color:#000;
    classDef error    fill:#FFFFFF,stroke:#C5221F,stroke-width:1.8px,color:#000;
    class END startend;
    class PREV link;
    class RESET,REQ,SLEEP,CLEAN,UPDATE,COMPLETE,FIN proc;
    class LOOP,CLEANCHK,COMPCHK decision;
    class EXC error;

    linkStyle 11,12 stroke:#C5221F,stroke-dasharray:5 5;
```

### מקרא לחלק ב'

<table dir="rtl" style="border-collapse:collapse;border:1pt solid #333333;font-family:'David','Times New Roman',serif;font-size:12pt;background:#FFFFFF;">
  <thead>
    <tr style="background-color:#DCE6F1;">
      <th style="border:1pt solid #333333;padding:4px 10px;font-weight:bold;text-align:right;">צורה</th>
      <th style="border:1pt solid #333333;padding:4px 10px;font-weight:bold;text-align:right;">משמעות</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">אובאל סגול</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">קישור מהחלק הקודם</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">אובאל ירוק</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">סיום</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">מלבן כחול</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">פעולה / קריאת מתודה</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">מעוין כתום</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">החלטה / תנאי</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">מלבן אדום (חץ מקווקו)</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">טיפול בחריגה</td>
    </tr>
  </tbody>
</table>

---

## טבלת אימות מול הקוד

<table dir="rtl" style="border-collapse:collapse;border:1pt solid #333333;font-family:'David','Times New Roman',serif;font-size:12pt;background:#FFFFFF;">
  <thead>
    <tr style="background-color:#DCE6F1;">
      <th style="border:1pt solid #333333;padding:4px 10px;font-weight:bold;text-align:right;">שלב</th>
      <th style="border:1pt solid #333333;padding:4px 10px;font-weight:bold;text-align:right;">פעולה</th>
      <th style="border:1pt solid #333333;padding:4px 10px;font-weight:bold;text-align:right;">מקור (line)</th>
      <th style="border:1pt solid #333333;padding:4px 10px;font-weight:bold;text-align:right;">חלק</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">1</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">אתחול <code>TrackerClient</code> עם <code>port=6881</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:207-212</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">א'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">2</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>announce(event='started')</code> ראשוני</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:217-218</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">א'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">3</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">הוספת peers ל-<code>_known_peers</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:219-221</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">א'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">4</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">יצירת tasks ברקע: <code>_choke_loop</code>, <code>_keep_alive_loop</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:225-226</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">א'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">5</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>await start_periodic_announce(callback)</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:229-231</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">א'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">6</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>_connect_to_peers</code> ראשוני (non-blocking)</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:234</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">א'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">7</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">לולאה ראשית</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:238</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">ב'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">7a</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>reset_stale_pieces(PIECE_REQUEST_TIMEOUT=30)</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:240</code>, <code>:33</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">ב'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">7b</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>_request_pieces()</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:242</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">ב'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">7c</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>await sleep(0.1)</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:243</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">ב'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">7d</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">כל 15 שניות: cleanup + reconnect</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:247-250</code>, <code>:34</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">ב'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">7e</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>_update_speed</code> + <code>tracker.update_stats</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:253-258</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">ב'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">8</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">אם <code>is_complete</code> → <code>_complete_download</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:260-261</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">ב'</td>
    </tr>
    <tr>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">9</td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>finally: _save_state()</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;"><code>download_manager.py:269-270</code></td>
      <td style="border:0.5pt solid #999999;padding:4px 10px;text-align:right;">ב'</td>
    </tr>
  </tbody>
</table>

---

## הערות חשובות

- **non-blocking**: ה-`_connect_to_peers` מופעל כ-`asyncio.create_task` — הלולאה לא מחכה לסיום של 50 ניסיונות חיבור.
- **חוסמים** (SHA-1, כתיבה לדיסק) רצים ב-`ThreadPoolExecutor`, לא בלולאה הזו.
- **שלוש דרכי יציאה** מהלולאה (כולן מובילות ל-`_save_state`):
  1. `is_complete = True` → `_complete_download` → `_save_state`.
  2. `state != RUNNING` (pause/cancel) → ישירות ל-`_save_state`.
  3. חריגה (`CancelledError` / `Exception`) → לוג + state=ERROR → `_save_state`.

---

## איך להעתיק את התרשימים ל-Google Docs / Word

לכל אחד מ-2 החלקים בנפרד:

1. גש ל-**https://mermaid.live**
2. מחק את הקוד שמופיע משמאל.
3. העתק את הקוד של החלק הרצוי (מתחת ל-` ```mermaid ` עד לפני ה-` ``` ` הסוגר).
4. הדבק משמאל. התרשים מתעדכן מימין על רקע לבן.
5. **Actions → SVG** (מומלץ — וקטורי, לא מתפקסל בכווץ) או **PNG**.
6. ב-Google Docs: `Insert → Image → Upload from computer`.
7. הדבק כותרת מעל כל תמונה: *"Fig-04a — אתחול"* / *"Fig-04b — לולאה ראשית"*.

> **טיפ**: אם בוחרים בכל זאת בתרשים אחד שלם, אפשר להפוך את העמוד ל-Landscape:
> `Insert → Break → Section break (next page)` → `File → Page setup → Apply to: This section → Landscape`.

## איך להעתיק את הטבלאות ל-Google Docs / Word

הטבלאות בקובץ זה מעוצבות ב-HTML inline-styles **שמותאמים בדיוק לסגנון
הספר** (גבול חיצוני `#333333`, גבולות פנימיים `#999999`, רקע שורת כותרת
`#DCE6F1`, פונט David 12pt). העיצוב נשמר אוטומטית בהעתקה:

1. פתח את הקובץ ב-GitHub / VS Code Preview (בעיניים בהירות).
2. סמן את הטבלה בעכבר (גרור מהפינה השמאלית-עליונה לפינה הימנית-תחתונה).
3. `Ctrl+C` (Mac: `Cmd+C`).
4. ב-Google Docs: `Ctrl+V`. הטבלה נכנסת כטבלה אמיתית עם העיצוב הנכון.
