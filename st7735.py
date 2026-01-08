import time
from machine import SPI, Pin

# 명령 상수 (기존과 동일)
SWRESET = 0x01
SLPOUT = 0x11
NORON = 0x13
DISPON = 0x29
CASET = 0x2A
RASET = 0x2B
RAMWR = 0x2C
MADCTL = 0x36
COLMOD = 0x3A

# 색상 상수
BLACK = 0x0000
BLUE = 0x001F
RED = 0xF800
GREEN = 0x07E0
CYAN = 0x07FF
MAGENTA = 0xF81F
YELLOW = 0xFFE0
WHITE = 0xFFFF
PINK = 0xF810

class TFT(object):
    def __init__(self, spi, aDC, aReset, aCS):
        self._spi = spi
        self._dc = aDC
        self._reset = aReset
        self._cs = aCS
        self._cs.value(1)
        self._dc.value(0)
        self._reset.value(1)
        
        # [중요] 오프셋 변수 추가 (여기서 화면 위치를 조절합니다)
        self.colstart = 0 
        self.rowstart = 0

    def _write(self, aData):
        self._spi.write(aData)

    def _writeCmd(self, aCmd):
        self._dc.value(0)
        self._cs.value(0)
        self._write(bytearray([aCmd]))
        self._cs.value(1)

    def _writeData(self, aData):
        self._dc.value(1)
        self._cs.value(0)
        self._write(bytearray([aData]))
        self._cs.value(1)

    def _writeBlock(self, aData):
        self._dc.value(1)
        self._cs.value(0)
        self._write(aData)
        self._cs.value(1)

    def initr(self):
        self._reset.value(0)
        time.sleep_ms(50)
        self._reset.value(1)
        time.sleep_ms(50)
        
        self._writeCmd(SWRESET)
        time.sleep_ms(150)
        self._writeCmd(SLPOUT)
        time.sleep_ms(255)
        
        # 색상 모드 (16bit)
        self._writeCmd(COLMOD)
        self._writeData(0x05)
        
        # 화면 방향 초기 설정
        self._writeCmd(MADCTL)
        self._writeData(0xC0) # 기본값

        self._writeCmd(NORON)
        time.sleep_ms(10)
        self._writeCmd(DISPON)
        time.sleep_ms(100)

    # [중요] 오프셋이 적용되도록 수정된 함수
    def _set_window(self, x0, y0, x1, y1):
        # x와 y에 오프셋(colstart, rowstart)을 더해서 보정함
        x0 += self.colstart
        x1 += self.colstart
        y0 += self.rowstart
        y1 += self.rowstart
        
        self._writeCmd(CASET)
        self._writeData(x0 >> 8)
        self._writeData(x0 & 0xFF)
        self._writeData(x1 >> 8)
        self._writeData(x1 & 0xFF)
        self._writeCmd(RASET)
        self._writeData(y0 >> 8)
        self._writeData(y0 & 0xFF)
        self._writeData(y1 >> 8)
        self._writeData(y1 & 0xFF)
        self._writeCmd(RAMWR)

    def fill(self, color):
        # 128x160 전체 채우기
        self.fillrect(0, 0, 128, 160, color)

    def fillrect(self, x, y, w, h, color):
        # 화면 범위를 벗어나지 않게 클리핑
        if x >= 128 or y >= 160: return
        if x + w > 128: w = 128 - x
        if y + h > 160: h = 160 - y
        
        self._set_window(x, y, x + w - 1, y + h - 1)
        
        high = color >> 8
        low = color & 0xFF
        
        # 메모리 부족 방지를 위한 분할 전송
        pixel_count = w * h
        chunk_size = 1024
        buffer = bytearray([high, low] * chunk_size)
        
        for i in range(0, pixel_count, chunk_size):
            pixels = min(chunk_size, pixel_count - i)
            if pixels < chunk_size:
                self._writeBlock(bytearray([high, low] * pixels))
            else:
                self._writeBlock(buffer)
                
    def fillcircle(self, x, y, r, color):
        for i in range(y - r, y + r + 1):
            for j in range(x - r, x + r + 1):
                if (j - x) ** 2 + (i - y) ** 2 <= r ** 2:
                    self.pixel(j, i, color)

    def pixel(self, x, y, color):
        if 0 <= x < 128 and 0 <= y < 160:
            self._set_window(x, y, x, y)
            self._writeData(color >> 8)
            self._writeData(color & 0xFF)
            
    def rotation(self, m):
        self._writeCmd(MADCTL)
        # 회전 모드에 따라 값 설정
        if m == 0: self._writeData(0xC0)
        elif m == 1: self._writeData(0xA0)
        elif m == 2: self._writeData(0x00)
        elif m == 3: self._writeData(0x60)
        
    def rgb(self, enable):
        pass