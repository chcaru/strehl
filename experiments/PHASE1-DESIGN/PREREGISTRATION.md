# Phase-1 W1 preregistration — revised development ledger

**State:** SEALED BEFORE ANY `flat-on-ruler-cpl` candidate merge, `n_eff`
width, Pareto ratio, or `k` outcome.

**Design:** `fe111781488ce950372fd17e45ab1d402dcc0e34`.

**Experiment epoch:** `w1-fe111781`.

This document and `results/preregistered-manifest.json` are one seal. The
manifest SHA-256 is `2a5f7f64942ec6044d59a5bfd561d3849522d3688cf0691256adb113ba97cc18`; `reference.py` must contain the
same digest and `measure.py --gate` refuses any mismatch.

## Mandatory leakage disclosure

The superseded design-`f5658e5d` attempt exposed real candidate outcomes from
calibration-grid-1 sw4 before the halt: all 161 width-grid readings and
detail/flat readings at its old `k=0.00` negative-report sentinel. Grid-1 sw4
is consumed and is not untouched holdout evidence. The old manifest, sidecar,
commissioning, widths, and gate are retained only under
`quarantine/f5658e5d-grid-sw4-exposed/`; active programs contain no path to
that directory.

Coffee-bubbles and 113MSDCF were also scored in the superseded development
attempt. Their score origins, 32 detail sites, 32 flat sites, transform
sidecars, metric, grid, and tie-break are carried forward unchanged, so those
outcomes cannot re-site or retune them. The repaired affine-beta, halo,
four-CFA-plane, frequency-unit, and decoder-provenance instruments address
independent verifier findings, not a criterion miss.

No candidate outcome exists for flat-on-ruler at this seal.

## Allowed and sealed data

Exactly these roots may be inventoried, decoded, or scored:

| key | read-only root | frames | sidecar reference | score crop `(x,y,w,h)`, CFA-plane px | work crop |
|---|---|---:|---:|---|---|
| flat-on-ruler | `D:\personal\macro\flat-on-ruler-cpl` | 79 | 39 | `(1500,900,512,512)` | `(988,388,1536,1536)` |
| coffee-bubbles | `D:\personal\macro\coffee-bubbles` | 19 | 9 | `(1450,700,512,512)` | `(938,188,1536,1536)` |
| 113MSDCF | `D:\personal\macro\113MSDCF` | 63 | 31 | `(1500,900,512,512)` | `(988,388,1536,1536)` |

The manifest freezes every ordered relative path, byte count, and SHA-256.
The allowlist is asserted before recursive enumeration.

Sealed from W1: every directory under
`requests\30-calibration-grid`, `coffee-bean`, `foam`, `119MSDCF`,
`bee-1-cpl`, and `112MSDCF`. Captures, crops, labels, exclusions, metrics,
grid, and tie-breaks cannot change after this seal.

## Alignment and input-only sites

All 161 frames must be `placed`; any refused/missing/extra/reordered frame is
an instrument error. The three Catmull-Rom text sidecars are hashed in the
manifest together with the alignment executable, version, exact argv, and
sidecar metadata. Sidecar geometry is carried per capture: flat-on-ruler is
`3520x2344`; the others are `3516x2344`. LibRaw's visible CFA planes are
`3514x2344`; both decoders share the active-area origin, so extra sidecar
columns extend only the right edge and do not shift a coordinate.

Flat-on-ruler sites were frozen from input-only reference `DSC00040.ARW`
before candidate scoring. On the non-overlapping 32-pixel lattice, detail is
the 32 greatest positive G1×G2 coherent powers; flat is the 32 smallest
shared-green powers among remaining tiles with mean signal at least 1200 DN
above black (excluding black ruler markings). The exact 64 coordinates,
readings, preview, and overlay are hashed in the manifest. It is coherent
detail, not MTF. Coffee and 113 use the unchanged pre-outcome coordinate lists
from commit `e64fca59`.

The flat sidecar reported 79/79 placement but a pre-score held-out corner error
of 10.8486 plane px, above the aligner's advisory 4-px `T_usable`. The W1 brief
sets an all-frame-placement rule but no alignment-error exclusion. This
warning is frozen here; it cannot trigger a post-outcome replacement.

## Decoder and independence boundary

`reference.py` imports no Strehl library and never consumes Rust merge output.
It copies `rawpy.raw_image_visible` while the LibRaw context is live, requires
CFA pattern `[[0,1],[3,2]]`, and extracts independent R/G1/G2/B arrays.
Runtime provenance is rawpy 0.27.0 with LibRaw 0.22.1; exact runtime strings
and the binding path are recorded at commissioning. Per-channel black must be
equal (512 DN on scouted frames). Catmull-Rom is independently implemented in
NumPy, then black is subtracted and undershoot clamped to physical zero.
Candidate and legacy arms consume the same aligned arrays with unity
photometric gain.

The crop commissioner checks the vector pull against both an analytic affine
ramp and a separately written scalar Keys-cubic oracle on nonlinear data.
A translation-only planted pull must go RED. No production focus, pyramid,
merge, or output helper is imported.

## Frozen operators

Seven Laplacian bands use separable `[1,4,6,4,1]/16`, nearest replicated
boundaries, reduce-by-two, and the corresponding expand operator in
`reference.py`. `HALO=512`; the band-6-plus-`smooth5` dependency radius is 510
input pixels. A larger-context null must be bit-identical at the score crop,
while the old 256 halo must go RED.

For shared green `s=(G1+G2)/2`, ISO supplies the frozen M10 model:

```text
g = max(ISO,100)/436.8
RN = 4.20 e- below ISO 400, otherwise 1.2392 e-
a = g/2
b = (RN*g)^2/2
A(s;a,b) = (2/a) sqrt(max(a*max(s,0) + 3a^2/8 + b, 0))
v_A = (a*max(s,0)+b)/(a*max(s,0)+3a^2/8+b)
```

