# 24. בדיקות והערכה

## בדיקות יחידה (Unit Tests)

בתיקייה `python_engine/tests/` קיימות **160 פונקציות
בדיקה** ב-8 קבצים, סך הכל 1,421 שורות קוד בדיקה. הן
מכסות את כל המודולים של ה-Engine.

| קובץ | מודול נבדק | מספר בדיקות |
|---|---|---|
| `test_bencode.py` | bencode | 44 |
| `test_piece_manager.py` | piece_manager | 27 |
| `test_security.py` | security | 26 |
| `test_peer_connection.py` | peer_connection | 14 |
| `test_tracker_client.py` | tracker_client | 14 |
| `test_torrent_metadata.py` | torrent_metadata | 14 |
| `test_api_server.py` | api_server | 13 |
| `test_download_manager.py` | download_manager | 8 |

הבדיקות מאורגנות בשלוש קטגוריות: בדיקות יחידה טהורות
(פונקציה אחת + assertions), בדיקות state machine (סדרת
פעולות + assertion על המצב הסופי), ובדיקות אינטגרציה
בין מודולים. דוגמה לבדיקת `select_piece_rarest_first`:

```python
def test_rarest_first_chooses_minimum_frequency():
    hashes = [b'\x00' * 20] * 4
    pm = PieceManager(num_pieces=4, piece_length=16384,
                      total_size=65536, piece_hashes=hashes)
    pm.update_peer_pieces("A:6881", [True, True, False, False])
    pm.update_peer_pieces("B:6881", [True, True, True, False])
    pm.update_peer_pieces("C:6881", [True, True, True, True])
    # Frequencies: 0→3, 1→3, 2→2, 3→1 (rarest)
    selected = pm.select_piece_rarest_first([True, True, True, True])
    assert selected == 3
```

הרצה: `pytest python_engine/tests/ -v` (נדרש
`pip install pytest pytest-asyncio`).

**פערים מתועדים**: אין בדיקות ל-Swing components ב-Java
(headless GUI testing מסובך); אין end-to-end network
tests עם peer חי (דורש mock TCP server).

## הערכה אמפירית

מעבר ל-unit tests, נדרשת הערכה אמפירית של הביצועים מול
ה-KPIs שהוגדרו בפרק 5. הפרוטוקול המוצע:

- **קובץ בדיקה**: torrent יציב בגודל ~1 GB (ISO של
  Debian/Ubuntu).
- **שתי תצורות**: A = `rarest_first` + `tit_for_tat`
  (המומלצת); B = `random` + `round_robin` (baseline).
- **5 הרצות לכל תצורה** → 10 הרצות סה"כ.
- **לכל הרצה**: שמירת CSV מ-`/algorithm-stats/<id>`
  ומ-`/stats-summary`.

המדדים שנמדדים: זמן הורדה, מהירות ממוצעת ושיא, peers
ממוצעים, choke cycles, בחירות rarest, ואחוז כשלי SHA-1.
ההשערה: תצורה A מהירה משמעותית מ-B עבור swarm זהה.

**הניסויים האמפיריים לא בוצעו בעת כתיבת הספר** — רשומה
ב-TODO.md מתעדת זאת. השלמה לפני ההגשה הסופית מומלצת.
חלופה: ציטוט ערכים מהספרות — Legout *et al.* (IMC 2006)
הראו ש-rarest-first משיג ~95% ניצול ניצולת ה-swarm
לעומת ~70% ב-random.

## בדיקות איכות נוספות

- **אין `print()` בקוד הפרודקשן**; הכל עובר דרך
  `logging.getLogger(__name__)`.
- **אין `bare except`**; כל `except` נקוב בטיפוס.
- **כל פונקציה ציבורית עם type hints + docstring**.
- **תאימות OS**: נוסה על Linux (Ubuntu 22.04) ועל
  Windows 10. macOS לא נוסה ידנית אך התשתית
  (`start.sh` + `brew`) נראית תקפה.
