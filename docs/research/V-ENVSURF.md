# V-ENVSURF: every `STREHL_*` variable, classified on the shipping default path

Pin `ba34142806cf`, binary sha256
`EE7A302963B7657CEBAE5BAFB5D8E5628E41EBF92213EB935401CEDDF37C4C5C`, copied out of
`target/release/` before measurement and run from that copy, because the shared
`target/` was rebuilt by another lane **during** this survey (section 7). Subject
`D:\personal\macro\coffee-bubbles`, command line
`stack <dir> --out <tif> -l 3 --srgb`, backend `pyramid` with **no `--merge`
flag** -- the path that ships. 197,801,290 bytes per render; every TIFF hashed
and deleted immediately. **All `file:line` citations are at the pin**, which has
already drifted from the working tree (`run_pyramid` is `merge_cmd.rs:5280` at
the pin and `:5316` in the tree as this was written).

## Verdict

**The env channel has 23 of 46 variables in the `STREHL_SOFT_GATE` class, and
`NOT-REACHED-BY-DESIGN` is EMPTY: not one of the 46 is refused under the pyramid
backend the way the estimator-only FLAGS are.** Fact 1882 is not an isolated
variable, it is a channel-wide property. `stack --help` states that the
estimator-only flags "are REFUSED under the pyramid backend rather than accepted
and ignored"; the environment channel implements the opposite policy across half
its surface.

| bucket | count | what it means on the pyramid default path |
|---|---:|---|
| `LIVE` | **14** | read, rejects garbage, effect demonstrated |
| `LIVE-UNVALIDATED` | **7** | changes the render, but a typo is accepted |
| `INERT-VALIDATED` | **1** | no effect, but a typo is refused |
| `DEBUG-ONLY` | **1** | side file appears, image byte-identical by design |
| `INERT-SILENT` | **23** | no effect AND a typo is accepted |
| `NOT-REACHED-BY-DESIGN` | **0** | -- |
| **total** | **46** | |

**46 attempted = 46 measured + 0 refused + 0 void.** Three variables
(`STREHL_DEFECT`, `STREHL_DEFECT_MAP`, `STREHL_SMOOTH_HUBER`) needed a second
subject or a deeper bracket before their effect appeared; that is recorded per
row rather than folded into a null. Section 9 lists what stayed unmeasured.

## 1. Commissioning the comparator, before any "no change" was trusted

A comparator that cannot see a real change reports byte-identical for
everything, and would have classified all 46 as inert. Two controls, on the
identical command line:

| arm | sha256 | reads |
|---|---|---|
| baseline, run 1 | `C5E59BC931C3AD93E08317CF4F0657E678648B9B19EA6E361BEA78A0EF568F55` | -- |
| baseline, run 2 | `C5E59BC931C3AD93E08317CF4F0657E678648B9B19EA6E361BEA78A0EF568F55` | **DETERMINISTIC** |
| `-l 4` instead of `-l 3` | `7900B76C369386A991F5B98A181745089EDB5895C471D86A5DB76E108C70AD92` | **DIFFERENT** |

The instrument is repeatable and it responds. The baseline hash and the byte
count reproduce ORCH's numbers exactly, so this lane and the commissioning lane
are measuring one artifact. Every hash in this document was re-derived from
scratch in a final pass after the ledger was drafted, and every one reproduced.

A second, unplanned commissioning came out of the survey itself:
`STREHL_SMOOTH=off` and `STREHL_WARPMAP=<sidecar solved with STREHL_SMOOTH=off>`
land on the **same** hash `CE2264BDEF181DE0...` through two unrelated code paths.
A comparator agreeing with itself across two channels is better evidence than a
planted delta.

## 2. Method, stated so it can be attacked

1. **Static first.** Every read site was located and traced for reachability
   from `run_pyramid` (`merge_cmd.rs:5280`) **before** any run. Static reading
   produced the prediction; the runtime arm was the test of it. Section 6 lists
   the four places the two disagreed.
2. **Every arm has a matched unset control on the identical command line.** The
   pyramid control is one hash because the render is deterministic (section 1);
   estimator arms carry their own control `11AA9411190CE1E5...` because that
   command line differs. This is fact 1883 and it is load-bearing:
   `--merge estimator` **without** `--photometric off` exits 1 on this subject
   with `U3 the eroded low-detail region keeps only 0 px`, an error that has
   nothing to do with any variable under test.
3. **The bucket is assigned from the variable set ALONE** on the shipping
   default command line. A variable needing a companion is bucketed on its
   alone-behaviour and annotated `cond:`. This is the only rule that keeps the
   count a partition; conditional behaviour is reported in the same row and in
   section 4, tier 3.
