# Outil de fabrication des données (pas besoin pour jouer). Dossier de travail : variable SV_TRAVAIL, qui contient
#   pokecrystal/ (désassemblage pret/pokecrystal compilé), jp/<ROM japonaise>.gbc, gen/ (sorties).
import os
T = os.environ.get('SV_TRAVAIL', '.')
# Dessine chaque carte de Pokémon Crystal (palette de jour) à partir de pokecrystal : donnees/cartes_crystal/<groupe>.<numéro>.png
import re, os, sys, json
from PIL import Image
PC=T+'/pokecrystal/'
OUT=sys.argv[1] if len(sys.argv)>1 else T+'/gen/cartes_crystal'
os.makedirs(OUT,exist_ok=True)
def camel_to_const(s): return re.sub(r'(?<!^)(?=[A-Z])','_',s).upper()
# palettes
pal=[]
for l in open(PC+'gfx/tilesets/bg_tiles.pal'):
    nums=[int(x) for x in re.findall(r'\d+',l.split(';')[0])]
    if l.strip().startswith('RGB'): pal.append([tuple(v*255//31 for v in nums[i:i+3]) for i in range(0,len(nums),3)])
env_cols={}; cur=None
for l in open(PC+'data/maps/environment_colors.asm'):
    m=re.match(r'\.(\w+)Colors:',l)
    if m: cur=m[1]; env_cols[cur]=[]; continue
    if cur and l.strip().startswith('db'): env_cols[cur].append([int(x,16) for x in re.findall(r'\$([0-9a-f]{2})',l)])
ENV={'TOWN':'Outdoor','ROUTE':'Outdoor','INDOOR':'Indoor','CAVE':'Dungeon','ENVIRONMENT_5':'Env5','GATE':'Indoor','DUNGEON':'Dungeon'}
PALN=['GRAY','RED','GREEN','WATER','YELLOW','BROWN','ROOF','TEXT']
roofpals=[]
for l in open(PC+'gfx/tilesets/roofs.pal'):
    nums=[int(x) for x in re.findall(r'\d+',l.split(';')[0])]
    if l.strip().startswith('RGB') and 'morn/day' in l: roofpals.append([tuple(v*255//31 for v in nums[i:i+3]) for i in range(0,6,3)])
roofs=[]; groofs=[]
for l in open(PC+'data/maps/roofs.asm'):
    m=re.match(r'\s*const (ROOF_\w+)',l)
    if m: roofs.append(m[1])
    m=re.match(r'\s*db (-1|ROOF_\w+)',l)
    if m: groofs.append(-1 if m[1]=='-1' else roofs.index(m[1]))
roofgfx=['new_bark','violet','azalea','olivine','goldenrod']
# tilesets : constante -> fichiers
tsnames=[]
for l in open(PC+'data/tilesets.asm'):
    m=re.match(r'\s*tileset Tileset(\w+)',l)
    if m: tsnames.append(m[1])
def labels_to_files(path, kind):
    res={}; pend=[]
    for l in open(PC+path):
        m=re.match(r'(Tileset\w+?)'+kind+r'::?',l)
        if m: pend.append(m[1]); continue
        m=re.match(r'\s*(INCBIN|INCLUDE) "([^"]+)"',l)
        if m and pend:
            for p in pend: res[p]=m[2]
            pend=[]
    return res
gfxf=labels_to_files('gfx/tilesets.asm','GFX'); metaf=labels_to_files('gfx/tilesets.asm','Meta'); palf=labels_to_files('gfx/tileset_palette_maps.asm','PalMap')
cache={}
def tileset(i):
    if i in cache: return cache[i]
    n='Tileset'+tsnames[i]
    png=PC+gfxf[n].replace('.2bpp.lz','.png').replace('.2bpp','.png')
    im=Image.open(png).convert('L')
    tiles=[im.crop((x*8,y*8,x*8+8,y*8+8)) for y in range(im.height//8) for x in range(16)]
    meta=open(PC+metaf[n],'rb').read()
    pm=[]
    for l in open(PC+palf[n]):
        m=re.match(r'\s*tilepal \d, (.*)',l)
        if m: pm+= [x.strip() for x in m[1].split(',')]
    cache[i]=(tiles,meta,pm); return cache[i]
# blocs
blk={}; pend=[]
for l in open(PC+'data/maps/blocks.asm'):
    m=re.match(r'(\w+)_Blocks:',l)
    if m: pend.append(m[1]); continue
    m=re.match(r'\s*INCBIN "([^"]+)"',l)
    if m and pend:
        for p in pend: blk[p]=m[1]
        pend=[]
dims={}
for l in open(PC+'constants/map_constants.asm'):
    m=re.match(r'\s*map_const (\w+),\s*(\d+),\s*(\d+)',l)
    if m: dims[m[1]]=(int(m[2]),int(m[3]))
attr={}
for l in open(PC+'data/maps/attributes.asm'):
    m=re.match(r'\s*map_attributes (\w+), (\w+),',l)
    if m: attr[m[1]]=m[2]
tconst=[('TILESET_'+t).upper().replace('_','') for t in tsnames]
info={}; g=0
for l in open(PC+'data/maps/maps.asm'):
    if re.match(r'^MapGroup_\w+:',l): g+=1; n=0
    m=re.match(r'\s*map (\w+), (\w+), (\w+),',l)
    if not (m and g): continue
    n+=1; name,ts,env=m[1],m[2],m[3]
    try:
        w,h=dims[attr[name]]; data=open(PC+blk[name],'rb').read()
        tiles,meta,pm=tileset(tconst.index(ts.replace('_','')))
        cols=env_cols[ENV[env]][1]
        P={PALN[k]:pal[cols[k]] for k in range(8)}
        tl=list(tiles)
        if ts in ('TILESET_JOHTO','TILESET_JOHTO_MODERN','TILESET_BATTLE_TOWER_OUTSIDE') and g<len(groofs) and groofs[g]>=0:
            r=Image.open(PC+'gfx/tilesets/roofs/'+roofgfx[groofs[g]]+'.png').convert('L')
            rt=[r.crop((x*8,y*8,x*8+8,y*8+8)) for y in range(r.height//8) for x in range(r.width//8)]
            for k in range(9): tl[0x0a+k]=rt[k]
        if g<len(roofpals) and ENV[env]=='Outdoor':
            rp=P['ROOF']; P['ROOF']=[rp[0],roofpals[g][0],roofpals[g][1],rp[3]]
        im=Image.new('RGB',(w*32,h*32))
        rendered={}
        for by in range(h):
            for bx in range(w):
                b=data[by*w+bx]
                for ty in range(4):
                    for tx in range(4):
                        t=meta[b*16+ty*4+tx]
                        if t<0x60: idx=t; pidx=t
                        elif t>=0x80: idx=0x60+t-0x80; pidx=t-0x80+0x60
                        else: continue
                        key=(t,)
                        if key not in rendered:
                            if idx>=len(tl): rendered[key]=None
                            else:
                                pn=pm[pidx] if pidx<len(pm) else 'GRAY'
                                c=P.get(pn,P['GRAY'])
                                src=tl[idx]; ti=Image.new('RGB',(8,8))
                                ti.putdata([c[3-v*3//255] for v in src.getdata()]); rendered[key]=ti
                        if rendered[key]: im.paste(rendered[key],(bx*32+tx*8,by*32+ty*8))
        im.save(f'{OUT}/{g}.{n}.png',optimize=True)
        info[f'{g}.{n}']=[w,h]
    except Exception as e:
        print('ERR',g,n,name,repr(e))
json.dump(info,open(OUT+'/../cartes_dims.json','w'))
print(len(info))
