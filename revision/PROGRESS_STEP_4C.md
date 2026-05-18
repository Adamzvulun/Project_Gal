# Progress — Step 4c

Branch: `book-revision-v3` · Commits: `16a4cf3` (code), `31b2a5b` (tests).

Step 4 splits the "deepen tit-for-tat" critique into three sub-steps:

| Sub-step | Subject | Status |
| --- | --- | --- |
| 4a | Sliding-window contribution metric | done — see `PROGRESS_STEP_4A.md` |
| 4b | Snubbing detection & peer demotion | done — see `PROGRESS_STEP_4B.md` |
| **4c** | **Seeding mode — post-completion choke algorithm** | **this doc** |

For each step:

* **Why** — which sentence of the teacher's critique this fixes.
* **What** — the deliverables.
* **How** — the design decisions and the reasons for each.
* **Where** — file paths and key line numbers.
* **Result** — what's measurable now that wasn't before.
* **Oral exam prep** — what to say if the examiner asks about this.

---

## STEP 4c — Seeding mode

### Why

Tit-for-tat as implemented through 4a/4b is a **leecher's** algorithm: it
ranks peers by how much they've sent us (sliding window) and demotes
those who go silent (snubbing). Both rules implicitly assume *we still
need data*.

Once `piece_manager.is_complete`, we don't. Every peer's
`bytes_received_in_window` is permanently zero — they have nothing to
send us because we asked for nothing. The leech sort collapses: all
peers tie at zero and the top-K is whatever insertion order Python's
sort happens to preserve. That isn't an algorithm; that's noise.

The teacher's predicted oral question — *"מה קורה כשההורדה מסתיימת? איך
האלגוריתם מתנהג כשאתה הופך ל-seeder?"* — would catch this gap. Standard
BitTorrent (Cohen 2003 §3; libtorrent; mainline) flips the metric
post-completion: rank by **upload bandwidth delivered** rather than
download bandwidth received. The peers who drain our upload fastest are
the ones with the best downstream pipes; serving them best helps the
swarm propagate the file. This is the natural inverse of tit-for-tat
and arguably what the algorithm "really is" — a bandwidth-pairing rule
where the pairing direction depends on which side of the trade you're on.

### What

* `peer_connection.py`:
    * `UPLOAD_SAMPLE_RETENTION = 30` constant (`peer_connection.py:35`),
      symmetric to `DOWNLOAD_SAMPLE_RETENTION`.
    * `_upload_samples: deque[(timestamp, bytes_sent)]` field
      (`peer_connection.py:173`), updated and left-evicted in `send_piece`
      (`peer_connection.py:482–486`).
    * `bytes_sent_in_window(window: float = 20.0) -> int` accessor
      (`peer_connection.py:572`), mirroring `bytes_received_in_window`.
    * Cumulative `bytes_uploaded` field preserved — stats and GUI still
      consume it; only the unchoke sort key changes.
* `download_manager.py`:
    * `DownloadState.SEEDING = "Seeding"` enum value
      (`download_manager.py:53`). Additive — `_load_state` still maps
      stored `"Completed"` to `DownloadState.COMPLETED`.
    * `_is_seeding() -> bool` method
      (`download_manager.py:522`): returns
      `piece_manager.is_complete and state in (COMPLETED, SEEDING)`.
      Matches the spec in `revision/PLAN.md` exactly.
    * `_choke_loop` runs while `RUNNING or _is_seeding()`
      (`download_manager.py:542–544`) — post-completion the algorithm
      keeps making decisions instead of exiting.
    * `_tit_for_tat_unchoke` branches when `_is_seeding()` is True
      (`download_manager.py:585`), delegating to
      `_seed_mode_unchoke` (`download_manager.py:640`). Seed mode sorts
      by `bytes_sent_in_window(TIT_FOR_TAT_WINDOW)`, fills top-K, and
      adds one optimistic unchoke. Snubbing is intentionally skipped:
      a peer not sending us blocks is the normal case in seed mode.
* 6 new tests in `TestUploadSlidingWindow` (`test_peer_connection.py`)
  and 3 in `TestSeedingMode` (`test_download_manager.py`).
  Total suite: **203 → 212 passing**.

