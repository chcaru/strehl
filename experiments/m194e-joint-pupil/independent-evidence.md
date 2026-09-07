# M194e independent evidence â€” initial numerical result

Status on the original author source: **UNCOMMISSIONED_NUMERICS**. The
independent reference instrument and all five complete reference frames pass
their own registered controls/refinement. The original author implementation
refuses 56 of 340 fixed diagnostic point/cell cases at its angular depth/error
limit. A returned value was never substituted for a refused case; no float/model
or CFA authority has been issued. A prospective author numerical-method
amendment is being reviewed separately. This file describes the retained first
outcome, not a prediction of that amendment.

## Authority and source separation

Root committed the reviewed preregistrations/release at `773f5762` before code.
The independent implementation was written and its analytic controls and full
reference runs completed before reading the author's numerical implementation.
It uses native clipped-cell polygon area/first moments/Fourier boundary
integrals and Cartesian pupil chords. The author uses polar radial integrals,
angular quadrature and triangulated numerical cell integration. The reference
imports no author evaluator or integration helper.

The implementation/API correspondence and source review followed reference
completion. All source versions tested are copied into their named run
directories; before/after hashes are recorded. The later refusal map executes
the copied original author sources, so ongoing author development cannot change
its subject. No historical source, production Rust, RAW, capture, holdout,
quality score or acceptance bar was changed for these runs.

## Commands and retained outcomes

Commands actually run from the repository root:

```text
python experiments/m194e-joint-pupil/independent-controls.py --output experiments/m194e-joint-pupil/independent-controls-1
```

For the full reference, the controls result's SHA-256 was obtained with
`Get-FileHash` and passed through the PowerShell variable `$controlHash`:

```text
python experiments/m194e-joint-pupil/independent-reference.py --output experiments/m194e-joint-pupil/independent-reference-1 --controls experiments/m194e-joint-pupil/independent-controls-1/result.json --controls-sha256 $controlHash
```

The run's `argv` retains the resolved digest, not a candidate-selected path
without a binding. Its result SHA-256 is
`8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc`.

```text
python experiments/m194e-joint-pupil/independent-author-check.py --output experiments/m194e-joint-pupil/independent-author-api-1 --model-sha256 a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8 --render-sha256 2320d2a24a8678da7d50795662bb34b54a41c5200abdc8d111d9457c86d599a5
python experiments/m194e-joint-pupil/independent-refusal-map.py --snapshot experiments/m194e-joint-pupil/independent-author-api-1 --snapshot-result-sha256 50db3812ca21ce518ea26fd68479d410247c07a385b67287598c2889edfb585e --output experiments/m194e-joint-pupil/independent-refusal-map-1
```

Python3.12.10, NumPy2.4.4 and SciPy1.17.1 were used. The independent scripts set
OMP, OpenBLAS, MKL and NumExpr thread limits to2 and use one Python worker.
Absolute errors are expected electrons in float64 reference calculations;
none of the figures below is a production-f32 or final-TIFF error bound.

| Run | Observed result | What it establishes |
| --- | --- | --- |
| `independent-controls-1` | 55 recorded checks pass, including 336 fixed re-chosen point/cell primary/refined evaluations; maximum re-chosen refinement difference `4.6413333620876074e-8` electrons | The independent reference agrees with its declared analytic limits and rejects the tested wrong operations. This is `PASS_REFERENCE_INSTRUMENT_ONLY`. |
| `independent-reference-1` | All five64Ã—48 scalar arrays completed in both primary/refined arms; maximum full-frame refinement difference `5.183519533602521e-7` electrons, below `.0005` | Complete independently refined numerical references exist for the intended scene. This is `PASS_COMPLETE_REFERENCE_ONLY`, not author commission. |
| `independent-author-api-1` | 25 checks pass, then the registered transformed affine **cell** raises `angular depth/error ceiling`; source unchanged | First author refusal is preserved. It returns no inaccurate pixel that could be scored; it fails the numerical completion requirement. |
| `independent-refusal-map-1` | All340 fixed cases attempted: 284 return within their tolerances,56 refuse,0 returned discrepancies,0 other instrument errors | The refusal is widespread among cell calls: all170 point cases pass;56/170 cell cases refuse. The aggregate remains `UNCOMMISSIONED_NUMERICS`. |

