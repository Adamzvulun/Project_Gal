"""
Rarest-first vs random — controlled localhost experiment.

Why this experiment, not a real public swarm?
  A real swarm is not reproducible: seeders and bandwidth change
  minute by minute. The teacher's complaint was specifically that the
  book promised an empirical comparison and produced none. The honest
  way to deliver the comparison is to control the swarm: same payload,
  same peer topology, same piece distribution, same starting state
  across runs — so the algorithm is the only variable.

Topology (designed to expose the rarest-first signal):
  Payload: 1 MB of deterministic random bytes (seeded), 16 pieces × 64 KB.
  4 mock seeders:
      "full"   — owns pieces  0..15
      "low_a"  — owns pieces  0.. 7
      "low_b"  — owns pieces  0.. 7
      "low_c"  — owns pieces  0.. 7
  Therefore: pieces 0..7  appear at 4 peers (freq = 4)
             pieces 8..15 appear at 1 peer  (freq = 1)
  A correct rarest-first should select 8..15 first; a random baseline
  should select uniformly. The wall-clock total time is expected to
  be similar on loopback (CPU-bound, not bandwidth-bound) — the
  interesting signal is in WHICH PIECES get selected EARLY and which
  peer gets the early load.

Outputs:
  data/experiments/comparison_summary.csv  — one row per run (totals).
  data/experiments/comparison_timeline.csv — per-piece timing per run.
  data/experiments/comparison_peers.csv    — per-peer upload per run.

Run it:
  python -m python_engine.experiments.run_comparison
"""

from __future__ import annotations

import asyncio
import csv
import logging
import os
import random
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ..download_manager import Download, AlgorithmType, DownloadState
from ..piece_manager import PieceStatus
from ..torrent_metadata import TorrentMetadata
from .make_torrent import make_torrent_bytes
from .mock_swarm import MockPeer, MockSwarm, MockTracker

logger = logging.getLogger(__name__)


# ── Experiment parameters ─────────────────────────────────────────────────

PIECE_LENGTH = 64 * 1024            # 64 KB per piece
NUM_PIECES = 16                     # → 1 MB payload
PAYLOAD_BYTES = PIECE_LENGTH * NUM_PIECES
RUNS_PER_ALGORITHM = 5
PER_RUN_TIMEOUT = 30                # seconds; loopback should finish in <5s
POLL_INTERVAL = 0.005               # 5ms — connection-count sampling cadence
ALGORITHMS = [AlgorithmType.RAREST_FIRST, AlgorithmType.RANDOM]
PEER_SEED = 0xDEC1AAA               # for the deterministic payload


# ── Result containers ────────────────────────────────────────────────────

@dataclass
class RunResult:
    algorithm: str
    run_idx: int
    total_time_s: float
    completed_pieces: int
    num_pieces: int
    avg_speed_Bps: float
    hash_failures: int
    peers_connected: int
    piece_first_seen_at: List[Optional[float]] = field(default_factory=list)
    piece_completed_at: List[Optional[float]] = field(default_factory=list)
    peer_upload_bytes: Dict[str, int] = field(default_factory=dict)


# ── Payload + torrent setup ───────────────────────────────────────────────

def generate_payload(path: Path, size: int, seed: int) -> None:
    """Write a deterministic pseudo-random payload to ``path``.

    Same seed across runs → identical bytes → identical piece hashes.
    """
    rng = random.Random(seed)
    with open(path, "wb") as f:
        # write in 64KB chunks to keep memory low
        remaining = size
        while remaining > 0:
            chunk = min(64 * 1024, remaining)
            f.write(bytes(rng.getrandbits(8) for _ in range(chunk)))
            remaining -= chunk


# ── Status sampler (records when pieces transition state) ────────────────

