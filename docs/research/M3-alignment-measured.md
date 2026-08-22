# M3 — Alignment, measured

Every number here came from a command that was run. Harness:
`<session>/files/scratch/drift-bench`, a throwaway crate outside the repo.
Subject: `C:\dev\macro\test\109MSDCF`, 22 frames, in-camera focus bracketing,
A7C II + SEL100M28GM. All work at CFA plane resolution, 3516 x 2344, on the
green luma `(G1 + G2) / 2`.

This was the largest unpinned term in the budget. It is now pinned, and three
architectural questions that §4.1 had left open are answered.

---

## 0. The estimator, and why it can be believed

Coarse-to-fine tiled normalised cross-correlation against a **fixed reference
frame**, with parabolic sub-pixel refinement, fitting a 4-parameter similarity
(isotropic scale, rotation, translation) by least squares over the tile
displacement field, with one MAD-based outlier rejection pass.

- Coarse: 8x-decimated plane, 32 px tiles, 8x6 grid, +/-10 px search
  (= +/-80 plane px, against a worst-case real drift of 39 px).
- Fine: full plane resolution, 128 px tiles, 12x8 grid, +/-6 px around the
  coarse prediction.

**VERIFIED — the estimator recovers known warps.** Frame 0 was resampled by four
similarity transforms with known parameters and re-estimated:

| Case | scale error | translation error | residual |
| --- | --- | --- | --- |
| pure translation (+3.7, -2.4 px) | 1e-6 | 0.151 px | 0.194 px |
| scale only, -1.00% | 2.2e-5 | 0.019 px | 0.196 px |
| scale -0.512% + translation + rotation | 2.2e-5 | 0.020 px | 0.190 px |
| scale only, -0.05% | 1.3e-5 | 0.008 px | 0.165 px |

Worst scale error **2.23e-5**, which is **0.047 px at the plane corner**
(radius 2113 px). Every effect claimed below is larger than that.

**MEASURED — the tile-noise floor is 0.19 px.** On synthetic data, where the
ground truth *is* a similarity, the residual after fitting is 0.19 px. That is
what the estimator contributes and nothing else. It is the yardstick for §2.

**VERIFIED — transform composition is correct.** `compose()` of 21 identical
-0.1% scale steps reproduces the closed form `(1-0.001)^21 - 1` to 1.7e-9,
which is f32 storage precision.

---

## 1. Cost: 13-16 ms per frame

**MEASURED.**

| Stage | Per frame | 22 frames | 60-frame stack |
| --- | --- | --- | --- |
| Decode + green plane extraction (warm) | 26.3 ms | 578 ms | 1.58 s |
| Alignment estimate | 13.2 - 16.3 ms | 278 - 341 ms | **0.78 - 0.96 s** |

Scalar Rust, no SIMD, no GPU, rayon across 32 threads. Every pair is
independent, so this is a pure `par_iter` with no reduction.

Against the ~0.5 s the corrected synthesis budgeted, and the 5.0 s the discarded
chained design implied: the corrected budget was the right order and the
discarded one was not. Alignment is **~6% of a 15 s budget**, and this is an
upper bound — it is the unoptimised version.

There is no separate warp cost. Gather-at-consumption means the transform is
applied inside whichever kernel reads the pixel; nothing is resampled into a
buffer.

---

## 2. A 4-parameter similarity is the whole story

**MEASURED.** Fitting progressively richer motion models to the *same* tile
displacements:

| Model | Parameters | Residual, k=1 | Residual, k=21 |
| --- | --- | --- | --- |
| similarity | 4 | 0.703 px | 1.330 px |
| affine | 6 | 0.693 px | 1.329 px |
| quadratic | 12 | 0.661 px | 1.274 px |

Tripling the parameter count buys **at most 6%**. The same holds on the
unfiltered tile set — 1.277 / 1.267 / 1.241 px at k=1 — which matters, because
the outlier rejection uses similarity residuals and judging the ladder only on
the survivors would be circular. It was checked both ways and the answer does
not change.

Affine strictly contains similarity, so its residual can never be larger. An
early version of this test reported affine residuals **11x worse** than
similarity, which is impossible; the cause was forcing x and y to share one
coefficient vector. The nesting property is what caught it.

**DERIVED — this closes the affine-vs-homography question.** §4.1 flagged
"affine ~ homography" as an n=1 artifact. It is not an artifact, and the true
statement is stronger: **even affine is more than is needed.** Similarity is
sufficient, and the two extra affine parameters are unnecessary.

**ARGUED — the mechanism says this generalises.** The camera does not move; only
focus does. The image-space effect is magnification about a fixed point, which
is exactly a similarity. It follows for *any* in-camera focus bracket, not just
this stack. **It does not follow for a rail**, which translates the camera and
produces genuine parallax. Rail data must never be run through this model — a
further reason the `CaptureMode` seam stays.

**MEASURED — there is no rotation.** `|r| <= 1.0e-4` across all 21 frames,
median ~1e-5, i.e. **under 0.21 px at the plane corner**. Consistent with a
camera that does not move. The rotation parameter is retained anyway: it costs
nothing to fit and it is the thing that would catch tripod flex.

### 2.1 What the residual is not

The residual is 0.56-1.33 px against a 0.19 px estimator floor — 3 to 7x — and
richer global geometry does not reduce it. So it is **neither estimator noise
nor global model error**.

**UNVERIFIED — what it is.** Two candidates, not yet separated:

1. **Depth-dependent magnification.** Refocusing moves the lens, and the
   image-space scale factor is not identical for objects at different
   distances. That is a motion field that varies with depth, which no global
   polynomial in image coordinates can express.
