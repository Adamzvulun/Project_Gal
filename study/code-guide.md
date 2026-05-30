<div dir="rtl">

# מדריך לימוד · הקוד (~5,960 שורות)

מסמך לימוד: מה כל קובץ עושה, איפה הוא נמצא, ואיזה snippets אני **חייב** לדעת להראות בעל-פה. הסדר הוא לפי הסיכוי שהבוחן יבקש לראות (מהגבוה לנמוך).

> כלל אצבע: לכל פיסת קוד שאני מצטט, יש לי file:line מוכן. ב-presentation/transcript.md כבר רשמתי את הנקודות. פה זה ה-deep dive.

---

## מפת המודולים

### Python Engine (`python_engine/`)

| מודול | שורות | תפקיד | רמת ביקורת אצל הבוחן |
|---|---|---|---|
| `download_manager.py` | 1,311 | המתאם המרכזי. כל ההחלטות עוברות פה. | ⭐⭐⭐ גבוהה מאוד |
| `peer_connection.py` | 620 | חיבור TCP בודד + פרוטוקול BEP-3 | ⭐⭐⭐ גבוהה מאוד |
| `api_server.py` | 530 | Flask REST + גשר asyncio | ⭐⭐ גבוהה |
| `piece_manager.py` | 473 | מעקב pieces + rarest-first | ⭐⭐⭐ גבוהה מאוד |
| `tracker_client.py` | 337 | HTTP לtracker + parsing peers | ⭐⭐ בינונית |
| `security.py` | 326 | מוניטין + ולידציה | ⭐⭐ בינונית |
| `torrent_metadata.py` | 241 | פענוח .torrent + info_hash | ⭐⭐ גבוהה |
| `bencode.py` | 231 | קידוד/פענוח קנוני | ⭐⭐ גבוהה |
| `main.py` | 190 | CLI entry | ⭐ נמוכה |
| `__main__.py` | 4 | `python -m python_engine` | ⭐ נמוכה |

### Java GUI (`java_gui/src/`)

| מחלקה | תפקיד |
|---|---|
| `TorrentClientGUI.java` | חלון ראשי, טבלה, toolbar, polling. |
| `ApiService.java` | HTTP client מול ה-Python API. |
| `AlgorithmStatsDialog.java` | חלון Algorithm Statistics עם bar chart Java2D. |

---

# הקוד שאני חייב לדעת בעל-פה

## ⭐⭐⭐ Snippet 1 - Handshake (peer_connection.py:207)

הבוחן יבקש את זה כמעט בוודאות.

```python
async def _send_handshake(self):
    handshake = (
        bytes([PROTOCOL_STRING_LEN]) +     # 1 byte: 19
        PROTOCOL_STRING +                  # 19 bytes: "BitTorrent protocol"
        b'\x00' * 8 +                      # 8 bytes: reserved (extensions)
        self.info_hash +                   # 20 bytes: torrent identity
        self.our_peer_id                   # 20 bytes: our id (-PG0001-...)
    )
    self._writer.write(handshake)
    await self._writer.drain()
```

**מה לומר:** "68 בתים בסך הכל. הביט הראשון הוא אורך מחרוזת הפרוטוקול - תמיד 19. אחרי 8 בתי reserved לדגלי הרחבות, יש info_hash שהוא הזהות של ה-torrent, ו-peer_id שלי. הצד השני שולח אליי אותו פורמט - אם info_hash שלו לא תואם, אני מנתק."

**הולידציה ב-receive (peer_connection.py:232):**
```python
pstrlen = data[0]
if pstrlen != PROTOCOL_STRING_LEN:        # חייב להיות 19
    raise PeerConnectionError(...)
if pstr != PROTOCOL_STRING:               # חייב "BitTorrent protocol"
    raise PeerConnectionError(...)
if received_info_hash != self.info_hash:  # ⭐ הקו הראשון של אבטחה
    raise PeerConnectionError("Info hash mismatch")
```

---

## ⭐⭐⭐ Snippet 2 - Rarest-First (piece_manager.py:279)

לב האלגוריתם הראשון של BitTorrent.

```python
def select_piece_rarest_first(self, peer_pieces: List[bool]) -> Optional[int]:
    with self._lock:
        candidates = []
        min_freq = float('inf')

        for i in range(self.num_pieces):
            if self.pieces[i].status != PieceStatus.MISSING:
                continue                          # מתעלם מ-IN_PROGRESS/COMPLETED
            if i >= len(peer_pieces) or not peer_pieces[i]:
                continue                          # רק pieces שה-peer מחזיק

            freq = self._peer_frequency.get(i, 0)
            if freq < min_freq:
                min_freq = freq
                candidates = [i]                  # מינימום חדש - איפוס
            elif freq == min_freq:
                candidates.append(i)              # tie - מתווסף ל-set

        if not candidates:
            return None

        selected = random.choice(candidates)     # ⭐ ה-randomization
        self.rarest_selections[selected] = self.rarest_selections.get(selected, 0) + 1
        return selected
```

