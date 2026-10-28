import random

import pytest

from board_logic import BaghChalLogic, NEIGHBOURS, EMPTY, TIGER, GOAT
from helpers import CORNERS, TRAPPED_ALL, position, snapshot, play, fill_board


def count(s, piece):
    return sum(row.count(piece) for row in s.grid)


class TestInitialState:
    def test_four_tigers_in_the_corners(self):
        s = BaghChalLogic()
        assert all(s.get_piece(r, c) == TIGER for r, c in CORNERS)
        assert count(s, TIGER) == 4 and count(s, GOAT) == 0

    def test_goats_move_first_in_placement_phase(self):
        s = BaghChalLogic()
        assert s.turn == GOAT and s.phase == 'PLACEMENT'
        assert s.goats_placed == 0 and s.goats_captured == 0

    def test_no_winner_at_start(self):
        assert BaghChalLogic().check_winner() is None


class TestNeighbourTable:
    def test_every_point_present(self):
        assert set(NEIGHBOURS) == {(r, c) for r in range(5) for c in range(5)}

    def test_line_counts(self):
        assert len(NEIGHBOURS[(0, 0)]) == 3   # corner: right, down, diagonal
        assert len(NEIGHBOURS[(2, 2)]) == 8   # centre: all directions
        assert len(NEIGHBOURS[(0, 1)]) == 3   # odd edge point: no diagonals
        assert len(NEIGHBOURS[(1, 2)]) == 4   # odd inner point: orthogonal only

    def test_jump_targets_are_two_steps_in_the_same_direction(self):
        for (r, c), entries in NEIGHBOURS.items():
            for (nr, nc), (jr, jc) in entries:
                if jr is None:
                    assert jc is None
                    continue
                assert (jr - r, jc - c) == (2 * (nr - r), 2 * (nc - c))

    def test_table_agrees_with_is_adjacent(self):
        s = BaghChalLogic()
        for (r, c), entries in NEIGHBOURS.items():
            neighbours = {n for n, _ in entries}
            for r2 in range(5):
                for c2 in range(5):
                    assert ((r2, c2) in neighbours) == s.is_adjacent(r, c, r2, c2)


