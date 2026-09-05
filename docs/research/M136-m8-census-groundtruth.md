# M136 — independent M8 census ground truth

**Status:** verifier preparation; no M142 target result and no M170 result or
implementation was inspected.

**Evidence labels:** **VERIFIED BY RUNNING** means I executed the stated check
and read its output. **INFERRED BY READING** means the conclusion follows from
the cited code or frozen protocol without executing a target census.
**COULD NOT VERIFY** marks evidence that does not yet exist in this verifier's
scope.

**VERIFIED BY RUNNING — citation basis:** All scorecard line references below
resolve against committed blob
`1fe7c9fc07e1eefcdc4526c277c4450a4283be90`
(`docs/proposals/2026-09-sota-scorecard.md` at source revision
`02c6224ad6d5cc14d396ed29266946f528f92d72`). The working copy was concurrently
loaned to another lane, so I neither edited it nor used its moving line numbers
as the citation basis.

**VERIFIED BY RUNNING — local generated-evidence identity:** The cited files
under `experiments/M8-overshoot/out/` and
`experiments/M134-kernel-frontier/` were not tracked at this revision. I read
the exact local bytes below. Their hashes identify this audit input; they are
not a substitute for a future run's sealed provenance.

| Local evidence | SHA-256 |
|---|---|
| `experiments/M134-kernel-frontier/patch_snapshot.py` | `1826B940ADA3832DA6EFF60F246614D5D55D320801057D60C0BE7460AD3CF708` |
| `experiments/M134-kernel-frontier/out/clamped-flat-et1s-state/m8-r.json` | `7FBCCC57671D36C017212C53859750E20AB5F34274A19D70883945BF0F1CC3F7` |
| `experiments/M134-kernel-frontier/out/clamped-flat-et2.5s-state/m8-r.json` | `5BE981BA661CFA424167383FC19F0697DA73EC5A38D1080B59A68318D58FBD59` |
| `experiments/M134-kernel-frontier/out/clamped-flat-et6s-state/m8-r.json` | `E4425625BE4FBB93E1D3C19943469F7A23E4F17B656F1A5EE61D34E961723C70` |
| `experiments/M8-overshoot/out/flat-et1s-state/meta.json` | `7534DE796DE369FA882B0173EBED0276CC0EEE9FDD6B4EA0F9178F5D206FEA2D` |
| `experiments/M8-overshoot/out/flat-et2.5s-state/meta.json` | `981725DFA9A875F1F2CAF2DEA1B45F33638114F2CF28447A49CFA90763B91195` |
| `experiments/M8-overshoot/out/flat-et6s-state/meta.json` | `846CCB936B68A586032724B55FF4F3C1585FD38044C9DA8C2BC1F184B0E8E4FF` |
| `experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs` | `F00AE825D4ED850830AB78D49B551E211A95C62EACF448A56C4BCB7BB5FFBAFD` |
| `experiments/M8-overshoot/out/source-snapshot/crates/strehl-core/src/align.rs` | `E1C906B28E4ED1FBD1610FB1D9770E14FCFC636D9658114EF60A6E314D3C499C` |

**VERIFIED BY RUNNING:** The frozen `align.rs` is byte-identical to the file at
commit `76b3d9cc8b5185735d6c19d4339ce74d29e333e2`. The frozen `align_cmd.rs`
differs from that commit's file only by the registered `trace_site` call at
snapshot lines 2122–2135.

## 1. Central ruling: an exact 4x4 source-hull clamp is sufficient for M8-R

**INFERRED BY READING — answer first:** M8-R does **not** compare a merged
output with the frames that formed it. It records and checks each frame's
resampler result independently, before merge. Therefore an exact zero-margin
clamp of the returned two-dimensional Catmull-Rom sample to the minimum and
maximum of the exact `4x4` source support is sufficient by construction to make
M8-R exactly zero. Merge, reconstruction, green averaging, output gain,
serialization and final rail clipping cannot contribute to M8-R because they
occur after its observed boundary
(`docs/proposals/2026-09-sota-scorecard.md:1330-1354`, M8-R exact computation;
`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2088-2147`).

