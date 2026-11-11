from time import perf_counter

import pico2d

from .player import Player
from .world import HEIGHT, PLAYER_RADIUS, WALLS, WIDTH


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
