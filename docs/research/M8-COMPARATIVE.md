# M8-COMPARATIVE — foreign-render applicability and candidate census

**Final verdict: exact comparative M8-O and its requested magnitude
distributions are UNMEASURED because none of the nine foreign renders supplies
the complete geometry/radiometry contract.** No retained render outcome pixel
was read by this lane. Predicates and exhaustive selection were committed
first at `7601657fe87852049095b1c1cf67f28f4185fc37`, frozen at
`2026-09-03T19:41:01.975-07:00`. Follow-up synthetic analysis, separately
preregistered at `c107e1cf`, rejects `~6%` as a universal Catmull-Rom ceiling:
the exact single-pass two-dimensional separable support bound is `28.125%` of
local support span. M8-O can establish invention, but magnitude alone cannot
name sharpening without the exact operator chain.

## 0. Question and prior art

The primary question is not a rate. It is whether exact M8-O can be evaluated
on the retained foreign renders at all. A foreign render is admissible only
when its pixels and every source frame can be placed at the same coordinates
in one documented linear domain. If that cannot be established, this lane will
report `UNMEASURED`, not substitute a local envelope or outcome-fitted proxy.

The mechanical rule-40 search was:

```text
python experiments\ORCH-drift-check\prior_art.py source hull overshoot comparator sharpening
```

It returned `BUILD-HULL.md`, `M8-overshoot.md`, `V-hull.md`,
`C-landscape.md`, `V-SPEED.md`, `V-ADJ13.md`, `V-REVIEW-halo.md`,
`M60-prior-art-and-the-rival-explanations.md`, and mentions in
`ORCH-veiling.md`, `M83-survey-audit.md`, `V-HEADTOHEAD3.md`, `V-GATHER.md`
and `BUILD-SHARP.md`. The load-bearing definitions are the scorecard M8
section, `M8-overshoot.md`, and `V-HEADTOHEAD3.md`. The last already warns
that its sharpening follow-up lacks a common linear input and independent
per-frame output warp; this lane tests that warning as an admission question
rather than assuming it.

## 1. Holdout ruling

No holdout is opened. The registered subjects are the already-observed
`113MSDCF`, `119MSDCF`, and `coffee-bean` comparator artifacts.
`113MSDCF` is `HISTORICAL CONTROL — NOT HOLDOUT` and `coffee-bean` is
`FIXED HISTORICAL BENCHMARK — NOT HOLDOUT` in scorecard v1.2. Under its
literal rule, only a manifest row whose evidence class begins `HOLDOUT` is a
holdout; `119MSDCF` is not designated as one. The unit remains subject plus
uninterrupted session.

## 2. Frozen selection

`experiments/M8-COMPARATIVE/candidate-manifest.json` registers all nine
unique-byte renders from the prior comparator census before this lane reads
any image sample:

* Zerene: two `113MSDCF` PMax renders and three `119MSDCF` PMax/UDR renders;
* focus-stack: three unique `119MSDCF` variants and one `coffee-bean` render.

`stack_v3.tif` is the byte-identical alias already identified by
`V-HEADTOHEAD3` and is not counted twice. There is no Helicon arm. Selection
is exhaustive, not outcome-dependent. If admitted, the site is the complete
geometrically valid output, all three channels; there is no ROI selection.

The same-stack strehl artifacts registered for provenance are the three
DELIVER-V6 masters. They are display-referred `--srgb` files, not the final
linear output M8-O requires. A new linear strehl render will be made only if a
foreign arm first passes every applicability predicate; otherwise there is no
common comparison to justify rendering.

## 3. Exact applicability predicates

Every predicate below is mandatory. One failure makes the render
`UNMEASURED` for exact M8-O:

1. output hash matches the frozen artifact;
2. every source image exists and source identity is auditable;
3. an exact output-to-source placement exists for every frame;
4. the exact discrete resampler support is known;
5. crop, rotation, orientation and scale map output sample centres exactly;
6. source and output are mapped into one documented linear RGB domain;
7. every per-frame gain, offset, colour conversion and spatial photometric
   correction into that domain is known in executable form and in order;
8. serialization is known (`0.5/65535` only for uint16).

