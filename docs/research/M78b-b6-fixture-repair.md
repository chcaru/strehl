# M78b — repair the B6 held-out ROI fixture

## Headline

**MEASURED.** M78b pre-registered the repair at
`259763615fe9079424cb00c9bd1b35e5b8e0a1ff` before changing the registry and
before decoding any held-out pixel.

**MEASURED.** All 1,252 ARWs in the six held-out stacks report the same visible
raw header geometry, `(height,width)=(4688,7028)`, hence green-quad geometry
`(height,width)=(2344,3514)`. The legacy fourth ROI is out of bounds on all six
stacks. The other three legacy ROIs are silently valid both in their registered
interpretation and with row and column exchanged.

**DERIVED — hypothesis verdict: CONFIRMED.** M55 registered
`QUAD_W=2344, QUAD_H=3514`: its width is the real height and its height is the
real width. `roi_rule` then used those constants to derive `x` and `y`.
The failure was a width/height transposition at fixture generation, not one
arbitrary bad coordinate.

**MEASURED.** Regenerating the four coordinates from M55's frozen fractional
rule against the real geometry gives:

```text
[(750, 458, 512, 512),
 (2252, 458, 512, 512),
 (1501, 916, 512, 512),
 (1501, 1466, 512, 512)]
```

**MEASURED.** The repaired registration procedure checks real RawPy header
geometry for every file, then checks every ROI with its 32 px padding. It
passes 24 of 24 stack/ROI combinations.

**MEASURED CONTROL.** A Python byte-string plant changed the final ROI back to
`(916,2402,512,512)`. Read-back found exactly one marker and exactly one
intended byte fragment. Registration exited 1 and named `roi_index=3`,
`y1=2946`, required raw extent `(5892,2920)`, and visible shape
`(4688,7028)` on every stack. Restoring the saved bytes reproduced the original
SHA-256 and the same command passed 24 of 24.

**MEASURED — ship decision.** The corrected fixture, real-geometry registration
guard, property test, audits, and falsifying control ship. No M76 association
was re-run, no held-out pixel was decoded by M78b, and no scientific result
ships.

---

## 1. Source boundary and ordering

**MEASURED — source read.** M55's fixture is
`experiments/M55-acceptance-spec/src/spec_v1.py::roi_rule`. M55's report §4
calls `ROI_FRACTIONS` the rule, prints the four integer tuples derived from it,
and says `validate_heldout.py` read EXIF and frame counts only.

**MEASURED — source read.** M76's
`e17_m76_stratum_variance.py::load_cubes` consumes a tuple as
`(x,y,w,h)`: raw rows are sliced from `2*y` and raw columns from `2*x`.
M76's own §4.1 records the initial broadcast failure, the six blocked fourth
cells, and continuation with 18 readable cells.

**MEASURED — ordering.** The pre-repair audit read only
`RawPy.sizes.height` and `.width`. Neither audit nor registration calls
`unpack`, `raw_image`, `raw_image_visible`, or `postprocess`. The audit and
pre-registration were committed together at `2597636`; only then was
`spec_v1.py` changed.

**ARGUED — alternatives considered.** Changing only ROI 3 would leave three
silently misplaced ROIs. Swapping every emitted `(x,y)` would also swap the
unequal `(0.75,0.25)` fractions. Regenerating all four tuples from the original
fractional rule and the measured geometry is the only repair that preserves
M55's registered intent without selecting on image content.

---

## 2. Pre-repair audit: all four ROIs on all six stacks

**MEASURED — stack geometry.** `out/m78b_roi_audit-before.log/.json` opens every
ARW header, verifies one uniform shape per stack, and performs no pixel decode:

