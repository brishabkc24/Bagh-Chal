import random

import pytest

from board_logic import BaghChalLogic, TIGER, GOAT
from ai import (BaghChalAI, evaluate, score_breakdown, static_score, terminal_score,
                WIN_SCORE, W_CAPTURE, W_THREAT, W_MOBILITY, W_TRAPPED, W_CENTER)
from helpers import CORNERS, TRAPPED_ALL, position


class TestScoring:
    def test_win_found_sooner_scores_higher(self):
        assert terminal_score(TIGER, 5) > terminal_score(TIGER, 1) > 0
        assert terminal_score(GOAT, 5) < terminal_score(GOAT, 1) < 0
        assert terminal_score('DRAW', 3) == 0

    def test_static_score_uses_the_published_weights(self):
        s = position(CORNERS, [(0, 1)], turn=TIGER, phase='PLACEMENT')
        slides, jumps, trapped = s.tiger_mobility()
        assert jumps == 1
        expected = jumps * W_THREAT + slides * W_MOBILITY - trapped * W_TRAPPED
        assert static_score(s, (slides, jumps, trapped)) == expected

    def test_centre_tiger_bonus(self):
        s = position([(2, 2), (0, 4), (4, 0), (4, 4)], [], turn=TIGER, phase='PLACEMENT')
        slides, jumps, trapped = s.tiger_mobility()
        assert static_score(s, (slides, jumps, trapped)) == slides * W_MOBILITY + W_CENTER

    def test_captures_raise_the_score(self):
        base = position(CORNERS, [(2, 2)], turn=TIGER, phase='PLACEMENT')
        after = position(CORNERS, [(2, 2)], turn=TIGER, phase='PLACEMENT', captured=1)
        assert evaluate(after) - evaluate(base) == W_CAPTURE

    def test_terminal_positions_evaluate_to_win_scores(self):
        assert evaluate(position(CORNERS, [(2, 2)], captured=5)) == WIN_SCORE
        assert evaluate(position(CORNERS, TRAPPED_ALL, captured=3)) == -WIN_SCORE

    def test_breakdown_matches_evaluate_on_random_boards(self):
        rng = random.Random(2024)
        for _ in range(300):
            s = BaghChalLogic()
            for _ in range(rng.randint(0, 60)):
                if s.check_winner() is not None:
                    break
                s.apply_move(rng.choice(s.get_all_legal_moves(s.turn)))
            if s.check_winner() is None:
                rows, total = score_breakdown(s)
                assert total == evaluate(s)
                assert total == sum(points for *_, points in rows)


class TestMoveChoice:
    def test_returns_none_when_not_its_turn(self):
        assert BaghChalAI(ai_player=TIGER, depth=2).get_best_move(BaghChalLogic()) is None

    @pytest.mark.parametrize("depth", [1, 2, 3, 4])
    def test_opening_move_is_legal(self, depth):
        s = BaghChalLogic()
        ai = BaghChalAI(ai_player=GOAT, depth=depth)
        move = ai.get_best_move(s)
        assert move in s.get_all_legal_moves(GOAT)
        assert ai.nodes_evaluated > 0

    @pytest.mark.parametrize("depth", [1, 2])
    def test_tiger_takes_an_available_capture(self, depth):
        s = position(CORNERS, [(0, 1), (3, 3), (2, 2)], turn=TIGER, phase='PLACEMENT')
        move = BaghChalAI(ai_player=TIGER, depth=depth).get_best_move(s)
        assert move == ('JUMP', 0, 0, 0, 2)

    def test_deeper_search_never_scores_below_the_obvious_capture(self):
        # At depth 4 the tiger may prefer a fork over the immediate capture, but
        # by its own evaluation the chosen line must be at least as good.
        s = position(CORNERS, [(0, 1), (3, 3), (2, 2)], turn=TIGER, phase='PLACEMENT')
        ai = BaghChalAI(ai_player=TIGER, depth=4)
        chosen = ai.get_best_move(s)
        assert chosen in s.get_all_legal_moves(TIGER)
        capture = ('JUMP', 0, 0, 0, 2)
        s.execute_simulated_move(capture)
        capture_score, _ = ai.minimax(s, 3, float('-inf'), float('inf'), False)
        s.undo_simulated_move(capture)
        assert ai.last_score >= capture_score

    def test_goat_does_not_place_itself_next_to_a_hungry_tiger(self):
        s = BaghChalLogic()
        move = BaghChalAI(ai_player=GOAT, depth=2).get_best_move(s)
        s.apply_move(move)
        assert s.tiger_mobility()[1] == 0, f"placement {move} can be captured at once"

    @pytest.mark.parametrize("depth", [1, 2, 4, 6])
    def test_single_legal_move_is_returned_not_none(self, depth):
        # Regression: the AI once returned None when every line looked lost.
        goats = [g for g in TRAPPED_ALL if g != (0, 1)]
        s = position(CORNERS, goats, turn=TIGER, captured=3)
        assert s.get_all_legal_moves(TIGER) == [('MOVE', 0, 0, 0, 1)]
        assert BaghChalAI(ai_player=TIGER, depth=depth).get_best_move(s) == ('MOVE', 0, 0, 0, 1)

    def test_alpha_beta_prunes_branches(self):
        ai = BaghChalAI(ai_player=GOAT, depth=3)
        ai.get_best_move(BaghChalLogic())
        assert ai.branches_pruned > 0
        assert ai.nodes_evaluated > ai.branches_pruned

    def test_search_leaves_the_board_untouched(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        grid_before = [row[:] for row in s.grid]
        history_len = len(s.history)
        BaghChalAI(ai_player=TIGER, depth=4).get_best_move(s)
        assert s.grid == grid_before and s.turn == TIGER
        assert len(s.history) == history_len and s.position_counts == {}


class TestSelfPlay:
    def test_depth_two_self_play_reaches_a_result(self):
        s = BaghChalLogic()
        bots = {TIGER: BaghChalAI(TIGER, depth=2), GOAT: BaghChalAI(GOAT, depth=2)}
        plies = 0
        while s.check_winner() is None and plies < 300:
            move = bots[s.turn].get_best_move(s)
            assert move in s.get_all_legal_moves(s.turn)
            s.apply_move(move)
            plies += 1
        assert s.check_winner() in (TIGER, GOAT, 'DRAW')
