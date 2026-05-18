# Progress — Step 4b

Branch: `book-revision-v3` · Commits: `8cb8c70` (peer_connection),
`379fe8f` (download_manager). See `git log` after push.

Step 4 splits the "deepen tit-for-tat" critique into three sub-steps:

| Sub-step | Subject | Status |
| --- | --- | --- |
| 4a | Sliding-window contribution metric | done (see `PROGRESS_STEP_4A.md`) |
| **4b** | **Snubbing — detect peers that unchoke us then stop sending** | **this doc** |
| 4c | Seeding mode (post-completion, sort by upload-window) | done — see `PROGRESS_STEP_4C.md` |

For each step:

* **Why** — which sentence of the teacher's critique this fixes.
* **What** — the deliverables.
* **How** — the design decisions and the reasons for each.
* **Where** — file paths and key line numbers.
* **Result** — what's measurable now that wasn't before.
* **Oral exam prep** — what to say if the examiner asks about this.

---

## STEP 4b — Snubbing detection & peer demotion

### Why

Step 4a fixed *one* failure mode of tit-for-tat (early-contributor stays
ranked forever) by switching the sort key to a 20-second sliding window.
But there's a second, related failure mode the window alone does NOT
catch: **a peer that sends `unchoke`, gets requests from us, and then
stops delivering blocks entirely**.

Within the 20-second window the snubbed peer's recent samples still
count, so they keep a high rank for ~20 seconds after going silent —
that's two full choke cycles. Worse, if the snubbing started right before
a piece batch landed, the peer can stay in top-4 for an entire cycle by
inertia alone. A buggy or malicious peer who never delivers can rinse and
repeat: their advertised willingness ("not choking you") combined with
just enough early blocks to seed the window keeps the slot locked.

Standard BitTorrent (Cohen 2003 §3; mainline; libtorrent) calls this
state **snubbed** and the algorithm demotes such peers from the unchoke
candidates and triggers a replacement optimistic unchoke. Without this,
the oral examiner's predictable follow-up — *"מה קורה אם peer נותן
unchoke אבל לא שולח כלום?"* — has no answer in the code.

### What

* `PeerConnection.is_snubbed(threshold: float = SNUB_THRESHOLD = 60.0) -> bool`
  in `peer_connection.py:557`. Returns `True` iff:
    * `peer_choking == False` — they said they would send.
    * `_last_request_time > 0` — we actually asked them for blocks.
    * `time.time() - max(_last_piece_time, _connect_time) > threshold`.
* `PeerConnection._connect_time` (`peer_connection.py:174`, set in
  `connect()` at line 197) — fallback "last signal" so a freshly-unchoked
  peer gets the full 60 s to deliver its first block before being
  marked snubbed.
* `SNUB_THRESHOLD = 60.0` module constant near the other timing constants
  (`peer_connection.py:36`).
* `Download._previously_snubbed: Set[str]` (`download_manager.py:146`)
  — tracks which peers we've already logged so the 10-second choke loop
  doesn't spam INFO lines for the same stuck peer.
* `_tit_for_tat_unchoke` (`download_manager.py:529`) rewritten:
    1. Partition `interested_peers` into `non_snubbed` and `snubbed`
       (`download_manager.py:556–562`).
    2. Log newly snubbed peers once per episode
       (`download_manager.py:565–569`).
    3. Sort `non_snubbed` by sliding-window contribution
       (`download_manager.py:575–578`).
    4. Fill top-K from `non_snubbed` first, fall back to `snubbed` only
       when there aren't enough healthy candidates
       (`download_manager.py:583–587`).
    5. Optimistic unchoke uses **non-snubbed remainder only**
       (`download_manager.py:595–602`) — picking a snubbed peer
       optimistically would defeat the demotion.
* 6 new tests in `TestSnubbing` (`test_peer_connection.py`) and 4 new
  tests in `TestSnubbingPartition` (`test_download_manager.py`).
  Total suite: **193 → 203 passing**.

### How — design decisions

#### 1. Reuse `_last_piece_time`, don't duplicate

The plan called for a new `last_block_received_at` field. But
`peer_connection.py:174` already had `_last_piece_time`, updated in the
PIECE handler at `peer_connection.py:341`. A second field would mean two
write paths (one of them likely to drift) and two ways to ask the same
question. Reusing the existing field keeps one source of truth: every
arriving block bumps it, every consumer reads it.

