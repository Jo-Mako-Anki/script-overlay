# Outil de fabrication des données (pas besoin pour jouer). Dossier de travail : variable SV_TRAVAIL, qui contient
#   pokecrystal/ (désassemblage pret/pokecrystal compilé), jp/<ROM japonaise>.gbc, gen/ (sorties).
import os
T = os.environ.get('SV_TRAVAIL', '.')
# Données de Pokémon Crystal pour la page (noms JP depuis la ROM japonaise, le reste depuis pokecrystal US)
import re, json
PC=T+'/pokecrystal/'
US=open(PC+'pokecrystal.gbc','rb').read()
JP=open(T+'/jp/Pocket Monsters - Crystal Version (Japan).gbc','rb').read()
sym={}
for l in open(PC+'pokecrystal.sym'):
    m=re.match(r'([0-9a-f]{2}):([0-9a-f]{4}) (\S+)',l)
    if m: sym[m[3]]=(int(m[1],16),int(m[2],16))
def off(name):
    b,a=sym[name]; return a if a<0x4000 else b*0x4000+a-0x4000
def boff(b,a): return a if a<0x4000 else b*0x4000+a-0x4000
# charmaps
ENm={}
for l in open(PC+'constants/charmap.asm',encoding='utf-8'):
    m=re.match(r'\s*charmap "(.*?)",\s*\$([0-9a-f]{2})',l)
    if m and int(m[2],16) not in ENm: ENm[int(m[2],16)]=m[1]
JPm={int(k):v for k,v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'code.json'))).items()}
def dec_en(b): return ''.join(ENm.get(x,'') for x in b).replace('<BSP>',' ').replace('<LF>',' ').replace('<PK><MN>','PKMN').strip()
AMB={'へ':'ヘ','べ':'ベ','ぺ':'ペ','り':'リ'}
KATA=re.compile('[ァ-ンー]')
def fixkata(s):
    # へ べ ぺ り : même tuile pour hiragana et katakana ; katakana si un voisin est en katakana
    c=list(s)
    for _ in range(2):
        for i,x in enumerate(c):
            if x in AMB and ((i>0 and KATA.match(c[i-1])) or (i+1<len(c) and KATA.match(c[i+1]))): c[i]=AMB[x]
    return ''.join(c)
def dec_jp(b): return fixkata(''.join(JPm.get(x,'') for x in b).replace('┐','').strip())
def strs(rom,o,n,dec):
    out=[]
    for i in range(n):
        e=rom.index(b'\x50',o); out.append(dec(rom[o:e])); o=e+1
    return out
NMON=251
mon_en=[dec_en(US[off('PokemonNames')+10*i:off('PokemonNames')+10*i+10].split(b'\x50')[0]) for i in range(NMON)]
mon_jp=[dec_jp(JP[0x5341a+5*i:0x5341a+5*i+5].split(b'\x50')[0]) for i in range(NMON)]
move_en=strs(US,off('MoveNames'),251,dec_en); move_jp=strs(JP,0x4163b,251,dec_jp)
item_en=strs(US,off('ItemNames'),255,dec_en); item_jp=strs(JP,0x70fa,255,dec_jp)
# types (constantes pokecrystal)
TYPES={0:('ノーマル','Normal'),1:('かくとう','Fighting'),2:('ひこう','Flying'),3:('どく','Poison'),4:('じめん','Ground'),5:('いわ','Rock'),6:('とり','Bird'),7:('むし','Bug'),8:('ゴースト','Ghost'),9:('はがね','Steel'),
 19:('？？？','???'),20:('ほのお','Fire'),21:('みず','Water'),22:('くさ','Grass'),23:('でんき','Electric'),24:('エスパー','Psychic'),25:('こおり','Ice'),26:('ドラゴン','Dragon'),27:('あく','Dark')}
# base stats
bd=off('BaseData'); mons=[]
for i in range(NMON):
    b=US[bd+32*i:bd+32*i+32]
    mons.append({'jp':mon_jp[i],'en':mon_en[i],'stats':list(b[1:7]),'types':sorted({b[7],b[8]},key=[b[7],b[8]].index)})
