# Session — Real Upload Serving + Visible Seeding State

Branch: `claude/quirky-brown-BlKJz`. This document is the complete record
of the work done in this session: what changed, where, why, how, and how
to verify it. Read it as the handoff for anyone (future Claude session or
Adam) picking the branch up.

---

## TL;DR

* **The trigger.** After the book-v4 work added seed-mode tit-for-tat,
  running the app showed no "Seeding" indicator. Investigation found the
  real problem was deeper: **the engine never uploaded at all.**
* **Root cause.** `send_piece` existed but was never called, and incoming
  `REQUEST` messages were silently dropped. So `bytes_uploaded` was always
  zero and seed-mode ranked every peer by an all-zero metric — the exact
  degenerate case it was meant to fix, just with a different zero.
* **The fix (one code commit, `c3e9e53`).** Wired the upload path
  (`REQUEST` → `_serve_block_request` → `send_piece`), made the state flip
  `COMPLETED → SEEDING` visibly, kept connections alive while seeding, and
  added 10 tests (suite **212 → 222 passing**). Java GUI updated to show
  "Seeding" and keep polling logs.
* **Book.** Updated §15.4.4 (seeding), §24 (test count + upload E2E), and
  §25.5 (NAT bullet) via a new reproducible edit pass
  (`edit_upload_seeding.py`).
* **Git note.** The branch `claude/quirky-brown-BlKJz` had never actually
  been pushed to GitHub at the start of the session (the identical commit
  existed only as `book-revision-v4-building`). It is now pushed.

---

## 1. Context — why this work happened

The book-v4 revision (steps 4a/4b/4c in `revision/PLAN.md`) added
sliding-window contribution, snubbing, and **seeding mode** to the
tit-for-tat algorithm, with book section §15.4.4 describing it. When Adam
ran the app and finished a download, the GUI never showed anything like a
"Seeding" status, which is what prompted this session.

Two findings came out of the investigation:

1. **The visible state never changed.** `_complete_download` set the state
   to `COMPLETED` and never moved it. `DownloadState.SEEDING` existed but
   nothing ever assigned it, so the GUI always showed "Completed".
2. **More importantly, there was no upload at all.** `send_piece`
   (`peer_connection.py`) was a complete, correct method — but grep showed
   it had *zero callers* outside its own test. Incoming `REQUEST` messages
   were explicitly ignored: `peer_connection.py` left a
   `pass  # Will be handled by download manager`, and the download
   manager's `_on_peer_message` had no `REQUEST` branch. The client was
   download-only (a pure leecher).

The consequence for seeding: `_seed_mode_unchoke` ranks peers by
`bytes_sent_in_window`, but with `send_piece` never called that value is
permanently zero. Seed mode was sorting every peer by zero — noise, not an
algorithm.

Adam chose (via the in-session questions) to **build real upload, make the
state visibly transition to Seeding, and verify upload with a test.**

---

## 2. Code changes (`python_engine` + `java_gui`)

All in commit `c3e9e53`.

### 2.1 `download_manager.py` — the upload-serving path

| Symbol | What it does | Why |
| --- | --- | --- |
| `BLOCK_SIZE` import | brought in from `peer_connection` | cap servable block size |
| `_on_peer_message` `REQUEST` branch | routes incoming `REQUEST` to the new server method | the branch that was missing |
| `_serve_block_request(conn, msg)` | the upload path: validate + read + `send_piece` | the only caller of `send_piece` |
| `_read_block_sync(piece, begin, length)` | returns the requested bytes from the in-memory piece | feeds `send_piece` off the event loop (executor) |
| `_maybe_enter_seeding()` | flips `COMPLETED → SEEDING` on a choke tick | makes the state visible |
| `_choke_loop` call | calls `_maybe_enter_seeding()` each tick | drives the transition |
| `_keep_alive_loop` condition | now `while RUNNING or _is_seeding()` | keep served connections alive post-completion |

**`_serve_block_request` — how it's safe.** Before touching data it checks,
in order: we are not choking the peer (`conn.am_choking` is False); the
piece index is in range; the requested length is `> 0` and `≤ BLOCK_SIZE`
(anti-abuse — refuses oversized reads); the piece is `COMPLETED`; and
`begin + length` stays inside the piece. Only then does it read the block
(in the thread-pool executor, like disk writes) and `send_piece` it,
incrementing `self.stats.bytes_uploaded`. `PeerConnectionError` is
swallowed (the peer may have vanished mid-serve).

