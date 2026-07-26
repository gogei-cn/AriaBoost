import sys
import datetime
import json
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QProgressBar, QTextEdit,
    QFrame, QGroupBox, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject  # 修正：pyqtSignal -> Signal
from PySide6.QtGui import QFont

from core import OptimizerCore
from config_dialog import ConfigDialog


class StatsDialog(QDialog):
    def __init__(self, stats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载统计报告")
        self.setFixedSize(400, 300)
        self.setModal(True)

        if parent:
            self.setStyleSheet(parent.styleSheet())

        font = QFont("Segoe UI", 10)
        self.setFont(font)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        title = QLabel("统计报告")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        data = [
            ("总重启次数", f"{stats['total_restarts']}"),
            ("平均速度", f"{stats['avg_speed_mb']:.2f} MB/s"),
            ("峰值速度", f"{stats['peak_speed_mb']:.2f} MB/s"),
            ("效率", f"{stats['efficiency']*100:.1f}%"),
        ]

        for label, value in data:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 10))
            val = QLabel(value)
            val.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            if parent and hasattr(parent, 'current_theme'):
                if parent.current_theme == "dark":
                    val.setStyleSheet("color: #6ea8fe;")
                else:
                    val.setStyleSheet("color: #007bff;")
            else:
                val.setStyleSheet("color: #007bff;")
            row_layout.addWidget(lbl)
            row_layout.addStretch()
            row_layout.addWidget(val)
            layout.addWidget(row)

        btn = QPushButton("关闭")
        btn.setFixedWidth(100)
        btn.clicked.connect(self.accept)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
        """)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)


STYLE_SHEET = """
* {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}

QMainWindow {
    background-color: #f0f4f8;
}
QWidget#ContentWidget {
    background-color: #f0f4f8;
}
QDialog {
    background-color: #ffffff;
}

QGroupBox {
    background-color: #ffffff;
    border: none;
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    font-size: 13px;
    color: #1a202c;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px 0 8px;
    background-color: #ffffff;
    color: #2c3e50;
}

QFrame#MetricCard {
    background-color: #ffffff;
    border: 1px solid #e8edf2;
    border-radius: 10px;
    padding: 10px;
}
QFrame#MetricCard QLabel {
    color: #2c3e50;
    font-size: 11px;
    font-weight: bold;
}

QPushButton {
    background-color: #6c757d;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
QPushButton:hover {
    background-color: #5a6268;
}
QPushButton:pressed {
    background-color: #343a40;
}
QPushButton:disabled {
    background-color: #b0b8c0;
    color: #e0e0e0;
}

QPushButton#startBtn {
    background-color: #28a745;
}
QPushButton#startBtn:hover {
    background-color: #218838;
}
QPushButton#startBtn:pressed {
    background-color: #145523;
}

QPushButton#stopBtn {
    background-color: #dc3545;
}
QPushButton#stopBtn:hover {
    background-color: #c82333;
}
QPushButton#stopBtn:pressed {
    background-color: #7a1a24;
}

QPushButton#configBtn {
    background-color: #0d6efd;
}
QPushButton#configBtn:hover {
    background-color: #0b5ed7;
}
QPushButton#configBtn:pressed {
    background-color: #06357a;
}

QPushButton#statsBtn {
    background-color: #17a2b8;
}
QPushButton#statsBtn:hover {
    background-color: #138496;
}
QPushButton#statsBtn:pressed {
    background-color: #0a4b5c;
}

QProgressBar {
    border: none;
    background-color: #e9ecef;
    border-radius: 4px;
    height: 8px;
}
QProgressBar::chunk {
    border-radius: 4px;
}

QTextEdit {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    color: #1a202c;
    font-family: Consolas, monospace;
    font-size: 12px;
    padding: 6px;
}

