# Phase-1 W1 preregistration

Status: **SEALED BEFORE CANDIDATE SCORING**  
Specification: `docs/proposals/2026-09-phase1-design.md` at `f5658e5d`  
Decision: whether one fixed global `k` clears the width, detail, and flat-power
bars on all three pilot captures. `NO_COMMON_K` is the required result if not.

At sealing, only synthetic commissioning data and one reference-frame preview
from each of the three pilot captures had been inspected. No candidate merge,
candidate `n_eff`, legacy/candidate ratio, or grid outcome had been produced.
No held-out W5 pixels were decoded or inspected.

## 1. Sealed inputs and complete ordered manifests

The authoritative complete manifest is
`results/preregistered-manifest.json`, SHA-256
`79b74a013e6598c985b6ad7bc969c732cf4189d8467eec3e13313ca23ab13b09`.
It records, in stable input order, **every RAW's relative name, byte count, and
SHA-256**, plus every crop/tile and transform. The gate rehashes every RAW and
refuses any mismatch.

The ordered brackets represented in that file are:

| key | exact read-only root | ordinals and ordered filenames | count |
|---|---|---|---:|
| `sw4` | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw4-cpl` | 000..054 = `DSC00015.ARW` .. `DSC00069.ARW`, inclusive lexical order | 55 |
| `coffee-bubbles` | `D:\personal\macro\coffee-bubbles` | 000..018 = `DSC00034.ARW` .. `DSC00052.ARW`, inclusive lexical order | 19 |
| `113MSDCF` | `D:\personal\macro\113MSDCF` | 000..062 = `DSC00001.ARW` .. `DSC00063.ARW`, inclusive lexical order | 63 |

The manifest's 137 individual hashes, rather than these range abbreviations,
are authoritative. Setup-2 `sw4`, `sw1`, `sw10`, `112MSDCF`, `coffee-bean`,
and `foam` are excluded and may not be opened by W1.

### Alignment provenance

The existing release executable was used only to create placement sidecars:
`strehl 0.0.0 (1ac2156015dd-dirty)`, binary SHA-256
`8f2ace3d6ffc39192b4b6ff1fddf72befaa8bb6475a87e2d4c79d5fe8679907`.
The executable's content hash, complete argv, sidecar metadata, and sidecar
hashes are also in the manifest.

| capture | command-specific worker count | sidecar SHA-256 |
|---|---:|---|
| `sw4` | 8 | `8bcab966eba33c8fb321a365e7cfc419fc7b454ab7992729aed3af4899286bd6` |
| `coffee-bubbles` | 4 | `d481b9e216f77ea0a2ba3d708e49ab617c146caedcccc92866945bdaf65ca894` |
| `113MSDCF` | 4 | `a5df650cce1224a7b6f54b5570b0bc1e643f1728b030d2496bd2bc13e462623e` |

The last two solves ran concurrently, so the total remained eight workers.
All frames are `placed`, all sidecars say `catmull-rom`, and placements are
pulled in the stored reference-to-frame direction without inversion.

## 2. Independent decode and geometry

- Decoder: rawpy 0.27.0 / LibRaw 0.21.4, `raw_image_visible`, no demosaic,
  white balance, gamma, auto-brightening, or Rust RAW code.
- Required CFA is rawpy `[[0,1],[3,2]]`; G1 is `(even,odd)` and G2
  `(odd,even)`. Shared green is `(G1+G2)/2`.
- LibRaw visible mosaic is 7028x4688, hence each green plane is 3514x2344.
  Sidecars were fitted on 3516x2344. The reference retains LibRaw's origin,
  evaluates placements about the sidecar centre `(1758,1172)`, and does not
  fabricate the two missing right-edge plane columns. Every sealed crop plus
  four-tap support is interior.
- Per-channel black metadata must be equal (observed 512 DN). Catmull-Rom
  float gathering occurs in sensor-code space; black is then subtracted and
  below-black undershoot is clipped to zero. Camera white 15360 is recorded;
  rawpy's 16383 container maximum is not substituted as camera white.
- W1 uses unity photometric gains. B3's scale law is the unresolved W4 arm,
  while W1 is specified as its prerequisite admission-only pilot. Applying an
  unadjudicated B3 law here would make W1 depend circularly on W4.
- The two merge arms consume the same in-memory aligned linear G1/G2 arrays.
  No Rust merge output, `strehl-core`, or experiment helper is imported.

`reference.py` reimplements the sidecar parser, pull, Catmull-Rom kernel,
noise model, pyramids, policy equations, reconstruction, hull, and metrics.
The gather is checked by a separately written scalar Keys-cubic evaluator and
an analytic ramp, rather than by another call through the vector gather.

## 3. Frozen crops, labels, and exclusions

Coordinates are `(x,y,w,h)` in reference quad-plane pixels. Each score crop is
surrounded by a 256-pixel halo, making a 1024x1024 work crop; this contains the
254-pixel seven-band dependency radius. Each listed tile is a 32x32 `(x,y)`
offset within its score crop. Tiles do not overlap within a label.

| capture | score crop |
|---|---|
| `sw4` | `(1500,916,512,512)` |
| `coffee-bubbles` | `(1450,700,512,512)` |
| `113MSDCF` | `(1500,900,512,512)` |

### `sw4`

- detail:
  `(48,45) (100,45) (152,45) (204,45) (256,45) (308,45) (360,45) (412,45);
   (48,97) (100,97) (152,97) (204,97) (256,97) (308,97) (360,97) (412,97);
   (48,149) (100,149) (152,149) (204,149) (256,149) (308,149) (360,149) (412,149);
   (48,201) (100,201) (152,201) (204,201) (256,201) (308,201) (360,201) (412,201)`
- flat:
  `(24,21) (76,21) (128,21) (180,21) (232,21) (284,21) (336,21) (388,21);
   (24,73) (76,73) (128,73) (180,73) (232,73) (284,73) (336,73) (388,73);
   (24,125) (76,125) (128,125) (180,125) (232,125) (284,125) (336,125) (388,125);
   (24,177) (76,177) (128,177) (180,177) (232,177) (284,177) (336,177) (388,177)`

Detail tiles straddle preregistered grid intersections; flat tiles sit inside
grid cells. No post-score saturation, texture, or outlier exclusion is allowed.

### `coffee-bubbles`

- detail:
  `(448,256) (352,128) (224,192) (224,288) (416,256) (192,256) (256,32) (32,32)
   (224,64) (160,192) (448,384) (192,384) (320,448) (448,352) (448,192) (320,480)
   (96,64) (288,224) (384,320) (288,96) (352,256) (96,320) (352,0) (192,64)
   (64,96) (352,224) (480,128) (352,288) (384,160) (160,64) (256,96) (192,224)`
- flat:
  `(352,352) (32,128) (64,384) (0,416) (32,384) (160,416) (128,416) (0,96)
   (0,288) (320,352) (32,192) (32,160) (0,352) (32,352) (32,320) (0,384)
   (384,32) (0,320) (96,384) (384,352) (0,128) (288,416) (32,288) (0,256)
   (128,384) (320,320) (32,256) (320,384) (64,192) (416,384) (288,288) (352,320)`

The reference preview was Gaussian-smoothed by sigma 2 only for siting: detail
tiles were the first 32 non-clipped high-gradient regular tiles (reference max
under 12000 black-subtracted DN), while flat tiles were the first 32
low-gradient dark regular tiles. That ranking is not rerun after sealing.

### `113MSDCF`

- detail:
  `(480,384) (448,480) (480,320) (448,384) (480,96) (448,416) (448,448) (480,256)
   (416,448) (448,352) (480,416) (0,224) (32,128) (0,256) (32,192) (480,288)
   (480,224) (416,320) (416,384) (416,416) (64,192) (480,352) (0,192) (416,352)
   (480,192) (32,0) (480,448) (448,64) (416,288) (96,160) (160,32) (192,384)`
- flat:
  `(224,128) (64,384) (64,352) (224,448) (352,32) (224,480) (128,320) (224,64)
   (96,352) (256,64) (224,416) (256,480) (352,0) (352,64) (128,352) (96,384)
   (320,32) (416,192) (128,224) (256,448) (160,288) (288,224) (32,416) (224,160)
   (96,416) (224,96) (320,0) (96,448) (320,384) (224,0) (256,128) (256,96)`

The same frozen preview rule selected natural branch detail and dark,
low-gradient defocused regions. There are no adaptive exclusions.

For width, each label is the union of its 32 tiles. Its binary mask is reduced
with the same Gaussian operator, and mean `n_eff` at every native band grid is
mask-weighted. Bands 0..6 are all scored for both labels and every capture.

## 4. Frozen topology, noise calibration, and equations

Seven Burt-Adelson bands are used. `reduce` is separable
`[1,4,6,4,1]/16` then even decimation; `expand` uses even
`[1,6,1]/8` and odd `[1,1]/2`, with replicated borders. Base coefficients are
arithmetic means. Reconstructed G1/G2 are clamped to their respective aligned
input min/max hulls.

At ISO `I`, `g=max(I,100)/436.8` DN/e and read noise is 4.20 e below ISO 400
or 1.2392 e otherwise. For shared green:

```text
a = g/2
b = (read_noise_e*g)^2/2
A(s) = (2/a) sqrt(max(a*max(s,0) + 3a^2/8 + b, 0))
v_A(s) = (a*max(s,0)+b)/(a*max(s,0)+3a^2/8+b)
```

`v_A` and linear variance `a*s+b` are propagated down Gaussian pyramids.

### Measured `beta` and `nu_eff`

A 512x512 deterministic unit-Gaussian field is independently Catmull-sampled
at every phase in `{0,1/8,...,7/8}^2`, with eight fit realizations per phase.
For each band, `beta=mean(L^2)` and `E=smooth5(L^2)` are measured on trimmed
interiors. The largest all-phase 95th absolute relative deviation gives the
coverage upper limit on `nu`; moment `2F^2/var(E)` is a second upper limit.
The raw fitted vector was:

```text
[9.686241744952936, 10.190096694231364, 9.291338354250149,
 8.734423750081067, 8.360377402498921, 5.691559808504721,
 0.728884361498442]
