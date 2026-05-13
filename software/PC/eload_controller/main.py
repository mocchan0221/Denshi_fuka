import sys
from PyQt6.QtWidgets import QApplication
from core.serial_worker import SerialWorker
from gui.main_window import MainWindow

# 環境に合わせてポート名を変更してください
TARGET_PORT = "COM3"

def main():
    app = QApplication(sys.argv)
    
    # ワーカーとウィンドウのインスタンス化
    worker = SerialWorker(port=TARGET_PORT)
    window = MainWindow()

    # --- シグナルの結線 (GUI <-> バックグラウンド通信) ---
    
    # 1. バックグラウンド -> GUI (データ受信、ステータス変更)
    worker.data_received.connect(window.on_data_received)
    worker.connection_status.connect(window.on_connection_status)
    
    # 2. GUI -> バックグラウンド (コマンド送信)
    window.sig_send_cmd.connect(worker.send_command)

    # 起動時の処理
    window.show()
    worker.start() # 通信スレッド起動

    # 終了時の安全処理 (ウィンドウが閉じられたらIDLEにして通信終了)
    def cleanup():
        print("終了処理を実行します...")
        worker.send_command(4, 0, 0) # CMD_SYS(4), IDLE(0)
        worker.stop()

    app.aboutToQuit.connect(cleanup)
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
