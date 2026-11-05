# -*- coding: utf-8 -*-
"""Where the game text comes from, and what is done with it.

- OcrSource: watches the dialogue-box region of the screen; when the picture has been still for ~0.4 s and is
  new, it is read by OCR.
- HookSource: a game script (Frida, like the Agent texthooker) reads the text in the game's memory.
Both hand the text to Session.handle(), which finds the line in the table and passes it to the overlay.
"""
import datetime, os, queue, threading, time

import numpy as np

from .matcher import JAP, Matcher
from .paths import data, res


class Session:
    def __init__(self, game, boxes, analyzer, out, live):
        """out: queue read by the overlay; live: LiveState shown by the web page."""
        self.game = game; self.B = boxes; self.M = Matcher(boxes); self.A = analyzer; self.out = out; self.live = live
        self.hist = []
        self.log = data('logs', '%s_%s.tsv' % (game['id'], datetime.date.today().isoformat()))
        self.last_shown = None

    def status(self, text):
        self.out.put(('status', text)); self.live.set(statut=text)

    def handle(self, text, ocr=False):
        """Returns True if the text was found in the table."""
        i, sc, whole = self.M.find(text, ocr)
        if i is None:
            self.out.put(('nomatch', text.replace(' / ', ' '), sc)); self.live.set(ocr=text.replace(' / ', ' '))
            return False
        self.M.last = i
        j = i
        if whole:
            j = self.M.row_end(i); self.M.last = j
        if ocr and (i, j) == self.last_shown:
            return True
        self.last_shown = (i, j)
        bx = self.B[i:j + 1]
        jp = '\n'.join(b['jp'] for b in bx)
        kanji = '\n'.join(b['kanji'] or b['jp'] for b in bx)
        en = '\n'.join(dict.fromkeys(b['en'] for b in bx))  # same English for every box when it could not be split
        line = dict(jp=jp, kanji=kanji if kanji != jp else '', en=en, speaker=bx[0]['speaker'],
                    speaker_jp=bx[0]['speaker_jp'], row=bx[0]['row'], score=round(sc),
                    words=self.A.analyze(jp), words_kanji=self.A.analyze(kanji) if kanji != jp else None)
        self.out.put(('line', line))
        now = datetime.datetime.now().strftime('%H:%M:%S')
        k = line['words_kanji']
        page = dict(i=i, heure=now, jp=jp, mots=line['words'], jp_k=kanji if k else '', mots_k=k, en=en,
                    perso_jp=line['speaker_jp'], perso_en=line['speaker'] if line['speaker'] != line['speaker_jp'] else '')
        self.hist.append(page); del self.hist[:-60]
        self.live.set(actuelle=page, historique=[dict(h, mots=None, mots_k=None) for h in self.hist], ocr='')
        try:
            with open(self.log, 'a', encoding='utf-8') as f:
                f.write('\t'.join([datetime.datetime.now().strftime('%H:%M:%S'), str(line['row']), bx[0]['id'],
                                   line['speaker'], jp.replace('\n', ' '), en.replace('\n', ' ')]) + '\n')
        except OSError:
            pass
        return True


class OcrSource(threading.Thread):
    def __init__(self, session, ocr, region, fps=12, still=0.25):
        super().__init__(daemon=True)
        self.S = session; self.ocr = ocr; self.region = region; self.fps = fps
        self.need = max(2, int(round(still * fps)))
        self.stop = threading.Event()

    def run(self):
        import cv2, mss
        sct = mss.mss()
        x, y, w, h = self.region
        mon = {'left': x, 'top': y, 'width': w, 'height': h}
        sw = 200; sh = max(1, int(sw * h / w))
        prev = None; still = 0; done = None; tries = 0
        self.S.status('Reading the text box (OCR)…')
        from .overlay import MENU_OPEN
        while not self.stop.is_set():
            t0 = time.time()
            if MENU_OPEN[0]:  # the right-click menu is on screen: do not read it
                prev = None; still = 0; time.sleep(0.2); continue
            try:
                img = np.asarray(sct.grab(mon))[:, :, :3]
            except Exception as e:
                self.S.status('Screen capture failed: %s' % e); time.sleep(1); continue
            small = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (sw, sh), interpolation=cv2.INTER_AREA).astype(np.int16)
            still = still + 1 if prev is not None and np.abs(small - prev).mean() < 1.5 else 0
            prev = small
            if still == self.need and small.std() > 6:  # still picture with something on it
                if done is None or np.abs(small - done).mean() > 3:
                    tries = 0
                if done is None or np.abs(small - done).mean() > 3 or tries:
                    txt = self.ocr.read(img, extra=tries)
                    if len(JAP.findall(txt)) >= 2 and not self.S.handle(txt, ocr=True) and tries < 2:
                        tries += 1; still = 0  # read again a moment later, a little bigger
                    else:
                        tries = 0
                    done = small
            time.sleep(max(0.0, 1.0 / self.fps - (time.time() - t0)))


