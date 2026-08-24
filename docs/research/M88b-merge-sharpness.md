# M88b — a paired instrument for "did alignment sharpen the merge?"

**Status: the instrument is BUILT, NULLED and POSITIVELY CONTROLLED. The
treatment arm has NOT been run — M86's alignment wiring was not finished. This
report is the instrument and its measured null, which the orchestrator
pre-agreed is a complete deliverable.**

**The task was to refuse if this is a fifth metric hunt. It is not, and that
was established by measurement before the instrument was committed to.**

## 1. Changes

| path | what |
| --- | --- |
| `experiments/M88b-merge-sharpness/` | new sibling directory (M88-optical-ceiling left frozen) |
| `.../PREREGISTRATION.md` | design, ROIs, floors, decision rule — frozen before any treatment number exists |
| `.../src/m88blib.py` | the instrument; imports M88's `m88lib.py` **unmodified** |
| `.../src/b01_survey.py` | geometry-only ROI survey over 6 stacks |
| `.../src/b02_graveyard.py` | the escape control |
| `.../src/b03_nulls.py` | null battery N0–N5 + ROI admission gate |
| `.../src/b04_ladder.py` | planted-misregistration positive control |
| `.../out/*.json` | results |

`crates/` was **not touched**. The merge was driven as a subprocess
(`strehl.exe stack <DIR> --gate <T> -o <TIFF>`). No default, including
`DEFAULT_GATE`, was changed. Merge TIFFs live in `data/` and are **not
committed** (47 MB each).

## 2. Does the paired design escape the graveyard?

**Yes, and it was tested rather than asserted.**

The four dead attempts (facts 468, 476, 612–613, 617/708, 809) — all verified
independently against `git show HEAD:docs/research/SYNTHESIS.md`, not taken on
trust — asked one question: **order arbitrary images by absolute sharpness with
no ground truth.** This asks a paired difference of one physical quantity
between two merges sharing subject, optics, frames, sensor, session and gate.

**ARGUED.** Under `rise² = d² + c²`, M88's negative result was that the
subject term `c` (~30 µm) is 3× the diffraction term `d` and cannot be
separated. Paired, `c` is fixed by construction and cancels:
`rise_off² − rise_on² = a_off² − a_on²`. The confound that made M88
UNIDENTIFIED is exactly what this design controls.

**MEASURED.** Fact 617/708 is a *proof* — ring FRC is `C/(C+U)` and a linear
post-filter scales both by `|H|²`, so the ratio cannot move. That proof is
about a **ratio of powers**; the 10–90 rise is a **distance on the ESF**, which
a low-pass strictly widens. Planting a linear post-filter and reading both
statistics off the same images:

| planted σ (px) | FRC @0.25 | Δ FRC | rise (µm) | Δ rise (µm) |
| --- | --- | --- | --- | --- |
| 0.00 | 0.9742 | +0.0000 | 14.258 | +0.000 |
| 0.50 | 0.9745 | +0.0003 | 19.066 | +4.808 |
| 1.00 | 0.9746 | +0.0004 | 29.732 | +15.474 |
| 2.00 | 0.9756 | +0.0015 | 41.619 | +27.362 |

FRC spans **+0.0015**; the rise spans **+27.362 µm**. The rise is **18,644×
more responsive** to the identical planted degradation. The class-killing proof
does not reach this statistic.

## 3. Verified (MEASURED)

**N0 — determinism.** Two merges of `109MSDCF` are SHA-256 identical, and the
paired statistic reads **|Δ| = 0.000000000 µm exactly** on all six ROIs. The
paired difference has **zero run-to-run noise**, which `dsig` never had.

**N1 — the floor, and the ROI admission gate.** 32 noise realisations per ROI,
pre-declared bar `p95|Δ| ≤ 1.0 µm`. **5 of 15** geometric ROIs admitted.
Pooled sd **0.2497 µm**; worst admitted p95 **0.6699 µm** — **the instrument
floor.** Rejected: `B31` 11.50, `B32` 71.06, `M92` 7.38, `TW3` 66.24,
`TW4` 91.20, and five others.

**N2 — gain.** ±8.93% / −6.84% gain gives **exactly 0.0000 µm**. The statistic
uses relative 10/90 thresholds of the span, so it is exactly degree 0 in gain —
the one property `dsig` did achieve, preserved here.

**N3 — pedestal.** +200 DN → 0.5956 µm, **below** the floor.

**N4 — displacement, and the fix.** An uncorrected integer 3 px displacement
produces a spurious **5.7054 µm** (8.52× floor). This is M88's own Bar 3
registration failure recurring, caught by control rather than by luck. Adding
integer phase-correlation registration takes it to **exactly 0.0000 µm**. The
sub-pixel arm (0.37 px + one resample) is **unchanged at 2.3987 µm**, which
disentangles the two: the residual is *resampling*, not displacement.

**N5 — resampling is a signed bias, not a null.** Net-zero-displacement round
trips varying only interpolation count give mean Δ **+0.3117 → −0.2752 →
−0.4052 µm** for 2 → 4 → 8 interpolations. Δ falling means the resampled arm's
edge is **wider**. The ON arm gathers through warps and pays one interpolation
the OFF arm does not, so **resampling biases the answer against alignment.** A
positive result is therefore conservative; a negative one is not. The decision
rule encodes that asymmetry.

**b04 — sensitivity.** Planted misregistration modelled as copies displaced
along a **line** (M86 measured the drift as smooth and monotonic, so isotropic
jitter would be the wrong model). Median Δ is **monotone across every in-range
rung that clears the floor**: `2.243 → 5.034 → 8.537 µm` at 4.00 / 5.78 / 8.00
merge px. On the fixed treatment set the median clears the floor at **4.00
merge px** and not at 2.00, so **minimum detectable planted spread is 2–4 merge
px = 4–8 sensor px**. M86's 11.56 px held-out residual is 5.78 merge px and is
**well inside** that sensitivity.

**b04 — the second gate, which the null alone would have missed.** Two ROIs
pass N1 and then **fail to respond to a planted effect**: `TW1` reads
+0.133/−0.222 µm at 4.00/5.78 px (blind) and `M94` reads −0.217/+1.010
(non-monotone). **An ROI that is quiet because it cannot respond passes a null
and then dilutes the treatment toward a false null.** M57's `dsig` died for
want of a null; a design can die just as easily for want of a positive control.
A pre-declared responsiveness gate fixes the treatment set at **`M95`, `RU1`,
`TW5`** (3 of 5).

## 4. Not verified

- **The treatment arm has not been run.** No aligned merge existed. Everything
  here is instrument characterisation.
- **The misregistration ladder is a simulation of the mechanism, not a re-run
  of the stacker.** It averages displaced copies of a real merge. It does not
  reproduce gate-driven frame selection under drift.
- **Why `TW1` is blind and `M94` unstable is not identified.** Both are
  excluded by a measured rule, not by a diagnosis.
- **The 16.00 px rung breaks down** (median −2.376 µm, one ROI fails). It is
  excluded by a bound computable a priori — `HALF_WIDTH_UM / MERGE_PITCH_UM =
  96 / 10.24 = 9.375` merge px — **not** by its result.
- **The ladder's zero rung is degenerate**: zero spread makes the simulated
  merge byte-identical to its input, so its exact 0.0000 restates N0 and is not
  an independent null.
- **Below roughly one third of the base rise the quadrature is second-order**
  and the statistic is directionally correct but not quantitative. Declared, not
  hidden.

## 5. The limitation that matters most (MEASURED)

**The instrument cannot be pointed at the stacks the owner is complaining
about.** `bee-2-cpl` yields **0** usable ROIs; `bee-3-cpl` yields **2**, and
**both fail the null catastrophically** (p95 |Δ| = 11.50 and 71.06 µm against a
1.0 µm bar); `wrapped-text-1` yields **0**. Every ROI in the treatment set
comes from `109MSDCF`, `ruler` or `tweezers`.

