# פרק 21 – קוד התוכנית — על פי סטנדרטים בליווי תיעוד

## פתיח

פרק זה מציג את **הסטנדרטים שלפיהם נכתב הקוד**, ואת קטעי
הקוד המתועדים שמייצגים את שלוש קבוצות הפונקציות הנדרשות
בנוהל ההגשה (סעיף 21, עמ' 12): **21.1 קלט**, **21.2 פלט**,
**21.3 פונקציות קריטיות/חשובות/עיקריות**.

הפרק מתאר את התקנים, ומציג קטעי קוד **קצרים בלבד (10–20
שורות)** כפי שהוגדר ב-`plan.md`; קטעי קוד מלאים של מודולים
שלמים מופיעים בנספח א'.

---

## 21.0 סטנדרטים של הקוד

### 21.0.1 Python (Engine)

הקוד עומד ב:
- **PEP 8** — סגנון פייתון רשמי (4 רווחים לכל indent, אורך
  שורה ≤ 99 תווים, snake_case לפונקציות ומשתנים, PascalCase
  למחלקות, UPPER_CASE לקבועים).
- **PEP 257** — docstrings בכל מודול, מחלקה, ופונקציה
  ציבורית. דוגמה מ-`security.py:96`:
  ```python
  def verify_piece(self, piece_data: bytes, expected_hash: bytes) -> bool:
      """Verify piece data integrity using SHA-1.

      Args:
          piece_data: The downloaded piece data.
          expected_hash: Expected 20-byte SHA-1 hash from .torrent file.

      Returns:
          True if hash matches.
      """
  ```
- **PEP 484 (Type Hints)** — חתימות מלאות בכל הפונקציות
  הציבוריות; `Optional[]`, `List[]`, `Dict[]`, `Tuple[]` מ-
  `typing`.
- **`logging`** מובנה — אין `print` בקוד הפרודקשן; הכל
  עובר דרך `logger = logging.getLogger(__name__)`.

### 21.0.2 Java (GUI)

הקוד עומד ב:
- **Oracle Code Conventions** — 4 רווחים לכל indent,
  camelCase למתודות ומשתנים, PascalCase למחלקות,
  UPPER_SNAKE_CASE לקבועים `static final`.
- **Javadoc** על כל מחלקה ציבורית ועל מתודות מורכבות. דוגמה
  מ-`ApiService.java`:
  ```java
  /**
   * Get status of all active downloads.
   *
   * @return List of TorrentStatus objects.
   * @throws IOException  If there is a network error.
   * @throws ApiException If the server returns an error.
   */
  public List<TorrentStatus> getStatus() ...
  ```
- **`java.util.logging` או `System.err`** — לא משמשים; הוצא
  המקום ב-`log(String)` מותאם של ה-GUI עם חותמת זמן.
- **Inner classes** רק לאלה שמופיעות פעם אחת
  (`ProgressBarRenderer`, `TorrentStatus`, `ApiException`,
  `BarChartPanel`).

### 21.0.3 שפת התיעוד

- **תיעוד פנימי בקוד** — באנגלית (תאימות לכלים, IDEs,
  ופלטפורמות שיתוף קוד).
- **תיעוד חיצוני** — ספר הפרויקט בעברית (כפי שדורש הנוהל).
  המקור היחיד של אמת הוא ה-Markdown ב-`book/`.

---

## 21.1 קלט (Input)

המערכת מקבלת קלט משלושה ערוצים שונים, כל אחד נכנס לפונקציית
parsing/ולידציה ייעודית:

### 21.1.1 קלט 1 — קובץ `.torrent` (bencoded binary)

הקלט הראשי. נכנס דרך `POST /torrents` (multipart) או דרך
ה-CLI. מעובד ב-`TorrentMetadata.__init__` → `_parse_metadata`.

**קטע קוד תיעודי** (`python_engine/torrent_metadata.py`):

```python
def __init__(self, torrent_path: Optional[str] = None,
             torrent_data: Optional[bytes] = None):
    """Initialize TorrentMetadata from a file path or raw bytes.

    Args:
        torrent_path: Path to a .torrent file.
        torrent_data: Raw bytes of a .torrent file.

    Raises:
        TorrentMetadataError: If the torrent data is invalid.
    """
    if torrent_path is not None:
        if not os.path.exists(torrent_path):
            raise TorrentMetadataError(f"File not found: {torrent_path}")
        with open(torrent_path, 'rb') as f:
            raw_data = f.read()
    elif torrent_data is not None:
        raw_data = torrent_data
    else:
        raise TorrentMetadataError(
            "Must provide either torrent_path or torrent_data")
    try:
        self._metadata = bencode.decode(raw_data)
    except bencode.BencodeDecodeError as e:
        raise TorrentMetadataError(f"Failed to decode torrent file: {e}")
    if not isinstance(self._metadata, dict):
        raise TorrentMetadataError("Torrent file must contain a dictionary")
    self._parse_metadata()
```

**הסבר תיעודי**: שני ערוצי קלט נתמכים (path או bytes ישירות
מה-HTTP). הקריאה ל-`bencode.decode` תזרוק `BencodeDecodeError`
אם הפורמט שגוי, ו-`_parse_metadata` ימשיך לאמת את המבנה
הפנימי. הקוד המלא של `_parse_metadata` מופיע בנספח א.1.

### 21.1.2 קלט 2 — בקשות HTTP REST

נכנסות דרך Flask routes ב-`api_server.py`. כל route מבצע
ולידציה מינימלית של פרמטרים. דוגמה (`POST /torrents`):

```python
@app.route('/torrents', methods=['POST'])
def start_download():
    manager = get_manager()
    try:
        if 'torrent_file' in request.files:
            file = request.files['torrent_file']
            torrent_data = file.read()
            torrent = TorrentMetadata(torrent_data=torrent_data)
        elif request.is_json and 'torrent_path' in request.json:
            torrent_path = request.json['torrent_path']
            torrent = TorrentMetadata(torrent_path=torrent_path)
        else:
            return jsonify({"error": "No torrent file provided"}), 400
        ...
```

הסבר: ה-route תומך גם ב-multipart וגם ב-JSON, ומחזיר
`400 Bad Request` אם לא הוגש קלט תקין. רשימת ה-endpoints
המלאה מופיעה בפרק 14.1.

### 21.1.3 קלט 3 — Bytes נכנסים מ-peers (TCP)

הקלט הרשתי הגולמי. נכנס ב-`PeerConnection._read_message`
שמבצע ולידציית אורך לפני קצירת payload:

```python
async def _read_message(self) -> Optional[PeerMessage]:
    """Read a single length-prefixed message from the peer."""
    try:
        length_bytes = await asyncio.wait_for(
            self._reader.readexactly(4),
            timeout=REQUEST_TIMEOUT * 2)
    except asyncio.TimeoutError:
        raise PeerConnectionError("Read timeout")
    except asyncio.IncompleteReadError:
        return None  # Connection closed
    length = struct.unpack('!I', length_bytes)[0]
    if length == 0:
        return PeerMessage(MessageType.KEEP_ALIVE)
    if length > MAX_MESSAGE_SIZE:
        raise PeerConnectionError(
            f"Message too large: {length} bytes (max {MAX_MESSAGE_SIZE})")
    ...
```

הקטע המלא של pארסר ההודעות מופיע בנספח א.2.

---

## 21.2 פלט (Output)

המערכת מייצרת פלט בארבעה ערוצים שונים:

### 21.2.1 פלט 1 — קבצים שהורדו (binary)

הפלט המרכזי של המערכת. נכתב ל-`download_path` שצוין בעת
ה-Add Torrent (ברירת מחדל: `data/downloads/<name>`).

**קטע קוד** (`download_manager.py:_write_piece_sync`):

```python
def _write_piece_sync(self, piece_index: int):
    """Write piece data to disk (synchronous - runs in thread pool)."""
    piece_data = self.piece_manager.get_piece_data(piece_index)
    if piece_data is None:
        return
    file_offsets = self.torrent.get_file_offset(piece_index)
    for file_path, offset_in_file, length in file_offsets:
        full_path = os.path.join(self.download_dir, file_path)
        os.makedirs(os.path.dirname(full_path) or '.', exist_ok=True)
        # Open with 'r+b' if exists else 'w+b'
        mode = 'r+b' if os.path.exists(full_path) else 'w+b'
        with open(full_path, mode) as f:
            f.seek(offset_in_file)
            piece_slice_start = sum(...)  # offset into piece_data
            f.write(piece_data[piece_slice_start:
                              piece_slice_start + length])
```

הסבר: כל piece עשוי להתפרס על פני מספר קבצים (torrent
multi-file). הפונקציה `get_file_offset` מחזירה רשימת
`(file_path, offset_in_file, length)`, וה-loop כותב את
החתיכה הנכונה לכל קובץ. הפעולה הזו רצה ב-`ThreadPoolExecutor`
כדי לא לחסום את ה-event loop.

### 21.2.2 פלט 2 — תגובות JSON ל-API

כל route ב-`api_server.py` מחזיר JSON דרך `flask.jsonify`.
דוגמת פלט של `GET /torrents/<id>` מופיעה בפרק 14.1.

### 21.2.3 פלט 3 — נתונים ל-SQLite (היסטוריה)

`save_torrent_to_db` כותב לטבלאות `torrents`,
`performance_stats`, `algorithm_stats`. ראה פרק 22 לסכמה
המלאה.

### 21.2.4 פלט 4 — לוגים

- **בקוד**: דרך `logging.getLogger(__name__)`.
- **למשתמש**: דרך `_log_buffer` (deque(maxlen=200)) +
  `/torrents/<id>/logs` polling → JTextArea ב-GUI.

---

## 21.3 פונקציות קריטיות / חשובות / עיקריות

הסעיף מציג קטעי קוד **קצרים ומתועדים** של חמש פונקציות
שמהוות את ליבת המערכת. הקוד המלא של כל אחת מופיע בנספח א'.

### 21.3.1 פונקציה קריטית #1 — `select_piece_rarest_first`

**(`python_engine/piece_manager.py:279`)**

```python
def select_piece_rarest_first(self, peer_pieces: List[bool]) -> Optional[int]:
    """Select a piece using the rarest-first algorithm.

    1. Consider only pieces that are missing AND the peer has
    2. Find the minimum frequency among those pieces
    3. Build a rarest set (all pieces with that frequency)
    4. Choose one at random from the rarest set
    """
    with self._lock:
        candidates = []
        min_freq = float('inf')
        for i in range(self.num_pieces):
            if self.pieces[i].status != PieceStatus.MISSING:
                continue
            if i >= len(peer_pieces) or not peer_pieces[i]:
                continue
            freq = self._peer_frequency.get(i, 0)
            if freq < min_freq:
                min_freq = freq
                candidates = [i]
            elif freq == min_freq:
                candidates.append(i)
        if not candidates:
            return None
        selected = random.choice(candidates)
        self.rarest_selections[selected] = (
            self.rarest_selections.get(selected, 0) + 1)
        return selected
```

**תפקיד**: לב האלגוריתם המרכזי של בחירת piece. סיבוכיות:
O(N). פירוט בפרק 15.4.1. הקוד המלא בנספח א.3.

### 21.3.2 פונקציה קריטית #2 — `verify_hash`

**(`python_engine/piece_manager.py:114`)**

```python
def verify_hash(self) -> bool:
    """Verify the piece data matches the expected SHA-1 hash."""
    actual_hash = hashlib.sha1(bytes(self._data)).digest()
    return actual_hash == self.expected_hash
```

**תפקיד**: שורת ההגנה האחרונה לפני כתיבת piece לדיסק.
חישוב SHA-1 על piece בגודל L: O(L) זמן. רץ ב-
`ThreadPoolExecutor` כדי לא לחסום את ה-event loop. ראה
פרק 12.2.2.

### 21.3.3 פונקציה קריטית #3 — `_tit_for_tat_unchoke`

**(`python_engine/download_manager.py:519`)** — קטע קצור:

```python
async def _tit_for_tat_unchoke(self):
    """1. Get all interested peers
       2. Sort by how much they uploaded to us
       3. Unchoke top K peers
       4. Optimistic unchoke: randomly unchoke one additional peer
       5. Choke all others"""
    interested_peers = [
        (key, conn) for key, conn in self._connections.items()
        if conn.connected and conn.peer_interested]
    if not interested_peers:
        return
    interested_peers.sort(key=lambda x: x[1].bytes_downloaded, reverse=True)
    to_unchoke = set()
    for i, (key, conn) in enumerate(interested_peers):
        if i < MAX_UNCHOKED_PEERS:
            to_unchoke.add(key)
    remaining = [(k, c) for k, c in interested_peers if k not in to_unchoke]
    if remaining:
        opt_key, _ = random.choice(remaining)
        to_unchoke.add(opt_key)
    # Apply choke/unchoke decisions ... (לראות נספח א.4)
```

**תפקיד**: לב האלגוריתם שמעודד reciprocity ב-swarm. סיבוכיות:
O(K log K) כאשר K ≤ 50. נקרא כל 10 שניות (`CHOKE_INTERVAL`).

### 21.3.4 פונקציה חשובה #4 — `_send_handshake` + `_receive_handshake`

**(`python_engine/peer_connection.py:181`)**

```python
async def _send_handshake(self):
    """Send the BitTorrent handshake message."""
    handshake = (
        bytes([PROTOCOL_STRING_LEN]) +
        PROTOCOL_STRING +
        b'\x00' * 8 +
        self.info_hash +
        self.our_peer_id)
    self._writer.write(handshake)
    await self._writer.drain()

async def _receive_handshake(self):
    """Receive and validate the peer's handshake."""
    data = await asyncio.wait_for(
        self._reader.readexactly(HANDSHAKE_LEN),
        timeout=CONNECTION_TIMEOUT)
    pstrlen = data[0]
    if pstrlen != PROTOCOL_STRING_LEN:
        raise PeerConnectionError(f"Invalid protocol length: {pstrlen}")
    if data[1:1+pstrlen] != PROTOCOL_STRING:
        raise PeerConnectionError("Invalid protocol string")
    received_info_hash = data[1+pstrlen+8:1+pstrlen+28]
    if received_info_hash != self.info_hash:
        raise PeerConnectionError("Info hash mismatch")
    self.remote_peer_id = data[1+pstrlen+28:1+pstrlen+48]
```

**תפקיד**: ה-handshake הוא קו ההגנה הראשון כל חיבור — בלי
התאמה ב-`info_hash` ו-`PROTOCOL_STRING`, החיבור נכשל. ראה
פרק 12.1.4.

### 21.3.5 פונקציה עיקרית #5 — `_download_loop` (התזמורת)

**(`python_engine/download_manager.py:203`)** — מבנה תמציתי:

```python
async def _download_loop(self):
    """Main download coordination loop."""
    try:
        # 1. Init tracker + initial announce
        self._tracker = TrackerClient(...)
        response = await self._tracker.announce(event='started', ...)
        for peer in response.peers:
            self._known_peers.add(peer)
        # 2. Start background coroutines
        self._choke_task = asyncio.create_task(self._choke_loop())
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        await self._tracker.start_periodic_announce(callback=...)
        asyncio.create_task(self._connect_to_peers())
        # 3. Main loop: request pieces until complete
        last_cleanup = time.time()
        while not self.piece_manager.is_complete and self.state == DownloadState.RUNNING:
            self.piece_manager.reset_stale_pieces(PIECE_REQUEST_TIMEOUT)
            await self._request_pieces()
            await asyncio.sleep(0.1)
            if time.time() - last_cleanup > PEER_CLEANUP_INTERVAL:
                self._cleanup_dead_peers()
                await self._connect_to_peers()
                last_cleanup = time.time()
            self._update_speed()
            self._tracker.update_stats(uploaded=..., downloaded=..., left=...)
        if self.piece_manager.is_complete:
            await self._complete_download()
    except asyncio.CancelledError:
        self._log("Download cancelled")
    finally:
        self._save_state()
```

**תפקיד**: ה-orchestrator שמרכז את כל ה-coroutines ומשמש
כנקודת הפיקוח של הורדה יחידה. הקוד המלא בנספח א.5.

---

## 21.4 סיכום הפרק

הפרק הציג:

- **סטנדרטים** — PEP 8/257/484 עבור Python; Oracle Code
  Conventions + Javadoc עבור Java; logging במקום print.
- **שלושת ערוצי הקלט** — קבצי `.torrent` (parsing דרך
  `TorrentMetadata`), בקשות HTTP (Flask routes), bytes
  מ-peers (`PeerConnection._read_message`).
- **ארבעת ערוצי הפלט** — קבצים שהורדו, JSON ל-API,
  רשומות SQLite, ולוגים.
- **חמש פונקציות מרכזיות מתועדות** — שתי קריטיות
  (`select_piece_rarest_first`, `verify_hash`), שתי חשובות
  (`_tit_for_tat_unchoke`, `_send/_receive_handshake`), ואחת
  עיקרית (`_download_loop`).

קטעי הקוד המלאים של חמש הפונקציות מופיעים בנספח א'
(`appendix-a-code-samples.md`).

הפרק הבא (פרק 22) מתאר את **מסד הנתונים** של המערכת:
טבלאות SQLite, סכמה כללית, ERD, ושימוש ב-state files
ב-JSON.
