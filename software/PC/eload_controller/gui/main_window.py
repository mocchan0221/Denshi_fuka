import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QDoubleSpinBox, QGroupBox, QGridLayout, QRadioButton)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from core.protocol import Protocol

# --- ハードウェア定数 ---
# ADC関連 (MCP3564)
ADC_VREF = 2.4
ADC_MAX = 32767.0  # 16bit signed (>hh) での最大値。unsignedの場合は 65535.0 に変更してください

# DAC関連 (MCP4822)
DAC_VREF = 2.048
DAC_GAIN = 1.0     # ゲイン設定が2の場合は 2.0 に変更してください
DAC_MAX = 4095.0

# 回路1 (大電流向け)
C1_SHUNT_R = 0.1
C1_VDIV_RATIO = (100.0 + 22.0) / 22.0

# 回路2 (小電流・高電圧向け)
C2_SHUNT_R = 10.0
C2_VDIV_RATIO = (1000.0 + 10.0) / 10.0
# ----------------------

class MainWindow(QMainWindow):
    sig_send_cmd = pyqtSignal(int, int, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("電子負荷コントローラー Ver 1.3 (物理単位対応)")
        self.resize(1050, 750)

        self.active_circuit = 1
        self.max_points = 1000
        self.data_v = np.zeros(self.max_points)
        self.data_i = np.zeros(self.max_points)
        self.ptr = 0

        self._init_ui()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plot)
        self.update_timer.start(33)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 1. 上部コントロール ---
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
        
        # 謎の数字(0-4095)から、実際の電流値(A)入力へ変更
        self.spin_current = QDoubleSpinBox()
        self.spin_current.setDecimals(3)
        self.spin_current.setSuffix(" A")
        self._update_spinbox_range() # 初期レンジ設定
        
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
        self.lbl_val = QLabel("最新値: V=--- V, I=--- A")
        status_bar.addWidget(self.lbl_status)
        status_bar.addWidget(self.lbl_val)
        main_layout.addLayout(status_bar)

        # --- 4. グラフ ---
        self.plot_widget = pg.PlotWidget(title="リアルタイム計測データ (物理単位)")
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Voltage (V) / Current (A)')
        self.curve_v = self.plot_widget.plot(pen='r', name="電圧 (V)")
        self.curve_i = self.plot_widget.plot(pen='c', name="電流 (A)")
        main_layout.addWidget(self.plot_widget)

    def _update_spinbox_range(self):
        """アクティブな回路に合わせて、入力可能な電流値の最大値とステップを変更"""
        dac_max_v = DAC_VREF * DAC_GAIN
        if self.active_circuit == 1:
            max_current = dac_max_v / C1_SHUNT_R # 約 20.48A
            self.spin_current.setRange(0.0, max_current)
            self.spin_current.setSingleStep(0.1) # 100mA刻み
        else:
            max_current = dac_max_v / C2_SHUNT_R # 約 0.2048A (204.8mA)
            self.spin_current.setRange(0.0, max_current)
            self.spin_current.setSingleStep(0.001) # 1mA刻み

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
        
        # 安全のため、切り替え時はUIの電流設定を0Aに戻す
        self._update_spinbox_range()
        self.spin_current.setValue(0.0)
        
        target_cmd = Protocol.CMD_DAC_A if circuit_num == 1 else Protocol.CMD_DAC_B
        self.sig_send_cmd.emit(target_cmd, 0x00, 0x00)
        
        self.data_v.fill(0)
        self.data_i.fill(0)

    def _send_dac_val(self):
        target_i = self.spin_current.value()
        shunt_r = C1_SHUNT_R if self.active_circuit == 1 else C2_SHUNT_R
        
        # 電流(A) -> 必要なDAC出力電圧(V) -> DAC設定値(0-4095) へ逆算
        target_v = target_i * shunt_r
        dac_val = int((target_v / (DAC_VREF * DAC_GAIN)) * DAC_MAX)
        
        # ハードウェアリミットのクランプ処理
        dac_val = max(0, min(int(DAC_MAX), dac_val))
        
        high = (dac_val >> 8) & 0xFF
        low = dac_val & 0xFF
        cmd = Protocol.CMD_DAC_A if self.active_circuit == 1 else Protocol.CMD_DAC_B
        self.sig_send_cmd.emit(cmd, high, low)

    def on_data_received(self, data):
        mode = data.get('mode')
        
        if (self.active_circuit == 1 and mode == Protocol.MODE_CH1_DATA) or \
           (self.active_circuit == 2 and mode == Protocol.MODE_CH2_DATA):
            
            # RAW値をADCピンの入力電圧(V)に変換
            adc_volts_i = (data['val1'] / ADC_MAX) * ADC_VREF
            adc_volts_v = (data['val2'] / ADC_MAX) * ADC_VREF
            
            # 回路ごとの物理計算
            if self.active_circuit == 1:
                real_v = adc_volts_v * C1_VDIV_RATIO
                real_i = adc_volts_i / C1_SHUNT_R
            else:
                real_v = adc_volts_v * C2_VDIV_RATIO
                real_i = adc_volts_i / C2_SHUNT_R
            
            self.data_v[:-1] = self.data_v[1:]
            self.data_v[-1] = real_v
            self.data_i[:-1] = self.data_i[1:]
            self.data_i[-1] = real_i
            
            self.ptr += 1
            if self.ptr % 50 == 0:
                self.lbl_val.setText(f"最新値(CH{self.active_circuit}): V={real_v:.2f} V, I={real_i:.3f} A")

        elif mode == Protocol.MODE_MONITOR:
            self.lbl_temp1.setText(f"温度1: {data['temp1']} ℃")
            self.lbl_temp2.setText(f"温度2: {data['temp2']} ℃")
            self.lbl_fan1.setText(f"ファン1: {data['fan1_rpm'] * 100} RPM")
            self.lbl_fan2.setText(f"ファン2: {data['fan2_rpm'] * 100} RPM")

    def _update_plot(self):
        self.curve_v.setData(self.data_v)
        self.curve_i.setData(self.data_i)

    def on_connection_status(self, is_connected):
        state = "接続中" if is_connected else "切断"
        self.lbl_status.setText(f"通信: {state}")