#### 2. `_connect_time` fallback — protect freshly-unchoked peers

Without a fallback, `is_snubbed()` for a peer that just unchoked us but
hasn't delivered its first block yet would compare `time.time() - 0`,
which is enormous, and immediately mark them snubbed. That punishes peers
who legitimately need a moment between handshake and first PIECE.

Setting `_connect_time` on successful handshake (`peer_connection.py:197`)
and computing `last_signal = max(_last_piece_time, _connect_time)` gives
every new peer the full 60-second window to start delivering. After the
first PIECE arrives, `_last_piece_time` takes over naturally.

#### 3. Partition before sort, not after

It would be tempting to sort all peers together by contribution and then
"filter out snubbed peers." That's wrong: a peer with high recent
contribution who *just* got snubbed (clock ticked past 60 s with no new
block) would already be at the top of the sort, so filtering still has to
remove top entries, then promote others — equivalent to partitioning
first, but harder to reason about.

Partitioning before the sort gives a clean invariant: **all peers in
`non_snubbed[:K]` are healthy and ranked by contribution**. Tests
exercise the failure mode where a snubbed peer has a *higher* window
total than every healthy peer (the snub is recent enough to keep the
window populated); the partition correctly demotes them anyway.

#### 4. Optimistic unchoke is non-snubbed-only

Initial implementation had optimistic unchoke fall back to a snubbed peer
when `non_snubbed_remaining` was empty. A failing test caught this: in a
swarm where top-K is fully healthy and only one snubbed peer remains, the
optimistic pick would unchoke the snubbed peer — defeating the demotion
on the very next cycle.

The corrected rule (`download_manager.py:592–602`): optimistic unchoke
only ever picks from non-snubbed remainder; if every healthy peer is
already unchoked, we skip optimistic unchoke this cycle entirely.
Discovery's purpose is finding *new* contributors, not promoting known
non-contributors.

#### 5. Threshold = 60 s, justified

60 s is six choke cycles (`CHOKE_INTERVAL = 10`). That's deliberately
generous — short transient stalls (NAT timer reset, OS scheduler hiccup,
peer waiting on disk) shouldn't trigger demotion. Mainline BitTorrent
uses 60 s; libtorrent uses 60 s; we match.

A shorter threshold (say 20 s) would flap on healthy peers that just
happened to have a slow piece. Longer (say 5 min) would let a malicious
peer hold a slot for the full 5 min. 60 s is the well-known reference.

#### 6. Log once per snub episode

A naive implementation would log "peer snubbed" on every choke cycle
while the peer stayed snubbed — 6 log lines per minute per stuck peer.
The `_previously_snubbed` set diff (`download_manager.py:565–569`)
makes it exactly one INFO line per snub episode, and a fresh one if the
peer recovers and snubs again later. A test verifies the once-per-episode
behaviour.

### Where — files

| Path | Lines | Purpose |
| --- | ---: | --- |
| `python_engine/peer_connection.py` | +35 | `SNUB_THRESHOLD = 60.0`; `_connect_time` field + setter in `connect()`; `is_snubbed(threshold=...)` method |
| `python_engine/download_manager.py` | +60 −20 | `_previously_snubbed` field; partition + replacement-optimistic logic in `_tit_for_tat_unchoke` |
| `python_engine/tests/test_peer_connection.py` | +79 | `TestSnubbing` (6 tests: peer_choking gate, no-requests gate, threshold detection, recent piece clears snub, configurable threshold, connect_time fallback) |
| `python_engine/tests/test_download_manager.py` | +157 | `TestSnubbingPartition` (4 tests: demotion when alternatives exist, fallback when only choice, optimistic-unchoke avoids snubbed, log-once-per-episode) |

### Result — what's measurable now

* `pytest python_engine/tests/ -q` → **203 passed** (was 193).
* Behavior change: a peer that sends `unchoke`, gets requests, then
  goes silent for ≥ 60 s is now removed from the top-K unchoke set on
  the next choke cycle, and the optimistic pick rotates to a healthy
  candidate instead. Verified by `TestSnubbingPartition::test_snubbed_peer_demoted_when_alternatives_exist`,
  which constructs a peer with the largest window contribution and
  asserts it gets choked.
