import time
import csv
import os
from datetime import datetime

class MacroBase:
    name = "未定義のマクロ"

    def __init__(self, engine):
        self._engine = engine
        self._csv_file = None
        self._csv_writer = None

    def get_parameters(self):
        return {}

    def run(self, params):
        pass

    def cleanup(self):
        """マクロ終了時（正常・強制問わず）に必ず呼ばれる片付け処理"""
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None
            self.log_message("CSVファイルをクローズしました。")

    def setup_csv(self, prefix="log", headers=["Time", "Voltage(V)", "Current(A)"]):
        """logsフォルダを作成し、タイムスタンプ付きのCSVファイルを開く"""
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs/{prefix}_{timestamp}.csv"
        
        # 追記モード＆都度フラッシュしやすいように設定
        self._csv_file = open(filename, mode='w', newline='', encoding='utf-8')
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(headers)
        self.log_message(f"CSV出力を開始: {filename}")
        return filename

    def write_csv_row(self, row_data: list):
        """CSVに1行追記し、OSのバッファをフラッシュする"""
        if self._csv_writer:
            self._csv_writer.writerow(row_data)
            self._csv_file.flush() # 途中でPCが落ちてもデータが残るようにする

    def wait(self, seconds: float):
        start = time.time()
        while time.time() - start < seconds:
            if not self.is_running():
                raise InterruptedError("マクロがユーザーによって停止されました。")
            time.sleep(0.05)

    def is_running(self) -> bool:
        return self._engine.is_running

    def set_state(self, state_name: str):
        states = {"IDLE": 0, "STANDBY": 1, "STREAM": 2}
        self._engine.req_set_state.emit(states.get(state_name.upper(), 0))

    def set_current(self, target_a: float):
        self._engine.req_set_current.emit(target_a)

    def get_latest_data(self):
        return self._engine.latest_v, self._engine.latest_i

    def log_message(self, msg: str):
        self._engine.log_msg.emit(msg)