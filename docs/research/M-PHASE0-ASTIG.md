# M-PHASE0-ASTIG — orientation-resolved through-focus split

**Claim:** C7 in `docs/proposals/2026-08-sota-path.md`
**Status:** complete; the registered instrument refused the decisive statistic
**Preregistration:** `experiments/M-PHASE0-ASTIG/PREREGISTRATION.md`, committed
as `bc3b00c53202f883c24bc098d4b903189c1a529b` before any real-effect
measurement

## Verdict

<!-- claim:verdict -->
**NOT ROBUST.**

<!-- claim:decisive-gate -->
The deciding quantity is **2 valid outer sectors out of 4 in `grid1-sw4`**;
the preregistered minimum is **3 valid sectors in each primary setup**.
`grid2-sw4` has 3. This is a deterministic validity count, not a parameter
estimate; each constituent tile gate uses a 2,000-draw paired block-bootstrap
95% interval. The registered `D4` is therefore **not estimable**, so this result
is neither evidence that C7 survives nor evidence that it is killed.

The failure is specific. At field radius 0.90 in `grid1-sw4`, the left and right
tiles were rejected because one arm's 95% peak interval was respectively
**2.688939** and **2.282475 frames** wide, above the fixed 1.50-frame limit.
Only top and bottom remained. Section 9 of the preregistration says to stop
rather than interpret numbers under exactly this condition; section 5 assigns
it to NOT ROBUST.

## What C7 actually asked

C7 asks for separate through-focus `Gx²` and `Gy²` responses, M33
three-point log-parabola peak fits, and a field map of
`delta_astig = z_tangential - z_sagittal`. The dispatch summary was accurate
about the optical question and algorithmic consequence.

One implementation detail in the proposal is stale. It says strehl elects with
“Tenengrad sums `Gx² + Gy²`.” The estimator backend currently computes
`sqrt(Gx² + Gy²)` in `crates/strehl-core/src/focus.rs`, while the shipping
default is the scalar luma-band selector in
`crates/strehl-core/src/pyramid.rs`; `docs/ARCHITECTURE.md` sections 5a and 8
make that backend split explicit. Both paths remain orientation-blind, so C7's
decision question still matters, but the proposal's exact formula and default
path do not describe current Rust.

## Corpus search before measurement

No prior commissioned sagittal/tangential **focus-split** measurement was
found.

* `docs/research/M16-orientation-fpn-measured.md` is preregistered and finds
  scene-gradient anisotropy (14–22x) rather than an optical focus split. It is
  a warning that global `Gx/Gy` amplitude is not astigmatism.
* `docs/research/M103-halfdrift.md` prominently retracts its earlier +37%
  acutance interpretation. Its orientation statistic concerns rendered
  registration smear, not two through-focus peaks.
* `docs/research/BUILD-SHARP.md` names astigmatism only as one unseparated
  candidate for a 2.2x non-diffraction blur and withdraws the associated
  aperture inference. It does not attribute that blur to astigmatism.
* `experiments/M128-razor-ladder/out/controls.json` reports 5 PASS / 5 FAIL and
  stops before any real measurement frame. The razor is therefore not a
  commissioned optical-width reference here.
* `docs/research/M-PHASE0-RHO.md` reports a separately commissioned physical
  diagnostic: the calibration grid has a 0.039062 cyc/sensor-px fundamental on
  both axes. That supports using the grid for paired orientations but says
  nothing about their best-focus separation.

None of these sources answers C7, and retracted material was not reused as
evidence.

## Registered instrument

The primary data are the two step-width-4 calibration-grid placements (55 and
46 ARWs). The step-width 1/10 stacks form a sampling ladder. Five fixed-subject
fabric stacks at f/5.6, f/8, f/11, f/14, and f/18 form an aperture falsifier.
A texture-poor region from the razor f/8 stack is a refusal control only.

Seventeen coordinates were fixed before image content was read: centre plus
four cardinal sectors at radii 0.25, 0.50, 0.75, and 0.90. Each RAW quad was
reduced to `(G1+G2)/2`; per-frame Sobel energies were divided by squared local
mean. The two peak locations use the same tile, frames, weights, and bootstrap
draws.

Cardinal mapping swaps the arm order at top/bottom so a radial-versus-
tangential split has one sign around the field. The radius statistic is the
median of at least three mapped sectors. The registered headline was

```text
D4 = abs(mean(delta_grid1-sw4(r=.90), delta_grid2-sw4(r=.90)))
```

with one captured frame as the materiality bar.

### Field curvature separation

Field curvature and chart tilt move both orientation arms together. For each
tile the reduction keeps

```text
mu    = (z_t + z_s) / 2
delta =  z_t - z_s
```

and never subtracts a fitted surface from `delta`. A robust plane and radial
bowl are fitted only to `mu`, for display and empirical sampling-width
calibration. Thus a wrong curvature model cannot create the registered local
split. The grid puts both orientations on the same film plane, unlike fabric
threads that can occupy different physical heights.

### Declared bias direction

Fixing the headline at the outer field, where optical astigmatism should be
largest, favours SURVIVE. Noise/alias energy can create arm-specific maxima and
also favours SURVIVE. A 192-pixel tile can blend local optima and favours KILL.
The four-sector median can suppress real decentered asymmetry and favours KILL;
the preregistration therefore forbids averaging away a sector conflict. The
clean SURVIVE result was declared the result to distrust most.

## Commissioning

