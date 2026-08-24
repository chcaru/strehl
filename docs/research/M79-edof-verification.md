# M79 — Independent verification of the EDOF workstream kill

**Status: INDEPENDENT LITERATURE VERIFICATION.** This milestone verifies three
claims made by `G-edof-deconvolution.md` (M19). It does not repeat M19's survey
and it does not modify M19, M20, M70, `SYNTHESIS.md`, or code.

**Tagging convention.** A tag at the start of a paragraph or table row governs
every factual claim in that paragraph or row. `MEASURED` means observed in a
paper, project report, or source record; `DERIVED` means algebra or a logical
consequence is shown; `ARGUED` is interpretation. Literature claims additionally
say `VERIFIED-AT-PRIMARY-SOURCE`, `VERIFIED-AT-PRIMARY-SOURCE (abstract only)`,
or `TAKEN-FROM-SECONDARY`. Project measurements say `READ-AT-PROJECT-SOURCE`.

## 0. Verdicts first

| Claim under verification | Verdict | Independent finding |
| --- | --- | --- |
| **G-edof claim 1:** Levin et al.'s Appendix B Eq. (52) is the focal-stack Wiener estimator, and they conclude against it | **OVERSTATED** | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** The equation attribution is **CONFIRMED**. The negative conclusion is only that a continuously swept camera beats a focal stack when both divide the same unit exposure and sensor noise is additive with fixed variance. It is not a rejection of focal-stack Wiener estimation, and it does not evaluate it against selection. |
| **G-edof claim 2:** “First to model the occlusion halo” is false because there are 28 years of prior art | **CONFIRMED, NARROWLY** | **ARGUED; VERIFIED-AT-PRIMARY-SOURCE / abstract boundary stated below.** Prior physical modelling is real, so the bare “first to model” claim is false. G-edof overreaches when it treats modelling, truncated-kernel correction, layer unmixing, light-field depth labelling, and a sequential photographic focus stack as solved instances of one problem. |
| **G-edof claim 3:** Do not build iterative deconvolution | **OVERSTATED** | **ARGUED; VERIFIED-AT-PRIMARY-SOURCE and READ-AT-PROJECT-SOURCE.** The evidence supports “do not make iterative deconvolution the core merge; test a guarded one-shot plugin first.” It does not support “never build an iterative method,” especially for structural occlusion unmixing, which none of M20, M70, or Sage et al.'s benchmark tests. |

**ARGUED; READ-AT-PROJECT-SOURCE.** The source report is more careful than the
ledger shorthand. G-edof §2.7.1 already says Levin's result depends on a
fixed-total-exposure assumption that does not hold for the rig, and G-edof
§0.2 says not to build iterative variants *“on the strength of this literature.”*
The compressed versions removed both qualifications. M79's first correction is
therefore to the summaries, not to those two qualifications in M19.

**ARGUED; READ-AT-PROJECT-SOURCE.** G-edof, M20, and M70 genuinely converge on
the **plugin-not-core** decision by different mechanisms. They do not converge
on a permanent ban on iteration. Their common blind spot is opaque,
visibility-changing occlusion: the exact case for which an iterative layered
solver might be justified.

---

## 1. Evidence boundary

### 1.1 Sources obtained and read

