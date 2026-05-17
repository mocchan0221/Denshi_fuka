# macros/battery_test.py
from core.macro_api import MacroBase

class BatteryTestMacro(MacroBase):
    name = "電池放電テスト (CCモード)"

    def get_parameters(self):
        return {
            "current": {"label": "放電電流 (A)", "type": "float", "default": 1.0},
            "cutoff_v": {"label": "終止電圧 (V)", "type": "float", "default": 3.0},
            "interval": {"label": "記録間隔 (秒)", "type": "float", "default": 1.0},
        }

    def run(self, params):
        target_a = params.get("current", 1.0)
        cutoff_v = params.get("cutoff_v", 3.0)
        interval = params.get("interval", 1.0)

        self.log_message(f"--- テスト開始: {target_a}A 定電流放電 ---")
        self.log_message(f"目標終止電圧: {cutoff_v}V")

        # 1. 準備フェーズ
        self.set_state("STANDBY")
        self.wait(2.0) # リレーがONになり、電圧が安定するのを待つ
        
        v, i = self.get_latest_data()
        self.log_message(f"無負荷電圧: {v:.2f} V")
        if v < cutoff_v:
            self.log_message("エラー: 開始時点で終止電圧を下回っています。")
            return

        # 2. 放電開始
        self.set_current(target_a)
        self.set_state("STREAM")
        self.log_message("STREAMモードへ移行、放電を開始します...")

        # 3. 計測ループ
        start_time = 0.0
        while self.is_running():
            v, i = self.get_latest_data()
            
            # TODO: 将来的にここで self.log_data(v, i) を呼んでCSVに書き出す
            self.log_message(f"[{start_time:04.1f}s] V: {v:.3f} V, I: {i:.3f} A")

            # 終了判定
            if v <= cutoff_v:
                self.log_message(f"終止電圧 ({v:.3f} V) に到達しました。")
                break

            self.wait(interval)
            start_time += interval

        # 4. 終了処理 (エンジン側でも安全処理は走りますが、明示的に書くことも可能)
        self.set_state("IDLE")
        self.log_message("放電テストを完了しました。")