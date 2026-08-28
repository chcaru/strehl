# V-ENVSURF: every `STREHL_*` variable, classified on the shipping default path

Pin `ba34142806cf`, binary sha256
`EE7A302963B7657CEBAE5BAFB5D8E5628E41EBF92213EB935401CEDDF37C4C5C`, copied out of
`target/release/` before measurement and run from that copy, because the shared
`target/` was rebuilt by another lane **during** this survey (see section 7).
Subject `D:\personal\macro\coffee-bubbles`, command line
`stack <dir> --out <tif> -l 3 --srgb`, backend `pyramid` with **no `--merge`
flag** -- the path that ships. 197,801,290 bytes per render; every TIFF hashed
and deleted immediately.

## Verdict

**The env channel has 23 of 46 variables in the `STREHL_SOFT_GATE` class, and
`NOT-REACHED-BY-DESIGN` is EMPTY: not one of the 46 is refused under the pyramid
backend the way the estimator-only FLAGS are.** Fact 1882 is not an isolated
variable, it is a channel-wide property. `stack --help` states that the
estimator-only flags "are REFUSED under the pyramid backend rather than accepted
and ignored"; the environment channel implements the opposite policy for exactly
half its surface.

| bucket | count | what it means on the pyramid default path |
|---|---:|---|
| `LIVE` | **14** | read, rejects garbage, and its effect is demonstrated |
| `LIVE-UNVALIDATED` | **7** | changes the render, but a typo is accepted |
| `INERT-VALIDATED` | **1** | no effect, but a typo is refused |
| `DEBUG-ONLY` | **1** | side file appears, image byte-identical by design |
| `INERT-SILENT` | **23** | no effect AND a typo is accepted |
| `NOT-REACHED-BY-DESIGN` | **0** | -- |
| **total** | **46** | |

**46 attempted = 46 measured + 0 refused + 0 void.** Three variables
(`STREHL_DEFECT`, `STREHL_DEFECT_MAP`, `STREHL_SMOOTH_HUBER`) needed a second
subject or a deeper bracket before their effect appeared; that is recorded per
row rather than folded into a null.

## 1. Commissioning the comparator, before any "no change" was trusted

A comparator that cannot see a real change reports byte-identical for
everything. Two controls, both on the identical command line:

| arm | sha256 | reads |
|---|---|---|
| baseline, run 1 | `C5E59BC931C3AD93E08317CF4F0657E678648B9B19EA6E361BEA78A0EF568F55` | -- |
| baseline, run 2 | `C5E59BC931C3AD93E08317CF4F0657E678648B9B19EA6E361BEA78A0EF568F55` | **DETERMINISTIC** |
| `-l 4` instead of `-l 3` | `7900B76C369386A991F5B98A181745089EDB5895C471D86A5DB76E108C70AD92` | **DIFFERENT** |

The instrument is repeatable and it responds. The baseline hash and the byte
count reproduce ORCH's numbers exactly, so this lane and the commissioning lane
are measuring one artifact.

A second, stronger commissioning came out of the survey itself and was not
planned: `STREHL_SMOOTH=off` and `STREHL_WARPMAP=<sidecar solved with
STREHL_SMOOTH=off>` land on the **same** hash `CE2264BDEF18...`, reached through
two unrelated code paths. A comparator agreeing with itself across two channels
is better evidence than a planted delta.

## 2. Method, stated so it can be attacked

1. **Static first.** Every read site was located in source and traced for
   reachability from `run_pyramid` (`merge_cmd.rs:5280`) before any run. Static
   reading produced the prediction; the runtime arm was the test of it.
2. **Every arm has a matched unset control on the identical command line.**
   The pyramid control is one hash because the render is deterministic
   (section 1); the estimator arms carry their own control
   (`11AA9411190CE1E5...`) because that command line differs. This is
   fact 1883 and it is load-bearing here: `--merge estimator` **alone**
   exits 1 on this subject with `U3 the eroded low-detail region keeps only
   0 px`, an error that has nothing to do with any variable under test.
3. **The bucket is assigned from the variable set ALONE** on the shipping
   default command line. A variable that needs a companion is bucketed on its
   alone-behaviour and annotated `cond:`. This is the only rule that keeps the
   count a partition; the conditional behaviour is reported in the same row.
