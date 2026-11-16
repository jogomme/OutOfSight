from dataclasses import dataclass
from heapq import heappop, heappush
from math import cos, hypot, radians

from .navigation import next_waypoint


WIDTH, HEIGHT = 800, 600
PLAYER_SPEED = 200
WATCHER_SPEED = 55
VIEW_DISTANCE = 430
VIEW_LIMIT = cos(radians(45))
PLATE = (500, 288, 572, 372)
DOOR = (744, 288, 768, 372)
CHASE_DISTANCE = 430
PATROL_WAIT = 1.2
WATCHER_STARTS = (('hall', 292, 330), ('dining', 540, 460), ('bath', 350, 430))
PATROLS = (
    (('hall', 292, 330), ('hall', 460, 345)),
    (('dining', 540, 460), ('dining', 620, 280), ('kitchen', 570, 200)),
    (('bath', 350, 430), ('bath', 430, 185), ('hall', 620, 151)),
)
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


@dataclass
class Watcher(Actor):
    room: str = 'hall'
    active: bool = False
    patrol_index: int = 0
    wait_remaining: float = 0.0
    waypoint: tuple[float, float] | None = None
    route_remaining: float = 0.0
    route_goal: tuple | None = None


def portal_center(rect):
    left, bottom, right, top = rect
    return (left + right) / 2, (bottom + top) / 2


class FirstPuzzle:
    def __init__(self):
        self.player = Actor(*START, 12)
        self.watchers = [Watcher(x, y, 10, room=room) for room, x, y in WATCHER_STARTS]
        self.room = 'hall'
        self.solved = False
        self.flashlight = True
        self.items = []
        self.activate_room()

    def activate_room(self):
        for watcher, (room, _, _) in zip(self.watchers, WATCHER_STARTS):
            if room == self.room:
                watcher.active = True

    @property
    def in_guest_room(self):
        return self.room == 'guest'

    @property
    def door_open(self):
        return any(watcher.room == 'hall' and contains(PLATE, watcher.x, watcher.y)
                   for watcher in self.watchers)

    @property
    def walls(self):
        return self.walls_for(self.room)

    def walls_for(self, room):
        if room != 'hall':
            return ROOMS[room]
        return COMMON_WALLS if self.door_open else (*COMMON_WALLS, DOOR)

    def exits(self, room):
        if room == 'guest':
            return ((EXIT, 'hall', (712, 330), 'Service Hall'),)
        if room == 'hall' and self.door_open:
            return (*PORTALS[room], ((732, 300, 748, 360), 'guest', (88, 330), 'Guest Room'))
        return PORTALS[room]

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
        return watcher.room == self.room and self.light_at(watcher.x, watcher.y) == 2

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
        for trigger, room, arrival, _ in self.exits(self.room):
            if contains(trigger, self.player.x, self.player.y):
                self.room = room
                self.player.x, self.player.y = arrival
                self.solved |= room == 'guest'
                self.activate_room()
                break

        for index, watcher in enumerate(self.watchers):
            self.update_watcher(watcher, PATROLS[index], dt)

    def route_to(self, watcher, room, target):
        origin = (watcher.x, watcher.y)
        if watcher.room == room:
            return hypot(target[0] - origin[0], target[1] - origin[1]), target, None

        # Room distances follow door links. Local obstacle avoidance is handled by A*.
        frontier = [(0.0, watcher.room, origin, None)]
        best = {(watcher.room, origin): 0.0}
        result = (float('inf'), None, None)
        while frontier:
            cost, current, point, first = heappop(frontier)
            if cost >= result[0]:
                break
            if current == room:
                distance = cost + hypot(target[0] - point[0], target[1] - point[1])
                if distance < result[0]:
                    result = distance, portal_center(first[0]), first
                continue
            for link in self.exits(current):
                trigger, destination, arrival, _ = link
                center = portal_center(trigger)
                distance = cost + hypot(center[0] - point[0], center[1] - point[1]) + 1
                key = destination, arrival
                if distance < best.get(key, float('inf')):
                    best[key] = distance
                    heappush(frontier, (distance, destination, arrival, first or link))
        return result

    def update_watcher(self, watcher, patrol, dt):
        if not watcher.active or self.observed(watcher):
            watcher.route_remaining = 0
            return

        distance, goal, portal = self.route_to(watcher, self.room, (self.player.x, self.player.y))
        chasing = distance <= CHASE_DISTANCE
        if not chasing:
            if watcher.wait_remaining > 0:
                watcher.wait_remaining = max(0, watcher.wait_remaining - dt)
                watcher.moving = False
                watcher.animation_time += dt
                return
            room, x, y = patrol[watcher.patrol_index]
            _, goal, portal = self.route_to(watcher, room, (x, y))
            if watcher.room == room and hypot(x - watcher.x, y - watcher.y) < 1:
                watcher.patrol_index = (watcher.patrol_index + 1) % len(patrol)
                watcher.wait_remaining = PATROL_WAIT
                goal = None

        watcher.animation_time += dt
        watcher.moving = False
        if goal is None:
            return

        walls = self.walls_for(watcher.room)
        route_goal = (watcher.room, portal, walls, chasing, None if chasing else goal)
        watcher.route_remaining -= dt
        if watcher.route_remaining <= 0 or watcher.route_goal != route_goal:
            watcher.waypoint = next_waypoint(watcher, goal, walls, WIDTH, HEIGHT, intersects_segment)
            watcher.route_remaining = 0.15
            watcher.route_goal = route_goal

        if watcher.waypoint is not None:
            dx, dy = watcher.waypoint[0] - watcher.x, watcher.waypoint[1] - watcher.y
            step = min(WATCHER_SPEED * dt, hypot(dx, dy))
            if chasing and portal is None:
                step = min(step, max(0, distance - 28))
            if step:
                watcher.move(dx, dy, step, walls)

        if portal is not None and contains(portal[0], watcher.x, watcher.y):
            _, watcher.room, arrival, _ = portal
            watcher.x, watcher.y = arrival
            watcher.route_remaining = 0