**מה לומר:** "שני שלבים. ראשון - לחפש את ה-freq המינימלי בין pieces שאני חסר וה-peer מחזיק. שני - להחזיק את כל ה-pieces עם אותו freq מינימלי - זה ה-tie set - ולבחור אחד באקראי. ה-`random.choice` בסוף הוא לא קוסמטיקה - בלעדיו כל ה-peers בורחים לאותו seeder ויוצרים thundering herd."

**שלוש הנקודות לזכור:**
1. `random.choice(candidates)` - הסיבה היחידה שה-swarm לא קורס בקונטנשן.
2. `_peer_frequency` - מילון O(1) מתעדכן בכל BITFIELD/HAVE.
3. `if status != MISSING: continue` - אסור לבחור piece שכבר בעבודה (אחרת duplicate work).

---

## ⭐⭐⭐ Snippet 3 - Tit-for-Tat (download_manager.py:610)

האלגוריתם השני. ארוך, אבל ה**מבנה** הוא הכל.

```python
async def _tit_for_tat_unchoke(self):
    interested_peers = [
        (key, conn) for key, conn in self._connections.items()
        if conn.connected and conn.peer_interested
    ]

    # מצב seeding - מטריקה הפוכה
    if self._is_seeding():
        await self._seed_mode_unchoke(interested_peers)
        return

    # פיצול snubbed/non-snubbed
    non_snubbed = []
    snubbed = []
    for key, conn in interested_peers:
        if conn.is_snubbed():
            snubbed.append((key, conn))
        else:
            non_snubbed.append((key, conn))

    # מיון לפי חלון נע של 20s - לא cumulative!
    non_snubbed.sort(
        key=lambda x: x[1].bytes_received_in_window(TIT_FOR_TAT_WINDOW),
        reverse=True
    )

    # top K מ-non_snubbed, fallback ל-snubbed אם אין מספיק
    to_unchoke = set()
    for key, _ in non_snubbed[:MAX_UNCHOKED_PEERS]:
        to_unchoke.add(key)
    if len(to_unchoke) < MAX_UNCHOKED_PEERS:
        for key, _ in snubbed[:MAX_UNCHOKED_PEERS - len(to_unchoke)]:
            to_unchoke.add(key)

    # Optimistic unchoke - peer אקראי מבין ה-non-snubbed שעוד לא נבחרו
    non_snubbed_remaining = [(k, c) for k, c in non_snubbed if k not in to_unchoke]
    if non_snubbed_remaining:
        opt_key, _ = random.choice(non_snubbed_remaining)
        to_unchoke.add(opt_key)

    # יישום ההחלטות
    for key, conn in self._connections.items():
        if key in to_unchoke and conn.am_choking:
            await conn.send_unchoke()
        elif key not in to_unchoke and not conn.am_choking:
            await conn.send_choke()
```

**מה לומר:** "5 שלבים. אחד - לוקח peers שhם interested. שתיים - אם אני seeder, מטריקה אחרת לגמרי. שלוש - מפצל בין snubbed (לא תורם 60s) ובריאים. ארבע - ממיין את הבריאים לפי חלון נע של 20s ולוקח top-4. חמש - peer אקראי נוסף ל-Optimistic. כל 10 שניות זה רץ."

**שלוש הנקודות החשובות:**
1. `bytes_received_in_window(TIT_FOR_TAT_WINDOW)` במקום `bytes_downloaded` - תיקון Phase 4a.
2. פיצול `non_snubbed`/`snubbed` - תיקון Phase 4b.
3. `if self._is_seeding(): await self._seed_mode_unchoke(...)` - תיקון Phase 4c.

---

## ⭐⭐⭐ Snippet 4 - Sliding Window (peer_connection.py:552)

זאת ההוכחה שתיקון Phase 4a עובד.

```python
def bytes_received_in_window(self, window: float = 20.0) -> int:
    if not self._download_samples:
        return 0
    cutoff = time.time() - window
    total = 0
    for t, b in self._download_samples:
        if t >= cutoff:
            total += b
    return total
```

**איך מתעדכן הdeque:** ב-`_handle_message` כש-PIECE מגיע, `self._download_samples.append((time.time(), len(data)))` ו-eviction של דגימות ישנות מ-30 שניות. ה-deque מוגבל ל-`DOWNLOAD_SAMPLE_RETENTION = 30`.

