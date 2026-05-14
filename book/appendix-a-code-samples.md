# נספח א' – קטעי קוד מרכזיים

נספח זה מרכז קטעי קוד ארוכים ומרכזיים מהפרויקט (מודולים שלמים,
מחלקות גדולות, אלגוריתמים במלואם, סכמת מסד נתונים) שאינם מתאימים
לשילוב ישיר בתוך גוף הפרקים. בתוך הפרקים עצמם מופיעים קטעים קצרים
(10–20 שורות) של החלקים המרכזיים, עם הפניה צולבת לרשומה המתאימה כאן.

מבנה כל רשומה:
- **כותרת ממוספרת** (א.1, א.2, ...).
- **נתיב הקובץ** בריפו.
- **תיאור תפקיד הרכיב במערכת**.
- **קטע הקוד המלא**.

---

## א.1 — `TorrentMetadata._parse_metadata`

- **קובץ**: `python_engine/torrent_metadata.py` (שורות 79–153).
- **תפקיד**: parsing מלא של מילון bencoded מקובץ `.torrent`,
  כולל חישוב `info_hash` (SHA-1 על ה-info dict), בידוד
  pieces ל-hashים בני 20 בתים, ופירוק single-file
  ל-multi-file mode.

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
            f"Pieces data length ({len(pieces_data)}) "
            f"is not a multiple of 20")
    self.pieces = [pieces_data[i:i+20]
                   for i in range(0, len(pieces_data), 20)]
    self.num_pieces = len(self.pieces)

    # Name (required)
    if b'name' not in info:
        raise TorrentMetadataError("Missing 'name' in info")
    self.name = info[b'name'].decode('utf-8')

    # Parse files (single vs multi-file mode)
    self.files = []
    if b'files' in info:
        for file_dict in info[b'files']:
            path_parts = [p.decode('utf-8') for p in file_dict[b'path']]
            file_path = os.path.join(self.name, *path_parts)
            file_size = file_dict[b'length']
            self.files.append(FileInfo(file_path, file_size))
    else:
        if b'length' not in info:
            raise TorrentMetadataError(
                "Missing 'length' in single-file info")
        self.files.append(FileInfo(self.name, info[b'length']))
    self.total_size = sum(f.size for f in self.files)
    # Optional fields: comment, created_by, creation_date (omitted)
```

---

## א.2 — `PeerConnection._read_message` + `_handle_message`

- **קובץ**: `python_engine/peer_connection.py` (שורות 245–347).
- **תפקיד**: parsing הודעות peer wire protocol עם ולידציית
  אורך וטיפול ב-state machine של ה-choking/interest.

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
    if length > MAX_MESSAGE_SIZE:
        raise PeerConnectionError(
            f"Message too large: {length} bytes (max {MAX_MESSAGE_SIZE})")
    try:
        payload = await asyncio.wait_for(
            self._reader.readexactly(length),
            timeout=REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        raise PeerConnectionError("Payload read timeout")
    except asyncio.IncompleteReadError:
        return None
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
    if message.type == MessageType.KEEP_ALIVE:
        return
    elif message.type == MessageType.CHOKE:
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
        # ... (update download_rate samples — see source)
    if self.on_message:
        await self.on_message(self, message)
```

---

## א.3 — `PieceManager.select_piece_rarest_first` (מלא)

- **קובץ**: `python_engine/piece_manager.py` (שורות 279–317).
- **תפקיד**: בחירת piece נדיר ביותר מבין pieces שעדיין
  חסרים, שה-peer מציע, ושעוד לא בתהליך.

הקוד המלא הוצג בפרק 21.3.1. סיבוכיות: O(N). פירוט מלא של
ניתוח הסיבוכיות מופיע בפרק 15.4.1.

---

## א.4 — `Download._tit_for_tat_unchoke` (מלא)

- **קובץ**: `python_engine/download_manager.py` (שורות 519–564).
- **תפקיד**: ה-choke/unchoke algorithm של BitTorrent
  הקלאסי — מעודד reciprocity בין peers.

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
    # Sort by download rate from this peer (how much they
    # contribute to us)
    interested_peers.sort(
        key=lambda x: x[1].bytes_downloaded, reverse=True)
    # Select top K (MAX_UNCHOKED_PEERS = 4)
    to_unchoke = set()
    for i, (key, conn) in enumerate(interested_peers):
        if i < MAX_UNCHOKED_PEERS:
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

## א.5 — `Download._download_loop` (מלא)

- **קובץ**: `python_engine/download_manager.py` (שורות 203–270).
- **תפקיד**: ה-orchestrator הראשי של ההורדה — מתאם tracker,
  peers, piece requests, ו-stats.

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

<!-- רשומות יתווספו כאן עם התקדמות כתיבת הפרקים -->
