# Spatial independence and local identifiability

Status: active research; no qualified mosaic photograph or master.

## Frozen observations

The complete marigold2+3 preparation contains 433+339 sources, all independently
placed. The cached native replay produced225 accepted receipts. The actual
production support selector retains65 FIT and25 held-out spatial sites; its
export is `outputs/multi-stack/completion/mosaic-marigold-2-3-independent-sites-01.json`.
These are independent physical patches, not multiple original choices counted
as new locations. All errors below are native green-quad pixels; multiply by2
for sensor pixels.

**MEASURED:** the current regularized mesh has zero qualified join cells,
FIT RMS8.365quad and maximum held-out error13.847quad. FIT-only planar and
focus-ordinal projective initializers have held-out RMS11.615 and9.257quad;
neither predicts a held-out site within the fixed0.5quad bar. The focus ordinal
is a runtime acquisition coordinate, not calibrated depth.

An unsmoothed thin-plate interpolant was commissioned from the mathematical
minimum-bending formulation, with affine polynomial terms and the
`r² log(r)` radial function. Its equations are documented in the
[SciPy RBFInterpolator reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RBFInterpolator.html);
the original geometric treatment is
[Bookstein, Principal Warps,1989](https://user.engineering.uiowa.edu/~aip/papers/bookstein-89.pdf).
No external implementation source was consulted.

**VERIFIED mechanical controls:** an analytic curved plant has interior
held-out RMS0.0456quad/max0.1791; wrong identities, false FIT landmarks and a
depth discontinuity fail. Held-out target poisoning leaves training exact.
**MEASURED real diagnostic:** all65 FIT points interpolate to rounding error,
but all25 held-out sites fail, RMS9.568quad/max26.422. Exact training fit is not
quality evidence. Four saved native128quad patch pairs were generated; two
were viewed at native display sampling, including the worst prediction. They
show plausible matching petal structure, with blur differences. This does not
independently certify their subpixel placement.

## Defects found by independent review

1. A square clipping precheck scanned an outer ring not recorded by the native
   query observer. Its admission decision could consume another spatial role.
   The redundant precheck is removed from production. The actual coarse,
   fine and affine query observers continue checking every consumed original
   tap, including clipping, interpolation and filter support.
2. Global feature normalization, detection quotas and ratio-test competitors
   mixed FIT and held-out roles. The repaired extractor constructs role masks
   before normalization/filtering; each role has separate peak/source-pool
   quotas and nearest competitors. Original box footprints are mapped into the
   frozen pass gauge before masking, including the square's rotated extent.
   FIT features are concatenated first so their IDs do not depend on held-out
   pool size.

The independence statement is **conditional on the bound independently fitted
within-pass maps, focus fields, source nominations and calibration**. Those
upstream inputs are not claimed to be blind to all eventual validation pixels.
No complete end-to-end statistical independence claim is made.

**VERIFIED:** `mosaic-independence-controls-build-05` compiles the current local
geometry sources against frozen product16 libraries. The complete37 controls
pass in `mosaic-independence-controls-run-05`; executable SHA256
`27777c4d39cf3ee96593fcfc9d06f90f2fbf947262edd25d16c44f71106425ce`.
The builder recursively binds45 local path/include files and confirms every
source hash unchanged across compilation. Earlier build03 passed the same
controls but its explicit input list omitted transitive matcher/scale sources;
it is superseded for source provenance. Build04 failed before compilation on
Windows text decoding; the builder now explicitly reads Rust files as UTF-8.
The controls include high-contrast held-pixel poisoning through actual
`discover_pairs`, exact FIT feature/descriptor/seed comparisons, an exact
held-only descriptor duplicate that formerly defeated the FIT ratio, a
scale1.13/rotation0.11 original-box mask poison, and an unconsumed clipping-ring
poison across the role boundary. The existing iterated-clipping test still
rejects a saturated tap reached only after a later measured correction.

The matcher tests moved to `session-mosaic-match-tests.rs`; the producing
matcher remains below1000lines. The scoped tests rebuild after that move.

## Why the simple smaller split is not yet justified

The existing hold-out side128guide pixels is512quad. A mesh cell is roughly
502×469quad. Most withheld regions therefore require prediction across an
entire cell, not local interpolation among nearby independent measurements.
The current real held sites commonly lie250–500quad from their nearest FIT.

The fixed512-versus256quad layout plant in `spatial-role-controls.py` uses
13.591quad amplitude and1.548e-4/quad curvature estimated from frozen FIT
points only. The estimate uses local quadratic neighborhoods of median
radius709.486quad; it is an engineering scale measurement, not a calibrated
optical model. The plant uses an independent analytic sinusoidal field, not a
surface generated by the interpolating basis. Native-sized nonoverlapping
footprints and a50quad inter-view shift are included.

**MEASURED plant diagnostic:** the512 arm has250 FIT/102 held sites,
held-out RMS2.140quad; the256 arm has191/42, RMS0.805quad. However the256 arm
has zero cells with the required three held-out sites. The512 arm has no cell
with both local FIT and three held-out sites. These are negative feasibility
results, not permission to lower a residual/count bar.

This plant's48/54quad half-widths describe a conservative native-only query.
They do not cover the generated-grid coarse query, whose actual nominator
requires120quad before pose expansion. A256quad held block leaves only16quad
of coarse-query centre width; an inter-view shift can remove its usable
intersection entirely. No64guide-block real replay has been dispatched.

## Candidate next design

Retain the initial512-block FIT-only seed, then freeze compact validation
islands wholly inside the original held-out regions in both views. Stage2
training may use the remaining parts of those old held-out regions. Initial
training cannot have consumed an island; all stage2 normalization, feature,
search, derivative/filter and interpolation footprints must exclude it.

Island centres, source witnesses and sizes must be frozen before stage2 image
signals are read. Moving-view reservations come only from initial FIT geometry
and a predetermined uncertainty envelope. A footprint outside its reservation
is refused. Fixed validation sites use native-only measurements and FIT-only
initialization; broad held-out descriptors and120quad coarse search cannot be
silently reused. Three sites must also be spatially spread and noncollinear.

Required controls before any real arm: complete initial/stage2 consumed-support
union excludes islands; held-island poisoning leaves both FIT stages exact;
initial-seed error plus measured-curvature and depth-discontinuity plants;
refusal when the projected island overlaps initial FIT support; wrong original
identities at the same search size; actual placement, loops and positive
Jacobians. A planned island is not a measured witness or qualified cell.

The product default remains128guide pixels. Full rendering remains withheld.

## Implemented island producer checkpoint

The coordinate feasibility arm is now recorded in
`mosaic-validation-island-controls-01.json`. It freezes three noncollinear
centres per old held block, reference reservation radius43quad and moving
radius69quad, before evaluating stage2 signals. On the same analytic plant,
stage1-only474 FIT sites yield RMS1.193quad with3/32 held sites passing0.5quad.
Stage2 uses675 FIT sites outside the frozen islands, yielding RMS0.270quad,
30/32 passing sites, and7 cells with three passing noncollinear sites.
Wrong identities, a depth discontinuity, an incorrect projection and late
search leaving a reservation fail. **This remains coordinate feasibility**,
not source-image correspondence or real-data qualification.

`session-mosaic-roles.rs` now implements the serialized source-bound plan.
It records the frozen initial seed, upstream binding, FIT-evidence digest,
whole attempted ancestor rectangles, original witness IDs, accepted islands
and every refusal. An initial attempt may have crossed its old role boundary
before being refused; its entire recorded footprint remains in the dependency
union. It removes each intersected island while remote islands may survive.
All islands must still lie wholly inside old held regions, excluding initial
normalization and descriptor dependencies. An unknown attempted footprint
must not be silently represented as an empty footprint by the driver.

An optional plan is connected to both feature paths, mapped original boxes,
native similarity/affine/coarse support checks, fixed held-site/original
identity checks, upstream geometry binding and conservative work reservations.
Stage2 held descriptors and broad generated-grid held nominations are disabled;
validation uses only the frozen native sites. A late query cannot resize its
reservation or substitute another island's witness. The absent-plan path
retains the initial block partition.

**VERIFIED mechanical producing-path controls:**
`mosaic-island-producer-build-03` / `mosaic-island-producer-controls-03` pass
45/45 tests against frozen product16 libraries. The complete47-file local
include closure is unchanged across compilation. Executable SHA256 is
`2d7b9861ecac2e921b2ab8f20c3b8abd485461ddb356f6bea2e518a396599349`.
Tests poison held-island intensities and compare exact FIT features, descriptor
bits and seeds in both actual discovery stages; repeat the check through
nonzero-scale/rotation original-to-anchor masks; measure actual native FIT
inside reclaimed old held territory; and refuse saturated held originals,
wrong islands, projected ancestor overlap and insufficient resource budgets.
Native query traces remain identical under poison outside consumed support.

The actual cached driver must still derive and recheck the FIT-only artifact
digest, initial seed and complete accepted/refused ancestor union, then save
and reload the frozen plan **before** stage2 reads its signals. A checksum-like
caller string alone is insufficient evidence. No actual772-source island
campaign or qualified mosaic photograph is claimed at this checkpoint.

## Complete attempt auditing and pre-arithmetic isolation

The shared `native_attempted_support` auditor now reuses the production
accepted-support aggregator for refused attempts too. It unions every fine
iteration and affine footprint, swaps reverse directions, adds the native
filter halo, and lifts original quad coordinates through the inverse source
placement. An empty trace is treated as no query only when the same geometric
preflight used by the producing path proves that no query could start.
Otherwise the missing dependency is an error, not an empty rectangle.

Native work is grouped by original pair, spatial role and exact validation
island. Raw quads outside that role are excluded before green arithmetic,
coarse box reduction, filtering and NCC. The raw ownership mask does not
double-count the filter halo: complete expanded query support is checked
separately. A zeroed value is never evidence of valid black. Original clipping
checks short-circuit after a geometric role failure, including reverse and
affine paths, so a refused attempt cannot read the validation clipping values.

**VERIFIED:** `mosaic-island-producer-controls-08` passed47/47 against the
complete48-file source closure in `mosaic-island-producer-build-08`; executable
SHA256 `944d27393c31d9111cc9388f676e81b0fcb667576926f22316023f228aa8c4f4`.
The new controls reach an actually escaping native query and compare complete
FIT diagnostic traces under validation-only poison. They also cover nonzero
scale/rotation/translation with native lowpass, including exact invalid-border
NaN bits; accepted in-role masked/unmasked arithmetic and one/four-worker
masked samples are identical. The preceding controls07 fixture used ordinary
float equality on deliberate NaN borders and failed46/47; that fixture error
and its full receipt are retained. No tolerance or estimator gate changed.

The unregistered `island-replay.rs` driver derives the initial FIT-only seed,
source-feature witnesses, candidates and all native attempts from the actual
producer. It saves and reloads that artifact, recomputes the complete support
union, and binds its digest before constructing reservations. Fixed island
positions and original witnesses come from the bound upstream guide. It then
publishes and reloads the frozen role plan before the first stage-two source
call. This remains conditional on the frozen per-pass maps, focus and source
nominations. Actual cached execution is still required; source compilation
and passing synthetic controls do not establish real join coverage.

**MEASURED first cached staged arm:** `mosaic-marigold-2-3-islands-run-01`
completed143.38s with711MB sampled private memory and zero RAW decodes. It
reproduced63 independent FIT sites, audited367 FIT attempts, proved13 had no
query, and retained708 source footprints. It stopped before stage2 because
the research driver wrongly required the strict usable-focus flag at each
fixed centre: none of36 paired centres passed. The resulting empty plan,
source receipts and all initial measurements are preserved.

This was a nomination restriction, not a native-placement failure. Only4.3%
and9.2% of the respective guides have usable focus summaries. Covered original
source witnesses can still be nominated without asserting a reliable ordinal
or compatible focus band; actual original-image measurement must certify the
geometry. The corrected arm keeps all36 positions and deterministic source
rank choices, and records each focus flag, width and ordinal explicitly. It
retains every native, held-out, reciprocal, loop and visibility threshold.

`mosaic-marigold-2-3-islands-02` reuses stage1 only after identical
source/map/guide/config/algorithm binding and reconstruction of its typed
FIT-only seed, features, candidates, all native attempts and complete ancestry.
The FIT artifact SHA256 is
`e162034c95156c8493f4dad2b63e355dd42febebf6eade6081786cfb41fb24d7`.
Typed f32 fields are restored before reconstruction; widening their shortest
decimal representations directly to f64 would change the serialized evidence.
The shared research writer now explicitly flushes and syncs publication errors.
The corrected arm found34 covered nominations and2 unavailable sites; all34
reservations survived the complete attempted ancestor union. Frozen plan
`6063d3e993aa9d90c58577bcbcbfb72d6ce6137b2d10c9ef62cd9d70d20c272f`
was published before stage2 source reads. **MEASURED arm02 completed:**161.43s,
715MB sampled private memory, zero RAW decodes. It retained88 independent FIT
sites but0 held sites, with0 qualified cells. Of42 held original-source
attempts,31 lacked enough correlated tiles,9 escaped an actual role footprint,
and2 failed image-edge preflight. All receipts remain visible. The larger FIT
pool alone does not demonstrate improved placement.

The9 escaped attempts exposed an asymmetric reservation model: the moving
view included the declared24quad seed uncertainty, but the reference view did
not reserve its inverse projection for the reverse query. An actual planted
native control reproduces this failure with a6quad seed offset. The corrected
planner reserves query windows and fixed uncertainty in both directions using
only the initial FIT similarity's forward/inverse L1 extents, before stage2
reads. It does not choose margins from the observed held residuals.

**VERIFIED reciprocal reservation controls:** `mosaic-island-producer-controls-10`
passes48/48, including actual forward and reverse native queries at all four
corners of the declared plus/minus24quad uncertainty square with nonunit scale
and nonzero rotation. A native tap one quad outside either frozen reservation
is refused. The exact planted initializer isolates this support test from the
separate problem of recovering a large initial error. Executable SHA256 is
`c6e236174753e6ff94f975f0d967c57121654dd363bce358b2bcc7901b1e0e28`.
The low-correlation held failures remain a separate pending problem; neither
this control nor enlarged reservations certify a join or photograph.

**MEASURED arm03:**164.41s,720MB sampled private memory, zero RAW decodes.
Reciprocal reservation removed every footprint escape. Three original attempts
passed at one independent held site; the final selection was91 FIT/1 held,
with0 qualified cells and held placement error2.038quad. The predeclared
FIT-only minimum-bending diagnostic also failed that site (2.349quad). Its
exact training interpolation is not quality evidence. Both models remain
negative; no model parameter was selected from this lone held result.

Four exact128quad native patch pairs were inspected under identical display
percentiles (`mosaic-island-native-patches-03/receipt.json`). The passing site
contains fine petal texture. Two rejected sites with NCC peaks0.97–0.99 and
residuals3.4/4.4quad contain smooth defocused gradients. High correlation alone
does not establish local two-dimensional geometry. The new actual-native
flat, directional and repeating-pattern pair foils pass in controls12 (49/49).

The reciprocal bound was further generalized for unequal per-pass source
placements: A reserves the maximum of its own source window and B's window
projected through the inverse cross-pass transform, plus inverse-projected
declared uncertainty; B uses the reciprocal maximum plus its uncertainty.
Controls11 pass48/48 with source pulls1.1+i0.02 and0.9-i0.025, cross-pass
1.035+i0.037 and all four uncertainty corners. No margin uses held residuals.

## Measured hulls limit cross-view admission

Inspection found that the initial core policy counted three held sites without
checking their two-dimensional spread. All recorded real runs were negative,
so none had licensed a seam. The corrected policy requires witness hull area
at least1/32 of the actual physical cell and both coordinate spans at least1/3
of that cell. These predeclared shape guards are **not interpolation error
bounds**. The actual canonical witness hull is stored in source-pass quad
coordinates, included in the report and serialized with the mesh.

Cross-view admission now requires the complete CFA quad inside that measured
hull. Outside-hull mapping retains continuous SingleView ownership. A refit
clears previous hulls/qualification; a saved cell label without a hull cannot
fabricate support. Positive Jacobian, native residual, reciprocal, held-out,
coverage and final photographic checks remain separate obligations. The core
hull primitive does not itself require loop witnesses; the CLI native receipt
consumer supplies and validates the independent reciprocal evidence.

Direct current-core controls pass15/15, including skinny/clustered/duplicate
triples, actual border-cell normalization, a measured-curvature common gauge,
depth-jump refusal and inside/outside-hull behavior. Root's fresh integration
passes29 core and64 CLI mosaic controls in `product17-mosaic-controls-01`.
The source is frozen for product17; there is still no qualified real mosaic
photograph or master.

The next separately named arm follows [the frozen focus/coverage nomination
protocol](focus-island-protocol.md). It may choose nearby validation centres
from the already bound upstream masks, before stage2 native reads, while
retaining all nominal anchors, full rankings, geometric refusals and exact
source identities. Its independence is explicitly conditional on those frozen
upstream masks and the resulting plan. It cannot erase the fixed-centre
failure, and it does not retry centres after seeing native scores.

## Focus-nominated real arm, product17

**VERIFIED mechanics:** `mosaic-focus-island-controls-run-01` passes53/53,
including the actual selector's tied-distance order, nearest moving-mask
coordinate, ancestor-refused nearest candidate, prior-island exclusion,
selected-point cell crossing and36 unavailable-anchor census. The complete
local include closure and frozen17 libraries are bound in
`mosaic-focus-island-controls-build-01/build-receipt.json`.

**MEASURED negative:** `mosaic-marigold-2-3-focus-islands-run-01` ran the fresh
two-stage772-source experiment through `mosaic-focus-island-replay-build-01`
(executable SHA256
`476d460e92f049b1eb10bed9539bf4a6ca1cc78f9331aed2ba3caaadd2bbfde3`).
The command completed with zero RAW decodes in322.863s and a sampled peak of
717,152,256private bytes. Four workers,3GiB work plus512MiB cache were reserved;
other root render work shared the host, so this is not an isolated benchmark.

Fresh stage1 reproduces the earlier seed bits, FIT feature identities, every
FIT native receipt and all708 ancestor footprints exactly. The bound algorithm
identity changes for the new hull/support implementation. Before stage2 reads,
the selector freezes28 of36 anchors and retains8 unavailable anchors. The plan
SHA256 is
`bc1238b0e9b557d9b5bc8b8918f6e1b860aa0d3a04d5cc41ed233c087d4e8d7f`.
Independent review checked the full nominations, both queried usable flags,
maximum96quad movement and absence of post-native retries.

Stage2 retains96 independent FIT and11 independent held sites from706
candidates. The82 held original attempts produce29 accepted original pairs,
but repeated source alternatives remain11 spatial sites. The107 independently
measured reciprocal loops have maximum error0.320quad. The fitted mesh still
has8.113quad FIT RMS, maximum local displacement1.863quad and maximum held
placement error6.318quad. **Zero cells qualify; no photograph was rendered.**

The planned-site census itself limits coverage:28 sites occupy14 actual cells;
10 cells contain only1–2 planned sites, while only4 contain3. After actual native
qualification every occupied cell has at most2 held sites. This does not justify
lowering the three-site/hull support guards. A denser independent plan must be
declared separately and must preserve enough original FIT support.

The existing fixed FIT-only thin-plate diagnostic also fails the11 held sites:
RMS4.548quad, maximum10.209quad, zero within0.5quad. A separately fixed family
of eight spatial/ordinal least-squares models chooses its model using five
spatial-block folds of the96 FIT sites only. `mosaic-focus-models-run-01` includes
ordinal-positive, shuffled-ordinal and unobserved-depth-jump controls before
reading real measurements. FIT-only cross-validation selects affine plus
ordinal/spatial cross terms (7.626quad versus8.522quad for affine; the shuffled
ordinal family cannot improve on8.522quad). The selected model's held RMS is
3.536quad, maximum6.077quad, again zero within0.5quad. These are diagnostics,
not output geometry or physical depth estimates.

Four actual original patch pairs were inspected at128quad without resizing in
`mosaic-focus-fit-patches-01`; their fitted diagnostic B panels are not independent
placement evidence. The two largest nearby FIT residuals contain plausible
matching blurred/bokeh structures. A frozen-guide census finds only3/96 FIT
sites usable in both focus masks versus11/11 held sites; only11/96 FIT original
witnesses belong to both guide top-four lists. This motivates testing matched
focus-based FIT nominations rather than interpreting more model parameters as
success. All previous refusals and real negative results remain preserved.

## Focus-matched FIT diagnostic

The separately reviewed [focus-matched FIT protocol](focused-fit-protocol.md)
keeps the same known-scene held plan and compares exact mixed-control,
focused-only and augmented arms. The first execution refuses before image
reads because two semantically identical ordered source-census JSON files have
different whitespace. The failed receipt is retained. The corrected driver
compares every ordered typed source identity and saves both file hashes; its
new control rejects any changed path,size,mtime,SHA,order or count. The full
research control suite passes56/56 in `mosaic-focused-fit-controls-run-04`.

**MEASURED negative:** `mosaic-focused-fit-run-02` completes with executable
SHA256`7704f31bb53d7c05a9149eaad983ad9907a44b5b9efc7557d9a867a239517380`
in126.147s, sampled peak712,581,120private bytes, four workers and zero RAW
decodes. Before reads it freezes205 selected anchors from486 nominal anchors,
603 source pairs, with complete source/mask/geometric refusal receipts. Every
new point is a generated-grid nomination requiring actual coarse original NCC.
The candidate SHA256 is
`2d75d04496fb2c5b24f9f06dc26179c6ec68354ee492aed59b04bdce844804e8`.

| Arm | Independent FIT | Known held | FIT RMS quad | Maximum held error quad | Qualified cells |
| --- | --- | --- | --- | --- | --- |
| Mixed control | 96 | 11 | 8.1132 | 6.3175 | 0 |
| Focused only | 30 | 11 | 8.5078 | 5.9608 | 0 |
| Augmented | 98 | 11 | 8.0888 | 6.4040 | 0 |

The mixed-control complete report is exactly reproduced.289 new original pairs
pass native checks, but the production physical-support selection retains only
30 independent focused sites: coarse-search footprints are much wider than fine
descriptor/refinement footprints. Adding the new observations contributes only
two more independent sites overall. Focus nomination alone is not a demonstrated
fix. No photograph was rendered, and reused held measurements cannot supply
fresh final qualification.

The next [correlated FIT diagnostic](dense-fit-protocol.md) tests model
underfitting on saved measurements only. It may retain correlated training rows
with explicit component weight normalization, while preserving independent
site/count semantics and every held footprint guard. Model/smoothness selection
uses fully purged FIT-only spatial cross-validation, never external held errors.

## Commands and bound artifacts

All paths are under `outputs/multi-stack/completion/` unless noted. The source
and argv hashes in each JSON accompany the actual command, not a suggested run.

| Command / receipt | Purpose |
| --- | --- |
| `python .../initializer-controls.py --out mosaic-initializer-controls-01.json` | Projective model commissioning |
| `python .../evaluate-initializers.py mosaic-marigold-2-3-independent-sites-01.json --out mosaic-marigold-2-3-initializer-evaluation-01.json` | Fixed real projective diagnostic |
| `python .../local-interpolant-controls.py --out mosaic-local-interpolant-controls-01.json` | Local model positive/negative controls |
| `python .../evaluate-local-interpolant.py mosaic-marigold-2-3-independent-sites-01.json --out mosaic-marigold-2-3-local-interpolant-01.json` | All real held-out local-model errors |
| `mosaic-marigold-2-3-native-patches-01/receipt.json` | Exact source hashes, patch origins and shared display percentiles |
| `python .../spatial-role-controls.py mosaic-marigold-2-3-independent-sites-01.json --out mosaic-spatial-role-controls-01.json` | Fixed spatial-layout negative controls |
| `mosaic-independence-controls-build-05/build-receipt.json` | Complete45-file source/library/compiler command binding |
| `mosaic-independence-controls-run-05/receipt.json` | Actual37-test command, workers and resource observation |
| `mosaic-validation-island-controls-01.json` | Fixed-island coordinate feasibility, all errors and negative arms |
| `mosaic-island-producer-build-03/build-receipt.json` | Complete47-file connected producer source/library binding |
| `mosaic-island-producer-controls-03/receipt.json` | Actual45-test command and resource observation |
| `mosaic-island-producer-build-08/build-receipt.json` | Complete staged-driver source/library binding and source snapshot |
| `mosaic-island-producer-controls-08/receipt.json` | Actual47-test command, filtered native poison and bounded resources |

The abbreviated `...` above is
`experiments/multi-stack-2026-10-28/completion/mosaic`; JSON receipts retain the
complete actual argv. Controls used at most4workers, no RAW decode and no
photographic render. Timings are not isolated performance claims.
