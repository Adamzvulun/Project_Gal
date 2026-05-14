# נספח א' – קטעי קוד מרכזיים

נספח זה מציג את קטעי הקוד החשובים והמרכזיים ביותר
בפרויקט, בסדר עדיפות יורד. כל קטע כולל את נתיב הקובץ
המקורי ותיאור קצר של תפקידו.

---

## א.1 — `Download._download_loop` (האלגוריתם הראשי)

**קובץ**: `python_engine/download_manager.py`. ה-orchestrator
המרכזי של ההורדה — מתאם בין tracker, peers, piece
requests, ו-stats. הוא רץ ב-asyncio event loop ומפעיל
כ-55 קואורוטינות במקביל עבור הורדה אחת עם 50 peers.

```python
async def _download_loop(self):
    """Main download coordination loop."""
    try:
        # Initialize tracker
        self._tracker = TrackerClient(
            announce_url=self.torrent.announce,
            info_hash=self.torrent.info_hash,
            peer_id=self.peer_id,
            port=6881)
        self._tracker.left = self.torrent.total_size

        # Initial announce
        self._log(f"Contacting tracker: {self.torrent.announce}")
        response = await self._tracker.announce(
            event='started', left=self.torrent.total_size)
        for peer in response.peers:
            self._known_peers.add(peer)
        self.stats.total_peers_seen = len(self._known_peers)
        self._log(f"Tracker responded: {len(response.peers)} peers found")

        # Start background coroutines
        self._choke_task = asyncio.create_task(self._choke_loop())
        self._keep_alive_task = asyncio.create_task(
            self._keep_alive_loop())
        await self._tracker.start_periodic_announce(
            callback=self._on_tracker_response)
        asyncio.create_task(self._connect_to_peers())

        # Main piece-request loop
        last_cleanup = time.time()
        while (not self.piece_manager.is_complete
               and self.state == DownloadState.RUNNING):
            self.piece_manager.reset_stale_pieces(PIECE_REQUEST_TIMEOUT)
            await self._request_pieces()
            await asyncio.sleep(0.1)
            now = time.time()
            if now - last_cleanup > PEER_CLEANUP_INTERVAL:
                self._cleanup_dead_peers()
                await self._connect_to_peers()
                last_cleanup = now
            self._update_speed()
            self._tracker.update_stats(
                uploaded=self.stats.bytes_uploaded,
                downloaded=self.stats.bytes_downloaded,
                left=self.piece_manager.bytes_remaining)

        if self.piece_manager.is_complete:
            await self._complete_download()
    except asyncio.CancelledError:
        self._log("Download cancelled")
    except Exception as e:
        self._log(f"Download error: {e}")
        logger.error(f"Download error: {e}", exc_info=True)
        self.state = DownloadState.ERROR
    finally:
        self._save_state()
```

---

## א.2 — `select_piece_rarest_first` (בחירת piece)

**קובץ**: `python_engine/piece_manager.py`. לב האלגוריתם
המרכזי. עוברת על כל ה-pieces החסרים שה-peer מציע, מוצאת
את אלה עם המינימום של `_peer_frequency`, ובוחרת אחד
אקראית מהקבוצה הנדירה.

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

---

## א.3 — `_tit_for_tat_unchoke` (אלגוריתם choke/unchoke)

**קובץ**: `python_engine/download_manager.py`. האלגוריתם
של BitTorrent הקלאסי שמעודד reciprocity. רץ כל 10 שניות.

```python
async def _tit_for_tat_unchoke(self):
    """1. Get all interested peers
       2. Sort by how much they uploaded to us
       3. Unchoke top K peers (K=4)
       4. Optimistic unchoke: randomly unchoke one additional peer
       5. Choke all others"""
    interested_peers = [
        (key, conn) for key, conn in self._connections.items()
        if conn.connected and conn.peer_interested]
    if not interested_peers:
        return

    # Sort by download rate from this peer (how much they
    # contribute to us)
    interested_peers.sort(
        key=lambda x: x[1].bytes_downloaded, reverse=True)

    # Select top K
    to_unchoke = set()
    for i, (key, conn) in enumerate(interested_peers):
        if i < MAX_UNCHOKED_PEERS:           # K = 4
            to_unchoke.add(key)

    # Optimistic unchoke: pick one random peer not in top K
    remaining = [
        (key, conn) for key, conn in interested_peers
        if key not in to_unchoke]
    if remaining:
        import random
        opt_key, _ = random.choice(remaining)
        to_unchoke.add(opt_key)

    # Apply choke/unchoke decisions
    for key, conn in self._connections.items():
        if not conn.connected:
            continue
        if key in to_unchoke and conn.am_choking:
            await conn.send_unchoke()
            self.stats.unchoke_count += 1
        elif key not in to_unchoke and not conn.am_choking:
            await conn.send_choke()
            self.stats.choke_count += 1
```

