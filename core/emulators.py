from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

import psutil

DEFAULT_ADB_PORT = 5555


def _candidate_paths() -> list[tuple[str, Path]]:
    roots = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        Path(os.environ.get("ProgramW6432", r"C:\Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    ]
    result: list[tuple[str, Path]] = []
    folders = [
        ("BlueStacks 5", "BlueStacks_nxt"),
        ("BlueStacks", "BlueStacks"),
        ("MSI App Player", "BlueStacks_msi5"),
        ("MSI App Player", "MSI App Player"),
    ]
    for root in roots:
        for label, folder in folders:
            p = root / folder / "HD-Player.exe"
            if p.exists() and (label, p) not in result:
                result.append((label, p))
    return result


def detect_emulators() -> list[dict]:
    found: list[dict] = [
        {"name": label, "path": str(path), "running": False, "pid": None}
        for label, path in _candidate_paths()
    ]
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if (proc.info.get("name") or "").lower() != "hd-player.exe":
                continue
            exe = proc.info.get("exe")
            if not exe:
                continue
            exe_path = Path(exe).resolve()
            for item in found:
                if exe_path == Path(item["path"]).resolve():
                    item["running"] = True
                    item["pid"] = proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
    return found


def default_adb_port() -> int:
    return DEFAULT_ADB_PORT


def port_is_open(host: str = "127.0.0.1", port: int = DEFAULT_ADB_PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def find_adb() -> str | None:
    candidates = [
        Path(r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"),
        Path(r"C:\Program Files\BlueStacks_msi5\HD-Adb.exe"),
        Path(r"C:\Program Files\BlueStacks_nxt\adb.exe"),
        Path(r"C:\Program Files\BlueStacks_msi5\adb.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if (proc.info.get("name") or "").lower() in {"adb.exe", "hd-adb.exe"}:
                return proc.info.get("exe")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def adb_connect_5555() -> tuple[bool, str]:
    adb = find_adb()
    if not adb:
        return False, "ADB executable not found. Start BlueStacks/MSI App Player first."
    try:
        proc = subprocess.run(
            [adb, "connect", f"127.0.0.1:{DEFAULT_ADB_PORT}"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        out = (proc.stdout + " " + proc.stderr).strip()
        return proc.returncode == 0, out or "ADB connect finished."
    except Exception as exc:
        return False, str(exc)


def optimize_emulator(pid: int) -> list[tuple[bool, str]]:
    from .system import set_process_all_cpu_affinity, set_process_high_priority
    # These are process-level, reversible changes only. Emulator configuration files,
    # VM images, system services, and Windows security settings are never overwritten.
    return [set_process_high_priority(pid), set_process_all_cpu_affinity(pid)]
