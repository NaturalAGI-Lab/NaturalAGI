"""Usage: fix.py pages_export.docx out.docx [--log]

Post-processes the Pages->Word export: layout fixes, figure/table placement and
plain-text math -> OMML. Every paragraph is located by a text or structural anchor
in the original paragraph list; a missing or ambiguous anchor stops the run."""
import sys, zipfile, re, copy, os, json
from typing import Callable, NoReturn, Optional
from lxml import etree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'mc':'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic':'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'wpg':'http://schemas.microsoft.com/office/word/2010/wordprocessingGroup',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
W='{%s}'%NS['w']; M='{%s}'%NS['m']
args=[a for a in sys.argv[1:] if not a.startswith('--')]
WRITE_LOG='--log' in sys.argv[1:]
src, dst = args
zin=zipfile.ZipFile(src)
files={n: zin.read(n) for n in zin.namelist()}
root=etree.fromstring(files['word/document.xml'])
body=root.find(W+'body')

PPR_ORDER=['pStyle','keepNext','keepLines','pageBreakBefore','framePr','widowControl','numPr','suppressLineNumbers','pBdr','shd','tabs','suppressAutoHyphens','kinsoku','wordWrap','overflowPunct','topLinePunct','autoSpaceDE','autoSpaceDN','bidi','adjustRightInd','snapToGrid','spacing','ind','contextualSpacing','mirrorIndents','suppressOverlap','jc','textDirection','textAlignment','textboxTightWrap','outlineLvl','divId','cnfStyle','rPr','sectPr','pPrChange']
def ppr(p):
    x=p.find(W+'pPr')
    if x is None:
        x=etree.SubElement(p,W+'pPr'); p.remove(x); p.insert(0,x)
    return x
def setp(p, name, **attrs):
    x=ppr(p); el=x.find(W+name)
    if el is None:
        el=etree.Element(W+name)
        idx=PPR_ORDER.index(name); pos=0
        for i,c in enumerate(x):
            ln=etree.QName(c).localname
            if ln in PPR_ORDER and PPR_ORDER.index(ln)<idx: pos=i+1
        x.insert(pos,el)
    for k,v in attrs.items(): el.set(W+k, v)
    for k in list(el.attrib):
        if etree.QName(k).localname not in attrs and name in ('ind',): del el.attrib[k]
    return el
def text(p):
    return ''.join(t.text or '' for t in p.iter(W+'t'))
def has_draw(p): return p.find('.//'+W+'drawing') is not None or p.find('.//'+W+'pict') is not None
def has_sect(p): return p.find(W+'pPr/'+W+'sectPr') is not None

# ---- anchors: all resolved against the untouched paragraph list
orig=list(body)

def fail(msg: str) -> NoReturn:
    sys.exit('fix.py: anchor failed: '+msg)

def find_p(pattern: str, pred: Optional[Callable]=None) -> etree._Element:
    hits=[p for p in orig if p.tag==W+'p' and re.search(pattern,text(p)) and (pred is None or pred(p))]
    if len(hits)!=1: fail('text /%s/ matches %d paragraphs, expected 1'%(pattern,len(hits)))
    return hits[0]

def near(el: etree._Element, offset: int, what: str) -> etree._Element:
    cur=el
    for _ in range(abs(offset)):
        cur=cur.getnext() if offset>0 else cur.getprevious()
        if cur is None: fail('%s: no element %+d from its anchor'%(what,offset))
    return cur

def expect(el: etree._Element, what: str, *, empty=False, sect=False, draw=False, tbl=False) -> etree._Element:
    if tbl:
        if el.tag!=W+'tbl': fail('%s: expected a table'%what)
        return el
    if el.tag!=W+'p': fail('%s: expected a paragraph'%what)
    if empty and text(el)!='': fail('%s: expected an empty paragraph, found %r'%(what,text(el)[:40]))
    if sect and not has_sect(el): fail('%s: expected a section-break paragraph'%what)
    if draw and not has_draw(el): fail('%s: expected a paragraph with a picture'%what)
    if empty and not sect and not draw and (has_sect(el) or has_draw(el)): fail('%s: spacer must have no section break or drawing'%what)
    return el

def cap(n: int, drawn: bool=False) -> etree._Element:
    return find_p(r'^Fig\. %d\. '%n, (lambda p: has_draw(p)) if drawn else (lambda p: not has_draw(p)))

