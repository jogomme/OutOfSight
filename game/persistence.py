import json
from math import hypot, isfinite
from pathlib import Path
from tempfile import NamedTemporaryFile

from .first_puzzle import BATH_KEY, FirstPuzzle, HEIGHT, PATROLS, PORTALS, WIDTH
from .opening import PHONE_ITEM


def save_game(path, puzzle, show_hints):
    def actor_state(actor):
        return [actor.x, actor.y, *actor.facing, actor.animation_time, actor.moving]

    data = {
        'version': 3,
        'bath_unlocked': puzzle.bath_unlocked,
        'room': puzzle.room,
        'player': actor_state(puzzle.player),
        'watchers': [actor_state(watcher) for watcher in puzzle.watchers],
        'watcher_behavior': [
            [watcher.room, watcher.active, watcher.patrol_index, watcher.wait_remaining]
            for watcher in puzzle.watchers
        ],
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
    if not isinstance(data, dict) or data.get('version') not in (1, 2, 3) or data.get('room') not in PORTALS:
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

    if data['version'] >= 2:
        behavior = data['watcher_behavior']
        if len(behavior) != len(puzzle.watchers):
            raise ValueError('Invalid Watcher count')
        for watcher, patrol, state in zip(puzzle.watchers, PATROLS, behavior):
            room, active, index, wait = state
            if room not in PORTALS or type(active) is not bool or type(index) is not int:
                raise ValueError('Invalid Watcher behavior')
            if not 0 <= index < len(patrol) or type(wait) not in (int, float) or not isfinite(wait) or wait < 0:
                raise ValueError('Invalid Watcher patrol')
            watcher.room, watcher.active, watcher.patrol_index, watcher.wait_remaining = state
    else:
        # Old saves kept every Watcher in the hall; keep those positions.
        for watcher in puzzle.watchers:
            watcher.room = 'hall'
            watcher.active = True

    for key in ('solved', 'flashlight', 'show_hints'):
        if type(data[key]) is not bool:
            raise ValueError('Invalid save option')
    items = data['items']
    if (not isinstance(items, list)
            or any(item not in ('Guest register', PHONE_ITEM, BATH_KEY) for item in items)
            or len(set(items)) != len(items)):
        raise ValueError('Invalid inventory')
    # Versions 1 and 2 allowed the player to enter the bathroom freely.
    bath_unlocked = data.get('bath_unlocked') if data['version'] == 3 else True
    if type(bath_unlocked) is not bool:
        raise ValueError('Invalid bathroom lock state')
    puzzle.bath_unlocked = bath_unlocked
    puzzle.solved = data['solved']
    puzzle.flashlight = data['flashlight']
    puzzle.items = items
    return puzzle, data['show_hints']
