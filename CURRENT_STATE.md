# Project Gal — Complete Project State Document

## What This Project Is

A **BitTorrent-style distributed file sharing system** built as an educational/academic project. It has a **Python backend** (the actual BitTorrent engine) and a **Java Swing frontend** (GUI). They communicate via a local REST API (Flask on localhost:5000).

The project implements the core BitTorrent protocol (BEP-3) from scratch — no BitTorrent libraries are used.

---

## Directory Structure

```
Project_Gal/
├── start.sh                    # One-click launcher for Linux/Mac
├── start.bat                   # One-click launcher for Windows
├── requirements.txt            # Python deps: flask, aiohttp, pytest, pytest-asyncio
├── README.md                   # Project documentation
├── DOWNLOAD_STALLING_DEBUG_GUIDE.md  # Debug history for the stalling bug
├── CURRENT_STATE.md            # This file
│
├── python_engine/              # Python BitTorrent engine (backend)
│   ├── __init__.py             # Package marker
│   ├── __main__.py             # Enables `python -m python_engine`
│   ├── main.py                 # CLI entry point with argparse
│   ├── api_server.py           # Flask REST API (bridges Python ↔ Java)
│   ├── download_manager.py     # Central coordinator: peers, pieces, download loop
│   ├── peer_connection.py      # Single TCP connection to one peer (Peer Wire Protocol)
│   ├── piece_manager.py        # Piece/block tracking, rarest-first algorithm
│   ├── tracker_client.py       # HTTP tracker communication (announce/peer discovery)
│   ├── torrent_metadata.py     # .torrent file parser
│   ├── bencode.py              # Bencode encoder/decoder (BitTorrent serialization format)
│   ├── security.py             # Peer reputation, hash verification, banning
│   └── tests/                  # Unit tests for each module
│       ├── test_bencode.py
│       ├── test_torrent_metadata.py
│       ├── test_tracker_client.py
│       ├── test_peer_connection.py
│       ├── test_piece_manager.py
│       ├── test_download_manager.py
│       ├── test_api_server.py
│       └── test_security.py
│
├── java_gui/                   # Java Swing GUI (frontend)
│   ├── src/
│   │   ├── TorrentClientGUI.java   # Main window, table, log area, toolbar
│   │   └── ApiService.java         # HTTP client for the Python REST API
│   ├── build/                  # Compiled .class files
│   └── lib/
│       └── json.jar            # org.json library for JSON parsing
│
└── data/                       # Runtime data (created at launch)
    ├── downloads/              # Where downloaded files are saved
    ├── state/                  # Download state JSON files (for resume)
    └── history.db              # SQLite database for download history
```

---

## How To Run

### One-click (recommended)
- **Linux/Mac**: `./start.sh` — auto-installs Python/Java if missing via apt/brew/dnf
- **Windows**: `start.bat` — auto-installs via winget, prompts to reopen terminal after install

Both scripts: install deps → compile Java → start API server in background → launch GUI in foreground → kill server on GUI close.

### Manual
```bash
# Terminal 1: Start Python API server
pip install flask aiohttp
python -m python_engine.api_server

# Terminal 2: Compile and run Java GUI
javac -cp java_gui/lib/json.jar -d java_gui/build java_gui/src/*.java
java -cp "java_gui/build:java_gui/lib/json.jar" TorrentClientGUI
```

### CLI only (no GUI)
```bash
python -m python_engine path/to/file.torrent --output ./downloads
```

---

## Architecture Deep Dive

### Communication Flow

```
User clicks "Add Torrent" in GUI
    ↓
TorrentClientGUI.java → HTTP POST /torrents (multipart with .torrent file)
    ↓
api_server.py → TorrentMetadata(torrent_data=...) → DownloadManager.add_torrent()
    ↓
Download.start() → creates asyncio Task for _download_loop()
    ↓
_download_loop():
  1. TrackerClient.announce(event='started') → gets peer list from tracker
  2. _connect_to_peers() → TCP connect + handshake to each peer
  3. Main loop (every 0.1s):
     - reset_stale_pieces(30s timeout)
     - _request_pieces() → send REQUEST messages to unchoked peers
     - _update_speed()
     - Periodic: _cleanup_dead_peers(), reconnect
```

