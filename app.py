from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QProgressBar, QStackedWidget, QVBoxLayout, QWidget
)

from core.emulators import adb_connect_5555, default_adb_port, detect_emulators, optimize_emulator, port_is_open
from core.keyauth import KeyAuthClient
from core.system import clean_temp_files, cpu_summary, empty_recycle_bin, flush_dns, is_admin, list_background_processes, ram_summary, set_high_performance_power_plan, terminate_process

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
        root.setContentsMargins(55, 45, 55, 45)
        root.setSpacing(18)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)).scaled(170, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        title = QLabel(APP_TITLE)
        title.setObjectName("HeroTitle")
        title.setAlignment(Qt.AlignCenter)
        sub = QLabel("Secure license access • Windows gaming optimization")
        sub.setObjectName("Muted")
        sub.setAlignment(Qt.AlignCenter)
        self.status = QLabel("Connecting to license service…")
        self.status.setAlignment(Qt.AlignCenter)
        self.key = QLineEdit()
        self.key.setPlaceholderText("Enter your license key")
        self.key.setEchoMode(QLineEdit.Password)
        self.btn = QPushButton("VERIFY LICENSE")
        self.btn.clicked.connect(self.do_login)
        root.addStretch(1)
        root.addWidget(logo)
        root.addWidget(title)
        root.addWidget(sub)
        root.addSpacing(10)
        root.addWidget(self.key)
        root.addWidget(self.btn)
        root.addWidget(self.status)
        root.addStretch(1)
        self.fade_in()
        QTimer.singleShot(150, self.init_auth)

    def fade_in(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(650)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._fade_anim = anim

    def init_auth(self):
        self.status.setText("Initializing secure session…")
        ok, msg = self.auth.init()
        self.status.setText(msg if ok else f"License service: {msg}")
        self.btn.setEnabled(ok)

    def do_login(self):
        key = self.key.text().strip()
        if not key:
            self.status.setText("Enter a license key.")
            return
        self.btn.setEnabled(False)
        ok, msg = self.auth.license(key)
        self.status.setText(msg)
        self.btn.setEnabled(True)
        if ok:
            self.login_ok.emit()


class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        self.setMinimumSize(1000, 680)
        self.setWindowIcon(QIcon(str(LOGO)))
        self.last_page = 0
        self.setup_ui()
        self.refresh_dashboard()
        self.refresh_processes()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        nav = QFrame()
        nav.setObjectName("Nav")
        nav.setFixedWidth(235)
        nv = QVBoxLayout(nav)
        nv.setContentsMargins(20, 24, 20, 20)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)).scaled(58, 58, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        brand = QLabel("PNL50\nOPTIMIZER PRO")
        brand.setObjectName("Brand")
        nv.addWidget(logo)
        nv.addWidget(brand)
        nv.addSpacing(20)
        for text, index in [("Dashboard", 0), ("PC Cleanup", 1), ("Gaming Mode", 2), ("Emulators", 3), ("Background Apps", 4)]:
            b = QPushButton(text)
            b.setObjectName("NavButton")
            b.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            nv.addWidget(b)
        nv.addStretch(1)
        discord = QPushButton("JOIN PANEL 50 DISCORD")
        discord.clicked.connect(lambda: os.startfile(DISCORD_URL))
        nv.addWidget(discord)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.dashboard_page())
        self.pages.addWidget(self.cleanup_page())
        self.pages.addWidget(self.gaming_page())
        self.pages.addWidget(self.emulator_page())
        self.pages.addWidget(self.process_page())
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
        anim.setDuration(260)
        anim.setStartValue(0.25)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._page_anim = anim
        self.refresh_dashboard()

    def page_base(self, title, desc):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(16)
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
        w, lay = self.page_base("System Overview", "See the current Windows resource state before optimizing.")
        grid = QHBoxLayout()
        self.cpu_card = self.metric_card("CPU", "—")
        self.ram_card = self.metric_card("RAM", "—")
        self.admin_card = self.metric_card("Access", "—")
        grid.addWidget(self.cpu_card)
        grid.addWidget(self.ram_card)
        grid.addWidget(self.admin_card)
        lay.addLayout(grid)
        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setTextVisible(False)
        lay.addWidget(self.overall_bar)
        note = QLabel("Conservative mode: personal files are not touched, security services are not disabled, and boot configuration is left alone.")
        note.setWordWrap(True)
        note.setObjectName("Muted")
        lay.addWidget(note)
        quick = QPushButton("OPEN SAFE OPTIMIZATION")
        quick.clicked.connect(lambda: self.switch_page(1))
        lay.addWidget(quick, 0, Qt.AlignLeft)
        lay.addStretch(1)
        return w

    def cleanup_page(self):
        w, lay = self.page_base("PC Cleanup", "Clear safe temporary data and optional caches without touching documents, downloads, or browser profiles.")
        self.cleanup_status = QLabel("Ready")
        self.cleanup_status.setObjectName("Status")
        lay.addWidget(self.cleanup_status)
        row = QHBoxLayout()
        for text, fn in [("CLEAN TEMP FILES", self.do_cleanup), ("FLUSH DNS", self.do_dns), ("EMPTY RECYCLE BIN", self.do_recycle)]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        lay.addStretch(1)
        return w

    def gaming_page(self):
        w, lay = self.page_base("Gaming Mode", "Apply a Windows-supported high-performance power profile. The setting is reversible in Windows Power Options.")
        self.power_check = QCheckBox("Use Windows High Performance power plan")
        lay.addWidget(self.power_check)
        btn = QPushButton("APPLY GAMING MODE")
        btn.clicked.connect(self.apply_gaming)
        lay.addWidget(btn, 0, Qt.AlignLeft)
        info = QLabel("The app intentionally avoids opaque registry hacks, boot edits, driver replacement, or disabling Windows security components.")
        info.setWordWrap(True)
        info.setObjectName("Muted")
        lay.addWidget(info)
        lay.addStretch(1)
        return w

    def emulator_page(self):
        w, lay = self.page_base("Emulator Optimizer", "Detect BlueStacks / MSI App Player (HD-Player.exe), raise emulator process priority, use all logical CPUs, and keep the app's ADB target at local port 5555.")
        self.emu_list = QListWidget()
        lay.addWidget(self.emu_list)
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
        w, lay = self.page_base("Background Apps", "Select user applications you no longer need right now. Critical Windows/system processes are not presented for one-click termination.")
        self.proc_list = QListWidget()
        lay.addWidget(self.proc_list)
        row = QHBoxLayout()
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self.refresh_processes)
        close = QPushButton("CLOSE SELECTED")
        close.clicked.connect(self.close_selected_processes)
        row.addWidget(refresh)
        row.addWidget(close)
        lay.addLayout(row)
        return w

    def refresh_dashboard(self):
        cores, cpu = cpu_summary()
        total, used, ram_pct = ram_summary()
        self.cpu_card.findChildren(QLabel)[1].setText(f"{cpu:.0f}% • {cores} threads")
        self.ram_card.findChildren(QLabel)[1].setText(f"{used:.1f} / {total:.1f} GB")
        self.admin_card.findChildren(QLabel)[1].setText("Administrator" if is_admin() else "Standard")
        self.overall_bar.setValue(int((cpu + ram_pct) / 2))

    def do_cleanup(self):
        result = clean_temp_files()
        self.cleanup_status.setText(f"Removed {result['files']} files and {result['dirs']} folders. Locked/protected items were skipped.")
        self.refresh_dashboard()

    def do_dns(self):
        self.cleanup_status.setText("DNS cache flushed." if flush_dns() else "DNS flush failed.")

    def do_recycle(self):
        self.cleanup_status.setText("Recycle Bin emptied." if empty_recycle_bin() else "Recycle Bin action failed.")

    def apply_gaming(self):
        if not self.power_check.isChecked():
            QMessageBox.information(self, APP_TITLE, "Enable the High Performance checkbox first.")
            return
        ok, msg = set_high_performance_power_plan()
        QMessageBox.information(self, APP_TITLE, msg if ok else f"Could not apply setting: {msg}")

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
        if not hasattr(self, "proc_list"):
            return
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
        QLineEdit:focus { border: 1px solid #8c8c8c; }
        QPushButton { background: #f4f4f5; color: #0b0c0f; border: 0; border-radius: 11px; padding: 11px 15px; font-weight: 700; }
        QPushButton:hover { background: #ffffff; }
        QPushButton:disabled { background: #343842; color: #888; }
        #NavButton { background: transparent; color: #babec8; text-align: left; padding: 13px; font-weight: 600; }
        #NavButton:hover { background: #16181f; color: #ffffff; }
        QListWidget { background: #0d0f14; border: 1px solid #242732; border-radius: 13px; padding: 8px; }
        QListWidget::item { padding: 11px; margin: 2px; border-radius: 8px; }
        QListWidget::item:selected { background: #242732; }
        QCheckBox { spacing: 8px; padding: 8px 0; }
        QProgressBar { height: 7px; border: 0; background: #161820; border-radius: 4px; }
        QProgressBar::chunk { background: #dfe1e7; border-radius: 4px; }
    """)
    login = LoginPage()
    login.setWindowTitle(APP_TITLE)
    login.resize(560, 680)
    login.setMinimumSize(520, 640)
    login.show()

    def launch():
        login.close()
        window = Dashboard()
        window.show()
        app._pnl50_window = window

    login.login_ok.connect(launch)
    return app.exec()


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("Windows only")
    sys.exit(show_main())
