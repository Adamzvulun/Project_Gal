#!/usr/bin/env bash
#
# build-book.sh — Builds the final Word document at docs/Project_Gal_Book.docx
# from all chapter Markdown files in book/.
#

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BOOK_DIR="$ROOT/book"
DOCS_DIR="$ROOT/docs"
OUTPUT="$DOCS_DIR/Project_Gal_Book.docx"
REFDOC="$BOOK_DIR/reference.docx"
TMP="$DOCS_DIR/.book-merged.md"

mkdir -p "$DOCS_DIR"

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

for ch in "${CHAPTERS[@]}"; do
    if [[ ! -f "$BOOK_DIR/$ch" ]]; then
        echo "ERROR: Missing chapter: $BOOK_DIR/$ch"
        exit 1
    fi
done

PAGEBREAK='
```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
'

# Build a static TOC from chapter headings (no Word TOC field — works in Google Docs)
echo "Generating static TOC..."
python3 << 'PYEOF'
import os, re

CHAPTERS = [
    "00-cover.md", "01-approved-proposal.md", "02-abstract-introduction.md",
    "03-goals-objectives.md", "04-challenges.md", "05-success-metrics.md",
    "06-theoretical-background.md", "07-existing-solutions.md",
    "08-alternatives-analysis.md", "09-chosen-alternative.md",
    "10-system-specification.md", "11-architecture.md", "12-security.md",
    "13-machine-learning-not-applicable.md", "14-software-description.md",
    "15-uml-use-cases.md", "16-screen-flow.md", "17-screens.md",
    "18-ui-elements.md", "19-user-alerts.md", "20-user-interface.md",
    "21-code.md", "22-database.md", "23-user-manual.md",
    "24-testing-evaluation.md", "25-conclusions.md",
    "26-future-developments.md", "27-bibliography.md",
    "appendix-a-code-samples.md"
]

out = ["# תוכן עניינים", ""]
for ch in CHAPTERS[1:]:  # skip 00-cover
    path = os.path.join("book", ch)
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^# +(.+?)\s*$', line)
            if m:
                out.append(f"- {m.group(1).strip()}")
                break

with open("docs/.toc.md", 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')

print(f"  TOC contains {len(out) - 2} chapter entries")
PYEOF

# Step 1: Concatenate
echo "Merging ${#CHAPTERS[@]} chapters..."
: > "$TMP"
cat "$BOOK_DIR/${CHAPTERS[0]}" >> "$TMP"
echo "$PAGEBREAK" >> "$TMP"
cat "$DOCS_DIR/.toc.md" >> "$TMP"
for ch in "${CHAPTERS[@]:1}"; do
    echo "$PAGEBREAK" >> "$TMP"
    cat "$BOOK_DIR/$ch" >> "$TMP"
done

# Step 2: pandoc
echo "Running pandoc..."
pandoc \
    "$TMP" \
    --from markdown \
    --to docx \
    --output "$OUTPUT" \
    --reference-doc="$REFDOC" \
    --top-level-division=chapter \
    --metadata lang=he \
    --metadata dir=rtl \
    --highlight-style=tango \
    --wrap=preserve 2>/dev/null

rm -f "$TMP" "$DOCS_DIR/.toc.md"

# Step 3: Post-process the docx
echo "Post-processing docx..."
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

with open(doc_path, 'r', encoding='utf-8') as f:
    doc = f.read()

# 1. Wire up header/footer (refs into sectPr)
with open(rels_path, 'r', encoding='utf-8') as f:
    rels = f.read()
hdr_match = re.search(r'<Relationship Id="(rId\d+)"[^>]*Target="header1\.xml"', rels)
ftr_match = re.search(r'<Relationship Id="(rId\d+)"[^>]*Target="footer1\.xml"', rels)
if hdr_match and ftr_match:
    hdr_id, ftr_id = hdr_match.group(1), ftr_match.group(1)
    hdr_ref = f'<w:headerReference xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" w:type="default" r:id="{hdr_id}"/>'
    ftr_ref = f'<w:footerReference xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" w:type="default" r:id="{ftr_id}"/>'
    new_sect = f'<w:sectPr>{hdr_ref}{ftr_ref}</w:sectPr>'
    doc = re.sub(r'<w:sectPr\s*/>', new_sect, doc)
    def inject(m):
        inner = m.group(1)
        if 'headerReference' in inner:
            return m.group(0)
        return f'<w:sectPr>{hdr_ref}{ftr_ref}{inner}</w:sectPr>'
    doc = re.sub(r'<w:sectPr>(.*?)</w:sectPr>', inject, doc, flags=re.DOTALL)
    print(f"  Wired up header={hdr_id}, footer={ftr_id}")

# 2. Force LTR on SourceCode paragraphs (strip pandoc's bidi/rtl)
def force_ltr(match):
    para = match.group(0)
    para = re.sub(r'<w:bidi\s*/>', '', para)
    para = re.sub(r'<w:rtl\s*/>', '', para)
    para = re.sub(
        r'(<w:pStyle w:val="SourceCode"\s*/>)',
        r'\1<w:bidi w:val="0"/>',
        para, count=1)
    return para
doc = re.sub(
    r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="SourceCode"\s*/>(?:(?!</w:p>).)*?</w:p>',
    force_ltr, doc, flags=re.DOTALL)
print("  Forced LTR on SourceCode paragraphs")

# 3. Remove bookmarks (pandoc adds them for every heading — Google Docs
#    shows them as little blue ribbon icons)
before_marks = doc.count('<w:bookmarkStart')
doc = re.sub(r'<w:bookmarkStart[^/]*/>', '', doc)
doc = re.sub(r'<w:bookmarkEnd[^/]*/>', '', doc)
print(f"  Removed {before_marks} bookmarks (cleaner Google Docs display)")

# 4. Add table borders to every table (in case pandoc forgot)
# pandoc usually emits <w:tblBorders/> but let's make sure
def add_borders(match):
    pr = match.group(0)
    if '<w:tblBorders>' in pr:
        return pr
    borders = (
        '<w:tblBorders>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="333333"/>'
        '<w:left w:val="single" w:sz="6" w:space="0" w:color="333333"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="333333"/>'
        '<w:right w:val="single" w:sz="6" w:space="0" w:color="333333"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        '</w:tblBorders>'
    )
    # Inject right before </w:tblPr>
    return pr.replace('</w:tblPr>', borders + '</w:tblPr>')
doc = re.sub(r'<w:tblPr>.*?</w:tblPr>', add_borders, doc, flags=re.DOTALL)
print("  Added borders to all tables")

# 5. Highlight first row of each table (header) with light blue
def highlight_first_row(match):
    table = match.group(0)
    def shade_first_tr(tr_match):
        tr = tr_match.group(0)
        # tcPr may be self-closing (<w:tcPr />) or have children (<w:tcPr>...</w:tcPr>)
        shade_xml = '<w:shd w:val="clear" w:color="auto" w:fill="DCE6F1"/>'
        # Replace self-closing tcPr first
        tr = re.sub(r'<w:tcPr\s*/>', f'<w:tcPr>{shade_xml}</w:tcPr>', tr)
        # Then add to existing tcPr (only if no shading already)
        def add_shade(tcpr_match):
            inner = tcpr_match.group(1)
            if '<w:shd' in inner:
                return tcpr_match.group(0)
            return f'<w:tcPr>{shade_xml}{inner}</w:tcPr>'
        tr = re.sub(r'<w:tcPr>((?:(?!</w:tcPr>).)*)</w:tcPr>', add_shade, tr, flags=re.DOTALL)
        return tr
    table_new = re.sub(r'<w:tr>.*?</w:tr>', shade_first_tr, table, count=1, flags=re.DOTALL)
    return table_new
doc = re.sub(r'<w:tbl>.*?</w:tbl>', highlight_first_row, doc, flags=re.DOTALL)
shaded = doc.count('fill="DCE6F1"')
print(f"  Highlighted {shaded} header cells (first row, light blue)")

with open(doc_path, 'w', encoding='utf-8') as f:
    f.write(doc)

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
