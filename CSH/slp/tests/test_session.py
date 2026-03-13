"""Unit tests for slp.protocol.session."""

import time
import pytest

from slp.protocol.session import (
    ReplayWindow, SLPSession, SessionState,
    WINDOW_SIZE, SESSION_TIMEOUT, REKEY_MESSAGE_LIMIT, REKEY_TIME_LIMIT,
)


class TestReplayWindow:
    def test_first_packet_accepted(self):
        w = ReplayWindow()
        assert w.check_and_accept(1) is True

    def test_sequence_zero_rejected(self):
        w = ReplayWindow()
        assert w.check_and_accept(0) is False

    def test_duplicate_rejected(self):
        w = ReplayWindow()
        assert w.check_and_accept(1) is True
        assert w.check_and_accept(1) is False

    def test_monotonic_accepted(self):
        w = ReplayWindow()
        for i in range(1, 100):
            assert w.check_and_accept(i) is True

    def test_out_of_order_within_window(self):
        w = ReplayWindow()
        assert w.check_and_accept(5) is True
        assert w.check_and_accept(3) is True
        assert w.check_and_accept(4) is True
        assert w.check_and_accept(1) is True
        assert w.check_and_accept(2) is True

    def test_out_of_order_duplicate_rejected(self):
        w = ReplayWindow()
        w.check_and_accept(5)
        w.check_and_accept(3)
        assert w.check_and_accept(3) is False

    def test_too_old_rejected(self):
        w = ReplayWindow(size=64)
        w.check_and_accept(100)
        # 100 - 64 = 36; seq 36 is the boundary
        assert w.check_and_accept(36) is False
        assert w.check_and_accept(37) is True

    def test_large_window_jump(self):
        w = ReplayWindow(size=64)
        w.check_and_accept(1)
        w.check_and_accept(1000)
        # Old sequences are all out of window now.
        assert w.check_and_accept(1) is False
        assert w.check_and_accept(936) is False
        assert w.check_and_accept(937) is True

    def test_max_sequence_property(self):
        w = ReplayWindow()
        assert w.max_sequence == 0
        w.check_and_accept(42)
        assert w.max_sequence == 42

    def test_window_size_2048(self):
        assert WINDOW_SIZE == 2048
        w = ReplayWindow()
        # Accept seq 2049, then check 1 (at boundary edge).
        w.check_and_accept(2049)
        assert w.check_and_accept(1) is False
        assert w.check_and_accept(2) is True  # 2049 - 2 = 2047 < 2048


class TestSLPSession:
    def test_initial_state(self):
        s = SLPSession(session_id=0xDEAD)
        assert s.session_id == 0xDEAD
        assert s.state == SessionState.HANDSHAKE
        assert s.encryption is None

    def test_next_sequence_monotonic(self):
        s = SLPSession(1)
        assert s.next_sequence() == 1
        assert s.next_sequence() == 2
        assert s.next_sequence() == 3

    def test_accept_sequence(self):
        s = SLPSession(1)
        assert s.accept_sequence(1) is True
        assert s.accept_sequence(1) is False
        assert s.accept_sequence(2) is True

    def test_mark_established(self):
        s = SLPSession(1)
        s.mark_established()
        assert s.state == SessionState.ESTABLISHED

    def test_mark_closed(self):
        s = SLPSession(1)
        s.mark_established()
        s.mark_closed()
        assert s.state == SessionState.CLOSED

    def test_timeout(self):
        s = SLPSession(1)
        s.last_activity = time.time() - 31
        assert s.is_timed_out(timeout=30.0) is True

    def test_not_timed_out(self):
        s = SLPSession(1)
        assert s.is_timed_out(timeout=30.0) is False

    def test_needs_rekey_false_when_not_established(self):
        s = SLPSession(1)
        assert s.needs_rekey() is False

    def test_needs_rekey_after_message_limit(self):
        s = SLPSession(1)
        s.mark_established()
        s._send_counter = REKEY_MESSAGE_LIMIT
        assert s.needs_rekey() is True

    def test_needs_rekey_after_time_limit(self):
        s = SLPSession(1)
        s.mark_established()
        s._established_at = time.time() - REKEY_TIME_LIMIT - 1
        assert s.needs_rekey() is True


class TestSessionState:
    def test_enum_values(self):
        assert SessionState.HANDSHAKE == 0
        assert SessionState.ESTABLISHED == 1
        assert SessionState.REKEYING == 2
        assert SessionState.CLOSED == 3
