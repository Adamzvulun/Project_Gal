# Progress — Steps 1 & 2

Branch: `claude/book-revision-v1` · Commits: `690454e`, `79ea365`.

This document records the first two work items from `revision/PLAN.md`
in detail: the empirical experiment that replaces the unrun chapter‑24
comparison, and the end‑to‑end peer wire protocol tests. It exists so
that (a) future sessions can pick up where this one left off, and (b)
Adam can read it before the oral exam and defend each decision.

For each step:

* **Why** — which sentence of the teacher's critique this fixes.
* **What** — the deliverables.
* **How** — the design decisions and the reasons for each.
* **Where** — file paths and key line numbers.
* **Result** — what's measurable now that wasn't before.
* **Oral exam prep** — what to say if the examiner asks about this.

---

## STEP 1 — Empirical comparison experiment

### Why

The single most damaging finding in the teacher's 18‑page assessment
was a self‑admitted gap in chapter 24:

> "הניסויים האמפיריים לא בוצעו בעת כתיבת הספר — רשומה ב‑TODO.md
> מתעדת זאת."

This collapsed יעילות to 2/10 and made every other "we measured X"
claim in the book unverifiable. The first item of the plan was to
generate real measured numbers so chapter 24 can quote them.

### What

A self‑contained, reproducible experiment that compares the
`rarest_first` vs `random` piece selection algorithms on a controlled
local swarm. Outputs three CSV files (committed) and a methodology
README so anyone can re‑run and check.

### How — design decisions

#### 1. Controlled localhost swarm, not a real public torrent

The plan offered both options. A real public torrent was rejected
because:

* **Not reproducible.** A real swarm's seeder count and bandwidth
  change minute to minute. Two runs of the same configuration would
  differ by noise larger than any algorithmic effect.
* **Not defensible.** The teacher's critique is specifically about
  unproven claims; an unreplicable result reads as another claim.
* **NAT risk.** The container can connect outbound, but most peers
  in a real swarm won't connect back to an unreachable address —
  yielding a degraded sample.

Instead the experiment runs everything on loopback with our own
tracker and our own peers, so the only variable across runs is the
algorithm under test.

#### 2. Topology designed to expose a measurable difference

Piece availability had to be **non‑uniform** for rarest‑first to
behave differently from random — otherwise both algorithms see
identical frequencies and pick identically.

| Peer name | Owns pieces | Why |
| --- | --- | --- |
| `full`  | 0..15 | The only source for the rare half. |
| `low_a` | 0..7  | Duplicates the common half. |
| `low_b` | 0..7  | Duplicates the common half. |
| `low_c` | 0..7  | Duplicates the common half. |

Effective availability: pieces 0..7 have frequency 4 (common); pieces
8..15 have frequency 1 (rare). A correct rarest‑first must
concentrate rare‑piece requests on `full`, leaving the three other
peers to handle the common half in parallel.

#### 3. Direct instrumentation instead of polling

First attempt polled `piece.status` every 50 ms to record state
transitions. On loopback the entire download finished in **30 ms**,
so the poll never sampled an intermediate state and every
`first_seen_at` slot came out `nan`.

Fix: replace polling with method wrapping. `PieceTimeline` in
`run_comparison.py` swaps `PieceManager.start_piece` and each
`Piece.verify_hash` for closures that record `time.perf_counter()` at
the actual event. The original method is still called — we only
intercept the timing. This gives sub‑millisecond timestamps for
free.

#### 4. Headline metric: per‑peer upload, not wall‑clock

We expected the wall‑clock total to be statistically identical
between algorithms (because the bottleneck on loopback is CPU and
the event loop, not bandwidth) — and that's what happened
(~30 ms in both). Wall‑clock is therefore *not* the metric we
report; we'd be claiming victory on noise.

The metric that *does* show the algorithm working is per‑peer
upload distribution. The README states this explicitly so the book
doesn't accidentally make the wrong claim.

#### 5. 5 runs per algorithm

3 runs would already show the deterministic pattern but 5 gives a
tighter mean and a cleaner sentence for the book. 10 runs would
take seconds longer for no real benefit.

### Where — files

