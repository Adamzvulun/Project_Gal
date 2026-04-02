# Download Stalling Bug — Debug History & Guide for Next Attempt

## The Problem

When downloading a real torrent (debian-13.4.0-amd64-netinst.iso, 790MB, 3016 pieces, 256KB per piece = 16 blocks of 16KB each), the download starts fast (~10MB/s with 17-22 unchoked peers) but stalls after downloading 7-19% of the file. After stalling, it either downloads one piece at a time or stops completely.

## Architecture Overview

- `download_manager.py` — Main loop runs `_request_pieces()` every 0.1s, handles peer messages via `_on_peer_message()` callback
- `peer_connection.py` — One per peer. Has its own `_message_loop()` asyncio task reading messages. Tracks `_pending_requests` counter (incremented on `send_request`, decremented on PIECE response). `MAX_PENDING_REQUESTS = 10`. `send_request()` raises `PeerConnectionError` if `_pending_requests >= MAX`
- `piece_manager.py` — Tracks pieces (MISSING → IN_PROGRESS → COMPLETED). `get_pending_blocks()` returns blocks where `not b.received`. `select_piece_rarest_first()` only selects MISSING pieces. `start_piece()` marks piece as IN_PROGRESS and returns its blocks.

## Key Code Flow

1. Every 0.1s, `_request_pieces()` iterates all peers
2. For each unchoked peer, `select_piece_rarest_first()` picks a MISSING piece
3. `start_piece()` marks it IN_PROGRESS and returns blocks
4. Blocks are sent via `send_request()` until `MAX_PENDING_REQUESTS` hit
5. Peer's `_message_loop` receives PIECE responses → calls `_on_peer_message` callback
6. `submit_block()` stores data, returns `is_complete=True` when all blocks received
7. If complete → `verify_piece()` (SHA1 hash) → `_write_piece()` (disk) → `_broadcast_have()` (tell all peers)

## Original Bugs (before any fixes)

1. **`_request_pieces()` only selected MISSING pieces**: Once a piece was IN_PROGRESS, no more blocks were requested for it. First 10 blocks sent, remaining 6 never requested.
2. **Duplicate verification spam**: Multiple peers sending blocks for the same piece, each triggering `verify_piece` + logging 50-80 times.
3. **`_broadcast_have()` is synchronous**: Sequentially `await`s `send_have()` to all 21 peers in the piece-completion callback, potentially blocking the peer's message loop.
4. **Initial `await _connect_to_peers()` blocks**: Waits for ALL 50 connection attempts (some timing out at 30s) before `_request_pieces` ever runs.

---

## Attempt 1: Fix piece request logic + duplicate log spam (commit 9fc2983)

**What we did:**
- Added early return in `_on_peer_message` for PIECE messages when piece is already COMPLETED
- Rewrote `_request_pieces()` to first check IN_PROGRESS pieces with pending blocks, then fall back to new MISSING pieces
- Added `claimed_pieces` dict so each peer gets a different IN_PROGRESS piece within one `_request_pieces()` call

**Outcome:** Download worked initially (~228 pieces fast burst) but stalled for ~2 minutes, then got a small burst of ~7 pieces, then stalled permanently.

**Why it didn't work:** `get_pending_blocks()` returns blocks where `not b.received`, but there's no tracking of whether a block was already REQUESTED and is in-flight. So the same blocks were re-requested every 0.1s loop, inflating `_pending_requests` far beyond MAX. When responses came back, each only decremented by 1, so the counter never came back down.

## Attempt 2: Track requested blocks (commit 7c6281c)

**What we did:**
- Added `block.requested = True/False` flag to Block class
- `get_pending_blocks()` changed to return blocks where `not b.received and not b.requested`
- Set `block.requested = True` when `send_request` called, reset on error

**Outcome:** Got to ~19% much faster than before, but then stalled. After the initial burst, status showed `in_progress=17-21` but no pieces completing. Periodic small bursts every ~20 seconds aligned with the `PIECE_REQUEST_TIMEOUT = 30` stale reset.

**Why it didn't work:** When a peer chokes us (common in BitTorrent — peers frequently choke/unchoke), the peer silently drops all our pending requests. `PeerConnection` sets `_pending_requests = 0` on CHOKE, but the blocks remain `requested = True`. Since `get_pending_blocks()` skips requested blocks, those blocks are stuck forever until the 30-second stale piece timeout resets the entire piece.

## Attempt 3: Block request timeout + non-blocking connect + immediate pipelining (commit 4adc2f8)

**What we did:**
- Added `block.requested_time` timestamp; `get_pending_blocks()` treats blocks as re-requestable after 15 seconds
- Changed initial `await _connect_to_peers()` to `asyncio.create_task()` (non-blocking)
- Added `_request_from_peer()` method called from `_on_peer_message` on piece completion for immediate pipelining
- `_request_pieces()` now calls `_request_from_peer()` for each peer

**Outcome:** No more 22-second initial delay (fixed!). Download reaches ~300 pieces fast, then slows to 1-3 pieces every few seconds with periodic bursts every ~15 seconds.

**Why it didn't work:** `_request_from_peer()` checked IN_PROGRESS pieces FIRST, causing all 17 peers to converge onto the same few pieces when getting new work. Status showed `in_progress=9-10` despite 17 unchoked peers. All peers fighting over the same pieces instead of working in parallel.

