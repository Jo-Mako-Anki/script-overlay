# -*- coding: utf-8 -*-
"""Pokopia.xlsx (A=ID, B=anglais brut, C=japonais brut, balises du jeu) -> Pokopia_overlay.xlsx pour Script Overlay.
Colonnes : ID, Fichier, Jap (lecture en kana), Kanji, Eng. Une case = une ligne ; boîtes séparées par un retour à la ligne
(<clear>/<slide> du jeu). Usage : python convertir_pokopia.py <source.xlsx> <sortie.xlsx>"""
import re, sys, openpyxl

SRC, DST = sys.argv[1], sys.argv[2]
BOX = re.compile(r'<(?:clear|slide)>')
VAR_JP = {'pname': '〇〇', 'nowner': '〇〇', 'acqpname': '〇〇', 'cname': '〇〇', 'spwname': '〇〇'}
VAR_EN = {'pname': '[Name]', 'nowner': '[Name]', 'acqpname': '[Name]', 'cname': '[Name]', 'spwname': '[Name]'}

def clean(s, jp, mode):
    # mode: 'kana' or 'kanji' for furigana <漢字:かな>
    s = re.sub(r'<([^<>:;$/][^<>:]*):([^<>]+)>', (lambda m: m.group(2)) if mode == 'kana' else (lambda m: m.group(1)), s)
    def var(m):
        name = m.group(1).lstrip('$')
        d = VAR_JP if jp else VAR_EN
        if name in d: return d[name]
        if name.startswith(('iname', 'ifull', 'spwfull', 'sklfull', 'pksrchtar', 'cname', 'pkkind', 'fqty', 'stflevel', 'ininameicon')):
            return '＊' if jp else '*'
        return ''
    s = re.sub(r'<\$?([A-Za-z_/][^<>;(,]*)[^<>]*>', var, s)
    return s

def boxes(raw, jp, mode):
    out = []
    for b in BOX.split(raw):
        b = b.replace('<br>', '\u3000' if jp else ' ')
        b = clean(b, jp, mode)
        b = re.sub(r'[ 　]+', lambda m: '　' if jp and '　' in m.group(0) else ' ', b).strip(' 　\n')
        if b: out.append(b)
    return out

wb = openpyxl.load_workbook(SRC, read_only=True)
o = openpyxl.Workbook(); ws = o.active; ws.title = 'Pokopia'
ws.append(['ID', 'Fichier', 'Jap', 'Kanji', 'Eng'])
n = mis = 0
for r in wb.worksheets[0].iter_rows(values_only=True):
    i, en, jp = (list(r) + [None] * 3)[:3]
    if not jp: continue
    ja, jk, e = boxes(str(jp), True, 'kana'), boxes(str(jp), True, 'kanji'), boxes(str(en or ''), False, '')
    if not ja: continue
    if len(e) != len(ja):
        mis += 1; e = [' '.join(e)]  # boîtes différentes : anglais entier pour chaque boîte
    fic = '.'.join(str(i).split('.')[:2]) if i else ''
    ws.append([i, fic, '\n'.join(ja), '\n'.join(jk), '\n'.join(e)]); n += 1
o.save(DST)
print(n, 'lignes ;', mis, "lignes où l'anglais n'a pas le même nombre de boîtes")