---

## א.4 — `Piece.verify_hash` ו-`Piece.submit_block`

**קובץ**: `python_engine/piece_manager.py`. אימות SHA-1
לפני כתיבה לדיסק. שני המתודות הם החלק האבטחתי הקריטי
ביותר במערכת.

```python
class Piece:
    BLOCK_SIZE = 16384  # 16 KB

    def __init__(self, index: int, length: int, expected_hash: bytes):
        self.index = index
        self.length = length
        self.expected_hash = expected_hash
        self.status = PieceStatus.MISSING
        self.blocks: List[Block] = []
        self._data = bytearray(length)
        # Create blocks
        offset = 0
        while offset < length:
            block_len = min(self.BLOCK_SIZE, length - offset)
            self.blocks.append(Block(index, offset, block_len))
            offset += block_len

    def submit_block(self, offset: int, data: bytes) -> bool:
        """Submit a received block. Returns True if piece complete."""
        for block in self.blocks:
            if block.offset == offset:
                block.data = data
                block.received = True
                self._data[offset:offset + len(data)] = data
                break
        return self.is_complete

    def verify_hash(self) -> bool:
        """Verify the piece data matches the expected SHA-1 hash."""
        actual_hash = hashlib.sha1(bytes(self._data)).digest()
        return actual_hash == self.expected_hash
```

---

## א.5 — `PeerConnection._send_handshake` + `_receive_handshake`

**קובץ**: `python_engine/peer_connection.py`. ה-handshake
של BEP-3 — קו ההגנה הראשון של כל חיבור. 68 בתים בדיוק.

```python
PROTOCOL_STRING = b'BitTorrent protocol'
PROTOCOL_STRING_LEN = len(PROTOCOL_STRING)
HANDSHAKE_LEN = 1 + PROTOCOL_STRING_LEN + 8 + 20 + 20  # 68 bytes

async def _send_handshake(self):
    """Send the BitTorrent handshake message."""
    handshake = (
        bytes([PROTOCOL_STRING_LEN]) +
        PROTOCOL_STRING +
        b'\x00' * 8 +                # Reserved bytes
        self.info_hash +
        self.our_peer_id
    )
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
    if data[1:1 + pstrlen] != PROTOCOL_STRING:
        raise PeerConnectionError("Invalid protocol string")
    received_info_hash = data[1 + pstrlen + 8: 1 + pstrlen + 28]
    if received_info_hash != self.info_hash:
        raise PeerConnectionError("Info hash mismatch during handshake")
    self.remote_peer_id = data[1 + pstrlen + 28: 1 + pstrlen + 48]
```

---

## א.6 — `PeerConnection._read_message` + `_handle_message`

**קובץ**: `python_engine/peer_connection.py`. parser הודעות
Peer Wire Protocol עם ולידציית אורך וטיפול ב-state
machine.

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
        return None
    length = struct.unpack('!I', length_bytes)[0]
    if length == 0:
        return PeerMessage(MessageType.KEEP_ALIVE)
    if length > MAX_MESSAGE_SIZE:           # 2 MB
        raise PeerConnectionError(
            f"Message too large: {length} bytes (max {MAX_MESSAGE_SIZE})")
    payload = await asyncio.wait_for(
        self._reader.readexactly(length),
        timeout=REQUEST_TIMEOUT)
    msg_id = payload[0]
    msg_payload = payload[1:]
    try:
        msg_type = MessageType(msg_id)
    except ValueError:
        logger.warning(f"Unknown message type {msg_id}")
        return None
    return PeerMessage(msg_type, msg_payload)


