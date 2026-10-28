# gui.py
import os
import sys
import tkinter as tk
from PIL import Image, ImageOps, ImageTk
from board_logic import EMPTY, TIGER, GOAT
from ai import (BaghChalAI, evaluate, score_breakdown,
                W_CAPTURE, W_THREAT, W_MOBILITY, W_TRAPPED, W_CENTER)

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


class BaghChalGUI:
    def __init__(self, root, logic, ai, on_menu_return):
        self.root = root
        self.logic = logic
        self.ai = ai
        self.on_menu_return = on_menu_return
        self.root.title("Bagh Chal - College Project")

        # --- THEME COLORS ---
        self.bg_dark = "#2C1E16"
        self.panel_bg = "#DEB887"
        self.line_color = "#FFF8DC"
        self.text_color = "#3A2112"
        self.highlight = "#FF4500"

        self.root.configure(bg=self.bg_dark)
        self.selected_pos = None
        self.hint_move = None
        self.ai_job = None           

       
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

       
        self.margin = 90
        self.cell_size = 100
        self.board_width = (self.cell_size * 4) + (self.margin * 2)

        self.canvas = tk.Canvas(self.board_frame, width=self.board_width, height=self.board_width,
                                bg="#DEB887", highlightthickness=2, highlightbackground=self.line_color)
        self.canvas.pack()

        tk.Button(self.board_frame, text="Return to Main Menu", font=("Arial", 12, "bold"),
                  bg=self.panel_bg, fg=self.text_color, width=20, command=self.return_to_menu).pack(pady=15)

    
        tk.Label(self.ui_frame, text="LIVE STRATEGY SCORE", font=("Arial", 14, "bold"),
                 bg=self.panel_bg, fg=self.text_color).pack(pady=10)

        self.score_label = tk.Label(self.ui_frame, text="", font=("Arial", 13, "bold"),
                                    bg=self.panel_bg, fg=self.highlight)
        self.score_label.pack(pady=5)

        self.goat_stats_label = tk.Label(self.ui_frame, text="", font=("Arial", 11, "bold"),
                                         bg=self.panel_bg, fg=self.text_color)
        self.goat_stats_label.pack(pady=(0, 10))

         
        formula = (f"+{W_CAPTURE}/goat eaten   +{W_THREAT}/goat threatened\n"
                   f"+{W_MOBILITY}/tiger move   -{W_TRAPPED}/trapped tiger   +{W_CENTER} centre")
        tk.Label(self.ui_frame, text=formula, font=("Arial", 9, "bold"),
                 bg=self.panel_bg, fg=self.text_color, justify="center").pack()
 
        btn_frame = tk.Frame(self.ui_frame, bg=self.panel_bg)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Undo", font=("Arial", 10, "bold"), bg="#FFB6C1",
                  command=self.undo_action).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Hint", font=("Arial", 10, "bold"), bg="#98FB98",
                  command=self.show_hint).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Explain AI Math", font=("Arial", 10, "bold"), bg="#FFD700",
                  command=self.show_ai_explanation).grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        self.log_list = tk.Listbox(self.ui_frame, bg="#FFF8DC", fg=self.text_color,
                                   font=("Consolas", 10), width=38, height=18,
                                   selectbackground=self.highlight)
        self.log_list.pack(padx=15, pady=15)
        self.log_list.insert(tk.END, "--- MATCH STARTED ---")

       
        tiger_size = int(self.cell_size * 0.7)
        goat_size = int(self.cell_size * 0.9)     # goat.png is wide, so give it a bigger box to fit into
        self.board_bg_img = load_image("inner_board.png", (self.board_width, self.board_width))
        self.tiger_img = load_image("tiger.png", (tiger_size, tiger_size), keep_aspect=True)
        self.goat_img = load_image("goat.png", (goat_size, goat_size), keep_aspect=True)

        self.canvas.bind("<Button-1>", self.on_click)
        self.draw_board()
        self.schedule_ai(500)

  
    def is_ai_turn(self):
        return self.ai is not None and self.logic.turn == self.ai.ai_player

    def schedule_ai(self, delay_ms=100):
        """Queue the AI's move if it is the AI's turn. Only one job is ever pending."""
        self.cancel_ai()
        if self.is_ai_turn() and self.logic.check_winner() is None:
            self.ai_job = self.root.after(delay_ms, self.play_ai_turn)

    def cancel_ai(self):
        if self.ai_job is not None:
            self.root.after_cancel(self.ai_job)
            self.ai_job = None

    def return_to_menu(self):
        self.cancel_ai()          
        self.on_menu_return()
 
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
 
    def point_xy(self, row, col):
        return self.margin + col * self.cell_size, self.margin + row * self.cell_size

    def draw_board(self):
        self.canvas.delete("all")
        end_pos = self.margin + (4 * self.cell_size)

        if self.board_bg_img:
            self.canvas.create_image(self.board_width // 2, self.board_width // 2, image=self.board_bg_img)
        else:
            self.canvas.create_rectangle(0, 0, self.board_width, self.board_width, fill="#DEB887")

        line_w = 4
        for i in range(5):
            pos = self.margin + (i * self.cell_size)
            self.canvas.create_line(self.margin, pos, end_pos, pos, width=line_w, fill=self.line_color)
            self.canvas.create_line(pos, self.margin, pos, end_pos, width=line_w, fill=self.line_color)

        self.canvas.create_line(self.margin, self.margin, end_pos, end_pos, width=line_w, fill=self.line_color)
        self.canvas.create_line(end_pos, self.margin, self.margin, end_pos, width=line_w, fill=self.line_color)

        mid = self.margin + (2 * self.cell_size)
        self.canvas.create_polygon(mid, self.margin, end_pos, mid, mid, end_pos, self.margin, mid,
                                   outline=self.line_color, fill="", width=line_w)
 
        if self.hint_move:
            action = self.hint_move[0]
            if action == 'PLACE':
                px, py = self.point_xy(self.hint_move[1], self.hint_move[2])
                self.canvas.create_oval(px - 40, py - 40, px + 40, py + 40, outline="#32CD32", width=5, dash=(5, 2))
            else:
                r1, c1, r2, c2 = self.hint_move[1:5]
                for px, py in (self.point_xy(r1, c1), self.point_xy(r2, c2)):
                    self.canvas.create_oval(px - 40, py - 40, px + 40, py + 40, outline="#32CD32", width=5, dash=(5, 2))

        for row in range(5):
            for col in range(5):
                if self.selected_pos == (row, col):
                    px, py = self.point_xy(row, col)
                    self.canvas.create_oval(px - 35, py - 35, px + 35, py + 35, outline=self.highlight, width=4)
                piece = self.logic.get_piece(row, col)
                if piece != EMPTY:
                    self.draw_piece(row, col, piece)

 
        self.score_label.config(text=self.eval_text())
        placed = self.logic.goats_placed
        self.goat_stats_label.config(
            text=f"Placed: {placed}/20  |  Remaining: {20 - placed}  |  Killed: {self.logic.goats_captured}")

        status = f"Turn: {'TIGERS' if self.logic.turn == TIGER else 'GOATS'}"
        if self.is_ai_turn():
            status += "  (AI)"
        self.canvas.create_rectangle(self.margin - 10, 15, end_pos + 10, 45, fill="#FFF8DC", outline=self.line_color)
        self.canvas.create_text(self.margin, 30, text=status, anchor="w", font=("Arial", 14, "bold"), fill=self.text_color)

 
        winner = self.logic.check_winner()
        if winner is not None:
            if winner == 'DRAW':
                win_text, color = "MATCH DRAW!", "#FF8C00"
            elif winner == TIGER:
                win_text, color = "TIGERS WIN!", "#DC143C"
            else:
                win_text, color = "GOATS WIN!", "#4169E1"
            center_xy = self.margin + (2 * self.cell_size)
            self.canvas.create_rectangle(center_xy - 170, center_xy - 40, center_xy + 170, center_xy + 40,
                                         fill="#FFF8DC", outline=color, width=5)
            self.canvas.create_text(center_xy, center_xy, text=win_text, fill=color, font=("Arial", 22, "bold"))

    def draw_piece(self, row, col, piece_type):
        px, py = self.point_xy(row, col)
        if piece_type == TIGER and self.tiger_img:
            self.canvas.create_image(px, py, image=self.tiger_img)
        elif piece_type == GOAT and self.goat_img:
            self.canvas.create_image(px, py, image=self.goat_img)
        else:
            radius = 20
            color = "#000000" if piece_type == TIGER else "#FFFFFF"
            self.canvas.create_oval(px - radius, py - radius, px + radius, py + radius,
                                    fill=color, outline=self.line_color, width=2)
 
    def play_ai_turn(self):
        self.ai_job = None
        if self.logic.check_winner() is not None or not self.is_ai_turn():
            self.draw_board()
            return

 
        self.log_move("AI thinking...")
        self.root.config(cursor="watch")
        self.root.update_idletasks()   # redraw only: queued clicks wait for the search

        old_score = evaluate(self.logic)
        best_move = self.ai.get_best_move(self.logic)
        self.root.config(cursor="")

        if best_move is None:
            self.log_move("AI has no legal move.")
            self.draw_board()
            return

        self.logic.apply_move(best_move)      # real move: recorded for Undo and the draw rule
        actor = "TIGER" if self.ai.ai_player == TIGER else "GOAT"
        if best_move[0] == 'PLACE':
            self.log_move(f"AI GOAT placed at ({best_move[1]}, {best_move[2]})")
        elif best_move[0] == 'JUMP':
            self.log_move(f"AI TIGER jumped ({best_move[1]},{best_move[2]}) -> ({best_move[3]},{best_move[4]}) "
                          f"and captured a goat!")
        else:
            self.log_move(f"AI {actor} moved ({best_move[1]},{best_move[2]}) -> ({best_move[3]},{best_move[4]})")

        # --- ALPHA-BETA STATS ---
        self.log_move(f"⚡ Nodes checked: {self.ai.nodes_evaluated:,}")
        self.log_move(f"✂ Branches pruned: {self.ai.branches_pruned:,}")
        self.log_eval_change(old_score)

        self.selected_pos = None
        self.hint_move = None
        self.draw_board()

 
    def on_click(self, event):
        if self.logic.check_winner() is not None:
            return
        if self.is_ai_turn():
            return                      

        col = round((event.x - self.margin) / self.cell_size)
        row = round((event.y - self.margin) / self.cell_size)
        if not (0 <= row <= 4 and 0 <= col <= 4):
            return
        px, py = self.point_xy(row, col)
        if (event.x - px) ** 2 + (event.y - py) ** 2 > CLICK_RADIUS ** 2:
            return                      

        
        if self.logic.phase == 'PLACEMENT' and self.logic.turn == GOAT:
            old_score = evaluate(self.logic)
            if self.logic.place_goat(row, col):
                self.log_move(f"GOAT placed at ({row}, {col})")
                self.log_eval_change(old_score)
                self.hint_move = None
                self.draw_board()
                self.schedule_ai()
            return

  
        clicked_piece = self.logic.get_piece(row, col)

        if self.selected_pos is None:
            if clicked_piece == self.logic.turn:
                self.selected_pos = (row, col)
                self.draw_board()
            return

        r1, c1 = self.selected_pos
        if (r1, c1) == (row, col):
            self.selected_pos = None
            self.draw_board()
        elif clicked_piece == self.logic.turn:
            self.selected_pos = (row, col)
            self.draw_board()
        elif clicked_piece == EMPTY:
            old_score = evaluate(self.logic)
            actor = "TIGER" if self.logic.turn == TIGER else "GOAT"
            captured_before = self.logic.goats_captured
            if self.logic.move_piece(r1, c1, row, col):
                if self.logic.goats_captured > captured_before:
                    self.log_move(f"{actor} jumped ({r1},{c1}) -> ({row},{col}) and captured a goat!")
                else:
                    self.log_move(f"{actor} moved ({r1},{c1}) -> ({row},{col})")
                self.log_eval_change(old_score)
                self.selected_pos = None
                self.hint_move = None
                self.draw_board()
                self.schedule_ai()
            else:
                self.log_move(f"Illegal move ({r1},{c1}) -> ({row},{col})")

 
    def show_ai_explanation(self):
        explain_win = tk.Toplevel(self.root)
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
        self.cancel_ai()
        if not self.logic.undo():
            return
        # Against the AI, one click takes back the AI's reply AND your own move
        if self.ai is not None and self.is_ai_turn():
            self.logic.undo()
        self.hint_move = None
        self.selected_pos = None
        self.log_move("--- MOVE UNDONE ---")
        self.draw_board()
        self.schedule_ai(300)   # only fires if it is (still) the AI's turn, e.g. its opening move was undone

    def show_hint(self):
        if self.logic.check_winner() is not None or self.is_ai_turn():
            return

        self.log_move("Hint: AI calculating...")
        self.root.config(cursor="watch")
        self.root.update_idletasks()   # redraw only: queued clicks wait for the search

        depth = self.ai.max_depth if self.ai else 4      # as strong as the opponent
        hint_ai = BaghChalAI(ai_player=self.logic.turn, depth=depth)
        best_move = hint_ai.get_best_move(self.logic)
        self.root.config(cursor="")

        if best_move:
            self.hint_move = best_move
            self.draw_board()
            self.log_move("HINT: check the green highlight!")
