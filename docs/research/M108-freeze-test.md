# M108 — the freeze registry, made machine-checked

**Commission.** M106's verifier closed with a sentence that is the whole of this
milestone:

> *"No test exists that pins any freeze hash. Every freeze in this project is
> enforced by prose in a report, not by CI — an untested freeze is an unverified
> freeze."*

**What landed.** Three new files, all uncontended, all under
`crates/strehl-cli/tests/`:

| file | size | what it is |
|---|---|---|
| `byte-freezes.tsv` | 4 742 B, 50 lines | the registry. Data, not prose. 13 columns, 2 rows. |
| `byte-freeze.rs` | 60 723 B, 1 453 lines | four tests that read the registry and check it. |
| `data/coffee-bean-20.warpmap.txt` | 3 171 B | committed warp fixture, sha `EF745413…93B3`. |

`cargo test -p strehl-cli --test byte-freeze` — 4 tests, **17.0 s** in release
on the reference rig, both freezes holding, each reproduced twice in separate
processes.

Three gates run before any hash is compared — isolation, placement and
determinism (§1.3) — because a hash from the wrong pipeline is not weak
evidence, it is evidence about something else.

---

## 1. The mechanism, and the argument for it

The brief invited me to argue for a different instrument if a hash-equality
assertion was the wrong one. **I kept hash equality, and changed what it is
attached to.** The reasoning:

The two defects M106 found are not the same defect.

* **Defect 1 — the stale freeze.** M85's hash broke at `885e9f7` and nobody
  noticed for weeks. This one *is* cured by an assertion. Nothing weaker
  notices; a "warn if it moved" check is a log line nobody reads.
* **Defect 2 — the splice.** Three milestones froze three different
  invocations, none recorded its full command, and a later dispatch combined
  M85's `--gate 2` with M100's `--limit 60` to produce a fourth invocation
  nobody had ever frozen. That cost a 1.9-hour investigation into a regression
  that had not happened (SYNTHESIS fact 1379). **An assertion does not cure
  this at all** — the assertion would have been perfectly green while the prose
  around it was fabricating a comparison.

So the load-bearing design decision is not the assertion. It is this:

> **The test builds the command out of the registry row.**

`Freeze::argv`, `Freeze::env` and `Freeze::command` are the *only* place a
frozen invocation exists. There is no second copy in a report to drift away
from the first. A hash cannot be compared against a command other than the one
it was measured under, and one milestone's flag cannot be spliced onto another
milestone's command, because neither the flag nor the command is written down
anywhere a human could recombine them. The failure message then prints that
generated command — so the reader who hits a red test is handed the *right*
reproduction rather than reconstructing one, which is precisely the step that
went wrong last time.

`--gate` is mandatory and **`default` is a rejected value** in the gate column.
`DEFAULT_GATE` at `crates/strehl-core/src/merge.rs:297` is `4.0` today and was
not always; recording "we used the default" records nothing.

### 1.1 Why two rows, not one

The registry holds the same stack, limit and gate under **two alignment
modes**, and `no_two_rows_freeze_the_same_invocation` asserts their hashes must
*differ*:

| row | align | sha256 | bytes |
|---|---|---|---|
| `coffee-bean-20-gate2-unaligned` | `off` | `D99F5D82…76CA` | 49 449 626 |
| `coffee-bean-20-gate2-sidecar` | `sidecar:coffee-bean-20.warpmap.txt` | `119936E6…D709` | 49 449 626 |

They differ only in registration, which gives the pair **discriminating
power**: if only the sidecar row moves, warp application changed; if both move,
the merge core did. That distinction is the M86c watershed itself — the
alignment wiring that broke M85's freeze — and a single row cannot express it.

### 1.2 What is asserted, and what is only reported

Deliberately asymmetric, because a freeze that fires on noise gets deleted:

* **Asserted:** sha256; byte count; the coarse alignment mode token
  (`off` / `on-solved` / `on-sidecar-override`) parsed from stderr; the placed
  and refused counts for aligned rows; agreement between two independent
  renders; the stack directory's entry-*name* set before and after each render.
* **Reported only:** the `workers … : N chunks of <= M frames` fingerprint.
  That is a property of the measuring host (RAM and core count), the merge
  reduces in a chunk tree, and f32 addition is not associative — so on a
  different machine it is the **first suspect** when a hash moves, but it is
  not itself a defect. Also reported, never asserted: any stray sidecar found
    in the capture library (§1.7).

The alignment mode is asserted at a coarse token, not the full log line,
because the full line carries prose that later milestones will reword. A freeze
that fires on a reworded sentence teaches its readers to ignore it.

Entry *names* are compared, not mtimes: several agents share this machine, and
another process rewriting a file it owns is not evidence about this test —
whereas a **new file appearing** is (see §3.3).