4. **Path-valued variables are scored on the artifact, not the image**
   (`*_MAP`, `*_DUMP`, `STREHL_CACHE_DIR`, `STREHL_WARPMAP`).
5. Garbage is `zzznope`, a string that names nothing anywhere in the tree.

## 3. The ledger

`A` cites the read site at the pin and whether any call chain from `run_pyramid`
reaches it. `B` is `zzznope`. `C` is a plausible non-default value. `SAME` means
byte-identical to the unset control `C5E59BC931C3AD93...`.

| # | variable | A: read site / reached? | B: `=zzznope` | C: value -> image | bucket |
|---:|---|---|---|---|---|
| 1 | `STREHL_ACUITY` | `merge_cmd.rs:1965` -- **no** | rc=0 SAME | `0` -> SAME | `INERT-SILENT` |
| 2 | `STREHL_ALIGN` | `align_cmd.rs:1272` -- yes | rc=0 SAME | `0` -> **DIFF** `EE1AD7DA2CAB88F9` | `LIVE-UNVALIDATED` |
| 3 | `STREHL_BIMODAL_DUMP` | `merge_cmd.rs:2019` -- **no** | rc=0 SAME | path -> **no side file** | `INERT-SILENT` |
| 4 | `STREHL_BUILD_ID` | `build.rs:101` -- **compile time only** | rc=0 SAME | `vtest` -> SAME | `INERT-SILENT` |
| 5 | `STREHL_CACHE_DIR` | `align_cmd.rs:1396` -- yes | rc=0, dir created | dir -> **sidecar written there** | `LIVE` |
| 6 | `STREHL_CONFIDENCE_DEBUG` | `merge_cmd.rs:5652` -- yes, gated | rc=0 SAME | dir -> no side file | `INERT-SILENT` `cond:CONFIDENCE_MAP` |
| 7 | `STREHL_CONFIDENCE_MAP` | `merge_cmd.rs:4758` -- yes | **rc=1** `creating zzznope` | path -> **`conf.tif` written** | `LIVE` |
| 8 | `STREHL_COVER` | `align_cmd.rs:1047` -- yes | **rc=1**, names the modes | `crop` -> **DIFF** `72AAFB43F62DCA46` | `LIVE` |
| 9 | `STREHL_DEFECT` | `stack.rs:884` -- yes | **rc=1** | `on` -> **DIFF** on `109MSDCF` | `LIVE` |
| 10 | `STREHL_DEFECT_ARM` | `stack.rs:911` -- not unless defect on | rc=0 SAME | `none` -> SAME | `INERT-SILENT` `cond:DEFECT=on` |
| 11 | `STREHL_DEFECT_HOT_FLOOR` | `stack.rs:915` -- not unless defect on | rc=0 SAME | `200` -> SAME | `INERT-SILENT` `cond:DEFECT=on` |
| 12 | `STREHL_DEFECT_MAP` | `stack.rs:897` -- yes | **rc=1** | real map -> **DIFF** on `109MSDCF` | `LIVE` |
| 13 | `STREHL_DEMOSAIC` | `demosaic.rs:323` -- yes | rc=0 SAME | `directional` -> **DIFF** `D4D10F9A3853536A` | `LIVE-UNVALIDATED` |
| 14 | `STREHL_DUMP_ELECTION` | `merge_cmd.rs:2451` -- **no** | rc=0 SAME | path -> **no side file** | `INERT-SILENT` |
| 15 | `STREHL_DUMP_MERGE_STATE` | `dump.rs:50` -- **no** | rc=0 SAME | dir -> **no side file** | `INERT-SILENT` |
| 16 | `STREHL_DUMP_NEFF` | `merge_cmd.rs:2792` -- **no** | rc=0 SAME | path -> **no side file** | `INERT-SILENT` |
| 17 | `STREHL_EDGE_AWARE` | `merge_cmd.rs:1928` -- **no** | rc=0 SAME | `off` -> SAME | `INERT-SILENT` |
| 18 | `STREHL_EDGE_CONF` | `merge_cmd.rs:1817` -- **no** | rc=0 SAME | `8` -> SAME | `INERT-SILENT` |
| 19 | `STREHL_EDGE_FEATHER` | `edgeaware.rs:854` -- **no** | rc=0 SAME | `4` -> SAME | `INERT-SILENT` |
| 20 | `STREHL_EDGE_TAU` | `merge_cmd.rs:1981` -- **no** | rc=0 SAME | `8` -> SAME | `INERT-SILENT` |
| 21 | `STREHL_FIX_CA` | `optics.rs:678`, preflighted `merge_cmd.rs:5231` -- yes | **rc=1**, lists profiles | `off` -> **DIFF** `873F201BB7D3974D` | `LIVE` |
| 22 | `STREHL_FIX_HALO` | `merge_cmd/halo.rs:113` -- **no** | rc=0 SAME | `on` -> SAME | `INERT-SILENT` |
| 23 | `STREHL_FIX_HALO_DELTA` | `merge_cmd/halo.rs:124` -- **no** | rc=0 SAME | `80` -> SAME | `INERT-SILENT` |
| 24 | `STREHL_FULLRES_GATHER` | `align_cmd.rs:1216` -- yes | **rc=101** panic | `0` -> **DIFF** `13D80070BF3CFD2E` | `LIVE` |
| 25 | `STREHL_GATE_FLOOR` | `gatefloor.rs:95` -- yes | rc=0 SAME | `white` -> **DIFF** `15567BBF54902787` | `LIVE-UNVALIDATED` |
| 26 | `STREHL_GATE_FLOOR_SCALE` | `gatefloor.rs:126` -- yes | **rc=101** panic | `1,4,4,4,4,4,4` -> **DIFF** `1EF1F9B6E77EC593` | `LIVE` |
| 27 | `STREHL_HIGHLIGHT_KNEE` | `highlight.rs:175` -- yes | rc=0 SAME, **warns** | `off` -> **DIFF** `24007472D35821C1` | `LIVE-UNVALIDATED` |
| 28 | `STREHL_HULL` | `pyramid.rs:767` -- yes | **rc=101** panic | `unclamped` -> **DIFF** `C253AF6B43FE2942` | `LIVE` |
| 29 | `STREHL_MERGE` | `merge_cmd.rs:566` -- yes | **rc=1** | `estimator` -> **DIFF**, identical to the flag | `LIVE` |
| 30 | `STREHL_ONLY_FRAME` | `merge_cmd.rs:1797` -- yes | **rc=101** panic | `1` -> **DIFF** `0D25E2572481420D` | `LIVE` |
| 31 | `STREHL_PHOTOMETRIC` | `merge_cmd.rs:2662` -- yes | **rc=1** | `off` -> SAME | `INERT-VALIDATED` |
| 32 | `STREHL_PYRAMID_MEAN_COARSE` | `pyramid.rs:726` -- yes | **rc=101** panic | `2` -> **DIFF** `5CC2634AAC0CBE97` | `LIVE` |
| 33 | `STREHL_PYRAMID_WEIGHT_DUMP` | `pyramid.rs:708` -- yes | rc=0, **25 files** | prefix -> **25 files**, image SAME | `DEBUG-ONLY` |
| 34 | `STREHL_PYRAMID_WORKERS` | `merge_cmd.rs:5192` -- yes | **rc=1** | `1` -> banner `3 -> 1 workers`, image SAME | `LIVE` |
| 35 | `STREHL_RESTORE` | `restore.rs:1243` -- yes | rc=0 SAME, **warns** | `4.0` -> stage RUNS, image SAME | `LIVE-UNVALIDATED` |
| 36 | `STREHL_RESTORE_SIGMA` | `restore.rs:1288` -- not unless restore on | rc=0 SAME | `4.0` -> SAME | `INERT-SILENT` `cond:RESTORE>1` |
| 37 | `STREHL_ROBUST_ELECTION` | `merge.rs:723` -- **no** | rc=0 SAME | `on`/`hard`/`ungated` -> SAME | `INERT-SILENT` |
| 38 | `STREHL_SMOOTH` | `align_cmd.rs:585` -- yes | rc=0 SAME, **warns** | `off` -> **DIFF** `CE2264BDEF181DE0` | `LIVE-UNVALIDATED` |
| 39 | `STREHL_SMOOTH_HUBER` | `align_cmd.rs:603` -- yes | rc=0 SAME, **silently means `off`** | `0.2` at `-l 19` -> **DIFF** `3DD8B18813DA2515` | `LIVE-UNVALIDATED` |
| 40 | `STREHL_SOFT_GATE` | `merge.rs:682` -- **no** | rc=0 SAME | `gaussian`, `exponential` -> SAME | `INERT-SILENT` |
| 41 | `STREHL_VEIL` | `merge_cmd.rs:2719` -- **no** | rc=0 SAME | `1` -> SAME | `INERT-SILENT` |
| 42 | `STREHL_VEIL_DISPERSION` | `merge_cmd.rs:3947` -- **no** | rc=0 SAME | `1` -> SAME | `INERT-SILENT` |
| 43 | `STREHL_VEIL_FLOOR` | `merge_cmd.rs:2773` -- **no** | rc=0 SAME | `0.5` -> SAME | `INERT-SILENT` |
| 44 | `STREHL_VEIL_MARGIN` | `merge_cmd.rs:2752` -- **no** | rc=0 SAME | `2` -> SAME | `INERT-SILENT` |
| 45 | `STREHL_WARPMAP` | `merge_cmd.rs:2383` -- yes | **rc=1** | alt sidecar -> **DIFF** `CE2264BDEF181DE0` | `LIVE` |
| 46 | `STREHL_WINDOW_RADIUS` | `focus.rs:110` -- **no** | rc=0 SAME | `8` -> SAME | `INERT-SILENT` |

