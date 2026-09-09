# Native green cue: fixed consumer falsifier

Status: frozen prospectively; no numerical result. One candidate, no retuning.
Read SYNTHESIS architecture/profile decisions and C12's partial commissioning.
This is an experimental RAW focus cue, not super-resolution or a novelty claim.

## Original-CFA operator

Use active native coordinates, independent of buffer padding. For quad q=(i,j),
g1(q)=u16(2i+1,2j)-black_G1 and g2(q)=u16(2i,2j+1)-black_G2.
Keep signed f32 values; inputs remain original u16. Greens have WB=1 here.
Let h(0)=1 and h(+/-ex)=h(+/-ey)=-1/4, with no other taps.
Hf(q)=sum_t h(t)f(q+t).

Cm(q)=H[g1(q)-g2(q)]; Cp(q)=H[g1(q)-g2(q+ex)].
E(q)=Cm(q)^2 + (Cp(q)^2+Cp(q-ex)^2)/2.
The fixed symmetric average centres E at native (2i+.5,2j+.5): Cm is centred
there; the two Cp filters are centred one native pixel either side in x.
Required original support is qx[-2,+2], qy[-1,+1]. No edge replication.
Every filter's coefficients sum to zero separately on each green phase.
Thus constant additive phase imbalance and affine illumination cancel in the
unquantized operator. Multiplicative imbalance on texture need not cancel.
This is not an estimator of pure alias energy or of noise from G1-G2.

For each individual filter F, combine coefficients of identical original sensels
first, then price V_F=sum_s c_F(s)^2 * noise.variance(actual_phase_s, g_s).
V(q)=V_Cm(q)+(V_Cp(q)+V_Cp(q-ex))/2, in original green DN^2.
This is the exact expectation of the filter noise energy under the injected
independent-source model. Correlation between the three filters does not add a
cross term to the expectation of their sum of squares; they are not independent
replicates. U16 rounding and physical inter-sensel correlation are not thereby
calibrated. No private fitted sigma, gain, beta or quantization correction.

## Transport and actual consumer

Prepare E,V before the existing MHC/fullres gather changes the source frame.
For full output quad coordinate z, map its native quad centre with the existing
pull transform: source cue index = T(z+(.25,.25))-(.25,.25), in plane units.
Crop coordinates must first be lifted to the full grid. Use fixed nonnegative
bilinear interpolation for E and V with the same weights. All four source sites
and their original filter support must exist. No clamped or fabricated coverage.

In BandMerge::add_frame_with_gain, apply the existing destination smooth5 once
to transported E and V. Replace ONLY band0 energy and floor at supported pixels:
energy=smooth5(E); floor=cfg.gate*smooth5(V). Do not multiply this price by the
old luma beta. Keep select_weight, exponent, significance rule, accumulation,
reconstruction, all coarser bands and the ordinary probe unchanged.
Erode cue validity by the actual smooth5 support; use the exact old band0 path
where that support is incomplete. Off/default must retain old arithmetic.
Initial scope requires explicit injected model, no defects, CA, exposure gain,
clipped source cells or non-RGGB phase interpretation; refuse unsupported config.
Only one frame's temporary source fields plus compact consumer fields are kept.

## Fixed generated population and truth

Reuse M194c Frame geometry: active274x190, origin(5,7), stride292, black512,
white15360, WB R/G/B=1.15/1/1.65; crop quad(9,6,112,78). Primary geometry is
identity through actual fullres gather/load_frame, current merge and collapse.
One independently chosen literal transform is the transport control: centred
matrix [[1.012,-.006],[.006,1.012]], translation(.375,-.25) in plane units.
It is not another scored population. Final ROI is native x[87,187),y[45,145).

