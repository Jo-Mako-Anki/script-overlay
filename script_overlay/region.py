# -*- coding: utf-8 -*-
"""Lets the user draw the rectangle of the game's dialogue box, over the whole desktop."""
import tkinter as tk


def pick_region(root, done):
    """done((x, y, w, h)) in screen pixels, or done(None) if cancelled (Esc / right-click)."""
    import mss
    v = mss.mss().monitors[0]  # all screens together
    win = tk.Toplevel(root)
    win.overrideredirect(True); win.attributes('-topmost', True); win.attributes('-alpha', 0.35)
    win.geometry('%dx%d+%d+%d' % (v['width'], v['height'], v['left'], v['top']))
    c = tk.Canvas(win, bg='black', highlightthickness=0, cursor='crosshair')
    c.pack(fill='both', expand=True)
    mon = mss.mss().monitors[1]
    c.create_text(mon['left'] - v['left'] + mon['width'] // 2, mon['top'] - v['top'] + 60,
                  text='Draw a rectangle around the game\'s dialogue box (only the text area).\n'
                       'Show a line of dialogue in the game first.   Esc = cancel',
                  fill='white', font=('Segoe UI', 20, 'bold'), justify='center')
    st = {}

    def press(e):
        st['x0'], st['y0'] = e.x, e.y
        st['r'] = c.create_rectangle(e.x, e.y, e.x, e.y, outline='#e5383b', width=3, fill='white', stipple='gray25')

    def move(e):
        if 'r' in st:
            c.coords(st['r'], st['x0'], st['y0'], e.x, e.y)

    def release(e):
        if 'r' not in st:
            return
        x0, x1 = sorted((st['x0'], e.x)); y0, y1 = sorted((st['y0'], e.y))
        win.destroy()
        done((x0 + v['left'], y0 + v['top'], x1 - x0, y1 - y0) if x1 - x0 > 20 and y1 - y0 > 10 else None)

    def cancel(e=None):
        win.destroy(); done(None)

    c.bind('<ButtonPress-1>', press); c.bind('<B1-Motion>', move); c.bind('<ButtonRelease-1>', release)
    c.bind('<Button-3>', cancel); win.bind('<Escape>', cancel)
    win.focus_force()
