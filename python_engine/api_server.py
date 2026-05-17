"""
REST API server module.

Provides a local HTTP API (Flask) that bridges the Python BitTorrent engine
and the Java GUI client. Runs on localhost.
"""

import asyncio
import concurrent.futures
import datetime
import json
import logging
import os
import sqlite3
import tempfile
import threading
import time
from typing import Optional

from flask import Flask, jsonify, request, Response
from werkzeug.utils import secure_filename

from .torrent_metadata import TorrentMetadata, TorrentMetadataError
from .download_manager import DownloadManager, AlgorithmType, DownloadState

logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join("data", "history.db")
STATE_DIR = os.path.join("data", "state")
DOWNLOAD_DIR = os.path.join("data", "downloads")

app = Flask(__name__)

# Global download manager (initialized on startup)
_manager: Optional[DownloadManager] = None
_db_lock = threading.Lock()

# Persistent asyncio event loop running in a background thread
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None


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


def get_manager() -> DownloadManager:
    """Get or create the download manager."""
    global _manager
    if _manager is None:
        _manager = DownloadManager(
            download_dir=DOWNLOAD_DIR,
            state_dir=STATE_DIR
        )
        restored = _manager.restore_state()
        if restored:
            logger.info(f"[engine] restored {restored} download(s) from {STATE_DIR}")
    return _manager


# ── Database Setup ──

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


def save_torrent_to_db(download):
    """Save torrent info and stats to the SQLite database."""
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        now = datetime.datetime.now().isoformat()
        stats = download.stats

        cursor.execute("""
            INSERT OR REPLACE INTO torrents
                (id, info_hash, name, size, started_at, completed_at,
                 total_time_seconds, final_status, piece_algorithm, peer_algorithm)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            download.id,
            download.torrent.info_hash_hex(),
            download.torrent.name,
            download.torrent.total_size,
            datetime.datetime.fromtimestamp(stats.start_time).isoformat()
            if stats.start_time else None,
            datetime.datetime.fromtimestamp(stats.end_time).isoformat()
            if stats.end_time else None,
            int(stats.elapsed_time) if stats.elapsed_time else 0,
            download.state.value,
            download.piece_algorithm.value,
            download.peer_algorithm.value
        ))

        cursor.execute("""
            INSERT OR REPLACE INTO performance_stats
                (torrent_id, avg_speed, peak_speed, avg_peers, choke_cycles)
            VALUES (?, ?, ?, ?, ?)
        """, (
            download.id,
            stats.average_speed,
            stats.peak_speed,
            stats.connected_peers,
            stats.choke_cycles
        ))

        # Save algorithm stats
        for piece_idx, count in download.piece_manager.rarest_selections.items():
            if count > 0:
                cursor.execute("""
                    INSERT INTO algorithm_stats
                        (torrent_id, piece_index, selected_as_rarest,
                         choke_count, unchoke_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    download.id, piece_idx, count,
                    stats.choke_count, stats.unchoke_count
                ))

        conn.commit()
        conn.close()


