import pygame
import random
import sys
import os
import ctypes
import ctypes.wintypes

# ==================== Windows API 接口定义 ====================
# 用于设置窗口透明
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def set_window_transparent(hwnd):
    """将窗口设置为分层窗口，并启用背景透明"""
    # 1. 设置窗口样式为分层窗口 (WS_EX_LAYERED)
    ex_style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE = -20
    user32.SetWindowLongW(hwnd, -20, ex_style | 0x00080000)  # WS_EX_LAYERED = 0x80000

    # 2. 设置窗口颜色键 (Color Key) 为纯黑色 (0, 0, 0)，黑色部分将变透明
    # LWA_COLORKEY (0x1) = 使用颜色键
    user32.SetLayeredWindowAttributes(hwnd, 0, 255, 0x1)


# 开启硬件渲染加速
os.environ["PYGAME_FORCE_SDL_RENDERER"] = "1"

pygame.init()

# ==================== 屏幕设置 ====================
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

# 创建无边框全屏窗口
screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT),
    pygame.NOFRAME
)
pygame.display.set_caption("透明桌面粒子特效")
clock = pygame.time.Clock()

# 🚀 获取窗口句柄并设置透明
hwnd = pygame.display.get_wm_info()["window"]
set_window_transparent(hwnd)

# ==================== 1. 矩阵代码雨背景引擎 ====================
MATRIX_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz@#$%^&*()_+"
FONT_SIZE = 10
FONT = pygame.font.SysFont("consolas", FONT_SIZE)

COLS = SCREEN_WIDTH // FONT_SIZE
DROPS = [random.randint(-20, 0) for _ in range(COLS)]
SPEEDS = [random.uniform(1.5, 4.0) for _ in range(COLS)]

# 创建一个专门用于画特效的独立表面（不透明）
MATRIX_SURFACE = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
# 初始填满纯黑色，这样背景就全透明了
MATRIX_SURFACE.fill((0, 0, 0))


def draw_matrix():
    # 每次用极淡的黑色覆盖，形成长长的绿色拖尾
    fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    fade.fill((0, 0, 0))
    fade.set_alpha(15)
    MATRIX_SURFACE.blit(fade, (0, 0))

    for col in range(COLS):
        if 0 <= DROPS[col] * FONT_SIZE < SCREEN_HEIGHT:
            if random.random() > 0.3:
                char = random.choice(MATRIX_CHARS)
                green = random.randint(100, 255)
                # 渲染文字（注意：因为背景是黑的且透明，文字必须是非黑色，否则也会被透掉）
                text_surface = FONT.render(char, True, (0, green, 0))
                MATRIX_SURFACE.blit(text_surface, (col * FONT_SIZE, int(DROPS[col]) * FONT_SIZE))

        DROPS[col] += SPEEDS[col]
        if int(DROPS[col]) * FONT_SIZE > SCREEN_HEIGHT:
            DROPS[col] = random.randint(-20, -5)


# ==================== 2. 粒子图处理 ====================
class Particle:
    def __init__(self, x, y, color):
        self.target_x = x
        self.target_y = y
        self.color = color
        self.current_x = random.randint(0, SCREEN_WIDTH)
        self.current_y = random.randint(0, SCREEN_HEIGHT)
        self.speed = random.uniform(0.03, 0.09)

    def update(self):
        self.current_x += (self.target_x - self.current_x) * self.speed
        self.current_y += (self.target_y - self.current_y) * self.speed


def load_image_to_points(image_filename):
    points_data = []
    try:
        img = pygame.image.load(image_filename).convert_alpha()
        original_width, original_height = img.get_size()

        # 🚀 尺寸缩放因子 (1.0 = 原尺寸, 0.6 = 缩小到 60%)
        SCALE_FACTOR = 0.6
        new_w = int(original_width * SCALE_FACTOR)
        new_h = int(original_height * SCALE_FACTOR)

        # 将图片直接按比例缩放
        img = pygame.transform.scale(img, (new_w, new_h))

        # 重新计算居中偏移
        offset_x = (SCREEN_WIDTH - new_w) // 2
        offset_y = (SCREEN_HEIGHT - new_h) // 2

        # 提取步长
        step = 1

        # 遍历图片像素
        for y in range(0, new_h, step):
            for x in range(0, new_w, step):
                pixel = img.get_at((x, y))
                r, g, b = pixel[0], pixel[1], pixel[2]

                # 核心逻辑：如果当前是暗色（缝隙），检查周围有没有颜色，有就补上
                if r <= 30 and g <= 30 and b <= 30:
                    is_edge_or_gap = False
                    # 检查上下左右四个邻居（防止越界）
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < new_w and 0 <= ny < new_h:
                            neighbor = img.get_at((nx, ny))
                            # 如果邻居有颜色（大于 50，说明是图案的一部分）
                            if neighbor[0] > 50 or neighbor[1] > 50 or neighbor[2] > 50:
                                r, g, b = neighbor[0], neighbor[1], neighbor[2]
                                is_edge_or_gap = True
                                break

                    if not is_edge_or_gap:
                        continue  # 真正的背景黑点，直接跳过

                # 智能提亮（保持边缘清晰）
                r = min(int(r * 2.2), 255)
                g = min(int(g * 2.2), 255)
                b = min(int(b * 2.2), 255)

                points_data.append((
                    x + offset_x,
                    y + offset_y,
                    (r, g, b)
                ))
        print(f"✅ 已提取 {len(points_data)} 个粒子，自动填坑完毕，缝隙已修复!")

    except Exception as e:
        print(f"❌ 错误：找不到 '{image_filename}' 图片文件！\n{e}")
    return points_data


# ==================== 3. 主循环 ====================
def main():
    # 加载粒子
    points_data = load_image_to_points("logo.jpg")
    if not points_data:
        print("没有找到粒子图片，程序退出...")
        return

    particles = [Particle(x, y, color) for x, y, color in points_data]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # 1. 绘制代码雨背景
        draw_matrix()

        # 2. 绘制粒子到背景层
        for p in particles:
            p.update()
            # 只要坐标在范围内，就画出粒子点
            px, py = int(p.current_x), int(p.current_y)
            if 0 <= px < SCREEN_WIDTH and 0 <= py < SCREEN_HEIGHT:
                MATRIX_SURFACE.set_at((px, py), p.color)

        # 3. 将最终画面贴到屏幕上
        screen.blit(MATRIX_SURFACE, (0, 0))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()