**מה לומר:** "deque של (timestamp, bytes). כשבא PIECE - append. כשקוראים את ה-window - sums מ-cutoff עד עכשיו. ה-deque לא משתנה בקריאה, רק ב-write."

**נקודת כאב לציין:** "בגרסה הראשונה השתמשתי במונה cumulative, ראיתי peer ששתק נשאר בראש לעד, החלפתי ל-window."

---

## ⭐⭐⭐ Snippet 5 - SHA-1 Verification (security.py:96 + piece_manager)

```python
# security.py:96
def verify_piece(self, piece_data: bytes, expected_hash: bytes) -> bool:
    actual_hash = hashlib.sha1(piece_data).digest()
    return actual_hash == expected_hash
```

**2 שורות, כל ה-trust במערכת.** Expected_hash הגיע מ-`pieces` ב-.torrent (20 בתים לכל piece). אם לא תואם → `report_hash_failure` → אחרי 3 → ban.

```python
# security.py:109 (גרסה מקוצרת)
def report_hash_failure(self, peer_key: str, piece_index: int):
    rep = self._get_reputation(peer_key)
    rep.hash_failures += 1
    if rep.should_ban:           # >= 3 hash failures
        self._ban_peer(peer_key, "Too many hash failures")
```

**הקבועים:**
```python
MAX_HASH_FAILURES_PER_PEER = 3
MAX_PROTOCOL_VIOLATIONS_PER_PEER = 5
```

---

## ⭐⭐⭐ Snippet 6 - info_hash Computation (torrent_metadata.py:100)

```python
# Compute info_hash: SHA-1 of the re-encoded info dictionary
info_encoded = bencode.encode(info)
self.info_hash = hashlib.sha1(info_encoded).digest()
```

**מה לומר:** "info_hash זאת לא איזה ערך שכתוב ב-.torrent - אני מחשב אותו. לוקח את ה-info dict, מקודד אותו מחדש ב-bencode canonical, ועליו עושה SHA-1. זה 20 בתים שהם הזהות הגלובלית של ה-torrent. הם מופיעים ב-handshake מול ה-tracker ומול כל peer."

**למה ה-canonical חשוב:** אם ה-bencode encoding שלי לא קנוני (מפתחות לא ממוינים, leading zeros), ה-hash יוצא שונה ממה שlצדים אחרים מחשבים. בדיקת `test_decode_unsorted_keys_rejected` בבnencode היא ההגנה.

---

## ⭐⭐⭐ Snippet 7 - Length-Prefix Framing (peer_connection.py:271)

```python
async def _read_message(self) -> Optional[PeerMessage]:
    length_bytes = await asyncio.wait_for(
        self._reader.readexactly(4),                  # ⭐ readexactly = framing
        timeout=REQUEST_TIMEOUT * 2
    )
    length, = struct.unpack('>I', length_bytes)       # big-endian uint32

    if length == 0:                                   # keep-alive
        return PeerMessage(MessageType.KEEP_ALIVE)
    if length > MAX_MESSAGE_SIZE:                     # ⭐ הגנת DoS
        raise PeerConnectionError(f"Message too large: {length}")

    msg_data = await self._reader.readexactly(length)  # קריאה מדויקת
    msg_id = msg_data[0]
    payload = msg_data[1:]
    return PeerMessage(MessageType(msg_id), payload)
```

**מה לומר:** "TCP הוא stream. בלי framing אני לא יודע איפה מתחילה הודעה ואיפה היא נגמרת. `readexactly(4)` חוזר רק כשיש בדיוק 4 בתים - מטפל ב-partial reads בעצמו. אחר כך struct.unpack חופף לאורך, אני מאמת מול 2MB cap (אחרת peer זדוני יכול להכריז על אורך 4GB), ואז readexactly של האורך הזה. הקסם הוא בשתי הקריאות הנפרדות."

---

## ⭐⭐ Snippet 8 - Async Bridge (api_server.py:61)

```python
def _run_async(coro, timeout=60):
    """Submit a coroutine to the persistent event loop and wait."""
    if _loop is None or not _loop.is_running():
        _start_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)
```

**מה לומר:** "Flask רץ ב-threads. כל בקשת REST היא thread נפרד. ה-engine הוא asyncio שרץ ב-loop יחיד ב-thread רקע. הגשר ביניהם הוא `run_coroutine_threadsafe` - שולח את ה-coro ל-loop השני ומקבל future. `future.result(timeout)` חוסם את ה-Flask thread עד שה-coro מסיים. הגישה היחידה של Flask ל-engine."