**INFERRED BY READING — precision correction:** A two-dimensional cubic sample
uses **sixteen source values**, not four. Four is the one-dimensional tap count.
The shipping `sample_catmull_rom` computes four horizontal taps in each of four
rows and then combines the four rows
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-core/src/align.rs:2664-2709`).
The independent checker takes offsets `(-1,0,1,2)` in both dimensions and
therefore reconstructs the same `4x4` set
(`experiments/M8-overshoot/checker.py:250-279`, symbols `support_spec` and
`exact_support`). A claim that a candidate is merely “inside four taps” is not
enough: the final 2-D returned value must be proved inside the hull of all
sixteen source values.

**INFERRED BY READING — proof:** Let the exact finite support be
`S={s_1,...,s_16}`, `lo=min(S)`, `hi=max(S)`, and let `c` be the ordinary
Catmull-Rom result. The M134 definition returns

```text
r = clamp(c, lo, hi).
```

It calls the unchanged Catmull-Rom gather, recomputes `lo` and `hi` from the
same indexed `4x4` rectangle, and clamps once
(`experiments/M134-kernel-frontier/patch_snapshot.py:31-58`,
constant `CLAMPED_FUNCTION`). Hence `lo <= r <= hi`. M8-R uses
`tau_R = 8*ULP_f32(max(1,abs(lo),abs(hi)))`, where `tau_R >= 0`, and counts only
`r < lo-tau_R` or `r > hi+tau_R`
(`experiments/M8-overshoot/checker.py:281-285`;
`experiments/M8-overshoot/checker.py:352-378`, symbols `tau_r` and
`consume`). Both predicates are false. This is an integer-zero result, not a
small-rate argument.

**INFERRED BY READING — support and population are unchanged by that clamp:**
M134 assigns clamped Catmull-Rom the same support half-width `2.0` and the same
`sample_checked` route as ordinary Catmull-Rom
(`experiments/M134-kernel-frontier/patch_snapshot.py:120-148`). The production
validity predicate rejects coordinates whose complete support leaves the plane
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-core/src/align.rs:2865-2896`,
method `Resampler::sample_checked`), and the checker independently repeats that
predicate before counting a sample
(`experiments/M8-overshoot/checker.py:258-266`, function `exact_support`).
Thus a correct clamp changes values, not the M8-R denominator.

**INFERRED BY READING — meaning of “pre-clamp”:** The scorecard also calls
`r_k` the “actual gathered value”
(`docs/proposals/2026-09-sota-scorecard.md:1330-1333`, M8-R actual-value rule).
The coherent reading of
“pre-clamp” there is before a later container or output-rail clamp, not before
a clamp that is constitutive of the registered resampler. For a clamped-cubic
kernel, the value it returns is the actual gathered value. A clamp applied only
to the trace while an unclamped value enters the merge would be invalid.

**VERIFIED BY RUNNING — corroboration, not a shipping verdict:** I parsed the
three existing M134 `m8-r.json` files and summed their integer fields. They
contain respectively `0/1,977,960,960`, `0/2,010,926,976`, and
`0/2,142,791,040`, with zero coverage mismatches, for aggregate
`0/6,131,678,976`
(`experiments/M134-kernel-frontier/out/clamped-flat-et1s-state/m8-r.json:1-8`;
`experiments/M134-kernel-frontier/out/clamped-flat-et1s-state/m8-r.json:373-381`;
`experiments/M134-kernel-frontier/out/clamped-flat-et2.5s-state/m8-r.json:1-8`;
`experiments/M134-kernel-frontier/out/clamped-flat-et2.5s-state/m8-r.json:379-387`;
`experiments/M134-kernel-frontier/out/clamped-flat-et6s-state/m8-r.json:1-8`;
`experiments/M134-kernel-frontier/out/clamped-flat-et6s-state/m8-r.json:403-411`).
Those artifacts agree with the proof, but they were produced by an experiment
snapshot; they do not by themselves prove that a later shipping implementation
is wired identically.