# moves
mv=off('Moves'); moves=[]
for i in range(251):
    b=US[mv+7*i:mv+7*i+7]
    moves.append({'jp':move_jp[i],'en':move_en[i],'power':b[2],'type':b[3],'acc':round(b[4]*100/255),'pp':b[5]})
# learnsets / évolutions
bank=sym['EvosAttacksPointers'][0]; ep=off('EvosAttacksPointers')
for i in range(NMON):
    p=boff(bank,US[ep+2*i]|US[ep+2*i+1]<<8); evo=[]
    while US[p]:
        meth=US[p]
        if meth==5: evo.append([meth,US[p+1],US[p+2],US[p+3]]); p+=4
        else: evo.append([meth,US[p+1],US[p+2]]); p+=3
    p+=1; learn=[]
    while US[p]: learn.append([US[p],US[p+1]]); p+=2
    mons[i]['learn']=learn; mons[i]['evo']=evo
# table des types
tm=off('TypeMatchups'); chart=[]
p=tm
while US[p]!=0xFF:
    if US[p]==0xFE: p+=1; continue
    chart.append([US[p],US[p+1],US[p+2]]); p+=3
# cartes : (groupe, numéro) -> nom EN de la carte, repère (landmark)
maps={}; g=0; n=0
for l in open(PC+'data/maps/maps.asm'):
    if re.match(r'^MapGroup_\w+:',l): g+=1; n=0
    m=re.match(r'\s*map (\w+), \w+, \w+, (\w+),',l)
    if m and g: n+=1; maps[f'{g}.{n}']={'name':m[1],'lm':m[2]}
lmc=[]
for l in open(PC+'constants/landmark_constants.asm'):
    m=re.match(r'\s*const (LANDMARK_\w+)',l)
    if m: lmc.append(m[1])
lb=off('Landmarks'); lbank=sym['Landmarks'][0]
lms=[]; ptrs=[]
for i in range(len(lmc)):
    x,y,lo,hi=US[lb+4*i:lb+4*i+4]; ptrs.append(lo|hi<<8); lms.append({'x':x,'y':y,'ptr':lo|hi<<8})
uptr=sorted(set(ptrs)); first=boff(lbank,uptr[0])
# noms à la suite dans la ROM US ; la ROM JP les range dans le même ordre
starts=[]; o=first
while len(starts)<len(uptr)+20:
    starts.append(o); o=US.index(b'\x50',o)+1
en_names=strs(US,first,len(starts),dec_en); jp_names=strs(JP,0x926d7,len(starts),dec_jp)
bypt={p:((jp_names[starts.index(boff(lbank,p))],en_names[starts.index(boff(lbank,p))]) if boff(lbank,p) in starts else ('','')) for p in uptr}
landmarks={c:{'x':lms[i]['x'],'y':lms[i]['y'],'jp':bypt[lms[i]['ptr']][0],'en':bypt[lms[i]['ptr']][1]} for i,c in enumerate(lmc)}
for k,v in maps.items(): v['lm']=lmc.index(v['lm']) if v['lm'] in lmc else -1
# Pokémon sauvages
const={}
mapconst={}
g=0
for l in open(PC+'constants/map_constants.asm'):
    if re.match(r'\s*newgroup',l): g+=1; n=0
    m=re.match(r'\s*map_const (\w+),',l)
    if m: n+=1; mapconst[m[1]]=f'{g}.{n}'
spc={}
k=0
for l in open(PC+'constants/pokemon_constants.asm'):
    m=re.match(r'\s*const_def\s*(\d*)',l)
    if m: k=int(m[1] or 0); continue
    m=re.match(r'\s*const (\w+)',l)
    if m: spc.setdefault(m[1],k); k+=1