async def _handle_message(self, message: PeerMessage):
    """Process a received message and update state."""
    if message.type == MessageType.CHOKE:
        self.peer_choking = True
        self._pending_requests = 0
    elif message.type == MessageType.UNCHOKE:
        self.peer_choking = False
    elif message.type == MessageType.INTERESTED:
        self.peer_interested = True
    elif message.type == MessageType.NOT_INTERESTED:
        self.peer_interested = False
    elif message.type == MessageType.HAVE:
        piece_index = message.piece_index
        if 0 <= piece_index < self.num_pieces:
            self.peer_pieces[piece_index] = True
        else:
            raise PeerConnectionError(
                f"Invalid piece index in HAVE: {piece_index}")
    elif message.type == MessageType.BITFIELD:
        self._parse_bitfield(message.bitfield_data)
    elif message.type == MessageType.PIECE:
        data_len = len(message.block_data) if message.block_data else 0
        self.bytes_downloaded += data_len
        self._pending_requests = max(0, self._pending_requests - 1)
    if self.on_message:
        await self.on_message(self, message)
```

---

## א.7 — `Download._on_peer_message` (זרימת קבלת PIECE)

**קובץ**: `python_engine/download_manager.py`. ה-callback
שמופעל לכל הודעה מ-peer. הזרימה של קבלת PIECE היא
המרכזית — כוללת אימות SHA-1 ב-thread pool, כתיבה לדיסק,
ו-broadcast HAVE.

```python
async def _on_peer_message(self, conn: PeerConnection, message: PeerMessage):
    """Handle messages from peers."""
    peer_key = f"{conn.ip}:{conn.port}"

    if message.type == MessageType.BITFIELD:
        self.piece_manager.update_peer_pieces(peer_key, conn.peer_pieces)
        if self._peer_has_needed_pieces(conn):
            await conn.send_interested()

    elif message.type == MessageType.HAVE:
        self.piece_manager.update_peer_have(peer_key, message.piece_index)
        if not self.piece_manager.has_piece(message.piece_index) \
                and not conn.am_interested:
            await conn.send_interested()

    elif message.type == MessageType.UNCHOKE:
        await self._request_from_peer(peer_key, conn)

    elif message.type == MessageType.PIECE:
        piece_idx = message.piece_index
        offset = message.block_offset
        data = message.block_data
        if data is None: return
        # Skip if piece already completed (dedup from another peer)
        if self.piece_manager.pieces[piece_idx].status == PieceStatus.COMPLETED:
            return

        is_complete = self.piece_manager.submit_block(piece_idx, offset, data)
        self.stats.bytes_downloaded += len(data)

        if is_complete:
            # Run hash verification in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            verified = await loop.run_in_executor(
                self._executor, self.piece_manager.verify_piece, piece_idx)
            if verified:
                self.security.report_successful_piece(peer_key, piece_idx)
                await loop.run_in_executor(
                    self._executor, self._write_piece_sync, piece_idx)
                self._log(f"Piece {piece_idx} verified OK")
                asyncio.create_task(self._broadcast_have(piece_idx))
                await self._request_from_peer(peer_key, conn)
            else:
                self._log(f"Piece {piece_idx} HASH FAILED from {peer_key}")
                self.security.report_hash_failure(peer_key, piece_idx)
                if self.security.is_peer_banned(peer_key):
                    self._log(f"Banned peer {peer_key}")
                    await conn.disconnect()
```

---

## א.8 — `SecurityManager` ו-`PeerReputation`

**קובץ**: `python_engine/security.py`. מערכת המוניטין
שחוסמת peers זדוניים אחרי 3 שגיאות hash או 5 הפרות
פרוטוקול.

```python
MAX_HASH_FAILURES_PER_PEER = 3
MAX_PROTOCOL_VIOLATIONS_PER_PEER = 5

