# -*- coding: utf-8 -*-
"""Local web page (http://localhost:8790): the hub (game list, start / stop, add a game) and the live text page.

The page only talks to 127.0.0.1. Anything that touches the windows (overlay, OCR region) is handed to the
app's main thread through App.call().
"""
import json, os, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .paths import res


class LiveState:
    """What the live page shows. The page waits on /etat?n=<last n> until something changes (long polling)."""

    def __init__(self):
        self.cond = threading.Condition(); self.n = 0
        self.d = dict(jeu='', nom='', statut='No game running.', actuelle=None, historique=[], suite=[], ocr='')

    def set(self, **kw):
        with self.cond:
            self.d.update(kw); self.n += 1; self.cond.notify_all()

    def reset(self, code='', name='', status=''):
        self.set(jeu=code, nom=name, statut=status, actuelle=None, historique=[], ocr='')

    def wait(self, n, timeout=20):
        with self.cond:
            if self.n == n:
                self.cond.wait(timeout)
            return self.n, json.dumps(self.d, ensure_ascii=False)


def serve(app, port=8790):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, typ, body):
            if isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(code); self.send_header('Content-Type', typ)
            self.send_header('Cache-Control', 'no-store'); self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)

        def js(self, obj, code=200):
            self.send(code, 'application/json; charset=utf-8', json.dumps(obj, ensure_ascii=False))

        def page(self, name):
            self.send(200, 'text/html; charset=utf-8', open(res('web', name), 'rb').read())

        def do_GET(self):
            u = urllib.parse.urlparse(self.path); qs = urllib.parse.parse_qs(u.query)
            if u.path in ('/', '/hub'):
                return self.page('hub.html')
            if u.path == '/live':
                return self.page('live.html')
            if u.path == '/etat':
                n, d = app.live.wait(int(qs.get('n', ['-1'])[0]))
                return self.send(200, 'application/json; charset=utf-8', '{"n":%d,"d":%s}' % (n, d))
            if u.path == '/api/games':
                return self.js(app.api_games())
            if u.path == '/guide':  # calendar of the running game (saved GameFAQs pages)
                return self.js(app.api_guide())
            self.send(404, 'text/plain', '?')

        def do_POST(self):
            # only our own page may call the API (blocks other web sites open in the browser)
            if self.headers.get('Origin') not in (None, 'http://localhost:%d' % self.server.server_port,
                                                  'http://127.0.0.1:%d' % self.server.server_port):
                return self.send(403, 'text/plain', 'forbidden')
            u = urllib.parse.urlparse(self.path); qs = urllib.parse.parse_qs(u.query)
            n = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(n) if n else b''
            try:
                if u.path == '/api/upload':  # raw file in the body, name in ?name=
                    return self.js(app.api_upload(qs.get('name', ['table.xlsx'])[0], body, qs.get('id', [None])[0]))
                arg = json.loads(body.decode('utf-8') or '{}')
                fn = {'/api/start': app.api_start, '/api/stop': app.api_stop, '/api/add': app.api_add,
                      '/api/remove': app.api_remove, '/api/options': app.api_options,
                      '/api/display': app.api_display}.get(u.path)
                if not fn:
                    return self.send(404, 'text/plain', '?')
                return self.js(fn(arg))
            except Exception as e:
                return self.js({'error': str(e)}, 400)

    for p in range(port, port + 10):  # port taken (another tool, AnkiConnect = 8765…): try the next ones
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', p), H); break
        except OSError:
            continue
    else:
        raise RuntimeError('No free port between %d and %d' % (port, port + 9))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, p
