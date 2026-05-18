"""Inspect the working docx and emit a STRUCTURE_MAP.md.

Read-only: opens the .docx, walks body paragraphs, records:
  - paragraph index
  - whether paragraph has an image (w:drawing or w:pict)
  - heading level (if pStyle starts with "Heading")
  - first 80 chars of text
Then writes revision/book-v2/STRUCTURE_MAP.md.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

DOCX = Path("revision/book-v2/ספר פרוייקט אדם זבולון.docx")
OUT = Path("revision/book-v2/STRUCTURE_MAP.md")

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def extract_document_xml(path: Path) -> bytes:
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml")


def text_of_paragraph(p: ET.Element) -> str:
    parts: list[str] = []
    for t in p.iter(f"{{{W}}}t"):
        if t.text:
            parts.append(t.text)
    return "".join(parts)


def heading_level(p: ET.Element) -> str | None:
    pStyle = p.find(f"{{{W}}}pPr/{{{W}}}pStyle")
    if pStyle is None:
        return None
    val = pStyle.get(f"{{{W}}}val", "")
    m = re.match(r"^(?:Heading|heading)(\d+)$", val)
    if m:
        return m.group(1)
    if val.lower() == "title":
        return "T"
    return None


def has_image(p: ET.Element) -> bool:
    return (
        p.find(f".//{{{W}}}drawing") is not None
        or p.find(f".//{{{W}}}pict") is not None
    )


def has_section_break(p: ET.Element) -> bool:
    return p.find(f".//{{{W}}}sectPr") is not None


def main() -> int:
    xml = extract_document_xml(DOCX)
    root = ET.fromstring(xml)
    body = root.find(f"{{{W}}}body")
    if body is None:
        print("no body", file=sys.stderr)
        return 1

    rows: list[tuple[int, str, str, str, str]] = []
    image_count = 0
    heading_count = 0
    section_breaks = 0
    para_count = 0

    for idx, child in enumerate(body):
        tag = child.tag
        if tag == f"{{{W}}}p":
            para_count += 1
            txt = text_of_paragraph(child).strip()
            hl = heading_level(child)
            img = has_image(child)
            sect = has_section_break(child)
            if img:
                image_count += 1
            if hl:
                heading_count += 1
            if sect:
                section_breaks += 1
            kind_bits = []
            if hl:
                kind_bits.append(f"H{hl}")
            if img:
                kind_bits.append("IMG")
            if sect:
                kind_bits.append("§break")
            kind = ",".join(kind_bits) if kind_bits else ""
            rows.append((idx, "p", kind, txt[:120], ""))
        elif tag == f"{{{W}}}tbl":
            rows.append((idx, "tbl", "", "(table)", ""))
        elif tag == f"{{{W}}}sectPr":
            rows.append((idx, "sectPr", "", "(final section properties)", ""))
        else:
            local = tag.rsplit("}", 1)[-1]
            rows.append((idx, local, "", "(element)", ""))

    lines: list[str] = []
    lines.append("# Document structure map — `ספר פרוייקט אדם זבולון.docx`\n\n")
    lines.append(
        f"Source: `{DOCX}` · "
        f"body children: {len(rows)} · paragraphs: {para_count} · "
        f"image paragraphs: {image_count} · headings: {heading_count} · "
        f"section breaks: {section_breaks}\n\n"
    )
    lines.append("## Headings (TOC) — paragraph index → heading level → text\n\n")
    lines.append("| Body idx | Level | Image? | Text |\n")
    lines.append("| ---: | --- | :---: | --- |\n")
    for idx, ttag, kind, text, _ in rows:
        if "H" in kind.split(",")[0] if kind else False:
            # only headings
            pass
        if ttag == "p" and any(k.startswith("H") for k in kind.split(",")):
            img_flag = "img" if "IMG" in kind else ""
            level = next(k for k in kind.split(",") if k.startswith("H"))
            lines.append(f"| {idx} | {level} | {img_flag} | {text} |\n")

    lines.append("\n## Image-bearing paragraphs (do NOT touch)\n\n")
    lines.append("| Body idx | Heading? | Nearby text |\n")
    lines.append("| ---: | --- | --- |\n")
    for idx, ttag, kind, text, _ in rows:
        if ttag == "p" and "IMG" in kind.split(","):
            h = next((k for k in kind.split(",") if k.startswith("H")), "")
            lines.append(f"| {idx} | {h} | {text} |\n")

    lines.append("\n## Tables\n\n")
    lines.append("| Body idx |\n")
    lines.append("| ---: |\n")
    for idx, ttag, kind, text, _ in rows:
        if ttag == "tbl":
            lines.append(f"| {idx} |\n")

    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"summary: para={para_count} img-para={image_count} "
          f"headings={heading_count} tables={sum(1 for r in rows if r[1] == 'tbl')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
