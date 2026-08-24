# M78b pre-registration — B6 ROI fixture repair

**MEASURED — ordering.** This document is written after a header-only geometry audit and before
M78b decodes any held-out pixel, changes the B6 registry, or runs any candidate measurement.

**MEASURED — metadata boundary.** The pre-repair audit uses `rawpy.imread(...).sizes.height` and
`.sizes.width` only. `rawpy.imread` calls `open_file`; the audit never calls `unpack`,
`raw_image`, `raw_image_visible`, or `postprocess`.

**MEASURED — source defect.** `spec_v1.py::roi_rule` consumes tuples named `(fx, fy)` and returns
tuples consumed as `(x, y, width, height)`. Every pixel loader indexes raw rows from `y` and raw
columns from `x`. The registry declares `QUAD_W=2344, QUAD_H=3514`, while all six held-out stacks
have visible raw shape `(4688,7028)` and therefore quad shape
`(height,width)=(2344,3514)`.

**DERIVED — transposition verdict.** The legacy width equals the measured quad height and the
legacy height equals the measured quad width. The row/column-transposition hypothesis is
**CONFIRMED** at the fixture-generation source, not inferred from one failing index.

## 1. Frozen repair rule

**ARGUED — authoritative intent.** `ROI_FRACTIONS` is the normative fixture: four `(fx,fy)`
locations at `(0.25,0.25)`, `(0.75,0.25)`, `(0.50,0.50)`, and `(0.50,0.80)`. The prose in
`docs/research/M55-acceptance-spec.md` also calls these fractions of the quad plane. The emitted
legacy integer coordinates are a derived fixture and do not outrank that rule.

**ARGUED — rejected minimal repair.** M78b will not keep the first three legacy coordinates and
choose only a fourth. The first three are silently in bounds despite being generated against
swapped dimensions. Preserving them would retain the defect and would make the fourth replacement
an arbitrary new choice.

**ARGUED — rejected tuple swap.** M78b will not simply exchange each legacy `x` and `y`. That
recovers the intended location only where `fx=fy`; for `(0.75,0.25)` it also exchanges the two
fractions.

**ARGUED — selected repair.** M78b will rename the geometry constants unambiguously to
`QUAD_HEIGHT=2344` and `QUAD_WIDTH=3514`, retain the existing side 512, pad 32, rounding, and clamp
formula, and regenerate all four ROIs from the frozen fractions without reading image content.

**DERIVED — expected repaired registry.** The selected rule must produce exactly:

```text
[(750, 458, 512, 512),
 (2252, 458, 512, 512),
 (1501, 916, 512, 512),
 (1501, 1466, 512, 512)]
```

**ARGUED — no selection.** No coordinate may move in response to texture, focus, metric value,
null score, candidate result, M76 association, or a decoded pixel.

## 2. Bounds contract

**ARGUED — coordinate contract.** For quad shape `(height,width)` and ROI `(x,y,w,h)` with pad
`p`, registration requires:

```text
x - p >= 0
y - p >= 0
x + w + p <= width
y + h + p <= height
```

**ARGUED — real-geometry source.** Registration will read every held-out ARW's
`RawPy.sizes.height` and `.width` from its header, without unpacking pixels. It will require an
even raw shape, one uniform visible shape per stack, and a quad shape equal to the registered
shape.

**ARGUED — failure diagnostic.** Every violation must raise before the substrate can print
`VALID`. The exception must identify the stack, ROI index, ROI tuple, padded quad bounds, required
raw extent, and measured visible raw shape.

**ARGUED — registration site.** `src/validate_heldout.py` is the registration procedure. It must
call the bounds validator for all four ROIs on all six stacks before writing a green substrate
record.

## 3. Negative control

**ARGUED — plant.** The negative control will temporarily replace the final repaired ROI with the
known-invalid legacy tuple `(916,2402,512,512)`.

**ARGUED — construction discipline.** Python byte-string construction will create the plant.
Before running registration, M78b will read the modified file back and prove that the exact
planted bytes occur once. No double-quoted PowerShell string will carry the planted content.

**ARGUED — failure criterion.** The planted registration run must return a non-zero exit and name
the final ROI, padded quad `y1=2946`, required raw row extent 5892, and visible raw height 4688.
Zero exit, a different failure, or a missing exact diagnostic fails the repair.

**ARGUED — restoration criterion.** After restoring the original bytes without `git checkout`,
the exact same registration command must return zero and report all 24 stack/ROI combinations in
bounds.

## 4. Acceptance

**ARGUED.** The fixture repair passes only if all of the following hold:

1. **MEASURED criterion.** All six held-out stack geometries are read from headers and agree at
   raw `(4688,7028)`, quad `(2344,3514)`.
2. **MEASURED criterion.** The repaired registry equals the four precomputed tuples in §1.
3. **MEASURED criterion.** All four repaired ROIs, including 32 px padding, pass on all six
   stacks: 24 of 24.
4. **MEASURED criterion.** The planted invalid ROI fails registration non-zero with the exact
   bounds diagnostic in §3.
5. **MEASURED criterion.** Removing the plant restores a zero-exit registration.
6. **MEASURED criterion.** Existing non-pixel unit/property tests that import `spec_v1` remain
   green.

**ARGUED — ship boundary.** Passing repairs only the executable fixture and its registration
guard. M78b will not decode a held-out pixel, re-run M76 Q1, score a candidate, or change any
acceptance threshold.

## 5. Exposure audit

**ARGUED — direct consumers.** M78b will search code and history for imports or calls of
`roi_rule`, exact registry tuples, and M76 output consumers.

**ARGUED — classification.** Each hit will be classified as metadata/printing only, synthetic or
development-only, or a held-out pixel measurement. Merely sharing one integer tuple does not prove
registry consumption; commit order and source comments must support that attribution.

**ARGUED — result handling.** Any held-out result that consumed a silently valid legacy ROI will
be called exposed to the wrong spatial fixture. No old result will be recomputed or promoted.

## 6. Unclaimed follow-up

**ARGUED.** Repair makes a 24-cell Q1 re-run possible but does not assign it to M78b. A future,
independent milestone must pre-register its primary arm and explain why, because M76's three arms
did not agree in sign or significance.
