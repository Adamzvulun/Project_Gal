"""
Tests for the Security module.
"""

import hashlib
import pytest
from python_engine.security import (
    SecurityManager, SecurityEvent, PeerReputation,
    MAX_HASH_FAILURES_PER_PEER, MAX_PROTOCOL_VIOLATIONS_PER_PEER
)


class TestPeerReputation:
    def test_initial_reputation(self):
        rep = PeerReputation("peer1")
        assert rep.hash_failures == 0
        assert rep.protocol_violations == 0
        assert rep.successful_pieces == 0
        assert rep.banned is False
        assert rep.trust_score == 0.5  # Neutral

    def test_should_ban_hash_failures(self):
        rep = PeerReputation("peer1")
        rep.hash_failures = MAX_HASH_FAILURES_PER_PEER
        assert rep.should_ban is True

    def test_should_ban_protocol_violations(self):
        rep = PeerReputation("peer1")
        rep.protocol_violations = MAX_PROTOCOL_VIOLATIONS_PER_PEER
        assert rep.should_ban is True

    def test_trust_score_good_peer(self):
        rep = PeerReputation("peer1")
        rep.successful_pieces = 100
        assert rep.trust_score > 0.9

    def test_trust_score_bad_peer(self):
        rep = PeerReputation("peer1")
        rep.hash_failures = 5
        rep.protocol_violations = 5
        assert rep.trust_score < 0.2


class TestSecurityManager:
    def setup_method(self):
        self.sm = SecurityManager()

    def test_verify_piece_success(self):
        data = b'hello world'
        expected = hashlib.sha1(data).digest()
        assert self.sm.verify_piece(data, expected) is True

    def test_verify_piece_failure(self):
        data = b'hello world'
        wrong_hash = b'\xff' * 20
        assert self.sm.verify_piece(data, wrong_hash) is False

    def test_report_hash_failure(self):
        self.sm.report_hash_failure("peer1", 0)
        rep = self.sm.get_peer_reputation("peer1")
        assert rep.hash_failures == 1
        assert not self.sm.is_peer_banned("peer1")

    def test_ban_after_hash_failures(self):
        for i in range(MAX_HASH_FAILURES_PER_PEER):
            self.sm.report_hash_failure("peer1", i)
        assert self.sm.is_peer_banned("peer1")

    def test_report_protocol_violation(self):
        self.sm.report_protocol_violation("peer1", "Invalid message length")
        rep = self.sm.get_peer_reputation("peer1")
        assert rep.protocol_violations == 1

    def test_ban_after_protocol_violations(self):
        for i in range(MAX_PROTOCOL_VIOLATIONS_PER_PEER):
            self.sm.report_protocol_violation("peer1", f"Violation {i}")
        assert self.sm.is_peer_banned("peer1")

    def test_report_successful_piece(self):
        self.sm.report_successful_piece("peer1", 0)
        rep = self.sm.get_peer_reputation("peer1")
        assert rep.successful_pieces == 1

    def test_validate_message_length_valid(self):
        assert self.sm.validate_message_length("peer1", 1000) is True

    def test_validate_message_length_negative(self):
        assert self.sm.validate_message_length("peer1", -1) is False

    def test_validate_message_length_too_large(self):
        assert self.sm.validate_message_length("peer1", 10_000_000) is False

    def test_validate_piece_index_valid(self):
        assert self.sm.validate_piece_index("peer1", 5, 10) is True

    def test_validate_piece_index_negative(self):
        assert self.sm.validate_piece_index("peer1", -1, 10) is False

    def test_validate_piece_index_too_large(self):
        assert self.sm.validate_piece_index("peer1", 10, 10) is False

    def test_get_banned_peers(self):
        for i in range(MAX_HASH_FAILURES_PER_PEER):
            self.sm.report_hash_failure("bad_peer", i)
        banned = self.sm.get_banned_peers()
        assert "bad_peer" in banned

    def test_get_recent_events(self):
        self.sm.report_hash_failure("peer1", 0)
        self.sm.report_protocol_violation("peer2", "test")
        events = self.sm.get_recent_events()
        assert len(events) == 2

    def test_get_events_for_peer(self):
        self.sm.report_hash_failure("peer1", 0)
        self.sm.report_protocol_violation("peer2", "test")
        events = self.sm.get_events_for_peer("peer1")
        assert len(events) == 1
        assert events[0].peer_key == "peer1"

    def test_report_timeout(self):
        self.sm.report_timeout("peer1")
        rep = self.sm.get_peer_reputation("peer1")
        assert rep.timeouts == 1

    def test_report_invalid_message(self):
        self.sm.report_invalid_message("peer1", "Unrequested piece")
        rep = self.sm.get_peer_reputation("peer1")
        assert rep.invalid_messages == 1

    def test_event_callback(self):
        events_received = []
        self.sm.on_event(lambda e: events_received.append(e))
        self.sm.report_hash_failure("peer1", 0)
        assert len(events_received) == 1
        assert events_received[0].event_type == "hash_failure"


class TestSecurityEvent:
    def test_event_creation(self):
        event = SecurityEvent("test", "peer1", "description", "warning")
        assert event.event_type == "test"
        assert event.peer_key == "peer1"
        assert event.description == "description"
        assert event.severity == "warning"
        assert event.timestamp > 0

    def test_event_repr(self):
        event = SecurityEvent("test", "peer1", "desc")
        r = repr(event)
        assert "test" in r
        assert "peer1" in r
