# M-COVER-BORDER preregistration

## Question

Why does `--cover crop` retain a border-level error hundreds of plane pixels
inward while `--cover scale` clears the registered 0.1% threshold at the
minimum tested inset, even though Crop performs no coverage rescale?

This lane diagnoses only. It will not edit Rust.

## Prior evidence and source pin

The required prior evidence was read before these predicates were written:

- `docs/research/cover-default.md`, including its admitted `109MSDCF` result:
  Crop peaks at `+2.6106%`, has a smallest evidenced safe inset of 256 px,
  and retains 64.6047% of the original plane after that inset; Scale is within
  threshold from the registered 8 px floor.
- `docs/research/BUILD-CROP.md` section 10, which previously proposed
  black-fill boundary transport through the pyramid and reported a 2/4/7-band
  reach ladder. The present work is an independent replication and a more
  explicit support/coverage audit, not a blind discovery claim.

The pixel-producing executable is the COVER-frozen binary:

`D:\strehl-out\cover-default\target\release\strehl.exe`

It identifies source commit
`4e5278870a5e6ff6e0da38762f716e5291508c16`. Existing b2/b7 files will be
accepted only if their SHA-256 values match the hashes in
`cover-default.md` section 5.1.

## Data and holdout discipline

Only `D:\personal\macro\109MSDCF` will be used. COVER already burned this stack
for this question. No scorecard holdout will be opened or measured.
`D:\personal\macro` remains strictly read-only. New render output goes under
`D:\strehl-out\M-COVER-BORDER`; logs and small derived results go only under
this experiment directory.

The exact sidecar is
`experiments\M-PHASE0-SPLIT\out\real-109\109-warpmap.txt`, accepted only at
SHA-256
`C29CAB9C6F944F4D03C4402998E54AAD4D4221CC450AC4BEF42A453DE848434D`.

## Frozen hypotheses

### H1 — no production 256 px window

Search the pixel-producing path at the frozen source commit:

- `crates/strehl-cli/src/align_cmd.rs`
- `crates/strehl-cli/src/merge_cmd.rs`
- `crates/strehl-core/src/pyramid.rs`
- `crates/strehl-core/src/align.rs`
- `crates/strehl-core/src/photometric.rs`

**Literal-window mechanism:** accepted only if an operational 256 px radius,
128 px half-window, tile, halo, gate, or neighbourhood lies on the Crop
warp/pyramid/write path.

**Pyramid-support mechanism:** supported if no such operational literal exists
and the relevant scale-setting constants are instead the five-tap radius-2
kernel and the seven dyadic bands. Mentions in comments, tests, reporting bins,
unrelated buffers, and numeric examples do not count as operational literals.

The existing COVER audit's `PROFILE_EDGES` includes 256 and refuses candidates
below 8. Therefore its reported 256 and 8 are *evidenced bins*, not assumed
exact physical cutoffs. This lane will also report an 8 px-bin estimate.

### H2 — dyadic pyramid transport

The intervention changes only `--pyramid-bands` on 109 Crop. Existing b2 and
b7 renders are reused; one fresh b4 render is made with the frozen executable,
same sidecar, Catmull-Rom, full-resolution gather on, defect correction off,
lateral CA off, and at most six Rayon threads.

For each b in `{2,4,7}`, compare green against b2 after normalising by the
mean ratio at distance at least 768 px. In 8 px annuli, define `reach_b` as the
smallest candidate at least 8 px for which every farther annulus is within
`|effect| <= 0.001`. For b2, the self-comparison defines the detector floor of
8 px.

Pass predicates:

1. `reach_2 <= reach_4 <= reach_7`.
2. Regressing `log2(reach_b)` on `b` gives slope in `[0.75, 1.25]` and
   `R^2 >= 0.90`.
3. `reach_7 / reach_2 >= 16`.
4. The outer peak magnitude need not grow monotonically; the claimed lever is
   reach, not amplitude.

The prior-art point prediction is 8, 32, and 256 px. It is recorded openly and
will be marked replicated or not replicated.

### H3 — coverage count is not falling inside the emitted Crop

Parse the sidecar's serialized f64 bit patterns. For the COVER rectangle
`(x=23, y=16, width=3470, height=2312)`, transform all four rectangle corners
through every placed similarity.