class PeerReputation:
    def __init__(self, peer_key: str):
        self.peer_key = peer_key
        self.hash_failures = 0
        self.protocol_violations = 0
        self.invalid_messages = 0
        self.successful_pieces = 0
        self.first_seen = time.time()
        self.last_violation = 0
        self.banned = False
        self.ban_reason: Optional[str] = None

    @property
    def should_ban(self) -> bool:
        if self.hash_failures >= MAX_HASH_FAILURES_PER_PEER:
            return True
        if self.protocol_violations >= MAX_PROTOCOL_VIOLATIONS_PER_PEER:
            return True
        return False

    @property
    def trust_score(self) -> float:
        """Score from 0.0 (untrustworthy) to 1.0 (trustworthy)."""
        total = (self.successful_pieces + self.hash_failures +
                 self.protocol_violations + self.invalid_messages)
        if total == 0:
            return 0.5
        good = self.successful_pieces
        bad = (self.hash_failures * 3 + self.protocol_violations * 2 +
               self.invalid_messages)
        return max(0.0, min(1.0, good / (good + bad)))


class SecurityManager:
    def __init__(self):
        self._peer_reputations: Dict[str, PeerReputation] = {}
        self._banned_peers: Set[str] = set()
        self._events: List[SecurityEvent] = []

    def report_hash_failure(self, peer_key: str, piece_index: int):
        rep = self._get_reputation(peer_key)
        rep.hash_failures += 1
        rep.last_violation = time.time()
        if rep.should_ban:
            self._ban_peer(peer_key, "Too many hash failures")

    def is_peer_banned(self, peer_key: str) -> bool:
        return peer_key in self._banned_peers

    def _ban_peer(self, peer_key: str, reason: str):
        rep = self._get_reputation(peer_key)
        rep.banned = True
        rep.ban_reason = reason
        self._banned_peers.add(peer_key)
        logger.warning(f"Peer {peer_key} banned: {reason}")
```

---

## א.9 — `TrackerClient.announce` (תקשורת עם tracker)

**קובץ**: `python_engine/tracker_client.py`. שליחת announce
ל-tracker עם פרסור Bencode של התגובה.

```python
async def announce(self, event: Optional[str] = None,
                   uploaded: Optional[int] = None,
                   downloaded: Optional[int] = None,
                   left: Optional[int] = None) -> TrackerResponse:
    """Send an announce request to the tracker."""
    params = {
        'info_hash': self.info_hash,
        'peer_id': self.peer_id,
        'port': self.port,
        'uploaded': uploaded if uploaded is not None else self.uploaded,
        'downloaded': downloaded if downloaded is not None else self.downloaded,
        'left': left if left is not None else self.left,
        'compact': 1,
    }
    if event:
        params['event'] = event
    if self._tracker_id:
        params['trackerid'] = self._tracker_id

    url = self._build_announce_url(params)
    session = await self._get_session()
    async with session.get(url) as resp:
        if resp.status != 200:
            raise TrackerError(f"Tracker returned HTTP {resp.status}")
        raw = await resp.read()
    decoded = bencode.decode(raw)
    response = TrackerResponse(decoded)
    if response.failure_reason:
        raise TrackerError(f"Tracker failure: {response.failure_reason}")
    self._interval = response.interval
    self._last_announce_time = time.time()
    return response


@staticmethod
def _parse_compact_peers(data: bytes) -> List[Peer]:
    """Parse compact peer format (6 bytes per peer: 4 IP + 2 port)."""
    peers = []
    if len(data) % 6 != 0:
        return peers
    for i in range(0, len(data), 6):
        ip_bytes = data[i:i + 4]
        port_bytes = data[i + 4:i + 6]
        ip = '.'.join(str(b) for b in ip_bytes)
        port = struct.unpack('!H', port_bytes)[0]
        peers.append(Peer(ip, port))
    return peers
