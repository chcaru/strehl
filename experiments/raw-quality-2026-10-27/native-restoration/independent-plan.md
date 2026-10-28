# Independent protocol: supported acutance, complete photographs

2026-10-27. Source-only preparation. Root owns numerical, RAW, build and vendor jobs. Freeze one authored correction and its controls before execution; this plan does not release an unspecified filter or a parameter sweep. No new crop search, source election, noise fit or lens-PSF estimate is authorized.

## Exact first proposal: algebraic mismatch refusal

**DERIVED; no execution.** Author proposes each same-color CFA plane at2native-pixel pitch, reflected-boundary separable `B=[1,2,1]/4`, `q=Bx-B(Bx)`, and `x'=x+2q`, with identical coefficients on all four phases and no spatial/noise gate. Its interior transfer `1+2H(1-H)`, `H=cos²(ωx/2)cos²(ωy/2)`, lies in[1,1.5]. That frequency-gain bound does not ensure spatial fidelity.

For an interior1D step constant in y, `B-B²=[-1/16,0,1/8,0,-1/16]`; therefore `x'[j]=1.25x[j]-.125x[j-2]-.125x[j+2]`. For unit step `x[j]=1` iff `j>=0`, output is−.125 at j=−2,−1 and1.125 at j=0,1. Thus the filter introduces12.5% dark/bright plateau excursions across two same-phase samples on each side, using correction taps at±4native pixels. This failure exists before noise, MHC, tone or color calibration. A clean neutral edge with enough black/white headroom exposes it without hiding the result behind clipping.

**Independent recommendation: refuse this exact plain amount2 recipe before a numerical screen or full-photo run.** The author independently confirmed the same reduction. No implementation or run is needed to establish this sharp-step mismatch failure, and no claim about every restoration method follows. A range-limited/shared-phase variant is a different proposal requiring root approval and a new frozen formula; range preservation alone would not establish color, thin-structure or developed-image fidelity. The remaining protocol below is preparation for such an explicitly released proposal, not admission of this one.

## Root-approved changed nonlinear candidate

Root subsequently froze a distinct formula: independently for each physical CFA phase,

```text
q = Bx - B(Bx)
lo,hi = minimum,maximum of original x in its reflected 3x3 same-phase neighborhood
x' = x + clamp(2q, lo-x, hi-x)
```

Use the same binomial B and same2native-pixel phase pitch. All neighborhoods and corrections read the unchanged original plane; this is one pass, not an in-place recurrent filter. There is no shared-quad gain, resampling, noise gate or parameter sweep. The local range constraint is the algorithm, not evidence of no RGB halo or preserved genuine structure. Independent per-phase clipping can affect chroma after MHC. The unbounded amount2 arm remains a deliberately harmful foil, not an alternative candidate; amount0 is a literal bypass.

The source author owns producing controls and this reviewer independently challenges their source and interpretation. Use the same actual MHC for truth/input/off/bounded/unbounded small panels. Noisy neutral/colored flats run first with a frozen supplied model/draw. Then one compact panel each covers the sharp step; an independently blurred step with close bright/dark lines; neutral/colored glints; and R/B fine diagonal/crossing structure with weak/flat green plus a coarse component. Do not generate blur by applying the candidate. A noiseless sharp interior step must stay exact in bounded CFA while the unbounded producing path exhibits the derived12.5% excursions. The field should retain headroom so clipping cannot hide them. Report RGB/chroma errors and each genuine signed component separately, retaining every harm; exercise missing-component/false-green destroyers before trusting an asserted detail/color guard.

Hard nonfinite, amount0/null, phase or writer-parity errors block interpretation. Root explicitly permits a finite full-photograph observation even if generated quality protection fails; those failures remain failed and `admission=false`. This is a prospective change of observation policy, not a threshold relaxation. No generated pass can qualify photographic quality.

The frozen `controls.rs` implements eight complete128x128 cases: neutral flat, colored flat, sharp step, blurred step/close bright-dark lines, neutral/colored glints, independent-color waves, fine/coarse superposition, and asymmetric-blur mismatch. Flats alone receive the one explicitly synthetic injected shot/read model and deterministic Gaussian draw, quantized/stored as originalu16 CFA. All arms use the same samples and actual MHC with unity WB; complete physical truth and every arm are saved. Main RGB/G/chroma errors use fixed interior[8,8,112,112]; component projections use the complete panel's two jointly fitted known templates. These are rendering controls, not Sony calibration or a physical visibility oracle.

Prospective error guards are RGB, green and chroma RMSE each at most1.10×baseline plus0.5DN for flats or1DN otherwise. Each two-template recovery requires baseline≥.25, candidate≥.95×baseline and candidate≤1.10×truth. Missing coarse structure, false green and an out-of-range sample commission those same guards; the actual unbounded step must also fail the image-error guard. Quality failure is reported, not a mechanical test failure. The joint color-template coefficient cannot independently establish retention of its8DN green component beside600DN blue; the separate green/chroma errors and actual photographs retain that limitation. No noise-free physical color reference is claimed exact after MHC at every fine frequency.

## Question and prior limits

