#ifndef UART_H_
#define UART_H_
#include <stdint.h>

void uart_init(void);

void uart_putchar_async(uint8_t c);

uint8_t uart_available(void);

uint8_t uart_read(void);

void uart_tx_task(void);

#endif