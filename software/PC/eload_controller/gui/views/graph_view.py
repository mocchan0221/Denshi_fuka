import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer

class GraphView(QWidget):
    def __init__(self):
        super().__init__()
        self.max_points = 1000
        self.data_v = np.zeros(self.max_points)
        self.data_i = np.zeros(self.max_points)
        
        self._init_ui()

        # グラフ更新用タイマー (約30FPS)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plot)
        self.update_timer.start(33)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget(title="リアルタイム計測データ")
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Voltage (V) / Current (A)')
        
        self.curve_v = self.plot_widget.plot(pen='r', name="電圧 (V)")
        self.curve_i = self.plot_widget.plot(pen='c', name="電流 (A)")
        
        layout.addWidget(self.plot_widget)

    def add_data(self, v: float, i: float):
        """新しいデータをバッファに追加"""
        self.data_v[:-1] = self.data_v[1:]
        self.data_v[-1] = v
        self.data_i[:-1] = self.data_i[1:]
        self.data_i[-1] = i

    def clear_data(self):
        """バッファをゼロクリア"""
        self.data_v.fill(0)
        self.data_i.fill(0)

    def _update_plot(self):
        self.curve_v.setData(self.data_v)
        self.curve_i.setData(self.data_i)