4. **Path-valued variables are scored on the artifact, not the image**
   (`*_MAP`, `*_DUMP`, `STREHL_CACHE_DIR`, `STREHL_WARPMAP`).
5. Garbage is `zzznope`, a string that names nothing anywhere in the tree.

## 3. The ledger

`A` cites the read site and whether any call chain from `run_pyramid` reaches
it. `B` is `zzznope`. `C` is a plausible non-default value. `SAME` means
byte-identical to the unset control.

| # | variable | A: read site / reached from `run_pyramid`? | B: `=zzznope` | C: value -> image | bucket |
|---:|---|---|---|---|---|
| 1 | `STREHL_ACUITY` | `merge_cmd.rs:1965` -- **no** | rc=0 SAME | `0` -> SAME | `INERT-SILENT` |
| 2 | `STREHL_ALIGN` | `align_cmd.rs:1272` -- yes | rc=0 SAME | `0` -> **DIFF** `EE1AD7DA` | `LIVE-UNVALIDATED` |
| 3 | `STREHL_BIMODAL_DUMP` | `merge_cmd.rs:2019` -- **no** | rc=0 SAME | path -> no side file | `INERT-SILENT` |
| 4 | `STREHL_BUILD_ID` | `build.rs:101` -- **compile time only** | rc=0 SAME | `vtest` -> SAME | `INERT-SILENT` |
| 5 | `STREHL_CACHE_DIR` | `align_cmd.rs:1396` -- yes | rc=0 SAME, dir created | dir -> **sidecar written there** | `LIVE` |
| 6 | `STREHL_CONFIDENCE_DEBUG` | `merge_cmd.rs:5652` -- yes, gated | rc=0 SAME | dir -> no side file | `INERT-SILENT` `cond:CONFIDENCE_MAP` |
| 7 | `STREHL_CONFIDENCE_MAP` | `merge_cmd.rs:4758` -- yes | **rc=1** `creating zzznope` | path -> **`conf.tif` written** | `LIVE` |
| 8 | `STREHL_COVER` | `align_cmd.rs:1047` -- yes | **rc=1** names the choices | `crop` -> **DIFF** `72AAFB43` | `LIVE` |
| 9 | `STREHL_DEFECT` | `stack.rs:884` -- yes | **rc=1** | `on` -> **DIFF** on `109MSDCF` | `LIVE` |
| 10 | `STREHL_DEFECT_ARM` | `stack.rs:911` -- not unless defect on | rc=0 SAME | `none` -> SAME | `INERT-SILENT` `cond:DEFECT=on` |
| 11 | `STREHL_DEFECT_HOT_FLOOR` | `stack.rs:915` -- not unless defect on | rc=0 SAME | `200` -> SAME | `INERT-SILENT` `cond:DEFECT=on` |
| 12 | `STREHL_DEFECT_MAP` | `stack.rs:897` -- yes | **rc=1** hard error | real map -> **DIFF** on `109MSDCF` | `LIVE` |
| 13 | `STREHL_DEMOSAIC` | `demosaic.rs:326` -- yes | rc=0 SAME | `directional` -> **DIFF** `D4D10F9A` | `LIVE-UNVALIDATED` |
| 14 | `STREHL_DUMP_ELECTION` | `merge_cmd.rs:2451` -- **no** | rc=0 SAME | path -> no side file | `INERT-SILENT` |
| 15 | `STREHL_DUMP_MERGE_STATE` | `dump.rs:50` -- **no** | rc=0 SAME | dir -> no side file | `INERT-SILENT` |
| 16 | `STREHL_DUMP_NEFF` | `merge_cmd.rs:2792` -- **no** | rc=0 SAME | path -> no side file | `INERT-SILENT` |
| 17 | `STREHL_EDGE_AWARE` | `merge_cmd.rs:1928` -- **no** | rc=0 SAME | `off` -> SAME | `INERT-SILENT` |
| 18 | `STREHL_EDGE_CONF` | `merge_cmd.rs:1817` -- **no** | rc=0 SAME | `8` -> SAME | `INERT-SILENT` |
| 19 | `STREHL_EDGE_FEATHER` | `edgeaware.rs:854` -- **no** | rc=0 SAME | `4` -> SAME | `INERT-SILENT` |
| 20 | `STREHL_EDGE_TAU` | `merge_cmd.rs:1981` -- **no** | rc=0 SAME | `8` -> SAME | `INERT-SILENT` |
| 21 | `STREHL_FIX_CA` | `optics.rs:690`, preflighted at `merge_cmd.rs:5284` -- yes | **rc=1** lists profiles | `off` -> **DIFF** `873F201B` | `LIVE` |
| 22 | `STREHL_FIX_HALO` | `halo.rs:113` -- **no** | rc=0 SAME | `on` -> SAME | `INERT-SILENT` |
| 23 | `STREHL_FIX_HALO_DELTA` | `halo.rs:124` -- **no** | rc=0 SAME | `80` -> SAME | `INERT-SILENT` |
| 24 | `STREHL_FULLRES_GATHER` | `align_cmd.rs:1216` -- yes | **rc=101** panic | `0` -> **DIFF** `13D80070` | `LIVE` |
| 25 | `STREHL_GATE_FLOOR` | `gatefloor.rs:95` -- yes | rc=0 SAME | `white` -> **DIFF** `15567BBF` | `LIVE-UNVALIDATED` |
| 26 | `STREHL_GATE_FLOOR_SCALE` | `gatefloor.rs:126` -- yes | **rc=101** panic | `1,4,4,4,4,4,4` -> **DIFF** `1EF1F9B6` | `LIVE` |
| 27 | `STREHL_HIGHLIGHT_KNEE` | `highlight.rs:175` -- yes | rc=0 SAME, **warns** | `off` -> **DIFF** `24007472` | `LIVE-UNVALIDATED` |
| 28 | `STREHL_HULL` | `pyramid.rs:767` -- yes | **rc=101** panic | `unclamped` -> **DIFF** `C253AF6B` | `LIVE` |
| 29 | `STREHL_MERGE` | `merge_cmd.rs:566` -- yes | **rc=1** | `estimator` -> **DIFF**, identical to the flag | `LIVE` |
| 30 | `STREHL_ONLY_FRAME` | `merge_cmd.rs:1797` -- yes | **rc=101** panic | `1` -> **DIFF** `0D25E257` | `LIVE` |
| 31 | `STREHL_PHOTOMETRIC` | `merge_cmd.rs:2662` -- yes | **rc=1** | `off` -> SAME | `INERT-VALIDATED` |
| 32 | `STREHL_PYRAMID_MEAN_COARSE` | `pyramid.rs:726` -- yes | **rc=101** panic | `2` -> **DIFF** `5CC2634A` | `LIVE` |
| 33 | `STREHL_PYRAMID_WEIGHT_DUMP` | `pyramid.rs:708` -- yes | rc=0 SAME, **25 files** | prefix -> **25 files**, image SAME | `DEBUG-ONLY` |
| 34 | `STREHL_PYRAMID_WORKERS` | `merge_cmd.rs:5192` -- yes | **rc=1** | `1` -> banner `3 -> 1 workers`, image SAME | `LIVE` |
| 35 | `STREHL_RESTORE` | `restore.rs:1243` -- yes | rc=0 SAME, **warns** | `4.0` -> stage RUNS, image SAME | `LIVE-UNVALIDATED` |
| 36 | `STREHL_RESTORE_SIGMA` | `restore.rs:1288` -- not unless restore on | rc=0 SAME | `4.0` -> SAME | `INERT-SILENT` `cond:RESTORE>1` |
| 37 | `STREHL_ROBUST_ELECTION` | `merge.rs:723` -- **no** | rc=0 SAME | `on`/`hard`/`ungated` -> SAME | `INERT-SILENT` |
| 38 | `STREHL_SMOOTH` | `align_cmd.rs:585` -- yes | rc=0 SAME, **warns** | `off` -> **DIFF** `CE2264BD` | `LIVE-UNVALIDATED` |
| 39 | `STREHL_SMOOTH_HUBER` | `align_cmd.rs:603` -- yes | rc=0 SAME, **silently means `off`** | `0.2` at N=19 -> **DIFF** `3DD8B188` | `LIVE-UNVALIDATED` |
| 40 | `STREHL_SOFT_GATE` | `merge.rs:682` -- **no** | rc=0 SAME | `gaussian`/`exponential` -> SAME | `INERT-SILENT` |
| 41 | `STREHL_VEIL` | `merge_cmd.rs:2719` -- **no** | rc=0 SAME | `1` -> SAME | `INERT-SILENT` |
| 42 | `STREHL_VEIL_DISPERSION` | `merge_cmd.rs:3947` -- **no** | rc=0 SAME | `1` -> SAME | `INERT-SILENT` |
| 43 | `STREHL_VEIL_FLOOR` | `merge_cmd.rs:2773` -- **no** | rc=0 SAME | `0.5` -> SAME | `INERT-SILENT` |
| 44 | `STREHL_VEIL_MARGIN` | `merge_cmd.rs:2752` -- **no** | rc=0 SAME | `2` -> SAME | `INERT-SILENT` |
| 45 | `STREHL_WARPMAP` | `merge_cmd.rs:2383` -- yes | **rc=1** hard error | alt sidecar -> **DIFF** `CE2264BD` | `LIVE` |
| 46 | `STREHL_WINDOW_RADIUS` | `focus.rs:110` -- **no** | rc=0 SAME | `8` -> SAME | `INERT-SILENT` |

