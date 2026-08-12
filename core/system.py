from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import tempfile
from typing import Iterable

import psutil

SAFE_USER_PROCESS_NAMES = {
    "onedrive.exe", "teams.exe", "msteams.exe", "discord.exe", "steamwebhelper.exe",
    "epicwebhelper.exe", "spotify.exe", "chrome.exe", "msedge.exe", "firefox.exe",
    "opera.exe", "brave.exe", "telegram.exe", "whatsapp.exe", "zoom.exe",
    "slack.exe", "code.exe", "notion.exe", "obs64.exe", "obs32.exe",
}

# These are optional Windows services commonly found on gaming PCs. We never touch
# Defender, Firewall, Windows Update, networking, audio, graphics, or core RPC services.
OPTIONAL_GAMING_SERVICES = {
    "MapsBroker": "Downloaded Maps Manager",
    "Fax": "Fax",
    "RetailDemo": "Retail Demo Service",
    "XblAuthManager": "Xbox Live Auth Manager",
    "XblGameSave": "Xbox Live Game Save",
    "XboxNetApiSvc": "Xbox Live Networking Service",
}


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ram_summary() -> tuple[float, float, float]:
    m = psutil.virtual_memory()
    total = m.total / (1024 ** 3)
    used = m.used / (1024 ** 3)
    return total, used, m.percent


def cpu_summary() -> tuple[int, float]:
    cores = psutil.cpu_count(logical=True) or 1
    return cores, psutil.cpu_percent(interval=0.15)


def _delete_contents(root: str) -> tuple[int, int, list[str]]:
    target = os.path.abspath(root)
    if not os.path.isdir(target):
        return 0, 0, []
    removed_files = removed_dirs = 0
    errors: list[str] = []
    for name in os.listdir(target):
        p = os.path.join(target, name)
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
                removed_dirs += 1
            else:
                os.remove(p)
                removed_files += 1
        except Exception as exc:
            errors.append(f"{p}: {exc}")
    return removed_files, removed_dirs, errors


def clean_temp_files() -> dict:
    local = os.environ.get("LOCALAPPDATA", "")
    windir = os.environ.get("WINDIR", r"C:\Windows")
    targets = [
        tempfile.gettempdir(),
        os.path.join(windir, "Temp"),
        os.path.join(local, "Temp") if local else "",
    ]
    files = dirs = 0
    errors: list[str] = []
    for target in dict.fromkeys(p for p in targets if p):
        f, d, e = _delete_contents(target)
        files += f
        dirs += d
        errors.extend(e)
    return {"files": files, "dirs": dirs, "errors": errors}


def empty_recycle_bin() -> bool:
    try:
        flags = 0x00000001 | 0x00000002 | 0x00000004
        return ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags) == 0
    except Exception:
        return False


def flush_dns() -> bool:
    try:
        return subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False


