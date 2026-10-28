# ai.py
from board_logic import TIGER, GOAT

 
WIN_SCORE  = 10000   
W_CAPTURE  = 500      
W_THREAT   = 150   
W_MOBILITY = 10       
W_TRAPPED  = 250      
W_CENTER   = 25       


def static_score(state, mobility):
    """Heuristic value of a non-terminal position. mobility = state.tiger_mobility()."""
    slides, jumps, trapped = mobility
    score = state.goats_captured * W_CAPTURE
    score += jumps * W_THREAT
    score += slides * W_MOBILITY
    score -= trapped * W_TRAPPED
    if state.grid[2][2] == TIGER:
        score += W_CENTER
    return score


def terminal_score(winner, depth):
    """Score for a finished game. depth = plies still unsearched, so a win found
    nearer the root (bigger depth) beats the same win found deeper."""
    if winner == TIGER:
        return WIN_SCORE + depth
    if winner == GOAT:
        return -WIN_SCORE - depth
    return 0  # 'DRAW'


def evaluate(state):
    """Full evaluation of a position (terminal check + heuristic). Used by the GUI."""
    mobility = state.tiger_mobility()
    winner = state.check_winner(mobility[0] + mobility[1])
    if winner is not None:
        return terminal_score(winner, 0)
    return static_score(state, mobility)


def score_breakdown(state):
    """Rows of (label, count, weight, points) for the 'Explain AI Math' window,
    plus the total. Built from the SAME weights the search uses."""
    slides, jumps, trapped = state.tiger_mobility()
    rows = [
        ("Captured goats",     state.goats_captured,                  W_CAPTURE),
        ("Goats under threat", jumps,                                 W_THREAT),
        ("Tiger slides",       slides,                                W_MOBILITY),
        ("Trapped tigers",     trapped,                              -W_TRAPPED),
        ("Tiger on centre",    1 if state.grid[2][2] == TIGER else 0, W_CENTER),
    ]
    rows = [(label, count, weight, count * weight) for label, count, weight in rows]
    return rows, sum(points for *_, points in rows)


class BaghChalAI:
    def __init__(self, ai_player=TIGER, depth=3):
        # The AI plays as TIGER (maximising) or GOAT (minimising)
        self.ai_player = ai_player
        self.max_depth = depth
        self.nodes_evaluated = 0
        self.branches_pruned = 0
        self.last_score = 0

    def evaluate_board(self, state):
        """Kept for compatibility: heuristic value of a position from the Tiger's view."""
        return evaluate(state)

    def minimax(self, state, depth, alpha, beta, is_maximizing_tiger):
        """Recursive Minimax with Alpha-Beta pruning. Returns (score, best_move)."""
        self.nodes_evaluated += 1

        # ONE board scan per node: mobility feeds both the winner test and the heuristic
        mobility = state.tiger_mobility()
        winner = state.check_winner(mobility[0] + mobility[1])
        if winner is not None:
            return terminal_score(winner, depth), None
        if depth == 0:
            return static_score(state, mobility), None

        side = TIGER if is_maximizing_tiger else GOAT
        moves = state.get_all_legal_moves(side)
        if not moves:
            # Safety net (check_winner already covers this): no legal move = loss for the mover
            return terminal_score(GOAT if is_maximizing_tiger else TIGER, depth), None

        if is_maximizing_tiger:
            # Try captures first: better move ordering = more Alpha-Beta cutoffs
            moves.sort(key=lambda m: m[0] != 'JUMP')
            best_score = float('-inf')
            best_move = moves[0]          # never None when a legal move exists
            for move in moves:
                state.execute_simulated_move(move)
                score, _ = self.minimax(state, depth - 1, alpha, beta, False)
                state.undo_simulated_move(move)

                if score > best_score:
                    best_score, best_move = score, move
                alpha = max(alpha, score)
                if beta <= alpha:
                    self.branches_pruned += 1
                    break
            return best_score, best_move
        else:  # Minimising (Goat's turn)
            # Edge points are the safest placements; try them first
            moves.sort(key=lambda m: min(m[1], m[2], 4 - m[1], 4 - m[2]) if m[0] == 'PLACE' else 0)
            best_score = float('inf')
            best_move = moves[0]
            for move in moves:
                state.execute_simulated_move(move)
                score, _ = self.minimax(state, depth - 1, alpha, beta, True)
                state.undo_simulated_move(move)

                if score < best_score:
                    best_score, best_move = score, move
                beta = min(beta, score)
                if beta <= alpha:
                    self.branches_pruned += 1
                    break
            return best_score, best_move

    def get_best_move(self, current_board_state):
        """Main entry point for the game loop: returns the AI's chosen move tuple,
        or None if it is not the AI's turn."""
        self.nodes_evaluated = 0
        self.branches_pruned = 0
        if current_board_state.turn != self.ai_player:
            return None
        is_maximizing = (self.ai_player == TIGER)
        score, best_move = self.minimax(current_board_state, self.max_depth,
                                        float('-inf'), float('inf'), is_maximizing)
        self.last_score = score
        return best_move
