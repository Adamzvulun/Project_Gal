"""
Tracker client module.

Handles communication with BitTorrent trackers using the HTTP tracker protocol.
Sends announce requests and parses peer lists from responses.
"""

import asyncio
import logging
import os
import struct
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode, quote

import aiohttp

from . import bencode

logger = logging.getLogger(__name__)

# Default values
DEFAULT_PORT = 6881
PEER_ID_PREFIX = b'-PG0001-'  # Project Gal client v0.0.1


def generate_peer_id() -> bytes:
    """Generate a unique 20-byte peer ID.

    Format: -PG0001- followed by 12 random bytes.
    """
    random_bytes = os.urandom(12)
    return PEER_ID_PREFIX + random_bytes


class Peer:
    """Represents a peer in the swarm."""

    def __init__(self, ip: str, port: int, peer_id: Optional[bytes] = None):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id

    def __repr__(self):
        return f"Peer({self.ip}:{self.port})"

    def __eq__(self, other):
        if not isinstance(other, Peer):
            return False
        return self.ip == other.ip and self.port == other.port

    def __hash__(self):
        return hash((self.ip, self.port))


class TrackerResponse:
    """Parsed response from a tracker announce request."""

    def __init__(self, data: dict):
        self.failure_reason = None
        self.warning_message = None
        self.interval = 1800  # Default 30 minutes
        self.min_interval = None
        self.tracker_id = None
        self.complete = 0  # Seeders
        self.incomplete = 0  # Leechers
        self.peers: List[Peer] = []

        self._parse(data)

    def _parse(self, data: dict):
        if b'failure reason' in data:
            self.failure_reason = data[b'failure reason'].decode('utf-8', errors='replace')
            return

        if b'warning message' in data:
            self.warning_message = data[b'warning message'].decode('utf-8', errors='replace')

        if b'interval' in data:
            self.interval = data[b'interval']

        if b'min interval' in data:
            self.min_interval = data[b'min interval']

        if b'tracker id' in data:
            self.tracker_id = data[b'tracker id']

        if b'complete' in data:
            self.complete = data[b'complete']

        if b'incomplete' in data:
            self.incomplete = data[b'incomplete']

        if b'peers' in data:
            peers_data = data[b'peers']
            if isinstance(peers_data, bytes):
                # Compact format: 6 bytes per peer (4 IP + 2 port)
                self.peers = self._parse_compact_peers(peers_data)
            elif isinstance(peers_data, list):
                # Regular format: list of dictionaries
                self.peers = self._parse_regular_peers(peers_data)

    @staticmethod
    def _parse_compact_peers(data: bytes) -> List[Peer]:
        """Parse compact peer format (6 bytes per peer)."""
        peers = []
        if len(data) % 6 != 0:
            logger.warning(f"Compact peers data length ({len(data)}) not multiple of 6")
            return peers

        for i in range(0, len(data), 6):
            ip_bytes = data[i:i + 4]
            port_bytes = data[i + 4:i + 6]
            ip = '.'.join(str(b) for b in ip_bytes)
            port = struct.unpack('!H', port_bytes)[0]
            peers.append(Peer(ip, port))

        return peers

    @staticmethod
    def _parse_regular_peers(data: list) -> List[Peer]:
        """Parse regular peer format (list of dicts)."""
        peers = []
        for peer_dict in data:
            if not isinstance(peer_dict, dict):
                continue
            ip = peer_dict.get(b'ip', b'').decode('utf-8', errors='replace')
            port = peer_dict.get(b'port', 0)
            peer_id = peer_dict.get(b'peer id')
            if ip and port:
                peers.append(Peer(ip, port, peer_id))
        return peers


