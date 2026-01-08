from machine import Pin, SPI
import time
import math
import random

# ==========================================
# 1. TFT 드라이버 (변경 없음)
# ==========================================
class TFT(object):
    def __init__(self, spi, aDC, aReset, aCS):
        self._spi = spi
        self._dc = aDC
        self._reset = aReset
        self._cs = aCS
        self._cs.value(1)
        self._dc.value(0)
        self._reset.value(1)
        self.width_limit = 160 
        self.height_limit = 132
        self.colstart = 0 
        self.rowstart = 0

    def _write(self, aData):
        self._spi.write(aData)
    def _writeCmd(self, aCmd):
        self._dc.value(0); self._cs.value(0); self._write(bytearray([aCmd])); self._cs.value(1)
    def _writeData(self, aData):
        self._dc.value(1); self._cs.value(0); self._write(bytearray([aData])); self._cs.value(1)
    def _writeBlock(self, aData):
        self._dc.value(1); self._cs.value(0); self._write(aData); self._cs.value(1)
    def initr(self):
        self._reset.value(0); time.sleep_ms(50)
        self._reset.value(1); time.sleep_ms(50)
        self._writeCmd(0x01); time.sleep_ms(150)
        self._writeCmd(0x11); time.sleep_ms(255)
        self._writeCmd(0x3A); self._writeData(0x05)
        self._writeCmd(0x36); self._writeData(0xC0)
        self._writeCmd(0x13); time.sleep_ms(10)
        self._writeCmd(0x29); time.sleep_ms(100)
    def _set_window(self, x0, y0, x1, y1):
        x0+=self.colstart; x1+=self.colstart; y0+=self.rowstart; y1+=self.rowstart
        self._writeCmd(0x2A); self._writeData(x0>>8); self._writeData(x0&0xFF); self._writeData(x1>>8); self._writeData(x1&0xFF)
        self._writeCmd(0x2B); self._writeData(y0>>8); self._writeData(y0&0xFF); self._writeData(y1>>8); self._writeData(y1&0xFF)
        self._writeCmd(0x2C)
    def fillrect(self, x, y, w, h, color):
        if x>=self.width_limit or y>=self.height_limit: return
        if x+w>self.width_limit: w=self.width_limit-x
        if y+h>self.height_limit: h=self.height_limit-y
        self._set_window(x, y, x+w-1, y+h-1)
        high=color>>8; low=color&0xFF
        chunk=1024; buffer=bytearray([high, low]*chunk); total=w*h
        for i in range(0, total, chunk):
            p=min(chunk, total-i)
            if p<chunk: self._writeBlock(bytearray([high, low]*p))
            else: self._writeBlock(buffer)
    def fill(self, color): self.fillrect(0, 0, self.width_limit, self.height_limit, color)
    def rotation(self, m):
        self._writeCmd(0x36)
        if m==1: self._writeData(0xA0); self.width_limit=160; self.height_limit=132

# ==========================================
# 2. 하드웨어 설정 (핀 매핑 수정됨)
# ==========================================
spi = SPI(2, baudrate=40000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
dc_pin = Pin(2, Pin.OUT)
reset_pin = Pin(4, Pin.OUT)
cs_pin = Pin(5, Pin.OUT)

tft = TFT(spi, dc_pin, reset_pin, cs_pin)
tft.initr()
tft.rotation(1)

# [수정됨] 핀 번호를 변수명으로 사용하여 헷갈리지 않게 정의
btn_27 = Pin(27, Pin.IN, Pin.PULL_UP) # 메인:위 / 버블:오른쪽
btn_14 = Pin(14, Pin.IN, Pin.PULL_UP) # 메인:아래 / 버블:왼쪽
btn_12 = Pin(12, Pin.IN, Pin.PULL_UP) # 메인:선택 / 미로:나가기 / 버블:발사

btn_32 = Pin(32, Pin.IN, Pin.PULL_UP) # 미로:위 / 버블:나가기
btn_33 = Pin(33, Pin.IN, Pin.PULL_UP) # 미로:왼쪽
btn_25 = Pin(25, Pin.IN, Pin.PULL_UP) # 미로:오른쪽
btn_26 = Pin(26, Pin.IN, Pin.PULL_UP) # 미로:아래

# 색상 정의
BLACK   = 0x0000
BLUE    = 0x001F
RED     = 0xF800
GREEN   = 0x07E0
CYAN    = 0x07FF
MAGENTA = 0xF81F
YELLOW  = 0xFFE0
WHITE   = 0xFFFF
GRAY    = 0x8410

COLORS = [RED, GREEN, BLUE, YELLOW, MAGENTA, CYAN]

# ==========================================
# 3. 게임 1: 미로 찾기 (버튼 로직 수정됨)
# ==========================================
TILE_SIZE = 11
MAP_W = 14
MAP_H = 11

MAP_LEVEL_1 = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
    [1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1],
    [1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
    [1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1],
    [1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]
MAP_LEVEL_2 = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 3, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]
MAP_LEVEL_3 = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 3, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1],
    [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1],
    [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]