**INFERRED BY READING — boundary of the ruling:** Exact clamping can close
M8-R alone. It cannot imply M8-O zero. After the M8-R trace, the pipeline still
undoes site gain, restores the pedestal, rounds and clamps to `u16`
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2136-2147`);
then it merges frames, forms output green from G1/G2, applies output gain and
range normalization, saturates, and serializes
(`crates/strehl-cli/src/merge_cmd.rs:4668-4735`,
`crates/strehl-cli/src/merge_cmd.rs:7124-7178`,
`crates/strehl-cli/src/merge_cmd.rs:7555-7579`). Those are M8-O contributors,
not M8-R contributors.

**COULD NOT VERIFY:** No M170 source patch, binary, trace, census, or
commissioning artifact was supplied. I therefore cannot yet verify that its
“clamped cubic” is the exact 2-D `4x4` clamp proved above, that every production
dispatch reaches it, or that its trace records the same clamped value consumed
by the merge.

## 2. Exact M8-R census

### 2.1 Population and stage

**INFERRED BY READING:** The scorecard population is every geometrically valid
placed sample of every frame in every scored capture, observed at the linear
pre-merge `f32` gather boundary
(`docs/proposals/2026-09-sota-scorecard.md:1324-1338`, M8 census and M8-R
population rules). In the frozen
development implementation, each frame is visited at each CFA site
`R=(0,0)`, `G1=(1,0)`, `G2=(0,1)`, and `B=(1,1)`; R and B map to output
channels 0 and 2 while both greens map to channel 1
(`experiments/M8-overshoot/checker.py:20-27`).

**INFERRED BY READING:** “Source” here does not mean untouched mosaic codes.
The producer first forms a full-resolution, black-subtracted,
white-balanced `f32` mosaic and demosaics it into R/G/B channel planes
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2027-2071`).
Each CFA site samples its corresponding full-resolution channel plane; G1 and
G2 sample the same green plane at different site offsets
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2081-2099`).
M8-R therefore certifies the resampler against these observed demosaiced
channel-plane values, not directly against raw CFA photosites.

**INFERRED BY READING:** `sample_checked` writes the gathered value into
`scratch.dst`; the trace receives that source plane and the same
`scratch.dst` immediately afterward
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2098-2135`).
The trace format serializes the source `f32` plane, gathered `f32` plane,
geometry, CFA site, channel, transform, sensor range and site gain
(`experiments/M8-overshoot/m8_trace.rs:35-60`;
`experiments/M8-overshoot/m8_trace.rs:83-121`, function `trace_site`).
Only after tracing does the producer undo gain, restore black, round and clamp
to `u16`
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2136-2147`).

### 2.2 Coordinate, validity and hull

**INFERRED BY READING:** For output quad coordinate `(x,y)` and CFA offset
`(dx,dy)`, the producer evaluates the per-site transform at
`(x+dx/2,y+dy/2)` about `(cx,cy)` and doubles the result to address the
full-resolution source plane
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:1978-1988`;
`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2095-2113`).
The checker independently expands the recorded complex similarity coefficients
into that same equation in `row_coordinates`
(`experiments/M8-overshoot/checker.py:234-248`).

**INFERRED BY READING:** For Catmull-Rom, a coordinate is counted only when the
full support half-width `2.0` fits. At the floor of the mapped coordinate, the
hull is

```text
lo_k(x,y,s) = min source[iy+dy, ix+dx]
hi_k(x,y,s) = max source[iy+dy, ix+dx]
              for dx,dy in {-1,0,1,2}.
```