class TrackerClient:
    """Communicates with BitTorrent trackers.

    Handles sending announce requests and parsing responses.
    Supports periodic re-announcing based on tracker interval.
    """

    def __init__(self, announce_url: str, info_hash: bytes, peer_id: bytes,
                 port: int = DEFAULT_PORT):
        """Initialize the tracker client.

        Args:
            announce_url: The tracker's announce URL.
            info_hash: 20-byte SHA-1 hash of the torrent's info dictionary.
            peer_id: 20-byte unique identifier for this client.
            port: Port the client is listening on.
        """
        self.announce_url = announce_url
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.port = port

        self.uploaded = 0
        self.downloaded = 0
        self.left = 0

        self._interval = 1800
        self._min_interval = None
        self._tracker_id = None
        self._last_announce_time = 0
        self._session: Optional[aiohttp.ClientSession] = None
        self._announce_task: Optional[asyncio.Task] = None
        self._running = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def announce(self, event: Optional[str] = None,
                       uploaded: Optional[int] = None,
                       downloaded: Optional[int] = None,
                       left: Optional[int] = None) -> TrackerResponse:
        """Send an announce request to the tracker.

        Args:
            event: One of 'started', 'completed', 'stopped', or None for periodic.
            uploaded: Override uploaded byte count.
            downloaded: Override downloaded byte count.
            left: Override remaining byte count.

        Returns:
            TrackerResponse with peer list and swarm info.
        """
        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'port': self.port,
            'uploaded': uploaded if uploaded is not None else self.uploaded,
            'downloaded': downloaded if downloaded is not None else self.downloaded,
            'left': left if left is not None else self.left,
            'compact': 1,
        }

        if event:
            params['event'] = event

        if self._tracker_id:
            params['trackerid'] = self._tracker_id

        # Build the URL with proper encoding for binary params
        url = self._build_announce_url(params)

        logger.info(f"Announcing to tracker: event={event}, left={params['left']}")

        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise TrackerError(
                        f"Tracker returned HTTP {resp.status}: {await resp.text()}"
                    )
                raw = await resp.read()
        except aiohttp.ClientError as e:
            raise TrackerError(f"Failed to connect to tracker: {e}")

        try:
            decoded = bencode.decode(raw)
        except bencode.BencodeDecodeError as e:
            raise TrackerError(f"Failed to decode tracker response: {e}")

        response = TrackerResponse(decoded)

        if response.failure_reason:
            raise TrackerError(f"Tracker returned failure: {response.failure_reason}")

        if response.warning_message:
            logger.warning(f"Tracker warning: {response.warning_message}")

        self._interval = response.interval
        if response.min_interval:
            self._min_interval = response.min_interval
        if response.tracker_id:
            self._tracker_id = response.tracker_id

        self._last_announce_time = time.time()

        logger.info(
            f"Tracker response: {len(response.peers)} peers, "
            f"{response.complete} seeders, {response.incomplete} leechers, "
            f"interval={response.interval}s"
        )

        return response

    def _build_announce_url(self, params: dict) -> str:
        """Build the announce URL with properly encoded parameters."""
        # info_hash and peer_id need special URL encoding (binary)
        url_params = []
        for key, value in params.items():
            if key in ('info_hash', 'peer_id'):
                # URL-encode binary data byte by byte
                encoded = quote(value, safe='')
                url_params.append(f"{key}={encoded}")
            else:
                url_params.append(f"{key}={value}")

        separator = '&' if '?' in self.announce_url else '?'
        if '?' in self.announce_url:
            return self.announce_url + '&' + '&'.join(url_params)
        else:
            return self.announce_url + '?' + '&'.join(url_params)

    async def start_periodic_announce(self, callback=None):
        """Start periodic re-announcing based on tracker interval.

        Args:
            callback: Optional async function called with TrackerResponse
                      after each announce.
        """
        self._running = True
        self._announce_task = asyncio.create_task(
            self._periodic_announce_loop(callback)
        )

    async def _periodic_announce_loop(self, callback):
        """Internal loop for periodic announces."""
        while self._running:
            try:
                wait_time = max(self._interval, self._min_interval or 0)
                await asyncio.sleep(wait_time)

                if not self._running:
                    break

                response = await self.announce()
                if callback:
                    await callback(response)

            except TrackerError as e:
                logger.error(f"Periodic announce failed: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in periodic announce: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop periodic announcing and send 'stopped' event to tracker."""
        self._running = False

        if self._announce_task:
            self._announce_task.cancel()
            try:
                await self._announce_task
            except asyncio.CancelledError:
                pass

        try:
            await self.announce(event='stopped')
        except TrackerError:
            logger.warning("Failed to send 'stopped' event to tracker")

        if self._session and not self._session.closed:
            await self._session.close()

    async def completed(self):
        """Announce download completion to tracker."""
        return await self.announce(event='completed')

    def update_stats(self, uploaded: int, downloaded: int, left: int):
        """Update upload/download statistics for next announce."""
        self.uploaded = uploaded
        self.downloaded = downloaded
        self.left = left


class TrackerError(Exception):
    """Raised when tracker communication fails."""
    pass
