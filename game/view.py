from ctypes import byref, c_int
from math import cos, hypot, sin, tau
from pathlib import Path

import pico2d as canvas
from pico2d import pico2d as sdl

from .dialogue import wrap_text
from .opening import DOORBELL, DOOR_SLAM_LINE, PHONE, PHONE_ITEM, THUNDER_LINE, WINDOW
from .lighting import Lighting

from .first_puzzle import (BATH_DOOR, BATH_KEY, BATH_KEY_POINT, COMMON_WALLS, DOOR,
                           DOOR_APPROACH, EXIT, HEIGHT, INSPECTIONS, PLATE, PORTALS,
                           WARDROBE, WARDROBE_HANDLE, WIDTH)


ASSETS = Path(__file__).resolve().parent
OPENING_ART = ASSETS / 'art' / 'opening'
INK = (236, 222, 190)
SKIP_BUTTON = (666, 546, 780, 581)
PORTRAITS = {'동생 · 문자': 'sibling', '자동 안내 음성': 'voicemail', '전화 연결음': 'voicemail'}
ITEM_LABELS = {'Guest register': '방문 기록부', PHONE_ITEM: '동생의 휴대전화', BATH_KEY: '공용 욕실 열쇠'}
ROOM_LABELS = {
    'hall': '별장 1층', 'dining': '연회 식당', 'kitchen': '준비 주방',
    'bath': '공용 욕실', 'guest': '귀빈실', 'upstairs': '별장 2층 · 갤러리',
}