### 1.3 Three gates run *before* any hash is compared

A hash is only evidence about the pipeline the row describes. If the tool did
not run that pipeline, comparing hashes is not a weak check — it is a check of
something else, and it will be green or red for reasons unrelated to the
freeze. So the hash comparison is the *last* thing that happens.

**Gate 1 — isolation, read from the tool's own output.** `strehl stack` prints
an `alignment :` line stating which pipeline it ran. The row records what that
line must say, and a mismatch fails with `ENVIRONMENT NOT ISOLATED` and
**no hash comparison at all**. `MISSING` — no such line found — is also a
failure, with a message saying the check has gone blind and must be repaired
rather than removed.

This gate is not hypothetical. Under the previous single-gate design, a run
that lost its `STREHL_WARPMAP` would have rendered `D99F5D82…` — a hash that
*is* in the registry, for the other row — and been reported as a moved freeze.
Verified as Check D (§2.4).

**Gate 2 — placement.** The same line carries `N placed / M refused`. For
aligned rows the test requires `placed == --limit` and `refused == 0`, both
**derived from the row rather than recorded in it**, so they cannot be
re-baselined into agreement with a bad sidecar by the same hand that edits a
hash.

This matters because `StackIdentity::from_paths` digests filename and file
**length** only (`warpmap.rs:238`), never content. `load_or_solve` does compare
`map.len() == paths.len()`, so an 8-frame sidecar under a `--limit 20` run is
caught — but an 8-frame sidecar under a `--limit 8` run is accepted **silently**
even if it came from a different reference frame, a different subset or a
different resampler.

**I must be precise about what this gate currently buys, because overclaiming
is the failure this milestone exists to stop.** I planted a refused frame in a
copy of the fixture and measured what actually happens: the tool reports
`19 placed / 1 refused` and then **exits 1**, because `merge_cmd.rs:932` bails
on a refused frame rather than giving it identity. So on today's code
`placed == limit && refused == 0` is *implied by the run succeeding* and cannot
fail where the exit-code check would not have failed first.

It is kept anyway, as a **tripwire on that guarantee**. "Warn and skip the bad
frame instead of failing the whole render" is an obvious, well-meant change for
somebody to make; the moment it lands, the exit code stops carrying this
information and a short placement goes silent. This assertion is what would
notice, it costs one line, and both the code comment and the failure message
say so explicitly rather than implying a strength the check does not yet have.
The run-failure message was also changed to print the placement line, because
in the planted case that line *is* the diagnosis (Check E, §2.5).

**Gate 3 — determinism.** Every row is rendered **twice, in two separate
processes**, and the two must agree with each other before either is compared
to the registry. This splits two failures a single render conflates:

* the two passes disagree → `NOT DETERMINISTIC`, a distinct and louder message
  that says *do not re-baseline anything*, because a freeze on a
  non-deterministic pipeline is a coin toss that will be red for one person in
  two and deleted by the third;
* the two passes agree but differ from the registry → the ordinary
  `BYTE-FREEZE MOVED`, which is what the test is for.

**Measured result: both rows reproduce byte-identically across two separate
processes.** Suite time roughly doubles, 8.5 s → 17.0 s, which is the whole
cost. Verified in the planted case too: the byte-moving change produced two
*mutually agreeing* wrong hashes and was correctly reported as moved rather
than as nondeterminism (§2.2).

### 1.4 Hermeticity — the crux

The capture library is read-only and irreplaceable. Every row runs in one of
exactly two modes, both of which write nothing near the captures:

* **`align = off`** → `STREHL_ALIGN=0`. `align_cmd::align_enabled()` returns
  false and `load_or_solve` returns *before a sidecar path is even computed*.
  This is hermetic **at every commit**, whichever agent's aligner happens to be
  in the tree.
* **`align = sidecar:F`** → `STREHL_WARPMAP` pointed at a committed fixture.
  Documented at `merge_cmd.rs:1035`: when that variable is set nothing is
  written anywhere, the sidecar is hard-validated against the bracket (stack
  identity *and* frame count), and a mismatch is a **refusal** rather than a
  silent re-solve.

**`align = solve` is rejected by the validator with an explanatory panic**, and
that is a decision rather than an omission. When these rows were measured at
`fea1a72` it would have written `<stackdir>/warpmap.txt` into the read-only
library on every run. M85's repair landed at `dccaea8` *while this milestone was
in flight*, so the hard objection is gone; the remaining one is softer and still
sufficient — a solving row freezes the **solver**, which two milestones were
actively rewriting on the day this was written, and a freeze that moves every
week is a freeze that gets deleted. The panic text says in as many words that
this should be **revisited, not inherited**.

