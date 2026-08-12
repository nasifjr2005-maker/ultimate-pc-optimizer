from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import psutil

SAFE_USER_PROCESS_NAMES = {
    "onedrive.exe", "teams.exe", "msteams.exe", "discord.exe", "steamwebhelper.exe",
    "epicwebhelper.exe", "spotify.exe", "chrome.exe", "msedge.exe", "firefox.exe",
    "opera.exe", "brave.exe", "telegram.exe", "whatsapp.exe", "zoom.exe",
    "slack.exe", "code.exe", "notion.exe", "obs64.exe", "obs32.exe",
}

OPTIONAL_GAMING_SERVICES = {
    "MapsBroker": "Downloaded Maps Manager",
    "Fax": "Fax",
    "RetailDemo": "Retail Demo Service",
    "XblAuthManager": "Xbox Live Auth Manager",
    "XblGameSave": "Xbox Live Game Save",
    "XboxNetApiSvc": "Xbox Live Networking Service",
}

SERVICE_SNAPSHOT = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "PNL50Optimizer" / "service_snapshot.json"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ram_summary() -> tuple[float, float, float]:
    m = psutil.virtual_memory()
    return m.total / (1024 ** 3), m.used / (1024 ** 3), m.percent


def cpu_summary() -> tuple[int, float]:
    return psutil.cpu_count(logical=True) or 1, psutil.cpu_percent(interval=0.15)


def disk_summary() -> tuple[float, float, float]:
    root = os.environ.get("SystemDrive", "C:") + "\\"
    usage = shutil.disk_usage(root)
    total = usage.total / (1024 ** 3)
    free = usage.free / (1024 ** 3)
    used_pct = ((usage.total - usage.free) / usage.total * 100) if usage.total else 0
    return total, free, used_pct


def _delete_contents(root: str) -> tuple[int, int, list[str]]:
    target = os.path.abspath(root)
    if not os.path.isdir(target):
        return 0, 0, []
    files = dirs = 0
    errors: list[str] = []
    for name in os.listdir(target):
        p = os.path.join(target, name)
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
                dirs += 1
            else:
                os.remove(p)
                files += 1
        except Exception as exc:
            errors.append(f"{p}: {exc}")
    return files, dirs, errors


def clean_temp_files() -> dict:
    local = os.environ.get("LOCALAPPDATA", "")
    windir = os.environ.get("WINDIR", r"C:\Windows")
    targets = [tempfile.gettempdir(), os.path.join(windir, "Temp")]
    if local:
        targets.append(os.path.join(local, "Temp"))
    files = dirs = 0
    errors: list[str] = []
    for target in dict.fromkeys(targets):
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
            rows.append({"pid": info["pid"], "name": info.get("name") or "Unknown", "cpu": float(info.get("cpu_percent") or 0), "ram_mb": round((mem.rss if mem else 0) / (1024 ** 2), 1)})
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
        result = subprocess.run(["powercfg", "/setactive", "SCHEME_MIN"], capture_output=True, text=True, timeout=15)
        return (result.returncode == 0, "Windows High Performance power plan enabled." if result.returncode == 0 else result.stderr.strip() or "powercfg failed")
    except Exception as exc:
        return False, str(exc)


def set_ultimate_performance_power_plan() -> tuple[bool, str]:
    template = "e9a42b02-d5df-448d-aa00-03f14749eb61"
    try:
        check = subprocess.run(["powercfg", "/list"], capture_output=True, text=True, timeout=15)
        if template in check.stdout.lower():
            active = subprocess.run(["powercfg", "/setactive", template], capture_output=True, text=True, timeout=15)
            if active.returncode == 0:
                return True, "Ultimate Performance power plan enabled."
        dup = subprocess.run(["powercfg", "-duplicatescheme", template], capture_output=True, text=True, timeout=20)
        if dup.returncode == 0:
            match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", dup.stdout + "\n" + dup.stderr)
            if match:
                guid = match.group(1)
                active = subprocess.run(["powercfg", "/setactive", guid], capture_output=True, text=True, timeout=15)
                if active.returncode == 0:
                    return True, "Ultimate Performance power plan created and enabled."
        return set_high_performance_power_plan()
    except Exception as exc:
        return set_high_performance_power_plan() if isinstance(exc, OSError) else (False, str(exc))


def set_process_high_priority(pid: int) -> tuple[bool, str]:
    try:
        psutil.Process(pid).nice(psutil.HIGH_PRIORITY_CLASS)
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


def run_powershell(script: str, timeout: int = 120, require_admin: bool = True) -> tuple[bool, str]:
    if require_admin and not is_admin():
        return False, "Administrator access is required for this Windows optimization."
    try:
        proc = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script], capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return proc.returncode == 0, out[-5000:]
    except subprocess.TimeoutExpired:
        return False, "PowerShell operation timed out."
    except Exception as exc:
        return False, str(exc)


