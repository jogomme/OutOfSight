from dataclasses import dataclass
from math import hypot

from .world import PLAYER_SPEED, touches_wall


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
