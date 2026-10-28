"""Shared helpers for building board positions in tests."""
from board_logic import BaghChalLogic, EMPTY, TIGER, GOAT

CORNERS = [(0, 0), (0, 4), (4, 0), (4, 4)]

# Every corner tiger boxed in: each neighbour holds a goat and every landing
# point behind those goats is also a goat. 17 goats in total.
TRAPPED_ALL = [
    (0, 1), (1, 0), (1, 1), (0, 2), (2, 0), (2, 2),
    (0, 3), (1, 4), (1, 3), (2, 4),
    (3, 0), (4, 1), (3, 1), (4, 2),
    (3, 4), (4, 3), (3, 3),
]


def position(tigers, goats, turn=TIGER, phase='MOVEMENT', captured=0):
    """Build an arbitrary board. In MOVEMENT all 20 goats count as placed."""
    s = BaghChalLogic()
    s.grid = [[EMPTY] * 5 for _ in range(5)]
    for r, c in tigers:
        s.grid[r][c] = TIGER
    for r, c in goats:
        s.grid[r][c] = GOAT
    s.turn = turn
    s.phase = phase
    s.goats_placed = 20 if phase == 'MOVEMENT' else len(goats) + captured
    s.goats_captured = captured
    return s


def snapshot(s):
    return (tuple(map(tuple, s.grid)), s.turn, s.phase, s.goats_placed, s.goats_captured,
            dict(s.position_counts), s.repetition_draw)


def play(s, move):
    """Play a move tuple through the public API and assert it was accepted."""
    if move[0] == 'PLACE':
        assert s.place_goat(move[1], move[2]), move
    else:
        assert s.move_piece(*move[1:]), move


def fill_board(s):
    """Place all 20 goats on every point except the corners and (0, 1) while the
    (0, 0) tiger shuttles between (0, 0) and (0, 1). Ends in MOVEMENT, tiger to move."""
    skip = set(CORNERS) | {(0, 1)}
    spots = [(r, c) for r in range(5) for c in range(5) if (r, c) not in skip]
    assert len(spots) == 20
    tiger_at = (0, 0)
    for i, (r, c) in enumerate(spots):
        assert s.place_goat(r, c)
        if i < 19:
            dest = (0, 1) if tiger_at == (0, 0) else (0, 0)
            assert s.move_piece(*tiger_at, *dest)
            tiger_at = dest
    return s