Same dimensions are not geometric evidence. A content-fitted registration is
not exact placement evidence: subpixel model error at an edge can create a
false hull failure. A filename saying `rec2020`, an untagged RGB TIFF, or a
monotone relationship fitted from the outcome is not a linear-domain
contract. A crop size without its origin is not a coordinate map. A retained
affine matrix without the interpolation support is insufficient.

## 4. Measure and failure direction

If any arm passes §3, this lane will use the byte-identical copy of
`experiments/M8-overshoot/checker.py`, SHA-256
`B66C9465D5F644D66646A14722475987F187E32B02ED3B687997C18CE1670B89`.
It will not write a second hull implementation. The denominator is every
channel sample bracketed by at least one geometrically valid frame. Report
lower/upper counts, total/denominator, rate, and maximum signed lower/upper
excess. Float output receives no serialization tolerance; uint16 receives
exactly `0.5/65535` in addition to the largest contributing `tau_R`.

The registered prediction is directional: on a valid same-stack,
same-input-development pair, a sharpened output has a higher M8-O violation
rate and/or larger extrema than its unsharpened partner. Equal or lower is a
failed prediction. The retained nominal 113 pair is not silently treated as a
pure sharpening experiment: `V-HEADTOHEAD3` records eleven development
differences, including Dehaze/Enhance and colour NR.

M8-O is one-sided. Nonzero is strong evidence that output values were invented.
Zero never proves their absence because final clamping can erase the evidence.
If an arm is zero, rail occupancy and clamping must be reported before any
favourable interpretation.

## 5. Commissioning registered before audit

The unchanged checker inherits M8's existing RED/GREEN commissioning:
fractional Catmull hard step RED; exact copy and convex bilinear GREEN; explicit
`lo/hi +/- 32*tau` plant found in both signs. This lane will rerun it unchanged.

The only new code, `applicability.py`, is an admission auditor, not a hull
checker. Its commissioning is:

* GREEN: a complete untouched contract is admitted;
* RED: removing any one mandatory predicate is rejected;
* improvement: restoring the planted missing resampler support changes the
  same record from rejected to admitted.

No real output sample may be read until this pre-registration is committed.

## 6. Governance

Any result is a **candidate comparative reading**, not an M8 score. The
scorecard currently owns M8 as a strehl self-check and is read-only to this
lane. A precise proposed comparative clause will be drafted here after the
audit and explicitly marked as requiring the `sota-scorecard` registrar's
licence.

## 7. Commissioning and audit execution

After commit `7601657f`, the new admission auditor passed all registered
controls (`applicability-commission.json`):

| control | result |
| --- | --- |
| complete untouched contract | GREEN, admitted |
| each mandatory predicate removed in turn | RED, 9/9 rejected |
| missing support restored on the same record | improvement, reject → admit |

The unchanged M8 checker was re-asserted against the prior lane's committed
commissioning summaries, copied read-only into this lane's `checker-fixture`
(`checker-commission.json`): Catmull hard step
`28/252`, 14 each sign, extrema `-0.0625/+0.0625`; copy `0/252` with exact
copy error zero; bilinear `0/300`; explicit plant `2/252`, one each sign.
`checker-independence.json` confirms the copied SHA-256 and no Strehl import.

The first real admission run exposed two implementation errors in
`applicability.py`, preserved verbatim as
`applicability-results-v1-semantic-bug.json` (SHA-256
`5A66B389378CB0EF10D5B80C5851C6F996835621FF9B5FCDD8C8EA65CFF40FF5`).
It treated a complete count of rounded log matrices as exact placement and
found the word `exact` inside the negative sentence *"not the exact
interpolation support"*. Both errors biased toward admitting coffee. Coffee
still failed two other mandatory predicates, so the zero-admissible headline
did not change. The repaired auditor uses explicit booleans for the five exact
contracts; its rerun is `applicability-results.json`.

## 8. Applicability result — the primary answer

M8-O is applicable to a foreign renderer **in principle**, but “black-box” does
not mean “metadata-free.” The final output can be opaque; the checker still
needs enough evidence to place each output sample into every source frame and
to compare the corresponding values in one linear domain. The scorecard itself
names active placement and linear source planes as evidence inputs.

No retained comparator passes:

