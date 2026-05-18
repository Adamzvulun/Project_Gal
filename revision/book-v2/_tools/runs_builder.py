"""Build <w:p> elements from light-markdown Hebrew/English prose.

Tokens recognised in the source string:
  **bold**            -> bold run (covers Hebrew or Latin)
  `code`              -> Consolas monospace run with light-grey shade
  plain text          -> split automatically by Hebrew vs. Latin char
                         class so each run has the correct w:rtl value

The paragraph carries <w:bidi w:val="1"/> so Word lays it out RTL.
"""
from __future__ import annotations

import re
from typing import Iterable

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WNS = f"{{{W}}}"


def _is_hebrew_char(c: str) -> bool:
    if not c:
        return False
    o = ord(c)
    return 0x0590 <= o <= 0x05FF or 0xFB1D <= o <= 0xFB4F


def _split_by_rtl(text: str) -> list[tuple[bool, str]]:
    """Split text into (is_hebrew, segment) chunks.

    Whitespace and punctuation attach to whichever neighbour they
    visually belong to: we look at the surrounding characters and
    inherit. Default: attach to the previous segment, otherwise to
    the next.
    """
    if not text:
        return []
    # First pass: classify each char as H (hebrew), L (latin), or N (neutral).
    def cls(c: str) -> str:
        if _is_hebrew_char(c):
            return "H"
        if c.isalnum() or c in "_/.-=:":
            return "L"
        return "N"
    chars = [(c, cls(c)) for c in text]
    # Resolve neutrals: prefer previous if available, else next.
    resolved: list[str] = []
    for i, (c, k) in enumerate(chars):
        if k != "N":
            resolved.append(k)
            continue
        prev = next((resolved[j] for j in range(len(resolved) - 1, -1, -1)
                     if resolved[j] in ("H", "L")), None)
        nxt = next((chars[j][1] for j in range(i + 1, len(chars))
                    if chars[j][1] in ("H", "L")), None)
        resolved.append(prev or nxt or "L")
    # Group adjacent same-class chars.
    out: list[tuple[bool, str]] = []
    cur_cls = resolved[0]
    buf = [chars[0][0]]
    for i in range(1, len(chars)):
        if resolved[i] == cur_cls:
            buf.append(chars[i][0])
        else:
            out.append((cur_cls == "H", "".join(buf)))
            cur_cls = resolved[i]
            buf = [chars[i][0]]
    out.append((cur_cls == "H", "".join(buf)))
    return out


_TOKEN_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


def _tokenize(src: str) -> list[tuple[str, str]]:
    """Return list of (kind, text). kind in {plain, bold, code}."""
    out: list[tuple[str, str]] = []
    pos = 0
    for m in _TOKEN_RE.finditer(src):
        if m.start() > pos:
            out.append(("plain", src[pos:m.start()]))
        tok = m.group(0)
        if tok.startswith("**"):
            out.append(("bold", tok[2:-2]))
        else:
            out.append(("code", tok[1:-1]))
        pos = m.end()
    if pos < len(src):
        out.append(("plain", src[pos:]))
    return out