| Source | What M79 actually read | Evidence depth |
| --- | --- | --- |
| Anat Levin, Samuel W. Hasinoff, Paul Green, Frédo Durand, William T. Freeman, **“4D Frequency Analysis of Computational Cameras for Depth of Field Extension,”** MIT-CSAIL-TR-2009-019, 8 May 2009, `hdl.handle.net/1721.1/45513` | Full 20-page technical report; especially §2–§5 and Appendices A–C, including Eqs. (51)–(57) | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** |
| Yoav Y. Schechner, Nahum Kiryati, Ronen Basri, **“Separation of Transparent Layers Using Focus,”** ICCV 1998, pp. 1061–1066, DOI `10.1109/ICCV.1998.710848` | Full six-page conference paper, including §§1–4 and its reference to Technion report EE-PUB-1086 (1997) | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** |
| Sundeep Singh Bhasin, Subhasis Chaudhuri, **“Depth from Defocus in Presence of Partial Self Occlusion,”** ICCV 2001, vol. 1, pp. 488–493, DOI `10.1109/ICCV.2001.937556` | Full six-page paper, including §§3–6 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** |
| Morgan McGuire, Wojciech Matusik, Hanspeter Pfister, John F. Hughes, Frédo Durand, **“Defocus Video Matting,”** *ACM TOG* 24(3):567–576, 2005, DOI `10.1145/1073204.1073231` | Full paper, including §§2, 4, 5 and 7 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** |
| Samuel W. Hasinoff, Kiriakos N. Kutulakos, **“A Layer-Based Restoration Framework for Variable-Aperture Photography,”** ICCV 2007, pp. 1–8, DOI `10.1109/ICCV.2007.4408898` | Full paper, including §§3–9 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** |
| Ting-Chun Wang, Alexei A. Efros, Ravi Ramamoorthi, **“Occlusion-Aware Depth Estimation Using Light-Field Cameras,”** ICCV 2015, pp. 3487–3495, DOI `10.1109/ICCV.2015.398` | Full paper, especially §§1–4 and §6 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** |
| Daniel Sage et al., **“DeconvolutionLab2: An Open-Source Software for Deconvolution Microscopy,”** *Methods* 115:28–41, 2017, DOI `10.1016/j.ymeth.2016.12.015` | Full paper, especially §§3–6, Figs. 4–7, and Tables 2–3 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** |
| `G-edof-deconvolution.md`, `M20-deconvolution-ceiling-measured.md`, `M70-through-focus-spectrum.md` | Each report in full, including M70's later addenda through §22 | **MEASURED; READ-AT-PROJECT-SOURCE** |

**MEASURED; TAKEN-FROM-SECONDARY.** Crossref resolves the peer-reviewed companion
to the Levin report as the same title in *ACM Transactions on Graphics* 28(3),
pp. 1–14, published 27 July 2009, DOI
`10.1145/1531326.1531403`. M79 did not use that shorter publication to verify
Appendix B. The load-bearing equations were read in
**MIT-CSAIL-TR-2009-019**, which is the source G-edof actually names for them.

### 1.2 Sources that do not carry the verdict

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE (abstract only).** M79 obtained the
abstracts, but not the full bodies, of N. Asada, H. Fujiwara and T. Matsuyama's
ICCV 1995 paper, DOI `10.1109/ICCV.1995.466793`, and its *IEEE TPAMI* 1998
extension, DOI `10.1109/34.659933`. The abstracts establish that the authors
introduced the reversed-projection-blurring model and tested it on real images.
They do **not** let M79 verify the equations, reconstruction procedure, or any
claimed focal-stack inversion. Those stronger claims are not used below.

**MEASURED; TAKEN-FROM-SECONDARY.** The 1995 DOI resolves to **“Seeing Behind
the Scene: Analysis of Photometric Properties of Occluding Edges by the Reversed
Projection Blurring Model,”** pp. 150–155—not to “Edge and Depth from Focus,”
as G-edof §4.1 labels it. “Edge and Depth from Focus” is an earlier Asada
citation in the 1995 paper's reference metadata. G-edof attached a real DOI to
the wrong title.

**MEASURED; TAKEN-FROM-SECONDARY.** M79 could not obtain Paolo Favaro and
Stefano Soatto's 2003 CVPR paper body, DOI
`10.1109/CVPR.2003.1211519`; the Bern repository record was restricted or under
maintenance. G-edof itself had only the abstract. M79 therefore records it as a
lead, not independent evidence. McCloskey et al. 2011 was likewise not obtained
and is not used to support a verdict.

**MEASURED.** No GPL/AGPL implementation was opened. Only papers, public
bibliographic records, and the three project reports were read.

---

## 2. Claim 1 — what Levin actually derived and concluded

### 2.1 Identity of the source and estimator

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** The primary source is the 8 May 2009
MIT technical report named in §1.1. Appendix B is titled “Cameras with multiple
measurements.” Levin et al. define, for each spatial frequency, observations

```text
B_j = phi_j I + n_j
```

with independent additive Gaussian sensor noise of variance `eta²` and a
zero-mean Gaussian signal prior of variance `sigma_omega²`.

**DERIVED; VERIFIED-AT-PRIMARY-SOURCE.** Levin TR Eq. (52) minimizes the sum of
the noise-normalized data residuals plus prior precision and returns

