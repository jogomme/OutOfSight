from math import hypot

from .dialogue import Dialogue, Line, load_script
from .first_puzzle import Actor, HEIGHT, PLAYER_SPEED, WIDTH


EXTERIOR_WALLS = (
    (0, 0, 22, HEIGHT), (WIDTH - 22, 0, WIDTH, HEIGHT),
    (0, 0, WIDTH, 24), (0, 300, WIDTH, HEIGHT),
)
DOORBELL = (400, 270)
WINDOW = (630, 270)
PHONE = (470, 255)
PHONE_ITEM = 'Sibling phone'
RING_LINES = (3, 8)
RING_DURATION = 1.8
THUNDER_DURATION = 0.30
CUES = {13: 'thunder', 14: 'door', 15: 'lock', 16: 'footsteps'}


class Opening:
    def __init__(self, puzzle):
        self.puzzle = puzzle
        self.lines = load_script()
        self.exterior = Actor(400, 75, 12, (0, 1))
        self.stage = 'arrival'
        self.blackout = False
        self.cue_remaining = 0.0
        self.cue_duration = 0.0
        self.sounds = []
        self.begin(0, 6)

    def begin(self, start, end):
        self.offset = start
        self.dialogue = Dialogue(self.lines[start:end])

    @property
    def index(self):
        return self.offset + self.dialogue.index if self.dialogue else None

    @property
    def background(self):
        if self.index is not None:
            if self.index < 3:
                return 'home'
            if self.index < 5:
                return 'car'
            if self.index == 10:
                return 'window'
        if self.stage == 'phone':
            return 'corridor'
        return 'outside'

    @property
    def changes_place(self):
        return self.index in (2, 4, 10, 11)

    def ringing_dialogue(self):
        text = '뚜르르…' if self.cue_remaining > RING_DURATION / 2 else '뚜르르… 뚜르르…'
        dialogue = Dialogue([Line(self.background, '전화 연결음', '효과음', text)])
        dialogue.advance()
        return dialogue

    def start_cue(self):
        if self.index in RING_LINES:
            self.sounds.append('ring')
            self.cue_remaining = self.cue_duration = RING_DURATION
        elif self.index in CUES:
            self.sounds.append(CUES[self.index])
            if self.index == 13:
                self.cue_remaining = self.cue_duration = THUNDER_DURATION

    def advance(self):
        if self.dialogue is None or self.cue_remaining > 0:
            return False
        previous = self.index
        if not self.dialogue.advance():
            if previous != self.index:
                self.start_cue()
            return False

        self.dialogue = None
        if self.stage == 'phone':
            return True
        self.stage = {
            'arrival': 'bell', 'bell_talk': 'window', 'window_talk': 'door', 'door_talk': 'phone',
        }[self.stage]
        return False

    def update(self, dt, horizontal=0, vertical=0, turn_only=False):
        if self.cue_remaining > 0:
            self.cue_remaining = max(0, self.cue_remaining - dt)
            if self.index == 13 and self.cue_remaining == 0:
                self.blackout = True
            return
        if self.dialogue:
            self.dialogue.update(dt)
            return
        indoors = self.stage == 'phone'
        actor = self.puzzle.player if indoors else self.exterior
        walls = self.puzzle.walls if indoors else EXTERIOR_WALLS
        actor.move(horizontal, vertical, 0 if turn_only else PLAYER_SPEED * dt, walls)
        actor.animation_time += dt

    def interact(self):
        if self.dialogue:
            return
        if self.stage == 'phone':
            if self.near(self.puzzle.player, PHONE):
                self.puzzle.items.append(PHONE_ITEM)
                self.begin(12, 17)
            else:
                return '복도 바닥의 휴대전화를 찾아보자.'
            return
        if self.stage == 'bell' and self.near(self.exterior, DOORBELL):
            self.stage = 'bell_talk'
            self.sounds.append('bell')
            self.begin(6, 10)
        elif self.stage == 'window' and self.near(self.exterior, WINDOW):
            self.stage = 'window_talk'
            self.begin(10, 11)
        elif self.stage == 'door' and self.near(self.exterior, DOORBELL):
            self.stage = 'door_talk'
            self.begin(11, 12)
        else:
            return '옆쪽 창문을 살펴보자.' if self.stage == 'window' else '근처에 조사할 건 없는 것 같아.'

    @staticmethod
    def near(actor, point):
        return hypot(actor.x - point[0], actor.y - point[1]) <= 49
