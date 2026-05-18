"""Direct zip+lxml patcher for the working .docx.

Guarantees:
  * Every zip entry EXCEPT word/document.xml is copied byte-for-byte
    from the source. Images, fonts, relationships, styles, headers,
    footers, settings, etc. are untouched.
  * word/document.xml is parsed once, mutated through an `edit_fn`,
    and re-serialized using lxml (preserving namespace map).

`edit_fn(root, body, W)` receives the parsed document root, the body
element, and the wordprocessing namespace string. It must mutate the
tree in place and return None.

The patcher refuses to write if `edit_fn` raises, leaving the working
file untouched.
"""
from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path
from typing import Callable

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DOC_PART = "word/document.xml"


def patch_docx(
    src: Path,
    dst: Path,
    edit_fn: Callable[[etree._Element, etree._Element, str], None],
) -> None:
    """Apply edit_fn to src's document.xml and write dst."""
    with zipfile.ZipFile(src, "r") as zin:
        doc_xml = zin.read(DOC_PART)
        all_entries = list(zin.infolist())

    # Parse, edit, serialize.
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(doc_xml, parser=parser)
    body = root.find(f"{{{W}}}body")
    if body is None:
        raise RuntimeError("no <w:body> in document.xml")
    edit_fn(root, body, W)
    patched = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    # Write new zip preserving entry order, compression, attributes.
    tmp_path = dst.with_suffix(dst.suffix + ".tmp")
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(
        tmp_path, "w"
    ) as zout:
        for info in all_entries:
            if info.filename == DOC_PART:
                # Build a fresh ZipInfo carrying source attrs but new size.
                new_info = zipfile.ZipInfo(
                    filename=info.filename,
                    date_time=info.date_time,
                )
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                new_info.create_system = info.create_system
                zout.writestr(new_info, patched)
            else:
                # Raw byte copy.
                data = zin.read(info.filename)
                new_info = zipfile.ZipInfo(
                    filename=info.filename,
                    date_time=info.date_time,
                )
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                new_info.create_system = info.create_system
                zout.writestr(new_info, data)

    shutil.move(str(tmp_path), str(dst))


def noop(root: etree._Element, body: etree._Element, W: str) -> None:
    return None


def verify_non_document_identical(src: Path, dst: Path) -> tuple[bool, list[str]]:
    """Confirm every part except word/document.xml is byte-identical."""
    diffs: list[str] = []
    with zipfile.ZipFile(src) as za, zipfile.ZipFile(dst) as zb:
        a = sorted(za.namelist())
        b = sorted(zb.namelist())
        if a != b:
            return False, [f"entry set differs: only_in_src={set(a) - set(b)} only_in_dst={set(b) - set(a)}"]
        for name in a:
            if name == DOC_PART:
                continue
            ba = za.read(name)
            bb = zb.read(name)
            if ba != bb:
                diffs.append(f"{name} differs (src_len={len(ba)} dst_len={len(bb)})")
    return (len(diffs) == 0), diffs


if __name__ == "__main__":
    # Smoke test: no-op patch should leave everything except document.xml
    # byte-identical. document.xml may differ slightly due to lxml
    # reserialization (whitespace, namespace prefix ordering); that's
    # acceptable as long as Word can still open and render it.
    SRC = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
    DST = Path("revision/book-v2/_tools/noop_smoke.docx")
    patch_docx(SRC, DST, noop)
    ok, diffs = verify_non_document_identical(SRC, DST)
    if ok:
        print("OK: no-op patch preserved every non-document.xml part byte-identical")
    else:
        print(f"FAIL: {len(diffs)} differences found:")
        for d in diffs:
            print(" -", d)
    DST.unlink(missing_ok=True)
