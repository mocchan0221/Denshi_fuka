#ifndef BOARD_H_
#define BOARD_H_

#include <stdint.h>

// ハードウェアの初期化 (リレー、ファンPWM、タコメータ割り込み等)
void board_init(void);

// リレーの制御 (1: ON, 0: OFF)
void board_relay_set(uint8_t state);

// ファンのPWM出力設定 (0: 停止, 255: 全開)
void board_fan_set(uint8_t fan1_pwm, uint8_t fan2_pwm);

// ファンの回転数(RPM)を取得する (1 or 2)
uint8_t board_get_fan_rpm(uint8_t fan_ch);

#endif /* BOARD_H_ */