# פרק 15 – ניתוח ותרשים Use Cases / UML של המערכת המוצעת

## פתיח

פרק זה הוא **הפרק הטכני המקיף ביותר בספר**. הוא עוקב אחר 12
תתי-הסעיפים הנדרשים בנוהל ההגשה (עמ' 11–12), ומציג את
המערכת מ-**שש זוויות מבט** משלימות:

1. **Use Cases** — תיאור פונקציונלי של המערכת מנקודת מבט המשתמש
   (15.1, 15.2, 15.7, 15.8).
2. **מבני נתונים** — מה משמש לאחסון מצב המערכת ומדוע (15.3).
3. **יעילות אלגוריתמים** — ניתוח סיבוכיות זמן ומקום של
   האלגוריתמים המרכזיים (15.4).
4. **קשרים בין יחידות** — מי קורא למי, מי מעדכן את מי (15.5).
5. **עץ מודולים** — מבנה הספריות והקבצים (15.6).
6. **UML / מחלקות** — תרשימי מחלקות, Design Class Diagram,
   ותיאור מפורט של כל מחלקה (15.9–15.12).

הפרק מסתמך על קוד הפרויקט בפועל בלבד; אין בו תכנונים תיאורטיים
שלא מומשו. הקבצים העיקריים שאליהם הפרק מתייחס:
`python_engine/*.py` (8 מודולים) ו-`java_gui/src/*.java`
(3 מחלקות).

---

## 15.1 ה-Use Cases העיקריים והאלגוריתם הראשי

### 15.1.1 ארבעת ה-UCs העיקריים

המערכת מספקת ארבע **קבוצות פעולה** עיקריות מנקודת מבט המשתמש:

- **UC-1: ניהול הורדה** — הוספת קובץ `.torrent`, צפייה בהתקדמות,
  עצירה/חידוש/ביטול הורדה, וצפייה בלוגים.
- **UC-2: בחירת אלגוריתמים** — לפני התחלת הורדה, בחירה בין
  *rarest-first* או *random* לבחירת piece, ובין *Tit-for-Tat*
  או *round-robin* לבחירת peers.
- **UC-3: צפייה בהיסטוריה** — פתיחת חלון היסטוריה ובו רשימת כל
  ההורדות שהסתיימו (גם מהפעלות קודמות, דרך SQLite).
- **UC-4: צפייה בסטטיסטיקות אלגוריתמיות** — חלון `AlgorithmStatsDialog`
  המציג גרף עמודות של בחירות *rarest*, choke/unchoke counts, ועוד.

### 15.1.2 האלגוריתם הראשי — `Download._download_loop`

ליבת המערכת היא **לולאה אסינכרונית יחידה** (`_download_loop`)
שרצה ב-`Python Engine` עבור כל torrent פעיל. הלולאה מנהלת
את כל מחזור החיים של ההורדה — מהתחברות ל-tracker, דרך תקשורת
עם peers, ועד לאימות piece-by-piece וכתיבה לדיסק.

**פסאודו-קוד תמציתי** של האלגוריתם הראשי (פרושו האמיתי
ב-`python_engine/download_manager.py:_download_loop`):

```
async _download_loop():
    1. אתחל TrackerClient + שלח announce(event='started')
    2. הוסף את ה-peers שהוחזרו ל-_known_peers
    3. הפעל ברקע:
         _choke_loop()           ← כל 10 שניות
         _keep_alive_loop()      ← כל 60 שניות
         start_periodic_announce ← כל interval של ה-tracker
         _connect_to_peers()     ← non-blocking
    4. while not piece_manager.is_complete and state == RUNNING:
         a. piece_manager.reset_stale_pieces(30s)
         b. _request_pieces()         ← מבקש בלוקים מ-peers
         c. await asyncio.sleep(0.1)  ← מאפשר ל-IO לרוץ
         d. כל 15 שניות:
              _cleanup_dead_peers()
              _connect_to_peers()
         e. _update_speed() + tracker.update_stats(...)
    5. אם is_complete:
         _complete_download() ← מסכם, שולח announce(event='completed')
    6. finally: _save_state() ← שמירת JSON ל-data/state/<id>.json
```

הלולאה הזו רצה ב-asyncio event loop בלבד; היא **לא חוסמת** —
בכל מקום שבו נדרשת פעולה חוסמת (SHA-1, כתיבה לדיסק) היא
מועברת ל-`ThreadPoolExecutor` דרך `loop.run_in_executor`.

### 15.1.3 שלושת האלגוריתמים המישניים

**אלגוריתם 1: rarest-first piece selection**
(`piece_manager.py:select_piece_rarest_first`)

```
select_piece_rarest_first(peer_pieces):
    candidates = []
    min_freq = infinity
    for i in range(num_pieces):
        if pieces[i].status != MISSING: continue
        if not peer_pieces[i]: continue
        freq = _peer_frequency[i]
        if freq < min_freq:
            min_freq = freq
            candidates = [i]
        elif freq == min_freq:
            candidates.append(i)
    return random.choice(candidates) if candidates else None
```

**אלגוריתם 2: Tit-for-Tat unchoke** (`download_manager.py:_tit_for_tat_unchoke`)

```
_tit_for_tat_unchoke():
    interested = peers_who_are_interested()
    sort interested by bytes_downloaded DESC
    unchoke_set = top K=4 peers
    optimistic = random choice from remaining
    unchoke_set.add(optimistic)
    for peer in connections:
        if peer in unchoke_set and was_choked: send_unchoke()
        elif peer not in unchoke_set and was_unchoked: send_choke()
```

**אלגוריתם 3: round-robin unchoke** (השוואה — `_round_robin_unchoke`)

```
_round_robin_unchoke():
    choke all currently unchoked
    pick next peer in rotation: connected[_rr_index]
    unchoke that peer
    _rr_index = (_rr_index + 1) % len(connected)
```

ניתוח יעילות מלא של שלושת האלגוריתמים מופיע בסעיף 15.4.

> **תרשים נדרש (Fig-10)**: תרשים זרימה (Flowchart) של
> `_download_loop`, המציג את שלבי האתחול, הלולאה הראשית,
> ושלבי הסיום. ראה רשומה ב-`IMAGES.md`.

---

## 15.2 Use Case מפורט לכל פונקציה עיקרית

הסעיף מציג Use Case מלא לפי תבנית רגילה (UC ID, שחקנים,
תנאים מקדימים, תרחיש ראשי, תרחישי חלופה) עבור הפונקציות
המרכזיות במערכת.

### UC-1: הוספת torrent חדש להורדה

| שדה | פרט |
|---|---|
| **מזהה** | UC-01 |
| **שם** | Add Torrent |
| **שחקן ראשי** | משתמש קצה |
| **תנאי מקדים** | מערכת רצה; קובץ `.torrent` תקין קיים מקומית |
| **תרחיש ראשי** | 1. המשתמש לוחץ "Add Torrent" ב-toolbar. 2. ה-GUI פותח `JFileChooser`. 3. המשתמש בוחר קובץ. 4. ה-GUI פותח `JFileChooser` שני לבחירת תיקיית יעד. 5. ה-GUI שולח `POST /torrents` עם הקובץ + אלגוריתמים שנבחרו. 6. ה-Engine מאתחל `TorrentMetadata`, יוצר `Download`, ומחזיר `id`. 7. ה-GUI מציג שורה חדשה בטבלה במצב `Queued`/`Running`. |
| **תרחיש חלופה — קובץ פגום** | 5a. ה-Engine מחזיר `400 Bad Request`. 5b. ה-GUI מציג Alert עם הודעת השגיאה (פרק 19). |
| **תרחיש חלופה — שרת לא זמין** | 5a. ה-HTTP request נכשל. 5b. ה-GUI לוכד `IOException` ומציג Alert. |
| **תוצאה (Postcondition)** | רשומה ב-`DownloadManager.downloads`; טאסק `_download_loop` רץ; `data/state/<id>.json` נוצר. |

### UC-2: השהיית/חידוש/ביטול הורדה

| שדה | פרט |
|---|---|
| **מזהה** | UC-02 |
| **שם** | Pause / Resume / Cancel Download |
| **שחקן ראשי** | משתמש קצה |
| **תנאי מקדים** | הורדה פעילה (`Running`) או מושהית (`Paused`) |
| **תרחיש ראשי (Pause)** | 1. המשתמש בוחר שורה בטבלה. 2. לוחץ "Pause". 3. GUI שולח `POST /torrents/<id>/pause`. 4. ה-Engine קורא ל-`manager.pause_download(id)` → `Download.pause()` → ה-state עובר ל-`Paused`, חיבורים נסגרים, מצב נשמר. 5. ה-GUI רואה בעדכון הבא ש-state השתנה ל-`Paused`. |
| **Resume** | זהה — קריאה ל-`POST /torrents/<id>/resume` שמפעילה מחדש את `_download_loop`. |
| **Cancel** | זהה — קריאה ל-`POST /torrents/<id>/cancel`; בנוסף, נשלח `event=stopped` ל-tracker וה-state נשמר ל-SQLite. |
| **תוצאה** | State המתאים, רישום אירוע ב-`events`, חיבורי peers סגורים. |

### UC-3: צפייה בהיסטוריה

| שדה | פרט |
|---|---|
| **מזהה** | UC-03 |
| **שם** | Show History |
| **שחקן ראשי** | משתמש קצה |
| **תרחיש ראשי** | 1. המשתמש לוחץ "History" ב-toolbar. 2. GUI שולח `GET /history`. 3. ה-Engine שולף מ-SQLite (`torrents` JOIN `performance_stats`). 4. GUI מציג `JDialog` עם `JTable` שכוללת: שם, גודל, זמן, מהירות ממוצעת, אלגוריתם, סטטוס סופי. 5. למשתמש יש כפתור "Clear History" שלוחץ עליו שולח `DELETE /history`. |
| **תוצאה** | חלון `JDialog` מודאלי שניתן לסגור עם "Close". |

### UC-4: צפייה בסטטיסטיקות אלגוריתמיות

| שדה | פרט |
|---|---|
| **מזהה** | UC-04 |
| **שם** | Show Algorithm Stats |
| **שחקן ראשי** | משתמש קצה |
| **תנאי מקדים** | קיימת לפחות הורדה אחת עם נתוני algorithm_stats |
| **תרחיש ראשי** | 1. המשתמש בוחר שורה בטבלה. 2. לוחץ "Stats". 3. GUI שולח `GET /algorithm-stats/<id>` + `GET /stats-summary`. 4. נפתח `AlgorithmStatsDialog` שמציג: bar chart של בחירות rarest-first, מספרי choke/unchoke, ממוצעי מהירות. |
| **תוצאה** | חלון מודאלי עם גרפים ב-Java2D. |

### UC-5: בחירת אלגוריתמים

| שדה | פרט |
|---|---|
| **מזהה** | UC-05 |
| **שם** | Configure Algorithms |
| **שחקן ראשי** | משתמש קצה |
| **תרחיש ראשי** | 1. ב-toolbar הראשי, ה-`JComboBox` מאפשרים לבחור: `pieceAlgorithm` ∈ {`rarest_first`, `random`}, `peerAlgorithm` ∈ {`tit_for_tat`, `round_robin`}. 2. הבחירה נשלחת כפרמטר ב-`POST /torrents` של ה-UC הבא. 3. ב-`Download` נשמרים `self.piece_algorithm`/`self.peer_algorithm`. |
| **תוצאה** | האלגוריתמים בשימוש עבור ההורדה הספציפית; ניתן להריץ הורדות שונות עם אלגוריתמים שונים בו-זמנית. |

### UC-6: אינטראקציה אוטומטית עם Peer (System UC, ללא משתמש)

| שדה | פרט |
|---|---|
| **מזהה** | UC-06 |
| **שם** | Exchange Data with Peer |
| **שחקן ראשי** | המערכת עצמה (system actor) |
| **שחקן שני** | Peer חיצוני |
| **תנאי מקדים** | יש peer ברשימת `_known_peers` שלא מבונה |
| **תרחיש ראשי** | 1. `_connect_to_peers` יוצר `PeerConnection`. 2. `connect()` פותח TCP + מבצע `_send_handshake` + `_receive_handshake`. 3. שולח `BITFIELD` של ה-pieces שלנו. 4. מקבל `BITFIELD` מהפיר → מעדכן `piece_manager._peer_frequency`. 5. שולח `INTERESTED` אם יש לפיר piece שאנחנו צריכים. 6. אם הפיר שלח `UNCHOKE` — `select_piece_rarest_first` בוחר piece. 7. שליחת `REQUEST` לבלוקים → קבלת `PIECE` → submit לפיס מנגר. 8. כשהפיס שלם → SHA-1 verify → אם OK: כתיבה לדיסק + `HAVE` broadcast; אחרת: `report_hash_failure`. |
| **תרחיש חלופה — handshake נכשל** | סגירת חיבור, `PeerConnectionError`. |
| **תרחיש חלופה — hash failure** | באן אחרי 3 כשלים (פרק 12). |

---

## 15.3 מבני נתונים

הסעיף מפרט את מבני הנתונים העיקריים בקוד, את הסיבה לבחירת
כל אחד, ואת השימוש בו בפועל.

### 15.3.1 טבלת מבני הנתונים העיקריים

| מבנה | סוג Python | שימוש | סיבה לבחירה |
|---|---|---|---|
| `Download.downloads` | `Dict[str, Download]` | מפתח לפי `id` של torrent | גישה O(1) לחיפוש לפי id |
| `Download._connections` | `Dict[str, PeerConnection]` | מפתח לפי `ip:port` | O(1) lookup/הסרה של peer |
| `Download._known_peers` | `Set[Peer]` | רשימת peers ידועים מה-tracker | מניעת כפילויות; `__hash__` ב-`Peer` |
| `Download._log_buffer` | `collections.deque(maxlen=200)` | חוצץ לוגים live עם capacity קבוע | רוטציה אוטומטית של היסטוריה ישנה — O(1) append + drop |
| `PieceManager.pieces` | `List[Piece]` | כל ה-pieces לפי index | גישה O(1) לפי index |
| `PieceManager._peer_frequency` | `Dict[int, int]` | piece_index → מספר peers שיש להם אותו | עדכון O(1) ב-HAVE; קריאה O(1) |
| `PieceManager._peer_pieces` | `Dict[str, Set[int]]` | peer_key → קבוצת piece_indices | חישוב diff מהיר בעת ניתוק peer |
| `PieceManager.rarest_selections` | `Dict[int, int]` | piece_index → מספר פעמים שנבחר כ-rarest | סטטיסטיקה לפרק 24 |
| `Piece.blocks` | `List[Block]` | חלוקת piece לבלוקים של 16KB | רשימה ממוינת לפי offset |
| `Piece._data` | `bytearray(length)` | מאגר נתונים mutable per-piece | יעיל לכתיבת בלוקים נפרדים |
| `SecurityManager._peer_reputations` | `Dict[str, PeerReputation]` | peer_key → מוניטין | O(1) lookup |
| `SecurityManager._banned_peers` | `Set[str]` | peer_keys מבוננים | O(1) `in` בדיקה |
| `SecurityManager._events` | `List[SecurityEvent]` | יומן אירועים | append O(1); נחתך ב-`/events?limit=N` |
| `PeerConnection.peer_pieces` | `List[bool]` | bitfield של ה-peer (אילו pieces יש לו) | התאמה לחתימת `select_piece` |
| `PeerConnection._download_samples` | `List[Tuple[float, int]]` | חלון 30 שניות של (timestamp, bytes) לחישוב rate | חישוב moving-average ללא מבנה משוכלל |

### 15.3.2 מבנים מיוחדים לתאום (concurrency)

- **`ThreadPoolExecutor(max_workers=2)`** ב-`Download._executor`:
  ממולא ע"י Python `concurrent.futures`. משמש לחישובי SHA-1
  ולכתיבה לדיסק — שני העומסים החוסמים היחידים. שני workers
  מאזנים בין שימוש במעבד לבין מניעת context-switch overhead.

- **`threading.Lock`** ב-`PieceManager._lock`: מגן על
  `_peer_frequency` ו-`_peer_pieces` שמתעדכנים גם מהאוויינט
  לופ וגם מהworker threads.

- **`threading.Lock`** ב-`api_server._db_lock`: מגן על
  הגישה ל-SQLite מבקשות Flask מקבילות.

- **`asyncio.Lock`** — לא בשימוש; ה-event loop של asyncio
  הוא single-threaded ולכן רוב המבנים האסינכרוניים אינם
  זקוקים לנעילה.

### 15.3.3 בחירת `deque` ל-log buffer

ה-log buffer הוא `collections.deque(maxlen=200)`. הסיבות
לבחירה:

- **append O(1)** — חשוב כי כותבים אליו בלולאת ההורדה
  אחת ל-100ms לפעמים.
- **drop oldest אוטומטי** — כשנגמרת capacity, איבר ישן יוצא
  מצד שמאל בלי קוד נוסף.
- **traversal ליניארי** ב-`get_logs(since_seq)` — O(N) על
  200 איברים, כלומר זמן קבוע בפועל.

החלופה הייתה `List` עם slicing — עולה לנו בהעתקות מיותרות
בכל `pop(0)`.

---

## 15.4 חישוב יעילות אלגוריתמים

זהו סעיף החובה החשוב ביותר במחוון לקטגוריה השנייה (*"פתרון
בעיה אלגוריתמית"*, עמ' 4 בנוהל). הסעיף מנתח את הסיבוכיות
של האלגוריתמים המרכזיים.

### 15.4.1 rarest-first piece selection

**הקוד:** `piece_manager.py:select_piece_rarest_first`.

**ניתוח**:
- מעבר על כל ה-pieces: `for i in range(num_pieces)` → **O(N)**
  כאשר N = מספר ה-pieces (בקובץ של 4GB עם piece_length=256KB,
  N ≈ 16,384).
- בכל piece, פעולות: 2 בדיקות סטטוס + lookup ב-`_peer_frequency`
  (dict, O(1)) + עדכון `candidates`. כל הפעולות **O(1)**.
- `random.choice(candidates)` — **O(1)** ל-list בגודל ≤ N.
- **סיבוכיות זמן כוללת**: **O(N)**.
- **סיבוכיות מקום**: **O(N)** במקרה הגרוע (`candidates`
  עשוי להכיל את כל ה-pieces המשותפים).

**תדירות קריאה**: כל פעם שיש לפיר חדש לתת לו piece — לרוב
פעם ב-100ms עד שנייה. עבור N=16,384, פעולה אחת אורכת
~1ms על Python — מתחת לסף של "חוסם את ה-event loop".

### 15.4.2 random piece selection (baseline)

**הקוד:** `piece_manager.py:select_piece_random`.

זהה במבנה ל-rarest-first **ללא** חישוב מינימום ובלי דירוג —
פשוט מאסף `candidates` ובוחר ב-random. **O(N)** זמן,
**O(N)** מקום. בפועל מהיר במעט בקבוע — 2 פעולות פחות
ב-piece.

**מסקנה השוואתית**: rarest-first ו-random הם **שניהם O(N)**.
ההבדל ביניהם הוא איכותי (התפלגות הבחירה), לא סיבוכיות.

### 15.4.3 עדכון תדירות (`update_peer_have`, `update_peer_pieces`)

**`update_peer_have(peer_key, piece_index)`** (קבלת
`HAVE`):
- בדיקת `peer_key in _peer_pieces` — **O(1)**.
- הוספה ל-set + עדכון מונה — **O(1)**.
- **סיבוכיות כוללת**: **O(1)**.

**`update_peer_pieces(peer_key, pieces)`** (קבלת
`BITFIELD`):
- מעבר על כל הביטים: **O(N)**.
- אם פיר זה כבר היה רשום, הסרה ראשונה גם O(N).
- **כוללת**: **O(N)** עבור BITFIELD יחיד.

תדירות: HAVE נשלח אחרי כל piece שהושלם — לכל peer; BITFIELD
נשלח פעם אחת בלבד בתחילת חיבור.

### 15.4.4 Tit-for-Tat unchoke

**הקוד:** `download_manager.py:_tit_for_tat_unchoke`.

- מעבר על כל החיבורים: **O(K)** כאשר K ≤ 50 (`MAX_CONNECTIONS`).
- מיון לפי `bytes_downloaded`: **O(K log K)**.
- בחירת optimistic random: **O(K)**.
- שליחת CHOKE/UNCHOKE לכל אחד: **O(K)** TCP writes.
- **סיבוכיות כוללת**: **O(K log K)**.
- תדירות: כל 10 שניות (`CHOKE_INTERVAL`).

עבור K=50, פעולה אחת לוקחת ~50·log₂(50) ≈ 280 פעולות
ביסיסיות, כלומר מיקרו-שנייה במעבד מודרני — זניח.

### 15.4.5 round-robin unchoke (baseline)

- choke כולם: **O(K)**.
- בחירת הבא בתור: **O(1)** באמצעות `_rr_index`.
- שליחת UNCHOKE לאחד: **O(1)**.
- **סיבוכיות כוללת**: **O(K)**.

**מסקנה השוואתית**: round-robin **טוב יותר בסיבוכיות**
(O(K) במקום O(K log K)), אך **גרוע יותר באיכות הסחר** —
לא מעודד peers שתורמים, אינו עמיד ל-leechers. הקבוצה
המומלצת היא לכן Tit-for-Tat למרות העלות הנוספת.

### 15.4.6 SHA-1 piece verification

**הקוד:** `piece_manager.py:Piece.verify_hash` →
`hashlib.sha1(bytes(self._data)).digest()`.

- חישוב SHA-1 על piece בגודל **L bytes**: **O(L)**.
- עבור L=256KB: ~0.5 מיליסקונדות במעבד מודרני.
- עבור L=1MB: ~2 מיליסקונדות.
- **לחישוב SHA-1 קבוע משוערך 500MB/s** במעבד x86-64 ללא
  הוראות AVX-512 ייעודיות.

**ההחלטה האדריכלית**: אף שעלות החישוב נמוכה במונחים אבסולוטיים,
היא **חוסמת את ה-event loop** אם הייתה רצה ב-coroutine רגיל.
לכן הקריאה נעטפת ב-`loop.run_in_executor(self._executor, ...)`
(ראה פרק 11.3.2).

### 15.4.7 חישוב bitfield ל-bytes

**הקוד:** `peer_connection.py:send_bitfield`.

- אריזה של N booleans ל-`bytearray((N+7)//8)`: **O(N)**.
- שליחת message: **O(N/8)** bytes.
- מתבצע פעם אחת בכל חיבור peer.

### 15.4.8 פרסור bencode

**הקוד:** `bencode.py:decode`.

- recursive descent parser; כל token מטופל **O(1)**.
- ה-input מ-`.torrent` הוא לרוב ≤ 1MB, וגם זה רק רשימת
  hashים.
- **סיבוכיות כוללת**: **O(M)** כאשר M = אורך ה-input
  בבתים. בפועל פחות מ-10 מילי-שניות לקובץ torrent ממוצע.

### 15.4.9 סיבוכיות מקום של הורדה פעילה

- ה-pieces **לא מוחזקים כולם בזיכרון בו-זמנית**: כל piece
  שמושלם נכתב לדיסק ונשמר במצב `COMPLETED` כעצם `Piece` עם
  `bytearray` ריק (לא מאופס לחיסכון).
- במקרה הגרוע: K peers × ≤ piece_length each (פיסים שאינם
  COMPLETED עדיין) = **O(K · piece_length)** במגבלה
  של `MAX_CONNECTIONS=50` ו-`piece_length≤4MB` = 200MB.
- בפועל הרבה פחות, כי לא כל ה-peers מורידים piece שונה
  בו-זמנית.

### 15.4.10 סיכום טבלאי

| פעולה | קוד | זמן | מקום |
|---|---|---|---|
| Rarest-first selection | `select_piece_rarest_first` | O(N) | O(N) |
| Random selection | `select_piece_random` | O(N) | O(N) |
| HAVE update | `update_peer_have` | O(1) | O(1) |
| BITFIELD update | `update_peer_pieces` | O(N) | O(N) |
| Tit-for-Tat unchoke | `_tit_for_tat_unchoke` | O(K log K) | O(K) |
| Round-robin unchoke | `_round_robin_unchoke` | O(K) | O(1) |
| SHA-1 verify | `Piece.verify_hash` | O(L) | O(1) |
| Send bitfield | `send_bitfield` | O(N) | O(N/8) |
| Bencode decode | `bencode.decode` | O(M) | O(M) |

---

## 15.5 הקשרים בין היחידות

הסעיף מתאר את **זרימת הנתונים והקריאות** בין המודולים. כל
מודול הוא יחידה אחראית בעלת חוזה מוגדר.

### 15.5.1 גרף תלויות בין מודולי Python (Engine)

```
                 api_server.py  (Flask + REST)
                       │
                       │ calls
                       ▼
                 DownloadManager        ←──── main entry per process
                       │
                       ├── add_torrent ──► Download
                       └── pause/resume/cancel_download(id)
                                 │
                       ┌─────────┼─────────────────────────┐
                       │         │                         │
                       ▼         ▼                         ▼
              TrackerClient  PieceManager           SecurityManager
                       │         │                         │
            uses HTTP  │         │                         │
                       │   manages Pieces + Blocks         │
                       ▼         │                         │
                  Peer (dataclass-like)                    │
                                 ▼                         │
                         hashlib.sha1                      │
                                                           │
              PeerConnection ◄────── DownloadManager ─────►│
                │                          │      reports  │
                │                          ▼               │
                └─── handshake/messages──► _on_peer_message
                                                  │
                                                  └──► piece_manager.submit_block
                                                  └──► security.report_*
```

### 15.5.2 גרף תלויות Java GUI

```
TorrentClientGUI (JFrame)
    ├── ApiService (HTTP client)
    │      ├── HttpClient (java.net.http)
    │      └── TorrentStatus (data class)
    │
    ├── AlgorithmStatsDialog (JDialog)
    │      └── BarChartPanel (JPanel, Java2D)
    │
    └── ScheduledExecutorService (polls API every 500ms)
```

### 15.5.3 חוצה-תהליכים: GUI ↔ Engine

המעבר בין שני התהליכים מבוצע **דרך REST/JSON בלבד**:

```
Java GUI                            Python Engine
┌────────────────┐                  ┌────────────────┐
│ ApiService     │   HTTP/JSON      │ Flask routes   │
│ .startDownload ├─── POST ────────►│ /torrents      │
│ .getStatus     ├─── GET   ────────►│ /torrents      │
│ .pause         ├─── POST ────────►│ /torrents/:id  │
│ ...            │                  │                │
└────────────────┘                  └────────────────┘
```

אין ערוצים נוספים — לא shared memory, לא pipes, לא file
descriptors משותפים. כל מה שצריך להעביר עובר במעבר אחד דרך
loopback.

### 15.5.4 זרימת אירועים בעת קבלת PIECE מ-peer

תרחיש מלא של "מה קורה ברגע ש-peer שלח אלינו block":

```
1. PeerConnection._read_message     ← קורא 4-byte length + payload
2. PeerConnection._handle_message   ← מעדכן conn.bytes_downloaded,
                                      conn.download_rate, מפחית
                                      _pending_requests
3. PeerConnection.on_message        ← callback מוקצה ב-_connect_peer
                                      ל-Download._on_peer_message
4. Download._on_peer_message (ענף message.type == PIECE):
   a. אם data is None — return
   b. אם piece כבר COMPLETED — return (dedup מ-peers שונים)
   c. piece_manager.submit_block(piece_idx, offset, data)
   d. stats.bytes_downloaded += len(data)
   e. אם is_complete של ה-piece (כל הבלוקים התקבלו):
        verify_piece(idx)              ← ב-ThreadPoolExecutor
        אם OK:
           security.report_successful_piece(peer_key)
           _write_piece_sync(idx)      ← ב-ThreadPoolExecutor
           ניקוי _peer_piece עבור ה-idx
           asyncio.create_task(_broadcast_have(idx))  ← non-blocking
           _on_progress callback (אם רשום)
           אם piece_manager.is_complete (כל ה-pieces): state = COMPLETED
           _request_from_peer(peer_key, conn)  ← עבודה חדשה לאותו peer
        אחרת (verify נכשל):
           security.report_hash_failure(peer_key, idx)
           ניקוי _peer_piece עבור ה-idx
           אם security.is_peer_banned(peer_key) → conn.disconnect()
```

> **תרשים נדרש (Fig-11)**: Sequence Diagram של זרימת
> קבלת PIECE כפי שתואר. ראה רשומה ב-`IMAGES.md`.

---

## 15.6 עץ מודולים

```
Project_Gal/
├── python_engine/                    ← Engine (Python 3.8+)
│   ├── __init__.py
│   ├── __main__.py                   ← entry: python -m python_engine
│   ├── api_server.py     (509 שורות) ← Flask REST API + SQLite + bridge
│   ├── download_manager.py (891)     ← Download + DownloadManager + algorithms
│   ├── piece_manager.py    (473)     ← Piece + Block + PieceManager
│   ├── peer_connection.py  (520)     ← PeerConnection + MessageType + PeerMessage
│   ├── tracker_client.py   (337)     ← TrackerClient + Peer + TrackerResponse
│   ├── torrent_metadata.py (241)     ← TorrentMetadata + FileInfo
│   ├── bencode.py          (231)     ← encode/decode + errors
│   ├── security.py         (326)     ← SecurityManager + PeerReputation + events
│   ├── main.py             (190)     ← CLI mode entry (ללא GUI)
│   └── tests/                        ← pytest tests
│
├── java_gui/                         ← GUI (Java 11+, Swing)
│   ├── src/
│   │   ├── TorrentClientGUI.java     (649) ← JFrame ראשי + toolbar + table
│   │   ├── ApiService.java           (430) ← HTTP client לעיניין ה-Engine
│   │   └── AlgorithmStatsDialog.java (562) ← JDialog + BarChartPanel
│   ├── lib/json.jar                  ← org.json תלות חיצונית יחידה
│   └── build/                        ← bytecode מקומפל
│
├── data/                             ← runtime data (לא ב-git)
│   ├── downloads/                    ← קבצים שהורדו
│   ├── state/                        ← <id>.json שמירת מצב
│   └── history.db                    ← SQLite — היסטוריה + events
│
├── book/                             ← הספר עצמו (Markdown)
├── guidelines/                       ← מחוון + נוהל
├── requirements.txt                  ← תלויות Python
├── start.sh / start.bat              ← launchers
└── README.md / CURRENT_STATE.md      ← תיעוד מפתח
```

הסך הכל: **5,359 שורות קוד פרודקשן** (חוץ מבדיקות) —
**3,718 ב-Python** (תשעת המודולים שלמעלה) ו-**1,641 ב-Java**
(שלושת מחלקות ה-GUI). ספירת `wc -l` המלאה (כולל
`__init__.py` ו-`__main__.py` הקטנים בני 1+4 שורות) היא 5,364.

---

## 15.7 Use Case Diagram

תרשים ה-Use Case מציג את כל ה-UCs מ-15.2 כתיבות ביציות
("ellipses") מקובצות בתוך גבול המערכת (system boundary), עם
שני שחקנים חיצוניים: משתמש קצה (User) ו-System (האקטור
המתאר תהליכים אוטומטיים).

> **תרשים נדרש (Fig-12)**: Use Case Diagram מלא של המערכת
> (UC-01 עד UC-06). ראה רשומה ב-`IMAGES.md`.

---

## 15.8 רשימת Use Cases (סיכום)

| ID | שם UC | שחקן | תדירות צפויה |
|---|---|---|---|
| UC-01 | Add Torrent | User | פעמים בודדות בכל הפעלה |
| UC-02 | Pause / Resume / Cancel | User | לפי הצורך, כפול × הורדות פעילות |
| UC-03 | Show History | User | פעמים בודדות בהפעלה |
| UC-04 | Show Algorithm Stats | User | לפי הצורך |
| UC-05 | Configure Algorithms | User | לפני כל הורדה (אופציונלי) |
| UC-06 | Exchange Data with Peer | System | רציף, עשרות בשנייה |

נוסף ל-UCs אלו, פעולות *פנימיות* שאינן UCs רשמיים אך מופיעות
כתת-תהליכים: `announce` עם tracker (תקופתי), `choke_loop`
(כל 10 שניות), `keep_alive_loop` (כל 60 שניות),
`reset_stale_pieces` (כל סבב לולאה). אלו מתועדות בפרק 11.3.

---

## 15.9 תרשים UML — סקירה

תרשים ה-UML הראשי הוא תרשים מחלקות (Class Diagram) ברמת
ה-package, שמציג את כל המחלקות, את היחסים ביניהן (composition,
aggregation, dependency), ואת ה-multiplicity (1, 0..1, *).

> **תרשים נדרש (Fig-13)**: Class Diagram ברמת Package של
> ה-Engine. ראה רשומה ב-`IMAGES.md`.

> **תרשים נדרש (Fig-14)**: Class Diagram ברמת Package של
> ה-GUI. ראה רשומה ב-`IMAGES.md`.

---

## 15.10 Design Class Diagram

ה-Design Class Diagram (DCD) מציג את **המחלקות הראשיות עם
הפעולות והשדות שלהן ברמת design** — לא רק שם המחלקה, אלא
גם החתימות של המתודות הציבוריות.

מבנה דוגמה (טקסטואלית) של ה-DCD עבור הליבה:

```
┌──────────────────────────────────────┐
│         Download                     │
├──────────────────────────────────────┤
│ - id: str                            │
│ - state: DownloadState               │
│ - piece_algorithm: AlgorithmType     │
│ - peer_algorithm: AlgorithmType      │
│ - piece_manager: PieceManager        │
│ - security: SecurityManager          │
│ - _connections: Dict[str,PeerConn]   │
│ - _executor: ThreadPoolExecutor      │
├──────────────────────────────────────┤
│ + async start()                      │
│ + async pause()                      │
│ + async resume()                     │
│ + async cancel()                     │
│ + get_status() -> dict               │
│ + get_logs(since_seq) -> List[dict]  │
│ - async _download_loop()             │
│ - async _request_pieces()            │
│ - async _choke_loop()                │
│ - async _on_peer_message(conn, msg)  │
└──────────────────────────────────────┘
```

> **תרשים נדרש (Fig-15)**: Design Class Diagram מלא של 4
> המחלקות המרכזיות (Download, PieceManager, PeerConnection,
> SecurityManager). ראה רשומה ב-`IMAGES.md`.

---

## 15.11 תרשים מחלקות (כל המחלקות + יחסים)

תרשים זה מציג את **כל המחלקות במערכת** עם החצים המסמלים
יחסים:

- **Composition (יהלום מלא)** — `Download` *מכיל*
  `PieceManager`, `SecurityManager`, `ThreadPoolExecutor`.
- **Aggregation (יהלום ריק)** — `Download` *משתמש ב-*
  `TrackerClient` (אולי `None` בהתחלה).
- **Dependency (חץ דק)** — `api_server` *תלוי ב-*
  `DownloadManager`; `DownloadManager` *תלוי ב-*
  `TorrentMetadata` כקלט.
- **Inheritance** — אין במערכת בפועל (Python prefers
  composition), פרט ל-`PeerConnectionError` שיורש מ-`Exception`,
  `TorrentMetadataError` ו-`BencodeDecodeError` שגם הם
  יורשים מ-`Exception`, ו-`TorrentClientGUI extends JFrame`,
  `AlgorithmStatsDialog extends JDialog`.

> **תרשים נדרש (Fig-16)**: Class Diagram מלא של כל המערכת
> (Python + Java ביחד), עם יחסים מסוננים לקריאות. ראה
> רשומה ב-`IMAGES.md`.

---

## 15.12 תיאור המחלקות המוצעות

הסעיף הוא **המעמיק ביותר בפרק**. הוא מציג, לכל מחלקה מרכזית:
**תפקיד · קלטים · פלטים · זרימת מידע (מאיפה הקלטים, לאן הפלטים)**.

### 15.12.1 `TorrentMetadata` (`torrent_metadata.py`)

- **תפקיד**: pארסר של קובץ `.torrent` ושער הכניסה למטא-דאטה.
- **קלטים**: `torrent_path` (נתיב) או `torrent_data` (bytes).
  הקלט מגיע מ-`api_server.start_download` או מ-`main.py` (CLI).
- **פלטים**: שדות `announce`, `info_hash` (SHA-1 על ה-info),
  `pieces` (רשימה של hashים), `files`, `total_size`,
  `piece_length`.
- **זרימה**: הקלט נצרך ב-`__init__` → `_parse_metadata()` →
  `bencode.decode`; הפלטים נצרכים ע"י `DownloadManager.add_torrent`
  → `Download.__init__` → `PieceManager.__init__` (לקבלת
  ה-hashים) ו-`TrackerClient.__init__` (לקבלת ה-info_hash
  ו-announce URL).

### 15.12.2 `PieceManager` + `Piece` + `Block` (`piece_manager.py`)

- **תפקיד**: ניהול מצב ההורדה ברמת piece — מי הושלם, מי
  בתהליך, מי חסר; בחירת piece הבא; חישוב/אימות SHA-1.
- **קלטים**: בעת אתחול — מ-`TorrentMetadata` (num_pieces,
  piece_length, hashes); בזמן ריצה — מ-`PeerConnection`
  (BITFIELDים, HAVEים), ומ-`Download` (בלוקים שהתקבלו).
- **פלטים**: `select_piece_rarest_first/random` מחזירות
  piece_index ל-`Download`; `submit_block` מחזירה bool
  שהפיס שלם; `verify_piece` מחזירה bool שעובר SHA-1.
- **זרימה**: `BITFIELD` נכנס → `update_peer_pieces` מעדכן
  `_peer_frequency`. `HAVE` נכנס → `update_peer_have` מעדכן
  spot-wise. `Download._request_pieces` קוראת ל-
  `select_piece_*` ומקבלת idx → קוראת ל-`start_piece(idx)`
  שמחזירה רשימת `Block` → שולחת `REQUEST` ל-peer. `PIECE`
  חוזר → `submit_block` → אם הפיס שלם, `verify_piece`.

### 15.12.3 `PeerConnection` + `PeerMessage` + `MessageType` (`peer_connection.py`)

- **תפקיד**: ניהול חיבור TCP יחיד ל-peer; ביצוע handshake;
  parsing של הודעות; state machine של choking/interest.
- **קלטים**: `ip`, `port`, `info_hash`, `peer_id`, `num_pieces`,
  `on_message` callback. בזמן ריצה — bytes נכנסים מ-TCP.
- **פלטים**: callback `on_message(self, message)` שמועבר
  ל-`Download._on_peer_message`. שדות סטטוס: `connected`,
  `peer_choking`, `peer_pieces`, `download_rate`.
- **זרימה**: `Download._connect_peer` יוצר אובייקט →
  `await conn.connect()` עושה handshake → `start_message_loop`
  פותח task שקורא הודעות → לכל הודעה `_handle_message`
  מעדכן state ואז קורא ל-callback של `Download`.

### 15.12.4 `TrackerClient` + `Peer` + `TrackerResponse` (`tracker_client.py`)

- **תפקיד**: תקשורת HTTP/HTTPS עם ה-tracker; שליחת announces;
  parsing תגובות compact/regular.
- **קלטים**: `announce_url`, `info_hash`, `peer_id`, `port`;
  בזמן ריצה — `uploaded`, `downloaded`, `left` (מעודכנים
  מ-`Download.stats`).
- **פלטים**: `TrackerResponse` עם רשימת `Peer` (ip, port),
  `interval`, `complete`/`incomplete` counts.
- **זרימה**: `Download._download_loop` יוצר `TrackerClient`
  → קורא ל-`announce(event='started')` → ה-peers שחוזרים
  מתווספים ל-`_known_peers` → `start_periodic_announce` מפעילה
  task פנימי שעושה announce תקופתי לפי `interval`; הקריאה
  החוזרת `_on_tracker_response` מקבלת `TrackerResponse` חדש
  ומוסיפה peers נוספים.

### 15.12.5 `Download` + `DownloadStats` (`download_manager.py`)

- **תפקיד**: **המחלקה המרכזית בעולם הפנימי של ההורדה**.
  מתאמת את כל הרכיבים, מריצה את `_download_loop`, מבצעת
  choke/unchoke, מבקשת בלוקים, מטפלת בכשלי hash, ושומרת state.
- **קלטים**: `TorrentMetadata`, `download_dir`, `state_dir`,
  שני אלגוריתמים; callbacks (`on_progress`, `on_complete`,
  `on_state_change`).
- **פלטים**: API פנימי: `start/pause/resume/cancel`,
  `get_status` → dict ל-Flask, `get_logs` → רשימה לפי seq.
- **זרימה**: יחידת ה-orchestration היחידה — מקבלת אירועים
  מ-`PeerConnection.on_message`, ממנה הוראות ל-`PieceManager`
  ול-`SecurityManager`, ומחזירה state ל-Flask. ראה תרשים
  Fig-11.

### 15.12.6 `DownloadManager` (`download_manager.py`)

- **תפקיד**: **רישום של כל ההורדות הפעילות**. כל הקריאות
  מ-Flask עוברות דרכו.
- **קלטים**: `download_dir`, `state_dir` (ברירת מחדל
  `data/downloads` / `data/state`).
- **פלטים**: `Download` instances; API:
  `add_torrent(torrent, piece_algo, peer_algo, download_dir=None)`,
  `start/pause/resume/cancel_download(id)`,
  `get_download(id) -> Optional[Download]`,
  `get_download_status(id) -> Optional[dict]`,
  `get_all_status() -> List[dict]`.
- **זרימה**: `api_server.start_download` קורא ל-`add_torrent`
  → מקבל `Download` חדש → רושם בפנים → מחזיר `id` ל-Flask.

### 15.12.7 `SecurityManager` + `PeerReputation` + `SecurityEvent` (`security.py`)

- **תפקיד**: ניהול אבטחה — מוניטין peers, באנים, יומן
  אירועים. ראה פרק 12 לפירוט.
- **קלטים**: `peer_key`, `piece_index`/`description` מקריאות
  `report_*`.
- **פלטים**: `is_peer_banned(peer_key) -> bool` (משמש
  ב-`_connect_to_peers`); `_events` (משמש ב-API);
  `trust_score` (לסטטיסטיקה).
- **זרימה**: `Download._on_peer_message` קורא ל-`report_*`;
  `_connect_to_peers` בודק `is_peer_banned`.

### 15.12.8 `Bencode` (functions, `bencode.py`)

- **תפקיד**: encode/decode של פורמט bencode (פורמט הקובץ
  של `.torrent` ושל תגובות tracker).
- **קלטים ל-`decode`**: `bytes`.
- **פלטים**: עץ של `int`/`bytes`/`list`/`dict` (Python).
- **קלטים ל-`encode`**: עץ Python; **פלטים**: `bytes`.
- **שימוש**: `torrent_metadata.py` (פענוח `.torrent` וקידוד
  מחדש של ה-info לחישוב info_hash); `tracker_client.py`
  (פענוח תגובת tracker).

### 15.12.9 `TorrentClientGUI` (`TorrentClientGUI.java`)

- **תפקיד**: חלון ראשי של האפליקציה. JFrame עם `JTable`
  להורדות, toolbar, `JTextArea` ללוגים, `ScheduledExecutorService`
  לעדכון.
- **קלטים**: אירועי משתמש (`ActionEvent` מכפתורים, בחירת
  שורה ב-טבלה).
- **פלטים**: קריאות ל-`ApiService` (פעולות) ועדכוני UI
  על ה-EDT (`SwingUtilities.invokeLater`).
- **זרימה**: בכל 500ms ה-scheduler קורא ל-`refreshStatus`
  שמפעיל Thread חדש שעושה `apiService.getStatus()` ואז
  חוזר ל-EDT לעדכון הטבלה. בלחיצת כפתור — קוראת למתודה
  המתאימה (`onAddTorrent`, `onPause`, `onShowStats`...).

### 15.12.10 `ApiService` + `TorrentStatus` + `ApiException` (`ApiService.java`)

- **תפקיד**: **שכבת abstraction מעל ה-REST API**. ה-GUI
  משתמש בה במקום לקרוא ל-HTTP ישירות.
- **קלטים**: ארגומנטים לכל מתודה — `File torrentFile`,
  `String torrentId`, וכו'.
- **פלטים**: `TorrentStatus` (מודל Java של ה-JSON שמחזיר
  Flask), `JSONArray` למתודות שמחזירות אוסף.
- **זרימה**: `TorrentClientGUI` קורא לכל מתודה → המתודה
  בונה `HttpRequest` → שולחת דרך `client.send(...)` (סינכרוני)
  או דרך `sendRequest` (private helper) → parsing
  של ה-JSON ל-`TorrentStatus`.

### 15.12.11 `AlgorithmStatsDialog` + `BarChartPanel` (`AlgorithmStatsDialog.java`)

- **תפקיד**: חלון מודאלי להצגת סטטיסטיקות אלגוריתם — bar
  chart של בחירות `rarest_first`, summary של choke/unchoke,
  speed averages.
- **קלטים**: `torrentId` של ההורדה.
- **פלטים**: חלון `JDialog` מלא; אינו מחזיר ערך.
- **זרימה**: בעת פתיחה — קריאה ל-`apiService.getAlgorithmStats(id)`
  ול-`apiService.getStatsSummary()` → parsing → רישום על
  `BarChartPanel` שמצייר ב-Java2D.

---

## 15.13 סיכום הפרק

הפרק כיסה **12 תתי-סעיפים** כפי שדורש הנוהל:

- **15.1** הציג 6 Use Cases עיקריים ואת האלגוריתם המרכזי
  (`_download_loop`) בפסאודו-קוד.
- **15.2** פירט כל UC לפי תבנית סטנדרטית (שחקנים, תנאים,
  תרחיש ראשי, תרחישי חלופה).
- **15.3** סקר את 13 מבני הנתונים המרכזיים והסביר את
  הבחירה בכל אחד.
- **15.4** ניתח סיבוכיות זמן ומקום של 9 אלגוריתמים — כולל
  השוואה כמותית בין rarest-first/random ו-Tit-for-Tat/round-robin.
- **15.5** הציג את גרפי התלויות הפנימיים (Engine ו-GUI)
  ואת מנגנון IPC הבין-תהליכי.
- **15.6** הביא עץ מודולים מלא עם שורות קוד לכל קובץ
  (סך הכל ~5,360 שורות פרודקשן — 3,718 Python + 1,641 Java).
- **15.7–15.11** הגדירו ארבעה תרשימים נדרשים (Fig-12 עד
  Fig-16) ב-`IMAGES.md` עם כתוביות ופירוט מלא.
- **15.12** סיכם 11 מחלקות מרכזיות לפי תבנית
  *תפקיד · קלטים · פלטים · זרימת מידע*.

הפרק הבא (פרק 16) יעבור מהמיקוד הטכני הפנימי ל-**ממשק
המשתמש** — היררכיית המסכים, ה-screen flow, ותיאור פרטני
של כל מסך, אלמנט, וההודעות.
