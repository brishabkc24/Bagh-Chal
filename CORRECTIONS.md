# Bagh Chal – corrections applied (2 Oct 2026)

Line numbers refer to the ORIGINAL files. Every item below was reproduced on the
original code first, then re-tested on the patched code (logic tests, 5,000
random boards, AI self-play, and the real Tk window driven under a virtual
display). Section H lists a later follow-up pass.

## A. Game-breaking

### A1. AI could return `None` and freeze the game — `ai.py:49,69`
- Was: `best_move = None`, updated only when `score > max_eval`. When every reply scored
  `-inf` (position where the tiger's only move leads to a forced trap) nothing was ever
  `>` than `-inf`, so the AI returned `None`; `gui.py:278` then silently did nothing and the
  turn never passed.
- Now: `best_move = moves[0]` before the loop (never `None` when a legal move exists);
  an empty move list returns a loss score instead of `±inf`; `play_ai_turn` logs
  "AI has no legal move" instead of ignoring `None`.
- Test: the exact freeze position (18 goats placed, one tiger move) now returns that move.

### A2. Two referees disagreed — `board_logic.py:162` vs `gui.py:218-245`
- Was: `check_winner` only detected trapped tigers in MOVEMENT; the GUI's private copy
  detected it in any phase → "GOATS WIN!" banner while the logic (and the AI) thought
  the game was still on; game hung under the banner.
- Now: `check_winner` detects trapped tigers in ANY phase (the "false win on turn 1"
  worry in the old comment cannot happen: corner tigers always have moves). The GUI
  no longer computes winners; it only asks `logic.check_winner()`.

## B. Rules that were missing

### B1. Goats with no legal move — new in `check_winner`
Movement phase + goats to move + no goat move → TIGER wins (common Bagh Chal rule).

### B2. Threefold repetition draw — `main.py:112` promised it, nothing implemented it
`board_logic` now counts positions after every REAL move (`_record_position`), sets
`repetition_draw`, `check_winner` returns `'DRAW'`, the GUI shows "MATCH DRAW!".
The counter is saved in `save_state()` so Undo rolls it back.

## C. Scoring shown to the player now equals the scoring the AI uses

- Was: three different formulas — `ai.py` (500/capture, +10/move, +25 centre, no trap
  term), `gui.py:70,117-151,361-416` (1000/capture, −500/trapped), `main.py:95-114`
  (+100/capture, "reach 500 points").
- Now: the weights are module constants in `ai.py` (`W_CAPTURE`, `W_THREAT`,
  `W_MOBILITY`, `W_TRAPPED`, `W_CENTER`). `score_breakdown()` returns the exact terms;
  the live label, the "Explain AI Math" window and the Rules window are all generated
  from them. Verified: breakdown total == search evaluation on 2,000 random boards and
  in the live window.

## D. AI strength and speed

### D1. Evaluation — `ai.py:20-28`
Added `+150 × goats a tiger can jump right now` (threat term) and
`−250 × trapped tigers`. The old evaluation valued a threatened goat at 10 points
(one extra "move") versus 500 once eaten, so the goat AI could not see danger beyond
its horizon and opened on the centre into forks. Self-play before/after:
- OLD tiger d2 vs OLD goat d4 → tigers win, 5 captures in 24 plies.
- OLD tiger d2 vs NEW goat d4 → goats win, 0 captures.
- NEW tiger d4 vs OLD goat d4 → tigers win in 16 plies (tiger side not weakened).
- NEW vs NEW at equal depth → draws by repetition with 1–3 captures (balanced play).

### D2. Win scores depend on distance — `ai.py:16,18`
`±10000 ± depth` so a win found nearer the root beats the same win found deeper; the
AI no longer dawdles in won positions (test: immediate winning jump chosen at depths
1, 4 and 6 with scores 10000/10003/10005).

### D3. Speed — `board_logic.py:140-152,166-193`, `ai.py:34-35`
- Pre-computed `NEIGHBOURS` table (≤ 8 entries per point) replaces scanning all 25
  points for every piece. Move generation verified identical to the old scan on
  5,000 random boards.
- One board scan per node: `tiger_mobility()` feeds both the winner test and the
  heuristic (`check_winner(total_tiger_moves)` accepts the precomputed count).
- Result from the opening, AI = goat, depth 6: 1.94 s / 62,041 nodes → 0.26 s / 38,083 nodes.

### D4. Move ordering
Tigers: captures first (unchanged idea, simpler key). Goats: edge points first — safer
placements get searched first, which also breaks ties sensibly.

## E. GUI behaviour

- `apply_move()` (new in `board_logic`) is used for AI moves, so they are in `history`
  and in the repetition count. Undo against the AI explicitly takes back two plies and
  re-schedules the AI if it is its turn (e.g. after undoing its opening placement).
- Input is ignored while it is the AI's turn (`is_ai_turn()`), and clicks more than
  40 px from an intersection are ignored.
- Exactly one pending `after()` job (`schedule_ai` / `cancel_ai`); it is cancelled on
  Undo and on "Return to Main Menu" (previously a pending job could fire on a
  destroyed canvas → `TclError`).
- "AI thinking..." + watch cursor are shown before the blocking search; the turn
  banner says "(AI)".
- Captures are logged as captures; illegal moves are logged instead of ignored.
- Removed the three duplicate tiger-mobility loops from `gui.py` (they were identical to
  `get_total_tiger_moves`, verified on 5,000 boards).
- Non-BMP emoji removed from buttons (Tk 8.6 on Windows can render them as boxes).

## F. Assets and packaging

- `resource_path()` resolves files next to the script, or inside the PyInstaller bundle
  (`sys._MEIPASS`), so the game no longer depends on the folder it is launched from.
  Verified by launching with cwd = `/`.
- `load_image()` caches every scaled image: `outer_bg.png` (6.7 MB) was re-decoded and
  re-scaled on every menu draw and every game start.
- Piece images keep their aspect ratio (`goat.png` is 677×369; it was squashed into
  70×70). Transparent margins are cropped and the goat gets a 90 px box.
- `main.spec` lists the four PNG files in `datas` so the images ship with the .exe
  (the old `dist/` had no images and no Pillow, and was built before the last code
  edits).
- `requirements.txt` added. Exclude `baghchal/` (virtualenv, ~90 MB), `build/`, `dist/`
  and `__pycache__/` from the submission zip.
- `root.state('zoomed')` is Windows/macOS only; wrapped in try/except with a Linux fallback.

## G. Cosmetic

- Leftover changelog comments removed; `ai.py` docstring that sat after code removed;
  `main.py` keeps a reference to the menu/game objects; `move_piece` rejects goat moves
  during placement (the GUI already prevented it, the rule now lives in the logic).

## H. Follow-up pass (28 Oct 2026)

### H1. Game would not start — `ai.py:60`
The `class BaghChalAI:` header was missing above `__init__`. The file still compiled
(the methods became nested functions inside `score_breakdown`), but `main.py` and
`gui.py` failed with `ImportError: cannot import name 'BaghChalAI'`. Header restored.
Re-verified with logic tests, AI self-play at depths 2/4/6 and a scripted
click-through of the real Tk window (menu, rules, all three modes, Undo, Hint,
Explain AI Math, full games to the win banner, return to menu).

### H2. Packaging
`main.spec` was referenced above but not present. Created; `dist\BaghChal.exe`
(single file, no console) builds and runs from any folder. `.gitignore` keeps
`build/`, `dist/` and `__pycache__/` out of the repository. `README.md` added.

### H3. Dead code removed
`timer.py` was never imported and `BaghChalGUI.__init__` ignored its
`game_minutes` / `piece_speed` parameters. File and parameters removed.

### H4. Board texture no longer squashed — `gui.py` `load_image`
`inner_board.png` is 640x326 and was stretched into the 580x580 board.
`load_image` now cover-fits (centre crop to the target aspect ratio, then resize)
whenever `keep_aspect` is False.

### H5. Trapped tigers lose on their own turn — `board_logic.py` `check_winner`
The goat win for four trapped tigers is now judged on the tigers' turn only, as
in tournament play. The AI search also counts repetitions for simulated moves, so
a side that is ahead no longer shuttles into a draw it could not see.
