import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSpinBox, QGroupBox, QGridLayout, QRadioButton)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from core.protocol import Protocol

class MainWindow(QMainWindow):
    sig_send_cmd = pyqtSignal(int, int, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("電子負荷コントローラー Ver 1.2")
        self.resize(1000, 750)

        # 内部状態
        self.active_circuit = 1 # 1 or 2
        self.max_points = 1000
        self.data_v = np.zeros(self.max_points)
        self.data_i = np.zeros(self.max_points)
        self.ptr = 0

        self._init_ui()

        # グラフ更新タイマー
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plot)
        self.update_timer.start(33)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 1. 上部コントロール ---
        top_layout = QHBoxLayout()
        
        # ステート制御 (名称を State に統一)
        state_group = QGroupBox("システム・ステート")
        state_layout = QHBoxLayout(state_group)
        self.btn_idle = QPushButton("IDLE")
        self.btn_standby = QPushButton("STANDBY")
        self.btn_stream = QPushButton("STREAM")
        
        self.state_buttons = {0: self.btn_idle, 1: self.btn_standby, 2: self.btn_stream}
        
        for code, btn in self.state_buttons.items():
            btn.clicked.connect(lambda ch, c=code: self._handle_state_change(c))
            state_layout.addWidget(btn)
        
        # 初期の見た目設定
        self._update_state_button_ui(0)
        top_layout.addWidget(state_group)

        # 回路モード切替 (新規追加)
        circuit_group = QGroupBox("回路切替 (Mode)")
        circuit_layout = QVBoxLayout(circuit_group)
        self.radio_ch1 = QRadioButton("Circuit 1 (DAC A)")
        self.radio_ch2 = QRadioButton("Circuit 2 (DAC B)")
        self.radio_ch1.setChecked(True)
        
        self.radio_ch1.toggled.connect(lambda checked: self._handle_circuit_change(1) if checked else None)
        self.radio_ch2.toggled.connect(lambda checked: self._handle_circuit_change(2) if checked else None)
        
        circuit_layout.addWidget(self.radio_ch1)
        circuit_layout.addWidget(self.radio_ch2)
        top_layout.addWidget(circuit_group)

        # DAC設定
        dac_group = QGroupBox("DAC 出力設定")
        dac_layout = QHBoxLayout(dac_group)
        self.spin_dac = QSpinBox()
        self.spin_dac.setRange(0, 4095)
        self.btn_dac_set = QPushButton("設定送信")
        self.btn_dac_set.clicked.connect(self._send_dac_val)
        dac_layout.addWidget(self.spin_dac)
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
        self.lbl_val = QLabel("最新計測値: V=---, I=---")
        status_bar.addWidget(self.lbl_status)
        status_bar.addWidget(self.lbl_val)
        main_layout.addLayout(status_bar)

        # --- 4. グラフ ---
        self.plot_widget = pg.PlotWidget(title="リアルタイム計測データ")
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)
        self.curve_v = self.plot_widget.plot(pen='r', name="電圧 (RAW)")
        self.curve_i = self.plot_widget.plot(pen='c', name="電流 (RAW)")
        main_layout.addWidget(self.plot_widget)

    def _handle_state_change(self, state_code):
        """ステート切替ボタン押下時の処理"""
        # 即座にUIを更新
        self._update_state_button_ui(state_code)
        # コマンド送信
        self.sig_send_cmd.emit(Protocol.CMD_SYS, state_code, 0)

    def _update_state_button_ui(self, active_code):
        """ステートボタンの色を即時更新"""
        active_style = "background-color: #4CAF50; color: white; font-weight: bold;"
        default_style = "background-color: none;"
        for code, btn in self.state_buttons.items():
            btn.setStyleSheet(active_style if code == active_code else default_style)

    def _handle_circuit_change(self, circuit_num):
        """回路(Mode)切替時の処理"""
        self.active_circuit = circuit_num
        print(f"回路切り替え: Circuit {circuit_num} が選択されました。")
        
        # 新回路のDACに0Vを設定する
        target_cmd = Protocol.CMD_DAC_A if circuit_num == 1 else Protocol.CMD_DAC_B
        self.sig_send_cmd.emit(target_cmd, 0x00, 0x00)
        
        # グラフを一度クリア（別の回路のデータが混ざらないように）
        self.data_v.fill(0)
        self.data_i.fill(0)

    def _send_dac_val(self):
        """現在アクティブな回路に対してDAC設定を送信"""
        val = self.spin_dac.value()
        high = (val >> 8) & 0xFF
        low = val & 0xFF
        cmd = Protocol.CMD_DAC_A if self.active_circuit == 1 else Protocol.CMD_DAC_B
        self.sig_send_cmd.emit(cmd, high, low)

    def on_data_received(self, data):
        mode = data.get('mode')
        
        # 受信データが現在の表示対象（Circuit 1 or 2）と一致する場合のみグラフ更新
        # 仕様: MODE_CH1_DATA = 0x01, MODE_CH2_DATA = 0x02
        if (self.active_circuit == 1 and mode == Protocol.MODE_CH1_DATA) or \
           (self.active_circuit == 2 and mode == Protocol.MODE_CH2_DATA):
            
            self.data_v[:-1] = self.data_v[1:]
            self.data_v[-1] = data['val2']
            self.data_i[:-1] = self.data_i[1:]
            self.data_i[-1] = data['val1']
            
            self.ptr += 1
            if self.ptr % 50 == 0:
                self.lbl_val.setText(f"最新計測値(CH{self.active_circuit}): V={data['val2']}, I={data['val1']}")

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