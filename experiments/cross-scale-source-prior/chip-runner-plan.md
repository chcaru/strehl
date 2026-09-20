# Root-executed chip observation driver

Root explicitly authorized this separate observation **after** the general
screen failed. The old `run.py`, controls, bars and result are unchanged. This
driver cannot turn a passing test process into quality admission: its fresh
screen must equal the retained twelve-case JSON semantically, including the
false `photographic_replay_admitted` decision. The photograph addresses only
the question in [observational-plan.md](observational-plan.md); it is not a
default proposal, automatic opaque-surface detector, or Helicon explanation.

Only `chip-run.py` and this plan belong to the runner author. Root adds the
test include, builds and executes. The numerical author owns the adapter; a
different agent reviews it. No build, RAW decode, test or image judgement is
performed by the runner author.

## Frozen execution sequence

Run from the repository root, using new non-existing output directories:

```text
python experiments/cross-scale-source-prior/chip-run.py build --out experiments/cross-scale-source-prior/chip-build-1
python experiments/cross-scale-source-prior/chip-run.py controls --build experiments/cross-scale-source-prior/chip-build-1 --out experiments/cross-scale-source-prior/chip-controls-1
python experiments/cross-scale-source-prior/chip-run.py cost --build experiments/cross-scale-source-prior/chip-build-1 --screen experiments/cross-scale-source-prior/chip-controls-1 --out experiments/cross-scale-source-prior/chip-cost-1
python experiments/cross-scale-source-prior/chip-run.py full --build experiments/cross-scale-source-prior/chip-build-1 --screen experiments/cross-scale-source-prior/chip-controls-1 --cost experiments/cross-scale-source-prior/chip-cost-1 --out experiments/cross-scale-source-prior/chip-full-1
python experiments/cross-scale-source-prior/chip-run.py finalise --build experiments/cross-scale-source-prior/chip-build-1 --screen experiments/cross-scale-source-prior/chip-controls-1 --run experiments/cross-scale-source-prior/chip-full-1 --out experiments/cross-scale-source-prior/chip-inspection-1
```

Build is release, two Cargo jobs, offline/locked, with the existing native
pyramid/GPU/direct-plane/correction-variance features. Both CLI and core source
timestamps are refreshed; fresh `Compiling` lines for both are mandatory.
Rust/WGSL/include/manifests, required designs/plans/driver/helper sources, and
the independent review when present before build are hash-bound. Future outcome
reports are excluded. Copies of both release and test executables are retained;
all later stages use exactly the bound test executable.

Controls run the unchanged module filter
`merge_cmd::cross_scale_source_prior::independent_controls::`, require exactly
two tests and twelve cases, and compare the complete parsed JSON to original
screen SHA256
`a63516111176f8b68a2f3d433ca596f672ea0a02823f71e298c92be546ee9144`.
Original control/plan source hashes are separately pinned. No timing/path
fields are dropped or approximate metric tolerances introduced.

Cost/full invoke the exact ignored test
`merge_cmd::cross_scale_source_prior_chip::chip_complete_pair` through
`STREHL_CROSS_SCALE_SOURCE_PRIOR_CHIP_CONFIG`. Schema1 contains phase,
source_dir, warp_map, out_dir, expected_crop and tone, matching the existing
phase-packed chip wrapper. GPU device scheduling, eight Rayon/pyramid threads,
full-resolution rounded direct planes, green probe, normal optical CA and
parallel warp writeback are explicit. The separate CA-before-MHC experiment,
fine-support and defect modes are off. Sanitized environment and exact commands
are retained. There is no user-selectable algorithm parameter.

## Resource decision and immutable input/output checks

| Stage | Wall seconds | CPU seconds | Windows job committed memory |
| --- | ---: | ---: | ---: |
| Build | 600 | 1800 | 16 GiB |
| Unchanged controls | 180 | 900 | 4 GiB |
| Source149 cost pair | 180 | 600 | 16 GiB |
| Complete299 pair | 1800 | 7200 | 16 GiB |

Each launched process uses the existing bounded Windows job utility; exit,
termination accounting and clean child cleanup are required. Finalisation
reads saved TIFFs only and does not launch the RAW consumer. No simultaneous
large external or Strehl render is scheduled by this driver; root controls
that scheduling.

The single-source cost still uses the original index149 probe identity and
held299-source geometry/metadata. Its two passes, complete finish and writers
are exercised; single-source candidate/baseline equality is required. Resource
permission for the full pair requires
`1.25 * 299 * source_phase_seconds + finish_seconds + 180 <= 1500`
and observed cost peak job memory below12 GiB. The source time includes both
streamed passes. This padded estimate reserves300 seconds below the hard wall
limit, but one source cannot certify whole-stack runtime or peak memory. It is
not a benchmark or a quality decision. A failed estimate refuses the full
stage; there is no override, reduced frame count, or parameter retry here.

All299 original paths/names/size/modification stamps come from the retained
chip inventory and are checked before/after; source149 additionally has a
whole-file hash before/after. Adapter source evidence hashes every decoded
active-u16 frame and checks both passes. The wrapper compares active hashes and
original-index beta values against the retained complete phase-packed baseline
receipt. This reuses the original RAW decoder, not a new decoding pipeline.
Map SHA256, reference149, common crop[141,97,3234,2150] quads, pinned
tone[.004293,.946441,.55], canonical four chunks of75/75/75/74 and eight threads
remain required. The adapter records held finest/base/fallback/hull state and
replay equality. Original buffers remain one source at a time.

Full baseline must be6468x4300 RGB16, have decoded little-endian pixel hash
`7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db`,
and equal the actual retained phase-packed full baseline pixel array. Its
collapsed four-plane hashes also match that receipt. TIFF container hashes are
recorded separately so the build tag is not confused with a pixel difference.
Every emitted TIFF hash is tied to the adapter receipt. A mismatch stops before
photographic interpretation; partial outputs and failure logs are preserved.

## Complete photograph delivery

Finalise requires the successful full receipt and exact baseline again, then
uses the existing phase-packed view helper: fixed high-byte RGB16-to-RGB8
conversion, no auto contrast, native6468x4300 PNG and1617x1075 overview, and
the original TIFF ICC preserved/read back. Native TIFF masters are linked,
never replaced by PNGs. The seven previously fixed native regions are copied
without warping/resizing, paired baseline-left/candidate-right with exact
decoded crop-byte and common-ICC checks. Whole images precede crops in review.
This own-pair display uses one convention; it is not the separate vendor
comparison's rounded conversion or an external-gauge correspondence test.

Completion JSON binds masters, whole views, all seven pairs, recipe/source
receipts and historical baseline equality. It retains
`photographic_replay_admitted=false`, `visual_verdict=null`, and the post-failure
rescoping statement. Any photographic judgement is a later independent review;
neither resource permission nor output creation supplies it.