def math_para(sel: Callable, what: str) -> etree._Element:
    hits=[p for p in orig if p.tag==W+'p' and any(sel(o) for o in p.findall(M+'oMath'))]
    if len(hits)!=1: fail('%s matches %d paragraphs, expected 1'%(what,len(hits)))
    return hits[0]

A={}
A['size']=find_p(r'^MNIST images were upscaled to ')
A['closing']=find_p(r'^Binarization initially keeps')
A['pruning']=find_p(r'^Pruning is needed')
A['gng']=find_p(r'^Nodes are placed on the skeleton pixels')
A['features']=find_p(r'^Each node has a set of geometric features')
A['ged']=find_p(r'^Graph Edit Distance \(GED\)\. GED is computed with NetworkX')
A['where_c']=find_p(r'^where c is the cost of the cheapest edit path')
A['where_n']=find_p(r'^n1 and n2 are the numbers of nodes')
A['where_K']=find_p(r'^where K is the complexity of the concept')
A['where_lambda']=find_p(r'^λ = 0\.10 is the weight of the complexity term')
A['software']=find_p(r'^Software used: ')
A['formation']=find_p(r'^The experiment for concept formation was done on the cached')
A['mismatch']=find_p(r'^structural mismatch: a concept of the true class')
A['override']=find_p(r'^complexity override: a concept of the true class')
A['convergence_text']=find_p(r'^Structures that are drawn with straight strokes')
A['feat_conv']=find_p(r'^Feature-range convergence \(mfeat\)')
A['complexity']=find_p(r'^Complexity override is needed')
A['eq1']=math_para(lambda o: any(t.text=='max' for t in o.iter(M+'t')), 'equation (1) (math containing "max")')
A['eq2']=math_para(lambda o: o.find('.//'+M+'limUpp') is not None, 'equation (2) (math containing a limUpp accent)')
A['table_cap']=find_p(r'^Table 1\. ', lambda p: not has_draw(p))
A['table']=expect(near(A['table_cap'],1,'Table 1'),'Table 1',tbl=True)
A['fig1_cap']=cap(1); A['fig1_pic']=expect(near(A['fig1_cap'],-1,'Fig. 1 picture'),'Fig. 1 picture',empty=True,draw=True)
A['fig1_sect_before']=expect(near(A['fig1_pic'],-1,'Fig. 1 leading section break'),'Fig. 1 leading section break',empty=True,sect=True)
A['fig1_sect_after']=expect(near(A['fig1_cap'],1,'Fig. 1 trailing section break'),'Fig. 1 trailing section break',empty=True,sect=True)
A['fig2_cap']=cap(2); A['fig2_pic']=expect(near(A['fig2_cap'],-1,'Fig. 2 picture'),'Fig. 2 picture',empty=True,draw=True)
A['fig3_group']=cap(3,drawn=True)
A['fig3_after']=find_p(r'^In Figure 3, ')
A['fig5_cap']=cap(5); A['fig5_pic']=expect(near(A['fig5_cap'],-1,'Fig. 5 picture'),'Fig. 5 picture',empty=True,draw=True)
A['fig5_sect']=expect(near(A['fig5_pic'],-1,'Fig. 5 leading section break'),'Fig. 5 leading section break',empty=True,sect=True)
A['fig6_group']=cap(6,drawn=True)
A['fig5_after']=find_p(r'^This method has issues that can also be observed in Figure 6')
A['fig7_cap']=cap(7); A['fig7_pic']=expect(near(A['fig7_cap'],-1,'Fig. 7 picture'),'Fig. 7 picture',empty=True,draw=True)
A['fig7_sect_before']=expect(near(A['fig7_pic'],-1,'Fig. 7 leading section break'),'Fig. 7 leading section break',empty=True,sect=True)
A['fig7_sect_after']=expect(near(A['fig7_cap'],1,'Fig. 7 trailing section break'),'Fig. 7 trailing section break',empty=True,sect=True)
A['fig7_after']=find_p(r'^One of the aims of the study was to assess class concept stability')
conclusions=find_p(r'^5\. Conclusions$')
conc_sect=None
for el in conclusions.itersiblings():
    if el.tag==W+'p' and has_sect(el): conc_sect=el; break