Before every render the test `env_remove`s all five `STREHL_*` variables that
change output (`STREHL_ALIGN`, `STREHL_WARPMAP`, `STREHL_CACHE_DIR`,
`STREHL_FIX_HALO`, `STREHL_FIX_HALO_DELTA`) and then applies only the row's own
settings, so an inherited shell variable cannot silently rebase a hash.

### 1.5 Skip, and the CI switch

The render arm needs `D:\personal\macro`, which is one machine's local data.
Without it the test **skips loudly and exits 0** — a test that fails on a fresh
clone is a test that gets ignored. `STREHL_FREEZE_REQUIRE=1` converts the skip
into a hard failure, which is what a machine that *is* supposed to have the data
should set. The other three tests need no capture library, no binary and no RAW
decode, so a fresh clone still checks that every row records a complete,
unambiguous, non-defaulted invocation.

### 1.6 No new dependency

SHA-256 is implemented inline (FIPS 180-4, ~120 lines) rather than adding a
crate to the workspace for a test. `the_hasher_reproduces_the_published_test_vectors`
checks it against the published vectors — **and it earned its keep**: the first
implementation had a bug where topping up a partial block reset `buf_len` to 0,
which made `finish`'s padding loop oscillate 0,1,0,1 forever. The symptom was a
test harness burning ~553 s of CPU with no output. The NIST vectors caught it;
the reason is now written into the code at the fix site.

### 1.7 A canary on the shared library, deliberately not an assertion

Before any render, the test scans the capture library for files whose name
contains `warpmap` and **prints** any it finds, with full paths. It does not
fail. A stray sidecar there is a real problem, but it is usually *another
agent's* write, and turning someone else's mistake into your red is how you
teach people to ignore reds. What *is* asserted is that this test's own renders
add nothing — the entry-name comparison in `render`.

Eleven of these accumulated in one night before anybody looked. A line of
output at the top of a test that already runs is close to free, and it is the
difference between finding out in seconds and finding out by eye.

---

## 2. Verification

Six named checks. A–C were run in a clean `git archive` scratch tree at
`fea1a72` (`C:\dev\strehl-out\M108\head-clean`), which discharges rule 31 as
well; D and E are registry/fixture plants run in the working tree and reverted.
A and B were re-run against the final two-pass test, not only the first draft.

### Check A0 — green before planting

```
running 4 tests
test every_registry_row_records_a_complete_invocation ... ok
test no_two_rows_freeze_the_same_invocation ... ok
test the_frozen_renders_still_produce_their_recorded_bytes ... ok
test the_hasher_reproduces_the_published_test_vectors ... ok
test result: ok. 4 passed; 0 failed
```

### Check A — planted change, expect RED

Planted in the **scratch copy only**, never in the shared tree:
`crates/strehl-core/src/merge.rs:185`, `FOCUS_NOISE_SD: f32` `0.015_214` →
`0.016_214`. Original sha `66F6E4C6…5582`, planted sha `19FD4257…A1A0`.

Note what the two-pass gate does here: both passes produced
`810A41A0…438D`, **agreed with each other**, and were therefore reported as a
*moved* freeze rather than as nondeterminism. That discrimination is the point
of gate 3, and this is it working.

```
   Compiling strehl-core v0.0.0 (...)
   Compiling strehl-cli v0.0.0 (...)
    Finished `release` profile [optimized] target(s) in 36.52s

thread 'the_frozen_renders_still_produce_their_recorded_bytes' panicked at
crates\strehl-cli\tests\byte-freeze.rs:952:9:

==============================================================================
BYTE-FREEZE MOVED: coffee-bean-20-gate2-unaligned
==============================================================================

The render this row freezes no longer produces the recorded bytes.

  expected sha256 : D99F5D82337AA2F093202D12677FBD1DE6D78A94761C0DE250020085271C76CA
  actual   sha256 : 810A41A0391BED0FB40DF206C90FEE1B671FDCBF7D23673FFE882BBC0572438D
  expected bytes  : 49449626
  actual   bytes  : 49449626   (unchanged -- same geometry, the pixel VALUES moved)
  expected align  : off
  actual   align  : off   (as recorded)
  baseline chunks : 10 chunks of <= 2 frames
  this run chunks : 10 chunks of <= 2 frames   (as recorded)

The render was kept at:
  ...\strehl-freeze-48280-coffee-bean-20-gate2-unaligned\render.tif

THE EXACT COMMAND THAT PRODUCED THE `actual` NUMBERS. It is generated from
the registry row, so it cannot be a different pipeline's command -- which is
the mistake that produced SYNTHESIS fact 1379:

  Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
  ... (all five render vars cleared) ...
  $env:STREHL_ALIGN = "0"
  strehl.exe stack D:\personal\macro\coffee-bean --limit 20 --gate 2.0 --out ...\render.tif

Last re-baselined at fea1a72 on 2026-08-24, because:
  "NOT A NEW BASELINE -- a re-record of an existing one. ..."

==============================================================================
WHAT TO DO
==============================================================================
Most moves here are INTENDED. ... (three numbered cases: (1) unexpected, do
not re-baseline, re-render with the row's own command first; (2) expected,
here are the exact five fields to edit and the new values to paste; (3) not
sure it is yours -- stash, REBUILD, and note the mtime hazard) ...

DO NOT delete this test, and do not #[ignore] it. If the row is wrong, fix
the row: that is a two-line edit and it leaves a record of who moved what.
==============================================================================

test result: FAILED. 0 passed; 1 failed
EXIT=101
```

