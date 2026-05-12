#include "board.h"
#include <avr/io.h>
#include <avr/interrupt.h>

// タコメータのパルスカウント用
volatile uint16_t fan1_pulses = 0;
volatile uint16_t fan2_pulses = 0;

void board_init(void) {
    // 1. リレー (PC0) の出力設定と初期OFF
    DDRC |= (1 << PC0);
    PORTC &= ~(1 << PC0);

    // 2. ファンPWM (Timer0, PD5/OC0B, PD6/OC0A)
    DDRD |= (1 << PD5) | (1 << PD6);
    // 高速PWMモード, プリスケーラ64 (約976HzのPWM)
    TCCR0A = (1 << COM0A1) | (1 << COM0B1) | (1 << WGM01) | (1 << WGM00);
    TCCR0B = (1 << CS01) | (1 << CS00);
    OCR0A = 255; // FAN1 初期100%
    OCR0B = 255; // FAN2 初期100%

    // 3. ファンタコメータ (INT0/PD2, INT1/PD3)
    // 今回はピンの入力設定とプルアップのみ記述（割り込み実装は省略・簡略化）
    DDRD &= ~((1 << PD2) | (1 << PD3));
    PORTD |= (1 << PD2) | (1 << PD3); 
}

void board_relay_set(uint8_t state) {
    if (state) PORTC |= (1 << PC0);
    else       PORTC &= ~(1 << PC0);
}

void board_fan_set(uint8_t fan1_pwm, uint8_t fan2_pwm) {
    OCR0B = fan1_pwm; // PD5
    OCR0A = fan2_pwm; // PD6
}

uint8_t board_get_fan_rpm(uint8_t fan_ch) {
    // ※実際はタイマーで1秒間のパルスを数えてRPMを計算するが、今回はダミー
    return (fan_ch == 1) ? 120 : 150; 
}