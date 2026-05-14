# נספח א' – קטעי קוד מרכזיים

נספח זה מציג את קטעי הקוד החשובים והמרכזיים ביותר
בפרויקט, בסדר עדיפות יורד. כל הקטעים הם מילה במילה מקובצי
המקור — אין שינויים או הפשטות.

## א.1 — `Download._download_loop` (האלגוריתם הראשי)

**קובץ**: `python_engine/download_manager.py` (שורות 203–270). ה-orchestrator המרכזי של ההורדה — מתאם בין tracker, peers, piece requests, ו-stats. רץ ב-asyncio event loop ומפעיל ~55 קואורוטינות במקביל עבור הורדה אחת עם 50 peers.

```python
    async def _download_loop(self):
        """Main download coordination loop."""
        try:
            # Initialize tracker
            self._tracker = TrackerClient(
                announce_url=self.torrent.announce,
                info_hash=self.torrent.info_hash,
                peer_id=self.peer_id,
                port=6881
            )
            self._tracker.left = self.torrent.total_size

            # Initial announce
            self._log(f"Contacting tracker: {self.torrent.announce}")
            response = await self._tracker.announce(event='started',
                                                    left=self.torrent.total_size)
            for peer in response.peers:
                self._known_peers.add(peer)
            self.stats.total_peers_seen = len(self._known_peers)
            self._log(f"Tracker responded: {len(response.peers)} peers found")

            # Start choke/unchoke timer
            self._choke_task = asyncio.create_task(self._choke_loop())
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())

            # Start periodic tracker announces
            await self._tracker.start_periodic_announce(
                callback=self._on_tracker_response
            )

            # Connect to peers (non-blocking — don't wait for all 50 attempts)
            asyncio.create_task(self._connect_to_peers())

            # Main piece request loop
            last_cleanup = time.time()
            while not self.piece_manager.is_complete and self.state == DownloadState.RUNNING:
                # Reset pieces stuck in IN_PROGRESS for too long
                self.piece_manager.reset_stale_pieces(PIECE_REQUEST_TIMEOUT)

                await self._request_pieces()
                await asyncio.sleep(0.1)

                # Periodically clean up dead peers and try new ones
                now = time.time()
                if now - last_cleanup > PEER_CLEANUP_INTERVAL:
                    self._cleanup_dead_peers()
                    await self._connect_to_peers()
                    last_cleanup = now

                # Update stats
                self._update_speed()
                self._tracker.update_stats(
                    uploaded=self.stats.bytes_uploaded,
                    downloaded=self.stats.bytes_downloaded,
                    left=self.piece_manager.bytes_remaining
                )

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

## א.2 — `select_piece_rarest_first` (בחירת piece)

**קובץ**: `python_engine/piece_manager.py` (שורות 279–317). לב האלגוריתם המרכזי. עוברת על כל ה-pieces החסרים שה-peer מציע, מוצאת את אלה עם המינימום של `_peer_frequency`, ובוחרת אחד אקראית מהקבוצה הנדירה.

```python
    def select_piece_rarest_first(self, peer_pieces: List[bool]) -> Optional[int]:
        """Select a piece using the rarest-first algorithm.

        1. Consider only pieces that are missing AND the peer has
        2. Find the minimum frequency among those pieces
        3. Build a rarest set (all pieces with that frequency)
        4. Choose one at random from the rarest set

        Args:
            peer_pieces: List of booleans indicating which pieces the peer has.

        Returns:
            Piece index to download, or None if no piece is available.
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

## א.3 — `_tit_for_tat_unchoke` (אלגוריתם choke/unchoke)

**קובץ**: `python_engine/download_manager.py` (שורות 519–564). האלגוריתם של BitTorrent הקלאסי שמעודד reciprocity. רץ כל 10 שניות.

```python
    async def _tit_for_tat_unchoke(self):
        """Implement the Tit-for-Tat choke/unchoke algorithm.

        1. Get all interested peers
        2. Sort by how much they uploaded to us
        3. Unchoke top K peers
        4. Optimistic unchoke: randomly unchoke one additional peer
        5. Choke all others
        """
        interested_peers = [
            (key, conn) for key, conn in self._connections.items()
            if conn.connected and conn.peer_interested
        ]

        if not interested_peers:
            return

        # Sort by download rate from this peer (how much they contribute to us)
        interested_peers.sort(key=lambda x: x[1].bytes_downloaded, reverse=True)

        # Select top K
        to_unchoke = set()
        for i, (key, conn) in enumerate(interested_peers):
            if i < MAX_UNCHOKED_PEERS:
                to_unchoke.add(key)

        # Optimistic unchoke: pick one random peer not in top K
        remaining = [
            (key, conn) for key, conn in interested_peers
            if key not in to_unchoke
        ]
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

## א.4 — `Piece.submit_block` ו-`Piece.verify_hash`

**קובץ**: `python_engine/piece_manager.py` (שורות 95–117). אימות SHA-1 לפני כתיבה לדיסק. החלק האבטחתי הקריטי ביותר במערכת.

```python
    def submit_block(self, offset: int, data: bytes) -> bool:
        """Submit a received block.

        Args:
            offset: Byte offset within the piece.
            data: Block data.

        Returns:
            True if the piece is now complete.
        """
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

## א.5 — `_send_handshake` + `_receive_handshake`

**קובץ**: `python_engine/peer_connection.py` (שורות 181–221). ה-handshake של BEP-3 — קו ההגנה הראשון של כל חיבור. 68 בתים בדיוק.

```python
    async def _send_handshake(self):
        """Send the BitTorrent handshake message."""
        handshake = (
            bytes([PROTOCOL_STRING_LEN]) +
            PROTOCOL_STRING +
            b'\x00' * 8 +  # Reserved bytes
            self.info_hash +
            self.our_peer_id
        )
        self._writer.write(handshake)
        await self._writer.drain()

    async def _receive_handshake(self):
        """Receive and validate the peer's handshake."""
        try:
            data = await asyncio.wait_for(
                self._reader.readexactly(HANDSHAKE_LEN),
                timeout=CONNECTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise PeerConnectionError("Handshake timeout")
        except asyncio.IncompleteReadError:
            raise PeerConnectionError("Connection closed during handshake")

        # Parse handshake
        pstrlen = data[0]
        if pstrlen != PROTOCOL_STRING_LEN:
            raise PeerConnectionError(f"Invalid protocol string length: {pstrlen}")

        pstr = data[1:1 + pstrlen]
        if pstr != PROTOCOL_STRING:
            raise PeerConnectionError(f"Invalid protocol string: {pstr!r}")

        # reserved = data[1 + pstrlen:1 + pstrlen + 8]  # Can check for extensions
        received_info_hash = data[1 + pstrlen + 8:1 + pstrlen + 8 + 20]
        self.remote_peer_id = data[1 + pstrlen + 8 + 20:1 + pstrlen + 8 + 40]

        if received_info_hash != self.info_hash:
            raise PeerConnectionError("Info hash mismatch during handshake")

        self._last_activity = time.time()
```

## א.6 — `_read_message` (parsing הודעות Peer Wire Protocol)

**קובץ**: `python_engine/peer_connection.py` (שורות 245–286). parser הודעות עם ולידציית אורך (`MAX_MESSAGE_SIZE = 2 MB`) וטיימאוטים.

```python
    async def _read_message(self) -> Optional[PeerMessage]:
        """Read a single length-prefixed message from the peer."""
        try:
            length_bytes = await asyncio.wait_for(
                self._reader.readexactly(4),
                timeout=REQUEST_TIMEOUT * 2
            )
        except asyncio.TimeoutError:
            raise PeerConnectionError("Read timeout")
        except asyncio.IncompleteReadError:
            return None  # Connection closed

        length = struct.unpack('!I', length_bytes)[0]

        if length == 0:
            return PeerMessage(MessageType.KEEP_ALIVE)

        if length > MAX_MESSAGE_SIZE:
            raise PeerConnectionError(
                f"Message too large: {length} bytes (max {MAX_MESSAGE_SIZE})"
            )

        try:
            payload = await asyncio.wait_for(
                self._reader.readexactly(length),
                timeout=REQUEST_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise PeerConnectionError("Payload read timeout")
        except asyncio.IncompleteReadError:
            return None

        msg_id = payload[0]
        msg_payload = payload[1:]

        try:
            msg_type = MessageType(msg_id)
        except ValueError:
            logger.warning(f"Unknown message type {msg_id} from {self.ip}:{self.port}")
            return None

        return PeerMessage(msg_type, msg_payload)
```

## א.7 — `Download._on_peer_message` (זרימת קבלת PIECE)

**קובץ**: `python_engine/download_manager.py` (שורות 333–411). ה-callback שמופעל לכל הודעה מ-peer. הזרימה של קבלת PIECE כוללת אימות SHA-1 ב-thread pool, כתיבה לדיסק, ו-broadcast HAVE.

```python
    async def _on_peer_message(self, conn: PeerConnection, message: PeerMessage):
        """Handle messages from peers."""
        peer_key = f"{conn.ip}:{conn.port}"

        if message.type == MessageType.BITFIELD:
            self.piece_manager.update_peer_pieces(peer_key, conn.peer_pieces)
            # Check if peer has pieces we need
            if self._peer_has_needed_pieces(conn):
                await conn.send_interested()

        elif message.type == MessageType.HAVE:
            piece_idx = message.piece_index
            self.piece_manager.update_peer_have(peer_key, piece_idx)
            if not self.piece_manager.has_piece(piece_idx) and not conn.am_interested:
                await conn.send_interested()

        elif message.type == MessageType.UNCHOKE:
            # Peer unchoked us — immediately try to request pieces
            await self._request_from_peer(peer_key, conn)

        elif message.type == MessageType.CHOKE:
            # Peer choked us — all our pending requests are silently dropped
            # Clear block request state so other peers can pick up those blocks
            self.piece_manager.clear_peer_requests(peer_key)

        elif message.type == MessageType.PIECE:
            piece_idx = message.piece_index
            offset = message.block_offset
            data = message.block_data

            if data is None:
                return

            # Guard: skip if piece is already completed (duplicate from another peer)
            piece = self.piece_manager.pieces[piece_idx]
            if piece.status == PieceStatus.COMPLETED:
                return

            is_complete = self.piece_manager.submit_block(piece_idx, offset, data)
            self.stats.bytes_downloaded += len(data)

            if is_complete:
                # Run hash verification in thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                verified = await loop.run_in_executor(
                    self._executor, self.piece_manager.verify_piece, piece_idx
                )
                if verified:
                    self.security.report_successful_piece(peer_key, piece_idx)
                    # Write to disk in thread pool
                    await loop.run_in_executor(
                        self._executor, self._write_piece_sync, piece_idx
                    )
                    done = self.piece_manager.completed_pieces
                    self._log(f"Piece {piece_idx} verified OK ({done}/{self.torrent.num_pieces})")
                    # Clear peer assignment for this piece so peers get new work
                    for pk, pi in list(self._peer_piece.items()):
                        if pi == piece_idx:
                            del self._peer_piece[pk]
                    # Announce to all peers (non-blocking fire-and-forget)
                    asyncio.create_task(self._broadcast_have(piece_idx))
                    if self._on_progress:
                        self._on_progress(self)
                    # Set state immediately on completion so GUI sees it on next poll
                    if self.piece_manager.is_complete:
                        self.state = DownloadState.COMPLETED
                        self.stats.end_time = time.time()
                    # Immediately try to give this peer new work
                    await self._request_from_peer(peer_key, conn)
                else:
                    self._log(f"Piece {piece_idx} HASH FAILED from {peer_key}")
                    self.security.report_hash_failure(peer_key, piece_idx)
                    # Clear peer assignment for the failed piece
                    for pk, pi in list(self._peer_piece.items()):
                        if pi == piece_idx:
                            del self._peer_piece[pk]
                    if self.security.is_peer_banned(peer_key):
                        self._log(f"Banned peer {peer_key} (too many hash failures)")
                        await conn.disconnect()
```

## א.8 — `PeerReputation` + `SecurityManager`

**קובץ**: `python_engine/security.py` (שורות 42–130). מערכת המוניטין שחוסמת peers זדוניים אחרי 3 שגיאות hash או 5 הפרות פרוטוקול.

```python
class PeerReputation:
    """Tracks reputation and violations for a single peer."""

    def __init__(self, peer_key: str):
        self.peer_key = peer_key
        self.hash_failures = 0
        self.protocol_violations = 0
        self.invalid_messages = 0
        self.timeouts = 0
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
        total_interactions = (
            self.successful_pieces + self.hash_failures +
            self.protocol_violations + self.invalid_messages
        )
        if total_interactions == 0:
            return 0.5  # Neutral
        good = self.successful_pieces
        bad = self.hash_failures * 3 + self.protocol_violations * 2 + self.invalid_messages
        return max(0.0, min(1.0, good / (good + bad)))


class SecurityManager:
    """Manages security aspects of the BitTorrent client.

    Responsibilities:
    - Verify piece data integrity using SHA-1 hashes
    - Track peer reputation and detect malicious behavior
    - Validate protocol messages
    - Manage peer bans
    - Log security events
    """

    def __init__(self):
        self._peer_reputations: Dict[str, PeerReputation] = {}
        self._banned_peers: Set[str] = set()
        self._events: List[SecurityEvent] = []
        self._event_callbacks = []

    def verify_piece(self, piece_data: bytes, expected_hash: bytes) -> bool:
        """Verify piece data integrity using SHA-1.

        Args:
            piece_data: The downloaded piece data.
            expected_hash: Expected 20-byte SHA-1 hash from .torrent file.

        Returns:
            True if hash matches.
        """
        actual_hash = hashlib.sha1(piece_data).digest()
        return actual_hash == expected_hash

    def report_hash_failure(self, peer_key: str, piece_index: int):
        """Report a hash verification failure for a peer.

        Args:
            peer_key: Identifier for the peer.
            piece_index: Index of the piece that failed verification.
        """
        rep = self._get_reputation(peer_key)
        rep.hash_failures += 1
        rep.last_violation = time.time()

        event = SecurityEvent(
            "hash_failure", peer_key,
            f"Piece {piece_index} failed hash verification "
            f"(failures: {rep.hash_failures}/{MAX_HASH_FAILURES_PER_PEER})",
            severity="warning"
        )
        self._log_event(event)

        if rep.should_ban:
            self._ban_peer(peer_key, "Too many hash failures")

```

## א.9 — `TrackerClient.announce` (תקשורת עם tracker)

**קובץ**: `python_engine/tracker_client.py` (שורות 175–249). שליחת announce ל-tracker עם פרסור Bencode של התגובה.

```python
    async def announce(self, event: Optional[str] = None,
                       uploaded: Optional[int] = None,
                       downloaded: Optional[int] = None,
                       left: Optional[int] = None) -> TrackerResponse:
        """Send an announce request to the tracker.

        Args:
            event: One of 'started', 'completed', 'stopped', or None for periodic.
            uploaded: Override uploaded byte count.
            downloaded: Override downloaded byte count.
            left: Override remaining byte count.

        Returns:
            TrackerResponse with peer list and swarm info.
        """
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

        # Build the URL with proper encoding for binary params
        url = self._build_announce_url(params)

        logger.info(f"Announcing to tracker: event={event}, left={params['left']}")

        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise TrackerError(
                        f"Tracker returned HTTP {resp.status}: {await resp.text()}"
                    )
                raw = await resp.read()
        except aiohttp.ClientError as e:
            raise TrackerError(f"Failed to connect to tracker: {e}")

        try:
            decoded = bencode.decode(raw)
        except bencode.BencodeDecodeError as e:
            raise TrackerError(f"Failed to decode tracker response: {e}")

        response = TrackerResponse(decoded)

        if response.failure_reason:
            raise TrackerError(f"Tracker returned failure: {response.failure_reason}")

        if response.warning_message:
            logger.warning(f"Tracker warning: {response.warning_message}")

        self._interval = response.interval
        if response.min_interval:
            self._min_interval = response.min_interval
        if response.tracker_id:
            self._tracker_id = response.tracker_id

        self._last_announce_time = time.time()

        logger.info(
            f"Tracker response: {len(response.peers)} peers, "
            f"{response.complete} seeders, {response.incomplete} leechers, "
            f"interval={response.interval}s"
        )

        return response
```

## א.10 — `TorrentMetadata._parse_metadata`

**קובץ**: `python_engine/torrent_metadata.py` (שורות 79–153). פענוח מילון bencoded מקובץ `.torrent` וחישוב `info_hash`.

```python
    def _parse_metadata(self):
        """Parse the decoded torrent metadata dictionary."""
        # Announce URL (required)
        if b'announce' not in self._metadata:
            raise TorrentMetadataError("Missing 'announce' field")
        self.announce = self._metadata[b'announce'].decode('utf-8')

        # Announce list (optional)
        self.announce_list = []
        if b'announce-list' in self._metadata:
            for tier in self._metadata[b'announce-list']:
                tier_urls = [url.decode('utf-8') for url in tier]
                self.announce_list.append(tier_urls)

        # Info dictionary (required)
        if b'info' not in self._metadata:
            raise TorrentMetadataError("Missing 'info' dictionary")
        info = self._metadata[b'info']
        if not isinstance(info, dict):
            raise TorrentMetadataError("'info' must be a dictionary")

        # Compute info_hash: SHA-1 of the re-encoded info dictionary
        info_encoded = bencode.encode(info)
        self.info_hash = hashlib.sha1(info_encoded).digest()

        # Piece length (required)
        if b'piece length' not in info:
            raise TorrentMetadataError("Missing 'piece length' in info")
        self.piece_length = info[b'piece length']

        # Pieces - concatenated SHA-1 hashes (required)
        if b'pieces' not in info:
            raise TorrentMetadataError("Missing 'pieces' in info")
        pieces_data = info[b'pieces']
        if len(pieces_data) % 20 != 0:
            raise TorrentMetadataError(
                f"Pieces data length ({len(pieces_data)}) is not a multiple of 20"
            )
        self.pieces = [pieces_data[i:i + 20] for i in range(0, len(pieces_data), 20)]
        self.num_pieces = len(self.pieces)

        # Name (required)
        if b'name' not in info:
            raise TorrentMetadataError("Missing 'name' in info")
        self.name = info[b'name'].decode('utf-8')

        # Parse files
        self.files = []
        if b'files' in info:
            # Multi-file mode
            for file_dict in info[b'files']:
                path_parts = [p.decode('utf-8') for p in file_dict[b'path']]
                file_path = os.path.join(self.name, *path_parts)
                file_size = file_dict[b'length']
                self.files.append(FileInfo(file_path, file_size))
        else:
            # Single-file mode
            if b'length' not in info:
                raise TorrentMetadataError("Missing 'length' in single-file info")
            self.files.append(FileInfo(self.name, info[b'length']))

        self.total_size = sum(f.size for f in self.files)

        # Optional fields
        self.comment = None
        if b'comment' in self._metadata:
            self.comment = self._metadata[b'comment'].decode('utf-8', errors='replace')

        self.created_by = None
        if b'created by' in self._metadata:
            self.created_by = self._metadata[b'created by'].decode('utf-8', errors='replace')

        self.creation_date = None
        if b'creation date' in self._metadata:
            self.creation_date = self._metadata[b'creation date']
```

## א.11 — `bencode.encode` ו-`bencode.decode`

**קובץ**: `python_engine/bencode.py` (שורות 25–72). encoder/decoder של פורמט Bencode — הפורמט שבו כתובים קובצי `.torrent` ותגובות tracker.

```python
def encode(data: Any) -> bytes:
    """Encode a Python object into bencode format.

    Args:
        data: Python object to encode (int, bytes, str, list, dict).

    Returns:
        Bencoded bytes.

    Raises:
        BencodeEncodeError: If the data type is not supported.
    """
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


def decode(data: bytes) -> Any:
    """Decode bencoded data into a Python object.

    Args:
        data: Bencoded bytes to decode.

    Returns:
        Decoded Python object.

    Raises:
        BencodeDecodeError: If the data is not valid bencode.
    """
    if not isinstance(data, bytes):
        raise BencodeDecodeError("Input must be bytes")
    if len(data) == 0:
        raise BencodeDecodeError("Empty input")

    result, remaining = _decode_next(data)
    if remaining:
        raise BencodeDecodeError(f"Unexpected data after decoded value: {remaining!r}")
    return result

```

## א.12 — `init_database` (סכמת SQLite)

**קובץ**: `python_engine/api_server.py` (שורות 90–160). הקמת ה-schema של SQLite בעת startup, כולל ה-migration להוספת `piece_algorithm` ו-`peer_algorithm` אם הם חסרים.

```python
def init_database():
    """Initialize the SQLite database with required tables."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS torrents (
            id TEXT PRIMARY KEY,
            info_hash TEXT,
            name TEXT,
            size INTEGER,
            started_at DATETIME,
            completed_at DATETIME,
            total_time_seconds INTEGER,
            final_status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torrent_id TEXT,
            avg_speed REAL,
            peak_speed REAL,
            avg_peers INTEGER,
            FOREIGN KEY (torrent_id) REFERENCES torrents(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS algorithm_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torrent_id TEXT,
            piece_index INTEGER,
            selected_as_rarest INTEGER DEFAULT 0,
            choke_count INTEGER DEFAULT 0,
            unchoke_count INTEGER DEFAULT 0,
            FOREIGN KEY (torrent_id) REFERENCES torrents(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torrent_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT,
            description TEXT,
            FOREIGN KEY (torrent_id) REFERENCES torrents(id)
        )
    """)

    # Migration: add algorithm columns if they don't exist yet
    for col, col_def in [("piece_algorithm", "TEXT DEFAULT 'rarest_first'"),
                         ("peer_algorithm",  "TEXT DEFAULT 'tit_for_tat'")]:
        try:
            cursor.execute(f"ALTER TABLE torrents ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE performance_stats ADD COLUMN choke_cycles INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()
    logger.info("Database initialized")

```

## א.13 — `_start_event_loop` + `_run_async` (Async Bridge)

**קובץ**: `python_engine/api_server.py` (שורות 44–75). הגשר בין Flask (סינכרוני) ל-asyncio event loop שרץ ב-daemon thread נפרד.

```python
def _start_event_loop():
    """Start the persistent asyncio event loop in a background daemon thread."""
    global _loop, _loop_thread
    if _loop is not None and _loop.is_running():
        return

    _loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    _loop_thread = threading.Thread(target=_run_loop, daemon=True)
    _loop_thread.start()
    logger.info("Background asyncio event loop started")


def _run_async(coro, timeout=60):
    """Submit a coroutine to the persistent event loop and wait for the result.

    Args:
        coro: The coroutine to run.
        timeout: Maximum seconds to wait for result.

    Returns:
        The coroutine's return value.
    """
    if _loop is None or not _loop.is_running():
        _start_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)

