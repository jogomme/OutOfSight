from pathlib import Path

import pico2d as canvas

if __package__:
    from .first_puzzle import DOOR, EXIT, HEIGHT, PLATE, WIDTH, FirstPuzzle
    from .framework import run
else:
    from first_puzzle import DOOR, EXIT, HEIGHT, PLATE, WIDTH, FirstPuzzle
    from framework import run


class PuzzleScene:
    def __init__(self):
        self.puzzle = FirstPuzzle()
        self.paused = False
        self.font = None

    def handle_event(self, event):
        if event.type != canvas.SDL_KEYDOWN:
            return
        if event.key == canvas.SDLK_ESCAPE:
            self.paused = not self.paused
        if event.key == canvas.SDLK_r:
            self.puzzle = FirstPuzzle()
            self.paused = False

    def update(self, dt):
        if self.paused or not canvas.SDL_GetKeyboardFocus():
            return
        keys = canvas.SDL_GetKeyboardState(None)
        horizontal = keys[canvas.SDL_SCANCODE_D] - keys[canvas.SDL_SCANCODE_A]
        vertical = keys[canvas.SDL_SCANCODE_W] - keys[canvas.SDL_SCANCODE_S]
        self.puzzle.update(horizontal, vertical, keys[canvas.SDL_SCANCODE_SPACE], dt)

    def draw(self):
        if self.font is None:
            self.font = canvas.load_font(str(Path(canvas.__file__).parent / 'data' / 'ConsolaMalgun.ttf'), 16)
        puzzle = self.puzzle
        canvas.draw_rectangle(0, 0, WIDTH, HEIGHT, 45, 38, 35, filled=True)
        for wall in puzzle.walls:
            canvas.draw_rectangle(*wall, 74, 77, 84, filled=True)

        if puzzle.in_guest_room:
            canvas.draw_rectangle(*EXIT, 94, 133, 107, filled=True)
            message = 'Guest room reached. Use the west door to return.'
        else:
            plate_color = (144, 186, 124) if puzzle.door_open else (176, 135, 76)
            canvas.draw_rectangle(*PLATE, *plate_color)
            door_color = (94, 133, 107) if puzzle.door_open else (157, 77, 65)
            canvas.draw_rectangle(*DOOR, *door_color, filled=True)
            for watcher in puzzle.watchers:
                color = (148, 166, 192) if puzzle.observed(watcher) else (121, 103, 114)
                self.draw_actor(watcher, color)
            message = 'Guide a Watcher onto the outlined plate. Green means the east door is open.'

        self.draw_actor(puzzle.player, (220, 216, 189))
        self.font.draw(40, 552, 'WASD Move  |  Space + WASD Turn  |  Esc Pause  |  R Restart', (235, 224, 205))
        self.font.draw(40, 529, 'Paused' if self.paused else message, (235, 224, 205))

    @staticmethod
    def draw_actor(actor, color):
        x, y = round(actor.x), round(actor.y)
        size = actor.radius
        dx, dy = actor.facing
        canvas.draw_rectangle(x - size, y - size, x + size, y + size, *color, filled=True)
        canvas.draw_line(x, y, x + round(dx * 20), y + round(dy * 20), 236, 182, 96)


if __name__ == '__main__':
    run(PuzzleScene(), WIDTH, HEIGHT)