### Threading Model

```
Main Thread (Flask):
  - Handles HTTP requests from Java GUI
  - Uses _run_async() to submit coroutines to the background event loop

Background Thread (asyncio event loop):
  - Runs forever via _loop.run_forever()
  - All BitTorrent protocol work happens here
  - One _message_loop() task per peer connection
  - One _download_loop() task per active download
  - One _choke_loop() task (10s interval)
  - One _keep_alive_loop() task (60s interval)
  - One _periodic_announce_loop() task (tracker interval)

Java EDT (Event Dispatch Thread):
  - Swing GUI updates
  - ScheduledExecutorService polls /torrents every 2 seconds
  - Polls /torrents/<id>/logs for engine log messages
```

---

## Module-by-Module Reference

### bencode.py
Pure encoder/decoder for BitTorrent's serialization format. No external dependencies.
- `encode(data) → bytes` — Encodes int/bytes/str/list/dict to bencode
- `decode(data) → Any` — Decodes bencode bytes to Python objects
- `decode_partial(data) → (value, remaining)` — For stream parsing
- Validates sorted dict keys, no leading zeros in ints, no negative zero

### torrent_metadata.py
Parses .torrent files into structured metadata.
- **`TorrentMetadata(torrent_path=... | torrent_data=...)`** — Main class
  - `announce: str` — Tracker URL
  - `announce_list: List[List[str]]` — Backup trackers
  - `piece_length: int` — Bytes per piece (typically 256KB)
  - `pieces: List[bytes]` — SHA-1 hashes, 20 bytes each
  - `files: List[FileInfo]` — File paths and sizes
  - `info_hash: bytes` — SHA-1 of bencoded info dict (torrent identity)
  - `total_size: int` — Sum of all file sizes
  - `num_pieces: int` — Total piece count
  - `get_piece_length(idx)` — Last piece may be shorter
  - `get_file_offset(piece_idx)` — Maps piece to `[(file_path, offset, length)]` for multi-file torrents
- **`FileInfo`** — Simple `(path, size)` container

### tracker_client.py
HTTP tracker protocol implementation.
- **`TrackerClient(announce_url, info_hash, peer_id, port=6881)`**
  - `announce(event=...) → TrackerResponse` — HTTP GET with url-encoded info_hash, peer_id, stats
  - `start_periodic_announce(callback)` — Background task re-announces at tracker interval
  - `completed()` — Sends 'completed' event
  - `stop()` — Sends 'stopped' event, closes session
  - `update_stats(uploaded, downloaded, left)` — For next announce
- **`TrackerResponse`** — Parses tracker response
  - `peers: List[Peer]` — Supports both compact (6 bytes/peer) and dict format
  - `interval: int` — Re-announce interval in seconds
  - `complete/incomplete` — Seeder/leecher counts
- **`Peer(ip, port, peer_id=None)`** — Hashable, used in sets
- **`generate_peer_id() → bytes`** — 20 bytes: `-PG0001-` + 12 random bytes
- Constants: `DEFAULT_PORT = 6881`, `PEER_ID_PREFIX = b'-PG0001-'`

### peer_connection.py
Single TCP connection implementing the Peer Wire Protocol.
- **`PeerConnection(ip, port, info_hash, peer_id, num_pieces, on_message=...)`**
  - State machine: `am_choking`, `am_interested`, `peer_choking`, `peer_interested`
  - `peer_pieces: List[bool]` — Bitfield of what the peer has
  - `connect()` — TCP connect + handshake (sends/receives 68-byte handshake)
  - `start_message_loop()` — Creates asyncio task for `_message_loop()`
  - `_message_loop()` — Reads messages forever, calls `_handle_message()`, then `on_message` callback
  - `_handle_message()` — Updates state (choking, bitfield, stats), decrements `_pending_requests` on PIECE
  - `send_request(piece_index, begin, length)` — Sends REQUEST message, increments `_pending_requests`
  - `send_interested/not_interested/choke/unchoke/have/bitfield/piece/cancel/keep_alive()`
  - `disconnect()` — Cancels read task, closes writer
  - `has_piece(idx) → bool`, `connected → bool`
  - Stats: `bytes_downloaded`, `bytes_uploaded`, `download_rate`, `_pending_requests`
