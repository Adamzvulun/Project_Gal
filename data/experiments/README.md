# Empirical comparison — rarest-first vs random piece selection

This folder holds the CSV evidence the project book's chapter 24 was
missing. The driver is `python_engine/experiments/run_comparison.py`.

## How to re-run

```
python3 -m python_engine.experiments.run_comparison
```

The script overwrites the three CSV files below on each invocation.

## Methodology (controlled localhost swarm)

We cannot get reproducible numbers from a real public swarm — seeder
count and bandwidth change minute by minute, and any A/B comparison
across two real downloads would be confounded by network noise. So
the experiment runs everything on loopback with a self-contained
swarm we control:

| Component | What it is |
| --- | --- |
| Payload  | 1 MB of deterministic pseudo-random bytes (seed = 0xDEC1AAA). |
| Torrent  | 16 pieces × 64 KB, generated fresh from the payload. |
| Tracker  | A minimal aiohttp server (`mock_swarm.MockTracker`) that returns the four peers in compact format. |
| Peers    | Four `mock_swarm.MockPeer` instances, each speaking enough of BEP-3 (handshake, bitfield, interested, unchoke, request, piece) to serve the pieces it owns. |

Peer topology (designed so piece availability is **non-uniform** — this
is what makes the rarest-first vs random comparison meaningful):

| Peer name | Owns pieces | Why |
| --- | --- | --- |
| `full`  | 0..15 | Sole source for the rare half. |
| `low_a` | 0..7  | Duplicates the common half. |
| `low_b` | 0..7  | Duplicates the common half. |
| `low_c` | 0..7  | Duplicates the common half. |

Effective piece-availability frequencies:

* pieces **0..7**  appear at **4 peers** (common)
* pieces **8..15** appear at **1 peer**  (rare)

For each algorithm (`rarest_first`, `random`) we run **5 independent
downloads** with a fresh `Download` object each time but the same
payload, torrent, and swarm topology. The peer-selection algorithm is
fixed at `tit_for_tat` in all runs — we are isolating piece selection.

## What the CSVs contain

### `comparison_summary.csv` (one row per run, 10 rows)

| Column | Meaning |
| --- | --- |
| `algorithm`        | `rarest_first` or `random` |
| `run_idx`          | 0..4 within each algorithm |
| `total_time_s`     | Wall-clock from `Download.start()` to all pieces complete |
| `completed_pieces` | Should equal `num_pieces` (sanity: did the run finish?) |
| `num_pieces`       | 16 |
| `avg_speed_Bps`    | `bytes_downloaded / total_time_s` |
| `hash_failures`    | Sum across all peer reputation records (expected 0). |
| `peers_connected`  | Peak number of connections during the run (expected 4). |

### `comparison_timeline.csv` (16 pieces × 10 runs = 160 rows)

For every piece in every run, the timestamps at which the piece was
first **selected** (entered IN_PROGRESS) and **completed** (verified
SHA-1 OK), measured from the run's start.

* `rarity_class` is the static label — `common` for pieces 0..7,
  `rare` for pieces 8..15 — letting us aggregate across runs.

Instrumentation is direct: `PieceTimeline` wraps
`PieceManager.start_piece` and each `Piece.verify_hash` so the
timestamps are captured at the exact event, independent of poll
resolution. (This matters because the entire download finishes in
~30 ms; coarse polling would record nothing.)

### `comparison_peers.csv` (4 peers × 10 runs = 40 rows)

How many bytes each mock peer uploaded to the engine during each
run. This is the **clearest** signal in the experiment.

## Headline result (means across 5 runs each)

| Peer    | rarest-first | random  |
| ---     | ---          | ---     |
| `full`  | **512.0 KB** | **576.0 KB** |
| `low_a` | 153.6 KB     | 128.0 KB |
| `low_b` | 166.4 KB     | 153.6 KB |
| `low_c` | 192.0 KB     | 166.4 KB |
| Total   | 1024 KB      | 1024 KB |

`full` is the **only** source for the 8 rare pieces. Under
rarest-first, the engine asks `full` for the rare pieces and asks the
three other peers for the common pieces in parallel — `full` ends up
uploading exactly 512 KB (= 8 × 64 KB), which is precisely the rare
half. Under random selection, the engine sometimes routes
common-piece requests to `full` as well (since `full` also holds
the common pieces), so `full` uploads ~12.5 % more (576 vs 512 KB)
while `low_a` correspondingly does less work.

Wall-clock total time is statistically identical (`rarest_first`
mean ≈ 30 ms, `random` mean ≈ 30 ms) because on loopback the
bottleneck is CPU and the asyncio event loop, not bandwidth. The
algorithmic effect we predict is **not** a faster download in this
setting — it's a different **distribution** of work. Per-peer upload
is what reveals it.

A secondary signal in `comparison_timeline.csv`: rare pieces enter
IN_PROGRESS later than common pieces under both algorithms (because
only one peer can source them, vs. three in parallel for common
pieces), but the gap relative to total time is consistently smaller
under rarest-first than under random — i.e., rarest-first does start
prioritising the rare half.

## What this experiment does NOT claim

* It does **not** measure speedup on a real public swarm.
* It does **not** demonstrate the "endgame" / piece-starvation
  scenario that motivates rarest-first in production (peer churn).
  Real impact of rarest-first emerges when the single seeder
  disconnects mid-download; simulating that requires peer-churn
  injection, which we haven't built.
* It does **not** compare tit-for-tat against round-robin (peer
  selection); only piece selection.

These are honest limitations and the book's chapter 24 should state
them. The experiment as built answers the specific question: *"In a
swarm where piece availability is non-uniform, does our rarest-first
implementation actually concentrate demand for rare pieces on the
only-source peer?"* The answer, from the data: **yes**, and it does so
deterministically across all 5 runs.
