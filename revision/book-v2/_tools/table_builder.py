"""Build a <w:tbl> table compatible with the document's existing tables.

The book already uses `Table29` style (light blue header row, thin grey
inner borders, RTL/bidi layout). This builder emits that structure.

Public API:
    build_table(rows: list[list[str]], col_widths: list[int],
                header: bool = True) -> <w:tbl>

Each cell string supports the same light-markdown as `runs_builder`:
**bold** and `code`. Hebrew vs Latin runs are auto-split.
"""
from __future__ import annotations

from lxml import etree

from runs_builder import build_paragraph

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WNS = f"{{{W}}}"


def _set(elem: etree._Element, name: str, value: str) -> None:
    elem.set(f"{WNS}{name}", value)


def _build_cell(text: str, *, is_header: bool, header_fill: str = "dce6f1") -> etree._Element:
    tc = etree.Element(f"{WNS}tc")
    tcPr = etree.SubElement(tc, f"{WNS}tcPr")
    if is_header:
        shd = etree.SubElement(tcPr, f"{WNS}shd")
        _set(shd, "fill", header_fill)
        _set(shd, "val", "clear")

    p = build_paragraph(text)
    # Tables look better with centered-by-default cells.
    pPr = p.find(f"{WNS}pPr")
    assert pPr is not None
    jc = etree.SubElement(pPr, f"{WNS}jc")
    _set(jc, "val", "left")
    # If header, bold all runs in this cell (covers the case where the
    # source string didn't wrap header text in **...**).
    if is_header:
        for r in p.iter(f"{WNS}r"):
            rPr = r.find(f"{WNS}rPr")
            if rPr is None:
                rPr = etree.SubElement(r, f"{WNS}rPr")
            if rPr.find(f"{WNS}b") is None:
                b = etree.SubElement(rPr, f"{WNS}b")
                _set(b, "val", "1")
                bCs = etree.SubElement(rPr, f"{WNS}bCs")
                _set(bCs, "val", "1")
    tc.append(p)
    return tc


def build_table(
    rows: list[list[str]],
    col_widths: list[int],
    header: bool = True,
) -> etree._Element:
    if not rows:
        raise ValueError("rows is empty")
    if any(len(r) != len(col_widths) for r in rows):
        raise ValueError("row width mismatches col_widths")

    tbl = etree.Element(f"{WNS}tbl")
    tblPr = etree.SubElement(tbl, f"{WNS}tblPr")

    style = etree.SubElement(tblPr, f"{WNS}tblStyle")
    _set(style, "val", "Table29")

    bidiVisual = etree.SubElement(tblPr, f"{WNS}bidiVisual")
    _set(bidiVisual, "val", "1")

    total_w = sum(col_widths)
    tblW = etree.SubElement(tblPr, f"{WNS}tblW")
    _set(tblW, "w", str(int(total_w)))
    _set(tblW, "type", "dxa")

    jc = etree.SubElement(tblPr, f"{WNS}jc")
    _set(jc, "val", "left")

    borders = etree.SubElement(tblPr, f"{WNS}tblBorders")
    for tag in ("top", "left", "bottom", "right"):
        b = etree.SubElement(borders, f"{WNS}{tag}")
        _set(b, "color", "333333")
        _set(b, "space", "0")
        _set(b, "sz", "6")
        _set(b, "val", "single")
    for tag in ("insideH", "insideV"):
        b = etree.SubElement(borders, f"{WNS}{tag}")
        _set(b, "color", "999999")
        _set(b, "space", "0")
        _set(b, "sz", "4")
        _set(b, "val", "single")

    layout = etree.SubElement(tblPr, f"{WNS}tblLayout")
    _set(layout, "type", "fixed")

    look = etree.SubElement(tblPr, f"{WNS}tblLook")
    _set(look, "val", "0020")

    grid = etree.SubElement(tbl, f"{WNS}tblGrid")
    for cw in col_widths:
        gc = etree.SubElement(grid, f"{WNS}gridCol")
        _set(gc, "w", str(int(cw)))

    for r_idx, row in enumerate(rows):
        tr = etree.SubElement(tbl, f"{WNS}tr")
        trPr = etree.SubElement(tr, f"{WNS}trPr")
        cantSplit = etree.SubElement(trPr, f"{WNS}cantSplit")
        _set(cantSplit, "val", "0")
        if header and r_idx == 0:
            hdr = etree.SubElement(trPr, f"{WNS}tblHeader")
            _set(hdr, "val", "1")
        for cell_text in row:
            tc = _build_cell(cell_text, is_header=(header and r_idx == 0))
            tr.append(tc)
    return tbl