- **`PeerMessage`** — Parsed message with properties: `piece_index`, `block_offset`, `block_length`, `block_data`, `bitfield_data`
- **`MessageType`** — Enum: CHOKE(0), UNCHOKE(1), INTERESTED(2), NOT_INTERESTED(3), HAVE(4), BITFIELD(5), REQUEST(6), PIECE(7), CANCEL(8), KEEP_ALIVE(-1)
- `can_request → bool` — Checks connection, choking state, and auto-resets stuck `_pending_requests` after 15s with no PIECE response
- `request_capacity → int` — How many more requests we can send (`MAX_PENDING_REQUESTS - _pending_requests`)
- Constants: `BLOCK_SIZE = 16384` (16KB), `MAX_PENDING_REQUESTS = 50`, `CONNECTION_TIMEOUT = 30`, `REQUEST_TIMEOUT = 60`, `MAX_MESSAGE_SIZE = 2MB`

### piece_manager.py
Tracks piece status and implements piece selection.
- **`Block(piece_index, offset, length)`** — Single 16KB block within a piece
  - `data`, `received` — Set when block arrives
  - `requested`, `requested_time`, `requested_by` — Track which peer requested this block and when
  - `is_requestable → bool` — True if not received AND (not requested OR request timed out after 10s)
  - `mark_requested(peer_key)` — Mark block as requested by a peer
  - `clear_request()` — Reset request state so block can be re-requested
  - `BLOCK_REQUEST_TIMEOUT = 10` — Seconds before a requested block can be re-requested
- **`Piece(index, length, expected_hash)`** — One piece (typically 256KB = 16 blocks)
  - `status: PieceStatus` — MISSING → IN_PROGRESS → COMPLETED
  - `blocks: List[Block]` — Created in constructor based on length
  - `submit_block(offset, data) → bool` — Returns True when all blocks received
  - `verify_hash() → bool` — SHA-1 check against expected hash
  - `get_pending_blocks() → List[Block]` — Blocks where `not b.received`
  - `get_requestable_blocks() → List[Block]` — Blocks that can be requested (not received, not recently requested)
  - `clear_peer_requests(peer_key)` — Clear request state for all blocks requested by a specific peer
  - `reset()` — Back to MISSING, clears all block data and request state
- **`PieceManager(num_pieces, piece_length, total_size, piece_hashes)`**
  - `pieces: List[Piece]` — All piece objects
  - `_peer_frequency: Dict[int, int]` — How many peers have each piece
  - `_peer_pieces: Dict[str, Set[int]]` — Per-peer piece sets
  - `_piece_start_times: Dict[int, float]` — When each piece entered IN_PROGRESS
  - `select_piece_rarest_first(peer_pieces) → Optional[int]` — Only selects MISSING pieces, picks from rarest set randomly
  - `select_piece_random(peer_pieces) → Optional[int]` — Random MISSING piece
  - `start_piece(idx) → List[Block]` — Marks IN_PROGRESS, records start time
  - `reset_stale_pieces(timeout)` — Resets pieces IN_PROGRESS longer than timeout
  - `submit_block(piece_idx, offset, data) → bool` — Delegates to Piece
  - `verify_piece(piece_idx) → bool` — Hash check, sets COMPLETED or resets
  - `clear_peer_requests(peer_key)` — Clear block request state across all IN_PROGRESS pieces for a peer (called on choke/disconnect)
  - `find_in_progress_piece(peer_pieces, exclude) → Optional[int]` — Find an IN_PROGRESS piece with requestable blocks (for endgame)
  - Properties: `completed_pieces`, `bytes_downloaded`, `bytes_remaining`, `progress`, `is_complete`

