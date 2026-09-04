# M8-COMPARATIVE — foreign-render applicability and candidate census

**State at this commit: PRE-REGISTERED; no outcome pixel has been read by this
lane.** Frozen at `2026-09-03T19:41:01.975-07:00`.

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
