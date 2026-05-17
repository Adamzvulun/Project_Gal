# Progress — Step 3

Branch: `book-revision-v2` · Commit: (see git log after push).

This step closes the auto‑resume gap that the book's own chapter 25
admitted: `_save_state` existed, `_load_state` did not, so a paused
download could not survive a process restart. After this step,
restarting the engine scans `data/state/*.json`, reconstructs the
`Download` objects, re‑verifies each previously COMPLETED piece
against the bytes still on disk, and seats the downloads in PAUSED
state ready for the user to resume.

For each step:

* **Why** — which sentence of the teacher's critique this fixes.
* **What** — the deliverables.
* **How** — the design decisions and the reasons for each.
* **Where** — file paths and key line numbers.
* **Result** — what's measurable now that wasn't before.
* **Oral exam prep** — what to say if the examiner asks about this.

---

## STEP 3 — `_load_state` (resume across process restarts)

### Why

Chapter 25 of the book, in the "what didn't work" section, names this
gap verbatim:

> "שחזור אוטומטי לאחר crash לא מומש — `_save_state` כותב את ה‑state
> אבל אין `_load_state` שמטעין אותו בעת startup."

The teacher quoted that admission as evidence the project is "מנופח"
— promising features it doesn't deliver. Closing the gap is ~150
lines of code and turns an admitted failure into a working,
test‑backed feature. The book §25 update (step 5) will move
auto‑resume from "what didn't work" to "what works", and the §25.5
honest‑limitations chapter will no longer need to list it.

### What

* `Download.from_state_file(state_file)` — a classmethod factory that
  reads `{id}.json`, the sidecar `{id}.torrent`, and re‑verifies each
  COMPLETED piece against the bytes on disk.
* `_save_state` extended to write a sidecar `{id}.torrent` alongside
  the JSON, plus three new JSON fields (`download_dir`,
  `piece_algorithm`, `peer_algorithm`) needed to reconstruct the
  Download.
* `DownloadManager.restore_state()` — scans `state_dir/*.json` on
  startup and reconstructs each `Download`.
* `api_server.get_manager()` calls `restore_state()` immediately
  after constructing the manager.
* Nine new tests in `test_download_manager.py` exercising the
  round‑trip, the COMPLETED → COMPLETED preservation, corrupt JSON,
  missing sidecar, on‑disk bytes mismatch, `info_hash` mismatch,
  manager scan, empty‑dir, and corrupt‑file‑skip paths.

Total tests: **185 passing** (up from 176).

### How — design decisions

#### 1. Sidecar `.torrent` over a `torrent_path` field

The original plan was to record the `.torrent` file's absolute path
in the JSON. That breaks for any download that came in via
`POST /torrents` file upload (the API server reads the bytes
straight into `TorrentMetadata(torrent_data=...)` — there is no
path on disk to reference).

Instead, `_save_state` re‑encodes `self.torrent._metadata` via the
engine's own `bencode.encode` and writes the bytes to
`{state_dir}/{id}.torrent`. This means:

* Restore works for both upload‑ and path‑based downloads, with no
  plumbing changes to the API surface.
* The re‑encoded `.torrent` has the same `info_hash` as the
  original (the bencode encoder is canonical and the info dict
  re‑encodes byte‑identically; this is the same property the engine
  already relies on at `torrent_metadata.py:101-102`).
* No new fields on `Download.__init__`; no breakage of the existing
  tests or the API server's add‑torrent flow.

We do still write `download_dir`, `piece_algorithm`, and
`peer_algorithm` into the JSON, because those are constructor
arguments that aren't recoverable from the `.torrent` bytes.

#### 2. Re‑verify pieces from disk instead of trusting the JSON

The JSON's `piece_status` array is a strong hint, not the truth. The
file on disk may have been modified, partially deleted, or replaced
between sessions. So for every piece the JSON claims is COMPLETED,
`from_state_file`:

1. Walks `torrent.get_file_offset(idx)` to find the file slices the
   piece spans.
2. Reads those bytes from `download_dir`.
3. Pastes them into `piece._data`.
4. Calls the existing `piece.verify_hash()` — exact same SHA‑1
   check the network path uses.
5. Only if it passes, marks `piece.status = COMPLETED` and flips
   every `block.received = True` so `piece.is_complete` returns
   True.

Pieces that fail re‑verification (or whose bytes are unreadable)
fall back to MISSING. A single corrupt piece does not invalidate
the rest — the download just resumes with that piece needing
re‑download. This is the correct, defensive behaviour.

#### 3. Force PAUSED on restore (except when saved as COMPLETED)

The PLAN.md policy and the user explicitly confirmed: a restored
download lands in PAUSED state and waits for the user to resume.
Auto‑resuming on app start would surprise the user and could
silently consume bandwidth. The one exception is downloads that
were already COMPLETED when the engine crashed — those stay
COMPLETED so the GUI shows them correctly.