### download_manager.py
Central coordinator for downloads.
- **`Download(torrent, download_dir, state_dir, piece_algorithm, peer_algorithm)`**
  - `id: str` — 8-char UUID
  - `state: DownloadState` — QUEUED/RUNNING/PAUSED/COMPLETED/CANCELLED/ERROR
  - `stats: DownloadStats` — Speed, bytes, timing, peer counts
  - `piece_manager: PieceManager` — Piece tracking
  - `security: SecurityManager` — Peer reputation
  - `_connections: Dict[str, PeerConnection]` — Active peer connections
  - `_known_peers: Set[Peer]` — All discovered peers
  - `_peer_piece: Dict[str, int]` — Per-peer piece assignment (each peer works on one piece at a time)
  - `_executor: ThreadPoolExecutor(2)` — For hash verification and disk I/O off the event loop
  - `_log_buffer: deque(maxlen=200)` — Ring buffer for GUI log polling
  - `_log_counter: int` — Sequence number for incremental polling
  - Key methods:
    - `start()` — Creates `_download_loop()` task
    - `_download_loop()` — Main loop: tracker → connect (non-blocking) → request loop
    - `_connect_to_peers()` — Connects to known peers concurrently (gather). Launched via `create_task()` to avoid blocking
    - `_connect_peer(peer)` — TCP connect + handshake + start message loop
    - `_on_peer_message(conn, message)` — Callback: handles BITFIELD, HAVE, UNCHOKE (immediate requests), CHOKE (clears block requests), PIECE (duplicate guard, executor for hash/disk)
    - `_request_pieces()` — Iterates unchoked peers, delegates to `_request_from_peer()`
    - `_request_from_peer(peer_key, conn)` — Per-peer request strategy: (1) continue current assigned piece, (2) get new MISSING piece, (3) endgame fallback to IN_PROGRESS with timed-out blocks
    - `_send_block_requests(conn, peer_key, blocks, max)` — Send block requests up to capacity, marking blocks as requested
    - `_choke_loop()` — Every 10s: Tit-for-Tat or Round-Robin unchoke decisions
    - `_keep_alive_loop()` — Every 60s: sends keep-alive to all peers
    - `_broadcast_have(piece_idx)` — Concurrent `asyncio.gather()` HAVE to all peers, launched as fire-and-forget `create_task()`
    - `_write_piece_sync(piece_idx)` — Synchronous disk write (runs in thread executor)
    - `_write_piece(piece_idx)` — Async wrapper using executor
    - `_cleanup_dead_peers()` — Removes dead peers, clears their piece assignments and block requests
    - `_complete_download()` — Sets COMPLETED state, announces to tracker
    - `_log(message)` — Adds to ring buffer with sequence number
    - `get_logs(since_seq) → List[dict]` — For GUI polling
    - `pause()`, `resume()`, `cancel()` — State management
    - `get_status() → dict` — JSON-serializable status
- **`DownloadManager(download_dir, state_dir)`**
  - `downloads: Dict[str, Download]` — All downloads by ID
  - `add_torrent(torrent, piece_algo, peer_algo) → Download`
  - `start/pause/resume/cancel_download(id)`
  - `get_all_status() → List[dict]`, `get_download(id) → Download`
- **`AlgorithmType`** — RAREST_FIRST, RANDOM, TIT_FOR_TAT, ROUND_ROBIN
- **`DownloadState`** — QUEUED, RUNNING, PAUSED, COMPLETED, CANCELLED, ERROR
- Constants: `CHOKE_INTERVAL = 10`, `MAX_UNCHOKED_PEERS = 4`, `MAX_CONNECTIONS = 50`, `KEEP_ALIVE_INTERVAL = 60`, `PIECE_REQUEST_TIMEOUT = 30`, `PEER_CLEANUP_INTERVAL = 15`

