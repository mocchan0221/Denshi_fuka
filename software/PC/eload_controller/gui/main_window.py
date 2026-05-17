import math
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QDoubleSpinBox, QGroupBox, QGridLayout, QRadioButton, QTabWidget)
from PyQt6.QtCore import pyqtSignal
from core.protocol import Protocol
from core.macro_engine import MacroEngine
from .views.graph_view import GraphView
from .views.numeric_view import NumericView
from .views.macro_view import MacroView

# --- ハードウェア定数 ---
ADC_VREF = 2.4
ADC_MAX = 32767.0
DAC_VREF = 2.048
DAC_GAIN = 1.0
DAC_MAX = 4095.0

C1_SHUNT_R = 0.1
C1_VDIV_RATIO = (100.0 + 22.0) / 22.0
C2_SHUNT_R = 10.0
C2_VDIV_RATIO = (1000.0 + 10.0) / 10.0
# ----------------------

class MainWindow(QMainWindow):
    sig_send_cmd = pyqtSignal(int, int, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("電子負荷コントローラー Ver 2.0 (マルチビュー対応)")
        self.resize(1050, 800)

        self.active_circuit = 1
        self.ptr = 0

        self.macro_engine = MacroEngine()

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 1. 上部コントロール ---
        # (※前回と同じコードのため、冗長を避けるため主要部分以外は省略せずにそのまま入れます)
        top_layout = QHBoxLayout()
        
        state_group = QGroupBox("システム・ステート")
        state_layout = QHBoxLayout(state_group)
        self.btn_idle = QPushButton("IDLE")
        self.btn_standby = QPushButton("STANDBY")
        self.btn_stream = QPushButton("STREAM")
        self.state_buttons = {0: self.btn_idle, 1: self.btn_standby, 2: self.btn_stream}
        for code, btn in self.state_buttons.items():
            btn.clicked.connect(lambda ch, c=code: self._handle_state_change(c))
            state_layout.addWidget(btn)
        self._update_state_button_ui(0)
        top_layout.addWidget(state_group)

        circuit_group = QGroupBox("回路切替 (Mode)")
        circuit_layout = QVBoxLayout(circuit_group)
        self.radio_ch1 = QRadioButton("Circuit 1 (0.1Ω)")
        self.radio_ch2 = QRadioButton("Circuit 2 (10Ω)")
        self.radio_ch1.setChecked(True)
        self.radio_ch1.toggled.connect(lambda checked: self._handle_circuit_change(1) if checked else None)
        self.radio_ch2.toggled.connect(lambda checked: self._handle_circuit_change(2) if checked else None)
        circuit_layout.addWidget(self.radio_ch1)
        circuit_layout.addWidget(self.radio_ch2)
        top_layout.addWidget(circuit_group)

        dac_group = QGroupBox("定電流(CC)設定")
        dac_layout = QHBoxLayout(dac_group)
        self.spin_current = QDoubleSpinBox()
        self.spin_current.setDecimals(3)
        self.spin_current.setSuffix(" A")
        self._update_spinbox_range()
        self.btn_dac_set = QPushButton("設定送信")
        self.btn_dac_set.clicked.connect(self._send_dac_val)
        dac_layout.addWidget(self.spin_current)
        dac_layout.addWidget(self.btn_dac_set)
        top_layout.addWidget(dac_group)

        main_layout.addLayout(top_layout)

        # --- 2. ボードモニター ---
        monitor_group = QGroupBox("ボードモニター")
        mon_layout = QGridLayout(monitor_group)
        self.lbl_temp1 = QLabel("温度1: -- ℃")
        self.lbl_temp2 = QLabel("温度2: -- ℃")
        self.lbl_fan1 = QLabel("ファン1: -- RPM")
        self.lbl_fan2 = QLabel("ファン2: -- RPM")
        mon_layout.addWidget(self.lbl_temp1, 0, 0)
        mon_layout.addWidget(self.lbl_temp2, 0, 1)
        mon_layout.addWidget(self.lbl_fan1, 1, 0)
        mon_layout.addWidget(self.lbl_fan2, 1, 1)
        main_layout.addWidget(monitor_group)

        # --- 3. ステータス ---
        status_bar = QHBoxLayout()
        self.lbl_status = QLabel("通信: 未接続")
        status_bar.addWidget(self.lbl_status)
        main_layout.addLayout(status_bar)

        # --- 4. ビューエリア (QTabWidgetを使って切り替え可能に) ---
        self.tab_widget = QTabWidget()
        
        # Viewをインスタンス化
        self.graph_view = GraphView()
        self.numeric_view = NumericView()
        self.macro_view = MacroView()
        
        # タブに追加
        self.tab_widget.addTab(self.graph_view, "波形グラフ (Graph)")
        self.tab_widget.addTab(self.numeric_view, "テスター表示 (Meter)")
        self.tab_widget.addTab(self.macro_view, "自動計測 (Macro)")
        
        # フォントサイズを少し大きくして押しやすく
        self.tab_widget.setStyleSheet("QTabBar::tab { height: 40px; width: 200px; font-size: 16px; font-weight: bold; }")
        
        main_layout.addWidget(self.tab_widget)


    def _update_spinbox_range(self):
        dac_max_v = DAC_VREF * DAC_GAIN
        if self.active_circuit == 1:
            self.spin_current.setRange(0.0, dac_max_v / C1_SHUNT_R)
            self.spin_current.setSingleStep(0.1)
        else:
            self.spin_current.setRange(0.0, dac_max_v / C2_SHUNT_R)
            self.spin_current.setSingleStep(0.001)

    def _handle_state_change(self, state_code):
        self._update_state_button_ui(state_code)
        self.sig_send_cmd.emit(Protocol.CMD_SYS, state_code, 0)

    def _update_state_button_ui(self, active_code):
        active_style = "background-color: #4CAF50; color: white; font-weight: bold;"
        default_style = "background-color: none;"
        for code, btn in self.state_buttons.items():
            btn.setStyleSheet(active_style if code == active_code else default_style)

    def _handle_circuit_change(self, circuit_num):
        self.active_circuit = circuit_num
        self._update_spinbox_range()
        self.spin_current.setValue(0.0)
        
        target_cmd = Protocol.CMD_DAC_A if circuit_num == 1 else Protocol.CMD_DAC_B
        self.sig_send_cmd.emit(target_cmd, 0x00, 0x00)
        
        # グラフのクリアをViewに依頼
        self.graph_view.clear_data()

    def _send_dac_val(self):
        target_v = self.spin_current.value() * (C1_SHUNT_R if self.active_circuit == 1 else C2_SHUNT_R)
        dac_val = max(0, min(int(DAC_MAX), int((target_v / (DAC_VREF * DAC_GAIN)) * DAC_MAX)))
        cmd = Protocol.CMD_DAC_A if self.active_circuit == 1 else Protocol.CMD_DAC_B
        self.sig_send_cmd.emit(cmd, (dac_val >> 8) & 0xFF, dac_val & 0xFF)

    def _calc_temperature(self, raw_8bit):
        if raw_8bit <= 0 or raw_8bit >= 255: return "--"
        r_th = 10000.0 * (raw_8bit / (255.0 - raw_8bit))
        return f"{(1.0 / ((1.0 / 298.15) + (math.log(r_th / 10000.0) / 3435.0)) - 273.15):.1f}"

    def on_data_received(self, data):
        mode = data.get('mode')
        
        if (self.active_circuit == 1 and mode == Protocol.MODE_CH1_DATA) or \
           (self.active_circuit == 2 and mode == Protocol.MODE_CH2_DATA):
            
            adc_volts_i = (data['val1'] / ADC_MAX) * ADC_VREF
            adc_volts_v = (data['val2'] / ADC_MAX) * ADC_VREF
            
            if self.active_circuit == 1:
                real_v, real_i = adc_volts_v * C1_VDIV_RATIO, adc_volts_i / C1_SHUNT_R
            else:
                real_v, real_i = adc_volts_v * C2_VDIV_RATIO, adc_volts_i / C2_SHUNT_R
            
            self.macro_engine.update_latest_data(real_v, real_i)

            self.ptr += 1

            # 1. グラフには毎回データを送る (内部でバッファされる)
            self.graph_view.add_data(real_v, real_i)
            
            # 2. 数値メーターは人間が読めるように更新頻度を落とす (例: 100回に1回 = 10Hz)
            if self.ptr % 100 == 0:
                self.numeric_view.update_values(real_v, real_i)

        elif mode == Protocol.MODE_MONITOR:
            self.lbl_temp1.setText(f"温度1: {self._calc_temperature(data['temp1'])} ℃")
            self.lbl_temp2.setText(f"温度2: {self._calc_temperature(data['temp2'])} ℃")
            self.lbl_fan1.setText(f"ファン1: {data['fan1_rpm'] * 100} RPM")
            self.lbl_fan2.setText(f"ファン2: {data['fan2_rpm'] * 100} RPM")

    def on_connection_status(self, is_connected):
        self.lbl_status.setText(f"通信: {'接続中' if is_connected else '切断'}")

    def _setup_macro_system(self):
        """マクロエンジンとGUI・システムをシグナルで接続する"""
        # 利用可能なマクロをスキャンしてViewに渡す
        available_macros = self.macro_engine.scan_macros("macros")
        self.macro_view.set_available_macros(available_macros)

        # View -> Engine
        self.macro_view.req_start.connect(self._start_macro_sequence)
        self.macro_view.req_stop.connect(self.macro_engine.stop_macro)

        # Engine -> View
        self.macro_engine.log_msg.connect(self.macro_view.append_log)
        self.macro_engine.finished_signal.connect(lambda: self.macro_view.set_running_state(False))
        self.macro_engine.error_signal.connect(lambda msg: self.macro_view.append_log(f"<font color='red'>{msg}</font>"))

        # Engine -> Device (API経由のコマンド実行)
        self.macro_engine.req_set_state.connect(self._handle_state_change)
        self.macro_engine.req_set_current.connect(self._set_current_from_macro)

    def _start_macro_sequence(self, macro_class, params):
        self.macro_view.text_log.clear()
        self.macro_view.set_running_state(True)
        self.macro_engine.start_macro(macro_class, params)

    def _set_current_from_macro(self, target_a: float):
        """マクロからの電流設定要求を受け取り、UIを更新してからコマンドを送信する"""
        self.spin_current.setValue(target_a)
        self._send_dac_val()