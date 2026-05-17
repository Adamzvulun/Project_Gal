# Code Audit — Ground Truth

Source: focused audit by Explore agent against `python_engine/` and `java_gui/`.
Compiled: 2026-05-17.
Purpose: what the code *actually* does, so book claims and fixes can cite real file:line refs.

## Headline

The teacher assumed the code was as shallow as the book suggested. It is not. The code is substantive and largely correct against BEP-3. The book's failure is one of presentation, not implementation — except for the few real gaps listed at the bottom.

## Inventory

```
python_engine/          5,144 LOC total
  api_server.py         509
  bencode.py            231
  download_manager.py   891
  main.py               190
  peer_connection.py    520
  piece_manager.py      473
  security.py           326
  torrent_metadata.py   241
  tracker_client.py     337
  tests/              1,421  (172 test functions across 8 files)

java_gui/src/         1,641 LOC total
  AlgorithmStatsDialog.java  562
  ApiService.java            430
  TorrentClientGUI.java      649
```

Grand total: ~6,785 LOC (book undersells at 5,360). 172 test functions (book undercounts at 160).

## Component-by-component truth

### 1. Bencode parser (`bencode.py`)
- `encode()` lines 25-48; `decode()` lines 51-71; `_decode_dict()` lines 210-231.
- **Canonical key ordering**: lines 110-123 sort keys lexicographically as bytes before encoding.
- **Strict validation**: rejects leading zeros in ints (157-162), negative zero (159-160), unsorted dict keys on decode (222-223).
- `decode_partial()` for stream parsing exists (74-89).
- Bool distinguished from int (37).
- **Missing**: streaming decoder for huge files (loads full torrent into memory); recovery from truncated input.

### 2. info_hash (`torrent_metadata.py:100-102`)
```python
info_encoded = bencode.encode(info)
self.info_hash = hashlib.sha1(info_encoded).digest()
```
Info dict is **re-encoded** from the parsed Python dict (not the original bytes), then SHA-1'd. This is correct: canonical re-encoding produces deterministic bytes regardless of source dict order.

### 3. Peer wire protocol (`peer_connection.py`)
- **Handshake bytes** (lines 183-189, 206-216):
  - 1 byte pstrlen (0x13) + 19 bytes "BitTorrent protocol" + 8 reserved + 20 info_hash + 20 peer_id = 68 bytes.
  - `HANDSHAKE_LEN` constant at line 20.
