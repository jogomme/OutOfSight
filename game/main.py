from pathlib import Path
import sys

import pico2d as canvas

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game.dialogue import Dialogue, Line
from game.first_puzzle import HEIGHT, WIDTH, FirstPuzzle, contains
from game.framework import run
from game.opening import Opening, PHONE, PHONE_ITEM, WINDOW
from game.persistence import load_game, save_game
from game.view import GameView, SKIP_BUTTON


FADE_TIME = 0.22
BLACK_HOLD = 0.12


class LodgeScene:
    def __init__(self, save_path):
        self.save_path = save_path
        self.puzzle = FirstPuzzle()
        self.screen = 'title'
        self.settings_parent = 'title'
        self.show_hints = True
        self.message = ''
        self.view = GameView()
        self.opening = None
        self.skip_update = False
        self.thought = None
        self.fade_elapsed = None
        self.fade_action = None

    def set_screen(self, screen):
        self.screen = screen
        self.message = ''
        self.thought = None

    def start(self):
        self.puzzle = FirstPuzzle()
        self.opening = Opening(self.puzzle)
        self.set_screen('opening')

    def transition(self, action):
        self.fade_elapsed = 0.0
        self.fade_action = action

    @property
    def fade_alpha(self):
        elapsed = self.fade_elapsed
        if elapsed is None:
            return 0
        if elapsed < FADE_TIME:
            return round(255 * elapsed / FADE_TIME)
        return round(255 * max(0.0, min(1.0, (2 * FADE_TIME + BLACK_HOLD - elapsed) / FADE_TIME)))

    def finish_opening(self):
        self.opening = None
        self.set_screen('play')
        self.skip_update = True

    def skip_opening(self):
        if PHONE_ITEM not in self.puzzle.items:
            self.puzzle.items.append(PHONE_ITEM)
        self.puzzle.player.x, self.puzzle.player.y = PHONE
        self.finish_opening()

    def advance_dialogue(self):
        if self.thought:
            if self.thought.advance():
                self.thought = None
                self.skip_update = True
            return
        if self.screen != 'opening' or self.opening.dialogue is None:
            return
        if self.opening.dialogue.complete and self.opening.index in (2, 4, 10, 11):
            self.transition(self.advance_opening)
        else:
            self.advance_opening()

    def advance_opening(self):
        if self.opening.advance():
            self.finish_opening()

    def show_thought(self, message):
        self.thought = Dialogue([Line(self.screen, '주인공 · 생각', '생각', message)])

    def inspect_opening(self):
        if self.opening.stage == 'window' and self.opening.near(self.opening.exterior, WINDOW):
            self.transition(self.opening.interact)
        else:
            message = self.opening.interact()
            if message:
                self.show_thought(message)

    def restart_puzzle(self):
        self.puzzle = FirstPuzzle()
        self.opening = None
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
        elif self.screen == 'game_over':
            actions = [('이어하기', self.load), ('타이틀로 돌아가기', lambda: self.set_screen('title'))]
        elif self.screen == 'pause':
            actions = [
                ('게임으로 돌아가기', self.back), ('저장하기', self.save), ('불러오기', self.load),
                ('설정', self.settings), ('퍼즐 다시 시작', self.restart_puzzle),
                ('타이틀로 돌아가기', lambda: self.set_screen('title')),
            ]
        elif self.screen == 'settings':
            state = '켜짐' if self.show_hints else '꺼짐'
            actions = [(f'조작 안내 · {state}', self.toggle_hints), ('뒤로', self.back)]
        elif self.screen == 'inventory':
            actions = [('뒤로', self.back)]
        else:
            return []
        if self.screen == 'game_over':
            return [((275, 216 - index * 46, 525, 255 - index * 46), label, action)
                    for index, (label, action) in enumerate(actions)]
        top = 336 if self.screen != 'inventory' else 155
        return [
            ((62, top - 39 - index * 46, 311, top - index * 46), label, action)
            for index, (label, action) in enumerate(actions)
        ]

    def handle_event(self, event):
        if self.fade_elapsed is not None:
            return
        if event.type == canvas.SDL_MOUSEBUTTONDOWN and event.button == canvas.SDL_BUTTON_LEFT:
            x, y = event.x, HEIGHT - 1 - event.y
            if self.screen == 'opening' and contains(SKIP_BUTTON, x, y):
                self.transition(self.skip_opening)
            elif self.thought or self.screen == 'opening':
                self.advance_dialogue()
            else:
                for rect, _, action in self.buttons():
                    if contains(rect, x, y):
                        action()
                        break
            return
        if event.type != canvas.SDL_KEYDOWN or getattr(event, 'repeat', False):
            return
        if self.thought or self.screen == 'opening':
            if event.key == canvas.SDLK_SPACE:
                self.advance_dialogue()
            elif event.key == canvas.SDLK_e and self.thought is None and self.opening.dialogue is None:
                self.inspect_opening()
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
                self.show_thought(self.puzzle.interact())
            elif event.key == canvas.SDLK_r:
                self.restart_puzzle()

    def update(self, dt):
        if self.fade_elapsed is not None:
            self.fade_elapsed += dt
            if self.fade_elapsed >= FADE_TIME and self.fade_action is not None:
                action = self.fade_action
                self.fade_action = None
                action()
            if self.fade_elapsed >= 2 * FADE_TIME + BLACK_HOLD:
                self.fade_elapsed = None
            return
        if self.thought:
            self.thought.update(dt)
            return
        if self.skip_update:
            self.skip_update = False
            return
        if self.screen == 'opening' and self.opening.dialogue:
            self.opening.update(dt)
            return
        if self.screen not in ('play', 'opening') or not canvas.SDL_GetKeyboardFocus():
            return
        keys = canvas.SDL_GetKeyboardState(None)
        horizontal = keys[canvas.SDL_SCANCODE_D] - keys[canvas.SDL_SCANCODE_A]
        vertical = keys[canvas.SDL_SCANCODE_W] - keys[canvas.SDL_SCANCODE_S]
        turn_only = keys[canvas.SDL_SCANCODE_SPACE]
        if self.screen == 'opening':
            self.opening.update(dt, horizontal, vertical, turn_only)
            return
        self.puzzle.update(horizontal, vertical, turn_only, dt, self.transition_room)
        if self.puzzle.caught:
            self.set_screen('game_over')

    def transition_room(self, enter):
        def switch():
            enter()
            self.message = ''
            if self.puzzle.caught:
                self.set_screen('game_over')

        self.transition(switch)

    def draw(self):
        self.view.draw(self)
        if self.thought:
            self.view.draw_dialogue(self.thought)
        if self.fade_alpha:
            self.view.draw_fade(self.fade_alpha)


def main():
    root = Path(__file__).resolve().parent
    run(LodgeScene(root / 'saves' / 'progress.json'), WIDTH, HEIGHT)


if __name__ == '__main__':
    main()