The checker implements the validity boundary, coordinate clamping and all
sixteen reads independently
(`experiments/M8-overshoot/checker.py:250-279`, functions `support_spec` and
`exact_support`). Those indices match the nested loops in the production
Catmull-Rom sampler
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-core/src/align.rs:2687-2708`).
Bilinear has a separate `2x2` support, offsets `(0,1)` in both axes
(`experiments/M8-overshoot/checker.py:250-257`).

### 2.3 Numeric domain, comparison and aggregation

**INFERRED BY READING:** The compared quantities `r_k`, `lo_k` and `hi_k` are
all `f32` values in the black-subtracted, white-balanced, demosaiced source-plane
domain. The only tolerance is

```text
tau_R = 8 * ULP_f32(max(1, abs(lo_k), abs(hi_k))).
```

The checker obtains the positive-`f32` ULP with `nextafter` and counts a lower
or upper violation exactly at the two strict inequalities stated in section 1
(`experiments/M8-overshoot/checker.py:281-285`;
`experiments/M8-overshoot/checker.py:352-378`). Sensor noise receives
no separate allowance because it is already present in the sixteen observed
support values
(`docs/proposals/2026-09-sota-scorecard.md:1339-1344`, M8-R tolerance rule).

**INFERRED BY READING:** The per-block denominator increments by the number of
independently reconstructed valid coordinates. The checker requires
`isfinite(trace)` to agree exactly with that validity mask and errors on the
first mismatch; it does not count only convenient finite outputs
(`experiments/M8-overshoot/checker.py:352-368`). Capture aggregation is an
integer sum over all consumed frame-site rows
(`experiments/M8-overshoot/checker.py:445-478`, function `aggregate_r`).
The bar is `V_R=0`, decided from the integer count, with a separate
crop/reference identity arm also required at zero
(`docs/proposals/2026-09-sota-scorecard.md:1356-1361`, M8 success rule).

**INFERRED BY READING — pass licence:** An M8-R pass licenses only:
“every traced resampler output was inside the scalar min/max hull of the exact
source values consumed at that coordinate, within `tau_R`.” It does not license
detail retention, spatial faithfulness, absence of clipping, a clean final
image, or M8-O. A nearest-neighbour, bilinear, or destructive in-hull operator
can legitimately pass M8-R while failing another quality axis; the scorecard
therefore retains independent detail/transfer controls
(`docs/proposals/2026-09-sota-scorecard.md:1434-1443`, M8 control paragraph).

## 3. Exact M8-O census

### 3.1 Superseded v1.4: the source of `74,173,536`

**INFERRED BY READING:** Historical M8-O v1.4 uses the final RGB `uint16` TIFF,
not the per-frame gather. The checker requires shape
`(height,width,3)`, decodes each channel code as `O=e/65535`, and counts one
coordinate for each finite reconstructed channel hull
(`experiments/M8-overshoot/checker.py:546-584`, function `final_output`).

**INFERRED BY READING:** While consuming every frame-site block, v1.4 first
computes the same exact source `lo`, `hi`, and `tau_R` as M8-R. It then maps
them only by

```text
scale = output_gain / site_gain / sensor_range
lo'   = f32(lo * scale)
hi'   = f32(hi * scale)
tau'  = f32(tau_R * scale).
```

For each output channel and coordinate it stores `min(lo')`, `max(hi')`, and
`max(tau')` over all geometrically valid frame-site blocks
(`experiments/M8-overshoot/checker.py:322-351`;
`experiments/M8-overshoot/checker.py:386-417`). Because
`SITE_CHANNEL` maps both G1 and G2 to channel 1, v1.4 reduces green site
intervals independently across all frames rather than first preserving the
same-frame G1/G2 pair
(`experiments/M8-overshoot/checker.py:20-27`;
`experiments/M8-overshoot/checker.py:411-417`).

**INFERRED BY READING:** V1.4 compares the final code against

```text
O < aggregate_lo - (aggregate_max_tau + 0.5/65535)
O > aggregate_hi + (aggregate_max_tau + 0.5/65535).
```

It counts every bracketed final `(x,y,R/G/B)` coordinate, raises if any final
coordinate is unbracketed, and records no per-frame multiplier in this
denominator
(`experiments/M8-overshoot/checker.py:568-611`). The min/max is a broad
interval hull across all valid frames, never a producer-selected contributor
set
(`docs/proposals/2026-09-sota-scorecard.md:1345-1350`, M8-O v1.4 rule).

**INFERRED BY READING — why superseded:** The traced gather does not go
directly through the scale above. It first traverses inverse site gain,
pedestal restoration, `f32` rounding and intermediate `u16` clamping
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2136-2147`),
while the final writer black-subtracts, combines green, applies output
gain/range, saturates, and quantizes
(`crates/strehl-cli/src/merge_cmd.rs:4668-4735`;
`crates/strehl-cli/src/merge_cmd.rs:7555-7579`). V1.4 omitted that
intermediate representation and did not project an above-one or below-zero
source interval into the final representable domain. It therefore mixed
algorithmic invention with unavoidable container saturation; the scorecard now
retains v1.4 only as superseded history
(`docs/proposals/2026-09-sota-scorecard.md:1363-1418`, prospective v1.5
replacement history).

### 3.2 Governing prospective v1.5

**INFERRED BY READING — population:** V1.5 counts every eligible
`(capture,x,y,channel)` in the compact final linear TIFF, with
`channel in {R,G,B}`. Compact `(x,y)` maps to full-plane
`(X,Y)=(x+crop_x,y+crop_y)`. Eligibility requires at least one geometrically
valid frozen input frame. Both rails and source intervals wholly outside
`[0,1]` remain in the denominator; a crop mismatch, unbracketed TIFF
coordinate, or missing/duplicate expected frame-site trace makes the result
`UNMEASURED`
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:65-70`).

**INFERRED BY READING — per-frame interval and representation:** For each valid
frame and site, v1.5 starts from the exact M8-R support interval expanded by its
M8-R tolerance,

```text
I_k = [lo_k - tau_R,k, hi_k + tau_R,k].
```

For R and B it then applies, with the recorded scalar types, operation order
and outward interval rounding,

```text
inv_k,c = f32(1.0_f32 / g_k,c)
t_k,c(z) = f32(f32(z * inv_k,c) + b_k)
u_k,c(z) = u16(clamp_[0,65535](round_ties_away_from_zero(t_k,c(z))))
P_k,c(z) = f32(f32(max(f32(f32(u_k,c(z)) - b_k), 0) * G_c) / R_k)
F_k,c(z) = clamp_[0,1](P_k,c(z)).
```

Here `g` is site gain, `b` black level, `G` final output gain and `R` sensor
range. Every parameter and arithmetic rule is evidence; an unknown or changed
operation makes the result `UNMEASURED`
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:71-79`;
`experiments/M136-m8o-bar/verifier_m136.py:807-841`).

**INFERRED BY READING — operation-order trap:** The preregistration's compact
`z/g+b` notation does not license direct per-sample division. The production
path computes one rounded `f32` reciprocal and then multiplies each gathered
sample before adding black
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2136-2147`).
The independent interval replay therefore computes
`inverse_gain=f32(1/g)` once and directed-multiplies by that rounded value
(`experiments/M136-m8o-bar/verifier_m136.py:807-818`). Direct division is a
different numeric path and can change the intermediate `u16`.