<!-- claim:commission -->
The estimator passed **8 of 8 controls** and all **8 of 8 named plants went
RED**. A fully present planted four-frame split read **3.999423 frames**.
The cancellation-immune external predicate consists of literal response
tables, never touched by the generator; its fixed 4.125-frame separation read
**4.125000**. Across 100 independently generated noisy cubes, nominal 95%
coverage was 92/100 and empirical-SD/reported-SE was 1.06515.

The controls covered pooled arms, dose response, field-ramp/curvature
rejection, cardinal mapping, focus-axis reversal, flat refusal, sub-frame peak
fit against the external predicate, and paired-bootstrap uncertainty. Each
targeted defect made its own check RED. Cardinal mapping also had to match a
literal four-sector geometry table outside the synthetic image factory.

The amended decoder gate reproduced 2/2 contracts and its padded-shape plant
went RED. Rawpy twice returned the same 4688x7028 visible array and checksum;
the Rust/rawler probe returned its known 4688x7032 active representation.
Coordinates use only rawpy's copied visible array and clipping uses rawler's
stricter 15360 linear white. The four-column representation difference is
covered by the registered plus/minus-two-green-column sensitivities.

The stop-gate evaluator was independently commissioned on literal dictionaries:
**6 of 6 gate controls passed and 6 of 6 disabling plants went RED**.

## Real-capture result

<!-- claim:capture-accounting -->
Extraction opened 915 registered ARWs (242 grid, 623 fabric, and 50 razor
control); the before/after capture inventory was unchanged.

The primary outer-field accounting is:

| setup | valid sectors | mapped point values (frames) | result |
|---|---|---|---|
| `grid1-sw4` | top, bottom (2/4) | +0.404859, -0.021322 | refuses |
| `grid2-sw4` | right, top, bottom (3/4) | -0.063683, +0.583129, -0.051409 | valid alone |

<!-- claim:grid2-diagnostic -->
The non-decisive `grid2-sw4` radius median is **-0.051409 frames**, with
ordinary bootstrap 95% interval **[-0.193464, +0.549880]**. It is not `D4` and
cannot substitute for the failed pair.

The centre-null stop did not fire and the razor flat tile correctly refused.
No fabric aperture has three valid outer sectors, so aperture robustness could
not be verified.

### Falsifiers and sensitivities

<!-- claim:sensitivities -->
All **14 of 14 registered sensitivities** were run: tile 128/256, G1/G2,
3x3/5x5 blocks, horizontal coordinate minus/plus two green columns, linear fit,
log fit without baseline, and omission of each cardinal sector.

Only tile-256 and x-minus-2 made both primary outer rows valid. Their
non-substitutable `D4` diagnostics were 0.024268 frames (signed 95% interval
[-0.357844, +0.294579]) and 0.107102 frames
([-0.451282, +0.249990]), respectively. The primary, tile-128, G1, G2, both
block grids, x-plus-2, both fit variants, and all four sector omissions still
refused at least one primary outer row. This dependence on tile/coordinate
choice reinforces the NOT ROBUST disposition; it does not license choosing a
valid arm after the fact.

The step-width-1 grid stack had only four valid tiles total, so the complete
sampling ladder refused. As a diagnostic only, step-width-4/10 `mu`-plane slope
ratios were 2.0469 and 2.0236 in the two setups; the corresponding coarse-stack
outer points rescale to -0.0795 and -0.1398 step-width-4 frames. No
multiplicity-controlled field or ladder classification was made after the
registered stop.

## What changes in Rust

<!-- claim:rust -->
**No Rust source changes.** In particular, do not alter
`crates/strehl-core/src/focus.rs`,
`crates/strehl-core/src/pyramid.rs`, or
`crates/strehl-cli/src/merge_cmd.rs` from this verdict.

This is not “nothing changes because astigmatism is absent.” It is “nothing
changes because the primary controlled chart did not support the registered
decision statistic.” C7 stays unresolved and must not enter the phase-3
implementation queue. A new controlled chart repeat needs broader,
orientation-balanced texture or a longer bracket at the outer horizontal
sectors; it must be preregistered rather than relaxing the 1.50-frame gate on
these data.

## Reproduction and traceability

From the repository root, with `PYTHONIOENCODING=utf-8` and
`PYTHONPATH=experiments/M-PHASE0-ASTIG/src`:

```powershell
python experiments\M-PHASE0-ASTIG\src\commission.py
python experiments\M-PHASE0-ASTIG\src\loader_check.py
python experiments\M-PHASE0-ASTIG\src\real_measure.py --stacks all --workers 4
python experiments\M-PHASE0-ASTIG\src\reduce_real.py --variant primary --bootstraps 2000
# Repeat reduce_real.py for the 14 variants named above.
python experiments\M-PHASE0-ASTIG\src\commission_verdict.py
python experiments\M-PHASE0-ASTIG\src\verdict.py
python experiments\M-PHASE0-ASTIG\src\report_check.py
```

Every JSON output records its invocation; extraction inventory and reductions
record capture/cache hashes, and `out/verdict.json` records every reduction
hash it consumed.

## Not verified

* `D4`, simultaneous multiplicity-controlled bounds, and a C7
  SURVIVE/NARROWED/KILL classification were not computed because the
  preregistered stop fired.
* The fabric aperture and complete sampling-width ladders did not have enough
  valid tiles to classify.
* The two RAW decoders were not compared pixel-by-pixel: the Rust probe exposes
  no checksum or per-plane moments. Their separate committed representation
  contracts passed.
* This one body/lens/teleconverter configuration cannot establish how another
  optical sample behaves.