```

## א.14 — `ApiService.startDownload` (Java HTTP Client)

**קובץ**: `java_gui/src/ApiService.java` (שורות 113–167). שכבת ה-abstraction של ה-GUI מעל ה-REST API. בונה multipart request עם קובץ ה-`.torrent` ובחירת האלגוריתמים.

```java
    public String startDownload(File torrentFile, String pieceAlgorithm, String peerAlgorithm,
                                String downloadDir)
            throws IOException, ApiException {
        // Build multipart request
        String boundary = "----FormBoundary" + System.currentTimeMillis();
        byte[] fileBytes = Files.readAllBytes(torrentFile.toPath());

        StringBuilder bodyBuilder = new StringBuilder();
        // Torrent file part
        bodyBuilder.append("--").append(boundary).append("\r\n");
        bodyBuilder.append("Content-Disposition: form-data; name=\"torrent_file\"; filename=\"")
                .append(torrentFile.getName()).append("\"\r\n");
        bodyBuilder.append("Content-Type: application/x-bittorrent\r\n\r\n");

        byte[] headerBytes = bodyBuilder.toString().getBytes();

        String algorithmPart = "\r\n--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"piece_algorithm\"\r\n\r\n" +
                pieceAlgorithm +
                "\r\n--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"peer_algorithm\"\r\n\r\n" +
                peerAlgorithm;

        // Add download directory if specified
        if (downloadDir != null && !downloadDir.isEmpty()) {
            algorithmPart += "\r\n--" + boundary + "\r\n" +
                    "Content-Disposition: form-data; name=\"download_dir\"\r\n\r\n" +
                    downloadDir;
        }

        algorithmPart += "\r\n--" + boundary + "--\r\n";

        byte[] footerBytes = algorithmPart.getBytes();

        // Combine
        byte[] body = new byte[headerBytes.length + fileBytes.length + footerBytes.length];
        System.arraycopy(headerBytes, 0, body, 0, headerBytes.length);
        System.arraycopy(fileBytes, 0, body, headerBytes.length, fileBytes.length);
        System.arraycopy(footerBytes, 0, body, headerBytes.length + fileBytes.length, footerBytes.length);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents"))
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                .build();

        HttpResponse<String> response = sendRequest(request);

        if (response.statusCode() != 201) {
            throw new ApiException("Failed to start download: " + response.body());
        }

        JSONObject json = new JSONObject(response.body());
        return json.getString("id");
    }