**INFERRED BY READING — green:** G1 and G2 are transformed through their own
intermediate-`u16` and black-removal paths **within the same frame**, then
averaged with the candidate's recorded `f32` order and only afterward mapped
through the common green output gain/range and final projection. Reduction
across frames happens last
(`experiments/M136-m8o-bar/prospective-interpretations.md:44-86`).
This matches the product's same-pixel green mean
(`crates/strehl-cli/src/merge_cmd.rs:4724-4735`) and prevents a synthetic lower
bound from G1 in one frame being paired with G2 in another.

**INFERRED BY READING — aggregation and comparison:** For each channel, let
`J_k=F_k,c(I_k)`. V1.5 forms

```text
L = min_k inf(J_k)
H = max_k sup(J_k),
O = e/65535,
q = 1/131070,
violation iff O < L-q or O > H+q.
```

The per-frame representation map is applied before reducing frames; old
aggregate `o-lo/o-hi/o-tau` arrays and an empirical global allowance are not
substitutes
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:71-87`).
The final half-code `q` is the only tolerance outside the source interval
construction.

**INFERRED BY READING — exact meaning of the broad hull:** `[L,H]` is the
interval hull of all valid per-frame interval images. It is generally wider
than the set-theoretic union when per-frame intervals are disjoint. Therefore
an M8-O pass licenses containment in the all-valid-frame min/max envelope; it
does not prove that one particular frame, or the producer's elected
contributors, individually support the output. This breadth is deliberate,
and it is why M8-R remains separately mandatory
(`docs/proposals/2026-09-sota-scorecard.md:1330-1333`, M8-R stage;
`docs/proposals/2026-09-sota-scorecard.md:1345-1350`, M8-O v1.4 reduction).

**INFERRED BY READING — rails and decision:** Final `[0,1]` projection makes a
correct matching rail value non-violating while retaining the coordinate in
`N`. The pre-saturation hull must separately report high/low
unrepresentable-support counts, split at-rail/off-rail
(`docs/research/M136-m8o-bar.md:670-682`). After commissioning, M8-O passes
iff every capture and aggregate has integer `V=0`; `V>=1`, including a rate
that formats as `0.0000%`, fails. The combined experiment passes only when
M8-O, M8-R and crop/reference identity are all zero
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:88-104`).

**INFERRED BY READING — pass licence:** A v1.5 M8-O pass licenses:
“every final serialized RGB code lies within the representable all-frame
min/max envelope reconstructed from exact source support after only the
declared fixed representation operations.” It does **not** license absence of
clipping or headroom loss, detail retention, per-frame support of the chosen
value, M8-R safety, or overall image quality. Mandatory rail reporting and the
separate M8-R gate preserve those distinctions
(`docs/research/M136-m8o-bar.md:399-407`;
`docs/research/M136-m8o-bar.md:432-442`).

### 3.3 The operational difference

| Element | M8-R | M8-O v1.5 |
|---|---|---|
| **INFERRED BY READING — observed value** | One actual gathered `f32` scalar per frame and CFA site, before merge (`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2098-2135`). | One decoded final `u16` RGB channel code per output pixel and capture (`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:65-70`; `experiments/M136-m8o-bar/clamped-m8o-preregistration.json:80-87`). |
| **INFERRED BY READING — source set** | Exact local support from one frame/site: `4x4` for Catmull/clamped Catmull. | The same per-frame support, transformed into the output domain, then enclosed across every valid frame; G1/G2 are paired within frame first. |
| **INFERRED BY READING — domain** | Black-subtracted, white-balanced, demosaiced source-plane `f32`. | Normalized final linear `[0,1]`, after declared intermediate representation and before comparison with the serialized code. |
| **INFERRED BY READING — what it can catch** | A resampler's own local under/overshoot before downstream clipping can erase it. | Merge, reconstruction, green-combination, restoration or other downstream excursions that survive into the deliverable. |
| **INFERRED BY READING — what cannot affect it** | Merge and all later output operations. | Nothing after serialization; however its broad all-frame hull can hide which frame or stage supplied an in-range value. |

## 4. Denominators

**VERIFIED BY RUNNING:** I parsed `results.json` and all three old `meta.json`
site tables, asserted every frame had exactly `{R,G1,G2,B}`, asserted every
site denominator was `3516*2344=8,241,504`, and recomputed both aggregates.
The recorded dimensions are height `2344` and width `3516`
(`experiments/M8-overshoot/out/flat-et1s-state/meta.json:2-3`;
`experiments/M8-overshoot/out/flat-et1s-state/meta.json:5775`;
`experiments/M8-overshoot/out/flat-et2.5s-state/meta.json:2-3`;
`experiments/M8-overshoot/out/flat-et2.5s-state/meta.json:5871`;
`experiments/M8-overshoot/out/flat-et6s-state/meta.json:2-3`;
`experiments/M8-overshoot/out/flat-et6s-state/meta.json:6255`).