class GameView:
    def __init__(self):
        self.images = {}
        self.fonts = {}
        self.lighting = Lighting()
        self.sounds = {}
        self.watcher_channel = -1
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
            if scene.opening.dialogue and not scene.opening.cue_remaining:
                canvas.draw_rectangle(*SKIP_BUTTON, 22, 25, 31, filled=True)
                canvas.draw_rectangle(*SKIP_BUTTON, 165, 130, 92)
                self.text(682, 564, '건너뛰기', 17)
            return
        if scene.screen == 'play':
            self.draw_play(scene)
            return

        backdrop = {
            'pause': 'settings', 'slots': 'title', 'confirm_slot': 'title',
        }.get(scene.screen, scene.screen)
        self.image(ASSETS / 'art' / f'{backdrop}.png').draw(400, 300, WIDTH, HEIGHT)
        title = {
            'title': 'OUT OF SIGHT', 'pause': '일시 정지',
            'inventory': '소지품', 'settings': '설정', 'game_over': 'GAME OVER',
            'slots': '저장 슬롯 선택', 'confirm_slot': '저장 슬롯 확인',
        }[scene.screen]
        if scene.screen == 'game_over':
            self.text(267, 350, title, 54)
        else:
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

    def sound(self, cue):
        if cue not in self.sounds:
            sound = OPENING_ART / f'{cue}.wav'
            self.sounds[cue] = canvas.load_wav(str(sound))
        return self.sounds[cue]

    def play_sound(self, cue):
        if sdl.audio_on:
            self.sound(cue).play()

    def update_watcher_audio(self, puzzle, listening):
        if not sdl.audio_on:
            return
        player = puzzle.player
        distance = min((
            hypot(watcher.x - player.x, watcher.y - player.y)
            for watcher in puzzle.watchers
            if listening and watcher.room == puzzle.room and watcher.active
            and watcher.moving and not puzzle.observed(watcher)
        ), default=360)
        volume = round(72 * max(0.0, 1 - distance / 360))
        if volume:
            if self.watcher_channel < 0 or not sdl.Mix_Playing(self.watcher_channel):
                self.watcher_channel = sdl.Mix_PlayChannel(-1, self.sound('footsteps').wav, -1)
            if self.watcher_channel >= 0:
                sdl.Mix_Volume(self.watcher_channel, volume)
        elif self.watcher_channel >= 0:
            sdl.Mix_HaltChannel(self.watcher_channel)
            sdl.Mix_Volume(self.watcher_channel, 128)
            self.watcher_channel = -1

    def draw_opening(self, opening):
        for cue in opening.sounds:
            self.play_sound(cue)
        opening.sounds.clear()

        background = opening.background
        if background == 'corridor':
            thunder = opening.index == THUNDER_LINE and opening.cue_remaining > 0
            if thunder:
                progress = 1 - opening.cue_remaining / opening.cue_duration
                offset = round(7 * sin(tau * progress) * (1 - progress))
                viewport = sdl.SDL_Rect(offset, 0, WIDTH, HEIGHT)
                sdl.SDL_RenderSetViewport(sdl.renderer, byref(viewport))
            self.draw_hall()
            if opening.index is None or opening.index < DOOR_SLAM_LINE:
                canvas.draw_rectangle(402, 30, 470, 51, 49, 38, 28, filled=True)
                canvas.draw_line(402, 51, 430, 70, 151, 105, 66)
            else:
                self.draw_locked_entrance()
            if opening.blackout:
                self.lighting.draw(opening.puzzle)
            elif opening.dialogue is None:
                canvas.draw_rectangle(464, 249, 476, 261, 38, 42, 51, filled=True)
                canvas.draw_rectangle(466, 251, 474, 259, 139, 180, 189, filled=True)
                self.draw_sparkle(PHONE, opening.puzzle.player.animation_time)
            self.draw_actor(opening.puzzle.player, 'protagonist', 56)
            if thunder:
                sdl.SDL_RenderSetViewport(sdl.renderer, None)
                flash = round(235 * max(0, 1 - progress / 0.42))
                self.draw_fade(flash, (255, 255, 255))
        else:
            path = OPENING_ART / f'{background}.png'
            self.image(path).draw(400, 300, WIDTH, HEIGHT)
            if background == 'outside':
                self.draw_actor(opening.exterior, 'protagonist', 56)
                if opening.dialogue is None:
                    target = WINDOW if opening.stage == 'window' else DOORBELL
                    self.draw_sparkle(target, opening.exterior.animation_time)
        if opening.dialogue is None:
            self.text(22, 576, 'WASD 이동   E 조사', 16)
        elif not opening.cue_remaining:
            self.draw_dialogue(opening.dialogue)

    @staticmethod
    def draw_sparkle(point, elapsed):
        x, y = point
        for dx, dy, offset, scale in ((0, 13, 0.0, 1.0), (9, 21, 0.24, 0.55)):
            phase = (elapsed / 1.4 + offset) % 1
            pulse = (1 + cos(tau * phase)) * 0.5
            radius = max(2, round((5 + 6 * pulse) * scale))
            color = (255, round(188 + 52 * pulse), round(91 + 120 * pulse))
            cx, cy = x + dx, y + dy
            canvas.draw_rectangle(cx - 3, cy - 3, cx + 3, cy + 3, 83, 53, 28, filled=True)
            canvas.draw_line(cx - radius, cy, cx + radius, cy, *color)
            canvas.draw_line(cx, cy - radius, cx, cy + radius, *color)
            canvas.draw_rectangle(cx - 1, cy - 1, cx + 1, cy + 1, *color, filled=True)

    def draw_dialogue(self, dialogue):
        line = dialogue.line
        canvas.draw_rectangle(23, 15, 777, 166, 18, 21, 27, filled=True)
        canvas.draw_rectangle(23, 15, 777, 166, 165, 130, 92)
        canvas.draw_line(185, 126, 756, 126, 108, 85, 62)
        portrait = PORTRAITS.get(line.speaker, 'hero')
        self.image(OPENING_ART / f'{portrait}.png').draw(103, 127, 142, 142)
        canvas.draw_rectangle(30, 54, 176, 200, 165, 130, 92)
        self.text(185, 145, line.speaker, 19)

        size = 22
        if self.dialogue_layout is None or self.dialogue_layout[0] != line:
            self.font(size)
            def measure(text):
                width, height = c_int(), c_int()
                sdl.TTF_SizeUTF8(self.fonts[size].font, text.encode('utf-8'), byref(width), byref(height))
                return width.value

            rows = wrap_text(line.text, measure, 565)
            while len(rows) > 3 and size > 10:
                size -= 1
                self.font(size)
                rows = wrap_text(line.text, measure, 565)
            self.dialogue_layout = (line, size, rows)

        _, size, rows = self.dialogue_layout
        remaining = int(dialogue.characters)
        for index, row in enumerate(rows):
            if remaining <= 0:
                break
            visible = row[:remaining].rstrip()
            if visible:
                self.text(185, 108 - index * (size + 5), visible, size)
            remaining -= len(row)
        if dialogue.complete:
            self.text(640, 31, '클릭 / Space ▸', 15)

    @staticmethod
    def draw_fade(alpha, color=(0, 0, 0)):
        sdl.SDL_SetRenderDrawBlendMode(sdl.renderer, sdl.SDL_BLENDMODE_BLEND)
        canvas.draw_rectangle(0, 0, WIDTH, HEIGHT, *color, alpha, filled=True)
        sdl.SDL_SetRenderDrawBlendMode(sdl.renderer, sdl.SDL_BLENDMODE_NONE)

    def draw_hall(self):
        self.image(ASSETS / 'art' / 'hall.png').draw(400, 300, WIDTH, HEIGHT)
        for left, bottom, right, top in COMMON_WALLS:
            # Match the movement bounds and leave the entry gaps on the wood floor.
            canvas.draw_rectangle(left, bottom, right - 1, top - 1, 65, 58, 61, filled=True)
            canvas.draw_rectangle(left + 2, bottom + 4, right - 3, top - 5, 97, 83, 81, filled=True)
            canvas.draw_line(left + 2, top - 3, right - 3, top - 3, 156, 130, 106)
            canvas.draw_line(left + 2, bottom + 4, right - 3, bottom + 4, 37, 31, 37)
            canvas.draw_line(left + 2, bottom + 4, left + 2, top - 4, 126, 106, 95)

    @staticmethod
    def draw_locked_entrance():
        canvas.draw_rectangle(402, 30, 470, 51, 112, 75, 49, filled=True)
        canvas.draw_rectangle(454, 43, 460, 47, 237, 189, 108, filled=True)

    @staticmethod
    def draw_plate_and_door(pressed):
        left, bottom, right, top = PLATE
        _, door_y = DOOR_APPROACH
        canvas.draw_rectangle(right, door_y - 4, DOOR[0], door_y + 3, 64, 55, 48, filled=True)
        canvas.draw_line(right, door_y + 1, DOOR[0], door_y + 1, 152, 129, 97)
        canvas.draw_rectangle(left, bottom, right, top, 130, 105, 71)
        inset = 6 if pressed else 3
        color = (115, 133, 92) if pressed else (160, 136, 94)
        canvas.draw_rectangle(left + inset, bottom + inset, right - inset, top - inset, *color, filled=True)
        canvas.draw_line(left + inset, top - inset, right - inset, top - inset, 208, 186, 137)
        door_color = (97, 163, 112) if pressed else (151, 71, 57)
        canvas.draw_rectangle(*DOOR, *door_color, filled=True)
        approach_x, _ = DOOR_APPROACH
        canvas.draw_line(approach_x, door_y - 27, approach_x, door_y + 27, 148, 120, 83)

    @staticmethod
    def draw_wardrobe(opened):
        left, bottom, right, top = WARDROBE
        canvas.draw_rectangle(left, bottom, right, top, 75, 51, 39, filled=True)
        canvas.draw_rectangle(left + 3, bottom + 5, right - 6, top - 5,
                              *((36, 25, 26) if opened else (110, 77, 56)), filled=True)
        if not opened:
            # Put the visible front trim on the lit side of the cabinet's collision edge.
            canvas.draw_rectangle(left - 5, bottom + 2, left, top - 2, 132, 89, 57, filled=True)
            canvas.draw_line(left - 5, (bottom + top) // 2, right - 6, (bottom + top) // 2, 63, 40, 32)
            for y in (WARDROBE_HANDLE[1] - 9, WARDROBE_HANDLE[1] + 9):
                canvas.draw_rectangle(left - 9, y, left - 3, y + 3, 208, 173, 116, filled=True)

    @staticmethod
    def draw_investigation_props(puzzle):
        room = puzzle.room
        if room == 'hall':
            for x, y in ((440, 146), (451, 157), (460, 171)):
                canvas.draw_rectangle(x, y, x + 4, y + 8, 82, 74, 67, filled=True)
        elif room == 'dining':
            for x in (383, 402, 421):
                canvas.draw_rectangle(x, 269, x + 8, 277, 169, 157, 141, filled=True)
        elif room == 'kitchen':
            canvas.draw_rectangle(356, 264, 374, 274, 188, 172, 138, filled=True)
            canvas.draw_line(359, 270, 371, 270, 93, 77, 63)
            x, y = BATH_KEY_POINT
            canvas.draw_rectangle(x - 4, y - 4, x + 4, y + 5, 116, 106, 93)
            if BATH_KEY not in puzzle.items:
                canvas.draw_line(x, y + 3, x, y - 9, 212, 172, 102)
                canvas.draw_line(x, y - 9, x + 5, y - 9, 212, 172, 102)
        elif room == 'bath':
            canvas.draw_rectangle(496, 326, 526, 340, 119, 150, 154)
            canvas.draw_rectangle(499, 329, 523, 337, 67, 112, 122, filled=True)
            canvas.draw_rectangle(248, 395, 268, 405, 171, 164, 149, filled=True)
            canvas.draw_line(250, 398, 265, 402, 88, 126, 123)

    def draw_play(self, scene):
        puzzle = scene.puzzle
        if puzzle.room == 'hall':
            self.draw_hall()
            self.draw_locked_entrance()
            self.draw_plate_and_door(puzzle.door_open)
        else:
            self.image(ASSETS / 'art' / f'{puzzle.room}.png').draw(400, 300, WIDTH, HEIGHT)
        if puzzle.room == 'dining':
            self.draw_wardrobe(puzzle.wardrobe_open)
        if puzzle.in_guest_room:
            canvas.draw_rectangle(*EXIT, 97, 163, 112)
            if 'Guest register' not in puzzle.items:
                canvas.draw_rectangle(413, 330, 431, 342, 193, 158, 95, filled=True)

        for rectangle, destination, _, _ in PORTALS[puzzle.room]:
            locked = destination == 'bath' and not puzzle.bath_unlocked
            canvas.draw_rectangle(*rectangle, *((154, 79, 65) if locked else (151, 134, 96)))
            if locked:
                x, y = 623, 70
                canvas.draw_rectangle(x - 5, y - 4, x + 5, y + 4, 186, 146, 88, filled=True)
        self.draw_investigation_props(puzzle)

        hidden = []
        for watcher in sorted(puzzle.watchers, key=lambda actor: -actor.y):
            if not watcher.active or watcher.room != puzzle.room:
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
                if rect == BATH_DOOR and not puzzle.bath_unlocked:
                    label = '공용 욕실 (잠김)'
                self.text(rect[0], min(rect[1] - 10, 537), label, 14)
        for point, _ in INSPECTIONS.get(puzzle.room, ()):
            if (hypot(puzzle.player.x - point[0], puzzle.player.y - point[1]) <= 95
                    and puzzle.light_at(*point)):
                self.draw_sparkle(point, puzzle.player.animation_time)
        if puzzle.in_guest_room and 'Guest register' not in puzzle.items:
            self.draw_sparkle((422, 336), puzzle.player.animation_time)
        if puzzle.room == 'dining' and not puzzle.wardrobe_open:
            self.draw_sparkle(WARDROBE_HANDLE, puzzle.player.animation_time)
        if puzzle.room == 'hall':
            self.draw_sparkle((536, 330), puzzle.player.animation_time)
            self.draw_sparkle((736, 330), puzzle.player.animation_time + 0.32)

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
