# gui.py
import os
import random
import sys
import tkinter as tk
from PIL import Image, ImageOps, ImageTk
from board_logic import BaghChalLogic, EMPTY, TIGER, GOAT
from ai import (BaghChalAI, evaluate, score_breakdown,
                W_CAPTURE, W_THREAT, W_MOBILITY, W_TRAPPED, W_CENTER)
from sounds import SoundBoard


def resource_path(name):
    """Absolute path of a bundled file. Works when running from source AND from
    a PyInstaller build (where files live in sys._MEIPASS), regardless of the
    folder the program was launched from."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


_IMAGE_CACHE = {}


def load_image(name, size, keep_aspect=False):
    """Loads + resizes a PNG once per (name, size) and caches the Tk image.
    Returns None if the file is missing (the GUI then draws simple shapes).
    keep_aspect=True fits the picture inside a transparent square instead of
    stretching it (goat.png is 677x369, so stretching squashes the goat).
    keep_aspect=False cover-fits: the centre is cropped to the target aspect
    ratio and then resized, so textures such as inner_board.png (640x326)
    are never squashed into the square board."""
    key = (name, size, keep_aspect)
    if key not in _IMAGE_CACHE:
        path = resource_path(name)
        if not os.path.exists(path):
            _IMAGE_CACHE[key] = None
        else:
            img = Image.open(path).convert("RGBA")
            if keep_aspect:
                bbox = img.getbbox()          # drop transparent margin around the piece
                if bbox:
                    img = img.crop(bbox)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                square = Image.new("RGBA", size, (0, 0, 0, 0))
                square.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2), img)
                img = square
            else:
                img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
            _IMAGE_CACHE[key] = ImageTk.PhotoImage(img)
    return _IMAGE_CACHE[key]


CLICK_RADIUS = 40  # pixels: clicks further than this from an intersection are ignored
LEVEL_NAMES = {2: "Easy", 4: "Medium", 6: "Hard"}
SIDE_NAMES = {TIGER: "Tigers", GOAT: "Goats"}
GOLD = "#FFD700"      # the last move
DANGER = "#FF3B30"    # captures and goats under threat
WATCH_PAUSE_MS = 450  # gap between moves when the AI plays both sides
WATCH_DRAW_AFTER = 100  # AI against AI: moves in a row without a capture before it is called a draw


def new_session():
    """What one run of the program remembers from game to game: the running
    score and the player's Sound / Show threats switches."""
    return {'scores': {TIGER: 0, GOAT: 0, 'DRAW': 0}, 'sound': True, 'threats': True}


