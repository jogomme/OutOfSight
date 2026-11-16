from pathlib import Path

import pico2d as canvas
from pico2d import pico2d as renderer

from .first_puzzle import DOOR, EXIT, HEIGHT, PLATE, PORTALS, WIDTH


ASSETS = Path(__file__).resolve().parent
INK = (236, 222, 190)
ROOM_LABELS = {
    'hall': 'Lodge / First Floor', 'dining': 'Dining Hall', 'kitchen': 'Kitchen',
    'bath': 'Washroom', 'guest': 'Guest Room',
}


class GameView:
    def __init__(self):
        self.images = {}
        self.fonts = {}
        self.mask_key = None
        self.mask = []

    def image(self, path):
        if path not in self.images:
            self.images[path] = canvas.load_image(str(path))
        return self.images[path]

    def text(self, x, y, message, size=18):
        if size not in self.fonts:
            font = Path(canvas.__file__).parent / 'data' / 'ConsolaMalgun.ttf'
            self.fonts[size] = canvas.load_font(str(font), size)
        self.fonts[size].draw(x, y, message, INK)

    def draw(self, scene):
        if scene.screen == 'play':
            self.draw_play(scene)
            return

        backdrop = 'settings' if scene.screen == 'pause' else scene.screen
        self.image(ASSETS / 'art' / f'{backdrop}.png').draw(400, 300, WIDTH, HEIGHT)
        title = {
            'title': 'OUT OF SIGHT', 'pause': 'Paused',
            'inventory': 'Inventory', 'settings': 'Settings',
        }[scene.screen]
        self.text(62, 447, title, 48)
        if scene.screen == 'inventory':
            for index, item in enumerate(['Flashlight', *scene.puzzle.items]):
                self.text(66, 359 - index * 36, item, 22)
        for rectangle, label, _ in scene.buttons():
            canvas.draw_rectangle(*rectangle, 23, 27, 32, filled=True)
            canvas.draw_rectangle(*rectangle, 136, 109, 74)
            self.text(rectangle[0] + 13, rectangle[1] + 20, label)
        if scene.message:
            self.text(62, 42, scene.message)

    def draw_play(self, scene):
        puzzle = scene.puzzle
        self.image(ASSETS / 'art' / f'{puzzle.room}.png').draw(400, 300, WIDTH, HEIGHT)
        if puzzle.room == 'hall':
            color = (172, 201, 138) if puzzle.door_open else (176, 128, 78)
            canvas.draw_rectangle(*PLATE, *color)
            door_color = (97, 163, 112) if puzzle.door_open else (151, 71, 57)
            canvas.draw_rectangle(*DOOR, *door_color, filled=True)
        elif puzzle.in_guest_room:
            canvas.draw_rectangle(*EXIT, 97, 163, 112)
            if 'Guest register' not in puzzle.items:
                canvas.draw_rectangle(413, 330, 431, 342, 193, 158, 95, filled=True)

        for rectangle, _, _, _ in PORTALS[puzzle.room]:
            canvas.draw_rectangle(*rectangle, 151, 134, 96)

        hidden = []
        if puzzle.room == 'hall':
            for watcher in sorted(puzzle.watchers, key=lambda actor: -actor.y):
                if puzzle.light_at(watcher.x, watcher.y):
                    self.draw_actor(watcher, 'watcher', 64)
                else:
                    hidden.append(watcher)

        self.draw_shadows(puzzle)
        for watcher in hidden:
            x, y = round(watcher.x), round(watcher.y) + 28
            canvas.draw_rectangle(x - 4, y, x - 3, y + 1, 208, 191, 150, filled=True)
            canvas.draw_rectangle(x + 3, y, x + 4, y + 1, 208, 191, 150, filled=True)
        self.draw_actor(puzzle.player, 'protagonist', 56)

        canvas.draw_rectangle(0, 552, WIDTH, HEIGHT, 17, 19, 23, filled=True)
        self.text(19, 579, ROOM_LABELS[puzzle.room], 20)
        if scene.show_hints:
            self.text(19, 560, 'WASD Move   Space+WASD Turn   E Inspect   F Light   Tab Bag   Esc Menu', 14)
        if scene.message:
            canvas.draw_rectangle(0, 0, WIDTH, 32, 17, 19, 23, filled=True)
            self.text(19, 16, scene.message, 16)
        for rect, _, _, label in PORTALS[puzzle.room]:
            if abs(puzzle.player.x - (rect[0] + rect[2]) / 2) < 75 and abs(puzzle.player.y - (rect[1] + rect[3]) / 2) < 75:
                self.text(rect[0], min(rect[1] - 10, 537), label, 14)
        if puzzle.in_guest_room and 'Guest register' not in puzzle.items:
            self.text(403, 315, 'Register / E', 14)

    def draw_shadows(self, puzzle):
        player = puzzle.player
        walls = puzzle.walls
        key = (round(player.x / 5), round(player.y / 5), player.facing, walls, puzzle.flashlight)
        if key != self.mask_key:
            self.mask_key = key
            self.mask = []
            step = 16
            shades = (226, 170, 38 if puzzle.flashlight else 130)
            for y in range(0, HEIGHT, step):
                start = 0
                previous = None
                for x in range(0, WIDTH + step, step):
                    shade = shades[puzzle.light_at(x + step / 2, y + step / 2, walls)] if x < WIDTH else None
                    if shade != previous:
                        if previous is not None:
                            self.mask.append((start, y, x - 1, min(y + step, HEIGHT) - 1, previous))
                        start, previous = x, shade

        renderer.SDL_SetRenderDrawBlendMode(renderer.renderer, renderer.SDL_BLENDMODE_BLEND)
        for x1, y1, x2, y2, shade in self.mask:
            canvas.draw_rectangle(x1, y1, x2, y2, 8, 11, 16, shade, filled=True)
        renderer.SDL_SetRenderDrawBlendMode(renderer.renderer, renderer.SDL_BLENDMODE_NONE)

    def draw_actor(self, actor, name, size):
        dx, dy = actor.facing
        row = (2 if dx > 0 else 1) if abs(dx) > abs(dy) else (3 if dy > 0 else 0)
        suffix = '-v1.png' if actor.moving else '-idle-v1.png'
        columns = (1, 2, 3, 2) if actor.moving else (0, 1, 2, 3)
        column = columns[int(actor.animation_time * (8 if actor.moving else 3)) % 4]
        image = self.image(ASSETS.parent / 'assets' / 'sprites' / (name + suffix))
        left, right = round(column * image.w / 4), round((column + 1) * image.w / 4)
        top, bottom = round(row * image.h / 4), round((row + 1) * image.h / 4)
        image.clip_draw(left, image.h - bottom, right - left, bottom - top,
                        round(actor.x), round(actor.y + size * 0.40), size, size)
