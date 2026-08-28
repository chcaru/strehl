# BUILD-GATE-PRINT — the red byte-freeze row is `eps_r` and nothing else, proved bit-exactly in both directions; and the print gate was already re-aimed, so the deliverable is the commissioning it never had

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`F1, F2, …` per rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision at start:** `6943f04b`. HEAD advanced to `62c0bb6a` during the
lane as roughly a dozen other lanes committed; `crates/strehl-cli/src/merge_cmd.rs`
was the only crate source to move in that window, so the byte-freeze verification
was **re-run at the later tree** rather than assumed — see §2.4.

**Instruments:**
- `experiments/BUILD-GATE-PRINT/rebaseline_sidecar.py` — the column-safe
  re-baseliner that performed the registry edit (§1.5).
- `experiments/BUILD-GATE-PRINT/commission_printgate.py` — the four
  commissioning arms this lane adds (§3).
- `experiments/BUILD-OUTPUT/clip_census.py` and `crush_luma.py` — **reused
  verbatim**, not reimplemented, to reproduce BUILD-OUTPUT's numbers (§3.1).
- `experiments/ORCH-drift-check/commission_clip.py` — **pre-existing**, run and
  cited, not duplicated (§3.3).

Sources under `D:\personal\macro\` were read only. Nothing was written to
`D:\personal\macro` or `D:\macro-dark-frames`.

---

## 0. The commission, and the two things it got wrong

> JOB 1 — re-baseline the red byte-freeze row, with its `why` column rewritten.
> JOB 2 — fix the print gate, which is currently aimed at the wrong quantity.

Job 1 was done as specified. Job 2 **was already done and committed before this
lane started**, which changes the deliverable entirely; see §3.0. Two further
premises in the commission did not survive contact:

- the brief said `compose` has **exactly two** live call sites. There are
  **three** (§1.1). The conclusion is unchanged, but the census was wrong.
- the brief said to write this report to `docs/research/BUILD-GATE.md`. That
  file exists and belongs to an unrelated lane (§5.2).

---

## 1. JOB 1 — the red row

### 1.1 The `compose` census, which the commission got wrong

**F1 — MEASURED. `OpticalProfile::compose` has three non-test call sites, not
two.** `git grep -n` across the whole workspace:

| site | target | linked by `strehl`? |
|---|---|---|
| `crates/strehl-cli/src/align_cmd.rs:1929` | `warp_frame_in_place_plane` | yes |
| `crates/strehl-cli/src/align_cmd.rs:2095` | `warp_frame_in_place_fullres` | yes |
| `crates/strehl-cli/examples/build-demosaic-truth.rs:516` | cargo **example** | **no** |

The remaining 11 occurrences in `optics.rs` are all at line ≥ 1082, inside
`#[cfg(test)] mod tests`, which opens at line 1005.

**F2 — DERIVED. The third site does not change the adjudication.** A cargo
`examples/` target is a separate binary. The `strehl` binary does not link it,
and the byte-freeze harness invokes `env!("CARGO_BIN_EXE_strehl")` — so
`build-demosaic-truth.rs` cannot participate in a frozen render. Both sites that
can are warp *application* sites on the alignment path. **The commission's
conclusion stands; its count did not.** This is reported rather than quietly
agreed with, because a census that is wrong by one is wrong.

**F3 — MEASURED. `eps_r` reaches the render through exactly one consumer.**
`optics.rs:461` (default, `-508.4e-6`) → `eps()` at `:278` → consumed by
`compose()` at `:344` and `displacement_at()` at `:388`. `displacement_at` has
**zero call sites outside tests**. So the whole causal chain from the constant to
a rendered byte runs through `compose`, and therefore through alignment.

### 1.2 The two rows, as they stood

Run at `6943f04b`, `--release`, private `--target-dir`, `Compiling strehl-cli`
present (rule 33):

```
freeze `coffee-bean-20-gate2-unaligned` HOLDS: 88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620
    (49450019 bytes, alignment off, 10 chunks of <= 2 frames) -- reproduced twice
BYTE-FREEZE MOVED: coffee-bean-20-gate2-sidecar
    expected 52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206
    actual   E600A506F6D05A84A21C9DF93E4EB82AED98C8098EAF956BCF0E25985F3D4CB2
    bytes unchanged 49450019 / align on-sidecar-override (as recorded)
test result: FAILED. 0 passed; 1 failed; ... finished in 93.84s
```

