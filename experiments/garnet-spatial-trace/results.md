# Native RAW numerator repair, September 25

MEASURED and independently reviewed: the default SoftPower merge could multiply
finite source coefficients by finite weights and overflow its f32 numerator.
Pyramid expansion spread those infinities; the final input-range clamp hid them
as finite rectangular patches. This is now fixed in the production core, keeping
the existing source weights, denominator, noise model, gather, and chunk order.

The implementation stores the weighted numerator in binary-scaled units and
restores DN after dividing by the denominator. It retains f32 arithmetic and
u16 source storage. HardMax and unweighted fallback remain in their original
units. Both live diagnostic coefficient readers use the same resolver.

## Cause and verification

The original complete183-source garnet has47 negative-infinite band2 coefficients,
expanding to4,343 invalid CFA-plane samples. Independent stencil propagation
matches the recorded masks exactly; those sites equal the final lower input
bound. A one-site shifted mask is rejected. Observer-on/off whole TIFF and
merged-plane hashes are identical. See `check-frozen-masks.py`, `garnet-on-1`,
`garnet-off-1`, and `observer-identity-1`.

The independent regression suite initially passes its flat/midtone test and
fails all three high-DN cases, including the injected ISO100 profile case.
After correction all four tests pass. Five additional controls cover1024
bounded sources, signed extremes, partial-merge absorption, tiny subnormal
products, normal finite arithmetic, HardMax and both base modes. All pass.
The finite f64 reference differs by at most0.001953125DN on the high-DN cases.
These controls validate accumulator arithmetic, not a new camera calibration.

The final fresh core binary passes569 tests with2 ignored. The first broad
run exposed two old M194d tests that expected valid bright input to overflow;
their inputs are retained and now checked against finite image references.
NaN/infinity, corrupted-state and actual reconstruction-overflow refusal tests
remain, including a correction to the manually encoded accumulator units.

The unconfigured feature-rich CLI suite reports177 passed,35 failed,39 ignored.
Independent review classifies all35 failures as missing explicit experiment
output/route configuration. That invocation remains failed; it is not an
all-green CLI claim. The actual configured complete-stack runs, fixed-source
oracle controls, and production CLI replay below pass. Details are in
`../pyramid-accumulator-range/cli-suite-fixed-2-independent-classification.md`.

## Complete images and practical scope

| Complete RAW stack | Sources | Corrected instrumented run | Interpretation |
| --- | ---: | ---: | --- |
| Garnet104 |183|114.266s|Artificial rectangular color borders disappear. Broad white reflection remains.|
| Marigold4 |488|281.609s|Only10 RGB pixels change. This does not solve its haze.|
| Ore100 |207|134.797s|Localized large corrections; broad glare is not established as repaired.|

These are overlapping operational run durations, not comparative speed
benchmarks. Each run hashes original sources, replays the historical full cache
to its exact old RGB16/ICC baseline, and requires exact per-source gathered
planes, guide, variance, energy, floor and selection weights plus canonical
chunk plan. All corrected finish census values are finite. Each source corpus
and retained alignment remains unchanged.

Garnet has only tiny rounding changes outside its old invalid footprint:
at most0.0000038146973DN. Automatic tone shifts its white anchor slightly,
so broad tiny RGB differences are not evidence of broad quality improvement.
The independent photographic report explicitly separates this dimming from
the repaired geometry. See `garnet-finite-and-tone-attribution.json` and
`../quality-september25/garnet-numeric-fix-photographic-review.md`.

The normal production executable reproduces the corrected garnet's complete
RGB16 pixels and ICC exactly, independently of the experimental stack adapter.
The deliverable is `outputs/quality-september25/garnet-104/stack-master.tiff`,
with a full-resolution JPEG alongside it. `production-equivalence.json` binds
the comparison. The current executable binding is `scripts/native-build.json`;
`scripts/render-native.py` uses it for future native renders. Old executables
and historical delivery scripts are preserved under their original hashes.

Both complete299-source production chip replays also finish, with identical
map and actual crop[133,89,3250,2166], yielding6500x4332 outputs. This differs
from the earlier manually inset experimental crop[141,97,3234,2150]. New
comparison views translate the old native targets by[16,16] and tile512px
regions into256px pieces. These are a fresh matched production pair, not a
claim of identity to the old inset master. Independent whole-image and native
inspection finds the duplicated colored rail edges and broad contact spill
remain. See `../quality-september25/chip-numeric-fix-photographic-review.md`.
The remaining broad ghosting must not be credited as repaired by small
arithmetic corrections. Independent delivery readback also verifies all three
production outputs, map/input order, unchanged source metadata, and garnet
RGB16/ICC equivalence; it does not reread all original RAW contents. The wrapper
itself hashed those contents at both endpoints.

## Other directions closed, next question

Full marigold/ore source-prior trials and the three fixed renderer factorials
did not establish a useful repair. They remain rejected. A new three-source
marigold test takes4.937s and preserves actual gathered source data, exact
development and a complete-image zero-mask placebo. Neither focused donor
retains both real hair groups; the deliberately blurred donor visibly destroys
them. This closes whole-source substitution on that fixed contact without a
donor/mask sweep. See `../marigold-source-pure/independent-photographic-review.md`.

The numerical fix is a concrete production correction, not SOTA qualification.
The remaining work concerns per-frame geometric placement and spatially varying
visibility/defocus while retaining both depths. Existing rejected free-visibility,
deconvolution and source-prior studies remain binding.

Two bounded questions follow: differential blur versus translation on already
saved chip patches, and whether excluding independently known mixed optical
support helps the actual pyramid on a generated opaque edge while preserving
both depths. Neither is a photographic improvement claim before execution and
independent review. The previous successful local chip-placement correction
already has a full299-frame trial; its negative star-sand transfer forbids
silently generalizing it.

The historical M194h raw-numerator export/verifier assumes the old internal
units. It was not used here; any future rerun needs a versioned scale in that
diagnostic protocol. Historical receipts are not reinterpreted as current data.

## Commands and exact bindings

Root used Python312 with `-I -B -X faulthandler`. The runnable phases are:

```
experiments/garnet-spatial-trace/run.py build --out <new-build>
experiments/garnet-spatial-trace/run.py regressions --build <build> --out <new-run>
experiments/garnet-spatial-trace/run.py bounds --build <build> --out <new-run>
experiments/garnet-spatial-trace/run.py census-on --build <old-build> --recipe <garnet-recipe> --out <new-run>
experiments/garnet-spatial-trace/run.py census-off --build <old-build> --recipe <garnet-recipe> --out <new-run>
experiments/garnet-spatial-trace/run.py candidate --build <fixed-build> --recipe <recipe> --historical <old-full-receipt> --out <new-run>
scripts/render-native.py --input <originals> --out <fresh-output> --warp-map <retained-map>
```

Each retained `process.json`/`invocation.json` records the actual absolute command,
environment, resource limits, terminal job status and log binding. `sources.json`
and `executables.json` bind the exact freshly compiled sources and artifacts;
no stale Cargo success is substituted. Build-fixed-2 is the final checked build.
Its production executable SHA256 is
`bec4c357836ad1383800a6c933460ee7ef072c525b5957a6f5deb5194b203314`.
