#include <avr/io.h>
#include "spi.h"

void spi_init(void) {
    // ピン設定
    // PB1: DAC_CS, PB2: ADC_CS, PB3: MOSI, PB4: MISO, PB5: SCK
    DDRB |= (1 << PB1) | (1 << PB2) | (1 << PB3) | (1 << PB5);
    PORTB |= (1 << PB1) | (1 << PB2);

    // SPIレジスタ設定
    SPCR = (1 << SPE) | (1 << MSTR);

    // 【追加】SPI倍速モード有効化 (F_CPU / 2 = 8MHz)
    SPSR |= (1 << SPI2X);
}

uint8_t spi_transfer(uint8_t data) {
    SPDR = data;
    while (!(SPSR & (1 << SPIF))) {
        ; // 送信完了待ち
    }
    return SPDR;
}