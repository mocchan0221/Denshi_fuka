#ifndef SPI_H_
#define SPI_H_
#include <stdint.h>

// 初期化 (Master, 4MHz)
void spi_init(void);

// データ送受信
uint8_t spi_transfer(uint8_t data);

#endif