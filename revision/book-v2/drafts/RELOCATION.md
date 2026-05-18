# Section relocation — book vs proposal

The pristine `docs/ספר פרוייקט אדם זבולון.docx` contains two distinct
parts:

* **Project proposal** — body indices `0..304`. Pages 1–23 of the
  print book. **OFF-LIMITS for this revision.** This is the original
  proposal submitted to the Ministry of Education; it is not part
  of the assessed project book and must not be edited.
* **Project book** — body indices `305..end`. The TOC starts at
  `305`, chapter 1 at `322`. This is what the teacher graded.

Initial drafts of edits §3.3 / §5.2 / §6.2 / §7.1 / §7.2 inadvertently
targeted proposal-area indices. They have been **removed**; the same
content is now placed in correct book locations:

| Original (wrong) target | Relocated to | Module |
|---|---|---|
| proposal §3.3 (idx 78) — attribution | dropped (book §6.1 already attributes) | `edit_tone.py` deleted |
| proposal §5.2 (idx 127) — bencode example | book §11.6.3 | `edit_book_116.py` |
| proposal §6.2 (idx 166) — handshake/framing | book §11.6.1, §11.6.2 | `edit_book_116.py` |
| proposal §7.1 (idx 180) — rarest-first depth | book §15.4.1 | `edit_book_154.py` |
| proposal §7.2 (idx 206) — sliding window / snubbing / seeding | book §15.4.2, §15.4.3, §15.4.4 | `edit_book_154.py` |

## Guard

`apply_all.py` now runs `_assert_no_proposal_writes()` before every
patch run. It introspects each pass module for ORIGINAL-source
body indices it touches (via the conventional names `REPLACEMENTS`,
`INSERT_PARA_AFTER`, `INSERT_AFTER`, `INSERT_AFTER_IDX`,
`INSERT_TABLE_AFTER`, `REMOVE_INDICES`) and refuses to run if any
index is below `PROPOSAL_CUTOFF_IDX = 305`.

`verify_proposal_untouched.py` is a post-edit check that canonicalises
every body child in the proposal range from both source and working
file and asserts byte-identity.

## Current passes (all in book region only)

```
book §11.3   asyncio+Flask hazard disclosure       (anchor idx  655)
book §11.6   handshake / framing / bencode         (anchor idx  710)
book §15.4   rarest-first depth + tit-for-tat trio (anchor idx  897)
book §24     empirical + E2E                       (idx 1316–1330)
book §25/§26 auto-resume update                    (idx 1348, 1349, 1363, 1377)
book §25.5   honest limitations                    (anchor idx 1349)
book §4h     trim inflated claims                  (idx 349, 579)
```

All indices ≥ 305.