2. **Blur-induced correlation bias.** A tile sharp in the reference and
   defocused in the moving frame can shift its correlation peak. The residual
   does grow with frame separation (0.70 px at k=1, 1.33 px at k=21), which fits
   this; adjacent pairs, where blur differs least, give 0.446 px, which also
   fits it.

Both predict growth with separation, so the trend does not discriminate. **The
experiment that does:** correlate the per-tile residual against the skeleton's
winner-index map. That map is a proxy depth map. If the residual is structured
by depth it is hypothesis 1; if it is structured by defocus magnitude alone it
is hypothesis 2. The data for this exists as soon as the skeleton runs.

This matters because ~1 px of unmodelled motion is the same scale as the detail
the merge is trying to preserve.

---

## 3. Never chain. Measured, not argued.

**MEASURED.** Two ways to reach frame 21 from frame 0:

| | scale g | tx | ty |
| --- | --- | --- | --- |
| Direct, 0 -> 21 | -0.018353 | -0.205 | -0.773 |
| Chained, 21 composed adjacent fits | -0.012443 | +0.463 | -0.655 |

**Chaining error: 12.5 px at the plane corner — 25 px at sensor resolution.**
Translation error 0.68 px.

Chaining underestimates total drift by **32%**, and the individual adjacent fits
look excellent while doing it (mean residual 0.446 px, *better* than the direct
fits, because adjacent frames differ least in blur).

**DERIVED — the mechanism is pixel locking, and it is worse than a random walk.**
Parabolic sub-pixel refinement is biased toward integer displacements. That bias
is roughly constant in absolute terms, so its *relative* size depends entirely on
how large the displacement is:

- adjacent frames drift ~1.9 px at the corner, so a ~0.1 px bias is ~5% — and it
  has the same sign every time, so 21 steps compound it coherently;
- direct-to-reference drifts up to 39 px at the corner, so the same bias is
  ~0.25% and is negligible.

This is a **systematic** error, not a random walk. It does not average out with
more frames; it gets worse. The synthesis discarded chaining on a random-walk
argument, which reached the right answer for a weaker reason than the real one.

**Consequence.** Align every frame against a fixed reference. Never against its
predecessor. This is also the faster option — all N alignments are independent,
so they parallelise perfectly, whereas a chain is serial by construction.

---

## 4. Do not model drift as a function of frame index

**MEASURED.** Scale drift over the stack, fitted per frame:

- total over 21 frames: **-1.835%**
- mean rate: -9.364e-4 per frame
- straight line through the origin: residual 2.69e-4 = **0.57 px** at the corner
- adding a quadratic term: residual 2.38e-4 = 0.50 px, a 12% improvement

**DERIVED — per-fit precision on `g` is ~7.4e-5**, i.e. 0.16 px at the corner
(0.7 px residual over ~60 tiles at RMS radius ~1220 px). So the departure from
linearity is ~3.6 sigma: **real, but modest.**

The important part is not which polynomial wins. It is that **no low-order
polynomial in frame index reaches the precision a direct per-frame fit already
has, for free.** The straight line is 3.6x worse than just measuring each frame.

So: no global drift model. Fit each frame independently against the reference,
coarse-to-fine. The coarse stage exists only to get within capture range, not to
supply accuracy.

**This corrects the synthesis.** §3.3 said to replace chaining with "seed every
frame from a global model". Killing the chain was right (§3 above). Fitting a
global model in `k` was not — it is less accurate than the per-frame fit it was
meant to seed, and it is unnecessary, because an 8x-decimated coarse pass gives
capture range on its own.

**ARGUED — why it is not linear.** In-camera bracketing steps focus by a constant
amount in the lens's own units. Magnification is hyperbolic in focus distance, so
equal focus steps are not equal magnification steps. The measured per-frame
increment does vary systematically, from -1357e-6 near the front of the stack to
-625e-6 at the back.

---

## 5. The scale centre is the principal point

**MEASURED.** A scale centre offset `o` from the plane centre appears as
translation `-g*o`. Regressing the fitted translation against the fitted scale
over all 21 frames:

**(-11, -56) plane px = (-22, -113) px at sensor resolution.**

The prior corpus claimed **(-176, -338)**. That is refuted: 8x too far in x and
3x too far in y. §4.1 called it "subject depth leaking into a geometric
parameter" and ruled it an artifact. Confirmed.

-113 px is 2.4% of sensor height, which is a plausible real principal-point
offset. Regularise toward the image centre with a tight prior, as §4.1 said, and
do not bake the corpus's number into anything.

---

## 6. What this changes

| Decision | Before | Now |
| --- | --- | --- |
| Alignment cost | ~0.5 s estimated | **0.78-0.96 s measured**, unoptimised |
| Geometry model | affine, homography an open question | **similarity, 4 params**; affine and quadratic buy <=6% |
| Rotation | assumed present | **absent**, <=0.21 px; keep the parameter as a guard |
| Chained alignment | rejected by argument | **rejected by measurement**, 25 px error at sensor |
| Global drift model in `k` | prescribed by §3.3 | **dropped**; per-frame direct fit is 3.6x better and free |
| Scale centre | corpus said (-176, -338) | **(-22, -113)**, near the principal point |
| Residual 0.6-1.3 px | unknown | **not noise, not global geometry**; cause still open |

## 7. Caveats

- **n=1.** One stack, one subject, one body, one lens. The similarity result has
  a mechanism behind it that predicts generality; the specific drift rate and
  scale centre do not, and must stay runtime-fitted.
- Sub-pixel refinement is a plain parabola fit and exhibits pixel locking. That
  is what §3 measures, and a better estimator would shrink but not remove it.
  Direct-to-reference alignment is insensitive to it either way.
- Fitting only. No merge, no warp, no output — this measures the cost of
  *deciding* the transform.
- Green luma only, at CFA plane resolution. A full-resolution or per-plane
  aligner would cost more.