```text
I_est =
    (eta^-2 SUM_j phi_j* B_j)
    ---------------------------------
    (eta^-2 SUM_j |phi_j|^2 + sigma_omega^-2)
```

Multiplying numerator and denominator by `eta²` gives
`Σ H*Y / (Σ|H|² + eta²/S)`. That is the proposed multi-frame
Wiener/MMSE estimator exactly. This part of G-edof claim 1 is **CONFIRMED**.

**DERIVED; VERIFIED-AT-PRIMARY-SOURCE.** Levin TR Eq. (53) gives expected
per-frequency reconstruction error as the reciprocal of summed OTF power plus
prior precision. The paper therefore does more than mention a familiar formula:
it explicitly connects the focal-stack merge to `Σ|H|²` and its error law.

### 2.2 The conclusion is comparative and configuration-specific

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Levin TR Eqs. (54)–(57) do not compare
Wiener reconstruction with selection, averaging, or a post-merge inverse. They
compare two **acquisition systems**: a focal stack that measures one focus depth
per time bin and a camera that sweeps focus continuously during the same
exposure.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** The load-bearing sentence before
Levin TR Eq. (54) is: *“Suppose we divide exposure time into N bins.”* The
per-bin OTF has amplitude `A²/N`. Levin TR Eq. (55) then explicitly multiplies
OTF power by `1/N²` *“to account for the shorter exposure.”* With `N` bins and
the minimum non-aliasing count `N = ASΩ`, Eq. (57) yields focal-stack summed
power

```text
A² / (S² Omega |omega|)
```

versus focus-sweep power

```text
A² / (S² |omega|²).
```

**DERIVED; VERIFIED-AT-PRIMARY-SOURCE.** Their ratio,
focal stack divided by sweep, is `|omega|/Omega`, below one inside the band.
Their actual conclusion is therefore: **under this additive-noise,
fixed-total-exposure construction**, the focus-sweep camera has lower expected
reconstruction error. It is not “Wiener focal-stack estimation is a bad merge.”

### 2.3 Assumption audit against this rig

| Load-bearing condition | Levin TR Appendix B | M79 commission's rig | Transfer |
| --- | --- | --- | --- |
| Exposure budget | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** One unit exposure is divided into `N` shorter bins | **MEASURED.** `N = 22–299` separately exposed full frames; total capture time and light grow with frame count | **ARGUED: VIOLATED.** This is the assumption that creates Levin's focal-stack disadvantage. |
| Noise | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Independent additive Gaussian noise with one common variance | **MEASURED.** Calibrated signal-dependent sensor model with read noise and PRNU | **ARGUED: VIOLATED.** A fixed-variance derivation can approximate a locally read-noise-dominated band, not the whole RAW range. |
| Focus samples | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Focus slopes are spread evenly; `N = ASΩ` is the minimum non-aliasing count | **MEASURED.** Lens-driven stacks without a motorised z rail or calibrated physical z increments | **ARGUED: NOT ESTABLISHED.** Frame count alone does not prove uniform slope sampling. |
| Scene | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Locally Lambertian, locally constant depth, one PSF per patch | **MEASURED.** Opaque macro subjects with depth discontinuities and veiled background at edges | **ARGUED: HOLDS only on single-surface interiors; fails at the target halo.** |
| Optics | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Eqs. (54)–(57) use the geometric/paraxial sinc OTF; diffraction is not in this focal-stack comparison | **MEASURED.** Sony A7C II, FE 100 mm F2.8 Macro GM plus 2× teleconverter, 1:1–2.8:1, effective aperture up to about f/33 | **ARGUED: VIOLATED in the load-bearing high band.** The report's separate Fourier-optics discussion says diffraction scales down the available budget. |
| Alignment and magnification | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Multiple measurements sample the same spatial frequency of the same latent patch | **MEASURED.** Ordinary tripod and internal focusing; registration must absorb focus breathing and motion | **ARGUED: CONDITIONAL.** It holds only after registration and only where one latent layer exists. |
| Known response | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Each `phi_j` is known | **MEASURED.** No calibrated per-pixel, per-frame complex PSF family is supplied by the capture | **ARGUED: VIOLATED today.** M70 measures modulus bands, not complex per-pixel OTFs. |

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** Macro magnification, the teleconverter,
and effective f/33 do not merely change Levin's parameter values. They weaken
the paraxial, geometric, single-layer model used for the comparison. Conversely,
the rig's static subject and many aligned observations do satisfy the broad
premise behind Levin TR Eq. (52): repeated measurements of one latent signal can
be combined.

