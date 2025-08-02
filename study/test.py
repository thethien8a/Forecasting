import math
import sys
import pygame

# ---------------------------
# Cấu hình
# ---------------------------
WIDTH, HEIGHT = 900, 600
FPS = 120

# Bóng
BALL_RADIUS = 10
GRAVITY = 900.0          # px/s^2
BOUNCE_DAMPING = 0.92    # hệ số mất mát năng lượng khi va chạm
AIR_DRAG = 0.0005        # lực cản không khí tuyến tính theo vận tốc
MAX_SPEED = 2000.0       # giới hạn vận tốc

# Lục giác
HEX_RADIUS = 230         # bán kính (từ tâm tới đỉnh)
HEX_THICKNESS = 6        # độ dày nét vẽ
HEX_ANGULAR_SPEED = math.radians(30)  # rad/s (30 độ/giây)
HEX_COLOR = (40, 180, 255)

BG_COLOR = (10, 10, 18)
BALL_COLOR = (255, 220, 40)


# ---------------------------
# Hỗ trợ hình học
# ---------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def rotate_point(x, y, angle):
    ca, sa = math.cos(angle), math.sin(angle)
    return x * ca - y * sa, x * sa + y * ca


def dot(ax, ay, bx, by):
    return ax * bx + ay * by


def reflect(vx, vy, nx, ny):
    # Phản xạ vận tốc v theo pháp tuyến đơn vị n
    vn = dot(vx, vy, nx, ny)
    rx = vx - 2.0 * vn * nx
    ry = vy - 2.0 * vn * ny
    return rx, ry


def length(x, y):
    return math.hypot(x, y)


def normalize(x, y):
    l = length(x, y)
    if l == 0:
        return 0.0, 0.0
    return x / l, y / l


# ---------------------------
# Tạo các cạnh lục giác (ở hệ toạ độ local, trước xoay)
# ---------------------------
def hex_vertices(radius):
    verts = []
    for i in range(6):
        a = math.radians(60 * i - 30)  # lệch -30 độ để có cạnh "phẳng" phía dưới ban đầu
        x = radius * math.cos(a)
        y = radius * math.sin(a)
        verts.append((x, y))
    return verts


def hex_edges(verts):
    edges = []
    n = len(verts)
    for i in range(n):
        p1 = verts[i]
        p2 = verts[(i + 1) % n]
        edges.append((p1, p2))
    return edges


# ---------------------------
# Va chạm bóng - cạnh (trong hệ toạ độ local của lục giác)
# ---------------------------
def collide_ball_segment(px, py, vx, vy, r, ax, ay, bx, by):
    """
    Kiểm tra và xử lý va chạm giữa bóng (tâm p, bán kính r, vận tốc v)
    với đoạn thẳng AB, tất cả ở cùng hệ local (lục giác đứng yên).
    Trả về (hit, nx, ny, fix_dx, fix_dy):
      - hit: có va chạm hay không
      - nx, ny: pháp tuyến đơn vị hướng ra ngoài cạnh (để phản xạ)
      - fix_dx, fix_dy: vector hiệu chỉnh đẩy bóng ra ngoài để tránh xuyên cạnh
    """
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay

    ab_len2 = abx * abx + aby * aby
    if ab_len2 == 0.0:
        # cạnh suy biến về điểm
        dx, dy = px - ax, py - ay
        dist = math.hypot(dx, dy)
        if dist < r:
            nx, ny = normalize(dx, dy)
            if nx == 0 and ny == 0:
                nx, ny = 0.0, -1.0
            fix = r - dist
            return True, nx, ny, nx * fix, ny * fix
        return False, 0.0, 0.0, 0.0, 0.0

    # chiếu AP lên AB để tìm điểm gần nhất trên đoạn
    t = dot(apx, apy, abx, aby) / ab_len2
    t = clamp(t, 0.0, 1.0)
    cx = ax + t * abx
    cy = ay + t * aby

    dx, dy = px - cx, py - cy
    dist = math.hypot(dx, dy)
    if dist >= r:
        return False, 0.0, 0.0, 0.0, 0.0

    # pháp tuyến hướng từ cạnh ra tâm bóng tại điểm gần nhất
    nx, ny = normalize(dx, dy)
    if nx == 0 and ny == 0:
        # nếu trùng tâm, lấy pháp tuyến vuông góc AB
        nx, ny = normalize(-aby, abx)

    fix = r - dist
    return True, nx, ny, nx * fix, ny * fix


