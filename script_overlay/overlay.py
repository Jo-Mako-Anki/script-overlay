# -*- coding: utf-8 -*-
"""Text window on top of the game (borderless / windowed games).

It never takes the keyboard or the mouse focus from the game, and it is left out of screen captures
(so the OCR, OBS and screenshots do not see it).

  left-drag: move            drag the left or right edge: width
  mouse wheel on the Japanese or the English: size of that text
  right-click: menu          mouse over a word: its meaning (JMdict)
"""
import ctypes, queue, tkinter as tk, tkinter.font as tkfont

BG = '#14161b'; FG = '#eceef2'; FG_EN = '#b9c3d6'; ACCENT = '#e5383b'; DIM = '#8a919c'
JP_FONT = 'Yu Gothic UI'; EN_FONT = 'Segoe UI'
DEFAULTS = {'t': 24, 'ten': 18, 'jp': True, 'en': True, 'kanji': True, 'furi': True, 'dico': True,
            'speaker': True, 'alpha': 0.88}
DISPLAY = ('jp', 'en', 'speaker', 'kanji', 'furi', 'dico')  # set per game (also from the web page)


MENU_OPEN = [False]  # True while the right-click menu is open: the OCR must not read the menu itself
CAPTURABLE = [False]  # True: the window shows up in screenshots (demo); False: hidden from captures (OCR never reads it)


def no_focus(win):
    """The window never takes the focus (the game keeps keyboard and pad) and is not captured."""
    try:
        u = ctypes.windll.user32
        hwnd = u.GetParent(win.winfo_id()) or win.winfo_id()
        GWL_EXSTYLE = -20; WS_EX_NOACTIVATE = 0x08000000; WS_EX_TOOLWINDOW = 0x80; WS_EX_TOPMOST = 0x8
        u.SetWindowLongW(hwnd, GWL_EXSTYLE, u.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)
        u.SetWindowDisplayAffinity(hwnd, 0 if CAPTURABLE[0] else 0x11)  # 0x11 = WDA_EXCLUDEFROMCAPTURE (Windows 10 2004+)
    except Exception:
        pass


def set_capturable(win):
    """Only changes the capture flag (demo screenshots); any error goes to data/logs/crash.txt instead of killing the app."""
    try:
        u = ctypes.windll.user32
        u.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]; u.GetAncestor.restype = ctypes.c_void_p
        hwnd = u.GetAncestor(win.winfo_id(), 2) or win.winfo_id()  # GA_ROOT
        ok = u.SetWindowDisplayAffinity(hwnd, 0 if CAPTURABLE[0] else 0x11)
        if not ok:
            raise OSError('SetWindowDisplayAffinity failed, error %d' % ctypes.GetLastError())
    except Exception:
        import traceback
        from .paths import data
        open(data('logs', 'crash.txt'), 'a', encoding='utf-8').write(traceback.format_exc() + '\n')


