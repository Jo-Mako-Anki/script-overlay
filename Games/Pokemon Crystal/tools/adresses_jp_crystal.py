# Outil de fabrication des données (pas besoin pour jouer). Dossier de travail : variable SV_TRAVAIL, qui contient
#   pokecrystal/ (désassemblage pret/pokecrystal compilé), jp/<ROM japonaise>.gbc, gen/ (sorties).
import os
T = os.environ.get('SV_TRAVAIL', '.')
import re, collections, json, sys
US=open(T+'/pokecrystal/pokecrystal.gbc','rb').read()
JP=open(T+'/jp/Pocket Monsters - Crystal Version (Japan).gbc','rb').read()
syms=[]
for l in open(T+'/pokecrystal/pokecrystal.sym'):
    m=re.match(r'([0-9a-f]{2}):([0-9a-f]{4}) (\S+)',l)
    if m: syms.append((int(m[1],16),int(m[2],16),m[3]))
I16={0x01,0x11,0x21,0x31,0x08,0xC2,0xC3,0xC4,0xCA,0xCC,0xCD,0xD2,0xD4,0xDA,0xDC,0xEA,0xFA}
I8={0x06,0x0E,0x16,0x1E,0x26,0x2E,0x36,0x3E,0x18,0x20,0x28,0x30,0x38,0xC6,0xCE,0xD6,0xDE,0xE6,0xEE,0xF6,0xFE,0xE0,0xF0,0xE8,0xF8,0xCB}
def off(b,a): return a if a<0x4000 else b*0x4000+a-0x4000
# ROM labels sorted
rl=sorted({off(b,a) for b,a,n in syms if a<0x8000 and not n.startswith('.')})
insts=[]  # (offset, len, opcode)
for i,st in enumerate(rl[:-1]):
    en=min(rl[i+1], st+0x400); p=st
    while p<en:
        op=US[p]; L=3 if op in I16 else 2 if op in I8 else 1
        insts.append((p,L)); p+=L
# index refs
refs=collections.defaultdict(list)
for k,(p,L) in enumerate(insts):
    if L==3:
        v=US[p+1]|US[p+2]<<8
        if 0xC000<=v<0xE000: refs[v].append(k)
def pattern(k, W=6):
    lo=max(0,k-W); hi=min(len(insts),k+W+1)
    # stay contiguous
    parts=[]; start=insts[lo][0]
    for j in range(lo,hi):
        p,L=insts[j]
        if j>lo and p!=insts[j-1][0]+insts[j-1][1]: return None
        if L==3 and US[p] not in (0x18,):
            parts.append(re.escape(US[p:p+1]) + (b'(..)' if j==k else b'..'))
        else: parts.append(re.escape(US[p:p+L]))
    return b''.join(parts)
res={}
for v,ks in refs.items():
    votes=collections.Counter()
    for k in ks[:40]:
        pat=pattern(k)
        if not pat: continue
        ms=list(re.finditer(pat,JP,re.DOTALL))
        if len(ms)==1:
            jv=ms[0].group(1); votes[jv[0]|jv[1]<<8]+=1
    if votes: res[v]=votes.most_common(3)
json.dump({hex(k):[(hex(a),c) for a,c in v] for k,v in sorted(res.items())},open(T+'/sig/res.json','w'),indent=0)
print(len(refs),len(res))
