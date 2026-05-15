from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

class NumericView(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        
        # フォント設定 (デジタルメーター風に大きく)
        font_style = "font-size: 64px; font-weight: bold; font-family: 'Consolas', monospace;"
        label_style = "font-size: 24px; color: gray;"

        # --- 電圧表示 ---
        v_layout = QVBoxLayout()
        v_label = QLabel("VOLTAGE")
        v_label.setStyleSheet(label_style)
        self.val_v = QLabel("0.00 V")
        self.val_v.setStyleSheet(font_style + "color: #e74c3c;") # 赤系
        v_layout.addWidget(v_label)
        v_layout.addWidget(self.val_v)

        # --- 電流表示 ---
        i_layout = QVBoxLayout()
        i_label = QLabel("CURRENT")
        i_label.setStyleSheet(label_style)
        self.val_i = QLabel("0.000 A")
        self.val_i.setStyleSheet(font_style + "color: #3498db;") # 青系
        i_layout.addWidget(i_label)
        i_layout.addWidget(self.val_i)

        # --- 電力表示 ---
        p_layout = QVBoxLayout()
        p_label = QLabel("POWER")
        p_label.setStyleSheet(label_style)
        self.val_p = QLabel("0.00 W")
        self.val_p.setStyleSheet(font_style + "color: #2ecc71;") # 緑系
        p_layout.addWidget(p_label)
        p_layout.addWidget(self.val_p)

        layout.addLayout(v_layout)
        layout.addLayout(i_layout)
        layout.addLayout(p_layout)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_values(self, v: float, i: float):
        """数値を更新する (電力は自動計算)"""
        p = v * i
        # 桁数を固定してチラつきを防ぐ
        self.val_v.setText(f"{v:5.2f} V")
        self.val_i.setText(f"{i:5.3f} A")
        self.val_p.setText(f"{p:6.2f} W")