if conc_sect is None: fail('no section-break paragraph after "5. Conclusions"')
spacers=[
    ('spacer after the lambda definition', expect(near(find_p(r'^GED was selected to provide a clear edit path'),-1,'spacer before "GED was selected"'),'spacer before "GED was selected"',empty=True)),
    ('spacer before Table 1', expect(near(A['table_cap'],-1,'spacer before Table 1'),'spacer before Table 1',empty=True)),
    ('spacer after Fig. 2', expect(near(A['fig2_cap'],2,'spacer after Fig. 2 section break'),'spacer after Fig. 2 section break',empty=True)),
    ('spacer before 3.3', expect(near(find_p(r'^3\.3 Misclassification analysis'),-1,'spacer before "3.3"'),'spacer before "3.3"',empty=True)),
    ('spacer after Conclusions', expect(near(conc_sect,-1,'spacer before the Conclusions section break'),'spacer before the Conclusions section break',empty=True)),
]
expect(near(A['fig2_cap'],1,'Fig. 2 trailing section break'),'Fig. 2 trailing section break',empty=True,sect=True)

# ---- 0. math written as text -> OMML; numbered equations tidied
from mathconv import r, sub, acc, func, convert, LOG, no_hyphen
Mn='{http://schemas.openxmlformats.org/officeDocument/2006/math}'
conv=convert
mtopo=lambda c:[sub([r('m',ctx=c)],[r('topo','p',c)],c)]
mfeat=lambda c:[sub([r('m',ctx=c)],[r('feat','p',c)],c)]
# the space and full stop after m_topo were formatted as italic subscript
for run in A['convergence_text'].findall(W+'r'):
    rp=run.find(W+'rPr'); t=''.join(x.text or '' for x in run.findall(W+'t'))
    if rp is not None and t in (' ','.') and rp.find(W+'vertAlign') is not None:
        for tag in ('vertAlign','i','iCs'):
            for e in rp.findall(W+tag): rp.remove(e)
conv(A['size'],'upscaled to ','100 × 100',' pixels',lambda c:[r('100',ctx=c),r('×',ctx=c),r('100',ctx=c)],'2.1 image size')
conv(A['closing'],'applies a ','3 × 3',' morphological',lambda c:[r('3',ctx=c),r('×',ctx=c),r('3',ctx=c)],'2.1 closing kernel')
conv(A['pruning'],'shorter than ','max','(8% of skeleton length',lambda c:[r('max','p',c)],'2.1 spur length: max')
conv(A['gng'],'(','ε = 4.55',')',lambda c:[r('ε',ctx=c),r('=',ctx=c),r('4.55',ctx=c)],'2.1 RDP epsilon')
conv(A['features'],'normalized to ','[0, 1]','. Features',lambda c:[r('[',ctx=c),r('0',ctx=c),r(',',ctx=c),r('1',ctx=c),r(']',ctx=c)],'2.1 feature range')
conv(A['features'],'the point ','(x, y)','; distance',lambda c:[r('(',ctx=c),r('x',ctx=c),r(',',ctx=c),r('y',ctx=c),r(')',ctx=c)],'2.1 point position')
conv(A['ged'],'with ','ε = 0.1','.',lambda c:[r('ε',ctx=c),r('=',ctx=c),r('0.1',ctx=c)],'2.1 weight epsilon')
# existing inline equation: "rangewidth" was ten one-letter runs; one run keeps it a single name
om=A['ged'].find(Mn+'oMath'); runs=om.findall(Mn+'r')
letters=[x for x in runs if (x.find(Mn+'t').text or '') in list('rangewidth')]
word=''.join(x.find(Mn+'t').text for x in letters)
assert word=='rangewidth', word
letters[0].find(Mn+'t').text='rangewidth'
for x in letters[1:]: om.remove(x)
LOG.append(('2.1 feature weight (existing equation)','1/(rangewidth+ε) as 10 one-letter runs','1/(rangewidth+ε), one run'))
# equation (1): max as an upright function name
om=A['eq1'].find(Mn+'oMath')
mxs=[x for x in om.iter(Mn+'r') if x.find(Mn+'t') is not None and x.find(Mn+'t').text=='max']
if len(mxs)!=1: fail('equation (1): %d runs with text "max", expected 1'%len(mxs))
mx=mxs[0]
mrp=mx.find(Mn+'rPr')
if mrp is None:
    mrp=etree.Element(Mn+'rPr'); mx.insert(0,mrp)
