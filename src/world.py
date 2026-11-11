WIDTH, HEIGHT = 800, 600
PLAYER_RADIUS = 12
PLAYER_SPEED = 200
WALLS = (
    (0, 0, WIDTH, 24),
    (0, HEIGHT - 24, WIDTH, HEIGHT),
    (0, 0, 24, HEIGHT),
    (WIDTH - 24, 0, WIDTH, HEIGHT),
    (280, 24, 304, 260),
    (280, 340, 304, HEIGHT - 24),
    (480, 24, 504, 400),
    (504, 376, WIDTH - 24, 400),
)


def touches_wall(x, y):
    return any(
        x + PLAYER_RADIUS > left and x - PLAYER_RADIUS < right
        and y + PLAYER_RADIUS > bottom and y - PLAYER_RADIUS < top
        for left, bottom, right, top in WALLS
    )