## 4. The `INERT-SILENT` list, ranked -- the fix list

Ranked by how much a user could believe the knob did something. Recommendation
per row.

**Tier 1 -- a real feature, reachable on the other backend, silently dead here.**
A caller who sets one of these gets a normal render, exit 0, and no hint.

| variable | proof it is a real knob | recommendation |
|---|---|---|
| `STREHL_SOFT_GATE` | `gaussian` -> `0A82D57A`, `exponential` -> `318BFC71` on the estimator; both SAME on pyramid | **error under pyramid** |
| `STREHL_EDGE_AWARE` | `off` -> `A4A2AC6C` on the estimator; SAME on pyramid | **error under pyramid** |
| `STREHL_WINDOW_RADIUS` | `zzznope` panics at `focus.rs:114` on the estimator; rc=0 SAME on pyramid | **error under pyramid** |
| `STREHL_EDGE_TAU` | `zzznope` panics at `merge_cmd.rs:1985` on the estimator | **error under pyramid** |
| `STREHL_EDGE_CONF` | `env_num(EDGE_CONF_ENV, 2.0)`, estimator-side | **error under pyramid** |
| `STREHL_EDGE_FEATHER` | `edgeaware.rs:854` panics on a non-number if reached; never reached on either backend from `stack` | **error under pyramid** |
| `STREHL_ACUITY` | `merge_cmd.rs:1965`, estimator-side; no effect measured on either backend | **error under pyramid** |
| `STREHL_VEIL` | estimator refuses it without `--photometric on` (rc=1, a real read); pyramid accepts silently | **error under pyramid** |
| `STREHL_VEIL_MARGIN` | `merge_cmd.rs:2752`, estimator-side | **error under pyramid** |
| `STREHL_VEIL_FLOOR` | `merge_cmd.rs:2773`, estimator-side | **error under pyramid** |
| `STREHL_VEIL_DISPERSION` | `merge_cmd.rs:3947`, estimator-side | **error under pyramid** |
| `STREHL_FIX_HALO` | `halo.rs:113`, estimator-side | **error under pyramid** |
| `STREHL_FIX_HALO_DELTA` | `halo.rs:124`, estimator-side | **error under pyramid** |

