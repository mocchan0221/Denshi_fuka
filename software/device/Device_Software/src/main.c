#ifndef F_CPU
#define F_CPU 16000000UL 
#endif

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include "uart.h"
#include "spi.h"
#include "dac_mcp4822.h"
#include "adc_mcp3564.h"
#include "board.h"

// --- システム状態とモード ---
#define SYS_STATE_IDLE    0  
#define SYS_STATE_STANDBY 1  
#define SYS_STATE_STREAM  2  

#define MODE_CH1 0x01
#define MODE_CH2 0x02

volatile uint8_t sys_state = SYS_STATE_IDLE;
volatile uint8_t active_mode = MODE_CH1; // PCからの指示で切り替わる

// 計測データバッファ (常に最新値が入る)
volatile int16_t current_I = 0, current_V = 0;
volatile uint8_t  current_T1 = 0, current_T2 = 0;

volatile uint8_t taskflag_50us = 0;

// タイマー初期化 (50µs周期 = 20000Hz)
void timer1_init(void) {
    TCCR1B = (1 << WGM12) | (1 << CS11); // プリスケーラ8 (1count=0.5µs)
    OCR1A = 99; // 100カウント = 50µs
    TIMSK1 = (1 << OCIE1A);
}

ISR(TIMER1_COMPA_vect) {
    taskflag_50us = 1;
}

// 8バイトパケット送信関数
void send_packet_8b(uint8_t mode, uint8_t d1, uint8_t d2, uint8_t d3, uint8_t d4) {
    uint8_t cs = mode ^ d1 ^ d2 ^ d3 ^ d4;
    uart_putchar_async(0xAA);
    uart_putchar_async(0x55);
    uart_putchar_async(mode);
    uart_putchar_async(d1);
    uart_putchar_async(d2);
    uart_putchar_async(d3);
    uart_putchar_async(d4);
    uart_putchar_async(cs);
}

