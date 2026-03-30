"""
Security module.

Handles data integrity verification (SHA-1 hash per piece),
malicious peer detection, message validation, and security logging.
"""

import hashlib
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Security thresholds
MAX_HASH_FAILURES_PER_PEER = 3
MAX_PROTOCOL_VIOLATIONS_PER_PEER = 5
MAX_MESSAGE_SIZE = 2 * 1024 * 1024  # 2 MB
REQUEST_TIMEOUT = 60  # seconds
KEEP_ALIVE_TIMEOUT = 120  # seconds


class SecurityEvent:
    """Represents a security-related event."""

    def __init__(self, event_type: str, peer_key: str, description: str,
                 severity: str = "warning"):
        self.event_type = event_type
        self.peer_key = peer_key
        self.description = description
        self.severity = severity
        self.timestamp = time.time()

    def __repr__(self):
        return (
            f"SecurityEvent({self.event_type}, peer={self.peer_key}, "
            f"severity={self.severity})"
        )


class PeerReputation:
    """Tracks reputation and violations for a single peer."""

    def __init__(self, peer_key: str):
        self.peer_key = peer_key
        self.hash_failures = 0
        self.protocol_violations = 0
        self.invalid_messages = 0
        self.timeouts = 0
        self.successful_pieces = 0
        self.first_seen = time.time()
        self.last_violation = 0
        self.banned = False
        self.ban_reason: Optional[str] = None

    @property
    def should_ban(self) -> bool:
        if self.hash_failures >= MAX_HASH_FAILURES_PER_PEER:
            return True
        if self.protocol_violations >= MAX_PROTOCOL_VIOLATIONS_PER_PEER:
            return True
        return False

    @property
    def trust_score(self) -> float:
        """Score from 0.0 (untrustworthy) to 1.0 (trustworthy)."""
        total_interactions = (
            self.successful_pieces + self.hash_failures +
            self.protocol_violations + self.invalid_messages
        )
        if total_interactions == 0:
            return 0.5  # Neutral
        good = self.successful_pieces
        bad = self.hash_failures * 3 + self.protocol_violations * 2 + self.invalid_messages
        return max(0.0, min(1.0, good / (good + bad)))


