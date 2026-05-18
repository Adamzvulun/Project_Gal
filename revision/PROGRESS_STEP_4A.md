# Progress — Step 4a

Branch: `book-revision-v2` · Commit: (see git log after push).

The teacher's most damaging algorithmic note was that tit-for-tat is
both unoriginal *and* shallow. Step 4 addresses the shallowness in
three independent sub-steps:

| Sub-step | Subject | Status |
| --- | --- | --- |
| **4a** | Sliding-window contribution metric | **this doc** |
| 4b   | Snubbing (detect peers that unchoke us then stop sending) | done — see `PROGRESS_STEP_4B.md` |
| 4c   | Seeding mode (post-completion, sort by upload-window) | done — see `PROGRESS_STEP_4C.md` |

For each step:

* **Why** — which sentence of the teacher's critique this fixes.
* **What** — the deliverables.
* **How** — the design decisions and the reasons for each.
* **Where** — file paths and key line numbers.
* **Result** — what's measurable now that wasn't before.
* **Oral exam prep** — what to say if the examiner asks about this.

---

## STEP 4a — Sliding-window contribution metric

### Why

The teacher's critique flagged the tit-for-tat implementation as
"שטחי" (shallow). The book sells the algorithm as "מימוש מלא של
Tit-for-Tat" but the actual sort key at `download_manager.py:537`
was `conn.bytes_downloaded` — **cumulative** since session start.
Failure mode: a peer that contributes 4MB in the first minute and
then goes silent keeps a #1 ranking forever, holding an unchoke
slot a fresher contributor would now deserve. That's not what Bram
Cohen's 2003 algorithm does — real BitTorrent uses a ~20-second
sliding window so the metric reflects *recent* generosity.