```

---

## א.10 — `TorrentMetadata._parse_metadata` (פענוח `.torrent` + info_hash)

**קובץ**: `python_engine/torrent_metadata.py`. פענוח של
מילון bencoded מקובץ `.torrent` וחישוב `info_hash`.

```python
def _parse_metadata(self):
    """Parse the decoded torrent metadata dictionary."""
    if b'announce' not in self._metadata:
        raise TorrentMetadataError("Missing 'announce' field")
    self.announce = self._metadata[b'announce'].decode('utf-8')

    if b'info' not in self._metadata:
        raise TorrentMetadataError("Missing 'info' dictionary")
    info = self._metadata[b'info']
    if not isinstance(info, dict):
        raise TorrentMetadataError("'info' must be a dictionary")

    # Compute info_hash: SHA-1 of the re-encoded info dictionary
    info_encoded = bencode.encode(info)
    self.info_hash = hashlib.sha1(info_encoded).digest()

    if b'piece length' not in info:
        raise TorrentMetadataError("Missing 'piece length' in info")
    self.piece_length = info[b'piece length']

    # Pieces - concatenated SHA-1 hashes (20 bytes each)
    pieces_data = info[b'pieces']
    if len(pieces_data) % 20 != 0:
        raise TorrentMetadataError(
            f"Pieces data length ({len(pieces_data)}) is not multiple of 20")
    self.pieces = [pieces_data[i:i + 20]
                   for i in range(0, len(pieces_data), 20)]
    self.num_pieces = len(self.pieces)
    self.name = info[b'name'].decode('utf-8')

    # Single-file vs multi-file mode
    self.files = []
    if b'files' in info:
        for file_dict in info[b'files']:
            path_parts = [p.decode('utf-8') for p in file_dict[b'path']]
            file_path = os.path.join(self.name, *path_parts)
            self.files.append(FileInfo(file_path, file_dict[b'length']))
    else:
        self.files.append(FileInfo(self.name, info[b'length']))
    self.total_size = sum(f.size for f in self.files)
```

---

## א.11 — `bencode.encode` / `bencode.decode` (פורמט BitTorrent)

**קובץ**: `python_engine/bencode.py`. encoder/decoder
של פורמט Bencode — הפורמט שבו כתובים קובצי `.torrent`
ותגובות tracker.

```python
def encode(data: Any) -> bytes:
    """Encode a Python object into bencode format."""
    if isinstance(data, int) and not isinstance(data, bool):
        return _encode_int(data)
    elif isinstance(data, bytes):
        return _encode_bytes(data)
    elif isinstance(data, str):
        return _encode_bytes(data.encode('utf-8'))
    elif isinstance(data, list):
        return _encode_list(data)
    elif isinstance(data, dict):
        return _encode_dict(data)
    else:
        raise BencodeEncodeError(f"Unsupported type: {type(data)}")


def _encode_int(value: int) -> bytes:
    return b'i' + str(value).encode('ascii') + b'e'

def _encode_bytes(value: bytes) -> bytes:
    return str(len(value)).encode('ascii') + b':' + value

def _encode_list(value: list) -> bytes:
    return b'l' + b''.join(encode(item) for item in value) + b'e'

def _encode_dict(value: dict) -> bytes:
    # Canonical encoding: keys must be sorted as byte-strings
    items = []
    for k in value:
        key_bytes = k if isinstance(k, bytes) else k.encode('utf-8')
        items.append((key_bytes, value[k]))
    items.sort(key=lambda x: x[0])
    result = b'd'
    for k, v in items:
        result += _encode_bytes(k) + encode(v)
    return result + b'e'


def decode(data: bytes) -> Any:
    """Decode bencoded data into a Python object."""
    if not isinstance(data, bytes):
        raise BencodeDecodeError("Input must be bytes")
    if len(data) == 0:
        raise BencodeDecodeError("Empty input")
    result, remaining = _decode_next(data)
    if remaining:
        raise BencodeDecodeError(
            f"Unexpected data after decoded value: {remaining!r}")
    return result


def _decode_next(data: bytes) -> Tuple[Any, bytes]:
    """Decode the next bencoded value and return remaining bytes."""
    first = data[0:1]
    if first == b'i':            # Integer: i<number>e
        end = data.index(b'e')
        return int(data[1:end]), data[end + 1:]
    elif first == b'l':          # List: l<items>e
        result = []
        data = data[1:]
        while data[0:1] != b'e':
            value, data = _decode_next(data)
            result.append(value)
        return result, data[1:]
    elif first == b'd':          # Dictionary: d<pairs>e
        result = {}
        data = data[1:]
        while data[0:1] != b'e':
            key, data = _decode_next(data)
            value, data = _decode_next(data)
            result[key] = value
        return result, data[1:]
    elif b'0' <= first <= b'9':  # String: <length>:<data>
        colon = data.index(b':')
        length = int(data[:colon])
        start = colon + 1
        return data[start:start + length], data[start + length:]
    else:
        raise BencodeDecodeError(f"Invalid token: {first!r}")
