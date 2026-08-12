from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

from core.emulators import (
    adb_connect_5555,
    default_adb_port,
    detect_emulators,
    optimize_emulator,
    port_is_open,
)
from core.keyauth import KeyAuthClient
from core.system import (
    clean_temp_files,
    clear_delivery_optimization_cache,
    cpu_summary,
    empty_recycle_bin,
    flush_dns,
    flush_prefetch_cache,
    get_optional_service_states,
    is_admin,
    list_background_processes,
    optimize_system_drive,
    powercfg_balanced_report,
    ram_summary,
    run_powershell,
    set_high_performance_power_plan,
    start_optional_gaming_services,
    stop_optional_gaming_services,
    terminate_process,
    windows_component_cleanup,
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
        root.setContentsMargins(54, 42, 54, 42)
        root.setSpacing(13)

        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)

        title = QLabel("PNL50 PC OPTIMIZER PRO")
        title.setObjectName("HeroTitle")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Fast. Clean. Focused on gaming performance.")
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
        self.btn.setMinimumHeight(48)
        self.btn.clicked.connect(self.do_login)

        self.status = QLabel("Preparing secure sign-in…")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)

        help_text = QLabel("Your login is verified through KeyAuth. PNL50 never needs your license key in the app.")
        help_text.setWordWrap(True)
        help_text.setAlignment(Qt.AlignCenter)
        help_text.setObjectName("Muted")

        root.addStretch(1)
        root.addWidget(logo)
        root.addSpacing(3)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(14)
        root.addWidget(self.username)
        root.addWidget(self.password)
        root.addWidget(show)
        root.addWidget(self.btn)
        root.addWidget(self.status)
        root.addWidget(help_text)
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
        self.resize(1240, 800)
        self.setMinimumSize(1080, 720)
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
            ("Optimize PC", 1),
            ("PC Cleanup", 2),
            ("Gaming Mode", 3),
            ("Emulators", 4),
            ("Background Apps", 5),
            ("Windows Services", 6),
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

    def card(self):
        c = QFrame()
        c.setObjectName("Card")
        return c

    def metric_card(self, label, value):
        c = self.card()
        l = QVBoxLayout(c)
        a = QLabel(label)
        a.setObjectName("Muted")
        b = QLabel(value)
        b.setObjectName("Metric")
        l.addWidget(a)
        l.addWidget(b)
        return c

    def dashboard_page(self):
        w, lay = self.page_base("System Overview", "Live system state and the fastest route to a cleaner gaming-ready Windows session.")
        row = QHBoxLayout()
        self.cpu_card = self.metric_card("CPU", "—")
        self.ram_card = self.metric_card("RAM", "—")
        self.admin_card = self.metric_card("Access", "—")
        row.addWidget(self.cpu_card)
        row.addWidget(self.ram_card)
        row.addWidget(self.admin_card)
        lay.addLayout(row)

        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setTextVisible(False)
        lay.addWidget(self.overall_bar)

        self.dashboard_status = QLabel("Ready to optimize.")
        self.dashboard_status.setObjectName("Status")
        lay.addWidget(self.dashboard_status)

        optimize = QPushButton("OPTIMIZE PC NOW")
        optimize.setMinimumHeight(52)
        optimize.clicked.connect(lambda: self.switch_page(1))
        lay.addWidget(optimize, 0, Qt.AlignLeft)

        tips = QLabel(
            "PNL50 uses reversible, Windows-supported optimizations. It does not disable Defender, Firewall, Windows Update, graphics/audio/network services, or delete personal files."
        )
        tips.setObjectName("Muted")
        tips.setWordWrap(True)
        lay.addWidget(tips)
        lay.addStretch(1)
        return w

    def optimize_page(self):
        w, lay = self.page_base(
            "Smart PC Optimization",
            "Run a guided optimization pass. Optional Windows services are limited to non-critical gaming-unneeded components; system security and core Windows services are preserved.",
        )
        checks = QHBoxLayout()
        self.opt_power = QCheckBox("High Performance power plan")
        self.opt_temp = QCheckBox("Clean temporary files")
        self.opt_dns = QCheckBox("Flush DNS")
        self.opt_do = QCheckBox("Clear Delivery Optimization cache")
        self.opt_dism = QCheckBox("DISM component cleanup")
        self.opt_drive = QCheckBox("ReTrim system drive")
        self.opt_services = QCheckBox("Stop optional gaming services temporarily")
        for cb in [self.opt_power, self.opt_temp, self.opt_dns, self.opt_do, self.opt_dism, self.opt_drive, self.opt_services]:
            cb.setChecked(True)
            checks.addWidget(cb)
        lay.addLayout(checks)

        self.optimize_progress = QProgressBar()
        self.optimize_progress.setRange(0, 100)
        self.optimize_progress.setTextVisible(False)
        lay.addWidget(self.optimize_progress)

        self.optimize_log = QTextEdit()
        self.optimize_log.setReadOnly(True)
        self.optimize_log.setMinimumHeight(270)
        lay.addWidget(self.optimize_log)

        row = QHBoxLayout()
        run = QPushButton("RUN SMART OPTIMIZATION")
        run.setMinimumHeight(48)
        run.clicked.connect(self.run_smart_optimization)
        row.addWidget(run)
        report = QPushButton("POWER REPORT")
        report.clicked.connect(self.run_power_report)
        row.addWidget(report)
        lay.addLayout(row)
        return w

    def cleanup_page(self):
        w, lay = self.page_base("PC Cleanup", "Clear safe temporary data and caches while leaving documents, Downloads, browser profiles, and Windows Prefetch intact.")
        self.cleanup_status = QLabel("Ready")
        self.cleanup_status.setObjectName("Status")
        lay.addWidget(self.cleanup_status)
        row = QHBoxLayout()
        for text, fn in [
            ("CLEAN TEMP FILES", self.do_cleanup),
            ("FLUSH DNS", self.do_dns),
            ("CLEAR DO CACHE", self.do_do_cache),
            ("EMPTY RECYCLE BIN", self.do_recycle),
        ]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        lay.addStretch(1)
        return w

    def gaming_page(self):
        w, lay = self.page_base("Gaming Mode", "Prepare Windows for gaming without opaque registry packs or risky system-service shutdowns.")
        self.power_check = QCheckBox("Windows High Performance power plan")
        self.power_check.setChecked(True)
        lay.addWidget(self.power_check)
        btn = QPushButton("APPLY GAMING MODE")
        btn.clicked.connect(self.apply_gaming)
        lay.addWidget(btn, 0, Qt.AlignLeft)
        scan = QPushButton("ANALYZE POWER EFFICIENCY")
        scan.clicked.connect(self.run_power_report)
        lay.addWidget(scan, 0, Qt.AlignLeft)
        info = QLabel("For maximum FPS, PNL50 prioritizes reducing background load, cleaning temporary data, preparing the power profile, and optimizing the emulator process rather than making unsupported registry claims.")
        info.setObjectName("Muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addStretch(1)
        return w

    def emulator_page(self):
        w, lay = self.page_base("Emulator Optimizer", "Detect BlueStacks / MSI App Player (HD-Player.exe), apply reversible process-level tuning, and use local ADB port 5555.")
        self.emu_list = QListWidget()
        lay.addWidget(self.emu_list)
        row = QHBoxLayout()
        for text, fn in [
            ("SCAN EMULATORS", self.refresh_emulators),
            ("OPTIMIZE SELECTED", self.optimize_selected_emulator),
            ("ADB CONNECT :5555", self.do_adb),
        ]:
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
        w, lay = self.page_base("Background Apps", "Close selected user applications that are consuming CPU/RAM before a gaming session. Critical Windows processes are excluded.")
        self.proc_list = QListWidget()
        lay.addWidget(self.proc_list)
        row = QHBoxLayout()
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self.refresh_processes)
        close = QPushButton("CLOSE SELECTED")
        close.clicked.connect(self.close_selected_processes)
        close_all = QPushButton("CLOSE ALL LISTED")
        close_all.clicked.connect(self.close_all_listed)
        row.addWidget(refresh)
        row.addWidget(close)
        row.addWidget(close_all)
        lay.addLayout(row)
        return w

    def services_page(self):
        w, lay = self.page_base("Windows Services", "Review a tightly allow-listed set of optional services. Nothing related to Windows security, networking, audio, graphics, or Windows Update is included.")
        self.service_list = QListWidget()
        lay.addWidget(self.service_list)
        row = QHBoxLayout()
        stop = QPushButton("STOP OPTIONAL GAMING SERVICES")
        stop.clicked.connect(self.stop_services)
        restore = QPushButton("RESTORE SERVICES")
        restore.clicked.connect(self.restore_services)
        row.addWidget(stop)
        row.addWidget(restore)
        lay.addLayout(row)
        self.refresh_services()
        return w

    def refresh_dashboard(self):
        cores, cpu = cpu_summary()
        total, used, ram_pct = ram_summary()
        self.cpu_card.findChildren(QLabel)[1].setText(f"{cpu:.0f}% • {cores} threads")
        self.ram_card.findChildren(QLabel)[1].setText(f"{used:.1f} / {total:.1f} GB")
        self.admin_card.findChildren(QLabel)[1].setText("Administrator" if is_admin() else "Standard")
        self.overall_bar.setValue(int((cpu + ram_pct) / 2))

    def run_smart_optimization(self):
        steps = []
        if self.opt_power.isChecked():
            steps.append(("High performance power plan", lambda: set_high_performance_power_plan()))
        if self.opt_temp.isChecked():
            steps.append(("Temporary files", lambda: self._cleanup_result()))
        if self.opt_dns.isChecked():
            steps.append(("DNS cache", lambda: (flush_dns(), "DNS cache flushed.")))
        if self.opt_do.isChecked():
            steps.append(("Delivery Optimization cache", clear_delivery_optimization_cache))
        if self.opt_dism.isChecked():
            steps.append(("DISM component cleanup", windows_component_cleanup))
        if self.opt_drive.isChecked():
            steps.append(("System drive ReTrim", optimize_system_drive))
        if self.opt_services.isChecked():
            steps.append(("Optional gaming services", lambda: self._service_result(stop_optional_gaming_services())))

        if not steps:
            self.optimize_log.setPlainText("Select at least one optimization.")
            return

        if any(fn in {windows_component_cleanup, optimize_system_drive, clear_delivery_optimization_cache} for _, fn in steps) and not is_admin():
            self.optimize_log.setPlainText("Run PNL50 as Administrator to use the full Windows optimization pass.")
            return

        self.optimize_progress.setValue(0)
        self.optimize_log.clear()
        for index, (label, fn) in enumerate(steps, 1):
            self.optimize_log.append(f"▶ {label}")
            ok, msg = fn()
            self.optimize_log.append(("  ✓ " if ok else "  ! ") + (msg or "Completed."))
            self.optimize_log.append("")
            self.optimize_progress.setValue(int(index * 100 / len(steps)))
            QApplication.processEvents()
        self.dashboard_status.setText("Optimization pass completed.")
        self.refresh_dashboard()

    def _cleanup_result(self):
        r = clean_temp_files()
        return True, f"Removed {r['files']} files and {r['dirs']} directories; locked items skipped."

    @staticmethod
    def _service_result(items):
        ok = all(x[0] for x in items)
        msg = "\n".join(("✓ " if state else "! ") + text for state, text in items)
        return ok, msg

    def run_power_report(self):
        ok, msg = powercfg_balanced_report()
        QMessageBox.information(self, APP_TITLE, msg if ok else f"Power analysis failed:\n{msg}")

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

    def apply_gaming(self):
        if not self.power_check.isChecked():
            QMessageBox.information(self, APP_TITLE, "Enable the High Performance option first.")
            return
        ok, msg = set_high_performance_power_plan()
        QMessageBox.information(self, APP_TITLE, msg if ok else f"Could not apply setting:\n{msg}")

    def refresh_emulators(self):
        self.emu_list.clear()
        found = detect_emulators()
        if not found:
            self.emu_list.addItem("No supported emulator installation detected.")
        else:
            for item in found:
                row = QListWidgetItem(
                    f"{item['name']}  |  {'RUNNING' if item['running'] else 'INSTALLED'}\n{item['path']}"
                )
                row.setData(Qt.UserRole, item)
                self.emu_list.addItem(row)
        self.adb_status.setText(
            f"ADB target: 127.0.0.1:{default_adb_port()} • {'OPEN' if port_is_open() else 'NOT LISTENING'}"
        )

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
            item = QListWidgetItem(
                f"{p['name']}  •  PID {p['pid']}  •  CPU {p['cpu']:.1f}%  •  RAM {p['ram_mb']:.0f} MB"
            )
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
        msgs = []
        for i in range(self.proc_list.count()):
            item = self.proc_list.item(i)
            _, msg = terminate_process(int(item.data(Qt.UserRole)))
            msgs.append(msg)
        self.refresh_processes()
        QMessageBox.information(self, APP_TITLE, "\n".join(msgs) if msgs else "No background apps listed.")

    def refresh_services(self):
        if not hasattr(self, "service_list"):
            return
        self.service_list.clear()
        for name, state in get_optional_service_states().items():
            item = QListWidgetItem(f"{name}  •  {state}")
            self.service_list.addItem(item)

    def stop_services(self):
        ok, msg = self._service_result(stop_optional_gaming_services())
        self.refresh_services()
        QMessageBox.information(self, APP_TITLE, msg)

    def restore_services(self):
        ok, msg = self._service_result(start_optional_gaming_services())
        self.refresh_services()
        QMessageBox.information(self, APP_TITLE, msg)

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
        #Metric { font-size: 25px; font-weight: 700; }
        #Muted { color: #858a99; }
        #Status { color: #d6d9e0; padding: 10px 0; }
        QLineEdit { background: #0d0f14; border: 1px solid #2a2d37; border-radius: 12px; padding: 14px; }
        QLineEdit:focus { border: 1px solid #aeb3c0; }
        QPushButton { background: #f4f4f5; color: #0b0c0f; border: 0; border-radius: 11px; padding: 11px 15px; font-weight: 700; }
        QPushButton:hover { background: #ffffff; }
        QPushButton:disabled { background: #343842; color: #888; }
        #NavButton { background: transparent; color: #babec8; text-align: left; padding: 13px; font-weight: 600; }
        #NavButton:hover { background: #16181f; color: #ffffff; }
        #GhostButton { background: #17191f; color: #d7d9e0; }
        QListWidget { background: #0d0f14; border: 1px solid #242732; border-radius: 13px; padding: 8px; }
        QListWidget::item { padding: 11px; margin: 2px; border-radius: 8px; }
        QListWidget::item:selected { background: #242732; }
        QTextEdit { background: #0d0f14; border: 1px solid #242732; border-radius: 13px; padding: 10px; }
        QCheckBox { spacing: 8px; padding: 7px 0; }
        QProgressBar { height: 8px; border: 0; background: #161820; border-radius: 4px; }
        QProgressBar::chunk { background: #dfe1e7; border-radius: 4px; }
    """)

    login = LoginPage()
    login.setWindowTitle(APP_TITLE)
    login.resize(560, 700)
    login.setMinimumSize(520, 650)
    login.show()

    holder: dict[str, Dashboard] = {}

    def launch():
        login.close()
        window = Dashboard(login.auth)
        holder["window"] = window
        window.show()

    login.login_ok.connect(launch)
    return app.exec()


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("Windows only")
    sys.exit(show_main())