**Tier 2 -- diagnostics that write nothing and say nothing.** `pyramid.rs`'s own
doc comment names this failure: *"a diagnostic that quietly writes nothing is
indistinguishable at the terminal from one that found nothing to report."*
Measured: on the estimator these three produce 4, 1 and 3 files respectively; on
pyramid, zero files and zero words.

| variable | estimator produces | pyramid produces | recommendation |
|---|---|---|---|
| `STREHL_BIMODAL_DUMP` | `guide.raw`, `radius.raw`, `first_mode_z.raw`, +1 | nothing | **error under pyramid** |
| `STREHL_DUMP_ELECTION` | `election.tif` | nothing | **error under pyramid** |
| `STREHL_DUMP_MERGE_STATE` | `best_focus.npy`, `best_index.npy`, `n_eff_gate4.00.npy` | nothing | **error under pyramid** |
| `STREHL_DUMP_NEFF` | `neff.tif` | nothing | **error under pyramid** |

**Tier 3 -- inert because the feature they configure is off by default.** These
become live and validated the moment their companion is set; setting them alone
is a silent no-op. Lower severity, but a harness that sets only the sub-knob
gets nothing and is told nothing.

| variable | companion | with the companion set |
|---|---|---|
| `STREHL_DEFECT_ARM` | `STREHL_DEFECT=on` | `zzznope` -> **rc=1**; `none` returns `109MSDCF` to the unset hash exactly |
| `STREHL_DEFECT_HOT_FLOOR` | `STREHL_DEFECT=on` | `zzznope` -> **rc=1** `is not a number of electrons` |
| `STREHL_RESTORE_SIGMA` | `STREHL_RESTORE=4.0` | `zzznope` -> **rc=101** at `restore.rs:1297`; `4.0` scales `sigma2` 699.3 -> 2797.4 DN^2 |
| `STREHL_CONFIDENCE_DEBUG` | `STREHL_CONFIDENCE_MAP` | writes `dmin`, `dsharp`, `spread`, `centrality`, `withinfrac` tiffs |

