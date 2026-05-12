import serial
import time
from PyQt6.QtCore import QThread, pyqtSignal
from .protocol import Protocol

class SerialWorker(QThread):
    # GUIスレッドへ送るシグナル
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    connection_status = pyqtSignal(bool)

    def __init__(self, port, baudrate=1000000):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.ser = None

    def stop(self):
        self.running = False
        self.wait()

    def send_command(self, cmd, d1, d2):
        """外部(GUI)からコマンドを送信するためのメソッド"""
        if self.ser and self.ser.is_open:
            packet = Protocol.create_command_packet(cmd, d1, d2)
            self.ser.write(packet)

    def run(self):
        self.running = True
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=0.1
            )
            self.connection_status.emit(True)
        except Exception as e:
            self.error_occurred.emit(f"Failed to open port: {e}")
            self.connection_status.emit(False)
            return

        buffer = bytearray()
        
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    # 溜まっているデータを一気に読み込む
                    raw_data = self.ser.read(self.ser.in_waiting)
                    buffer.extend(raw_data)

                    # パケット同期と抽出
                    while len(buffer) >= 8:
                        # ヘッダを探す
                        idx = buffer.find(Protocol.HEADER)
                        
                        if idx == -1:
                            # ヘッダがない。パケットの破片かもしれないので、
                            # 最後の1バイトを残してクリア（ヘッダの半分 AA が最後にある可能性）
                            buffer = buffer[-1:] if len(buffer) > 0 else bytearray()
                            break
                        
                        if idx > 0:
                            # ヘッダより前のゴミデータを削除
                            del buffer[:idx]
                        
                        # 8バイト（テレメトリパケット長）に足りるか確認
                        if len(buffer) < 8:
                            break
                        
                        # 1パケット分取り出し
                        packet = bytes(buffer[:8])
                        del buffer[:8]
                        
                        # 解析
                        parsed = Protocol.parse_telemetry_packet(packet)
                        if parsed:
                            self.data_received.emit(parsed)
                else:
                    # CPU負荷低減のための微小スリープ
                    time.sleep(0.001)

            except Exception as e:
                self.error_occurred.emit(f"Comm error: {e}")
                self.running = False

        if self.ser and self.ser.is_open:
            self.ser.close()
        self.connection_status.emit(False)
