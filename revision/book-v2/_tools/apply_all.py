"""Master orchestrator for all book-v2 edit passes.

Runs from a pristine copy of `docs/ספר פרוייקט אדם זבולון.docx`. Body
children are snapshotted once at the start; every section's `apply()`
captures element references from that snapshot, so insertions and
deletions in one section do not invalidate the original indices used
by other sections.

Run from repo root:
    python3 revision/book-v2/_tools/apply_all.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import edit_24  # noqa: E402
import edit_25_26  # noqa: E402
import edit_72  # noqa: E402
import edit_62  # noqa: E402
import edit_52  # noqa: E402
import edit_71  # noqa: E402
import edit_113  # noqa: E402
import edit_tone  # noqa: E402
import edit_255  # noqa: E402
import edit_trim  # noqa: E402
from docx_patcher import patch_docx, verify_non_document_identical, W  # noqa: E402

DOCX = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
SOURCE = Path("docs/ספר פרוייקט אדם זבולון.docx")
BACKUP = Path("revision/book-v2/_tools/before_all.docx")


PASSES = [
    ("§3.3/§7.1/§7.2 attribution sentences", edit_tone.apply),
    ("§5.2.1 bencode + info_hash worked example", edit_52.apply),
    ("§6.2.1 handshake bytes + §6.2.2 framing", edit_62.apply),
    ("§7.1 rarest-first depth + thundering-herd pain", edit_71.apply),
    ("§7.2 tit-for-tat — sliding window / snubbing / seeding", edit_72.apply),
    ("§11.3 asyncio+Flask hazard disclosure", edit_113.apply),
    ("§24 empirical + E2E", edit_24.apply),
    ("§25/§26 auto-resume update", edit_25_26.apply),
    ("§25.5 honest limitations", edit_255.apply),
    ("§4h trim inflated claims", edit_trim.apply),
]


def edit(root, body, W):  # noqa: ARG001
    """Combined edit: snapshot once, run every pass against that snapshot."""
    snapshot = list(body)
    for name, apply_fn in PASSES:
        print(f"  · applying {name}")
        apply_fn(body, snapshot, W)


def main() -> int:
    if not SOURCE.exists():
        print(f"missing source: {SOURCE}", file=sys.stderr)
        return 1
    shutil.copy2(SOURCE, DOCX)
    shutil.copy2(SOURCE, BACKUP)
    patch_docx(BACKUP, DOCX, edit)
    ok, diffs = verify_non_document_identical(BACKUP, DOCX)
    if not ok:
        print(f"FAIL: post-edit non-document.xml diff ({len(diffs)} entries):")
        for d in diffs:
            print(" -", d)
        shutil.copy2(SOURCE, DOCX)
        return 1
    print("OK: all edits applied; non-document.xml parts byte-identical.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
