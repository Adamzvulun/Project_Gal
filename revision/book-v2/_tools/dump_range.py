"""Dump paragraph text in a body-index range, plus pStyle info."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

DOCX = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def text_of(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.iter(f"{{{W}}}t"))


def style(p: ET.Element) -> str:
    s = p.find(f"{{{W}}}pPr/{{{W}}}pStyle")
    return s.get(f"{{{W}}}val", "") if s is not None else ""


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: dump_range.py START END", file=sys.stderr)
        return 2
    start, end = int(sys.argv[1]), int(sys.argv[2])
    with zipfile.ZipFile(DOCX) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(f"{{{W}}}body")
    assert body is not None
    for idx, child in enumerate(body):
        if idx < start or idx > end:
            continue
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            st = style(child)
            img = "img" if child.find(f".//{{{W}}}drawing") is not None else "   "
            txt = text_of(child).strip()
            print(f"[{idx:>5}] {img} <{st:>14}> {txt}")
        else:
            print(f"[{idx:>5}]     <{tag}>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