# ---------------------------
# Game
# ---------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ball in Rotating Hexagon")
    clock = pygame.time.Clock()

    center_x, center_y = WIDTH // 2, HEIGHT // 2

    # Lục giác local (chưa xoay)
    verts_local = hex_vertices(HEX_RADIUS)
    edges_local = hex_edges(verts_local)

    # Bóng - khởi tạo hơi lệch tâm để thấy chuyển động
    ball_x = center_x + 40.0
    ball_y = center_y - 80.0
    ball_vx = 120.0
    ball_vy = 0.0

    # Góc quay của lục giác
    hex_angle = 0.0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Nhấn ESC để thoát
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            running = False

        # Cập nhật góc quay lục giác
        hex_angle += HEX_ANGULAR_SPEED * dt

        # Trọng lực + cản không khí
        ball_vy += GRAVITY * dt
        ball_vx *= (1.0 - AIR_DRAG) ** (dt * 60.0)
        ball_vy *= (1.0 - AIR_DRAG) ** (dt * 60.0)

        # Giới hạn vận tốc
        speed = math.hypot(ball_vx, ball_vy)
        if speed > MAX_SPEED:
            scale = MAX_SPEED / (speed + 1e-8)
            ball_vx *= scale
            ball_vy *= scale

        # Tích phân vị trí
        ball_x += ball_vx * dt
        ball_y += ball_vy * dt

        # Chuyển sang hệ local của lục giác (xoay ngược bóng)
        lx, ly = ball_x - center_x, ball_y - center_y
        lx, ly = rotate_point(lx, ly, -hex_angle)
        lvx, lvy = rotate_point(ball_vx, ball_vy, -hex_angle)

        # Kiểm tra va chạm với từng cạnh trong hệ local
        hit_any = False
        corr_x = 0.0
        corr_y = 0.0
        nx_total = 0.0
        ny_total = 0.0

        for (a, b) in edges_local:
            hit, nx, ny, fix_dx, fix_dy = collide_ball_segment(
                lx, ly, lvx, lvy, BALL_RADIUS, a[0], a[1], b[0], b[1]
            )
            if hit:
                hit_any = True
                # cộng dồn hiệu chỉnh để đẩy ra ngoài
                corr_x += fix_dx
                corr_y += fix_dy
                # cộng dồn pháp tuyến để lấy hướng tổng
                nx_total += nx
                ny_total += ny

        if hit_any:
            # Đẩy bóng ra khỏi các cạnh (nếu chạm nhiều cạnh cùng lúc)
            lx += corr_x
            ly += corr_y

            # Tính pháp tuyến tổng hợp
            nnx, nny = normalize(nx_total, ny_total)
            if nnx == 0 and nny == 0:
                # fallback: lấy pháp tuyến hướng từ tâm ra bóng
                nnx, nny = normalize(lx, ly)
                if nnx == 0 and nny == 0:
                    nnx, nny = 0.0, -1.0

            # Phản xạ vận tốc trong hệ local
            lvx, lvy = reflect(lvx, lvy, nnx, nny)
            lvx *= BOUNCE_DAMPING
            lvy *= BOUNCE_DAMPING

            # Chuyển lại sang hệ thế giới
            gx, gy = rotate_point(lx, ly, hex_angle)
            ball_x = gx + center_x
            ball_y = gy + center_y
            gvx, gvy = rotate_point(lvx, lvy, hex_angle)
            ball_vx, ball_vy = gvx, gvy

        # Vẽ
        screen.fill(BG_COLOR)

        # Tính các đỉnh lục giác đã xoay để vẽ
        verts_world = []
        for vx, vy in verts_local:
            wx, wy = rotate_point(vx, vy, hex_angle)
            verts_world.append((int(wx + center_x), int(wy + center_y)))

        pygame.draw.polygon(screen, HEX_COLOR, verts_world, HEX_THICKNESS)

        # Vẽ tâm và trục để quan sát
        pygame.draw.circle(screen, (70, 90, 120), (center_x, center_y), 3)

        # Vẽ bóng
        pygame.draw.circle(screen, BALL_COLOR, (int(ball_x), int(ball_y)), BALL_RADIUS)

        # Thông tin debug nhỏ
        info_font = pygame.font.SysFont("consolas", 16)
        s1 = info_font.render(f"FPS: {clock.get_fps():.1f}", True, (180, 180, 200))
        s2 = info_font.render(f"angle: {math.degrees(hex_angle)%360:6.2f} deg", True, (180, 180, 200))
        s3 = info_font.render(f"v=({ball_vx:7.1f},{ball_vy:7.1f})", True, (180, 180, 200))
        screen.blit(s1, (10, 8))
        screen.blit(s2, (10, 28))
        screen.blit(s3, (10, 48))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()