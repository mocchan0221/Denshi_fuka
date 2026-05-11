#ifndef UART_H_
#define UART_H_

#include <avr/io.h>

// UART初期化
void uart_init(void);

// 1文字送信
void uart_putchar(char c);

// 文字列送信
void uart_print(const char* str);

// 1文字受信 (受信するまで待機)
char uart_getchar(void);

#endif /* UART_H_ */