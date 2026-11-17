from pathlib import Path
import sys

import pico2d as canvas

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game.dialogue import Dialogue, Line
from game.first_puzzle import FIRST_ENCOUNTER, HEIGHT, WIDTH, FirstPuzzle, contains
from game.framework import run
from game.opening import Opening, PHONE_ITEM, WINDOW
from game.persistence import load_game, save_game
from game.view import GameView, SKIP_BUTTON


FADE_TIME = 0.22
BLACK_HOLD = 0.12
AUTOSAVE_INTERVAL = 60.0


class LodgeScene:
    def __init__(self, save_path):
        self.slot_paths = (
            save_path,
            save_path.with_stem(f'{save_path.stem}_2'),
            save_path.with_stem(f'{save_path.stem}_3'),
        )
        self.active_slot = None
        self.pending_slot = None
        self.slot_mode = 'new'
        self.autosave_elapsed = 0.0
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
        self.autosave_elapsed = 0.0
        self.puzzle = FirstPuzzle()
        self.opening = Opening(self.puzzle)
        self.set_screen('opening')

    @property
    def save_path(self):
        return self.slot_paths[self.active_slot] if self.active_slot is not None else None

    def choose_slots(self, mode):
        self.slot_mode = mode
        self.set_screen('slots')

    def select_slot(self, index):
        if self.slot_mode == 'new':
            if self.slot_paths[index].is_file():
                self.pending_slot = index
                self.set_screen('confirm_slot')
                self.message = '이 슬롯은 다음 저장 시 새 진행으로 덮어씁니다.'
            else:
                self.start_in_slot(index)
        else:
            self.load_slot(index)

    def start_in_slot(self, index):
        self.active_slot = index
        self.start()

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
        self.puzzle.player.x, self.puzzle.player.y = FIRST_ENCOUNTER
        self.puzzle.player.facing = (1, 0)
        self.opening = None
        self.set_screen('play')
        self.skip_update = True

    def skip_opening(self):
        opening = self.opening
        while opening.dialogue and not opening.cue_remaining:
            dialogue = opening.dialogue
            dialogue.characters = len(dialogue.line.text)
            if opening.changes_place or dialogue.index == len(dialogue.lines) - 1:
                self.advance_dialogue()
                return
            self.advance_opening()

    def advance_dialogue(self):
        if self.thought:
            if self.thought.advance():
                self.thought = None
                self.skip_update = True
            return
        if self.screen != 'opening' or self.opening.dialogue is None:
            return
        if self.opening.dialogue.complete and self.opening.changes_place:
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
        self.autosave_elapsed = 0.0
        has_phone = PHONE_ITEM in self.puzzle.items
        self.puzzle = FirstPuzzle()
        if has_phone:
            self.puzzle.items.append(PHONE_ITEM)
            self.finish_opening()
        else:
            self.opening = None
            self.set_screen('play')

    def save(self, automatic=False):
        path = self.save_path
        if path is None or self.screen not in ('play', 'pause') or self.puzzle.caught:
            return
        self.autosave_elapsed = 0.0
        try:
            save_game(path, self.puzzle, self.show_hints)
        except OSError:
            self.message = '저장하지 못했습니다. 저장 폴더의 쓰기 권한을 확인해 주세요.'
        else:
            self.message = '자동 저장했습니다.' if automatic else '진행 상황을 저장했습니다.'

    def load(self):
        if self.active_slot is not None:
            self.load_slot(self.active_slot)

    def load_slot(self, index):
        try:
            puzzle, hints = load_game(self.slot_paths[index])
        except FileNotFoundError:
            self.message = '저장된 게임이 없습니다.'
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            self.message = '저장된 게임을 읽을 수 없습니다.'
        else:
            self.active_slot = index
            self.autosave_elapsed = 0.0
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
        if self.screen == 'slots':
            self.set_screen('title')
        elif self.screen == 'confirm_slot':
            self.set_screen('slots')
        elif self.screen == 'settings':
            self.set_screen(self.settings_parent)
        elif self.screen in ('pause', 'inventory'):
            self.set_screen('play')
        elif self.screen == 'play':
            self.set_screen('pause')

    def buttons(self):
        if self.screen == 'title':
            actions = [('새 게임', lambda: self.choose_slots('new')),
                       ('이어하기', lambda: self.choose_slots('load')), ('설정', self.settings)]
        elif self.screen == 'slots':
            actions = [
                (f"{index + 1}번 슬롯 · {'저장 있음' if path.is_file() else '비어 있음'}",
                 lambda index=index: self.select_slot(index))
                for index, path in enumerate(self.slot_paths)
            ]
            actions.append(('뒤로', self.back))
        elif self.screen == 'confirm_slot':
            actions = [('이 슬롯으로 시작', lambda: self.start_in_slot(self.pending_slot)), ('뒤로', self.back)]
        elif self.screen == 'game_over':
            actions = []
            if self.save_path and self.save_path.is_file():
                actions.append(('이어하기', self.load))
            actions.extend([
                ('첫 퍼즐 다시 시도', self.restart_puzzle),
                ('타이틀로 돌아가기', lambda: self.set_screen('title')),
            ])
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
                self.skip_opening()
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
            self.choose_slots('new')
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
        door_was_open = self.puzzle.door_open
        self.puzzle.update(horizontal, vertical, turn_only, dt, self.transition_room)
        if self.puzzle.room == 'hall' and door_was_open != self.puzzle.door_open:
            self.view.play_sound('lock')
        if self.puzzle.caught:
            self.set_screen('game_over')
            return
        self.autosave_elapsed += dt
        if self.fade_elapsed is None and self.autosave_elapsed >= AUTOSAVE_INTERVAL:
            self.save(automatic=True)

    def transition_room(self, enter):
        def switch():
            enter()
            self.message = ''
            if self.puzzle.caught:
                self.set_screen('game_over')

        self.transition(switch)

    def draw(self):
        listening = (self.screen == 'play' and self.thought is None
                     and self.fade_elapsed is None and canvas.SDL_GetKeyboardFocus())
        self.view.update_watcher_audio(self.puzzle, listening)
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