## Attempt 4: Prefer new MISSING pieces (commit a6f3bcc)

**What we did:**
- Swapped the order in `_request_from_peer()`: try new MISSING piece first, fall back to IN_PROGRESS only for end-game

**Outcome:** `in_progress=1133` but `pieces=0/3016` — over 1000 pieces started but NONE completing!

**Why it didn't work:** Without tracking which piece a peer is currently working on, each peer started a BRAND NEW piece on every 0.1s loop iteration (whenever `_pending_requests` dropped by 1). Each piece got 1-2 blocks, none completing because each needs all 16.

## Attempt 5: Track peer-to-piece assignment (commit f4a98f6)

**What we did:**
- Added `_peer_piece: Dict[str, int]` mapping each peer to its current piece
- `_request_from_peer()` continues peer's current piece first, only starts new piece when current is complete
- Clean up assignment on peer disconnect

**Outcome:** Partially better — `in_progress=21` with 21 peers, but still stalled at ~18% (~562 pieces). Then only 1 piece in 24 seconds, then nothing.

**Why it didn't work:** Combination of issues: (1) `_pending_requests` counter getting stuck at MAX when peers stop responding (counter never decrements if no responses arrive, even though the requests are effectively lost), (2) `_broadcast_have` still blocking 21 sequential network writes in the callback.

## Attempt 6: Stale counter reset + non-blocking broadcast (commit 990b24b)

**What we did:**
- Added `_last_piece_received` timestamp to PeerConnection
- In `_request_from_peer()`, reset `_pending_requests` to 0 if no PIECE response in 10 seconds
- Made `_broadcast_have()` fire each HAVE as independent `asyncio.create_task()`
- Removed `MAX_PENDING_REQUESTS` check from `send_request()` (let caller handle)
- Added "wait for responses" logic: if current piece has all blocks requested but not all received, return without starting new piece

**Outcome:** Still stalled at ~18%.

**Why it didn't work:** Not fully diagnosed. The "wait for responses" logic may have been too conservative — peers wait idle while blocks are in flight, rather than pipelining multiple pieces. The stale counter reset at 10 seconds may not have been enough, or other timing issues with the asyncio event loop processing.

---

## Key Observations Across All Attempts

1. **The initial burst always works**: First 200-500 pieces download at ~10MB/s with 17+ peers. The pipeline is healthy during this phase.

2. **The stall always happens around 15-20%**: Something changes fundamentally around the 300-600 piece mark.

3. **`in_progress` pieces accumulate**: Before stalling, there are always pieces stuck in IN_PROGRESS that never complete.

4. **Speed counter goes stale**: `speed=10945.3KB/s` stays frozen, meaning `_update_speed()` isn't seeing new `bytes_downloaded`.

5. **Peers remain connected and unchoked**: The log shows "UNCHOKED" messages throughout the stall. Peers aren't disconnecting.

6. **30-second stale timeout rescues a few pieces**: Periodic small bursts align with `PIECE_REQUEST_TIMEOUT`, confirming pieces are stuck IN_PROGRESS.

7. **The `_pending_requests` counter is fragile**: It's incremented on send, decremented on receive, but has no protection against desync (lost requests, chokes, timeouts).

## Core Unsolved Design Issues

1. **No per-block peer tracking**: We don't know which peer was sent which block. When blocks are lost (choke, disconnect), we can't efficiently recover.

2. **`_broadcast_have` in the callback chain**: Even when made async, the piece-completion callback (`_on_peer_message`) does heavy work: SHA1 hash verification, disk I/O, broadcasting, new piece selection. This all runs inside the peer's `_message_loop`, delaying processing of further messages from that peer.

3. **Single-piece-per-peer model vs reality**: Real BitTorrent clients pipeline requests across multiple pieces per peer. Our model of "one piece per peer" means a single lost block can idle a peer for the full timeout duration.

4. **`select_piece_rarest_first` returns only MISSING pieces**: There's no mechanism to top up an IN_PROGRESS piece from a different peer when the original peer goes slow/dead, without the coordination problems of multiple peers on one piece.

5. **Event loop contention**: With 20+ peer message loops, the main request loop, choke timer, and keep-alive timer all sharing one asyncio event loop, heavy processing in callbacks (hash, disk I/O, broadcast) can starve other tasks.

## Files to Modify

- `python_engine/download_manager.py` — `_request_pieces()`, `_on_peer_message()`, `_broadcast_have()`, `_download_loop()`
- `python_engine/peer_connection.py` — `_pending_requests` tracking, `send_request()`, `MAX_PENDING_REQUESTS`
- `python_engine/piece_manager.py` — `Block` class, `get_pending_blocks()`, `Piece.reset()`

## Suggestions for Next Attempt

- Consider removing `_pending_requests` entirely and using a simpler flow-control mechanism
- Consider running piece verification and disk writes in a thread executor (`loop.run_in_executor`) to avoid blocking the event loop
- Consider a completely different request strategy: each peer maintains a request queue, blocks are assigned round-robin, timed out blocks are automatically reassigned
- Look at how libtorrent or other production clients handle request pipelining
- The `_broadcast_have` should definitely be non-blocking (fire-and-forget tasks)
- The initial `await _connect_to_peers()` should definitely be non-blocking
- Maybe increase `MAX_PENDING_REQUESTS` to 50+ (real clients use higher values)
- Consider whether the 0.1s polling loop is the right model vs event-driven