Recommendation for tier 3: **validate the sub-knob whenever it is set**, not
only when the parent is on. The parse is already written; it is the call site
that is conditional.

**Tier 4 -- dead everywhere, or not a runtime knob at all.**

| variable | finding | recommendation |
|---|---|---|
| `STREHL_ROBUST_ELECTION` | byte-inert on **both** backends at N=3 and N=19, for all four settings (`unset`/`on`/`hard`/`ungated` all hash `FC492B99E9F47FD5` on the estimator). `robust.rs:313` says the module "has been dead code since it was written" | **delete the variable, or wire `active_arm()` into a call site** |
| `STREHL_BUILD_ID` | read by `build.rs:101` at **compile time**. It has no runtime read site and cannot be exercised by a run. Not a defect | **document as build-time; exclude from the runtime channel** |

## 5. The `LIVE-UNVALIDATED` list -- these work, and misbehave on a typo

| variable | what a typo does | severity |
|---|---|---|
| `STREHL_SMOOTH_HUBER` | **silently reconfigures the solve to `off`** -- `.parse().ok().filter(...)` maps any unparseable value to `None`, which is the same state `off` selects. `0.2` at N=19 renders `3DD8B188`, `off` and `zzznope` both render the unset hash `A59982E8`. The robust threshold on a real tripod bump is discarded without a word | **highest** |
| `STREHL_ALIGN` | anything not in `{0,off,false,no}` leaves registration ON. `STREHL_ALIGN=of` renders aligned. The off arm is a real change (`EE1AD7DA` vs `C5E59BC9`) | high |
| `STREHL_GATE_FLOOR` | anything not equal to `white` selects the measured floor, i.e. the default. `STREHL_GATE_FLOOR=whit` silently means "default" while `white` renders `15567BBF` | high |
| `STREHL_DEMOSAIC` | only `eq_ignore_ascii_case("directional")` is tested; every other string is the Malvar default. `directional` renders `D4D10F9A` | high |
| `STREHL_SMOOTH` | falls back to the default lambda, **but prints a warning** | medium |
| `STREHL_HIGHLIGHT_KNEE` | falls back to 0.60, **but prints a warning** | medium |
| `STREHL_RESTORE` | declines to run, **but prints a warning** naming the reason | medium |

Recommendation for all seven: **refuse rather than default**, the rule
`STREHL_FULLRES_GATHER`, `STREHL_HULL`, `STREHL_ONLY_FRAME`,
`STREHL_PYRAMID_MEAN_COARSE` and `STREHL_GATE_FLOOR_SCALE` already follow in the
same tree. Five variables in this binary already do it right; the split is a
choice made file by file, not a policy.

## 6. Where static reading and the runtime disagreed