```

---

## א.12 — `api_server.py` — Flask REST API + Async Bridge

**קובץ**: `python_engine/api_server.py`. הגשר בין Flask
(סינכרוני) לבין asyncio event loop, ושני handlers מרכזיים.

```python
import asyncio, threading
from flask import Flask, jsonify, request

app = Flask(__name__)
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None


def _start_event_loop():
    """Start the persistent asyncio event loop in a daemon thread."""
    global _loop, _loop_thread
    if _loop is not None and _loop.is_running():
        return
    _loop = asyncio.new_event_loop()
    def _run_loop():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()
    _loop_thread = threading.Thread(target=_run_loop, daemon=True)
    _loop_thread.start()


def _run_async(coro, timeout=60):
    """Bridge: call asyncio coroutine from Flask thread."""
    if _loop is None or not _loop.is_running():
        _start_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)


@app.route('/torrents', methods=['POST'])
def start_download():
    """Start a new download from a .torrent file."""
    manager = get_manager()
    if 'torrent_file' in request.files:
        file = request.files['torrent_file']
        torrent = TorrentMetadata(torrent_data=file.read())
    elif request.is_json and 'torrent_path' in request.json:
        torrent = TorrentMetadata(torrent_path=request.json['torrent_path'])
    else:
        return jsonify({"error": "No torrent file provided"}), 400

    piece_algo = AlgorithmType.RAREST_FIRST
    peer_algo = AlgorithmType.TIT_FOR_TAT
    algo_data = request.json if request.is_json else request.form
    if algo_data.get('piece_algorithm') == 'random':
        piece_algo = AlgorithmType.RANDOM
    if algo_data.get('peer_algorithm') == 'round_robin':
        peer_algo = AlgorithmType.ROUND_ROBIN

    async def create_and_start():
        download = await manager.add_torrent(torrent, piece_algo, peer_algo)
        await download.start()
        return download
    download = _run_async(create_and_start())
    return jsonify({
        "id": download.id, "name": torrent.name,
        "size": torrent.total_size,
        "num_pieces": torrent.num_pieces,
        "state": download.state.value}), 201


@app.route('/torrents/<torrent_id>/pause', methods=['POST'])
def pause_download(torrent_id: str):
    manager = get_manager()
    download = manager.get_download(torrent_id)
    if download is None:
        return jsonify({"error": "Torrent not found"}), 404
    _run_async(manager.pause_download(torrent_id))
    return jsonify({"id": torrent_id, "state": "Paused"})
