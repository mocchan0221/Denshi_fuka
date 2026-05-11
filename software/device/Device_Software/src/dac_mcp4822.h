#ifndef DAC_H_
#define DAC_H_

#include <stdint.h>

#define DAC_CH_A 0
#define DAC_CH_B 1

void dac_init(void);

void dac_write(uint8_t channel, uint16_t value);

#endif /* DAC_H_ */