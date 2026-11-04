import copy, re
from lxml import etree
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
M='{http://schemas.openxmlformats.org/officeDocument/2006/math}'
LOG=[]

def _wrpr(sz=None, bold=False, nor=False):
    rpr=etree.Element(W+'rPr')
    f=etree.SubElement(rpr,W+'rFonts')
    font='Times New Roman' if nor else 'Cambria Math'
    for a in ('ascii','hAnsi','cs'): f.set(W+a, font)
    if bold: etree.SubElement(rpr,W+'b')
    if sz:
        etree.SubElement(rpr,W+'sz').set(W+'val',sz); etree.SubElement(rpr,W+'szCs').set(W+'val',sz)
    return rpr

class Ctx:
    def __init__(self, sz=None, bold=False): self.sz=sz; self.bold=bold

def r(text, sty=None, ctx=None):
    """sty: None = math italic, 'p' upright, 'b'/'bi' bold, 'nor' ordinary text"""
    ctx=ctx or Ctx()
    el=etree.Element(M+'r')
    if ctx.bold and sty in (None,'p'): sty={None:'bi','p':'b'}[sty]
    if sty:
        mr=etree.SubElement(el,M+'rPr')
        if sty=='nor':
            etree.SubElement(mr,M+'nor')
        else:
            etree.SubElement(mr,M+'sty').set(M+'val',sty)
    el.append(_wrpr(ctx.sz, ctx.bold and sty in ('b','bi','nor'), sty=='nor'))
    t=etree.SubElement(el,M+'t'); t.text=text
    if text!=text.strip(): t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    return el

def _box(tag, items):
    e=etree.Element(M+tag)
    for i in items: e.append(i)
    return e

def ctrl(parent, ctx):
    c=etree.SubElement(parent, M+'ctrlPr'); c.append(_wrpr(ctx.sz, ctx.bold)); return c

def sub(base, s, ctx=None):
    ctx=ctx or Ctx()
    e=etree.Element(M+'sSub'); pr=etree.SubElement(e,M+'sSubPr'); ctrl(pr,ctx)
    e.append(_box('e',base)); e.append(_box('sub',s)); return e

def acc(base, ch='̂', ctx=None):
    ctx=ctx or Ctx()
    e=etree.Element(M+'acc'); pr=etree.SubElement(e,M+'accPr')
    etree.SubElement(pr,M+'chr').set(M+'val',ch); ctrl(pr,ctx)
    e.append(_box('e',base)); return e

def func(name, arg, ctx=None):
    ctx=ctx or Ctx()
    e=etree.Element(M+'func'); pr=etree.SubElement(e,M+'funcPr'); ctrl(pr,ctx)
    e.append(_box('fName',name)); e.append(_box('e',arg)); return e

def omath(items):
    return _box('oMath', items)

def _plain_run(c):
    return c.tag==W+'r' and all(k.tag in (W+'rPr',W+'t') for k in c)

def _rtext(c): return ''.join(t.text or '' for t in c.findall(W+'t'))

def _set_text(run, text):
    for t in run.findall(W+'t'): run.remove(t)
    t=etree.SubElement(run,W+'t'); t.text=text
    t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')

def _split(p, before, target, after, label):
    kids=list(p)
    S=''; owner=[]
    for c in kids:
        if _plain_run(c):
            t=_rtext(c)
            for k in range(len(t)): owner.append((c,k))
            S+=t
        else:
            S+='\x00'; owner.append((None,0))
    lead=before.pattern if isinstance(before,re.Pattern) else re.escape(before)
    hits=list(re.finditer('(?=(%s)(%s)%s)'%(lead,re.escape(target),re.escape(after)),S))
    assert len(hits)==1, (label, 'expected exactly one match of', lead+target+after, 'found', len(hits), S[:200])
    a=hits[0].start(2); b=a+len(target)
    assert S[a:b]==target
    first_run,fo=owner[a]; last_run,lo=owner[b-1]
    assert first_run is not None and last_run is not None
    lt=_rtext(last_run)
    if lo+1<len(lt):
        tail=copy.deepcopy(last_run); _set_text(tail, lt[lo+1:]); last_run.addnext(tail)
        _set_text(last_run, lt[:lo+1])
    ft=_rtext(first_run)
    if fo>0:
        head=copy.deepcopy(first_run); _set_text(head, ft[:fo]); first_run.addprevious(head)
        _set_text(first_run, ft[fo:])
    seq=[]; cur=first_run
    while True:
        seq.append(cur)
        if cur is last_run: break
        cur=cur.getnext()
    return seq

def convert(p, before, target, after, build, label):
    """Replace the single occurrence of `target` (located by before+target+after in the
    paragraph's direct plain runs) with the OMML built by build(ctx)."""
    seq=_split(p, before, target, after, label)
    rpr=seq[0].find(W+'rPr')
    sz=None; bold=False
    if rpr is not None:
        s_=rpr.find(W+'sz'); sz=s_.get(W+'val') if s_ is not None else None
        bb=rpr.find(W+'b'); bold=bb is not None and bb.get(W+'val','1') not in ('0','false')
    ctx=Ctx(sz or '20',bold)
    om=omath(build(ctx))
    seq[0].addprevious(om)
    for s_ in seq: p.remove(s_)
    LOG.append((label, target, linear(om)))
    return om

def no_hyphen(p, before, target, after, label):
    """Keep an identifier or URL whole: its runs get noProof, which Word and LibreOffice
    both treat as 'do not hyphenate'."""
    for run in _split(p, before, target, after, label):
        rpr=run.find(W+'rPr')
        if rpr is None:
            rpr=etree.Element(W+'rPr'); run.insert(0,rpr)
        if rpr.find(W+'noProof') is None:
            np_=etree.Element(W+'noProof')
            later=[c for c in rpr if etree.QName(c).localname in ('snapToGrid','vanish','webHidden','color','spacing','w','kern','position','sz','szCs','highlight','u','effect','bdr','shd','fitText','vertAlign','rtl','cs','em','lang','eastAsianLayout','specVanish','oMath') or c.tag.startswith('{http://schemas.microsoft.com/office/word/2010/wordml}')]
            if later: later[0].addprevious(np_)
            else: rpr.append(np_)
        run.set('data-nohyph','1')

def linear(el):
    out=[]
    def go(e):
        tag=etree.QName(e).localname
        if tag=='t': out.append(e.text or '')
        elif tag=='sSub':
            go(e.find(M+'e')); out.append('_'); s=[]; 
            inner=''.join(x.text or '' for x in e.find(M+'sub').iter(M+'t'))
            out.append(inner if len(inner)==1 else '('+inner+')')
        elif tag=='acc':
            go(e.find(M+'e')); out.append(e.find(M+'accPr/'+M+'chr').get(M+'val'))
        elif tag=='func':
            go(e.find(M+'fName')); out.append('⁡'); go(e.find(M+'e'))
        elif tag=='f':
            out.append('('); go(e.find(M+'num')); out.append(')/('); go(e.find(M+'den')); out.append(')')
        else:
            for k in e: go(k)
    go(el)
    return ''.join(out).replace('⁡',' ')
