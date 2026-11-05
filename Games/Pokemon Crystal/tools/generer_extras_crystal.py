# Outil de fabrication (pas besoin pour jouer) : Pokédex japonais, équipes des dresseurs et événements des cartes,
# puis écrit infos.js (= gen/crystal.json de generer_pokemon_crystal.py + ces données).
# Dossier de travail : variable SV_TRAVAIL (pokecrystal/, jp/<ROM japonaise>.gbc, gen/).
import os, re, json
T = os.environ.get('SV_TRAVAIL', '.')
PC = T + '/pokecrystal/'
JP = open(T + '/jp/Pocket Monsters - Crystal Version (Japan).gbc', 'rb').read()
code = {int(k): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'code.json'))).items()}
inv = {}
for k, v in code.items(): inv.setdefault(v, k)
for a, b in (('リ', 'り'), ('ヘ', 'へ'), ('ベ', 'べ'), ('ペ', 'ぺ')): inv[a] = inv[b]
AMB = {'り': 'リ', 'へ': 'ヘ', 'べ': 'ベ', 'ぺ': 'ペ'}; KATA = re.compile('[ァ-ヺー]')
def fixkata(s):
    # へ べ ぺ り : même tuile pour hiragana et katakana ; katakana si un voisin est en katakana
    c = list(s)
    for _ in range(2):
        for i, x in enumerate(c):
            if x in AMB and ((i > 0 and KATA.match(c[i-1])) or (i+1 < len(c) and KATA.match(c[i+1]))): c[i] = AMB[x]
    return ''.join(c)
def dec(b): return fixkata(''.join(code.get(x, '?') for x in b))
def consts(path):
    d = {}; k = 0
    for l in open(PC + path):
        l = l.split(';')[0]
        m = re.match(r'\s*const_def\s*(\S*)', l)
        if m: k = int(m[1].replace('$', '0x'), 0) if m[1] else 0; continue
        m = re.match(r'\s*const_next\s*(\S+)', l)
        if m: k = int(m[1].replace('$', '0x'), 0); continue
        if re.match(r'\s*const_skip', l): k += 1; continue
        m = re.match(r'\s*const (\w+)', l)
        if m: d.setdefault(m[1], k); k += 1
    return d

# ---------------------------------------------------------------- Pokédex
# entrée : catégorie @, taille (dm), poids (hg, 2 octets), texte jusqu'à $5F
SPEC = {0x4a: 'が　', 0x56: '……', 0x5b: 'パソコン', 0x5c: 'わざマシン', 0x5d: 'トレーナー', 0x5e: 'ロケットだん', 0x1d: 'に　', 0x1e: 'って',
        0x1f: 'を　', 0x22: 'た！', 0x23: 'こうげき', 0x24: 'は　', 0x25: 'の　', 0x54: 'ポケモン', 0x4e: '\n', 0x4f: '\n', 0x55: '\n', 0x51: '\n', 0x7f: '　'}
def entry(o):
    e = JP.find(b'\x50', o, o + 9)
    if e < 0 or e == o or any(b not in code for b in JP[o:e]): return None
    cat = dec(JP[o:e]); h = JP[e+1]; w = JP[e+2] | JP[e+3] << 8
    t = e + 4; s = []; bad = 0
    while JP[t] not in (0x5f, 0x50) and len(s) < 150:
        b = JP[t]
        if b in SPEC: s.append(SPEC[b])
        elif b in code: s.append(code[b])
        else: bad += 1
        t += 1
    if bad or JP[t] != 0x5f or not (0 < h < 250) or len(s) < 20: return None
    return [cat, h, w, fixkata(''.join(s)).replace('　\n', '\n').strip()], t + 1
# la ROM JP range le Pokédex en plusieurs tables : une table de pointeurs, ses entrées, puis la table suivante
dex = []; tbl = 0x44337; bank = 0x11
while len(dex) < 251:
    n0 = len(dex); i = 0; end = None
    while True:
        p = JP[tbl+2*i] | JP[tbl+2*i+1] << 8
        if not (0x4000 <= p < 0x8000): break
        r = entry(bank * 0x4000 + p - 0x4000)
        if not r: break
        dex.append(r[0]); end = r[1]; i += 1
    if len(dex) == n0: raise SystemExit('Pokédex : table introuvable à ' + hex(tbl))
    tbl = end
dex = dex[:251]
print('Pokédex :', len(dex), dex[24][:3])

