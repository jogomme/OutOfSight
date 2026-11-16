from dataclasses import dataclass
from math import cos, hypot, radians

from .navigation import next_waypoint


WIDTH, HEIGHT = 800, 600
PLAYER_SPEED = 200
WATCHER_SPEED = 55
VIEW_DISTANCE = 430
VIEW_LIMIT = cos(radians(45))
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

BOUNDARY = COMMON_WALLS[:4]
ROOMS = {
    'dining': (*BOUNDARY, (250, 280, 550, 380)),
    'kitchen': (*BOUNDARY, (160, 450, 640, 530), (310, 270, 490, 333)),
    'bath': (*BOUNDARY, (520, 344, 700, 463), (210, 415, 280, 495)),
    'guest': ROOM_WALLS,
}
# Each portal stores its trigger, destination and corresponding arrival point.
PORTALS = {
    'hall': (
        ((235, 524, 321, 556), 'dining', (400, 100), 'Dining Hall'),
        ((647, 438, 731, 465), 'kitchen', (682, 300), 'Kitchen'),
        ((586, 55, 660, 84), 'bath', (400, 100), 'Washroom'),
    ),
    'dining': (
        ((358, 43, 442, 75), 'hall', (278, 490), 'Main Hall'),
        ((679, 278, 722, 355), 'kitchen', (130, 300), 'Kitchen'),
    ),
    'kitchen': (
        ((53, 258, 95, 344), 'dining', (650, 315), 'Dining Hall'),
        ((712, 258, 746, 344), 'hall', (689, 496), 'Service Hall'),
    ),
    'bath': (((358, 43, 442, 75), 'hall', (623, 115), 'Service Hall'),),
    'guest': (),
}


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

    moving: bool = False
    animation_time: float = 0.0

    def move(self, dx, dy, distance, walls):
        old = (self.x, self.y)
        self.moving = False
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
        self.moving = old != (self.x, self.y)

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
        self.room = 'hall'
        self.solved = False
        self.flashlight = True
        self.items = []
        self._routes = {}
        self._route_time = 0.0

    @property
    def in_guest_room(self):
        return self.room == 'guest'

    @property
    def door_open(self):
        return any(contains(PLATE, watcher.x, watcher.y) for watcher in self.watchers)

    @property
    def walls(self):
        if self.room != 'hall':
            return ROOMS[self.room]
        if self.door_open:
            return COMMON_WALLS
        return (*COMMON_WALLS, DOOR)

    def light_at(self, x, y, walls=None):
        dx, dy = x - self.player.x, y - self.player.y
        distance = hypot(dx, dy)
        facing_x, facing_y = self.player.facing
        dot = dx * facing_x + dy * facing_y
        if distance > VIEW_DISTANCE or any(
            intersects_segment(wall, self.player.x, self.player.y, dx, dy)
            for wall in (self.walls if walls is None else walls)
        ):
            return 0
        if dot >= distance * VIEW_LIMIT:
            return 2
        if distance <= 90 or dot >= distance * 0.58:
            return 1
        return 0

    def observed(self, watcher):
        return self.light_at(watcher.x, watcher.y) == 2

    def interact(self):
        x, y = self.player.x, self.player.y
        if self.in_guest_room and hypot(x - 422, y - 336) <= 48:
            if 'Guest register' not in self.items:
                self.items.append('Guest register')
                return 'Guest register added to inventory.'
            return 'The guest register is already in your inventory.'
        if self.room == 'hall' and hypot(x - 736, y - 330) <= 62:
            return 'The plate holds the door open.' if self.door_open else 'Locked. A Watcher can hold down the plate.'
        if self.room == 'hall' and hypot(x - 536, y - 330) <= 62:
            return 'The plate responds to a Watcher.'
        return 'Nothing to inspect nearby.'

    def update(self, horizontal, vertical, turn_only, dt):
        self.player.move(horizontal, vertical, 0 if turn_only else PLAYER_SPEED * dt, self.walls)

        self.player.animation_time += dt
        for trigger, room, arrival, _ in PORTALS[self.room]:
            if contains(trigger, self.player.x, self.player.y):
                self.room = room
                self._routes.clear()
                self.player.x, self.player.y = arrival
                return

        if self.in_guest_room:
            if contains(EXIT, self.player.x, self.player.y):
                self.room = 'hall'
                self.player.x, self.player.y = 712, 330
            return

        if self.room != 'hall':
            return

        door_left, door_bottom, door_right, door_top = DOOR
        radius = self.player.radius
        doorway = (door_left - radius, door_bottom + radius, door_right, door_top - radius)
        if self.door_open and contains(doorway, self.player.x, self.player.y):
            self.room = 'guest'
            self._routes.clear()
            self.solved = True
            self.player.x, self.player.y = 88, 330
            return

        self._route_time -= dt
        refresh = self._route_time <= 0
        if refresh:
            self._route_time = 0.15
        for index, watcher in enumerate(self.watchers):
            if self.observed(watcher):
                self._routes.pop(index, None)
                continue
            if refresh or index not in self._routes:
                self._routes[index] = next_waypoint(
                    watcher, (self.player.x, self.player.y), self.walls,
                    WIDTH, HEIGHT, intersects_segment,
                )
            waypoint = self._routes[index]
            watcher.moving = False
            if waypoint is not None:
                dx, dy = waypoint[0] - watcher.x, waypoint[1] - watcher.y
                separation = hypot(self.player.x - watcher.x, self.player.y - watcher.y)
                distance = min(WATCHER_SPEED * dt, hypot(dx, dy), max(0, separation - 28))
                if distance:
                    watcher.move(dx, dy, distance, self.walls)
            watcher.animation_time += dt