Read as a stranger in CI, that message answers: *what moved* (pixel values, not
geometry — the byte count is called out as unchanged), *under what command*
(printed, copy-pasteable), *why the old number was what it was* (the `why`
column), *what to do* (three cases, with the new hash already formatted for
pasting), and *what not to do* (delete it). The kept render is left on disk so
the reader can diff it rather than re-render.

The `Compiling strehl-core` line is in the transcript on purpose: rule 33 says
prove the binary under test is the one you meant.

### Check B — restore, expect GREEN again

`Copy-Item` preserved the source mtime, exactly as the corpus records:

```
after Copy-Item, mtime = 08/24/2026 10:28:35   <-- Copy-Item preserved the SOURCE mtime
after touch,     mtime = 08/24/2026 10:56:07
restored sha    = 66F6E4C65FC15D96C30B7758134F8AEF7E080C16BF7F01E1FEA56C9163D35582
original sha    = 66F6E4C65FC15D96C30B7758134F8AEF7E080C16BF7F01E1FEA56C9163D35582
line 185 now    : pub const FOCUS_NOISE_SD: f32 = 0.015_214;
```

Then, with a `Compiling` line confirming the rebuild actually happened:

```
   Compiling strehl-core v0.0.0 (...)
    Finished `release` profile [optimized] target(s) in 36.09s

running 4 tests
test every_registry_row_records_a_complete_invocation ... ok
test no_two_rows_freeze_the_same_invocation ... ok
test the_frozen_renders_still_produce_their_recorded_bytes ...
freeze `coffee-bean-20-gate2-unaligned` HOLDS: D99F5D82…76CA (49449626 bytes, alignment off, 10 chunks of <= 2 frames) -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar` HOLDS: 119936E6…D709 (49449626 bytes, alignment on-sidecar-override, 10 chunks of <= 2 frames, 20 placed / 0 refused) -- reproduced twice
ok
test the_hasher_reproduces_the_published_test_vectors ... ok

test result: ok. 4 passed; 0 failed; finished in 17.32s
EXIT=0
```

Green → red → green, with the restored file's hash verified byte-for-byte
against the original and the mtime hazard handled explicitly.

### Check C — the skip path, both directions

C1, `$STREHL_CAPTURES` pointed at a nonexistent directory:

```
test the_frozen_renders_still_produce_their_recorded_bytes ...
------------------------------------------------------------------------------
SKIPPED: the byte-freeze renders were NOT checked.
------------------------------------------------------------------------------
$STREHL_CAPTURES is set to `D:\no-such-capture-library`, and there is no directory there.
Point it at a capture library, or unset it to fall back to `D:\personal\macro`.

The registry rows themselves WERE still validated by the other tests in this
file -- their completeness, not their hashes. Set STREHL_FREEZE_REQUIRE=1 to
make this skip a hard failure on a machine that is supposed to have the data,
which is what CI should do.
------------------------------------------------------------------------------
ok
test result: ok. 1 passed; 0 failed
EXIT=0
```

C2, same, plus `STREHL_FREEZE_REQUIRE=1`:

```
BYTE-FREEZE NOT CHECKED, and STREHL_FREEZE_REQUIRE says that is a failure.
...
Nothing was rendered, so this run is evidence about NOTHING. Unset
STREHL_FREEZE_REQUIRE if you genuinely do not have the captures.

test result: FAILED. 0 passed; 1 failed
EXIT=101
```

Exit codes were read with `$out = & $exe …; $code = $LASTEXITCODE` before any
filtering, per rule 46.

### Check D — the isolation gate, expect RED with no hash compared

Planted in the registry: the sidecar row's `align` column changed to `off`
while its `alignment_mode` still claims `on-sidecar-override`. This is the
contamination shape exactly — the tool runs a pipeline other than the one the
row describes.

**This control is worth reading twice.** The `off` render produces
`D99F5D82…76CA`, which *is* a hash in this registry — the other row's. Under a
design where the hash is the only check, this run would have been reported as a
moved freeze, and the reader would have gone looking for a code change that
did not exist. That is a small-scale reproduction of SYNTHESIS fact 1379.

```
==============================================================================
ENVIRONMENT NOT ISOLATED: `coffee-bean-20-gate2-sidecar` (pass 1)
==============================================================================

