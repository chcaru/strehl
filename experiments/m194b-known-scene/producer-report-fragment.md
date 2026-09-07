## M194b producer: bounded numerical commissioning

**MEASURED, author commissioning; independent verification is separately owned.**
The producer delivered 20 strict manifests and 180 active-CFA frame files: flat
and scalar textured plane each have one noise-off stack and eight noisy stacks;
analytic color and its separately named `color-null` each have one noise-off
stack. Every stack has nine 320x240 RGGB frames. All source rail counts are zero.
The accepted output package is `producer-output-1/`; its
`producer-result.json` lists manifest hashes and complete source bindings.
No RAW file, capture or holdout was opened. No product source or M25 source was
changed by this producer task.

The frozen preregistration is `producer-preregister.json`, committed by the
orchestrator before production at `f1286fdaa8347bcbc60d78e171bd6eef25eb0ba6`.
Its SHA256 is
`b8295044614f55db45e715d7c5ffc985e676f3104443e6fe5dcf20193e9c0129`.
The fixture parameters did not change after any render or control ran.

Commands executed, from the repository root:

```powershell
python -B experiments/m194b-known-scene/commission-forward.py --out experiments/m194b-known-scene/producer-commission-1
python -B experiments/m194b-known-scene/produce.py --commission experiments/m194b-known-scene/producer-commission-1/commission.json --out experiments/m194b-known-scene/producer-output-1
```

