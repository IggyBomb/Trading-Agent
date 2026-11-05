"""Pre-populate the Table of Contents in python-docx reports.

python-docx can insert a TOC field but cannot compute it, so Word shows a
placeholder until the field is updated. This script:
  1. writes the Heading 1/2 entries (clickable links to each section) into the
     TOC field result, so the contents are visible immediately;
  2. sets <w:updateFields w:val="true"/> so Word offers to refresh page numbers
     on open.

Usage: python3 fix_docx_toc.py reports/X_long_term_deep_dive_DATE.docx [...]
"""
import copy
import sys

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches


def _fld(kind):
    r = OxmlElement("w:r"); f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), kind); r.append(f)
    return r


def _run(text, bold=False, size=10):
    r = OxmlElement("w:r"); rpr = OxmlElement("w:rPr")
    if bold:
        rpr.append(OxmlElement("w:b"))
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(size * 2)); rpr.append(sz)
    r.append(rpr); t = OxmlElement("w:t"); t.set(qn("xml:space"), "preserve"); t.text = text; r.append(t)
    return r


def fix(path):
    d = docx.Document(path)
    body = d.element.body
    paras = list(d.paragraphs)

    # locate TOC field paragraph
    toc_p = next((p for p in paras if any((it.text or "").strip().startswith("TOC")
                                           for it in p._p.iter(qn("w:instrText")))), None)
    if toc_p is None:
        print(f"{path}: no TOC field found, skipped"); return

    # collect headings after the TOC, add bookmarks
    heads, bid = [], 9000
    after = False
    for p in paras:
        if p._p is toc_p._p:
            after = True; continue
        if not after:
            continue
        st = p.style.name if p.style is not None else ""
        if st in ("Heading 1", "Heading 2") and p.text.strip():
            name = f"_TocAuto{bid}"
            bs = OxmlElement("w:bookmarkStart"); bs.set(qn("w:id"), str(bid)); bs.set(qn("w:name"), name)
            be = OxmlElement("w:bookmarkEnd"); be.set(qn("w:id"), str(bid))
            p._p.insert(1 if p._p.pPr is not None else 0, bs); p._p.append(be)
            heads.append((int(st[-1]), p.text.strip(), name)); bid += 1

    # rebuild the TOC: field begin+instr+separate in the first entry, end after the last
    instr = next(it for it in toc_p._p.iter(qn("w:instrText"))).text
    entries = []
    for lvl, text, name in heads:
        p = OxmlElement("w:p"); ppr = OxmlElement("w:pPr")
        sp = OxmlElement("w:spacing"); sp.set(qn("w:after"), "40" if lvl == 2 else "80"); ppr.append(sp)
        ind = OxmlElement("w:ind"); ind.set(qn("w:left"), "0" if lvl == 1 else "360"); ppr.append(ind)
        p.append(ppr)
        h = OxmlElement("w:hyperlink"); h.set(qn("w:anchor"), name); h.set(qn("w:history"), "1")
        h.append(_run(text, bold=(lvl == 1), size=11 if lvl == 1 else 10))
        p.append(h); entries.append(p)
    if not entries:
        print(f"{path}: no headings found"); return

    first = entries[0]
    ir = OxmlElement("w:r"); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; ir.append(it)
    for i, el in enumerate([_fld("begin"), ir, _fld("separate")]):
        first.insert(1 + i, el)
    entries[-1].append(_fld("end"))

    anchor = toc_p._p
    for e in entries:
        anchor.addnext(e); anchor = e
    body.remove(toc_p._p)

    # replace the "right-click" hint
    for p in d.paragraphs:
        if p.text.startswith("(Right-click"):
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            p.runs[0].text = "(Click a section to jump to it. Page numbers: References → Update Table.)"

    # ask Word to refresh fields on open
    st = d.settings.element
    uf = st.find(qn("w:updateFields"))
    if uf is None:
        uf = OxmlElement("w:updateFields"); st.append(uf)
    uf.set(qn("w:val"), "true")

    d.save(path)
    print(f"{path}: TOC populated with {len(heads)} entries")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        fix(f)
