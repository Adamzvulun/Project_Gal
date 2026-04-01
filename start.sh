#!/usr/bin/env bash
#
# Project Gal - BitTorrent Client Launcher
# Starts the Python API server and Java GUI with a single command.
#
# Usage:  ./start.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   Project Gal - BitTorrent Client${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ---------- Check Python ----------
echo -e "${YELLOW}[1/5] Checking Python...${NC}"
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed.${NC}"
    echo "       Install it from https://www.python.org/downloads/"
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)
PY_VERSION=$($PYTHON --version 2>&1)
echo -e "       Found: ${GREEN}$PY_VERSION${NC}"

# ---------- Check Java ----------
echo -e "${YELLOW}[2/5] Checking Java...${NC}"
if ! command -v java &>/dev/null || ! command -v javac &>/dev/null; then
    echo -e "${RED}ERROR: Java JDK is not installed (need both java and javac).${NC}"
    echo "       Install JDK 11+ from https://adoptium.net/"
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | head -1)
echo -e "       Found: ${GREEN}$JAVA_VERSION${NC}"

# ---------- Install Python dependencies ----------
echo -e "${YELLOW}[3/5] Installing Python dependencies...${NC}"
$PYTHON -m pip install --quiet flask aiohttp 2>/dev/null || \
    $PYTHON -m pip install flask aiohttp
echo -e "       ${GREEN}Done${NC}"

# ---------- Compile Java GUI ----------
echo -e "${YELLOW}[4/5] Compiling Java GUI...${NC}"
mkdir -p java_gui/build

if [ ! -f java_gui/lib/json.jar ]; then
    echo "       Downloading org.json library..."
    mkdir -p java_gui/lib
    curl -sL "https://repo1.maven.org/maven2/org/json/json/20240303/json-20240303.jar" \
        -o java_gui/lib/json.jar
fi

javac -cp java_gui/lib/json.jar -d java_gui/build java_gui/src/*.java 2>/dev/null
echo -e "       ${GREEN}Done${NC}"

# ---------- Launch ----------
echo -e "${YELLOW}[5/5] Launching...${NC}"
echo ""

# Create data directories
mkdir -p data/downloads data/state

# Start Python API server in background
echo -e "  Starting API server on ${GREEN}http://localhost:5000${NC} ..."
$PYTHON -m python_engine.api_server &
API_PID=$!

# Give the server a moment to start
sleep 2

# Check server is running
if ! kill -0 $API_PID 2>/dev/null; then
    echo -e "${RED}ERROR: API server failed to start. Check the logs above.${NC}"
    exit 1
fi

# Cleanup function - kill the server when GUI closes
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down API server (PID $API_PID)...${NC}"
    kill $API_PID 2>/dev/null
    wait $API_PID 2>/dev/null
    echo -e "${GREEN}Goodbye!${NC}"
}
trap cleanup EXIT INT TERM

echo -e "  ${GREEN}API server running${NC} (PID $API_PID)"
echo -e "  Launching GUI..."
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  GUI is open! Use it to add .torrent${NC}"
echo -e "${CYAN}  files and manage downloads.${NC}"
echo -e "${CYAN}  Close the GUI window to stop.${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Run Java GUI in foreground (blocks until window is closed)
java -cp "java_gui/build:java_gui/lib/json.jar" TorrentClientGUI

# cleanup() runs automatically via trap when GUI exits