This row freezes a specific pipeline, and `strehl stack` reported a
different one on its own output. NO HASH WAS COMPARED, because a hash from
the wrong pipeline is not weak evidence -- it is evidence about something
else.

  registry says the tool must report : on-sidecar-override
  the tool actually reported         : off

The `alignment` line is the tool's own statement about which pipeline it
ran. `MISSING` means no such line was found at all, which means either the
binary is older than the alignment wiring or the line has been reworded --
and in the second case this check has gone blind and must be repaired, not
removed.

WHAT USUALLY CAUSES THIS
  * An ambient STREHL_ALIGN / STREHL_WARPMAP in the shell. This test
    removes all of 5 render variables before applying the row's own,
    so if that is the cause, the removal list is now incomplete.
  * A sidecar the tool discovered by itself. The capture library is
    read-only and must contain none; the warning printed at the top of
    this test lists any it found.
  * The row is simply wrong about the mode. Fix the row.

Command that was run:
  ... $env:STREHL_ALIGN = "0" ...

test result: FAILED. 0 passed; 1 failed
EXIT=101
```

The unaligned row in the same run reported `HOLDS … reproduced twice`, so the
failure is scoped to the contaminated row and not a blanket red.

Registry restored from backup and verified byte-identical
(`9F331BE0…14CD`), with `git status` showing the file unmodified.

### Check E — the placement gate, with a real artifact

Rather than test the assertion's plumbing, I built the fault: a copy of the
committed fixture with frame 7 rewritten from `7 placed …` to
`7 refused control-plant-M108`, and a registry row pointed at it. The frame
*count* still matches, which is the case `StackIdentity` cannot see.

```
The frozen render for `coffee-bean-20-gate2-sidecar` FAILED TO RUN (exit Some(1), pass 1).
This is not a moved hash -- the command did not complete.

What the tool reported about registration before it stopped:
  alignment : on-sidecar-override
  placement : 19 placed / 1 refused
If the placement count is short of `--limit 20`, that IS the diagnosis:
the warp map and the bracket disagree, and `merge_cmd.rs:932` refuses to
merge a frame the solve refused rather than quietly giving it identity.
...
Error: frame 7 was refused by the alignment solve: control-plant-M108

