# Optical-support veto: fixed generated mechanism screen

PROPOSED / UNEXECUTED. Root executes and independently reviews. No photographic
RAW, new visibility estimator, parameter sweep, or production default is involved.
Read first: `../quality-september25/next-spatial-direction.md`, current
`docs/proposals/2026-09-quality-path.md`, `../cross-scale-source-prior/results.md`,
and `../layered-raw-inverse/pupil-stencil-results.md`. Their failures remain.

The plant is fixed at96x96 native samples, five focus positions1,.75,.5,.25,0,
near/far inverse depths1/0, defocus scale12 native pixels, common Gaussian
sigma.7 with finite radius3, and the previously commissioned equal-area
128x128 pupil at angle.23 (16384 points). Use the existing coupled pupil table
and forward; never the independent-marginal visibility shortcut. The plant has
an opaque bright half-plane x<32, a three-pixel near filament at x58..60 and
y35..61, and coloured far texture. Flat and transparent fine-near/coarse-far
scenes are separate nulls. Sensor noise is injected by the actual Rust ISO100
profile; Python's forward does not synthesize noise or estimate its constants.
Storage handed to the actual consumer is rounded u16 CFA. WB is unity and
geometry identity, so this measures optical support without registration/CA.

The crop is plane[8,8,32,32], producing the entire64x64 generated output. Actual
levels are32x32,16x16,8x8: TWO AC bands, not the seven-band photographic regime.
Do not enlarge the plant if the small fixture is unexercised. Its source arrays
include real optical context beyond the cropped consumer. Pyramid borders use
the actual consumer's replicate convention; the mask uses exactly that same
convention and decimation/expansion phases. This is a bounded consumer screen.

For each original sensor location, enumerate nonzero SAME-RAY joint table
entries against the supplied binary scene geometry. Union the actually visible
near/far surface IDs; flag unsupported original accesses. Union those IDs through
the finite common-PSF footprint. For an identity gathered quad, union all four CFA
sites. The Rust mask then unions through exact REDUCE and EXPAND source indices:
L_k=G_k-EXPAND(G_{k+1}). Q is true only for one supported opaque surface matching
the sharp visible surface at the nominal coefficient centre. Crossing an opaque
boundary is conservatively invalid even at nominal focus. No energy, gradient,
output error, fitted depth or source winner enters Q. Transparent/flat scenes
explicitly have all-one Q; legitimate layered superposition is never vetoed.

Compare Current, all-one Q, oracle Q, and a fixed source permutation Q_(i+2)%5.
Use actual rounded native GPU gather, actual synthetic green probe, injected
variance, canonical energy/floor/weights, actual accumulation/collapse, input
hull and current MHC. The only altered values are positive AC source weights:
w'=w*Q. If a coefficient has NO clean positive source weight, retain all canonical
weights there exactly; report no-clean-support. Each AC band has its own support.
Keep unweighted sums, terminal mean, coefficients and bounds exact. All-one Q
must reproduce the actual Current CFA and developed RGB16 bit for bit.
An additional literal all-zero-Q mechanical arm must also reproduce Current
exactly via the no-clean-support fallback; it is not an image-quality candidate.

Identity-gathered samples MUST equal original CFA minus black exactly at their
actual sites; otherwise support propagation is invalid and execution refuses.
This explicitly covers native rounding and prevents an unmodelled MHC/resampling
footprint from being silently omitted. Generated source hashes remain exact.

The three windows, in original native coordinates, are outside-spill
[44,20,6,12], near-filament[56,40,7,18], far-texture[66,20,10,12]. A whole interior
[22,22,52,52] is supplementary. Before any positive claim require positive
canonical weight on invalid optical support AND a clean positive alternative
at a coefficient whose nominal centre lies in the outside-spill window, plus
positive outside luma error exceeding twice the flat RMS. Otherwise result is
UNEXERCISED; do not shift geometry/contrast/windows or sweep a threshold.

Root independently scores linear camera RGB and R-G/B-G errors against the
supplied common-in-focus optical floor, never the unblurred pinhole. Fixed
developer: actual Develop::measurement(true), no auto tone, matrix or exposure
fit. Outputs include full generated images and linear arrays for all arms.
Edge improvement requires lower RGB AND chroma RMS; protected filament/far
windows must remain within1.05x Current errors and their centred template
amplitudes within0.95..1.05x Current (also report uncapped absolute amplitudes).
The fixed permutation must be measured separately; record its changed weight
mass and effective sample count because permutation does not preserve those.
No quality admission follows solely from numerical changes, lower mean light,
or lower noisy-flat RMS. A blurred truth destroyer must fail detail protection;
an overcontrast and grey destroyer must fail truth-error/chroma protection.
Transparent component amplitudes are jointly fitted against both supplied
components, not two independent regressions with spectral leakage ignored.

This is an oracle availability test. Passing would justify seeking the same
clean/contaminated source circumstances on a registered opaque photographic
edge; it would not prove automatic visibility, fix flat-chip alignment, cure
transparent mineral glare, or establish SOTA. Failure closes this exact veto.

Root commands after review and the two includes described in integration.md:
`python -I -B experiments/optical-support-veto/run.py prepare --out experiments/optical-support-veto/prepare-1`
`python -I -B experiments/optical-support-veto/run.py build --out experiments/optical-support-veto/build-1`
`python -I -B experiments/optical-support-veto/run.py consume --prepare experiments/optical-support-veto/prepare-1 --build experiments/optical-support-veto/build-1 --out experiments/optical-support-veto/consume-1`
The existing Windows job helper bounds preparation at120s wall/240s CPU/4GiB,
and consumer at120s wall/480s CPU/4GiB. There is no unbounded ray-by-image tensor;
the commissioned sparse joint table is reused, and support union loops its
bounded offsets using96x96 boolean/byte arrays only.