**איפה ה-loop נוצר:**
```python
# api_server.py סביב שורה 40-58
_loop = asyncio.new_event_loop()
_loop_thread = threading.Thread(target=_run_loop, daemon=True)
_loop_thread.start()
```

---

## ⭐⭐ Snippet 9 - Upload Path (download_manager.py:432)

הסיפור של Phase 6 - נתיב ה-upload האמיתי.

```python
async def _serve_block_request(self, conn: PeerConnection, message: PeerMessage):
    # Never serve a peer we are choking
    if conn.am_choking:
        return

    piece_idx = message.piece_index
    begin = message.block_offset
    length = message.block_length

    # Bounds + anti-abuse guards
    if piece_idx < 0 or piece_idx >= self.torrent.num_pieces:
        return
    if length <= 0 or length > BLOCK_SIZE:           # ⭐ הגנה מ-oversized request
        return
    if self.piece_manager.pieces[piece_idx].status != PieceStatus.COMPLETED:
        return                                        # אין piece - אי-אפשר לתת
    if begin < 0 or begin + length > self.torrent.get_piece_length(piece_idx):
        return                                        # מחוץ לגבולות

    # קריאה מהדיסק ב-executor (לא חוסם את ה-event loop)
    loop = asyncio.get_event_loop()
    block = await loop.run_in_executor(
        self._executor, self._read_block_sync, piece_idx, begin, length
    )
    if not block:
        return

    await conn.send_piece(piece_idx, begin, block)
    self.stats.bytes_uploaded += len(block)
```

**מה לומר:** "זה הקוד שתיקנתי ב-Phase 6 כי הוא לא היה קיים. הזרימה: REQUEST מגיע → 4 ולידציות (choking, bounds, piece status, oversized) → קריאה מהדיסק ב-executor → send_piece → bytes_uploaded עולה. בלעדיו - upload היה אפס וה-seeding mode מיין הכול לפי אפס."

---

## ⭐⭐ Snippet 10 - PIECE Handler (download_manager.py:374)

זה ה-payload של הזרימה - מה קורה כשhblock מגיע.

```python
elif message.type == MessageType.PIECE:
    piece_idx = message.piece_index
    offset = message.block_offset
    data = message.block_data

    # Duplicate guard
    piece = self.piece_manager.pieces[piece_idx]
    if piece.status == PieceStatus.COMPLETED:
        return

    is_complete = self.piece_manager.submit_block(piece_idx, offset, data)
    self.stats.bytes_downloaded += len(data)

    if is_complete:
        loop = asyncio.get_event_loop()
        verified = await loop.run_in_executor(           # SHA-1 ב-executor
            self._executor, self.piece_manager.verify_piece, piece_idx
        )
        if verified:
            self.security.report_successful_piece(peer_key, piece_idx)
            await loop.run_in_executor(                  # disk write ב-executor
                self._executor, self._write_piece_sync, piece_idx
            )
            asyncio.create_task(self._broadcast_have(piece_idx))   # fire-and-forget
            if self.piece_manager.is_complete:
                self.state = DownloadState.COMPLETED
            await self._request_from_peer(peer_key, conn)  # תן לו עבודה חדשה מיד
        else:
            self.security.report_hash_failure(peer_key, piece_idx)
            if self.security.is_peer_banned(peer_key):
                await conn.disconnect()
```

**מה לומר:** "blockא מגיע - submit_block מחזיר True אם זה ה-block האחרון של ה-piece. אז SHA-1 ו-disk write עוברים ל-executor. אם hash OK - broadcast HAVE לכולם (fire-and-forget בtask נפרד), ומיד מבקש מה-peer הזה piece חדש. אם hash נכשל - report למוניטין, אם הוא חוצה את ה-3 - ban."

---

## ⭐⭐ Snippet 11 - Compact Peers Parsing (tracker_client.py:104)

```python
@staticmethod
def _parse_compact_peers(data: bytes) -> List[Peer]:
    peers = []
    if len(data) % 6 != 0:                       # ⭐ ולידציה
        logger.warning(...)
        return peers

    for i in range(0, len(data), 6):
        ip_bytes = data[i:i + 4]                 # 4 בתי IP
        port_bytes = data[i + 4:i + 6]           # 2 בתי port
        ip = '.'.join(str(b) for b in ip_bytes)
        port = struct.unpack('!H', port_bytes)[0]
        peers.append(Peer(ip, port))
    return peers
```

**מה לומר:** "tracker מחזיר peers בשני פורמטים. ה-compact הוא 6 בתים לכל peer - 4 IP, 2 port. הולידציה הראשונה: אם len לא מתחלק ב-6, זה format מקולקל - לא מנסה לפענח. כל iteration קוראת 6 בתים, ה-IP נוסחה ב-dotted decimal, ה-port בread big-endian."