**VERIFIED BY RUNNING — M8-R arithmetic:**

| Capture | Frames | CFA-site traces | Count |
|---|---:|---:|---:|
| `flat-et1s` | 60 | 240 | `8,241,504 * 4 * 60 = 1,977,960,960` |
| `flat-et2.5s` | 61 | 244 | `8,241,504 * 4 * 61 = 2,010,926,976` |
| `flat-et6s` | 65 | 260 | `8,241,504 * 4 * 65 = 2,142,791,040` |
| **Aggregate** | 186 | 744 | **`6,131,678,976`** |

The frame/site counts and recorded denominators are present in the frozen
result
(`experiments/M8-overshoot/results.json:67-130`;
`experiments/M8-overshoot/results.json:132-197`;
`experiments/M8-overshoot/results.json:199-264`), and the
aggregate is `6,131,678,976`
(`experiments/M8-overshoot/results.json:14-25`).

**INFERRED BY READING — what M8-R counts:** These are not six billion distinct
image pixels. They are gathered scalar plane-values: every valid output-grid
coordinate, repeated for every frame and each of four CFA sites. Green is
counted twice per frame, once as G1 and once as G2. The old Scale run happened
to make every output coordinate valid in every block; the general code counts
`valid`, not array size
(`experiments/M8-overshoot/checker.py:352-378`).

**VERIFIED BY RUNNING — superseded M8-O arithmetic:** One final TIFF has
`8,241,504` pixels and three output channels:

```text
8,241,504 * 3 = 24,724,512 channel-values per capture
24,724,512 * 3 captures = 74,173,536 channel-values.
```

All three captures record denominator `24,724,512` and zero unbracketed
samples, and the aggregate records `74,173,536`
(`experiments/M8-overshoot/results.json:3-13`;
`experiments/M8-overshoot/results.json:68-87`;
`experiments/M8-overshoot/results.json:133-153`;
`experiments/M8-overshoot/results.json:200-220`).

**INFERRED BY READING — what M8-O counts:** These are final serialized
channel-values, three per output pixel per capture, with no per-frame
multiplier. The checker loops three channels and counts each bracketed
coordinate once
(`experiments/M8-overshoot/checker.py:568-590`).

