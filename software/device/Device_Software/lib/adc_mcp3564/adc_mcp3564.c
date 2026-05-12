#include "adc_mcp3564.h"
#include "spi.h"
#include <avr/io.h>
#include <util/delay.h>

#define ADC_CS_LOW()  (PORTB &= ~(1 << PB2))
#define ADC_CS_HIGH() (PORTB |= (1 << PB2))

#define CMD_READ(reg)  (0x40 | ((reg) << 2) | 0x03) 
#define CMD_WRITE(reg) (0x40 | ((reg) << 2) | 0x02) 

#define FAST_CMD_START 0x68
#define FAST_CMD_RESET 0x78


void adc_write_reg(uint8_t reg, uint8_t value) {
    ADC_CS_LOW();
    spi_transfer(CMD_WRITE(reg));
    spi_transfer(value);
    ADC_CS_HIGH();
}

uint8_t adc_read_reg(uint8_t reg) {
    ADC_CS_LOW();
    spi_transfer(CMD_READ(reg));
    uint8_t val = spi_transfer(0x00);
    ADC_CS_HIGH();
    return val;
}

void adc_init(void) {
    ADC_CS_HIGH();
    _delay_ms(50);
    
    // レジスタ設定リセット
    ADC_CS_LOW();
    spi_transfer(FAST_CMD_RESET); 
    ADC_CS_HIGH();
    _delay_ms(10);

    // レジスタ設定
    adc_write_reg(0x01, 0xB2); // CONFIG0
    adc_write_reg(0x02, 0x0C); // CONFIG1: OSR=1024
    adc_write_reg(0x03, 0x8B); // CONFIG2: BOOST=1x, GAIN=1x
    adc_write_reg(0x04, 0xC0); // CONFIG3: Continuous mode
    adc_write_reg(0x05, 0x07); // IRQ
    adc_write_reg(0x06, 0x08); // MUX: CH0 - AGND

    // ADC変換開始
    ADC_CS_LOW();
    spi_transfer(FAST_CMD_START); 
    ADC_CS_HIGH();
    _delay_ms(1);
}

int32_t adc_read_data(void) {
    ADC_CS_LOW();
    spi_transfer(CMD_READ(0x00)); // ADCDATAレジスタ(0x00)
    uint8_t b2 = spi_transfer(0x00); 
    uint8_t b1 = spi_transfer(0x00); 
    uint8_t b0 = spi_transfer(0x00); 
    ADC_CS_HIGH();

    int32_t raw = ((int32_t)b2 << 16) | ((int32_t)b1 << 8) | b0;
    if (raw & 0x00800000) {
        raw |= 0xFF000000; // 符号拡張
    }
    return raw;
}