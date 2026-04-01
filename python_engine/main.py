"""
CLI entry point for downloading torrents.

Usage:
    python -m python_engine.main path/to/file.torrent [--output DIR] [--algorithm rarest_first|random]
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
import time

from .torrent_metadata import TorrentMetadata, TorrentMetadataError
from .download_manager import DownloadManager, Download, AlgorithmType, DownloadState


def format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string."""
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_speed(speed_bps: float) -> str:
    """Format bytes/sec into a human-readable string."""
    return format_size(speed_bps) + "/s"


def format_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS."""
    if seconds <= 0:
        return "--:--:--"
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


async def run_download(torrent_path: str, output_dir: str,
                       piece_algo: AlgorithmType, peer_algo: AlgorithmType):
    """Run a torrent download with progress reporting."""
    # Parse torrent file
    try:
        torrent = TorrentMetadata(torrent_path=torrent_path)
    except TorrentMetadataError as e:
        print(f"Error: Invalid torrent file: {e}")
        sys.exit(1)

    print(f"Torrent:  {torrent.name}")
    print(f"Size:     {format_size(torrent.total_size)}")
    print(f"Pieces:   {torrent.num_pieces} x {format_size(torrent.piece_length)}")
    print(f"Tracker:  {torrent.announce}")
    print(f"Output:   {os.path.abspath(output_dir)}")
    print(f"Piece algorithm: {piece_algo.value}")
    print(f"Peer algorithm:  {peer_algo.value}")
    print()

    # Create download manager and start
    manager = DownloadManager(download_dir=output_dir, state_dir="data/state")
    download = await manager.add_torrent(torrent, piece_algo, peer_algo)

    # Handle Ctrl+C gracefully
    stop_event = asyncio.Event()

    def handle_signal():
        print("\nStopping download...")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    # Start the download
    await download.start()
    print("Download started. Connecting to tracker and peers...\n")

    # Progress reporting loop
    last_progress_line_len = 0
    while download.state == DownloadState.RUNNING and not stop_event.is_set():
        await asyncio.sleep(2)

        progress = download.progress * 100
        speed = download.stats.download_speed
        peers = download.connected_peers
        elapsed = download.stats.elapsed_time
        downloaded = download.stats.bytes_downloaded
        total = download.file_size

        # ETA calculation
        if speed > 0:
            remaining_bytes = total - downloaded
            eta = remaining_bytes / speed
            eta_str = format_time(eta)
        else:
            eta_str = "--:--:--"

        line = (
            f"\rProgress: {progress:5.1f}% | "
            f"{format_size(downloaded)}/{format_size(total)} | "
            f"Speed: {format_speed(speed)} | "
            f"Peers: {peers} | "
            f"ETA: {eta_str} | "
            f"Elapsed: {format_time(elapsed)}"
        )
        # Clear previous line if it was longer
        padded = line.ljust(last_progress_line_len)
        print(padded, end='', flush=True)
        last_progress_line_len = len(line)

    print()  # newline after progress

    if stop_event.is_set():
        await download.cancel()
        print("Download cancelled by user.")
    elif download.state == DownloadState.COMPLETED:
        elapsed = download.stats.elapsed_time
        avg_speed = download.stats.average_speed
        print(f"Download complete!")
        print(f"  Time:      {format_time(elapsed)}")
        print(f"  Avg speed: {format_speed(avg_speed)}")
        print(f"  Saved to:  {os.path.abspath(output_dir)}")
    elif download.state == DownloadState.ERROR:
        print("Download failed with an error. Check logs for details.")
    else:
        print(f"Download ended in state: {download.state.value}")


def main():
    parser = argparse.ArgumentParser(
        description="BitTorrent file downloader",
        prog="python -m python_engine.main"
    )
    parser.add_argument(
        "torrent_file",
        help="Path to the .torrent file"
    )
    parser.add_argument(
        "-o", "--output",
        default="data/downloads",
        help="Output directory (default: data/downloads)"
    )
    parser.add_argument(
        "--piece-algorithm",
        choices=["rarest_first", "random"],
        default="rarest_first",
        help="Piece selection algorithm (default: rarest_first)"
    )
    parser.add_argument(
        "--peer-algorithm",
        choices=["tit_for_tat", "round_robin"],
        default="tit_for_tat",
        help="Peer selection algorithm (default: tit_for_tat)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )

    # Map algorithm strings to enums
    piece_algo = (AlgorithmType.RAREST_FIRST if args.piece_algorithm == "rarest_first"
                  else AlgorithmType.RANDOM)
    peer_algo = (AlgorithmType.TIT_FOR_TAT if args.peer_algorithm == "tit_for_tat"
                 else AlgorithmType.ROUND_ROBIN)

    # Verify torrent file exists
    if not os.path.isfile(args.torrent_file):
        print(f"Error: File not found: {args.torrent_file}")
        sys.exit(1)

    # Run the download
    asyncio.run(run_download(args.torrent_file, args.output, piece_algo, peer_algo))


if __name__ == "__main__":
    main()