### 2.4 Independent check of G-edof's `N²` algebra

**DERIVED; VERIFIED-AT-PRIMARY-SOURCE.** G-edof §2.7.1's algebra is correct
*inside Levin's constant-additive-noise model*. Giving every stack frame a full
exposure removes the `1/N` OTF-amplitude factor in Levin TR Eq. (54), so each
power term rises by `N²`. The focal-stack/sweep power ratio becomes

```text
N² |omega| / Omega
```

instead of `|omega|/Omega`.

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** That is not a general physical `N²`
information gain. It changes the acquisition budget from one exposure to `N`
exposures while keeping additive noise variance fixed. In a shot-noise-dominated
regime, signal and photon variance rise together and information scales more
like total photons; in a read-noise-dominated regime the constant-noise algebra
is more relevant. Diffraction and PSF error then reduce the usable band. G-edof
states both caveats, but its ledger shorthand does not.

### 2.5 Claim-1 disposition

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** **Estimator attribution: CONFIRMED.**
**“They conclude against it” without its configuration: OVERSTATED.** Levin et
al. conclude that a focus sweep is better than a separately sampled stack under
a fixed-total-exposure, additive-noise comparison. They neither reject the
estimator nor test the rig's full-exposure stack. The result cannot kill the
workstream by itself.

---

## 3. Claim 2 — the occlusion lineage, oldest first

### 3.1 Four different questions were being collapsed

**ARGUED.** “Occlusion prior art” must be separated into:

1. modelling the shift-variant irradiance near an opaque depth edge;
2. correcting a depth or focused-image estimate with that model;
3. explicitly solving for foreground radiance, background radiance, and opacity;
4. doing item 3 from an ordinary, sequential, single-camera focus stack with
   unknown z spacing and an uncalibrated PSF.

**ARGUED; READ-AT-PROJECT-SOURCE.** G-edof §4.1 says the problem was
*“modelled and inverted—six times.”* The primary sources below establish prior
art for items 1–3 in several different capture systems. They do not establish
that item 4 had already been solved.

### 3.2 Chronological source audit