def create_restore_point() -> tuple[bool, str]:
    ok, msg = run_powershell("Checkpoint-Computer -Description 'PNL50 Optimizer Pre-Optimization' -RestorePointType 'MODIFY_SETTINGS'", timeout=90)
    return ok, ("System restore point created." if ok else msg)


def enable_windows_game_mode() -> tuple[bool, str]:
    script = "New-Item -Path 'HKCU:\Software\Microsoft\GameBar' -Force | Out-Null; New-ItemProperty -Path 'HKCU:\Software\Microsoft\GameBar' -Name 'AutoGameModeEnabled' -PropertyType DWord -Value 1 -Force | Out-Null; 'Windows Game Mode enabled.'"
    return run_powershell(script, timeout=20, require_admin=False)


def normalize_network_stack() -> tuple[bool, str]:
    script = "netsh interface tcp set global autotuninglevel=normal; netsh interface tcp set global rss=enabled; 'TCP autotuning=normal, RSS=enabled.'"
    return run_powershell(script, timeout=30)


def windows_component_cleanup() -> tuple[bool, str]:
    return run_powershell("DISM.exe /Online /Cleanup-Image /StartComponentCleanup", timeout=600)


def schedule_component_cleanup_task() -> tuple[bool, str]:
    return run_powershell("schtasks.exe /Run /TN '\\Microsoft\\Windows\\Servicing\\StartComponentCleanup'; 'Windows servicing cleanup task triggered.'", timeout=60)


def clear_delivery_optimization_cache() -> tuple[bool, str]:
    return run_powershell("if (Get-Command Delete-DeliveryOptimizationCache -ErrorAction SilentlyContinue) { Delete-DeliveryOptimizationCache -Force; 'Delivery Optimization cache cleared.' } else { 'Delivery Optimization cmdlet is unavailable on this Windows build.' }", timeout=180)


def optimize_system_drive() -> tuple[bool, str]:
    return run_powershell("$drive=$env:SystemDrive.TrimEnd(':'); Optimize-Volume -DriveLetter $drive -ReTrim -Verbose", timeout=300)


def powercfg_balanced_report() -> tuple[bool, str]:
    return run_powershell("$p=Join-Path $env:TEMP 'pnl50-energy.html'; powercfg /energy /output $p /duration 30; \"Energy report: $p\"", timeout=70)


def system_health_repair() -> tuple[bool, str]:
    return run_powershell("sfc.exe /scannow; DISM.exe /Online /Cleanup-Image /RestoreHealth", timeout=1200)


def get_startup_items() -> list[dict]:
    ok, output = run_powershell("Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location,User | ConvertTo-Json -Compress", timeout=45, require_admin=False)
    if not ok:
        return []
    try:
        data = json.loads(output)
        return [data] if isinstance(data, dict) else data if isinstance(data, list) else []
    except Exception:
        return []


def get_optional_service_states() -> dict[str, str]:
    states: dict[str, str] = {}
    for name in OPTIONAL_GAMING_SERVICES:
        try:
            states[name] = psutil.win_service_get(name).status()
        except Exception:
            states[name] = "not-found"
    return states


def stop_optional_gaming_services() -> list[tuple[bool, str]]:
    if not is_admin():
        return [(False, "Administrator access is required to stop optional Windows services.")]
    snapshot: dict[str, str] = {}
    results: list[tuple[bool, str]] = []
    for name, display in OPTIONAL_GAMING_SERVICES.items():
        try:
            service = psutil.win_service_get(name)
            state = service.status()
            snapshot[name] = state
            if state == psutil.STATUS_RUNNING:
                result = subprocess.run(["sc.exe", "stop", name], capture_output=True, text=True, timeout=15)
                results.append((result.returncode == 0, f"{'Stopped' if result.returncode == 0 else 'Could not stop'}: {display}"))
            else:
                results.append((True, f"Skipped {display}: already {state}."))
        except Exception as exc:
            results.append((False, f"Skipped {display}: {exc}"))
    try:
        SERVICE_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SERVICE_SNAPSHOT.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    except Exception:
        pass
    return results


def start_optional_gaming_services() -> list[tuple[bool, str]]:
    if not is_admin():
        return [(False, "Administrator access is required to restore optional Windows services.")]
    try:
        snapshot = json.loads(SERVICE_SNAPSHOT.read_text(encoding="utf-8"))
    except Exception:
        snapshot = {}
    results: list[tuple[bool, str]] = []
    for name, display in OPTIONAL_GAMING_SERVICES.items():
        if snapshot.get(name) != psutil.STATUS_RUNNING:
            results.append((True, f"Left {display} unchanged because it was not running before optimization."))
            continue
        try:
            result = subprocess.run(["sc.exe", "start", name], capture_output=True, text=True, timeout=15)
            results.append((result.returncode == 0, f"{'Restored' if result.returncode == 0 else 'Could not restore'}: {display}"))
        except Exception as exc:
            results.append((False, f"Could not restore {display}: {exc}"))
    return results