ALL_LEVELS = [MAP_LEVEL_1, MAP_LEVEL_2, MAP_LEVEL_3]

def draw_maze_map(current_map):
    tft.fill(BLACK)
    for y in range(MAP_H):
        for x in range(MAP_W):
            tile = current_map[y][x]
            px = x * TILE_SIZE
            py = y * TILE_SIZE
            if tile == 1:
                tft.fillrect(px, py, TILE_SIZE, TILE_SIZE, GRAY)
                tft.fillrect(px+1, py+1, TILE_SIZE-2, TILE_SIZE-2, 0xC618)
            elif tile == 2:
                tft.fillrect(px, py, TILE_SIZE, TILE_SIZE, BLUE)
            elif tile == 3:
                tft.fillrect(px, py, TILE_SIZE, TILE_SIZE, GREEN)

def run_maze_game():
    current_level = 0
    max_level = len(ALL_LEVELS)
    
    while current_level < max_level:
        current_map = ALL_LEVELS[current_level]
        draw_maze_map(current_map)
        
        # 시작 위치 찾기
        start_x, start_y = 10, 10
        for y in range(MAP_H):
            for x in range(MAP_W):
                if current_map[y][x] == 2:
                    start_x = x * TILE_SIZE + 2
                    start_y = y * TILE_SIZE + 2
        
        px, py = start_x, start_y
        pw, ph = 7, 7
        tft.fillrect(px, py, pw, ph, WHITE)
        
        level_cleared = False
        
        while not level_cleared:
            # [기능 추가] 12번 누르면 메인으로 복귀
            if btn_12.value() == 0:
                return

            dx, dy = 0, 0
            speed = 2
            
            # [수정됨] 미로 게임 키 매핑
            # 32:위, 33:왼쪽, 25:오른쪽, 26:아래
            if btn_32.value() == 0: dy = -speed # 위
            if btn_26.value() == 0: dy = speed  # 아래
            if btn_33.value() == 0: dx = -speed # 왼쪽
            if btn_25.value() == 0: dx = speed  # 오른쪽
            
            if dx == 0 and dy == 0:
                time.sleep(0.01)
                continue

            new_x = px + dx
            new_y = py + dy
            
            if new_x < 0: new_x = 0
            if new_x > 160 - pw: new_x = 160 - pw 
            if new_y < 0: new_y = 0
            if new_y > 132 - ph: new_y = 132 - ph
            
            hit_wall = False
            reached_goal = False
            corners = [(new_x, new_y), (new_x+pw-1, new_y), (new_x, new_y+ph-1), (new_x+pw-1, new_y+ph-1)]
            
            for cx, cy in corners:
                tx = int(cx // TILE_SIZE)
                ty = int(cy // TILE_SIZE)
                if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                    tile = current_map[ty][tx]
                    if tile == 1: hit_wall = True
                    elif tile == 3: reached_goal = True
            
            if hit_wall:
                for _ in range(3):
                    tft.fillrect(px, py, pw, ph, RED)
                    time.sleep(0.05)
                    tft.fillrect(px, py, pw, ph, BLACK)
                    time.sleep(0.05)
                
                tft.fillrect(px, py, pw, ph, BLACK)
                px, py = start_x, start_y
                tft.fillrect(px, py, pw, ph, WHITE)
                time.sleep(0.3)
                continue 
                
            if reached_goal:
                level_cleared = True
                tft.fill(GREEN)
                time.sleep(0.5)
                break
                
            if new_x != px or new_y != py:
                tft.fillrect(px, py, pw, ph, BLACK)
                sx, sy = start_x, start_y
                if abs(px - sx) < 11 and abs(py - sy) < 11:
                      tft.fillrect(int(sx//TILE_SIZE)*TILE_SIZE, int(sy//TILE_SIZE)*TILE_SIZE, TILE_SIZE, TILE_SIZE, BLUE)
                
                px, py = new_x, new_y
                tft.fillrect(px, py, pw, ph, WHITE)
            
            time.sleep(0.02)
            
        current_level += 1
        
    tft.fill(BLACK)
    for _ in range(3):
        tft.fill(YELLOW); time.sleep(0.2)
        tft.fill(RED); time.sleep(0.2)
    return

# ==========================================
# 4. 게임 2: 버블 슈터 (버튼 로직 수정됨)
# ==========================================
GRID_RADIUS = 7             
GRID_DIA = GRID_RADIUS * 2
DRAW_RADIUS = 5             
COLS = 160 // GRID_DIA  
ROWS = 15
ROW_HEIGHT = int(GRID_DIA * 0.90) 
bubble_grid = []

def draw_circle(x, y, r, color):
    tft.fillrect(int(x-r+2), int(y-r), int(2*r-4), int(2*r), color)
    tft.fillrect(int(x-r), int(y-r+2), int(2*r), int(2*r-4), color)
    if color != BLACK:
        tft.fillrect(int(x-r/2), int(y-r/2), 2, 2, WHITE)

def get_bubble_coords(r, c):
    y = r * ROW_HEIGHT + GRID_RADIUS + 2 
    offset = GRID_RADIUS if r % 2 == 1 else 0
    x = c * GRID_DIA + GRID_RADIUS + offset + 2
    return int(x), int(y)

def check_matches(grid, r, c, color, visited):
    if (r, c) in visited: return []
    if r < 0 or r >= ROWS or c < 0 or c >= COLS: return []
    if grid[r][c] != color: return []
    
    visited.add((r, c))
    matches = [(r, c)]
    directions = [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]
    for dr, dc in directions:
        matches += check_matches(grid, r+dr, c+dc, color, visited)
    return matches

def count_bubbles(grid):
    cnt = 0
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] != 0: cnt += 1
    return cnt

def run_bubble_game():
    global bubble_grid
    bubble_grid = [[0] * COLS for _ in range(ROWS)]
    for r in range(4):
        for c in range(COLS):
            bubble_grid[r][c] = random.choice(COLORS)
            
    shooter_angle = 90
    shooter_color = random.choice(COLORS)
    next_color = random.choice(COLORS)
    shooter_x = 80
    shooter_y = 125
    
    tft.fill(BLACK)
    for r in range(ROWS):
        for c in range(COLS):
            if bubble_grid[r][c] != 0:
                gx, gy = get_bubble_coords(r, c)
                draw_circle(gx, gy, DRAW_RADIUS, bubble_grid[r][c])
                
    playing = True
    while playing:
        # [수정됨] 32번: 메인으로 돌아가기
        if btn_32.value() == 0:
            return

        rad = math.radians(shooter_angle)
        tft.fillrect(0, 105, 160, 27, BLACK)
        
        for i in range(5, 20, 2):
            px = shooter_x + math.cos(rad) * i
            py = shooter_y - math.sin(rad) * i
            tft.fillrect(int(px), int(py), 2, 2, WHITE)
            
        draw_circle(shooter_x, shooter_y, DRAW_RADIUS, shooter_color)
        draw_circle(10, 125, 4, next_color)
        
        fired = False
        while not fired:
            # [수정됨] 버블 게임 키 매핑
            # 27:오른쪽(각도감소), 14:왼쪽(각도증가), 12:발사, 32:나가기
            
            if btn_32.value() == 0: # 대기 중 나가기
                return

            if btn_14.value() == 0: # 왼쪽으로 이동 (각도 증가)
                if shooter_angle < 160: shooter_angle += 5
                break
            if btn_27.value() == 0: # 오른쪽으로 이동 (각도 감소)
                if shooter_angle > 20: shooter_angle -= 5
                break
            if btn_12.value() == 0: # 발사
                fired = True
                while btn_12.value() == 0: time.sleep(0.01)
            time.sleep(0.04)
        
        if not fired:
            continue
            
        bx, by = shooter_x, shooter_y
        dx = math.cos(rad) * 12
        dy = -math.sin(rad) * 12
        moving = True
        
        while moving:
            draw_circle(bx, by, DRAW_RADIUS, BLACK)
            bx += dx
            by += dy
            
            if bx <= GRID_RADIUS or bx >= 160 - GRID_RADIUS:
                dx = -dx; bx += dx
            if by <= GRID_RADIUS: moving = False
            
            for r in range(ROWS):
                gx_dummy, gy = get_bubble_coords(r, 0)
                if abs(gy - by) > GRID_DIA: continue
                for c in range(COLS):
                    if bubble_grid[r][c] != 0:
                        gx, gy = get_bubble_coords(r, c)
                        if math.sqrt((bx-gx)**2 + (by-gy)**2) < GRID_DIA - 1:
                            moving = False
            
            if moving: draw_circle(bx, by, DRAW_RADIUS, shooter_color)
            else: draw_circle(bx, by, DRAW_RADIUS, BLACK)
            
            time.sleep(0.01)
            
        best_dist = 9999
        best_r, best_c = -1, -1
        for r in range(ROWS):
            for c in range(COLS):
                if bubble_grid[r][c] == 0:
                    gx, gy = get_bubble_coords(r, c)
                    dist = math.sqrt((bx-gx)**2 + (by-gy)**2)
                    if dist < best_dist:
                        best_dist = dist; best_r = r; best_c = c
                        
        if best_r != -1 and best_dist < GRID_DIA * 1.5:
            bubble_grid[best_r][best_c] = shooter_color
            
            matches = check_matches(bubble_grid, best_r, best_c, shooter_color, set())
            if len(matches) >= 3:
                for r, c in matches:
                    bubble_grid[r][c] = 0
                    gx, gy = get_bubble_coords(r, c)
                    draw_circle(gx, gy, DRAW_RADIUS, BLACK)
                for r, c in matches:
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                        nr, nc = r+dr, c+dc
                        if 0<=nr<ROWS and 0<=nc<COLS and bubble_grid[nr][nc]!=0:
                            gx, gy = get_bubble_coords(nr, nc)
                            draw_circle(gx, gy, DRAW_RADIUS, bubble_grid[nr][nc])
            else:
                gx, gy = get_bubble_coords(best_r, best_c)
                draw_circle(gx, gy, DRAW_RADIUS, shooter_color)
                
            shooter_color = next_color
            next_color = random.choice(COLORS)
            
            if count_bubbles(bubble_grid) == 0:
                tft.fill(BLACK)
                for _ in range(3):
                    tft.fill(GREEN); time.sleep(0.2)
                    tft.fill(BLUE); time.sleep(0.2)
                return 

# ==========================================
# 5. 메인 메뉴 시스템 (버튼 로직 수정됨)
# ==========================================
def draw_menu_ui(selected_idx):
    tft.fill(BLACK)
    
    color1 = YELLOW if selected_idx == 0 else GRAY
    tft.fillrect(40, 20, 80, 40, color1)
    tft.fillrect(42, 22, 76, 36, BLACK)
    tft.fillrect(50, 30, 60, 5, BLUE)
    tft.fillrect(50, 45, 60, 5, BLUE)
    tft.fillrect(50, 30, 5, 20, BLUE)
    tft.fillrect(105, 30, 5, 20, BLUE)
    tft.fillrect(20, 30, 5, 20, WHITE) 

    color2 = YELLOW if selected_idx == 1 else GRAY
    tft.fillrect(40, 70, 80, 40, color2)
    tft.fillrect(42, 72, 76, 36, BLACK)
    draw_circle(60, 90, 6, RED)
    draw_circle(75, 90, 6, GREEN)
    draw_circle(90, 90, 6, BLUE)
    draw_circle(67, 80, 6, YELLOW)
    draw_circle(82, 80, 6, MAGENTA)
    tft.fillrect(20, 75, 15, 5, WHITE)
    tft.fillrect(30, 75, 5, 10, WHITE)
    tft.fillrect(20, 85, 15, 5, WHITE)
    tft.fillrect(20, 85, 5, 10, WHITE)
    tft.fillrect(20, 95, 15, 5, WHITE)

def main_system():
    selected = 0 
    draw_menu_ui(selected)
    
    while True:
        # [수정됨] 메인 메뉴 키 매핑
        # 27:위, 14:아래, 12:선택
        
        if btn_27.value() == 0: # 위로 이동
            if selected == 1:
                selected = 0
                draw_menu_ui(selected)
            time.sleep(0.15)
            
        elif btn_14.value() == 0: # 아래로 이동
            if selected == 0:
                selected = 1
                draw_menu_ui(selected)
            time.sleep(0.15)
            
        elif btn_12.value() == 0: # 선택
            if selected == 0:
                run_maze_game()
            else:
                run_bubble_game()
            
            draw_menu_ui(selected)
            while btn_12.value() == 0: time.sleep(0.01)
            
        time.sleep(0.05)

main_system()