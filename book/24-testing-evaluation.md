# פרק 24 – בדיקות והערכה

## פתיח

פרק זה מציג את **שתי שכבות הבדיקה** של המערכת:

1. **בדיקות יחידה אוטומטיות (Unit Tests)** — ממומשות
   ב-`pytest` ומכסות את כל המודולים הקריטיים של ה-Engine.
2. **הערכה מערכתית** — הערכה אמפירית של הביצועים מול
   מדדי ההצלחה שהוגדרו בפרק 5.

הפרק עוקב אחר סעיף 24 בנוהל ההגשה (עמ' 13).

---

## 24.1 בדיקות יחידה (Unit Tests)

### 24.1.1 סקירה כללית

בתיקייה `python_engine/tests/` מצויות **160 פונקציות בדיקה**
ב-8 קבצים, סך הכל **1,421 שורות קוד בדיקה** — יחס כיסוי
של ~38% מקוד הפרודקשן (1,421 על 3,718).

| קובץ בדיקה | מודול נבדק | מספר בדיקות | תכולה עיקרית |
|---|---|---|---|
| `test_bencode.py` | `bencode.py` | 44 | encode/decode של כל הטיפוסים; round-trip; קלטים תקולים |
| `test_torrent_metadata.py` | `torrent_metadata.py` | 14 | parsing קובצי `.torrent`; חישוב info_hash; שדות מרכזיים |
| `test_tracker_client.py` | `tracker_client.py` | 14 | parsing תגובות tracker (compact/regular); URL building |
| `test_peer_connection.py` | `peer_connection.py` | 14 | handshake encoding; message parsing; state machine |
| `test_piece_manager.py` | `piece_manager.py` | 27 | algorithms rarest-first/random; submit_block; verify_hash |
| `test_download_manager.py` | `download_manager.py` | 8 | integration tests של תיאום מודולים |
| `test_security.py` | `security.py` | 26 | trust_score; should_ban; report_*; validation |
| `test_api_server.py` | `api_server.py` | 13 | endpoints; status codes; פורמט תגובות |
| **סך הכל** | — | **160** | — |

### 24.1.2 הרצת ה-Tests

```bash
# מתוך תיקיית הפרויקט
cd python_engine
pip install pytest pytest-asyncio
pytest tests/ -v
```

תוצאה צפויה: **160 passing**.

### 24.1.3 דוגמת קוד בדיקה — `test_piece_manager.py`

```python
def test_rarest_first_chooses_minimum_frequency():
    """rarest-first should choose the piece with lowest peer count."""
    hashes = [b'\x00' * 20] * 4
    pm = PieceManager(num_pieces=4, piece_length=16384,
                      total_size=65536, piece_hashes=hashes)
    # Peer A has pieces 0, 1
    pm.update_peer_pieces("A:6881", [True, True, False, False])
    # Peer B has pieces 0, 1, 2
    pm.update_peer_pieces("B:6881", [True, True, True, False])
    # Peer C has pieces 0, 1, 2, 3
    pm.update_peer_pieces("C:6881", [True, True, True, True])
    # Frequencies: 0→3, 1→3, 2→2, 3→1 (rarest)
    selected = pm.select_piece_rarest_first([True, True, True, True])
    assert selected == 3  # The unique rarest piece
```

זוהי בדיקה דטרמיניסטית של האלגוריתם המרכזי בפרויקט. בדיקות
דומות מוודאות:
- בחירה אקראית מתוך multiple-rarest.
- החזרת `None` כש-peer לא מחזיק כלום שצריך.
- אי-בחירה של pieces ב-`IN_PROGRESS`/`COMPLETED`.

### 24.1.4 קטגוריות בדיקה

הבדיקות מאורגנות בשלוש קטגוריות:

- **Pure unit tests** (≈70%): פונקציה אחת + assertions
  על ערכי החזרה. לדוגמה, `test_bencode_encode_int`.
- **State-machine tests** (≈20%): בדיקת state transitions
  אחרי סדרת פעולות. לדוגמה,
  `test_peer_choking_state_after_choke_message`.
- **Integration tests** (≈10%): מספר מודולים יחד.
  לדוגמה, ב-`test_download_manager.py` שעובד מול
  `TorrentMetadata` + `PieceManager` + `SecurityManager`
  מדומים.

### 24.1.5 בדיקות שלא בוצעו (Gaps)

| תחום | סיבה |
|---|---|
| **GUI Java** | אין tests ל-Swing components — מורכב מבחינת `JFrame` headless; שיפור עתידי |
| **End-to-end network** | דורש peer חי או mock TCP server — שיפור עתידי |
| **Performance benchmarks** | מוצגים בסעיף 24.2 (אמפירי) ולא כ-pytest |

---

## 24.2 הערכה אמפירית מערכתית

הסעיף מציג את **מתודולוגיית הניסויים** שיש לבצע כדי להעריך
את המערכת מול ה-KPIs שנקבעו בפרק 5.

### 24.2.1 פרוטוקול הניסוי

לפי `book/TODO.md` ופרק 5.5.2, פרוטוקול הניסוי הוא:

- **קובץ הבדיקה**: torrent יציב בגודל ~1 GB (לדוגמה: ISO
  של Debian או Ubuntu, שלהם trackers יציבים ו-swarms
  פעילים).
- **תצורות שנמדדות**:
  - תצורה A: `rarest_first` + `tit_for_tat` (המומלצת).
  - תצורה B: `random` + `round_robin` (baseline).
- **5 הרצות לכל תצורה** → 10 הרצות סה"כ.
- **כל הרצה נמדדת בעצמאות** (קובץ נקי, ללא קאש).
- **שמירת CSV** של `/algorithm-stats/<id>` ושל
  `/stats-summary` לכל הרצה.

### 24.2.2 מדדים שנמדדים

| KPI | מה נמדד | מקור הנתונים |
|---|---|---|
| **K1: זמן הורדה** | שניות מ-`event=started` עד `event=completed` | `total_time_seconds` |
| **K2: מהירות ממוצעת** | bytes/sec מצרפי | `avg_speed` |
| **K3: מהירות שיא** | מקסימום bytes/sec בריקוע 30 שניות | `peak_speed` |
| **K4: peers ממוצעים** | מספר חיבורים פעילים | `avg_peers` |
| **K5: choke cycles** | מספר ריצות של choke loop | `choke_cycles` |
| **K6: בחירות rarest** | סכום `selected_as_rarest` | `total_rarest_selections` |
| **K7: אחוז verification נכשל** | hash_failures / total_pieces | חישוב מ-`events` |

### 24.2.3 דרישות ההצלחה לכל KPI

מקור: פרק 5 (מדדי הצלחה).

| KPI | ערך מינימלי לעבירה |
|---|---|
| K1 (זמן) | תצורה A מהירה פי 1.5 לפחות מ-B עבור swarm זהה |
| K2 (מהירות ממוצעת) | תצורה A ≥ 80% מקצב התעבורה האפשרי |
| K3 (מהירות שיא) | ≥ 5 MB/s על swarm פעיל סטנדרטי |
| K4 (peers) | ≥ 10 peers ממוצע |
| K5 (choke) | תצורה A — choke cycles בקצב יציב; B — חזרתיות גבוהה |
| K7 (כשלי hash) | < 1% מסך ה-pieces |

### 24.2.4 מצב הביצוע

> **סטטוס**: הניסויים האמפיריים **לא בוצעו בזמן כתיבת הפרק**.
> רשומה ב-`book/TODO.md` מתעדת זאת. ההמלצה לסטודנט: לבצע
> את 10 ההרצות לפי הפרוטוקול הנ"ל לפני ההגשה הסופית, ולמלא
> את הטבלאות בסעיף 24.2.6 בערכים האמיתיים.

### 24.2.5 טבלת תוצאות — תבנית

טבלה למילוי לפי הניסויים:

| הרצה # | תצורה | זמן (sec) | Avg Speed (MB/s) | Peak (MB/s) | Avg Peers | Choke Cycles | Rarest Sel. |
|---|---|---|---|---|---|---|---|
| 1 | A | _____ | _____ | _____ | _____ | _____ | _____ |
| 2 | A | _____ | _____ | _____ | _____ | _____ | _____ |
| 3 | A | _____ | _____ | _____ | _____ | _____ | _____ |
| 4 | A | _____ | _____ | _____ | _____ | _____ | _____ |
| 5 | A | _____ | _____ | _____ | _____ | _____ | _____ |
| 1 | B | _____ | _____ | _____ | _____ | _____ | N/A |
| 2 | B | _____ | _____ | _____ | _____ | _____ | N/A |
| ... | ... | ... | ... | ... | ... | ... | ... |

### 24.2.6 ניתוח סטטיסטי שיש לבצע

לאחר 5 הרצות לכל תצורה, יש לחשב:

- **ממוצע** ו-**סטיית תקן** לכל KPI.
- **t-test** למובהקות סטטיסטית של ההפרש בין A ל-B.
- **גרף עמודות** של ממוצעים A מול B עם error bars.

> **תרשים נדרש (Fig-30)**: גרף השוואת ביצועים A מול B
> (bar chart עם error bars). יצויר אחרי הניסויים. ראה
> רשומה ב-`IMAGES.md`.

### 24.2.7 חלופה: ערכים מהספרות

אם הזמן לא מאפשר ניסויים עצמיים, ניתן להציג ערכים מסקרים
אקדמיים. ההפניות העיקריות:

- **Legout et al., IMC 2006** ("Rarest First and Choke
  Algorithms Are Enough") — מציגים rarest-first שמשיג ~95%
  ניצול ניצולת ה-swarm כאשר random משיג ~70%.
- **Cohen, 2003** ("Incentives Build Robustness in
  BitTorrent") — מדגים ש-Tit-for-Tat מונע free-riders
  ביעילות.

ערכים אלה ניתנים לציטוט בפרק 27 (ביבליוגרפיה) ובסעיף 6.2
(רקע תיאורטי).

---

## 24.3 בדיקות איכות נוספות

### 24.3.1 Linting & Static Analysis

לפי הקוד הקיים:
- אין `print()` בקוד הפרודקשן — וידאתי בחיפוש `grep`.
- אין `bare except:` (תפיסת חריגות ללא טיפוס) — כל
  `except` נקוב.
- כל הפונקציות הציבוריות עם type hints.
- כל הפונקציות הציבוריות עם docstring.

### 24.3.2 בדיקת אבטחה ידנית

נבדקו ידנית מספר וקטורי תקיפה (פרק 12.1.2, T1–T11):

| וקטור | סטטוס בדיקה |
|---|---|
| T1 (piece data שגוי) | מאומת ע"י `test_security_hash_failure_triggers_ban` |
| T2 (length prefix חורג) | מאומת ע"י קבוע `MAX_MESSAGE_SIZE`; בדיקה ידנית |
| T3 (piece_index לא חוקי) | מאומת ע"י `test_validate_piece_index` |
| T4 (info_hash שגוי ב-handshake) | מאומת ב-`test_peer_connection.py` |
| T5 (msg_id לא חוקי) | בדיקה ידנית — `MessageType(msg_id)` זורקת `ValueError` |
| T6–T11 | חלקם תיאורטיים בלבד; פירוט בפרק 12 |

### 24.3.3 בדיקת תאימות מערכת הפעלה

המערכת נוסתה (בזמן הפיתוח) על:
- **Linux** (Ubuntu 22.04): מלאה.
- **Windows 10**: דרך `start.bat` + winget — מלאה.
- **macOS**: לא נוסתה ידנית — תאימות לוגית בלבד (`start.sh`
  תומך ב-brew).

---

## 24.4 סיכום הפרק

הפרק תיעד:

- **160 unit tests** ב-pytest המכסים את כל 8 המודולים של
  ה-Engine (1,421 שורות בדיקה).
- **פרוטוקול הערכה אמפירית מערכתית** שמשווה rarest-first
  + Tit-for-Tat מול random + round-robin על 5 הרצות לכל
  תצורה.
- **7 KPIs** שנמדדים לכל הרצה, עם מקור הנתונים מ-API
  endpoints.
- **6 דרישות עבירה** מינימליות (פרק 5).
- **תבנית טבלת תוצאות** (סעיף 24.2.5) שתמולא לפני
  ההגשה.
- **בדיקות איכות משלימות** — lint, security manual, OS
  compat.

> **פער מתועד**: הניסויים האמפיריים (5×2 הרצות) **לא בוצעו
> בעת כתיבה** — רשומה ב-`book/TODO.md`. השלמת הניסויים
> נדרשת לפני ההגשה הסופית; חלופה: ערכים מספרות (פרק 27).

הפרק הבא (פרק 25) הוא **מסקנות** — מה למדנו מהפרויקט.
