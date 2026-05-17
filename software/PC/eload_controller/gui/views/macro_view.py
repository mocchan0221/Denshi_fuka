# gui/views/macro_view.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QComboBox, QLabel, QDoubleSpinBox, QFormLayout, QGroupBox, QTextEdit)
from PyQt6.QtCore import pyqtSignal

class MacroView(QWidget):
    req_start = pyqtSignal(object, dict) # macro_class, params_dict
    req_stop = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.available_macros = {}
        self.current_params_widgets = {} # 動的に生成した入力フォームを保持
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- マクロ選択と制御 ---
        ctrl_layout = QHBoxLayout()
        self.combo_macro = QComboBox()
        self.combo_macro.currentIndexChanged.connect(self._on_macro_selected)
        
        self.btn_start = QPushButton("▶ マクロ実行")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_start.clicked.connect(self._on_start_clicked)
        
        self.btn_stop = QPushButton("■ 強制停止")
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.req_stop)

        ctrl_layout.addWidget(QLabel("実行マクロ:"))
        ctrl_layout.addWidget(self.combo_macro, stretch=1)
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        layout.addLayout(ctrl_layout)

        # --- パラメータ入力エリア (動的生成) ---
        self.group_params = QGroupBox("設定パラメータ")
        self.layout_params = QFormLayout(self.group_params)
        layout.addWidget(self.group_params)

        # --- ログ表示エリア ---
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setStyleSheet("font-family: monospace; background-color: #2b2b2b; color: #a9b7c6;")
        layout.addWidget(self.text_log)

    def set_available_macros(self, macros_dict):
        """エンジンから読み込んだマクロ一覧をコンボボックスにセット"""
        self.available_macros = macros_dict
        self.combo_macro.clear()
        for name in macros_dict.keys():
            self.combo_macro.addItem(name)

    def _on_macro_selected(self):
        """マクロが切り替わったら、パラメータ入力欄を再構築する"""
        # 既存のウィジェットを削除
        for i in reversed(range(self.layout_params.count())): 
            widget = self.layout_params.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.current_params_widgets.clear()

        macro_name = self.combo_macro.currentText()
        macro_class = self.available_macros.get(macro_name)
        
        if not macro_class: return

        # ダミーインスタンスを作ってパラメータ定義を取得
        dummy_instance = macro_class(None) 
        params_def = dummy_instance.get_parameters()

        # 定義に基づいてSpinBoxを生成
        for key, conf in params_def.items():
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1000.0) # 汎用的なレンジ
            spin.setDecimals(3)
            spin.setValue(conf.get("default", 0.0))
            
            self.layout_params.addRow(conf.get("label", key), spin)
            self.current_params_widgets[key] = spin

    def _on_start_clicked(self):
        macro_name = self.combo_macro.currentText()
        macro_class = self.available_macros.get(macro_name)
        if not macro_class: return

        # 入力されたパラメータを収集
        params = {key: widget.value() for key, widget in self.current_params_widgets.items()}
        
        self.req_start.emit(macro_class, params)

    def append_log(self, msg: str):
        self.text_log.append(msg)

    def set_running_state(self, is_running: bool):
        """実行中/停止中でボタンの有効状態を切り替える"""
        self.btn_start.setEnabled(not is_running)
        self.combo_macro.setEnabled(not is_running)
        self.btn_stop.setEnabled(is_running)
        for w in self.current_params_widgets.values():
            w.setEnabled(not is_running)