### How — design decisions

#### 1. Symmetric deque, not a reused one

Could we reuse `_download_samples` and store sign-bit-tagged bytes? No.
The retention windows differ in spirit (downloads feed both rate display
and tit-for-tat; uploads feed only seed-mode tit-for-tat), the writers
differ (PIECE handler vs `send_piece`), and the metric semantics differ
(bytes consumed from us vs delivered to us). A symmetric, independent
deque keeps the two paths trivially correct: every `send_piece` appends
+ evicts; readers walk a single-purpose structure.

#### 2. `_is_seeding()` accepts both COMPLETED and SEEDING

The plan was deliberate here: a download restored from disk
(`_load_state` path) lands in `DownloadState.COMPLETED` because that's
what we wrote to the state file. We want such a restored download to
seed-on-resume rather than sit idle. `_is_seeding()` therefore checks
membership in the set `{COMPLETED, SEEDING}` plus the piece-complete
predicate — a clean predicate that holds in both lifecycles (live
finish vs disk restore) without forcing a state migration.

`SEEDING` itself is reserved for an explicit user/API action ("re-seed
this completed torrent"), which is out of scope for 4c.

#### 3. Extend the loop, don't fork a new task

The original `_choke_loop` exited at `state != RUNNING`. Two options:
(a) start a separate `_seed_loop` on completion, or (b) widen the
existing loop's condition. (a) means two near-identical code paths and
a startup ordering question (what if completion fires during the
sleep?). (b) is one line of condition logic: `while RUNNING or
_is_seeding()`. The break check inside the loop is widened the same way.

The cost is a hot-path predicate call (`_is_seeding`) once per choke
cycle — negligible at 10-second intervals.

#### 4. Branch the unchoke, don't merge metrics

It would have been "clever" to combine the leech and seed metrics into
one composite sort key (`α · received + β · sent` with α=1 in leech,
α=0 in seed). Two reasons not to:

  * The interpretation question changes. In leech mode "high upload
    contribution from this peer" is irrelevant — they're not the one
    we're paying back. In seed mode "high download contribution to us"
    is zero. A composite hides that nothing about the two metrics is
    comparable across modes.
  * Snubbing logic is leech-only. A merged sort can't easily skip
    snubbing partitioning when seeding without re-introducing the
    branch we wanted to avoid.

Two clearly-named methods (`_tit_for_tat_unchoke`, `_seed_mode_unchoke`)
with a one-line dispatch make the mode boundary loud, which is what an
oral examiner wants to see.

#### 5. Seed mode keeps optimistic unchoke

Removing optimistic unchoke in seed mode would mean a fresh peer with
zero upload-window history can never break into the top-K — their
metric stays at zero unless someone gives them a chance. The optimistic
slot is exactly that chance. Spec match: libtorrent does the same.

### Where — files

| Path | Lines | Purpose |
| --- | ---: | --- |
| `python_engine/peer_connection.py` | +28 | `UPLOAD_SAMPLE_RETENTION`; `_upload_samples` deque; append+evict in `send_piece`; `bytes_sent_in_window` accessor |
| `python_engine/download_manager.py` | +90 | `DownloadState.SEEDING`; `_is_seeding()`; extended `_choke_loop` condition; branch in `_tit_for_tat_unchoke`; new `_seed_mode_unchoke` |
| `python_engine/tests/test_peer_connection.py` | +73 | `TestUploadSlidingWindow` (6 tests) |
| `python_engine/tests/test_download_manager.py` | +118 | `TestSeedingMode` (3 tests) |

### Result — what's measurable now

* `pytest python_engine/tests/ -q` → **212 passed** (was 203).
* Behavior change: a completed download no longer leaves the choke
  algorithm tied-at-zero. Verified by
  `TestSeedingMode::test_seeding_sorts_by_upload_window_not_download`,
  which constructs 5 peers with zero leech contribution and descending
  upload-window totals; the algorithm correctly unchokes the top-4 by
  upload.
* The book's §7.2.3 rewrite (step 5) can now cite seed mode honestly:
  pointing at `_is_seeding` and `_seed_mode_unchoke` with the
  asymmetric-trade rationale that makes the inversion intuitive.

### Oral exam prep — Step 4c

If asked **"מה קורה כשההורדה מסתיימת? איך האלגוריתם מתנהג?"**:

> ההגיון של tit-for-tat מבוסס על "כמה ה-peer שלח לי לאחרונה". אחרי
> שההורדה הסתיימה המספר הזה הוא אפס לכל ה-peers, כי אין לי מה לבקש.
> אז יש branch: `_is_seeding()` ב-`download_manager.py:522` מחזיר True,
> והאלגוריתם עובר ל-`_seed_mode_unchoke` (`download_manager.py:640`)
> שממיין לפי `bytes_sent_in_window` — כמה אני שולח אליו, לא כמה הוא
> שולח אלי.

If asked **"למה לא להמשיך באותו אלגוריתם רק עם המדד ההפוך?"**:

> זה בדיוק מה שאנחנו עושים — אבל בלי snubbing. ב-seed mode peer שלא
> שולח לי כלום זה לא pathology, זה ברירת המחדל (אין לו מה לשלוח לי,
> אני המקור). אז snubbing partition לא רלוונטי. בלי הbranch הייתי
> צריך תנאי בתוך snubbing שיודע "אנחנו seeding עכשיו" — שני שיפטים
> במקום אחד.

If asked **"איך אתה מודד את ה-bytes_sent_in_window?"**:

> כל קריאה ל-`send_piece` ב-`peer_connection.py:461` מוסיפה דגימה
> ל-`_upload_samples` (deque של זוגות `(timestamp, bytes_sent)`),
> ומפנה דגימות מעבר ל-30 שניות. הקורא ב-`_seed_mode_unchoke` סוכם
> דגימות מתוך החלון של 20 שניות — אותה ארכיטקטורה כמו
> `bytes_received_in_window`, רק עם direction הפוך.

If asked **"מה זה DownloadState.SEEDING?"**:

> ערך חדש ב-enum (`download_manager.py:53`). הוא לא הופעל אוטומטית —
> המעבר הרגיל נשאר RUNNING → COMPLETED. SEEDING שמור לפעולה
> מפורשת ("re-seed this completed torrent" דרך ה-API). אבל
> `_is_seeding()` בודק חברות בקבוצה `{COMPLETED, SEEDING}`, כך
> ש-download שהשלים גם בריצה חיה וגם דרך `_load_state` יזוהה
> כ-seeding ויעבור לbranch הנכון.

If asked **"מה ההבדל בין leech mode ל-seed mode בקצרה?"**:

> שניהם tit-for-tat: 4 unchoke מבוסס מדד + 1 optimistic. ההבדל הוא
> ה-direction של המדד: ב-leech לפי "מה הוא שלח לי" (bytes_received_in_window),
> ב-seed לפי "מה אני שלחתי לו" (bytes_sent_in_window). ב-leech יש
> גם snubbing partition כי peer שלא שולח זה buggy/malicious;
> ב-seed זה הנורמלי, אז אין partition.

If asked **"מה קורה כש-download מסתיים אבל ה-state עדיין RUNNING?"**:

> `_is_seeding` יחזיר False — כי הוא דורש state in (COMPLETED,
> SEEDING). זה מגן מפני branch מוקדם. ה-test
> `test_is_seeding_requires_completion_and_terminal_state` בודק את
> כל ארבע הקומבינציות.

### How to re-run

```bash
# Just the new seed-mode tests
python3 -m pytest \
    python_engine/tests/test_peer_connection.py::TestUploadSlidingWindow \
    python_engine/tests/test_download_manager.py::TestSeedingMode -v

# Full suite (must stay >= 212)
python3 -m pytest python_engine/tests/ -q

# Confirm the seed-mode branch is in the diff
git log book-revision-v2..book-revision-v3 --oneline
git diff book-revision-v2..book-revision-v3 -- \
    python_engine/peer_connection.py python_engine/download_manager.py
```
