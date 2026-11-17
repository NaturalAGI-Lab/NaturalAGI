import sys, os, subprocess, unicodedata, difflib, collections
EXTRACT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'extract2.py')
def load(docx: str, mode: str) -> list[str]:
    out=subprocess.run([sys.executable,EXTRACT,docx,mode],capture_output=True,text=True,check=True).stdout
    return out.split('\n')[:-1]
def norm(s):
    s=s.encode().decode('unicode_escape') if '\\' in s else s
    s=unicodedata.normalize('NFD', s).replace('₂','2')
    return ''.join(s.split())
base, fin = sys.argv[1], sys.argv[2]
bl, fl = load(base,'lines'), load(fin,'lines')
bc, fc = load(base,'chars'), load(fin,'chars')
print('paragraphs (incl. empty):', len(bl), '->', len(fl))
print('empty paragraphs:', sum(1 for x in bl if not x.strip()), '->', sum(1 for x in fl if not x.strip()))
# 1. strict: identical text paragraphs (exact, incl. spaces), non-empty
B=[x for x in bl if x.strip()]; F=[x for x in fl if x.strip()]
cb, cf = collections.Counter(B), collections.Counter(F)
only_b = list((cb-cf).elements()); only_f = list((cf-cb).elements())
print('\n== non-empty paragraphs whose exact text differs:', len(only_b), 'baseline vs', len(only_f), 'final')
# pair them by normalized char content
nb={norm(x):x for x in [c for c in bc if c.strip()]}
pairs=[]
for x in only_b:
    i=bl.index(x); y_chars=norm(bc[i])
    match=[j for j,c in enumerate(fc) if norm(c)==y_chars]
    pairs.append((x, fl[match[0]] if match else None))
for x,y in pairs:
    print('  BEFORE:', x[:0] or '', end='')
    # show only the differing spans
    sm=difflib.SequenceMatcher(None,x,y or '',autojunk=False)
    for op,i1,i2,j1,j2 in sm.get_opcodes():
        if op!='equal': print(f'[{x[i1:i2]!r} -> {(y or "")[j1:j2]!r}]', end=' ')
    print()
# 2. character-level: whole document, whitespace-free, NFD, U+2082->2, non-empty paragraphs as multiset
NB=collections.Counter(norm(c) for c in bc if c.strip()); NF=collections.Counter(norm(c) for c in fc if c.strip())
print('\n== normalized paragraph multiset identical:', NB==NF)
print('== total non-whitespace chars (normalized):', sum(len(k)*v for k,v in NB.items()), '->', sum(len(k)*v for k,v in NF.items()))
# 3. order: which paragraphs moved
sb=[norm(c) for c in bc if c.strip()]; sf=[norm(c) for c in fc if c.strip()]
sm=difflib.SequenceMatcher(None,sb,sf,autojunk=False)
print('\n== order changes (normalized, non-empty paragraphs):')
for op,i1,i2,j1,j2 in sm.get_opcodes():
    if op=='equal': continue
    for k in range(i1,i2): print(f'  removed at base#{k}:', [x for x in bc if x.strip()][k][:90])
    for k in range(j1,j2): print(f'  inserted at final#{k}:', [x for x in fc if x.strip()][k][:90])
sys.exit(0 if NB==NF else 1)