* The book's §7.2.2 rewrite (step 5) can now cite snubbing honestly:
  *"המימוש מזהה peers שהשתתקו כפי שמתואר בעבודתו של Cohen ב-2003,
  באמצעות סף של 60 שניות"* — pointing at `is_snubbed` +
  `SNUB_THRESHOLD`.

### Oral exam prep — Step 4b

If asked **"איך אתה מטפל ב-peers שלא משתפים פעולה?"**:

> זה נקרא snubbing. peer שלא choking אותנו, אנחנו ביקשנו ממנו בלוקים,
> אבל לא הגיע אף PIECE כבר 60 שניות — מסומן כ-snubbed.
> `peer_connection.py:557` חושב את זה: `not peer_choking`, יש לנו
> `_last_request_time > 0`, וה-`time.time() - max(_last_piece_time,
> _connect_time) > 60`.

If asked **"למה 60 שניות ולא יותר קצר?"**:

> 60 = שישה מחזורי choke. סף קצר יותר היה flapping — peer בריא ש-piece
> אחד שלו לקח 25 שניות היה נופל ומחזיר את עצמו כל הזמן. 60 שניות
> מסביר רעש קצר ועדיין תופס את הפתולוגיה של peer שאף פעם לא שולח.
> זה גם המספר שמגיע מ-mainline ו-libtorrent — לא המצאתי אותו.

If asked **"איך זה משפיע על מי שמקבל unchoke?"**:

> ב-`_tit_for_tat_unchoke` ב-`download_manager.py:529`, לפני המיון אני
> מפצל את ה-peers ל-`non_snubbed` ו-`snubbed`. רק non_snubbed מתחרים
> במיון לפי החלון הנע. ה-K הראשונים ממולאים מ-non_snubbed, ורק אם אין
> מספיק peers בריאים אני נופל ל-snubbed. ה-optimistic unchoke גם
> בודק רק את ה-remainder של non_snubbed — לא רוצים שה-optimistic
> "יבטל" את הdemotion.

If asked **"מה אם peer מתחבר ועוד לא הספיק לשלוח כלום?"**:

> בגלל זה יש לי `_connect_time` (`peer_connection.py:174`) שמתמלא ב-
> `connect()` (`peer_connection.py:197`). אני משווה את הסף ל-
> `max(_last_piece_time, _connect_time)`, אז peer שזה עתה התחבר מקבל
> את כל ה-60 שניות לשלוח את הבלוק הראשון לפני שמסמנים אותו snubbed.
> בלי זה כל peer חדש היה מסומן snubbed מיד.

If asked **"איך אתה לא רושם log של אותו peer 10 פעמים בדקה?"**:

> יש לי `_previously_snubbed: Set[str]` ב-`Download.__init__`
> (`download_manager.py:146`). בכל cycle אני מחשב diff בין הסט
> הנוכחי לקודם ורושם INFO רק על הפרש החיובי. ה-test
> `test_snubbed_peer_logged_once_per_episode` מאמת שזה רק פעם אחת
> לכל episode של snub.

If asked **"מה ההבדל בין snubbed ל-choking?"**:

> choking זה הצהרה רשמית של ה-peer ("אני לא שולח לך"). snubbing זה
> מצב פסיבי שאני מזהה: הוא אומר שהוא לא choking אבל בפועל לא שולח.
> אי-אפשר לזהות את שניהם באותו אופן — בקוד `is_snubbed` חוזר False
> כש-`peer_choking is True` כי במצב הזה ה-choke decision כבר ידחה
> אותו ממילא; אין מה לחשב.

### How to re-run

```bash
# Just the new snubbing tests
python3 -m pytest \
    python_engine/tests/test_peer_connection.py::TestSnubbing \
    python_engine/tests/test_download_manager.py::TestSnubbingPartition -v

# Full suite (must stay >= 203)
python3 -m pytest python_engine/tests/ -q

# Confirm the partition logic is in the diff
git log book-revision-v2..book-revision-v3 --oneline
git diff book-revision-v2..book-revision-v3 -- \
    python_engine/peer_connection.py python_engine/download_manager.py
```
