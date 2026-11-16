from dataclasses import dataclass
from pathlib import Path
import re


SCRIPT = Path(__file__).resolve().parents[1] / 'story' / 'opening_stroy_script.md'
CHARACTERS_PER_SECOND = 32
SPEAKERS = {
    '동생 (어제 보낸 문자)': '동생 · 문자',
    '자동 안내 음성': '자동 안내 음성',
    '주인공': '주인공',
}
HEADER = re.compile(r'^\*\*(대화|생각) · (.+?)\*\*\s*$', re.MULTILINE)


@dataclass(frozen=True)
class Line:
    scene: str
    speaker: str
    kind: str
    text: str


def load_script(path=SCRIPT):
    lines = []
    for scene in re.split(r'^## 장소 — ', path.read_text(encoding='utf-8'), flags=re.MULTILINE)[1:]:
        title, body = scene.split('\n', 1)
        headers = list(HEADER.finditer(body))
        for index, header in enumerate(headers):
            kind, actor = header.groups()
            end = headers[index + 1].start() if index + 1 < len(headers) else len(body)
            speaker = '주인공 · 생각' if kind == '생각' else SPEAKERS[actor]
            lines.append(Line(title.strip(), speaker, kind, body[header.end():end].strip()))
    return lines


class Dialogue:
    def __init__(self, lines):
        self.lines = tuple(lines)
        self.index = 0
        self.characters = 0.0

    @property
    def line(self):
        return self.lines[self.index]

    @property
    def complete(self):
        return self.characters >= len(self.line.text)

    def update(self, dt):
        self.characters = min(len(self.line.text), self.characters + dt * CHARACTERS_PER_SECOND)

    def advance(self):
        """Return True when a completed final line is dismissed."""
        if not self.complete:
            self.characters = len(self.line.text)
        elif self.index + 1 == len(self.lines):
            return True
        else:
            self.index += 1
            self.characters = 0.0
        return False


def wrap_text(text, measure, max_width):
    rows = []
    for paragraph in text.splitlines(keepends=True):
        remaining = paragraph.rstrip('\r\n')
        while remaining and measure(remaining) > max_width:
            end = 1
            while end < len(remaining) and measure(remaining[:end + 1]) <= max_width:
                end += 1
            boundary = remaining.rfind(' ', 0, end + 1)
            end = boundary if boundary > 0 else end
            rows.append(remaining[:end])
            remaining = remaining[end:]
            if remaining.startswith(' '):
                # Keep the space in the character count without drawing it.
                rows[-1] += ' '
                remaining = remaining[1:]
        rows.append(remaining + paragraph[len(paragraph.rstrip('\r\n')):])
    return rows