The §7.2.1 oral-exam question the teacher predicted ("איזה חלון
זמן? למה לא cumulative?") would have caught the gap. This step
closes it before the exam.

### What

* `PeerConnection.bytes_received_in_window(window: float = 20.0)
  -> int` — sums `(timestamp, bytes_received)` samples from a
  bounded deque, returning bytes received in the last `window`
  seconds. Pure read; doesn't mutate the deque.
* The existing `_download_samples` list is now a
  `collections.deque` with lazy left-eviction on every PIECE
  message. Retention is bumped from a magic-30 to a named constant
  `DOWNLOAD_SAMPLE_RETENTION = 30` so it documents *why* (must be
  ≥ longest sliding window any consumer queries).
* The cumulative `bytes_downloaded` field is preserved — chapter 24
  stats and the GUI display still use it.
* `_tit_for_tat_unchoke` (`download_manager.py:540`) now sorts by
  `conn.bytes_received_in_window(TIT_FOR_TAT_WINDOW)` where
  `TIT_FOR_TAT_WINDOW = 20`. Choosing 20s deliberately: two
  10-second choke cycles fit inside, so the metric is stable
  across consecutive decisions.
* 8 new tests across `test_peer_connection.py` (6) and
  `test_download_manager.py` (2). Total suite: **185 → 193 passing**.

### How — design decisions

#### 1. One deque, two readers (rate display + sliding window)

The pre-step code already kept a 30-second window of samples for
the `download_rate` display. Adding a second, parallel structure
for tit-for-tat would have meant two append paths on every PIECE
message, two retention policies, and two ways for them to drift.

Instead the same `_download_samples` deque now serves both
purposes: the existing rate calc reads it the way it always did,
and the new `bytes_received_in_window(W)` walks the same samples
with a tighter cutoff. Retention is set to the *longest* window any
consumer needs (`DOWNLOAD_SAMPLE_RETENTION = 30`), so a 20-second
query is well-defined.

The eviction also moved from `list` rebuild on every PIECE
(O(n) → new list) to `deque.popleft` in a while loop (amortized
O(1) per evicted sample). On a busy peer this matters — the old
code was rebuilding a 30s sample list per block.

#### 2. Window length: 20 seconds, justified by choke interval

Two choke cycles (`CHOKE_INTERVAL = 10s`) fit inside a 20-second
window. That isn't an accident; it's the property that keeps the
metric stable: by the time we make a new choke decision, the
metric we read includes data from the previous cycle plus the
current one, so a single transient (an unlucky 1-second pause)
doesn't flip a peer's ranking. Mainline BitTorrent and libtorrent
use the same 20s; we're matching the well-known reference, which
is the right thing for an exam-defensible implementation.

#### 3. Read-only accessor; eviction happens on write

`bytes_received_in_window` walks the deque without `popleft`. Two
reasons:

* The deque is mutated only by the message loop (single-writer);
  letting the unchoke loop (different task) mutate it too would
  introduce shared-state hazards.
* Read-side eviction would be wrong anyway — a `bytes_received_in_window(5)`
  call shouldn't discard samples that the 30-second rate calc
  still needs.

The trade-off: the deque can briefly contain samples slightly older
than the longest window any consumer reads. Bounded by retention
on the next PIECE message; in the worst case it's 30s of stale
state. Negligible.

#### 4. Keep `bytes_downloaded` cumulative

The book's chapter 24 reports "total bytes per peer" numbers and
the GUI surfaces a cumulative counter; both rely on
`bytes_downloaded`. Replacing it with the windowed metric would
have silently changed two unrelated surfaces. Additive change only.

### Where — files

| Path | Lines | Purpose |
| --- | ---: | --- |
| `python_engine/peer_connection.py` | +20 | `collections` import; `DOWNLOAD_SAMPLE_RETENTION` constant; `_download_samples` typed as `deque`; deque-style eviction in the PIECE handler; new `bytes_received_in_window` accessor |
| `python_engine/download_manager.py` | +4 | `TIT_FOR_TAT_WINDOW` constant; `_tit_for_tat_unchoke` sorts by `bytes_received_in_window(TIT_FOR_TAT_WINDOW)` instead of `bytes_downloaded` |
| `python_engine/tests/test_peer_connection.py` | +75 | `TestSlidingWindow` class: empty, sums recent, excludes old, doesn't mutate, PIECE-handler append-and-evict, cumulative-stat preservation |
| `python_engine/tests/test_download_manager.py` | +50 | `TestTitForTatSlidingWindow` class: silent peer demoted despite huge cumulative; sort key is window not cumulative |

### Result — what's measurable now

* `pytest python_engine/tests/ -q` → **193 passed** (was 185).
* Behavior change: a peer that uploads 10MB then goes silent for
  20+ seconds is now sorted *after* a peer that just uploaded 50
  bytes. The unchoke loop reflects current generosity, not session
  totals.
* `download_manager.py:543-547` is the new sort line; the comment
  above it documents the failure mode this fixes.
* The book's §7.2 update (step 5) can now cite the sliding-window
  implementation honestly: "המימוש משתמש בחלון זמן של 20 שניות,
  כפי שמופיע ב-Cohen 2003 וב-mainline BitTorrent" — pointing at
  `bytes_received_in_window` + `TIT_FOR_TAT_WINDOW`.

### Oral exam prep — Step 4a

If asked **"איך אתה ממיין peers ב-tit-for-tat?"**:

> לפי כמה בייטים ה-peer שלח לנו ב-20 השניות האחרונות, לא
> cumulative. הקוד ב-`download_manager.py:540` ממיין לפי
> `conn.bytes_received_in_window(TIT_FOR_TAT_WINDOW)`. המבנה
> הפנימי הוא `collections.deque` של זוגות `(timestamp,
> bytes_received)` ב-`peer_connection.py`, שמתעדכן בכל הודעת PIECE
> ומפנה מצדו השמאלי כל דגימה מעבר ל-30 שניות.

If asked **"למה 20 שניות?"**:

> שני מחזורי choke (כל אחד 10 שניות, `CHOKE_INTERVAL`) נכנסים
> בתוך החלון. זה אומר שכשאנחנו מקבלים החלטת choke חדשה, המדד
> מכסה את המחזור הקודם והנוכחי — peer לא נופל מהרשימה רק כי
> נשנק לשנייה. זה גם המספר ש-mainline BitTorrent ו-libtorrent
> משתמשות בו.

If asked **"מה הבעיה ב-cumulative bytes_downloaded?"**:

> Peer שתרם הרבה בהתחלה ואז השתתק — נשאר על #1 לנצח. תופס מקום
> שמגיע למישהו שמתרם עכשיו. זה הופך את tit-for-tat ל-give-once
> instead of give-continuously. החלון נותן את מה שהאלגוריתם
> מתיימר לעשות: לחלק bandwidth ל-peers שכרגע מחזירים טובה.

If asked **"איך אתה מאחסן את הדגימות בלי לדלוף זיכרון?"**:

> `collections.deque` עם פינוי שמאלי בכל הודעת PIECE: כל דגימה
> מעבר ל-30 שניות נזרקת. החלון של 20 שניות תמיד מסתכל על תת-קבוצה
> של הדגימות הקיימות, אז קוראים לא צריכים לפנות בעצמם. הקבוע
> `DOWNLOAD_SAMPLE_RETENTION` מתעד שזה חייב להיות לפחות
> כאורך החלון הארוך ביותר שמישהו שואל.

If asked **"איך זה משפיע על display שהמשתמש רואה?"**:

> לא משפיע. `bytes_downloaded` (הסכום הצבור) נשאר fields ציבורי,
> וה-GUI ממשיך להראות אותו. שיניתי רק את מפתח המיון של
> tit-for-tat — לא את הסטטיסטיקות.

### How to re-run

```bash
# Just the new sliding-window tests
python3 -m pytest python_engine/tests/test_peer_connection.py::TestSlidingWindow \
                  python_engine/tests/test_download_manager.py::TestTitForTatSlidingWindow -v

# Full suite (must stay >= 193)
python3 -m pytest python_engine/tests/ -q
```