#### 4. Preserve the original `id` across restore

Without this, the restored Download would generate a fresh UUID on
construction, and the next `_save_state` would write a *second*
JSON file (with the new id) while leaving the old one behind to be
loaded again next startup — a duplicate ghost. So
`from_state_file` overrides `dl.id` with `data["torrentId"]` after
construction.

#### 5. Defensive failure modes — never crash startup

`get_manager()` is called on the first API request. If a stale or
corrupt state file blew up the loop, the whole API would fail to
serve. So `from_state_file` catches every expected exception
(`FileNotFoundError`, `JSONDecodeError`, `OSError`, `ValueError`,
parse errors from `TorrentMetadata`), logs a warning, and returns
`None`. `restore_state()` skips Nones and keeps scanning. The 22
test cases include three explicit "broken input" paths to lock
this in.

### Where — files

| Path | Lines | Purpose |
| --- | ---: | --- |
| `python_engine/download_manager.py` | +138 | `Download.from_state_file`, sidecar write in `_save_state`, three new JSON fields, `DownloadManager.restore_state` |
| `python_engine/api_server.py` | +3 | Call `_manager.restore_state()` in `get_manager()` |
| `python_engine/tests/test_download_manager.py` | +200 | 9 new tests covering round‑trip, COMPLETED preservation, 5 failure paths, manager scan, empty/corrupt scans |

### Result — what's measurable now

* `pytest python_engine/tests/ -q` → **185 passed** (was 176).
* Restart workflow: `_save_state` now produces `{id}.json` *and*
  `{id}.torrent` under `data/state/`. On engine startup,
  `restore_state` walks them, reconstructs every Download in PAUSED
  state, and the user can call `/torrents/{id}/resume` to continue.
* `api_server.get_manager()` logs `[engine] restored N download(s) from data/state`.
* The book's chapter‑25 admission ("`_load_state` לא קיים") is now
  factually false — to be edited out in step 5.

### Oral exam prep — Step 3

If asked **"איך התוכנה שורדת crash או הפעלה מחדש?"**:

> Two artefacts persist per download under `data/state/`: a JSON
> snapshot (`{id}.json`) and a sidecar `.torrent` file
> (`{id}.torrent`). On startup, `DownloadManager.restore_state()` —
> wired into `api_server.get_manager()` — scans the directory. For
> each pair, `Download.from_state_file` rebuilds the
> `TorrentMetadata` from the sidecar, reconstructs the `Download`,
> and re‑verifies each piece the JSON claims is COMPLETED by
> reading its bytes back from disk and running the same
> `Piece.verify_hash()` SHA‑1 check the network path uses.
> Verified pieces are marked COMPLETED; failed pieces fall back to
> MISSING. The restored download is left in PAUSED state — the
> user has to explicitly resume.

If asked **"למה לא לסמוך פשוט על מה ש‑JSON אומר?"**:

> Because the JSON is a hint about what was true when the engine
> last wrote state, not the truth about what's on disk now. The
> file may have been modified, partially deleted, or replaced
> between sessions. Re‑hashing every piece we plan to claim as
> COMPLETED costs O(file size) once at startup, but it's the only
> honest way to know the bytes match the torrent. The same check
> the BitTorrent protocol does at every piece receive.

If asked **"מה קורה אם piece אחד נכשל בבדיקה?"**:

> That single piece is reset to MISSING. The rest of the download
> is unaffected; when the user resumes, the engine will re‑request
> just that piece from peers. There's no all‑or‑nothing failure
> mode.

If asked **"איך זה עובד אם ה‑.torrent המקורי כבר לא קיים?"**:

> `_save_state` writes a sidecar `{id}.torrent` next to the JSON,
> using `bencode.encode` to re‑serialise the parsed metadata. The
> info dict re‑encodes byte‑identically (canonical bencode), so the
> `info_hash` round‑trips. `from_state_file` reads the sidecar,
> not the original path — so the original .torrent can be deleted,
> moved, or never have existed on disk at all (e.g. file‑upload
> case in the API).

If asked **"למה PAUSED ולא RUNNING אוטומטית?"**:

> Two reasons. First, surprise minimisation — auto‑resuming
> consumes bandwidth and connects to peers without the user asking
> for it. Second, the saved state may itself be from a crash, not a
> clean shutdown; making the user resume forces them to glance at
> the GUI and notice anything wrong. The exception is downloads
> that were COMPLETED when state was last saved — those stay
> COMPLETED so the history view is correct.

### How to re‑run

```bash
# Just the new tests
python3 -m pytest python_engine/tests/test_download_manager.py -v \
  -k "load_state or restore_state"

# Full suite (must stay green)
python3 -m pytest python_engine/tests/ -q

# Manual smoke
python3 -m python_engine.api_server  # observe "[engine] restored 0 download(s)..."
```