class PieceTimeline:
    """Records the timestamps at which each piece transitions states.

    Uses two complementary instrumentation points:
      * ``start_piece`` is wrapped to record the moment a piece is
        first selected (enters IN_PROGRESS). This is the
        rarest-first / random selection event itself, so it's the
        canonical "first seen" timestamp.
      * ``Piece.verify_hash`` is wrapped to record completion, since
        the engine only marks a piece COMPLETED inside its async
        on-message handler after verification succeeds.

    Direct instrumentation avoids the polling resolution problem
    where 16 pieces on loopback complete inside one poll tick.
    """

    def __init__(self, download: Download, start_time: float) -> None:
        self.download = download
        self.start_time = start_time
        n = download.torrent.num_pieces
        self.first_seen_at: List[Optional[float]] = [None] * n
        self.completed_at: List[Optional[float]] = [None] * n
        self.peak_connected: int = 0
        self._task: Optional[asyncio.Task] = None
        self._stop = False

        pm = download.piece_manager
        original_start_piece = pm.start_piece

        def wrapped_start_piece(piece_index: int):
            if (0 <= piece_index < n
                    and self.first_seen_at[piece_index] is None):
                self.first_seen_at[piece_index] = (
                    time.perf_counter() - self.start_time
                )
            return original_start_piece(piece_index)

        pm.start_piece = wrapped_start_piece  # type: ignore[assignment]

        # Wrap verify_hash on each piece object so we capture the
        # moment the piece's data hashes correctly. This fires once
        # per piece (or once per failed retry) but we only record the
        # first successful verification.
        timeline_self = self
        for piece in pm.pieces:
            original_verify = piece.verify_hash

            def make_wrapped(idx, orig):
                def wrapped_verify():
                    ok = orig()
                    if (ok and timeline_self.completed_at[idx] is None):
                        timeline_self.completed_at[idx] = (
                            time.perf_counter() - timeline_self.start_time
                        )
                    return ok
                return wrapped_verify

            piece.verify_hash = make_wrapped(piece.index, original_verify)  # type: ignore[assignment]

    async def _loop(self) -> None:
        # We still poll to track peak connection count, since that
        # number is observable but not hookable.
        while not self._stop:
            connected = sum(
                1 for c in self.download._connections.values() if c.connected
            )
            if connected > self.peak_connected:
                self.peak_connected = connected
            await asyncio.sleep(POLL_INTERVAL)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop = True
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=1)
            except asyncio.TimeoutError:
                self._task.cancel()


# ── A single run ──────────────────────────────────────────────────────────

async def run_one(algorithm: AlgorithmType, run_idx: int,
                  payload_path: Path, torrent_path: Path,
                  swarm: MockSwarm, work_dir: Path) -> RunResult:
    download_dir = work_dir / f"download_{algorithm.value}_{run_idx}"
    state_dir = work_dir / f"state_{algorithm.value}_{run_idx}"
    download_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    torrent = TorrentMetadata(torrent_path=str(torrent_path))
    download = Download(
        torrent=torrent,
        download_dir=str(download_dir),
        state_dir=str(state_dir),
        piece_algorithm=algorithm,
        peer_algorithm=AlgorithmType.TIT_FOR_TAT,
    )

    start_perf = time.perf_counter()
    timeline = PieceTimeline(download, start_perf)
    timeline.start()

    await download.start()

    # Poll for completion or timeout.
    deadline = start_perf + PER_RUN_TIMEOUT
    while True:
        if download.piece_manager.is_complete:
            break
        if download.state in (DownloadState.ERROR, DownloadState.CANCELLED):
            break
        if time.perf_counter() > deadline:
            logger.warning("Run timed out after %ds (algo=%s, run=%d)",
                           PER_RUN_TIMEOUT, algorithm.value, run_idx)
            break
        await asyncio.sleep(POLL_INTERVAL)

    end_perf = time.perf_counter()
    total_time = end_perf - start_perf

    await timeline.stop()

    # Gracefully cancel the download's tasks so the next run starts clean.
    if download._main_task and not download._main_task.done():
        download._main_task.cancel()
        try:
            await download._main_task
        except (asyncio.CancelledError, Exception):
            pass
    if download._choke_task and not download._choke_task.done():
        download._choke_task.cancel()
    if download._keep_alive_task and not download._keep_alive_task.done():
        download._keep_alive_task.cancel()
    # Close all peer connections from the engine's side.
    for conn in list(download._connections.values()):
        try:
            await conn.disconnect()
        except Exception:
            pass
    # Close the tracker's aiohttp ClientSession to avoid leaking sockets.
    if download._tracker is not None:
        try:
            await download._tracker.stop()
        except Exception:
            pass
    download._executor.shutdown(wait=False)

    completed = download.piece_manager.completed_pieces
    avg_speed = (download.stats.bytes_downloaded / total_time
                 if total_time > 0 else 0.0)
    hash_failures = sum(
        rep.hash_failures
        for rep in download.security._peer_reputations.values()
    )

    result = RunResult(
        algorithm=algorithm.value,
        run_idx=run_idx,
        total_time_s=total_time,
        completed_pieces=completed,
        num_pieces=torrent.num_pieces,
        avg_speed_Bps=avg_speed,
        hash_failures=hash_failures,
        peers_connected=timeline.peak_connected,
        piece_first_seen_at=list(timeline.first_seen_at),
        piece_completed_at=list(timeline.completed_at),
        peer_upload_bytes={p.name: p.upload_bytes for p in swarm.peers},
    )

    # Reset per-peer upload counters between runs (they accumulate
    # across the lifetime of the MockPeer process).
    for p in swarm.peers:
        p.upload_bytes = 0

    return result


