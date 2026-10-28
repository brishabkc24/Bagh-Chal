# Bagh Chal

A desktop version of **Bagh Chal** (Tigers and Goats), the traditional Nepali
board game, written in Python with Tkinter. Play against another person on the
same computer or against a minimax AI with alpha-beta pruning.

## Features

- **Local multiplayer** or **play as Tigers / play as Goats** against the AI
- Three AI levels: Easy (search depth 2), Medium (depth 4), Hard (depth 6)
- **Hint** button that asks the AI for the best move on your turn
- **Undo** (against the AI it takes back the AI's reply and your move)
- **Live strategy score** and an **Explain AI Math** window that shows the exact
  heuristic terms the search uses
- Move log with node and pruning counts for every AI move
- Threefold-repetition draw rule

## Requirements

- Python 3.10 or newer (tested on 3.13)
- Pillow (`pip install Pillow`)

Tkinter ships with the standard Python installer on Windows and macOS.

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

## Build a Windows .exe

PyInstaller is listed in `requirements.txt`. From the project folder:

```bash
python -m PyInstaller main.spec --noconfirm --clean
```

The single-file build appears at `dist\BaghChal.exe`. It bundles the four PNG
images, so it runs from any folder. The `dist` and `build` folders are ignored
by Git; publish the .exe through a GitHub Release instead of committing it.

## Project layout

| File | Purpose |
| --- | --- |
| `main.py` | Main menu, difficulty selection, rules window, program entry point |
| `gui.py` | Tkinter board, click handling, Undo / Hint / Explain, move log |
| `board_logic.py` | Rules engine: moves, jumps, phases, win conditions, undo stack |
| `ai.py` | Minimax with alpha-beta pruning and the evaluation heuristic |
| `main.spec` | PyInstaller build definition |
| `*.png` | Board, piece and background art |
| `CORRECTIONS.md` | Changelog of bugs found and fixed during review |

## Rules in brief

- Four tigers start in the corners. Goats move first and place one goat per
  turn until all 20 are on the board, then goats move one step along a line.
- Tigers move one step along a line, or jump over an adjacent goat onto the
  empty point behind it to capture it. One capture per turn.
- **Tigers win** by capturing 5 goats, or if the goats have no legal move.
- **Goats win** by trapping all four tigers so none can move.
- The same position occurring three times is a draw.

## How the AI scores a position

Positive is good for the tigers. The weights live at the top of `ai.py`.

| Term | Weight |
| --- | --- |
| Each captured goat | +500 |
| Each goat a tiger can jump right now | +150 |
| Each legal tiger move | +10 |
| Each trapped tiger | -250 |
| Tiger on the centre point | +25 |
| Win / loss | +10000 / -10000 (plus distance so nearer wins are preferred) |
