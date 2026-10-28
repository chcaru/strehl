# Fixed independent blur-phase screen

2026-10-27, before execution. Root alone runs:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/run-controls.py --iteration 1
```

The worker interface is `controls.py --out <fresh-directory>`. Its terminal
`receipt.json` records `COMPLETE_INSECT_BLUR_PHASE_CONTROLS`, `complete`,
`all_cases_completed`, `controls_pass`, every failed required case, and
unconditional `quality_claim:false`/`photographic_admission:false`. Scientific
failure does not suppress subsequent cases or the terminal record. Mechanical
exceptions remain incomplete failed jobs. No RAW or developed corpus pixels
are read. The only corpus-derived input is the SHA-pinned held map below.

## Physical inputs and fixed populations

Forty fixed pairs run in order: two exact flats, two independently noisy flats,
two rank-one periodic scenes, six Gaussian pairs, four disk pairs, fourteen
curved-track pairs, eight adverse pairs, and two branch demonstrations. G1 and
G2 are separately acquired at physical origins(4001,2400)/(4000,2401), with
native pitch2 and128x128 original samples. The scene is an independently
evaluated continuous Fourier sum, not a shifted raster or producer-generated
phase. Unit-square sensel integration is the analytic sinc product; symmetric
disk transfer is `2*J1(2*pi*r*f)/(2*pi*r*f)`, radius5 native pixels. The fixed
four low and sixteen high frequency vectors/phases/amplitudes are literal in
the source and saved in the receipt. This is an analytic plant, not a measured
Sony PSF or pixel-response calibration. High-band disk transfer changes sign.

One injected model uses f32 gain0.22893773DN/e, read4.2e, black512 and working
white15360. Gaussian acquisition noise has variance gain*noiseless_signal plus
the exact f32 squared read-DN value, followed by nearest-u16 rounding. There is
no second noise estimate or added rounding-variance floor. The producer uses
the same parameters on its observed samples; that signal substitution and
data-dependent spectral weighting do not constitute calibrated likelihood.
Working-white rejection is not evidence of physical sensor saturation.

The seven rungs0/49/99/149/199/249/298 use the held map's actual nonlinear
point trajectory at native(4650,2680), anchored to149. Map SHA is
`4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`, path
`outputs/raw-quality-2026-10-26/weevil-107-baseline/alignment.txt`.
All299 stored transform bits and derived point positions are recorded;
departure from the endpoint chord is retained. This reuses estimated-track
curvature as a plant, not independently calibrated camera motion. Each sampled
rung must pass separately. Coarse EVEN physical-origin differences carry the
large displacement; seed0 searches only its fractional remainder. This is a
translation-reader control at one point, not a complete similarity/global-solve
commission or a claim about all299 actual placements.

## Frozen gates and causal defects

Every Gaussian p1/p2 result and every disk/track p2 result must be accepted and
have Euclidean total-displacement error <=0.10 native pixels. There is no
averaging over bad rungs/phases. At least one of the four disk p1 readings must
refuse or err by >=0.20 native pixels, while all four p2 readings pass: otherwise
the claimed distinct sign-inversion advantage is not demonstrated. Both readers
must refuse each flat/noise and rank-one input. Refusal-all cannot pass positives.

Wrong sign and missing phase-factor-two mutate an actual positive output and
must fail the identical headline `error_record` scorer. Ignoring the recorded
physical-origin transport must produce a >5-native-pixel error on the track;
passing a G1 rectangle with an R-phase physical origin must raise ValueError.
Neither foil is evidence of physical alignment accuracy on photographs.

For the explicit half-period demonstration, all x-frequency indices are odd.
A128-native-pixel translation flips every AC sign. The same original pair is
read with declared seed0 and seed128: p2 should accept the alias near0 under
the former and the correct128 branch under the latter. The former must fail
the physical-truth scorer. This control establishes
`UNIDENTIFIABLE_WITHOUT_VALID_BRANCH_SEED`; no universal branch detector is
claimed. The producer's expanded integer seed allowance and per-arm periodic
phase reduction were agreed before any run; the original narrow checkpoint
was never executed.

The eight adverse inputs retain all accepted errors and refusals: asymmetric
two-tap blur with zero geometric motion, nonperiodic window truncation, local
scale1.008/rotation0.012rad, and changing two-depth blur/visibility with zero
geometric motion. Their scores do not gate the sign-inversion mechanism screen,
nor are they silently called passes. These can be observationally ambiguous;
the screen cannot certify safe physical correction at occlusion/glint boundaries.

## Source and resource checks

The already fixed gaussian-0-G1 and disk-0-G1 arrays are replayed as one
two-pair batch. All accepted/refused decisions, refusal lists, displacement
vectors and grid indices must equal their singleton results; every complete
p1/p2 score surface must agree within2e-6 absolute normalized score. This adds
no new scene, threshold choice or population. The parity record is preserved
even when a required scientific case fails.

Source read-through verifies physical two-pixel frequency units, forward phase
sign, separate G1/G2 offsets, doubled phase only in p2, and total displacement
as origin difference plus searched patch displacement. Spectral noise includes
the covariance of removing the arithmetic mean before the Hann window. Both
powers use the same signal fractions, support and score/refusal thresholds.
Conjugate-bin counts and effective counts are heuristic diagnostics, not
independent statistical observations. Shared G agreement or reverse consistency
cannot supply missing truth. The producer performs no interpolation or MHC.

The root job binds producer/control/protocol/wrapper and held map before/after.
The worker additionally preserves all eighty complete u16 input arrays and
eighty complete257x257 f32 score surfaces, per-case diagnostics and exact scene
parameters. Four Torch CPU threads/one interop, f32/complex64 production,
TF32 disabled,4GiB Torch allocator limit; root bounds300s wall/1200CPU seconds
and8GiB host. Generation/reference scalars use f64 independently; storage is
u16 and saved score arithmetic f32. No numerical work was performed by the
control author before freeze. Passing permits only root's separately selected
actual-reader/full-photograph decision, never a quality claim.
