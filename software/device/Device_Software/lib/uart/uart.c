#include "uart.h"
#include <avr/io.h>
#include <avr/interrupt.h>

// 16MHz/(8*nMbps)-1
#define UBRR_SET 1

// UART送受信データ用リングバッファ
volatile uint8_t rx_buffer[256];
volatile uint8_t rx_head = 0;
volatile uint8_t rx_tail = 0;

volatile uint8_t tx_buffer[256];
volatile uint8_t tx_head = 0;
volatile uint8_t tx_tail = 0;

void uart_init(void) {
    // Boud Rate設定
    UBRR0H = (UBRR_SET >> 8);
    UBRR0L = UBRR_SET;
    
    // 倍速モード
    UCSR0A = (1 << U2X0); 

    // モード設定
    UCSR0B = (1 << TXEN0) | (1 << RXEN0) | (1 << RXCIE0);
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
}

// UART受信割り込み
ISR(USART_RX_vect) {
    // 受信バッファへの格納処理
    uint8_t data = UDR0;
    rx_buffer[rx_head] = data;
    rx_head++;
}

// 受信バッファ確認
uint8_t uart_available(void) {
    return (uint8_t)(rx_head - rx_tail);
}

// 受信バッファ読み出し
uint8_t uart_read(void) {
    if (rx_head == rx_tail) return 0;
    uint8_t data = rx_buffer[rx_tail];
    rx_tail++;
    return data;
}

// 送信バッファに追加
void uart_putchar_async(uint8_t c) {
    tx_buffer[tx_head] = c;
    tx_head++;
}

// 送信処理ワーカー
void uart_tx_task(void) {
    // 送信バッファにデータがあり、かつハードウェアの送信枠(UDRE0)が空いていれば1バイト送る
    if ((tx_head != tx_tail) && (UCSR0A & (1 << UDRE0))) {
        UDR0 = tx_buffer[tx_tail];
        tx_tail++;
    }
}