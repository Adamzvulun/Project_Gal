# Changelog — Everything Done Since the Project Book Was Submitted

**Purpose.** A single chronological record of all work done *after* the project
book was submitted and assessed, so both Adam and any future session can see
what changed, why, how, and where — without re-reading every progress doc.

**Scope.** Two branches:

| Branch | What it holds |
| --- | --- |
| `claude/quirky-brown-BlKJz` (the "previous" branch) | All revision work up to and including the real-upload/seeding session (commits `91446dd` → `98cb310`). |
| `claude/adoring-dijkstra-uOMhd` (current) | Same history, plus the restart-cleanup + Delete-button work (`19bddca`, `abdbcb5`). |

The two branches share identical history through `98cb310`; the current branch
is simply two commits ahead.

**Where the deeper detail lives.** Each phase below points at the matching
`revision/PROGRESS_STEP_*.md`, `revision/PLAN.md`, or
`revision/SESSION_*.md` doc, which carry the file:line specifics. This file is
the index/timeline over those.

---

## Background — why any of this happened

The project book (`docs/ספר פרוייקט אדם זבולון.docx`) was submitted and the
teacher returned **43/150**, accusing it of being LLM-generated and inflated.
The full critique is distilled in `revision/ASSESSMENT_SUMMARY.md`. The single
most damaging point: **Chapter 24 admitted the empirical experiments were never
run** (`"הניסויים האמפיריים לא בוצעו"`), which crushed the יעילות score and
poisoned credibility everywhere.

A code audit (`revision/CODE_AUDIT.md`) showed the engine was actually
substantive — the problem was dishonest/inflated *documentation* plus a few
genuinely missing pieces. The rescue strategy (`revision/PLAN.md`): document
honestly, run the promised experiments, fix the one broken claim (resume), add
a real end-to-end test, and deepen the algorithm chapters so Adam can defend
them orally. Everything below executes that plan.

> Note: commits before `91446dd` (the May-14 batch: pandoc book build, the
> `docs/Fig-*` Mermaid diagrams, trims/polish) are the *original* book
> authoring, i.e. pre-assessment. They are not part of this changelog.

---

## Phase 0 — Assessment & planning · 2026-05-17 · `91446dd`

**What.** Created the `revision/` folder with the planning artifacts:
`PLAN.md` (the full rescue plan, ordered by score-per-hour), `ASSESSMENT_SUMMARY.md`
(1-page distillation of the 18-page teacher PDF), and `CODE_AUDIT.md`
(file:line proof of what the engine really implements).

**Why.** So the work was driven by an explicit, prioritized plan, and so any
future session could reload context without re-reading the PDF or re-auditing
the code.

**Where.** `revision/PLAN.md`, `revision/ASSESSMENT_SUMMARY.md`,
`revision/CODE_AUDIT.md`.

---

## Phase 1 — Run the missing experiments · 2026-05-17 · `690454e`

**What.** Built an experiment harness and actually ran the rarest-first-vs-random
comparison the book had only promised, committing the raw CSV evidence.

**How.** A self-contained synthetic swarm on loopback (chosen for
*reproducibility* — a public swarm's seeder count/bandwidth varies run-to-run
and swamps the algorithmic signal):
- `make_torrent.py` generates a 1 MB / 16-piece file from a fixed seed.
- `mock_swarm.py` runs an aiohttp tracker + four BEP-3 mock peers, with
  deliberately *non-uniform* piece availability (one `full` peer holds all 16;
  three `low_*` peers hold only pieces 0–7, so 8–15 are genuinely rarest).
- `run_comparison.py` runs 5 independent runs per algorithm (10 total) and
  dumps three CSVs.

**Result.** `data/experiments/comparison_summary.csv` (10 rows),
`comparison_peers.csv` (40 rows), `comparison_timeline.csv` (160 rows), plus a
methodology `README.md`. Rarest-first deterministically routes the rare-half
requests to the `full` peer (it serves exactly 512 KB = 8×64 KB).

**Why.** Directly answers the teacher's most damaging point and converts
יעילות from an admitted gap into measured evidence.

**Where.** `python_engine/experiments/*`, `data/experiments/*`.

---

## Phase 2 — End-to-end Peer Wire Protocol test · 2026-05-17 · `79ea365`, `ac5a279`, `6b96fa2`, `1a4602a`

**What.** Added a live-socket E2E test that exercises the whole BEP-3 stack at
once, then documented Phases 1–2 and wrote a handoff for the remaining steps.

**How.** `test_e2e_peer.py` spins up an `asyncio` mock peer on a loopback
socket that performs handshake → bitfield → unchoke → piece; the real
`PeerConnection` drives it: 68-byte handshake, length-prefix framing, request,
piece reception, and SHA-1 verification — all over a real socket.