---

## ⭐ Snippet 12 - Snubbing (peer_connection.py:592)

```python
def is_snubbed(self, threshold: float = SNUB_THRESHOLD) -> bool:
    if self.peer_choking:
        return False                  # choking לא snubbing
    if self._last_request_time <= 0:
        return False                  # לא ביקשתי - אי אפשר לסנובן
    last_signal = max(self._last_piece_time, self._connect_time)
    if last_signal <= 0:
        return False
    return (time.time() - last_signal) > threshold   # > 60s שקט = snubbed
```

**מה לומר:** "3 תנאים. הוא לא choking אותי (אז שקט הוא באחריותו), ביקשתי ממנו לפחות פעם אחת, ועברו 60 שניות בלי PIECE. ה-connect_time fallback מגן על peer שhרגע הצטרף - הוא לא ייסנובן לפני שהיה לו זמן לענות."

---

## ⭐ Snippet 13 - Bencode encode/decode (bencode.py)

האלגוריתם בעצמו פשוט, אבל כל פסקה מהוויקיפדיה של הפרוטוקול. הנקודות החשובות:

**Encoding integer:**
```python
def _encode_int(value: int) -> bytes:
    return b'i' + str(value).encode('ascii') + b'e'   # i42e
```

**Encoding dict (חשוב - canonical):**
```python
def _encode_dict(value: dict) -> bytes:
    result = b'd'
    sorted_keys = sorted(value.keys(), key=lambda k: k if isinstance(k, bytes) else k.encode('utf-8'))
    for key in sorted_keys:                            # ⭐ מיון חיוני
        result += _encode_bytes(key.encode('utf-8') if isinstance(key, str) else key)
        result += encode(value[key])
    result += b'e'
    return result
```

**Decoding integer (חשוב - ולידציה):**
```python
def _decode_int(data: bytes) -> Tuple[int, bytes]:
    end_idx = data.index(b'e')
    num_str = data[1:end_idx]

    if len(num_str) > 1 and num_str[0:1] == b'0':       # ⭐ leading zero
        raise BencodeDecodeError(...)
    if num_str == b'-0':                                 # ⭐ negative zero
        raise BencodeDecodeError(...)

    return int(num_str), data[end_idx + 1:]
```

**הולידציה החשובה ביותר:**
```python
def _decode_dict(data: bytes) -> Tuple[dict, bytes]:
    ...
    while data and data[0:1] != b'e':
        key, data = _decode_bytes(data)
        value, data = _decode_next(data)
        if prev_key is not None and key <= prev_key:
            raise BencodeDecodeError(f"Dictionary keys not in sorted order")
        prev_key = key
        result[key] = value
    ...
```

**מה לומר:** "כל פסקה ב-canonical bencode חשובה כי info_hash מחושב על ה-encoding. leading zeros, negative zero, ומיון מפתחות - אם משנה אחד מהם, ה-hash שונה וכל ה-handshake שבור."

---

# מה כל קובץ עושה (סקירת רוחב)

## `bencode.py` (231 שורות)