# ── Driver ────────────────────────────────────────────────────────────────

async def main_async(output_dir: Path) -> List[RunResult]:
    work_dir = Path(tempfile.mkdtemp(prefix="bt_experiment_"))
    payload_path = work_dir / "payload.bin"
    torrent_path = work_dir / "payload.torrent"

    try:
        # Build payload + torrent once, reused across all runs.
        generate_payload(payload_path, PAYLOAD_BYTES, PEER_SEED)
        # Tracker URL filled in after we know the tracker's port.
        # We construct the swarm first to learn the port, then build the
        # .torrent that points at it.
        tracker = MockTracker()
        await tracker.start()

        torrent_bytes, info_hash = make_torrent_bytes(
            str(payload_path),
            announce_url=tracker.announce_url,
            piece_length=PIECE_LENGTH,
        )
        torrent_path.write_bytes(torrent_bytes)

        peers = [
            MockPeer(name="full",  info_hash=info_hash,
                     payload_path=str(payload_path),
                     piece_length=PIECE_LENGTH,
                     num_pieces=NUM_PIECES,
                     total_size=PAYLOAD_BYTES,
                     owned_pieces=list(range(0, 16))),
            MockPeer(name="low_a", info_hash=info_hash,
                     payload_path=str(payload_path),
                     piece_length=PIECE_LENGTH,
                     num_pieces=NUM_PIECES,
                     total_size=PAYLOAD_BYTES,
                     owned_pieces=list(range(0, 8))),
            MockPeer(name="low_b", info_hash=info_hash,
                     payload_path=str(payload_path),
                     piece_length=PIECE_LENGTH,
                     num_pieces=NUM_PIECES,
                     total_size=PAYLOAD_BYTES,
                     owned_pieces=list(range(0, 8))),
            MockPeer(name="low_c", info_hash=info_hash,
                     payload_path=str(payload_path),
                     piece_length=PIECE_LENGTH,
                     num_pieces=NUM_PIECES,
                     total_size=PAYLOAD_BYTES,
                     owned_pieces=list(range(0, 8))),
        ]
        for p in peers:
            await p.start()
        tracker.set_peers([(p.host, p.port) for p in peers])
        swarm = MockSwarm(tracker=tracker, peers=peers)

        results: List[RunResult] = []
        for algo in ALGORITHMS:
            for run_idx in range(RUNS_PER_ALGORITHM):
                logger.info("=== Run algo=%s idx=%d ===", algo.value, run_idx)
                result = await run_one(
                    algorithm=algo, run_idx=run_idx,
                    payload_path=payload_path,
                    torrent_path=torrent_path,
                    swarm=swarm,
                    work_dir=work_dir,
                )
                results.append(result)
                logger.info(
                    "    completed=%d/%d, time=%.2fs, avg=%.0f B/s",
                    result.completed_pieces, result.num_pieces,
                    result.total_time_s, result.avg_speed_Bps,
                )

        await swarm.stop()
        return results
    finally:
        # Clean working dir
        shutil.rmtree(work_dir, ignore_errors=True)


# ── CSV writers ───────────────────────────────────────────────────────────

def write_summary_csv(path: Path, results: List[RunResult]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "algorithm", "run_idx",
            "total_time_s", "completed_pieces", "num_pieces",
            "avg_speed_Bps", "hash_failures", "peers_connected",
        ])
        for r in results:
            w.writerow([
                r.algorithm, r.run_idx,
                f"{r.total_time_s:.4f}", r.completed_pieces, r.num_pieces,
                f"{r.avg_speed_Bps:.1f}", r.hash_failures, r.peers_connected,
            ])


