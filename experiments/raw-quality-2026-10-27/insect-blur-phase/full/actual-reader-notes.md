# Full-grid original-green reader: fixed coordinates and phase combination

Implementation and these notes belong to the `insect-blur-phase/full` continuation.

Source design only2026-10-27. The fixed phase reader remains unchanged at
SHA`99bca095aa6c203ff248184f6c4b08801682565e65c03afabed5e9d5585f9410`.
Root reports controls1 PASS, all40 cases,9.844s and maximum required p2 error
<=0.057 native pixels. This is a generated mechanism result, not an actual
placement or photographic improvement. Root alone releases the actual reader,
Rust fit/global adapter and later full-image replay.

## Population and immutable source quantity

Use every2340 pair in the observed ordinary graph, in its original order,
with all96 original tile origins per pair. This is224640 tile slots,
449280 separate physical-green comparisons and898560 p1/p2 arm records.
No three-site selection or stationary field correction enters this campaign.
Spans remain1,2,4,8,16,32,64,96,128; preserve all refusals, including pairs
that the old coarse/fine path refused. Reproduce exact tile origins from the
observer and verify them against the existing `tile_grid` integer formula:
guide3516x2344, tile128, grid12x8, margin96. Do not round a floating grid.

Inputs are the existing independently checked original-u16 cache export:
`outputs/raw-quality-2026-10-27/direct-cfa-streamed-originals-1/output/receipt.json`,
SHA`057b50d7b311d9ff88e818a8d2376a00aac5abf07ab091afea37dd7627c56669`.
Require COMPLETE299_ORIGINAL_NATIVE_CFA_EXPORT, original_sensor_codes_preserved,
all299 identities and records. Each cache has16 header bytes: little-endian
u32(y0,x0,h,w)=(0,0,4688,7032), then original row-major u16, stride7032.
Read separate G1/G2 samples without WB, MHC, interpolation or green averaging.
Use the same injected phase noise/working levels as the passing control.
The15360 working threshold does not establish physical sensor clipping.

Bind the input-order manifest SHA
`0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f`
and held Catmull map SHA
`4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`,
reference149. Verify all cache content hashes once before and once after the
campaign, source/cache metadata and map/code bindings. Original RAW metadata
may be checked without decoding or hashing RAW anew; distinguish that from
the export receipt's earlier original-byte verification. Never write capture
sidecars. A bounded source cache may hold current original-u16 frames, not
an aligned volume; copy only requested128x128 phase patches into batch32.

## Physical point algebra

Let T_k be the held pull from anchor149 guide coordinates to source-k guide
coordinates, with guide centre(1758,1172). Its native-coordinate version is
`M_k(x)=2*T_k(x/2)`, with centre C=(3516,2344). Use the exact stored f64 map
bits. There is **no added half-pixel centroid offset** in this map convention.
The source-i to source-j prediction is `S_ji=M_j composed with inverse(M_i)`.
Equivalently, centred complex parameters are `a_ji=a_j/a_i`,
`b_ji_native=2*b_j-a_ji*(2*b_i)`. Wrong inverse/order/centre must fail a
geometry control before use. These f64 geometry calculations do not change
the reader's original-u16 storage or f32 signal arithmetic.

For observed tile origin(t_x,t_y), take exact original phase origins
`O_i1=(2*t_x+1,2*t_y)` and `O_i2=(2*t_x,2*t_y+1)`.
The128 samples have pitch2; their physical centres are
`c_1=O_i1+(127,127)` and `c_2=O_i2+(127,127)`.
The old nominal fit point is `P=2*(t_x+64,t_y+64)`, so c_1=P+(0,-1) and
c_2=P+(-1,0). Do not equate either sample centre to P.

For phase p with parity offset o_p=(1,0) or(0,1), choose the moving origin

```text
O_jp = o_p + 2*round_ties_to_even((S_ji(c_p)-(127,127)-o_p)/2).
```

This makes the predicted patch-centre remainder at most1 native pixel per
axis. Call the frozen reader with patch seed(0,0), its fixed+/-2-native search,
both actual origins and the same phase. The search is centered on integer-origin
correspondence, not the held fractional prediction: if that prediction leaves
remainder r, the held-relative correction interval is[-2-r,2-r] on each axis.
The actual reader records both r and those bounds; it does not recenter the
frozen search. Strict original-array support is
required for all128 samples. Out-of-support requests get a retained status;
do not shift, shrink, extend, pad or resample the patch to make it fit.
The reader returns total displacement
`D_p=O_jp-O_ip+estimated_patch_displacement`, in native source coordinates.
The shared initializer is the **held globally solved map**, different from
ordinary alignment's per-pair coarse estimate; it does not become measured
data merely because a reader refuses.

## One frozen G1/G2 combination, independently for p1 and p2

Require both phase estimates accepted by the unchanged reader. Compare their
held-map-relative residuals at their own physical centres:
`r_p=D_p-(S_ji(c_p)-c_p)`. Require Euclidean `norm(r_1-r_2)<=0.20` native
pixels. This is a prospective agreement heuristic (twice the0.10 control
error bar), not a propagated confidence interval or an occlusion detector.
Common bias can pass; phases are not independent repeated noise measurements.
No single-phase fallback or peak/SNR weighting is allowed.