The intended benefit is visibly cleaner existing structure under the held development, not new information or a repaired occlusion model. M115's two-stack matched-contrast SNR null is relevant to information claims; it does not alone disprove a useful acutance rendering on the current weevil. Its noise amplification and gross halos remain explicit adverse evidence. M70's measured near-scaled through-focus content likewise does not calibrate this image's blur. Do not adopt either old best-frame/selector reference as current truth.

BUILD-SHARP33–34 correct the old restore header: response was subject-dependent, default-off, and a huge gain cap could remain inert because the estimated response was already unity. A potency foil must demonstrably change actual CFA and developed pixels. The modern gather includes full-resolution MHC/remosaic/CA effects; the old quad-grid interpolator response is not an exact inverse of that consumer. Grid pitch, native-pixel support and the full two-dimensional gain must be explicit. A cap applied independently along two axes can square in two dimensions. A single-capture injected profile is not a measured post-merge noise covariance.

Before execution the author must bind the one formula/kernel, native-pixel units, boundary treatment, maximum correction, noise-model use and exact amount-zero bypass. Any blur scale is an uncalibrated hypothesis. Do not infer correctness from a kernel's DC sum, maximum principle or output sharpness alone. If current implementation changes per-phase filters or gains, color protection needs an actual colored witness through final MHC.

## Small controls, fixed before results

Reuse existing deterministic noise/fixture machinery and actual restoration/MHC/writer path rather than a new approximate Python renderer. Save complete small truth/input/zero/candidate/excessive panels before assertions. Run neutral and colored flats first, then one compact set covering these distinct failure directions:

| Control | What it must expose |
| --- | --- |
| Amount0 and constant/DC | Bit-exact bypass; constants stay constant without a Bayer-phase pattern. Check all four unequal phases, boundaries and nonzero color. |
| Noisy neutral/colored flats | Noise becoming artificial detail or false color. Compare delivered errors with the unchanged input under the same injected model; spatial texture is not a temporal-noise estimate. |
| Supported fine structure plus missing structure | A genuinely blurred visible line may become clearer, but a deliberately absent gap/line must not be counted as recovered. Compare known signed detail and topology, not gradient energy. |
| Bright/dark thin lines, close double lines and crossing depths | Loss, merging, reversal or extra lobes must remain visible independently of improved coarse contrast. Separate the fine and coarse components; one region's RMS cannot hide the other's loss. |
| R/B-only fine structure with weak/flat green | False green, chromatic displacement or erased independent color must fail even if neutral edges improve. Use same physical coordinates at all phases. |
| Step and isolated bright/colored glint | Added dark/bright shoulders, clipping, changed plateau color and detached halos. Already-clipped input cannot establish restored highlight color. |
| Mismatch and excessive correction | Include an already-sharp input and one fixed asymmetric/annular blur companion; a nominal blur-positive alone is circular. The deliberately excessive producing-path arm must change pixels and trigger the actual halo/color/detail guard before that guard is trusted. |

Numerical rejection thresholds must be bound with the formula before its first run, retaining existing applicable guards rather than tuning to outcomes. Mechanical null failure, nonfinite output, wrong-phase handling or an unexercised guard blocks interpretation. A fixed generated image-preservation failure remains a failure; root separately decides any explicitly labelled photographic observation. No generated pass establishes photographic quality. Do not expand a refusal into another metric campaign.

## Actual complete-image replay

Use retained exact merged-CFA masters, not inverse-developed RGB. Verify physical RGGB order, active origin, DN units, all four phases and unchanged CFA files. Preserve signed/headroom values until the existing writer applies its normal operations. The exact amount0 path must reproduce the existing complete RGB16 and float payloads with the same WB, saturation/highlight handling, color matrix, tone and ICC. No fresh automatic exposure/contrast fit is allowed. Record any new color/range clipping separately from a claimed lack of halos.

For each released arm deliver the complete weevil6896x4596 and flat6932x4620 photographs, full RGB16/float masters and retained CFA, including rejected candidates. Root and independent reviewer view complete images first, then all existing native384 witnesses without moving or dropping any. The [weevil manifest](../../raw-quality-2026-10-26/photo-review/baseline-witnesses.json) has SHA`826c4ab6c620122449f6575cdd18c0f9ee9cb460f29f6d895e832325d6405888`; use its ten witnesses with the current CA-off arm's identical geometry. The [flat manifest](../../raw-quality-2026-10-26/flat-baseline/frozen-witnesses.json) retains SHA`fde6bb02b6ca12793176b3e30ef8d60bba5aed3ed86dd1d4e3ea080c736a297e`, eight witnesses. Inspect background/dark field first, then hairs/scales/colored features, glints and occlusion rims; flat bars/stars/dots test detail and contour integrity.

A useful result must visibly improve supported contours across the complete photograph without disappearing structures, unacceptable noise, color shifts or new halos. Negligible complete-image benefit is a rejection. Revisit existing complete Helicon B8/B4/C and source support; retain native/vendor geometry and development-order confounds. Do not use them as a pixelwise oracle. An improved local hair or score cannot qualify the arm, and one weevil win cannot establish SOTA or release a default. Preserve regressions and uncertainty plainly.
