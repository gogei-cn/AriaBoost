import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget,
    QWidget, QSpinBox, QDoubleSpinBox, QCheckBox,
    QGroupBox, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置设置")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        self.parent_window = parent

        self.apply_theme_styles()

        self.config = self.load_config()
        self.widgets = {}

        self.init_ui()
        self.load_values()

    def apply_theme_styles(self):
        if self.parent_window and hasattr(self.parent_window, 'current_theme'):
            theme = self.parent_window.current_theme
            if theme == "dark":
                self.setStyleSheet("""
                    QDialog { background-color: #2d2d44; }
                    QLabel { color: #e8e8e8; }
                    QGroupBox {
                        color: #e8e8e8;
                        background-color: #3d3d5c;
                        border: 1px solid #4d4d6c;
                        border-radius: 6px;
                        margin-top: 14px;
                    }
                    QGroupBox::title { color: #e8e8e8; background-color: #3d3d5c; }
                    QTabWidget::pane { background-color: #2d2d44; border: 1px solid #4d4d6c; }
                    QTabBar::tab {
                        color: #a0aec0;
                        background-color: #3d3d5c;
                        padding: 8px 12px;
                    }
                    QTabBar::tab:selected { color: #e8e8e8; background-color: #4d4d6c; }
                    QLineEdit, QComboBox {
                        background-color: #1a1a2e;
                        color: #e8e8e8;
                        border: 1px solid #4d4d6c;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QSpinBox, QDoubleSpinBox {
                        background-color: #1a1a2e;
                        color: #e8e8e8;
                        border: 1px solid #4d4d6c;
                        border-radius: 4px;
                        padding: 4px 6px;
                        min-height: 20px;
                    }
                    QSpinBox::up-button, QDoubleSpinBox::up-button {
                        subcontrol-origin: border;
                        subcontrol-position: top right;
                        width: 20px;
                        height: 14px;
                        background-color: #3d3d5c;
                        border: 1px solid #4d4d6c;
                        border-top-right-radius: 3px;
                        margin: 1px;
                    }
                    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                        width: 0;
                        height: 0;
                        border-left: 4px solid transparent;
                        border-right: 4px solid transparent;
                        border-bottom: 4px solid #e8e8e8;
                    }
                    QSpinBox::down-button, QDoubleSpinBox::down-button {
                        subcontrol-origin: border;
                        subcontrol-position: bottom right;
                        width: 20px;
                        height: 14px;
                        background-color: #3d3d5c;
                        border: 1px solid #4d4d6c;
                        border-bottom-right-radius: 3px;
                        margin: 1px;
                    }
                    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                        width: 0;
                        height: 0;
                        border-left: 4px solid transparent;
                        border-right: 4px solid transparent;
                        border-top: 4px solid #e8e8e8;
                    }
                    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
                    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                        background-color: #4d4d6c;
                    }
                    QCheckBox { color: #e8e8e8; }
                    QPushButton { color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
                """)
            else:
                self.setStyleSheet("""
                    QDialog { background-color: #ffffff; }
                    QLabel { color: #1a202c; }
                    QGroupBox {
                        color: #1a202c;
                        background-color: #f8f9fa;
                        border: 1px solid #dee2e6;
                        border-radius: 6px;
                        margin-top: 14px;
                    }
                    QGroupBox::title { color: #1a202c; background-color: #f8f9fa; }
                    QTabWidget::pane { background-color: #ffffff; border: 1px solid #dee2e6; }
                    QTabBar::tab { color: #495057; background-color: #e9ecef; padding: 8px 12px; }
                    QTabBar::tab:selected { color: #1a202c; background-color: #ffffff; }
                    QLineEdit, QComboBox {
                        background-color: #ffffff;
                        color: #1a202c;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QSpinBox, QDoubleSpinBox {
                        background-color: #ffffff;
                        color: #1a202c;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        padding: 4px 6px;
                        min-height: 20px;
                    }
                    QSpinBox::up-button, QDoubleSpinBox::up-button {
                        subcontrol-origin: border;
                        subcontrol-position: top right;
                        width: 20px;
                        height: 14px;
                        background-color: #e9ecef;
                        border: 1px solid #ced4da;
                        border-top-right-radius: 3px;
                        margin: 1px;
                    }
                    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                        width: 0;
                        height: 0;
                        border-left: 4px solid transparent;
                        border-right: 4px solid transparent;
                        border-bottom: 4px solid #495057;
                    }
                    QSpinBox::down-button, QDoubleSpinBox::down-button {
                        subcontrol-origin: border;
                        subcontrol-position: bottom right;
                        width: 20px;
                        height: 14px;
                        background-color: #e9ecef;
                        border: 1px solid #ced4da;
                        border-bottom-right-radius: 3px;
                        margin: 1px;
                    }
                    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                        width: 0;
                        height: 0;
                        border-left: 4px solid transparent;
                        border-right: 4px solid transparent;
                        border-top: 4px solid #495057;
                    }
                    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
                    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                        background-color: #dee2e6;
                    }
                    QCheckBox { color: #1a202c; }
                    QPushButton { color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
                """)

    def load_config(self):
        try:
            import config
            return config.CONFIG.copy()
        except:
            return {
                "RPC_URL": "http://127.0.0.1:16800/jsonrpc",
                "RPC_TOKEN": "9652530",
                "CHECK_INTERVAL": 1,
                "WARMUP_SEC": 10,
                "PAUSE_WAIT_SEC": 1,
                "MIN_TRIGGER_SPEED": 204800,
                "LOW_SPEED_TRIGGER_COUNT": 3,
                "SPEED_DROP_FILTER": 0.5,
                "PHASE_FACTOR_MIN": 0.9,
                "PHASE_FACTOR_MAX": 1.1,
                "PEAK_HISTORY_SIZE": 20,
                "PREDICTIVE_TRIGGER_ENABLED": True,
                "PREDICTIVE_GAP_SEC": 1.5,
                "PREDICTIVE_SPEED_MARGIN": 0.15,
                "VOLATILITY_THRESHOLD": 0.15,
                "SECOND_ORDER_SENSITIVITY": 0.8,
                "USE_BAYESIAN_OPT": True,
                "BAYES_OPT_INIT_SAMPLES": 5,
                "BAYES_OPT_CANDIDATES": 200,
                "OPT_THRESHOLD_RANGE": [0.3, 0.9],
                "OPT_WARMUP_RANGE": [5, 30],
                "EXPLORE_KAPPA_START": 1.0,
                "EXPLORE_KAPPA_MIN": 0.3,
                "USE_PATTERN_CLUSTER": True,
                "CLUSTER_K": 3,
                "CLUSTER_FEATURE_WINDOW": 20,
                "DISABLE_AFTER_PROGRESS": 0.95,
                "DISABLE_REMAINING_MB": 50,
                "SMOOTH_FACTOR": 0.3,
                "THEME": "light",
                "TRIGGER_COUNT_RANGE": [1, 5],
                "PREDICT_MARGIN_RANGE": [0.05, 0.25],
                "DROP_FILTER_RANGE": [0.3, 0.8],
                "ANOMALY_DETECTION_ENABLED": True,
                "CIRCUIT_BREAKER_ENABLED": True,
            }

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self.create_basic_tab(), "基础设置")
        tabs.addTab(self.create_trigger_tab(), "触发设置")
        tabs.addTab(self.create_bayesian_tab(), "贝叶斯优化")
        tabs.addTab(self.create_cluster_tab(), "聚类设置")
        tabs.addTab(self.create_advanced_tab(), "高级设置")
        tabs.addTab(self.create_theme_tab(), "外观")

        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def create_basic_tab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(10)
        row = 0

        group = QGroupBox("RPC 连接")
        group_layout = QGridLayout()
        self.add_field(group_layout, 0, "RPC 地址:", "RPC_URL", QLineEdit)
        self.add_field(group_layout, 1, "RPC Token:", "RPC_TOKEN", QLineEdit)
        group.setLayout(group_layout)
        layout.addWidget(group, row, 0, 1, 2)
        row += 1

        group = QGroupBox("基本参数")
        group_layout = QGridLayout()
        self.add_field(group_layout, 0, "检测间隔(秒):", "CHECK_INTERVAL", QDoubleSpinBox, 0.1, 10, 0.1)
        self.add_field(group_layout, 1, "热身时长(秒):", "WARMUP_SEC", QSpinBox, 1, 60)
        self.add_field(group_layout, 2, "暂停等待(秒):", "PAUSE_WAIT_SEC", QDoubleSpinBox, 0.1, 5, 0.1)
        group.setLayout(group_layout)
        layout.addWidget(group, row, 0, 1, 2)
        row += 1

        layout.setRowStretch(row, 1)
        return widget

    def create_trigger_tab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(10)

        group = QGroupBox("触发条件")
        group_layout = QGridLayout()
        self.add_field(group_layout, 0, "最低触发速度(KB/s):", "MIN_TRIGGER_SPEED", QSpinBox, 1, 1000000, 1024)
        self.add_field(group_layout, 1, "低速触发次数:", "LOW_SPEED_TRIGGER_COUNT", QSpinBox, 1, 10)
        self.add_field(group_layout, 2, "速度暴跌过滤:", "SPEED_DROP_FILTER", QDoubleSpinBox, 0, 1, 0.05)
        group.setLayout(group_layout)
        layout.addWidget(group, 0, 0, 1, 2)

        group2 = QGroupBox("预测触发")
        group2_layout = QGridLayout()
        self.add_checkbox(group2_layout, 0, "启用预测触发:", "PREDICTIVE_TRIGGER_ENABLED")
        self.add_field(group2_layout, 1, "预测间隔(秒):", "PREDICTIVE_GAP_SEC", QDoubleSpinBox, 0.1, 5, 0.1)
        self.add_field(group2_layout, 2, "预测裕度:", "PREDICTIVE_SPEED_MARGIN", QDoubleSpinBox, 0, 1, 0.01)
        group2.setLayout(group2_layout)
        layout.addWidget(group2, 1, 0, 1, 2)

        group3 = QGroupBox("阶段因子")
        group3_layout = QGridLayout()
        self.add_field(group3_layout, 0, "阶段因子最小值:", "PHASE_FACTOR_MIN", QDoubleSpinBox, 0.5, 1.5, 0.05)
        self.add_field(group3_layout, 1, "阶段因子最大值:", "PHASE_FACTOR_MAX", QDoubleSpinBox, 0.5, 1.5, 0.05)
        group3.setLayout(group3_layout)
        layout.addWidget(group3, 2, 0, 1, 2)

        layout.setRowStretch(3, 1)
        return widget

    def create_bayesian_tab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(10)

        group = QGroupBox("贝叶斯优化")
        group_layout = QGridLayout()
        self.add_checkbox(group_layout, 0, "启用贝叶斯优化:", "USE_BAYESIAN_OPT")
        self.add_field(group_layout, 1, "初始采样数:", "BAYES_OPT_INIT_SAMPLES", QSpinBox, 1, 20)
        self.add_field(group_layout, 2, "候选点数:", "BAYES_OPT_CANDIDATES", QSpinBox, 10, 1000, 10)
        self.add_field(group_layout, 3, "探索参数 κ 起始:", "EXPLORE_KAPPA_START", QDoubleSpinBox, 0.1, 5, 0.1)
        self.add_field(group_layout, 4, "探索参数 κ 最小:", "EXPLORE_KAPPA_MIN", QDoubleSpinBox, 0.01, 5, 0.01)
        group.setLayout(group_layout)
        layout.addWidget(group, 0, 0, 1, 2)

        group2 = QGroupBox("优化范围")
        group2_layout = QGridLayout()
        self.add_field(group2_layout, 0, "阈值范围 最小:", "OPT_THRESHOLD_MIN", QDoubleSpinBox, 0.1, 0.9, 0.05)
        self.add_field(group2_layout, 1, "阈值范围 最大:", "OPT_THRESHOLD_MAX", QDoubleSpinBox, 0.1, 1.0, 0.05)
        self.add_field(group2_layout, 2, "热身范围 最小:", "OPT_WARMUP_MIN", QSpinBox, 1, 60)
        self.add_field(group2_layout, 3, "热身范围 最大:", "OPT_WARMUP_MAX", QSpinBox, 1, 120)
        group2.setLayout(group2_layout)
        layout.addWidget(group2, 1, 0, 1, 2)

        layout.setRowStretch(2, 1)
        return widget

    def create_cluster_tab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(10)

        group = QGroupBox("聚类模式")
        group_layout = QGridLayout()
        self.add_checkbox(group_layout, 0, "启用聚类模式:", "USE_PATTERN_CLUSTER")
        self.add_field(group_layout, 1, "聚类数量:", "CLUSTER_K", QSpinBox, 2, 5)
        group.setLayout(group_layout)
        layout.addWidget(group, 0, 0, 1, 2)

        info_label = QLabel("聚类模式会根据下载速度模式自动选择最优策略")
        info_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        layout.addWidget(info_label, 1, 0, 1, 2)

        layout.setRowStretch(2, 1)
        return widget

    def create_advanced_tab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(10)

        group = QGroupBox("高级参数")
        group_layout = QGridLayout()
        self.add_field(group_layout, 0, "抖动阈值:", "VOLATILITY_THRESHOLD", QDoubleSpinBox, 0, 1, 0.01)
        self.add_field(group_layout, 1, "二阶灵敏度:", "SECOND_ORDER_SENSITIVITY", QDoubleSpinBox, 0, 2, 0.1)
        self.add_field(group_layout, 2, "平滑因子:", "SMOOTH_FACTOR", QDoubleSpinBox, 0, 1, 0.05)
        self.add_field(group_layout, 3, "峰值历史大小:", "PEAK_HISTORY_SIZE", QSpinBox, 5, 100)
        group.setLayout(group_layout)
        layout.addWidget(group, 0, 0, 1, 2)

        group2 = QGroupBox("高级功能")
        group2_layout = QGridLayout()
        self.add_checkbox(group2_layout, 0, "启用异常检测:", "ANOMALY_DETECTION_ENABLED")
        self.add_checkbox(group2_layout, 1, "启用熔断器:", "CIRCUIT_BREAKER_ENABLED")
        group2.setLayout(group2_layout)
        layout.addWidget(group2, 1, 0, 1, 2)

        group3 = QGroupBox("优化参数范围")
        group3_layout = QGridLayout()
        self.add_field(group3_layout, 0, "触发计数范围 最小:", "TRIGGER_COUNT_MIN", QSpinBox, 1, 5)
        self.add_field(group3_layout, 1, "触发计数范围 最大:", "TRIGGER_COUNT_MAX", QSpinBox, 1, 5)
        self.add_field(group3_layout, 2, "预测裕度范围 最小:", "PREDICT_MARGIN_MIN", QDoubleSpinBox, 0.01, 0.5, 0.01)
        self.add_field(group3_layout, 3, "预测裕度范围 最大:", "PREDICT_MARGIN_MAX", QDoubleSpinBox, 0.01, 0.5, 0.01)
        self.add_field(group3_layout, 4, "暴跌过滤范围 最小:", "DROP_FILTER_MIN", QDoubleSpinBox, 0.1, 0.9, 0.05)
        self.add_field(group3_layout, 5, "暴跌过滤范围 最大:", "DROP_FILTER_MAX", QDoubleSpinBox, 0.1, 0.9, 0.05)
        group3.setLayout(group3_layout)
        layout.addWidget(group3, 2, 0, 1, 2)

        layout.setRowStretch(3, 1)
        return widget

    def create_theme_tab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(10)

        group = QGroupBox("主题设置")
        group_layout = QGridLayout()
        group_layout.setSpacing(15)

        theme_label = QLabel("界面主题：")
        theme_label.setStyleSheet("font-weight: bold;")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("浅色模式", "light")
        self.theme_combo.addItem("深色模式", "dark")
        self.theme_combo.setMinimumWidth(150)
        group_layout.addWidget(theme_label, 0, 0)
        group_layout.addWidget(self.theme_combo, 0, 1)

        preview_label = QLabel("选择后点击「保存」立即生效")
        preview_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        group_layout.addWidget(preview_label, 1, 0, 1, 2)

        group.setLayout(group_layout)
        layout.addWidget(group, 0, 0, 1, 2)

        self.widgets["THEME"] = self.theme_combo

        layout.setRowStretch(1, 1)
        return widget

    def add_field(self, layout, row, label, key, widget_type, min_val=None, max_val=None, step=None):
        label_widget = QLabel(label)
        layout.addWidget(label_widget, row, 0)
        if widget_type == QLineEdit:
            widget = QLineEdit()
        elif widget_type == QSpinBox:
            widget = QSpinBox()
            if min_val is not None:
                widget.setMinimum(min_val)
            if max_val is not None:
                widget.setMaximum(max_val)
            if step is not None:
                widget.setSingleStep(step)
        elif widget_type == QDoubleSpinBox:
            widget = QDoubleSpinBox()
            if min_val is not None:
                widget.setMinimum(min_val)
            if max_val is not None:
                widget.setMaximum(max_val)
            if step is not None:
                widget.setSingleStep(step)
                widget.setDecimals(2)
        else:
            widget = QLineEdit()
        layout.addWidget(widget, row, 1)
        self.widgets[key] = widget

    def add_checkbox(self, layout, row, label, key):
        checkbox = QCheckBox(label)
        layout.addWidget(checkbox, row, 0, 1, 2)
        self.widgets[key] = checkbox

    def load_values(self):
        for key, widget in self.widgets.items():
            if key not in self.config:
                continue
            value = self.config[key]
            if isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                try:
                    widget.setValue(float(value))
                except:
                    widget.setValue(0)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)

    def save_config(self):
        try:
            new_config = {}
            for key, widget in self.widgets.items():
                if isinstance(widget, QLineEdit):
                    if key in ["RPC_TOKEN", "RPC_URL"]:
                        new_config[key] = widget.text().strip()
                    else:
                        try:
                            new_config[key] = float(widget.text()) if '.' in widget.text() else int(widget.text())
                        except:
                            new_config[key] = widget.text().strip()
                elif isinstance(widget, QSpinBox):
                    new_config[key] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    new_config[key] = widget.value()
                elif isinstance(widget, QCheckBox):
                    new_config[key] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    new_config[key] = widget.currentData()

            if "OPT_THRESHOLD_MIN" in new_config and "OPT_THRESHOLD_MAX" in new_config:
                new_config["OPT_THRESHOLD_RANGE"] = [
                    new_config.pop("OPT_THRESHOLD_MIN"),
                    new_config.pop("OPT_THRESHOLD_MAX")
                ]
            if "OPT_WARMUP_MIN" in new_config and "OPT_WARMUP_MAX" in new_config:
                new_config["OPT_WARMUP_RANGE"] = [
                    new_config.pop("OPT_WARMUP_MIN"),
                    new_config.pop("OPT_WARMUP_MAX")
                ]
            if "TRIGGER_COUNT_MIN" in new_config and "TRIGGER_COUNT_MAX" in new_config:
                new_config["TRIGGER_COUNT_RANGE"] = [
                    new_config.pop("TRIGGER_COUNT_MIN"),
                    new_config.pop("TRIGGER_COUNT_MAX")
                ]
            if "PREDICT_MARGIN_MIN" in new_config and "PREDICT_MARGIN_MAX" in new_config:
                new_config["PREDICT_MARGIN_RANGE"] = [
                    new_config.pop("PREDICT_MARGIN_MIN"),
                    new_config.pop("PREDICT_MARGIN_MAX")
                ]
            if "DROP_FILTER_MIN" in new_config and "DROP_FILTER_MAX" in new_config:
                new_config["DROP_FILTER_RANGE"] = [
                    new_config.pop("DROP_FILTER_MIN"),
                    new_config.pop("DROP_FILTER_MAX")
                ]

            if "THEME" in new_config:
                theme = new_config["THEME"]
                if self.parent_window:
                    self.parent_window.apply_theme(theme)

            import config
            config.CONFIG.update(new_config)

            with open(config.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config.CONFIG, f, indent=4, ensure_ascii=False)

            config.reload_config()

            QMessageBox.information(self, "成功", "配置已保存")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")