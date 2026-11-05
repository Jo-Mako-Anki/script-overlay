# -*- coding: utf-8 -*-
"""Where the app keeps its files.

- RES_DIR: read-only files shipped with the app (catalog, hook scripts, dictionary).
- DATA_DIR: everything the app writes (downloaded tables, settings, OCR model, logs). It sits next to the .exe
  (portable app); if that folder is read-only, %LOCALAPPDATA%\\ScriptOverlay is used instead.
  build.bat puts the .exe at the root of the sources, so the .exe and `python -m script_overlay` share the same
  data folder (same games and settings).
- GAMES_DIR: Games\\<game>\\ next to the .exe (scripts and saved guide pages of each game).
"""
import json, os, sys

FROZEN = getattr(sys, 'frozen', False)
APP_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(getattr(sys, '_MEIPASS', APP_DIR), 'resources')
ROOT = APP_DIR
GAMES_DIR = os.path.join(ROOT, 'Games')


def _data_dir():
    d = os.path.join(ROOT, 'data')
    try:
        os.makedirs(d, exist_ok=True)
        t = os.path.join(d, '.write_test_%d' % os.getpid())  # one name per process: two starts at once don't clash
        open(t, 'w').close(); os.remove(t)
        return d
    except OSError:
        d = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ScriptOverlay')
        os.makedirs(d, exist_ok=True)
        return d


DATA_DIR = _data_dir()


def data(*parts):
    """Path inside DATA_DIR; its folder is created if needed."""
    p = os.path.join(DATA_DIR, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def res(*parts):
    return os.path.join(RES_DIR, *parts)


class Settings(dict):
    """settings.json in DATA_DIR (Tesseract path, OCR region of each game, overlay look)."""
    PATH = None

    def __init__(self):
        super().__init__()
        self.PATH = data('settings.json')
        try:
            self.update(json.load(open(self.PATH, encoding='utf-8')))
        except Exception:
            pass

    def game(self, gid):
        return self.setdefault('games', {}).setdefault(gid, {})

    def save(self):
        try:
            tmp = self.PATH + '.tmp'
            json.dump(self, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            os.replace(tmp, self.PATH)
        except Exception as e:
            print('Could not save settings:', e)
