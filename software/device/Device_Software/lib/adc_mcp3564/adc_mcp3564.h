#ifndef ADC_H_
#define ADC_H_
#include <stdint.h>

// ADCの初期化
void adc_init(void);

// レジスタ操作関数
uint8_t adc_read_reg(uint8_t reg);
void adc_write_reg(uint8_t reg, uint8_t value);

// 測定データ取得関数
int32_t adc_read_data(void);

#endif /* ADC_H_ */