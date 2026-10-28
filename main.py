# main.py
import tkinter as tk
from board_logic import BaghChalLogic, TIGER, GOAT
from gui import BaghChalGUI, load_image
from ai import BaghChalAI, W_CAPTURE, W_THREAT, W_MOBILITY, W_TRAPPED, W_CENTER


class MainMenu:
    def __init__(self, root):
        self.root = root
        self.bg_image = None
        self.app = None
        self.ai_depth = tk.IntVar(value=4)
        self.draw_menu()

    def draw_menu(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.app = None

        self.root.title("Bagh Chal")
        w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}")
        try:
            self.root.state('zoomed')      
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)    
            except tk.TclError:
                pass
            
        self.bg_image = load_image("outer_bg.jpg", (w, h))
        if self.bg_image:
            tk.Label(self.root, image=self.bg_image).place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self.root.configure(bg="#2C1E16")

        menu_frame = tk.Frame(self.root, bg="#DEB887", bd=6, relief="ridge", padx=30, pady=30)
        menu_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(menu_frame, text="Bagh Chal", font=("Arial", 28, "bold"), bg="#DEB887", fg="#3A2112").pack(pady=(0, 20))

        #DIFFICULTY BUTTONS
        tk.Label(menu_frame, text="Select AI Difficulty:", bg="#DEB887", font=("Arial", 12, "bold"), fg="#3A2112").pack(pady=(5, 5))
        diff_frame = tk.Frame(menu_frame, bg="#DEB887")
        diff_frame.pack(pady=(0, 15))

        def set_difficulty(val):
            self.ai_depth.set(val)
            update_diff_buttons()

        self.btn_easy = tk.Button(diff_frame, text="Easy\n(Depth 2)", font=("Arial", 10, "bold"), width=12, command=lambda: set_difficulty(2))
        self.btn_easy.pack(side="left", padx=5)

        self.btn_med = tk.Button(diff_frame, text="Medium\n(Depth 4)", font=("Arial", 10, "bold"), width=12, command=lambda: set_difficulty(4))
        self.btn_med.pack(side="left", padx=5)

        self.btn_hard = tk.Button(diff_frame, text="Hard\n(Depth 6)", font=("Arial", 10, "bold"), width=12, command=lambda: set_difficulty(6))
        self.btn_hard.pack(side="left", padx=5)

        def update_diff_buttons():
            val = self.ai_depth.get()
            self.btn_easy.config(bg="#32CD32" if val == 2 else "#FFF8DC", fg="white" if val == 2 else "#3A2112")
            self.btn_med.config(bg="#FF8C00" if val == 4 else "#FFF8DC", fg="white" if val == 4 else "#3A2112")
            self.btn_hard.config(bg="#DC143C" if val == 6 else "#FFF8DC", fg="white" if val == 6 else "#3A2112")

        update_diff_buttons()

        #MAIN GAME BUTTONS
        btn_style = {"width": 25, "height": 2, "font": ("Arial", 11, "bold"), "bg": "#FFF8DC", "fg": "#3A2112"}
        tk.Button(menu_frame, text="Local Multiplayer (PvP)", command=lambda: self.start_game("PVP"), **btn_style).pack(pady=5)
        tk.Button(menu_frame, text="Play as Tigers (vs AI Goats)", command=lambda: self.start_game("TIGER"), **btn_style).pack(pady=5)
        tk.Button(menu_frame, text="Play as Goats (vs AI Tigers)", command=lambda: self.start_game("GOAT"), **btn_style).pack(pady=5)
        tk.Button(menu_frame, text="How to Play / Rules", command=self.show_rules, **btn_style).pack(pady=15)

    def start_game(self, mode):
        for widget in self.root.winfo_children():
            widget.destroy()

        logic = BaghChalLogic()
        selected_depth = self.ai_depth.get()

        if mode == "PVP":
            ai = None
        elif mode == "TIGER":
            ai = BaghChalAI(ai_player=GOAT, depth=selected_depth)   # human = tigers
        else:
            ai = BaghChalAI(ai_player=TIGER, depth=selected_depth)  # human = goats

        self.app = BaghChalGUI(self.root, logic, ai, on_menu_return=self.draw_menu)

    def show_rules(self):
        rules_window = tk.Toplevel(self.root)
        rules_window.title("How to Play Bagh Chal")
        rules_window.geometry("520x680")

        rules_text = (
            "=== THE GOAL ===\n"
            "• Tigers win by capturing 5 goats.\n"
            "• Goats win by trapping all 4 tigers so that none of them can move.\n\n"

            "=== PLAYING AS TIGERS ===\n"
            "1. Click a tiger, then click an adjacent empty point to move along a line.\n"
            "2. Capturing: if a goat is next to a tiger and the point directly behind the goat "
            "is empty, click that point to jump over the goat and remove it. One capture per turn.\n"
            "3. Tigers move from the very first turn, while the goats are still being placed.\n\n"

            "=== PLAYING AS GOATS ===\n"
            "1. Placement: drop all 20 goats onto empty points, one per turn.\n"
            "2. Movement: once all 20 are placed, click a goat and then an adjacent empty point.\n"
            "3. Goats never capture - they win by surrounding the tigers.\n\n"

            "=== OTHER RULES ===\n"
            "• If the goats have no legal move on their turn, the tigers win.\n"
            "• If the same position appears three times, the match is a draw.\n\n"

            "=== LIVE STRATEGY SCORE ===\n"
            "The AI's own heuristic, from the tigers' point of view (+ favours tigers):\n"
            f"  +{W_CAPTURE} per captured goat     +{W_THREAT} per goat a tiger can jump now\n"
            f"  +{W_MOBILITY} per legal tiger move      -{W_TRAPPED} per trapped tiger\n"
            f"  +{W_CENTER} for a tiger on the centre point\n"
            "A win or loss scores ±10000."
        )
        tk.Label(rules_window, text=rules_text, font=("Arial", 11), justify="left", wraplength=480).pack(padx=15, pady=15)
        tk.Button(rules_window, text="Close", width=15, command=rules_window.destroy).pack(pady=10)


def main():
    root = tk.Tk()
    root.main_menu = MainMenu(root) 
    root.mainloop()


if __name__ == "__main__":
    main()