etree.SubElement(mrp,Mn+'sty').set(Mn+'val','p')
for wi in mx.findall(W+'rPr/'+W+'i'): wi.getparent().remove(wi)
LOG.append(('equation (1)','s=1-c/(c+max(n_1,n_2)), max italic','s=1-c/(c+max(n_1,n_2)), max upright'))
conv(A['where_c'],'where ','c',' is',lambda c:[r('c',ctx=c)],'2.1 where c')
conv(A['where_n'],'','n1',' and',lambda c:[sub([r('n',ctx=c)],[r('1',ctx=c)],c)],'2.1 n1')
conv(A['where_n'],'and ','n2',' are',lambda c:[sub([r('n',ctx=c)],[r('2',ctx=c)],c)],'2.1 n2')
# equation (2): s-hat as an accent, log2 K as a function
om=A['eq2'].find(Mn+'oMath'); lu=om.find(Mn+'limUpp')
base=lu.find(Mn+'e')
a=acc(list(base)); lu.addprevious(a); om.remove(lu)
ss=[x for x in om.findall(Mn+'sSub')][0]; K=ss.getnext()
f=func([copy.deepcopy(ss)],[copy.deepcopy(K)]); ss.addprevious(f); om.remove(ss); om.remove(K)
LOG.append(('equation (2)','ŝ as limUpp(s, U+0302); log_2 K as separate runs','ŝ as accent; log_2 K as function'))
conv(A['where_K'],'where ','K',' is',lambda c:[r('K',ctx=c)],'2.1 where K')
conv(A['where_lambda'],'','λ = 0.10',' is',lambda c:[r('λ',ctx=c),r('=',ctx=c),r('0.10',ctx=c)],'2.1 lambda')
conv(A['formation'],'pass: ','mtopo',' records',mtopo,'2.2 m_topo (1st)')
conv(A['formation'],'; and ','mfeat',' records',mfeat,'2.2 m_feat')
conv(A['formation'],'of the ','mtopo',' metric',mtopo,'2.2 m_topo (2nd)')
conv(A['mismatch'],'similarity ','s',';',lambda c:[r('s',ctx=c)],'2.2 list: s')
conv(A['override'],'similarity ','s',' but',lambda c:[r('s',ctx=c)],'2.2 list: s')
conv(A['override'],'score ','ŝ',' (2)',lambda c:[acc([r('s',ctx=c)],ctx=c)],'2.2 list: ŝ')
conv(A['convergence_text'],re.compile(r'Table 1\. +'),'mtopo',' indicates',mtopo,'3.1 m_topo')
conv(A['feat_conv'],'(','mfeat',')',mfeat,'3.1 m_feat')
conv(A['fig1_cap'],'mark ','mtopo',' (blue)',mtopo,'Fig. 1 caption m_topo')
conv(A['fig1_cap'],'and ','mfeat',' (orange)',mfeat,'Fig. 1 caption m_feat')
hdr=A['table'].find(W+'tr')
for cp in hdr.iter(W+'p'):
    t=text(cp)
    if t in ('mtopo','mfeat'): conv(cp,'',t,'',mtopo if t=='mtopo' else mfeat,'Table 1 header '+t)
no_hyphen(A['ged'],'(version 3.6) ','optimize_graph_edit_distance',' and','identifier')
no_hyphen(A['software'],'available at ','github.com/NaturalAGI-Lab/NaturalAGI',' [33]','url')
# an unbreakable identifier/URL would stretch the justified line before it
for _p in (A['ged'],A['software']): setp(_p,'jc',val='left')
conv(A['complexity'],'(','λ·log₂K',')',lambda c:[r('λ',ctx=c),r('·',ctx=c),func([sub([r('log','p',c)],[r('2',ctx=c)],c)],[r('K',ctx=c)],c)],'3.3 complexity factor')

def is_heading(p):
    x=p.find(W+'pPr')
    return x is not None and x.find(W+'keepNext') is not None and x.find(W+'jc') is not None \
        and x.find(W+'jc').get(W+'val')=='center' and x.find(W+'spacing') is not None \
        and x.find(W+'spacing').get(W+'before')=='100'

