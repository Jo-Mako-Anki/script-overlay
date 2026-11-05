# Adds the characters to talk to (key "p") to infos.js, leaving the rest alone.
# Usage: python ajouter_pnj.py <pokecrystal folder> <path of infos.js>
# Exemple : python ajouter_pnj.py C:\travail\pokecrystal "Games\Pokemon Crystal\infos.js"
import sys, os, re, json
PC, JS = sys.argv[1].rstrip('/\\') + '/', sys.argv[2]
s = open(JS, encoding='utf-8').read()
i = s.index('= {"mons"') + 2
D, end = json.JSONDecoder().raw_decode(s[i:]); end += i
NK = {m['name']: k for k, m in D['maps'].items()}        # nom de carte -> "groupe.numéro"
SKIP = {'BOULDER', 'ROCK', 'CUT_TREE', 'FRUIT_TREE', 'POKE_BALL', 'STRENGTH_BOULDER', 'SUDOWOODO', 'BIG_SNORLAX', 'BIG_ONIX', 'BIG_LAPRAS', 'BIG_DOLL', 'PAPER', 'COMPUTER', 'MAP'}
for k in D['evenements']: D['evenements'][k].pop('p', None)
n = 0
for f in sorted(os.listdir(PC + 'maps')):
    name = f[:-4]; key = NK.get(name)
    if not f.endswith('.asm') or not key: continue
    src = open(PC + 'maps/' + f, encoding='utf-8').read()
    body = {}; lab = None
    for l in src.split('\n'):
        m = re.match(r'^(\w+):', l)
        if m: lab = m[1]; body[lab] = []; continue
        if lab: body[lab].append(l.split(';')[0].strip())
    P = []
    for m in re.finditer(r'object_event\s+(.*)', src):
        a = [x.strip() for x in m[1].split(';')[0].split(',')]
        if len(a) < 13: continue
        x, y, spr, typ, scr, fl = int(a[0]), int(a[1]), a[2].replace('SPRITE_', ''), a[9], a[11], a[12]
        if typ not in ('OBJECTTYPE_SCRIPT', 'OBJECTTYPE_COMMAND') or spr in SKIP: continue
        if any(re.match(r'(loadtrainer|trainer)\b', l) for l in body.get(scr, [])): continue   # déjà dans les dresseurs
        P.append([x, y, spr, 0 if fl == '-1' else 1])
    if P:
        D['evenements'].setdefault(key, {})['p'] = P; n += len(P)
out = s[:i] + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + s[end:]
open(JS, 'w', encoding='utf-8').write(out)
print(n, 'characters added in', len(D['evenements']), 'maps ->', JS)
