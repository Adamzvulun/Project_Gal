"""No-op round-trip check.

Round-trips the working docx through python-docx (load -> save) into a
temp file, then verifies that every entry inside the .zip EXCEPT
word/document.xml is byte-identical to the source. This proves that
later edits which only touch document.xml cannot perturb images,
relationships, fonts, headers, footers, styles, or any other part.

Exit 0 on success; exit 1 on any difference.
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path

import docx  # python-docx

SRC = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def main() -> int:
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        d = docx.Document(str(SRC))
        d.save(str(tmp_path))

        with zipfile.ZipFile(SRC) as za, zipfile.ZipFile(tmp_path) as zb:
            a_names = set(za.namelist())
            b_names = set(zb.namelist())
            if a_names != b_names:
                print("FAIL: zip entry set differs")
                print("  only in source:", a_names - b_names)
                print("  only in saved :", b_names - a_names)
                return 1

            differing: list[str] = []
            image_count_a = sum(1 for n in a_names if n.startswith("word/media/"))
            image_count_b = sum(1 for n in b_names if n.startswith("word/media/"))
            if image_count_a != image_count_b:
                print(f"FAIL: image count differs (src={image_count_a}, saved={image_count_b})")
                return 1

            for name in sorted(a_names):
                if name == "word/document.xml":
                    continue
                ba = za.read(name)
                bb = zb.read(name)
                if ba != bb:
                    differing.append(f"{name}  src_sha={sha(ba)} new_sha={sha(bb)}  src_len={len(ba)} new_len={len(bb)}")

            if differing:
                print(f"FAIL: {len(differing)} non-document.xml part(s) differ after no-op save:")
                for line in differing:
                    print("  -", line)
                return 1

            print(f"OK: {len(a_names)} zip entries match (excluding word/document.xml)")
            print(f"OK: image count preserved ({image_count_a} files under word/media/)")
            return 0
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
