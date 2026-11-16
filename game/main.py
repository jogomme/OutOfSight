from pathlib import Path
import sys

import pico2d as canvas

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game.first_puzzle import HEIGHT, WIDTH, FirstPuzzle, contains
from game.framework import run
from game.persistence import load_game, save_game
from game.view import GameView


class LodgeScene:
    def __init__(self, save_path):
        self.save_path = save_path
        self.puzzle = FirstPuzzle()
        self.screen = 'title'
        self.settings_parent = 'title'
        self.show_hints = True
        self.message = ''
        self.view = GameView()

    def set_screen(self, screen):
        self.screen = screen
        self.message = ''

    def start(self):
        self.puzzle = FirstPuzzle()
        self.set_screen('play')

    def save(self):
        try:
            save_game(self.save_path, self.puzzle, self.show_hints)
        except OSError:
            self.message = '저장하지 못했습니다. 저장 폴더의 쓰기 권한을 확인해 주세요.'
        else:
            self.message = '진행 상황을 저장했습니다.'

    def load(self):
        try:
            puzzle, hints = load_game(self.save_path)
        except FileNotFoundError:
            self.message = '저장된 게임이 없습니다.'
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            self.message = '저장된 게임을 읽을 수 없습니다.'
        else:
            self.puzzle = puzzle
            self.show_hints = hints
            self.set_screen('play')
            self.message = '저장한 게임을 불러왔습니다.'

    def settings(self):
        self.settings_parent = self.screen
        self.set_screen('settings')

    def toggle_hints(self):
        self.show_hints = not self.show_hints

    def back(self):
        if self.screen == 'settings':
            self.set_screen(self.settings_parent)
        elif self.screen in ('pause', 'inventory'):
            self.set_screen('play')
        elif self.screen == 'play':
            self.set_screen('pause')

    def buttons(self):
        if self.screen == 'title':
            actions = [('새 게임', self.start), ('이어하기', self.load), ('설정', self.settings)]
        elif self.screen == 'pause':
            actions = [
                ('게임으로 돌아가기', self.back), ('저장하기', self.save), ('불러오기', self.load),
                ('설정', self.settings), ('퍼즐 다시 시작', self.start),
                ('타이틀로 돌아가기', lambda: self.set_screen('title')),
            ]
        elif self.screen == 'settings':
            state = '켜짐' if self.show_hints else '꺼짐'
            actions = [(f'조작 안내 · {state}', self.toggle_hints), ('뒤로', self.back)]
        elif self.screen == 'inventory':
            actions = [('뒤로', self.back)]
        else:
            return []
        top = 336 if self.screen != 'inventory' else 155
        return [
            ((62, top - 39 - index * 46, 311, top - index * 46), label, action)
            for index, (label, action) in enumerate(actions)
        ]

    def handle_event(self, event):
        if event.type == canvas.SDL_MOUSEBUTTONDOWN and event.button == canvas.SDL_BUTTON_LEFT:
            for rect, _, action in self.buttons():
                if contains(rect, event.x, HEIGHT - 1 - event.y):
                    action()
                    break
        if event.type != canvas.SDL_KEYDOWN:
            return
        if event.key == canvas.SDLK_ESCAPE:
            self.back()
        elif self.screen == 'title' and event.key == canvas.SDLK_RETURN:
            self.start()
        elif event.key == canvas.SDLK_TAB and self.screen in ('play', 'inventory'):
            self.set_screen('inventory' if self.screen == 'play' else 'play')
        elif self.screen == 'play':
            if event.key == canvas.SDLK_f:
                self.puzzle.flashlight = not self.puzzle.flashlight
            elif event.key == canvas.SDLK_e:
                self.message = self.puzzle.interact()
            elif event.key == canvas.SDLK_r:
                self.start()

    def update(self, dt):
        if self.screen != 'play' or not canvas.SDL_GetKeyboardFocus():
            return
        keys = canvas.SDL_GetKeyboardState(None)
        horizontal = keys[canvas.SDL_SCANCODE_D] - keys[canvas.SDL_SCANCODE_A]
        vertical = keys[canvas.SDL_SCANCODE_W] - keys[canvas.SDL_SCANCODE_S]
        room = self.puzzle.room
        self.puzzle.update(horizontal, vertical, keys[canvas.SDL_SCANCODE_SPACE], dt)
        if room != self.puzzle.room:
            self.message = ''

    def draw(self):
        self.view.draw(self)


def main():
    root = Path(__file__).resolve().parent
    run(LodgeScene(root / 'saves' / 'progress.json'), WIDTH, HEIGHT)


if __name__ == '__main__':
    main()