**F4 — MEASURED. The moved hash is reproducible.** Two renders, same build,
two separate processes, both
`sha256=E600A506F6D05A84A21C9DF93E4EB82AED98C8098EAF956BCF0E25985F3D4CB2
bytes=49450019`, both logging `alignment ON (sidecar-override), reference frame
10, 20 placed / 0 refused`.

**F5 — MEASURED, and this is the finding. The control held in the same
session.** `-unaligned` stayed at `88712017…`. The two rows differ *only* in
alignment, so a change that moves one and not the other is localised to the
alignment path — which by F3 is the only path `eps_r` can reach.

**D1 — DISCIPLINE. The freeze harness already refuses to report a move it
cannot reproduce.** Reading `byte-freeze.rs`: each row is rendered **twice, in
two separate processes**, and `a.hash == b.hash` is asserted *before* the
registry comparison. A `MOVED` panic therefore already implies determinism. The
commission's step 2 was satisfied by construction; it was performed manually as
well, and both agreed.

### 1.3 Attribution, bit-exact and in both directions

Performed in an isolated source copy (`C:\dev\strehl-src-BUILDGATE`, `optics.rs`
verified byte-identical to the repo's at SHA256 `1E17AE25…44FE`) so that
`optics.rs` was never perturbed in a tree shared with a dozen live lanes.

| arm | source | registry | result |
|---|---|---|---|
| ISO CONTROL | unmodified | old | unaligned `88712017…`, sidecar `E600A506…` — copy is faithful |
| **ISO ARM A** | `eps_r` = `-704.5e-6` | old | `test result: ok. 1 passed` — sidecar HOLDS at the **superseded** `52517FF8…C206`; unaligned unchanged |
| **ISO ARM B** | `eps_r` = `-704.5e-6` | new | `BYTE-FREEZE MOVED`, expected `E600A506…` actual `52517FF8…`, `FAILED` |
| ISO ARM C | restored | new | `test result: ok. 1 passed`, both rows hold; 4 `Compiling` lines, 2m07s |

**F6 — MEASURED. Reverting one constant reproduces the old hash exactly.** ARM A
is the strong form of the claim: setting `eps_r` back to `-704.5e-6` returns the
sidecar row to `52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206`
— the *superseded* baseline, bit for bit — while the unaligned control is
invariant under **both** values of the constant. Nothing else in the tree was
touched. This is attribution, not correlation.

**F7 — MEASURED. The freeze test has teeth against the NEW baseline.** ARM B
plants the same perturbation against the re-baselined registry and the test goes
RED with the two hashes exchanged. Re-baselining did not turn the row into a
tautology, which is the specific failure mode this step exists to catch.

ARM C restored `optics.rs` from `$env:TEMP\BUILD-GATE-backup\optics.rs.orig`
(**not** `git checkout --`, per house rule), set `LastWriteTime` to force a
rebuild, and returned both rows to GREEN.

### 1.4 What changed in the registry

One line. `git diff --numstat` = `1  1`.

| column | before | after |
|---|---|---|
| `sha256` | `52517FF8…C206` | `E600A506F6D05A84A21C9DF93E4EB82AED98C8098EAF956BCF0E25985F3D4CB2` |
| `baselined_at` | `4c99cc40` | `6943f04b` |
| `baselined_on` | `2026-08-26` | `2026-08-28` |
| `why` | 3 824 chars | 3 285 chars, rewritten |

`bytes` (49450019), `workers` and every invocation field are unchanged, and the
`-unaligned` row is byte-identical afterwards — asserted by the instrument, not
eyeballed.

**Q1 — OPEN. The registry defines `baselined_at` twice, and the two definitions
disagree.** The file header says it is *"the commit at which this row's hash was
last measured."* The test's own failure message says it is *"the commit that
moves it (COMMITTED; rule 31)."* Those are different commits here: the mover is
`393d7ca3`, the measurement was at `6943f04b`. Precedent decides it — the
previous re-baseline recorded `4c99cc40`, which is neither the mover nor related
to it, i.e. HEAD at measurement time. So `6943f04b` is recorded, and the mover
`393d7ca3` is named explicitly inside `why`, which satisfies both readings. The
intra-file contradiction should be resolved by whoever owns the header.

### 1.5 The instrument

`rebaseline_sidecar.py` parses the TSV **by header name**, asserts the target row
is unique, asserts 13 `FROZEN` fields did not move, asserts the `-unaligned`
control row is byte-identical afterwards, and refuses a `why` containing a tab or
newline or shorter than 60 characters (the harness's own floor). `--check` was
run before `--apply`; both printed the full before/after and
`control: coffee-bean-20-gate2-unaligned byte-identical (4023 chars)`.

**D2 — DISCIPLINE. A re-baseline should be applied by an instrument that asserts
what must NOT change.** Hand-editing a 90-column TSV row cannot demonstrate that
the frozen invocation fields survived the edit; a script that refuses to write
unless they did, can.

---

## 2. JOB 1 — final state

```
test every_registry_row_records_a_complete_invocation ... ok
test no_two_rows_freeze_the_same_invocation ... ok
test the_alignment_parser_names_every_mode_the_tool_can_report ... ok
freeze `coffee-bean-20-gate2-unaligned` HOLDS: 88712017FE...154A8620 -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar`   HOLDS: E600A506F6...5F3D4CB2 -- reproduced twice
test the_frozen_renders_still_produce_their_recorded_bytes ... ok
test the_hasher_reproduces_the_published_test_vectors ... ok
test result: ok. 5 passed; 0 failed; ... finished in 113.55s
```

All five tests, not merely the render one — the other four validate registry
parsing and completeness, which is precisely what a registry edit can break.

**F8 — MEASURED. Verification was repeated after HEAD moved.** Twenty commits
landed during the lane. `git diff --name-only 6943f04b..HEAD -- crates/`
returned `crates/strehl-cli/src/merge_cmd.rs` — a file on the render path — so
the freeze run above was **repeated against the later tree**. A verification that
predates a change to the code under test is not a verification. The repeat, with
`Compiling strehl-cli` present:

```
Compiling strehl-cli v0.0.0 (...\crates\strehl-cli)
    Finished `release` profile [optimized] target(s) in 31.21s
freeze `coffee-bean-20-gate2-unaligned` HOLDS: 88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620 -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar`   HOLDS: E600A506F6D05A84A21C9DF93E4EB82AED98C8098EAF956BCF0E25985F3D4CB2 -- reproduced twice
test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 43.53s
```

Both hashes are unchanged across the `merge_cmd.rs` move, so that change does not
touch these two renders.

---

## 3. JOB 2 — the print gate

### 3.0 The commission was already satisfied, which is the first finding

**F9 — MEASURED. Job 2 items 2 and 3 were already done and committed at
`04074ab8`, before this lane began.** `experiments/ORCH-drift-check/orch_printready.py`
(**not** `scripts/orch_printready.py`; the brief's path does not exist) already
reads:

```python
clip = float(((rgb >= CLIP_DN).sum(axis=2) == 3).mean())   # all three channels
clip_ch = float((rgb >= CLIP_DN).mean())                   # old statistic, reported only
crush = float((rgb <= 35).mean())                          # never appended to `fails`
```

The working tree was clean for that file and **this lane changed not one line of
the gate**. Re-doing a correction that is already in place would have produced a
diff that looked like work and proved nothing.

**So the deliverable became the part that was missing: the commissioning.** The
brief itself says this is "the part that matters most", and it was the part with
nothing behind it.

### 3.1 Reproducing BUILD-OUTPUT, using its scripts

Run against `C:\dev\strehl-out\acceptance\SHIP-V3` (26 masters), reusing
`experiments/BUILD-OUTPUT/clip_census.py` and `crush_luma.py` **verbatim**.

**F10 — MEASURED. BUILD-OUTPUT's clip numbers reproduce.**
`dry-erase-marker-head-cpl` clipALL3 **0.0000%** — the joint corpus minimum.
`112MSDCF` clipALL3 **0.0691%** — the corpus maximum, matching the gate's
recorded provenance. `flowers-cpl` clipCH **0.1433%** against clipALL3
**0.0086%**, with B==65535 at 0.4458%: a blue-channel gamut pin, not a blow.

**F11 — MEASURED. The crush anti-correlation reproduces.**

| subject | crush px | median luma | distinct levels |
|---|---|---|---|
| 109MSDCF | 7.4110% | 0.2381 | 51 962 |
| 119MSDCF | 9.7788% | 0.2450 | 53 741 |
| flower-inner-edge-cpl | 10.9185% | 0.3254 | 36 276 |
| **flowers-cpl** (genuine black) | — | **0.0011** | **135** |

Open shadow with tens of thousands of surviving levels is the opposite of
crushed. The one subject with real black is not what the statistic flags.
`crushALL3` reads 0.0000% on 24 of 26.

### 3.2 The threshold

**F12 — ARGUED. `CLIP_MAX` stays at 0.001 — 0.1% of the frame — now that it is
attached to the right statistic.** In units a printer cares about: **one frame
pixel in a thousand with no recoverable highlight detail in any channel.** A
neutral all-channel pin is unrecoverable — there is no channel left holding the
value — whereas a single-channel pin still carries luminance in the other two and
survives a gamut-mapped print. The corpus maximum on the corrected statistic is
0.0691%, so the threshold sits **1.45× above the worst real master**: tight
enough to bite on a doubling, loose enough not to indict the corpus. Retaining
the number while changing the quantity is deliberate — the old value was never
wrong as a *fraction*, it was pointed at the wrong denominator.

### 3.3 Commissioning — pre-existing arms, re-run and cited

`experiments/ORCH-drift-check/commission_clip.py` on
`dry-erase-marker-head-cpl--SHIP-V3.tiff`, exit 0:

| arm | expect | got | clip (all-3) | gamut (old) |
|---|---|---|---|---|
| CLEAN | PASS | PASS | 0.0000% | 0.000% |
| NEUTRAL | FAIL | FAIL | 0.3840% | 0.384% |
| ONECHAN | PASS | PASS | 0.0000% | 0.128% |
| TINY | PASS | PASS | 0.0213% | 0.021% |

This covers sensitivity and specificity. It was **run and cited, not
duplicated**.

### 3.4 The four arms that were missing

`experiments/BUILD-GATE-PRINT/commission_printgate.py`, exit 0,
`COMMISSION PASSED`. It reads `CLIP_MAX` out of the gate's source with a regex
and aborts if it disagrees with its own copy, so the commissioning constant
cannot drift away from the gate it commissions.

**NULL ARM.**

```
partition : 17 PASS, 0 FAIL, 9 ACQUITTED, 0 ACQUITTAL EXPIRED, 0 REVIEW,
            0 NOT EXAMINED, 26 total (found 26)
exit code : 0
partition sums: 26 counted == 26 found
```

**F13 — MEASURED. The corrected gate issues ZERO FAIL over the 26 masters, and
this report says so out loud.** Its discriminating power on this corpus is
demonstrated **only** by plants. That is the "absent gate" risk the commission
warned about, and it is not disposed of by the plant arms — it is bounded by
them. The honest statement is: the gate bites when given something to bite, and
the corpus currently contains nothing that crosses the line.

**F14 — DERIVED. No acquittal can mask a clip failure.** Reading `verdict()`:
`fails` is populated by banding and clip alone, and a non-empty `fails` returns
`FAIL` immediately. `REVIEW` is therefore reachable only when `fails` is empty,
and `ACQUIT` only from `REVIEW`. The nine acquittals are structurally incapable
of hiding a clip FAIL — they waive blotch and chroma reviews. This matters
because "0 FAIL, 9 ACQUITTED" would otherwise be an obvious place for a failure
to hide.

**REGRESSION ARM** — read out of the *same* run as the null arm, so the two
cannot disagree:

| subject | verdict | clipALL3 | old statistic | under `CLIP_MAX`? |
|---|---|---|---|---|
| `dry-erase-marker-head-cpl` | PASS | 0.0000% | 0.0000% | YES |
| `flowers-cpl` | PASS | 0.0086% | 0.1430% | YES |
| `112MSDCF` | ACQUIT | 0.0691% | 0.0770% | YES |

**F15 — MEASURED. The zero-clipping master the old gate failed now passes, and
the subject the old gate passed while failing it is still not failed.**
`flowers-cpl` reads 0.1430% on the old statistic — over the 0.1% line, so the old
gate failed it — and 0.0086% on the corrected one.

**D3 — DISCIPLINE. A regression arm must assert the number as well as the
verdict glyph.** `112MSDCF` reads `ACQUIT`, not `PASS`, because of an unrelated
chroma review. A naive equality check on the glyph called that a failure. The arm
now asserts (a) the subject is in an outcome its clip prediction admits, **and**
(b) its clip statistic is genuinely under `CLIP_MAX` — because a subject that
passed for some reason *other* than being under the threshold satisfies (a) and
is exactly the silent pass this exercise is about.

**PLANTED ARMS** — on `dry-erase-marker-head-cpl`, the zero-clipping master, so
any clip the gate reads is the plant:

| arm | dose | expect | got | clip | gamut |
|---|---|---|---|---|---|
| SENS-4X | 4× `CLIP_MAX`, all 3 ch | FAIL | **FAIL** | 0.3840% | 0.384% |
| SPEC-40X | 40× `CLIP_MAX`, **one** ch | PASS | **PASS** | 0.0000% | 1.330% |
| DOSE-0P5X | 0.5× `CLIP_MAX` | PASS | **PASS** | 0.0427% | 0.043% |
| DOSE-2X | 2× `CLIP_MAX` | FAIL | **FAIL** | 0.1920% | 0.192% |

**F16 — MEASURED. The gate ignores a one-channel gamut pin TEN TIMES LARGER in
area than the neutral blow it fails.** SPEC-40X plants 3.99% of the frame with
one channel at the ceiling and reads clipALL3 **0.0000%** while the old statistic
reads 1.330% — thirteen times the threshold. That single row is the whole
correction.

**F17 — MEASURED. The threshold is bracketed within a factor of four on the same
plant.** 0.5× passes, 2× fails. The gate respects its own number rather than
firing on presence.

Every arm also asserts its partition (`1 total (found 1)`) and, where a FAIL is
expected, the **failure-reason substring** — so an arm cannot be satisfied by the
right verdict reached for the wrong reason, and a skipped subject cannot read as
a passed one.

### 3.5 Crush is reported and cannot vote — and the first two attempts to prove it were wrong

**F18 — MEASURED. A crush dose ladder up to 5% of the frame moves crush and
nothing else, and every rung PASSES.**

| rung | crush | blotch | verdict | reason |
|---|---|---|---|---|
| CLEAN | 0.000% | 0.00446 | PASS | — |
| CRUSH-1PC | 0.981% | **0.00446** | PASS | (none) |
| CRUSH-2P5PC | 2.496% | **0.00446** | PASS | (none) |
| CRUSH-5PC | 4.992% | **0.00446** | PASS | (none) |
| CRUSHBAND | 9.983% | 0.02742 | REVIEW | blotch 0.0274 |
| CRUSHSPARSE | 10.006% | 0.25219 | REVIEW | blotch 0.2522; chroma 0.0296 |

Blotch is pinned at its clean value `0.00446` for the first three rungs, and
**4.992% is above the corpus maximum of 3.639%** — so this is a genuine
single-variable arm carried past the range real data occupies.

**F19 — MEASURED. Above 5% no plant geometry is single-variable, and this lane's
own first fix was refuted by its own instrument.** A contiguous 10% black band
drives blotch 0.00446 → 0.02742 and trips `BLOTCH_REVIEW = 0.02`, because
`blotch_ratio` is `std(band)/MEAN` and a large black region collapses the
denominator. Scattering the same dose was *predicted* to leave blotch alone, on
the argument that both boxblurs remove single-pixel structure. **It does not:**
blotch goes to **0.25219**, ten times worse than the band, because a difference
of box filters at two radii does not cancel an injection that large. The
prediction was written before the run, the run refuted it, and the arm is kept in
the script for that reason.

**F20 — MEASURED. No verdict is ever attributed to crush.** Across CLEAN and all
five rungs — *including the two whose verdict did move* — the verdict-bearing
text after `<==` names blotch and chroma and **never** crush: `rungs naming crush
in a reason: NONE (0 of 5)`; `rungs FAILED: NONE (0 of 5)`.

**D4 — DISCIPLINE. "The verdict did not move" is not a proof that a statistic is
ungated, when the plant perturbs a second statistic.** The check that survives
confounding is the **reason string**: which statistic the gate *names* when it
speaks. Note the trap — searching the whole detail line for `crush` fires on
every arm, because the gate **reports** `crush N%` by design. Only the segment
after `<==` is verdict-bearing. This lane's first version of the check made
exactly that mistake and reported a false alarm.

**F21 — MEASURED, and the strongest line, because it has no plant and therefore
no confounder. Real masters carry heavy crush and pass.** `109MSDCF` reads crush
**2.470%** and its verdict is **PASS**, unqualified. `119MSDCF` reads 3.260%,
PASS. The corpus maximum is 3.639%. Any threshold below 2.470% must fail a good
master; any threshold above 3.639% is inert. **There is no threshold to set** —
which is the operational form of "do not re-gate it".

### 3.6 Reporting shape

**D5 — DISCIPLINE. Clipping and crush are printed as numbers beside their
subject, never as a bare verdict**, and the column that gates (`clipALL3`) is
printed next to the column that does not (`gamut`), so a reader can see the two
statistics disagree rather than being told they do.

**D6 — DISCIPLINE. Every input lands in a counted outcome and the counts are
asserted to sum.** The gate prints `26 total (found 26)` and returns 2 if the
partition does not sum; each plant arm asserts `1 total (found 1)`. A count that
does not move is the same glyph whether nothing was wrong or nothing was
examined.

### 3.7 Known non-finding

`flowers-cpl` will still trip `CLIP_MAX` after the corpus re-render now in
flight. Bounding it properly needs a **per-channel** rather than per-luminance
tone stage, which is a corpus-wide change nobody has authorised. Noted, not
re-diagnosed.

---

## 4. Verified vs. assumed

**Verified by measurement:** F1, F4, F5, F6, F7, F8, F9, F10, F11, F13, F15,
F16, F17, F18, F19, F20, F21 — each has the command output above or in the lane
transcript.

**Derived from source reading, not executed:** F2 (an example target is not
linked into `strehl`), F3 (`displacement_at` has no non-test callers), F14 (the
`fails`/`REVIEW`/`ACQUIT` control flow).

**Argued, not proved:** F12 — the *value* 0.001 is a judgement about print
tolerance. What is measured is the corpus distribution beneath it and the
bracketing at 0.5× and 2×. Nobody has printed a 0.1%-clipped master and looked at
it, and until someone does, the number is defensible rather than validated.

**Assumed:** that `C:\dev\strehl-out\acceptance\SHIP-V3` is the corpus the
print-readiness claim refers to. `DELIVER-V5\print-masters` and
`V-NEVERWORSE\masters` vanished mid-session as other lanes churned; SHIP-V3 is
the arm the threshold provenance was measured on, so it is the one used.
`SHIP-V2` no longer exists, so BUILD-OUTPUT's original 0.3265% dry-erase failure
could not be re-measured on its own arm — `flowers-cpl` is the live equivalent.

---

## 5. Two collisions that need somebody's decision

### 5.1 The gate's path

The brief specified `scripts/orch_printready.py`. The script lives at
`experiments/ORCH-drift-check/orch_printready.py`. Nothing at the given path.

### 5.2 This report's filename

The brief specified `docs/research/BUILD-GATE.md`. **That file exists**, is
22 049 bytes, and holds a different lane's committed report on the band-noise
gate (`8457dfc2`). `BUILD-GATE-2/-3/-4.md` are continuations of that same
investigation, so a `-5` suffix would masquerade as a fifth instalment of an
unrelated series. This report is therefore `BUILD-GATE-PRINT.md`, with precedent
in `BUILD-PYRNOISE-ADJUDICATION.md`; the `why` column committed to the registry
cites that name. Experiments are under `experiments/BUILD-GATE-PRINT/` for the
same reason.

---

## 6. Proposed facts

Numbered locally; the orchestrator allocates absolute numbers at fold. **This
lane did not edit `SYNTHESIS.md`.**

**F6/F7 together are the row worth folding:** the byte-freeze registry's
red row was one constant, and reverting that constant reproduces the superseded
hash bit-for-bit while the unaligned control is invariant under both values.

**F19 is the methodological row:** a commissioning plant large enough to move
one statistic decisively may move a second, and the check that survives the
confound is which statistic the gate *names*, not whether the verdict moved.

**F13 is the caveat that must travel with any print-readiness claim:** the
corrected gate issues zero FAIL on the 26 masters, so on this corpus it is
evidenced only by plants.
