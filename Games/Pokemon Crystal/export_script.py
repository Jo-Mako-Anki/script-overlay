"""Fabrique Pokemon Crystal.txt (pour le journal de Script Viewer) à partir du tableau.
Usage : python3 export_script.py "Pokemon Crystal.xlsx" "Deck\\Pokemon Crystal\\mGBA\\Pokemon Crystal.txt"
Colonnes écrites : UID, ID, Boîte, Jap, Kanji, Eng (texte lisible, sauts de ligne = \\n, noms = <P> <R> <PG>)."""
import re, sys

JP = {'<NI>': 'に　', '<TTE>': 'って', '<WO>': 'を　', '<TA!>': 'た！', '<KOUGEKI>': 'こうげき', '<WA>': 'は　',
      '<NO>': 'の　', '<GA>': 'が　', '<ROUTE>': 'ばん　どうろ', '<WATASHI>': 'わたし', '<KOKO_WA>': 'ここは　',
      '<……>': '⋯⋯', '<TRAINER>': 'トレーナー', '<PC>': 'パソコン', '<TM>': 'わざマシン', '<ROCKET>': 'ロケットだん',
      '<MOBILE>': 'モバイル', '<ID>': 'ＩＤ', '<zu>': 'ず', '<do>': 'ど', '<ENEMY>': 'てきの　', '#': 'ポケモン'}
EN = {'#': 'POKé', '<PK>': 'PK', '<MN>': 'MN', '<PKMN>': 'POKéMON', '<……>': '……', '<ENEMY>': 'Enemy ',
      '<TRAINER>': 'TRAINER', '<PC>': 'PC', '<TM>': 'TM', '<ROCKET>': 'ROCKET', '<ID>': 'ID', '<BSP>': ' '}
NAMES = {'<PLAYER>': '<P>', '<PLAY_G>': '<PG>', '<RIVAL>': '<R>', '{text_ram wPlayerName}': '<P>',
         '{nts_player_name 0}': '<P>', '<USER>': '<V>', '<TARGET>': '<V>'}
BREAK = re.compile(r'<(?:LINE|CONT|_CONT|SCROLL|NEXT|PARA|LF)>')

def common(t):
    if t is None: return ''
    t = str(t)
    if t.strip() in ('[NULL]', '@'): return ''
    for k, v in NAMES.items(): t = t.replace(k, v)
    t = re.sub(r'\{(text_ram|text_decimal|nts_\w+)[^}]*\}', '<V>', t)
    t = re.sub(r'\{[^}]*\}', '', t)                       # text_start, sons, pauses…
    t = re.sub(r'<(?:DONE|PROMPT|DEXEND)>', '', t)
    return t.replace('@', '')

def jp(t):
    t = common(t)
    for k, v in JP.items(): t = t.replace(k, v)
    t = re.sub('　+', '　', t)
    t = re.sub('　*(' + BREAK.pattern + ')', r'\1', t)
    t = BREAK.sub('\n', t)
    t = re.sub(r'<(?!P>|PG>|R>|V>)[^>]*>', '', t)
    return t.strip('\n').strip('　')

def en(t):
    t = common(t)
    for k, v in EN.items(): t = t.replace(k, v)
    t = re.sub(r'POKéMN', 'POKéMON', t.replace('PKMN', 'POKéMON'))
    t = re.sub(r'([a-z])-' + BREAK.pattern + r'([a-z])', r'\1\2', t)   # "every-<LINE>thing"
    t = BREAK.sub(' ', t)
    t = re.sub(r'<(?!P>|PG>|R>|V>)[^>]*>', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def rows_from_xlsx(path):
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True).active
    it = ws.iter_rows(values_only=True)
    hdr = [str(h or '').strip().lower() for h in next(it)]
    col = {h: i for i, h in enumerate(hdr)}
    for n, r in enumerate(it, start=2):
        uid = r[col['uid']] if 'uid' in col and r[col['uid']] is not None else n
        kj = r[col['kanji']] if 'kanji' in col else None
        yield uid, r[col['id']], r[col.get('boîte', 5)], r[col['jap']], kj, r[col['eng']]

def main(src, dst):
    out, n = ['UID\tID\tBoîte\tJap\tKanji\tEng'], 0
    for uid, id_, box, j, k, e in rows_from_xlsx(src):
        j2 = jp(j)
        k2 = jp(k) if k else ''
        if k2 == j2: k2 = ''                                  # pas de kanji : la page reprend le kana
        if not re.sub(r'<[^>]*>|\s|　', '', j2): continue
        cell = lambda s: (s or '').replace('\t', ' ').replace('\r', '').replace('\n', '\\n')
        out.append('\t'.join([str(uid), cell(str(id_ or '')), cell(str(box or '')), cell(j2), cell(k2), cell(en(e))]))
        n += 1
    open(dst, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    print(n, 'répliques écrites dans', dst)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
