# -*- coding: utf-8 -*-
"""Script Overlay: the game list is a local web page (the hub); the English of each line shows on the live page
and in a window over the game. A small window on the desktop keeps the app running (close it to quit)."""
import hashlib, json, os, queue, re, shutil, sys, threading, time, traceback, urllib.request, webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

from . import games as G, ocr as O
from .analysis import Analyzer
from .guide import guide
from .overlay import Overlay
from .pack import read_pack
from .paths import DATA_DIR, ROOT, Settings, data
from .region import pick_region
from .sources import HookSource, OcrSource, Session
from .tables import guess_columns, load_table, read_header
from .web import LiveState, serve

VERSION = '0.5'


class App:
    def __init__(self):
        self.S = Settings()
        self.A = Analyzer()
        self.hooks = G.hooks_available()
        self.live = LiveState()
        self.calls = queue.Queue()
        self.busy = False; self.source = None; self.overlay = None; self.running = None; self.events = None
        self.guides = {}
        r = self.root = tk.Tk()
        r.title('Script Overlay'); r.resizable(False, False)
        try:
            ttk.Style().theme_use('vista')
        except tk.TclError:
            pass
        self.srv, self.port = serve(self)
        self.url = 'http://localhost:%d/' % self.port
        f = ttk.Frame(r, padding=14); f.pack(fill='both', expand=True)
        ttk.Label(f, text='Script Overlay %s is running.' % VERSION, font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        ttk.Label(f, text='Choose your game in the web page:\n%s' % self.url, foreground='#555').pack(anchor='w', pady=(4, 10))
        self.msg = ttk.Label(f, text='', foreground='#555', wraplength=320); self.msg.pack(anchor='w')
        b = ttk.Frame(f); b.pack(fill='x', pady=(8, 0))
        ttk.Button(b, text='Open the game list', command=self.open_hub).pack(side='left')
        ttk.Button(b, text='Quit', command=r.destroy).pack(side='right')
        r.report_callback_exception = self.report
        threading.Thread(target=self.refresh_catalog, daemon=True).start()
        r.after(100, self.pump)
        r.after(500, self.open_hub)

    # ------------------------------------------------------------ helpers
    def open_hub(self):
        webbrowser.open(self.url)

    def report(self, *exc):
        traceback.print_exception(*exc)
        self.error(''.join(traceback.format_exception_only(exc[0], exc[1])).strip())

    def error(self, text):
        self.say(text); self.live.set(statut='Error: ' + text)
        messagebox.showerror('Script Overlay', text)

    def refresh_catalog(self):
        G.refresh_catalog(self.S.get('catalog_url'))

    def call(self, fn, *a):
        """Runs fn in the window thread (the web server runs in other threads)."""
        self.calls.put((fn, a))

    def pump(self):
        try:
            while True:
                fn, a = self.calls.get_nowait()
                fn(*a)
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    def say(self, text):
        """Status line of the small window and of the live page; safe from any thread."""
        self.call(lambda: self.msg.configure(text=text))
        if text:
            self.live.set(statut=text)

    def in_thread(self, work, then):
        """Runs work() in a thread, then then(result) in the window thread (errors are shown)."""
        self.busy = True
        def run():
            try:
                r = work(); self.call(lambda: (setattr(self, 'busy', False), then(r)))
            except Exception as e:
                traceback.print_exc()
                self.call(lambda: (setattr(self, 'busy', False), self.failed(str(e))))
        threading.Thread(target=run, daemon=True).start()

    def failed(self, text):
        self.running = None; self.live.reset(status='Error: ' + text); self.error(text)

    def mode(self, g):
        if g.get('emulator'):  # the emulator's own script (Script Viewer for mGBA) reads the text: no OCR
            return 'emulator', None
        h = self.hooks.get(g.get('hook') or '')
        if h:
            return 'hook', h
        return 'ocr', None

    def game(self, gid):
        for g in G.load_games():
            if g['id'] == gid:
                return g
        raise RuntimeError('Unknown game.')

    # ------------------------------------------------------------ web API (called from the server threads)
    def api_games(self):
        out = []
        for g in sorted(G.load_games(), key=lambda g: g['name'].lower()):
            ready = G.is_ready(g)
            if g.get('emulator'):
                ready = True; st = 'dialogues ready'
            elif ready:
                st = 'table ready'
            else:
                st = 'table to download' if g['table'].get('url') else 'table not online yet: you will be asked for the file'
            out.append(dict(id=g['id'], name=g['name'], ready=ready, status=st, mode=self.mode(g)[0], source=g['source'],
                            has_region=bool(self.S.game(g['id']).get('region')),
                            emulator=(g.get('emulator') or {}).get('name'),
                            can_remove=g['source'] == 'local' or ready))
        return dict(version=VERSION, games=out, running=self.running,
                    tesseract=bool(O.find_tesseract(self.S)), hooks={k: h['name'] for k, h in self.hooks.items()})

    def api_guide(self):
        """Day-by-day calendar of the running game (empty if no saved guide pages)."""
        if not self.running:
            return []
        gid = self.running['id']
        if gid not in self.guides:
            try:
                d = G.guide_dir(self.game(gid))
                self.guides[gid] = guide(d) if d else []
            except Exception as e:
                print('Guide not read:', e); self.guides[gid] = []
        return self.guides[gid]

    def api_start(self, arg):
        g = self.game(arg['id'])
        if g.get('emulator'):  # nothing to run here: open the emulator's page and say what to do in the emulator
            return self.start_emulator(g)
        if self.busy:
            return {'message': 'Busy, try again in a moment.'}
        if not G.is_ready(g):
            if not g['table'].get('url'):
                return {'need_table': True}
            self.say('Downloading the table of %s…' % g['name'])
            G.download_table(g, lambda d, t: self.live.set(statut='Downloading the table… %.1f MB' % (d / 1e6)))
        self.call(self.start, g)
        return {'ok': True}

    def start_emulator(self, g):
        e = g['emulator']
        script = os.path.normpath(os.path.join(ROOT, e['script']))
        page = os.path.normpath(os.path.join(ROOT, e['page']))
        if not os.path.exists(script):
            raise RuntimeError('Script not found: ' + script)
        if os.path.exists(page):
            webbrowser.open('file:///' + page.replace('\\', '/'))
        return {'emulator': {'name': e.get('name', 'the emulator'), 'script': script, 'game': g['name']}}

    def api_stop(self, arg):
        self.call(self.stop_game)
        return {'ok': True}

    def api_upload(self, name, body, gid=None):
        name = os.path.basename(name)
        ext = os.path.splitext(name)[1].lower()
        if ext not in ('.xlsx', '.csv', '.tsv', '.sop'):
            raise RuntimeError('The table must be a .xlsx, .csv, .tsv or .sop file.')
        if gid:  # table of a catalog game that is not online yet
            dest = G.table_path(self.game(gid))
            if ext == '.sop':
                dest = os.path.splitext(dest)[0] + '.sop'
            open(dest + '.part', 'wb').write(body); os.replace(dest + '.part', dest)
            return {'ok': True}
        token = hashlib.md5(body).hexdigest()[:12]
        if ext == '.sop':  # game file: everything is inside, the game is added at once
            p = data('uploads', token, name)
            open(p, 'wb').write(body)
            meta = read_pack(p)[0]
            n = meta.get('name') or os.path.splitext(name)[0]
            gid = re.sub(r'[^a-z0-9]+', '_', n.lower()).strip('_')[:30] + '_' + token[:6]
            dest = data('tables', gid, name)
            shutil.move(p, dest); shutil.rmtree(os.path.dirname(p), ignore_errors=True)
            g = {'id': gid, 'name': n, 'table': {'path': os.path.relpath(dest, DATA_DIR)},
                 'hook': meta.get('hook') if meta.get('hook') in self.hooks else None}
            g.update({k: meta[k] for k in ('code', 'folder', 'emulator') if meta.get(k)})
            G.save_user_game(g)
            return {'added': n}
        p = data('uploads', token, name)
        open(p, 'wb').write(body)
        head = read_header(p)
        return {'token': token, 'head': head, 'guess': guess_columns(head)}

    def api_add(self, arg):
        up = os.path.dirname(data('uploads', arg['token'], 'x'))
        files = os.listdir(up) if os.path.isdir(up) else []
        if not files:
            raise RuntimeError('Choose the table file again.')
        cols = arg.get('columns') or {}
        if not (cols.get('jp') or cols.get('kanji')) or not cols.get('en'):
            raise RuntimeError('Choose the Japanese and the English columns.')
        n = (arg.get('name') or '').strip() or 'Game'
        gid = re.sub(r'[^a-z0-9]+', '_', n.lower()).strip('_')[:30] + '_' + arg['token'][:6]
        dest = data('tables', gid, files[0])
        shutil.move(os.path.join(up, files[0]), dest); shutil.rmtree(up, ignore_errors=True)
        hook = arg.get('hook') if arg.get('hook') in self.hooks else None
        G.save_user_game({'id': gid, 'name': n, 'table': {'path': os.path.relpath(dest, DATA_DIR)}, 'columns': cols,
                          'hook': hook})
        return {'ok': True, 'id': gid}

    def api_remove(self, arg):
        g = self.game(arg['id'])
        if self.running and self.running['id'] == g['id']:
            raise RuntimeError('Stop the game first.')
        tables = os.path.dirname(data('tables', g['id'], 'x'))
        if g['source'] == 'local':
            G.remove_user_game(g['id'])
            if os.path.abspath(G.table_path(g)).startswith(os.path.abspath(tables)):
                shutil.rmtree(tables, ignore_errors=True)
        elif G.is_ready(g):
            os.remove(G.table_path(g))
        self.S['games'].pop(g['id'], None) if 'games' in self.S else None
        self.S.save()
        return {'ok': True}

    def display(self, gid):
        """What to show for this game (speaker, Japanese, English, furigana, kanji version, dictionary)."""
        from .overlay import DEFAULTS, DISPLAY
        d = self.S.game(gid).setdefault('display', {})
        for k in DISPLAY:
            d.setdefault(k, self.S.get('overlay', {}).get(k, DEFAULTS[k]))
        return d

    def api_display(self, arg):
        """Settings of the running game, changed from the live page."""
        from .overlay import DISPLAY
        gid = arg.get('id') or (self.running or {}).get('id')
        if not gid:
            raise RuntimeError('No game running.')
        d = self.display(gid)
        d.update({k: bool(v) for k, v in (arg.get('display') or {}).items() if k in DISPLAY})
        self.S.save()
        if self.running and self.running['id'] == gid:
            self.live.set(reglages=dict(d))
            if self.events is not None:
                self.events.put(('display', dict(d)))
        return {'ok': True, 'display': d}

    def api_options(self, arg):
        if arg.get('reset_region'):
            self.S.game(arg['id']).pop('region', None)
        self.S.save()
        return {'ok': True}

    # ------------------------------------------------------------ start a game (window thread)
    def start(self, g):
        if self.running:
            self.stop_game()
        self.running = {'id': g['id'], 'name': g['name']}
        self.live.reset(g.get('code') or g['id'].upper(), g['name'], 'Loading the table…')
        self.live.set(reglages=dict(self.display(g['id'])))
        cols = g.get('columns') or None
        def loaded(B):
            if not self.running or self.running['id'] != g['id']:  # stopped while loading
                return
            self.say('%d text boxes in the table.' % len(B))
            m, h = self.mode(g)
            if m == 'hook':
                return self.run(g, B, h)
            self.prepare_ocr(g, B)
        self.in_thread(lambda: load_table(G.table_path(g), cols, g.get('sheet'), self.say), loaded)

    def prepare_ocr(self, g, B):
        exe = O.find_tesseract(self.S)
        if not exe:
            self.running = None; self.live.reset(status='OCR needs Tesseract.')
            if messagebox.askyesno('Tesseract is needed',
                                   'OCR needs Tesseract (free). Install the Windows version (UB Mannheim), '
                                   'then start the game again.\n\nOpen the download page now?'):
                webbrowser.open(O.TESSERACT_HELP)
            return
        if not O.has_model():
            self.say('Downloading the Japanese OCR model…')
            return self.in_thread(lambda: O.download_model(lambda d, t: self.live.set(
                statut='Downloading the Japanese OCR model… %.1f MB' % (d / 1e6))), lambda _: self.prepare_ocr(g, B))
        reg = self.S.game(g['id']).get('region')
        if reg:
            return self.run(g, B, None, O.Tesseract(exe), reg)
        self.say('Draw the rectangle of the dialogue box on the screen.')
        def got(r):
            if not r:
                self.running = None; self.live.reset(status='Cancelled.'); return
            self.S.game(g['id'])['region'] = list(r); self.S.save()
            self.run(g, B, None, O.Tesseract(exe), r)
        self.root.after(300, lambda: pick_region(self.root, got))

    def run(self, g, B, hook, engine=None, region=None):
        events = self.events = queue.Queue()
        sess = Session(g, B, self.A, events, self.live)
        self.source = HookSource(sess, hook) if hook else OcrSource(sess, engine, region)
        self.source.start()
        prefs = self.S.setdefault('overlay', {})
        extra = []
        if not hook:
            def reselect():
                self.stop_game()
                self.S.game(g['id']).pop('region', None); self.S.save()
                self.start(g)
            extra.append(('Select the text box again…', reselect))
        extra.append(('Open the game list (web page)', self.open_hub))
        extra.append(('Open the log folder', lambda: os.startfile(os.path.dirname(data('logs', 'x')))))
        def from_menu(d):  # changed in the overlay menu: save it and update the page
            self.display(g['id']).update(d); self.S.save(); self.live.set(reglages=dict(self.display(g['id'])))
        self.overlay = Overlay(self.root, 'Script Overlay - %s' % g['name'], prefs, events, self.stopped, extra,
                               self.display(g['id']), from_menu)
        self.root.iconify()

    def stop_game(self):
        if self.overlay is not None and self.overlay.alive:
            self.overlay.close()  # calls stopped()
        else:
            self.stopped()

    def stopped(self):
        if self.source:
            self.source.stop.set(); self.source = None
        self.overlay = None; self.running = None; self.events = None
        self.S.save(); self.live.reset(status='Stopped.'); self.say('')


def running_instance(port=8790):
    """Address of a Script Overlay already running (its hub answers /api/games), or None.
    Two copies at once each showed their own game list on their own port."""
    for p in range(port, port + 10):
        try:
            r = urllib.request.urlopen('http://127.0.0.1:%d/api/games' % p, timeout=0.5)
            if 'games' in json.loads(r.read().decode('utf-8')):
                return 'http://localhost:%d/' % p
        except Exception:
            continue
    return None


def main():
    url = running_instance()
    if url:  # already running: show its game list instead of starting a second copy
        webbrowser.open(url)
        return
    try:  # real pixels on high-DPI screens (the OCR region must match the screen capture)
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass
    if getattr(sys, 'frozen', False) and sys.stdout is None:  # windowed .exe: keep messages in a log file
        sys.stdout = sys.stderr = open(data('script_overlay.log'), 'w', encoding='utf-8', buffering=1)
    App().root.mainloop()
