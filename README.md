# Bagh Chal

[![Tests](https://github.com/brishabkc24/Bagh-Chal/actions/workflows/tests.yml/badge.svg)](https://github.com/brishabkc24/Bagh-Chal/actions/workflows/tests.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
[![Download for Windows](https://img.shields.io/github/v/release/brishabkc24/Bagh-Chal?label=download%20.exe)](https://github.com/brishabkc24/Bagh-Chal/releases/latest)

A desktop version of **Bagh Chal** (Tigers and Goats), the traditional Nepali
board game, written in Python with Tkinter. Play against another person on the
same computer, against a minimax AI with alpha-beta pruning, or watch the AI
play both sides.

![The AI playing itself: the tigers take two goats, then the goats trap all four tigers](docs/demo.gif)

| Main menu | Mid-game |
| --- | --- |
| ![Main menu](docs/menu.jpg) | ![Playing tigers against the AI: the selected tiger's steps and its capture are marked](docs/game.jpg) |

## Features

- **Local multiplayer**, **play as Tigers / play as Goats** against the AI, or
  **watch the AI play itself** (with pause)
- Three AI levels: Easy (search depth 2), Medium (depth 4), Hard (depth 6).
  While the goats are being placed the AI chooses at random among equally good
  moves, so every game opens differently
- **Move guidance**: dots on the points a selected piece can reach, a target on
  every capture and a gold trail on the last move
- **Threat markers**: a red `!` on a goat that can be eaten right now and a
  `TRAPPED` tag on a tiger that cannot move (can be switched off)
- Pieces slide, captures flash, a win throws confetti, and every action has a
  short **sound effect** synthesised at run time, so no audio files are shipped
  (can be muted)
- Meters for goats in hand, goats captured (5 wins) and tigers trapped (4 wins)
- **New Game** and **Swap Sides** without leaving the board, and a running
  score for the session
- **Hint** button that asks the AI for the best move on your turn
- **Undo** (against the AI it takes back the reply and your move together)
- **Live strategy score** and an **Explain AI Math** window that shows the exact
  heuristic terms the search uses
- Move log with node and pruning counts for every AI move
- Threefold-repetition draw rule
- Keyboard: `Ctrl+Z` undo, `H` hint, `M` sound on/off, `Esc` put the piece down

## Quick start

No Python needed on Windows: grab `BaghChal.exe` from the
[latest release](https://github.com/brishabkc24/Bagh-Chal/releases/latest) and run it.

To run from source (Python 3.10 or newer; Tkinter ships with the standard installer):

```bash
pip install -r requirements.txt
python main.py
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The suite covers the rules engine (placement, moves, captures, win conditions,
threefold repetition, undo, simulate/undo round trips on thousands of random
positions, the threat and trap queries behind the board markers), the AI (move
legality at every depth, capture preference, heuristic consistency, a
regression for a past freeze, self-play, and a check that the randomised choice
only ever plays a move scored exactly as high as the best one) and the sound
synthesis (valid WAV data that neither clips nor clicks). GitHub
Actions runs it on Python 3.10 to 3.13 for every push, then builds the Windows
executable with PyInstaller.

## How it works

- `board_logic.py` is the rules engine. A precomputed neighbour table encodes
  which points are joined by lines (diagonals only exist on even-sum points),
  so move generation never scans the board. It also keeps the undo stack and
  the position counts for the repetition rule.
- `ai.py` is a minimax search with alpha-beta pruning. Captures are searched
  first for tigers and edge placements first for goats, which improves cutoffs.
  Terminal scores carry the remaining depth so a nearer win is preferred. For
  variety, during the placement phase the root search keeps every move tied for
  the best score (each one is searched with a window one point below the best,
  so a tie is exact) and picks one at random. After placement it is
  deterministic again, so level endings repeat and end by the threefold rule.
- `gui.py` draws the board on a Tkinter canvas. Every timed job (the AI's move,
  the frames of a sliding piece, the confetti) goes through one wrapper around
  `root.after`, so all of them are cancelled together on Undo, New Game or on
  returning to the menu.
- `sounds.py` builds each effect from a few decaying sine notes, writes it once
  to a WAV in the temp folder and plays it through `winsound`. On systems
  without `winsound` the game is simply silent.

## Build the Windows .exe

```bash
python -m PyInstaller main.spec --noconfirm --clean
```

The single-file build appears at `dist\BaghChal.exe` with the images bundled,
so it runs from any folder. `dist` and `build` are ignored by Git. Pushing a tag
such as `v1.1` makes GitHub Actions build the .exe and publish it as a release
automatically.

## Project layout

| Path | Purpose |
| --- | --- |
| `main.py` | Main menu, difficulty selection, rules window, program entry point |
| `gui.py` | Tkinter board, markers, animation, Undo / Hint / Explain, move log |
| `sounds.py` | Sound effects synthesised at run time |
| `board_logic.py` | Rules engine: moves, jumps, phases, win conditions, undo stack |
| `ai.py` | Minimax with alpha-beta pruning and the evaluation heuristic |
| `tests/` | pytest suite for the engine and the AI |
| `.github/workflows/tests.yml` | CI: tests on four Python versions, then the .exe build |
| `main.spec` | PyInstaller build definition |
| `*.png`, `outer_bg.jpg` | Board, piece and background art |
| `LICENSE` | MIT licence |
| `docs/` | Screenshots and the demo GIF used above |
| `CORRECTIONS.md` | Changelog of bugs found and fixed during review |

## Rules in brief

- Four tigers start in the corners. Goats move first and place one goat per
  turn until all 20 are on the board, then goats move one step along a line.
- Tigers move one step along a line, or jump over an adjacent goat onto the
  empty point behind it to capture it. One capture per turn.
- **Tigers win** by capturing 5 goats, or if the goats have no legal move.
- **Goats win** by trapping all four tigers so none can move.
- The same position occurring three times is a draw.
- Watch mode only: 100 moves in a row without a capture are called a draw,
  because nobody is at the board to agree one.

## How the AI scores a position

Positive is good for the tigers. The weights live at the top of `ai.py`.

| Term | Weight |
| --- | --- |
| Each captured goat | +500 |
| Each goat a tiger can jump right now | +150 |
| Each legal tiger move | +10 |
| Each trapped tiger | -250 |
| Tiger on the centre point | +25 |
| Win / loss | +10000 / -10000, plus remaining depth so nearer wins are preferred |

## License

MIT. See [LICENSE](LICENSE).
