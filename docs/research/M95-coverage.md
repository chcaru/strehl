# M95 arm 5 — the coverage rescale is not the softness, and removing it makes the render very slightly worse

Milestone M95, arm 5. Follows arm 4 (`56e4cfa`, `docs/research/M95-resample.md`).
Answers the orchestrator's instruction to act on `resample_budget.py`.

Every number below was printed by code run in this session. The consolidated
sheet is `experiments/M95-coverage/out/x12_summary.txt`; each figure traces to a
JSON written by the instrument that produced it.

## 1. Headline

**Do not build the native-sampling fix. I measured it and it recovers nothing.**

Priced against the real 299-frame warp sidecar, on strehl's own unresampled
decode:

| arm | what it is | cost vs unresampled |
| --- | --- | --- |
| **NOW** | real frame warp + coverage scale, output 7032 × 4688 | **+0.1813 dex** (sem 0.0031) |
| **FIX** | real frame warp, coverage scale removed, output 6550 × 4367 | **+0.1855 dex** (sem 0.0017) |
| **SNAP** | translation rounded to integer, unit scale | **−0.0003 dex** (sem 0.0005) |

The fix recovers **−0.0042 dex**. It is very slightly *worse* than what ships
today, and both are far outside each other's standard errors of the mean. My
pre-registered bar was *dead if recovery < +0.03 dex*; it landed below zero.

The reason is in the third row. **SNAP costs nothing.** With every frame on an
integer offset and unit scale, one Catmull-Rom gather is free. So the entire
cost of the gather is *sub-pixel phase*, and the coverage scale is only one of
the things that produces it. Remove the scale and the per-frame warp still has
phase: `w0_warpstats.py` measures the fractional part of the real displacements
at mean 0.5086 with sd 0.3042 against uniform's 0.5000 / 0.2887, and only 1.3%
of frames land within 0.05 px of an integer where uniform predicts 9.8%. The
per-frame solve also carries its own scale, from −3.113e−02 to +5.037e−02,
which is independent of coverage and sweeps phase on its own.

**The lever that does work is the kernel, which is arm 4's finding and arm 4's
patch.** It is unchanged by this arm.

## 2. Why the magnitude of the enlargement is the wrong variable

The proposal rests on the idea that a +7.35% interpolated enlargement is costly
*because it is 7.35%*. It is not. Pure scale, no translation, about the field
centre, band-matched, on real decoded tiles:

| k | enlargement | cost (dex) |
| --- | --- | --- |
| 1.0000 | 0.00% | −0.0000 |
| 0.9999 | 0.01% | +0.0755 |
| 0.9995 | 0.05% | +0.1412 |
| 0.9990 | 0.10% | +0.1728 |
| 0.9970 | 0.30% | +0.1793 |
| 0.9974 | 0.26% | +0.1851 |
| 0.9900 | 1.01% | +0.1849 |
| 0.9700 | 3.09% | +0.2062 |
| 0.9315 | 7.35% | +0.1836 |
| 0.8500 | 17.65% | +0.1478 |
| 0.7000 | 42.86% | +0.1080 |

Three readings of that table, none of which the magnitude model survives:

1. **A 0.01% enlargement already costs +0.0755 dex** — 41% of what the shipped
   7.35% costs, for 1/735th of the enlargement.
2. **The curve is not monotone.** A 42.86% enlargement costs **+0.1080**, *less*
   than a 1.01% one at **+0.1849**.
3. **It saturates by k ≈ 0.999** and then wanders in a band of 0.0981 dex while
   the enlargement changes by a factor of over four hundred.

What actually matters is whether the geometry is exactly integer or not. At
k = 1.0000 the cost is zero to four decimals. One step off it, at 0.01%, most of
the cost is already there. This is a threshold, not a dose.

## 3. The orchestrator's four questions, answered

**Q. What did "8.2 MP" mean?** The literal pixel dimensions of the file the
default `--srgb` path writes, 2344 × 3516. The file measured in
`fullres_check.py`, `bee-3-cpl-g0.tif`, is 4688 × 7032 — the `--demosaic`
branch. Two different files, no contradiction. Answered in arm 4 §2 and repeated
here because it was asked twice.

**Q. Is it two interpolations in series?** No, one.
`align_cmd.rs:1277` `fit_to_cover` composes a pure scale onto every frame
placement and returns `s.then(*t)` — a single fused matrix, gathered once. Two in
series would cost roughly double, which is why `resample_budget.py`'s R2 arm
overshot.