class HookSource(threading.Thread):
    """Attaches Frida to the game process and loads the game script (resources/hooks)."""

    def __init__(self, session, hook):
        super().__init__(daemon=True)
        self.S = session; self.hook = hook; self.stop = threading.Event()

    def code(self):
        parts = []
        for name in self.hook.get('libs', []):
            lib = open(res('hooks', name), encoding='utf-8').read()
            parts.append(lib[:lib.rindex('module.exports')] if 'module.exports' in lib else lib)
        parts.append(open(res('hooks', self.hook['script']), encoding='utf-8').read())
        return '\n'.join(parts)

    def find_pid(self, dev):
        names = [n.lower() for n in self.hook['process']]
        for p in dev.enumerate_processes():
            if p.name.lower() in names:
                return p.pid
        return None

    def run(self):
        try:
            import frida
        except ImportError:
            self.S.status('Frida is missing: the game script cannot run.'); return
        q = queue.Queue(); dev = frida.get_local_device(); code = self.code()
        session = None; last = ('', 0)
        while not self.stop.is_set():
            if session is None:
                self.S.status('Waiting for the game (%s)…' % ', '.join(self.hook['process']))
                pid = self.find_pid(dev)
                if pid is None:
                    self.stop.wait(2); continue
                try:
                    session = dev.attach(pid)
                    sc = session.create_script(code)
                    sc.on('message', lambda m, d: q.put(m))
                    session.on('detached', lambda *a: q.put({'type': 'detached'}))
                    sc.load()
                    self.S.status('Connected to the game. Waiting for text…')
                except Exception as e:  # game still starting, rights, etc.
                    self.S.status('Cannot attach to the game: %s' % e)
                    session = None; self.stop.wait(3); continue
            try:
                m = q.get(timeout=0.5)
            except queue.Empty:
                continue
            if m.get('type') == 'detached':
                self.S.status('Game closed.'); session = None; continue
            if m.get('type') == 'error':
                print('Game script error:', m.get('description')); continue
            p = m.get('payload') or {}
            if 'info' in p:
                print(p['info']); continue
            if 'erreur' in p or 'error' in p:
                self.S.status(p.get('error') or p.get('erreur')); continue
            if 'dbg' in p:  # TEST: text of the types the game script normally skips -> data/logs/p5r_types.tsv
                try:
                    from .paths import data
                    with open(data('logs', 'p5r_types.tsv'), 'a', encoding='utf-8') as f:
                        f.write('%s\t%s\t%s\n' % (time.strftime('%H:%M:%S'), p['dbg'], (p.get('text') or '').replace('\n', ' / ')))
                except Exception:
                    pass
                continue
            txt = p.get('texte') or p.get('text')
            if not txt:
                continue
            time.sleep(0.15)  # a box sometimes comes in several pieces: join them
            while not q.empty():
                m2 = q.get()
                p2 = m2.get('payload') or {}
                if m2.get('type') == 'send' and (p2.get('texte') or p2.get('text')):
                    txt += p2.get('texte') or p2.get('text')
                elif m2.get('type') == 'detached':
                    q.put(m2); break
            if not JAP.search(txt) or (txt == last[0] and time.time() - last[1] < 2):
                continue
            last = (txt, time.time())
            self.S.handle(txt)
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass
