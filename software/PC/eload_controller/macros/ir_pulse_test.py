from core.macro_api import MacroBase
import time

class PulsedIRTestMacro(MacroBase):
    name = "パルスDCIR (内部抵抗) 測定"

    def get_parameters(self):
        return {
            "start_i": {"label": "開始電流 (A)", "type": "float", "default": 0.5},
            "end_i": {"label": "終了電流 (A)", "type": "float", "default": 3.0},
            "step_i": {"label": "ステップ電流 (A)", "type": "float", "default": 0.5},
            "pulse_time": {"label": "負荷パルス幅 (秒)", "type": "float", "default": 0.1},
            "recovery_time": {"label": "休止回復時間 (秒)", "type": "float", "default": 2.0},
            "cutoff_v": {"label": "終止電圧制限 (V)", "type": "float", "default": 2.5},
        }

    def run(self, params):
        start_i = params.get("start_i", 0.5)
        end_i = params.get("end_i", 3.0)
        step_i = params.get("step_i", 0.5)
        pulse_time = params.get("pulse_time", 0.1)
        recovery_time = params.get("recovery_time", 2.0)
        cutoff_v = params.get("cutoff_v", 2.5)

        if step_i <= 0:
            self.log_message("エラー: ステップ電流は0より大きくしてください")
            return

        # 1. CSV初期化 (パルス前後の電圧を記録できるようにヘッダを変更)
        self.setup_csv(
            prefix="Pulsed_IR", 
            headers=["Time(s)", "Set_I(A)", "V_Rest(V)", "V_Load(V)", "I_Load(A)", "Delta_V(V)", "DCIR(mOhm)"]
        )

        self.log_message("--- パルスDCIR測定を開始します ---")
        
        # 準備
        self.set_current(0.0)
        self.set_state("STREAM")
        self.wait(2.0) # 電池の電圧が落ち着くのを待つ

        start_time = time.time()
        current_target = start_i
        
        # 2. パルススイープロジック
        while current_target <= end_i and self.is_running():
            elapsed = time.time() - start_time
            
            # --- フェーズA: 休止電圧 (V_Rest) の計測 ---
            self.set_current(0.0)
            # すでに前のサイクルのrecovery_timeで休止しているため、即座に計測
            v_rest, i_rest = self.get_latest_data()
            
            if v_rest < cutoff_v:
                self.log_message(f"休止電圧({v_rest:.3f}V)が終止電圧に達しました。終了します。")
                break

            self.log_message(f"[{elapsed:.1f}s] {current_target:.2f}A パルス印加 ({pulse_time}秒)...")

            # --- フェーズB: パルス負荷の印加と計測 ---
            self.set_current(current_target)
            self.wait(pulse_time) # 指定時間(例:0.1秒)だけ負荷をかける
            
            v_load, i_load = self.get_latest_data() # 負荷がかかった瞬間の沈み込んだ電圧
            
            # --- フェーズC: 負荷遮断と計算 ---
            self.set_current(0.0) # すぐに0Aに戻す
            
            delta_v = v_rest - v_load
            # ノイズ等でi_loadが極端に小さい場合のゼロ割り回避
            ir_calc = (delta_v / i_load) if i_load > 0.05 else 0.0
            ir_mohm = ir_calc * 1000.0
            
            self.log_message(f" -> V_Rest:{v_rest:.3f}V, V_Load:{v_load:.3f}V, DCIR:{ir_mohm:.1f}mΩ")
            
            # CSV記録
            self.write_csv_row([
                f"{elapsed:.2f}",
                f"{current_target:.3f}",
                f"{v_rest:.4f}",
                f"{v_load:.4f}",
                f"{i_load:.4f}",
                f"{delta_v:.4f}",
                f"{ir_mohm:.1f}"
            ])
            
            # --- フェーズD: 回復待ち ---
            # 電流を上げたあとの分極（化学的な反応遅れ）から回復するまで待つ
            current_target += step_i
            if current_target <= end_i:
                self.wait(recovery_time)
            
        self.log_message("測定シーケンス完了。IDLEに移行します。")
        self.set_state("IDLE")