Four disagreements. All four resolved in favour of the runtime, and three of
them changed a classification.

**6.1 `STREHL_RESTORE=4.0` -- static said reachable, hash said nothing
happened.** `run_pyramid` calls `restore::gain_cap_from_env()` at the
`write_merged` argument list, so the read is on the shipping path. The render is
byte-identical anyway. **The stage runs**: stderr carries
`restore R : cap 4.000, max gain 1.0000 (2-D 1.0000), at Nyquist 1.0000,
recovered 0.0000` for all four planes. The gain saturates at the identity, which
`restore.rs`'s own doc predicts (*"the cap is measured never to bind"*). The
variable is read, the stage executes, the pixel delta is zero. Classified
`LIVE-UNVALIDATED` with the pixel delta stated, not hidden.

**6.2 `STREHL_RESTORE_SIGMA=zzznope` -- static said it panics, runtime exited
0.** `sigma_scale_from_env()` panics on a non-number, and `restore.rs` says so
in a doc comment: *"a mis-set instrument that reads plausibly is worse than one
that stops."* It exits 0 because the function is never called: with
`STREHL_RESTORE` unset there is no `RestorePlan` and nothing asks for the sigma.
Set both, and it panics as advertised (`restore.rs:1297`). **The refusal exists
and is unreachable from the default configuration.**

**6.3 `STREHL_PYRAMID_WORKERS=1` -- static said the fold partition changes,
hash said byte-identical.** It does change: `memory plan : 3 workers x 1328 MB`
becomes `1 workers x 1328 MB` and the fold goes 2.0 s -> 3.4 s. The render is
byte-identical because the accumulator is summed left to right within a chunk
and chunks are absorbed in order, so 3x1 and 1x3 evaluate `(f0+f1)+f2` either
way. Byte-invariance here is a **correctness property**, not inertness.
Classified `LIVE`.

**6.4 ORCH's `STREHL_SOFT_GATE=on` is not a valid setting.**
`kernel_from_setting` accepts `""`, `0`, `off`, `false` (all -> no kernel),
`gaussian`, `exponential`, and errors on everything else. `on` is in the error
arm, so ORCH's `=on` column and its `=zzznope` column are **the same
experiment** and the 2x2 has three distinct cells, not four. Re-run with the
real kernel names, the finding survives and sharpens: on the estimator
`gaussian` -> `0A82D57A3B3D` and `exponential` -> `318BFC71D2D5`, both differing
from the estimator control `11AA9411190CE1E5`; on pyramid both render the
baseline hash exactly. **The knob is real, it works, and it is silently dead on
the backend that ships.**

## 7. What moved under me: a 47th variable, and a partial fix

The shared `target/release/strehl.exe` was rebuilt at 01:01:49 while this survey
was running -- `EE7A3029...` -> `55E0C07E...`, `ba34142806cf` ->
`165074a1606a-dirty`. Both binaries were copied out and hashed, so both columns
are attributable. `git diff ba34142806cf -- crates/` is 4 files, and two of them
matter here:

1. **`merge_cmd.rs` gains `preflight_soft_kernel()`**, called from `run()`
   before the backend dispatch. Uncommitted: it is in neither `ba34142806cf` nor
   `HEAD` (`165074a1`), only in the working tree.
2. **`pyramid.rs` gains `STREHL_PYRAMID_SIGNIFICANCE`** (`SIGNIFICANCE_ENV`), a
   **47th** variable that did not exist when this lane's list was drawn.

Re-running the full garbage sweep on the new binary (47 variables, unset control
`369D4FC2468E20F98D530AFFA2565E3D4AC093EA2994AB6A9EDBBA819F8F78DB`) shows
**exactly one row moved**: `STREHL_SOFT_GATE=zzznope` goes rc=0 -> **rc=1**. The
new variable `STREHL_PYRAMID_SIGNIFICANCE=zzznope` reads rc=101, so it arrives
validated. The other 45 rows are unchanged.

**The fix closes the typo hole and not the inert hole.** On the new binary
`STREHL_SOFT_GATE=gaussian` still exits 0 and still renders
`369D4FC2468E20F9...`, byte-identical to the unset control. A caller who spells
the kernel *correctly* is still told nothing and still gets nothing. The bucket
moves `INERT-SILENT` -> `INERT-VALIDATED`, which is an improvement of exactly one
step. Refusing an unknown value is not the same guarantee as refusing a value the
backend cannot honour, and `stack --help`'s flag contract promises the second.