- **Length-prefix framing** (lines 245-286): uses `asyncio.StreamReader.readexactly(4)` for length, then `readexactly(length)` for payload. Real incremental parsing, handles partial reads transparently. Handles `IncompleteReadError`. Returns `KEEP_ALIVE` for length=0.
- **Messages implemented** (lines 28-39): CHOKE, UNCHOKE, INTERESTED, NOT_INTERESTED, HAVE, BITFIELD, REQUEST, PIECE, CANCEL, plus KEEP_ALIVE special case. All 9 core BEP-3 messages.
- **State tracking** (lines 132-136): four boolean flags `am_choking`, `am_interested`, `peer_choking`, `peer_interested`. Implicit FSM (not an enum), but rules enforced (e.g. can't request if `peer_choking`, line 432).
- **Missing**: BEP-6 SUGGEST_PIECE/ALLOWED_FAST; BEP-10 extension protocol (reserved-byte check commented out at line 214).

### 4. Rarest-first (`piece_manager.py:279-317`)
- True rarest-first: scans missing pieces, finds min frequency, builds tie set, `random.choice()` on the tie set (line 313). The random-tie-break is the thundering-herd fix.
- **Pipelining / endgame-ish** (lines 478-486 + `download_manager.py:432-486`): when no MISSING pieces available, falls back to IN_PROGRESS pieces with stale blocks. Up to 50 requests per peer queued (`MAX_PENDING_REQUESTS` line 25). Not a distinct endgame "mode", just a fallback path.
- **Stale-piece reset** (lines 357-375): 10-second timeout per piece; `reset_stale_pieces()` reverts to MISSING.
- **Peer pieces tracking**: bitfield (220-244) and HAVE messages update `_peer_frequency`. Peer removal cleans up contributions (265-277).

### 5. Tit-for-tat (`download_manager.py:519-587`)
- **Current metric** (line 537): sorts interested peers by `conn.bytes_downloaded` — cumulative since session start, NOT a sliding window. This is the major simplification the teacher caught.
- **Top-K + optimistic**: `MAX_UNCHOKED_PEERS = 4` (line 25 vicinity) plus exactly one random peer outside the top-4 (lines 545-553).
- **Choke interval**: 10s (`CHOKE_INTERVAL` line 29).
- **No snubbing**: no auto-disconnect or de-prioritization when peer goes silent.
- **No seeding mode**: post-completion, `bytes_downloaded` is permanently zero for everyone → effectively random unchoke.

### 6. SHA-1 verification (`piece_manager.py:114-117`, `download_manager.py:375-411`)
- Whole-piece (not streaming): all blocks collected in `_data` bytearray, then `hashlib.sha1(bytes(self._data)).digest()` compared to expected.
- Runs in thread-pool executor (`download_manager.py:377`) to keep event loop unblocked.
- Failure path: `SecurityManager.report_hash_failure()` (`security.py:109-129`); peer banned after 3 failures (`MAX_HASH_FAILURES_PER_PEER` line 17).

### 7. asyncio + Flask architecture (`api_server.py:39-74`)
- Flask runs synchronously on main thread.
- Daemon thread runs `asyncio.new_event_loop()` + `loop.run_forever()`.
- Flask endpoints submit coroutines via `asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=60)`.
- Disk I/O delegated to ThreadPoolExecutor; hash verification in executor.
- **Hazard called out**: `_save_state()` (lines 765-794) writes JSON synchronously from async context — could block event loop on slow disk. Mitigated by being called only on state transitions, not in hot path.
- Cancellation: `_read_task.cancel()` + await exception handling at lines 468-472.

### 8. Java Swing GUI (`TorrentClientGUI.java`, `ApiService.java`)
- **EDT respect**: 20+ uses of `SwingUtilities.invokeLater()` for cross-thread GUI updates.
- **Polling**: `ScheduledExecutorService` polls every 2 seconds (`scheduleAtFixedRate`).
- **API down handling**: try-catch around HTTP calls (lines 437-451); logs "[engine] error", no crash.

### 9. Tracker client (`tracker_client.py`)
- **HTTP only** via aiohttp (no UDP).
- **Compact peer format** parsed (lines 104-118): 6 bytes per peer, 4-byte IP + 2-byte big-endian port.
- **BEP-12 announce-list**: parsed (lines 87-91) but **not used for fallback** — only first tracker is contacted.
- Announce params: info_hash, peer_id, port, uploaded, downloaded, left, compact=1, optional event + trackerid.
- **No IPv6** (only 4-byte IP parsing).

### 10. Tests (`python_engine/tests/`)
- 8 files, 1,421 LOC, 172 test functions.
- All unit tests with mocks. **No real-network or live-peer integration tests anywhere.**
- `test_peer_connection.py` mocks `asyncio.open_connection()` but does not simulate a real peer server.

### 11. Persistence
- **JSON state** (`download_manager.py:765-794`): per-download file at `data/state/{id}.json`. Stores piece status array, byte counters, peer list, timestamps. Written on pause/cancel/periodically.
- **SQLite history** (`api_server.py:90-159`, `:162-200`): tables `torrents`, `performance_stats`, `algorithm_stats`, `events`. Populated **only after completion**.
- **`_load_state` does NOT exist.** Paused downloads cannot resume across process restarts. (Ch.25 of book admits this.)

### 12. Production gaps explicitly admitted by the code itself
1. BEP-10 extension protocol (commented out at `peer_connection.py:214`).
2. BEP-12 tracker fallback (parsed but unused).
3. MSE/PE protocol encryption (none).
4. DHT (none).
5. Magnet links (.torrent only).
6. IPv6 (compact peer parser is IPv4-only).
7. Resume on restart (state saved, never loaded).
8. Seeding mode (no distinct logic post-completion).
9. NAT traversal / incoming connections (outgoing only).
10. Sliding-window contribution (cumulative counter only).
11. Snubbing (no detection).

## Bottom line for the book revision

- Items 1-7 in the truth section above are **real depth** the book should showcase — with file:line citations — instead of generic descriptions.
- Items 5, 7, 10, 11 (tit-for-tat metric, resume, sliding window, snubbing) are the genuine code gaps this revision is filling.
- Item 8 (seeding mode) is being added.
- Everything else under "production gaps" goes into the new §25.5 honest limitations list.