| Date and citation | What the source actually covers | Does it unmix the rig's two-layer halo? |
| --- | --- | --- |
| **1995 / 1998 — Asada, Fujiwara, Matsuyama.** ICCV 1995, pp. 150–155, DOI `10.1109/ICCV.1995.466793`; *IEEE TPAMI* 20(2):155–167, 1998, DOI `10.1109/34.659933` | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE (abstract only).** Introduces an optical-flux, shift-variant reversed-projection-blurring model for opaque occluding edges. The 1998 abstract predicts a nonmonotonic brightness transition when the hidden surface has its own edge and reports real-image validation. | **ARGUED: NO INVERSION VERIFIED.** This is enough to establish an earlier physical model, but the unavailable body prevents M79 from claiming a layer solver or a focal-stack experiment. |
| **1997 report / 1998 conference — Schechner, Kiryati, Basri.** Technion EE-PUB-1086 (1997), expanded at ICCV 1998, pp. 1061–1066, DOI `10.1109/ICCV.1998.710848`; later IJCV 39(1):25–39, 2000, DOI `10.1023/A:1008166017466` | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE for ICCV; 1997 report TAKEN-FROM-SECONDARY from the ICCV reference list.** A literal through-focus sequence detects two peaks, estimates both depths, and iteratively separates two linearly superimposed semi-reflections using a calibrated PSF and a telecentric, motorised sensor scan. | **ARGUED: ADJACENT, NOT OPAQUE OCCLUSION.** The paper explicitly says it does not address variable opacity because that superposition is nonlinear. It is the missing “1997-ish” focal-stack paper, but it solves transparent addition, not foreground visibility. |
| **2001 — Bhasin and Chaudhuri.** ICCV 2001, vol. 1, pp. 488–493, DOI `10.1109/ICCV.2001.937556` | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Two images at known camera settings; a partially occluded PSF is a truncated kernel. An iterative MRF/MAP scheme updates depth and the all-focused intensity image. On its synthetic step, whole-image RMS changes from 0.0075 to 0.0070 and RMS within ±4 pixels of the boundary from 0.0142 to 0.0080 (Bhasin §5). | **ARGUED: NO.** It repairs the forward kernel and depth estimate. It does not solve separate foreground radiance, background radiance, or opacity, and its evidence is synthetic only. |
| **2005 — McGuire et al.** *ACM TOG* 24(3):567–576, DOI `10.1145/1073204.1073231` | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Explicitly solves for `alpha`, RGB foreground, and RGB background by minimizing three defocus-aware formation equations. Three synchronized, beam-splitter-aligned 640×480 Bayer streams supply nine colour constraints for seven unknowns per pixel. | **ARGUED: YES TO UNMIXING, NO TO TRANSFER.** This is genuine `alpha/F/B` unmixing, but it needs a specialised three-sensor camera, known foreground/background focus planes, calibration, and adjacent video frames to recover hidden background. |
| **2007 — Hasinoff and Kutulakos.** ICCV 2007, pp. 1–8, DOI `10.1109/ICCV.2007.4408898` | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Jointly estimates layered HDR radiance, binary layer mattes, blur diameters, and front-to-back ordering. Its forward model independently blurs each layer and composites it through cumulative defocused occlusion mattes. The solver alternates conjugate-gradient restoration, blur refinement, label changes, ordering search, and inpainting. | **ARGUED: YES TO OPAQUE LAYERS, NO TO THIS STACK.** Inputs are three RAW Canon DSLR images at fixed focus and f/8, f/4 and f/2, with calibrated response and lens attenuation, evaluated at 500×333 output. Boundary quality is qualitative; this is aperture bracketing, not a focus sweep. |
| **2015 — Wang, Efros, Ramamoorthi.** ICCV 2015, pp. 3487–3495, DOI `10.1109/ICCV.2015.398` | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Estimates depth from a light field. At an occluding edge, approximately half the angular views still agree; the edge orientation partitions angular views into visible and occluded halves. | **ARGUED: NO.** It estimates one depth and an occlusion boundary; it does not recover `F`, `B`, or `alpha`. Wang §3 explicitly says the orientation identity is specific to dense planar light fields and does not directly hold for ordinary stereo or general multiview layouts. |

### 3.3 The missing 1997-ish paper is decisive—but not in the way G-edof says

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** The closest old paper to a literal
focus stack is Schechner, Kiryati and Basri's ICCV 1998 paper. Its own reference
19 names the 1997 Technion report. It scans focus by moving a CCD axially,
detects two modes in the focus response, selects the two focused slices, and
iteratively subtracts each layer's predicted blur from the other. Its real
experiment uses a telecentric 75 mm triplet, linear step motor, known sampling,
and an empirically calibrated PSF; the reported reconstruction uses 11
iterations.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** The same paper explicitly limits its
claim to transparent, linearly superimposed layers and excludes an object with
variable opacity. That exclusion is exactly the distinction between a window
reflection and the rig's opaque foreground veil. It therefore proves that
through-focus **two-layer separation** is old while leaving opaque
visibility-changing unmixing open.

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** This distinction also explains why
McGuire 2005 and Hasinoff 2007 need compositing equations instead of the
additive Schechner equations. At an opaque boundary, the foreground matte
changes which aperture rays can reach the background. A convolution of two
independent transparent layers cannot represent that.

### 3.4 What is and is not novel

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE (abstract only).** The bare statement
“first to model the occlusion halo” is false. Asada's 1995/1998 lineage predates
the project and explicitly models the shift-variant blurred occluding edge. The
“28 years” wording corresponds to the 1998 journal extension versus the
project's 2026 milestone date; the 1995 conference version makes the modelling
lineage 31 years old. The chronology is real even though M79 could not inspect
the full Asada derivation.

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** “The exact two-layer problem was already
solved” is too broad. The verified primary record splits as follows:

- Schechner 1998: focus stack plus iterative layer separation, but transparent
  linear addition;
- Bhasin 2001: opaque self-occlusion plus iterative PSF correction, but no layer
  unmixing;
- McGuire 2005: actual `alpha/F/B` unmixing, but a synchronized three-camera
  apparatus;
- Hasinoff 2007: actual opaque multilayer restoration on RAW DSLR data, but
  variable aperture at fixed focus;