class TestPlacement:
    def test_place_goat_on_empty_point(self):
        s = BaghChalLogic()
        assert s.place_goat(2, 2)
        assert s.get_piece(2, 2) == GOAT and s.goats_placed == 1 and s.turn == TIGER

    def test_cannot_place_on_occupied_point(self):
        s = BaghChalLogic()
        assert not s.place_goat(0, 0)
        assert s.goats_placed == 0 and s.turn == GOAT

    def test_cannot_place_on_tiger_turn(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        assert not s.place_goat(2, 3)

    def test_goats_cannot_move_during_placement(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        assert s.move_piece(0, 0, 0, 1)
        assert s.turn == GOAT
        assert not s.move_piece(2, 2, 2, 3)

    def test_phase_switches_after_twentieth_goat(self):
        s = fill_board(BaghChalLogic())
        assert s.goats_placed == 20 and s.phase == 'MOVEMENT' and s.turn == TIGER
        assert count(s, GOAT) == 20

    def test_goats_can_move_once_placement_is_over(self):
        s = fill_board(BaghChalLogic())
        assert s.move_piece(0, 1, 0, 0)          # tiger steps aside
        assert s.move_piece(0, 2, 0, 1)          # goat slides into the gap
        assert s.get_piece(0, 1) == GOAT and s.turn == TIGER


class TestTigerMoves:
    def test_diagonal_slide_from_even_point(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        assert s.move_piece(0, 0, 1, 1)
        assert s.get_piece(1, 1) == TIGER and s.get_piece(0, 0) == EMPTY and s.turn == GOAT

    def test_no_diagonal_from_odd_point(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        s.move_piece(0, 0, 0, 1)
        s.place_goat(3, 3)
        assert not s.move_piece(0, 1, 1, 2)      # (0,1) has no diagonal lines
        assert s.move_piece(0, 1, 1, 1)          # straight down is fine

    def test_cannot_move_onto_occupied_point(self):
        s = BaghChalLogic()
        s.place_goat(0, 1)
        assert not s.move_piece(0, 0, 0, 1)

    def test_cannot_move_opponent_piece(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        assert not s.move_piece(2, 2, 2, 3)      # goat on the tiger turn

    def test_two_step_move_without_goat_is_rejected(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        assert not s.move_piece(0, 0, 0, 2)
        assert s.goats_captured == 0


class TestCaptures:
    def test_straight_jump_captures_goat(self):
        s = BaghChalLogic()
        s.place_goat(0, 1)
        assert s.move_piece(0, 0, 0, 2)
        assert s.get_piece(0, 2) == TIGER
        assert s.get_piece(0, 1) == EMPTY and s.get_piece(0, 0) == EMPTY
        assert s.goats_captured == 1 and s.turn == GOAT

    def test_diagonal_jump_from_even_point(self):
        s = BaghChalLogic()
        s.place_goat(1, 1)
        assert s.move_piece(0, 0, 2, 2)
        assert s.goats_captured == 1 and s.get_piece(1, 1) == EMPTY

    def test_diagonal_jump_from_odd_point_is_rejected(self):
        s = position(CORNERS + [(1, 2)], [(2, 3)], turn=TIGER, phase='PLACEMENT')
        assert not s.move_piece(1, 2, 3, 4)
        assert s.goats_captured == 0

    def test_jump_blocked_when_landing_point_occupied(self):
        s = position(CORNERS, [(0, 1), (0, 2)], turn=TIGER, phase='PLACEMENT')
        assert not s.move_piece(0, 0, 0, 2)

    def test_goats_never_capture(self):
        s = position(CORNERS + [(2, 1)], [(2, 2)], turn=GOAT)
        assert not s.move_piece(2, 2, 2, 0)      # a goat jumping over a tiger
        assert s.get_piece(2, 1) == TIGER

    def test_tiger_mobility_counts_threats(self):
        s = position(CORNERS, [(0, 1), (1, 0)], turn=TIGER, phase='PLACEMENT')
        slides, jumps, trapped = s.tiger_mobility()
        assert jumps == 2 and trapped == 0
        assert s.get_total_tiger_moves() == slides + jumps
        assert len(s.get_all_legal_moves(TIGER)) == slides + jumps


class TestWinConditions:
    def test_tigers_win_after_five_captures(self):
        s = position(CORNERS, [(2, 2)], captured=5)
        assert s.check_winner() == TIGER

    def test_goats_win_when_every_tiger_is_trapped(self):
        s = position(CORNERS, TRAPPED_ALL, captured=3)
        assert s.tiger_mobility() == (0, 0, 4)
        assert s.check_winner() == GOAT

    def test_trapped_tigers_lose_during_placement_too(self):
        s = position(CORNERS, TRAPPED_ALL, turn=TIGER, phase='PLACEMENT')
        assert s.check_winner() == GOAT

    def test_trapped_tigers_are_not_lost_until_their_turn(self):
        # Tournament rule: with the goats to move, a forced goat move might free a tiger.
        s = position(CORNERS, TRAPPED_ALL, turn=GOAT, captured=3)
        assert s.tiger_mobility() == (0, 0, 4)
        assert s.check_winner() is None

    def test_tigers_win_when_goats_cannot_move(self):
        tigers = [(0, 1), (1, 0), (1, 1), (4, 4)]
        goats = [(r, c) for r in range(5) for c in range(5)
                 if (r, c) != (0, 0) and (r, c) not in tigers]
        s = position(tigers, goats, turn=GOAT)
        assert len(goats) == 20
        assert not s.goats_can_move()
        assert s.check_winner() == TIGER

    def test_ongoing_game_has_no_winner(self):
        s = fill_board(BaghChalLogic())
        assert s.check_winner() is None


def shuttle_position():
    """Tiger (0,0) and goat (2,2) can shuttle back and forth without captures."""
    goats = ([(1, c) for c in range(5)] + [(3, c) for c in range(5)]
             + [(4, 1), (4, 2), (4, 3), (0, 2), (0, 3), (2, 0), (2, 2)])
    return position(CORNERS, goats, turn=TIGER, captured=3)


SHUTTLE_CYCLE = [('MOVE', 0, 0, 0, 1), ('MOVE', 2, 2, 2, 3),
                 ('MOVE', 0, 1, 0, 0), ('MOVE', 2, 3, 2, 2)]


class TestThreefoldRepetition:
    def _shuttle_position(self):
        return shuttle_position()

    CYCLE = SHUTTLE_CYCLE

    def test_third_occurrence_is_a_draw(self):
        s = self._shuttle_position()
        for i in range(8):
            play(s, self.CYCLE[i % 4])
            assert s.check_winner() is None, f"draw declared too early at ply {i + 1}"
        play(s, self.CYCLE[0])                   # same position for the third time
        assert s.repetition_draw and s.check_winner() == 'DRAW'

    def test_undo_takes_the_draw_back(self):
        s = self._shuttle_position()
        for i in range(9):
            play(s, self.CYCLE[i % 4])
        assert s.check_winner() == 'DRAW'
        assert s.undo()
        assert s.check_winner() is None

    def test_simulated_move_sees_the_third_repetition(self):
        s = shuttle_position()
        for i in range(8):
            play(s, SHUTTLE_CYCLE[i % 4])
        counts = dict(s.position_counts)
        s.execute_simulated_move(SHUTTLE_CYCLE[0])      # third time this position occurs
        assert s.check_winner() == 'DRAW'
        s.undo_simulated_move(SHUTTLE_CYCLE[0])
        assert s.check_winner() is None and not s.repetition_draw
        assert s.position_counts == counts

    def test_positions_are_not_counted_during_placement(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        s.move_piece(0, 0, 0, 1)
        assert s.position_counts == {}


class TestUndo:
    def test_undo_restores_placement(self):
        s = BaghChalLogic()
        s.place_goat(2, 2)
        assert s.undo()
        assert s.get_piece(2, 2) == EMPTY and s.goats_placed == 0 and s.turn == GOAT

    def test_undo_restores_capture(self):
        s = BaghChalLogic()
        s.place_goat(0, 1)
        s.move_piece(0, 0, 0, 2)
        assert s.undo()
        assert s.get_piece(0, 1) == GOAT and s.get_piece(0, 0) == TIGER
        assert s.goats_captured == 0 and s.turn == TIGER

    def test_undo_restores_phase_change(self):
        s = fill_board(BaghChalLogic())
        assert s.undo()
        assert s.phase == 'PLACEMENT' and s.goats_placed == 19 and s.turn == GOAT

    def test_undo_on_empty_history_returns_false(self):
        assert not BaghChalLogic().undo()

    def test_apply_move_is_undoable(self):
        s = BaghChalLogic()
        before = snapshot(s)
        s.apply_move(('PLACE', 2, 2))
        assert snapshot(s) != before
        assert s.undo() and snapshot(s) == before


class TestMoveGeneration:
    def test_placement_moves_are_every_empty_point(self):
        s = BaghChalLogic()
        moves = s.get_all_legal_moves(GOAT)
        assert len(moves) == 21 and all(m[0] == 'PLACE' for m in moves)

    def test_generated_moves_are_accepted_by_the_rules(self):
        rng = random.Random(7)
        s = BaghChalLogic()
        for _ in range(400):
            if s.check_winner() is not None:
                s = BaghChalLogic()
            play(s, rng.choice(s.get_all_legal_moves(s.turn)))

    def test_move_generation_agrees_with_mobility(self):
        rng = random.Random(99)
        s = BaghChalLogic()
        for _ in range(500):
            if s.check_winner() is not None:
                s = BaghChalLogic()
            if s.turn == TIGER:
                moves = s.get_all_legal_moves(TIGER)
                slides, jumps, _ = s.tiger_mobility()
                assert sum(m[0] == 'MOVE' for m in moves) == slides
                assert sum(m[0] == 'JUMP' for m in moves) == jumps
            s.apply_move(rng.choice(s.get_all_legal_moves(s.turn)))

    def test_simulated_move_and_undo_round_trip(self):
        rng = random.Random(1234)
        s = BaghChalLogic()
        for _ in range(3000):
            if s.check_winner() is not None:
                s = BaghChalLogic()
            move = rng.choice(s.get_all_legal_moves(s.turn))
            before = snapshot(s)
            s.execute_simulated_move(move)
            s.undo_simulated_move(move)
            assert snapshot(s) == before, move
            s.apply_move(move)

    @pytest.mark.parametrize("seed", range(25))
    def test_random_games_always_end_or_offer_a_move(self, seed):
        rng = random.Random(seed)
        s = BaghChalLogic()
        for _ in range(400):
            if s.check_winner() is not None:
                break
            moves = s.get_all_legal_moves(s.turn)
            assert moves, "no legal move but no winner declared"
            s.apply_move(rng.choice(moves))
