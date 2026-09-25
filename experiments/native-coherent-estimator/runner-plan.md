# Root-only bounded runner and separate photographic gate

This is a new fixed whole-source consumer using the current actual rounded
gather, with legacy Tenengrad27/box17/Gate4 choices. It is not a new default or
a repeat of the rejected coarse-prior qualification. The legacy focus-response
noise constant is not calibrated for the current gathered guide; the runner
does not turn structural success into a calibration or quality claim.

The independent plan defines two prospective decisions on all twelve cases.
`general_qualification_admitted` retains every general guard, including the
known absent contact-outside positive. `optional_chip_observation_admitted`
separately requires both-ISO flat protection and averaging participation,
contact interior/edge gain with live source exclusion, preserved true coloured
rays, and completed structural/destroyer evidence. Glint and transparent
near/far results remain reported even if that limited gate passes. The driver
preserves both booleans and permits cost/full **only** when the optional gate is
true. There is no command-line override or post-result reclassification.

Root executes; the runner author does not build, run controls, decode RAW or
judge the resulting photograph. Implementation, controls and runner ownership
are separate. This file and `runner.py` are the only files owned by this author.

## Commands and source freeze

Use new output directories from the repository root:

```text
python experiments/native-coherent-estimator/runner.py build --out experiments/native-coherent-estimator/build-1
python experiments/native-coherent-estimator/runner.py controls --build experiments/native-coherent-estimator/build-1 --out experiments/native-coherent-estimator/controls-1
python experiments/native-coherent-estimator/runner.py cost --build experiments/native-coherent-estimator/build-1 --screen experiments/native-coherent-estimator/controls-1 --out experiments/native-coherent-estimator/cost-1
python experiments/native-coherent-estimator/runner.py full --build experiments/native-coherent-estimator/build-1 --screen experiments/native-coherent-estimator/controls-1 --cost experiments/native-coherent-estimator/cost-1 --out experiments/native-coherent-estimator/full-1
python experiments/native-coherent-estimator/runner.py finalise --build experiments/native-coherent-estimator/build-1 --screen experiments/native-coherent-estimator/controls-1 --run experiments/native-coherent-estimator/full-1 --out experiments/native-coherent-estimator/inspection-1
```

Build is release, two Cargo jobs, offline/locked, using existing native
pyramid/GPU/direct-plane/correction-variance features. Fresh CLI/core source
timestamps and `Compiling` lines for both are mandatory. The copied test and
release executable hashes, actual Rust/WGSL/manifests, imported bounded-job and
view helpers, all new implementation/control/design/plan files and existing
pre-build source review are bound. Future outcome reports and output folders
are excluded. Root waits for all authors' freeze hashes before building.

Controls use filter
`merge_cmd::native_coherent_estimator::independent_controls::`, output env
`STREHL_NATIVE_COHERENT_OUT`, and require exactly two successful tests plus the
NATIVE_COHERENT marker. `screen.json` must be SCREEN_COMPLETE with the twelve
fixed scene/ISO identities and two Boolean decisions. Unlike preservation of an
old operator, there is no equality requirement to the prior screen's results.
Image failures remain valid recorded results of a successful instrument run;
they are not replaced by the test executable's exit status. Actual MeanAll and
wrong-donor evidence is supplied by the independently authored controls through
the same consumer, not invented or rescored by this driver.

## Cost and full input contract

The ignored exact test is
`merge_cmd::native_coherent_estimator_chip::chip_complete_pair`, configured by
`STREHL_NATIVE_COHERENT_ESTIMATOR_CHIP_CONFIG`. Schema1 contains phase cost/full,
source_dir, warp_map, out_dir, expected_crop and tone. GPU device scheduling,
eight threads, full-resolution rounded direct planes, existing green probe,
parallel warp writeback and normal optical CA are explicit. CA-before-MHC,
fine-support and defect experiments are off. The fixed algorithm has no tunable
driver argument. Sanitized environment, command, helper and wrapper identities
are retained in receipts.

All299 uncapped-chip names/paths/size/mtime are checked against the existing
inventory before/after. Source149 additionally has a complete file hash;
adapter active-u16 hashes and original-index beta are compared to the retained
complete current receipt for every consumed source. Both actual-gather passes
must reproduce original storage, known4, guide, variance and regularized focus
evidence. This is one current source at a time, not an aligned-frame volume.

The fixed map SHA, reference149, crop[141,97,3234,2150] quads,
tone[.004293,.946441,.55], original WB/matrix/profile, and canonical baseline
75/75/75/74 chunks remain held. The full baseline must equal the retained
phase-packed current6468x4300 RGB16 array and pixel SHA256
`7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db`.
Its four collapsed plane hashes must also agree. TIFF container hashes are
recorded independently; a build tag is not treated as a pixel difference.

Cost consumes only source149 twice, keeping its actual original index/count299
gather/probe gauge while the coherent estimator has one source. The required
identity is the literal one-source mean: candidate four planes equal actual
source149 known4 bits. It is **not** required to equal the canonical one-frame
BandMerge output, whose collapse can introduce different f32 roundoff. There
is no false cost RGB equality requirement to that baseline.

## Bounds and feasibility

| Stage | Wall seconds | CPU seconds | Windows job committed memory |
| --- | ---: | ---: | ---: |
| Build | 600 | 1800 | 16 GiB |
| Generated controls | 180 | 900 | 4 GiB |
| Source149 cost | 180 | 600 | 16 GiB |
| Complete299 pair | 1800 | 7200 | 16 GiB |

The existing bounded-job helper enforces process-tree limits and records final
job accounting/cleanup. Cost must satisfy
`1.25 * 299 * source_phase_seconds + finish_seconds + 180 <= 1500`
and observed peak job memory below12 GiB before full execution. Source time
includes both passes. This is a deliberately padded feasibility estimate with
300 seconds left below the hard wall cap, not a speed claim or proof of peak
memory on299 sources. A refused resource gate has no bypass, resize or substack
fallback. Root schedules sequentially with other large jobs. Finalise only
reads retained TIFFs; it never invokes the RAW consumer.

## Delivered evidence

Finalise validates the same full receipt and baseline again. It retains both
native TIFF masters, native6468x4300 PNGs and1617x1075 overviews. Existing view
helper conversion is fixed high-byte RGB16→RGB8, with no contrast normalization,
and original common TIFF ICC preserved/read back. The seven fixed chip regions
from ca-before-mhc/inspection-1 are copied without registration or resampling;
paired PNGs are canonical-left/coherent-right, with each half's decoded bytes
and ICC checked against its source patch. Whole images are reviewed before
crops. The separate vendor comparison uses a different declared conversion;
this driver does not mix that display path into its own pair.

Completion binds masters, views, seven pairs, source/receipt hashes and both
screen decisions, leaving visual_verdict null. No alpha/depth-map smoothness,
gradient increase or isolated attractive crop can supply a photographic
verdict. A useful whole-chip result would license only investigation of an
optional mode with explicit limitations, not general/default eligibility.
