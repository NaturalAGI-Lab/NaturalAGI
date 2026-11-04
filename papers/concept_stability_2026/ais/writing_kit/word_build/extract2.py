"""Usage: extract2.py docx lines|chars
lines: one line per paragraph (body, table cells, text boxes in order), math as ⟦linear⟧.
chars: same but math as its raw characters (accent chars after base), for character-level checks."""
import sys, os, zipfile
from lxml import etree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathconv import linear
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
M='{http://schemas.openxmlformats.org/officeDocument/2006/math}'
MC='{http://schemas.openxmlformats.org/markup-compatibility/2006}'
mode=sys.argv[2]
def mchars(e):
    out=[]
    def go(n):
        for k in n:
            if k.tag==M+'t': out.append(k.text or '')
            elif k.tag==M+'acc':
                go(k.find(M+'e')); out.append(k.find(M+'accPr/'+M+'chr').get(M+'val'))
            else: go(k)
    go(e)
    return ''.join(out)
def walk(el, out):
    for c in el:
        if c.tag==MC+'Fallback': continue
        if c.tag==W+'p':
            buf=[]; nested=[]
            def tx(n):
                for k in n:
                    if k.tag==MC+'Fallback': continue
                    if k.tag==M+'oMath':
                        buf.append('⟦'+linear(k)+'⟧' if mode=='lines' else mchars(k)); continue
                    if k.tag==W+'t': buf.append(k.text or '')
                    elif k.tag==W+'tab' and k.getparent().tag==W+'r': buf.append('\t')
                    elif k.tag==W+'br': buf.append('\n')
                    elif k.tag==W+'txbxContent': nested.append(k); continue
                    else: tx(k)
            tx(c); out.append(''.join(buf))
            for n in nested: walk(n, out)
        else: walk(c, out)
z=zipfile.ZipFile(sys.argv[1]); root=etree.fromstring(z.read('word/document.xml'))
out=[]; walk(root.find(W+'body'), out)
for l in out: print(repr(l)[1:-1])