So the treatment will answer *"does alignment sharpen these merges"*, and
carrying that to the bees is an **extrapolation across subject** this design
cannot license. This is the same shape as fact 1184 — machine built, no fuel —
and it is a capture request rather than a defect in the method. **The unblocking
capture is a bee-like subject containing at least one straight, high-contrast,
1.2–9° slanted edge**, shot as a normal bracket.

## 6. Notes — five defects found in my own instrument

Three of the five were controls that **read exactly 0.000 and looked like
passes**:

1. The wing-flatness filter read the ESF from a function that flattens wings
   *by construction*, so it reported exactly 0.000 for every window. Vacuous.
2. `nan < threshold` is False in Python, so a NaN-contrast ROI passed silently.
3. `N5_identity_warp` used a spline shift at an exactly integer offset, which
   is exact, so it read 0.0000 everywhere while exercising nothing.
4. `measure_flat_noise` returned `nan` — an absolute 4 DN/px gradient bar on
   kilo-DN data rejected every window.
5. Saturation at 65535 DN in `tweezers` was not excluded.

**Working rule, offered to the corpus: a control that reads exactly zero should
be treated as suspect until it is shown to exercise its mechanism.** In this
milestone that heuristic caught three real defects, and the two legitimate
exact zeros (N0 determinism, N2 gain) each have a proof of why they must be
zero.

## 7. Candidate facts for owner review

| id | claim | label |
| --- | --- | --- |
| P1 | The paired merge comparison escapes the sharpness-metric graveyard: under a planted linear post-filter, ring FRC spans +0.0015 while the 10–90 edge rise spans +27.362 µm, a **18,644×** responsiveness gap. Fact 617/708's proof concerns a ratio of powers and does not reach a distance on the ESF. | MEASURED |
| P2 | `strehl.exe stack` is **byte-deterministic**: two merges of the same stack are SHA-256 identical and the paired rise statistic reads exactly 0.000000000 µm. The paired difference therefore has zero run-to-run noise. | MEASURED |
| P3 | The M88b instrument floor is **0.6699 µm** (worst admitted p95, 32 realisations); pooled sd 0.2497 µm. Only **5 of 15** geometrically valid ROIs pass the pre-declared 1.0 µm null bar. | MEASURED |
| P4 | Comparing two merges at **fixed window coordinates** without registration produces a spurious **5.7054 µm** difference under a 3 px displacement (8.52× floor). Integer phase-correlation registration reduces it to **exactly 0.0000 µm**. | MEASURED |
| P5 | Resampling is a **signed bias, not a null**: mean Δ falls +0.3117 → −0.2752 → −0.4052 µm for 2 → 4 → 8 interpolations. Since the aligned arm gathers through warps, resampling biases any A/B **against** alignment, making a positive result conservative and a negative one not. | MEASURED |
| P6 | The instrument resolves a planted misregistration of **2–4 merge px (4–8 sensor px)** on its treatment ROIs, and is monotone across every in-range rung above its floor. M86's 11.56 px held-out residual is 5.78 merge px, **inside** that sensitivity. | MEASURED |
| P7 | **A null-passing ROI can be blind.** `TW1` passes the noise null yet reads +0.133/−0.222 µm against a planted effect that moves other ROIs by 4–14 µm. A null establishes that an instrument is quiet; only a positive control establishes that it can speak. Both gates are required. | MEASURED |
| P8 | The bee stacks cannot support edge-based merge metrology: `bee-2-cpl` yields 0 usable ROIs, `bee-3-cpl` yields 2 and both fail the null (11.50 and 71.06 µm vs a 1.0 µm bar). Any A/B verdict from `109MSDCF`/`ruler`/`tweezers` is an extrapolation across subject. | MEASURED |
| P9 | A control that reads exactly 0.000 should be treated as suspect until shown to exercise its mechanism. Three of five defects found in M88b's own instrument were vacuous controls reading exact zero. | ARGUED |
