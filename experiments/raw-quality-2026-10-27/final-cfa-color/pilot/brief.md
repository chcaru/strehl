# Fixed final-CFA spectral completion pilot

2026-10-27. Root releases source implementation of ../design.md with all
qualifications in ../challenge.md and ../prior-photo-constraints.md retained.
The active native-spectral-full299-1 recipe remains frozen. No numerical, RAW,
GPU, image-export or build work runs until root observes its terminal state.
New files here are permitted; do not edit existing Rust/Cargo or spectral-pilot
files. This pilot has no product-default or photographic admission.

## Ownership and operator

Cfa-residual owns spectral-completion.py, API and implementation notes: the
single fixed full mirror-periodic operator, sequential R/combined-G/B, exact
integer passband boundaries, f32/complex64 signal arithmetic, same held known
sample normalization, pre-restoration diagnostic and exact known-site restore.
No tiling, tapered transition, extra color prior, learned model or per-source
completion. Preserve signed input CFA and actual normalized CFA/camera outputs.
Runtime has no import-time GPU work. Controls can call the actual operator and
exercise wrong green mask, phase/channel assignment and doubled-gain foils.

Photo-review owns a NEW, unregistered normalized-camera native writer and its
saved-field driver/views adapter. The existing direct-rgb-develop executable
is not suitable: it expects camera DN, applies WB/range again, and requires
demosaic_calls=0. Do not counterfeit that receipt or invert normalization to
reuse it. Adapt the native spectral final developer's genuine normalized-camera
writing path in a new file; no source demosaic, second completion or retone.
Record one final completion in the upstream producer and zero in the writer.
Only root later registers/builds it. If formatting new Rust, explicitly use
skip_children=true; a path module must not reformat shared image_out.rs.

Integration-review owns independent controls.py/protocol and reviews the actual
operator/API before execution. Use an independently implemented small direct
DFT or finite compatible truth, not the producer's mask helper. Retain all ten
existing controls5 CFA cases and both candidate/uniform fields byte-identically.
Known-site identity alone cannot validate the missing RGB field. Freeze numeric
mechanical tolerances and descriptive quality bars before root executes.

Root owns wrappers, process limits, registration/build, full photographic release
and final decision. Agents can coordinate source/API details but cannot schedule
jobs. New source-only files do not authorize concurrent numerical execution.

## Prospective stages after the active full299 job

1. Build the new normalized-camera writer with an explicit owned job boundary;
   exact native null of the existing held MHC camera field must reproduce full
   baseline RGB16/float pixels and material metadata. No re-normalization.
2. One fixed controls job:300s wall/1200CPU/12GiB host/8GiB GPU. Constants and
   saved noisy flats first; all20 existing generated fields, physical parity,
   green diamond and exact Nyquist-boundary partitions, affine/edge/ringing
   fields and identical-CFA neutral/chromatic ambiguity. Preserve actual native
   outputs and signed components; no lower-bound-only sharpness acceptance.
   Mechanical errors block real-field execution. Known prior tradeoffs remain
   explicit quality failures and do not by themselves erase the option of one
   finite complete photograph, as the actual corpus is decisive.
3. One complete-field cost:300s/1200CPU/16GiB host/8GiB GPU, actual6896x4596,
   exact13790x9190 extension, all FFT planning/workspace, channels and writers.
   Refuse if bounds fail; no automatic tiling/precision/boundary substitution.
4. If mechanically valid and practical, root can release the bounded comparison
   on the exact completed full spectral candidate and uniform CFA. Include the
   complete-field cost output from the held native baseline CFA as a direct
   final-color intervention independent of the new fusion. Retain the ordinary
   MHC and new color completion for all three CFA inputs: six complete photos
   and sixty frozen native witnesses, plus HeliconB4/B8. Complete RGB16, float,
   genuine camera and unchanged CFA masters and independent photographic review
   are mandatory. This prospective addition needs no further numerical job.

No299-frame rerun is required for this final-stage comparison. A photographic
null closes this exact recipe without strength sweeps. A substantial whole-image
benefit still needs flat60 and second-insect299 transfer with their own metadata,
geometry and development. This is a general final-color reconstruction question,
not a weevil-specific texture or color treatment. Neither a synthetic gain nor
noise reduction by erased detail can complete the user's broader quality goal.