For accepted pairs of phase estimates, use the exact mean physical point and
raw displacement, **without adding the held slope to measured displacement**:

```text
P_c = (c_1+c_2)/2 = P-(0.5,0.5) native pixels
D   = (D_1+D_2)/2
Observation { ux=(P_c.x-C.x)/2, uy=(P_c.y-C.y)/2,
              dx=D.x/2,          dy=D.y/2 }
```

A similarity/affine displacement evaluated at the mean point equals the mean
of its two values, so this combination requires no assumption that the held
slope is correct. It explicitly places the fit point0.25 guide pixels below
and left of the old nominal centre while preserving the same tile origins.
Convert to existing f32 Observation only at that interface. The held map is
used for origin selection and the phase-agreement heuristic, not injected as
an observation or substituted for a refused edge.

Retain both original phase records, origins, predicted centres, displacement
and residual vectors, disagreement and combined acceptance/refusal. p1 and p2
have independent acceptance populations under the same initializer; preserve
both rather than report only their favorable intersection. The raw phase
comparison would contain the predictable inter-centroid magnification term;
the residual agreement check removes that coordinate difference only.

## What the later map and photograph can establish

This local translation reader leaves intra-patch scale/rotation, finite-window
effects, changing depth and asymmetric/specular radiance unresolved. The
passing generated mechanism does not prove that a real accepted peak locates
the same physical structure. Record these limitations with every fitted map.

A separately released thin Rust adapter must reuse the existing similarity
fit, MAD/refit and robust global solve on these direct observations; no Python
geometry solver, chained correction or custom spatial field. Keep the existing
minimum-tile/refusal behavior, source ordering and graph. Preserve all edges
and statuses, anchor149's connected component, unplaced frames and cycle rank;
never insert held edges to conceal lost coverage. Score per-frame placement in
the actual merge gauge, not only an endpoint or fitted residual. Any fallback
graph policy would be a separate root decision, not implicit in this design.

If released and sufficiently supported, render complete all299 baseline/p1/p2
with identical fusion, CA-off, fixed crop/development and original source
order. p1 versus p2 isolates phase power conditional on this initializer;
either versus ordinary baseline also changes initialization, samples and
admission and cannot be attributed to squaring alone. Preserve full masters,
complete images and ten fixed witnesses plus HeliconB4/B8 comparison. The
legacy renderer's per-source-MHC/remosaic limitation remains; this registration
consumer does not repair it. No actual-reader, map or photographic claim is
made by these unexecuted source notes.

## Executable handoff and preservation

`full/actual.py` is the source-only implementation. Root executes:

```text
python -X faulthandler full/actual.py --mode cost --out <fresh-directory>
python -X faulthandler full/actual.py --mode full --out <fresh-directory>
```

The retained observer serializes pairs in lexicographic(i,j) order. Validate
that exact order against the complete requested span population; never renumber
the six cost pairs. `population.json` contains every selected original ordinal
and the exact96 tile origins. The authoritative observer is172MB JSONL and is
parsed one pair at a time into only compact pair identity/status records.

Each compact `observations.jsonl` row is
`{schema:1,ordinal,i,j,tiles:[{ordinal,p1,p2},...]}`. There are exactly96 tiles;
each arm is null or `{ux,uy,dx,dy,score}` with explicitly rounded f32 scalars.
`score` is the equal mean of accepted phase scores, diagnostic only. The actual
similarity/global fit remains in the separately commissioned native adapter.
`pairs.jsonl` separately retains all96 detailed tile records, both phase origins,
centroids, held predictions/remainders/search bounds, complete supported-reader
p1/p2 diagnostics, original observer statuses and per-arm combination refusal.
An out-of-support phase has an explicit support status and null reader, never
a fabricated estimate; both combined arms preserve the missing-phase reason.

Both modes verify all299 cache content hashes and headers before and after,
plus original RAW file metadata and all pinned source/map/manifest/observer
bytes. The new job does not rehash or decode original RAW captures; the prior
export receipt's RAW-byte verification is reused and labeled separately.
Only two original read-only u16 memory maps are open during a pair. Each phase
is independently copied into batches of at most32 original128x128 patches.
No full float guide, source RGB, resampling, spatial correction or aligned
volume is created. The worker uses four CPU threads, one interop thread, and
a six-GiB Torch allocation bound. The fixed noise is read from the pinned export
and verified against its exact f32 gain/read-variance bits, without an extra
quantization variance or any fitted private noise estimate.

The successful receipt status is `COMPLETE_INSECT_BLUR_PHASE_ACTUAL`, with mode,
pair/tile/phase/arm counts, all refusal populations, source/cache preservation,
reader metadata, per-pair timing and GPU high-water. Complete means the fixed
population was observed and saved; zero accepted observations would still be
a complete diagnostic, not an accepted map. `quality_claim`,
`photographic_admission` and `physical_error_identified` remain false.
Cost mode includes six fixed pairs and all their tiles, with binding/hash time
separate from the measured reader campaign. No full-graph performance claim
is made from unexecuted source or an extrapolation of six pairs.
