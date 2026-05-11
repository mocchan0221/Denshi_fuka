#include "uart.h"

// 16MHzで115200bps設定時のUBRR値 (倍速モード時)
#define UBRR_115200 16

void uart_init(void) {
    // 1. ボーレートの設定
    UCSR0A = (1 << U2X0); // 倍速モード有効
    UBRR0H = (UBRR_115200 >> 8);
    UBRR0L = UBRR_115200;

    // 2. 送信(TX)と受信(RX)の有効化
    UCSR0B = (1 << TXEN0) | (1 << RXEN0);

    // 3. フレームフォーマット設定 (8データビット, 1ストップビット)
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
}

void uart_putchar(char c) {
    // 送信バッファ(UDRE0)が空になるまで待機
    while (!(UCSR0A & (1 << UDRE0))) {
        // 待機
    }
    UDR0 = c;
}

void uart_print(const char* str) {
    while (*str) {
        uart_putchar(*str++);
    }
}

char uart_getchar(void) {
    // 受信完了フラグ(RXC0)が立つまで待機
    while (!(UCSR0A & (1 << RXC0))) {
        // 待機
    }
    return UDR0;
}