**Q. Does the coverage crop's rescale account for the deficit?** It accounts for
essentially all of what *one gather* costs, but that is not the same claim.
Running the coverage scale alone on an identity warp costs **+0.183568 dex**,
and the same k on the independent ladder in §2 reads **+0.1836** — two code
paths agreeing to five decimals. But the per-frame warp *by itself*, with
coverage removed, costs **+0.1855**. They are alternative sources of the same
phase, not additive contributors, so removing one leaves the other.

**Q. What about the remaining unexplained deficit?** The demosaic confound the
orchestrator flagged three times is now priced from inside the codebase, which
was the stated reason it could not be done from outside. Re-printed this
session by arm 4's `x2_pairs.py`: **A → B0 = −0.0332 dex, 1.079× power**, rawpy's
demosaic against strehl's Malvar-He-Cutler on the same frame. It is small. It
does not carry the remainder.

## 4. What the eye says

`C:\dev\strehl-out\M95-coverage\M95-coverage-fix.png` — five panels, one 100%
crop of `bee-3-cpl` frame 199, whose offset is (+2.501, −2.860) render px,
0.499 px from the nearest integer, so it is the worst realistic case rather than
a flattering one.

Every panel covers the **identical scene span** from the same unresampled decode
and is shown at the pixel count its own geometry produces, with no display
resampling — so FIX appears at 427 px and NOW at 459 px for the same scene,
which is precisely the 7% the proposal would give up.

No sharpness number is printed on any panel. The numbers in this report are
measured on a band-matched spectral axis, and printing them beside pixels
invites reading them as a per-panel measurement they are not.

NOW and FIX are indistinguishable. SNAP is indistinguishable from SOURCE.
LANCZOS3 is visibly crisper than NOW on the same geometry. The eye and the
metric agree on all three, which matters here because this project has already
had a metric outrank the eye and be wrong.

## 5. Pre-registration, and how badly it fared

`experiments/M95-coverage/PRE-REGISTRATION.md`, written before any arm ran.

**Both of my B1 readings failed.** I pre-registered "MAGNITUDE model if
cost(0.997) < ⅓ × cost(0.9315)" and "PHASE model if the spread across sweeping k
is under 0.04 dex". The corrected ladder returned **False for both**: cost(0.997)
is +0.1793 against a threshold of 0.0612, and the spread is 0.0981 against 0.04.

I am reporting that rather than quietly restating the bar. The bars were badly
chosen — I picked k = 0.997 as the "small enlargement" probe without noticing
that it sweeps only 0.77 phase cycles across a 256 px tile, and I set the spread
window without allowing for the scene-content shift at k = 0.85 and 0.70, where
the tile covers a different number of source pixels. **The conclusion in §1 does
not rest on B1.** It rests on B2, whose bars were unambiguous and did fire.

**B3 refuted a hypothesis of mine.** I predicted `resample_budget.py`'s fixed
0.30–0.48 cyc/px band would materially overstate the cost, because an arm
magnified by 1/0.9315 is empty above 0.4657 cyc/px by construction. The bias is
**−0.0112 dex**, and it runs the other way — the fixed band very slightly
*understates*. The geometry argument is sound; the magnitude is negligible. The
orchestrator's +0.2392 is not a units artifact.

**B4 held.** Arm 4's end-to-end `B0 → B1 = −0.2851 dex` re-printed unchanged.

## 6. Controls, including the ones that failed

Passing gates, `x7b` and `x8` and `x10c`:

| control | reading | bar |
| --- | --- | --- |
| K1 null, scale 1.0 offset 0 | −0.000041 | \|c\| < 0.005 |
| K1 null, x8 identity warp | −0.000041 | \|c\| < 0.005 |
| K1 null, x10c full and planes | +0.000069 | \|c\| < 0.006 |
| K4 integer shift, 1.0 px | −0.000225 | \|c\| < 0.005 |
| K4 integer plane shift, 2 mosaic px | −0.000502 | \|c\| < 0.006 |
| K3 positive, planted Gaussian σ = 0.30 px | +0.2209 | ≥ 0.15 |
| K5 band-match legitimacy, Lanczos-8 at k = 0.9315 | +0.0091 | \|c\| < 0.05 |

K3 is the discipline-594 clause: the instrument is shown saying otherwise before
any null it produces counts. K5 is the one that makes §2 admissible — it proves
band-matching does not manufacture the null, because a near-ideal kernel through
the same correction reads +0.0091 where Catmull-Rom reads +0.1836.

### Four failures, with diagnoses

