"""
SLP Session State Management.

Tracks per-session state: encryption context, sequence counters,
anti-replay sliding window, and timeout logic.
"""

import enum
import time


class SessionState(enum.IntEnum):
    HANDSHAKE   = 0
    ESTABLISHED = 1
    REKEYING    = 2
    CLOSED      = 3


# Anti-replay sliding window size (bits).
WINDOW_SIZE = 2048

# Session is considered dead after this many seconds without a message.
SESSION_TIMEOUT = 30.0

# Rekey thresholds.
REKEY_MESSAGE_LIMIT = 2**32
REKEY_TIME_LIMIT = 3600  # 1 hour


class ReplayWindow:
    """Bitmap-based sliding window for anti-replay protection.

    Accepts 64-bit sequence numbers.  Rejects duplicates and numbers
    that fall behind the window.
    """

    def __init__(self, size: int = WINDOW_SIZE):
        self._size = size
        self._max_seq: int = 0
        # Bitmap stored as a Python int (arbitrary precision).
        self._bitmap: int = 0

    def check_and_accept(self, seq: int) -> bool:
        """Return True if *seq* is acceptable (not a replay), and mark it.

        Rules:
          - seq > max_seq → slide window, accept.
          - max_seq - size < seq <= max_seq → check bitmap.
          - seq <= max_seq - size → too old, reject.
        """
        if seq == 0:
            # Sequence 0 is reserved / never used.
            return False

        if self._max_seq == 0:
            # First packet.
            self._max_seq = seq
            self._bitmap = 1
            return True

        if seq > self._max_seq:
            shift = seq - self._max_seq
            if shift >= self._size:
                self._bitmap = 1
            else:
                self._bitmap = (self._bitmap << shift) | 1
                # Mask to window size.
                self._bitmap &= (1 << self._size) - 1
            self._max_seq = seq
            return True

        diff = self._max_seq - seq
        if diff >= self._size:
            return False  # Too old.

        bit = 1 << diff
        if self._bitmap & bit:
            return False  # Duplicate.

        self._bitmap |= bit
        return True

    @property
    def max_sequence(self) -> int:
        return self._max_seq


class SLPSession:
    """Per-session state for the SLP protocol."""

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.state = SessionState.HANDSHAKE
        self.encryption = None  # TripleLayerEncryption instance
        self.remote_addr = None

        # Counters
        self._send_counter: int = 0
        self._recv_window = ReplayWindow()

        # Timestamps
        self.created_at: float = time.time()
        self.last_activity: float = self.created_at
        self._established_at: float = 0.0

    # ── Sequence management ───────────────────────────────────────────

    def next_sequence(self) -> int:
        """Return the next monotonic send sequence number."""
        self._send_counter += 1
        return self._send_counter

    def accept_sequence(self, seq: int) -> bool:
        """Check a received sequence against the replay window."""
        ok = self._recv_window.check_and_accept(seq)
        if ok:
            self.last_activity = time.time()
        return ok

    # ── Lifecycle ─────────────────────────────────────────────────────

    def mark_established(self):
        self.state = SessionState.ESTABLISHED
        self._established_at = time.time()
        self.last_activity = time.time()

    def mark_closed(self):
        self.state = SessionState.CLOSED

    def is_timed_out(self, timeout: float = SESSION_TIMEOUT) -> bool:
        return (time.time() - self.last_activity) > timeout

    def needs_rekey(self) -> bool:
        if self.state != SessionState.ESTABLISHED:
            return False
        if self._send_counter >= REKEY_MESSAGE_LIMIT:
            return True
        if self._established_at and (time.time() - self._established_at) > REKEY_TIME_LIMIT:
            return True
        return False
