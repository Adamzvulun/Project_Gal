"""Dump raw XML for specific body-child indices."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from lxml import etree

DOCX = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: dump_xml.py IDX [IDX...]", file=sys.stderr)
        return 2
    wanted = set(int(a) for a in sys.argv[1:])
    with zipfile.ZipFile(DOCX) as z:
        xml = z.read("word/document.xml")
    root = etree.fromstring(xml)
    body = root.find(f"{{{W}}}body")
    assert body is not None
    for idx, child in enumerate(body):
        if idx in wanted:
            print(f"===== body[{idx}] =====")
            print(etree.tostring(child, pretty_print=True).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