**Why upload now works without inbound connections.** BitTorrent sockets
are symmetric. We still only *dial out* (no `asyncio.start_server`, see the
§25.5 NAT limitation), but a peer we connected to in order to download can
request pieces from us on that same socket. The `REQUEST` handler serves
those. So uploading to already-connected peers works; accepting brand-new
inbound connections still does not.

**Why the SEEDING flip happens on the choke tick, not immediately.** The
GUI fires its completion popup and writes history when it observes the
`"Completed"` state (and the api_server records `state.value` as the
history `final_status`). `_complete_download` keeps the state `COMPLETED`
and fires the completion callback; the flip to `SEEDING` happens on the
next choke tick (≤ `CHOKE_INTERVAL` = 10s later), so "Completed" is shown
first and the popup/history are correct. `_maybe_enter_seeding` is
idempotent.

**Why `_read_block_sync` is memory-only (no disk fallback).** A `COMPLETED`
piece always has its bytes in memory: a live finish fills them via
`submit_block`, and a restore via `_load_state` replays disk bytes into
`piece._data` (`download_manager.py:1130`). So `get_piece_data` never
returns `None` for a `COMPLETED` piece. An early draft had a disk-read
fallback; it was removed as unreachable dead code.

### 2.2 `java_gui/src/TorrentClientGUI.java`

* Log polling now also runs while state is `"Seeding"` (previously only
  Running/Error/Completed), so seeding-time engine logs still surface.
* The completion popup now fires on transition into **either** finished
  state (`Completed` *or* `Seeding`). This is robust even if a fast choke
  tick flips the status straight to `Seeding` inside a 2-second poll
  window — the popup still fires exactly once.

(The Java compiles clean with `javac -cp java_gui/lib/json.jar`.)

---

## 3. Tests (suite 212 → 222)

### 3.1 `tests/test_download_manager.py` — `TestUploadServing` (6)