## 8. An edge the survey found on its own: empty string is not a policy

`""` is how a harness clears an inherited variable. The tree handles it three
different ways on one command line.

| variable | `=""` |
|---|---|
| `STREHL_COVER`, `STREHL_PHOTOMETRIC` | treated as "nobody asked" -- rc=0, documented |
| `STREHL_DUMP_ELECTION`, `STREHL_SOFT_GATE`, `STREHL_FULLRES_GATHER`, `STREHL_WINDOW_RADIUS` | rc=0, no effect |
| `STREHL_PYRAMID_WEIGHT_DUMP` | **rc=101** `pyramid.rs:712` -- intended |
| `STREHL_HULL` | **rc=101** `pyramid.rs:773` -- **not** intended; unset is fine, empty crashes the shipping default path |
| `STREHL_ONLY_FRAME` | **rc=101** `merge_cmd.rs:1803` |
| `STREHL_DEFECT` | **rc=1** `STREHL_DEFECT="" is not a setting` |

`STREHL_HULL=` (empty) aborting the shipping default render is the one worth
fixing: `hull_default()` matches the trimmed string against three names and
panics on the fall-through, and `""` reaches the fall-through while unset does
not. `MEAN_COARSE_ENV` has the same shape and survives `""` only because
`"".parse::<usize>()` is the panic it already documents.

## 9. What I could not measure

Recorded as skips, not passes.

| variable | why the effect arm is incomplete |
|---|---|
| `STREHL_VEIL` and its three sub-knobs | the estimator refuses the veil without `--photometric on`, and `--photometric on` exits 1 on `coffee-bubbles` with `U3 ... keeps only 0 px`. Their **pyramid** classification is unaffected (silent, no effect); what is unmeasured is whether they do anything on the estimator |
| `STREHL_DEFECT_HOT_FLOOR` | the hot arm corrected 0 sites on both subjects tried (`examined 0, corrected 0`), consistent with M101's measured null on this body. Its parse is reached and validated; its pixel effect is undemonstrated |
| `STREHL_RESTORE`, `STREHL_RESTORE_SIGMA` | the stage runs and the parameter propagates (`sigma2` x4 in the banner), but `max gain` reads 1.0000 on this subject so the pixel delta is structurally zero. A subject where the gain binds would be needed |
| `STREHL_ACUITY` | `=0` is byte-identical on **both** backends. Either the term is inert as shipped or `acuity_shrink()` sits behind a condition this subject does not meet. Not chased -- it is estimator-side and outside this lane |
| `STREHL_CACHE_DIR` | scored on the artifact. A path on a missing volume prints `could not cache sidecar (os error 3); continuing` and re-solves, rc=0, image SAME -- loud degradation, not silent |
| all 46 | one subject, three frames, one exposure. `STREHL_DEFECT` and `STREHL_SMOOTH_HUBER` both read SAME on `coffee-bubbles -l 3` and DIFF elsewhere, which is the measured warning that a single-subject null is weak evidence |

## 10. What would falsify this

- **The partition.** Any variable shown to change the pyramid render at a value
  I did not try moves out of `INERT-SILENT` and the count of 23 is wrong. The
  cheapest attack is `STREHL_ACUITY` and the four `VEIL` knobs, where my
  plausible value is a guess at the author's intent.
- **The comparator.** If SHA256 over the TIFF can miss a change the merge made,
  every `SAME` is void. Two controls argue otherwise (section 1) and one of them
  was not planted by me.
- **The binary.** Everything in sections 1-6 is `ba34142806cf`. Section 7's
  sweep is `165074a1606a-dirty`, whose working tree is uncommitted and may not
  survive. A third build could move rows again; the method is one command per
  row and re-running it is cheap.
- **`STREHL_ROBUST_ELECTION`.** I claim it is byte-inert on both backends. One
  render where it moves a byte refutes the "delete it" recommendation outright.
  It is the strongest claim in this document and the easiest to break.
