#!/usr/bin/env bash
#
# build-book.sh — Combines all chapters in book/ into a single Word document
# under docs/, using pandoc with the customised Hebrew/RTL reference docx,
# and post-processes the result to wire up the page header/footer that
# pandoc strips from sectPr.
#
# Output: docs/Project_Gal_Book.docx
#

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BOOK_DIR="$ROOT/book"
DOCS_DIR="$ROOT/docs"
OUTPUT="$DOCS_DIR/Project_Gal_Book.docx"
REFDOC="$BOOK_DIR/reference.docx"
TMP="$DOCS_DIR/.book-merged.md"

mkdir -p "$DOCS_DIR"

# Chapter order: cover → main chapters 01-27 → appendix
CHAPTERS=(
    "00-cover.md"
    "01-approved-proposal.md"
    "02-abstract-introduction.md"
    "03-goals-objectives.md"
    "04-challenges.md"
    "05-success-metrics.md"
    "06-theoretical-background.md"
    "07-existing-solutions.md"
    "08-alternatives-analysis.md"
    "09-chosen-alternative.md"
    "10-system-specification.md"
    "11-architecture.md"
    "12-security.md"
    "13-machine-learning-not-applicable.md"
    "14-software-description.md"
    "15-uml-use-cases.md"
    "16-screen-flow.md"
    "17-screens.md"
    "18-ui-elements.md"
    "19-user-alerts.md"
    "20-user-interface.md"
    "21-code.md"
    "22-database.md"
    "23-user-manual.md"
    "24-testing-evaluation.md"
    "25-conclusions.md"
    "26-future-developments.md"
    "27-bibliography.md"
    "appendix-a-code-samples.md"
)

# Verify all chapters exist
for ch in "${CHAPTERS[@]}"; do
    if [[ ! -f "$BOOK_DIR/$ch" ]]; then
        echo "ERROR: Missing chapter: $BOOK_DIR/$ch"
        exit 1
    fi
done

# Page-break marker for docx (raw OpenXML, recognised by pandoc)
PAGEBREAK='
```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
'

# ---------- Step 1. Concatenate chapters ----------
echo "Merging ${#CHAPTERS[@]} chapters..."
: > "$TMP"
cat "$BOOK_DIR/${CHAPTERS[0]}" >> "$TMP"
echo "$PAGEBREAK" >> "$TMP"
for ch in "${CHAPTERS[@]:1}"; do
    echo "$PAGEBREAK" >> "$TMP"
    cat "$BOOK_DIR/$ch" >> "$TMP"
done

# ---------- Step 2. pandoc → docx ----------
echo "Running pandoc..."
pandoc \
    "$TMP" \
    --from markdown \
    --to docx \
    --output "$OUTPUT" \
    --reference-doc="$REFDOC" \
    --toc \
    --toc-depth=3 \
    --top-level-division=chapter \
    --metadata lang=he \
    --metadata dir=rtl \
    --highlight-style=tango \
    --wrap=preserve 2>/dev/null

rm -f "$TMP"

# ---------- Step 3. Post-process: wire header/footer + force LTR on code blocks ----------
echo "Post-processing docx (wiring header/footer + LTR code blocks)..."
OUTPUT_DOCX="$OUTPUT" python3 << 'PYEOF'
import os, re, zipfile, shutil

DOCX = os.environ['OUTPUT_DOCX']

# Extract
tmp_dir = "/tmp/postproc-docx"
if os.path.exists(tmp_dir):
    shutil.rmtree(tmp_dir)
os.makedirs(tmp_dir)
with zipfile.ZipFile(DOCX, 'r') as z:
    z.extractall(tmp_dir)

doc_path = os.path.join(tmp_dir, 'word', 'document.xml')
rels_path = os.path.join(tmp_dir, 'word', '_rels', 'document.xml.rels')

# Find header / footer rIds in rels
with open(rels_path, 'r', encoding='utf-8') as f:
    rels = f.read()

header_match = re.search(r'<Relationship Id="(rId\d+)"[^>]*Target="header1\.xml"', rels)
footer_match = re.search(r'<Relationship Id="(rId\d+)"[^>]*Target="footer1\.xml"', rels)

if not header_match or not footer_match:
    print("WARNING: header/footer relationships not found - skipping wiring.")
    exit(0)

hdr_id = header_match.group(1)
ftr_id = footer_match.group(1)
print(f"  header={hdr_id}, footer={ftr_id}")

# Patch document.xml: replace empty <w:sectPr /> with one that has refs
with open(doc_path, 'r', encoding='utf-8') as f:
    doc = f.read()

hdr_ref = f'<w:headerReference xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" w:type="default" r:id="{hdr_id}"/>'
ftr_ref = f'<w:footerReference xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" w:type="default" r:id="{ftr_id}"/>'

# Pattern 1: <w:sectPr /> (self-closing) - the most common case after pandoc
new_sect = f'<w:sectPr>{hdr_ref}{ftr_ref}</w:sectPr>'
patched = re.sub(r'<w:sectPr\s*/>', new_sect, doc)

# Pattern 2: <w:sectPr>...inner...</w:sectPr>
def inject_into_sectpr(match):
    inner = match.group(1)
    # Don't double-inject
    if 'headerReference' in inner:
        return match.group(0)
    return f'<w:sectPr>{hdr_ref}{ftr_ref}{inner}</w:sectPr>'

patched = re.sub(r'<w:sectPr>(.*?)</w:sectPr>', inject_into_sectpr, patched, flags=re.DOTALL)

# ---------- Force LTR on SourceCode paragraphs ----------
# pandoc injects <w:bidi/> into every paragraph because of `dir: rtl`.
# For SourceCode paragraphs we must override this to LTR.
# Strategy: in every <w:p> that uses pStyle="SourceCode", replace
# <w:bidi/> (no value -> defaults to RTL) with <w:bidi w:val="0"/> (LTR).
def force_ltr_in_sourcecode(match):
    para = match.group(0)
    # Remove any explicit <w:bidi/> inside this paragraph's pPr
    para = re.sub(r'<w:bidi\s*/>', '', para)
    # Inject explicit LTR bidi flag right after the pStyle line
    para = re.sub(
        r'(<w:pStyle w:val="SourceCode"\s*/>)',
        r'\1<w:bidi w:val="0"/>',
        para, count=1)
    return para

# Match every <w:p>...SourceCode...</w:p> block
patched = re.sub(
    r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="SourceCode"\s*/>(?:(?!</w:p>).)*?</w:p>',
    force_ltr_in_sourcecode,
    patched, flags=re.DOTALL)

# Also remove <w:rtl/> from runs inside SourceCode paragraphs
# (they're added when text contains characters that pandoc thinks are RTL)
def strip_rtl_in_sourcecode(match):
    para = match.group(0)
    para = re.sub(r'<w:rtl\s*/>', '', para)
    return para

patched = re.sub(
    r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="SourceCode"\s*/>(?:(?!</w:p>).)*?</w:p>',
    strip_rtl_in_sourcecode,
    patched, flags=re.DOTALL)

with open(doc_path, 'w', encoding='utf-8') as f:
    f.write(patched)

# Re-zip
new_docx = DOCX + '.new'
with zipfile.ZipFile(new_docx, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(tmp_dir):
        for file in files:
            full = os.path.join(root, file)
            arc = os.path.relpath(full, tmp_dir)
            z.write(full, arc)

shutil.move(new_docx, DOCX)
shutil.rmtree(tmp_dir)
print("  Post-processing complete.")
PYEOF

echo "Done: $OUTPUT"
ls -lh "$OUTPUT"
