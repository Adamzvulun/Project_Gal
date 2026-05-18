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
import edit_113  # noqa: E402
import edit_255  # noqa: E402
import edit_trim  # noqa: E402
import edit_book_116  # noqa: E402
import edit_book_154  # noqa: E402
import edit_book_attribution  # noqa: E402
import edit_book_diagrams  # noqa: E402
# NOTE: edit_tone, edit_52, edit_62, edit_71, edit_72 are deliberately NOT
# imported here. They targeted proposal-area indices (idx < 305) which the
# user has declared off-limits. Their content was moved into edit_book_116
# (handshake/framing/bencode → book §11.6) and edit_book_154 (rarest-first
# depth + tit-for-tat trio → book §15.4).
from docx_patcher import patch_docx, verify_non_document_identical, W  # noqa: E402

DOCX = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
SOURCE = Path("docs/ספר פרוייקט אדם זבולון.docx")
BACKUP = Path("revision/book-v2/_tools/before_all.docx")


PASSES = [
    ("book §6.2 attribution framing", edit_book_attribution.apply),
    ("book §11.3 asyncio+Flask hazard disclosure", edit_113.apply),
    ("book §11.6 handshake / framing / bencode", edit_book_116.apply),
    ("book §15.4 rarest-first depth + tit-for-tat trio", edit_book_154.apply),
    ("book §24 empirical + E2E", edit_24.apply),
    ("book §25/§26 auto-resume update", edit_25_26.apply),
    ("book §25.5 honest limitations", edit_255.apply),
    ("book §4h trim inflated claims", edit_trim.apply),
    ("book ASCII-art diagram bidi fix", edit_book_diagrams.apply),
]


PROPOSAL_CUTOFF_IDX = 305  # body indices < 305 are the project proposal
                            # (pages 1–23). Off-limits per user instruction.


def _assert_no_proposal_writes(passes_named) -> None:
    """Inspect each pass module for ORIGINAL-source body indices it edits.
    Fail loudly if any pass declares an index inside the proposal range.
    """
    import importlib
    for name, apply_fn in passes_named:
        mod = importlib.import_module(apply_fn.__module__)
        candidates: list[int] = []
        for attr in ("REPLACEMENTS", "INSERT_PARA_AFTER", "INSERT_AFTER",
                     "INSERT_AFTER_IDX", "REMOVE_INDICES", "INSERT_TABLE_AFTER"):
            v = getattr(mod, attr, None)
            if v is None:
                continue
            if isinstance(v, dict):
                candidates.extend(v.keys())
            elif isinstance(v, (list, tuple)):
                candidates.extend(v)
            elif isinstance(v, int):
                candidates.append(v)
        bad = [i for i in candidates if i < PROPOSAL_CUTOFF_IDX]
        if bad:
            raise RuntimeError(
                f"pass {apply_fn.__module__!r} ({name}) targets proposal "
                f"indices (off-limits): {sorted(set(bad))}"
            )


def edit(root, body, W):  # noqa: ARG001
    """Combined edit: snapshot once, run every pass against that snapshot."""
    _assert_no_proposal_writes(PASSES)
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