Define u=n dot (x,y), n=(1,0),(0,1),(1,1)/sqrt(2). Sharp post-WB irradiance:
I=3000+500*cos(2*pi*.06*u+.2)+40*cos(2*pi*.30*u+1.1).
Nine frames have Gaussian sigma [1.6,1.2,.8,.4,0,.4,.8,1.2,1.6] native pixels.
Generate each tone directly: multiply by exp(-2*pi^2*sigma^2*|f|^2), and integrate
its native unit-square sensel with sinc(fx)*sinc(fy). No raster resampling plant.
Divide by actual phase WB before source storage; sharp truth uses sigma=0 and
the same physical unit-cell integration, independently of the candidate output.
The two frequencies have different blur attenuation and relative filter responses,
so the two cue energies are not algebraically forced to be common MTF multiples.
Require positive valid-site coverage through the actual band0-weight route and
changed collapsed output; otherwise intended-benefit evidence is vacuous. No
direct per-frame energy or weight receipt is collected. An isolated noiseless
tone is not an improvement witness. The fixed .30 band is below the green quincunx
isotropic limit .35355 but above either individual phase's .25 Nyquist.

Noise: injected g=.25 DN/e, RN=4e (read sigma1DN), independently per source
sensel/frame. Reuse the existing fill_probe_noise standardized-draw mechanism;
multiply by sqrt(.25*S_original+1), then existing u16 rounding. Disclose its
finite draw quantization. Generate each original once and reuse identically
off/on. Assert no generator/source clipping; record seed/frame stream mapping.
Use noise-off plus seeds701,709,719,727,733,739,743,751.
Flat plus three mixed directions x nine noise states x two modes =72 outputs.
Three low-only directions (high amplitude0), noise-off, two modes add6: total78
tiny stack outputs, nine frames each. No stored image corpus or TIFF apparatus.
M194b saved fields are later regression material only; they cannot establish the
intended >.25 information gain and are not added to this first population.

## Independent controls and decision

Before scoring: finite literal coefficients/noise price; flat and affine signals
with green offsets +/-32DN and phase gains1.01/.99; missing support; padded
origins; identity/nonidentity half-pixel coordinate checks; exact default/fallback.
Use independent variance-price factor-two destroyer. Constant/affine noiseless
cue must vanish away from support boundaries; a low sine is real scene content.
Sharp-source reconstruction controls use original noiseless phase fields and the
actual demosaic_row, without additional stack outputs. Both phase-position and
demosaiced-green readouts require >=50% true high-tone amplitude and <=25% relative
complex coefficient error; otherwise the intended information is not admitted.
Wrong G1/G2 coordinates (axis case) and +50% high-tone amplitude must worsen the
independent known-truth coefficient error by >=.10 relative units.

Score collapsed greens at their DISTINCT native positions, and actual current
demosaic_row green over the same ROI. Fit fixed five-term f64 least squares
[1,cos/sin(.06*u),cos/sin(.30*u)] to avoid window leakage; no fitted registration,
gain, blur or truth. Report complex coefficient error and full known-truth RMSE.
The second readout tests reconstruction, not TIFF/tone/ICC or a photographic claim.

Flat first: candidate temporal variance point estimate <=off; paired95% upper
bound on its difference <=.05*Voff. Candidate noisy mean-field RMSE <=off.
Use exact paired delete-one jackknife across eight independent seeds, 1.96SE;
pixels are not independent replicates. Preserve noise-off bias and every seed.
Failing flat blocks intended-benefit scoring/release, with no rescue parameter.
For every mixed direction, both readouts' high complex error and full RMSE must
not worsen versus off in noise-off and eight-seed-mean images. Low-tone relative
complex error may not worsen by >.002. Each noisy seed's full RMSE <=1.05*off.
Require >=5% high complex-error reduction in BOTH readouts for at least one same
direction; baseline relative error must be >=.02 or that benefit is unresolved.
Every low-only case must preserve full RMSE and low complex error to the same
nonregression bars. Numerical allowances: 1e-5 DN RMSE, 1e-6 relative error only.
Report paired uncertainty/extremes. Amplitude alone can reward alias or sharpening;
phase error, full error, flat noise and low-tone controls prevent that shortcut.
Any missing support, nonfinite score, unexercised branch or incomplete population
refuses admission. Any failed bar ends this candidate; no retuning after results.
Apply charter limits:120 aggregate numerical CPU seconds,2GiB process,256MiB
artifacts,120 wall seconds/child,two workers. No RAW reads or full photo renders.
