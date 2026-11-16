from ctypes import byref, c_int
from pathlib import Path

import pico2d as canvas
from pico2d import pico2d as sdl

from .dialogue import wrap_text
from .opening import DOORBELL, PHONE, WINDOW
from .lighting import Lighting

from .first_puzzle import DOOR, EXIT, HEIGHT, PLATE, PORTALS, WIDTH


ASSETS = Path(__file__).resolve().parent
INK = (236, 222, 190)
ITEM_LABELS = {'Guest register': '방문 기록부'}
ROOM_LABELS = {
    'hall': '별장 1층', 'dining': '연회 식당', 'kitchen': '준비 주방',
    'bath': '공용 욕실', 'guest': '귀빈실',
}


class GameView:
    def __init__(self):
        self.images = {}
        self.fonts = {}
        self.lighting = Lighting()
        self.sounds = {}
        self.dialogue_layout = None

    def image(self, path):
        if path not in self.images:
            self.images[path] = canvas.load_image(str(path))
        return self.images[path]

    def font(self, size):
        if size not in self.fonts:
            font = Path(canvas.__file__).parent / 'data' / 'ConsolaMalgun.ttf'
            self.fonts[size] = canvas.load_font(str(font), size)
        return self.fonts[size]

    def text(self, x, y, message, size=18):
        self.font(size).draw(x, y, message, INK)

    def draw(self, scene):
        if scene.screen == 'opening':
            self.draw_opening(scene.opening)
            return
        if scene.screen == 'play':
            self.draw_play(scene)
            return

        backdrop = 'settings' if scene.screen == 'pause' else scene.screen
        self.image(ASSETS / 'art' / f'{backdrop}.png').draw(400, 300, WIDTH, HEIGHT)
        title = {
            'title': 'OUT OF SIGHT', 'pause': '일시 정지',
            'inventory': '소지품', 'settings': '설정',
        }[scene.screen]
        self.text(62, 447, title, 48)
        if scene.screen == 'inventory':
            items = ['손전등', *(ITEM_LABELS[item] for item in scene.puzzle.items)]
            for index, item in enumerate(items):
                self.text(66, 359 - index * 36, item, 22)
        for rectangle, label, _ in scene.buttons():
            canvas.draw_rectangle(*rectangle, 23, 27, 32, filled=True)
            canvas.draw_rectangle(*rectangle, 136, 109, 74)
            self.text(rectangle[0] + 13, rectangle[1] + 20, label)
        if scene.message:
            self.text(62, 42, scene.message)

    def draw_opening(self, opening):
        folder = ASSETS / 'art' / 'opening'
        for cue in opening.sounds:
            sound = folder / f'{cue}.wav'
            if sound.is_file():
                if cue not in self.sounds:
                    self.sounds[cue] = canvas.load_wav(str(sound))
                self.sounds[cue].play()
        opening.sounds.clear()

        background = opening.background
        if background == 'corridor':
            self.image(ASSETS / 'art' / 'hall.png').draw(400, 300, WIDTH, HEIGHT)
            if opening.blackout:
                self.lighting.draw(opening.puzzle)
                canvas.draw_rectangle(402, 40, 470, 51, 82, 57, 42, filled=True)
                canvas.draw_rectangle(454, 43, 460, 47, 200, 160, 94, filled=True)
            elif opening.dialogue is None:
                self.marker(PHONE, '휴대전화 [E]')
            self.draw_actor(opening.puzzle.player, 'protagonist', 56)
        else:
            path = folder / f'{background}.png'
            self.image(path if path.is_file() else ASSETS / 'art' / 'title.png').draw(400, 300, WIDTH, HEIGHT)
            if background == 'outside':
                self.draw_actor(opening.exterior, 'protagonist', 56)
                if opening.dialogue is None:
                    markers = {'bell': (DOORBELL, '초인종 [E]'), 'window': (WINDOW, '옆 창문 [E]'),
                               'door': (DOORBELL, '현관문 [E]')}
                    self.marker(*markers[opening.stage])
        if opening.dialogue:
            self.draw_dialogue(opening.dialogue)
        else:
            self.text(22, 576, 'WASD 이동   E 조사', 16)
            if opening.message:
                canvas.draw_rectangle(0, 0, WIDTH, 36, 17, 19, 23, filled=True)
                self.text(22, 18, opening.message, 16)

    def marker(self, point, label):
        x, y = point
        canvas.draw_rectangle(x - 6, y - 5, x + 6, y + 5, 185, 137, 76, filled=True)
        self.text(x - 24, y - 20, label, 16)

    def draw_dialogue(self, dialogue):
        line = dialogue.line
        canvas.draw_rectangle(23, 15, 777, 166, 18, 21, 27, filled=True)
        canvas.draw_rectangle(23, 15, 777, 166, 165, 130, 92)
        canvas.draw_line(42, 126, 756, 126, 108, 85, 62)
        self.text(42, 145, line.speaker, 19)

        size = 22
        if self.dialogue_layout is None or self.dialogue_layout[0] != line:
            self.font(size)
            def measure(text):
                width, height = c_int(), c_int()
                sdl.TTF_SizeUTF8(self.fonts[size].font, text.encode('utf-8'), byref(width), byref(height))
                return width.value

            rows = wrap_text(line.text, measure, 710)
            while len(rows) > 3 and size > 10:
                size -= 1
                self.font(size)
                rows = wrap_text(line.text, measure, 710)
            self.dialogue_layout = (line, size, rows)

        _, size, rows = self.dialogue_layout
        remaining = int(dialogue.characters)
        for index, row in enumerate(rows):
            if remaining <= 0:
                break
            visible = row[:remaining].rstrip()
            if visible:
                self.text(42, 108 - index * (size + 5), visible, size)
            remaining -= len(row) + 1 if '\n' in line.text and not row.endswith(' ') else len(row)
        if dialogue.complete:
            self.text(640, 31, 'Space 다음 ▸', 15)

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
        for watcher in sorted(puzzle.watchers, key=lambda actor: -actor.y):
            if watcher.room != puzzle.room:
                continue
            if puzzle.light_at(watcher.x, watcher.y):
                self.draw_actor(watcher, 'watcher', 64)
            else:
                hidden.append(watcher)

        self.lighting.draw(puzzle)
        for watcher in hidden:
            x, y = round(watcher.x), round(watcher.y) + 28
            canvas.draw_rectangle(x - 4, y, x - 3, y + 1, 208, 191, 150, filled=True)
            canvas.draw_rectangle(x + 3, y, x + 4, y + 1, 208, 191, 150, filled=True)
        self.draw_actor(puzzle.player, 'protagonist', 56)

        canvas.draw_rectangle(0, 552, WIDTH, HEIGHT, 17, 19, 23, filled=True)
        self.text(19, 579, ROOM_LABELS[puzzle.room], 20)
        if scene.show_hints:
            self.text(19, 560, 'WASD 이동   Space+WASD 방향 전환   E 조사   F 손전등   Tab 소지품   Esc 메뉴', 14)
        if scene.message:
            canvas.draw_rectangle(0, 0, WIDTH, 32, 17, 19, 23, filled=True)
            self.text(19, 16, scene.message, 16)
        for rect, _, _, label in PORTALS[puzzle.room]:
            if abs(puzzle.player.x - (rect[0] + rect[2]) / 2) < 75 and abs(puzzle.player.y - (rect[1] + rect[3]) / 2) < 75:
                self.text(rect[0], min(rect[1] - 10, 537), label, 14)
        if puzzle.in_guest_room and 'Guest register' not in puzzle.items:
            self.text(403, 315, '방문 기록부 [E]', 14)

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