# ---------------------------------------------------------------- dresseurs (équipes : pokecrystal ; noms : ROM JP)
SP=consts('constants/pokemon_constants.asm'); MV=consts('constants/move_constants.asm'); IT=consts('constants/item_constants.asm')
TT={'TRAINERTYPE_NORMAL':0,'TRAINERTYPE_MOVES':1,'TRAINERTYPE_ITEM':2,'TRAINERTYPE_ITEM_MOVES':3}
# ordre des groupes = classes 1, 2, 3…
order=[m[1] for m in re.finditer(r'dw (\w+Group)', open(PC+'data/trainers/party_pointers.asm').read())]
groups={}; cur=None; tr=None
for l in open(PC+'data/trainers/parties.asm'):
    l=l.split(';')[0].strip()
    m=re.match(r'(\w+Group):',l)
    if m: cur=groups.setdefault(m[1],[]); continue
    m=re.match(r'db "(.*)@", (TRAINERTYPE_\w+)',l)
    if m: tr={'en':m[1],'type':TT[m[2]],'mons':[]}; cur.append(tr); continue
    if l.startswith('db -1'): tr=None; continue
    m=re.match(r'db\s+(\d+),\s*(.*)',l)
    if m and tr is not None:
        a=[x.strip() for x in m[2].split(',')]
        mon=[int(m[1]), SP[a[0]]]; k=1
        if tr['type'] in (2,3): mon.append(IT[a[k]]); k+=1
        else: mon.append(0)
        mon.append([MV[x] for x in a[k:k+4]] if tr['type'] in (1,3) else [])
        tr['mons'].append(mon)
def tail(t):
    b=[t['type']]
    for lv,sp,it,mv in t['mons']:
        b+=[lv,sp]+([it] if t['type'] in (2,3) else [])+(mv if t['type'] in (1,3) else [])
    return bytes(b+[0xFF])
ok=0; classes=[]
for g in order:
    ts=groups[g]
    pat=b'(?<=\xff)'+b''.join(b'([^\x50\xff]{1,12})\x50'+re.escape(tail(t)) for t in ts)
    ms=list(re.finditer(pat,JP,re.DOTALL)); fb=not ms
    if not ms and ts: ms=list(re.finditer(b'(?<=[\x40-\x7f])'+pat[len(b'(?<=\xff)'):],JP,re.DOTALL))[-1:]
    if len(ms)>1 and len({m.groups() for m in ms})==1: ms=ms[:1]
    if len(ms)!=1: print('pas trouvé', g, len(ms), len(ts))
    if len(ms)==1 and ts:
        ok+=1
        for i,(t,nm) in enumerate(zip(ts,ms[0].groups())):
            if i==0 and fb: nm=re.split(rb'[\x40-\x7f]',nm)[-1]  # 1er nom : couper ce qui précède (pointeurs)
            t['jp']=dec(nm)
    classes.append([{'n':t.get('jp') or t['en'],'en':t['en'],'m':[[lv,sp,it,mv] if mv or it else [lv,sp] for lv,sp,it,mv in t['mons']]} for t in ts])
print('groupes trouvés en JP :', ok, '/', len(order))
# noms des classes : liste JP qui commence par 8 fois « ジムリーダー »
en_cls=re.findall(r'li "([^"]*)"', open(PC+'data/trainers/class_names.asm').read())
start=JP.find((bytes(inv[c] for c in 'ジムリーダー')+b'\x50')*8)
jp_cls=[]
if start>=0:
    o=start
    for _ in en_cls: e=JP.index(b'\x50',o); jp_cls.append(dec(JP[o:e])); o=e+1
TRAINERS={'classes':[{'jp':j,'en':e} for j,e in zip(jp_cls or en_cls,en_cls)],'trainers':classes}

# ---------------------------------------------------------------- événements des cartes
EV=consts('constants/event_flags.asm'); IT=consts('constants/item_constants.asm')
# classes et numéros de dresseurs
CL={}; TID={}; c=-1; k=1
for l in open(PC+'constants/trainer_constants.asm'):
    l=l.split(';')[0]
    m=re.match(r'\s*trainerclass (\w+)',l)
    if m: c+=1; CL[m[1]]=c; k=1; cur=m[1]; continue
    m=re.match(r'\s*const (\w+)',l)
    if m and c>=0: TID[(cur,m[1])]=k; k+=1
# constante de carte -> "groupe.numéro"
MK={}; g=0; n=0
for l in open(PC+'constants/map_constants.asm'):
    if re.match(r'\s*newgroup',l): g+=1; n=0
    m=re.match(r'\s*map_const (\w+),',l)
    if m: n+=1; MK[m[1]]=f'{g}.{n}'
# nom de carte -> clé (ordre de maps.asm, comme gen.py)
NK={}; g=0; n=0
for l in open(PC+'data/maps/maps.asm'):
    if re.match(r'^MapGroup_\w+:',l): g+=1; n=0
    m=re.match(r'\s*map (\w+), ',l)
    if m and g: n+=1; NK[m[1]]=f'{g}.{n}'
