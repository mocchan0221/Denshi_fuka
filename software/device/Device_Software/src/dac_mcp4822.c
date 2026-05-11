#include "dac_mcp4822.h"
#include "spi.h"
#include <avr/io.h>

// CS操作用マクロ
#define DAC_CS_LOW()  (PORTB &= ~(1 << PB1))
#define DAC_CS_HIGH() (PORTB |= (1 << PB1))

void dac_init(void) {
    DAC_CS_HIGH(); 
}

void dac_write(uint8_t channel, uint16_t value) {
    // 下位12bitの切り出し
    value &= 0x0FFF;

    // 基本コマンド (DAC A, ゲイン1倍, 出力ON = 0x3000)
    uint16_t command =0x3000;

    // DAC B設定
    if (channel == DAC_CH_B) {
        command |= 0x8000; // 0x3000 | 0x8000 = 0xB000
    }

    // コマンドと出力データを合成
    uint16_t packet = command | value;

    // 通信開始
    DAC_CS_LOW();

    // 上位8ビット送信
    spi_transfer(packet >> 8);

    // 下位8ビット送信
    spi_transfer(packet & 0xFF);

    // 通信終了
    DAC_CS_HIGH();
}