Reference primary/refined normal-integrand call counts are6,337,002 and
7,125,594, each within the30,000,000 ceiling. Their own process-CPU/wall counters
remain under the registered600/1200-second limits. These are budget records,
not performance comparisons. Full-reference explicit ndarray accounting
records122,880 bytes conservatively as five current-frame-sized arrays; that
field is an upper-bound accounting figure, **not an exact measured live peak
or RSS**. Source inspection shows frames are written/released individually and
comparison loads only the current primary/refined pair, not a five-frame
volume. No memory-performance claim follows.

## Actual controls and failure interpretation

The first instrument run starts with DC controls. It then checks clipped-cell
Fourier integration against direct rectangular quadrature, polygon area and
first moments, the two-ray25/20 versus separate22.5 counterexample, continuous
half-disc affine moments, noncentral disc-segment coverage, hidden-layer
invariance, focused limits, and aperture-zero cell17.52/18.48 versus separate18.
The transformed affine reference is also checked against a closed-form disc
moment and an independently nested Cartesian pixel-area calculation.

The actual author API reproduces the discrete ray values, affine/segment
point integrals, explicit full/absent foreground and hidden-layer changes,
layer-order/refusal controls, focused points, and both shared-cell values
before its first refusal. Its transformed affine point is
11393.177721579741 electrons, agreeing with the independent reference at the
reported precision. The next call, the same registered affine scene integrated
over its transformed native unit cell, refuses inside
`integrate_triangle -> render_points` before returning a cell value.

The separately authorized diagnostic retains the fail-fast attempt unchanged
and continues all four R5 point/cell cases plus all336 re-chosen textured cases,
with the same primary settings and resource bounds. It finds55 textured-cell
refusals and one R5-cell refusal. All56 report the same angular depth/error
ceiling. No RMS over the successful subset is presented as the registered
whole-population RMS. The map's SHA-256 is
`dba7db6989cb54abdc7e268e4644149d5e095550c74f47a9a52858c6e453d8de`.

This distribution localizes where the numerical contract fails, not why it
fails. Tiny angular transition regions were suggested for author inspection;
that is a hypothesis until a bound, source analysis or diagnostic establishes
the mechanism. The next numerical method must keep the declared model, scene,
precision, depth/work/time ceilings and complete case population. The original
Cartesian references need not be recomputed if their source/scene stays fixed.

All required author analytic controls, the complete five-frame primary and
separate angle/cell-refinement comparisons, and observer/output invariance
remain prerequisites to an external float/model commission. Actual CFA and
manifest checks are a later, separate stage owned by the other independent
reviewer. No passed reference calculation repairs M25's physical gates or
establishes camera-calibrated occlusion truth.

## Amended API result, still awaiting full-frame commission

Root committed numerical amendment1 at
`d77bc3feccefb3a02d8d2c8e3911d681ead4f8f1` before its implementation. The
amended author numerical source is
`84790fb4b963ae863f21248108402fe077a21584868eeca53a06a16c8f0a75ff`;
the model source stays unchanged. The exact same analytic and re-chosen API
cases were run with this command:

```text
python experiments/m194e-joint-pupil/independent-author-check.py --output experiments/m194e-joint-pupil/independent-author-api-2 --model-sha256 a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8 --render-sha256 84790fb4b963ae863f21248108402fe077a21584868eeca53a06a16c8f0a75ff
```

**PASS_AUTHOR_API_ONLY:** all31 analytic/control checks and all336 textured
point/cell comparisons complete. Maximum textured discrepancy is
`6.5509884734638035e-6` electron; RMS is `6.296348760267145e-7` electron.
The originally refused transformed affine cell returns11374.568793577935
against the independent11374.568793577937. The result hash is
`9bd267fa56af8823b9734b14740e49f74443a388ce3c9f6001c6267b281b0197`.
Source hashes remain unchanged through the run.

The checker made one transport correction before this attempt: it imports the
freshly copied source snapshot rather than the shared working directory, to
avoid stale shared Python bytecode or concurrent source changes affecting its
subject. The previous checker is retained with API run1. No mathematical case,
setting or tolerance changed. Post-reference source inspection confirmed signed
alpha in the ladder crossings, reuse of chief-ray h, complete interval coverage
and refusal at an unrepresentable failing midpoint.

The comparison arithmetic also has seven independent power checks at
`independent-comparison-controls-1`: an unchanged null; a sparse `.005`-electron
maximum-only failure; a dense `.0009`-electron RMS-only failure; an outside-edge
failure retained in the whole-frame domain; and shape/dtype/nonfinite refusals.
These commission existing error bars, not a new quality metric or image scene.
The command was
`python experiments/m194e-joint-pupil/independent-comparison-controls.py --output experiments/m194e-joint-pupil/independent-comparison-controls-1`.

The complete author primary and two refinement frame sets remain required.
The amended API result is therefore not yet a float/model commission, and
cannot authorize dependent CFA emission.

## Final numerical source and reader controls

The author then added the root-approved exact zero-width radial fast path.
Final render SHA is
`ef52c45d28ec2dda5aa897cfd57dacc4b4a3e300d3a581c35f305c76e2dd03f8`.
The unchanged complete independent API population was run again:

```text
python experiments/m194e-joint-pupil/independent-author-check.py --output experiments/m194e-joint-pupil/independent-author-api-3 --model-sha256 a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8 --render-sha256 ef52c45d28ec2dda5aa897cfd57dacc4b4a3e300d3a581c35f305c76e2dd03f8
```

All31 analytic/control checks and all336 textured point/cell comparisons pass
with exactly the API2 maximum/RMS values. Source hashes remain unchanged. The
result is still **PASS_AUTHOR_API_ONLY**; its SHA is
`4c7d513a986b952e1f99f77ef283b3a62a44b548985e22e4a06f4410d39a48bb`.

`independent-reader-preregister.md` fixes nine file-reader controls. Both the
unchanged NPY and an identical relocated copy pass. A false digest, trailing
payload, float32 header, wrong dimensions, NaN value and duplicate JSON keys
refuse. A correctly bound finite `.005`-electron mutation at pixel(32,24)
passes the file reader but fails the existing maximum-discrepancy bar, while
the RMS bar remains below threshold. The reader validates the bounded header
before allocating pixel data and requires the entire file payload to be used.

Both reader-control runs pass all nine checks. Run1 is retained; run2 follows
the purely administrative addition of required externally bound reader-control
arguments to the final comparison command. No reader logic, mutation or
numerical threshold changed between these runs. The final command was
`python experiments/m194e-joint-pupil/independent-reader-controls.py --output experiments/m194e-joint-pupil/independent-reader-controls-2`.
Result SHA is
`7b85bf37ea460a1d6a7240e27e5f2aa63d671d36081fea1d3390c72fc8dd77f1`.
This is **PASS_READER_CONTROLS_ONLY**, not float/model commissioning.

The author's3Ã—2 tile8/16 control crosses no tile boundary. It is admissible for
the optional event hook but has no power against changed tile traversal. A
prospective independent supplement fixes19Ã—11, a tilted edge, the independent
frequencies, and a foreground-DC+17e positive control. It executes actual native
off/count/placebo at tile8, count at tile16, plus separate coordinate-tracing
wrappers at both tile sizes. The command was
`python experiments/m194e-joint-pupil/independent-observer-check.py --output experiments/m194e-joint-pupil/independent-observer-1`.

All25 controls pass. The two actual209-cell traversals differ and each visits
every pixel once. All six null arms have identical scalar NPY SHA
`d06d2e0d445bfafead65381281282b7c65a65fdd123d248cd77bd82c4c851f41`
and indicator NPY SHA
`8ef72684e516e80d163a002166ea234077009e623e3ee68aa4a75c15d8b3d321`.
Count/placebo execute57578 optional hooks each, with382314/0 collected events;
off executes neither. The tracing observer itself leaves both arrays identical.
The fixed source change moves at least one pixel by17.00000000000182 electrons.
Final source hashes remain unchanged. This supports observer/traversal
invariance on the named fixture, not a performance or physical-optics claim.
Result SHA is
`b399094afc2956ab2f2d38aa4c8470ce62eb1cbd54c4ecc3e25648dfc18b4385`.

The final comparison now requires this supplemental result as an independently
bound input. After adding that dependency, the nine file-reader controls were
rerun unchanged in `independent-reader-controls-3`; all pass, with result SHA
`0b2bf5e7c386bec00769a4405680011c43d1a9086efac9a380ee701cf41845bf`.
Earlier reader runs and their exact source snapshots remain retained. This
administrative source change does not alter parsing, arrays or numeric bars.

A separately named missing-bundle preflight at `independent-reader-preflight-1`
passed all bound predecessor checks, then returned the expected
`UNCOMMISSIONED`/FileNotFoundError at the externally supplied absent bundle.
It compared zero frames and wrote no float commission. Its command is retained
in the result. This is a refusal-path check, not a failed numerical rendering.

## Second actual numerical refusal and prospective amendment2

The complete author attempt `float-run-1` ended
`UNCOMMISSIONED_NUMERICS` after primary frames0,1,2. Primary frame3 refused
at native cell(30,4), inverse-focus.875, after230 cells in tile8 traversal.
No complete fifteen-array bundle exists, and no independent float commission
was emitted. The prior API and observer checks did not guarantee that every
intended full-scene cell would meet the fixed indicator limits.

The frozen complete independent reference remains available at this cell:
15204.412150777305 electrons. The author leaf trace shows cell-rule difference
dominating its weighted pupil indicators at a tangency. Two local independent
diagnostic attempts are explicitly retained as invalid: first an incorrectly
specified affine null, then a tiny-triangle reference quadrature refusal after
correcting that null to K0. Neither independently certifies the leaf's true
error. See `independent-amendment-2-review.md` and both
`independent-cell-diagnosis-*` result/snapshot directories for exact bounds.

The prospective review re-derives a square-distance triangle coordinate map,
positive Jacobians and complete-area coverage. Its deterministic finite
proximity predicate selects quadrature coordinates without snapping vertices
or dropping area. It fixes independently chosen area/affine/cusp/Fourier,
permutation and predicate controls, then requires the same complete API and
all fifteen images against unchanged full-cell/full-image bars. This is a
numerical-method proposal, with no present CFA authority or physical-optics
claim. Implementation still requires root's preregistration release.

## Amendment2 implementation checks

Root committed the prospective amendment/review/release at `d839ce9b`.
The implemented render SHA is
`a59e9686823d6f4ab2749dd8ca0f1a0bbf6cd847ee32ed04eef44dc78a87aba5`;
the geometric model remains unchanged. These commands were run:

```text
python experiments/m194e-joint-pupil/independent-map-controls.py --render-sha256 a59e9686823d6f4ab2749dd8ca0f1a0bbf6cd847ee32ed04eef44dc78a87aba5 --output experiments/m194e-joint-pupil/independent-map-controls-1
python experiments/m194e-joint-pupil/independent-author-check.py --output experiments/m194e-joint-pupil/independent-author-api-4 --model-sha256 a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8 --render-sha256 a59e9686823d6f4ab2749dd8ca0f1a0bbf6cd847ee32ed04eef44dc78a87aba5
python experiments/m194e-joint-pupil/independent-observer-check.py --output experiments/m194e-joint-pupil/independent-observer-2
```

All399 independently chosen component/predicate controls pass. They cover the
exact re-chosen area/affine/cusp integrals, all six vertex permutations,
positive weights and interior nodes, near-predicate decisions, unchanged
coordinates, Fourier integrals, R0/full/absent and near-coalesced cases,
retained tiny positive area, nonfinite refusal and old-rule byte identity.
The incorrect-Jacobian and linear-rule destroyers are rejected.

The previously refused actual cell returns15204.412150780796 electrons,
differing from the independent reference by3.49e-9 electrons. The read-only
map-call observer preserves the scalar's exact bits and witnesses34 vertex,
6 edge and32 old-rule calls. On this same candidate source, disabling only
the new triangle maps restores the cell-depth/error refusal. The result is
**PASS_MAP_COMPONENTS_ONLY**, SHA
`6480a9c4c69311a9aa6b1a0c5ffe02e132c3a828b91e47b2a7a9675583e64b27`.
This attributes the formerly refused whole-cell behavior to the coordinate
substitution; it does not retroactively certify the old individual leaf's
true error.

The unchanged31 analytic and336 textured API checks all pass, with maximum
texture discrepancy2.0689185475930572e-7 electrons and RMS
1.2337532955849193e-8 electrons. Result SHA is
`bbc4de8fd60328fb7bfbbf4f99ea8e3fd3d178fb829c18d15afe712f1f769bc1`.
The independent evaluator and full-reference arrays were not changed.

The unchanged19Ã—11 observer/traversal population also passes all25 controls.
Only the explicitly bound author-render digest changed in its driver; the
prior source/outputs remain in observer1. Six null arms have scalar NPY SHA
`c2a6f609d525bde22e203e87a32ac7464afb7f2669e00248200df689f7eb5fe7`
and indicator NPY SHA
`6b5adc8d20a1603243d11f3da91ac20d41f6e777e5e8bf5eac9b63da6a55b124`.
Count/placebo each execute41714 optional hooks, collecting276714/0 events;
off remains0/0. The two actual traversals differ and cover all209 cells once,
while foreground+17e remains live. Result SHA is
`6eaa07e185da8c1914274dcaeacf35bccb9d57a14f769891fe3958cc3346355c`.
Every checked source is unchanged through its run.

These results commission the named implementation controls only. A fresh
complete fifteen-array campaign and independent comparison are still required;
no CFA authority follows from these passing subsets.

The final full-array reader now binds the before/after design records added to
the author driver, the amendment2 API/map/observer evidence, and every
predecessor source through comparison completion. Its source SHA is
`9c2005df8684de000464ea55c3d3d028d44505e654953e7eb76f9ea1116678c1`.
The unchanged nine reader controls pass in `independent-reader-controls-4`,
result SHA
`a85a84b1d535a6a9f4f398e6150917a4c2c932124b58c94c7a7ed3113599768d`.
This refresh follows administrative source/evidence-binding updates; the
complete-file parser and numerical bars remain unchanged.

## Global allocation amendment3: independent execution

The amendment2 full campaign remains failed: `float-run-2` stopped at primary
frame3 cell(31,7), after frames0â€“2 and255 cells of frame3. The selected vertex
map was present. The depth6 leaf's low/high difference3.44316831757e-6 exceeded
its local area share3.17449881569e-6, with negligible weighted pupil indicators.
This is not an independently certified tiny-leaf true-error measurement.
`independent-allocation-read.json` instead verifies complete partitions of the
retained508-node diagnostic tree against the frozen whole-cell reference.
The original34 terminal leaves, including that local refusal, have aggregate
8.856774755455326e-5, below the existing whole-cell bar. This motivated the
prospectively committed global allocation rule at `2a75e519`; neither failed
full campaign has been reclassified as passing.

Current-source execution binds model
`a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8`
and renderer
`a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460`.
No reference source or full-reference array was edited or regenerated.

The first independent allocation control run is retained as
`UNCOMMISSIONED_ALLOCATION_CONTROLS`: after43 passing assertions, my temporary
accepted-frontier observer remained installed across two calls on one Meter.
Its second invocation appended the second cell into both expected lists,
making expected leaves20 while the real counter correctly reported11. Run2
restores that wrapper after each helper call and passes56 controls on unchanged
stimuli and renderer. Root then identified that the separate pupil-limit check
inspected the real aggregate through my acceptance predicate but did not power
deletion of the allocator's own pupil acceptance clause. Run3 adds the same
registered faults as area densities through the actual queue: excessive
high-pupil density.0003, opposite signed deltas with absolute density.0012,
and D/pl/ph densities.0004/.0002/.0002 must exhaust depth and refuse. Each has
a valid companion. No threshold or scene changed.

Final `independent-allocation-controls-3/result.json` passes62 controls,
SHA `358905a23abbe77453b2eb6c8ff04f8d9153a8aaa798d72546f71250300754f6`.
They cover actual admission/refusal, capped-leaf retention, increasing child
indicators, canonical priority under reversed storage, incomplete/overlapping
paths, area faults, negative/nonfinite terms, resource/depth exhaustion and
wrong geometry at the actual callback boundary. The aggregate alone receives
areas rather than root coordinates; it is not claimed to detect a spatially
duplicated triangle. The actual evaluator boundary rejects the independently
injected duplicate half-triangle, including in-place coordinate mutation.
Synthetic root/leaf records commission software components, not optical truth.

The new actual cell(30,4) returns15204.412150782977e, versus frozen reference
15204.412150777305e, with cell indicator.00036663299340708325 and high-pupil
9.709902541659062e-8. Cell(31,7) returns15172.350816997267e, versus reference
15172.35081699726e; its18 accepted leaves have cell indicator
.0006571524094194218 and high-pupil1.4623755233115732e-6. The count observer
matches actual accepted frontier lengths/depths. These pass the unchanged
individual-cell limits; they do not substitute for the complete image campaign.

`independent-map-controls-2/result.json` passes400 controls, SHA
`3c4eae49bd5097d1f7ae2cca0d8e1981f2eb8985e87873bbad8a4b3b629b4d68`.
The archived a59e local allocator still refuses(31,7). As prospectively allowed,
disabling the tangent maps under the new global allocator now returns(30,4),
with whole-cell error7.131497113732621e-6. Thus the earlier local-rule ablation
does not establish that those maps are necessary on this globally allocated
cell. The separate fractional-moment/Jacobian/Fourier destroyers retain power.

`independent-author-api-5/result.json` passes all31 analytic and336 textured
cases, SHA `72304b090ab0eb39c56583146c59e4fbcfefd272ef7adb951283121e5f1e244f`.
Maximum textured discrepancy is1.858716132119298e-6e and RMS
1.0395546513467505e-7e, below the unchanged.004/.0008e bars.

`independent-observer-3/result.json` passes32 controls, SHA
`29e7312d20bd2a46033c1ce5fc982749a52f95ef6ad533f87f1960d902b507fd`.
All six19Ã—11 original/count/placebo/traced/order nulls have identical scalar
NPY SHA `b475c65674ef4aad20e76e6c727c70e105766a1563351ae1f7732381b69e7c21`
and indicator NPY SHA
`143230af726b0385d6f39e46da777910b1a5c95fa7447917f27d19a98199232d`.
Count records209 cells/559 leaves, terminal depths0â€“2, and48 locally
overallocated leaves across28 cells. Off/placebo retain six zero allocation
fields. Count/placebo each execute35273 hooks; off executes zero. Tile8/16
traversals differ while each visits all209 cells exactly once. Foreground+17e
changes actual pixels by up to17.00000000000182e. Local-overallocation counts
are numerical-allocation diagnostics, not image quality or admission bars.

The complete-array reader is now SHA
`36b781b954b2717752ebb03660e9ea3d0e8decd6e43cbe8119f4d2faf2a99a6e`.
It requires this exact allocation/API/map/observer evidence and rechecks every
source, alongside the original reference controls. The unchanged nine file
reader controls pass in `independent-reader-controls-5/result.json`, SHA
`fe1d8474cd3e4aef9f6d6b66e33ebec3127fec4f1c9cf7497746e0d4052b8b27`.
`independent-reader-preflight-2` passes all predecessor/source checks then
refuses an intentionally absent bundle with zero compared frames and no gate.
This is an expected transport/preflight refusal, not a numerical campaign.

The exact commands below were run from the repository root. `python` resolved
to `C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe`,
Python3.12.10 MSC1943 AMD64; NumPy2.4.4 and SciPy1.17.1. There were **no**
`-B`, `-X pycache_prefix`, or interpreter-prefix arguments in these invocations.
Each numerical subject driver copied author source into its new, initially
nonexistent output directory and imported that snapshot; no pre-existing
snapshot bytecode was present. The reader-control driver imported its current
source and bound its bytes. All drivers set OMP/OPENBLAS/MKL/NUMEXPR threads
to2 before numerical imports and ran sequentially in one Python worker.
Results' `command` fields record script arguments through `sys.argv`; this
paragraph supplies the interpreter boundary they omit.

```powershell
python experiments/m194e-joint-pupil/independent-allocation-controls.py --render-sha256 a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460 --output experiments/m194e-joint-pupil/independent-allocation-controls-1
python experiments/m194e-joint-pupil/independent-allocation-controls.py --render-sha256 a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460 --output experiments/m194e-joint-pupil/independent-allocation-controls-2
python experiments/m194e-joint-pupil/independent-map-controls.py --render-sha256 a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460 --output experiments/m194e-joint-pupil/independent-map-controls-2
python experiments/m194e-joint-pupil/independent-author-check.py --output experiments/m194e-joint-pupil/independent-author-api-5 --model-sha256 a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8 --render-sha256 a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460
python experiments/m194e-joint-pupil/independent-observer-check.py --output experiments/m194e-joint-pupil/independent-observer-3
python experiments/m194e-joint-pupil/independent-allocation-controls.py --render-sha256 a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460 --output experiments/m194e-joint-pupil/independent-allocation-controls-3
python experiments/m194e-joint-pupil/independent-reader-controls.py --output experiments/m194e-joint-pupil/independent-reader-controls-5
python experiments/m194e-joint-pupil/independent-compare.py --bundle experiments/m194e-joint-pupil/reader-intentionally-absent-bundle.json --bundle-sha256 0000000000000000000000000000000000000000000000000000000000000000 --author-run experiments/m194e-joint-pupil/reader-intentionally-absent-run.json --author-run-sha256 0000000000000000000000000000000000000000000000000000000000000000 --schema-sha256 578f403ed7167c6c0988d927691fa91e5deec7010407f90999e12a0328bbaf8b --reader-controls experiments/m194e-joint-pupil/independent-reader-controls-5/result.json --reader-controls-sha256 fe1d8474cd3e4aef9f6d6b66e33ebec3127fec4f1c9cf7497746e0d4052b8b27 --output experiments/m194e-joint-pupil/independent-reader-preflight-2
```

All final control source bindings are unchanged. These are component/API and
observer checks only. The required fresh fifteen-array campaign, full-array
comparison and genuine CFA authority remain outstanding. Low/high differences
are heuristic numerical indicators; independent complete-array comparison is
the decisive fixture-level precision check. No real-camera, diffraction,
product-quality, performance, default-promotion or SOTA claim follows.

The subsequent full3 refusal and its independent complete-frontier diagnosis
are retained in `independent-coupled-budget-audit.md`. The released amendment4
implementation's independent target/mass controls, complete population refresh,
exact fresh-cache commands and final reader bindings are recorded in
`independent-amendment-4-evidence.md`. Neither document grants a partial float
or CFA pass; the fifteen-array comparison remains separately required.

That subsequent complete comparison has now run on fresh `float-run-4` data.
All fifteen arrays and both complete refinement families pass their unchanged
bars. Exact inputs, output authority, original invocation and limits are in
`independent-full-comparison-report.md`; this is genuine float/model authority,
with CFA conversion and production integration still separate.