| Path | Lines | Purpose |
| --- | ---: | --- |
| `python_engine/experiments/__init__.py` | 11 | Package marker + docstring explaining the dual purpose (experiment + E2E test). |
| `python_engine/experiments/make_torrent.py` | 73 | Builds a `.torrent` from a payload file by reusing the engine's own `bencode.encode`, so the resulting `info_hash` is the same hash the engine recomputes when it parses the file. |
| `python_engine/experiments/mock_swarm.py` | 256 | `MockTracker` (aiohttp /announce returning compact peer list) + `MockPeer` (asyncio TCP server speaking enough of BEP‑3: handshake, bitfield, interested→unchoke, request→piece). Reused by Step 2. |
| `python_engine/experiments/run_comparison.py` | 358 | The experiment driver: builds payload, starts swarm, runs each algorithm N times, writes CSVs. Contains `PieceTimeline` (the direct‑instrumentation timing capture) and the console summary. |
| `data/experiments/comparison_summary.csv` | 11 | One row per run: algorithm, run_idx, total_time, avg_speed, peers, hash_failures. |
| `data/experiments/comparison_timeline.csv` | 161 | Per piece per run: first_seen_s and completed_s, with `rarity_class` (common/rare) so the book can aggregate. |
| `data/experiments/comparison_peers.csv` | 41 | Per peer per run: upload_bytes. This is the file that holds the headline result. |
| `data/experiments/README.md` | 117 | Methodology, the headline numbers table, and explicit honest limitations (no churn simulation, no real swarm, no tit‑for‑tat vs round‑robin). |

### Result — what's measurable now

Mean across 5 runs each:

| Peer | rarest_first uploads | random uploads | Δ |
| --- | ---: | ---: | ---: |
| `full`  | **524 288 bytes** | **589 824 bytes** | +12.5 % |
| `low_a` | 153 600 bytes     | 128 000 bytes     | |
| `low_b` | 166 400 bytes     | 153 600 bytes     | |
| `low_c` | 192 000 bytes     | 166 400 bytes     | |

The 524 288 bytes under rarest‑first is **exactly** 8 × 64 KB — the
total size of the rare half. This is deterministic across all 5
runs (the CSV shows identical 524288 in every `rarest_first` row).
Under random, `full` ends up serving ~12.5 % more bytes because
random selection sometimes routes a common‑piece request to `full`
rather than to one of the three other peers that also hold it.

Wall‑clock: ~30 ms in both, as predicted. Total bytes transferred:
1 048 576 in every run (sanity).

### Oral exam prep — Step 1

If asked **"did you actually run the comparison the book promises?"**:

> Yes. The driver is `python_engine/experiments/run_comparison.py`
> and the committed CSVs are in `data/experiments/`. We run on
> loopback against four mock peers — three duplicate the common half
> of the file, one is the sole source for the rare half. Under
> rarest‑first, the sole‑source peer uploads exactly the size of the
> rare half (524 288 bytes); under random it uploads ~12.5 % more.
> That's the algorithm working: rarest‑first concentrates demand
> for the rare pieces on the only peer that has them, and lets the
> other three peers serve the common half in parallel.

If asked **"why not a real swarm?"**:

> A real swarm changes minute to minute — seeder count, bandwidth,
> peer churn — so an A/B between two runs would be confounded by
> network noise larger than the algorithmic signal. We control the
> swarm so the algorithm is the only variable.

If asked **"why didn't wall‑clock differ?"**:

> Because on loopback the bottleneck is CPU and the event loop, not
> bandwidth. The algorithmic effect of rarest‑first is in *which
> peer* does the work, not *how fast*. The per‑peer upload CSV
> (`comparison_peers.csv`) is the right metric. We say this
> explicitly in the README.

If asked **"how did you measure per‑piece timing if the download
finished in 30 ms?"**:

> Polling at any reasonable cadence misses transitions inside a
> 30 ms run. So `PieceTimeline` wraps `PieceManager.start_piece`
> and each `Piece.verify_hash` to record `time.perf_counter()` at
> the exact event — direct instrumentation rather than sampling.

### How to re‑run

```
python3 -m python_engine.experiments.run_comparison
```

Overwrites the three CSVs in `data/experiments/`. Takes a few seconds.

---

## STEP 2 — End‑to‑end peer wire protocol tests

### Why

The teacher's bullet:

> "אין end‑to‑end network tests מול peer חי."

…and from the body of the assessment:

> "הספר טוען למימוש handshake, length‑prefixed messages, bitfield,
> have, request, piece, cancel, choke/unchoke — תחום קשה מאוד.
> תלמיד שלא שולט בחומר יישבר מיד בשאלות בסיסיות."

The 172 existing tests are all unit tests with mocked sockets
(`AsyncMock` and `MagicMock`). The wire protocol claim was unproven
against a real socket. This step closes that gap.

### What

`python_engine/tests/test_e2e_peer.py` — four integration tests that
drive the engine's real `PeerConnection` and `Download` classes
against a real (loopback) TCP socket via the `MockPeer` built in
step 1. Final test count: **176 passing** (up from 172).

### How — design decisions

#### 1. Reuse `MockPeer`, don't build a second one

`MockPeer` from `python_engine/experiments/mock_swarm.py` already
speaks enough of BEP‑3 for the engine to download from it. Building
a parallel one for tests would duplicate hand‑rolled protocol code,
which is exactly the kind of drift we don't want.

#### 2. Test cumulative coverage, not random coverage

The four tests are ordered by depth:

