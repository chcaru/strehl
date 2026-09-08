# Factor-eight representation: compact source proposal

2026-09-07. **SOURCE ONLY / UNVERIFIED.** This proposes the next direct-pair representation arm. No numerical import, control, image decode or registration has run. Preserve direct-pair-1 and all its sources/results. The saved native 23 outcomes are the baseline; the prospective arm repeats the same literal 23 directions on the same nine admitted TIFFs. No graph solve, overlap admission or quality claim is authorized by this proposal.

## One changed representation and exact native gauge

The proposed [factor-eight-prototype.py](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/factor-eight-prototype.py) takes dependency objects from the future pinned runner; it imports no image/numerical subject. Its only representation change is a uniform nonoverlapping 8×8 RGB average, rounded once to nearest-even u16. Explicit uint32 block sums cannot overflow: 64×65535=4,194,240. This defines AREA8 independently of an unspecified resize library's rounding default. Review must accept this exact choice before implementation freeze; it is not yet a released API.

The real 7032×4688 input becomes 879×586 RGB. Apply the unchanged frozen registration-u8 projection/stretch and SIFT extraction to this RGB. Do not average a previously stretched u8 or change the ProPhoto-weight coefficients, feature cap, descriptor ratio, hypothesis model, radii or RMS bar. This intentionally tests the existing CameraLinear-proxy representation at a coarser spatial scale; it does not fix or validate a colorimetric interpretation.

A small pixel centre corresponds to the mean of native centres 8j..8j+7, namely `8j+3.5`. Therefore lift each actual detector coordinate **before matching, hash-split generation and fitting**:

```text
q_native = 8*q_small + 896
896 = 3.5*256
```

The original 2-pixel inlier radius, ≥12 and at-least-half counts, and 1-pixel held-out RMS remain **native** values. They are effectively 0.25 and 0.125 small pixels, respectively; no tolerance scales up with the representation. Q8 quantization becomes 1/32 native pixel. Detector keys/descriptor ordering remain in their actual coarse gauge, recorded as such; the positive common affine lift preserves their coordinate tie ordering. The matcher consumes the lifted coordinates, so match hashes and calibration/holdout assignments may change. That is part of this representation arm, not a null or a claim of identical populations.

Use the existing authenticated same-byte TIFF decoder and parent Job boundary. Keep one native RGB alive only through AREA8; release it before SIFT. Retain small feature objects and scalar receipts, not nine RGBs. Exact average sums and coarse RGB are small; this is no promise about actual process memory. Preserve the 8 GiB committed-memory limit and snapshot writes 0, plus all carried old resource charges. No native TIFF is rewritten.

## Powered positive before any real input

Use the existing 384×288 positive fixture RGB from the held direct-pair fixture population, selected by its actual frozen FileRef. Decode only that private fixture, repeat each RGB pixel exactly 8×8 in memory to create a 3072×2304 reference, and make the source by exact native `np.rot90(k=1)` followed by a contiguous copy. This is an integer-grid permutation, not an interpolated warp. Source dimensions are 2304×3072. AREA8 must reproduce the original fixture and its exact 90° rotation byte-for-byte.

The independent source→reference native-centre oracle is:

```text
x_reference = 3071 - y_source
y_reference = x_source
(a,b,tx,ty)_Q32 = (0, 2^32, 3071*2^32, 0)
```

Require the **actual** coarse-detector/lifted-matcher registration to return under the unchanged native 2/1-pixel limits, and its map to agree with the literal oracle within 1 native pixel at all four source-image corner centres. Evaluate squared errors with Fraction arithmetic in the separate oracle. The plant defines the mapping over the full rectangle, so this corner oracle does not infer real-image accuracy from a small support region. SIFT's rotation/localization behavior at these tight native limits is unmeasured. If this positive refuses or fails its coordinate oracle, preserve that outcome and stop before all nine real decodes; do not widen the tolerance, pick another fixture or reclassify the failure as harmless.

Seven proposed additive groups, all persisted before their assertion:

1. `area8-half-ties`: six 8×8 blocks with exact channel sums 31,32,33,95,96,97 yield 0,0,1,1,2,2; an all-65535 block stays65535. Generate each block from quotient/remainder integer values. This exercises the actual average, including both half-tie parities and neighbors.
2. `repeated-block-null`: actual AREA8 of the repeated fixture equals original u16 bytes; actual AREA8 of its native rotation equals the exact coarse rotation. Record actual SHA256s.
3. `native-rotation-positive`: the actual returned map and native calibration/holdout evidence pass the unchanged registrar and the literal corner oracle.
4. `native-two-pixel-map-destroyer`: add exactly 2×2^32 to the actual returned `tx`; require the same corner oracle to reject that mutated result. This defect is only 0.25 coarse pixel. Retain the actual squared errors; no assertion can pass merely because the mutated value differs.
5. `centre-offset-destroyer`: use the same actual coarse feature objects/descriptors but call the helper with `omit_centre=True` on both endpoints, then the actual unchanged matcher/fitter. Require a returned finite map which fails the correct native corner oracle; an unrelated exception is not powered evidence. For the exact rotation, omitting +896 yields `tx=3064` instead of3071, a 7-native-pixel defect. A pure translation plant would not expose this missing shared offset.
6. `native-rotation-restored`: restore the ordinary lift and repeat the actual positive call; require its canonical returned signature and corner errors to equal baseline exactly.
7. `rotation-observer-null`: off/count/placebo calls on this same restored pair must give byte-identical canonical return signatures, while count records actual matched coordinates. Keep actual hashes, not just an equality boolean.

This is five new matcher calls (positive, active missing-centre, restored, off, placebo), two feature extractions reused across the calls, and no added product TIFF. The 2-pixel map fault and integer average checks do not call the matcher. The original seven private direct-pair controls remain required under the shared source snapshot; do not replace them with these new checks. The future small runner delta must fix total counts before its command release. Keep one shared control/real-stage budget and preserve partial failed controls.

## Saved support and comparison

Record both coarse and lifted native coordinate arrays with the actual coarse RGB hash and exact AREA8 method ID. Keep the same 23 source/reference directions and original indices; matching reference remains local5/original65, while any later merge placement gauge would be local4/original52. Compare each new pair against its exact cached native FileRef; the old5→8 refusal is historical evidence, not a requirement that an intentionally changed representation reproduce it.

Before any interpretation of a returned pair, save raw descriptor-match count, exact unique reference/source/joint-coordinate groups, repeated endpoints and their calibration/holdout membership, and both endpoint spatial extents. The prototype's `site_evidence` only describes these; it must not filter matches, alter the digest split or silently mint “independent locations.” Empty exact intersections do not prove spatial independence. In this first arm these observations are **descriptive**, not a newly invented acceptance threshold. A returned fit with duplicate or narrow-region support remains subject to that explicit limitation, even if its frozen scalar checks pass. Do not call an accepted descriptor count whole-frame coverage or treat a connected diagnostic graph as a placement solution.

The later real arm is eligible only after all original and additive controls pass. Save all 23 outcomes and operational failures without search/retry. The scientific question is whether this single representation supplies supported, spatially described direct fits at the original native tolerances. A positive may justify a separately reviewed placement experiment; it does not prove cross-focus physical truth or establish a new standard for the 0.1-pixel product-output map oracle. A negative selects further support research, not looser thresholds.