Unit tests of `_serve_block_request` using a real `PeerConnection` with
`send_message` mocked (so `send_piece`'s real body runs and counters move):

* `test_serves_correct_block_and_counts_upload` — exact PIECE payload,
  `bytes_uploaded` and the upload window all increment.
* `test_serves_partial_block_at_offset` — offset slicing is correct.
* `test_choking_peer_is_not_served` — choke is honored.
* `test_request_for_piece_we_lack_is_ignored` — only `COMPLETED` pieces.
* `test_oversized_request_rejected` — `> BLOCK_SIZE` refused.
* `test_out_of_bounds_request_rejected` — `begin + length` past the piece.

### 3.2 `tests/test_download_manager.py` — `TestSeedingTransition` (3)

* `test_maybe_enter_seeding_flips_completed_to_seeding` (+ idempotent).
* `test_maybe_enter_seeding_noop_while_running`.
* `test_maybe_enter_seeding_noop_when_incomplete`.

### 3.3 `tests/test_e2e_peer.py` — `test_seeder_serves_block_to_requesting_peer` (1)

The convincing one: a **live loopback socket**. A minimal inline leecher
connects to our `Download`-wired `PeerConnection`, sends `INTERESTED` +
`REQUEST`, and asserts it receives the **exact source bytes** back, with
`bytes_uploaded` / per-peer / upload-window all incremented. This proves
`send_piece` actually fires and real bytes cross the wire.

Run them:

```bash
python -m pytest python_engine/tests/ -q                       # full suite (222)
python -m pytest python_engine/tests/test_e2e_peer.py -q        # E2E incl. upload
python -m pytest python_engine/tests/test_download_manager.py::TestUploadServing -v
```

---

## 4. Book updates

Edited the working book `revision/book-v2/ספר פרוייקט אדם זבולון.docx`
through the existing reproducible tooling — **not** by hand. A new pass
`revision/book-v2/_tools/edit_upload_seeding.py` was added and wired into
`apply_all.py` as the final pass. Re-running `apply_all.py` rebuilds the
whole book from the pristine `docs/` source through every pass, so these
edits survive regeneration.

Sections changed:

* **§15.4.4 (מצב Seeding).** Rewrote the implementation paragraph; inserted
  two new paragraphs — *"נתיב ההעלאה עצמו"* (the `REQUEST` →
  `_serve_block_request` → `send_piece` path) and *"מצב גלוי למשתמש"* (the
  `COMPLETED → SEEDING` transition + keep-alive); rewrote the pain-point
  paragraph to the **real** pain point found this session (`send_piece` was
  dead code, `REQUEST` was dropped, the metric was all-zeros until the path
  was wired); updated the code-locations list.
* **§24 (בדיקות).** Unit-test count `212 → 222`; added a sentence on the
  upload E2E (`test_seeder_serves_block_to_requesting_peer`) as proof the
  client uploads in practice.
* **§25.5 (limitations).** Refined the NAT bullet: uploading to already-
  connected (outbound) peers **does** work; only accepting new inbound
  connections does not.

Regenerate + verify:

```bash
python revision/book-v2/_tools/apply_all.py        # rebuilds the .docx; prints OK
python revision/book-v2/_tools/structure_map.py    # refresh STRUCTURE_MAP.md
```

`apply_all.py` asserts every non-`document.xml` part stays byte-identical
(images, fonts, styles untouched), and refuses to write if a pass touches
the off-limits proposal area (body idx < 305). This pass touches none of
that — it locates paragraphs in the live tree by text, since they are
created by earlier passes (§15.4.4 does not exist in the pristine source).

---

## 5. Oral-exam prep (likely questions)

**"מה קורה כשההורדה מסתיימת — איך רואים שאתה seeder?"**
> סיום ההורדה מסמן את ה-state כ-`COMPLETED`, וב-choke tick הבא
> `_maybe_enter_seeding` מקדם אותו ל-`SEEDING`, כך שה-GUI מציג "Seeding".
> במצב הזה `_seed_mode_unchoke` ממיין peers לפי `bytes_sent_in_window` —
> כמה אני מעלה אליהם.

**"איך אתה בכלל מעלה אם אתה לא מקבל חיבורים נכנסים?"**
> חיבור TCP ב-BitTorrent הוא דו-כיווני. גם אם אני יזמתי את החיבור כדי
> להוריד, ה-peer בצד השני יכול לשלוח לי `REQUEST` על אותו socket. הטיפול
> ב-`REQUEST` ב-`_on_peer_message` מנתב ל-`_serve_block_request` ששולח
> את ה-block ב-`send_piece`. מה שאין זה `start_server` שמקבל חיבורים
> *חדשים* — זו המגבלה ב-§25.5.

**"מה הייתה נקודת הכאב פה?"**
> ה-seed-mode והמדד `bytes_sent_in_window` היו כתובים, אבל `send_piece`
> לא נקרא מעולם — הודעת `REQUEST` נזרקה בשקט. אז `bytes_uploaded` היה
> אפס תמיד וה-seed-mode מיין הכול לפי אפס. רק חיווט ה-`REQUEST` ל-
> `_serve_block_request` הפך את ההעלאה לאמיתית.

**"איך אתה מוכיח שזה באמת מעלה ולא רק מספרים?"**
> ב-`test_seeder_serves_block_to_requesting_peer` peer אמיתי על socket
> loopback מבקש block ומקבל בדיוק את ה-bytes של המקור בחזרה, ו-
> `bytes_uploaded` עולה. זו ראיה end-to-end, לא mock של המספר.

---

## 6. Files touched this session

```
python_engine/download_manager.py              (+ upload path, seeding flip)
python_engine/tests/test_download_manager.py   (+ 9 tests)
python_engine/tests/test_e2e_peer.py           (+ 1 socket upload test)
java_gui/src/TorrentClientGUI.java             (seeding state in GUI)
revision/book-v2/_tools/edit_upload_seeding.py (NEW book pass)
revision/book-v2/_tools/apply_all.py           (wire the new pass)
revision/book-v2/ספר פרוייקט אדם זבולון.docx   (regenerated)
revision/book-v2/STRUCTURE_MAP.md              (regenerated)
revision/SESSION_REAL_UPLOAD_AND_SEEDING.md    (this file)
```

## 7. Commits on this branch this session

* `c3e9e53` — download_manager: serve block REQUESTs (real upload) +
  visible seeding state (code + tests + Java GUI).
* (book + this doc) — committed separately; see `git log`.