def _make_run(text: str, is_hebrew: bool,
              bold: bool = False, code: bool = False) -> etree._Element:
    r = etree.Element(f"{WNS}r")
    rPr = etree.SubElement(r, f"{WNS}rPr")
    if code:
        rFonts = etree.SubElement(rPr, f"{WNS}rFonts")
        rFonts.set(f"{WNS}ascii", "Consolas")
        rFonts.set(f"{WNS}cs", "Consolas")
        rFonts.set(f"{WNS}eastAsia", "Consolas")
        rFonts.set(f"{WNS}hAnsi", "Consolas")
        sz = etree.SubElement(rPr, f"{WNS}sz")
        sz.set(f"{WNS}val", "20")
        szCs = etree.SubElement(rPr, f"{WNS}szCs")
        szCs.set(f"{WNS}val", "20")
        shd = etree.SubElement(rPr, f"{WNS}shd")
        shd.set(f"{WNS}fill", "eaeaea")
        shd.set(f"{WNS}val", "clear")
    if bold:
        b = etree.SubElement(rPr, f"{WNS}b")
        b.set(f"{WNS}val", "1")
        bCs = etree.SubElement(rPr, f"{WNS}bCs")
        bCs.set(f"{WNS}val", "1")
    rtl = etree.SubElement(rPr, f"{WNS}rtl")
    rtl.set(f"{WNS}val", "1" if (is_hebrew and not code) else "0")
    t = etree.SubElement(r, f"{WNS}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return r


def build_paragraph(src: str) -> etree._Element:
    """Build a fresh <w:p> bidi paragraph from light-markdown source."""
    p = etree.Element(f"{WNS}p")
    pPr = etree.SubElement(p, f"{WNS}pPr")
    bidi = etree.SubElement(pPr, f"{WNS}bidi")
    bidi.set(f"{WNS}val", "1")
    etree.SubElement(pPr, f"{WNS}rPr")

    for kind, text in _tokenize(src):
        if kind == "code":
            # Code segments stay one run regardless of script.
            p.append(_make_run(text, is_hebrew=False, code=True))
            continue
        segs = _split_by_rtl(text)
        for is_h, seg in segs:
            if not seg:
                continue
            p.append(_make_run(seg, is_hebrew=is_h, bold=(kind == "bold")))
    return p


def build_heading(text: str, level: int = 4) -> etree._Element:
    """Build a heading paragraph (Heading{level}) with bidi and Arial bold.

    Matches the styling pattern used by existing headings in the doc
    (see source idx 102 for H4).
    """
    p = etree.Element(f"{WNS}p")
    pPr = etree.SubElement(p, f"{WNS}pPr")

    pStyle = etree.SubElement(pPr, f"{WNS}pStyle")
    pStyle.set(f"{WNS}val", f"Heading{level}")

    bidi = etree.SubElement(pPr, f"{WNS}bidi")
    bidi.set(f"{WNS}val", "1")

    # Default heading run-properties (Arial bold, color 000000).
    rPr_default = etree.SubElement(pPr, f"{WNS}rPr")
    rFonts = etree.SubElement(rPr_default, f"{WNS}rFonts")
    for attr in ("ascii", "cs", "eastAsia", "hAnsi"):
        rFonts.set(f"{WNS}{attr}", "Arial")
    b = etree.SubElement(rPr_default, f"{WNS}b")
    b.set(f"{WNS}val", "1")
    bCs = etree.SubElement(rPr_default, f"{WNS}bCs")
    bCs.set(f"{WNS}val", "1")

    # Now emit runs for the actual heading text (RTL-aware).
    for is_h, seg in _split_by_rtl(text):
        if not seg:
            continue
        r = etree.SubElement(p, f"{WNS}r")
        rPr = etree.SubElement(r, f"{WNS}rPr")
        rFonts_r = etree.SubElement(rPr, f"{WNS}rFonts")
        for attr in ("ascii", "cs", "eastAsia", "hAnsi"):
            rFonts_r.set(f"{WNS}{attr}", "Arial")
        b_r = etree.SubElement(rPr, f"{WNS}b")
        b_r.set(f"{WNS}val", "1")
        bCs_r = etree.SubElement(rPr, f"{WNS}bCs")
        bCs_r.set(f"{WNS}val", "1")
        rtl = etree.SubElement(rPr, f"{WNS}rtl")
        rtl.set(f"{WNS}val", "1" if is_h else "0")
        t = etree.SubElement(r, f"{WNS}t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = seg
    return p


def replace_paragraph_text(p: etree._Element, src: str) -> None:
    """Replace all <w:r> children of p with runs rendered from src.

    Preserves <w:pPr> and any non-run children.
    """
    to_remove = [child for child in p if child.tag == f"{WNS}r"]
    for child in to_remove:
        p.remove(child)
    new = build_paragraph(src)
    for r in list(new):
        if r.tag == f"{WNS}r":
            p.append(r)
