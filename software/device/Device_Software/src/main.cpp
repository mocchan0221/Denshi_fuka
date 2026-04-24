#include <avr/io.h>
#include <util/delay.h>

int main(void) {
    // PB5(Arduinoの13番ピン)を出力ピンに設定 (データディレクションレジスタ)
    DDRB |= (1 << PB5); 

    while (1) {
        PORTB |= (1 << PB5);  // PB5をHIGHにする
        _delay_ms(1000);
        PORTB &= ~(1 << PB5); // PB5をLOWにする
        _delay_ms(1000);
    }
    return 0;
}