NON_PNJ={'POKE_BALL','FRUIT_TREE','BOULDER','ROCK','POKEDEX','PAPER','CONSOLE','DOLL_1','DOLL_2','BIG_DOLL','BIG_SNORLAX','SURF'}
def num(s): return int(s.replace('$','0x'),0)
def flag(s): return EV.get(s.strip(),-1)
out={}; miss=[]
for f in sorted(os.listdir(PC+'maps')):
    if not f.endswith('.asm'): continue
    name=f[:-4]; key=NK.get(name)
    if not key: continue
    src=open(PC+'maps/'+f).read()
    # corps de chaque étiquette (jusqu'à la prochaine étiquette de haut niveau)
    body={}; lab=None
    for l in src.split('\n'):
        m=re.match(r'^(\w+):',l)
        if m: lab=m[1]; body[lab]=[]; continue
        if lab: body[lab].append(l.split(';')[0].strip())
    def find(lab, pat):
        for l in body.get(lab,[]):
            m=re.match(pat,l)
            if m: return m
    e={}
    for m in re.finditer(r'warp_event\s+(\d+),\s*(\d+),\s*(\w+),\s*(\d+)',src):
        e.setdefault('w',[]).append([int(m[1]),int(m[2]),MK.get(m[3],'')])
    for m in re.finditer(r'bg_event\s+(\d+),\s*(\d+),\s*BGEVENT_ITEM,\s*(\w+)',src):
        h=find(m[3], r'hiddenitem (\w+),\s*(\w+)')
        if h: e.setdefault('h',[]).append([int(m[1]),int(m[2]),IT.get(h[1],0),flag(h[2])])
        else: miss.append(('h',name,m[3]))
    for m in re.finditer(r'object_event\s+(.*)',src):
        a=[x.strip() for x in m[1].split(',')]
        x,y,typ,scr,fl=int(a[0]),int(a[1]),a[9],a[11],a[12]
        if typ=='OBJECTTYPE_ITEMBALL':
            it=find(scr, r'itemball (\w+)')
            if it: e.setdefault('i',[]).append([x,y,IT.get(it[1],0),flag(fl)])
            else: miss.append(('i',name,scr))
        elif typ=='OBJECTTYPE_TRAINER':
            t=find(scr, r'trainer (\w+),\s*(\w+),\s*(\w+)')
            if t: e.setdefault('t',[]).append([x,y,CL[t[1]],TID[(t[1],t[2])],flag(t[3])])
            else: miss.append(('t',name,scr))
        elif typ=='OBJECTTYPE_SCRIPT' and scr in body:
            # champions d'arène et autres combats scriptés : loadtrainer + checkevent EVENT_BEAT_…
            lt=find(scr, r'loadtrainer (\w+),\s*(\w+)')
            if lt and lt[1] in CL and (lt[1],lt[2]) in TID:
                ce=find(scr, r'checkevent (EVENT_BEAT_\w+)')
                e.setdefault('t',[]).append([x,y,CL[lt[1]],TID[(lt[1],lt[2])],flag(ce[1]) if ce else -1])
            elif a[2].replace('SPRITE_','') not in NON_PNJ:
                # personne à qui parler : position de départ, sprite, 1 = n'est là qu'à certains moments (drapeau d'événement)
                e.setdefault('p',[]).append([x,y,a[2].replace('SPRITE_',''),0 if fl=='-1' else 1])
    if e: out[key]=e
print('Cartes :', len(out), 'avec événements ; manqués', miss)
MASQUER = '''// répliques du système de combat (menus, attaques, noms) : pas affichées pendant un combat, sauf l'annonce du combat
DONNEES["Pokemon Crystal"].masquer_en_combat = { debut: ["battle.", "common_1.", "common_2.", "common_3.", "menu.", "names.", "fixed_words.", "party_menu.", "stats_screen.", "text.", "core.", "class_names.", "generic_callee.", "trainer_names."], sauf: ["battle.WantsToBattleText"] };
'''
D = json.load(open(T + '/gen/crystal.json', encoding='utf-8'))
D['cartes'] = 'maps/'
D['dex'] = dex; D['dresseurs'] = TRAINERS; D['evenements'] = out
js = ('// Données de Pokémon Crystal pour Script Viewer.html (générées par generer_pokemon_crystal.py et generer_extras_crystal.py :'
      ' noms et textes JP lus dans la ROM japonaise, le reste vient de pokecrystal)\nwindow.DONNEES = window.DONNEES || {};\nDONNEES["Pokemon Crystal"] = '
      + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ';\n' + MASQUER)
open(T + '/gen/infos.js', 'w', encoding='utf-8').write(js)
print('infos.js :', len(js.encode()) // 1024, 'Ko')