## 4. The `INERT-SILENT` list, ranked -- the fix list

Ranked by how much a user could believe the knob did something, which is the
severity that matters for this defect class.

### Tier 1a -- proven to work on the estimator, silently dead on the shipping backend

Two variables. These are the strongest cases: the same value that visibly moves
the estimator render moves nothing here, exit 0, no message.

| variable | estimator, same subject | pyramid |
|---|---|---|
| `STREHL_SOFT_GATE` | `gaussian` -> `0A82D57A3B3D044B`, `exponential` -> `318BFC71D2D5AF03`, both **DIFF** from `11AA9411190CE1E5` | both **SAME** as baseline |
| `STREHL_EDGE_AWARE` | `off` -> `A4A2AC6CB41C2424`, **DIFF** | **SAME** |

**Recommendation for both: make them an error under pyramid**, exactly as the
estimator-only flags already are.

### Tier 1b -- validated on the estimator, silent here

The estimator refuses a bad value; the pyramid accepts it and does nothing. The
refusal machinery exists and is simply not on this path.

| variable | estimator | pyramid |
|---|---|---|
| `STREHL_EDGE_AWARE` | `zzznope` -> **rc=101** `merge_cmd.rs:193x` | rc=0 SAME |
| `STREHL_EDGE_TAU` | `zzznope` -> **rc=101** `merge_cmd.rs:198x` | rc=0 SAME |
| `STREHL_WINDOW_RADIUS` | `zzznope` -> **rc=101** `focus.rs:114` | rc=0 SAME |
| `STREHL_VEIL` | `1` -> **rc=1**: *"STREHL_VEIL needs --photometric on (or auto)"* | rc=0 SAME |
| `STREHL_SOFT_GATE` | `zzznope` -> **rc=101** (fact 1882) | rc=0 SAME |

