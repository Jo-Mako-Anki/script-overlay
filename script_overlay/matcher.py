# -*- coding: utf-8 -*-
"""Finds the table box that matches a text read on screen (OCR) or sent by a game script.

Order: exact match (box, or whole row for game scripts) -> the boxes that follow the last match in the table
(the next line is by far the most likely, this fixes most OCR errors) -> fuzzy search in the whole table.
"""
import bisect, re, unicodedata

from rapidfuzz import fuzz, process

JAP = re.compile(r'[぀-ヿ㐀-鿿０-ｚ]')


def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    return re.sub(r'[\s・…‥\.。、,!?「」『』\-ー~〜―▼▽]', '', s)


def clean_ocr(text):
    """Keeps the OCR lines that look like Japanese (portraits and backgrounds give noise lines)."""
    keep = []
    for l in text.split(' / '):
        l = l.strip(); nj = len(JAP.findall(l)); nt = len(re.sub(r'\s', '', l))
        if nj >= 2 and nj >= 0.5 * nt:
            keep.append(l)
    return ''.join(keep)


def score(q, key):
    if not q or not key:
        return 0
    s = fuzz.ratio(q, key)
    if len(key) >= 4 and len(q) > len(key):
        s = max(s, fuzz.partial_ratio(key, q) * 0.95)
    return s


class Matcher:
    def __init__(self, B):
        self.B = B
        self.keys = []; self.key_box = []
        self.exact = {}; self.rows = {}
        self.pos = {}  # group -> box indices in table order
        for i, b in enumerate(B):
            for k in b['keys']:
                self.keys.append(k); self.key_box.append(i)
                self.exact.setdefault(k, []).append(i)
            self.pos.setdefault(b['group'], []).append(i)
        i = 0
        while i < len(B):
            j = self.row_end(i)
            for kk in ('jp', 'kanji'):
                whole = norm(''.join(B[x][kk] for x in range(i, j + 1)))
                if whole:
                    self.rows.setdefault(whole, []).append(i)
            i = j + 1
        self.last = None

    def row_end(self, i):
        j = i
        while j + 1 < len(self.B) and self.B[j + 1]['row'] == self.B[i]['row']:
            j += 1
        return j

    def best(self, q, i):
        return max(score(q, k) for k in self.B[i]['keys'])

    def following(self):
        if self.last is None:
            return []
        L = self.pos[self.B[self.last]['group']]
        j = bisect.bisect_left(L, self.last)
        return L[max(0, j - 3):j + 40]

    def pick(self, cands):
        """Among copies of the same line, the nearest one after the last match, in the same group."""
        if self.last is not None:
            g = self.B[self.last]['group']
            near = [c for c in cands if self.B[c]['group'] == g and c > self.last]
            if near:
                return min(near)
        return cands[0]

    def find(self, text, ocr=False):
        """(box index or None, score 0-100, whole_row)."""
        q = norm(clean_ocr(text) if ocr else text)
        if len(q) < 2:
            return None, 0, False
        if not ocr and q in self.rows:
            return self.pick(self.rows[q]), 100, True
        if q in self.exact:
            return self.pick(self.exact[q]), 100, False
        best, bs = None, 0
        for i in self.following():
            s = self.best(q, i)
            if s > bs:
                best, bs = i, s
        if bs >= 80:
            return best, bs, False
        cb, cs = best, bs
        best, bs = None, 0
        for _, _, k in process.extract(q, self.keys, scorer=fuzz.ratio, limit=25, score_cutoff=40):
            i = self.key_box[k]
            s = self.best(q, i)
            if s > bs:
                best, bs = i, s
        if cb is not None and cs >= 55 and cs >= bs - 15:
            return cb, cs, False
        if best is None or bs < (70 if len(q) >= 6 else 85):
            return None, bs, False
        return best, bs, False
