import json, sys, docx
from docx.oxml.ns import qn
M='{http://schemas.openxmlformats.org/officeDocument/2006/math}'
d=docx.Document(sys.argv[1])
body=d.element.body
items=[]; mathcount=0
def ptext(p):
    global mathcount
    out=[]
    for el in p.iter():
        if el.tag==M+'oMath':
            mathcount+=1; out.append(f'⟦M{mathcount}⟧')
        elif el.tag==qn('w:t') and not any(a.tag==M+'oMath' for a in el.iterancestors()):
            out.append(el.text or '')
        elif el.tag==qn('w:tab') and not any(a.tag==M+'oMath' for a in el.iterancestors()):
            out.append('\t')
    return ''.join(out)
started=False
for child in body:
    if child.tag==qn('w:p'):
        t=ptext(child)
        if t.strip()=='1. Introduction': started=True
        if t.strip()=='References': break
        if started and t.strip(): items.append({'id':f'p{len(items)+1}','en':t})
    elif child.tag==qn('w:tbl') and started:
        for ci,tc in enumerate(child.iter(qn('w:tc'))):
            t=''.join(ptext(p) for p in tc.iter(qn('w:p')))
            if t.strip(): items.append({'id':f't{ci}','en':t})
json.dump(items,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
print(len(items),'items', sum(len(i['en']) for i in items),'chars', mathcount,'math')
