# Bounded session geometry consumer

Allocation: multi-stack-2026-10-28-geometry-core. Base: c149e52834fc1c86c2af0fe022713c39fa25f33c.
Source is implemented; root schedules compilation and measurements. No RAW pilot,
placement-quality improvement or throughput result is claimed by this note.

## Public integration

`align_session(session, identities, source_cache, config, resampler)` returns
`SessionAlignment { map, report, pair_candidates }`. The supplied full SHA256
identities must match the resolved ordered frames. `SessionAlignConfig` exposes
memory and worker limits plus explicit research settings; normal product controls
need only memory and workers. `save(path, session)` creates a fresh envelope and
`load(path, session, identities, config, resampler)` requires an exact binding.

The envelope includes the original exact-hex WarpMap, its SHA256, all full source
identities, ordered manifest/pass/segment layout, all configuration values,
resampler, and hashes of this consumer and core alignment implementation. It is
published with an atomic same-directory hard link that refuses an existing name.
Unsupported filesystems refuse publication. Sources and their directories remain
read-only; no ordinary capture sidecar is used.

An explicit primary chooses its middle frame as the geometry reference. Otherwise
the longest pass (lowest index on ties) supplies the middle reference. Every
delivered pose maps that one reference's centered plane coordinates to the source
frame. One plane pixel is two active sensor pixels. Automatic reference choice
confers no appearance or fusion priority. Output geometry preserves the reference
active plane dimensions; consumers can derive framing and support from the map.

## Measurements and search policy

Each original source is decoded at most once when absent from the persistent u16
CFA cache. A guide averages the ordinary black-subtracted green luma directly from
active CFA quads, with the same order, clamps and box arithmetic as the existing
operators. The default maximum guide side is 1024. Its integer reduction drops a
partial final box; lifting estimates includes the resulting centered-coordinate
offsets. Guides have ordinary 4x and 2x coarse pyramids.

Within each explicit pass, direct guide candidates use spans 1, 2, 4, 8, 16, 32,
64 and 128. Ordered folder segments remain inside that pass. A 7-by-7 distributed
probe grid links the reference pass to each other pass. Per-pass guide solves and
median probe offsets propose a breathing-scale search axis only. Each frame
proposes the closest scale in the other pass and its immediate neighbors, in both
directions. Those composed search hints never become delivered poses.

Every accepted guide pair is measured directly again against native-resolution
green planes reconstructed from original cached CFA. Native refinement uses the
existing iterated fine estimator with a correctly lifted guide seed. There is no
aligned source volume. Default fine settings are 128-pixel tiles, 12-by-8 grid,
96-pixel margin, radius 6 and eight iterations; guide fine settings are 32-pixel
tiles, 8-by-6 grid, margin 24, radius 6 and two iterations. Both require at least
eight retained tiles, contrast 4, NCC peak 0.5 and MAD outlier factor 3. Coarse
guide settings are 16-pixel tiles, 6-by-4 grid and radius 8. These values are bound
in the envelope, not selected after looking at outcomes.

One joint native-edge solve uses explicit original pass tracks. Default solver
settings are unit edge weighting, smoothness 1, prior Huber 1 plane pixel, edge
Huber 3 plane pixels and three IRLS passes. Only original adjacent triples within
a pass receive smoothness. Only the reference's measured component receives
placements. Numerical gauge rebasing happens once after the solve. Both guide
and native accepted/refused attempts are reported; accepted receipts preserve
exact transform coefficient bits, tile counts, fit residual and lever arm.
Global and per-pass component/cycle counts are reported. Estimator residual is
not placement truth. WarpMap held-out error and cycle floor remain explicitly
unmeasured until a separate commissioned pilot establishes them.

Final common-gauge scale matches are still unvalidated candidates. Mutual nearest
matches within one quarter of the smaller pass median adjacent scale step are
marked `candidate_same_focus`; `validated_same_focus` is always false. Flat scale
tracks have no step threshold and certify nothing. Distinct focus, aperture,
illumination, view or depth content can share the same scale. A merge consumer
must separately establish agreement, independent source support and radiometric
compatibility before claiming repeat noise reduction.

## Resource contract

Header stored dimensions are required before RAW allocation. The reservation
allows 256 padded rows/columns and four u16-equivalent decoded buffers, then
checks actual decoded geometry against the reservation. All sources must share
camera model and exact decoded sensor geometry. These checks do not establish
physical camera-body identity; the current metadata reader exposes no serial.

The memory plan includes the entire supplied resident-CFA cache budget, decoder
workspace, maximum-square guide/pyramid cache, native green cache, per-worker NCC
scratch, dense global solver matrices, bounded edge records and fixed overhead.
Arithmetic is checked for overflow. Worker counts shrink to fit one or more
native pairs; budgets unable to hold a direct pair are refused before decoding.
The LRU plane caches cannot evict pinned pair handles, and batch sizes reserve
their worst case of two distinct planes per worker. CFA I/O is serialized through
the single cache owner; independent pair fits run in a bounded Rayon pool and are
collected in canonical pair order. Guide residency is released before native
refinement; native planes are released before the global solve. This is a
conservative allocation reservation, not a measured process-RSS guarantee.

## Controls and remaining evidence

Nine CLI controls commission direct box arithmetic including padding/clamps,
pin-aware eviction/refusal, impossible resource budgets, pass boundaries and
reference choice, reversed focus hints and flat-scale refusal, probe direction,
actual guide/native pair consumers with forced CFA disk-cache reuse and a flat
refusal, exact bound-envelope reuse, and competing no-clobber writers. The
analytic pair consumer uses direct continuous-function source construction,
including scale/rotation, and checks final placements in the chosen common gauge.
It commissions operators, not photographic quality or calibration.

The first root core run passed seven of eight controls. The guide-lift negative
fixture's factor-3 dimensions accidentally gave zero box-center residual, so the
naive lift was also correct for that arm. Both 713-by-521 geometries were changed
to 715-by-523, producing a nonzero half-pixel center residual. Every positive
coordinate-chain assertion and the negative-control bar remain unchanged. Root
must rerun that corrected fixture; this lane ran no Cargo jobs.

Real pilots must preserve full source identities, exact build/config/commands,
host load and worker count; report common-gauge native placement and graph
coverage/cycles separately from merge outputs. Full-resolution photographs and
masters plus independently reviewed whole scenes and identical native crops are
required before a quality claim. Default native edge volume should be timed
before changing search density: dropping span-1 edges or replacing the joint
solve with per-pass reference composition is not an optimization candidate.