`beta_i,b` is commissioned from deterministic unit-white stochastic traces
pulled through every actual sidecar matrix, translation, score origin, and
sidecar centre. Bands 0–3 use each frame's direct 512-core trace; bands 4–6
use a preregistered log-linear fit across the actual transform features to
suppress finite 32/16/8-pixel trace noise. Validation uses disjoint seeds over
all 161 actual affine lattices. No RAW intensity enters calibration.

The measured validation maxima licensed the conservative downward-rounded:

```text
nu_eff = [8.0, 10.0, 9.5, 9.0, 9.0, 9.0, 7.5]
```

Commissioning records raw/fitted beta for every frame/band, held-out coverage,
the measured unrounded `nu_eff`, and the phase/affine-omission plant.
`NU_SMOOTH=13.37469` is only a planted analytic value and is never relabelled
as measured.

## Candidate equations

For each frame `i`, band, and pixel:

```text
E_i      = smooth5(LaplacianBand(A_i)^2)
F_i      = beta_i,b * v_A,i,b
q_i      = max(E_i-F_i,0)
sigma2_i = (2F_i^2+4F_i*q_i)/nu_eff_b
winner   = finite argmax(E_i), lower original frame ordinal on ties
admit_i  = winner OR E_w-E_i <= k*sqrt(sigma2_w+sigma2_i)
w_i      = 1/F_i when admitted
n_eff    = (sum_i w_i)^2/sum_i(w_i^2)
```

If `q_w=0`, all valid frames are admitted with unit weight and their
arithmetic mean is emitted. One shared-green weight reconstructs separate
linear-DN pyramids for R/G1/G2/B. The base is the arithmetic mean. Each
reconstructed plane is clamped to its own aligned-input level-0 hull.

## Legacy gate-4.5 comparator

The comparator consumes the identical aligned linear shared green and four
CFA planes:

```text
E        = smooth5(LaplacianBand(shared_green)^2)
V_b      = GaussianBand(a*shared_green+b)
floor    = 4.5*beta_i,b*V_b
excess   = max(E-floor,0)
r        = excess/max(floor,1)/64
p_b      = min(2*1.4^(6-b),8)
weight   = r^p_b
```

Zero total weight falls back to the arithmetic mean (`n_eff=N`). It uses the
same arithmetic-mean base, four linear pyramids, and per-plane input hull.

## Width gate and one global `k`

The immutable grid is
`k=0.00,0.05,...,8.00` (161 values). For every value, exactly 42 predicates
(3 captures × 7 bands × 2 frozen ROIs) must be finite:

```text
abs(mean_n_eff_candidate/mean_n_eff_legacy_gate4.5 - 1) <= 0.05
```

Means are pixel means under the Gaussian-pyramid projection of each frozen
32-tile mask. A value survives only if all 42 pass.

Exactly one unchanged global value must serve all captures. No per-capture
selection, interpolation, wider grid, new crop, new metric, exclusion, or
post-outcome repair is allowed.

## Pareto metrics

Only width survivors are rendered. There is no negative-report sentinel.
Each 32×32 CFA-plane tile is sampled at `d=2` full-resolution output pixels;
`numpy.fft.fftfreq(...,d=2)` therefore reports cycles/output-pixel directly.
Only radial bins 0.10–0.25 inclusive are integrated, and commissioning makes
a known 0.20 cycles/output-pixel sinusoid go GREEN while the wrong `d=1`
interpretation goes RED.

Detail is phase-corrected real G1×G2 cross-power, reported as the square-root
candidate/legacy amplitude ratio. Flat is shared-green power ratio. For each
capture and metric, 32 paired sites are resampled with replacement as sites,
8192 replicates, fixed seed `0x5A172026 + 1009*capture_ordinal`, ordinary
2.5/97.5 percentiles:

```text
detail lower95 >= 0.95
flat-power upper95 <= 0.90
```

All six Pareto predicates must pass. Select the smallest global survivor and
report every contiguous passing range at the fixed 0.05 resolution.

## Commissioning and STOP semantics

Commissioning must report a null GREEN and planted defect RED for hand
`F/q/sigma2`, admission boundary/monotonicity, stable ties under reordered
scheduling, below-floor arithmetic mean, Kish width, VST covariance,
independent affine crop, all four CFA phases, constant field, 512 halo,
physical frequency units, actual-affine correlated coverage, analytic
`NU_SMOOTH`, Poisson–Gaussian null, coherent-detail metric, and flat-power
metric. Any missing control or non-finite value is an instrument error.

Exact gate:

```powershell
python experiments/PHASE1-DESIGN/reference.py --commission; python experiments/PHASE1-DESIGN/measure.py --gate
```

`measure.py` rehashes the manifest, both programs, this preregistration, all
sidecars, and every RAW before scoring. Exit 0 means one fixed global `k`
clears width and Pareto. Exit 20 means valid `NO_COMMON_K`, a successful W1
kill. Exit 2 means instrument/seal/input failure. A width-negative run writes
all 161 arms and every failed width criterion, performs no discretionary
Pareto render, prints `NO_COMMON_K`, and stops phase 1.

## Final source hashes

- `reference.py`: `08eee60df8170500af11deab18d3a3074535ad16323554d7caa69edc7e37e51e`
- `measure.py`: `ed2bda79d0148a90578016027066dbbd586230791c40252b07809459cc6e811f`
- `PREREGISTRATION.md` before substituting this self-referential list is not
  separately pinned here; commissioning pins the exact final file.
- Alignment binary and every input/artifact hash: see the sealed manifest.
