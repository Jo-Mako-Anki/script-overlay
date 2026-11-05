# -*- coding: utf-8 -*-
"""Reads a JP/EN table (.xlsx, .csv, .tsv) into a list of text boxes.

Columns are found by name (case does not matter); a game entry can name them explicitly in "columns".
A cell can hold several boxes: separated by line breaks, or by two spaces (project convention).
"""
import csv, hashlib, os, pickle, re

from .matcher import norm
from .paths import data

GUESS = {
    'jp': ['Jap', 'Texte JP', 'Japanese', 'JP', 'Japonais', 'Text JP'],
    'kanji': ['Kanji'],
    'en': ['Eng', 'Texte EN', 'English', 'EN', 'Anglais', 'Text EN'],
    'speaker_jp': ['Perso JP', 'Speaker JP'],
    'speaker_en': ['Perso EN', 'Perso', 'Speaker', 'Speaker EN', 'Name'],
    'group': ['Fichier', 'File', 'Lieu', 'Location', 'Map', 'Scene'],
    'id': ['ID'],
}
BOX_SPLIT = re.compile(r'\n| {2,}|　{2,}|　 | 　')


def read_rows(path, sheet=None):
    """Header + rows (lists of strings) of the first sheet (or the named one)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.csv', '.tsv', '.txt'):
        raw = open(path, 'rb').read()
        txt = raw.decode('utf-8-sig', errors='replace')
        delim = '\t' if ext != '.csv' or txt.count('\t') > txt.count(',') else ','
        rows = list(csv.reader(txt.splitlines(), delimiter=delim))
    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb[sheet] if sheet else wb.worksheets[0]
        rows = [['' if v is None else str(v) for v in r] for r in ws.iter_rows(values_only=True)]
        wb.close()
    if not rows:
        return [], []
    head = [h.strip() for h in rows[0]]
    return head, rows[1:]


def read_header(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.csv', '.tsv', '.txt'):
        return read_rows(path)[0]
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    head = next(wb.worksheets[0].iter_rows(values_only=True, max_row=1), ())
    wb.close()
    return [str(h).strip() for h in head if h is not None]


def guess_columns(head):
    low = {h.lower(): h for h in head if h}
    out = {}
    for k, names in GUESS.items():
        for n in names:
            if n.lower() in low:
                out[k] = low[n.lower()]
                break
    return out


def load_table(path, columns=None, sheet=None, progress=None):
    """List of boxes: {jp, kanji, en, speaker, group, id, row, k, nb, keys}. Cached in data/cache/.
    A game file (.sop, see pack.py) already holds the boxes."""
    if path.lower().endswith('.sop'):
        from .pack import read_pack
        return read_pack(path)[1]
    st = os.stat(path)
    tag = hashlib.md5(('%s|%s|%s|%s|%s' % (os.path.abspath(path), st.st_mtime, st.st_size, columns, sheet)).encode()).hexdigest()
    cache = data('cache', tag + '.pkl')
    if os.path.exists(cache):
        try:
            return pickle.load(open(cache, 'rb'))
        except Exception:
            pass
    if progress:
        progress('Reading the table (first time only)…')
    head, rows = read_rows(path, sheet)
    col = dict(guess_columns(head)); col.update(columns or {})
    idx = {k: head.index(v) for k, v in col.items() if v in head}
    if 'jp' not in idx and 'kanji' not in idx:
        raise RuntimeError('No Japanese column found in the table (expected e.g. "Jap", "Kanji" or "Texte JP").')
    if 'en' not in idx:
        raise RuntimeError('No English column found in the table (expected e.g. "Eng" or "Texte EN").')
    B = []
    for row, r in enumerate(rows, 2):
        g = lambda k: (r[idx[k]] if k in idx and idx[k] < len(r) and r[idx[k]] else '').replace('\r', '')
        jp = g('jp') or g('kanji')
        if not jp.strip():
            continue
        jb = BOX_SPLIT.split(jp.strip())
        kb = BOX_SPLIT.split(g('kanji').strip()) if 'kanji' in idx and 'jp' in idx else []
        eb = BOX_SPLIT.split(g('en').strip())
        if len(kb) != len(jb):
            kb = []
        sp = g('speaker_en') or g('speaker_jp')
        for k, j in enumerate(jb):
            kj = kb[k] if kb else ''
            B.append(dict(jp=j, kanji=kj if kj != j else '', en=eb[k] if len(eb) == len(jb) else g('en'),
                          speaker=sp, speaker_jp=g('speaker_jp'), group=g('group'), id=g('id'),
                          row=row, k=k + 1, nb=len(jb), keys=[x for x in {norm(j), norm(kj)} if x]))
    if not B:
        raise RuntimeError('The table has no Japanese text.')
    try:
        pickle.dump(B, open(cache, 'wb'))
    except Exception:
        pass
    return B