| stack | ARWs checked | visible raw `(h,w)` | quad `(h,w)` |
| --- | ---: | ---: | ---: |
| `coffee-bean` | 105 | `(4688,7028)` | `(2344,3514)` |
| `wrapped-text-1` | 130 | `(4688,7028)` | `(2344,3514)` |
| `wrapped-text-2` | 120 | `(4688,7028)` | `(2344,3514)` |
| `bee-1` | 299 | `(4688,7028)` | `(2344,3514)` |
| `bee-2` | 299 | `(4688,7028)` | `(2344,3514)` |
| `bee-3` | 299 | `(4688,7028)` | `(2344,3514)` |

**DERIVED — arithmetic.** For `(x,y,w,h)` and padding `p=32`, padded quad
bounds are `[x-p,x+w+p) × [y-p,y+h+p)`. The raw extent required by M76's green
sampling is `(rows,cols)=(2*(y+h+p),2*(x+w+p))`.

**MEASURED — native bounds.** Because every stack has the same measured
geometry, each explicit calculation below applies independently to all six;
the final column reports those six checks:

| ROI | legacy `(x,y,w,h)` | padded quad x | padded quad y | required raw `(rows,cols)` | valid stacks |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | `(458,750,512,512)` | `426..1002` | `718..1294` | `(2588,2004)` | 6/6 |
| 1 | `(1374,750,512,512)` | `1342..1918` | `718..1294` | `(2588,3836)` | 6/6 |
| 2 | `(916,1501,512,512)` | `884..1460` | `1469..2045` | `(4090,2920)` | 6/6 |
| 3 | `(916,2402,512,512)` | `884..1460` | `2370..2946` | `(5892,2920)` | **0/6** |

**MEASURED — all 24 cells.** The audit log prints the four calculations
separately under each of the six stack names. ROIs 0–2 account for 18 valid
stack/ROI cells. ROI 3 requires raw row 5892 while each image has only 4688
visible rows, accounting for six invalid cells.

**MEASURED — relation to M76.** These are the same six failures recorded in
M76's own §4.1 and `out/e17_m76_stratum_variance.log`; M78b found them before
repair without attempting a pixel array.

---

## 3. Transposed reading and silent validity

**MEASURED — swapped-coordinate audit.** M78b exchanged only `x` and `y` while
retaining side and padding, then repeated the same bounds arithmetic:

| ROI | transposed tuple | padded quad x | padded quad y | required raw `(rows,cols)` | transposed valid | valid both ways |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | `(750,458,512,512)` | `718..1294` | `426..1002` | `(2004,2588)` | 6/6 | **6/6** |
| 1 | `(750,1374,512,512)` | `718..1294` | `1342..1918` | `(3836,2588)` | 6/6 | **6/6** |
| 2 | `(1501,916,512,512)` | `1469..2045` | `884..1460` | `(2920,4090)` | 6/6 | **6/6** |
| 3 | `(2402,916,512,512)` | `2370..2946` | `884..1460` | `(2920,5892)` | 6/6 | 0/6 |

**MEASURED.** The dangerous case exists: ROIs 0, 1, and 2 are valid under both
coordinate readings on every stack. An array-bounds failure cannot reveal that
those 18 cells occupy the wrong declared fractional locations.

**MEASURED — source discriminator.** In M55's original
`spec_v1.py::roi_rule`, `x` was computed from `QUAD_W=2344` and `y` from
`QUAD_H=3514`. The measured quad has height 2344 and width 3514. Both constants
are therefore the opposite dimension, exactly as a transposition predicts.

**DERIVED — verdict.** The row/column-transposition hypothesis is
**CONFIRMED**. The one value 2402 would have been weak evidence alone; the
paired source constants, tuple semantics in M76's loader, all-six geometry,
three silently dual-valid ROIs, and the fourth transposed-valid ROI jointly
identify the mechanism.

---

## 4. Registry consumers and exposed results

**MEASURED — search method.** M78b searched current Python sources for
`roi_rule`, the four legacy tuples, and the M76 output names; then searched Git
history with `-S 'S.roi_rule()'` and inspected the introducing commits.
`a353c3b` introduced M55's registry, calibration printer, and metadata
validator. `4fdea18` introduced M76's only pixel consumer.