class SecurityManager:
    """Manages security aspects of the BitTorrent client.

    Responsibilities:
    - Verify piece data integrity using SHA-1 hashes
    - Track peer reputation and detect malicious behavior
    - Validate protocol messages
    - Manage peer bans
    - Log security events
    """

    def __init__(self):
        self._peer_reputations: Dict[str, PeerReputation] = {}
        self._banned_peers: Set[str] = set()
        self._events: List[SecurityEvent] = []
        self._event_callbacks = []

    def verify_piece(self, piece_data: bytes, expected_hash: bytes) -> bool:
        """Verify piece data integrity using SHA-1.

        Args:
            piece_data: The downloaded piece data.
            expected_hash: Expected 20-byte SHA-1 hash from .torrent file.

        Returns:
            True if hash matches.
        """
        actual_hash = hashlib.sha1(piece_data).digest()
        return actual_hash == expected_hash

    def report_hash_failure(self, peer_key: str, piece_index: int):
        """Report a hash verification failure for a peer.

        Args:
            peer_key: Identifier for the peer.
            piece_index: Index of the piece that failed verification.
        """
        rep = self._get_reputation(peer_key)
        rep.hash_failures += 1
        rep.last_violation = time.time()

        event = SecurityEvent(
            "hash_failure", peer_key,
            f"Piece {piece_index} failed hash verification "
            f"(failures: {rep.hash_failures}/{MAX_HASH_FAILURES_PER_PEER})",
            severity="warning"
        )
        self._log_event(event)

        if rep.should_ban:
            self._ban_peer(peer_key, "Too many hash failures")

    def report_successful_piece(self, peer_key: str, piece_index: int):
        """Report a successfully verified piece from a peer."""
        rep = self._get_reputation(peer_key)
        rep.successful_pieces += 1

    def report_protocol_violation(self, peer_key: str, description: str):
        """Report a protocol violation by a peer.

        Args:
            peer_key: Identifier for the peer.
            description: Description of the violation.
        """
        rep = self._get_reputation(peer_key)
        rep.protocol_violations += 1
        rep.last_violation = time.time()

        event = SecurityEvent(
            "protocol_violation", peer_key,
            f"{description} (violations: {rep.protocol_violations}/"
            f"{MAX_PROTOCOL_VIOLATIONS_PER_PEER})",
            severity="warning"
        )
        self._log_event(event)

        if rep.should_ban:
            self._ban_peer(peer_key, f"Too many protocol violations: {description}")

    def report_invalid_message(self, peer_key: str, description: str):
        """Report an invalid or anomalous message from a peer."""
        rep = self._get_reputation(peer_key)
        rep.invalid_messages += 1
        rep.last_violation = time.time()

        event = SecurityEvent(
            "invalid_message", peer_key, description, severity="info"
        )
        self._log_event(event)

    def report_timeout(self, peer_key: str):
        """Report a timeout from a peer."""
        rep = self._get_reputation(peer_key)
        rep.timeouts += 1

        event = SecurityEvent(
            "timeout", peer_key,
            f"Peer timed out (timeouts: {rep.timeouts})",
            severity="info"
        )
        self._log_event(event)

    def validate_message_length(self, peer_key: str, length: int) -> bool:
        """Validate that a message length is within acceptable bounds.

        Args:
            peer_key: Identifier for the peer.
            length: Reported message length.

        Returns:
            True if the length is valid.
        """
        if length < 0:
            self.report_protocol_violation(peer_key, f"Negative message length: {length}")
            return False
        if length > MAX_MESSAGE_SIZE:
            self.report_protocol_violation(
                peer_key,
                f"Message too large: {length} bytes (max {MAX_MESSAGE_SIZE})"
            )
            return False
        return True

    def validate_piece_index(self, peer_key: str, piece_index: int,
                             num_pieces: int) -> bool:
        """Validate that a piece index is within valid range."""
        if piece_index < 0 or piece_index >= num_pieces:
            self.report_protocol_violation(
                peer_key,
                f"Invalid piece index: {piece_index} (max: {num_pieces - 1})"
            )
            return False
        return True

    def is_peer_banned(self, peer_key: str) -> bool:
        """Check if a peer is banned."""
        return peer_key in self._banned_peers

    def get_peer_reputation(self, peer_key: str) -> PeerReputation:
        """Get reputation info for a peer."""
        return self._get_reputation(peer_key)

    def get_banned_peers(self) -> Set[str]:
        """Get set of all banned peer keys."""
        return self._banned_peers.copy()

    def get_recent_events(self, limit: int = 100) -> List[SecurityEvent]:
        """Get the most recent security events."""
        return self._events[-limit:]

    def get_events_for_peer(self, peer_key: str) -> List[SecurityEvent]:
        """Get all security events for a specific peer."""
        return [e for e in self._events if e.peer_key == peer_key]

    def on_event(self, callback):
        """Register a callback for security events."""
        self._event_callbacks.append(callback)

    def _get_reputation(self, peer_key: str) -> PeerReputation:
        if peer_key not in self._peer_reputations:
            self._peer_reputations[peer_key] = PeerReputation(peer_key)
        return self._peer_reputations[peer_key]

    def _ban_peer(self, peer_key: str, reason: str):
        """Ban a peer and log the event."""
        rep = self._get_reputation(peer_key)
        rep.banned = True
        rep.ban_reason = reason
        self._banned_peers.add(peer_key)

        event = SecurityEvent(
            "peer_banned", peer_key,
            f"Peer banned: {reason}",
            severity="error"
        )
        self._log_event(event)
        logger.warning(f"Peer {peer_key} banned: {reason}")

    def _log_event(self, event: SecurityEvent):
        """Log a security event."""
        self._events.append(event)
        logger.log(
            logging.WARNING if event.severity == "warning"
            else logging.ERROR if event.severity == "error"
            else logging.INFO,
            f"Security: [{event.event_type}] {event.peer_key}: {event.description}"
        )

        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in security event callback: {e}")


# Privacy analysis documentation
TRACKER_PRIVACY_ANALYSIS = """
## Privacy Analysis: Tracker Communication

### Information Exposed During Announce

When the client sends an announce request to the tracker, the following
information is disclosed:

1. **info_hash** — Reveals which torrent (file) we are downloading.
   The tracker knows our download interest.

2. **peer_id** — A unique identifier that can track our client across
   multiple announce requests and potentially across different torrents.

3. **IP Address** — Our network address is visible to the tracker
   (and often to other peers in the swarm). This reveals our approximate
   geographic location.

4. **uploaded / downloaded** — The tracker knows how much data we have
   transferred, which can reveal usage patterns over time.

5. **port** — Our listening port, which combined with IP gives a complete
   network endpoint.

### Risks

- **Download Monitoring**: The tracker (or anyone who compromises it) can
  build a complete history of what files a user downloads.

- **Correlation Attacks**: The peer_id and IP can be used to correlate
  activity across multiple torrents.

- **Legal Exposure**: In some jurisdictions, the tracker's logs could be
  subpoenaed to identify users downloading specific content.

- **Traffic Analysis**: Even without content access, metadata about timing,
  volume, and frequency of announces can reveal behavioral patterns.

### Mitigations (Future Extensions)

- **DHT (Distributed Hash Table)**: Eliminates dependence on a single
  tracker server, distributing peer discovery across the network.

- **Peer Exchange (PEX)**: Peers share known peer addresses directly,
  reducing tracker queries.

- **Protocol Encryption**: Encrypt peer-to-peer traffic to prevent
  deep packet inspection.

- **Randomized peer_id**: Generate a new peer_id for each session to
  reduce tracking capability.
"""