### security.py
Peer reputation tracking and banning.
- **`SecurityManager`**
  - `verify_piece(data, expected_hash) → bool` — SHA-1 check
  - `report_hash_failure(peer_key, piece_idx)` — Increments failure count, may ban
  - `report_successful_piece(peer_key, piece_idx)` — Increments success count
  - `report_protocol_violation(peer_key, description)` — May ban after threshold
  - `is_peer_banned(peer_key) → bool`
- **`PeerReputation`** — Per-peer tracking: hash_failures, protocol_violations, successful_pieces, trust_score
- Thresholds: `MAX_HASH_FAILURES_PER_PEER = 3`, `MAX_PROTOCOL_VIOLATIONS_PER_PEER = 5`
- Includes `TRACKER_PRIVACY_ANALYSIS` docstring analyzing privacy implications

### api_server.py
Flask REST API bridging Python engine and Java GUI.
- Runs a persistent asyncio event loop in a background daemon thread
- `_run_async(coro, timeout=60)` — Submits coroutines to the background loop from Flask threads
- SQLite database at `data/history.db` with tables: torrents, performance_stats, algorithm_stats, events
- **Endpoints:**
  - `POST /torrents` — Start download (multipart .torrent upload or JSON path)
  - `GET /torrents` — All download statuses
  - `GET /torrents/<id>` — Single download status
  - `POST /torrents/<id>/pause` — Pause download
  - `POST /torrents/<id>/resume` — Resume download
  - `POST /torrents/<id>/cancel` — Cancel download
  - `GET /torrents/<id>/logs?since=N` — Incremental log polling (sequence-based)
  - `GET /history` — Download history from SQLite
  - `GET /events?limit=N` — Event log from SQLite
  - `GET /algorithm-stats/<id>` — Rarest-first selection statistics
  - `GET /health` — Health check

### main.py (CLI)
Command-line torrent downloader with progress display.
- `python -m python_engine path/to/file.torrent [-o DIR] [--piece-algorithm rarest_first|random] [--peer-algorithm tit_for_tat|round_robin] [-v]`
- Real-time progress bar: percentage, size, speed, peers, ETA, elapsed
- Graceful Ctrl+C via asyncio signal handlers

### TorrentClientGUI.java
Java Swing main window.
- Downloads table with columns: Name, Size, Progress (bar renderer), Speed, Peers, State, ID
- Toolbar: Add Torrent (file chooser), Pause, Resume, Cancel, History, Piece/Peer algorithm dropdowns
- Event log text area at bottom (split pane)
- `ScheduledExecutorService` polls status every 2 seconds
- Polls `/torrents/<id>/logs?since=N` for incremental engine log messages
- `logSeqTracker: Map<String, Integer>` tracks last seen sequence per torrent
- Hebrew title: "מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent"

### ApiService.java
HTTP client using java.net.http.HttpClient.
- `startDownload(File) → String` — Multipart POST with .torrent file, returns torrent ID
- `getStatus() → List<TorrentStatus>` — All downloads
- `pause/resume/cancel(id)` — Control actions
- `getHistory() → String` — JSON history
- `getLogs(id, sinceSeq) → JSONArray` — Incremental log polling
- `isServerAvailable() → boolean` — Health check
- `TorrentStatus` — Inner class with all status fields, `fromJson()` factory

---

## BitTorrent Protocol Implementation Details

### Handshake (68 bytes)
```
[1 byte: pstrlen=19][19 bytes: "BitTorrent protocol"][8 bytes: reserved=0x00]
[20 bytes: info_hash][20 bytes: peer_id]
```

### Message Format
```
[4 bytes: length prefix (big-endian)][1 byte: message ID][payload...]
```
Length=0 → keep-alive. Messages: CHOKE(0), UNCHOKE(1), INTERESTED(2), NOT_INTERESTED(3), HAVE(4), BITFIELD(5), REQUEST(6), PIECE(7), CANCEL(8).