**MEASURED — consumer inventory.**

| milestone / source | use of the registry | held-out pixels | exposure |
| --- | --- | ---: | --- |
| M55, `calibrate.py::main` | prints `S.roi_rule()`; its docstring and code exclude held-out stacks | no | no calibration number is exposed by this registry |
| M55, legacy `validate_heldout.py::main` | prints the tuples after EXIF/count checks and reports substrate `VALID` | no | the validation conclusion is false and is replaced here |
| M55, `spec_v1.py::describe` | serialises the rule as specification text | no | the printed fixture was wrong; no candidate acceptance result exists |
| M76, `e17_m76_stratum_variance.py::main` and `load_cubes` | calls `S.roi_rule()`, decodes ROIs 0–2, blocks ROI 3 | **yes** | all 18 real-data cells are spatially exposed |
| M78b audit, registration, test, and control | reads current or explicitly named legacy fixture to repair it | no | maintenance evidence only |

**DERIVED — M55 exposure.** M55's `substrate VALID` statement is retracted by
the real-geometry check. Its synthetic batteries, development-stack
calibrations, thresholds, and roll-up tests do not consume held-out ROI pixels.
B6 had not produced a candidate verdict, so there is no M55 acceptance result
to retract.

**DERIVED — M76 exposure.** M76's 18 finite Q1 cells came from legacy ROIs 0–2,
the three coordinates that are silently valid both ways. They therefore
measure valid arrays but not the fractional sensor locations declared by
M55. M76's Q1 numbers cannot be treated as measurements of the repaired
24-cell fixture. M76 already registered the result **INCONCLUSIVE** because 18
finite primary cells missed its required 20; that verdict is neither promoted
nor re-run here. M76's synthetic control and its Q2/Q3 property/enumeration
results do not decode this registry and are not exposed.

**MEASURED — same literal, not the registry.** M55's earlier sigpow attack
commit `c7ce4f0` and M57's commits `73ed0f0`/`bf8700f` predate the acceptance
registry commit `a353c3b`. Their development-stack scripts independently call
`(916,1501,512,512)` the “geometric centre”; M55 acceptance's `e12_null.py`
also carries that literal without importing `roi_rule`.

**ARGUED — separate risk.** Those earlier uses cannot be downstream consumers
of a registry that did not yet exist, so they do not expose results *through
this fixture*. The literal is nevertheless the same transposed-centre
convention: the corrected centred top-left is `(1501,916)`. That older,
development-stack lineage deserves a separate audit before any claim depends
on the ROI being geometrically central; M78b does not reinterpret its
measurements.

---

## 5. Frozen repair rule and repaired arithmetic

**ARGUED — rule frozen before repair.** `M78B-PREREGISTRATION.md` binds the
replacement to M55's existing fractions, real header geometry, existing
512 side, 32 padding, `round`, and clamp. It expressly forbids movement in
response to texture, focus, metric values, null scores, candidate results, or
M76's association.

**MEASURED — code repair.** `spec_v1.py` now names
`QUAD_HEIGHT=2344, QUAD_WIDTH=3514`; `roi_rule` uses width for `x` and height
for `y`. All four tuples are regenerated, rather than preserving the three
silent failures.

**MEASURED — repaired bounds.**

| ROI | repaired `(x,y,w,h)` | padded quad x | padded quad y | required raw `(rows,cols)` | valid stacks |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | `(750,458,512,512)` | `718..1294` | `426..1002` | `(2004,2588)` | 6/6 |
| 1 | `(2252,458,512,512)` | `2220..2796` | `426..1002` | `(2004,5592)` | 6/6 |
| 2 | `(1501,916,512,512)` | `1469..2045` | `884..1460` | `(2920,4090)` | 6/6 |
| 3 | `(1501,1466,512,512)` | `1469..2045` | `1434..2010` | `(4020,4090)` | 6/6 |

