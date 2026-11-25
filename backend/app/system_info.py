import ctypes
import os
import platform
import subprocess
from functools import lru_cache
from typing import Any


def _detect_cpu_name() -> str:
    system = platform.system()
    if system == "Darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True,
                timeout=2,
            ).strip()
            if out:
                return out
        except Exception:
            pass
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        parts = line.split(":", 1)
                        if len(parts) == 2 and parts[1].strip():
                            return parts[1].strip()
        except Exception:
            pass

    proc = platform.processor().strip()
    if proc:
        return proc
    return platform.machine() or "Unknown CPU"


def _detect_ram_gb() -> int | None:
    system = platform.system()
    if system == "Darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                text=True,
                timeout=2,
            ).strip()
            total_bytes = int(out)
            if total_bytes > 0:
                return max(1, round(total_bytes / (1024**3)))
        except Exception:
            pass
    elif system == "Linux":
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if isinstance(pages, int) and isinstance(page_size, int) and pages > 0:
                return max(1, round((pages * page_size) / (1024**3)))
        except Exception:
            pass
    elif system == "Windows":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
                return max(1, round(stat.ullTotalPhys / (1024**3)))
        except Exception:
            pass
    return None


def _recommend_models_for_ram(ram_gb: int | None) -> list[str]:
    if ram_gb is None:
        return ["qwen3:4b", "qwen3:8b"]
    if ram_gb < 12:
        return ["qwen3:1.7b", "qwen3:4b"]
    if ram_gb < 24:
        return ["qwen3:4b", "qwen3:8b"]
    if ram_gb < 48:
        return ["qwen3:8b", "qwen3:14b"]
    return ["qwen3:14b", "qwen3:32b"]


@lru_cache(maxsize=1)
def get_system_info() -> dict[str, Any]:
    cpu = _detect_cpu_name()
    ram_gb = _detect_ram_gb()
    return {
        "cpu": cpu,
        "ram_gb": ram_gb,
        "os": platform.system(),
        "recommended_models": _recommend_models_for_ram(ram_gb),
    }
