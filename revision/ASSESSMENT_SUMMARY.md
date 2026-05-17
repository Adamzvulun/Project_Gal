# Teacher Assessment — Distilled Summary

Source: `docs/אדם- הערכת ספר.pdf` (18 pages, Hebrew).
Compiled: 2026-05-17.
Purpose: 1-page summary so future sessions don't re-read the full PDF every time.

## Final score

| Section | Score | Max |
| --- | --- | --- |
| הצגת הבעיה | 13 | 20 |
| רקע תיאורטי | 5 | 10 |
| אסטרטגיית פתרון | 11 | 30 |
| ארכיטקטורה | 9 | 20 |
| למידה עצמאית | 6 | 20 |
| אלגוריתמים ומבני נתונים | 8 | 30 |
| יעילות | 2 | 10 |
| UML / Use Cases | 10 | 20 |
| תיעוד | 5 | 10 |
| **TOTAL** | **43** | **150** |

Verdict: "מנופח באופן מלאכותי" + "חשד קיצוני ל-LLM-generated engineering" + "לא מומלץ שייגש במתכונת הנוכחית".

## Top-level diagnosis

The teacher's central claim: the book is **LLM-generated**. Evidence cited:
- Tone too polished, too academic, "מושלם מדי".
- Terminology used precisely without showing comprehension.
- No "pain points", no debugging stories, no failures, no dead ends.
- Architecture descriptions read as inflated; "Architecture inflation via AI".
- Claims (50 peers, 4 GB swarm, 160 tests) without empirical evidence.
- BEPs name-dropped (BEP-3, 5, 11, 23) without analysis of their implications.

## The single most damning admission

Chapter 24 explicitly states **"הניסויים האמפיריים לא בוצעו בעת כתיבת הספר"** — the experiments promised throughout the book were never run. This crushed יעילות to 2/10 and damaged credibility everywhere else.

## Specific oral-defense risks the teacher flagged

The examiner will (per the teacher) drill into:
1. **Handshake** — exact byte structure of the 68-byte handshake.
2. **TCP framing** — why `recv()` doesn't return whole messages; partial-recv handling; length-prefix parser.
3. **Bencode** — byte-level format, canonical key ordering, why `info_hash` is computed on the re-encoded info dict (not the raw torrent file), bytes-vs-string distinction.
4. **rarest-first** — what's actually computed, edge cases (endgame, stale bitfields, lying peers).
5. **tit-for-tat** — sliding window? snubbing? seeding mode? what metric drives the sort?
6. **asyncio + Flask coexistence** — how does the event loop run alongside Flask?
7. **state machine** — what messages are valid in what state.

If the student can't answer these from memory, the project fails the oral.

## Teacher's "what would save the project" list

1. Stop writing "כמו מאמר" — show real understanding with pain points.
2. Stop framing rarest-first / tit-for-tat as "developed by student" — use "implemented".
3. Deepen rarest-first explanation (endgame, race conditions, swarm dynamics).
4. Deepen tit-for-tat (snubbing, seeding, bandwidth asymmetry, exploit resistance).
5. Real TCP framing walkthrough (partial recv, fragmented packets, buffering).
6. Real Bencode internals (byte-level, canonical ordering, info_hash derivation).
7. Real failure modes (peers disconnecting, corrupted pieces, race conditions).
8. Honest claims — drop unproven "50 peers / 4GB / robust" language.

## How this revision responds (cross-reference)

| Teacher critique | Our fix (see PLAN.md) |
| --- | --- |
| "ניסויים לא בוצעו" | §1: run real experiments, commit CSVs |
| "tit-for-tat שטחי" | §4e: sliding window + snubbing; §4e-bis: seeding mode |
| "no E2E test with live peer" | §2: mock-peer E2E test |
| "resume claim broken" | §3: implement `_load_state` |
| "polished, no pain points" | §4d/§4e/§4e-bis: pain stories per algorithm |
| "no TCP framing depth" | §4b: §6.2.1 handshake bytes + §6.2.2 framing walkthrough |
| "no Bencode depth" | §4c: §5.2 worked example + info_hash derivation |
| "developed → implemented" | §4a: tone fix across book |
| "no honest limitations" | §4g: explicit §25.5 list |
| "inflated claims" | §4h: trim "50 peers / 4 GB / robust" language |