**F1 — `x7_scale.py`, the entire first ladder. Withdrawn.** It scaled about each
*tile's* centre, so every tile sat at zero base phase and swept only
±(TILE/2)(1−k) about it. For k near 1 that keeps every sample near integer phase
where Catmull-Rom is nearly exact. It read **+0.0340 dex** at k = 0.997 where the
corrected version reads **+0.1793**. All five of its controls passed. The defect
was invisible until the ladder disagreed with the end-to-end measurement by 8×,
and the only thing that caught it was refusing to accept a synthetic number that
contradicted a measurement through the shipped binary.

**F2 — `x10_planeres.py`, both new arms failed their null.** STRETCH read
+0.842994 dex and PLANES +0.491529 dex at integer phase, where a copy must read
zero. STRETCH was ill-posed: a 2×-dilated kernel on the full field reads only
every other sample of the *whole* field, which is decimation, not a plane
gather. Dropped rather than patched, because a correct version is just PLANES
again and would not be independent. PLANES had a literal `+ oy - oy` and no
constraint that the mosaic offset be even — strehl's warp is expressed in plane
units, so the mosaic offset it induces is always twice a plane quantity, and an
odd one would map output red sites onto source blue sites.

**F3 — `x10c_planeres.py`'s K7 equivalence control. A true positive on a false
premise.** It asserted that d plane px must cost the same as 2d mosaic px, i.e.
that a plane gather is just the same kernel on a coarser grid, and failed at
0.0221 / 0.0692 / 0.0960 dex apart. The premise is wrong: the measurement band,
0.30–0.48 cyc per *mosaic* px, sits at 0.60–0.96 cyc per *plane* px, above a
single plane's Nyquist of 0.50. This is the same shape as arm 4's Mitchell
control — the control fired correctly and the conclusion I would have drawn from
it was still wrong.

**F4 — `x10c`'s plane-resolution arm. Withdrawn, undiagnosed.** The penalty
reads **−0.0572 dex** at k = 0.9974 and **+0.0877 dex** at k = 0.9315. A quantity
that flips sign across two nearby values of the same knob is not a measurement,
and its own mechanism check returned a meaningless −34%. All its gating controls
passed.

I had a hypothesis and I tested it: the plane gather manufactures aliasing,
which a power-spectrum metric counts as signal. `x11_alias.py` band-limited the
input below plane Nyquist — positive control confirms the low-pass suppresses
the band by **1.266e+07×** — and measured what each gather puts back above it.
The plane gather emits **0.41×** what the full-resolution gather does. **Less,
not more. Hypothesis refuted.** The sign flip stays undiagnosed and arm 4's
**P56 remains ARGUED and is not upgraded**.

**F5 — the report verifier's own negative control failed on its first run.** One
of the three planted mutations reported `MUTATION TARGET NOT FOUND (0 hits)`:
the anchor spelled the panel dimensions with an ASCII `x` where the report uses
`×`. The mutation would simply not have been applied, and a bare
`replace(old, new, 1)` would have reported that check as passing. It is caught
only because the control asserts its anchor lands exactly once and hard-errors
otherwise.

## 7. What this does not cover

- It prices **geometry** for one fixed kernel. It does not revisit which kernel
  to use; that is arm 4 and its patch is unchanged.
- It says nothing about **election quality** — whether the frame that wins a
  pixel is the sharpest available. Arm 1 proved the merge reproduces the elected
  frame byte-exactly, which makes election a live and separate question.
- It cannot speak outside 0.30–0.48 cyc/px scaled by each image's own coverage.
- `x8`'s arms are a faithful model of the shipped mapping, not the shipped code.
  They use the real sidecar's per-frame similarities and the real `fit_to_cover`
  composition order, but they are Python, and the end-to-end anchor for them is
  arm 4's `B0 → B1`.
- The plane-resolution question is **open**, not answered.

**What would falsify §1.** A render actually emitted at 6550 × 4367 that
measures materially sharper than today's on the band-matched axis. I could not
produce one — the change is in `merge_cmd.rs`, which is contended — so if
someone builds it and it wins, I am wrong. The cheapest single check is SNAP: if
a build that forces integer offsets does *not* come out near-free, my account of
where the cost lives is wrong.

## 8. Files and ownership

I changed **no code**. Nothing in `image_out.rs`, `color.rs` or `demosaic.rs` is
implicated by this arm, and I did not edit them.

The levers this arm identifies are both outside my ownership:

- the interpolation kernel — `crates/strehl-core/src/align.rs` and
  `crates/strehl-core/src/warpmap.rs`. Verbatim patch already delivered in
  `docs/research/M95-resample.md` §9, compiled standalone under `rustc`.
  **`align.rs` has uncommitted work from M103 in it**, so that patch still needs
  arbitration before it is applied.
