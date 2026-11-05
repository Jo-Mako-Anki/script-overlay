# -*- coding: utf-8 -*-
"""Game list: the catalog (shipped with the app, refreshed from GitHub when CATALOG_URL is set) plus the games
the user added from a local table. Tables listed in the catalog are downloaded once into data/tables/<id>/."""
import hashlib, json, os, urllib.request

from .paths import DATA_DIR, GAMES_DIR, data, res

# Raw URL of resources/games.json on GitHub. Empty until the repository is published.
CATALOG_URL = ''
USER_GAMES = 'games_user.json'


def _read(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return None


def load_games():
    cat = _read(res('games.json')) or {'version': 0, 'games': []}
    remote = _read(data('catalog.json'))
    if remote and remote.get('version', 0) > cat.get('version', 0):
        cat = remote
    games = [dict(g, source='catalog') for g in cat.get('games', [])]
    user = _read(data(USER_GAMES)) or []
    ids = {g['id'] for g in games}
    games += [dict(g, source='local') for g in user if g['id'] not in ids]
    return games


def refresh_catalog(url=None):
    """Downloads the latest catalog (called in the background at start-up). Returns True if it changed."""
    url = url or CATALOG_URL
    if not url:
        return False
    try:
        raw = urllib.request.urlopen(url, timeout=10).read()
        new = json.loads(raw.decode('utf-8'))
        old = _read(data('catalog.json'))
        if old == new:
            return False
        open(data('catalog.json'), 'wb').write(raw)
        return True
    except Exception as e:
        print('Catalog not refreshed:', e)
        return False


def table_path(g):
    t = g['table']
    if t.get('path'):  # local table chosen by the user: used where it is (relative = inside the data folder)
        return os.path.normpath(os.path.join(DATA_DIR, t['path']))
    p = data('tables', g['id'], t.get('file') or os.path.basename(t['url'].split('?')[0]))
    sop = os.path.splitext(p)[0] + '.sop'  # game file given instead of the table
    return sop if not os.path.exists(p) and os.path.exists(sop) else p


def guide_dir(g):
    """Saved GameFAQs pages of the game: Games\\<folder>\\guide_gamefaqs, or guide_gamefaqs next to the table."""
    for d in (os.path.join(GAMES_DIR, g.get('folder') or g['name'], 'guide_gamefaqs'),
              os.path.join(os.path.dirname(table_path(g)), 'guide_gamefaqs')):
        if os.path.isdir(d):
            return d
    return None


def is_ready(g):
    return os.path.exists(table_path(g))


def download_table(g, progress=None):
    """Downloads the game's table into data/tables/<id>/. progress(done_bytes, total_bytes)."""
    t = g['table']
    if not t.get('url'):
        raise RuntimeError('No download address for this game yet.')
    dest = table_path(g)
    part = dest + '.part'
    req = urllib.request.Request(t['url'], headers={'User-Agent': 'ScriptOverlay'})
    with urllib.request.urlopen(req, timeout=30) as r, open(part, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0); done = 0
        h = hashlib.sha256()
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            f.write(b); h.update(b); done += len(b)
            if progress:
                progress(done, total)
    if t.get('sha256') and h.hexdigest().lower() != t['sha256'].lower():
        os.remove(part)
        raise RuntimeError('The downloaded table is damaged (checksum mismatch). Try again.')
    os.replace(part, dest)
    return dest


def save_user_game(g):
    user = _read(data(USER_GAMES)) or []
    user = [x for x in user if x['id'] != g['id']] + [{k: v for k, v in g.items() if k != 'source'}]
    json.dump(user, open(data(USER_GAMES), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def remove_user_game(gid):
    user = [x for x in (_read(data(USER_GAMES)) or []) if x['id'] != gid]
    json.dump(user, open(data(USER_GAMES), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def hooks_available():
    """Game scripts shipped with the app (resources/hooks/hooks.json): id -> description."""
    return _read(res('hooks', 'hooks.json')) or {}