# ---- 1. group (picture + caption text box) -> inline picture paragraph + caption paragraph
def ungroup(p, gid):
    ac=p.find('.//mc:AlternateContent', NS)
    run=ac.getparent()
    choice=ac.find('mc:Choice',NS)
    container=choice.find('.//wp:inline',NS)
    if container is None: container=choice.find('.//wp:anchor',NS)
    docpr=container.find('wp:docPr',NS)
    pic=copy.deepcopy(choice.find('.//pic:pic',NS))
    ext=pic.find('pic:spPr/a:xfrm/a:ext',NS)
    cap=copy.deepcopy(choice.find('.//w:txbxContent/w:p',NS))
    inline=etree.fromstring(
        '<wp:inline xmlns:wp="%s" xmlns:a="%s" distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%s" cy="%s"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="%s" name="Figure %s"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"/></a:graphic></wp:inline>'
        % (NS['wp'],NS['a'],ext.get('cx'),ext.get('cy'),docpr.get('id'),gid))
    inline.find('.//a:graphicData',NS).append(pic)
    drawing=etree.Element(W+'drawing'); drawing.append(inline)
    newrun=etree.Element(W+'r'); newrun.append(drawing)
    return run, newrun, cap

# Fig. 3: grouped inline picture -> picture paragraph + caption paragraph, placed after its first citation
p3=A['fig3_group']; run,newrun,cap3=ungroup(p3,3)
run.addprevious(newrun); run.getparent().remove(run)
p3.addnext(cap3)
A['fig3_after'].addnext(p3); p3.addnext(cap3)

# Fig. 6: grouped, anchored in the full-width section of Fig. 5
p118=A['fig6_group']; run,newrun,cap6=ungroup(p118,6)
run.getparent().remove(run)
p6=etree.Element(W+'p'); p6.append(copy.deepcopy(A['fig5_pic'].find(W+'pPr'))); p6.append(newrun)
# Fig. 1 joins Fig. 2 in one full-width block after 3.2
A['fig2_pic'].addprevious(A['fig1_pic']); A['fig2_pic'].addprevious(A['fig1_cap'])
body.remove(A['fig1_sect_before']); body.remove(A['fig1_sect_after'])
# Fig. 5 block (section break, picture, caption, Fig. 6 section break) after the paragraph citing Fig. 6
anchor=A['fig5_after']
for el in (A['fig5_sect'],A['fig5_pic'],A['fig5_cap'],p118):
    anchor.addnext(el); anchor=el
p118.addnext(p6)
p6.addnext(cap6)

# ---- 2. Fig. 7 block (section break, picture, caption, section break) right after its first citation
anchor=A['fig7_after']
for el in (A['fig7_sect_before'],A['fig7_pic'],A['fig7_cap'],A['fig7_sect_after']):
    anchor.addnext(el); anchor=el

# ---- 2c. empty spacer paragraphs
for _, p in spacers: body.remove(p)

# ---- 3. paragraph-level layout
captions=[]
for p in body.iter(W+'p'):
    t=text(p)
    if re.match(r'Fig\. \d+\. ',t) and not has_draw(p): captions.append(p)
for c in captions:
    setp(c,'keepLines',val='1'); setp(c,'suppressAutoHyphens',val='1')
    setp(c,'spacing',after='160'); setp(c,'ind',left='0',right='0',firstLine='0'); setp(c,'jc',val='center')
for p in body.iter(W+'p'):
    if has_draw(p) and p.find('.//w:txbxContent',NS) is None:
        setp(p,'keepNext',val='1'); setp(p,'ind',left='0',right='0',firstLine='0'); setp(p,'jc',val='center')

for p in body.findall(W+'p'):
    t=text(p)
    if is_heading(p): setp(p,'ind',left='0',right='0',firstLine='0')
    if t.startswith('Table 1. '):
        setp(p,'ind',left='0',right='0',firstLine='0'); setp(p,'jc',val='left')
    pr=p.find(W+'pPr')
    if pr is not None and pr.find(W+'suppressAutoHyphens') is not None and pr.find(W+'ind') is not None \
       and pr.find(W+'ind').get(W+'firstLine')=='85':
        # reference entries: hanging indent 0.5 cm, left-aligned (journal rule + template)
        setp(p,'ind',left='284',hanging='284'); setp(p,'jc',val='left')

# front matter lines (UDC, authors, affiliations, titles): no first-line indent
front=[]
for p in body:
    if p.tag==W+'p' and has_sect(p): break
    if p.tag==W+'p': front.append(p)
if not front: fail('no front-matter paragraphs before the first section break')
for p in front:
    t=text(p)
    if not (t.startswith('Анотація') or t.startswith('Ключові') or t.startswith('Abstract') or t.startswith('Keywords')):
        setp(p,'ind',left='0',right='0',firstLine='0')