class BaghChalGUI:
    def __init__(self, root, mode, depth, on_menu_return, session=None):
        """mode is 'PVP' (two people), 'TIGER' or 'GOAT' (the side the human
        plays against the AI) or 'WATCH' (the AI plays both sides)."""
        self.root = root
        self.mode = mode
        self.depth = depth
        self.on_menu_return = on_menu_return
        self.session = session if session is not None else new_session()
        self.sounds = SoundBoard(enabled=self.session['sound'])
        self.rng = random.Random()
        self.root.title("Bagh Chal")

        # --- THEME COLORS ---
        self.bg_dark = "#2C1E16"
        self.panel_bg = "#DEB887"
        self.line_color = "#FFF8DC"
        self.text_color = "#3A2112"
        self.highlight = "#FF4500"

        self.root.configure(bg=self.bg_dark)

        # Every root.after job goes through later(), so all of them can be
        # cancelled when the game restarts or the screen is closed.
        self._jobs = set()
        self.ai_job = None
        self.animating = False
        self.paused = False
        self.confetti = []
        self.explain_win = None
        self.pause_btn = None

        w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.full_bg_img = load_image("outer_bg.jpg", (w, h))
        if self.full_bg_img:
            tk.Label(self.root, image=self.full_bg_img).place(x=0, y=0, relwidth=1, relheight=1)

        self.main_container = tk.Frame(self.root, bg=self.bg_dark)
        self.main_container.pack(padx=20, pady=20, expand=True)

        self.board_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        self.board_frame.grid(row=0, column=0, padx=10)

        self.ui_frame = tk.Frame(self.main_container, bg=self.panel_bg, bd=4, relief="ridge")
        self.ui_frame.grid(row=0, column=1, padx=10, sticky="ns")

        # --- BOARD ---
        self.margin = 90
        self.cell_size = 100
        self.board_width = (self.cell_size * 4) + (self.margin * 2)

        self.canvas = tk.Canvas(self.board_frame, width=self.board_width, height=self.board_width,
                                bg="#DEB887", highlightthickness=2, highlightbackground=self.line_color)
        self.canvas.pack()

        nav = tk.Frame(self.board_frame, bg=self.bg_dark)
        nav.pack(pady=15)
        nav_style = {"font": ("Arial", 12, "bold"), "bg": self.panel_bg, "fg": self.text_color}
        tk.Button(nav, text="Return to Main Menu", width=19, command=self.return_to_menu,
                  **nav_style).pack(side="left", padx=6)
        tk.Button(nav, text="New Game", width=11, command=self.new_game,
                  **nav_style).pack(side="left", padx=6)
        if mode in ('TIGER', 'GOAT'):
            tk.Button(nav, text="Swap Sides", width=11, command=lambda: self.new_game(swap=True),
                      **nav_style).pack(side="left", padx=6)
        elif mode == 'WATCH':
            self.pause_btn = tk.Button(nav, text="Pause", width=11, command=self.toggle_pause,
                                       **nav_style)
            self.pause_btn.pack(side="left", padx=6)

        # --- SIDE PANEL ---
        self.mode_label = tk.Label(self.ui_frame, text="", font=("Arial", 10, "bold"),
                                   bg=self.panel_bg, fg=self.text_color)
        self.mode_label.pack(pady=(8, 0))

        tk.Label(self.ui_frame, text="LIVE STRATEGY SCORE", font=("Arial", 14, "bold"),
                 bg=self.panel_bg, fg=self.text_color).pack(pady=(4, 2))

        self.score_label = tk.Label(self.ui_frame, text="", font=("Arial", 13, "bold"),
                                    bg=self.panel_bg, fg=self.highlight)
        self.score_label.pack(pady=2)

        # Progress of both sides: goats still in hand, goats eaten, tigers trapped
        self.tray = tk.Canvas(self.ui_frame, width=290, height=100, bg=self.panel_bg,
                              highlightthickness=0)
        self.tray.pack(pady=(4, 6))

        formula = (f"+{W_CAPTURE}/goat eaten   +{W_THREAT}/goat threatened\n"
                   f"+{W_MOBILITY}/tiger move   -{W_TRAPPED}/trapped tiger   +{W_CENTER} centre")
        tk.Label(self.ui_frame, text=formula, font=("Arial", 9, "bold"),
                 bg=self.panel_bg, fg=self.text_color, justify="center").pack()

        btn_frame = tk.Frame(self.ui_frame, bg=self.panel_bg)
        btn_frame.pack(pady=5)
        human_tools = "disabled" if mode == 'WATCH' else "normal"   # nobody to undo or hint for
        tk.Button(btn_frame, text="Undo", font=("Arial", 10, "bold"), bg="#FFB6C1", state=human_tools,
                  command=self.undo_action).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Hint", font=("Arial", 10, "bold"), bg="#98FB98", state=human_tools,
                  command=self.show_hint).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Explain AI Math", font=("Arial", 10, "bold"), bg="#FFD700",
                  command=self.show_ai_explanation).grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        self.sound_var = tk.BooleanVar(value=self.session['sound'])
        self.threat_var = tk.BooleanVar(value=self.session['threats'])
        switches = tk.Frame(self.ui_frame, bg=self.panel_bg)
        switches.pack()
        switch_style = {"font": ("Arial", 10, "bold"), "bg": self.panel_bg, "fg": self.text_color,
                        "activebackground": self.panel_bg, "selectcolor": "#FFF8DC"}
        tk.Checkbutton(switches, text="Sound", variable=self.sound_var,
                       command=self.on_sound_switch, **switch_style).grid(row=0, column=0, padx=8)
        tk.Checkbutton(switches, text="Show threats", variable=self.threat_var,
                       command=self.on_threat_switch, **switch_style).grid(row=0, column=1, padx=8)

        self.session_label = tk.Label(self.ui_frame, text="", font=("Arial", 10, "bold"),
                                      bg=self.panel_bg, fg=self.text_color)
        self.session_label.pack(pady=(4, 0))

        self.log_list = tk.Listbox(self.ui_frame, bg="#FFF8DC", fg=self.text_color,
                                   font=("Consolas", 10), width=38, height=12,
                                   selectbackground=self.highlight)
        self.log_list.pack(padx=15, pady=(8, 12))

        # --- IMAGES ---
        tiger_size = int(self.cell_size * 0.7)
        goat_size = int(self.cell_size * 0.9)     # goat.png is wide, so give it a bigger box to fit into
        self.board_bg_img = load_image("inner_board.png", (self.board_width, self.board_width))
        self.tiger_img = load_image("tiger.png", (tiger_size, tiger_size), keep_aspect=True)
        self.goat_img = load_image("goat.png", (goat_size, goat_size), keep_aspect=True)
        self.tiger_icon = load_image("tiger.png", (20, 20), keep_aspect=True)
        self.goat_icon = load_image("goat.png", (20, 20), keep_aspect=True)

        # --- INPUT ---
        self.canvas.bind("<Button-1>", self.on_click)
        self.keys = {"<Control-z>": self.undo_action, "<Control-Z>": self.undo_action,
                     "<Key-h>": self.show_hint, "<Key-H>": self.show_hint,
                     "<Key-m>": self.flip_sound, "<Key-M>": self.flip_sound,
                     "<Escape>": self.clear_selection}
        for sequence, action in self.keys.items():
            self.root.bind(sequence, lambda event, action=action: action())

        self.update_session_label()
        self.new_game()

    # ------------------------------------------------------------------ setup

    def make_ais(self):
        """The AI (or None for a human) behind each side, for the current mode."""
        def ai(side):
            return BaghChalAI(ai_player=side, depth=self.depth, rng=self.rng)
        if self.mode == 'PVP':
            return {TIGER: None, GOAT: None}
        if self.mode == 'TIGER':
            return {TIGER: None, GOAT: ai(GOAT)}
        if self.mode == 'GOAT':
            return {TIGER: ai(TIGER), GOAT: None}
        return {TIGER: ai(TIGER), GOAT: ai(GOAT)}

    def mode_text(self):
        level = LEVEL_NAMES.get(self.depth, f"depth {self.depth}")
        if self.mode == 'PVP':
            return "Two players on this computer"
        if self.mode == 'TIGER':
            return f"You: Tigers   vs   AI Goats ({level})"
        if self.mode == 'GOAT':
            return f"You: Goats   vs   AI Tigers ({level})"
        return f"AI Tigers   vs   AI Goats ({level})"

    def human_side(self):
        """The side the human plays against the AI, or None (two players / watch)."""
        return {'TIGER': TIGER, 'GOAT': GOAT}.get(self.mode)

    def new_game(self, swap=False):
        """Starts a fresh match on this screen. swap=True also trades sides with the AI."""
        self.cancel_all()
        if swap and self.mode in ('TIGER', 'GOAT'):
            self.mode = 'GOAT' if self.mode == 'TIGER' else 'TIGER'
        self.logic = BaghChalLogic()
        self.ais = self.make_ais()
        self.moves_played = []       # every real move, in step with logic.history
        self.selected_pos = None
        self.hint_move = None
        self.recorded = None         # result already added to the session score, if any
        self.quiet_moves = 0         # moves in a row without a placement or a capture
        self.paused = False
        if self.pause_btn is not None:
            self.pause_btn.config(text="Pause")
        if self.explain_win is not None and self.explain_win.winfo_exists():
            self.explain_win.destroy()
        self.mode_label.config(text=self.mode_text())
        self.log_list.delete(0, tk.END)
        self.log_move("--- MATCH STARTED ---")
        self.draw_board()
        self.schedule_ai(500)

    # ------------------------------------------------------------- scheduling

    def later(self, delay_ms, func, *args):
        """root.after, remembered so cancel_all() can stop it."""
        def run():
            self._jobs.discard(job)
            func(*args)
        job = self.root.after(delay_ms, run)
        self._jobs.add(job)
        return job

    def cancel_all(self):
        """Stops everything that is queued: the AI's move, a sliding piece,
        the result jingle and the confetti."""
        for job in self._jobs:
            self.root.after_cancel(job)
        self._jobs.clear()
        self.ai_job = None
        self.animating = False
        self.confetti = []

    def is_ai_turn(self):
        return self.ais[self.logic.turn] is not None

    def result(self):
        """TIGER, GOAT, 'DRAW' or None while the game is on. The rules decide,
        with one addition: a game the AI plays against itself is called a draw
        after WATCH_DRAW_AFTER moves without a capture. The side that is ahead
        steers clear of the threefold repetition, so with nobody at the board
        to offer a draw a level ending could go on for hours."""
        winner = self.logic.check_winner()
        if winner is None and self.mode == 'WATCH' and self.quiet_moves >= WATCH_DRAW_AFTER:
            return 'DRAW'
        return winner

    def schedule_ai(self, delay_ms=100):
        """Queue the AI's move if it is the AI's turn. Only one job is ever pending."""
        self.cancel_ai()
        if self.is_ai_turn() and not self.paused and self.result() is None:
            self.ai_job = self.later(delay_ms, self.play_ai_turn)

    def cancel_ai(self):
        if self.ai_job is not None:
            self.root.after_cancel(self.ai_job)
            self._jobs.discard(self.ai_job)
            self.ai_job = None

    def return_to_menu(self):
        self.cancel_all()
        for sequence in self.keys:
            self.root.unbind(sequence)
        self.on_menu_return()

    def toggle_pause(self):
        """Watch mode only: holds the AI-against-AI game between two moves."""
        self.paused = not self.paused
        self.pause_btn.config(text="Resume" if self.paused else "Pause")
        if self.paused:
            self.cancel_ai()
        else:
            self.schedule_ai()
        self.refresh()

    # ---------------------------------------------------------- small helpers

    def eval_text(self):
        score = evaluate(self.logic)
        side = "Tigers ahead" if score > 0 else "Goats ahead" if score < 0 else "balanced"
        return f"EVAL: {score:+d}  ({side})"

    def log_eval_change(self, old_score):
        diff = evaluate(self.logic) - old_score
        if diff != 0:
            self.log_move(f"   -> eval {diff:+d} pts ({'tigers' if diff > 0 else 'goats'} gained)")

    def log_move(self, msg):
        self.log_list.insert(tk.END, msg)
        self.log_list.yview(tk.END)

    def update_session_label(self):
        scores = self.session['scores']
        self.session_label.config(
            text=f"Session:  Tigers {scores[TIGER]}   Goats {scores[GOAT]}   Draws {scores['DRAW']}")

    def point_xy(self, row, col):
        return self.margin + col * self.cell_size, self.margin + row * self.cell_size

    def point_at(self, x, y):
        """The board point under a click, or None if the click is not near one."""
        col = round((x - self.margin) / self.cell_size)
        row = round((y - self.margin) / self.cell_size)
        if not (0 <= row <= 4 and 0 <= col <= 4):
            return None
        px, py = self.point_xy(row, col)
        if (x - px) ** 2 + (y - py) ** 2 > CLICK_RADIUS ** 2:
            return None
        return row, col

    def refresh(self):
        """Redraw, unless a piece is sliding (the slide ends with a redraw anyway)."""
        if not self.animating:
            self.draw_board()

    def on_sound_switch(self):
        self.session['sound'] = self.sounds.enabled = self.sound_var.get()
        self.sounds.play('select')

    def flip_sound(self):
        self.sound_var.set(not self.sound_var.get())
        self.on_sound_switch()

    def on_threat_switch(self):
        self.session['threats'] = self.threat_var.get()
        self.refresh()

    def clear_selection(self):
        if self.selected_pos is not None and not self.animating:
            self.selected_pos = None
            self.draw_board()

    # ---------------------------------------------------------------- drawing

    def draw_board(self, moving=False, hidden=None):
        """Redraws the whole board. moving=True draws the frame under a sliding
        piece: no markers, no result banner, and no piece on the point `hidden`."""
        c = self.canvas
        c.delete("all")
        self.confetti = []
        end_pos = self.margin + (4 * self.cell_size)
        mid = self.margin + (2 * self.cell_size)

        if self.board_bg_img:
            c.create_image(self.board_width // 2, self.board_width // 2, image=self.board_bg_img)
        else:
            c.create_rectangle(0, 0, self.board_width, self.board_width, fill="#DEB887")

        line_w = 4
        for i in range(5):
            pos = self.margin + (i * self.cell_size)
            c.create_line(self.margin, pos, end_pos, pos, width=line_w, fill=self.line_color)
            c.create_line(pos, self.margin, pos, end_pos, width=line_w, fill=self.line_color)
        c.create_line(self.margin, self.margin, end_pos, end_pos, width=line_w, fill=self.line_color)
        c.create_line(end_pos, self.margin, self.margin, end_pos, width=line_w, fill=self.line_color)
        c.create_polygon(mid, self.margin, end_pos, mid, mid, end_pos, self.margin, mid,
                         outline=self.line_color, fill="", width=line_w)

        if not moving:
            self.draw_last_move()
            if self.hint_move:
                points = [self.hint_move[1:3]] if self.hint_move[0] == 'PLACE' \
                    else [self.hint_move[1:3], self.hint_move[3:5]]
                for row, col in points:
                    px, py = self.point_xy(row, col)
                    c.create_oval(px - 40, py - 40, px + 40, py + 40,
                                  outline="#32CD32", width=5, dash=(5, 2))
            if self.selected_pos:
                px, py = self.point_xy(*self.selected_pos)
                c.create_oval(px - 35, py - 35, px + 35, py + 35, outline=self.highlight, width=4)

        for row in range(5):
            for col in range(5):
                piece = self.logic.get_piece(row, col)
                if piece != EMPTY and (row, col) != hidden:
                    self.draw_piece_at(*self.point_xy(row, col), piece)

        winner = None if moving else self.result()
        if not moving:
            if self.threat_var.get():
                self.draw_threats()
            if self.selected_pos:
                self.draw_destinations()

        # Status bar: whose turn on the left, the phase on the right
        if winner is not None:
            status = "Game over"
        else:
            status = f"Turn: {'TIGERS' if self.logic.turn == TIGER else 'GOATS'}"
            if self.is_ai_turn():
                status += "  (AI, paused)" if self.paused else "  (AI)"
            elif self.human_side() is not None:
                status += "  (you)"
        if self.logic.phase == 'PLACEMENT':
            phase = f"Placing goats: {self.logic.goats_placed}/20"
        else:
            phase = "Movement phase"
        c.create_rectangle(self.margin - 10, 15, end_pos + 10, 45, fill="#FFF8DC", outline=self.line_color)
        c.create_text(self.margin, 30, text=status, anchor="w", font=("Arial", 14, "bold"), fill=self.text_color)
        c.create_text(end_pos, 30, text=phase, anchor="e", font=("Arial", 10, "bold"), fill=self.text_color)

        if winner is not None:
            if winner == 'DRAW':
                win_text, color = "MATCH DRAW!", "#FF8C00"
            elif winner == TIGER:
                win_text, color = "TIGERS WIN!", "#DC143C"
            else:
                win_text, color = "GOATS WIN!", "#4169E1"
            c.create_rectangle(mid - 170, mid - 48, mid + 170, mid + 48,
                               fill="#FFF8DC", outline=color, width=5)
            c.create_text(mid, mid - 10, text=win_text, fill=color, font=("Arial", 22, "bold"))
            c.create_text(mid, mid + 26, text="New Game starts another match",
                          fill=self.text_color, font=("Arial", 10, "bold"))

        self.score_label.config(text=self.eval_text())
        self.draw_trays()

    def draw_piece_at(self, x, y, piece_type):
        """Draws one piece centred on canvas point (x, y) and returns the canvas item."""
        if piece_type == TIGER and self.tiger_img:
            return self.canvas.create_image(x, y, image=self.tiger_img)
        if piece_type == GOAT and self.goat_img:
            return self.canvas.create_image(x, y, image=self.goat_img)
        radius = 20
        color = "#000000" if piece_type == TIGER else "#FFFFFF"
        return self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                                       fill=color, outline=self.line_color, width=2)

    def draw_last_move(self):
        """Gold trail under the pieces: where the last move started and ended."""
        if not self.moves_played:
            return
        c = self.canvas
        move = self.moves_played[-1]
        x2, y2 = self.point_xy(*move[-2:])
        if move[0] != 'PLACE':
            x1, y1 = self.point_xy(move[1], move[2])
            c.create_line(x1, y1, x2, y2, width=8, fill=GOLD, capstyle="round")
            c.create_oval(x1 - 8, y1 - 8, x1 + 8, y1 + 8, fill=GOLD, outline="")
            if move[0] == 'JUMP':          # a cross where the captured goat stood
                mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                c.create_line(mx - 10, my - 10, mx + 10, my + 10, width=4, fill=DANGER)
                c.create_line(mx - 10, my + 10, mx + 10, my - 10, width=4, fill=DANGER)
        c.create_oval(x2 - 40, y2 - 40, x2 + 40, y2 + 40, outline=GOLD, width=4)

    def draw_threats(self):
        """A red '!' on every goat that can be captured right now and a
        TRAPPED tag under every tiger that cannot move."""
        c = self.canvas
        for row, col in self.logic.threatened_goats():
            px, py = self.point_xy(row, col)
            bx, by = px + 30, py - 24
            c.create_oval(bx - 10, by - 10, bx + 10, by + 10, fill=DANGER, outline="#FFFFFF", width=2)
            c.create_text(bx, by, text="!", fill="#FFFFFF", font=("Arial", 11, "bold"))
        for row, col in self.logic.trapped_tigers():
            px, py = self.point_xy(row, col)
            c.create_rectangle(px - 31, py + 28, px + 31, py + 44, fill="#4A4A4A", outline="#FFFFFF")
            c.create_text(px, py + 36, text="TRAPPED", fill="#FFFFFF", font=("Arial", 8, "bold"))

    def draw_destinations(self):
        """Where the selected piece may go: a green dot for a step, a red
        target for a capture plus a red ring on the goat that would be taken."""
        c = self.canvas
        for move in self.logic.legal_moves_from(*self.selected_pos):
            px, py = self.point_xy(move[3], move[4])
            if move[0] == 'JUMP':
                gx, gy = self.point_xy((move[1] + move[3]) // 2, (move[2] + move[4]) // 2)
                c.create_oval(gx - 38, gy - 38, gx + 38, gy + 38, outline=DANGER, width=4)
                c.create_oval(px - 16, py - 16, px + 16, py + 16, outline=DANGER, width=4)
                c.create_oval(px - 6, py - 6, px + 6, py + 6, fill=DANGER, outline="")
            else:
                c.create_oval(px - 10, py - 10, px + 10, py + 10, fill="#7CFC00",
                              outline=self.bg_dark, width=2)

    def draw_trays(self):
        """Side-panel meters: goats in hand, goats eaten (5 wins), tigers trapped (4 wins)."""
        t = self.tray
        t.delete("all")
        label_font = ("Arial", 10, "bold")
        placed, captured = self.logic.goats_placed, self.logic.goats_captured
        trapped = len(self.logic.trapped_tigers())

        if self.logic.phase == 'PLACEMENT':
            text = f"Goats to place: {20 - placed}"
        else:
            text = f"Goats on the board: {placed - captured}"
        t.create_text(6, 9, text=text, anchor="w", font=label_font, fill=self.text_color)
        for i in range(20):                       # one pip per goat, filled while still in hand
            x = 6 + i * 14
            if i < 20 - placed:
                t.create_oval(x, 20, x + 11, 31, fill="#FFF8DC", outline=self.text_color)
            else:
                t.create_oval(x, 20, x + 11, 31, fill="", outline="#B08D5E")

        rows = [(54, f"Captured: {captured} / 5", captured, 5, "#B22222", self.goat_icon),
                (82, f"Tigers trapped: {trapped} / 4", trapped, 4, "#4169E1", self.tiger_icon)]
        for y, text, filled, slots, color, icon in rows:
            t.create_text(6, y, text=text, anchor="w", font=label_font,
                          fill=color if filled else self.text_color)
            for i in range(slots):
                x = 166 + i * 27
                if i < filled:
                    t.create_oval(x - 12, y - 12, x + 12, y + 12, fill=color, outline="#FFF8DC", width=2)
                    if icon:
                        t.create_image(x, y, image=icon)
                else:
                    t.create_oval(x - 12, y - 12, x + 12, y + 12, fill="",
                                  outline=self.text_color, width=2, dash=(3, 3))

    # ------------------------------------------------------------------ moves

    def play_move(self, move, ai=None):
        """Plays a legal move for real (Undo history + repetition count), logs
        it and animates it. ai is the BaghChalAI that chose it, if any."""
        mover = self.logic.turn
        old_score = evaluate(self.logic)
        self.logic.apply_move(move)
        self.moves_played.append(move)
        self.quiet_moves = self.quiet_moves + 1 if move[0] == 'MOVE' else 0

        who = ("AI " if ai else "") + ("TIGER" if mover == TIGER else "GOAT")
        if move[0] == 'PLACE':
            self.log_move(f"{who} placed at ({move[1]}, {move[2]})")
        elif move[0] == 'JUMP':
            self.log_move(f"{who} captured ({move[1]},{move[2]}) -> ({move[3]},{move[4]})")
        else:
            self.log_move(f"{who} moved ({move[1]},{move[2]}) -> ({move[3]},{move[4]})")
        if ai:
            # --- ALPHA-BETA STATS ---
            self.log_move(f"⚡ Nodes checked: {ai.nodes_evaluated:,}")
            self.log_move(f"✂ Branches pruned: {ai.branches_pruned:,}")
        self.log_eval_change(old_score)

        self.selected_pos = None
        self.hint_move = None
        self.animate_move(move, mover)

    def animate_move(self, move, mover):
        """Shows the move that was just played: a pulse for a placed goat, a
        slide for a step, and a slide that removes the goat on the way for a
        capture. move_finished() runs when the last frame is done."""
        c = self.canvas
        if move[0] == 'PLACE':
            self.sounds.play('place')
            self.draw_board(moving=True)
            x, y = self.point_xy(move[1], move[2])
            ring = c.create_oval(x - 24, y - 24, x + 24, y + 24, outline=GOLD, width=4)

            def pulse(i):
                r = 24 + 5 * i
                c.coords(ring, x - r, y - r, x + r, y + r)
            self.run_frames(6, 20, pulse)
            return

        x1, y1 = self.point_xy(move[1], move[2])
        x2, y2 = self.point_xy(move[3], move[4])
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        self.draw_board(moving=True, hidden=(move[3], move[4]))
        victim = None
        if move[0] == 'JUMP':
            victim = self.draw_piece_at(mx, my, GOAT)    # stands until the tiger is over it
        else:
            self.sounds.play('move')
        slider = self.draw_piece_at(x1, y1, mover)
        frames = 14 if move[0] == 'JUMP' else 9
        at = [x1, y1]

        def slide(i):
            eased = 1 - (1 - i / frames) ** 2           # fast start, soft landing
            nx, ny = x1 + (x2 - x1) * eased, y1 + (y2 - y1) * eased
            c.move(slider, nx - at[0], ny - at[1])
            at[0], at[1] = nx, ny
            if victim is not None and i == frames // 2:
                c.delete(victim)
                self.sounds.play('capture')
                burst = c.create_oval(mx - 30, my - 30, mx + 30, my + 30, outline=DANGER, width=6)
                c.tag_lower(burst, slider)
        self.run_frames(frames, 16, slide)

    def run_frames(self, count, delay_ms, on_frame):
        """Calls on_frame(1..count) every delay_ms, then move_finished().
        Clicks are ignored while self.animating is set."""
        self.animating = True

        def step(i):
            if i > count:
                self.animating = False
                self.move_finished()
                return
            on_frame(i)
            self.later(delay_ms, step, i + 1)
        step(1)

    def move_finished(self):
        self.draw_board()
        if self.result() is not None:
            self.announce_result()
        else:
            self.schedule_ai(WATCH_PAUSE_MS if self.mode == 'WATCH' else 100)

    def announce_result(self):
        """Game over: counts the result in the session score once, plays the
        jingle and, when a human has something to celebrate, throws confetti."""
        winner = self.result()
        if winner is None or self.recorded is not None:
            return
        self.recorded = winner
        self.session['scores'][winner] += 1
        self.update_session_label()
        if winner == 'DRAW':
            if self.logic.check_winner() == 'DRAW':
                self.log_move("--- DRAW: position repeated 3x ---")
            else:
                self.log_move(f"--- DRAW: {WATCH_DRAW_AFTER} moves, no capture ---")
            jingle = 'draw'
        else:
            self.log_move(f"--- {SIDE_NAMES[winner].upper()} WIN ---")
            human = self.human_side()
            jingle = 'lose' if human is not None and human != winner else 'win'
            if jingle == 'win':
                self.start_confetti(winner)
        self.later(350, self.sounds.play, jingle)     # after the move's own sound

    def start_confetti(self, winner):
        if winner == TIGER:
            colours = [GOLD, "#FFF8DC", "#DC143C", "#FF8C00"]
        else:
            colours = [GOLD, "#FFF8DC", "#4169E1", "#32CD32"]
        self.confetti = []
        for _ in range(80):
            x = self.rng.uniform(0, self.board_width)
            y = self.rng.uniform(-260, -10)
            size = self.rng.randint(5, 10)
            item = self.canvas.create_rectangle(x, y, x + size, y + size * 0.6,
                                                fill=self.rng.choice(colours), outline="")
            self.confetti.append([item, self.rng.uniform(-1.2, 1.2), self.rng.uniform(3.0, 7.0)])
        self.confetti_step(0)

    def confetti_step(self, tick):
        if not self.confetti:
            return                      # the board was redrawn: the paper is gone
        if tick >= 110:
            for item, _, _ in self.confetti:
                self.canvas.delete(item)
            self.confetti = []
            return
        for piece in self.confetti:
            self.canvas.move(piece[0], piece[1], piece[2])
            piece[2] += 0.1             # gravity
        self.later(30, self.confetti_step, tick + 1)

    def play_ai_turn(self):
        self.ai_job = None
        if self.paused or not self.is_ai_turn() or self.result() is not None:
            return

        ai = self.ais[self.logic.turn]
        self.log_move("AI thinking...")
        self.root.config(cursor="watch")
        self.root.update_idletasks()   # redraw only: queued clicks wait for the search

        best_move = ai.get_best_move(self.logic)
        self.root.config(cursor="")

        if best_move is None:
            self.log_move("AI has no legal move.")
            self.draw_board()
            return
        self.play_move(best_move, ai=ai)

    def on_click(self, event):
        if self.animating or self.is_ai_turn() or self.result() is not None:
            return
        point = self.point_at(event.x, event.y)
        if point is None:
            return
        row, col = point

        if self.logic.phase == 'PLACEMENT' and self.logic.turn == GOAT:
            if self.logic.is_valid_placement(row, col):
                self.play_move(('PLACE', row, col))
            else:
                self.sounds.play('illegal')
            return

        if self.logic.get_piece(row, col) == self.logic.turn:
            # Own piece: select it, or put it down again if it was selected
            self.selected_pos = None if self.selected_pos == (row, col) else (row, col)
            if self.selected_pos:
                self.sounds.play('select')
            self.draw_board()
            return

        if self.selected_pos is None:
            return
        for move in self.logic.legal_moves_from(*self.selected_pos):
            if (move[3], move[4]) == (row, col):
                self.play_move(move)
                return
        r1, c1 = self.selected_pos
        self.sounds.play('illegal')
        self.log_move(f"Illegal move ({r1},{c1}) -> ({row},{col})")

    # ---------------------------------------------------------------- buttons

    def show_ai_explanation(self):
        # One analysis window at a time: close the previous one so its numbers
        # can never go stale behind a newer board.
        if self.explain_win is not None and self.explain_win.winfo_exists():
            self.explain_win.destroy()
        explain_win = tk.Toplevel(self.root)
        self.explain_win = explain_win
        explain_win.title("Minimax Algorithm Analysis")
        explain_win.geometry("470x560")
        explain_win.configure(bg=self.bg_dark)

        tk.Label(explain_win, text="Minimax Heuristic Breakdown", font=("Arial", 16, "bold"),
                 bg=self.bg_dark, fg=self.line_color).pack(pady=15)

        rows, total = score_breakdown(self.logic)   # the exact terms the search uses
        lines = ["HOW THE AI SCORES THIS EXACT BOARD", "(positive = good for Tigers)", ""]
        for i, (label, count, weight, points) in enumerate(rows, 1):
            lines.append(f"{i}. {label}: {count}")
            lines.append(f"   {count} x {weight:+d} = {points:+d}")
        lines += ["", "-" * 38, f"HEURISTIC SCORE: {total:+d}", "-" * 38, ""]
        winner = self.logic.check_winner()
        if winner is not None:
            lines.append("Game over: terminal score ±10000 applies.")
        lines += ["MINIMAX DECISION:",
                  "• Tigers (Maximiser) look ahead for the",
                  "  line that makes this score HIGHEST.",
                  "• Goats (Minimiser) look ahead for the",
                  "  line that makes it LOWEST.",
                  "• Alpha-Beta skips branches that cannot",
                  "  change the final choice."]

        tk.Label(explain_win, text="\n".join(lines), font=("Consolas", 11), bg=self.panel_bg,
                 fg=self.text_color, justify="left", padx=20, pady=20).pack(padx=20, pady=10, fill="both", expand=True)
        tk.Button(explain_win, text="Close Analysis", font=("Arial", 11, "bold"), bg="#FFF8DC",
                  command=explain_win.destroy).pack(pady=10)

    def undo_action(self):
        if self.mode == 'WATCH':
            return
        self.cancel_all()               # a pending AI move, a slide in progress, the confetti
        if self.logic.undo():
            self.moves_played.pop()
            # Against the AI, one click takes back the AI's reply AND your own move
            if self.is_ai_turn() and self.logic.undo():
                self.moves_played.pop()
            if self.recorded is not None:        # the finished game is live again
                self.session['scores'][self.recorded] -= 1
                self.recorded = None
                self.update_session_label()
            self.log_move("--- MOVE UNDONE ---")
        self.hint_move = None
        self.selected_pos = None
        self.draw_board()
        self.schedule_ai(300)   # only fires if it is (still) the AI's turn, e.g. its opening move was undone

    def show_hint(self):
        if (self.mode == 'WATCH' or self.animating or self.is_ai_turn()
                or self.result() is not None):
            return

        self.log_move("Hint: AI calculating...")
        self.root.config(cursor="watch")
        self.root.update_idletasks()   # redraw only: queued clicks wait for the search

        depth = 4 if self.mode == 'PVP' else self.depth      # as strong as the opponent
        hint_ai = BaghChalAI(ai_player=self.logic.turn, depth=depth)
        best_move = hint_ai.get_best_move(self.logic)
        self.root.config(cursor="")

        if best_move:
            self.hint_move = best_move
            self.draw_board()
            self.log_move("HINT: check the green highlight!")