int main(void) {
    DDRC |= (1 << PC1);
    PORTC &= ~(1 << PC1);
    
    cli();
    uart_init();
    spi_init();
    board_init();
    timer1_init();
    sei();

    uint16_t target_dac1 = 0;
    uint16_t target_dac2 = 0;

    // ラウンドロビンと待機用のステート
    uint8_t seq_idx = 0;
    uint8_t adc_wait_ticks = 0; 
    uint16_t slow_tick = 0;
    uint16_t tx_tick = 0;

    // 受信バッファ用
    uint8_t rx_state = 0;
    uint8_t cmd_buf[6];

    while (1) {
        uart_tx_task();
        
        // ==========================================
        // ADCスキャンタスク (50µs毎)
        // ==========================================
        if (taskflag_50us) {
            taskflag_50us = 0;

            if (sys_state >= SYS_STATE_STANDBY) {
                // 待機中（OSRを上げた時など）はスキップ
                if (adc_wait_ticks > 0) {
                    adc_wait_ticks--;
                } 
                else {
                    int32_t adc_raw = adc_read_data();
                    uint8_t next_mux = 0x00;

                    // --- 動的スキャンリスト ---
                    // 1回のループ(seq_idx)で: I -> V -> I -> V -> I -> V -> T(ボードモニタ)
                    
                    if (seq_idx % 2 == 0 && seq_idx < 6) {
                        // 電流の回収
                        current_I = (adc_raw >> 8) & 0xFFFF;
                        // 次は電圧
                        next_mux = (active_mode == MODE_CH1) ? 0x2C : 0x3C; // V1(CH2-AGND) or V2(CH3-AGND)
                    } 
                    else if (seq_idx % 2 == 1 && seq_idx < 6) {
                        // 電圧の回収
                        current_V = (adc_raw >> 8) & 0xFFFF;
                        // 次は電流
                        next_mux = (active_mode == MODE_CH1) ? 0x01 : 0x45; // I1(CH0-CH1) or I2(CH4-CH5)
                    }
                    else if (seq_idx == 6) {
                        // T1の回収
                        current_T1 = (adc_raw >> 16) & 0xFF;
                        // 次はT2
                        next_mux = 0x6C; // T2(CH6-AGND)
                    }
                    else if (seq_idx == 7) {
                        // T2の回収
                        current_T2 = (adc_raw >> 16) & 0xFF;
                        // 次は電流に戻る
                        next_mux = (active_mode == MODE_CH1) ? 0x01 : 0x45; 
                    }

                    // --- 動的OSRの制御 ---
                    if (seq_idx == 5) { // 次からサーミスタを読む時
                        adc_write_reg(0x02, 0x0E); // OSRを1024に上げる
                        adc_wait_ticks = 4; // 変換に200µs以上かかるので4回(200µs)スキップする
                    } 
                    else if (seq_idx == 7) { // サーミスタが終わり、電流・電圧に戻る時
                        adc_write_reg(0x02, 0x0C); // OSRを256に下げる (超高速化)
                        adc_wait_ticks = 1; // 変換に約50µsかかるので1回スキップ
                    } 
                    else {
                        adc_wait_ticks = 1; // 通常(OSR=256)の変換待ち
                    }

                    adc_write_reg(0x06, next_mux); // MUXの切り替え指示

                    seq_idx++;
                    if (seq_idx >= 8) seq_idx = 0;
                }

                // --- 送信タスク ---
                tx_tick++;
                // 高速モード時: 1ms周期(1000Hz) で現在のモードのデータを送信
                if (sys_state == SYS_STATE_STREAM && tx_tick >= 20) { 
                    tx_tick = 0;
                    send_packet_8b(active_mode, current_I >> 8, current_I & 0xFF, current_V >> 8, current_V & 0xFF);
                }
                
                // ボードモニタ送信: 高速/低速問わず、約1秒に1回送信
                slow_tick++;
                if (slow_tick >= 20000) { 
                    slow_tick = 0;
                    uint8_t f1 = board_get_fan_rpm(1);
                    uint8_t f2 = board_get_fan_rpm(2);
                    send_packet_8b(0x03, current_T1, current_T2, f1, f2);
                }
            }
        }

        // ==========================================
        // PCコマンド受信 (6Byte)
        // ==========================================
        while (uart_available()) {
            uint8_t data = uart_read();

            if (rx_state == 0 && data == 0xAA) { rx_state = 1; cmd_buf[0] = data; }
            else if (rx_state == 1 && data == 0x55) { rx_state = 2; cmd_buf[1] = data; }
            else if (rx_state >= 2) {
                cmd_buf[rx_state] = data;
                rx_state++;
                
                if (rx_state == 6) { 
                    rx_state = 0; 
                    
                    if ((cmd_buf[2] ^ cmd_buf[3] ^ cmd_buf[4]) == cmd_buf[5]) {
                        uint8_t cmd = cmd_buf[2];
                        
                        // DAC A設定
                        if (cmd == 0x01 && sys_state == SYS_STATE_STREAM) {
                            target_dac1 = ((uint16_t)cmd_buf[3] << 8) | cmd_buf[4];
                            dac_write(DAC_CH_A, target_dac1);
                        }
                        // DAC B設定
                        else if (cmd == 0x02 && sys_state == SYS_STATE_STREAM) {
                            target_dac2 = ((uint16_t)cmd_buf[3] << 8) | cmd_buf[4];
                            dac_write(DAC_CH_B, target_dac2);
                        }
                        // ファン設定 (これはいつでも許可)
                        else if (cmd == 0x03) {
                            board_fan_set(cmd_buf[3], cmd_buf[4]);
                        }
                        // システム制御コマンド
                        else if (cmd == 0x04) {
                            uint8_t new_state = cmd_buf[3];
                            
                            // IDLE -> STANDBY への移行 (リレーON、ADC初期化)
                            if (new_state == SYS_STATE_STANDBY && sys_state == SYS_STATE_IDLE) {
                                board_relay_set(1);
                                _delay_ms(100); // 電圧安定待ち
                                dac_init();
                                adc_init();
                                sys_state = SYS_STATE_STANDBY;
                            }
                            // STANDBY -> STREAM への移行
                            else if (new_state == SYS_STATE_STREAM && sys_state == SYS_STATE_STANDBY) {
                                sys_state = SYS_STATE_STREAM;
                            }
                            // 強制終了/安全停止 (リレーOFF、DAC目標値0)
                            else if (new_state == SYS_STATE_IDLE) {
                                dac_write(DAC_CH_A, 0); 
                                dac_write(DAC_CH_B, 0);
                                target_dac1 = 0; target_dac2 = 0;
                                _delay_ms(1);
                                board_relay_set(0);
                                sys_state = SYS_STATE_IDLE;
                            }
                        }
                    }
                }
            } else {
                rx_state = 0; 
            }
        }
    }
}