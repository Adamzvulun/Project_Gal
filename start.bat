@echo off
REM Project Gal - BitTorrent Client Launcher (Windows)
REM Starts the Python API server and Java GUI with a single command.
REM
REM Usage:  start.bat
REM

echo ========================================
echo    Project Gal - BitTorrent Client
echo ========================================
echo.

REM ---------- Check Python ----------
echo [1/5] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python 3 is not installed.
    echo        Install it from https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version

REM ---------- Check Java ----------
echo [2/5] Checking Java...
where java >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Java is not installed.
    echo        Install JDK 11+ from https://adoptium.net/
    pause
    exit /b 1
)
where javac >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: javac not found. Install a full JDK, not just JRE.
    pause
    exit /b 1
)
java -version 2>&1 | findstr /i "version"

REM ---------- Install Python dependencies ----------
echo [3/5] Installing Python dependencies...
python -m pip install --quiet flask aiohttp 2>nul
echo        Done

REM ---------- Compile Java GUI ----------
echo [4/5] Compiling Java GUI...
if not exist java_gui\build mkdir java_gui\build

if not exist java_gui\lib\json.jar (
    echo        Downloading org.json library...
    if not exist java_gui\lib mkdir java_gui\lib
    curl -sL "https://repo1.maven.org/maven2/org/json/json/20240303/json-20240303.jar" -o java_gui\lib\json.jar
)

javac -cp java_gui\lib\json.jar -d java_gui\build java_gui\src\*.java
echo        Done

REM ---------- Create data directories ----------
if not exist data\downloads mkdir data\downloads
if not exist data\state mkdir data\state

REM ---------- Launch ----------
echo [5/5] Launching...
echo.

REM Start Python API server in a separate window
echo   Starting API server on http://localhost:5000 ...
start "Project Gal API Server" /min python -m python_engine.api_server

REM Wait for server to start
timeout /t 2 /nobreak >nul

echo   Launching GUI...
echo.
echo ========================================
echo   GUI is open! Use it to add .torrent
echo   files and manage downloads.
echo   Close the GUI window to stop.
echo ========================================
echo.

REM Run GUI (blocks until window closes)
java -cp "java_gui\build;java_gui\lib\json.jar" TorrentClientGUI

REM Kill the API server when GUI closes
echo.
echo Shutting down API server...
taskkill /FI "WINDOWTITLE eq Project Gal API Server" /F >nul 2>&1
echo Goodbye!
pause