- Wang 2015: an occlusion-aware depth decision, not unmixing, and light-field
  geometry only.

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** G-edof proposed mapping Wang's angular
half-view split to “partition frames by through-focus mode.” That mapping is
G-edof's analogy, not Wang's result. Frame index has no edge-orientation
geometry corresponding to Wang's camera plane, and the paper explicitly limits
its construction to light fields.

**ARGUED; search boundary documented in §6.** M79 **did not find** a
primary-source demonstration that takes an ordinary, sequential, single-camera
focus stack with unknown physical z spacing and an uncalibrated PSF and jointly
recovers opaque foreground radiance, hidden background radiance, and a
defocus-varying visibility matte. This is not proof of novelty. It is the
surviving, narrower claim.

### 3.5 Claim-2 disposition

**ARGUED.** **CONFIRMED at the word “model”; OVERSTATED beyond it.** The project
must not claim first physical modelling, first depth-discontinuity correction,
or first two-layer defocus inversion in general. It may accurately say:

> We found no prior primary-source system that performs opaque two-layer
> unmixing inside an ordinary sequential photographic focus stack under this
> rig's uncalibrated capture conditions.

**ARGUED.** Even “first shipping focus-stacking tool” remains a search result,
not a theorem: closed commercial stackers cannot be audited from papers or
source.

---

## 4. Claim 3 — does “do not build iterative deconvolution” follow?

### 4.1 It does not follow from claims 1 and 2

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** Levin TR Eq. (52) is a closed-form
one-shot estimator, and its focal-stack comparison is an exposure-budget
comparison. It says nothing about whether iteration improves a correctly posed
inverse problem.

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** Old occlusion prior art removes a broad
novelty claim; it does not remove engineering value. In fact, Schechner 1998,
Bhasin 2001, McGuire 2005, and Hasinoff 2007 all use iterative optimization or
iterative reconstruction for their structural variants. Claim 2 therefore
cannot logically imply an iteration ban.

**MEASURED; READ-AT-PROJECT-SOURCE.** G-edof's actual evidence for the directive
is its V5 reading of Sage et al. 2017 Table 2—not Levin and not the existence of
occlusion prior art.

### 4.2 Re-reading Sage et al. Table 2 at primary source

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Sage §5.1 uses one synthetic
widefield-microscopy volume: 128 axial views of 512×256 cellular microtubules,
convolved with a theoretical 3-D PSF and corrupted by mixed Gaussian and Poisson
noise. Algorithm parameters were selected by visual assessment, and all
algorithms used non-negativity.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Sage Table 2 reports regularized
inverse filtering at 3.47 dB SNR in 7.0 s and Richardson–Lucy at 3.66 dB in
1661 s. **DERIVED:** the difference is +0.19 dB for 237.3× the runtime. G-edof's
arithmetic is correct for that dataset and that metric.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** The same table does not produce a
metric-independent ranking. FISTA has SSIM `3.87e-2`, above regularized inverse
filtering's `3.41e-2` and Richardson–Lucy's `3.30e-2`, while Richardson–Lucy
wins SNR. RL-TV is below plain RL in SNR and PSNR but slightly above it in SSIM
on this filamentary object.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Sage's own prose says *“the beneficial
effect of deconvolution increases when classical iterative algorithms (LW, RL,
TM) are applied,”* then prices their computation. It also says the object's
thin filaments make TV a poor prior and explicitly warns that the reported
results cannot be used straightforwardly as direct indicators of individual
algorithm performance on other data.

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** G-edof's “they did not pay” is therefore
a defensible engineering reading of **SNR gain per second on one benchmark**,
not the paper's general conclusion. The benchmark has a known 3-D PSF,
transparent additive emission, no opaque occlusion, 16.8 million voxels, and no
focus-stack merge baseline. None of those conditions matches the decision the
blanket directive purports to settle.

### 4.3 Do G-edof, M20, and M70 agree independently?