### Piece Structure
- Torrent file is split into fixed-size pieces (typically 256KB)
- Each piece is split into blocks of 16KB (BLOCK_SIZE)
- A 256KB piece = 16 blocks
- Last piece may be smaller than piece_length

### Download Flow
1. Parse .torrent → get tracker URL, info_hash, piece hashes
2. Announce to tracker → get peer list (typically 50 peers)
3. TCP connect to each peer (non-blocking) → handshake → exchange bitfields
4. Send INTERESTED to peers that have pieces we need
5. Wait for UNCHOKE from peer → immediately request pieces (event-driven)
6. Each peer is assigned one piece at a time. Blocks are requested up to `MAX_PENDING_REQUESTS=50` with per-block tracking
7. Receive PIECE messages with block data. Duplicates for completed pieces are silently dropped
8. When all blocks received → SHA-1 verify (in thread executor) → write to disk (in thread executor) → broadcast HAVE (fire-and-forget task)
9. On piece completion, peer immediately gets new work assigned
10. On choke, peer's block requests are cleared so other peers can pick them up
11. Stuck `_pending_requests` counters auto-reset after 15s with no response
12. Repeat until all pieces complete

### Tit-for-Tat Algorithm (every 10 seconds)
1. Get all interested peers
2. Sort by how much they've uploaded to us (contribution)
3. Unchoke top 4 peers (MAX_UNCHOKED_PEERS)
4. Optimistic unchoke: randomly unchoke 1 additional peer
5. Choke all others

---

## Resolved Bug: Download Stalling at 15-20% (FIXED)

**See `DOWNLOAD_STALLING_DEBUG_GUIDE.md` for the full debug history (6 failed attempts before the final fix).**

The download previously stalled after 300-600 pieces (15-20%). This was fixed with a comprehensive pipeline redesign addressing all root causes simultaneously:

1. **Per-peer piece assignment** — Each peer works on one piece at a time, preventing block scattering and peer convergence
2. **Block request tracking with timeouts** — Blocks track who requested them and when; re-requestable after 10s timeout
3. **Choke handling** — When a peer chokes, their block requests are immediately cleared so other peers can pick them up
4. **Stuck counter recovery** — `_pending_requests` auto-resets after 15s with no PIECE response
5. **Non-blocking initial connect** — `asyncio.create_task()` instead of blocking await
6. **Non-blocking broadcast** — HAVE messages via concurrent `asyncio.gather()` in a fire-and-forget task
7. **Duplicate completion guard** — PIECE messages for already-completed pieces are silently skipped
8. **Heavy work off event loop** — Hash verification and disk I/O run in a thread pool executor
9. **Pipeline depth** — `MAX_PENDING_REQUESTS` increased from 10 to 50
10. **Immediate pipelining** — New work assigned on UNCHOKE and piece completion events

Downloads now complete successfully.

---

## Testing

```bash
# Run all tests
python -m pytest python_engine/tests/ -v

# Run specific test
python -m pytest python_engine/tests/test_piece_manager.py -v
```

Test files exist for all modules. Tests use pytest and pytest-asyncio.

---

## Dependencies

### Python
- `flask>=2.3.0` — REST API server
- `aiohttp>=3.8.0` — Async HTTP client for tracker communication
- `pytest>=7.0.0` + `pytest-asyncio>=0.21.0` — Testing

### Java
- JDK 11+ (Temurin 21 recommended)
- `org.json` (json.jar) — JSON parsing, auto-downloaded by startup scripts

### System
- Python 3.8+
- Java JDK 11+
- Network access (for tracker communication and peer connections)

---

## Git Branch

Development branch: `claude/bitTorrent-file-sharing-system-UcIZc`

The download stalling bug has been fixed. The `DOWNLOAD_STALLING_DEBUG_GUIDE.md` documents the 6 failed attempts that informed the final successful fix.
