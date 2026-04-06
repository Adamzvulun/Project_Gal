# מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent
# Distributed File Sharing System in BitTorrent Style

A complete BitTorrent-style distributed file sharing system with a Python engine and Java GUI.

## Architecture

```
┌─────────────────────────────────────────┐
│              Client Layer               │
│  ┌──────────────┐  ┌─────────────────┐  │
│  │   Java GUI   │  │   HTTP Client   │  │
│  │   (Swing)    │  │  (REST calls)   │  │
│  └──────────────┘  └─────────────────┘  │
└─────────────────────┬───────────────────┘
                      │ REST API (localhost:5000)
┌─────────────────────┴───────────────────┐
│           BitTorrent Engine (Python)    │
│  ┌──────────────────────────────────┐   │
│  │  REST API Server (Flask)         │   │
│  │  TorrentMetadata (Bencode)       │   │
│  │  Security (Validation & Logging) │   │
│  └──────────────┬───────────────────┘   │
│  ┌──────────────┴───────────────────┐   │
│  │      DownloadManager             │   │
│  │      (Tit-for-Tat choke/unchoke) │   │
│  └──┬──────────┬──────────┬─────────┘   │
│  ┌──┴───┐  ┌───┴────┐  ┌─┴──────────┐  │
│  │Track-│  │Piece   │  │Peer        │  │
│  │er    │  │Manager │  │Connection  │  │
│  │Client│  │(rarest │  │(TCP/BEP-3) │  │
│  └──────┘  │ first) │  └────────────┘  │
│            └────────┘                   │
└─────────────────────────────────────────┘
```

## Project Structure

```
project/
├── start.sh                 # One-click launcher (Linux/macOS)
├── start.bat                # One-click launcher (Windows)
├── requirements.txt
├── README.md
├── python_engine/           # BitTorrent engine (Python)
│   ├── bencode.py           # Bencode encoder/decoder
│   ├── torrent_metadata.py  # .torrent file parser
│   ├── tracker_client.py    # HTTP tracker communication
│   ├── peer_connection.py   # Peer Wire Protocol (BEP-3)
│   ├── piece_manager.py     # Piece tracking & rarest-first algorithm
│   ├── download_manager.py  # Central download coordinator & Tit-for-Tat
│   ├── security.py          # Hash verification & malicious peer detection
│   ├── api_server.py        # REST API server (Flask)
│   ├── main.py              # CLI entry point
│   └── tests/               # Unit tests
│       ├── test_bencode.py
│       ├── test_torrent_metadata.py
│       ├── test_tracker_client.py
│       ├── test_peer_connection.py
│       ├── test_piece_manager.py
│       ├── test_security.py
│       ├── test_download_manager.py
│       └── test_api_server.py
├── java_gui/                # GUI client (Java Swing)
│   └── src/
│       ├── TorrentClientGUI.java      # Main window
│       ├── ApiService.java            # REST API client
│       └── AlgorithmStatsDialog.java  # Statistics visualization dialog
└── data/                    # Created at runtime
    ├── state/               # JSON state files (download resume)
    └── history.db           # SQLite database
```

## Python Modules

| Module | Responsibility |
|--------|---------------|
| `bencode.py` | Encode/decode Bencode format (numbers, strings, lists, dictionaries) |
| `torrent_metadata.py` | Read `.torrent` files, decode Bencode, store metadata, compute `info_hash` |
| `tracker_client.py` | Send announce requests to tracker, parse response, extract peer list |
| `peer_connection.py` | Manage TCP connection to one peer: handshake, send/receive messages |
| `piece_manager.py` | Track piece status, peer frequency counts, implement rarest-first |
| `download_manager.py` | Central download logic: manage peers, choke/unchoke, request queue |
| `security.py` | SHA-1 verification, timeouts, malicious peer detection/disconnection |
| `api_server.py` | Local HTTP server (Flask) providing REST API for the Java GUI |

## Java Classes

| Class | Responsibility |
|-------|---------------|
| `TorrentClientGUI` | Main window with download table, progress bars, and control buttons |
| `ApiService` | HTTP client for communicating with the Python REST API |
| `AlgorithmStatsDialog` | Statistics visualization dialog with bar charts for piece/peer algorithm performance |

## Algorithms

### Piece Selection: Rarest-First
Selects pieces held by the fewest peers to maximize piece availability across the swarm. Falls back to random selection from the rarest set to avoid hot-spotting.

### Peer Selection: Tit-for-Tat (Choke/Unchoke)
Rewards contributing peers by unchoking the top-K uploaders every 10 seconds. Includes optimistic unchoke of one random peer to discover new partners.

### Baseline Comparisons
- **Random Piece Selection**: Picks any missing piece at random
- **Round-Robin Peer Selection**: Distributes unchokes in turn without regard to contribution

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/torrents` | Start a new download |
| GET | `/torrents` | Get all download statuses |
| GET | `/torrents/{id}` | Get specific download status |
| POST | `/torrents/{id}/pause` | Pause a download |
| POST | `/torrents/{id}/resume` | Resume a download |
| POST | `/torrents/{id}/cancel` | Cancel a download |
| GET | `/torrents/{id}/logs?since=N` | Incremental log polling (sequence-based) |
| GET | `/algorithm-stats/{id}` | Piece/peer algorithm performance statistics |
| GET | `/history` | Get download history (SQLite) |
| GET | `/events` | Get event log |
| GET | `/health` | Health check |

## Persistence

- **JSON files** (`data/state/`): Real-time download state for recovery after restart
- **SQLite** (`data/history.db`): Historical data, performance stats, algorithm stats, event log
- **Downloads**: Saved to the directory chosen by the user via the GUI folder picker (not a fixed path)

## Setup & Running

### One-click (recommended)

```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

Both scripts automatically install Python and Java if missing, compile the Java GUI, start the Flask API server in the background, and launch the GUI. The server is shut down automatically when the GUI is closed.

### Manual

```bash
# Terminal 1: Start Python API server
pip install -r requirements.txt
python -m python_engine.api_server

# Terminal 2: Compile and run Java GUI
javac -cp java_gui/lib/json.jar -d java_gui/build java_gui/src/*.java
java -cp "java_gui/build:java_gui/lib/json.jar" TorrentClientGUI
```

### CLI only (no GUI)

```bash
python -m python_engine path/to/file.torrent --output ./downloads
# Optional flags: --piece-algorithm rarest_first|random  --peer-algorithm tit_for_tat|round_robin
```

### Run Tests
```bash
python -m pytest python_engine/tests/ -v
```

## Security Features

- **SHA-1 hash verification** for every downloaded piece
- **Peer reputation tracking** with automatic banning
- **Protocol validation** to detect malicious/faulty peers
- **Message size limits** to prevent flooding attacks
- **Connection timeouts** to handle unresponsive peers

## References

1. Bram Cohen, "Incentives Build Robustness in BitTorrent" (2003)
2. A. Legout et al., "Rarest First and Choke Algorithms Are Enough" (IMC 2006)
3. A. Legout et al., "Understanding BitTorrent: An Experimental Perspective"
4. M. Piatek et al., "Do Incentives Build Robustness in BitTorrent? (BitTyrant)" (NSDI 2007)
5. F. Azzedin, "Modeling BitTorrent choking algorithm using game theory" (2016)
6. BEP-3 — The BitTorrent Protocol Specification
