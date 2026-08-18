#!/usr/bin/env python3
"""
Chess — GUI version using tkinter (click to move).
Run: python3 chess.py
Requires Python 3.x with tkinter (standard on Windows, macOS, most Linux distros).
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from copy import deepcopy

# ─────────────────────────────────────────────────────────────────────────────
# Chess engine (pure Python, no dependencies)
# ─────────────────────────────────────────────────────────────────────────────

def empty_board():
    return [[None] * 8 for _ in range(8)]

def starting_board():
    b = empty_board()
    back = ['R','N','B','Q','K','B','N','R']
    for c, t in enumerate(back):
        b[0][c] = (t, 'b')
        b[1][c] = ('P', 'b')
        b[6][c] = ('P', 'w')
        b[7][c] = (t, 'w')
    return b

def opp(color):
    return 'b' if color == 'w' else 'w'

def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8

def raw_moves(board, r, c, en_passant):
    piece = board[r][c]
    if piece is None:
        return []
    t, color = piece
    moves = []

    def slide(dr, dc):
        nr, nc = r + dr, c + dc
        while in_bounds(nr, nc):
            target = board[nr][nc]
            if target is None:
                moves.append((nr, nc))
            elif target[1] != color:
                moves.append((nr, nc)); break
            else:
                break
            nr += dr; nc += dc

    def step(dr, dc):
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc):
            target = board[nr][nc]
            if target is None or target[1] != color:
                moves.append((nr, nc))

    if t == 'P':
        d = -1 if color == 'w' else 1
        sr = 6 if color == 'w' else 1
        nr = r + d
        if in_bounds(nr, c) and board[nr][c] is None:
            moves.append((nr, c))
            if r == sr and board[r + 2*d][c] is None:
                moves.append((r + 2*d, c))
        for dc in [-1, 1]:
            nr, nc = r + d, c + dc
            if in_bounds(nr, nc):
                target = board[nr][nc]
                if target and target[1] != color:
                    moves.append((nr, nc))
                if en_passant and (nr, nc) == en_passant:
                    moves.append((nr, nc))
    elif t == 'N':
        for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            step(dr, dc)
    elif t == 'B':
        for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]: slide(dr, dc)
    elif t == 'R':
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]: slide(dr, dc)
    elif t == 'Q':
        for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)]: slide(dr, dc)
    elif t == 'K':
        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]: step(dr, dc)
    return moves

def king_pos(board, color):
    for r in range(8):
        for c in range(8):
            if board[r][c] == ('K', color):
                return r, c
    return None

def in_check(board, color, en_passant=None):
    kp = king_pos(board, color)
    if kp is None:
        return True
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and p[1] == opp(color):
                if kp in raw_moves(board, r, c, en_passant):
                    return True
    return False

def _check_after(board, fr, fc, tr, tc, color):
    nb = deepcopy(board)
    nb[tr][tc] = nb[fr][fc]
    nb[fr][fc] = None
    return in_check(nb, color)

def legal_moves(board, r, c, en_passant, castling):
    """All moves for piece at (r,c) — no check-filtering; king can be captured."""
    piece = board[r][c]
    if piece is None:
        return []
    color = piece[1]
    moves = list(raw_moves(board, r, c, en_passant))
    # Castling: only requires clear squares, not safety checks
    if piece == ('K', color):
        row = 7 if color == 'w' else 0
        if r == row and c == 4:
            if castling.get((color,'K')) and board[row][5] is None and board[row][6] is None:
                moves.append((row, 6))
            if castling.get((color,'Q')) and board[row][3] is None and board[row][2] is None and board[row][1] is None:
                moves.append((row, 2))
    return moves

def all_legal_moves(board, color, en_passant, castling):
    moves = []
    for r in range(8):
        for c in range(8):
            if board[r][c] and board[r][c][1] == color:
                for nr, nc in legal_moves(board, r, c, en_passant, castling):
                    moves.append((r, c, nr, nc))
    return moves

def apply_move(board, fr, fc, tr, tc, en_passant, castling, promotion='Q'):
    board = deepcopy(board)
    castling = dict(castling)
    piece = board[fr][fc]
    t, color = piece
    new_ep = None
    if t == 'P' and board[tr][tc] is None and tc != fc:
        board[fr][tc] = None
    if t == 'P' and abs(tr - fr) == 2:
        new_ep = ((fr + tr) // 2, fc)
    if t == 'K':
        row = 7 if color == 'w' else 0
        if fc == 4 and tc == 6:
            board[row][5] = board[row][7]; board[row][7] = None
        elif fc == 4 and tc == 2:
            board[row][3] = board[row][0]; board[row][0] = None
        castling[(color,'K')] = False
        castling[(color,'Q')] = False
    if t == 'R':
        if fr == (7 if color == 'w' else 0):
            if fc == 0: castling[(color,'Q')] = False
            if fc == 7: castling[(color,'K')] = False
    board[tr][tc] = piece
    board[fr][fc] = None
    if t == 'P' and (tr == 0 or tr == 7):
        board[tr][tc] = (promotion, color)
    return board, new_ep, castling

def sq_name(r, c):
    return f"{'abcdefgh'[c]}{8 - r}"

# ─────────────────────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────────────────────

UNICODE = {
    ('K','w'):'♔',('Q','w'):'♕',('R','w'):'♖',
    ('B','w'):'♗',('N','w'):'♘',('P','w'):'♙',
    ('K','b'):'♚',('Q','b'):'♛',('R','b'):'♜',
    ('B','b'):'♝',('N','b'):'♞',('P','b'):'♟',
}

# Palette
C_LIGHT   = '#F0D9B5'   # classic light square
C_DARK    = '#B58863'   # classic dark square
C_SEL     = '#7FC97F'   # selected piece (green)
C_HINT    = '#CDD16E'   # legal move dot (yellow-green)
C_LAST    = '#AAC244'   # last move highlight
C_CHECK   = '#E84040'   # king in check
C_BG      = '#2B2B2B'   # window background
C_PANEL   = '#1E1E1E'   # side panel
C_TEXT    = '#EEEEEE'
C_SUBTEXT = '#999999'
C_BTN     = '#3A3A3A'
C_BTN_H   = '#505050'

SQ  = 80          # square size in px
PAD = 24          # board padding
PIECE_FONT_SIZE = 46

class ChessApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Chess')
        self.resizable(False, False)
        self.configure(bg=C_BG)

        self._init_state()
        self._build_ui()
        self._draw_board()
        self._update_status()

    # ── State ────────────────────────────────────────────────────────────────
    def _init_state(self):
        self.board      = starting_board()
        self.en_passant = None
        self.castling   = {('w','K'):True,('w','Q'):True,('b','K'):True,('b','Q'):True}
        self.turn       = 'w'
        self.selected   = None   # (r, c) of selected piece
        self.hints      = []     # legal move squares for selected piece
        self.last_move  = None   # (fr, fc, tr, tc)
        self.half_moves = 0
        self.pos_history = []
        self.move_log   = []     # [(white_move_str, black_move_str), ...]
        self.game_over  = False

    # ── UI layout ────────────────────────────────────────────────────────────
    def _build_ui(self):
        board_px = SQ * 8 + PAD * 2
        panel_w  = 220

        # Left: board canvas
        self.canvas = tk.Canvas(self, width=board_px, height=board_px + 4,
                                bg=C_BG, highlightthickness=0)
        self.canvas.pack(side='left', padx=(12, 0), pady=12)
        self.canvas.bind('<Button-1>', self._on_click)

        # Right: panel
        panel = tk.Frame(self, bg=C_PANEL, width=panel_w)
        panel.pack(side='right', fill='both', expand=True, padx=12, pady=12)
        panel.pack_propagate(False)

        # Title
        tk.Label(panel, text='♟  CHESS', font=('Helvetica', 18, 'bold'),
                 bg=C_PANEL, fg=C_TEXT).pack(pady=(18, 4))

        # Status
        self.status_var = tk.StringVar(value="White to move")
        self.status_lbl = tk.Label(panel, textvariable=self.status_var,
                                   font=('Helvetica', 12), bg=C_PANEL, fg='#7EC97F',
                                   wraplength=panel_w - 20)
        self.status_lbl.pack(pady=(0, 14))

        sep = tk.Frame(panel, height=1, bg='#444'); sep.pack(fill='x', padx=12, pady=4)

        # Move log
        tk.Label(panel, text='Move history', font=('Helvetica', 9, 'bold'),
                 bg=C_PANEL, fg=C_SUBTEXT).pack(anchor='w', padx=14, pady=(6,2))

        log_frame = tk.Frame(panel, bg=C_PANEL)
        log_frame.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side='right', fill='y')
        self.log_box = tk.Text(log_frame, width=20, font=('Courier', 10),
                               bg='#2A2A2A', fg=C_TEXT, relief='flat',
                               state='disabled', yscrollcommand=scrollbar.set,
                               selectbackground='#444', insertbackground=C_TEXT)
        self.log_box.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.log_box.yview)
        # colour tags
        self.log_box.tag_config('num',  foreground=C_SUBTEXT)
        self.log_box.tag_config('wmove', foreground='#EEEEEE')
        self.log_box.tag_config('bmove', foreground='#AAAAAA')

        sep2 = tk.Frame(panel, height=1, bg='#444'); sep2.pack(fill='x', padx=12, pady=4)

        # Buttons
        btn_cfg = dict(bg=C_BTN, fg=C_TEXT, font=('Helvetica', 10),
                       relief='flat', cursor='hand2', pady=6)
        tk.Button(panel, text='New Game',  command=self._new_game,  **btn_cfg)\
            .pack(fill='x', padx=14, pady=3)
        tk.Button(panel, text='Resign',    command=self._resign,    **btn_cfg)\
            .pack(fill='x', padx=14, pady=3)
        tk.Button(panel, text='Offer Draw',command=self._offer_draw,**btn_cfg)\
            .pack(fill='x', padx=14, pady=(3,14))

    # ── Drawing ──────────────────────────────────────────────────────────────
    def _draw_board(self):
        self.canvas.delete('all')
        board = self.board
        sel   = self.selected
        hints = set(self.hints)
        last  = set()
        if self.last_move:
            last = {(self.last_move[0], self.last_move[1]),
                    (self.last_move[2], self.last_move[3])}

        for r in range(8):
            for c in range(8):
                x1 = PAD + c * SQ
                y1 = PAD + r * SQ
                x2, y2 = x1 + SQ, y1 + SQ

                is_light = (r + c) % 2 == 0
                base = C_LIGHT if is_light else C_DARK
                if (r, c) == sel:
                    color = C_SEL
                elif (r, c) in last:
                    color = C_LAST
                else:
                    color = base

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='')

                # Dot for legal-move hints
                if (r, c) in hints:
                    piece_here = board[r][c]
                    if piece_here and piece_here[1] == opp(self.turn):
                        # Capture ring
                        self.canvas.create_oval(x1+3, y1+3, x2-3, y2-3,
                                                outline=C_HINT, width=4, fill='')
                    else:
                        # Move dot
                        cx, cy = (x1+x2)//2, (y1+y2)//2
                        r2 = SQ // 6
                        self.canvas.create_oval(cx-r2, cy-r2, cx+r2, cy+r2,
                                                fill=C_HINT, outline='')

                # Piece glyph
                piece = board[r][c]
                if piece:
                    glyph = UNICODE[piece]
                    fg = '#FFFFFF' if piece[1] == 'w' else '#1A1A1A'
                    # Shadow for readability
                    cx, cy = (x1+x2)//2, (y1+y2)//2
                    self.canvas.create_text(cx+1, cy+1, text=glyph,
                                            font=('Arial', PIECE_FONT_SIZE),
                                            fill='#333333')
                    self.canvas.create_text(cx, cy, text=glyph,
                                            font=('Arial', PIECE_FONT_SIZE),
                                            fill=fg)

        # Rank / file labels
        label_font = ('Helvetica', 9, 'bold')
        for i in range(8):
            file_lbl = 'abcdefgh'[i]
            rank_lbl = str(8 - i)
            # Files (bottom)
            self.canvas.create_text(PAD + i*SQ + SQ//2, PAD + 8*SQ + 10,
                                    text=file_lbl, font=label_font, fill=C_SUBTEXT)
            # Ranks (left)
            self.canvas.create_text(PAD - 10, PAD + i*SQ + SQ//2,
                                    text=rank_lbl, font=label_font, fill=C_SUBTEXT)

    # ── Click handling ───────────────────────────────────────────────────────
    def _on_click(self, event):
        if self.game_over:
            return
        c = (event.x - PAD) // SQ
        r = (event.y - PAD) // SQ
        if not (0 <= r < 8 and 0 <= c < 8):
            return

        piece = self.board[r][c]

        # Nothing selected yet → select own piece
        if self.selected is None:
            if piece and piece[1] == self.turn:
                self.selected = (r, c)
                self.hints = legal_moves(self.board, r, c, self.en_passant, self.castling)
        else:
            fr, fc = self.selected
            # Click same square → deselect
            if (r, c) == (fr, fc):
                self.selected = None; self.hints = []
            # Click another own piece → re-select
            elif piece and piece[1] == self.turn:
                self.selected = (r, c)
                self.hints = legal_moves(self.board, r, c, self.en_passant, self.castling)
            # Attempt move
            elif (r, c) in self.hints:
                self._do_move(fr, fc, r, c)
            else:
                self.selected = None; self.hints = []

        self._draw_board()

    def _do_move(self, fr, fc, tr, tc):
        promotion = 'Q'
        # Pawn promotion dialog
        piece = self.board[fr][fc]
        if piece[0] == 'P' and (tr == 0 or tr == 7):
            promotion = self._ask_promotion(piece[1])

        # Record move string before applying
        move_str = sq_name(fr, fc) + sq_name(tr, tc)
        if piece[0] == 'P' and (tr == 0 or tr == 7):
            move_str += promotion.lower()

        prev_board = self.board
        self.board, self.en_passant, self.castling = apply_move(
            self.board, fr, fc, tr, tc, self.en_passant, self.castling, promotion)
        self.last_move = (fr, fc, tr, tc)
        self.selected  = None
        self.hints     = []

        # Half-move clock
        if piece[0] == 'P' or prev_board[tr][tc] is not None:
            self.half_moves = 0
        else:
            self.half_moves += 1

        # Did we just capture the enemy king?
        captured_king = king_pos(self.board, opp(self.turn)) is None

        self._log_move(move_str)

        if captured_king:
            winner = 'White' if self.turn == 'w' else 'Black'
            self._draw_board()
            self.game_over = True
            self.status_var.set(f'{winner} captured the king! 🏆')
            self.status_lbl.config(fg='#E8A040')
            messagebox.showinfo('Game over', f'{winner} captured the king!')
            return

        self.turn = opp(self.turn)
        self._update_status()
        self._check_game_over()

    def _ask_promotion(self, color):
        choices = {'Queen':'Q','Rook':'R','Bishop':'B','Knight':'N'}
        dialog = tk.Toplevel(self)
        dialog.title('Promote pawn')
        dialog.configure(bg=C_BG)
        dialog.resizable(False, False)
        dialog.grab_set()
        chosen = tk.StringVar(value='Q')
        tk.Label(dialog, text='Choose promotion piece:',
                 bg=C_BG, fg=C_TEXT, font=('Helvetica', 12)).pack(pady=(16,8))
        for label, val in choices.items():
            glyph = UNICODE[(val, color)]
            tk.Radiobutton(dialog, text=f'  {glyph}  {label}', variable=chosen,
                           value=val, bg=C_BG, fg=C_TEXT, selectcolor='#444',
                           font=('Helvetica', 13), activebackground=C_BG,
                           activeforeground=C_TEXT).pack(anchor='w', padx=24)
        tk.Button(dialog, text='OK', command=dialog.destroy,
                  bg=C_BTN, fg=C_TEXT, font=('Helvetica', 11),
                  relief='flat', padx=20, pady=6).pack(pady=14)
        self.wait_window(dialog)
        return chosen.get()

    # ── Game state ───────────────────────────────────────────────────────────
    def _check_game_over(self):
        # Only king capture ends the game (handled in _do_move).
        # Keep 50-move draw as the sole draw condition.
        if self.half_moves >= 100:
            self.game_over = True
            self.status_var.set('Draw — 50-move rule 🤝')
            messagebox.showinfo('Game over', 'Draw by 50-move rule.')

    def _update_status(self):
        if self.game_over:
            return
        name = 'White' if self.turn == 'w' else 'Black'
        self.status_var.set(f'{name} to move')
        self.status_lbl.config(fg='#7EC97F')

    # ── Move log ─────────────────────────────────────────────────────────────
    def _log_move(self, move_str):
        self.move_log.append(move_str)
        self.log_box.config(state='normal')
        n = len(self.move_log)
        if n % 2 == 1:
            move_num = (n + 1) // 2
            self.log_box.insert('end', f'{move_num:>3}. ', 'num')
            self.log_box.insert('end', f'{move_str:<8}', 'wmove')
        else:
            self.log_box.insert('end', f'{move_str}\n', 'bmove')
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    # ── Buttons ──────────────────────────────────────────────────────────────
    def _new_game(self):
        if not self.game_over:
            if not messagebox.askyesno('New game', 'Abandon current game and start over?'):
                return
        self._init_state()
        self.log_box.config(state='normal')
        self.log_box.delete('1.0', 'end')
        self.log_box.config(state='disabled')
        self.status_lbl.config(fg='#7EC97F')
        self._draw_board()
        self._update_status()

    def _resign(self):
        if self.game_over: return
        name = 'White' if self.turn == 'w' else 'Black'
        winner = 'Black' if self.turn == 'w' else 'White'
        if messagebox.askyesno('Resign', f'{name} resigns?'):
            self.game_over = True
            self.status_var.set(f'{name} resigned. {winner} wins 🏆')
            self.status_lbl.config(fg='#E8A040')

    def _offer_draw(self):
        if self.game_over: return
        name = 'White' if self.turn == 'w' else 'Black'
        opp_name = 'Black' if self.turn == 'w' else 'White'
        if messagebox.askyesno('Draw offer', f'{name} offers a draw. Does {opp_name} accept?'):
            self.game_over = True
            self.status_var.set("Draw agreed 🤝")
            self.status_lbl.config(fg='#7EC97F')


if __name__ == '__main__':
    app = ChessApp()
    app.mainloop()