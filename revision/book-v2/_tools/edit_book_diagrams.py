"""Fix ASCII-art / diagram paragraphs that were rendered scrambled.

Six Consolas-formatted paragraphs in the book area contain box-drawing
or arrow-style ASCII art (sequence diagram, screen hierarchy, module
dependency tree, directory trees, event log mockup). Their `<w:pPr>`
sets `<w:jc w:val="left"/>` but does NOT set `<w:bidi>`, so they
inherit the document's RTL default. That makes the Unicode Bidi
Algorithm flip neutral characters (`[`, `]`, arrows, pipes) inside an
otherwise-Latin string, scrambling the diagram.

Fix: insert `<w:bidi w:val="0"/>` into each paragraph's pPr to force
LTR paragraph direction. Run-level `<w:rtl>` markers are left
untouched, so any Hebrew runs inside the same paragraph (e.g. column
descriptions next to a directory-tree entry) continue to render
right-to-left within the now-LTR paragraph.

Targets (ORIGINAL source body indices, verified via dump):
    800  — directory tree (`data/├── downloads/...`)
    907  — module dependency tree (`api_server ──calls──► ...`)
    912  — project directory tree (`תיקיית הפרויקט/├── ...`)
    928  — sequence diagram (`Peer → PeerConnection: PIECE...`)
   1037  — screen hierarchy (`[S1] Main Window ...`)
   1141  — event-log mockup (`[14:23:01] Application started...`)
"""
from __future__ import annotations

from lxml import etree


TARGETS = [800, 907, 912, 928, 1037, 1141]


def apply(body, snapshot, W):
    WNS = f"{{{W}}}"
    for idx in TARGETS:
        p = snapshot[idx]
        if p.tag != f"{WNS}p":
            raise RuntimeError(f"snapshot[{idx}] is not <w:p> (got {p.tag})")
        pPr = p.find(f"{WNS}pPr")
        if pPr is None:
            pPr = etree.SubElement(p, f"{WNS}pPr")
            p.insert(0, pPr)
        existing = pPr.find(f"{WNS}bidi")
        if existing is not None:
            existing.set(f"{WNS}val", "0")
        else:
            bidi = etree.Element(f"{WNS}bidi")
            bidi.set(f"{WNS}val", "0")
            # Insert near the top of pPr — the schema doesn't strictly
            # require ordering, but consistency helps Word's serializer.
            pPr.insert(0, bidi)