| Route | What it tests | Mechanism of the negative result | Independence and limits |
| --- | --- | --- | --- |
| **G-edof / Sage 2017** | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** One-shot and iterative 3-D microscopy restoration on one synthetic, known-PSF volume | **DERIVED.** Diminishing SNR return per runtime: +0.19 dB for 237.3× from RIF to RL | **ARGUED.** Independent modality and benchmark, but not a focal-stack merge; ranking changes with metric and object prior. |
| **M20** | **MEASURED; READ-AT-PROJECT-SOURCE.** A gated 1-D simulation using this rig's diffraction-plus-defocus model, Gaussian noise, oracle depth/prior, then a local-SNR mapping on `109MSDCF` | **MEASURED.** Unguarded Wiener loses to argmax by up to 31% RMSE in M20 §5; implementable guarded estimation wins at about 15.1% of one stack's pixels in M20 §7; the OTF cutoff makes some frequencies unrecoverable | **ARGUED.** Different mechanism from Sage. It is one-dimensional, one-subject, no-occlusion, oracle-heavy, and M20 §9 still marks it not independently verified. |
| **M70** | **MEASURED; READ-AT-PROJECT-SOURCE.** Real through-focus modulus spectra over 12 stacks and 1,568 frames; later same-stack comparison with M73 | **MEASURED.** Within ±5 frames, leading singular-value share is 0.9860–0.9983, median 0.9959 (M70 §6.3): nearly scaled copies. Best matched filter over best equal average is 1.1100×, +0.91 dB (M70 §0.3). On M73's two stacks, gate widening closes 74–81% of the gap and weighting adds 1.092–1.096× (M70 §21.4). M70 §19.8 separately finds a one-response model mis-specified on multi-lobed patches. | **ARGUED.** This is the strongest independent route because it uses real rig data and does not assume Levin's exposure budget. It sees modulus in five bands, not phase, and it does not render or score a deconvolved image. |
| **Levin 2009** | **DERIVED; VERIFIED-AT-PRIMARY-SOURCE.** Analytic comparison of a fixed-total-exposure focal stack and focus sweep | **DERIVED.** The stack divides exposure, reducing summed OTF power | **ARGUED.** Not an independent reason to reject this rig's merge and not an iteration comparison. It should not be counted as a fourth vote. |

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE and READ-AT-PROJECT-SOURCE.** The routes
agree in conclusion only after it is narrowed to **“iterative deconvolution has
not earned a place in the core merge.”** Their mechanisms are different:
microscopy compute/regularization economics, M20's noise amplification and
diffraction ceiling, and M70's spectral collinearity, gate reach, and
multi-response mismatch. Different mechanisms make that narrow architectural
decision stronger.

### 4.4 The hidden assumptions they do share

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE and READ-AT-PROJECT-SOURCE.**

1. **Linear blur with no opaque visibility change.** Levin assumes one local
   Lambertian depth; Sage simulates a linearly emitting 3-D volume; M20 §9 says
   no occlusion. M70 measures real scenes, but its matched-filter algebra still
   presumes observations of one common latent signal. M70 §19.8 detects the
   failure rather than solving it.
2. **A known or adequate response.** Levin's OTF is analytic, Sage degrades and
   restores with a theoretical PSF, and M20 uses a model that reproduces selected
   rig optics facts. M70 avoids that assumption only by measuring coarse modulus
   bands; it does not recover complex per-pixel PSFs.
3. **None is the requested end-to-end experiment.** No route runs an iterative,
   occlusion-aware, RAW-CFA estimator on the rig's 22–299-frame stacks against
   the shipped gated merge with a two-sided output metric.

**ARGUED.** The shared assumptions matter in one direction: these results are
strong evidence against spending core-merge complexity on a single-layer
iterative inverse. They are weak evidence against an iterative **layered
occlusion plugin**, because that is the model they omit.

### 4.5 Claim-3 disposition and engineering directive

**ARGUED.** The evidence supports this directive:

> Do not implement RL, RL-TV, Landweber, FISTA, or another iterative
> single-layer deconvolver as the core merge. If deconvolution is pursued, first
> test the guarded one-shot inverse as a plugin. Iterate only after that test
> establishes residual headroom, a validated response model, and a failure that
> iteration is designed to fix.

**ARGUED.** The evidence does **not** support:

> Never build iterative deconvolution.

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** A future opaque-layer solver would not
be “more iterations of the same Wiener filter.” It would introduce visibility,
mattes, ordering, and hidden radiance, as McGuire and Hasinoff do. It should be
judged as an occlusion model, with iteration as a cost, rather than killed by a
single-layer microscopy timing table.

---

## 5. Honest residual: what G-edof missed

