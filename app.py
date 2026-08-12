from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGraphicsOpacityEffect, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

from core.emulators import (
    adb_connect_5555, default_adb_port, detect_emulators,
    optimize_emulator, port_is_open,
)
from core.keyauth import KeyAuthClient
from core.system import (
    clean_temp_files, clear_delivery_optimization_cache, cpu_summary,
    create_restore_point, disk_summary, empty_recycle_bin, enable_windows_game_mode,
    flush_dns, get_optional_service_states, get_startup_items, is_admin,
    list_background_processes, normalize_network_stack, optimize_system_drive,
    powercfg_balanced_report, ram_summary, schedule_component_cleanup_task,
    set_high_performance_power_plan, set_ultimate_performance_power_plan,
    start_optional_gaming_services, stop_optional_gaming_services,
    system_health_repair, terminate_process, windows_component_cleanup,
)

APP_TITLE = "PNL50 PC OPTIMIZER PRO"
DISCORD_URL = "https://discord.com/invite/a6Q8QXFM44"
ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "panel50.svg"


class LoginPage(QFrame):
    login_ok = Signal()

    def __init__(self):
        super().__init__()
        self.auth = KeyAuthClient()
        self.setObjectName("Panel")
        root = QVBoxLayout(self)
        root.setContentsMargins(56, 42, 56, 42)
        root.setSpacing(13)

        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)).scaled(168, 168, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)

        title = QLabel(APP_TITLE)
        title.setObjectName("HeroTitle")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Advanced Windows performance control • Panel 50")
        subtitle.setObjectName("Muted")
        subtitle.setAlignment(Qt.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setClearButtonEnabled(True)
        self.username.returnPressed.connect(self.do_login)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setClearButtonEnabled(True)
        self.password.returnPressed.connect(self.do_login)

        show = QCheckBox("Show password")
        show.toggled.connect(lambda checked: self.password.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))

        self.btn = QPushButton("SIGN IN")
        self.btn.setMinimumHeight(50)
        self.btn.clicked.connect(self.do_login)

        discord = QPushButton("PANEL 50 DISCORD")
        discord.setObjectName("GhostButton")
        discord.clicked.connect(lambda: os.startfile(DISCORD_URL))

        self.status = QLabel("Preparing secure sign-in…")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)

        root.addStretch(1)
        root.addWidget(logo)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(12)
        root.addWidget(self.username)
        root.addWidget(self.password)
        root.addWidget(show)
        root.addWidget(self.btn)
        root.addWidget(discord)
        root.addWidget(self.status)
        root.addStretch(1)
        self.fade_in()
        QTimer.singleShot(150, self.init_auth)

    def fade_in(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(700)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._fade_anim = anim

    def init_auth(self):
        ok, msg = self.auth.init()
        self.status.setText(msg if ok else f"Authentication service: {msg}")
        self.btn.setEnabled(ok)
        if ok:
            self.username.setFocus()

    def do_login(self):
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self.status.setText("Enter both username and password.")
            return
        self.btn.setEnabled(False)
        self.status.setText("Verifying account…")
        ok, msg = self.auth.login(username, password)
        self.status.setText(msg)
        self.btn.setEnabled(True)
        if ok:
            self.login_ok.emit()


class Dashboard(QMainWindow):
    def __init__(self, auth: KeyAuthClient):
        super().__init__()
        self.auth = auth
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 820)
        self.setMinimumSize(1100, 740)
        self.setWindowIcon(QIcon(str(LOGO)))
        self.last_page = 0
        self.setup_ui()
        self.refresh_dashboard()
        self.refresh_processes()
        self.refresh_services()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        nav = QFrame()
        nav.setObjectName("Nav")
        nav.setFixedWidth(250)
        nv = QVBoxLayout(nav)
        nv.setContentsMargins(18, 22, 18, 18)

        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)).scaled(66, 66, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        brand = QLabel("PNL50\nOPTIMIZER PRO")
        brand.setObjectName("Brand")
        brand.setAlignment(Qt.AlignCenter)
        nv.addWidget(logo)
        nv.addWidget(brand)
        nv.addSpacing(18)

        nav_items = [
            ("Dashboard", 0),
            ("Smart Optimize", 1),
            ("PC Cleanup", 2),
            ("Gaming Mode", 3),
            ("Emulators", 4),
            ("Background Apps", 5),
            ("Windows Services", 6),
            ("Startup", 7),
            ("Maintenance", 8),
        ]
        for text, index in nav_items:
            b = QPushButton(text)
            b.setObjectName("NavButton")
            b.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            nv.addWidget(b)

        nv.addStretch(1)
        discord = QPushButton("JOIN PANEL 50 DISCORD")
        discord.clicked.connect(lambda: os.startfile(DISCORD_URL))
        nv.addWidget(discord)
        logout = QPushButton("LOG OUT")
        logout.setObjectName("GhostButton")
        logout.clicked.connect(self.logout)
        nv.addWidget(logout)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.dashboard_page())
        self.pages.addWidget(self.optimize_page())
        self.pages.addWidget(self.cleanup_page())
        self.pages.addWidget(self.gaming_page())
        self.pages.addWidget(self.emulator_page())
        self.pages.addWidget(self.process_page())
        self.pages.addWidget(self.services_page())
        self.pages.addWidget(self.startup_page())
        self.pages.addWidget(self.maintenance_page())

        main.addWidget(nav)
        main.addWidget(self.pages, 1)

    def switch_page(self, index: int):
        if index == self.last_page:
            return
        self.pages.setCurrentIndex(index)
        self.last_page = index
        page = self.pages.currentWidget()
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", page)
        anim.setDuration(240)
        anim.setStartValue(0.20)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._page_anim = anim
        self.refresh_dashboard()

    def page_base(self, title: str, desc: str):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(30, 26, 30, 26)
        lay.setSpacing(15)
        h = QLabel(title)
        h.setObjectName("PageTitle")
        d = QLabel(desc)
        d.setObjectName("Muted")
        d.setWordWrap(True)
        lay.addWidget(h)
        lay.addWidget(d)
        return w, lay

    def card(self, title: str, value: str):
        c = QFrame()
        c.setObjectName("Card")
        l = QVBoxLayout(c)
        a = QLabel(title)
        a.setObjectName("Muted")
        b = QLabel(value)
        b.setObjectName("Metric")
        l.addWidget(a)
        l.addWidget(b)
        return c

    def dashboard_page(self):
        w, lay = self.page_base("System Overview", "Live resource state, storage pressure and the fastest route to a gaming-ready Windows session.")
        row = QHBoxLayout()
        self.cpu_card = self.card("CPU", "—")
        self.ram_card = self.card("RAM", "—")
        self.disk_card = self.card("SYSTEM DISK", "—")
        self.admin_card = self.card("ACCESS", "—")
        for c in [self.cpu_card, self.ram_card, self.disk_card, self.admin_card]:
            row.addWidget(c)
        lay.addLayout(row)
        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setTextVisible(False)
        lay.addWidget(self.overall_bar)
        self.dashboard_status = QLabel("Ready to optimize.")
        self.dashboard_status.setObjectName("Status")
        lay.addWidget(self.dashboard_status)
        big = QPushButton("ONE-CLICK GAMING OPTIMIZE")
        big.setMinimumHeight(54)
        big.clicked.connect(lambda: self.switch_page(1))
        lay.addWidget(big, 0, Qt.AlignLeft)
        note = QLabel("The optimizer focuses on measurable system load and supported Windows controls. It avoids blanket registry packs, Defender shutdowns, driver replacement, and personal-file deletion.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addStretch(1)
        return w

    def _check(self, text, checked=True):
        cb = QCheckBox(text)
        cb.setChecked(checked)
        return cb

    def optimize_page(self):
        w, lay = self.page_base(
            "Smart Optimize",
            "A deeper, selectable optimization pass with a restore point, power control, Windows maintenance, network normalization and optional background-service trimming.",
        )
        grid = QGridLayout()
        self.opt_restore = self._check("Create restore point", True)
        self.opt_ultimate = self._check("Ultimate Performance power plan", True)
        self.opt_gamemode = self._check("Enable Windows Game Mode", True)
        self.opt_apps = self._check("Close listed user background apps", False)
        self.opt_temp = self._check("Clean Windows/user temp files", True)
        self.opt_do = self._check("Clear Delivery Optimization cache", True)
        self.opt_dns = self._check("Flush DNS cache", True)
        self.opt_tcp = self._check("Normalize TCP autotuning + RSS", True)
        self.opt_dism = self._check("DISM component cleanup", True)
        self.opt_task = self._check("Run Windows servicing cleanup task", False)
        self.opt_retrim = self._check("ReTrim system drive", True)
        self.opt_services = self._check("Stop optional gaming services", False)
        checks = [
            self.opt_restore, self.opt_ultimate, self.opt_gamemode, self.opt_apps,
            self.opt_temp, self.opt_do, self.opt_dns, self.opt_tcp,
            self.opt_dism, self.opt_task, self.opt_retrim, self.opt_services,
        ]
        for i, cb in enumerate(checks):
            grid.addWidget(cb, i // 2, i % 2)
        lay.addLayout(grid)
        self.optimize_progress = QProgressBar()
        self.optimize_progress.setRange(0, 100)
        self.optimize_progress.setTextVisible(False)
        lay.addWidget(self.optimize_progress)
        self.optimize_log = QTextEdit()
        self.optimize_log.setReadOnly(True)
        lay.addWidget(self.optimize_log, 1)
        run = QPushButton("RUN DEEP OPTIMIZATION")
        run.setMinimumHeight(50)
        run.clicked.connect(self.run_deep_optimization)
        lay.addWidget(run, 0, Qt.AlignLeft)
        return w

    def cleanup_page(self):
        w, lay = self.page_base("PC Cleanup", "Clean transient data and Windows caches without touching personal documents, Downloads or browser profiles.")
        self.cleanup_status = QLabel("Ready")
        self.cleanup_status.setObjectName("Status")
        lay.addWidget(self.cleanup_status)
        grid = QGridLayout()
        buttons = [
            ("CLEAN TEMP FILES", self.do_cleanup),
            ("FLUSH DNS", self.do_dns),
            ("CLEAR DO CACHE", self.do_do_cache),
            ("EMPTY RECYCLE BIN", self.do_recycle),
        ]
        for i, (text, fn) in enumerate(buttons):
            b = QPushButton(text)
            b.clicked.connect(fn)
            grid.addWidget(b, i // 2, i % 2)
        lay.addLayout(grid)
        lay.addStretch(1)
        return w

    def gaming_page(self):
        w, lay = self.page_base("Gaming Mode", "Switch between performance-focused Windows power modes and enable Windows Game Mode without touching security controls.")
        self.power_check = self._check("Use Ultimate Performance when available", True)
        self.game_check = self._check("Enable Windows Game Mode", True)
        lay.addWidget(self.power_check)
        lay.addWidget(self.game_check)
        row = QHBoxLayout()
        apply_btn = QPushButton("APPLY GAMING MODE")
        apply_btn.clicked.connect(self.apply_gaming)
        high_btn = QPushButton("HIGH PERFORMANCE ONLY")
        high_btn.clicked.connect(self.apply_high)
        row.addWidget(apply_btn)
        row.addWidget(high_btn)
        lay.addLayout(row)
        report = QPushButton("ANALYZE POWER EFFICIENCY")
        report.clicked.connect(self.run_power_report)
        lay.addWidget(report, 0, Qt.AlignLeft)
        info = QLabel("Windows documents Game Mode as a gaming optimization mechanism. Actual FPS gains vary by CPU/GPU load, driver state, thermals, and the game itself.")
        info.setObjectName("Muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addStretch(1)
        return w

    def emulator_page(self):
        w, lay = self.page_base("Emulator Optimizer", "Detect BlueStacks / MSI App Player (HD-Player.exe), apply reversible process-level tuning, and use local ADB port 5555.")
        self.emu_list = QListWidget()
        lay.addWidget(self.emu_list, 1)
        row = QHBoxLayout()
        for text, fn in [("SCAN EMULATORS", self.refresh_emulators), ("OPTIMIZE SELECTED", self.optimize_selected_emulator), ("ADB CONNECT :5555", self.do_adb)]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        self.adb_status = QLabel(f"ADB target: 127.0.0.1:{default_adb_port()} • Checking…")
        self.adb_status.setObjectName("Status")
        lay.addWidget(self.adb_status)
        self.refresh_emulators()
        return w

    def process_page(self):
        w, lay = self.page_base("Background Apps", "Only an allow-listed set of common user applications is shown. Windows/system processes are excluded.")
        self.proc_list = QListWidget()
        lay.addWidget(self.proc_list, 1)
        row = QHBoxLayout()
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self.refresh_processes)
        close = QPushButton("CLOSE SELECTED")
        close.clicked.connect(self.close_selected_processes)
        close_all = QPushButton("CLOSE ALL LISTED")
        close_all.clicked.connect(self.close_all_listed)
        for b in (refresh, close, close_all):
            row.addWidget(b)
        lay.addLayout(row)
        return w

    def services_page(self):
        w, lay = self.page_base("Windows Services", "Optional services are tightly allow-listed. PNL50 never includes Defender, Firewall, Windows Update, audio, graphics, networking, RPC or other core services.")
        self.service_list = QListWidget()
        lay.addWidget(self.service_list, 1)
        row = QHBoxLayout()
        stop = QPushButton("STOP OPTIONAL SERVICES")
        stop.clicked.connect(self.stop_services)
        restore = QPushButton("RESTORE PREVIOUS STATE")
        restore.clicked.connect(self.restore_services)
        row.addWidget(stop)
        row.addWidget(restore)
        lay.addLayout(row)
        self.refresh_services()
        return w

    def startup_page(self):
        w, lay = self.page_base("Startup Analyzer", "See startup entries and commands so you can decide what should remain enabled. PNL50 does not silently disable startup programs.")
        self.startup_list = QListWidget()
        lay.addWidget(self.startup_list, 1)
        refresh = QPushButton("SCAN STARTUP ITEMS")
        refresh.clicked.connect(self.refresh_startup)
        lay.addWidget(refresh, 0, Qt.AlignLeft)
        self.refresh_startup()
        return w

    def maintenance_page(self):
        w, lay = self.page_base("Windows Maintenance", "Tools for health, servicing and network maintenance. These are separate from the fast gaming profile because some operations can take several minutes.")
        grid = QGridLayout()
        buttons = [
            ("CREATE RESTORE POINT", self.do_restore),
            ("SYSTEM HEALTH REPAIR", self.do_health_repair),
            ("DISM COMPONENT CLEANUP", self.do_dism),
            ("RUN SERVICING CLEANUP TASK", self.do_cleanup_task),
            ("NORMALIZE TCP + RSS", self.do_tcp),
            ("RETRIM SYSTEM DRIVE", self.do_retrim),
            ("POWER EFFICIENCY REPORT", self.run_power_report),
        ]
        for i, (text, fn) in enumerate(buttons):
            b = QPushButton(text)
            b.clicked.connect(fn)
            grid.addWidget(b, i // 2, i % 2)
        lay.addLayout(grid)
        self.maintenance_log = QTextEdit()
        self.maintenance_log.setReadOnly(True)
        lay.addWidget(self.maintenance_log, 1)
        return w

    def refresh_dashboard(self):
        cores, cpu = cpu_summary()
        total, used, ram_pct = ram_summary()
        dtotal, dfree, dused = disk_summary()
        self.cpu_card.findChildren(QLabel)[1].setText(f"{cpu:.0f}% • {cores} threads")
        self.ram_card.findChildren(QLabel)[1].setText(f"{used:.1f} / {total:.1f} GB")
        self.disk_card.findChildren(QLabel)[1].setText(f"{dfree:.1f} GB free • {dused:.0f}% used")
        self.admin_card.findChildren(QLabel)[1].setText("Administrator" if is_admin() else "Standard")
        self.overall_bar.setValue(min(100, int((cpu + ram_pct + dused) / 3)))

    def _append(self, text: str):
        self.optimize_log.append(text)
        QApplication.processEvents()

    def _run_step(self, index, total, label, fn):
        self._append(f"▶ {label}")
        ok, msg = fn()
        self._append(("  ✓ " if ok else "  ! ") + (msg or "Completed."))
        self.optimize_progress.setValue(int(index * 100 / max(total, 1)))
        return ok

    def run_deep_optimization(self):
        if not is_admin() and any(cb.isChecked() for cb in [self.opt_restore, self.opt_ultimate, self.opt_temp, self.opt_do, self.opt_dns, self.opt_tcp, self.opt_dism, self.opt_task, self.opt_retrim, self.opt_services]):
            QMessageBox.information(self, APP_TITLE, "Run PNL50 PC OPTIMIZER PRO as Administrator for the full optimization profile.")
            return
        if self.opt_restore:
            pass
        steps = []
        if self.opt_restore.isChecked():
            steps.append(("Create restore point", create_restore_point))
        if self.opt_ultimate.isChecked():
            steps.append(("Enable Ultimate Performance power plan", set_ultimate_performance_power_plan))
        if self.opt_gamemode.isChecked():
            steps.append(("Enable Windows Game Mode", enable_windows_game_mode))
        if self.opt_apps.isChecked():
            steps.append(("Close allow-listed user background apps", self._close_all_result))
        if self.opt_temp.isChecked():
            steps.append(("Clean Windows and user temporary files", self._cleanup_result))
        if self.opt_do.isChecked():
            steps.append(("Clear Delivery Optimization cache", clear_delivery_optimization_cache))
        if self.opt_dns.isChecked():
            steps.append(("Flush DNS cache", lambda: (flush_dns(), "DNS cache flushed.")))
        if self.opt_tcp.isChecked():
            steps.append(("Normalize TCP autotuning and RSS", normalize_network_stack))
        if self.opt_dism.isChecked():
            steps.append(("Clean superseded Windows components", windows_component_cleanup))
        if self.opt_task.isChecked():
            steps.append(("Run Windows servicing cleanup task", schedule_component_cleanup_task))
        if self.opt_retrim.isChecked():
            steps.append(("ReTrim system drive", optimize_system_drive))
        if self.opt_services.isChecked():
            steps.append(("Stop optional gaming services", self._service_result_wrapper))

        self.optimize_progress.setValue(0)
        self.optimize_log.clear()
        if not steps:
            self._append("Select at least one optimization.")
            return
        self._append(f"PNL50 deep optimization started • {len(steps)} operations")
        success = 0
        for i, (label, fn) in enumerate(steps, 1):
            if self._run_step(i, len(steps), label, fn):
                success += 1
            self._append("")
        self._append(f"Completed: {success}/{len(steps)} operations.")
        self.dashboard_status.setText("Deep optimization completed.")
        self.refresh_dashboard()

    def _cleanup_result(self):
        r = clean_temp_files()
        return True, f"Removed {r['files']} files and {r['dirs']} directories; locked items skipped."

    def _close_all_result(self):
        msgs = []
        for p in list_background_processes(limit=40):
            ok, msg = terminate_process(p["pid"])
            if ok:
                msgs.append(msg)
        return True, f"Closed {len(msgs)} allow-listed user applications."

    @staticmethod
    def _service_result_wrapper():
        items = stop_optional_gaming_services()
        ok = all(x[0] for x in items)
        return ok, "\n".join(("✓ " if s else "! ") + t for s, t in items)

    def _service_result(self, items):
        return all(x[0] for x in items), "\n".join(("✓ " if s else "! ") + t for s, t in items)

    def run_power_report(self):
        ok, msg = powercfg_balanced_report()
        box = QMessageBox(self)
        box.setWindowTitle(APP_TITLE)
        box.setText(msg if ok else f"Power analysis failed:\n{msg}")
        box.exec()

    def apply_gaming(self):
        msgs = []
        if self.power_check.isChecked():
            ok, msg = set_ultimate_performance_power_plan()
            msgs.append(("✓ " if ok else "! ") + msg)
        if self.game_check.isChecked():
            ok, msg = enable_windows_game_mode()
            msgs.append(("✓ " if ok else "! ") + msg)
        QMessageBox.information(self, APP_TITLE, "\n".join(msgs) if msgs else "No gaming mode options selected.")

    def apply_high(self):
        ok, msg = set_high_performance_power_plan()
        QMessageBox.information(self, APP_TITLE, msg)

    def do_cleanup(self):
        r = clean_temp_files()
        self.cleanup_status.setText(f"Removed {r['files']} files and {r['dirs']} folders. Locked items were skipped.")
        self.refresh_dashboard()

    def do_dns(self):
        self.cleanup_status.setText("DNS cache flushed." if flush_dns() else "DNS flush failed.")

    def do_do_cache(self):
        ok, msg = clear_delivery_optimization_cache()
        self.cleanup_status.setText(msg if ok else f"Delivery Optimization: {msg}")

    def do_recycle(self):
        self.cleanup_status.setText("Recycle Bin emptied." if empty_recycle_bin() else "Recycle Bin action failed.")

    def refresh_emulators(self):
        self.emu_list.clear()
        found = detect_emulators()
        if not found:
            self.emu_list.addItem("No supported emulator installation detected.")
        else:
            for item in found:
                row = QListWidgetItem(f"{item['name']}  |  {'RUNNING' if item['running'] else 'INSTALLED'}\n{item['path']}")
                row.setData(Qt.UserRole, item)
                self.emu_list.addItem(row)
        self.adb_status.setText(f"ADB target: 127.0.0.1:{default_adb_port()} • {'OPEN' if port_is_open() else 'NOT LISTENING'}")

    def optimize_selected_emulator(self):
        item = self.emu_list.currentItem()
        if not item or not item.data(Qt.UserRole):
            return
        info = item.data(Qt.UserRole)
        if not info.get("running") or not info.get("pid"):
            QMessageBox.information(self, APP_TITLE, "Start the emulator first, then run the optimization.")
            return
        messages = optimize_emulator(int(info["pid"]))
        QMessageBox.information(self, APP_TITLE, "\n".join(("OK" if ok else "SKIP") + ": " + msg for ok, msg in messages))

    def do_adb(self):
        ok, msg = adb_connect_5555()
        self.adb_status.setText(("ADB: " if ok else "ADB failed: ") + msg)

    def refresh_processes(self):
        self.proc_list.clear()
        for p in list_background_processes():
            item = QListWidgetItem(f"{p['name']}  •  PID {p['pid']}  •  CPU {p['cpu']:.1f}%  •  RAM {p['ram_mb']:.0f} MB")
            item.setData(Qt.UserRole, p["pid"])
            item.setCheckState(Qt.Unchecked)
            self.proc_list.addItem(item)

    def close_selected_processes(self):
        msgs = []
        for i in range(self.proc_list.count()):
            item = self.proc_list.item(i)
            if item.checkState() == Qt.Checked:
                _, msg = terminate_process(int(item.data(Qt.UserRole)))
                msgs.append(msg)
        self.refresh_processes()
        QMessageBox.information(self, APP_TITLE, "\n".join(msgs) if msgs else "No apps selected.")

    def close_all_listed(self):
        for p in list_background_processes():
            terminate_process(p["pid"])
        self.refresh_processes()

    def refresh_services(self):
        if not hasattr(self, "service_list"):
            return
        self.service_list.clear()
        for name, state in get_optional_service_states().items():
            self.service_list.addItem(QListWidgetItem(f"{name}  •  {state}"))

    def stop_services(self):
        ok, msg = self._service_result(stop_optional_gaming_services())
        self.refresh_services()
        QMessageBox.information(self, APP_TITLE, msg)

    def restore_services(self):
        ok, msg = self._service_result(start_optional_gaming_services())
        self.refresh_services()
        QMessageBox.information(self, APP_TITLE, msg)

    def refresh_startup(self):
        self.startup_list.clear()
        items = get_startup_items()
        if not items:
            self.startup_list.addItem("No startup entries found or Windows denied the query.")
            return
        for row in items:
            name = row.get("Name", "Unknown")
            user = row.get("User", "")
            location = row.get("Location", "")
            command = row.get("Command", "")
            self.startup_list.addItem(QListWidgetItem(f"{name}  •  {user}\n{location}\n{command}"))

    def _log_maintenance(self, label, fn):
        self.maintenance_log.append(f"▶ {label}")
        ok, msg = fn()
        self.maintenance_log.append(("✓ " if ok else "! ") + (msg or "Completed."))
        self.maintenance_log.append("")
        QApplication.processEvents()
        return ok

    def do_restore(self):
        self._log_maintenance("Create restore point", create_restore_point)

    def do_health_repair(self):
        self._log_maintenance("Run SFC + DISM RestoreHealth", system_health_repair)

    def do_dism(self):
        self._log_maintenance("Run DISM component cleanup", windows_component_cleanup)

    def do_cleanup_task(self):
        self._log_maintenance("Run Windows servicing cleanup task", schedule_component_cleanup_task)

    def do_tcp(self):
        self._log_maintenance("Normalize TCP autotuning + RSS", normalize_network_stack)

    def do_retrim(self):
        self._log_maintenance("ReTrim system drive", optimize_system_drive)

    def logout(self):
        self.auth.logout()
        self.close()


def show_main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { background: #08090d; color: #f4f4f5; font-family: Segoe UI; font-size: 14px; }
        #Nav { background: #0c0d12; border-right: 1px solid #1c1e26; }
        #Card, #Panel { background: #101218; border: 1px solid #242732; border-radius: 18px; }
        #Brand { font-size: 19px; font-weight: 800; letter-spacing: 2px; padding: 5px; }
        #HeroTitle { font-size: 27px; font-weight: 800; }
        #PageTitle { font-size: 28px; font-weight: 800; }
        #Metric { font-size: 23px; font-weight: 700; }
        #Muted { color: #858a99; }
        #Status { color: #d6d9e0; padding: 9px 0; }
        QLineEdit { background: #0d0f14; border: 1px solid #2a2d37; border-radius: 12px; padding: 14px; }
        QLineEdit:focus { border: 1px solid #aeb3c0; }
        QPushButton { background: #f4f4f5; color: #0b0c0f; border: 0; border-radius: 11px; padding: 11px 15px; font-weight: 700; }
        QPushButton:hover { background: #ffffff; }
        QPushButton:disabled { background: #343842; color: #888; }
        #NavButton { background: transparent; color: #babec8; text-align: left; padding: 12px; font-weight: 600; }
        #NavButton:hover { background: #16181f; color: #ffffff; }
        #GhostButton { background: transparent; color: #c4c8d2; border: 1px solid #2c303b; }
        #GhostButton:hover { background: #151820; color: #ffffff; }
        QListWidget { background: #0d0f14; border: 1px solid #242732; border-radius: 13px; padding: 8px; }
        QListWidget::item { padding: 10px; margin: 2px; border-radius: 8px; }
        QListWidget::item:selected { background: #242732; }
        QTextEdit { background: #0d0f14; border: 1px solid #242732; border-radius: 13px; padding: 10px; }
        QCheckBox { spacing: 8px; padding: 7px 3px; }
        QProgressBar { height: 7px; border: 0; background: #161820; border-radius: 4px; }
        QProgressBar::chunk { background: #dfe1e7; border-radius: 4px; }
    """)

    login = LoginPage()
    login.setWindowTitle(APP_TITLE)
    login.resize(580, 710)
    login.setMinimumSize(540, 650)
    login.show()

    def launch():
        login.close()
        window = Dashboard(login.auth)
        window.show()
        app._pnl50_window = window

    login.login_ok.connect(launch)
    return app.exec()


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("Windows only")
    sys.exit(show_main())
