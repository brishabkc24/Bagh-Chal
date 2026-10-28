import copy

# Constants to keep the code readable
EMPTY = 0
TIGER = 1
GOAT = 2

def _build_neighbours():
    table = {}
    for r in range(5):
        for c in range(5):
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if (r + c) % 2 == 0:
                directions += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            entries = []
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 5 and 0 <= nc < 5:
                    jr, jc = r + 2 * dr, c + 2 * dc
                    if not (0 <= jr < 5 and 0 <= jc < 5):
                        jr = jc = None
                    entries.append(((nr, nc), (jr, jc)))
            table[(r, c)] = entries
    return table


NEIGHBOURS = _build_neighbours()


class BaghChalLogic:
    def __init__(self):
        # 5x5 grid, [row][col] mapping (y, x)
        self.grid = [[EMPTY for _ in range(5)] for _ in range(5)]
        self.history = []
        # Place the 4 Tigers in the corners
        self.grid[0][0] = TIGER
        self.grid[0][4] = TIGER
        self.grid[4][0] = TIGER
        self.grid[4][4] = TIGER

        # Game state trackers
        self.turn = GOAT  # Goats always move first in Bagh Chal
        self.goats_placed = 0
        self.goats_captured = 0

        # Goats cannot move until all 20 are dropped on the board
        self.phase = 'PLACEMENT'

        # Threefold repetition (draw rule). Only REAL moves are counted here,
        # never the AI's simulated moves.
        self.position_counts = {}
        self.repetition_draw = False
        # Draw flags saved by execute_simulated_move, restored by undo_simulated_move
        self._sim_repetition = []
 
    def get_piece(self, row, col):
        """Returns what is currently at the specified grid intersection."""
        return self.grid[row][col]

    def is_valid_placement(self, row, col):
        """Checks if a Goat can be placed at the given coordinates."""
        return (self.grid[row][col] == EMPTY
                and self.phase == 'PLACEMENT'
                and self.turn == GOAT)
 
    def place_goat(self, row, col):
        """Places a goat, updates counters, and swaps the turn."""
        if self.is_valid_placement(row, col):
            self.save_state()
            self.grid[row][col] = GOAT
            self.goats_placed += 1
            if self.goats_placed == 20:
                self.phase = 'MOVEMENT'
            self.turn = TIGER
            self._record_position()
            return True
        return False

    def move_piece(self, r1, c1, r2, c2):
        """Attempts to move a piece or jump. Returns True on success."""
        if self.grid[r1][c1] != self.turn:
            return False
        if self.grid[r2][c2] != EMPTY:
            return False
       
        if self.turn == GOAT and self.phase == 'PLACEMENT':
            return False

        if self.is_adjacent(r1, c1, r2, c2):
            self.save_state()
            self.grid[r2][c2] = self.grid[r1][c1]
            self.grid[r1][c1] = EMPTY
            self.turn = TIGER if self.turn == GOAT else GOAT
            self._record_position()
            return True

        if self.turn == TIGER and self.is_valid_jump(r1, c1, r2, c2):
            self.save_state()
            mid_r = (r1 + r2) // 2
            mid_c = (c1 + c2) // 2
            self.grid[r2][c2] = TIGER
            self.grid[r1][c1] = EMPTY
            self.grid[mid_r][mid_c] = EMPTY
            self.goats_captured += 1
            self.turn = GOAT
            self._record_position()
            return True

        return False

    def apply_move(self, move):
        """Plays a move tuple ('PLACE'/'MOVE'/'JUMP', ...) FOR REAL:
        saved to history (so Undo works) and counted for repetition.
        Used by the GUI to play the AI's chosen move."""
        self.save_state()
        self._apply(move)
        self._record_position()

   
    def save_state(self):
        """Pushes a snapshot of the current game state onto the stack."""
        state = {
            'grid': copy.deepcopy(self.grid),
            'turn': self.turn,
            'phase': self.phase,
            'goats_placed': self.goats_placed,
            'goats_captured': self.goats_captured,
            'position_counts': dict(self.position_counts),
            'repetition_draw': self.repetition_draw,
        }
        self.history.append(state)

    def undo(self):
        """Pops the last game state from the stack and restores it."""
        if not self.history:
            return False

        state = self.history.pop()
        self.grid = state['grid']
        self.turn = state['turn']
        self.phase = state['phase']
        self.goats_placed = state['goats_placed']
        self.goats_captured = state['goats_captured']
        self.position_counts = state['position_counts']
        self.repetition_draw = state['repetition_draw']
        return True

    def _position_key(self):
        return (tuple(map(tuple, self.grid)), self.turn)

    def _record_position(self):
        """Counts the position for the threefold-repetition draw rule.
        Positions can only repeat once all goats are on the board."""
        if self.phase != 'MOVEMENT':
            return
        key = self._position_key()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1
        if self.position_counts[key] >= 3:
            self.repetition_draw = True

    def _unrecord_position(self):
        """Reverses _record_position for the position currently on the board."""
        if self.phase != 'MOVEMENT':
            return
        key = self._position_key()
        n = self.position_counts.get(key, 0)
        if n <= 1:
            self.position_counts.pop(key, None)
        else:
            self.position_counts[key] = n - 1

     
    def is_adjacent(self, r1, c1, r2, c2):
        """Calculates if two coordinates are connected by a valid line."""
        dr = abs(r1 - r2)
        dc = abs(c1 - c2)

        # Valid straight move (Up, Down, Left, Right)
        if dr + dc == 1:
            return True

        # Valid diagonal move (Only allowed on even sum coordinates)
        if dr == 1 and dc == 1:
            if (r1 + c1) % 2 == 0:
                return True

        return False

    def is_valid_jump(self, r1, c1, r2, c2):
        """Checks if a jump is geometrically valid and if a goat is in the middle."""
        dr = abs(r1 - r2)
        dc = abs(c1 - c2)

        # A jump must be exactly 2 steps horizontally, vertically, or diagonally
        if (dr == 2 and dc == 0) or (dr == 0 and dc == 2):
            pass  # Valid straight jump
        elif dr == 2 and dc == 2:
            # Valid diagonal jump (Only allowed if starting on an even-sum coordinate)
            if (r1 + c1) % 2 != 0:
                return False
        else:
            return False  # Not a 2-step move

        mid_r = (r1 + r2) // 2
        mid_c = (c1 + c2) // 2

        # The jump is only valid if a GOAT is on the midpoint
        return self.grid[mid_r][mid_c] == GOAT

   
    def tiger_mobility(self):
        """Returns (slides, jumps, trapped_tigers).
        slides  = legal one-step tiger moves
        jumps   = legal captures available right now (= goats under threat)
        trapped = tigers with no legal move at all"""
        slides = jumps = trapped = 0
        grid = self.grid
        for r in range(5):
            for c in range(5):
                if grid[r][c] == TIGER:
                    own_moves = 0
                    for (nr, nc), (jr, jc) in NEIGHBOURS[(r, c)]:
                        target = grid[nr][nc]
                        if target == EMPTY:
                            slides += 1
                            own_moves += 1
                        elif target == GOAT and jr is not None and grid[jr][jc] == EMPTY:
                            jumps += 1
                            own_moves += 1
                    if own_moves == 0:
                        trapped += 1
        return slides, jumps, trapped

    def get_total_tiger_moves(self):
        """Total legal tiger moves (slides + jumps)."""
        slides, jumps, _ = self.tiger_mobility()
        return slides + jumps

    def goats_can_move(self):
        """True if at least one goat has a legal one-step move."""
        grid = self.grid
        for r in range(5):
            for c in range(5):
                if grid[r][c] == GOAT:
                    for (nr, nc), _ in NEIGHBOURS[(r, c)]:
                        if grid[nr][nc] == EMPTY:
                            return True
        return False

 
    def check_winner(self, total_tiger_moves=None):
        """Returns TIGER, GOAT, 'DRAW', or None if the game is ongoing.
        Pass total_tiger_moves if you already computed it (saves a board scan)."""
        # Condition 1: Tigers eat 5 goats
        if self.goats_captured >= 5:
            return TIGER

 
        # Condition 2: tigers to move and none can -> Goats win. Judged on the
        # tigers' turn only, as in tournament play: on the goats' turn a forced
        # goat move could still free a tiger.
        if self.turn == TIGER:
            if total_tiger_moves is None:
                total_tiger_moves = self.get_total_tiger_moves()
            if total_tiger_moves == 0:
                return GOAT

        # Condition 3: Goats to move but have no legal move -> Tigers win
        if self.phase == 'MOVEMENT' and self.turn == GOAT and not self.goats_can_move():
            return TIGER

        # Condition 4: same position three times -> draw
        if self.repetition_draw:
            return 'DRAW'

        return None

   
    def get_all_legal_moves(self, player_type):
        """Returns a list of all legal moves for the given player.
        Move tuples: ('PLACE', r, c) | ('MOVE', r1, c1, r2, c2) | ('JUMP', r1, c1, r2, c2)"""
        moves = []
        grid = self.grid

        # 1. Placement Phase (Goats only)
        if player_type == GOAT and self.phase == 'PLACEMENT':
            for r in range(5):
                for c in range(5):
                    if grid[r][c] == EMPTY:
                        moves.append(('PLACE', r, c))
            return moves

        # 2. Movement Phase (Tigers any time, Goats after placement)
        for r1 in range(5):
            for c1 in range(5):
                if grid[r1][c1] == player_type:
                    for (r2, c2), (jr, jc) in NEIGHBOURS[(r1, c1)]:
                        target = grid[r2][c2]
                        if target == EMPTY:
                            moves.append(('MOVE', r1, c1, r2, c2))
                        elif (player_type == TIGER and target == GOAT
                              and jr is not None and grid[jr][jc] == EMPTY):
                            moves.append(('JUMP', r1, c1, jr, jc))
        return moves

 
    def execute_simulated_move(self, move):
        """Applies a move for the AI search. No history entry is made, but the
        position IS counted for the repetition rule, so a line that repeats a
        position three times is scored as the draw it really is. Must be paired
        with undo_simulated_move."""
        self._apply(move)
        self._sim_repetition.append(self.repetition_draw)
        self._record_position()

    def undo_simulated_move(self, move):
        """Reverses execute_simulated_move: board, counts and draw flag."""
        self._unrecord_position()
        self.repetition_draw = self._sim_repetition.pop()
        self._revert(move)

    def _apply(self, move):
        """Puts a move on the board. Touches neither history nor repetition counts."""
        move_type = move[0]

        if move_type == 'PLACE':
            _, r, c = move
            self.grid[r][c] = GOAT
            self.goats_placed += 1
            if self.goats_placed == 20:
                self.phase = 'MOVEMENT'
            self.turn = TIGER

        elif move_type == 'MOVE':
            _, r1, c1, r2, c2 = move
            self.grid[r2][c2] = self.grid[r1][c1]
            self.grid[r1][c1] = EMPTY
            self.turn = TIGER if self.turn == GOAT else GOAT

        elif move_type == 'JUMP':
            _, r1, c1, r2, c2 = move
            self.grid[r2][c2] = TIGER
            self.grid[r1][c1] = EMPTY
            mid_r = (r1 + r2) // 2
            mid_c = (c1 + c2) // 2
            self.grid[mid_r][mid_c] = EMPTY
            self.goats_captured += 1
            self.turn = GOAT

    def _revert(self, move):
        """Takes a move off the board again (the inverse of _apply)."""
        move_type = move[0]

        if move_type == 'PLACE':
            _, r, c = move
            self.grid[r][c] = EMPTY
            self.goats_placed -= 1
            if self.goats_placed < 20:
                self.phase = 'PLACEMENT'
            self.turn = GOAT

        elif move_type == 'MOVE':
            _, r1, c1, r2, c2 = move
            self.grid[r1][c1] = self.grid[r2][c2]
            self.grid[r2][c2] = EMPTY
            self.turn = TIGER if self.turn == GOAT else GOAT

        elif move_type == 'JUMP':
            _, r1, c1, r2, c2 = move
            self.grid[r1][c1] = TIGER
            self.grid[r2][c2] = EMPTY
            mid_r = (r1 + r2) // 2
            mid_c = (c1 + c2) // 2
            self.grid[mid_r][mid_c] = GOAT
            self.goats_captured -= 1
            self.turn = TIGER