1. **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** **Schechner, Kiryati and Basri
   1997/1998 is the substantive miss.** It is the earliest source M79 found that
   literally scans focus, identifies two through-focus modes, and iteratively
   separates two layers. It narrows novelty and supplies a useful ill-conditioning
   result: the two constraints become similar and noise-sensitive at low
   frequencies, then coincide and become non-identifiable at DC. Its
   transparent-addition model, telecentric motorised scan, and calibrated PSF
   prevent direct transfer to the rig.
2. **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Reading Hasinoff 2007 beyond its
   abstract changes the engineering lesson. The paper implements the opaque
   multilayer forward model on three RAW consumer-DSLR captures and explicitly
   alternates radiance, blur, labels, ordering, and inpainting. Its results are
   qualitative and its calibration burden is high, but it is a concrete reason
   not to let a single-layer timing benchmark permanently close an occlusion
   workstream.
3. **ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** No additional microscopy result found
   by M79 overturns M70. The most transferable import is not an iterative core
   merge; it is the **layered compositing forward model as a synthetic control**
   for an occlusion plugin. Bhasin's truncated-PSF boundary case is the cheap
   intermediate control. A full `alpha/F/B` solve should remain behind the
   plugin boundary until those controls show a structural win.

---

## 6. Repeatable search and negative result

### 6.1 Search path

**MEASURED.** M79 followed G-edof's citations forward and backward, then followed
the primary reference lists of McGuire 2005, Hasinoff 2007, Bhasin 2001, and
Schechner 1998. Exact-title and DOI searches were resolved through Crossref,
OpenAlex, and Semantic Scholar. Full texts came from MIT DSpace, the Technion
author page, IIT Bombay DSpace, Harvard DASH, the University of Toronto author
page, CVF Open Access, and the EPFL author-publication server.

**MEASURED.** Repeatable query families:

```text
"reversed projection blurring" occluding edge
"depth from defocus" "partial self occlusion"
"separation of transparent layers" focus
"depth from focus" overlapping objects fractional alpha
defocus matting alpha foreground background
"layer-based restoration" variable aperture occlusion
"focus stack" occlusion alpha layer unmixing
"focal stack" foreground background unmixing
```

**MEASURED.** G-edof's named Asada, Favaro, McGuire, Hasinoff, McCloskey, and
Wang line was checked individually. The separate Schechner citation was found
in McGuire §2 and then obtained at primary source. Searches also checked both
the 1998 conference DOI and the 2000 journal DOI because bibliographic services
attach the same author PDF to both; the PDF M79 read is the six-page ICCV 1998
paper.

### 6.2 Negative result

**ARGUED.** **NOT FOUND within this search:** a primary-source opaque
two-layer-unmixing system operating on an ordinary sequential photographic
focus stack under unknown z spacing and an uncalibrated, spatially varying PSF.
The nearest neighbours each miss one load-bearing property:

- Schechner: correct capture axis, wrong transparent formation model;
- Bhasin: opaque boundary, but kernel correction rather than layer unmixing;
- McGuire: correct unknowns, specialised synchronized camera;
- Hasinoff: correct layered opacity and consumer RAW, wrong aperture-bracket
  capture axis;
- Wang: occlusion-aware decision, not unmixing and not focus diversity.

**ARGUED.** This null preserves a narrow engineering-novelty claim. It does not
restore the broad “first to model an occlusion halo” claim, which is false.

---

## 7. Final answer to the workstream decision

**ARGUED.** The primary-source record strengthens M70's **PLUGIN** verdict but
for a more precise reason than the ledger gives:

1. Levin supplies the exact one-shot estimator and error law, not a general
   rejection; his negative acquisition comparison does not transfer to
   separately exposed rig frames.
2. M20 says a single-layer inverse is noise- and cutoff-limited even with oracle
   help; M70 says the available real spectra are mostly scaled copies and that a
   one-response model fails on multi-lobed patches.
3. Sage says iteration can improve restoration, but on its one benchmark the
   SNR increment over a one-shot regularized inverse is expensive and
   object/metric dependent.
4. The old occlusion literature says the remaining hard problem is a different
   forward model, not more iterations of the same one.

**ARGUED.** Therefore: **do not build iterative single-layer deconvolution as
the core merge. Do not declare iterative structural occlusion unmixing dead.**
If the guarded one-shot plugin shows no residual headroom, stop. If a calibrated
two-layer control shows a structural halo reduction that selection and a
one-shot inverse cannot reproduce, iteration may then be justified as the cost
of the correct model.
