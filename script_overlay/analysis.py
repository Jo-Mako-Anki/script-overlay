# -*- coding: utf-8 -*-
"""Furigana and dictionary for a Japanese line (offline, ~1 ms per line).

Word splitting: SudachiPy (+ sudachidict_core). Dictionary: JMdict (EDRDG, CC BY-SA 4.0), extracted into
resources/dico_jmdict.json.gz. If either is missing the app still works, without furigana / dictionary.
"""
import gzip, json, re, threading

from .paths import res

KANJI = re.compile(r'[㐀-鿿豈-﫿々〆ヶ]')
NO_DICT = ('補助記号', '空白', '助詞', '助動詞', '記号', '接頭辞')


def hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def furigana(surface, reading):
    """Splits a word into (text, reading) parts: the reading goes on the kanji only, not on the okurigana."""
    if not KANJI.search(surface) or not reading:
        return [[surface, '']]
    reading = hira(reading)
    if hira(surface) == reading:
        return [[surface, '']]
    parts = re.findall(r'[㐀-鿿豈-﫿々〆ヶ]+|[^㐀-鿿豈-﫿々〆ヶ]+', surface)
    pat = ''.join('(.+?)' if KANJI.match(m) else '(' + re.escape(hira(m)) + ')' for m in parts)
    r = re.fullmatch(pat, reading)
    if not r:
        return [[surface, reading]]
    return [[m, g if KANJI.match(m) else ''] for m, g in zip(parts, r.groups())]


class Analyzer:
    def __init__(self):
        self.tok = None; self.dico = None
        threading.Thread(target=self._load, daemon=True).start()  # ~2 s, without blocking start-up

    def _load(self):
        try:
            from sudachipy import dictionary
            self.tok = dictionary.Dictionary(dict='core').create()
        except Exception as e:
            print('Furigana unavailable (pip install sudachipy sudachidict_core):', e)
        try:
            self.dico = json.load(gzip.open(res('dico_jmdict.json.gz'), 'rt', encoding='utf-8'))
        except Exception as e:
            print('Dictionary unavailable:', e)

    def definitions(self, *forms):
        if not self.dico:
            return None
        for f in forms:
            ids = self.dico['i'].get(f)
            if ids:
                out = []
                for i in ids[:2]:
                    e = self.dico['e'][str(i)]
                    out.append({'word': '・'.join(e['k'][:2]) or e['r'][0], 'read': '・'.join(e['r'][:2]),
                                'senses': ['; '.join(g[:3]) for _, g in e['s'][:3]]})
                return out
        return None

    def analyze(self, text):
        """[{t: text, f: [[part, reading], ...], d: definitions or None}, ...]; None if not ready."""
        if self.tok is None or not text:
            return None
        words = []
        for li, line in enumerate(text.split('\n')):
            if li:
                words.append({'t': '\n', 'f': [['\n', '']], 'd': None})
            for m in self.tok.tokenize(line):
                s = m.surface()
                d = None if m.part_of_speech()[0] in NO_DICT else self.definitions(m.normalized_form(), m.dictionary_form(), s)
                words.append({'t': s, 'f': furigana(s, m.reading_form()), 'd': d})
        return words