def list_background_processes(limit: int = 40) -> list[dict]:
    rows: list[dict] = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            name = (info.get("name") or "").lower()
            if name not in SAFE_USER_PROCESS_NAMES:
                continue
            mem = info.get("memory_info")
            rows.append({
                "pid": info["pid"],
                "name": info.get("name") or "Unknown",
                "cpu": float(info.get("cpu_percent") or 0.0),
                "ram_mb": round((mem.rss if mem else 0) / (1024 ** 2), 1),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    rows.sort(key=lambda r: (r["cpu"], r["ram_mb"]), reverse=True)
    return rows[:limit]


def terminate_process(pid: int) -> tuple[bool, str]:
    try:
        p = psutil.Process(pid)
        if p.name().lower() not in SAFE_USER_PROCESS_NAMES:
            return False, "Only allow-listed user applications can be closed."
        name = p.name()
        p.terminate()
        try:
            p.wait(timeout=2)
        except psutil.TimeoutExpired:
            p.kill()
        return True, f"Closed {name} (PID {pid})"
    except Exception as exc:
        return False, str(exc)


def set_high_performance_power_plan() -> tuple[bool, str]:
    try:
        result = subprocess.run(["powercfg", "/setactive", "SCHEME_MIN"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return True, "Windows High Performance power plan enabled."
        return False, result.stderr.strip() or "powercfg failed"
    except Exception as exc:
        return False, str(exc)


def set_process_high_priority(pid: int) -> tuple[bool, str]:
    try:
        p = psutil.Process(pid)
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        return True, f"High priority applied to PID {pid}."
    except Exception as exc:
        return False, str(exc)


def set_process_all_cpu_affinity(pid: int) -> tuple[bool, str]:
    try:
        p = psutil.Process(pid)
        cpus = list(range(psutil.cpu_count(logical=True) or 1))
        p.cpu_affinity(cpus)
        return True, f"CPU affinity set to all {len(cpus)} logical processors."
    except Exception as exc:
        return False, str(exc)


def run_powershell(script: str, timeout: int = 120) -> tuple[bool, str]:
    if not is_admin():
        return False, "Administrator access is required for this Windows optimization."
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (proc.stdout + "\n" + proc.stderr).strip()
        return proc.returncode == 0, output[-4000:]
    except subprocess.TimeoutExpired:
        return False, "PowerShell operation timed out."
    except Exception as exc:
        return False, str(exc)


def windows_component_cleanup() -> tuple[bool, str]:
    return run_powershell(
        "DISM.exe /Online /Cleanup-Image /StartComponentCleanup",
        timeout=600,
    )


def clear_delivery_optimization_cache() -> tuple[bool, str]:
    return run_powershell(
        "if (Get-Command Delete-DeliveryOptimizationCache -ErrorAction SilentlyContinue) { Delete-DeliveryOptimizationCache -Force; 'Delivery Optimization cache cleared.' } else { 'Delivery Optimization cmdlet is unavailable on this Windows build.' }",
        timeout=180,
    )


def optimize_system_drive() -> tuple[bool, str]:
    return run_powershell(
        "$drive = $env:SystemDrive.TrimEnd(':'); Optimize-Volume -DriveLetter $drive -ReTrim -Verbose",
        timeout=300,
    )


def powercfg_balanced_report() -> tuple[bool, str]:
    return run_powershell(
        "powercfg /energy /output \"$env:TEMP\\pnl50-energy.html\" /duration 30; 'Windows power efficiency report generated.'",
        timeout=60,
    )


def get_optional_service_states() -> dict[str, str]:
    states: dict[str, str] = {}
    for name in OPTIONAL_GAMING_SERVICES:
        try:
            states[name] = psutil.win_service_get(name).status()
        except Exception:
            states[name] = "not-found"
    return states


def stop_optional_gaming_services() -> list[tuple[bool, str]]:
    results: list[tuple[bool, str]] = []
    if not is_admin():
        return [(False, "Administrator access is required to stop optional Windows services.")]
    for name, display in OPTIONAL_GAMING_SERVICES.items():
        try:
            service = psutil.win_service_get(name)
            if service.status() == psutil.STATUS_RUNNING:
                subprocess.run(["sc.exe", "stop", name], capture_output=True, text=True, timeout=15)
                results.append((True, f"Stopped optional service: {display}"))
            else:
                results.append((True, f"Skipped {display}: already {service.status()}."))
        except Exception as exc:
            results.append((False, f"Skipped {display}: {exc}"))
    return results


def start_optional_gaming_services() -> list[tuple[bool, str]]:
    results: list[tuple[bool, str]] = []
    if not is_admin():
        return [(False, "Administrator access is required to restore optional Windows services.")]
    for name, display in OPTIONAL_GAMING_SERVICES.items():
        try:
            subprocess.run(["sc.exe", "start", name], capture_output=True, text=True, timeout=15)
            results.append((True, f"Restore requested: {display}"))
        except Exception as exc:
            results.append((False, f"Could not restore {display}: {exc}"))
    return results


def flush_prefetch_cache() -> tuple[bool, str]:
    # We intentionally do not delete the Windows Prefetch folder: Windows manages it
    # and clearing it can make launches slower rather than faster.
    return True, "Prefetch left intact; Windows manages it automatically for faster application launches."