test result: FAILED. 0 passed; 1 failed
EXIT=101
```

**And this is the honest result:** the render exits 1, so the failure is caught
by the exit-code check and the placement assertion is never reached. I have
recorded that in §1.3 and in the code rather than claiming a live check I do
not have. What the control *does* establish is that the diagnosis reaches the
reader — `19 placed / 1 refused` against `--limit 20` is printed at the top of
the message, which it was not before this control was run.

Planted fixture deleted; `tests/data/` verified to contain only
`coffee-bean-20.warpmap.txt`.

### Supporting measurements

* **Determinism, gate 3.** Every row is rendered twice in separate processes on
  every run. Both rows agree with themselves: `-- reproduced twice` on each.
  Suite cost 8.5 s → 17.0 s.
* **Determinism, wider.** The hash is invariant across `RAYON_NUM_THREADS` =
  2, 4, 8, and **identical in debug and release** (debug run 26.1 s).
* **Reproducibility at a committed revision.** Both hashes are identical in the
  clean `fea1a72` scratch tree and in the shared dirty working tree, so neither
  baseline is contaminated by the uncommitted diffs that were present
  (`robust.rs` +15 pure-`cargo fmt`, `align_cmd.rs` +161, `align.rs` +28 — the
  latter two have since landed at `dccaea8`).
* **No writes to the library.** After the sidecar row ran, `D:\personal\macro`
  contained **0** warpmap files. See §3.3 for the ones that appeared from other
  processes.
* **The warp fixture is CRLF-safe.** Git will check it out with CRLF line
  endings on Windows, so I rendered against a CRLF copy (3 207 B vs 3 171 B)
  rather than reasoning about `WarpMap::load`. Same hash,
  `119936E6…D709`, `alignment : ON (sidecar-override), reference frame 10,
  20 placed / 0 refused`, and still 0 warpmaps in the library afterwards.
  (`warpmap.rs:650` does `raw.trim()`, which is why.)
* `cargo clippy --release -p strehl-cli --test byte-freeze -- -D warnings` →
  clean, exit 0. (The workspace-wide `--all-targets` form fails on many
  pre-existing errors in `examples/` and `strehl-core`; that is not mine and I
  did not touch it.)
* `rustfmt --edition 2024` was run on `byte-freeze.rs` **only**. A workspace
  `cargo fmt` would have touched six other agents' files.

---

## 3. Findings

### 3.1 M95's freeze is ALIVE — and its full hash existed nowhere

`coffee-bean --limit 20 --gate 2.0` with `STREHL_ALIGN=0` reproduces SYNTHESIS
fact 1323's freeze **exactly** at `fea1a72`:

```
D99F5D82337AA2F093202D12677FBD1DE6D78A94761C0DE250020085271C76CA   49 449 626 bytes   3.3 s
```

This was the thing the brief asked me to check before enshrining it, and it is
good news: there is **no fourth stale freeze**. But the corpus recorded that
hash only as the truncated `D99F5D82...76CA` — **the full 64-character digest
was written nowhere in the repository**, which means it could not have been
checked by anything. The registry now carries it in full, which is the first
time it has existed as verifiable data.

*Caveat, stated because I cannot close it:* I verified that the
invocation-with-alignment-off reproduces the hash. I cannot establish whether
M95's original run set `STREHL_ALIGN=0` or simply predated alignment being
wired in — the record does not say. Those are the same bytes either way, but
they are not the same claim.

### 3.2 The stale citation at `merge_cmd.rs:2958-2971` (file HELD by M87)

I did not edit it. The comment claims M85's report "carries the SHA-256 proof
that it still emits the identical bytes"; M106 established that this proof
broke at `885e9f7`. **Exact replacement text for lines 2965-2970**, to be
applied by whoever holds the file:

```rust
    // Every quality number in the corpus was measured on the file this branch
    // writes. The arithmetic below is exactly what shipped before M85 --
    // clamp before the curve, no matrix, no demosaic -- and it is byte-frozen
    // by `crates/strehl-cli/tests/byte-freezes.tsv`, which records the full
    // invocation beside each hash and is checked by `tests/byte-freeze.rs`.
    // The SHA-256 in `docs/research/M85-output-correctness.md` is NO LONGER
    // LIVE: it was invalidated at `885e9f7` when M86c wired alignment into
    // `strehl stack` (intended and correct; see
    // `docs/research/M106-freeze-attribution.md`). Do not refactor this into
    // the helpers above for tidiness; the tidiness is not worth re-measuring
    // the corpus.