**Recommendation: make them an error under pyramid.**

### Tier 2 -- diagnostics that write nothing and say nothing

`pyramid.rs:701` names this failure in its own words: *"a diagnostic that quietly
writes nothing is indistinguishable at the terminal from one that found nothing
to report."* Four variables do exactly that on the backend that ships. Both
columns measured on the same subject, same `-l 3`, same scratch directory
emptied between arms:

| variable | estimator writes | pyramid writes |
|---|---|---|
| `STREHL_BIMODAL_DUMP` | `guide.raw`, `radius.raw`, `first_mode_z.raw`, `second_mode_z.raw` | **nothing** |
| `STREHL_DUMP_ELECTION` | `elect.tif` | **nothing** |
| `STREHL_DUMP_MERGE_STATE` | `best_focus.npy`, `best_index.npy`, `n_eff_gate4.00.npy` | **nothing** |
| `STREHL_DUMP_NEFF` | `neff.tif` | **nothing** |

**Recommendation: make them an error under pyramid.** A diagnostic is the one
category where silence is indistinguishable from a clean result, so this tier
outranks its image-effect severity.

### Tier 3 -- inert alone, live with a companion

These become validated the moment their companion is set. Setting one alone is a
silent no-op; the parse that would have caught the typo is behind a condition.

| variable | companion | with the companion set |
|---|---|---|
| `STREHL_DEFECT_ARM` | `STREHL_DEFECT=on` | `zzznope` -> **rc=1**; `none` returns `109MSDCF` to the unset hash exactly |
| `STREHL_DEFECT_HOT_FLOOR` | `STREHL_DEFECT=on` | `zzznope` -> **rc=1** *"is not a number of electrons"* |
| `STREHL_RESTORE_SIGMA` | `STREHL_RESTORE=4.0` | `zzznope` -> **rc=101** `restore.rs:1297`; `4.0` scales `sigma2` 699.3 -> 2797.4 DN^2 |
| `STREHL_CONFIDENCE_DEBUG` | `STREHL_CONFIDENCE_MAP` | writes `dmin`, `dsharp`, `spread`, `centrality`, `withinfrac` tiffs |

**Recommendation: validate the sub-knob whenever it is set**, not only when the
parent is on. The parser is already written; only the call site is conditional.

### Tier 4 -- no effect and no validation on EITHER backend

Measured, not assumed: each was run on the estimator as well, and every one
returned rc=0 with the estimator control hash `11AA9411190CE1E5`.

