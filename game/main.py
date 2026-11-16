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
            self.message = 'Save failed. Check whether the save directory is writable.'
        else:
            self.message = 'Progress saved.'

    def load(self):
        try:
            puzzle, hints = load_game(self.save_path)
        except FileNotFoundError:
            self.message = 'No save found.'
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            self.message = 'The save could not be read.'
        else:
            self.puzzle = puzzle
            self.show_hints = hints
            self.set_screen('play')
            self.message = 'Progress restored.'

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
            actions = [('New Game', self.start), ('Continue', self.load), ('Settings', self.settings)]
        elif self.screen == 'pause':
            actions = [
                ('Resume', self.back), ('Save Game', self.save), ('Load Game', self.load),
                ('Settings', self.settings), ('Restart Puzzle', self.start),
                ('Title Screen', lambda: self.set_screen('title')),
            ]
        elif self.screen == 'settings':
            state = 'On' if self.show_hints else 'Off'
            actions = [(f'Control Hints / {state}', self.toggle_hints), ('Back', self.back)]
        elif self.screen == 'inventory':
            actions = [('Back', self.back)]
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