- the coverage geometry — `crates/strehl-cli/src/align_cmd.rs` (`fit_to_cover`)
  and `crates/strehl-cli/src/merge_cmd.rs`. **Contended, not mine, and on this
  measurement not worth changing anyway.**

## 9. A request

The `SNAP` result says the gather is free at integer offsets. That is not
reachable for a real handheld or rail stack, but it bounds the prize: everything
the gather costs is recoverable in principle by a better reconstruction, and
nothing is recoverable by moving the output grid. If the project wants that
prize, the kernel is the only lever in this family, and choosing it needs an
eye-graded comparison on the halo edges M87 owns, because arm 4 measured
Lanczos-3 ringing **9.902×** more than Catmull-Rom.

## Candidate facts

**P57.** Removing the coverage rescale and emitting at native sampling recovers
−0.0042 dex on `bee-3-cpl` — nothing, and marginally negative. Measured against
the real 299-frame sidecar with n = 960 tile-frame pairs per arm: NOW +0.1813
(sem 0.0031), FIX +0.1855 (sem 0.0017).
*Significance:* retires the leading proposed sharpness fix before it is built.
*Label:* MEASURED.

**P58.** One Catmull-Rom gather costs −0.0003 dex (sem 0.0005) when every frame
is placed at an integer offset with unit scale. The entire cost of the gather is
sub-pixel phase, not resampling as such.
*Significance:* bounds the prize and identifies the only lever — reconstruction
quality, since integer placement is unreachable for a real stack.
*Label:* MEASURED.

**P59.** The cost of a pure scale gather is a threshold in the presence of
sub-pixel phase, not a dose in enlargement magnitude. A 0.01% enlargement costs
+0.0755 dex; a 7.35% one costs +0.1836; a 42.86% one costs +0.1080, less than
the 1.01% case at +0.1849.
*Significance:* refutes "the enlargement is 7.35% so it costs 7.35%-worth" for
any future output-geometry proposal.
*Label:* MEASURED.

**P60.** The real `bee-3-cpl` warps have sub-pixel phase indistinguishable from
uniform: fractional displacement mean 0.5086 / sd 0.3042 at the plane centre
against uniform's 0.5000 / 0.2887, with 1.3% of frames within 0.05 px of an
integer where uniform predicts 9.8%. The per-frame solve also carries scale from
−3.113e−02 to +5.037e−02, independent of coverage.
*Significance:* explains P57 mechanically — the warp supplies the same phase the
coverage scale did, so removing one cannot help.
*Label:* MEASURED.

**P61.** `fit_to_cover` composes the coverage scale onto each frame placement and
returns `s.then(*t)`, one fused matrix. The coverage scale acting alone on an
identity warp costs +0.183568 dex, matching the independent k = 0.9315 ladder
entry of +0.1836 to five decimals.
*Significance:* two independent code paths agreeing is the internal consistency
check that licenses §2 and §3; also settles "one gather or two" as one.
*Label:* MEASURED.

**P62.** rawpy's demosaic versus strehl's Malvar-He-Cutler on the same frame is
−0.0332 dex, 1.079× power. The confound flagged three times against
`fullres_check.py` is real but small and does not carry any material part of
that script's deficit.
*Significance:* closes an outstanding caveat on an externally measured number,
from inside the codebase where it could be measured.
*Label:* MEASURED.

**P63.** Scaling a tile about its own centre rather than the field centre
collapses the measured cost of a small enlargement by 8× — +0.0340 dex against
+0.1793 at k = 0.997 — while every control still passes, because every tile then
sits at near-integer base phase.
*Significance:* a synthetic resampling harness must place tiles on the true
output grid; this defect is silent and flatters the pipeline under test.
*Label:* MEASURED.

**P64.** A per-plane CFA gather does not manufacture aliasing into
0.30–0.48 cyc/mosaic px: fed a field band-limited below plane Nyquist
(suppression 1.266e+07×), it emits 0.41× the out-of-band energy a
full-resolution gather does.
*Significance:* refutes the obvious explanation for the plane-resolution arm's
sign flip and keeps P56 at ARGUED rather than letting a plausible story upgrade
it.
*Label:* MEASURED.

**P65.** A sharpness band of 0.30–0.48 cyc per mosaic px lies at
0.60–0.96 cyc per plane px, above a single CFA plane's Nyquist of 0.50. Detail
in that band exists only in the interleaved lattice of all four planes, not in
any one of them.
*Significance:* any comparison of a plane-grid operation against a mosaic-grid
one on that band is measuring reconstruction, not signal; this is why the
plane-resolution arm was withdrawn.
*Label:* DERIVED.