| variable | estimator `zzznope` | estimator plausible value | recommendation |
|---|---|---|---|
| `STREHL_ACUITY` | rc=0 SAME | `0` -> SAME | **delete, or wire it in** |
| `STREHL_EDGE_CONF` | rc=0 SAME | -- | **delete, or wire it in** |
| `STREHL_EDGE_FEATHER` | rc=0 SAME | -- | **delete, or wire it in** |
| `STREHL_FIX_HALO` | rc=0 SAME | -- | **delete, or wire it in** |
| `STREHL_FIX_HALO_DELTA` | -- | `80` -> SAME | **delete, or wire it in** |
| `STREHL_VEIL_MARGIN` | rc=0 SAME | -- | **delete, or wire it in** |
| `STREHL_VEIL_FLOOR` | -- | `0.5` -> SAME | **delete, or wire it in** |
| `STREHL_VEIL_DISPERSION` | -- | `1` -> SAME | **delete, or wire it in** |
| `STREHL_ROBUST_ELECTION` | rc=0 SAME | `on`, `hard`, `ungated` all -> `11AA9411190CE1E5` | **delete, or wire `active_arm()` in** |

`STREHL_ROBUST_ELECTION` is the sharpest of these. `robust.rs:313` states the
module "has been dead code since it was written" and that a producer was "ported
so the election can be reached from the product" -- yet all four settings
(`unset`, `on`, `hard`, `ungated`) hash `11AA9411190CE1E5` on the estimator and
`C5E59BC931C3AD93` on pyramid at `-l 3`, and `A59982E8EFF295E2` on pyramid at
`-l 19`. **The port did not reconnect it to the render.** The three veil
sub-knobs are inert because their parent is refused without `--photometric on`;
that is a reason, not an exoneration, since nothing tells the caller.

### Not a defect

`STREHL_BUILD_ID` is read by `build.rs:101` at **compile time** and consumed
through `env!()`. It has no runtime read site and cannot be exercised by a run.
It lands in `INERT-SILENT` because the bucket is defined by runtime behaviour,
and it must be **excluded from the fix list**. Recommendation: document it as
build-time. Net fix list: **22 variables**, not 23.

## 5. The `LIVE-UNVALIDATED` list -- these work, and misbehave on a typo

| variable | what a typo does | severity |
|---|---|---|
| `STREHL_SMOOTH_HUBER` | **silently reconfigures the solve to `off`.** `.parse().ok().filter(...)` maps any unparseable value to `None`, the same state `off` selects. Measured at `-l 19`: `0.2` -> `3DD8B18813DA2515`, while `off` and `zzznope` both -> `A59982E8EFF295E2`, the unset hash. The robust threshold is discarded without a word | **highest** |
| `STREHL_ALIGN` | anything outside the off-spellings leaves registration ON; `zzznope` renders the baseline while `0` renders `EE1AD7DA2CAB88F9` | high |
| `STREHL_GATE_FLOOR` | anything not equal to `white` selects the default; `zzznope` renders the baseline while `white` renders `15567BBF54902787` | high |
| `STREHL_DEMOSAIC` | only `eq_ignore_ascii_case("directional")` is tested, every other string is the Malvar default; `directional` renders `D4D10F9A3853536A` | high |
| `STREHL_SMOOTH` | falls back to the default lambda, **but prints a warning** | medium |
| `STREHL_HIGHLIGHT_KNEE` | falls back to the default knee, **but prints a warning** | medium |
| `STREHL_RESTORE` | declines to run, **but prints a warning** naming the reason | medium |

**Recommendation for all seven: refuse rather than default** -- the rule
`STREHL_FULLRES_GATHER`, `STREHL_HULL`, `STREHL_ONLY_FRAME`,
`STREHL_PYRAMID_MEAN_COARSE` and `STREHL_GATE_FLOOR_SCALE` already follow in the
same binary. Five variables here already do it right; the split is a choice made
file by file, not a policy. `STREHL_HULL`'s own doc comment cites the `--merge`
help for its reason -- the identical sentence the env channel violates 23 times.

## 6. Where static reading and the runtime disagreed

Four disagreements. All four resolved in favour of the runtime; three changed a
classification, and one changed the shape of the finding this lane was
commissioned to confirm.

**6.1 `STREHL_RESTORE=4.0` -- static said reachable, hash said nothing
happened.** `run_pyramid` calls `restore::gain_cap_from_env()`, so the read is on
the shipping path, and the render is byte-identical anyway. **The stage runs.**
The unset control prints no restore line at all; the `4.0` arm prints

    restore R       : cap 4.000, max gain 1.0000 (2-D 1.0000), at Nyquist 1.0000,
                      recovered 0.0000, mean 302.0 DN, sigma2 699.3 DN^2

The gain saturates at the identity, which `restore.rs:1271` predicts in as many
words ("measured never to bind"). The variable is read, the stage executes, the
pixel delta is zero. Classified `LIVE-UNVALIDATED` with the zero delta stated,
not hidden.