def write_timeline_csv(path: Path, results: List[RunResult]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "algorithm", "run_idx", "piece_index",
            "rarity_class",
            "first_seen_s", "completed_s",
        ])
        for r in results:
            for piece_idx in range(r.num_pieces):
                rarity = "common" if piece_idx < 8 else "rare"
                fs = r.piece_first_seen_at[piece_idx]
                ca = r.piece_completed_at[piece_idx]
                w.writerow([
                    r.algorithm, r.run_idx, piece_idx, rarity,
                    f"{fs:.4f}" if fs is not None else "",
                    f"{ca:.4f}" if ca is not None else "",
                ])


def write_peers_csv(path: Path, results: List[RunResult]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algorithm", "run_idx", "peer", "upload_bytes"])
        for r in results:
            for peer_name, ub in r.peer_upload_bytes.items():
                w.writerow([r.algorithm, r.run_idx, peer_name, ub])


# ── Console summary ───────────────────────────────────────────────────────

def print_summary(results: List[RunResult]) -> None:
    print()
    print("=" * 72)
    print(" SUMMARY (one row per run)")
    print("=" * 72)
    print(f"{'algorithm':<14} {'run':>3}  {'time(s)':>8}  "
          f"{'pieces':>10}  {'avg KB/s':>10}  {'connected':>10}")
    for r in results:
        print(f"{r.algorithm:<14} {r.run_idx:>3}  "
              f"{r.total_time_s:>8.2f}  "
              f"{r.completed_pieces:>4d}/{r.num_pieces:<4d}  "
              f"{r.avg_speed_Bps/1024:>10.1f}  "
              f"{r.peers_connected:>10d}")

    print()
    print("=" * 72)
    print(" MEAN OF FIRST-SEEN TIME BY RARITY CLASS  (lower for rare = "
          "rarest-first working)")
    print("=" * 72)
    by_algo: Dict[str, Dict[str, List[float]]] = {}
    for r in results:
        bucket = by_algo.setdefault(r.algorithm,
                                    {"common": [], "rare": []})
        for piece_idx in range(r.num_pieces):
            klass = "common" if piece_idx < 8 else "rare"
            fs = r.piece_first_seen_at[piece_idx]
            if fs is not None:
                bucket[klass].append(fs)
    print(f"{'algorithm':<14} {'mean(common)':>14} {'mean(rare)':>14} "
          f"{'rare - common':>14}")
    for algo, bucket in by_algo.items():
        mc = (sum(bucket["common"]) / len(bucket["common"])
              if bucket["common"] else float("nan"))
        mr = (sum(bucket["rare"]) / len(bucket["rare"])
              if bucket["rare"] else float("nan"))
        print(f"{algo:<14} {mc:>14.4f} {mr:>14.4f} {mr - mc:>14.4f}")

    print()
    print("=" * 72)
    print(" PER-PEER UPLOAD (means across runs)")
    print("=" * 72)
    by_algo_peer: Dict[str, Dict[str, List[int]]] = {}
    for r in results:
        d = by_algo_peer.setdefault(r.algorithm, {})
        for peer, ub in r.peer_upload_bytes.items():
            d.setdefault(peer, []).append(ub)
    for algo, d in by_algo_peer.items():
        print(f"  [{algo}]")
        for peer, ubs in d.items():
            mean = sum(ubs) / len(ubs) if ubs else 0
            print(f"    {peer:<8} {mean/1024:>8.1f} KB")
    print()


# ── Entry point ───────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.getLogger("python_engine.experiments").setLevel(logging.INFO)

    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "data" / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)

    results = asyncio.run(main_async(output_dir))

    summary_path = output_dir / "comparison_summary.csv"
    timeline_path = output_dir / "comparison_timeline.csv"
    peers_path = output_dir / "comparison_peers.csv"

    write_summary_csv(summary_path, results)
    write_timeline_csv(timeline_path, results)
    write_peers_csv(peers_path, results)

    print_summary(results)
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {timeline_path}")
    print(f"Wrote: {peers_path}")


if __name__ == "__main__":
    main()