**Why.** The assessment flagged that *no* test proved the wire protocol end to
end. This single test backs the entire "we implemented BEP-3" claim.

**Where.** `python_engine/tests/test_e2e_peer.py`;
`revision/PROGRESS_STEP_1_AND_2.md`, `revision/HANDOFF1&2.md`.

---

## Phase 3 — Honor the resume claim (`_load_state`) · 2026-05-17 · `67e05a7`, `7a06dfc`

**What.** Implemented download resume, which the book's own ch.25 had admitted
was broken (`_save_state` existed; `_load_state` did not).

**How.** `Download.from_state_file()` rebuilds a download from its saved JSON +
a sidecar `.torrent`, re-reads each COMPLETED piece's bytes from disk and
**re-verifies SHA-1** before trusting it (corrupt/unreadable pieces fall back
to MISSING). `DownloadManager.restore_state()` scans `data/state/*.json` on
startup and reconstructs downloads in PAUSED state — the user explicitly
resumes; we never auto-start the network loop. Wired into `api_server` startup.

**Why.** Turns an openly admitted failure into a working, tested feature.

**Where.** `python_engine/download_manager.py`, `api_server.py`,
`tests/test_download_manager.py`; `revision/PROGRESS_STEP_3.md`.

---

## Phase 4a — Tit-for-tat: sliding-window contribution · 2026-05-17 · `c14ad8b`, `ddd54b6`

**What.** Replaced the cumulative `bytes_downloaded` ranking metric with a
proper 20-second sliding window.

**How.** In `peer_connection.py`, contributions are tracked as a deque of
`(timestamp, bytes)` samples; `bytes_received_in_window(20.0)` sums recent
samples and lazily evicts old ones. `_tit_for_tat_unchoke` now ranks by the
windowed value.

**Why.** With a cumulative counter, a peer that contributed early and then went
silent keeps a high score forever — the unchoke set never reflects *current*
behavior. The window fixes that. (Choke interval stays 10s so two cycles fit
inside the 20s window and the metric is stable.)

**Where.** `python_engine/peer_connection.py`, `download_manager.py`, +tests in
`test_peer_connection.py` / `test_download_manager.py`;
`revision/PROGRESS_STEP_4A.md`.

---

## Phase 4b — Tit-for-tat: snubbing · 2026-05-18 · `8cb8c70`, `379fe8f`, `b4ff343`

**What.** Detect and de-prioritize peers that unchoke us but stop sending.

**How.** `PeerConnection.is_snubbed(threshold=60s)` is true when the peer is
*not* choking us (they should be feeding us), we've requested from them, but no
block has arrived in >60s. `_tit_for_tat_unchoke` partitions peers into
non-snubbed/snubbed, ranks non-snubbed by the sliding window, and only falls
back to snubbed peers if there aren't enough candidates.

**Why.** Without it, a buggy or malicious peer can unchoke us, never send, and
permanently lock an unchoke slot.

**Where.** `python_engine/peer_connection.py`, `download_manager.py`, +tests;
`revision/PROGRESS_STEP_4B.md`.

---

## Phase 4c — Tit-for-tat: seeding mode · 2026-05-18 · `16a4cf3`, `31b2a5b`, `0036342`

**What.** A distinct unchoke policy for when the download is complete.

**How.** Mirror sliding window for *uploads* (`bytes_sent_in_window`). Added
`DownloadState.SEEDING` and an `_is_seeding()` check; in seed mode the unchoke
branch ranks peers by how fast we upload *to* them, not download from them.

**Why.** Tit-for-tat is a *leecher's* algorithm. Once complete, the download
metric is permanently zero so every peer ties — the ranking degenerates to
noise. Seeding asks the right question instead: "who can I feed fastest?"

**Where.** `python_engine/download_manager.py`, `peer_connection.py`, +tests;
`revision/PROGRESS_STEP_4C.md`.

> ⚠️ Caveat discovered later (Phase 6): the seed metric was still always zero
> here because the upload path itself was never wired. Fixed in Phase 6.

---

## Phase 5 — Rewrite the book (book-v2) · 2026-05-18 · `6a13fc0` … `adaee6e`

**What.** Produced the revised book under `revision/book-v2/`, applying every
content fix from `PLAN.md` §4.

**How.** Built reproducible editing tooling (`revision/book-v2/_tools/`):
`apply_all.py` rebuilds the `.docx` from the pristine `docs/` source through a
chain of passes, asserting every non-`document.xml` part (images, fonts,
styles) stays byte-identical and refusing to touch the locked proposal area.
Edits include: §24 real empirical numbers + results table + the mock-peer E2E
mention; §25/§26 closing the auto-resume admission; deeper handshake/framing,
bencode/info_hash, rarest-first (thundering-herd pain story), and tit-for-tat
(window/snubbing/seeding) sections; tone fixes ("developed"→"implemented");
an honest §25.5 limitations list; and a fix for scrambled ASCII diagrams
(forced LTR).