**6.2 `STREHL_RESTORE_SIGMA=zzznope` -- static said it panics, runtime exited
0.** `sigma_scale_from_env()` panics on a non-number and says why at
`restore.rs:1300`: *"a mis-set instrument that reads plausibly is worse than one
that stops."* It exits 0 because the function is never called: with
`STREHL_RESTORE` unset there is no plan and nothing asks for the sigma. Set both
and it panics as advertised. **The refusal exists and is unreachable from the
default configuration** -- which is the same defect shape as the rest of this
report, in the validation layer rather than the effect layer.

**6.3 `STREHL_PYRAMID_WORKERS=1` -- static said the fold partition changes, hash
said byte-identical.** It does change: `memory plan : 3 workers x 1328 MB =
3.9 GB` becomes `1 workers x 1328 MB = 1.3 GB`, and the fold slows. The render is
byte-identical because the accumulator sums in frame order either way, so 3x1
and 1x3 evaluate the same expression. Byte-invariance here is a **correctness
property**, not inertness. Classified `LIVE` on the banner evidence.

**6.4 ORCH's `STREHL_SOFT_GATE=on` is not a valid setting, and the 2x2 has three
cells.** `kernel_from_setting` (`merge.rs:650`) accepts `""`, `0`, `off`,
`false` (all meaning no kernel), `gaussian`, `exponential`, and errors on
everything else. `on` falls in the error arm, so ORCH's `=on` column and its
`=zzznope` column are **the same experiment**. Re-run with the real kernel
names, the finding survives and sharpens: on the estimator `gaussian` ->
`0A82D57A3B3D044B` and `exponential` -> `318BFC71D2D5AF03`, both differing from
the estimator control; on pyramid both render the baseline hash exactly. **The
knob is real, it works, and it is silently dead on the backend that ships** --
a stronger statement than the one the 2x2 supported.

## 7. What moved under me: a 47th variable, and a partial fix

The shared `target/release/strehl.exe` was rebuilt mid-survey:
`EE7A3029...` -> `55E0C07E8BC74DAB7BEAAE3890458F5637C9C813EBEB2A69B9D34B9D9B6F62A7`,
`ba34142806cf` -> `165074a1606a-dirty`. Both binaries were copied out and hashed,
so both columns are attributable. Two working-tree changes matter here:

1. **`merge_cmd.rs` gains `preflight_soft_kernel()`**, called from `run()` before
   the backend dispatch. It is in neither `ba34142806cf` nor `HEAD` -- working
   tree only.
2. **`pyramid.rs` gains `STREHL_PYRAMID_SIGNIFICANCE`**, a **47th** variable that
   did not exist when this lane's list was drawn.

Re-running the full garbage sweep on the new binary (47 variables, unset control
`369D4FC2468E20F98D530AFFA2565E3D4AC093EA2994AB6A9EDBBA819F8F78DB`) shows
**exactly one row moved**: `STREHL_SOFT_GATE=zzznope` goes rc=0 -> **rc=1**. The
new variable arrives validated (`zzznope` -> rc=101). The other 45 rows are
unchanged, so the ledger above stands on the newer build too.

**The fix closes the typo hole and not the inert hole.** On the new binary
`STREHL_SOFT_GATE=gaussian` still exits 0 and still renders
`369D4FC2468E20F9...`, byte-identical to its control. A caller who spells the
kernel *correctly* is still told nothing and still gets nothing. The bucket moves
`INERT-SILENT` -> `INERT-VALIDATED`, an improvement of exactly one step of two.
Refusing an unknown value is not the guarantee `stack --help` makes; refusing a
value the backend cannot honour is.

## 8. An edge the survey found on its own: empty string is not a policy

`""` is how a harness clears an inherited variable. The tree handles it three
different ways on one command line.

| variable | `=""` on the pyramid default path |
|---|---|
| `STREHL_COVER`, `STREHL_PHOTOMETRIC` | treated as "nobody asked" -- rc=0, documented |
| `STREHL_DUMP_ELECTION`, `STREHL_SOFT_GATE`, `STREHL_FULLRES_GATHER`, `STREHL_WINDOW_RADIUS` | rc=0, no effect |
| `STREHL_PYRAMID_WEIGHT_DUMP` | **rc=101** `pyramid.rs:712` -- intended |
| `STREHL_ONLY_FRAME` | **rc=101** `merge_cmd.rs:1803` |
| `STREHL_DEFECT` | **rc=1** `STREHL_DEFECT="" is not a setting` |
| `STREHL_HULL` | **rc=101** `pyramid.rs:773` -- **not** intended |

