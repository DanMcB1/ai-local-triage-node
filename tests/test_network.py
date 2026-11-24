"""Tests for the outbound network guard."""

from __future__ import annotations

import socket
import unittest

from triage.engine import triage
from triage.network import GUARD, NetworkBlockedError


class NetworkGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        GUARD.restore()
        GUARD.blocked_attempts.clear()
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        GUARD.disable()
        GUARD.restore()
        GUARD.blocked_attempts.clear()

    def test_blocks_outbound_create_connection(self) -> None:
        GUARD.enable()
        with self.assertRaises(NetworkBlockedError):
            socket.create_connection(("huggingface.co", 443), timeout=1)
        with self.assertRaises(NetworkBlockedError):
            socket.create_connection(("8.8.8.8", 53), timeout=1)
        self.assertGreaterEqual(len(GUARD.blocked_attempts), 2)

    def test_loopback_is_not_blocked(self) -> None:
        GUARD.enable()
        with self.assertRaises(OSError) as ctx:
            socket.create_connection(("127.0.0.1", 1), timeout=0.3)
        self.assertNotIsInstance(ctx.exception, NetworkBlockedError)

    def test_connect_ex_returns_unreachable_instead_of_raising(self) -> None:
        GUARD.enable()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            err = sock.connect_ex(("1.1.1.1", 443))
        finally:
            sock.close()
        self.assertNotEqual(err, 0)

    def test_triage_still_works_with_guard_on(self) -> None:
        GUARD.enable()
        result = triage(
            "My Civic won't start on Route 30. I need a tow to Lakeside Honda.",
            backend="rules",
            network_off=True,
        )
        self.assertEqual(result.category, "service")
        self.assertEqual(result.urgency, "critical")
        self.assertTrue(result.network_guard)

    def test_probe_reports_blocked_by_guard(self) -> None:
        GUARD.enable()
        probe = GUARD.probe_outbound("example.com", 443, timeout=1)
        self.assertTrue(probe["blocked_by_guard"])
        self.assertFalse(probe["opened"])
        self.assertTrue(probe["guard_enabled"])

    def test_disable_allows_code_path_without_guard_error(self) -> None:
        GUARD.enable()
        GUARD.disable()
        # Documentation IP; we do not care whether the network path exists,
        # only that the guard itself does not raise.
        try:
            socket.create_connection(("192.0.2.1", 1), timeout=0.2)
        except NetworkBlockedError:
            self.fail("disabled guard still blocked a connection")
        except OSError:
            pass


if __name__ == "__main__":
    unittest.main()
