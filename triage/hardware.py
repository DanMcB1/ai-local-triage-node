"""Describe the machine this node is running on."""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path


def _cpu_model() -> str:
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return platform.processor() or platform.machine() or "unknown CPU"
    match = re.search(r"^model name\s*:\s*(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return platform.processor() or platform.machine() or "unknown CPU"


def _ram_gib() -> float | None:
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB", text, re.MULTILINE)
    if not match:
        return None
    return int(match.group(1)) / (1024 * 1024)


def hardware_report() -> dict:
    """Return a plain description of CPU, RAM, and the lack of a GPU."""
    ram = _ram_gib()
    return {
        "cpu": _cpu_model(),
        "cpu_cores": os.cpu_count() or 1,
        "ram_gib": None if ram is None else round(ram, 1),
        "gpu": "None detected. This demo runs on CPU. In production this node would typically use one GPU.",
        "platform": f"{platform.system()} {platform.machine()}",
    }
