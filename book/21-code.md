# 21. קוד התוכנית

## סטנדרטים

קוד ה-Python עומד ב-**PEP 8** (סגנון), **PEP 257**
(docstrings) ו-**PEP 484** (type hints). כל פונקציה
ציבורית מתועדת ב-docstring שכולל `Args` ו-`Returns`.
שימוש ב-`logging.getLogger(__name__)` במקום `print`.

קוד ה-Java עומד ב-**Oracle Code Conventions** עם
Javadoc על כל מחלקה ומתודה ציבורית מרכזית.

## 21.1 קלט

הקלט מגיע משלושה ערוצים:

**קובץ `.torrent`** — נקלט דרך `POST /torrents` (multipart)
או דרך ה-CLI ל-`python -m python_engine.main`. מעובד
ב-`TorrentMetadata.__init__`:

```python
# python_engine/torrent_metadata.py
def __init__(self, torrent_path: Optional[str] = None,
             torrent_data: Optional[bytes] = None):
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
    self._parse_metadata()
```

**בקשות REST** — נכנסות דרך Flask routes ב-`api_server.py`.
כל route מבצע ולידציה מינימלית של הפרמטרים ומחזיר תגובה
JSON.

**Bytes מ-peers ב-TCP** — נקלטים ב-`PeerConnection._read_message`
שמבצע ולידציית אורך לפני קצירת ה-payload (פרק 12.1).

## 21.2 פלט

הפלט יוצא בארבעה ערוצים:

**קבצים שהורדו** — נכתבים ל-`download_path` שצוין בעת
ה-Add Torrent. כל piece שעבר אימות SHA-1 נכתב על ידי
`_write_piece_sync` שרץ ב-`ThreadPoolExecutor`.
ה-`get_file_offset` מטפל ב-piece שמשתרע על פני מספר
קבצים (multi-file torrent).

**JSON ל-API** — כל route ב-`api_server.py` מחזיר תגובה
דרך `flask.jsonify`. דוגמאות בפרק 14.

**SQLite** — `save_torrent_to_db` כותב לשלוש טבלאות
(`torrents`, `performance_stats`, `algorithm_stats`).
ה-event log מנוהל ב-`log_event_to_db`. הסכמה בפרק 22.

**Logs** — דרך `logging.getLogger(__name__)` בקוד הפנימי,
ודרך `_log_buffer` (`deque(maxlen=200)`) שנחשף ל-GUI דרך
`/torrents/<id>/logs` polling.

## 21.3 פונקציות עיקריות

**`_download_loop`** (`download_manager.py:203`) — ה-
orchestrator המרכזי של ההורדה. מאתחל את ה-tracker, מקבל
peers ראשונים, מפעיל את ה-coroutines של choke ו-keep-
alive, ומריץ את לולאת בקשת ה-pieces עד שההורדה מסתיימת.
פסאודו-קוד מלא מופיע בפרק 15.1.

**`select_piece_rarest_first`** (`piece_manager.py:279`)
— לב האלגוריתם המרכזי. מוצא את כל ה-pieces החסרים שה-peer
מציע, מסנן לקבוצה הנדירה ביותר, ובוחר אחד אקראי מתוכה.
סיבוכיות O(N).

```python
# python_engine/piece_manager.py
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
            self.rarest_selections.get(selected, 0) + 1
        )
        return selected
```

**`Piece.verify_hash`** (`piece_manager.py:114`) — מאמת
SHA-1 לפני כתיבה לדיסק:

```python
# python_engine/piece_manager.py
def verify_hash(self) -> bool:
    """Verify the piece data matches the expected SHA-1 hash."""
    actual_hash = hashlib.sha1(bytes(self._data)).digest()
    return actual_hash == self.expected_hash
```

**`_tit_for_tat_unchoke`** (`download_manager.py:519`) —
האלגוריתם של BitTorrent הקלאסי שמעודד reciprocity. ממיין
את ה-peers שמעוניינים לפי `bytes_downloaded` יורד, פותח
choke ל-4 הטובים ביותר, ובנוסף optimistic unchoke לאחד
אקראי מהשאר.

**`_send_handshake`** / **`_receive_handshake`**
(`peer_connection.py:181`) — הקווים הראשונים של פרוטוקול
BEP-3. כל סטייה מאורך 68 בתים או מהמחרוזת
`"BitTorrent protocol"`, או אי-התאמה ב-`info_hash`,
גורמת לזריקת `PeerConnectionError` וסגירת החיבור.

קטעי קוד מלאים של חמש הפונקציות הללו מופיעים בנספח א.
