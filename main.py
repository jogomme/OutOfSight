from dataclasses import dataclass
from math import hypot
from time import perf_counter

import pico2d


WIDTH, HEIGHT = 800, 600
PLAYER_RADIUS = 12
PLAYER_SPEED = 200
WALLS = (
    (0, 0, WIDTH, 24),
    (0, HEIGHT - 24, WIDTH, HEIGHT),
    (0, 0, 24, HEIGHT),
    (WIDTH - 24, 0, WIDTH, HEIGHT),
    (280, 24, 304, 260),
    (280, 340, 304, HEIGHT - 24),
    (480, 24, 504, 400),
    (504, 376, WIDTH - 24, 400),
)
def touches_wall(x, y):
    return any(
        x + PLAYER_RADIUS > left and x - PLAYER_RADIUS < right
        and y + PLAYER_RADIUS > bottom and y - PLAYER_RADIUS < top
        for left, bottom, right, top in WALLS
    )


@dataclass
class Player:
    x: float = 130
    y: float = 180
    facing: tuple[float, float] = (1, 0)

    def move(self, horizontal, vertical, dt):
        length = hypot(horizontal, vertical)
        if not length:
            return

        self.facing = horizontal / length, vertical / length
        distance = PLAYER_SPEED * dt
        next_x = self.x + self.facing[0] * distance
        next_y = self.y + self.facing[1] * distance

        # 축을 따로 검사하면 벽에 닿아도 벽을 따라 이동할 수 있다.
        if not touches_wall(next_x, self.y):
            self.x = next_x
        if not touches_wall(self.x, next_y):
            self.y = next_y


def draw(player):
    pico2d.clear_canvas()
    pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 22, 25, 32, filled=True)
    for left, bottom, right, top in WALLS:
        pico2d.draw_rectangle(left, bottom, right, top, 63, 72, 87, filled=True)

    x, y = round(player.x), round(player.y)
    pico2d.draw_rectangle(
        x - PLAYER_RADIUS, y - PLAYER_RADIUS, x + PLAYER_RADIUS, y + PLAYER_RADIUS,
        197, 217, 227, filled=True,
    )
    facing_x, facing_y = player.facing
    pico2d.draw_line(x, y, x + round(facing_x * 22), y + round(facing_y * 22), 255, 188, 85)
    pico2d.update_canvas()


def main():
    pico2d.open_canvas(WIDTH, HEIGHT, sync=True)
    try:
        player = Player()
        last_time = perf_counter()
        while True:
            for event in pico2d.get_events():
                if event.type == pico2d.SDL_QUIT:
                    return
            now = perf_counter()
            # 프레임이 늦어져도 한 번에 얇은 벽을 건너뛰지 않도록 이동량을 제한한다.
            dt = min(now - last_time, 0.05)
            last_time = now
            if pico2d.SDL_GetKeyboardFocus():
                keys = pico2d.SDL_GetKeyboardState(None)
                horizontal = keys[pico2d.SDL_SCANCODE_D] - keys[pico2d.SDL_SCANCODE_A]
                vertical = keys[pico2d.SDL_SCANCODE_W] - keys[pico2d.SDL_SCANCODE_S]
                player.move(horizontal, vertical, dt)
            draw(player)
    finally:
        pico2d.close_canvas()


if __name__ == '__main__':
    main()