```

## א.15 — `ApiService.getStatus`

**קובץ**: `java_gui/src/ApiService.java` (שורות 169–191). החלק ב-GUI שמושך את הסטטוס מכל ההורדות. נקרא כל 500ms מתוך ה-polling thread.

```java
    /**
     * Get status of all active downloads.
     *
     * @return List of TorrentStatus objects.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
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
```

## א.16 — `TorrentClientGUI.startStatusUpdater` + `refreshStatus`

**קובץ**: `java_gui/src/TorrentClientGUI.java` (שורות 436–478). ה-polling mechanism של ה-GUI שמעדכן את הטבלה כל 500ms בלי לחסום את ה-EDT. כל קריאת HTTP חוסמת רצה ב-`Thread` חדש.

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
        new Thread(() -> {
            try {
                List<ApiService.TorrentStatus> statuses = apiService.getStatus();
                SwingUtilities.invokeLater(() -> updateTable(statuses));

                // Poll logs for each active download
                for (ApiService.TorrentStatus status : statuses) {
                    if ("Running".equals(status.state) || "Error".equals(status.state) || "Completed".equals(status.state)) {
                        int since = logSeqTracker.getOrDefault(status.id, 0);
                        try {
                            JSONArray logs = apiService.getLogs(status.id, since);
                            if (logs.length() > 0) {
                                int maxSeq = since;
                                for (int i = 0; i < logs.length(); i++) {
                                    JSONObject entry = logs.getJSONObject(i);
                                    int seq = entry.getInt("seq");
                                    String msg = entry.getString("msg");
                                    if (seq > maxSeq) maxSeq = seq;
                                    SwingUtilities.invokeLater(() -> log("[engine] " + msg));
                                }
                                logSeqTracker.put(status.id, maxSeq);
                            }
                        } catch (Exception ex) {
                            // Ignore log polling errors
                        }
                    }
                }
            } catch (Exception e) {
                // Server might not be running yet
            }
        }).start();
    }
```

## א.17 — `ProgressBarRenderer` (renderer מותאם)

**קובץ**: `java_gui/src/TorrentClientGUI.java` (שורות 605–631). renderer מותאם שמצייר עמודת Progress כ-`JProgressBar` במקום טקסט, עם מעבר צבעי כחול→ירוק כשמגיעים ל-100%.

```java
    static class ProgressBarRenderer extends DefaultTableCellRenderer {
        private final JProgressBar progressBar = new JProgressBar(0, 100);

        public ProgressBarRenderer() {
            progressBar.setStringPainted(true);
        }

        @Override
        public Component getTableCellRendererComponent(JTable table, Object value,
                                                       boolean isSelected, boolean hasFocus,
                                                       int row, int column) {
            double progress = 0.0;
            if (value instanceof Double) {
                progress = (Double) value;
            }
            progressBar.setValue((int) progress);
            progressBar.setString(String.format("%.1f%%", progress));

            if (progress >= 100) {
                progressBar.setForeground(new Color(50, 150, 50));
            } else {
                progressBar.setForeground(new Color(60, 120, 200));
            }

            return progressBar;
        }
    }
```