Because a similarity is affine and the source support box is convex, all four
corners inside the support box proves every point of the rectangle is inside.
The predicate is strict: all 22 placed frames must cover the complete emitted
rectangle at the production 3 px conservative margin. Also evaluate the exact
full-resolution Catmull-Rom site bounds (`0.75 <= sx <= width-1.25`, likewise
y) for all four CFA site offsets.

If this passes, the contribution count in every emitted Crop pixel is exactly
22. Coverage falloff may create the exterior step, but it cannot itself match a
256 px inward count profile.

### H4 — black fill plus cross-band mixing is sufficient

Implement the production one-dimensional forms of the five-tap binomial
`reduce` and the documented even/odd `expand`, then build/collapse Laplacian
pyramids.

Checks:

1. A pyramid whose levels all come from one signal must reconstruct that signal
   to max absolute error `<= 1e-6` (operator null).
2. Mix levels from a bright signal with a black exterior and a continuous
   version of the same signal. A boundary-local error on the valid bright side
   must appear when different bands/base come from different inputs (planted
   cross-band defect).
3. Replacing the black exterior with continuous extension must reduce peak
   valid-side error by at least 95% (planted improvement).
4. Restoring the black exterior must restore the defect within `1e-6` relative
   error.
5. Its threshold reach must increase monotonically over 2/4/7 bands, with
   log2-reach slope in `[0.5, 1.5]`.

This synthetic arm establishes sufficiency and scale law, not the real
artifact's exact amplitude. The real b2/b4/b7 intervention identifies the
production mechanism.

### H5 — Scale removes the source; it does not smear a conserved defect

Two discriminators are frozen:

1. Geometry: compose the COVER `S_k` with every placement and require every
   full-plane corner to clear the same 3 px margin. If so, Scale supplies no
   uncovered/black samples to the pyramid.
2. Measurement: on the existing Scale b7/b2 pair, the maximum registered
   annular effect through 256 px must be below 20% of Crop's, and Scale's
   positive boundary residual mass through 256 px must be below 20% of Crop's.

If both pass, “Scale smears the same contamination below threshold” is
rejected: the causal step is absent before pyramid construction and the
measured residual mass is not conserved. If either fails, the report will not
claim source removal.

### H6 — photometric and resampler alternatives

- Photometric normalisation is rejected structurally only if the frozen
  `run_pyramid` path neither fits nor applies `photometric.rs` gains and its
  banner says so.
- Resampler support is rejected as the 256 px transport only if the same
  Catmull-Rom gather and same Crop geometry are used in b2/b4/b7 while reach
  follows band count. Its 2 px kernel support and the 3 px cover margin may
  explain only the immediate edge floor.

## Instrument commissioning

The border detector itself will be commissioned before real files are scored:

- **GREEN null:** identical 1024x1024 positive images; peak error `<= 1e-12`,
  safe inset 8.
- **RED defect:** a planted `+2.0%` outer 64 px ring; recovered peak within
  `1e-6` of 0.020 and safe inset exactly 64.
- **Improvement:** reduce the plant to `+0.05%`; recovered peak within `1e-6`
  of 0.0005, safe inset 8, and at least 95% reduction.
- **Restoration:** reapply `+2.0%`; the RED readings must return within `1e-12`.

No real result is admissible unless every commissioning predicate passes.

## Defect/necessity and fix prediction

The artifact will be called a defect only if H2, H3, and H4 pass: real dyadic
reach, complete data throughout the emitted rectangle, and causal
black-step/cross-band transport.

The proposed fix to evaluate in writing is to make the Crop rectangle the
pyramid's support *before* decomposition, not only an address window after
collapse: all per-frame planes supplied to `BandMerge` must contain only the
common covered rectangle (or an exactly equivalent shared continuous boundary
extension), while the warp itself remains defined on the original reference
coordinates. No missing/filled sample may be emitted.

If the black-step mechanism is right, the point prediction on admitted 109 is
the Scale/control floor, `<= 8 px`, not 256 px. An 8 px inset would retain
`(3470-16)*(2312-16)/(3516*2344)` of the original plane; the exact percentage
will be reported. Passing the 80% gate is predicted. No general safe inset will
be claimed from the ruler profile, whose specificity already failed in COVER.
