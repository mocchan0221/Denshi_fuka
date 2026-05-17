import os
import importlib.util
import inspect
from PyQt6.QtCore import QThread, pyqtSignal
from .macro_api import MacroBase

class MacroEngine(QThread):
    # マクロ -> GUI へ送るシグナル
    log_msg = pyqtSignal(str)
    log_data_point = pyqtSignal(float, float)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    
    # マクロ -> デバイス(MainWindow経由) へ送るシグナル
    req_set_state = pyqtSignal(int)
    req_set_current = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.current_macro = None
        self.params = {}
        
        # 常に最新の計測値をキャッシュしておく変数
        self.latest_v = 0.0
        self.latest_i = 0.0

    def update_latest_data(self, v: float, i: float):
        """SerialWorkerから届いた最新データをキャッシュする(GUIから呼ばれる)"""
        self.latest_v = v
        self.latest_i = i

    def scan_macros(self, macros_dir="macros"):
        """指定ディレクトリ内の.pyファイルを読み込み、利用可能なマクロの辞書を返す"""
        available_macros = {}
        if not os.path.exists(macros_dir):
            os.makedirs(macros_dir)
            return available_macros

        for filename in os.listdir(macros_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                file_path = os.path.join(macros_dir, filename)
                
                try:
                    # 動的にモジュールをインポート
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # MacroBaseを継承しているクラスを探す
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, MacroBase) and obj is not MacroBase:
                            available_macros[obj.name] = obj
                except Exception as e:
                    print(f"Failed to load macro {filename}: {e}")
                    
        return available_macros

    def start_macro(self, macro_class, params):
        """選択されたマクロクラスをインスタンス化してスレッドを開始する"""
        self.current_macro = macro_class(self)
        self.params = params
        self.start()

    def stop_macro(self):
        """マクロの実行を安全に停止させるフラグを立てる"""
        self.is_running = False

    def run(self):
        """別スレッドでマクロを実行するメインループ"""
        self.is_running = True
        try:
            self.log_msg.emit(f"=== マクロ '{self.current_macro.name}' を開始 ===")
            self.current_macro.run(self.params)
            self.log_msg.emit("=== マクロが正常終了しました ===")
        except InterruptedError as e:
            self.log_msg.emit(f"[停止] {e}")
        except Exception as e:
            self.error_signal.emit(f"マクロ実行時エラー: {e}")
        finally:
            self.is_running = False
            # 安全のため、マクロ終了時は必ずIDLE状態へ戻す要求を出す
            self.req_set_state.emit(0) 

            if hasattr(self.current_macro, 'cleanup'):
                self.current_macro.cleanup()

            self.finished_signal.emit()