| arms | what exists | decisive missing evidence |
| --- | --- | --- |
| 5 Zerene PMax/UDR | output hashes; all 63/33 source TIFFs; prior identity census | no per-frame placements, resampler support, crop/orientation map, output linear-domain tag/contract, or per-frame photometric map |
| 3 marker focus-stack variants | output hashes and dtype/shape | all source TIFFs and exact invocation are deleted; therefore identity, geometry and source domain are unrecoverable |
| coffee focus-stack | 105 sources; 104 logged transforms plus one identity; 104 contrast and WB rows; log says linear Rec.2020 gamma 1.0 | matrices and corrections are rounded log text, not exact executable transforms; no interpolation support; crop size but no exact output coordinate origin; no formula/order for spatial contrast and WB correction |

All comparator outputs are `4672x7008x3`. The Zerene outputs are untagged
uint16; their Lightroom sources are untagged float32 TIFFs. Same dimensions do
not prove unchanged geometry. Coffee explicitly expanded to `7168x5120`,
aligned frames, then cropped to `7008x4672`; the retained log therefore proves
that identity-coordinate comparison would be wrong while lacking the precision
needed to reconstruct the right one.

An executable search did not close the coffee gap
(`focus-stack-executable-provenance.json`). The archived render is dated
2026-05-11. The available customized binary, SHA-256 `0ABA0CF0...74CA45D`,
is dated 2026-05-17; the other binary has a different hash and predates the
run. The log contains no version, commit or executable hash, and the available
source tree has no Git metadata. Therefore neither binary can be bound to the
archived pixels, and consulting its current implementation would not recover
the missing historical contract.

The three registered strehl masters hash correctly, but are
`4688x7032x3` display files whose descriptions say sRGB, *For viewing*, and
record nonlinear tone rendering. They are neither on the comparator grid nor
the final linear M8 boundary. Inverting them would not restore values lost to
tone/clamping and would not recover foreign per-frame placement. Because no
foreign arm passed, the preregistered stop rule correctly prevented a new
linear strehl render.

The comparison becomes invalid if a renderer silently aligns, rescales,
rotates, crops, locally warps, changes interpolation support, applies a colour
matrix, per-frame gain/offset, local tone, denoise, clipping, or output tone
without retaining the exact mapping. Content-fitting those terms from the
outcome is also invalid for exact M8: model error at an edge can manufacture
the violation the statistic is meant to detect.

## 9. Requested rates and common stacks

There are **no new same-stack M8-O rates, denominators or extrema**:

| subject | strehl exact M8-O | comparator exact M8-O | common? |
| --- | --- | --- | --- |
| `113MSDCF` | `UNMEASURED` (available master is sRGB) | `UNMEASURED` | no |
| `119MSDCF` | `UNMEASURED` (available master is sRGB) | `UNMEASURED` | no |
| `coffee-bean` | `UNMEASURED` (available master is sRGB) | `UNMEASURED` | no |

The only commissioned strehl reading remains the already-published,
**non-common-stack** development result; it was not repeated:

```text
983,648 / 74,173,536 = 1.326144%
signed extrema: -1.049185276 / +0.003703290 linear
```

Those are the three flat-slide stacks in `M8-overshoot.md`, not 113, 119 or
coffee. Comparing that rate to an absent comparator denominator would be false
precision. `results-summary.json` records all null fields explicitly rather
than encoding `UNMEASURED` as zero.

## 10. Sharpening pair and registered prediction

The nominal 113 Sharpness-0/Sharpness-40 pair cannot answer the registered
prediction.

1. It lacks exact foreign placements, support and output-domain mapping.
2. It is not sharpening-only: `V-HEADTOHEAD3` records eleven development
   differences, including colour NR and Dehaze/Enhance.
3. Most importantly, Lightroom sharpening was applied to the **source TIFFs**.
   If each PMax output were compared against its own actual inputs, that
   upstream overshoot would already lie inside the source hull. M8-O can detect
   invention after its declared input boundary; it cannot retroactively audit
   processing baked into that boundary.

Comparing PMax40 against PMax0's input hull would appear to solve (3), but is
invalid because the source pixels differ in eleven fields. Therefore the
sharpening movement is `UNMEASURED`, and the prediction is **neither confirmed
nor refuted**. The theory did not fail; the retained experiment cannot test it.

A direct mechanism test requires one byte-identical, tagged linear source set,
one frozen foreign geometry/run manifest, and two outputs differing only in a
post-input sharpening amount. The unsharpened intermediate must be retained,
and clipping/rail occupancy reported for both.

## 11. One-sided interpretation

