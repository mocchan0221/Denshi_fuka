import struct

class Protocol:
    HEADER = b'\xAA\x55'
    
    # CMD (PC -> Device)
    CMD_DAC_A = 0x01
    CMD_DAC_B = 0x02
    CMD_FAN   = 0x03
    CMD_SYS   = 0x04

    # MODE (Device -> PC)
    MODE_CH1_DATA  = 0x01
    MODE_CH2_DATA  = 0x02
    MODE_MONITOR   = 0x03

    @staticmethod
    def calculate_checksum(payload: bytes) -> int:
        """Payload (CMD/MODE + DATA) の XOR チェックサムを計算"""
        cs = 0
        for b in payload:
            cs ^= b
        return cs

    @classmethod
    def create_command_packet(cls, cmd: int, d1: int, d2: int) -> bytes:
        """CMDパケット(6バイト)を作成: [0xAA, 0x55, CMD, DATA1, DATA2, CS]"""
        body = struct.pack('BBB', cmd, d1, d2)
        cs = cls.calculate_checksum(body)
        return cls.HEADER + body + struct.pack('B', cs)

    @classmethod
    def parse_telemetry_packet(cls, packet: bytes) -> dict:
        """
        テレメトリパケット(8バイト)を解析。
        packet: HEADER(2) + BODY(5) + CS(1) の計8バイト
        """
        if len(packet) != 8:
            return None
            
        body = packet[2:7]
        received_cs = packet[7]
        
        if cls.calculate_checksum(body) != received_cs:
            return None # チェックサム不一致
            
        mode = body[0]
        data = body[1:] # 4 bytes
        
        result = {'mode': mode}
        
        if mode == cls.MODE_CH1_DATA or mode == cls.MODE_CH2_DATA:
            # 符号付き16bit整数 (Big Endian) x 2
            val1, val2 = struct.unpack('>hh', data)
            result.update({'val1': val1, 'val2': val2})
        elif mode == cls.MODE_MONITOR:
            # 8bit整数 x 4
            t1, t2, f1, f2 = struct.unpack('BBBB', data)
            result.update({'temp1': t1, 'temp2': t2, 'fan1_rpm': f1, 'fan2_rpm': f2})
            
        return result