**תפקיד:** קידוד ופענוח של פורמט bencode (BitTorrent's serialization).

**Public API:**
- `encode(data) -> bytes` - מקודד int/bytes/str/list/dict
- `decode(data) -> Any` - מפענח bytes ל-Python objects
- `decode_partial(data) -> (value, remaining)` - לזרמים

**ולידציות (קריטיות):**
- מפתחות dict ממוינים
- אין leading zeros ב-int
- אין `-0`
- string length תואם ל-data בפועל

**Exceptions:** `BencodeEncodeError`, `BencodeDecodeError`.

---

## `torrent_metadata.py` (241 שורות)

**תפקיד:** פענוח .torrent + חישוב info_hash.

**מחלקה ראשית:** `TorrentMetadata(torrent_path=... | torrent_data=...)`

**שדות מרכזיים:**
- `announce: str` - URL של ה-tracker
- `announce_list: List[List[str]]` - tracker tiers
- `piece_length: int` - בדרך כלל 256KB
- `pieces: List[bytes]` - hash של 20 בתים לכל piece
- `info_hash: bytes` - **SHA-1 של ה-info dict המקודד מחדש**
- `files: List[FileInfo]` - תמיכה במולטי-קובץ
- `total_size: int`, `num_pieces: int`

**מתודות חשובות:**
- `get_piece_length(idx)` - ה-piece האחרון יכול להיות קצר יותר
- `get_file_offset(piece_idx)` - לטורנט מולטי-קובץ, ממפה piece ל-`[(path, offset, length)]`

---

## `tracker_client.py` (337 שורות)

**תפקיד:** תקשורת HTTP מול tracker.

**מחלקה ראשית:** `TrackerClient(announce_url, info_hash, peer_id, port=6881)`

**מתודות:**
- `announce(event=...)` - HTTP GET, מחזיר `TrackerResponse`
- `start_periodic_announce(callback)` - background task
- `completed()`, `stop()` - אירועים
- `update_stats(uploaded, downloaded, left)` - לאnnounce הבא

**`TrackerResponse`:**
- `peers: List[Peer]` - תומך compact (6 בתים) ו-dict format
- `interval: int` - re-announce interval

**קבוע חשוב:** `PEER_ID_PREFIX = b'-PG0001-'` (peer_id מתחיל בזה).

---

## `peer_connection.py` (620 שורות) ⭐

**תפקיד:** חיבור TCP בודד + Peer Wire Protocol.

**מחלקה ראשית:** `PeerConnection(ip, port, info_hash, peer_id, num_pieces, on_message=...)`

**State machine:**
- `am_choking`, `am_interested` - מה אני מהציע ל-peer
- `peer_choking`, `peer_interested` - מה ה-peer מהציע לי
- `peer_pieces: List[bool]` - bitfield של ה-peer

**זרימה ראשית:**
- `connect()` - TCP + handshake
- `start_message_loop()` - asyncio task ל-`_message_loop`
- `_message_loop()` - לולאה אינסופית של `_read_message` → `_handle_message`

**שליחת הודעות:**
- `send_interested()`, `send_choke()`, `send_unchoke()`, `send_have()`, `send_bitfield()`
- `send_request(piece_index, begin, length)`
- `send_piece(piece_index, begin, block_data)` - ⭐ עכשיו באמת בשימוש
- `send_keep_alive()`

**מטריקות:**
- `bytes_received_in_window(20.0)` - לתdownload tit-for-tat
- `bytes_sent_in_window(20.0)` - לseeding mode
- `is_snubbed(60.0)` - לפיצול ב-tit-for-tat
- `download_rate`, `bytes_downloaded`, `bytes_uploaded`

**קבועים:**
```python
BLOCK_SIZE = 16384                      # 16KB - גודל block סטנדרטי
MAX_PENDING_REQUESTS = 50               # depth של pipeline
MAX_MESSAGE_SIZE = 2 * 1024 * 1024      # 2MB - הגנת DoS
HANDSHAKE_LEN = 68                      # 1+19+8+20+20
SNUB_THRESHOLD = 60.0
```

---

## `piece_manager.py` (473 שורות) ⭐

**תפקיד:** מעקב pieces/blocks + אלגוריתם בחירה.

**מחלקות:**
- `Block(piece_index, offset, length)` - 16KB single block
- `Piece(index, length, expected_hash)` - בדרך כלל 256KB = 16 blocks
- `PieceManager(num_pieces, piece_length, total_size, piece_hashes)` - הכל ביחד

**`Piece` API:**
- `status: PieceStatus` - MISSING/IN_PROGRESS/COMPLETED
- `submit_block(offset, data) -> bool` - True אם piece שלם
- `verify_hash() -> bool` - SHA-1 check
- `reset()` - חזרה ל-MISSING (אם hash נכשל)

**`PieceManager` API:**
- `select_piece_rarest_first(peer_pieces)` ⭐
- `select_piece_random(peer_pieces)` - baseline
- `update_peer_pieces(peer_key, pieces)` - על BITFIELD
- `update_peer_have(peer_key, piece_idx)` - על HAVE
- `remove_peer(peer_key)` - cleanup (מפחית counters)
- `start_piece(idx) -> List[Block]` - מסמן IN_PROGRESS
- `reset_stale_pieces(timeout)` - timeout של pieces תקועים
- `submit_block(piece_idx, offset, data)`
- `verify_piece(piece_idx) -> bool`
- `clear_peer_requests(peer_key)` - על choke/disconnect
- `find_in_progress_piece(...)` - endgame mode

**מבני נתונים פנימיים:**
```python
self._peer_frequency: Dict[int, int]      # כמה peers מחזיקים piece i
self._peer_pieces: Dict[str, Set[int]]     # אילו pieces יש לכל peer
self._piece_start_times: Dict[int, float]  # מתי piece נכנס ל-IN_PROGRESS
self.rarest_selections: Dict[int, int]    # סטטיסטיקות לחלון Algorithm Stats
```

---

## `download_manager.py` (1,311 שורות) ⭐⭐⭐

**תפקיד:** המתאם המרכזי. כל החלטה עוברת פה.

**מחלקה ראשית:** `Download(torrent, download_dir, state_dir, piece_algo, peer_algo)`

**State:**
- `state: DownloadState` - QUEUED/RUNNING/PAUSED/COMPLETED/SEEDING/CANCELLED/ERROR
- `stats: DownloadStats` - מהירות, bytes, peer counts
- `piece_manager`, `security` - subsystems
- `_connections: Dict[str, PeerConnection]` - חיבורי peers פעילים
- `_known_peers: Set[Peer]` - כל ה-peers שדווחנו עליהם
- `_peer_piece: Dict[str, int]` - לכל peer, ה-piece שהוא עובד עליו
- `_executor: ThreadPoolExecutor(2)` - ל-hash + disk

**Loops (asyncio tasks):**
- `_download_loop()` - הראשי: tracker → connect → request loop
- `_choke_loop()` - כל 10s, מפעיל את `_tit_for_tat_unchoke`
- `_keep_alive_loop()` - כל 60s, שולח keep-alive
- `_periodic_announce_loop()` - לפי interval של tracker
- `_message_loop` per peer (ב-PeerConnection)

**מתודות מרכזיות:**
- `start()`, `pause()`, `resume()`, `cancel()` - state management
- `_connect_to_peers()` - חיבור concurrent ל-known peers
- `_connect_peer(peer)` - TCP + handshake + start_message_loop
- `_on_peer_message(conn, message)` ⭐ - הטיפול ב-BITFIELD/HAVE/UNCHOKE/CHOKE/PIECE/REQUEST
- `_request_pieces()` - לולאה על peers unchoked
- `_request_from_peer(peer_key, conn)` ⭐ - אסטרטגיית request לpeer יחיד
- `_serve_block_request(...)` ⭐ - upload path
- `_tit_for_tat_unchoke()` ⭐
- `_seed_mode_unchoke(interested_peers)`
- `_maybe_enter_seeding()` - COMPLETED → SEEDING
- `_broadcast_have(piece_idx)` - HAVE לכל peer (concurrent)
- `_write_piece_sync()` / `_write_piece()` - disk write (executor)
- `_complete_download()` - הגעה לסיום
- `_save_state()` / `from_state_file()` - persistence

**`DownloadManager` (wrapper):**
- `downloads: Dict[str, Download]`
- `add_torrent(...)`, `start/pause/resume/cancel/remove_download(id)`
- `restore_state()` - על startup, סורק data/state/*.json

**Enums:**
- `DownloadState`: QUEUED, RUNNING, PAUSED, COMPLETED, SEEDING, CANCELLED, ERROR
- `AlgorithmType`: RAREST_FIRST, RANDOM, TIT_FOR_TAT, ROUND_ROBIN

**קבועים:**
```python
CHOKE_INTERVAL = 10                  # שניות בין מחזורי tit-for-tat
MAX_UNCHOKED_PEERS = 4               # top-K
MAX_CONNECTIONS = 50                 # מספר peers מקסימלי
KEEP_ALIVE_INTERVAL = 60
PIECE_REQUEST_TIMEOUT = 30
TIT_FOR_TAT_WINDOW = 20.0
```

---

## `security.py` (326 שורות)

**תפקיד:** מוניטין + ולידציה + לוג אבטחה.

**מחלקות:**
- `PeerReputation` - dataclass: hash_failures, protocol_violations, successful_pieces, trust_score, last_violation
- `SecurityManager` - מנהל את כל ה-reputations
- `SecurityEvent` - אירוע לוג

**API:**
- `verify_piece(data, expected_hash) -> bool` ⭐ - SHA-1
- `report_hash_failure(peer_key, piece_index)` - אחרי 3 → ban
- `report_protocol_violation(peer_key, description)` - אחרי 5 → ban
- `report_successful_piece(peer_key, piece_index)`
- `report_timeout(peer_key)`, `report_invalid_message(...)`
- `validate_message_length(peer_key, length)` - < 0 או > 2MB?
- `validate_piece_index(peer_key, idx, num_pieces)`
- `is_peer_banned(peer_key) -> bool`

**קבועים:**
```python
MAX_HASH_FAILURES_PER_PEER = 3
MAX_PROTOCOL_VIOLATIONS_PER_PEER = 5
MAX_MESSAGE_LENGTH = 2 * 1024 * 1024
```

---

## `api_server.py` (530 שורות) ⭐⭐

**תפקיד:** Flask REST API + גשר asyncio.

**Globals:**
- `_loop` - asyncio event loop רץ ב-thread רקע
- `_loop_thread` - daemon thread
- `_manager` - DownloadManager singleton

**Helpers:**
- `_run_async(coro, timeout)` ⭐ - הגשר Flask → asyncio
- `_start_event_loop()` - מקים את ה-loop ב-thread רקע

**Endpoints:** (15 נקודות קצה)
- `POST /torrents` - multipart upload + algorithms + download_dir
- `GET /torrents` - כל ה-statuses
- `GET /torrents/<id>` - status בודד
- `POST /torrents/<id>/pause` / `resume` / `cancel`
- `DELETE /torrents/<id>` - הסרת שורה (לא מוחק קובץ)
- `GET /torrents/<id>/logs?since=N` - polling incrementally
- `GET /history`, `DELETE /history`
- `GET /events?limit=N`
- `GET /algorithm-stats/<id>`
- `GET /stats-summary`
- `GET /health`

**SQLite:** ב-`data/history.db`, טבלאות: torrents, performance_stats, algorithm_stats, events.

---

## `main.py` (190 שורות)

**תפקיד:** CLI entry point.

```bash
python -m python_engine path/to/file.torrent -o ./downloads \
  --piece-algorithm rarest_first --peer-algorithm tit_for_tat -v
```

מציג progress bar בזמן אמת + מטפל ב-Ctrl+C דרך asyncio signal handlers.

---

## Java GUI - 3 מחלקות

### `TorrentClientGUI.java` (~900 שורות)

- חלון ראשי עם JTable של הורדות
- Toolbar: Add / Pause / Resume / Cancel / Delete / History / Algorithm Stats
- Log area בתחתית
- `ScheduledExecutorService` polls כל 500ms
- `logSeqTracker` - מפת sequence numbers per torrent
- `previousStates` - לזיהוי מעבר ל-COMPLETED → popup

### `ApiService.java` (~400 שורות)

- HTTP client דרך `java.net.http.HttpClient`
- `startDownload(File, pieceAlgo, peerAlgo, downloadDir)`
- `getStatus()`, `pause/resume/cancel/remove(id)`
- `getHistory()`, `getLogs(id, sinceSeq)`
- Inner class `TorrentStatus` עם `fromJson()` factory

### `AlgorithmStatsDialog.java` (~400 שורות)

- JDialog עם 2 tabs: Piece Selection, General Statistics
- Bar chart ב-Java2D (ידני, לא ספרייה)
- Fetches מ-`/algorithm-stats/<id>`

---

# שאלות סבירות + לאן לקפוץ

| שאלה | קוד להראות |
|---|---|
| "תראה לי את ה-handshake" | `peer_connection.py:207` |
| "איך rarest-first עובד?" | `piece_manager.py:279` |
| "איך tit-for-tat?" | `download_manager.py:610` |
| "איפה האימות SHA-1?" | `security.py:96` + `piece_manager.py:verify_hash` |
| "איך מחשבים info_hash?" | `torrent_metadata.py:100` |
| "איפה ה-framing?" | `peer_connection.py:271` (`_read_message`) |
| "איך upload עובד?" | `download_manager.py:432` (`_serve_block_request`) |
| "איך ה-GUI מדבר עם ה-engine?" | `api_server.py:61` (`_run_async`) |
| "איפה ה-sliding window?" | `peer_connection.py:552` |
| "איפה ה-snubbing?" | `peer_connection.py:592` + `download_manager.py:651` |
| "איך אתה יודע ש-tcp הוא stream?" | `peer_connection.py:271` `readexactly` |
| "איפה ה-Optimistic Unchoke?" | `download_manager.py:687-693` |

---

# מילים שאני חייב לדעת לבטא (לא להתבלבל)

| מונח | הגייה / שימוש |
|---|---|
| BEP-3 | "בי-אי-פי-3" - BitTorrent Enhancement Proposal #3 - הספציפיקציה הקלאסית |
| bencode | "בן-קוד" - לא "ביי-אנקוד" |
| handshake | 68 בתים, לא להזכיר 67 או 69 |
| `info_hash` | תמיד SHA-1, 20 בתים |
| `piece` | רגיל 256KB - 16 blocks |
| `block` | רגיל 16KB - הגודל הסטנדרטי |
| `pstrlen` | האורך של מחרוזת הפרוטוקול - תמיד 19 |
| Tit-for-Tat | טיט-פור-טאט, מילה במילה |
| Snubbing | סנאבינג - peer ש-unchoked אבל לא שולח |
| Optimistic Unchoke | בחירה אקראית של peer ל-unchoke (לא חישובית) |
| Endgame mode | בסוף ההורדה - לבקש pieces חופפים מכמה peers |
| Sliding window | 20 שניות אצלי, ל-tit-for-tat |
| SHAttered | מתקפת collision על SHA-1, פורסמה ב-2017 |
| BitTyrant | NSDI 2007 - מאמר על ניצול tit-for-tat |
| BEP-52 | BitTorrent v2 - SHA-256 + Merkle Trees |

</div>