# English keywords: 9 pt after (journal rule), as for the Ukrainian block
for p in front:
    if text(p).startswith('Keywords'): setp(p,'spacing',after='180')

# back matter
BACK_LABELS=('Author Contributions.','Conflicts of interest.','Funding.','Data Availability.','Use of artificial intelligence.')
started=False
for p in body.findall(W+'p'):
    t=text(p)
    if t.startswith(BACK_LABELS[:2]): started=True
    if not started: continue
    setp(p,'suppressAutoHyphens',val='1')
    if t.startswith(BACK_LABELS):
        setp(p,'ind',left='0',right='0',firstLine='0'); setp(p,'jc',val='left')
    elif t.startswith(('Received','Accepted','ВІДОМОСТІ')) or t=='References':
        setp(p,'ind',left='0',right='0',firstLine='0')
    elif re.match(r'\d+\. ',t):
        pass
    elif t.strip():
        setp(p,'ind',left='0',right='0',firstLine='0')
        if t.startswith(('e-mail:','Scopus ID:')): setp(p,'jc',val='left')
if not started: fail('no back-matter label ("Author Contributions." or "Conflicts of interest.")')

# ---- 4. upright function names in equations
for mr_ in root.iter(M+'r'):
    mt=mr_.find(M+'t')
    if mt is not None and mt.text in ('max','log'):
        rpr=mr_.find(M+'rPr')
        if rpr is None:
            rpr=etree.Element(M+'rPr'); mr_.insert(0,rpr)
        if rpr.find(M+'sty') is None: etree.SubElement(rpr,M+'sty').set(M+'val','p')
        wr=mr_.find(W+'rPr')
        if wr is not None:
            for i in wr.findall(W+'i'): wr.remove(i)

# ---- 5. run language: Pages tagged words with fr/pt/it/da/...; hyphenation follows the run language
cyr=re.compile('[Ѐ-ӿ]')
for r in root.iter(W+'r'):
    t=''.join(x.text or '' for x in r.findall(W+'t'))
    if not t: continue
    rpr=r.find(W+'rPr')
    if rpr is None:
        rpr=etree.Element(W+'rPr'); r.insert(0,rpr)
    lang=rpr.find(W+'lang')
    want='uk-UA' if cyr.search(t) else 'en-US'
    if r.get('data-nohyph'):
        del r.attrib['data-nohyph']; want='zxx'
    if lang is None:
        if want=='en-US': continue
        lang=etree.SubElement(rpr,W+'lang')
        # keep schema order: lang goes before eastAsianLayout/specVanish/oMath and w14 extensions
        after=[c for c in rpr if etree.QName(c).localname in ('eastAsianLayout','specVanish','oMath') or c.tag.startswith('{http://schemas.microsoft.com/office/word/2010/wordml}')]
        if after: after[0].addprevious(lang)
    lang.set(W+'val',want)

# ---- 6. sections: exact A4, no header/footer references
for s in root.iter(W+'sectPr'):
    pg=s.find(W+'pgSz'); pg.set(W+'w','11906'); pg.set(W+'h','16838')
    for ref in s.findall(W+'headerReference')+s.findall(W+'footerReference'): s.remove(ref)

files['word/document.xml']=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)

# drop the empty header/footer parts
rels=files['word/_rels/document.xml.rels'].decode()
rels=re.sub(r'<Relationship [^>]*Target="(header1|footer1)\.xml"[^>]*/>','',rels)
files['word/_rels/document.xml.rels']=rels.encode()
ct=files['[Content_Types].xml'].decode()
ct=re.sub(r'<Override PartName="/word/(header1|footer1)\.xml"[^>]*/>','',ct)
files['[Content_Types].xml']=ct.encode()
files.pop('word/header1.xml'); files.pop('word/footer1.xml')

# ---- 7. settings: hyphenation zone as in the template
st=files['word/settings.xml'].decode()
if 'hyphenationZone' not in st:
    st=st.replace('<w:autoHyphenation w:val="1"/>','<w:autoHyphenation w:val="1"/><w:hyphenationZone w:val="227"/><w:doNotHyphenateCaps w:val="1"/>')
files['word/settings.xml']=st.encode()

with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as z:
    for n in zin.namelist():
        if n in files: z.writestr(n, files[n])
print('ok', dst)
if WRITE_LOG:
    json.dump(LOG, open(dst+'.mathlog.json','w'), ensure_ascii=False, indent=1)