`STREHL_HULL=` (empty) aborts the shipping default render:

    thread 'main' panicked at crates\strehl-core\src\pyramid.rs:773:22:
    STREHL_HULL="" is not one of input-range, per-level, unclamped

`hull_default()` matches the trimmed string against three names and panics on the
fall-through; `""` reaches the fall-through while unset takes the `Err(_)` arm.
Unset is fine, cleared is a crash. Recommendation: **treat `""` as unset** in
`hull_default()`, the way `STREHL_COVER` already does.

## 9. What I could not measure

Recorded as skips, not passes.

| variable | why the effect arm is incomplete |
|---|---|
| `STREHL_VEIL` and its three sub-knobs | the estimator refuses the veil without `--photometric on`, and `--photometric on` exits 1 on this subject with `U3 ... keeps only 0 px`. The **pyramid** classification is unaffected (silent, no effect); what is unmeasured is whether they do anything anywhere |
| `STREHL_DEFECT_HOT_FLOOR` | the hot arm corrected 0 sites on every subject tried (`examined 0, corrected 0`). Its parse is reached and validated under `STREHL_DEFECT=on`; its pixel effect is undemonstrated |
| `STREHL_RESTORE`, `STREHL_RESTORE_SIGMA` | the stage runs and the parameter propagates (`sigma2` x4 in the banner), but `max gain` reads 1.0000 here so the pixel delta is structurally zero. A subject where the gain binds would be needed |
| `STREHL_ACUITY` | `0` and `zzznope` are both byte-identical on **both** backends. Either the term is inert as shipped or it sits behind a condition this subject does not meet |
| `STREHL_CACHE_DIR` | scored on the artifact. A path on a missing volume prints `could not cache sidecar (os error 3); continuing` and re-solves, rc=0, image SAME -- loud degradation, not silent |
| `STREHL_EDGE_CONF`, `STREHL_EDGE_FEATHER`, `STREHL_FIX_HALO*` | inert on both backends here. Whether some other command or subject reaches them is untested; only `stack` was surveyed |
| all 46 | one subject, one exposure, `-l 3` except where noted. `STREHL_DEFECT` and `STREHL_SMOOTH_HUBER` both read SAME on `coffee-bubbles -l 3` and DIFF elsewhere -- the measured warning that a single-subject null is weak evidence, and the reason section 4 separates "inert here" from "inert everywhere I looked" |

## 10. What would falsify this

- **The partition.** Any variable shown to change the pyramid render at a value
  I did not try leaves `INERT-SILENT` and the count of 23 is wrong. The cheapest
  attack is `STREHL_ACUITY` and the veil knobs, where the plausible value is a
  guess at the author's intent.
- **The comparator.** If SHA256 over the TIFF can miss a change the merge made,
  every `SAME` is void. Two controls argue otherwise (section 1) and one of them
  was not planted by me.
- **The binary.** Sections 1-6 and 8-9 are `ba34142806cf`. Section 7's sweep is
  `165074a1606a-dirty`, whose working tree is uncommitted and may not survive. A
  third build could move rows again; the method is one command per row.
- **`STREHL_ROBUST_ELECTION`.** The claim that it is byte-inert on both backends,
  at `-l 3` and `-l 19`, for all three settings, is the strongest claim in this
  document and the easiest to break. One render where it moves a byte refutes the
  "delete it" recommendation outright.
- **Tier 4.** Each row asserts a null on two backends from one subject. A subject
  with the structure the knob is aimed at -- a real halo for `STREHL_FIX_HALO`, a
  real veil for the veil knobs -- could move any of them out of tier 4 and into
  tier 1a, which would make them more urgent, not less.

## 11. Post-audit re-verification on the landed build

ORCH amended the brief after this ledger was measured, requiring the binary to be
pinned, the pin to be *commissioned* rather than assumed, and the shared binary to
be re-hashed at the end. All three were done. The pin discipline is vindicated by
measurement: **the shared `target/release/strehl.exe` took three distinct
identities in 102 minutes.**

| # | sha256 | `LastWriteTime` | bytes | version |
|---:|---|---|---:|---|
| 1 | `EE7A302963B7657CEBAE5BAFB5D8E5628E41EBF92213EB935401CEDDF37C4C5C` | 00:01:35 | 9,858,048 | `ba34142806cf` |
| 2 | `55E0C07E8BC74DAB7BEAAE3890458F5637C9C813EBEB2A69B9D34B9D9B6F62A7` | 01:01:49 | 9,861,632 | `165074a1606a-dirty` |
| 3 | `B2EC82935182E754B57223FCAFC0250FCF8BEB9B4A2960D1B60ACCD2749DF41F` | 01:43:25 | 9,861,632 | `c9f557f61e6f-dirty` |

