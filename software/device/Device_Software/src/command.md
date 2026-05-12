## 受信パケット
形式は以下の6Byte

**0xAA 0x55 CMD DATA1 DATA2 CS**

0xAA, 0x55: パケットヘッダ

CMD, DATA1, DATA2: DAC設定値(12bitを形式上16bit化) or ファン制御値 or システムコマンド
- Vout1: 0x01\
[0xAA] [0x55] [0x01] [DAC_H] [DAC_L] [CS]
- Vout2: 0x02\
[0xAA] [0x55] [0x02] [DAC_H] [DAC_L] [CS]
- FAN: 0x03\
[0xAA] [0x55] [0x03] [FAN1] [FAN2] [CS]
- System: 0x04\
[0xAA] [0x55] [0x04] [HOGE] [FUGA] [CS]

※HOGE FUGAの内容は要検討

CS: チェックサム(CMD^DATA1^DATA2)

## 送信パケット
形式は以下の8Byte

**0xAA 0x55 MODE DATA1 DATA2 DATA3 DATA4 CS**

0xAA, 0x55: パケットヘッダ

MODE, DATA1, DATA2, DATA3, DATA4: 測定データ
- 回路1: 0x01\
[0xAA] [0x55] [0x01] [I1_H] [I1_L] [V1_H] [V1_L] [CS]
- 回路2: 0x02\
[0xAA] [0x55] [0x02] [I2_H] [I2_L] [V2_H] [V2_L] [CS]
- ボードモニタ: 0x03\
[0xAA] [0x55] [0x03] [T1] [T2] [F1_rpm] [F2_rpm] [CS]

CS: チェックサム(MODE^DATA1^DATA2^DATA3^DATA4)