```

---

## א.13 — `init_database` ו-`save_torrent_to_db` (SQLite)

**קובץ**: `python_engine/api_server.py`. הקמת ה-schema
של SQLite ושמירת היסטוריה.

```python
def init_database():
    """Initialize the SQLite database with required tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS torrents (
            id TEXT PRIMARY KEY,
            info_hash TEXT, name TEXT, size INTEGER,
            started_at DATETIME, completed_at DATETIME,
            total_time_seconds INTEGER, final_status TEXT
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torrent_id TEXT, avg_speed REAL,
            peak_speed REAL, avg_peers INTEGER,
            FOREIGN KEY (torrent_id) REFERENCES torrents(id)
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS algorithm_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torrent_id TEXT, piece_index INTEGER,
            selected_as_rarest INTEGER DEFAULT 0,
            choke_count INTEGER DEFAULT 0,
            unchoke_count INTEGER DEFAULT 0,
            FOREIGN KEY (torrent_id) REFERENCES torrents(id)
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torrent_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT, description TEXT,
            FOREIGN KEY (torrent_id) REFERENCES torrents(id)
        )""")
    # Migration: add algorithm columns if missing
    for col, col_def in [("piece_algorithm", "TEXT DEFAULT 'rarest_first'"),
                         ("peer_algorithm",  "TEXT DEFAULT 'tit_for_tat'")]:
        try:
            cursor.execute(f"ALTER TABLE torrents ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    conn.close()


def save_torrent_to_db(download):
    """Save torrent info and stats to the SQLite database."""
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        stats = download.stats
        cursor.execute("""
            INSERT OR REPLACE INTO torrents (id, info_hash, name, size,
                started_at, completed_at, total_time_seconds, final_status,
                piece_algorithm, peer_algorithm)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (download.id, download.torrent.info_hash_hex(),
              download.torrent.name, download.torrent.total_size,
              datetime.datetime.fromtimestamp(stats.start_time).isoformat()
                  if stats.start_time else None,
              datetime.datetime.fromtimestamp(stats.end_time).isoformat()
                  if stats.end_time else None,
              int(stats.elapsed_time) if stats.elapsed_time else 0,
              download.state.value,
              download.piece_algorithm.value,
              download.peer_algorithm.value))
        cursor.execute("""
            INSERT OR REPLACE INTO performance_stats
                (torrent_id, avg_speed, peak_speed, avg_peers, choke_cycles)
            VALUES (?, ?, ?, ?, ?)
        """, (download.id, stats.average_speed, stats.peak_speed,
              stats.connected_peers, stats.choke_cycles))
        conn.commit()
        conn.close()
```

---

## א.14 — `ApiService.startDownload` ו-`getStatus` (Java HTTP Client)

**קובץ**: `java_gui/src/ApiService.java`. שכבת
ה-abstraction של ה-GUI מעל ה-REST API.

```java
public class ApiService {
    private final String baseUrl;
    private final HttpClient client;

    public ApiService(String baseUrl) {
        this.baseUrl = baseUrl;
        this.client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    /**
     * Start a new download by uploading a .torrent file (multipart).
     */
    public String startDownload(File torrentFile, String pieceAlgorithm,
                                String peerAlgorithm, String downloadDir)
            throws IOException, ApiException {
        String boundary = "----FormBoundary" + System.currentTimeMillis();
        byte[] fileBytes = Files.readAllBytes(torrentFile.toPath());

        StringBuilder bodyBuilder = new StringBuilder();
        bodyBuilder.append("--").append(boundary).append("\r\n");
        bodyBuilder.append("Content-Disposition: form-data; name=\"torrent_file\"; filename=\"")
                .append(torrentFile.getName()).append("\"\r\n");
        bodyBuilder.append("Content-Type: application/x-bittorrent\r\n\r\n");
        byte[] headerBytes = bodyBuilder.toString().getBytes();

        String trailingPart = "\r\n--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"piece_algorithm\"\r\n\r\n" +
                pieceAlgorithm +
                "\r\n--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"peer_algorithm\"\r\n\r\n" +
                peerAlgorithm;
        if (downloadDir != null) {
            trailingPart += "\r\n--" + boundary + "\r\n" +
                    "Content-Disposition: form-data; name=\"download_dir\"\r\n\r\n" +
                    downloadDir;
        }
        trailingPart += "\r\n--" + boundary + "--\r\n";
        byte[] footerBytes = trailingPart.getBytes();

        byte[] body = new byte[headerBytes.length + fileBytes.length + footerBytes.length];
        System.arraycopy(headerBytes, 0, body, 0, headerBytes.length);
        System.arraycopy(fileBytes, 0, body, headerBytes.length, fileBytes.length);
        System.arraycopy(footerBytes, 0, body, headerBytes.length + fileBytes.length,
                         footerBytes.length);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents"))
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                .build();

        HttpResponse<String> response = sendRequest(request);
        if (response.statusCode() != 201) {
            throw new ApiException("Failed to start download: " + response.body());
        }
        return new JSONObject(response.body()).getString("id");
    }

    /**
     * Get status of all active downloads.
     */
    public List<TorrentStatus> getStatus() throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents"))
                .GET()
                .build();
        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);

        JSONArray jsonArray = new JSONArray(response.body());
        List<TorrentStatus> statuses = new ArrayList<>();
        for (int i = 0; i < jsonArray.length(); i++) {
            statuses.add(TorrentStatus.fromJson(jsonArray.getJSONObject(i)));
        }
        return statuses;
    }
}
```

---

## א.15 — `TorrentClientGUI`: scheduler + refreshStatus + updateTable

**קובץ**: `java_gui/src/TorrentClientGUI.java`. ה-polling
mechanism של ה-GUI שמעדכן את הטבלה כל 500ms בלי לחסום
את ה-EDT.

```java
private void startStatusUpdater() {
    scheduler.scheduleAtFixedRate(() -> {
        try {
            SwingUtilities.invokeLater(this::refreshStatus);
        } catch (Exception e) {
            // Ignore refresh errors
        }
    }, 500, 500, TimeUnit.MILLISECONDS);
}

private void refreshStatus() {
    // Run blocking HTTP in a separate thread so EDT stays responsive
    new Thread(() -> {
        try {
            List<ApiService.TorrentStatus> statuses = apiService.getStatus();
            SwingUtilities.invokeLater(() -> updateTable(statuses));

            // Poll engine logs for each active download
            for (ApiService.TorrentStatus status : statuses) {
                if ("Running".equals(status.state)
                        || "Error".equals(status.state)
                        || "Completed".equals(status.state)) {
                    int since = logSeqTracker.getOrDefault(status.id, 0);
                    JSONArray logs = apiService.getLogs(status.id, since);
                    if (logs.length() > 0) {
                        int maxSeq = since;
                        for (int i = 0; i < logs.length(); i++) {
                            JSONObject entry = logs.getJSONObject(i);
                            int seq = entry.getInt("seq");
                            String msg = entry.getString("msg");
                            if (seq > maxSeq) maxSeq = seq;
                            SwingUtilities.invokeLater(() ->
                                log("[engine] " + msg));
                        }
                        logSeqTracker.put(status.id, maxSeq);
                    }
                }
            }
        } catch (Exception e) {
            // Server might not be running yet — silent
        }
    }).start();
}

private void updateTable(List<ApiService.TorrentStatus> statuses) {
    String selectedId = getSelectedTorrentId();
    // Detect completion transitions and show notification
    for (ApiService.TorrentStatus status : statuses) {
        String prevState = previousStates.get(status.id);
        if ("Completed".equals(status.state)
                && !"Completed".equals(prevState)) {
            String msg = status.name + "\nSaved to: " + status.downloadPath;
            SwingUtilities.invokeLater(() ->
                JOptionPane.showMessageDialog(this, msg, "Download Complete",
                        JOptionPane.INFORMATION_MESSAGE)
            );
        }
        previousStates.put(status.id, status.state);
    }
    tableModel.setRowCount(0);
    for (ApiService.TorrentStatus status : statuses) {
        tableModel.addRow(new Object[]{
                status.name, formatSize(status.size),
                status.progress, formatSpeed(status.downloadSpeed),
                String.valueOf(status.connectedPeers),
                status.state, status.downloadPath, status.id
        });
    }
    // Restore selection
    if (selectedId != null) {
        for (int i = 0; i < tableModel.getRowCount(); i++) {
            if (selectedId.equals(tableModel.getValueAt(i, COL_ID))) {
                downloadTable.setRowSelectionInterval(i, i);
                break;
            }
        }
    }
}
```

---

## א.16 — `ProgressBarRenderer` (renderer מותאם ב-Swing)

**קובץ**: `java_gui/src/TorrentClientGUI.java`. renderer
מותאם שמצייר עמודת Progress כ-`JProgressBar` במקום טקסט,
עם מעבר צבעי כחול→ירוק.

```java
/**
 * Custom cell renderer that displays a progress bar in the table.
 */
static class ProgressBarRenderer extends DefaultTableCellRenderer {
    private final JProgressBar progressBar = new JProgressBar(0, 100);

    public ProgressBarRenderer() {
        progressBar.setStringPainted(true);
    }

    @Override
    public Component getTableCellRendererComponent(JTable table, Object value,
                                                   boolean isSelected,
                                                   boolean hasFocus,
                                                   int row, int column) {
        double progress = 0.0;
        if (value instanceof Double) {
            progress = (Double) value;
        }
        progressBar.setValue((int) progress);
        progressBar.setString(String.format("%.1f%%", progress));

        if (progress >= 100) {
            progressBar.setForeground(new Color(50, 150, 50));     // ירוק
        } else {
            progressBar.setForeground(new Color(60, 120, 200));    // כחול
        }
        return progressBar;
    }
}
```