Both completed with exit 0. `producer-commission-1/commission.json` retains all
seven groups and 93 individual author checks. Python 3.12.10, NumPy 2.4.4 and
SciPy 1.17.1 were used. The producer sets `OMP_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and `NUMEXPR_NUM_THREADS` to 2 before
importing NumPy/SciPy; no host scheduling intervention was made. Exact
interpreter/version/environment details are in `producer-runtime.json`.
That metadata was read subsequently with the same executable and producer
import; it is not a performance sampler or a CPU-use measurement.

### What was commissioned

| Group | Result and failure power |
|---|---|
| Flat first | Constant signal survives all nine focus/scale settings; maximum pre-exposure error1.3643e-12 raw DN against1e-8. |
| Aperture/CFA/quantization | Literal finite midpoint integration, affine centre, every RGGB site, rounding ties and saturation pass. Point sampling, quad-pitch aperture, omitted half-pixel phase and R/B swap are rejected. The saturation control has two counted rails. |
| Defocus/diffraction | Independently integrated uniform discs and two-pupil overlap agree with actual M25 OTF/blur operators within2.4698e-7 absolute complex transfer, against0.002. Radius/diameter substitution, negative-lobe clipping, deleted diffraction, doubled wavelength and doubled effective f-number reject. The measured negative disc lobe at CoC4, frequency(.375,0) is-0.1195393292; the independent spatial integral is-0.1195395761. |
| Noise law | Four-parity temporal variance errors are at most0.5042% at dark and0.5978% at the two bright levels, inside2% and1% bars respectively. All null correlations have magnitude at most0.001171, below0.02. A factor-two gain gives3.9916x expected variance; removed read noise and repeated frames give zero temporal variance. Repeated-frame correlation is1.0. A correlated negative retains marginal variance within0.2956% while yielding correlation0.23214, above0.15. |
| Observer/replay | Original, observing and allocated-but-disabled placebo modes produce byte-identical complete nine-frame arrays on both flat and textured plane. Re-exposure of cached expected electrons reproduces each observing run exactly. All original/on/placebo raw arrays remain available. |
| Numerical convergence | Across every one of the nine frames, maximum ROI RMS change is0.200388 post-WB DN for S4 toS8 and0.00332962 DN for margin48 to96, both below1 DN. Maximum absolute ROI changes are0.393836 and0.00627795 DN. No refinement or tolerance change was needed. |
| Analytic color/geometry | Independent12x12 cell quadrature at54 frame/site locations differs by at most1.3188e-11 desired post-WB DN. Wrong inverse scale, wrong centre and point sampling reject. The analytic achromatic null has zero inter-channel spread. The curved/chord maps share endpoints but differ by4.2344 native pixels at the chosen far corner; this is the small fixture's own gauge, not the old capture's pixel displacement. |

Numerical convergence is recorded per frame in the control JSON, not merely
pooled. An effect smaller than twice the observed numerical difference cannot
rank algorithms under this design. A passing difference bound is not physical
accuracy, and S8 is a refinement comparison rather than an exact ground truth.

Observer raw NPY byte hashes, identical across all three modes:

- Flat: `99b69b5d77e6b1edc94afa65ab6566c6ae087ea7bc61c48e0107e1579084b449`.
- Plane: `108852930b3c32eb6607c463888a9a2c1186806134f747b9e37fabf841ca5d89`.

### Producer/consumer boundary and conventions

Files store **only active CFA data**, little-endian u16, 153600 bytes each. The
consumer reconstructs padded storage with stride 327, buffer height 247, active
origin (2,4), and poison padding. Physical coordinates stay in the active array:
integer native pixel centres, RGGB R at (0,0). Geometry is the known forward map
`z=c+s*(q-c)` with centre (183,101), frame 4 identity gauge, and the nine frozen
nonlinear scales derived from the already-published M103 JSON. Storage offset
is not an optical coordinate offset.

Raw black/white are 512/15360. Synthetic gain 0.25 DN/electron and read noise 4
electrons are supplied explicitly to both the producer and, by contract, the
consumer's one injected model. This commissions that synthetic operation; it
cannot independently calibrate those shared constants to a physical camera.
Noise is independent Poisson shot plus Gaussian read, then ties-to-even
rounding and clipping. There is no FPN, PRNU, hot-pixel or correlated-noise claim.
The dark rounded-normal variance is independently summed from bin probabilities
(1.0833333224 DN2); bright expectations include the 1/12 DN2 rounding term.

Scalar M25 channel multipliers are exactly (.75,1,.6). The manifest WB values
are f64 representations of (4/3,1,5/3), which the consumer rounds to f32.
Scalar optical references must retain the resulting channel-scale times actual
f32-WB factors. Analytic color starts in desired post-WB DN, divides by the
declared f64 WB and 0.25 before mosaicking, and is rounded once at exposure.
The subsequent f32 WB representation discrepancy is retained; the fixture was
not changed to cancel it. Root scoring may report the desired analytic target
and disclose that tiny finite-arithmetic contribution.

The returned M25 geometric truth is not used as an attainable optical
reference. The standalone transfer controls establish numerical OTF/blur
operators; complete renderer wiring also needs the independently owned
cached-frame/reference check. Scoring and actual TIFF crop/placement checks
are outside this producer's ownership and remain required before accepting
the production baseline. In particular, a source array or decoded TIFF of the
right shape is not proof of the correct output map.

### Failure accounting and executable selective refusal

No scientific control failed in the first complete commissioning run. A
syntax-only check caught and corrected one unmatched parenthesis in the new
control script before any control executed; no fixture or threshold changed.

After the normal package completed, the selective-refusal behavior was
predeclared in `producer-refusal-preregister.json` and tested using a clearly
labelled copy of the commission. Only the diffraction and convergence group
statuses were changed to fail; original artifacts and bindings were preserved.
The live producer withheld the plane, retained 11 flat/color/color-null
manifests, and reported `partial-refusal`. All 99 retained CFA files match the
corresponding normal package byte for byte. Thus an optical check failure does
not silently cancel valid flat/color work or let the failed plane proceed.

The first direct shell tool reported a nonzero exit 1. A second invocation
captured the Python child's exit directly and confirmed the required code 2;
both output directories are retained, labelled `producer-refusal-control-1`
and `producer-refusal-control-2`. Exact command, child stdout/stderr and all 99
comparisons are in `producer-refusal-result.json`. These are failure controls,
not substitutes for `producer-output-1` in the 40-TIFF baseline.

Implementation hashes at the successful commissioning run:

- `produce.py`: `c17391b26199ea70b29e4f0da12667fe1b8ca9dc355053ea49b3e8a87cc6c4a0`.
- `commission-forward.py`: `b29160d462c5f340fffeb10c772cd5bb8a5629536837d57ac059bccd4fd01775`.

All five frozen M25 module hashes and the published scale-source hash match
before and after commissioning and production. Existing sources and payloads
were not moved or overwritten. Two-layer alpha/compositing, spatial chromatic
defocus, physical camera PSF fidelity, alignment estimation and real
occlusion-halo qualification remain unmeasured by this first benchmark.