**MEASURED.** `out/m78b_roi_audit-after.log/.json` records every one of the 24
checks. `validate_heldout.py` independently reports `ROI bounds checks: 24/24`
and `substrate VALID` in `out/m78b_validate-after.log`.

---

## 6. Registration-time guard and falsifying control

**MEASURED — guard.** `spec_v1.py::validate_roi_registry` requires even raw
dimensions, checks measured quad geometry against the registered geometry, and
checks all four padded bounds. Its exception names the stack, ROI index and
tuple, padded quad bounds, required raw extent, and measured visible shape.

**MEASURED — registration site.** `validate_heldout.py::raw_visible_shape`
reads `RawPy.sizes` for every ARW. `main` rejects missing stacks, insufficient
frames, non-uniform geometry, geometry mismatches, or any invalid ROI before it
can report `VALID`. The historical EXIF/count output remains untouched;
the repaired record is `out/m78b_heldout_geometry.json`.

**MEASURED — property tests.** `e20_m78b_roi_bounds_test.py` passes 6/6:
the fractional rule yields the four pre-registered tuples, the real geometry
passes, the legacy fourth ROI fails with the exact extent, transposed geometry
fails, an incomplete registry fails, and odd geometry fails. Existing B6
property tests `e14`, `e16`, and `e18` pass 7/7, 13/13, and 7/7 respectively.
The combined record is `out/m78b_property_tests.log`.

**MEASURED — execution disclosure.** One verification launch mistakenly ran
the property suite concurrently with the deliberate source plant. `e20`
encountered `(916,2402,512,512)` and failed at the new guard, as it should.
After the control restored and hash-checked `spec_v1.py`, the suite was rerun
serially; the committed property-test log is that green run. No red result was
reclassified as green.

**MEASURED — plant bytes.** `m78b_negative_control.py::build_plant` constructs
the edit as Python bytes. Before execution:

```text
original sha256=e032dda4bbcb842cd473102e1b0d5eac338d2121341a5996ba8cd63e6a23c563
planted  sha256=96dea04a835b89ff0fcf31f2cbee5a8840610cd3a7910f8485b356a696b3ebbc
marker_count=1  exact_fragment_count=1  exact_match=True
```

**MEASURED — red control.** The planted command exited 1. It emitted this
diagnostic for each of the six stacks:

```text
B6 ROI bounds violation: stack=... roi_index=3
roi=(916, 2402, 512, 512) pad=32
padded_quad_bounds=(x0=884, y0=2370, x1=1460, y1=2946)
required_raw_extent=(5892, 2920) visible_raw_shape=(4688, 7028)
```

**MEASURED — restoration and green control.** The script restored from its
saved byte copy without `git checkout`, removed the backup, and re-read the
original SHA-256 exactly. The restored command exited 0 with 24/24 checks and
`substrate VALID`. The full red and green transcript is
`out/m78b_negative_control.log`; the red machine record is
`out/m78b_negative_control_invalid.json`.

**DERIVED.** The planted failure proves the new path exercises the coordinate
guard rather than merely printing geometry. Restoration proves the green
result depends on the repaired registry rather than a disabled check.

---

## 7. What was deliberately not measured

**MEASURED.** M78b did not invoke
`e17_m76_stratum_variance.py`, access `raw_image_visible`, merge a held-out
frame, calculate a candidate metric, or recompute an association.

**MEASURED — M76's own §4.2, not SYNTHESIS.** The prior arms disagree:
`sigpow-canonical` reports `rho=-0.8596, p=0.002400`;
`ring-power-of-mean` reports `rho=-0.1228, p=0.302267`; and
`band-ratio-PROBE` reports `rho=+0.0941, p=0.827182`. The third arm is opposite
in sign.

**ARGUED — unclaimed follow-up.** The fixture now makes a 24-cell re-run
possible, but it remains unclaimed. A milestone independent of both M76 and
M78b must pre-register which arm is primary and why. An instrument repair is
not evidence for the measurement the instrument may later make.

