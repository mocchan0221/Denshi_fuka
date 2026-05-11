#ifndef ADC_H_
#define ADC_H_

#include <stdint.h>

// ADCの初期化
void adc_init(void);

// 任意のレジスタを読み書きする関数（デバッグ用）
uint8_t adc_read_reg(uint8_t reg);
void adc_write_reg(uint8_t reg, uint8_t value);

// 24bitの生データを読み取る関数
int32_t adc_read_data(void);

#endif /* ADC_H_ */