class Overlay:
    def __init__(self, root, title, prefs, events, on_close, extra_menu=(), game_prefs=None, on_display=None):
        """events: queue of ('line', dict) / ('status', str) / ('nomatch', text, score) / ('display', dict).
        prefs: dict saved by the caller (size, position, look); game_prefs: what to show for this game (DISPLAY keys);
        on_display(dict) is called when they change from the menu. extra_menu: [(label, command), ...]."""
        self.game_prefs = game_prefs if game_prefs is not None else {}; self.on_display = on_display
        self.P = dict(DEFAULTS); self.P.update(prefs); self.P.update(self.game_prefs); self.prefs = prefs
        self.events = events; self.on_close = on_close; self.alive = True
        self.line = None; self.status_text = 'Waiting for game text…'
        win = self.win = tk.Toplevel(root); win.title(title)
        win.overrideredirect(True); win.attributes('-topmost', True); win.attributes('-alpha', self.P['alpha'])
        self.W = win.winfo_screenwidth(); self.H = win.winfo_screenheight()
        self.larg = self.P.get('larg', int(self.W * 0.6))
        win.geometry('%dx10+%d+%d' % (self.larg, self.P.get('x', (self.W - self.larg) // 2), self.P.get('y', 20)))
        win.configure(bg=BG)
        fr = self.frame = tk.Frame(win, bg=BG, highlightthickness=2, highlightbackground=ACCENT)
        fr.pack(fill='both', expand=True)
        self.who = tk.Label(fr, bg=BG, fg=ACCENT, anchor='w', justify='left')
        self.jp = tk.Canvas(fr, bg=BG, highlightthickness=0, height=40)
        self.en = tk.Label(fr, bg=BG, fg=FG_EN, anchor='w', justify='left')
        self.st = tk.Label(fr, bg=BG, fg=DIM, anchor='w', justify='left')
        self.tip = None
        self.build_menu(extra_menu)
        for w in (win, fr, self.who, self.jp, self.en, self.st):
            w.bind('<Motion>', self.hover); w.bind('<ButtonPress-1>', self.press)
            w.bind('<B1-Motion>', self.drag); w.bind('<ButtonRelease-1>', lambda e: self.save())
            w.bind('<MouseWheel>', self.wheel); w.bind('<Button-3>', self.popup)
        win.update_idletasks(); no_focus(win); self.layout()
        win.after(100, self.poll)

    # ------------------------------------------------------------ menu and settings
    def build_menu(self, extra):
        m = self.menu = tk.Menu(self.win, tearoff=0)
        self.vars = {}
        def check(label, key):
            v = self.vars[key] = tk.BooleanVar(value=self.P[key])
            m.add_checkbutton(label=label, variable=v, command=lambda: self.set_display({key: v.get()}, True))
        m.add_command(label='Japanese: bigger', command=lambda: self.size('t', 2))
        m.add_command(label='Japanese: smaller', command=lambda: self.size('t', -2))
        m.add_command(label='English: bigger', command=lambda: self.size('ten', 2))
        m.add_command(label='English: smaller', command=lambda: self.size('ten', -2))
        m.add_separator()
        check('Show Japanese', 'jp'); check('Show English', 'en'); check('Show speaker', 'speaker')
        check('Kanji version (when the table has one)', 'kanji')
        check('Furigana', 'furi'); check('Dictionary on hover', 'dico')
        sm = tk.Menu(m, tearoff=0); self.alpha = tk.DoubleVar(value=self.P['alpha'])
        for v in (1.0, 0.88, 0.75, 0.6):
            sm.add_radiobutton(label='%d %%' % round(v * 100), variable=self.alpha, value=v,
                               command=lambda: (self.P.update(alpha=self.alpha.get()), self.layout()))
        m.add_cascade(label='Opacity', menu=sm)
        if extra:
            m.add_separator()
            for label, cmd in extra:
                m.add_command(label=label, command=cmd)
        cap = self.cap_var = tk.BooleanVar(value=CAPTURABLE[0])
        def toggle_cap():
            CAPTURABLE[0] = cap.get()
            self.win.after(50, lambda: set_capturable(self.win))
        m.add_checkbutton(label='Visible in screenshots (demo)', variable=cap, command=toggle_cap)
        m.add_separator()
        m.add_command(label='Close (back to the game list)', command=self.close)

    def set_display(self, d, from_menu=False):
        self.P.update({k: bool(v) for k, v in d.items() if k in DISPLAY})
        for k in DISPLAY:
            if k in self.vars:
                self.vars[k].set(self.P[k])
        self.layout()
        if from_menu and self.on_display:
            self.on_display({k: self.P[k] for k in DISPLAY})

    # ------------------------------------------------------------ toolbar (appears when the mouse is over the window)
    def build_toolbar(self, extra):
        tb = self.tb = tk.Toplevel(self.win)
        tb.overrideredirect(True); tb.attributes('-topmost', True); tb.configure(bg=BG)
        self.tb_shown = False
        def btn(text, cmd, tip=''):
            b = tk.Label(tb, text=text, bg='#232733', fg=FG, font=(EN_FONT, 9, 'bold'), padx=8, pady=3, cursor='hand2')
            b.pack(side='left', padx=(1, 0), pady=1)
            b.bind('<Button-1>', lambda e: cmd())
            b.bind('<Enter>', lambda e: b.configure(bg=ACCENT)); b.bind('<Leave>', lambda e: b.configure(bg='#232733'))
        btn('JP +', lambda: self.size('t', 2)); btn('JP \u2212', lambda: self.size('t', -2))
        btn('EN +', lambda: self.size('ten', 2)); btn('EN \u2212', lambda: self.size('ten', -2))
        btn('JP', lambda: self.set_display({'jp': not self.P['jp']}, True))
        btn('EN', lambda: self.set_display({'en': not self.P['en']}, True))
        btn('Screenshot mode', self.toggle_capture)
        for label, cmd in extra:
            if label.startswith('Select the text box'):
                btn('Zone', cmd)
        btn('\u2630 Menu', lambda: self.menu.tk_popup(tb.winfo_rootx(), tb.winfo_rooty() + tb.winfo_height()))
        tb.update_idletasks(); no_focus(tb); tb.withdraw()
        self.win.after(200, self.tb_poll)

    def toggle_capture(self):
        CAPTURABLE[0] = not CAPTURABLE[0]
        self.cap_var.set(CAPTURABLE[0])
        self.win.after(50, lambda: set_capturable(self.win))

    def tb_poll(self):
        if not self.alive:
            return
        try:
            px, py = self.win.winfo_pointerxy()
            w, t = self.win, self.tb
            x0, y0, x1, y1 = w.winfo_rootx(), w.winfo_rooty(), w.winfo_rootx() + w.winfo_width(), w.winfo_rooty() + w.winfo_height()
            th = t.winfo_reqheight(); ty = y0 - th - 2 if y0 - th - 2 >= 0 else y1 + 2
            over = x0 <= px <= x1 and y0 <= py <= y1 or x0 <= px <= x0 + t.winfo_reqwidth() and ty <= py <= ty + th
            if over and not self.tb_shown:
                t.deiconify(); self.tb_shown = True
            elif not over and self.tb_shown and not self.menu_open():
                t.withdraw(); self.tb_shown = False
            if self.tb_shown:
                t.geometry('+%d+%d' % (x0, ty)); t.lift(); t.attributes('-topmost', True)
        except Exception:
            pass
        self.win.after(120, self.tb_poll)

    def menu_open(self):
        return False

    def popup(self, e):
        self.menu_up = True; MENU_OPEN[0] = True
        try:
            self.menu.tk_popup(e.x_root, e.y_root); self.menu.grab_release()
        finally:
            self.menu_up = False; MENU_OPEN[0] = False

    def size(self, key, d):
        self.P[key] = max(8, min(72, self.P[key] + d)); self.layout()

    def wheel(self, e):
        self.size('ten' if e.widget is self.en else 't', 2 if e.delta > 0 else -2)

    def save(self):
        self.P.update(larg=self.larg, x=self.win.winfo_x(), y=self.win.winfo_y())
        look = {k: v for k, v in self.P.items() if k not in DISPLAY}
        self.prefs.clear(); self.prefs.update(look)
        self.game_prefs.update({k: self.P[k] for k in DISPLAY})

    # ------------------------------------------------------------ move / resize
    EDGE = 16

    def zone(self, e):
        x = e.x_root - self.win.winfo_x()
        return 'r' if x >= self.win.winfo_width() - self.EDGE else ('l' if x <= self.EDGE else '')

    def hover(self, e):
        self.win.configure(cursor='sb_h_double_arrow' if self.zone(e) else 'fleur')

    def press(self, e):
        self.d = dict(x=e.x_root - self.win.winfo_x(), y=e.y_root - self.win.winfo_y(), z=self.zone(e),
                      x0=e.x_root, l0=self.larg, fx=self.win.winfo_x())

    def drag(self, e):
        d = self.d
        if d['z'] == 'r':
            self.larg = max(300, d['l0'] + e.x_root - d['x0']); self.layout()
        elif d['z'] == 'l':
            self.larg = max(300, d['l0'] - (e.x_root - d['x0']))
            self.win.geometry('+%d+%d' % (d['fx'] + d['l0'] - self.larg, self.win.winfo_y())); self.layout()
        else:
            self.win.geometry('+%d+%d' % (e.x_root - d['x'], e.y_root - d['y']))

    # ------------------------------------------------------------ drawing
    def layout(self):
        P = self.P; L = self.line
        for w in (self.who, self.jp, self.en, self.st):
            w.pack_forget()
        top = (8, 0)
        if L and P['speaker'] and L.get('speaker'):
            self.who.configure(text=L['speaker'], font=(EN_FONT, max(9, int(P['ten'] * 0.7)), 'bold'))
            self.who.pack(fill='x', padx=14, pady=(6, 0)); top = (2, 0)
        if L and P['jp']:
            self.draw_jp(); self.jp.pack(fill='x', padx=14, pady=top); top = (2, 0)
        if L and P['en']:
            self.en.configure(text=' '.join((L['en'] or '').split()), font=(EN_FONT, P['ten']), wraplength=self.larg - 36)
            self.en.pack(fill='x', padx=14, pady=(top[0], 8))
        if self.status_text or not L:
            self.st.configure(text=self.status_text or '', font=(EN_FONT, 9), wraplength=self.larg - 36)
            self.st.pack(fill='x', padx=14, pady=(2, 6))
        self.win.attributes('-alpha', P['alpha'])
        self.win.update_idletasks()
        self.win.geometry('%dx%d' % (self.larg, self.frame.winfo_reqheight()))
        self.save()

    def draw_jp(self):
        P = self.P; L = self.line; c = self.jp
        c.delete('all')
        width = self.larg - 28
        F = tkfont.Font(family=JP_FONT, size=P['t'], weight='bold')
        Fr = tkfont.Font(family=JP_FONT, size=max(7, int(P['t'] * 0.45)))
        use_k = P['kanji'] and L.get('kanji')
        words = L.get('words_kanji') if use_k else L.get('words')
        if not words:  # no analysis: one "word" per character so lines can wrap
            words = [{'t': ch, 'f': [[ch, '']], 'd': None} for ch in ' '.join(((L['kanji'] if use_k else L['jp']) or '').split())]
        rh = Fr.metrics('linespace') if P['furi'] else 0
        lh = F.metrics('linespace')
        x = y = 0
        for i, m in enumerate(words):
            parts = [[' ', '']] if m['t'] == '\n' else m['f']
            if not P['furi']:
                parts = [[''.join(t for t, _ in parts), '']]
            ws = [max(F.measure(t), Fr.measure(r) if r else 0) for t, r in parts]
            if x + sum(ws) > width and x > 0:
                x = 0; y += rh + lh + 2
            tag = 'w%d' % i
            for (t, r), w in zip(parts, ws):
                c.create_text(x + w / 2, y + rh, text=t, font=F, fill=FG, anchor='n', tags=(tag, 'txt'))
                if r:
                    c.create_text(x + w / 2, y + 1, text=r, font=Fr, fill='#c9cfd9', anchor='n', tags=(tag,))
                x += w
            if m.get('d'):
                c.tag_bind(tag, '<Enter>', lambda e, d=m['d'], t=tag: (c.itemconfigure(t + '&&txt', fill='#ffd166'), self.show_tip(d, e)))
                c.tag_bind(tag, '<Leave>', lambda e, t=tag: (c.itemconfigure(t + '&&txt', fill=FG), self.hide_tip()))
        c.configure(width=width, height=y + rh + lh + 2)

    def hide_tip(self):
        if self.tip is not None:
            self.tip.destroy(); self.tip = None

    def show_tip(self, d, e):
        self.hide_tip()
        if not self.P['dico'] or not d:
            return
        b = tk.Toplevel(self.win); b.overrideredirect(True); b.attributes('-topmost', True); b.configure(bg=ACCENT)
        lines = []
        for x in d:
            lines.append('%s【%s】' % (x['word'], x['read']) if x['read'] and x['read'] != x['word'] else x['word'])
            lines += ['  %d. %s' % (k + 1, g) for k, g in enumerate(x['senses'])]
        tk.Label(b, text='\n'.join(lines), bg='#1d2027', fg=FG, justify='left', anchor='w',
                 font=(JP_FONT, max(10, int(self.P['ten'] * 0.8))), wraplength=520, padx=10, pady=6).pack(padx=1, pady=1)
        b.update_idletasks()
        x = min(e.x_root + 12, self.W - b.winfo_reqwidth() - 4)
        y = self.win.winfo_y() + self.win.winfo_height() + 4
        if y + b.winfo_reqheight() > self.H:
            y = max(0, self.win.winfo_y() - b.winfo_reqheight() - 4)
        b.geometry('+%d+%d' % (x, y)); no_focus(b); self.tip = b

    # ------------------------------------------------------------ events
    def poll(self):
        if not self.alive:
            return
        changed = False
        try:
            while True:
                ev = self.events.get_nowait()
                if ev[0] == 'line':
                    self.line = ev[1]; self.status_text = ''; self.hide_tip()
                elif ev[0] == 'status':
                    self.status_text = ev[1]
                elif ev[0] == 'display':
                    self.set_display(ev[1])
                elif ev[0] == 'nomatch':
                    self.status_text = 'Not found in the table: %s' % ev[1][:60]
                changed = True
        except queue.Empty:
            pass
        if changed:
            self.layout()
        if not getattr(self, 'menu_up', False):
            self.win.lift(); self.win.attributes('-topmost', True)  # stay above the game even if it comes back on top
        self.win.after(150, self.poll)

    def close(self):
        if not self.alive:
            return
        self.save(); self.alive = False; self.hide_tip()
        self.win.destroy()
        self.on_close()
