#ifndef SPI_H_
#define SPI_H_

#include <avr/io.h>
#include <stdint.h>

// SPIを初期化する (Masterモード, 4MHz)
void spi_init(void);

// 1バイトのデータを送信し、同時に受信したデータを返す
uint8_t spi_transfer(uint8_t data);

#endif /* SPI_H_ */