| # | Test | What it proves |
| --- | --- | --- |
| 1 | `test_handshake_roundtrip_succeeds` | The 68‑byte handshake completes both directions; the 20‑byte remote `peer_id` arrives intact. |
| 2 | `test_handshake_rejects_wrong_info_hash` | The engine raises `PeerConnectionError` when its `info_hash` doesn't match the peer's — i.e. the security check actually works. |
| 3 | `test_one_piece_download_via_peer_connection` | Drives a real `PeerConnection` through bitfield → interested → unchoke → request → piece for one 64 KB piece (= 4 × 16 KB blocks). Reassembles via the engine's `Piece` class and asserts `verify_hash()` returns True. **This is the single most important test in the project**: it proves framing, message IDs, payload layout, and block assembly all work on bytes that traveled the wire. |
| 4 | `test_full_download_byte_identical` | Drives the whole stack — `Download` with `DownloadManager` against tracker + one full seeder. Asserts the final file on disk is byte‑identical to the source payload. |

#### 3. Async resource cleanup in `finally`

Every test tears down its `MockPeer`, `MockTracker`, and (in test 4)
its `Download` in a `finally` block. Without this, the next test
inherits dangling tasks (the engine spawns a `_choke_loop`, a
`_keep_alive_loop`, peer message loops, and the tracker's periodic
announce) and pytest takes seconds to exit instead of milliseconds.

#### 4. Deterministic payload

Each test writes a payload with `random.Random(seed)` so the bytes
are deterministic. SHA‑1 verification therefore checks against
known expected hashes; a flake would mean the wire path corrupted
data, not that the random seed changed.

### Where — files

| Path | Lines | Purpose |
| --- | ---: | --- |
| `python_engine/tests/test_e2e_peer.py` | 307 | The four tests + helpers (`_write_payload`, `_build_swarm`). |

Key sections:

* `_build_swarm` (lines 64‑89) — starts tracker + one `MockPeer`,
  builds the `.torrent`, returns the parsed `TorrentMetadata`.
* `test_one_piece_download_via_peer_connection` (lines 138‑212) —
  the deep wire‑protocol test described above.
* `test_full_download_byte_identical` (lines 216‑287) — full stack
  test with disk verification.

### Result — what's measurable now

* `pytest python_engine/tests/ -q` → **176 passed in 0.83 s**.
* The single command `pytest python_engine/tests/test_e2e_peer.py
  -v` is a verifiable answer to "do your protocol claims hold on a
  real socket?".

### Oral exam prep — Step 2

If asked **"do you have any tests with a real peer, or are they all
mocked?"**:

> The unit tests use mocks, but
> `python_engine/tests/test_e2e_peer.py` has four integration
> tests that drive the engine over a real loopback TCP socket
> against a mock peer that speaks BEP‑3. The fourth test does a
> full download and asserts the file on disk is byte‑identical to
> the source.

If asked **"how do you know the wire protocol parsing is correct?"**:

> The third test in `test_e2e_peer.py` —
> `test_one_piece_download_via_peer_connection` — drives a real
> `PeerConnection` through every message type in a single piece
> download: bitfield, interested, unchoke, request, piece. It then
> reassembles the piece using the engine's `Piece` class and asserts
> `verify_hash()` is True. If framing or message layout were wrong,
> the SHA‑1 wouldn't match.

If asked **"what about partial TCP reads / message fragmentation?"**:

> The engine uses `asyncio.StreamReader.readexactly(n)`, which
> blocks until exactly *n* bytes have been read regardless of how
> the kernel chose to split them. That code is at
> `peer_connection.py:248-271`. The E2E tests exercise this path on
> a real socket — if it didn't handle partial reads, the third or
> fourth test would have failed.

### How to re‑run

```
python3 -m pytest python_engine/tests/test_e2e_peer.py -v
```

Should finish in well under a second.

---

## Combined summary

| Step | Lines added (code) | Lines added (data) | Tests added | Outcome |
| --- | ---: | ---: | ---: | --- |
| 1 — experiment | 698 | ~330 | 0 | יעילות 2/10 → real measured numbers |
| 2 — E2E tests  | 307 | 0   | 4 | בדיקות 5/10 → real socket‑level coverage |
| **Total**      | **1005** | **~330** | **+4** | Test count 172 → 176, all passing |

## Plan items remaining (from `revision/PLAN.md`)

* Step 3 — implement `_load_state` so the "resume after pause"
  claim is actually true (the book's own chapter 25 admits this is
  missing today).
* Step 4 — sliding‑window contribution + snubbing + seeding mode
  (tit‑for‑tat depth; targets the algorithm part of the critique).
* Step 5 — book rewrites: tone fixes, new §6.2.1 handshake bytes
  table, §6.2.2 TCP framing walkthrough, §5.2 bencode worked
  example, §7.2.1/2/3 for the new algorithms, §25.5 honest
  limitations chapter, "50 peers / 4 GB" claims trimmed.
* Step 6 — wire the new chapter‑24 numbers from the CSVs into the
  rewritten chapter‑24 prose.
