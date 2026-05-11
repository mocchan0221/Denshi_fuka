#ifndef F_CPU
#define F_CPU 16000000UL 
#endif

#include <avr/io.h>
#include <util/delay.h>
#include <stdio.h>
#include "uart.h"
#include "spi.h"
#include "dac_mcp4822.h"
#include "adc_mcp3564.h"

int main(void) {
    uart_init();
    spi_init();
    
    uart_print("\r\n--- Booting MCP3564 ---\r\n");

    // 初期化と書き込み実行
    adc_init(); 

    // 書き込んだ設定(0x32 または 0xB2)が反映されたか確認
    uint8_t conf0 = adc_read_reg(0x01);
    char msgBuf[64];
    sprintf(msgBuf, "CONFIG0 Read: 0x%02X\r\n", conf0);
    uart_print(msgBuf);

    if (conf0 == 0x33 || conf0 == 0xB3) {
        uart_print("SUCCESS: ADC is PERFECTLY initialized!\r\n");
    } else {
        uart_print("WARNING: Config mismatch.\r\n");
    }

    uart_print("Press 'S' to start reading data...\r\n");
    while (uart_getchar() != 'S'); 

    while (1) {
        // データ取得
        int32_t adc_val = adc_read_data();
        
        sprintf(msgBuf, "ADC Raw: %ld\r\n", adc_val);
        uart_print(msgBuf);
        
        _delay_ms(100); 
    }
    return 0;
}