**INFERRED BY READING — future denominator warning:** `6,131,678,976` and
`74,173,536` are the frozen historical Scale-census denominators. V1.5 defines
its population on the compact Crop TIFF and requires independent crop
reconciliation
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:65-70`).
A later candidate must report its reconstructed integer denominator; it may
not inherit either historical number without reproducing the same dimensions,
frames, sites and validity population.

## 5. What can make a clean result untrustworthy

**INFERRED BY READING — required review checklist:** I will treat a future zero
as untrustworthy or narrower than claimed if any item below is not discharged.

| Failure mode | Required falsification/check |
|---|---|
| **Wrong support: `1x4` called `4x4`.** | Independently enumerate the sixteen final 2-D source indices. A separable four-tap claim is accepted only with a proof that its complete returned 2-D value lies inside the global sixteen-value hull (`experiments/M8-overshoot/out/source-snapshot/crates/strehl-core/src/align.rs:2687-2708`; `experiments/M8-overshoot/checker.py:250-279`). |
| **Checker support differs from clamp support.** | Compare floor rule, offsets, site phase, transform centre, coordinate doubling and boundary validity field by field; do not call the product sampler from the checker (`experiments/M8-overshoot/checker.py:234-279`). |
| **Clamp occurs only in instrumentation.** | Prove the traced buffer is the same `scratch.dst` consumed by the later frame write, and prove the production binary contains those bytes (`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2098-2147`). |
| **A later container clamp is mislabelled as the resampler fix.** | Trace the returned resampler `f32` before inverse gain/pedestal/`u16`; a final rail can erase evidence and cannot substitute for M8-R. |
| **Silent bilinear, nearest, constant, or wrong dispatch.** | In addition to zero M8-R, require an in-hull fractional texture where clamped output is bit-identical to ordinary Catmull-Rom and distinguishable from bilinear, plus a clamp-active case landing exactly on `lo` or `hi`. M8-R zero alone does not identify the kernel. |
| **Changed support shrinks the denominator.** | Require clamped support half-width `2.0`, exact expected frame/site manifest, and denominator equality with the Catmull arm (`experiments/M134-kernel-frontier/patch_snapshot.py:137-148`). |
| **Missing frames/sites or producer-selected validity.** | Reconstruct validity independently; require exactly four sites per expected frame; any missing/duplicate block is `UNMEASURED`, never a smaller clean census (`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:88-121`). |
| **G1/G2 mishandled.** | M8-R counts both sites separately. M8-O must pair them within the same frame before reducing frames (`experiments/M136-m8o-bar/prospective-interpretations.md:44-86`). |
| **Wrong numeric domain.** | M8-R hulls must use the traced WB+demosaiced `f32` plane. M8-O must replay inverse gain, black, intermediate `u16`, output gain/range and projection in the recorded order; neither may compare unlike units. |
| **Tolerance inflation or rounded-zero reporting.** | Recompute exact `tau_R`; use only final `q=1/131070` for M8-O; decide on integer `V==0`, never formatted `0.0000%` (`experiments/M8-overshoot/checker.py:281-285`; `experiments/M136-m8o-bar/clamped-m8o-preregistration.json:80-104`). |
| **32-bit aggregation.** | Use at least 64-bit integer counts: the historical M8-R denominator `6,131,678,976` exceeds `2^32`. Assert per-block, per-capture and aggregate sums. |
| **Producer-supplied hull, mask or verdict.** | Ignore all such fields and regenerate coordinates, support, validity, intervals and comparisons from source planes, placement and actual outputs (`docs/proposals/2026-09-sota-scorecard.md:1330-1338`, M8-R source/support rule; `experiments/M136-m8o-bar/clamped-m8o-preregistration.json:218-225`). |
| **Artifact consistency mistaken for re-derivation.** | Recompute from source-plane and gathered/TIFF bytes. Stored `m8-r.json`, `L/H` arrays or a second summation of the producer's verdict are cross-checks only. |
| **Hash/parse time-of-check gap.** | Read each sealed metadata artifact once, hash those bytes, and parse those same bytes; for large traces, bind parsing to the same sealed file handle/snapshot. Hashing a path and reopening it is insufficient. |
| **Mixed source, binary, map, trace or TIFF.** | Require one frozen source commit/build and one run identity to bind the binary, map, trace, crop, final TIFF and checker before reading the verdict (`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:56-63`; `experiments/M136-m8o-bar/clamped-m8o-preregistration.json:105-121`). |
| **A mutation that did not land.** | Anchor every plant on one exact full line, require exactly one occurrence, hash before/after, and hard-error otherwise. The existing verifier's `replace_unique_line` implements that discipline (`experiments/M136-m8o-bar/verifier_m136.py:4997-5008`). |
| **One-direction-only commissioning.** | Require both a degradation and an improvement. In the commissioned M136 fixture, Catmull hard step is `28/252` (`14` low, `14` high), clamped is `0/252`, widened-clamp sabotage is `28/252`, explicit plant is `2/252` (`1+1`), copy and clamped-copy are each `0/252`, and the independently supported bilinear null is `0/300` (`experiments/M136-m8o-bar/verifier-commission.json:186-230`; `experiments/M136-m8o-bar/verifier_m136.py:5260-5362`). The improvement mutation must make a known-red production-path case green; the reverse/widened mutation must restore red. |
| **M8-O rail deletion.** | Keep rails in `N`; project support through `[0,1]`; require correct-rail green and one-code-off-rail red in both directions (`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:134-225`). |
| **Whole-axis overclaim.** | A clean M8-R is not a clean M8 axis. Require exact M8-O zero and crop/reference identity zero in the same candidate evidence (`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:88-104`). |

**VERIFIED BY RUNNING — repaired verifier identity:** The present
`verifier_m136.py` has raw SHA-256
`EBC780597CCC72E48DC73A6FA72CD14329BAA806CDF066484595FD1A03F520FB`
and canonical SHA-256
`03E3BCD41FA01D161D6077994E042B0BB9B6DA73CCAE767CA59AFA28D6686C9C`.
The independently reproduced `PASS` commissioning report has SHA-256
`E60B699113D5896E735F85EA791C28747CFA6CCC57EF50BA17F9A3749CDF11E4`.

**INFERRED BY READING — single-read requirement satisfied:** `PinnedFile`
retains a Windows read handle with write sharing denied and hashes that file
object; bounded metadata is parsed from the captured bytes, while `PinnedNpy`,
`AcceptedTrace`, and TIFF decoding consume the same digest-checked handle
(`experiments/M136-m8o-bar/verifier_m136.py`, `PinnedFile`, `PinnedNpy`,
`AcceptedTrace`, and `load_tiff`). `verify_capture` processes one frame's four
CFA traces within one `ExitStack`, then closes mappings before handles. A
pathname replacement can therefore land without changing the bytes consumed
by the verifier, and an in-place writer cannot open the accepted file while it
is pinned. End-of-run path rehashing remains a persistent-mutation alarm rather
than the identity mechanism.

**VERIFIED BY RUNNING — commissioned attack:** Both JSON trust-direction
substitutions, a trace-header kernel `2`→`0` substitution, and a trace-body
`2`→`0` violation substitution landed at the pathname. Deliberately vulnerable
reopens saw every substitute; the verifier retained every accepted value and
restored every original digest. The equal-bytes recovery case reports exactly
`transient substitution did not change the bytes`, preserves the original
path/digest, and leaves no scratch; deleting either inequality guard makes that
control red
(`experiments/M136-m8o-bar/verifier-commission.json`,
`transient_json_substitution`, `transient_trace_header_substitution`, and
`transient_trace_body_substitution`).

**INFERRED BY READING — remaining boundary:** No target `verify --manifest`
campaign has run. M142 must replace its superseded `636d3f57` pins with the
identities above and regenerate the source/build/freeze chain before target
bytes are admissible. That is a campaign/provenance blocker, not an open
single-read defect.

**INFERRED BY READING — discrimination versus quality:** A destructive in-hull
operator can earn a truthful M8-R zero. That is not an artifact in M8-R; it is
outside M8-R's pass licence. To claim specifically that clamped Catmull-Rom
preserves Catmull detail, the verifier must additionally show unchanged bits
where the ordinary result is already in-hull and use the separate
detail/transfer controls. The scorecard explicitly keeps those controls because
clipping or attenuation can buy a hull result
(`docs/proposals/2026-09-sota-scorecard.md:1430-1443`, M8 known-defeat and
control paragraphs).

## 6. Does the `0870f785` M-FLATNULL trap apply?

**VERIFIED BY RUNNING:** `git hash-object docs/research/M-FLATNULL.md` and
`git rev-parse 0870f785:docs/research/M-FLATNULL.md` both returned blob
`f9eb49e7d8c48eff01decc754a7eee27343163d5`; the file read for this review is
the report committed by `0870f785`, not a later transcription.

**VERIFIED BY RUNNING — result:** I parsed its committed `results.json`. On the
clean six-second 256-pixel inset, old M8-O found `715,477` violations, of which
`699,932`, or `97.82732358971707%`, were the post-hoc class “encoded 65535 and
hull lower bound above one”
(`experiments/M-FLATNULL/results.json:283-315`). The planted USM arm moved the
inset rate from `4.333602019238783%` to `12.301308105446983%` and increased all
64 blocks, so the instrument was sensitive while the clean null still failed
(`experiments/M-FLATNULL/results.json:4504-4517`). Its registered verdict was
`NULL-MATERIAL`, not exact-zero
(`experiments/M-FLATNULL/results.json:4464-4469`).

**INFERRED BY READING — applies directly to M8-O v1.4:** Yes. M-FLATNULL shows
that a real clean null can fail the unprojected final-output hull mainly because
the output container saturates, while a sharpening plant can still drive the
statistic upward. That is sensitivity without specificity for invention. It is
the same representability mechanism that v1.5 fixes by transforming support
through the mandatory numeric path and final `[0,1]` projection while retaining
and reporting the rail population
(`docs/research/M-FLATNULL.md:29-53`;
`docs/research/M-FLATNULL.md:56-95`;
`docs/research/M-FLATNULL.md:160-190`;
`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:65-87`).

**INFERRED BY READING — does not refute M8-R:** The specific flat-null rail trap
cannot create an M8-R false positive because M8-R is observed before the
intermediate and final `u16` rails. Conversely, a clean final M8-O can be
manufactured by final clipping, which is why it cannot replace M8-R
(`docs/research/M-FLATNULL.md:124-155`;
`docs/proposals/2026-09-sota-scorecard.md:1430-1432`, M8 known-defeat
paragraph).

**INFERRED BY READING — general lesson still applies:** A checker that has gone
red under one plant may still measure the wrong construct. Future M8 evidence
must therefore prove both directions, preserve the population, and state the
narrow pass licence. For M8-R, exact same-support clamping is a genuine fix to
the measured invariant; for M8-O, representation projection is required to
avoid charging finite output range as invented data.

## 7. Evidence boundary

**COULD NOT VERIFY:** I did not inspect or execute anything under
`experiments/M142-m8o-execute/`; no M8-O v1.5 target count is certified by this
document.

**COULD NOT VERIFY:** I did not receive an M170 artifact. This document proves
what an exact same-support clamp would guarantee and defines the checks M170
must survive; it does not certify that M170 implemented or landed that clamp.

**COULD NOT VERIFY:** The historical denominators do not establish the
denominators of later scored quality captures or of a differently sized Crop
output. Those must be reconstructed from each registered run.

**INFERRED BY READING — final verifier ruling:** If M170 presents an exact
M134-style `4x4` clamp, unchanged support/validity, production-path binding and
complete denominator, M8-R zero is expected **by proof**, and a nonzero result
would diagnose an implementation or evidence mismatch. Even then, the M8 axis
cannot pass until independently verified M8-O v1.5 and crop/reference identity
also equal integer zero.