```

A separate safety-development seed was used before sealing to lower, never
raise, those limits. The frozen conservative vector is:

```text
nu_eff = [8.5, 9.0, 8.0, 7.5, 6.5, 2.5, 0.5]
```

Final commissioning uses four realizations at every phase from untouched seed
`0xE7719000`. It requires worst phase/band coverage >=0.93, pooled coverage for
each band in `[0.94,0.997]`, and frozen/fitted `nu` in `[0.40,1.00]`.
An additional Poisson-Gaussian null at ISO 100/500/1000 must cover >=0.90.
The analytic independence value 13.37469 is a planted defect and must
under-cover (<0.93 worst phase/band).

The full measured 8x8x7 `beta` table is written by commissioning. For each
real frame/ROI, actual source phases are evaluated every eight work-crop
pixels, the periodic table is bilinearly interpolated, and each band is
averaged. Thus `beta_i,b` changes with frame, transform, and ROI; no global
scalar replaces it.

### Legacy gate-4.5

For linear shared-green band `L_i,b` and Gaussian linear variance `V_i,b`:

```text
E = smooth5(L^2)
floor = 4.5 * beta_i,b * V_i,b
excess = max(E-floor,0)
r = excess / max(floor,1) / 64
p_b = min(2 * 1.4^(6-b), 8)
w = 0                         if excess=0
w = r^2                       if p_b=2
w = exp(clamp(p_b*ln(r),-80,80)) otherwise
```

Legacy `n_eff=(sum w)^2/sum(w^2)`. An all-zero coefficient uses unit weights,
an arithmetic-mean coefficient, and `n_eff=N`. The base is the arithmetic mean
and the final G1/G2 hull is retained.

### Candidate

```text
L_i = LaplacianBand(A_i)
E_i = smooth5(L_i^2)
F_i = beta_i,b * v_A,i,b
q_i = max(E_i-F_i,0)
sigma2_i = (2F_i^2 + 4F_i*q_i) / nu_eff_b
winner = largest finite E_i, lower stable ordinal on an exact tie
admit_i = winner OR E_w-E_i <= k*sqrt(sigma2_w+sigma2_i)
w_i = 1/F_i if admitted
n_eff = (sum w_i)^2/sum(w_i^2)
```

If winner `q_w=0`, every frame is admitted with unit weight. Non-finite
decisions or non-finite/non-positive used `F` fail; there is no epsilon.
The one shared-green weight applies to the separately decomposed linear G1
and G2 bands. Base and hull match legacy.

## 5. Fixed grid, metrics, intervals, and decision

The ordered grid is exactly `k=0.00,0.05,...,8.00`. Every value is run unchanged
on all captures. A value survives width only if every capture x band x label
satisfies:

```text
abs(mean_n_eff_candidate / mean_n_eff_legacy - 1) <= 0.05
```

For each survivor:

- **detail/MTF amplitude** is the square root of summed candidate/legacy
  phase-corrected G1xG2 cross-power. The known G1/G2 CFA displacement is removed
  in Fourier phase before taking real cross-power. Independent channel noise
  therefore has zero expected cross-power rather than earning detail credit.
- **flat power** is summed candidate/legacy power of shared-green output.
- Both use demeaned Hann-windowed 32x32 tiles and radial
  **0.10..0.25 cycles/output-pixel**, inclusive. Plane FFT frequency is divided
  by two. Any attempted frequency above 0.25 is
  `UNLICENSED_GT_0.25` and invalidates the run.
- A non-positive detail bootstrap numerator/denominator or flat denominator is
  an instrument failure, not a post-hoc exclusion.

Intervals are paired nonparametric spatial block bootstraps: resample the 32
fixed tiles with replacement, sum raw powers inside each replicate, form the
ratio (and square root for detail), and take percentiles 2.5/97.5 from 8192
PCG64 replicates. Base seed is `0x5A172026`; capture seeds add 0, 1009, and
2018 in manifest order. The same resamples are used for every `k`.

A capture passes if detail lower95 >=0.95 and flat upper95 <=0.90. A `k` passes
only if it first survives every width check and then all three captures pass
both bars. Select the smallest passing grid value. Report all contiguous
passing ranges. No interpolation, per-capture selection, metric/crop change,
or range extension is permitted.

If no value survives width, Pareto metrics are not used to rescue it.
`k=0.00` is preregistered solely as a negative-report sentinel so the requested
per-capture detail/flat table is still numeric; it cannot be selected unless it
independently passed the unchanged procedure.

`measure.py --gate` exits 0 only for a common selected `k`; it prints
`NO_COMMON_K` and exits 20 for the successful scientific halt. This follows
the brief's explicit distinct-code negative rule despite its earlier,
contradictory sentence that both exact-command programs exit 0.

## 6. Commissioning predicates

`reference.py --commission` must make each correct/null arm GREEN and each
planted defect RED:

1. hand `F/q/sigma2` vs a missing-`4Fq` plant;
2. lower-ordinal winner tie vs upper/encounter-order tie;
3. weighted Kish vs admission-count substitution;
4. below-floor unit mean vs inverse-`F` weighting;
5. known monotone admission boundary vs reversed inequality;
6. permutation-stable ordinal/reduction vs encounter-order tie;
7. consistently scaled generalized Anscombe (error <=2e-5) vs unscaled `b`;
8. analytic ramp plus independent scalar Keys gather vs inverted placement;
9. hand RGGB two-green extraction vs G2/blue swap;
10. constant pyramid vs planted step;
11. untouched correlated-band coverage vs analytic 13.37469 substitution;
12. untouched Poisson-Gaussian coverage vs planted 20-point undercoverage;
13. detail identity/noise null vs Gaussian-blur plant;
14. known 30% flat-power reduction vs known 20% inflation.

The commissioning artifact hashes both programs, this preregistration, the
complete manifest, and every sidecar. `measure.py` refuses stale hashes and
rehashes every RAW before scoring.

At sealing (before this file itself existed), program hashes were:

- `reference.py`: `b5c831e93fc572606cad21b5b1d49839e2a838875197d0e938e2e6a412f92961`
- `measure.py`: `d964fac2d0edaacf7cc08ef7e8d667b4990b7a8e917f269d50ff2aa48e4227e9`

The exact commissioning command hashes the final files again; those runtime
hashes, rather than the informational pre-document values above, gate scoring.
