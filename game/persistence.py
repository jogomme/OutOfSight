import json
from math import hypot, isfinite
from pathlib import Path
from tempfile import NamedTemporaryFile

from .first_puzzle import FirstPuzzle, HEIGHT, PORTALS, WIDTH


def save_game(path, puzzle, show_hints):
    def actor_state(actor):
        return [actor.x, actor.y, *actor.facing, actor.animation_time, actor.moving]

    data = {
        'version': 1,
        'room': puzzle.room,
        'player': actor_state(puzzle.player),
        'watchers': [actor_state(watcher) for watcher in puzzle.watchers],
        'solved': puzzle.solved,
        'flashlight': puzzle.flashlight,
        'items': puzzle.items,
        'show_hints': show_hints,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            json.dump(data, file)
            file.close()
            temporary.replace(path)
        finally:
            file.close()
            temporary.unlink(missing_ok=True)


def load_game(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('room') not in PORTALS:
        raise ValueError('Unsupported save file')

    puzzle = FirstPuzzle()
    puzzle.room = data['room']
    states = [data['player'], *data['watchers']]
    actors = [puzzle.player, *puzzle.watchers]
    if len(states) != len(actors):
        raise ValueError('Invalid actor count')
    for actor, state in zip(actors, states):
        x, y, dx, dy, time, moving = state
        if not all(type(value) in (float, int) and isfinite(value) for value in (x, y, dx, dy, time)):
            raise ValueError('Invalid actor state')
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT and time >= 0 and abs(hypot(dx, dy) - 1) < 0.001):
            raise ValueError('Invalid actor coordinates')
        if type(moving) is not bool:
            raise ValueError('Invalid animation state')
        actor.x, actor.y, actor.facing, actor.animation_time, actor.moving = x, y, (dx, dy), time, moving

    for key in ('solved', 'flashlight', 'show_hints'):
        if type(data[key]) is not bool:
            raise ValueError('Invalid save option')
    if data['items'] not in ([], ['Guest register']):
        raise ValueError('Invalid inventory')
    puzzle.solved = data['solved']
    puzzle.flashlight = data['flashlight']
    puzzle.items = data['items']
    return puzzle, data['show_hints']