No clean comparator result was observed; none was measured. Thus there is no
occasion to infer that clamping hid a pass. The asymmetry still governs the
future experiment:

* nonzero M8-O licenses “this output contains values outside its source hull”;
* zero licenses only “no surviving excursion was observed at this boundary”;
* zero never licenses “the renderer did not invent detail,” and must be paired
  with direct clamping/rail occupancy.

The orchestrator's supplied synthetic result materially strengthens the
interior case: its USM excursions were unchanged after global `[0,1]` clipping.
That does not repeal the registered one-sided rule or repair an unknown output
tone map. It establishes that rail clipping is not a general attack on local
M8-O sensitivity; it does not establish that every excursion survives at a
rail.

## 12. Proposed comparative clause — registrar licence required

> **Candidate comparative M8-O (not scored).** A foreign render may receive a
> candidate M8-O reading only when the exact source bytes, source identities,
> per-frame output-to-source placements, discrete resampler supports,
> crop/orientation/scale mapping, common linear colour domain, ordered
> per-frame photometric transforms, and serialization contract are frozen
> before output samples are inspected. Apply the commissioned producer-
> independent M8 checker over every geometrically valid output sample and all
> frames; report lower/upper counts, both the all-output-sample and
> valid-source-hull denominators, fractions, signed extrema, coordinates, and
> absolute-excess median/p99/maximum in linear units and serialized DN. Report
> sign balance but do not treat symmetry as a mechanism discriminator. A
> nonzero result is evidence of surviving invented values. A zero result is not
> a pass because clipping or another frame's broad hull may hide invention.
> Attribute an excursion beyond resampling only against the frozen pipeline's
> exact per-sample negative-weight bound, including every resampling pass; no
> generic `~6%` ceiling is licensed. Even a bound exceedance establishes only
> that the declared interpolation model is insufficient, not that sharpening
> was the cause. A sharpening comparison is licensed only for byte-identical
> inputs and geometry with sharpening as the sole changed setting.

This extends a registered strehl self-check and therefore requires the
`sota-scorecard` registrar's explicit licence before entering the scorecard.

## 13. Reproduction

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:OMP_NUM_THREADS = '6'
$env:OPENBLAS_NUM_THREADS = '6'
$env:MKL_NUM_THREADS = '6'

python -B experiments\M8-COMPARATIVE\applicability.py --commission
python -B experiments\M8-COMPARATIVE\applicability.py `
  --output experiments\M8-COMPARATIVE\applicability-results.json
python -B experiments\M8-COMPARATIVE\checker.py commission-assert `
  --root experiments\M8-COMPARATIVE\checker-fixture
python -B experiments\M8-COMPARATIVE\checker.py independence
python -B experiments\M8-COMPARATIVE\kernel-bound.py `
  --output experiments\M8-COMPARATIVE\kernel-bound-results.json
```

The admission audit opens TIFF containers and metadata only
(`tifffile.TiffFile`); it never calls `imread`, `asarray` or `memmap` on image
samples. No Rust file changed. No file under `D:\personal\macro` or
`D:\edited\macro` was written, moved, renamed or deleted.

## 14. Follow-up preregistration — magnitude versus kernel mechanism

The orchestrator supplied a 1-D synthetic premise test after the first final
report. Its registered null was `0.0000%`; USM amount
`0.3/0.5/1.0/2.0` produced monotone
`0.6836%/1.1475%/1.9043%/5.8350%`, unchanged by `[0,1]` clipping.
This lane accepts that result as supplied and does not repeat it. It supports
the narrower proposition that global rail clipping need not erase local
interior excursions. It does not supply a missing foreign linear-domain or
geometry contract.

The same message proposes distinguishing resampling from sharpening by treating
the commissioned half-phase Catmull hard-step excursion, `0.0625` of a
full-scale step, as an approximate interpolation ceiling. Before executing new
code, this lane registers a direct two-dimensional test of that ceiling:

1. `kernel-bound.py` is synthetic kernel algebra, not another M8 checker, and
   will read no real render pixels.
2. All magnitudes are divided by the exact local interpolation-support span
   `hi-lo`; raw normalised-output magnitude alone is not a kernel comparison.
3. The half-phase one-dimensional hard step should reproduce `0.0625`.
4. A phase-optimal one-dimensional hard step should exceed it: the registered
   Catmull prediction is `2/27`, approximately `0.074074`.