def log_event_to_db(torrent_id: str, event_type: str, description: str):
    """Log an event to the SQLite database."""
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (torrent_id, event_type, description)
            VALUES (?, ?, ?)
        """, (torrent_id, event_type, description))
        conn.commit()
        conn.close()


# ── API Endpoints ──

@app.route('/torrents', methods=['POST'])
def start_download():
    """Start a new download from a .torrent file.

    Accepts multipart/form-data with a 'torrent_file' field,
    or application/json with a 'torrent_path' field.
    """
    manager = get_manager()

    try:
        if 'torrent_file' in request.files:
            # File upload
            file = request.files['torrent_file']
            torrent_data = file.read()
            torrent = TorrentMetadata(torrent_data=torrent_data)
        elif request.is_json and 'torrent_path' in request.json:
            # File path
            torrent_path = request.json['torrent_path']
            torrent = TorrentMetadata(torrent_path=torrent_path)
        else:
            return jsonify({"error": "No torrent file provided"}), 400

        # Algorithm selection (optional)
        piece_algo = AlgorithmType.RAREST_FIRST
        peer_algo = AlgorithmType.TIT_FOR_TAT

        if request.is_json:
            algo_data = request.json
        else:
            algo_data = request.form

        if algo_data.get('piece_algorithm') == 'random':
            piece_algo = AlgorithmType.RANDOM
        if algo_data.get('peer_algorithm') == 'round_robin':
            peer_algo = AlgorithmType.ROUND_ROBIN

        # Optional custom download directory
        download_dir = algo_data.get('download_dir', None)

        # Create and start download on the persistent event loop
        async def create_and_start():
            download = await manager.add_torrent(
                torrent, piece_algo, peer_algo,
                download_dir=download_dir
            )
            await download.start()
            return download

        download = _run_async(create_and_start())

        # Save stats to DB when download completes
        def on_download_complete(dl):
            save_torrent_to_db(dl)
            log_event_to_db(dl.id, "download_completed",
                            f"Download completed: {dl.torrent.name}")
        download.on_complete(on_download_complete)

        log_event_to_db(download.id, "download_started",
                        f"Started download: {torrent.name}")

        return jsonify({
            "id": download.id,
            "name": torrent.name,
            "size": torrent.total_size,
            "num_pieces": torrent.num_pieces,
            "state": download.state.value
        }), 201

    except TorrentMetadataError as e:
        return jsonify({"error": f"Invalid torrent file: {e}"}), 400
    except Exception as e:
        logger.error(f"Error starting download: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/torrents', methods=['GET'])
def get_all_status():
    """Get status of all downloads."""
    manager = get_manager()
    statuses = manager.get_all_status()
    return jsonify(statuses)


@app.route('/torrents/<torrent_id>', methods=['GET'])
def get_torrent_status(torrent_id: str):
    """Get status of a specific download."""
    manager = get_manager()
    status = manager.get_download_status(torrent_id)
    if status is None:
        return jsonify({"error": "Torrent not found"}), 404
    return jsonify(status)


@app.route('/torrents/<torrent_id>/pause', methods=['POST'])
def pause_download(torrent_id: str):
    """Pause a specific download."""
    manager = get_manager()
    download = manager.get_download(torrent_id)
    if download is None:
        return jsonify({"error": "Torrent not found"}), 404

    _run_async(manager.pause_download(torrent_id))

    save_torrent_to_db(download)
    log_event_to_db(torrent_id, "download_paused", "Download paused")

    return jsonify({"id": torrent_id, "state": "Paused"})


@app.route('/torrents/<torrent_id>/resume', methods=['POST'])
def resume_download(torrent_id: str):
    """Resume a paused download."""
    manager = get_manager()
    download = manager.get_download(torrent_id)
    if download is None:
        return jsonify({"error": "Torrent not found"}), 404

    _run_async(manager.resume_download(torrent_id))

    log_event_to_db(torrent_id, "download_resumed", "Download resumed")

    return jsonify({"id": torrent_id, "state": "Running"})


@app.route('/torrents/<torrent_id>/cancel', methods=['POST'])
def cancel_download(torrent_id: str):
    """Cancel a specific download."""
    manager = get_manager()
    download = manager.get_download(torrent_id)
    if download is None:
        return jsonify({"error": "Torrent not found"}), 404

    _run_async(manager.cancel_download(torrent_id))

    save_torrent_to_db(download)
    log_event_to_db(torrent_id, "download_cancelled", "Download cancelled")

    return jsonify({"id": torrent_id, "state": "Cancelled"})


# ── History & Stats Endpoints ──

@app.route('/history', methods=['GET'])
def get_history():
    """Get download history from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, p.avg_speed, p.peak_speed, p.avg_peers,
               COALESCE(p.choke_cycles, 0) AS choke_cycles
        FROM torrents t
        LEFT JOIN performance_stats p ON t.id = p.torrent_id
        ORDER BY t.started_at DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/history', methods=['DELETE'])
def clear_history():
    """Clear all download history from SQLite."""
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM algorithm_stats")
        cursor.execute("DELETE FROM performance_stats")
        cursor.execute("DELETE FROM events")
        cursor.execute("DELETE FROM torrents")
        conn.commit()
        conn.close()
    logger.info("Download history cleared")
    return jsonify({"status": "ok"})


@app.route('/events', methods=['GET'])
def get_events():
    """Get event log from SQLite."""
    limit = request.args.get('limit', 100, type=int)
    torrent_id = request.args.get('torrent_id')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if torrent_id:
        cursor.execute("""
            SELECT * FROM events WHERE torrent_id = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (torrent_id, limit))
    else:
        cursor.execute("""
            SELECT * FROM events ORDER BY timestamp DESC LIMIT ?
        """, (limit,))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/algorithm-stats/<torrent_id>', methods=['GET'])
def get_algorithm_stats(torrent_id: str):
    """Get algorithm statistics for a specific torrent."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM algorithm_stats WHERE torrent_id = ?
        ORDER BY piece_index
    """, (torrent_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/stats-summary', methods=['GET'])
def get_stats_summary():
    """Aggregated per-torrent stats for algorithm comparison table."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.name, t.piece_algorithm, t.peer_algorithm,
               t.total_time_seconds, t.size, t.final_status,
               p.avg_speed, p.peak_speed, p.avg_peers,
               COALESCE(p.choke_cycles, 0) AS choke_cycles,
               (SELECT COUNT(*)   FROM algorithm_stats a WHERE a.torrent_id = t.id)          AS piece_count,
               (SELECT SUM(a.selected_as_rarest) FROM algorithm_stats a WHERE a.torrent_id = t.id) AS total_rarest_selections
        FROM torrents t
        LEFT JOIN performance_stats p ON t.id = p.torrent_id
        ORDER BY t.started_at DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route('/torrents/<torrent_id>/logs', methods=['GET'])
def get_torrent_logs(torrent_id: str):
    """Get live log messages from a running download."""
    manager = get_manager()
    download = manager.get_download(torrent_id)
    if download is None:
        return jsonify({"error": "Torrent not found"}), 404

    since = request.args.get('since', 0, type=int)
    logs = download.get_logs(since_seq=since)
    return jsonify({"logs": logs})


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": time.time()})


def create_app():
    """Create and configure the Flask application."""
    init_database()
    _start_event_loop()
    return app


def run_server(host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Run the API server."""
    init_database()
    _start_event_loop()
    logger.info(f"Starting API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_server(debug=True)