**Sections 1-10 describe binary 1.** An unpinned audit would have straddled all
three and nothing in the output would have shown it.

### Commissioning the pin

Not assumed. Binary 3 was copied to scratch and one arm was run twice, once from
`target/release/strehl.exe` and once from the copy:

| runner | rc | sha256 | bytes |
|---|---:|---|---:|
| shared `target/release/strehl.exe` | 0 | `B46AECAA19CFD178E672B44CF3C47C2E9AD18A7E4104F72CAA43CF6EDF06BD20` | 197,801,296 |
| pinned copy | 0 | `B46AECAA19CFD178E672B44CF3C47C2E9AD18A7E4104F72CAA43CF6EDF06BD20` | 197,801,296 |

The copy resolves the same sidecars and renders the same bytes, so a null measured
from a pinned copy is a real null. Note that this control hash is **not**
`C5E59BC931C3AD93...`: the shipping default render itself moved between binary 1
and binary 3, and the output grew by 6 bytes. Ledger hashes are not comparable
across the boundary; ledger *classifications* were re-tested below.

### The fix list survives the rebuild

All 22 `INERT-SILENT` rows excluding `STREHL_SOFT_GATE` were re-run with `zzznope`
against binary 3 and its own unset control `B46AECAA...`. **All 22 returned rc=0
and byte-identical output.** `STREHL_ACUITY`, `STREHL_BIMODAL_DUMP`,
`STREHL_BUILD_ID`, `STREHL_CONFIDENCE_DEBUG`, `STREHL_DEFECT_ARM`,
`STREHL_DEFECT_HOT_FLOOR`, `STREHL_DUMP_ELECTION`, `STREHL_DUMP_MERGE_STATE`,
`STREHL_DUMP_NEFF`, `STREHL_EDGE_AWARE`, `STREHL_EDGE_CONF`,
`STREHL_EDGE_FEATHER`, `STREHL_EDGE_TAU`, `STREHL_FIX_HALO`,
`STREHL_FIX_HALO_DELTA`, `STREHL_RESTORE_SIGMA`, `STREHL_ROBUST_ELECTION`,
`STREHL_VEIL`, `STREHL_VEIL_DISPERSION`, `STREHL_VEIL_FLOOR`,
`STREHL_VEIL_MARGIN`, `STREHL_WINDOW_RADIUS` are all still silent on the backend
that ships. The channel-wide finding is not an artifact of a stale binary.

### `STREHL_SOFT_GATE`: the validation half landed, the wiring half did not

This variable is owned by BUILD-SOFTGATE and was not re-audited. Two arms were
spent confirming which half of its commit is observable, because section 7 made a
falsifiable prediction about it and the prediction can now be tested on a
committed build rather than a dirty tree.

On binary 3, `zzznope` is refused properly:

    Error: unknown soft-gate kernel "zzznope"; known kernels: gaussian,
    exponential (unset, "", "0", "off" or "false" run the shipped hard gate)

But all four accepted settings render the identical file:

| setting | rc | render |
|---|---:|---|
| unset | 0 | `B46AECAA19CFD178` |
| `off` | 0 | `B46AECAA19CFD178` |
| `gaussian` | 0 | `B46AECAA19CFD178` |
| `exponential` | 0 | `B46AECAA19CFD178` |

Section 7 predicted exactly this ("the fix closes the typo hole and not the inert
hole"), from the dirty tree, before the commit landed. **Confirmed.**

The source agrees. `preflight_soft_kernel` (`merge_cmd.rs:2904`) is
`strehl_core::merge::active_kernel()?; Ok(())` -- it asks the question and throws
the answer away, which its own doc comment now says in as many words after
`9bbb7a1c`. Grepping the working tree for `active_kernel`, `SoftKernel` and
`soft_kernel` returns **four hits in `merge_cmd.rs`, all inside the preflight, and
zero hits in `pyramid.rs`.** The kernel is not consumed by the pyramid backend.

One trap worth recording, because it nearly produced a false accusation here: the
banner line `selection : SOFT -- weight = (band power above the noise floor)^...`
prints on **all four** arms including unset, and looks at first like a knob
announcing itself and doing nothing. It is not. `merge_cmd.rs:5426` switches that
string on `cfg.select` (`SelectMode::SoftPower` vs `SelectMode::HardMax`), a
pyramid-internal weighting mode that is already soft by default and is unrelated
to `SoftKernel`. The banner is honest; the coincidence of the word "soft" is not
evidence. **A string match is not a wiring proof.**

Accordingly `STREHL_SOFT_GATE` is `INERT-VALIDATED` on binary 3, moved one step
from `INERT-SILENT`, and the count on the landed build is `INERT-SILENT` 22 +
`INERT-VALIDATED` 2. The ledger in section 3 is left as measured on binary 1.