---

## 8. Files and reproducibility

**MEASURED — changed executable files.**

- `experiments/M55-acceptance-spec/src/spec_v1.py`
  — corrected dimensions and `validate_roi_registry`.
- `experiments/M55-acceptance-spec/src/validate_heldout.py`
  — all-file header geometry and mandatory bounds registration.
- `experiments/M55-acceptance-spec/src/e20_m78b_roi_bounds_test.py`
  — pure property tests.
- `experiments/M55-acceptance-spec/src/m78b_negative_control.py`
  — byte-confirmed red/restore/green control.
- `experiments/M55-acceptance-spec/src/m78b_roi_audit.py`
  — before/after header-only audit.

**MEASURED — evidence files.**

- `experiments/M55-acceptance-spec/M78B-PREREGISTRATION.md`
- `experiments/M55-acceptance-spec/out/m78b_roi_audit-before.log/.json`
- `experiments/M55-acceptance-spec/out/m78b_roi_audit-after.log/.json`
- `experiments/M55-acceptance-spec/out/m78b_validate-after.log`
- `experiments/M55-acceptance-spec/out/m78b_heldout_geometry.json`
- `experiments/M55-acceptance-spec/out/m78b_negative_control.log`
- `experiments/M55-acceptance-spec/out/m78b_negative_control_invalid.json`
- `experiments/M55-acceptance-spec/out/m78b_property_tests.log`

---

## 9. Facts proposed for SYNTHESIS

1. **MEASURED.** Every ARW across M55's six held-out stacks has visible raw
   header geometry `(4688,7028)`, quad `(2344,3514)`. Legacy ROIs 0–2 are valid
   both natively and with `x/y` exchanged on all six; ROI 3 is invalid natively
   on all six and valid when exchanged. Check:
   `out/m78b_roi_audit-before.log/.json`.

2. **DERIVED — CONFIRMED.** M55's B6 fixture was generated with width and
   height transposed: original `roi_rule` used `QUAD_W=2344` for `x` and
   `QUAD_H=3514` for `y`, exactly opposite the measured quad geometry. The
   three silently dual-valid ROIs explain why first decode found only the
   fourth defect. Check: original `spec_v1.py::roi_rule` at `a353c3b`,
   `m78b_roi_audit-before`.

3. **MEASURED.** A content-independent repair, pre-registered at `2597636`,
   regenerates all four ROIs as `(750,458)`, `(2252,458)`, `(1501,916)`,
   `(1501,1466)` with side 512. All 24 padded stack/ROI checks pass. Check:
   `spec_v1.py::roi_rule`, `out/m78b_roi_audit-after.log/.json`,
   `out/m78b_validate-after.log`.

4. **MEASURED.** Registration now reads every real raw header and validates
   every padded ROI. An exact Python-byte plant of the legacy bad ROI exits 1
   with `y1=2946` and required extent `(5892,2920)` on all six stacks; restoring
   byte-identical source exits 0 at 24/24. Check:
   `spec_v1.py::validate_roi_registry`,
   `validate_heldout.py::raw_visible_shape`,
   `out/m78b_negative_control.log`.

5. **DERIVED.** M76 Q1 is the only prior pixel measurement found that directly
   consumed the B6 registry. Its 18 finite cells used the three silently valid
   but spatially misplaced ROIs, so they do not measure the repaired fixture.
   Its registered **INCONCLUSIVE** verdict stands; a 24-cell re-run is available
   but unclaimed. Check:
   `e17_m76_stratum_variance.py::load_cubes/main`, M76 §§4.1–4.2, Git commit
   `4fdea18`.

6. **ARGUED — discipline candidate.** A registered pixel-coordinate fixture
   must be checked against real image geometry at registration, including
   padding and every registered file. EXIF and frame counts cannot validate
   spatial coordinates, and successful array allocation is insufficient where
   a transposed coordinate is silently in bounds.