```

The point of the replacement is not tidiness — it is that a citation which is
*wrong* is worse than no citation, because it reads as current. The whole of
M106 is that lesson.

### 3.3 The sidecar situation (round 4)

* At `fea1a72`, HEAD still wrote sidecars into the capture library; M85's
  `cache_root()` fix existed only in an **uncommitted** working copy. That is
  why strays kept reappearing after each quarantine. **It has since landed at
  `dccaea8`** and the working tree now matches HEAD for `align_cmd.rs`.
* **Disclosure:** my own clean-`fea1a72` build overwrote
  `D:\personal\macro\coffee-bean\warpmap.txt` at 10:31:11 with a 20-frame
  solve, before I had switched the aligned row to `STREHL_WARPMAP`. Quarantined
  to `C:\dev\strehl-out\ORCH-quarantine-sidecars\round3-M108-coffee-bean-warpmap.txt`;
  library verified clean and intact afterwards (0 warpmaps, 105 ARWs, 210
  entries). This is exactly the hazard rule 45 exists for, and it caught me
  even while I was reading rule 45.
* **Another process** rewrote the same path at 10:24:00, 10:27:37 and again at
  10:33:42, after the orchestrator's round-2 quarantine. The 10:33:42 file was
  608 B, `frames 1`, `stack-digest f616fd0a669cb4ed` — **not mine** (my solve is
  3 171 B). Quarantined to
  `…\ORCH-quarantine-sidecars\round4-1033-coffee-bean-warpmap.txt`, sha
  `1869EEBB…C907`. Library re-verified: **0 warpmaps**.
* Independently, the orchestrator observed two more strays at 10:17:17
  (`coffee-bean`, 1 560 B, an 8-frame solve with reference 4) and 10:17:38
  (`flat-on-ruler-cpl`, 8 frames) — minutes after quarantining eleven. **The
  8-frame `coffee-bean` one is the dangerous shape**: under a `--limit 8` run
  it would have been accepted silently, because `StackIdentity::from_paths`
  digests filename and file length only. That is the case gate 2 was added for,
  and it is the reason the aligned row uses a committed fixture rather than
  whatever happens to be lying in the capture directory.
* My finished test suite ran at 10:56 and wrote **nothing** — the 10:33:42
  mtime survived it untouched, which is the cleanest available evidence that
  the `STREHL_WARPMAP` mode is hermetic. Every run since has re-verified
  **0 warpmaps** in the library afterwards.

---

## 4. What this test does **not** protect

Every instrument has a blind spot. Naming mine, in rough order of how likely it
is to matter:

1. **The aligner's solver is entirely uncovered.** The sidecar row consumes a
   committed warp map; it never solves one. A total rewrite of the solver that
   produced different placements would leave both rows green. This is a
   deliberate trade (§1.3) and it is the first row to add when the solver
   settles.
2. **One stack, one depth, one gate.** 20 frames of `coffee-bean` at
   `--gate 2.0`. Nothing here covers the 299-frame renders the quality numbers
   were actually measured on, nor any other bracket, nor gate values near the
   default. A change that only bites at depth — a chunk-tree edge case, an
   accumulator overflow, a gate that rejects differently when there are more
   candidates — passes cleanly.
3. **The `--srgb` / demosaic / exposure paths are not frozen at all.** Both rows
   are `srgb = no`. That is on purpose (§5) but it means the viewing pipeline
   has no freeze whatsoever.
4. **Cross-host chunking is unverified.** Both baselines were measured at
   `10 chunks of <= 2 frames`. The merge reduces in a chunk tree and f32
   addition is not associative, so a host with different RAM or core count may
   legitimately produce a different hash. The `workers` column exists to make
   that the first hypothesis rather than a mystery, but I did **not** measure a
   second host, and I do not know whether the chunking actually moves the
   bytes. This is the blind spot most likely to produce a confusing red.
5. **Gate 3 catches only nondeterminism that shows up within seconds.** Two
   consecutive renders on one machine will not expose a race that needs a
   different core count, a cold cache, or a loaded machine to appear. Agreement
   twice is evidence, not proof.
6. **The placement gate is presently redundant with the exit code.** Measured,
   not assumed (§1.3, Check E). It is a tripwire for a future change, not a
   live check today, and it should not be counted as coverage until
   `merge_cmd.rs:932` stops being fatal.
7. **The isolation gate trusts a string.** It reads the tool's own
   `alignment :` line. A binary that reports `sidecar-override` while doing
   something else would pass. That is a much narrower hole than having no check
   — the tool would have to lie rather than merely be misconfigured — but it is
   a hole, and if the line is ever reworded the gate reports `MISSING` and must
   be repaired rather than deleted.
8. **A hash proves sameness, not correctness.** Both rows would stay green
   through a change that is wrong but deterministic. The freeze is an alarm on
   *movement*; it has no opinion about quality. Nothing here replaces the
   measured bars.
9. **The registry can be re-baselined dishonestly.** Nothing stops someone
   pasting the new hash and leaving the `why` column stale. The test checks that
   `why` is long enough and free of placeholders — it cannot check that it is
   true. This is the residual risk, and it is why the failure message spends a
   paragraph on the `why` column specifically.
10. **The stray-sidecar scan is one level deep and name-based.** It looks at
    `<library>/<stack>/*warpmap*`. A sidecar nested deeper, or named something
    else, is invisible to it. It is a canary, not an audit.
11. **The source comment at `merge_cmd.rs:2958` is still prose.** Nothing
    mechanically ties a code comment to a registry row. §3.2's replacement text
    points at the registry instead of a report, which is better, but it is still
    a human promise.
12. **A deleted row fails nothing.** If someone removes a row, the suite goes
    green with less coverage. The header check catches *reshaping*, not
    *shrinking*.

---

## 5. Which invocations deserve to be frozen

Freezing everything is the same as freezing nothing: the cost of a freeze is
paid every time someone has to decide whether a red is theirs, and that budget
is small. My recommendation:

**Freeze (done):**

1. **The unaligned measurement path on one small stack** —
   `coffee-bean --limit 20 --gate 2.0`, `STREHL_ALIGN=0`. It covers decode,
   focus, the regulariser, the gate, the merge and the byte-frozen encoder in
   one 3-second render, it is hermetic at every commit, and it re-uses a hash
   the corpus already trusted.
2. **Its sidecar-aligned partner.** Cheap (adds ~5 s), and it is the only thing
   that turns "something moved" into "*registration* moved". A freeze you can
   localise is worth several you cannot.

**Freeze later, not now:**

3. **A solving row**, once the aligner's solver stops moving. It is the only
   row that would cover the solver, and `dccaea8` removed the objection that
   made it unsafe. It must set `$STREHL_CACHE_DIR` to a scratch path.
4. **One deep render** (the 299-frame bracket the corpus numbers were measured
   on), *if* someone is willing to pay ~55 s and mark it `#[ignore]`-by-default
   with an explicit opt-in. The shallow row catches nearly everything the deep
   one would; the deep one exists to catch depth-dependent bugs, and that is a
   real but narrow class.

**Do not freeze:**

5. **The `--srgb` / viewing path.** Deliberately in flux — M95 is actively
   testing demosaic ladders and rescale fixes. A freeze there would go red
   weekly for intended reasons, and the third person to hit it deletes the file.
   Freeze it when the viewing pipeline is declared settled, not before.
6. **Any invocation whose hash nobody cites.** A freeze earns its row by being
   load-bearing for a claim somewhere in the corpus. A hash that supports no
   argument is maintenance with no return.
7. **More than one row per pipeline.** Two rows that always move together carry
   one row's information and two rows' cost. The pair above is justified
   precisely because they can move *independently*.

The TSV's comment header points here, so the rule travels with the data.

---

## 6. Enforcement: the other half of the problem

This section answers a question the orchestrator put to me directly, and it is
the same question as the rest of the milestone.

**The observation.** Rule 45 was broadcast to seven agents, and two more stray
sidecars appeared in the read-only capture library within minutes — one of them
in `coffee-bean`, the stack this test freezes. Whether or not those writes began
before the broadcast landed, the shape is the point: **a convention announced is
not a convention enforced.** Prose in `AGENTS.md` did not stop the writes,
exactly as prose in a milestone report did not stop M85's freeze going stale for
weeks. This test is the enforcement layer for the second problem. The first
needs its own.

**The one verified fact that bears on it.** `align`'s sidecar cache is a *soft*
failure: it warns `could not cache sidecar (…); continuing` and proceeds with
the solve it just computed. So a genuinely read-only capture directory does not
break the tool — it only forces a re-solve, which is slower and correct. A
deny-write ACL is therefore viable on the merits.

**But I do not recommend the ACL as the primary mechanism**, for the reason
already identified: the owner copies new captures onto that drive, and a
deny-write ACL fails confusingly the next time he does. An enforcement that
punishes the legitimate user more reliably than the illegitimate one gets turned
off, which is the same failure mode as a test that goes red too often.

Narrower mechanisms, in the order I would apply them:

1. **Code, not convention — already landed, and this is the real fix.**
   `sidecar_path` no longer resolves to `<stackdir>/warpmap.txt`; at `dccaea8`
   it resolves under `cache_root()`. And `align_cmd.rs` carries a **unit test**
   asserting the sidecar path is not inside the capture directory, so a
   refactor that reintroduces the old behaviour fails CI. That is the enforcement
   layer, it is the same shape as this milestone's, and it exists. The strays
   observed tonight are explained by agents running binaries built from *before*
   that landed — which is itself the argument for landing enforcement early
   rather than announcing it.
2. **A detector, because enforcement can be bypassed by an old binary.** The
   canary in §1.7 prints any stray it finds on every test run. That is cheap and
   already in. A standalone scheduled check over the whole library would be
   better still: it would have found eleven strays in seconds rather than by
   eye, and it does not depend on which binary anyone is running.
3. **A read-only assertion in the tool itself**, if 1 and 2 prove insufficient:
   have `strehl` refuse to create any file underneath a directory it read
   captures from, with an error naming rule 45. This is narrower than an ACL
   because it constrains the program rather than the filesystem, so the owner
   copying captures in is unaffected.
4. **The ACL last**, and only scoped to a directory the owner does not write to
   directly.

The general lesson, which is this milestone's lesson: **the enforcement layer
belongs as close to the mechanism as it can get.** A rule in `AGENTS.md` is the
weakest form, a detector is stronger, a test is stronger still, and code that
cannot express the mistake is strongest. M85's freeze was defended by prose and
went stale; rule 45 was defended by prose and was breached within minutes. Both
are now defended by tests, and that is the only reason either is trustworthy.

---

## 7. How to re-baseline (the short version)

You will need this more often than you will need anything else in this
document, because **most moves here will be intended**.

1. Read the failure message. It contains the new hash, the new byte count, and
   the exact command.
2. Edit the row in `crates/strehl-cli/tests/byte-freezes.tsv`: `sha256`,
   `bytes`, `baselined_at` (a **committed** commit, rule 31), `baselined_on`.
3. **Rewrite `why` from scratch.** Say what moved the bytes and why that is
   correct. A `why` still describing the previous baseline is worse than an
   empty one, because it reads as current — that is the M106 lesson in one
   column.
4. Say in your milestone report that you moved a freeze, and name it.

If you are *not* sure the move is yours: stash, **rebuild** — and set the
restored file's mtime to now, `(Get-Item <path>).LastWriteTime = Get-Date`, or
cargo will consider the stale artifact fresh and you will test the binary you
meant to remove (rule 33). Read the `Compiling` lines.

Do not delete the test and do not `#[ignore]` it. Fixing the row is a two-line
edit and it leaves a record of who moved what; deleting the test leaves nothing,
which is the state this milestone was commissioned to end.
