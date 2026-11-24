"""Outbound network guard.

When enabled, non-loopback TCP/UDP connections are refused. Localhost
(Streamlit, local sockets) still works. This is a demo of an air-gapped
path, not a kernel-level firewall.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any

PROBE_HOSTS = (
    ("huggingface.co", 443),
    ("example.com", 443),
    ("1.1.1.1", 443),
)


class NetworkBlockedError(OSError):
    """Raised when the guard refuses an outbound connection."""


def _is_loopback(host: str) -> bool:
    if not host:
        return False
    cleaned = host.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    if cleaned.lower() in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(cleaned).is_loopback
    except ValueError:
        return False


def _host_from_address(address: Any) -> str | None:
    if isinstance(address, (tuple, list)) and address:
        host = address[0]
        return host if isinstance(host, str) else str(host)
    if isinstance(address, str):
        # AF_UNIX path, or a packed address string.
        if address.startswith("/"):
            return None
        return address
    return None


class NetworkGuard:
    """Process-wide socket patch that blocks outbound connections."""

    def __init__(self) -> None:
        self.enabled = False
        self.blocked_attempts: list[str] = []
        self._orig_connect = socket.socket.connect
        self._orig_connect_ex = socket.socket.connect_ex
        self._orig_create = socket.create_connection
        self._patched = False

    def _deny(self, address: Any) -> None:
        host = _host_from_address(address)
        label = host or repr(address)
        self.blocked_attempts.append(label)
        raise NetworkBlockedError(
            f"Outbound connection to {label} blocked. "
            "This node is running with the network guard on; triage stays on this machine."
        )

    def _check(self, address: Any) -> None:
        if not self.enabled:
            return
        host = _host_from_address(address)
        if host is None:
            # Unix sockets are local.
            return
        if not _is_loopback(host):
            self._deny(address)

    def _connect(self, sock: socket.socket, address: Any, *args: Any, **kwargs: Any):
        self._check(address)
        return self._orig_connect(sock, address, *args, **kwargs)

    def _connect_ex(self, sock: socket.socket, address: Any, *args: Any, **kwargs: Any) -> int:
        if self.enabled:
            host = _host_from_address(address)
            if host is not None and not _is_loopback(host):
                self.blocked_attempts.append(host)
                return errno_host_unreachable()
        return self._orig_connect_ex(sock, address, *args, **kwargs)

    def _create_connection(self, address: Any, *args: Any, **kwargs: Any):
        self._check(address)
        return self._orig_create(address, *args, **kwargs)

    def enable(self) -> None:
        if not self._patched:
            # Use plain functions, not bound methods. Assigning a bound method
            # onto socket.socket would get bound a second time on lookup.
            guard = self

            def connect(sock: socket.socket, address: Any, *args: Any, **kwargs: Any):
                return guard._connect(sock, address, *args, **kwargs)

            def connect_ex(sock: socket.socket, address: Any, *args: Any, **kwargs: Any) -> int:
                return guard._connect_ex(sock, address, *args, **kwargs)

            def create_connection(address: Any, *args: Any, **kwargs: Any):
                return guard._create_connection(address, *args, **kwargs)

            socket.socket.connect = connect  # type: ignore[method-assign]
            socket.socket.connect_ex = connect_ex  # type: ignore[method-assign]
            socket.create_connection = create_connection  # type: ignore[assignment]
            self._patched = True
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def restore(self) -> None:
        if self._patched:
            socket.socket.connect = self._orig_connect  # type: ignore[method-assign]
            socket.socket.connect_ex = self._orig_connect_ex  # type: ignore[method-assign]
            socket.create_connection = self._orig_create  # type: ignore[assignment]
            self._patched = False
        self.enabled = False

    def probe_outbound(self, host: str = "huggingface.co", port: int = 443, timeout: float = 2.0) -> dict:
        """Try one outbound connection and describe what happened."""
        error = None
        blocked = False
        try:
            socket.create_connection((host, port), timeout=timeout)
            opened = True
        except NetworkBlockedError as exc:
            opened = False
            blocked = True
            error = str(exc)
        except OSError as exc:
            opened = False
            error = f"{type(exc).__name__}: {exc}"
        return {
            "host": host,
            "port": port,
            "opened": opened,
            "blocked_by_guard": blocked,
            "guard_enabled": self.enabled,
            "error": error,
            "blocked_attempts": list(self.blocked_attempts[-5:]),
        }


def errno_host_unreachable() -> int:
    try:
        import errno

        return int(errno.EHOSTUNREACH)
    except Exception:
        return 113


# A process-wide guard the UI and CLI can share.
GUARD = NetworkGuard()
