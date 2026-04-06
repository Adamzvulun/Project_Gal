#!/usr/bin/env bash
#
# Project Gal - BitTorrent Client Launcher
# Starts the Python API server and Java GUI with a single command.
# Auto-installs Python and Java if missing (apt/brew/dnf).
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

# Detect package manager
install_package() {
    local package_name="$1"
    local apt_name="$2"
    local brew_name="$3"
    local dnf_name="$4"

    echo -e "       ${YELLOW}$package_name not found. Attempting to install...${NC}"

    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq "$apt_name"
    elif command -v brew &>/dev/null; then
        brew install "$brew_name"
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y "$dnf_name"
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm "$apt_name"
    else
        echo -e "${RED}ERROR: Could not find a package manager (apt/brew/dnf/pacman).${NC}"
        echo "       Please install $package_name manually."
        exit 1
    fi
}

# ---------- Check/Install Python ----------
echo -e "${YELLOW}[1/5] Checking Python...${NC}"
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    install_package "Python 3" "python3" "python@3" "python3"
fi

PYTHON=$(command -v python3 || command -v python)
PY_VERSION=$($PYTHON --version 2>&1)
echo -e "       Found: ${GREEN}$PY_VERSION${NC}"

# Make sure pip is available
if ! $PYTHON -m pip --version &>/dev/null; then
    echo -e "       ${YELLOW}pip not found. Installing...${NC}"
    install_package "python3-pip" "python3-pip" "python@3" "python3-pip"
fi

# ---------- Check/Install Java ----------
echo -e "${YELLOW}[2/5] Checking Java...${NC}"
NEED_JAVA=false
if ! command -v java &>/dev/null; then
    NEED_JAVA=true
fi
if ! command -v javac &>/dev/null; then
    NEED_JAVA=true
fi

if [ "$NEED_JAVA" = true ]; then
    install_package "Java JDK" "default-jdk" "openjdk" "java-21-openjdk-devel"
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
