"""Verify that the project-proposal portion of the document (idx 0–304)
is byte-identical to the pristine source.

Compares the serialised XML of every body child in that range between
the pristine `docs/...docx` and the patched working copy. If any byte
differs, exits non-zero and reports the offending index.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from lxml import etree

SOURCE = Path("docs/ספר פרוייקט אדם זבולון.docx")
WORK = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CUTOFF = 305


def body(path: Path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = etree.fromstring(xml)
    b = root.find(f"{{{W}}}body")
    assert b is not None
    return list(b)


def main() -> int:
    src = body(SOURCE)
    dst = body(WORK)

    src_proposal = src[:CUTOFF]
    dst_proposal = dst[:CUTOFF]

    if len(src_proposal) != len(dst_proposal):
        print(f"FAIL: proposal-region length differs "
              f"(source={len(src_proposal)}, working={len(dst_proposal)})")
        return 1

    bad: list[int] = []
    for i, (a, b_) in enumerate(zip(src_proposal, dst_proposal)):
        a_bytes = etree.tostring(a, method="c14n")
        b_bytes = etree.tostring(b_, method="c14n")
        if a_bytes != b_bytes:
            bad.append(i)

    if bad:
        print(f"FAIL: {len(bad)} body child(ren) in idx 0..{CUTOFF - 1} "
              "differ from source:")
        for i in bad[:10]:
            print(f"  - idx {i}")
        if len(bad) > 10:
            print(f"  ... and {len(bad) - 10} more")
        return 1

    print(f"OK: proposal area idx 0..{CUTOFF - 1} ({len(src_proposal)} body "
          "children) byte-identical to pristine source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
