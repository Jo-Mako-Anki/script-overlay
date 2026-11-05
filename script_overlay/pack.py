# -*- coding: utf-8 -*-
"""Game file (.sop): the dialogues of a table, compressed and scrambled, so the apps run without the table.

Not real protection (the key is in the apps), only enough that the dialogues can't be opened in Excel or a
text editor. Format: b'SOP2' + 16-byte nonce + (zlib(JSON) XOR keystream). The JSON holds
  meta   {name, code, hook, folder}
  boxes  the text boxes for Script Overlay (tables.load_table)
  sheets {sheet name: rows (lists of strings)} for Script Viewer (optional, --sheets)
The keystream is simple on purpose: Script Viewer.html decodes it too (readSop).
Old files (b'SOP1', numpy PCG64 keystream) can still be read.

Make one from a table (no button in the apps on purpose):
  python -m script_overlay.pack <table.xlsx> <out.sop> --name "Game" [--code P5R] [--hook p5r] [--folder "Game"]
                                [--col jp=Jap --col en=Eng ...] [--sheet Sheet1] [--sheets]
"""
import argparse, hashlib, json, os, zlib

import numpy as np

MAGIC = b'SOP2'
_KEY = b'ScriptOverlay/game-file/v1'


def _seed(nonce):
    """FNV-1a (32 bits) of key + nonce."""
    h = 0x811C9DC5
    for b in _KEY + nonce:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def _xor(raw, nonce):
    """XOR with a counter keystream: word k = lowbias32(k ^ seed), 4 bytes little-endian per word."""
    n = len(raw)
    with np.errstate(over='ignore'):
        x = np.arange((n + 3) // 4, dtype=np.uint32) ^ np.uint32(_seed(nonce))
        x ^= x >> np.uint32(16); x *= np.uint32(0x7FEB352D)
        x ^= x >> np.uint32(15); x *= np.uint32(0x846CA68B)
        x ^= x >> np.uint32(16)
    ks = x.astype('<u4').view(np.uint8)[:n]
    return (np.frombuffer(raw, np.uint8) ^ ks).tobytes()


def _xor_v1(raw, nonce):
    seed = int.from_bytes(hashlib.sha256(_KEY + nonce).digest(), 'little')
    ks = np.random.Generator(np.random.PCG64(seed)).bytes(len(raw))
    return (np.frombuffer(raw, np.uint8) ^ np.frombuffer(ks, np.uint8)).tobytes()


def write_pack(path, meta, boxes, sheets=None):
    d = {'meta': meta, 'boxes': boxes}
    if sheets:
        d['sheets'] = sheets
    body = zlib.compress(json.dumps(d, ensure_ascii=False).encode('utf-8'), 9)
    nonce = os.urandom(16)
    tmp = path + '.part'
    with open(tmp, 'wb') as f:
        f.write(MAGIC + nonce + _xor(body, nonce))
    os.replace(tmp, path)


def read_all(path):
    """Whole content of a .sop file: {meta, boxes, sheets?}."""
    raw = open(path, 'rb').read()
    xor = {b'SOP2': _xor, b'SOP1': _xor_v1}.get(raw[:4])
    if not xor:
        raise RuntimeError('Not a Script Overlay game file.')
    return json.loads(zlib.decompress(xor(raw[20:], raw[4:20])).decode('utf-8'))


def read_pack(path):
    """(meta, boxes) of a .sop file."""
    d = read_all(path)
    return d.get('meta') or {}, d['boxes']


def read_sheets(path):
    """{sheet name: rows} of a table, all sheets, as strings (what Script Viewer reads)."""
    from .tables import read_rows
    if os.path.splitext(path)[1].lower() != '.xlsx':
        head, rows = read_rows(path)
        return {os.path.basename(path): [head] + rows}
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    out = {ws.title: [['' if v is None else str(v) for v in r] for r in ws.iter_rows(values_only=True)]
           for ws in wb.worksheets}
    wb.close()
    return out


def main():
    from .tables import load_table
    p = argparse.ArgumentParser(description='Table -> Script Overlay game file (.sop)')
    p.add_argument('table'); p.add_argument('out')
    p.add_argument('--name', required=True); p.add_argument('--code'); p.add_argument('--hook')
    p.add_argument('--folder'); p.add_argument('--sheet')
    p.add_argument('--sheets', action='store_true', help='also keep the whole table, for Script Viewer (mGBA)')
    p.add_argument('--col', action='append', default=[], help='key=column, e.g. jp=Jap (keys: jp kanji en '
                                                                'speaker_jp speaker_en group id)')
    a = p.parse_args()
    cols = dict(c.split('=', 1) for c in a.col) or None
    boxes = load_table(a.table, cols, a.sheet, print)
    meta = {k: v for k, v in dict(name=a.name, code=a.code, hook=a.hook, folder=a.folder).items() if v}
    write_pack(a.out, meta, boxes, read_sheets(a.table) if a.sheets else None)
    print('%s: %d text boxes, %.1f MB' % (a.out, len(boxes), os.path.getsize(a.out) / 1e6))


if __name__ == '__main__':
    main()
