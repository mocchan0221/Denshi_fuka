import sys
from PyQt6.QtCore import QCoreApplication, QTimer
from core.protocol import Protocol
from core.serial_worker import SerialWorker

# 環境に合わせてポート名を変更してください (例: Windowsは "COM3", Mac/Linuxは "/dev/ttyUSB0" など)
TARGET_PORT = "COM8"

def main():
    # GUIを持たないQtアプリケーションを作成
    app = QCoreApplication(sys.argv)
    
    print(f"[{TARGET_PORT}] へ接続を試みます...")
    worker = SerialWorker(port=TARGET_PORT)
    
    # シグナルを受信した際のコールバック関数
    def on_data_received(data):
        # 1000HzなどでSTREAMが来るとログが流れてしまうため、適宜間引くか整形して表示します
        mode = data.get('mode')
        if mode in (Protocol.MODE_CH1_DATA, Protocol.MODE_CH2_DATA):
            print(f"[受信: DATA] モード:{mode} V={data['val2']} I={data['val1']}")
        elif mode == Protocol.MODE_MONITOR:
            print(f"[受信: MONI] Temp1:{data['temp1']} Fan1:{data['fan1_rpm']}")
        else:
            print(f"[受信: MISC] {data}")

    def on_error(err_msg):
        print(f"[エラー] {err_msg}")

    def on_status(is_connected):
        state = "接続成功" if is_connected else "切断"
        print(f"[ステータス] {state}")

    # シグナルの結線
    worker.data_received.connect(on_data_received)
    worker.error_occurred.connect(on_error)
    worker.connection_status.connect(on_status)

    # --- テストシーケンスの定義 ---
    def step1_standby():
        print("\n>>> [シーケンス 1] STANDBYモードへ遷移 (1秒に1回テレメトリが来るはずです)")
        worker.send_command(Protocol.CMD_SYS, 1, 0)

    def step2_set_dac():
        # 12bit(0〜4095)の中間値、2048(0x0800)を設定してみる
        print("\n>>> [シーケンス 2] DAC A に 0x0800 を設定")
        worker.send_command(Protocol.CMD_DAC_A, 0x08, 0x00)

    def step3_stream():
        print("\n>>> [シーケンス 3] STREAMモードへ遷移 (高速でテレメトリが来るはずです)")
        worker.send_command(Protocol.CMD_SYS, 2, 0)

    def step4_idle_and_quit():
        print("\n>>> [シーケンス 4] IDLEモード(安全停止)へ遷移し、終了します")
        worker.send_command(Protocol.CMD_SYS, 0, 0)
        
        # デバイスが処理する猶予を少し与えてからワーカーを停止・アプリ終了
        QTimer.singleShot(1000, worker.stop)
        QTimer.singleShot(2000, app.quit)

    # スレッド起動
    worker.start()

    # QTimerを使って、時間差でテストシーケンスを実行
    QTimer.singleShot(2000, step1_standby)       # 起動1秒後
    QTimer.singleShot(4000, step2_set_dac)       # 起動4秒後
    QTimer.singleShot(6000, step3_stream)        # 起動6秒後
    QTimer.singleShot(10000, step4_idle_and_quit) # 起動10秒後

    # イベントループの開始（app.quit() が呼ばれるまでブロックされる）
    sys.exit(app.exec())

if __name__ == '__main__':
    main()