from ctypes import c_int
from math import atan2, cos, hypot, pi, sin

from pico2d import pico2d as sdl

from .first_puzzle import VIEW_DISTANCE, WIDTH, HEIGHT


def smoothstep(start, end, value):
    fraction = max(0.0, min(1.0, (value - start) / (end - start)))
    return fraction * fraction * (3 - 2 * fraction)


def ray_limit(x, y, dx, dy, walls):
    nearest = VIEW_DISTANCE
    for left, bottom, right, top in walls:
        near, far = 0.0, nearest
        for origin, direction, low, high in ((x, dx, left, right), (y, dy, bottom, top)):
            if abs(direction) < 1e-10:
                if not low <= origin <= high:
                    far = -1
                continue
            hit1, hit2 = (low - origin) / direction, (high - origin) / direction
            near, far = max(near, min(hit1, hit2)), min(far, max(hit1, hit2))
        if near <= far:
            nearest = near
    return nearest


class Lighting:
    def __init__(self):
        self.key = None

    def draw(self, puzzle):
        player = puzzle.player
        walls = puzzle.walls
        key = (player.x, player.y, player.facing, walls, puzzle.flashlight)
        if key != self.key:
            self.build(player, walls, puzzle.flashlight)
            self.key = key

        renderer = sdl.renderer
        sdl.SDL_SetRenderDrawBlendMode(renderer, sdl.SDL_BLENDMODE_BLEND)
        sdl.SDL_RenderGeometry(renderer, None, self.vertices, len(self.vertices),
                              self.indices, len(self.indices))
        sdl.SDL_SetRenderDrawBlendMode(renderer, sdl.SDL_BLENDMODE_NONE)

    def build(self, player, walls, flashlight):
        x, y = player.x, player.y
        fx, fy = player.facing
        angles = {index * pi / 90 for index in range(180)}
        # Include both sides of wall corners to keep their shadows aligned.
        for left, bottom, right, top in walls:
            for cx, cy in ((left, bottom), (left, top), (right, bottom), (right, top)):
                if hypot(cx - x, cy - y) <= VIEW_DISTANCE:
                    angle = atan2(cy - y, cx - x)
                    angles.update((angle + offset) % (2 * pi) for offset in (-0.001, 0, 0.001))

        vertices = []
        radii = (0, 36, 60, 90, 240, 340, 380, 410, 430)
        ring = len(radii) + 2
        darkness = 228
        for angle in sorted(angles):
            dx, dy = cos(angle), sin(angle)
            edge = ray_limit(x, y, dx, dy, walls)
            cone = smoothstep(0.56, 0.82, dx * fx + dy * fy)
            for radius in radii:
                radius = min(radius, edge)
                near_glow = 1 - smoothstep(35, 96, radius)
                beam = cone * (1 - smoothstep(340, VIEW_DISTANCE, radius))
                light = max(0.52 * near_glow, beam * (0.84 if flashlight else 0.43))
                alpha = round(darkness * (1 - light))
                vertices.append(self.vertex(x + dx * radius, y + dy * radius, alpha))
            for radius in (edge + 3, 1100):
                vertices.append(self.vertex(x + dx * radius, y + dy * radius, darkness))

        indices = []
        for ray in range(len(angles)):
            current = ray * ring
            following = (current + ring) % len(vertices)
            for level in range(ring - 1):
                a, b = current + level, following + level
                indices.extend((a, a + 1, b + 1, a, b + 1, b))
        self.vertices = (sdl.SDL_Vertex * len(vertices))(*vertices)
        self.indices = (c_int * len(indices))(*indices)

    @staticmethod
    def vertex(x, y, alpha):
        return sdl.SDL_Vertex(sdl.SDL_FPoint(x, HEIGHT - y), sdl.SDL_Color(8, 11, 16, alpha),
                              sdl.SDL_FPoint(0, 0))