5. For arbitrary bounded support values, the registered negative-weight-mass
   bounds are `0.125` in one dimension and `0.28125` for a separable
   two-dimensional kernel. The latter follows from
   `N_2D = n_x + n_y + 2*n_x*n_y` with `n_x=n_y=0.125`.
6. Therefore, if the implementation confirms those values, `~6%` is rejected
   as a universal Catmull bound and an observed excursion above it cannot by
   itself identify sharpening.
7. The controls are a convex-kernel GREEN null, Catmull upper/lower RED plants,
   and an improvement arm that removes the negative lobes (`a=-0.5` to `a=0`)
   and must reduce the planted excess to zero.

No comparator becomes admissible merely because a magnitude discriminator is
proposed. Real-render rate, median, p99, maximum and sign symmetry remain
`UNMEASURED` unless the frozen §3 contract is recovered. A finite render also
cannot exhibit an “unbounded tail”; unbounded growth is a property of a
controlled gain sweep, not one empirical histogram.

## 15. Follow-up result — the `~6%` discriminator fails

The preregistered script passed every control. The convex null read zero; the
Catmull plant found exactly symmetric lower/upper excursions; changing the
negative-lobe parameter from `a=-0.5` to `a=0` reduced the same plant to zero.
`kernel-bound-results.json`, SHA-256
`8F1AB53132C40249A3B5C1AC909B9C43C1FE2D2F8013A41588ED7ED3E6220F32`,
contains the full result.

| Catmull-Rom case | excess / local support span | full-scale uint16 equivalent |
| --- | ---: | ---: |
| 1-D hard step, half phase | `0.062500` | `4095.9375 DN` |
| 1-D hard step, phase `1/3` | `0.074074` | `4854.4444 DN` |
| 1-D arbitrary bounded support | `0.125000` | `8191.8750 DN` |
| separable 2-D arbitrary bounded support | `0.281250` | `18431.7188 DN` |

The half-phase commissioning value was one plant, not a kernel maximum.
Catmull's one-dimensional negative mass is
`n(t)=0.5*t*(1-t)`, maximised at `0.125`. For the separable two-dimensional
kernel the negative mass is `n_x+n_y+2*n_x*n_y`, maximised at `0.28125`.
Upper and lower bounds are exactly symmetric. Therefore neither sign symmetry
nor excursion above `6%` separates sharpening from resampling.

Across the registered uniform 1024-interval phase grid, the worst-case bound
distribution—not an observed-image distribution—had
median/p99/max `0.093750/0.124987/0.125000` in 1-D and
`0.183201/0.279254/0.281250` in 2-D. It cannot substitute for the requested
per-render histogram; it shows why a fixed `~6%` cutoff is not conservative.

For a declared single resampling pass, a defensible per-sample diagnostic would
normalise excess by that sample's support span and compare it with the exact
negative weight mass at its two fractional phases. Multiple passes require the
composed operator bound. Exceeding that bound rejects the declared resampler as
the sole explanation, but still does not identify sharpening rather than local
contrast, deconvolution, non-convex merging or an omitted transform.

The requested real-render fields remain:

| render IDs | all-pixel rate | valid-hull rate | median / p99 / max | sign symmetry | kernel comparison |
| --- | --- | --- | --- | --- | --- |
| `113-pmax-0`, `113-pmax-40` | `UNMEASURED` | `UNMEASURED` | `UNMEASURED` | `UNMEASURED` | unknown Zerene operator |
| `119-pmax`, `119-pmax-udr`, `119-pmax-udr-neutral` | `UNMEASURED` | `UNMEASURED` | `UNMEASURED` | `UNMEASURED` | unknown Zerene operator |
| `119-focus-stack-float`, `119-focus-stack-defringed`, `119-focus-stack-u16` | `UNMEASURED` | `UNMEASURED` | `UNMEASURED` | `UNMEASURED` | sources and invocation absent |
| `coffee-focus-stack` | `UNMEASURED` | `UNMEASURED` | `UNMEASURED` | `UNMEASURED` | producing executable and exact operator unbound |

The nominal sharpness pair remains unusable: its source pixels differ in eleven
development fields, sharpening is upstream of each declared hull, and no
frozen common placement survives. Consequently the within-pair movement and
the registered sharpening prediction remain **untested**, not negative.
