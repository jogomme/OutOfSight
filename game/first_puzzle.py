from dataclasses import dataclass
from math import cos, hypot, radians


WIDTH, HEIGHT = 800, 600
PLAYER_SPEED = 200
WATCHER_SPEED = 55
VIEW_DISTANCE = 430
VIEW_LIMIT = cos(radians(40))
PLATE = (500, 288, 572, 372)
DOOR = (744, 288, 768, 372)
WATCHER_SPAWN = (292, 330)
START = (436, 188)

COMMON_WALLS = (
    (0, 0, 32, 600), (768, 0, 800, 600),
    (32, 0, 768, 32), (32, 568, 768, 600),
    (168, 32, 200, 248), (200, 216, 360, 248),
    (360, 400, 744, 432), (360, 32, 392, 264),
    (744, 32, 768, 288), (744, 372, 768, 568),
)
ROOM_WALLS = (
    (0, 0, 32, 600), (768, 0, 800, 600),
    (32, 0, 768, 32), (32, 568, 768, 600),
    (32, 32, 56, 288), (32, 372, 56, 568),
    (536, 384, 696, 504),
)
EXIT = (32, 288, 56, 372)


def contains(rect, x, y):
    left, bottom, right, top = rect
    return left <= x < right and bottom <= y < top


def intersects_segment(rect, x, y, dx, dy):
    near, far = 0.0, 1.0
    for start, change, low, high in (
        (x, dx, rect[0], rect[2]), (y, dy, rect[1], rect[3]),
    ):
        if change == 0:
            if start < low or start > high:
                return False
            continue
        enter, leave = sorted(((low - start) / change, (high - start) / change))
        near, far = max(near, enter), min(far, leave)
        if near > far:
            return False
    return True


@dataclass
class Actor:
    x: float
    y: float
    radius: int
    facing: tuple[float, float] = (1, 0)

    def move(self, dx, dy, distance, walls):
        length = hypot(dx, dy)
        if not length:
            return

        self.facing = dx / length, dy / length
        # 축을 따로 검사해 모퉁이에서 벽을 따라 움직일 수 있게 합니다.
        next_x = self.x + self.facing[0] * distance
        next_y = self.y + self.facing[1] * distance
        if not self.touches(next_x, self.y, walls):
            self.x = next_x
        if not self.touches(self.x, next_y, walls):
            self.y = next_y

    def touches(self, x, y, walls):
        radius = self.radius
        return any(
            x + radius > left and x - radius < right
            and y + radius > bottom and y - radius < top
            for left, bottom, right, top in walls
        )


class FirstPuzzle:
    def __init__(self):
        self.player = Actor(*START, 12)
        self.watchers = [
            Actor(*WATCHER_SPAWN, 10), Actor(94, 148, 10), Actor(116, 488, 10),
        ]
        self.in_guest_room = False
        self.solved = False

    @property
    def door_open(self):
        return any(contains(PLATE, watcher.x, watcher.y) for watcher in self.watchers)

    @property
    def walls(self):
        if self.in_guest_room:
            return ROOM_WALLS
        if self.door_open:
            return COMMON_WALLS
        return (*COMMON_WALLS, DOOR)

    def observed(self, watcher):
        dx, dy = watcher.x - self.player.x, watcher.y - self.player.y
        distance = hypot(dx, dy)
        facing_x, facing_y = self.player.facing
        return (
            distance <= VIEW_DISTANCE
            and dx * facing_x + dy * facing_y >= distance * VIEW_LIMIT
            and not any(
                intersects_segment(wall, self.player.x, self.player.y, dx, dy)
                for wall in self.walls
            )
        )

    def update(self, horizontal, vertical, turn_only, dt):
        self.player.move(horizontal, vertical, 0 if turn_only else PLAYER_SPEED * dt, self.walls)

        if self.in_guest_room:
            if contains(EXIT, self.player.x, self.player.y):
                self.in_guest_room = False
                self.player.x, self.player.y = 712, 330
            return

        door_left, door_bottom, door_right, door_top = DOOR
        radius = self.player.radius
        doorway = (door_left - radius, door_bottom + radius, door_right, door_top - radius)
        if self.door_open and contains(doorway, self.player.x, self.player.y):
            self.in_guest_room = True
            self.solved = True
            self.player.x, self.player.y = 88, 330
            return

        for watcher in self.watchers:
            dx, dy = self.player.x - watcher.x, self.player.y - watcher.y
            # 벽 너머의 플레이어를 향해 벽에 밀착하는 동작을 피합니다.
            clear_path = not any(
                intersects_segment(wall, watcher.x, watcher.y, dx, dy)
                for wall in self.walls
            )
            if clear_path and not self.observed(watcher):
                distance = min(WATCHER_SPEED * dt, max(0, hypot(dx, dy) - 28))
                watcher.move(dx, dy, distance, self.walls)