**Why.** Make every claim honest and traceable to a file:line Adam can point
at in the oral — the core of the rescue.

**Where.** `revision/book-v2/ספר פרוייקט אדם זבולון.docx` (the current book),
`revision/book-v2/_tools/*`, `revision/book-v2/STRUCTURE_MAP.md`.

> The top-level `book/` folder is the **old** pre-revision book and is now
> superseded by `revision/book-v2/`.

---

## Phase 6 — Real upload serving + visible Seeding · 2026-05-28 · `c3e9e53`, `98cb310`  ⟶ *previous branch (quirky-brown)*

**What.** Made the client actually upload, and made the Seeding state visible
in the GUI.

**Why (the trigger).** Running the app after Phase 4c, finishing a download
showed no "Seeding" indicator. Investigation found a deeper bug: **the engine
never uploaded at all.** `send_piece` existed but had zero callers, and
incoming `REQUEST` messages were silently dropped — so `bytes_uploaded` was
always zero and seed mode (Phase 4c) was ranking every peer by an all-zero
metric, the exact degenerate case it was meant to fix.

**How.** Wired the upload path `REQUEST → _serve_block_request → send_piece`
(with bounds/choke/size guards; block read off the event loop). Made the state
flip `COMPLETED → SEEDING` on the next choke tick (so the completion popup and
history still fire on "Completed" first), and kept connections alive while
seeding. The Java GUI now shows "Seeding" and keeps polling logs. Suite grew
**212 → 222**, including a live-loopback test proving real source bytes cross
the wire on upload. Book §15.4.4/§24/§25.5 updated via a new reproducible pass.

**Where.** `python_engine/download_manager.py`, `tests/test_download_manager.py`,
`tests/test_e2e_peer.py`, `java_gui/src/TorrentClientGUI.java`,
`revision/book-v2/_tools/edit_upload_seeding.py` + regenerated docx;
full writeup in `revision/SESSION_REAL_UPLOAD_AND_SEEDING.md`.

---

## Phase 7 — Restart cleanup + Delete button · 2026-05-29 · `19bddca`, `abdbcb5`  ⟶ *current branch (adoring-dijkstra)*

**What.** (1) Finished/cancelled downloads no longer reappear after the app is
reopened. (2) A Delete button removes a selected row from the list.

**Why.** A completed download persisted its state as `Completed`, and
`restore_state()` rebuilt *every* saved download on startup — so finished
downloads kept coming back as paused rows. There was also no way to clear a row
without deleting the file.

**How.**
- `restore_state()` now **skips** downloads whose saved state is `COMPLETED`,
  `SEEDING`, or `CANCELLED`, and deletes their state files (the downloaded file
  on disk is kept). This required teaching `from_state_file` to **preserve**
  those terminal states instead of collapsing everything non-COMPLETED to
  PAUSED (otherwise a cancelled download came back as PAUSED and slipped the
  check). In-progress/paused downloads still restore normally.
- New `DownloadManager.remove_download(id)` stops the download if active, drops
  it from the manager, and deletes its state files — exposed via
  `DELETE /torrents/<id>`. A **Delete** button in the GUI (with confirm dialog,
  "the downloaded file on disk will be kept") calls it and refreshes. Because
  the table is rebuilt from the server every 500ms, deletion has to go through
  the backend or the row would snap back on the next poll.

**Result.** Suite **222 → 226** (4 new tests: skip-finished, skip-cancelled,
remove-deletes-state-keeps-file, remove-unknown-returns-false).

**Where.** `python_engine/download_manager.py`, `api_server.py`,
`tests/test_download_manager.py`, `java_gui/src/ApiService.java`,
`java_gui/src/TorrentClientGUI.java`.

---

## Test-count trail

| Milestone | Tests |
| --- | --- |
| Baseline at submission (book undercounted as 160) | 172 |
| After Phase 6 (real upload + seeding) | 222 |
| After Phase 7 (restart cleanup + delete) | 226 |

Run them with: `python -m pytest python_engine/tests/ -q`

## Current state (as of 2026-05-29)

- Current book: `revision/book-v2/ספר פרוייקט אדם זבולון.docx` (regenerable via
  `revision/book-v2/_tools/apply_all.py`).
- Engine: real download **and** upload, sliding-window + snubbing + seeding
  tit-for-tat, resume-from-state, finished/cancelled rows auto-dropped on
  restart, GUI Delete button.
- 226 tests passing; committed experiment CSVs under `data/experiments/`.