wild={}
for f,kind in [('johto_grass','grass'),('kanto_grass','grass'),('johto_water','water'),('kanto_water','water')]:
    cur=None
    for l in open(PC+f'data/wild/{f}.asm'):
        m=re.match(r'\s*def_(grass|water)_wildmons (\w+)',l)
        if m: cur=wild.setdefault(mapconst[m[2]],{}).setdefault(kind,[]); continue
        m=re.match(r'\s*db (\d+), (\w+)\s*(;.*)?$',l)
        if m and cur is not None and m[2] in spc: cur.append([int(m[1]),spc[m[2]]])
        if 'end_' in l: cur=None
out={'mons':mons,'moves':moves,'items':[{'jp':a,'en':b} for a,b in zip(item_jp,item_en)],'types':{k:{'jp':a,'en':b} for k,(a,b) in TYPES.items()},
     'chart':chart,'maps':maps,'landmarks':[landmarks[c] for c in lmc],'wild':wild}
open(T+'/gen/crystal.json','w').write(json.dumps(out,ensure_ascii=False))
print(mons[151]['jp'],mons[151]['en'],mons[151]['types'],mons[151]['learn'][:4]); print(moves[0],moves[32]); print(item_jp[:3],item_en[:3])
print(len(maps),maps['24.4'] if '24.4' in maps else list(maps.items())[:2]); print([landmarks[c] for c in lmc[:4]]); print(len(wild), list(wild.items())[0])
print(len(uptr),len(en_names)); print(list(zip(jp_names,en_names))); print(list(zip(jp_names,en_names))[:6], list(zip(jp_names,en_names))[-4:])

# cartes de la région (Pokégear) : 160x144, agrandies ×3, en PNG data: URL
from PIL import Image
import base64, io
tm=Image.open(PC+'gfx/pokegear/town_map.png').convert('L')
pal=[]
for l in open(PC+'gfx/pokegear/pokegear.pal'):
    m=re.match(r'\s*RGB (\d+), (\d+), (\d+)',l)
    if m: pal.append(tuple(int(x)*255//31 for x in m.groups()))
pals=[pal[i*4:i*4+4] for i in range(6)]
NAMES=['BORDER','EARTH','MOUNTAIN','CITY','POI','POI_MTN']
palmap=[]
for l in open(PC+'gfx/pokegear/town_map_palette_map.asm'):
    m=re.match(r'\s*townmappals (.*)',l)
    if m: palmap+= [NAMES.index(x.strip()) for x in m[1].split(',')]
def render(fn):
    d=open(PC+'gfx/pokegear/'+fn,'rb').read()
    im=Image.new('RGB',(160,144))
    for i in range(360):
        t=d[i]; tx,ty=(t%16)*8,(t//16)*8; p=pals[palmap[t] if t<len(palmap) else 0]
        for y in range(8):
            for x in range(8):
                v=tm.getpixel((tx+x,ty+y)); im.putpixel(((i%20)*8+x,(i//20)*8+y),p[3-v*3//255])
    im=im.resize((480,432),Image.NEAREST); b=io.BytesIO(); im.save(b,'PNG'); im.save(T+'/gen/'+fn+'.png')
    return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
kanto_first=None
for i,l in enumerate(open(PC+'constants/landmark_constants.asm')):
    pass
out['regions']={'johto':render('johto.bin'),'kanto':render('kanto.bin')}
src=open(PC+'constants/landmark_constants.asm').read()
m=re.search(r'DEF KANTO_LANDMARK EQU const_value',src)
pre=src[:m.start()] if m else ''
out['kanto_first']=len(re.findall(r'^\s*const LANDMARK_',pre,re.M))
dims=json.load(open(T+'/gen/cartes_dims.json'))
for k,v in out['maps'].items():
    if k in dims: v['w'],v['h']=dims[k]
out['cartes']='cartes_crystal/'
out['kanto_end']=lmc.index('LANDMARK_FAST_SHIP')
out['charset']={str(k):v for k,v in JPm.items()}
open(T+'/gen/crystal.json','w').write(json.dumps(out,ensure_ascii=False))
print('kanto_first',out['kanto_first'], lmc[out['kanto_first']])