QLabel {
    color: #2c3e50;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
QLabel#titleLabel {
    color: #2c7be5;
    font-size: 18px;
    font-weight: bold;
}
QLabel#versionLabel {
    color: #6c757d;
    font-size: 12px;
}
QLabel#progressLabel {
    color: #6c757d;
}
QLabel#progressPct {
    font-weight: bold;
    color: #007bff;
}
QLabel#taskStatus {
    color: #6c757d;
}
QLabel#rpcStatus {
    color: #6c757d;
}
QLabel#rpcIndicator {
    font-size: 14px;
    font-weight: bold;
    color: #28a745;
}

QLabel.metricValue {
    font-size: 18px;
    font-weight: bold;
}
"""

DARK_STYLES = {
    "main": """
        QMainWindow { background-color: #1a1a2e; }
        QWidget#ContentWidget { background-color: #1a1a2e; }
        QDialog { background-color: #2d2d44; }
        QLabel { color: #e8e8e8; }
    """,
    "groupbox": """
        QGroupBox {
            background-color: #2d2d44;
            border: none;
            border-radius: 12px;
            margin-top: 14px;
            padding-top: 14px;
            font-weight: bold;
            font-size: 13px;
            color: #e8e8e8;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px 0 8px;
            background-color: #2d2d44;
            color: #e8e8e8;
        }
    """,
    "card": """
        QFrame#MetricCard {
            background-color: #3d3d5c;
            border: 1px solid #4d4d6c;
            border-radius: 10px;
            padding: 10px;
        }
        QFrame#MetricCard QLabel {
            color: #e8e8e8;
            font-size: 11px;
            font-weight: bold;
        }
    """,
    "log": """
        QTextEdit {
            background-color: #1a1a2e;
            border: 1px solid #3d3d5c;
            border-radius: 8px;
            color: #e8e8e8;
        }
    """,
    "progress": """
        QProgressBar {
            border: none;
            background-color: #2d2d44;
            border-radius: 4px;
            height: 8px;
        }
        QProgressBar::chunk {
            border-radius: 4px;
        }
    """,
    "progress_label": "color: #a0aec0;",
    "progress_pct": "font-weight: bold; color: #6ea8fe;",
    "task_status": "color: #a0aec0;",
    "rpc_status": "color: #a0aec0;",
    "rpc_indicator": "color: #48bb78; font-size: 14px; font-weight: bold;",
    "title": "color: #6ea8fe;",
    "version": "color: #a0aec0;",
}


class CoreWorker(QObject):
    log_signal = Signal(str)          # 修正：pyqtSignal -> Signal
    status_signal = Signal(str)       # 修正
    speed_signal = Signal(dict)       # 修正
    state_signal = Signal(dict)       # 修正
    stats_signal = Signal(dict)       # 修正

    def __init__(self):
        super().__init__()
        self.core = OptimizerCore(ui_callback=self._core_callback)
        self.running = False

    def _core_callback(self, event_type, data):
        if event_type == "log":
            self.log_signal.emit(data)
        elif event_type == "status":
            self.status_signal.emit(data)
        elif event_type == "speed":
            self.speed_signal.emit(data)
        elif event_type == "stats":
            self.stats_signal.emit(data)

    def start(self):
        if self.running:
            return
        self.running = True
        self.core.running = True
        self.core.initial_restart()

    def stop(self):
        self.running = False
        self.core.running = False

    def step(self):
        if not self.running:
            return
        try:
            state = self.core.step()
            if state:
                self.state_signal.emit(state)
                self.status_signal.emit(state.get("status", ""))
                speed_str = state.get("speed", "0")
                try:
                    speed_mb = float(speed_str.split()[0])
                except:
                    speed_mb = 0
                peak_str = state.get("peak", "0")
                if peak_str == "测算中":
                    peak = 0
                else:
                    try:
                        peak = float(peak_str.split()[0]) * 1048576
                    except:
                        peak = 0
                self.speed_signal.emit({"speed": speed_mb, "peak": peak})
        except Exception as e:
            self.log_signal.emit(f"核心异常: {e}")

    def get_stats(self):
        if self.core:
            stats = self.core.get_statistics()
            self.stats_signal.emit(stats)

    def reload_config(self):
        import config
        config.reload_config()
        self.log_signal.emit("配置已重载")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_theme = self.load_theme_preference()
        self.thread = None
        self.worker = None
        self.timer = None

        self.current_progress_value = 0

        self.init_ui()
        self.apply_theme(self.current_theme)
        self.append_log('优化器已启动，点击"开始优化"')
        self.update_status_text("等待开始")

    def _create_thread(self):
        if self.thread is not None:
            self._cleanup_thread()
        self.thread = QThread()
        self.worker = CoreWorker()
        self.worker.moveToThread(self.thread)

        self.worker.log_signal.connect(self.append_log)
        self.worker.status_signal.connect(self.update_status_text)
        self.worker.speed_signal.connect(self.update_speed)
        self.worker.state_signal.connect(self.update_ui_from_state)
        self.worker.stats_signal.connect(self.show_stats_dialog)

        self.thread.started.connect(self.worker.start)
        self.thread.finished.connect(self._on_thread_finished)

        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timer)
        self.timer.setInterval(1000)

    def _cleanup_thread(self):
        if self.thread is not None:
            try:
                if self.thread.isRunning():
                    self.thread.quit()
                    self.thread.wait(2000)
            except:
                pass
            self.thread = None
            self.worker = None
            self.timer = None

    def _on_thread_finished(self):
        if self.thread is not None:
            try:
                self.thread.deleteLater()
            except:
                pass
            self.thread = None
            self.worker = None

    def _on_timer(self):
        if self.thread is not None and self.thread.isRunning() and self.worker is not None and self.worker.running:
            try:
                self.worker.step()
            except RuntimeError:
                pass

    def init_ui(self):
        self.setWindowTitle("AriaBoost")
        self.setGeometry(100, 100, 960, 720)
        self.setMinimumSize(850, 600)

        font = QFont("Segoe UI", 9)
        self.setFont(font)
        self.setStyleSheet(STYLE_SHEET)

        central_widget = QWidget()
        central_widget.setObjectName("ContentWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 12, 24, 24)
        main_layout.setSpacing(12)

        # 标题栏
        title_layout = QHBoxLayout()
        self.title_label = QLabel("AriaBoost")
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label)

        self.version_label = QLabel("v1.0")
        self.version_label.setObjectName("versionLabel")
        title_layout.addWidget(self.version_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # 工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)

        self.start_btn = QPushButton("开始优化")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setFixedWidth(110)
        self.start_btn.clicked.connect(self.start_optimization)

        self.stop_btn = QPushButton("停止优化")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setFixedWidth(110)
        self.stop_btn.clicked.connect(self.stop_optimization)
        self.stop_btn.setEnabled(False)

        config_btn = QPushButton("设置")
        config_btn.setObjectName("configBtn")
        config_btn.setFixedWidth(90)
        config_btn.clicked.connect(self.open_config)

        stats_btn = QPushButton("统计")
        stats_btn.setObjectName("statsBtn")
        stats_btn.setFixedWidth(90)
        stats_btn.clicked.connect(self.show_statistics)

        toolbar_layout.addWidget(self.start_btn)
        toolbar_layout.addWidget(self.stop_btn)
        toolbar_layout.addWidget(config_btn)
        toolbar_layout.addWidget(stats_btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setFixedHeight(28)
        toolbar_layout.addWidget(line)

        rpc_layout = QHBoxLayout()
        rpc_layout.setSpacing(5)
        self.rpc_indicator = QLabel("*")
        self.rpc_indicator.setObjectName("rpcIndicator")
        rpc_layout.addWidget(self.rpc_indicator)

        self.rpc_status = QLabel("RPC 正常")
        self.rpc_status.setObjectName("rpcStatus")
        rpc_layout.addWidget(self.rpc_status)
        toolbar_layout.addLayout(rpc_layout)

        self.task_status = QLabel("* 等待任务")
        self.task_status.setObjectName("taskStatus")
        toolbar_layout.addWidget(self.task_status)

        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        # 主内容
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)

        # 仪表盘
        self.dashboard_group = QGroupBox("实时监控")
        dashboard_layout = QGridLayout()
        dashboard_layout.setSpacing(12)

        metrics = [
            ("当前速度", "speed", "#007bff"),
            ("基准峰值", "peak", "#28a745"),
            ("动态阈值", "threshold", "#ffc107"),
            ("热身时长", "warmup", "#17a2b8"),
            ("全局平均", "global_avg", "#17a2b8"),
            ("下载进度", "progress", "#dc3545"),
            ("运行状态", "cycle", "#6c757d"),
            ("重启次数", "restart", "#ffc107"),
            ("聚类模式", "mode", "#6c757d"),
        ]

        self.value_labels = {}
        self.metric_cards = []
        for i, (label_text, key, color) in enumerate(metrics):
            row, col = divmod(i, 3)
            card = QFrame()
            card.setObjectName("MetricCard")
            card.setAutoFillBackground(True)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(2)

            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 10))
            card_layout.addWidget(lbl)

            val_lbl = QLabel("0")
            val_lbl.setObjectName("metricValue")
            val_lbl.setStyleSheet(f"font-size: 19px; font-weight: bold; color: {color};")
            card_layout.addWidget(val_lbl)
            self.value_labels[key] = val_lbl
            self.metric_cards.append(card)

            dashboard_layout.addWidget(card, row, col)

        self.dashboard_group.setLayout(dashboard_layout)
        content_layout.addWidget(self.dashboard_group)

        # 进度条
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("下载进度：")
        self.progress_label.setObjectName("progressLabel")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)

        self.progress_pct = QLabel("0%")
        self.progress_pct.setObjectName("progressPct")

        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_pct)
        content_layout.addLayout(progress_layout)

        # 日志
        self.log_group = QGroupBox("事件日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        self.log_group.setLayout(log_layout)
        content_layout.addWidget(self.log_group)

        main_layout.addWidget(content_widget)

    def load_theme_preference(self):
        try:
            import config
            return config.CONFIG.get("THEME", "light")
        except:
            return "light"

    def save_theme_preference(self, theme):
        try:
            import config
            config.CONFIG["THEME"] = theme
            with open(config.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config.CONFIG, f, indent=4, ensure_ascii=False)
        except:
            pass

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        if theme_name == "dark":
            dark = DARK_STYLES
            self.setStyleSheet(STYLE_SHEET + "\n" + dark["main"])
            self.dashboard_group.setStyleSheet(dark["groupbox"])
            self.log_group.setStyleSheet(dark["groupbox"])
            for card in self.metric_cards:
                card.setStyleSheet(dark["card"])
            self.log_text.setStyleSheet(dark["log"])
            self.progress_bar.setStyleSheet(dark["progress"])
            self.title_label.setStyleSheet(dark["title"])
            self.version_label.setStyleSheet(dark["version"])
            self.progress_label.setStyleSheet(dark["progress_label"])
            self.progress_pct.setStyleSheet(dark["progress_pct"])
            self.task_status.setStyleSheet(dark["task_status"])
            self.rpc_status.setStyleSheet(dark["rpc_status"])
            self.rpc_indicator.setStyleSheet(dark["rpc_indicator"])
        else:
            self.setStyleSheet(STYLE_SHEET)
            self.dashboard_group.setStyleSheet("")
            self.log_group.setStyleSheet("")
            for card in self.metric_cards:
                card.setStyleSheet("")
            self.log_text.setStyleSheet("")
            self.progress_bar.setStyleSheet("")
            self.title_label.setStyleSheet("")
            self.version_label.setStyleSheet("")
            self.progress_label.setStyleSheet("")
            self.progress_pct.setStyleSheet("")
            self.task_status.setStyleSheet("")
            self.rpc_status.setStyleSheet("")
            self.rpc_indicator.setStyleSheet("")

        self.save_theme_preference(theme_name)

    def append_log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            self.log_text.append(f"{ts}  {msg}")
        except:
            pass

    def update_status_text(self, text):
        try:
            self.value_labels["cycle"].setText(text)
        except:
            pass

    def update_speed(self, data):
        try:
            speed = data.get("speed", 0)
            peak = data.get("peak", 0)
            self.value_labels["speed"].setText(f"{speed:.2f} MB/s")
            if isinstance(peak, (int, float)):
                self.value_labels["peak"].setText(f"{peak/1048576:.2f} MB/s")
            else:
                self.value_labels["peak"].setText(str(peak))
        except:
            pass

    def update_ui_from_state(self, state):
        try:
            for key, value in state.items():
                if key in self.value_labels:
                    self.value_labels[key].setText(value)

            progress_str = state.get("progress", "0%").replace('%', '')
            try:
                val = float(progress_str)
                self.current_progress_value = int(val)
                self.progress_bar.setValue(self.current_progress_value)
                self.progress_pct.setText(f"{val:.1f}%")

                if val < 30:
                    color = "#dc3545"
                elif val < 70:
                    color = "#ffc107"
                else:
                    color = "#28a745"

                if self.current_theme == "dark":
                    bg = "#2d2d44"
                else:
                    bg = "#e9ecef"

                self.progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: none;
                        background-color: {bg};
                        border-radius: 4px;
                        height: 8px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {color};
                        border-radius: 4px;
                    }}
                """)
            except:
                pass

            status_text = state.get("status", "")
            if "异常" in status_text or "错误" in status_text:
                self.rpc_indicator.setStyleSheet("color: #dc3545; font-size: 14px; font-weight: bold;")
                self.rpc_status.setText("RPC 异常")
                self.task_status.setText("* 异常")
                self.task_status.setStyleSheet("color: #dc3545;")
            elif "停止" in status_text:
                self.rpc_indicator.setStyleSheet("color: #ffc107; font-size: 14px; font-weight: bold;")
                self.rpc_status.setText("RPC 暂停")
                self.task_status.setText("* 已停止")
                self.task_status.setStyleSheet("color: #ffc107;")
            else:
                theme_color = "#48bb78" if self.current_theme == "dark" else "#28a745"
                self.rpc_indicator.setStyleSheet(f"color: {theme_color}; font-size: 14px; font-weight: bold;")
                self.rpc_status.setText("RPC 正常")
                if "任务" in status_text:
                    self.task_status.setText("* 运行中")
                    self.task_status.setStyleSheet(f"color: {theme_color};")
                else:
                    self.task_status.setText("* 等待任务")
                    task_color = "#a0aec0" if self.current_theme == "dark" else "#6c757d"
                    self.task_status.setStyleSheet(f"color: {task_color};")
        except:
            pass

    def show_stats_dialog(self, stats):
        dialog = StatsDialog(stats, self)
        dialog.exec()

    def show_statistics(self):
        if self.worker is not None:
            self.worker.get_stats()

    def start_optimization(self):
        try:
            self._cleanup_thread()
            self._create_thread()

            if self.thread is None:
                self.append_log("创建线程失败")
                return

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.thread.start()
            if self.timer is not None:
                self.timer.start()
            self.append_log("优化已启动")
        except Exception as e:
            self.append_log(f"启动失败: {e}")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def stop_optimization(self):
        try:
            if self.thread is not None:
                if self.worker is not None:
                    self.worker.stop()
                if self.timer is not None:
                    self.timer.stop()
                if self.thread.isRunning():
                    self.thread.quit()
                    self.thread.wait(2000)

            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.append_log("优化已停止")
        except Exception as e:
            self.append_log(f"停止失败: {e}")

    def open_config(self):
        try:
            dialog = ConfigDialog(self)
            dialog.exec()
        except Exception as e:
            self.append_log(f"打开设置失败: {e}")

    def closeEvent(self, event):
        self.stop_optimization()
        self._cleanup_thread()
        event.accept()


def run_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())