# Workstream G — EDOF Deconvolution: the Microscopy Literature the Project Never Surveyed

Research subagent report, milestone **M19**, 2026-08-23. Fills the gap named in the 2026-08 external review: *"The microscopy/EDOF literature was never surveyed, and it is the one adjacent field that has spent thirty years on exactly this estimation problem."*

Scope: widefield / z-stack deconvolution EDOF; the multi-frame focus-axis Wiener estimator; its failure modes; the two-layer occlusion problem; PSF estimation without a lens model; validation and benchmarks; licences. Companion to `B-algorithms-sota.md` (which surveyed fusion/MFIF/SFF and treated deconvolution only in §7.5), and reconciled throughout against `M20-deconvolution-ceiling-measured.md` and `M21-occlusion-bimodality-measured.md`, which measured the same two proposals in-house.

---

## 0. Verdict

> **Should multi-frame Wiener deconvolution across the focus axis be the core merge, an opt-in post-process, or neither?**

**Opt-in, gated post-merge plugin — not the core merge.** The literature does not overturn `B` §7.5 or M20's disposition. What it *adds* is four independent, externally-measured reasons the guard is load-bearing, two externally-derived reasons the estimator is worth building at all, one settled question about who invented it, and one reframing of priorities that is more consequential than the estimator itself.

### 0.1 Six findings that decide it

| # | Finding | Source | Label |
|---|---|---|---|
| **V1** | **Unregularised inversion is catastrophic, and this is measured, not feared.** On the DeconvolutionLab2 synthetic microtubule benchmark the naive inverse filter scores **SNR −75.45 dB / SSIM 6.29 × 10⁻⁹**; the same pipeline with a regularised inverse filter scores **+3.47 dB / 3.41 × 10⁻²**. A ~79 dB swing turns on the regulariser alone. | Sage et al. 2017, *Methods* 115:28–41, Table 2, DOI `10.1016/j.ymeth.2016.12.015` (full text) | MEASURED |
| **V2** | **Deconvolution measurably *degrades* the axis along which the OTF is weakest.** On a real 2.5 µm bead (λ 530 nm, NA 1.4), acquisition axial FWHM is **3979 nm**; *every* deconvolution setting tested made it **worse** — RIF low/med/high regularisation → 5909 / 4881 / 4900 nm, Landweber 4/64/1024 iterations → 4624 / 4777 / 4449 nm — while lateral FWHM improved at most **3.3%** (2695 → 2605 nm). | Sage et al. 2017, Table 3 (full text) | MEASURED |
| **V3** | **There is a published information-theoretic ceiling and it has the shape of fact 143.** Levin et al. prove the worst-case defocus MTF power over a depth range is bounded by `β(ω)·A³ / (S·|ω|)` with `β ∈ [0.93, 1]` — i.e. it decays as `1/|ω|` — and note that under Fourier optics rather than geometric optics "the budget is no longer equal across spatial frequencies, but **decreases with the diffraction-limited MTF**." Where the diffraction MTF is zero the budget is zero. | Levin, Hasinoff, Green, Durand, Freeman 2009, *ACM TOG* 28(3):1–14, Claim 2 and §3.2, DOI `10.1145/1531326.1531403` (full text) | MEASURED (proved) |
| **V4** | **The exact motivating argument for reconstruction-over-selection is already published, in IEEE TIP, in 2020.** "For **undersampled** image stacks, fusion methods cannot remove the blur in regions where the in-focus position is between two optical sections." That is the reviewer's reframe, stated by someone else, six years ago. | Zhou Xu, Molina, Ma, Wang, Ni 2020, *IEEE TIP* 29:3227–3238, abstract, DOI `10.1109/tip.2019.2957941` (abstract only) | VERIFIED (claim) |
| **V5** | **Nearly all of the achievable gain is available from a one-shot regularised inverse filter.** RIF: 3.47 dB in **7.0 s**. Richardson–Lucy: 3.66 dB in **1661 s**. ~237× the compute buys **+0.19 dB**. Commercial Huygens CMLE scored **below** the 7-second RIF (2.47 dB). | Sage et al. 2017, Table 2 (full text) | MEASURED |
| **V6** | **The exact estimator, applied to the exact capture strategy, is published — in Appendix B of Levin et al.'s tech report, with a closed-form error.** Eq. (52) *is* the proposed formula; Eq. (53) states the reconstruction error is `(σ⁻² Σ_j\|φ̂_j\|² + σ_prior⁻²)⁻¹`, "a function of the sum of power spectra of the individual OTFs"; Eqs. (54)–(57) evaluate it **specifically for a focal stack**. Their conclusion: under additive noise a focus-sweep camera beats the focal stack. **But their model splits one exposure into N bins** — and removing that constraint flips the result (§2.7.1). | Levin, Hasinoff, Green, Durand, Freeman, MIT-CSAIL-TR-2009-019, 8 May 2009, Appendix B, `hdl.handle.net/1721.1/45513` (full text) | MEASURED (derived in-paper) |

### 0.2 What this means for the plan

0. **The formula is not the project's.** V6 settles Q2 decisively: the multi-frame Wiener estimator across a focal stack, complete with the `Σ|H|²` error law, was written down and analysed by Levin et al. in 2009. `SYNTHESIS.md` §6 must not claim it. What is left as the bet is the *calibration* (measured diffraction OTF, photon-transfer σ) and the *scale* — see the ledger in §2.8.
1. **Keep the estimator behind the plugin boundary.** V1 is Fact 141 measured by someone else on a different modality: the guard is what makes deconvolution safe, not an optional third safeguard. V2 says the direction in which the OTF is weakest gets *worse*, not merely "no better" — which is precisely the regime the project sits in above `f_sig = 0.2762 cyc/px` (fact 27).
2. **The aperture change outranks the estimator.** V3 is an independent derivation of the project's own ceiling (fact 143): no merge recovers a band no frame observed, and the budget scales with the diffraction MTF. Fact 144's measured lever — marked f/11 → f/5.6 buys 9.6× contrast at 4-px detail for 2× the frames — moves the ceiling itself. **Every hour spent on the estimator before `captures-needed.md` §0 is executed is an hour spent optimising under a ceiling you could have raised.**
3. **Build it anyway, cheaply, because V5 says it is cheap.** A single regularised inverse filter across the focus axis is one FFT pair per tile and no iteration. If the plugin is 7 seconds rather than 27 minutes, "opt-in" costs almost nothing to offer. Do **not** build RL, RL-TV, Landweber, FISTA or any iterative variant on the strength of this literature: V5 measured them and they did not pay.
4. **The genuinely-new deliverable is not the Wiener merge; it is the occlusion-aware merge — and the novelty claim must be narrowed.** See §4. The two-layer occlusion model has been formulated and inverted at least six times in the vision literature (Asada 1995/1998; Bhasin & Chaudhuri 2001; Favaro & Soatto 2003; McGuire et al. 2005; Hasinoff & Kutulakos 2007; McCloskey et al. 2011), and Wang et al. 2015 give a working remedy for the bimodal case. **"First to model the occlusion halo" is false.** What survives is **"first shipping focus-stacking tool to model it"**, and that is worth stating carefully because a SIGGRAPH paper says the problem is open in general: *"depth estimation can fail, especially next to occlusion boundaries, which present a general problem for all computational extended-DOF systems … While a principled solution to this problem is beyond the scope of this paper, most artifacts can be eliminated with simple manual layer refinement."* (Levin et al. 2009, §5, full text — MEASURED as a statement of the field's practice: their fix is **manual**.)
5. **A calibrated physical simulator with hidden ground truth already exists and should be learned from, not reinvented from scratch.** The EPFL 3-D Deconvolution Grand Challenge (ISBI 2013, ISBI 2014) generated stacks from "a faithful physical description of a widefield digital microscope, combining an advanced PSF model with a noise generator that accounts for **shot noise, electronic noise and quantization**", deliberately withheld the ground truth from entrants, and listed "**PSF-inaccuracy compensation, noise-model calibration and regularization-parameter adjustment**" as explicit hurdles. See §6.4 — its design is directly transplantable; its *data* is microscopy and does not transfer.

### 0.3 The kill experiment, in one paragraph

Run six merge arms on **109MSDCF (22 frames)** and **119MSDCF (33 frames)**: (A) shipped noise-gated merge, (B) plain argmax, (C) plain mean, (D) guarded focus-axis regularised inverse filter with per-frame OTF from the through-focus curve width composed with the measured diffraction OTF and σ from the photon-transfer model, (D′) the same without the diffraction term, (E) the same unguarded. Score **only** on paired metrics that can fail in both directions — gradient *correlation* against a reference plus a flat-ROI noise ratio, never bare `mean |∇|` (fact 145) — restricted to the 15.1% of pixels M20 says are candidates (fact 142) *and* reported over the whole frame, *and* split at the measured cutoff `f_sig = 0.2762 cyc/px`. **Null control:** permute frame order before building the OTFs; the advantage must collapse to ~1.0× (M21's placebo read 1.01×). **Degenerate control, free:** `coffee-bubbles` is 19 frames at *constant* focus (fact 49), so arm D must reproduce arm C exactly or the implementation is broken. **Positive control:** a planted synthetic stack, built Forster-2004 style, where the estimator is known to win; if it does not win there, the harness is broken, not the idea. **Kill criterion, pre-registered:** if D does not beat A on gradient correlation on the candidate pixels below `f_sig` by a margin that survives the permutation null, *or* if D's flat-ROI noise exceeds A's at equal gradient correlation, *or* if the advantage vanishes when the OTF comes from an independent optical model instead of the through-focus curve, the estimator is dead as a merge and stays a plugin. Full design in §8.

---

### 0.4 How to read this report

### Evidence labels (same convention as `B-algorithms-sota.md` §0)

| Label | Meaning |
|---|---|
| **MEASURED** | A number from the cited paper's own experiments. The benchmark is always named. |
| **VERIFIED** | Citation resolved against a primary source (Crossref / OpenAlex / publisher PDF). Per-citation I state **full text** / **abstract only** / **metadata only**. |
| **DERIVED** | Follows by algebra from something MEASURED. The derivation is shown or named. |
| **ARGUED** | A paper's or my own reasoning, with no number attached. Treat as a hypothesis. |
| **UNVERIFIED** | Named from background knowledge and *not* resolved to a primary source. A lead, not a citation. |
| **could not confirm** | I searched and found nothing. Query and source recorded in §10. Not evidence of absence. |

### Method notes

- Every DOI below was resolved live through the **Crossref REST API** (`api.crossref.org/works?query.bibliographic=`) or **OpenAlex** (`api.openalex.org/works/doi:`) during this milestone. Year, venue, volume, pages and author order were read off the API response, not from memory. Where the two disagreed I recorded Crossref.
- Paper bodies were read by fetching the PDF into memory and extracting text with `pypdf`. No PDF was written to disk.
- **Read depth is stated per citation.** Eight sources were read in full or near-full: **Levin et al., MIT-CSAIL-TR-2009-019 (2009)**, Levin et al. 2009 (TOG), Sage et al. 2017 (Methods), Aguet et al. 2008 (TIP), Forster et al. 2004 (MRT), Forster et al. 2004 (ISBI), Nagahara et al. 2008 (ECCV), Wang et al. 2015 (ICCV, skimmed). Everything else is abstract or metadata, and is marked as such. **Nothing is cited from memory.**
- **Modality mismatch is called out inline every time.** Widefield fluorescence microscopy differs from this rig in four ways that matter: (i) the object is *emissive and translucent*, so there is no occlusion and the single-depth-per-pixel model is not merely an approximation but usually correct; (ii) the PSF is 3-D and known analytically from NA/λ/n; (iii) photon counts are often single-digit per voxel; (iv) stacks are 30–200 slices of ≤ 1 MP, not 22–33 frames of 33 MP. Results do **not** transfer automatically.
- **The GPL constraint was honoured.** The EPFL Extended-Depth-of-Field plugin, DeconvolutionLab2 and PSFGenerator are all GPL-3.0 and all on the project's do-not-read list. Only their **papers** were read. No line of their source was opened. Licences in §7 were read from repository metadata (`gh api repos/<owner>/<repo>` → `.license.spdx_id`) and from `LICENSE` files of permissive projects only.
- **Nothing in this report is an in-house measurement.** Every MEASURED row is somebody else's number. The project's own numbers appear only as facts 12/19/23/26/27/28/140–145/150–152, always cited as such.

---

## 1. Q1 — Widefield / z-stack deconvolution EDOF in microscopy: the actual state of the art

### 1.1 The field's structure

Microscopy has two separate lineages that both get called "EDOF", and conflating them is the single biggest source of confusion when reading this literature.

| Lineage | Output | Forward model | Representative |
|---|---|---|---|
| **3-D deconvolution** ("deconvolution microscopy") | A restored **3-D volume**. EDOF is a *projection* afterwards, if wanted at all. | Full 3-D convolution `i(x,y,z) = (o *₃ h)(x,y,z)`. The object occupies the volume. | Agard & Sedat lineage; Richardson–Lucy; DeconvolutionLab2 |
| **2-D EDOF fusion** ("extended depth of focus") | A single **2-D image** (+ optionally a topography map). | Object is a *thin surface*: a texture mapped onto a height field, a Dirac in z. | Forster/Van De Ville/Unser CWT-EDF; Aguet 2.5-D; Zhou Xu 2020 |

**This project is squarely in the second lineage** — an opaque macro subject is a height field with texture, not a translucent volume — and the second lineage is much smaller, much less famous, and much closer to the reviewer's proposal. ARGUED, but it is the reading that makes the rest of the literature legible.

### 1.2 The Agard/Sedat lineage — 3-D widefield deconvolution

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| Agard, "Optical Sectioning Microscopy: Cellular Architecture in Three Dimensions", *Ann. Rev. Biophys. Bioeng.* 13:191–219, 1984, DOI `10.1146/annurev.bb.13.060184.001203` | Founding statement of computational optical sectioning: the z-stack is a 3-D convolution and can be inverted. | VERIFIED | metadata |
| Agard, Hiraoka, Shaw, Sedat, "Fluorescence Microscopy in Three Dimensions", *Methods Cell Biol.* 30:353–377, 1989, DOI `10.1016/s0091-679x(08)60986-3` | The lineage's practical formulation, still the standard citation. | VERIFIED | metadata |
| Streibl, "Three-dimensional imaging by a microscope", *JOSA A* 2(2):121, 1985, DOI `10.1364/josaa.2.000121` | The 3-D OTF of a widefield microscope, and the **missing cone**: a conical region around the `f_z` axis where the 3-D OTF is identically zero. | VERIFIED | metadata |
| Sage et al. 2017, *Methods* 115:28–41, DOI `10.1016/j.ymeth.2016.12.015`, §1 | Restates the anisotropy quantitatively: for DAPI (λ 470 nm), NA 1.4, `n_i` 1.51, lateral resolution `0.61λ/NA ≈ 200 nm` but axial `2n_iλ/NA² ≈ 700 nm`. Deconvolution's stated appeal is that it "combines lateral and axial information". | MEASURED (optical constants) | full text |

**The missing cone is the microscopy name for fact 143.** A widefield 3-D OTF is *exactly zero* over a solid region of frequency space, so `Σ|H|² = 0` there, so no estimator recovers it. Microscopists have lived with this for forty years, and V2 above is what it costs: the axial FWHM of a deconvolved bead got **worse in 6 of 6 settings tested**. DERIVED (from Streibl 1985 + Sage 2017 Table 3).

### 1.3 Richardson–Lucy and its variants — measured, not assumed

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| Richardson, *JOSA* 62(1):55, 1972, DOI `10.1364/josa.62.000055`; Lucy, *Astron. J.* 79:745, 1974, DOI `10.1086/111605` | The EM/ML-Poisson iteration, independently in optics and astronomy. Non-negative by construction, flux-conserving. | VERIFIED | metadata |
| Holmes, "Maximum-likelihood image restoration adapted for noncoherent optical imaging", *JOSA A* 5(5):666, 1988, DOI `10.1364/josaa.5.000666` | Brings ML-Poisson to widefield microscopy explicitly. | VERIFIED | metadata |
| Biggs & Andrews, "Acceleration of iterative image restoration algorithms", *Appl. Opt.* 36(8):1766, 1997, DOI `10.1364/ao.36.001766` | The vector-extrapolation acceleration shipped in essentially every RL implementation since (including `scipy`/`skimage` derivatives). | VERIFIED | metadata |
| Dey et al., "Richardson–Lucy algorithm with total variation regularization for 3D confocal microscope deconvolution", *Microsc. Res. Tech.* 69(4):260–266, 2006, DOI `10.1002/jemt.20294` | RL + TV, the standard regularised RL. | VERIFIED | metadata |
| Laasmaa, Vendelin, Peterson, "Application of regularized Richardson–Lucy algorithm for deconvolution of confocal microscopy images", *J. Microsc.* 243(2):124–140, 2011, DOI `10.1111/j.1365-2818.2011.03486.x` | Regularised RL evaluated on confocal data. | VERIFIED | metadata |
| Verveer & Jovin, "Image restoration based on Good's roughness penalty with application to fluorescence microscopy", *JOSA A* 15(5):1077, 1998, DOI `10.1364/josaa.15.001077` | Good's roughness — a smoothness prior that, unlike TV, does not promote piecewise-constant output. | VERIFIED | metadata |
| Verveer, Gemkow, Jovin, "A comparison of image restoration approaches applied to three-dimensional confocal and wide-field fluorescence microscopy", *J. Microsc.* 193(1):50–61, 1999, DOI `10.1046/j.1365-2818.1999.00421.x` | The field's own early head-to-head comparison. | VERIFIED | metadata |

**The decisive measured comparison** is Sage et al. 2017 Table 2 (synthetic microtubules, 128 slices × 512 × 256, theoretical PSF, mixed Gaussian + Poisson noise, SNR against a known ground truth):

| Algorithm | SNR (dB) | PSNR (dB) | SSIM | Time (s) |
|---|---|---|---|---|
| Naive inverse filter (NIF) | **−75.45** | −49.79 | 6.29e−9 | 7.6 |
| **Regularised inverse filter (RIF)** | **3.47** | 29.13 | 3.41e−2 | **7.0** |
| Tikhonov–Miller (TR) | 2.78 | 28.45 | 2.48e−2 | 6.4 |
| Landweber (LW) | 2.57 | 28.23 | 2.06e−2 | 2107 |
| FISTA | 3.37 | 29.04 | 3.87e−2 | 1400 |
| Tikhonov–Miller iterative (TM) | 2.56 | 28.22 | 2.05e−2 | 2128 |
| **Richardson–Lucy (RL)** | **3.66** | 29.33 | 3.30e−2 | 1661 |
| RL + total variation | 3.36 | 29.03 | 3.34e−2 | 2759 |
| Huygens CMLE (commercial, USD 5–10 k) | 2.47 | 28.13 | 1.84e−2 | 180 |
| **"Learn 2D Apply 3D" (challenge winner)** | **7.27** | 32.94 | 6.73e−2 | 7200 |

MEASURED, full text. Four readings the project should take:

1. **RIF (a regularised inverse filter — i.e. a Wiener-class one-shot) is within 0.19 dB of RL at 1/237 the compute.** The expensive machinery is not where the gain is.
2. **RL+TV is *worse* than plain RL here.** The authors explain why: TV promotes piecewise-constant surfaces and the object is thin filaments. They explicitly warn that the table is not a transferable ranking. A macro subject (chitin, hair, mineral) is not piecewise-constant either. **Do not adopt TV by reputation.**
3. **Commercial Huygens ranked 9th of 10**, below a 7-second free filter, on this benchmark. Commercial ≠ better.
4. **The only method that beat the field by a wide margin (+3.6 dB over RL) was a learned prior**, and it took 2 hours. Soulez, "A 'learn 2D, apply 3D' method for 3D deconvolution microscopy", ISBI 2014, pp. 1075–1078, DOI `10.1109/isbi.2014.6868060` (VERIFIED, metadata). Sage et al.'s own gloss: it "exploit[s] the fact that the resolution is much better within the lateral sections than along the axial direction … it learned from the lateral sections of the acquired volume a dictionary of 2D high-resolution features that are used as priors to enhance the resolution along the axial direction" (full text). **This is a self-supervised, in-stack prior — no external training set.** It is the one learned idea in this literature that transfers cleanly to a photographic stack, where the in-focus frame is exactly the "high-resolution lateral section".

**Caveat the project must apply**: Sage et al. state that parameters were tuned "through visual assessment". The table therefore has a human in the loop and its absolute values should not be treated as an automatic-operation benchmark. ARGUED.

### 1.4 Modern regularised 3-D deconvolution — the three that matter

| Ref | Claim | Label | Read |
|---|---|---|---|
| Arigovindan et al., "High-resolution restoration of 3D structures from widefield images with extreme low signal-to-noise-ratio", *PNAS* 110(43):17344–17349, 2013, DOI `10.1073/pnas.1315675110` | An entropy-based regulariser with kernels exploiting general spatial characteristics, targeted at the regime where "most deconvolution methods perform very poorly at low signal-to-noise ratios". Claims to "push the required dose to extreme low levels". | VERIFIED (claim) | abstract only |
| Lefkimmiatis, Ward, Unser, "Hessian Schatten-Norm Regularization for Linear Inverse Problems", *IEEE TIP* 22(5):1873–1888, 2013, DOI `10.1109/tip.2013.2237919`; Poisson variant `10.1109/tip.2013.2271852`; 3-D Poisson ISBI `10.1109/isbi.2013.6556437` | Second-order TV that does **not** produce the staircase artifact of first-order TV. Third-placed method in the 2014 Grand Challenge per Sage et al. | VERIFIED | metadata |
| Ikoma, Broxton, Kudo, Wetzstein, "A convex 3D deconvolution algorithm for low photon count fluorescence imaging", *Sci. Rep.* 8:11489, 2018, DOI `10.1038/s41598-018-29768-x` | **Directly relevant.** Mixed **Poisson–Gaussian** noise model (shot + read), convex loss, ADMM, Hessian regulariser, and — critically — "**estimates noise parameters on-the-fly, thereby eliminating a manual calibration step required by most deconvolution software**". Demonstrated at "peak intensities of tens of photoelectrons per voxel". | VERIFIED (claim) | abstract only |

**Ikoma 2018 is the closest published match to the project's noise philosophy.** It uses the same Poisson–Gaussian model the project's photon-transfer calibration produces (fact 27 checks the floor against exactly this model to 0.950×), and it treats parameter estimation as part of the algorithm rather than a manual step. The difference is that the project *already has* the calibration and does not need to estimate it on the fly — which is a genuine, defensible advantage over this line. ARGUED.

### 1.5 The EPFL EDOF line — Forster / Van De Ville / Unser (papers only; the code is GPL)

**Licence note, prominent:** the reference implementation of *both* Forster's CWT-EDF and Aguet's 2.5-D method is the **same GPL-3.0 ImageJ plugin** at `bigwww.epfl.ch/demo/edf/`, already on the project's do-not-read list. Only the papers were read. See §7.

#### 1.5.1 Forster et al. 2004 — CWT-EDF is a *selector*, and its own paper measures the selector defect

Forster, Van De Ville, Berent, Sage, Unser, "Complex wavelets for extended depth-of-field: A new method for the fusion of multichannel microscopy images", *Microsc. Res. Tech.* 65(1–2):33–42, 2004, DOI `10.1002/jemt.20092` (full text: Results and targeted passages). Companion: Forster et al., ISBI 2004, vol. 2, pp. 660–663, DOI `10.1109/isbi.2004.1398624` (full text, 4 pp.).

The method: take a complex dual-tree wavelet transform of every slice, and **select the maximum-absolute-value coefficient per subband per location**. It is a transform-domain selector, exactly the family `B` §3 surveyed. Its stated selling point is the absence of a forward model: *"We do not need knowledge of the imaging parameters, such as the point spread function…"* (full text).

**The measurement that matters to this project:**

> **MEASURED:** *"For typical images, ≈30% of the pixels are over or under the original dynamic range of all images"* — a direct consequence of max-abs coefficient selection, which the authors say "boosts the global energy of the image, the noise level, and the amount of saturation."

**This is the project's "out-of-range" confidence signal, measured in 2004 by the people who invented the method.** It is independent, external corroboration of fact 19's thesis (selection injects energy that was not in any frame). Their mitigation — "reassignment", snapping each fused value to the nearest available source value — is MEASURED to "diminish ringing effects". It is also, structurally, a range clamp, i.e. exactly the guard the project would derive from its own noise model.

**Table 1** (four synthetic stacks built from Brodatz textures D18/D22/D23/D112 mapped onto a surface), SNR **gain over the variance method**, dB:

| Post-processing | real spline-3 | complex Daub-6 | complex − real |
|---|---|---|---|
| none | 2.49 | 3.21 | 0.72 |
| reassignment | 2.87 | 3.51 | 0.64 |
| spatial consistency | 3.55 | 3.67 | 0.12 |
| spatial + reassignment | 3.74 | 3.89 | 0.15 |
| subband consistency | 4.14 | 4.50 | 0.36 |
| subband + reassignment | **4.33** | **4.70** | 0.37 |

**Table 2** is the control that fails, and the project should note it: on **real histological tissue**, the variance method scored **26.79 dB** absolute, and **real spline-3 wavelet fusion without post-processing was −0.58 dB *worse* than the variance method**. Complex Daub-6 managed only +0.64 dB. Only with subband consistency + reassignment did the wavelet method reach +2.54 / +3.41 dB. MEASURED, full text.

> **Reading:** the transform-domain advantage over a plain focus measure is **content-dependent and can invert sign on real data.** A synthetic-texture benchmark showed +2.5 to +4.7 dB; the real-tissue benchmark showed −0.58 dB for the same method. This is the same trap `B` §9.3 risk 2 flags for learned MFIF, in a 2004 non-learned method.

Their simulator (a precedent for §6): Brodatz textures or histological tissue mapped onto a surface, linear interpolation along z, each slice convolved with a Gaussian PSF of increasing width, coefficient sum normalised to model Köhler illumination. Real stacks were 1996 × 1450 px, ≈40 images, Zeiss 40×/NA 0.75 and 10×/NA 0.3, z-step 20 µm. **Consistency checks were abandoned on the real stacks for storage and compute cost** (full text) — a scaling failure at 2.9 MP × 40, which is ~11× smaller than this project's workload.

#### 1.5.2 Aguet, Van De Ville & Unser 2008 — the closest published formulation to the reviewer's proposal

Aguet, Van De Ville, Unser, "Model-Based 2.5-D Deconvolution for Extended Depth of Field in Brightfield Microscopy", *IEEE TIP* 17(7):1144–1153, 2008, DOI `10.1109/tip.2008.924393` (**read in full, 10 pp.**). Precursor: ISBI 2006, pp. 778–781, DOI `10.1109/isbi.2006.1625032` (VERIFIED, metadata).

The formulation:

- Object model: a **texture mapped onto a thin surface** — a Dirac in z. Image `i(x,y,z) = (o *₃ h₃D)(x,y,z)`, then sampled.
- **Joint least-squares estimation of texture *and* continuous topography**, alternating updates, interpretable as EM (texture = E-step; topography = the hidden state).
- Topography lives in a **cubic B-spline basis**, optimised coarse-to-fine over dyadic scales with a Brent inverse-parabolic line search. ~5 sub-iterations for topography, 2–3 gradient steps for texture.
- PSF: Gaussian with σ(z) fitted to a Gibson–Lanni scalar model, normalised so each xy-section sums to unity (Köhler), plus an extra normalisation to prevent blow-up as σ → 0.

Three quotations that decide the novelty question in §2:

> **"Compared to classical deconvolution, the texture estimation is much better conditioned since the whole z-stack contributes to its estimation."** — the authors' own name for it is **2.5-D deconvolution**.

> With the separable/simplified PSF model, the texture update is **"essentially a weighted interpolation among the slices of the z-stack around the position indicated by the topography"**, which they relate to **nearest-neighbour deconvolution**.

> **"only the in-focus PSF needs to be precise. Otherwise … the deconvolution of the fusion image is either too weak, or results in out-of-focus information being falsely reallocated to the texture."**

**MEASURED sensitivity, and it is the single most useful number in this report for Q5:**

> **"an error up to 30% on the σ parameter in the PSF model leads to the recovery of the topography without any significant loss in accuracy."**

**MEASURED cost:** 64 s versus 16 s for CWT-EDF — a **4× penalty** for the model-based method. (Stack dimensions for this timing did not extract from the PDF; see §11.)

**A structural fix the project should copy outright:** because the separable texture update is an interpolation among slices, "the possible values for the texture are constrained to the dynamic range of the input volume." That is a *structural* remedy for the exact 30%-out-of-range defect Forster 2004 measured — the estimator cannot invent out-of-range values because its output is a convex combination of observed ones. **DERIVED consequence for this project: a merge expressed as a normalised weighted sum over frames is automatically range-safe; a merge with a `1/Σ|H|²` division is not.** That is a concrete design constraint on the proposed estimator.

**The limitation the authors state themselves, and it is the one that matters here:** the thin-surface model "ignores potential out-of-focus contributions from beneath the surface" — i.e. **one depth per pixel; occlusion is outside the model.** This is Q4's answer for the microscopy lineage: the closest published formulation to the reviewer's proposal explicitly cannot represent the occlusion case.

**Not read:** Table I of this paper (SNR for topography and texture: variance / CWT-EDF / model-based) is an **embedded TIFF image**; its numbers did not extract and I have not read them. Recorded in §11.

#### 1.5.3 Zhou Xu et al. 2020 — the reframe, already published

Zhou Xu, Molina, Ma, Wang, Ni, "Parameter-Free Gaussian PSF Model for Extended Depth of Field in Brightfield Microscopy", *IEEE TIP* 29:3227–3238, 2020, DOI `10.1109/tip.2019.2957941` (**abstract only** — closed access, no OA copy found).

From the abstract, VERIFIED as claims:

- Motivation: **"for undersampled image stacks, fusion methods cannot remove the blur in regions where the in-focus position is between two optical sections."**
- Method: a parameter-free Gaussian PSF model where **the all-in-focus image, the depth map, *and* the in-plane sampling distances are all estimated from the sequence automatically, "without knowledge on the z-stack acquisition"**.
- Optimisation: MAP; iteratively reweighted least squares for the image; adaptive scaled gradient descent for depth and sampling distances.
- Claimed result: "outperforms the current state-of-the-art, mitigating fusion artifacts and recovering sharper edges."

**This is the reviewer's argument, the reviewer's proposed remedy family, and the reviewer's PSF-self-calibration claim, all in one IEEE TIP paper from 2020.** It is the single most important paper for the project's novelty accounting. I could not verify the *measured* numbers (§11).

### 1.6 Learned EDOF — is it genuinely SOTA?

| Ref | Claim | Label | Read |
|---|---|---|---|
| Weigert et al., "Content-aware image restoration: pushing the limits of fluorescence microscopy", *Nat. Methods* 15:1090–1097, 2018, DOI `10.1038/s41592-018-0216-7` | CARE — the reference learned-restoration framework for microscopy. | VERIFIED | metadata |
| Wu et al., "Three-dimensional virtual refocusing of fluorescence microscopy images using deep learning" (Deep-Z), *Nat. Methods* 16:1323–1331, 2019, DOI `10.1038/s41592-019-0622-5` | Refocus a **single** 2-D image to arbitrary planes; generate a virtual z-stack from one exposure. | VERIFIED | metadata |
| Yang et al., "Deep learning-based virtual refocusing of images using an engineered point-spread function", arXiv `2012.11892`, 2020 | Same idea with a designed PSF. | VERIFIED | metadata |
| Manescu et al., "Deep Learning Enhanced Extended Depth-of-Field for Thick Blood-Film Malaria High-Throughput Microscopy", arXiv `1906.07496`, 2019 | Learned EDOF on a real high-throughput clinical pipeline. | VERIFIED | metadata |
| Soulez, ISBI 2014, DOI `10.1109/isbi.2014.6868060` | "Learn 2D, apply 3D" — dictionary learned **from the stack itself**. Won the 2014 Grand Challenge by +3.6 dB over RL. | MEASURED (via Sage 2017 Table 2) | metadata |
| Kim & Naemura, "Blind Depth-variant Deconvolution of 3D Data in Wide-field Fluorescence Microscopy", *Sci. Rep.* 5:9894, 2015, DOI `10.1038/srep09894` | Depth-varying blind deconvolution. | VERIFIED | metadata |

**Assessment (ARGUED):** learned methods hold the top of the one benchmark with hidden ground truth (Soulez, +3.6 dB), and the Nature Methods line is genuinely transformative *for microscopy*, but every one of these is trained on a fixed modality with a fixed PSF and abundant matched training pairs. None of the conditions hold for a macro rig where the OTF changes with every bellows extension (fact 27: `B ∈ [2.41, 3.06]`, known at one magnification only). The one transferable idea is Soulez's: **learn the prior from the in-focus regions of the same stack**, which needs no external dataset and no fixed modality. Consistent with `B` §9.3 risk 2, keep all of it behind the plugin boundary.

---

## 2. Q2 — Is the multi-frame focus-axis Wiener estimator established, and where?

The estimator under evaluation:

```
                SUM_k  H_k*(f) . Y_k(f)
L_hat(f) =  ------------------------------------
            SUM_k |H_k(f)|^2  +  sigma^2 / S(f)
```

**Short answer: the *estimator* is textbook. Its *application* is not, and the boundary is narrow and specific.** Below, the six places it already exists, then the residue.

### 2.1 It is the standard multichannel Wiener filter — 1960s-vintage mathematics

Given `y_k = h_k * x + n_k` with independent noise, the linear MMSE estimate of `x` is exactly the expression above. This is not in dispute and needs no citation beyond a textbook; the project's fact 140 derived it independently by three routes agreeing to 6 decimals. **The novelty cannot be in the formula.** DERIVED.

The relevant published theory is about what happens when you have *several* channels:

> **Harikumar & Bresler, "Perfect blind restoration of images blurred by multiple filters: theory and efficient algorithms", *IEEE TIP* 8(2):202–219, 1999, DOI `10.1109/83.743855`** (VERIFIED, abstract only). "Restoring an image from its noisy convolutions with two or more unknown FIR filters… under some generically true assumptions, **both the filters and the image can be determined exactly in the absence of noise, and stably estimated in its presence**." Subspace- and likelihood-based algorithms; edge effects and "weakly exciting" images examined explicitly.

**This is the theoretical licence for the project's core intuition** — "frames one or two steps off peak carry mid-frequency information the best frame does not". Multiple blurred observations with *distinct* blurs are jointly invertible where any single one is not, because the channels' zero sets do not coincide. The condition — **distinct, co-prime-ish channels** — is exactly what a focus stack provides by construction and what a burst of identical exposures does not. VERIFIED as a claim; I did not read the proofs.

Multichannel blind deconvolution as an applied line: Šroubek & Flusser, *IEEE TIP* 12(9), 2003, DOI `10.1109/tip.2003.815260`; *IEEE TIP* 14(7), 2005, DOI `10.1109/tip.2005.849322`; Šroubek & Milanfar, "Robust Multichannel Blind Deconvolution via Fast Alternating Minimization", *IEEE TIP* 21(4):1687–1700, 2012, DOI `10.1109/tip.2011.2175740`. All VERIFIED, metadata only.

### 2.2 3-D widefield deconvolution — the same idea, one axis over

3-D widefield deconvolution *is* a multi-frame focus-axis inverse problem: every slice of the z-stack constrains every voxel of the object, weighted by the 3-D OTF. Solve it with a Wiener/Tikhonov filter and you have literally the formula above, in 3-D. See §1.2 and Sage et al.'s RIF row. **The project's estimator is the 2.5-D projection of this: collapse the object to one depth per pixel and the 3-D inverse becomes a per-pixel weighted combination across k.** DERIVED. So: established, thoroughly, for forty years — in a modality with no occlusion and a known analytic PSF.

### 2.3 Aguet 2008 — established, in microscopy, as an EDOF *merge*

§1.5.2. The texture update **is** the reconstruction merge: a weighted combination across the z-stack driven by an explicit PSF model and a topography estimate. The authors call it "2.5-D deconvolution" and say the whole z-stack contributes. **The reviewer's proposal, in its "merge = reconstruction, not selection" form, is published, in IEEE TIP, in 2008.** VERIFIED, full text.

### 2.4 Zhou Xu 2020 — established, in microscopy, with self-calibrated PSF

§1.5.3. Adds automatic PSF/sampling estimation from the stack. VERIFIED (abstract), claims not independently checked.

### 2.5 Focal sweep — established as the *equal-weight degenerate case*

| Ref | What it is | Label | Read |
|---|---|---|---|
| Häusler, "A method to increase the depth of focus by two step image processing", *Opt. Commun.* 6(1):38–42, 1972, DOI `10.1016/0030-4018(72)90243-x` | The original: integrate over focus, then deconvolve once with a depth-invariant kernel. Microscopy. | VERIFIED | metadata |
| Pieper & Korpel, *Appl. Opt.* 22(10):1449, 1983, DOI `10.1364/ao.22.001449`; Sugimoto & Ichioka, *Appl. Opt.* 24(14):2076, 1985, DOI `10.1364/ao.24.002076` | Successors in the same integrate-then-deconvolve family. | VERIFIED | metadata |
| **Nagahara, Kuthirummal, Zhou, Nayar, "Flexible Depth of Field Photography", ECCV 2008, LNCS 5305:60–73, DOI `10.1007/978-3-540-88693-8_5`** | Translate the **detector** during one exposure; the integrated PSF becomes "nearly invariant to scene depth", so "the captured image can be deconvolved with a single, known blur kernel". Explicitly "similar in spirit to Häusler's work in microscopy". | MEASURED | **full text** |
| Kuthirummal, Nagahara, Zhou, Nayar, "Flexible Depth of Field Photography", *IEEE TPAMI* 33(1):58–71, 2011, DOI `10.1109/tpami.2010.66` | Journal version. | VERIFIED | metadata |
| Dowski & Cathey, "Extended depth of field through wave-front coding", *Appl. Opt.* 34(11):1859, 1995, DOI `10.1364/ao.34.001859` | The optical-coding alternative: a cubic phase mask makes the OTF depth-invariant, then one deconvolution. | VERIFIED | metadata |

**Nagahara 2008, MEASURED, full text:** prototype 12.5 mm Fujinon f/1.4, 0.36 s sweep, depth range 450–2000 mm ≈ **10× the DOF** of a conventional camera at the same settings. And, importantly for §3: **"Mild ringing artifacts in the computed EDOF images are due to deconvolution."** They name the artifact in their own results.

**Relationship to the project's estimator (DERIVED):** set every `H_k` equal in the formula and it collapses to `Σ_k Y_k` divided by `K|H|² + σ²/S` — i.e. **sum the frames, then deconvolve once.** That is Häusler 1972 / Nagahara 2008 exactly. The project's plain-mean measurement (fact 19: **0.534×** single-frame noise) is the numerator of that degenerate case, already measured in-house. **So the "all OTFs equal ⇒ mean" limb of the reviewer's argument is not a nice property of a new estimator; it is a fifty-four-year-old published method, and the project has already measured its noise behaviour.**

### 2.6 Astronomy — established, and with the hardest version of the problem

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| Schulz, "Multiframe blind deconvolution of astronomical images", *JOSA A* 10(5):1064, 1993, DOI `10.1364/josaa.10.001064` | MFBD proper: many frames, all blurred differently, unknown PSFs, joint estimation. | VERIFIED | metadata |
| Jefferies & Christou, "Restoration of Astronomical Images by Iterative Blind Deconvolution", *ApJ* 415:862, 1993, DOI `10.1086/173208` | The companion foundational paper. | VERIFIED | metadata |
| **van Noort, Rouppe van der Voort, Löfdahl, "Solar image restoration by use of multi-frame blind de-convolution with multiple objects and phase diversity" (MOMFBD), *Solar Phys.* 228:191–215, 2005, DOI `10.1007/s11207-005-5782-z`** | The production solar MFBD system; 500+ citations. | VERIFIED | **metadata only** — no OA copy found |
| Löfdahl, "Multi-frame blind deconvolution with linear equality constraints", *Proc. SPIE* 4792:146, 2002, DOI `10.1117/12.451791` | The constraint machinery MOMFBD is built on. | VERIFIED | metadata |
| Fried, "Probability of getting a lucky short-exposure image through turbulence", *JOSA* 68(12):1651, 1978, DOI `10.1364/josa.68.001651` | The theory behind lucky imaging — the *selection* strategy. | VERIFIED | metadata |
| Law, Mackay, Baldwin, "Lucky imaging: high angular resolution imaging in the visible from the ground", *A&A* 446:739–745, 2006, DOI `10.1051/0004-6361:20053695` | Lucky imaging in practice. | VERIFIED | metadata |
| Harmeling, Hirsch, Sra, Schölkopf, "Online blind deconvolution for astronomical imaging", ICCP 2009, DOI `10.1109/iccphot.2009.5559014`; Hirsch et al., "Efficient filter flow for space-variant multiframe blind deconvolution", CVPR 2010, DOI `10.1109/cvpr.2010.5540158` | Multiframe blind deconvolution brought into the vision community, including the **space-variant** case. | VERIFIED | metadata |

**The structural parallel is exact and the project should say so out loud:** astronomy has been choosing between *selecting* the best frames (lucky imaging) and *reconstructing* from all of them (MFBD) for thirty years, over a stack of frames whose PSFs differ. **In astronomy, reconstruction won for resolution and selection won for robustness and simplicity, and both still ship.** ARGUED — I did not find a single head-to-head measurement, and I am not claiming one exists.

**The disanalogy that matters (DERIVED):** in astronomy the PSF varies *randomly* frame to frame, the object is the same in every frame, and there is no occlusion — a distant star field is a single plane. In a focus stack the PSF varies *systematically and monotonically* along a known axis, which is much more informative, but the object is a 3-D opaque surface, which introduces occlusion (§4). **Astronomy's easier problem is PSF diversity; its harder problem is that the PSFs are unknown. The project has the reverse.**

### 2.7 Computational photography — the 4-D bound and the focal-stack gap

Levin, Hasinoff, Green, Durand, Freeman, "4D Frequency Analysis of Computational Cameras for Depth of Field Extension", *ACM TOG* 28(3):1–14, 2009, DOI `10.1145/1531326.1531403` (**full text**).

**Claim 2, MEASURED (proved):**

```
min_{s in [-S/2, S/2]}  |phi_s_hat(w_x, w_y)|^2   <=   beta(w_xy) . A^3 / (S . |w_xy|)
```

with `β = (|ω| / max(|ω_x|,|ω_y|)) · (1 − min/(3·max)) ∈ [5√5/12, 1] ≈ [0.93, 1]`. **The worst-case defocus MTF power over a depth range `S` falls as `1/|ω|`.** And §3.2: under Fourier rather than geometric optics, "the budget is no longer equal across spatial frequencies, but **decreases with the diffraction-limited MTF**".

Also from the full text, and directly on point for §4:

> **"depth estimation can fail, especially next to occlusion boundaries, which present a general problem for all computational extended-DOF systems [Dowski and Cathey 1995; Nagahara et al. 2008; Levin et al. 2007; Veeraraghavan et al. 2007]. While a principled solution to this problem is beyond the scope of this paper, most artifacts can be eliminated with simple manual layer refinement."**

and, on the forward model:

> "scene radiance is fairly constant over the narrow solid angle subtended by the camera aperture. This assumption is violated by highly specular objects **or at occlusion boundaries**."

and, on the degenerate case again:

> "Our new lattice-focal lens can be thought of as capturing all the images from a special focal stack, shifted and summed together in a single photo."

**Their companion tech report — Levin, Hasinoff, Green, Durand, Freeman, MIT-CSAIL-TR-2009-019, 8 May 2009 — turned out to be the single most important source in this survey, and I obtained and read it** (`hdl.handle.net/1721.1/45513`; PDF and extracted text via the MIT DSpace REST API; **full text**). Its Appendix B is the answer to Q2.

#### 2.7.1 Levin et al., MIT-CSAIL-TR-2009-019, Appendix B — the estimator, applied to the focal stack, in print

**Appendix B is titled "Cameras with multiple measurements"** and opens: *"Many imaging models in the literature, like a focal stack, or a plenoptic camera involve multiple measurements per pixel. Analyzing these cameras requires additional assumptions about the noise model."* They assume additive Gaussian sensor noise, Wiener reconstruction, and a Gaussian zero-mean signal prior, with `N` measurements per spatial frequency, `B̂_j(ω) = φ̂_j(ω)·Î(ω) + n_j`, noise variance `σ²`, signal variance `σ²_ω`. Then, **their Eq. (52)**:

```
                                    1                         1
Iest_hat(w) = argmin  SUM_j  ------- | phi_j_hat(w) Ihat(w) - Bhat_j(w) |^2  +  ------- |Ihat(w)|^2
                                sigma^2                                        sigma_w^2

                 (1/sigma^2) SUM_j  phi_j_hat(w)* . Bhat_j(w)
            =  --------------------------------------------------
                (1/sigma^2) SUM_j |phi_j_hat(w)|^2  +  1/sigma_w^2
```

**This is, character for character, the estimator M19 was asked to assess.** Multiply numerator and denominator by `σ²` and it is `Σ H* Y / (Σ|H|² + σ²/S)`. MEASURED (derived in-paper), full text.

**Their Eq. (53)** gives the expected reconstruction error in closed form:

```
E[ |Iest_hat(w) - Ihat(w)|^2 ]  =  ( (1/sigma^2) SUM_j |phi_j_hat(w)|^2  +  1/sigma_w^2 )^(-1)
```

> *"Eq. (53) states that the reconstruction error is a function of the sum of power spectra of the individual OTFs."*

**This is the project's `Σ|H|²` guard, as an error law rather than a heuristic** — and it is the cleanest possible statement of fact 143: as `Σ_j|φ̂_j(ω)|² → 0`, the error tends to `σ²_ω`, i.e. the prior variance, i.e. you learn nothing about that frequency. Not "the estimator becomes unstable"; *the estimator returns the prior*. MEASURED (derived in-paper).

They also insert a warning the project should quote verbatim in code comments:

> *"Note that this suggests how to merge multiple independent measurements of the same spatial frequency, and **should not be confused with summing multiple elements of a single measurement**."*

**Then they evaluate it for a focal stack specifically (Eqs. 54–57).** Splitting the exposure into `N` time bins with focus spread evenly over the depth range, the bin-`j` OTF is `φ̂_s(ω) = (A²/N)·sinc(Aω_x(s_j−s))·sinc(Aω_y(s_j−s))` (Eq. 54); integrating over slopes gives `E[|φ̂_s(ω)|²] = (1/N²)·A³/(S|ω_xy|)` (Eq. 55); summing over `N` bins gives `Σ_j|φ̂_j,s(ω)|² = (1/N)·A³/(S|ω_xy|)` (Eq. 56); and with the minimum non-aliasing bin count `N = ASΩ` (Ω = the band limit),

```
SUM_j |phi_hat_j,s(w)|^2  =  A^2 / ( S^2 . Omega . |w_xy| )        (Eq. 57)
```

versus a focus-sweep camera's `A²/(S²|ω_xy|²)`. Their conclusion, MEASURED (derived in-paper):

> *"Since |ω_xy| < Ω … the reconstruction error of a focus sweep camera which measures different focus depths simultaneously is better than the focal stack approach which measures each focus depth separately."*

**The ratio is `|ω_xy| / Ω` — the focal stack is worse, and worst at low frequencies.**

##### The exposure assumption, and why it flips for this project

**DERIVED (my algebra, from their Eqs. 54–57 — not a result they state):** the entire disadvantage is the **`1/N` exposure split**. Levin et al. hold *total* exposure time fixed, so each bin collects `1/N` of the light and Eq. (54) carries an explicit `A²/N`, contributing the `1/N²` in Eq. (55). A photographic focus stack of a static subject does **not** operate under that constraint: each of the 22 or 33 frames is a **full-length exposure**. Dropping the `1/N`:

```
E[|phi_hat_s|^2]        =  A^3 / (S |w_xy|)                      (Eq. 55 without the 1/N^2)
SUM_j |phi_hat_j,s|^2   =  N . A^3 / (S |w_xy|)                  (Eq. 56 without the 1/N)
with N = A.S.Omega:     =  A^4 . Omega / |w_xy|

ratio to focus sweep    =  [A^4 Omega / |w|] / [A^2 / (S^2 |w|^2)]  =  A^2 . Omega . S^2 . |w|
                        =  N^2 . |w_xy| / Omega
```

**So the ordering inverts by exactly `N²`.** At `N = 22` the focal stack's summed OTF power exceeds the equal-total-exposure focus sweep's by `484·|ω|/Ω`, which is > 1 for every frequency above `Ω/484`. **The one published analysis that evaluates this exact estimator on this exact capture strategy concludes against it — and it concludes against it for a reason that does not apply here.** This is the strongest single argument in the literature *for* the reviewer's proposal, and it is stronger than the argument the reviewer gave.

Two caveats that must travel with it, both ARGUED: (i) `N² ` gain assumes read noise dominates and the frames are independent — with shot-noise-dominated pixels the scaling is weaker; (ii) their `sinc` OTF is a geometric-optics pillbox aperture with **no diffraction**, and §3.2 of the same work says that under Fourier optics the budget "decreases with the diffraction-limited MTF". At marked f/11 → optical f/33 (fact 28) that reduction is total above `f_sig = 0.2762 cyc/px` (fact 27). **`N²` more of zero is zero.** The two corrections push in opposite directions and neither is quantified here.

Also worth noting from the same TR (full text): their prototype's minimum subsquare size "is limited by diffraction. Since a normal lens starts being diffraction-limited around an f/12 aperture [Goodman 1968]" — a computational-photography paper treating **f/12** as the onset of diffraction limitation, while this rig's *effective* aperture is f/27–f/33 at marked f/11 (fact 28). MEASURED (as their design constant).

Related computational-photography EDOF, all VERIFIED (metadata): Levin, Fergus, Durand, Freeman, coded aperture, SIGGRAPH 2007, DOI `10.1145/1276377.1276464`; Zhou & Nayar, "What are Good Apertures for Defocus Deblurring?", ICCV 2009, DOI `10.1109/iccv.2009.5459268`, and IJCV 2010, DOI `10.1007/s11263-010-0409-8`; Cossairt, Zhou, Nayar, "Diffusion coded photography for extended depth of field", SIGGRAPH 2010, DOI `10.1145/1833349.1778768`; Hasinoff & Kutulakos, "Light-Efficient Photography", ECCV 2008, DOI `10.1007/978-3-540-88693-8_4`, TPAMI 2011, DOI `10.1109/tpami.2011.62`.

### 2.8 The novelty ledger — what is old, what is the bet

**This section exists because the project labels novelty claims as bets and needs to know exactly which part is the bet.**

| Component | Status | Prior art |
|---|---|---|
| The multichannel Wiener/MMSE formula itself | **OLD** — textbook | linear estimation theory; project fact 140 re-derived it |
| **That formula written down explicitly as the merge of a focal stack, with its `Σ\|H\|²` error law** | **OLD** — and this is the decisive one | **Levin et al., MIT-CSAIL-TR-2009-019, 2009, Appendix B, Eqs. (52)–(57)**, `hdl.handle.net/1721.1/45513` |
| "Multiple differently-blurred observations are jointly invertible where one is not" | **OLD** — proved | Harikumar & Bresler 1999, `10.1109/83.743855` |
| Deconvolving a focus stack as a 3-D inverse problem | **OLD**, 40 years | Agard 1984; Agard et al. 1989; Sage et al. 2017 |
| Collapsing that to one depth per pixel and calling the result an EDOF **merge** | **OLD** | Aguet, Van De Ville, Unser 2008, `10.1109/tip.2008.924393` |
| "All OTFs equal ⇒ the estimator is the mean, then deconvolve once" | **OLD**, 54 years | Häusler 1972; Nagahara et al. 2008 |
| "Where one OTF dominates, it collapses to selection" | **OLD** — an algebraic property of the same formula | as above |
| Self-calibrating the PSF from the stack itself for EDOF | **OLD** | Zhou Xu et al. 2020, `10.1109/tip.2019.2957941` |
| Many frames, differing PSFs, joint reconstruction vs. selecting the best | **OLD**, 30+ years | Schulz 1993; van Noort et al. 2005 vs. Fried 1978; Law et al. 2006 |
| An information-theoretic ceiling on what any EDOF method can recover | **OLD** | Levin et al. 2009 Claim 2 |
| **The observation that Levin's focal-stack verdict rests on a fixed-total-exposure assumption that a static macro subject does not impose, and inverts by `N²` without it** | **Possibly new — no prior statement found**, but it is three lines of algebra on a published equation, so claim it as an *observation*, never as a contribution | §2.7.1; §10 |
| **Composing the per-frame defocus OTF with a *measured* diffraction OTF from the actual composed optical path (bellows factor `B`, fact 27/28) rather than an assumed lens model** | **The bet — no prior art found** | §10 negative-search log |
| **Driving the regulariser with a *calibrated photon-transfer* σ per pixel rather than a tuned scalar** | **The bet — no prior art found.** Ikoma 2018 is nearest but *estimates* rather than pre-calibrates | `10.1038/s41598-018-29768-x` |
| **Doing this as the merge of a 22–33 frame × 33 MP CFA-native photographic stack** | **The bet** — every cited system is ≤ 3 MP microscopy or ≤ 3-frame photography | §10 |
| **A structural two-layer occlusion fix inside a shipping stacker** | **Partly the bet.** The *model* is old (§4). "First shipping stacking tool to model it" is the defensible form | §4 |

**Honest summary (ARGUED):** *nothing in the estimator is new; the bet is entirely in the calibration and the scale.* That is a defensible bet — the project's fact 27 measurement of a real optical cutoff and its photon-transfer floor check at 0.950× are things none of the cited papers had — but it must be stated as engineering novelty, not algorithmic novelty. **If M19 changes one sentence in `SYNTHESIS.md` §6, it should be the sentence that claims the Wiener merge is novel.**

---

## 3. Q3 — The failure modes, in detail

Sage et al. 2017 §4.3 names the canonical three for the whole field: **noise amplification, ringing (Gibbs/Runge), and aliasing** (full text). The project's list adds two more that microscopy mostly does not have: **OTF misestimation** and **depth discontinuity**. Taken in turn.

### 3.1 Noise amplification where `Σ|H|²` is small

**Detection.** Trivial in simulation (SNR against truth), hard on real data. The field's own answer is the one the project already uses: a **flat-region variance check**. What the field actually does, per Sage et al. §5, is worse — parameters are tuned "through visual assessment" (full text). ARGUED: this is a weakness of the microscopy literature, not a model to copy.

**Magnitude, MEASURED.** NIF −75.45 dB vs RIF +3.47 dB, Sage et al. Table 2. Roughly **79 dB** separates the guarded from the unguarded filter on the same data with the same PSF. The project's fact 141 measured the same effect in a different unit: unguarded Wiener loses to argmax by up to **31% RMSE** even with oracle depth *and* oracle prior (σ = 0.03: 0.0825 vs 0.0628). **Two independent measurements, different fields, same conclusion: the `Σ|H|²` guard is not a refinement, it is the difference between working and not.**

**Mitigation, and its cost in resolution.**

| Regulariser | Reference | Cost in resolution | Label |
|---|---|---|---|
| Tikhonov / Wiener `σ²/S(f)` | Sage et al. Table 2 (RIF, TR rows) | Isotropic low-pass. At λ = 0 both RIF and TR **reduce exactly to NIF** (Sage et al., full text) — the regularisation *is* the whole method. RIF 3.47 dB vs RL 3.66 dB ⇒ the smoothing costs ≈ **0.19 dB** here. | MEASURED |
| Total variation | Rudin, Osher, Fatemi, *Physica D* 60:259–268, 1992, DOI `10.1016/0167-2789(92)90242-f`; Dey et al. 2006, DOI `10.1002/jemt.20294` | **Staircasing** — promotes piecewise-constant regions. MEASURED to *hurt* on filaments: RL-TV 3.36 dB vs RL 3.66 dB (Sage Table 2). | MEASURED |
| Hessian–Schatten (2nd-order TV) | Lefkimmiatis, Ward, Unser, *IEEE TIP* 22(5):1873–1888, 2013, DOI `10.1109/tip.2013.2237919` | Designed precisely to remove staircasing; placed 3rd in the 2014 challenge. | VERIFIED, metadata |
| Good's roughness | Verveer & Jovin 1998, DOI `10.1364/josaa.15.001077` | Smoothness without the piecewise-constant bias. | VERIFIED, metadata |
| Entropy-type | Arigovindan et al. 2013, DOI `10.1073/pnas.1315675110` | Targeted at extreme low SNR. | VERIFIED, abstract |
| **Early stopping** | Sage et al., full text | The field's most-used regulariser in practice: iteration count acts as one; the advice is literally "stop before noise dominates". Landweber 4 → 1024 iterations in Table 3 moves axial FWHM 4624 → 4449 nm and lateral 2714 → 2605 nm — i.e. **more iterations kept improving both** on a bead, which is *not* what the folklore predicts. | MEASURED |
| **Non-negativity** | Sage et al., full text | Cancels undershoot **only**. Does not stop overshoot or noise amplification. | MEASURED (qualitative) |
| **Range clamping to the observed dynamic range** | Forster et al. 2004 ("reassignment"), DOI `10.1002/jemt.20092`; structurally free in Aguet 2008 | MEASURED to "diminish ringing effects" in Forster; +0.37 to +0.64 dB in Table 1. Costs nothing in resolution because it only touches out-of-range pixels. | MEASURED |

> **Recommendation, ARGUED:** for this project, the ranking implied by the literature is **(1) range clamping — free, measured to help; (2) Tikhonov/Wiener with the calibrated σ — measured to be within 0.19 dB of the best; (3) nothing else until (1) and (2) have been measured on real stacks.** Do not adopt TV: Sage Table 2 measured it losing on a non-piecewise-constant object.

### 3.2 Ringing at edges — including at occluding edges

**Mechanism, MEASURED (Sage et al. §4.3.1, full text):** two distinct sources, and they need different fixes.

1. **FFT circular periodicity** ⇒ **ghosts**: structure at one boundary wrapping to the other. Fix: **zero-padding** (keeps the data intact, costs compute) or **apodization** (Cosine, Hamming, Hann, Tukey, Welch — "cancels the ghosts but reduces the intensity of the data"; DeconvolutionLab2 lets the axial and lateral apodizations be chosen independently).
2. **Band-limiting** ⇒ **Gibbs/Runge ringing** at sharp edges. This one is intrinsic: the estimate is band-limited and a step is not.

**And a directly transferable warning, MEASURED:** *"Fourier-related artifacts frequently appear, particularly in the axial direction since this direction is often sampled to a lesser extent than the lateral ones."* **The under-sampled axis is where the ringing lives.** For this project the under-sampled axis is the focus axis: 22–33 frames against 7032 × 4688 pixels. DERIVED: expect the artifacts to appear *along the focus axis*, i.e. as depth-direction reallocation of energy near depth steps — which is the occlusion-halo geometry.

Other named treatments, VERIFIED (metadata only):

- Liu & Jia, "Reducing boundary artifacts in image deconvolution", ICIP 2008, DOI `10.1109/icip.2008.4711802`.
- Šorel, "Removing Boundary Artifacts for Real-Time Iterated Shrinkage Deconvolution", *IEEE TIP* 21(4):2329–2334, 2012, DOI `10.1109/tip.2011.2176344`.
- Cho, Wang, Lee, "Handling outliers in non-blind image deconvolution", ICCV 2011, DOI `10.1109/iccv.2011.6126280` — **the closest analogue to occlusion**: model the pixels that violate the forward model as outliers rather than trying to fit them. Recommended as the cheap fallback if the two-layer model of §4 proves too expensive.
- Yuan, Sun, Quan, Shum, "Progressive inter-scale and intra-scale non-blind image deconvolution", SIGGRAPH 2008, DOI `10.1145/1360612.1360673` — an explicitly ringing-suppressing multiscale schedule.

And from Nagahara et al. 2008, MEASURED on a real prototype: **"Mild ringing artifacts in the computed EDOF images are due to deconvolution."** Even with a deliberately depth-invariant, *known* kernel, ringing survived. DERIVED: ringing is not a symptom of a bad PSF estimate; it is what deconvolution does.

### 3.3 Sensitivity to OTF misestimation

**The one hard number in the literature, MEASURED:** Aguet et al. 2008 — *"an error up to 30% on the σ parameter in the PSF model leads to the recovery of the topography without any significant loss in accuracy."* (full text). Note carefully what is claimed: **topography** is robust to 30% σ error. The paper does **not** extend that tolerance to the texture, and in fact says the opposite about the in-focus slice:

> *"only the in-focus PSF needs to be precise. Otherwise … the deconvolution of the fusion image is either too weak, or results in out-of-focus information being falsely reallocated to the texture."*

**DERIVED, and this is a design directive:** the accuracy budget is **highly asymmetric along k**. The OTF of the frame at or near the peak must be right; the OTFs of frames several steps away can be sloppy. That is convenient, because the through-focus curve is best resolved near its peak — which is exactly where the reviewer's self-calibration proposal (§5) is most reliable.

Two corroborating structural facts:

- Sage et al. §6.1 (full text): blind deconvolution suffers a **scale degeneracy** — `(a·h) * (x/a) = h * x` for any `a` — so PSF norm is unidentifiable without a constraint, and "setting a meaningful value to ‖h‖ is highly nontrivial". **DERIVED for this project:** a PSF width estimated from a *normalised* through-focus curve inherits this ambiguity unless the normalisation is pinned — e.g. by Köhler-style unit-sum normalisation per frame, which is exactly what both Forster 2004 and Aguet 2008 do.
- Sage et al. §5 (full text): an **experimental** PSF (averaged z-stacks of ~100 nm beads) is not automatically better than a theoretical one — "the resolution of an experimental PSF is tied to the resolution of the acquisition". A measured PSF at 33 MP inherits the sensor's own sampling limits.

### 3.4 Depth discontinuity — where the forward model is simply wrong

**The literature's honest position, MEASURED as a statement of practice.** Three sources, all read in full:

1. **Levin et al. 2009** (SIGGRAPH): occlusion boundaries "present a general problem for all computational extended-DOF systems"; "a principled solution to this problem is beyond the scope of this paper"; their fix is **"simple manual layer refinement"**.
2. **Nagahara et al. 2008** (ECCV): *"While computing images with extended DOF, we have not explicitly modeled occlusions at depth discontinuities"* — they then ARGUE that depth-invariance makes boundaries approximately fine. They do not measure it.
3. **Aguet et al. 2008** (TIP): the thin-surface model "ignores potential out-of-focus contributions from beneath the surface".

**So: the three most relevant papers in three different fields each state that the depth-discontinuity case is outside their model.** That is the strongest available support for the project's judgement that a structural occlusion fix is where the real headroom is — stronger than any argument about the estimator. VERIFIED, all three read in full.

**Space-varying deconvolution — the cost, MEASURED (Sage et al. §6.2, full text):**

- *"space-varying deconvolution is an oxymoron"* — the whole FFT machinery presupposes shift-invariance.
- Cost rises "as the square of the number of voxels" without the FFT.
- The **depth-only-varying** case is tractable (a per-depth PSF, blockwise), which is the tractable subset the project actually needs.
- On space-varying **blind** PSF inference: *"only one attempt has been done."*

**DERIVED budget note:** FFT is measured at ~**95%** of RL runtime in DeconvolutionLab2 (2 × 2520 ms of ~2651 ms per iteration; Sage et al., full text). Any tiled/blockwise space-varying scheme multiplies the FFT count by the tile count. At 33 MP this is the dominant cost and should be budgeted before it is designed.

### 3.5 The failure-mode table, condensed

| Failure | Detect | Mitigate | Cost | Best source |
|---|---|---|---|---|
| Noise amplification | flat-ROI variance ratio (project rule 9); SNR in simulation | Wiener/Tikhonov with calibrated σ; the `Σ\|H\|²` guard | ~0.19 dB vs RL | Sage Table 2 (MEASURED) |
| Boundary ghosts | wrap-around structure at tile edges | zero-padding (compute) or apodization (intensity loss) | compute or contrast | Sage §4.3.1 (MEASURED) |
| Gibbs/Runge ringing | overshoot beyond the observed range | range clamp to observed dynamic range ("reassignment"); non-negativity (undershoot only) | ≈ free | Forster 2004 (MEASURED) |
| PSF width error | — | keep the near-peak OTF accurate; tolerate the tails | 30% σ error tolerable for topography | Aguet 2008 (MEASURED) |
| PSF scale degeneracy | — | pin ‖h‖ by unit-sum normalisation per frame | none | Sage §6.1 (MEASURED) |
| Axial/focus-axis artifacts | check the *under-sampled* axis first | axis-specific apodization | intensity loss | Sage §4.3.1 (MEASURED) |
| Depth discontinuity | bimodal through-focus curve (project fact 150: 4.38× enrichment) | two-layer model (§4); or outlier-robust loss | model complexity | Levin 2009; Cho 2011 |
| Model wrong at boundary | — | **the field's actual answer is manual retouching** | human time | Levin 2009 (MEASURED practice) |

---

## 4. Q4 — The two-layer / occlusion problem

The model in question:

```
I_k  =  alpha_k . (F conv PSF_k)  +  (1 - alpha_k) . (B conv PSF_k)
```

with a **bimodal** through-focus curve at veiled background pixels. The project measured that bimodality in M21: **4.38× enrichment at depth steps on `coffee-bean`** (19.4% vs 4.4%), against a frame-permutation placebo at **1.01×**, surviving every intensity-gradient quintile (pooled ~2.7×, up to 9.5–14.3×), with intensity edges alone giving **0.00×** (fact 150).

### 4.1 Yes, it has been modelled and inverted — six times, in four communities

| Ref | What it does | Does it work? | Label | Read |
|---|---|---|---|---|
| **Asada, Fujiwara, Matsuyama, "Edge and Depth from Focus", ICCV 1995, DOI `10.1109/iccv.1995.466793`; *IEEE TPAMI* 20(2):155–167, 1998, DOI `10.1109/34.659933`** | **Reversed projection blurring (RPB)** model of blurred occluding edges. States "**an object surface behind a nearer object is partially observable beyond the occluding edges**", and discusses "a limitation of the image blurring model using the convolution". Names two phenomena: (i) a blurred occluding edge produces the same brightness profile as a surface edge on the occluder when the occluded radiance is uniform — **an identifiability failure**; (ii) **"a nonmonotonic brightness transition would be observed in blurred occluding edge profiles when the occluded object has a surface edge."** | Validated on real images per the abstract. | VERIFIED | abstract only |
| Bhasin & Chaudhuri, "Depth from defocus in presence of partial self occlusion", ICCV 2001, DOI `10.1109/iccv.2001.937556` | DfD with partial self-occlusion explicitly modelled. | not verified | VERIFIED | metadata |
| **Favaro & Soatto, "Seeing beyond occlusions (and other marvels of a finite lens aperture)", CVPR 2003, DOI `10.1109/cvpr.2003.1211519`** | Reconstructs geometry **and** photometry with occlusions from defocused images: "**the presence of a finite lens aperture allows us to recover portions of the scene that would be occluded in a pin-hole projection**"; estimates each object's surface *including occluding boundaries* and radiance *including occluded portions*. | Claimed; numbers not read. | VERIFIED | abstract only |
| McGuire, Matusik, Pfister, Hughes, Durand, "Defocus video matting", *ACM TOG* 24(3):567–576, 2005, DOI `10.1145/1073204.1073231` | Pulls a **matte** — i.e. solves for `α`, `F` and `B` — using *differences in defocus* between synchronised cameras as the cue. This is the two-layer equation above, solved, with video results. | Shipped as a matting system. | VERIFIED | metadata |
| **Hasinoff & Kutulakos, "A Layer-Based Restoration Framework for Variable-Aperture Photography", ICCV 2007, DOI `10.1109/iccv.2007.4408898`** | "Simultaneously account for defocus, high dynamic range exposure (HDR), and noise", producing "**a layered decomposition of the scene that models occlusion effects in detail**", from the 3-image aperture bracket available on consumer DSLRs. | Claimed on consumer-camera data. | VERIFIED | abstract only |
| McCloskey, Langer, Siddiqi, "Removal of Partial Occlusion from Single Images", *IEEE TPAMI* 33(3):647–654, 2011, DOI `10.1109/tpami.2010.187` (also ICPR 2010 `10.1109/icpr.2010.1069`; ACCV 2007 `10.1007/978-3-540-76386-4_25`) | Removes a defocused foreground occluder from a single image. | Claimed. | VERIFIED | metadata |

Plus the matting and light-field lines that bound the problem:

- Levin, Lischinski, Weiss, "A Closed-Form Solution to Natural Image Matting", *IEEE TPAMI* 30(2):228–242, 2008, DOI `10.1109/tpami.2007.1177` (VERIFIED, metadata). The reference matting formulation; its **colour-line** local model is what makes `α` tractable without a forward optical model. Directly usable for regularising `α_k`.
- Vaish, Szeliski, Zitnick, Kang, Levoy, "Reconstructing Occluded Surfaces Using Synthetic Apertures: Stereo, Focus and Robust Measures", CVPR 2006, DOI `10.1109/cvpr.2006.244` (VERIFIED, metadata). **Robust statistics (median, entropy) instead of the mean across the aperture** to see through partial occluders — the cheap alternative to explicit unmixing.
- **Wang, Efros, Ramamoorthi, "Occlusion-aware depth estimation using light-field cameras", ICCV 2015, DOI `10.1109/iccv.2015.398`** (open-access PDF at `openaccess.thecvf.com/content_iccv_2015/papers/Wang_Occlusion-Aware_Depth_Estimation_ICCV_2015_paper.pdf`, VERIFIED, skimmed); TPAMI extension `10.1109/tpami.2016.2515615`. The central insight: **at an occlusion boundary the angular patch is bimodal and splitting it by the local edge orientation restores unimodality in each half.** This is M21's bimodality, in the light-field domain, with a working remedy.
- Agarwala et al., "Interactive digital photomontage", *ACM TOG* 23(3):294–302, 2004, DOI `10.1145/1015706.1015718` (VERIFIED, metadata) — the graph-cut + gradient-domain composite that most stackers' seam handling descends from. It is a *labelling* fix, not an unmixing one.

### 4.2 The honest answer to "would a structural occlusion fix be a first?"

**"First to model the occlusion halo" is FALSE.** Asada et al. modelled blurred occluding edges in 1995–98, including the non-monotonic (bimodal) brightness transition the project measured in M21 — **prior art for fact 150 exists and predates it by 28 years, and the project should cite it rather than be corrected by a reviewer later.** Favaro & Soatto inverted it in 2003, McGuire et al. solved the matting form in 2005, Hasinoff & Kutulakos built a layered restoration framework in 2007, McCloskey et al. removed occluders in 2011, and Wang et al. gave a working occlusion-aware remedy for the bimodal case in 2015.

**"First shipping focus-stacking tool with a structural occlusion model" is PLAUSIBLE and is the form the claim should take.** Supporting evidence, in decreasing strength:

1. **MEASURED practice:** Levin et al. 2009, a SIGGRAPH paper by five of the field's leading authors, says occlusion boundaries "present a general problem for **all** computational extended-DOF systems", cites four systems as sharing it, and reports that their own fix is **manual layer refinement**. If a principled fix were shipping anywhere in 2009, that sentence would not read that way.
2. **MEASURED absence:** Aguet 2008 — the closest published EDOF reconstruction — states the model ignores contributions from beneath the surface. Nagahara 2008 states occlusion is not modelled.
3. **could not confirm** — I did not audit the source of every shipping stacker (Helicon Focus and Zerene Stacker are closed-source; `PetteriAimonen/focus-stack` is MIT and on the project's safe list but I did not read it in this milestone). **The claim should therefore be phrased as "we know of no stacking tool that does this" and not as "no stacking tool does this."** Query log in §10.

### 4.3 What the project should actually build, per this literature

**ARGUED, but grounded in the six papers above:**

1. **Detect first, unmix second.** M21 already has the detector (fact 150) and — critically — fact 151 says the detector is *unusable without the noise model* (permutation null: noise alone flags 60–98% of pixels as multi-peaked). Wang et al. 2015 is the precedent that detection + a local split is enough to fix the estimate; full `α, F, B` unmixing (McGuire, Hasinoff) is the expensive version.
2. **Split by edge orientation, do not solve for `α` blind.** Wang et al. 2015's remedy is cheap: at a detected boundary, partition the observations by the local edge direction and estimate from the consistent half. This maps directly onto the focus axis: **partition the frames by which mode of the through-focus curve they belong to, and merge within the mode.** No matting solve, no extra unknowns.
3. **Use robust statistics as the fallback** (Vaish et al. 2006): a median or trimmed combination across k instead of a weighted mean is a one-line change with published support.
4. **Respect fact 152.** Bimodality was *invisible at `WINDOW_RADIUS = 13`* (enrichment 0.36×, i.e. depleted) and appeared only at radius 2. Any unmixing must operate at the small-window scale; a large-window formulation will silently have nothing to work with.
5. **Regularise `α` with the matting Laplacian** (Levin et al. 2008) if full unmixing is ever attempted, rather than inventing a smoothness term.

---

## 5. Q5 — PSF estimation without a lens model

**The reviewer's claim under test:** *per-frame OTF widths can be self-calibrated from the through-focus response curve itself, since its width IS the local PSF scale sampled by the operator.*

### 5.1 Verdict on the claim

**Sound in principle, with two named caveats, and it has been done.** ARGUED, with support below.

**Support 1 — it is published.** Zhou Xu et al. 2020 (`10.1109/tip.2019.2957941`, abstract only) estimate the all-in-focus image, the depth map **and the z-sampling distances** jointly from the sequence, "without knowledge on the z-stack acquisition", with a "parameter-free Gaussian PSF model". That is exactly self-calibration of the defocus scale from the stack.

**Support 2 — the accuracy required is low.** Aguet et al. 2008 MEASURED that **a 30% error in the PSF σ costs no significant accuracy** in the recovered topography (full text). If a self-calibrated width lands within 30%, the literature says that is enough for the depth part of the problem.

**Caveat 1 — scale degeneracy.** Sage et al. §6.1 (full text): `(a·h) * (x/a) = h * x`, so blind estimation cannot pin `‖h‖`; "setting a meaningful value to ‖h‖ is highly nontrivial". A width read off a *normalised* through-focus curve is a *shape* parameter and inherits this. **Mitigation, published twice:** Köhler-style per-slice unit-sum normalisation (Forster 2004; Aguet 2008, both full text) fixes the gain and removes the ambiguity by fiat.

**Caveat 2 — the accuracy budget is asymmetric.** Aguet et al. 2008, full text: *"only the in-focus PSF needs to be precise. Otherwise … the deconvolution of the fusion image is either too weak, or results in out-of-focus information being falsely reallocated to the texture."* The self-calibration is *most* reliable near the peak of the through-focus curve, which is exactly where accuracy is *most* required. **DERIVED: the caveats and the method are aligned, not opposed. This is a favourable structural coincidence and the strongest technical point in the reviewer's favour on Q5.**

**Caveat 3 — the operator confound (the project's own rule 17 applied to this idea).** The measured width of the through-focus response is the width of the PSF **convolved with the focus-measure operator's own response and sampled at the step interval**. It is not the PSF width. Concretely: with 22 frames the curve is sampled at 22 points, so a curve narrower than ~2 steps is unresolvable, and the operator window (fact 152: bimodality visible at `WINDOW_RADIUS = 2`, invisible at 13) sets a floor on the apparent width. **Calibrating the OTF from a quantity that the merge then uses is exactly the circularity rule 17 warns about, and it is the same structural risk M20 §2 already flagged in its own optics gate.** ARGUED — and it is the first thing the kill experiment must control (§8.4).

### 5.2 What the literature actually does — four families

| Family | Method | Accuracy achievable | Sources |
|---|---|---|---|
| **Measured / experimental PSF** | Average z-stacks of sub-resolution beads (~100 nm). | Sage et al., full text: *"the resolution of an experimental PSF is tied to the resolution of the acquisition"* — a measured PSF cannot be sharper than the instrument that measured it. In their Table 3, the *target* is a 2.5 µm bead imaged at 64.5 nm lateral / 160 nm axial. | Sage et al. 2017 (MEASURED) |
| **Parametric scalar diffraction** | Gibson & Lanni depth-varying model — refractive-index mismatch, coverslip thickness, working distance. | The field's default for a theoretical PSF; drives EPFL's PSFGenerator (GPL, do not read). | Gibson & Lanni, *JOSA A* 8(10):1601, 1991, DOI `10.1364/josaa.8.001601`; *JOSA A* 9(1):154, 1992, DOI `10.1364/josaa.9.000154` (VERIFIED, metadata) |
| | Stokseth's approximation to the defocused OTF. | The standard closed form for a **defocused, diffraction-limited, circular pupil** — i.e. exactly `H_defocus × H_diffraction` for this project. | Stokseth, "Properties of a Defocused Optical System", *JOSA* 59(10):1314, 1969, DOI `10.1364/josa.59.001314` (VERIFIED, metadata) |
| | Aguet's own PSF model paper. | Aguet, Van De Ville, Unser, ISBI 2008 (`bigwww.epfl.ch/publications/aguet0801.pdf`, VERIFIED, fetched) | |
| **Blind / semi-blind** | Alternating deconvolution and PSF estimation. Sage et al. §6.1 (full text) reports the trend is (i) alternation, (ii) optically-motivated PSF parameterisation, or (iii) a PSF dictionary. Space-varying blind: *"only one attempt has been done."* | Strongly ill-posed; scale-degenerate. | Holmes, *JOSA A* 9(7):1052, 1992, DOI `10.1364/josaa.9.001052` (errata `10.1364/josaa.9.002097`); Fish, Walker, Brinicombe, Pike, *JOSA A* 12(1):58, 1995, DOI `10.1364/josaa.12.000058`; Markham & Conchello, *JOSA A* 16(10):2377, 1999, DOI `10.1364/josaa.16.002377`; Chan & Wong TV-blind, *IEEE TIP* 7(3):370–375, 1998, DOI `10.1109/83.661187`; Soulez et al., ISBI 2012:1735–1738, DOI `10.1109/isbi.2012.6235915`; Kim & Naemura, *Sci. Rep.* 5:9894, 2015, DOI `10.1038/srep09894`. All VERIFIED, metadata |
| | **The warning from the deblurring community**: Levin, Weiss, Durand, Freeman, "Understanding and evaluating blind deconvolution algorithms", CVPR 2009, DOI `10.1109/cvpr.2009.5206815`, and "Efficient marginal likelihood optimization in blind deconvolution", CVPR 2011, DOI `10.1109/cvpr.2011.5995308` (VERIFIED, metadata). The central result of the 2009 paper — widely cited — is that naive MAP over image *and* kernel **favours the no-blur (delta-kernel) explanation**, so many published blind methods work for reasons other than their stated objective. | | |
| **Calibrated measurement of a real camera** | "Learning Lens Blur Fields", arXiv `2310.11535`, 2023 (VERIFIED, metadata) — measure a *spatially- and focus-varying* blur field for an actual consumer lens. | Closest published analogue to what fact 27's `f_sig` measurement is doing. | |

**Note the Levin 2009 CVPR caveat propagating into the TR read in §2.7.1:** in a footnote of MIT-CSAIL-TR-2009-019 the same authors write *"despite the discussion in [Levin et al. 2009], we employ a MAP_{x,k} approach that scores a depth d based on the best I_d explanation alone. The reason this approach works here is that a delta explanation is absent from the search space"* (full text). **DERIVED design rule for this project: any per-pixel depth/OTF search must exclude the zero-blur hypothesis from the search space, or MAP will select it everywhere.** That is a concrete, cheap, checkable implementation constraint.

### 5.3 What an error in PSF width costs

| Error | Consequence | Label |
|---|---|---|
| up to **30% in σ** | no significant loss in topography accuracy | MEASURED — Aguet et al. 2008, full text |
| **PSF too narrow** (under-blurred model) | "the deconvolution of the fusion image is … too weak" — under-sharpening, benign | MEASURED (qualitative) — Aguet 2008 |
| **PSF too wide** (over-blurred model) | "out-of-focus information [is] falsely reallocated to the texture" — **out-of-focus content is promoted into the output as if it were sharp detail.** This is the dangerous direction. | MEASURED (qualitative) — Aguet 2008 |
| **Unknown gain `‖h‖`** | scale degeneracy; output brightness is unidentifiable | MEASURED (structural) — Sage 2017 §6.1 |
| **σ error near the peak frame** | direct error in the sharp output; no slack | MEASURED (qualitative) — Aguet 2008 |
| **σ error in far-off-peak frames** | absorbed; those frames contribute little `\|H\|²` anyway | DERIVED from Eq. (53), §2.7.1 |

> **Rule-18 statement (which way each can be fooled):** an over-wide PSF estimate makes the output look *sharper and more detailed* while being wrong — the metric-friendly failure. An over-narrow estimate makes it look *softer* while being wrong — the metric-hostile failure. **Any automated PSF-width search that optimises a sharpness metric will therefore drift systematically toward over-wide.** Pair it with a flat-ROI noise control (project rule 9) and with the out-of-range-pixel count (Forster 2004's 30% measurement) as the second, opposite-signed check.

---

## 6. Q6 — Validation, metrics, benchmarks, simulators

### 6.1 The honest state of it

Microscopy has the same ground-truth problem this project has, and its practical answer is worse than the project's. Sage et al. 2017 (full text) report that in their own study, algorithm parameters were tuned **"through visual assessment"**. That is the field's default. ARGUED: do not treat published EDOF/deconvolution comparisons as automatic-operation benchmarks.

### 6.2 Metrics actually used

| Metric | Where | Notes |
|---|---|---|
| SNR, PSNR, SSIM against a synthetic ground truth | Sage et al. 2017 Table 2 | The main quantitative instrument. Requires simulation. |
| **NMISE** (normalised mean integrated squared error) | EPFL Grand Challenge | Poisson-appropriate error measure. |
| **Lateral and axial FWHM of a real bead** | Sage et al. 2017 Table 3 | The one *real-data*, ground-truth-free instrument in the paper, and the one that produced the damning V2 result. **Directly transplantable: this project's `f_sig` knee measurement is the frequency-domain twin of it.** |
| SNR **gain over a named baseline** | Forster et al. 2004 Tables 1 & 2 | Reporting *relative* to the variance method is what made the sign inversion on real tissue visible. **Copy this convention.** |
| **Fourier Ring Correlation (FRC)** | Nieuwenhuizen et al., *Nat. Methods* 10:557–562, 2013, DOI `10.1038/nmeth.2448` (VERIFIED, metadata); Banterle, Bui, Lemke, Beck, *J. Struct. Biol.* 183(3):363–367, 2013, DOI `10.1016/j.jsb.2013.05.004` (VERIFIED, metadata) | Resolution from **two independent noisy realisations** of the same object — **no ground truth needed**. |
| **Image decorrelation analysis** | Descloux, Grußmayer, Radenovic, *Nat. Methods* 16:918–924, 2019, DOI `10.1038/s41592-019-0515-7`, addendum `10.1038/s41592-020-0963-0` (VERIFIED, metadata) | Resolution estimate from **a single image**, no ground truth, no second acquisition. |

> **Strong recommendation, ARGUED:** FRC is the metric this project is missing. Two independent captures of the same static scene are trivially obtainable on a macro rig (shoot the stack twice), the method needs no ground truth, and it reports a **resolution in cycles/pixel** — directly comparable to the measured `f_sig = 0.2762 cyc/px` (fact 27) and to the MTF@Nyquist table (fact 12). It is also two-sided in the sense rule 18 demands: a merge that invents detail from noise gets *no* FRC credit, because invented detail is uncorrelated between the two independent realisations. **FRC is a sharpness metric that cannot be fooled upward by noise amplification** — which is exactly the property `mean |∇|` lacks (fact 145).

### 6.3 Does a benchmark with real ground truth exist?

**For microscopy, yes — with hidden ground truth.**

**The EPFL 3-D Deconvolution Grand Challenge** (`bigwww.epfl.ch/deconvolution/challenge/`, page fetched this milestone; two editions, ISBI 2013 and ISBI 2014). VERIFIED from the challenge page:

- Data are **computer-generated** 3-D stacks from *"a faithful physical description of a widefield digital microscope, combining an advanced PSF model with a noise generator that accounts for **shot noise, electronic noise and quantization**."*
- Structures span **point sources, filaments, membranes and dense volumetric features** — one class per colour channel, no cross-talk, so one dataset scores four structure types independently.
- **The ground truth was deliberately not disclosed to entrants**, which is what makes it a real benchmark rather than a tuning set.
- Named hurdles: "algorithm selection, **PSF-inaccuracy compensation, noise-model calibration**, regularization-parameter adjustment".
- Scoring: MSE, SSIM, NMISE **plus** "structure-oriented and post-processing-based" measures, aggregated as a weighted average.
- 2014 results: 1st **Ferréol Soulez** (Lyon), 2nd **David Biggs** (KB Imaging), 3rd **Sander Kromwijk** (EPFL).

**For 20–60 frame × 33 MP real photographic focus stacks — still no.** This survey did not change that finding. The nearest photographic focal-stack datasets, all VERIFIED (metadata), are small-format and built for depth estimation, not for merge quality:

| Dataset | Ref | Why it does not substitute |
|---|---|---|
| DSLR focal stacks / "Depth from focus with your mobile phone" | Suwajanakorn, Hernández, Seitz, CVPR 2015, DOI `10.1109/cvpr.2015.7298972` | Phone/DSLR stacks, depth ground truth absent or approximate |
| **DDFF 12-Scene** | Hazirbas, Soyer, Staab, Leal-Taixé, Cremers, ACCV 2018, LNCS 11363, DOI `10.1007/978-3-030-20893-6_33` | Light-field derived, low resolution, **depth** ground truth |
| DefocusNet synthetic | Maximov, Galim, Leal-Taixé, CVPR 2020, DOI `10.1109/cvpr42600.2020.00115` | Synthetic, rendered, **depth** ground truth |
| Learning to Autofocus | Herrmann, Bowen, Wadhwa, Garg, He, Barron, Zabih, CVPR 2020, DOI `10.1109/cvpr42600.2020.00230` | Focus-setting ground truth for autofocus, not merge quality |
| Classical DfF benchmarks | Ens & Lawrence, *IEEE TPAMI* 15(2):97–108, 1993, DOI `10.1109/34.192482`; Xiong & Shafer, CVPR 1993, DOI `10.1109/cvpr.1993.340977`; Watanabe & Nayar, *IJCV* 27(3):203–225, 1998, DOI `10.1023/a:1007905828438` | Historic, tiny, depth-focused |

### 6.4 Should the project build a simulator? Yes — and here is the published design to copy

Three simulator designs are documented well enough to reimplement without touching any GPL code:

1. **Forster et al. 2004** (full text): Brodatz textures (D18, D22, D23, D112) or a histological section mapped onto a surface; **linear interpolation along z**; each slice convolved with a Gaussian PSF of increasing width; **coefficient sum normalised** per slice to model Köhler illumination. Simple enough to build in an afternoon.
2. **Aguet et al. 2008** (full text): the same, but with σ(z) fitted to a **Gibson–Lanni scalar diffraction model** rather than an arbitrary ramp, and an extra normalisation to avoid blow-up as σ → 0.
3. **EPFL Grand Challenge** (page fetched): advanced PSF model **plus a noise generator with shot noise, electronic noise and quantisation**, four structure classes, ground truth withheld.

**The synthesis for this project (ARGUED):**

> **Note added after reading the repository:** the project is **already building this** — `experiments/m25-simulator/` exists, with a `PREREGISTRATION.md` written before any gate was run, a port-check against `m9-support`'s committed numbers on **real** data as a prerequisite, an explicit rule-18 failure-direction table, and gates that include `04-gate1c-occlusion.py` and `05-gate2-negative-control.py`. **This section is therefore not a proposal to start a simulator; it is a list of what the literature says a simulator of this kind must contain, offered as a checklist against M25.** I did not run or modify M25 (rule: I own only this file). Read depth: `PREREGISTRATION.md` first 45 lines, file listing only.

- Take the **surface-plus-texture geometry** from Forster/Aguet — it is the correct object model for a macro subject, unlike a fluorescent volume.
- Take the **noise generator** from the Grand Challenge, but instantiate it with the project's **own photon-transfer calibration** (fact 27's floor matched the model to 0.950×) rather than a nominal one. **This is the part no published simulator has, and it is the project's actual advantage.** M25 already fits mean green level, texture contrast and spectral slope β from the real stack while *sweeping* the defocus growth rate — which is the right split, and matches the challenge's "noise-model calibration" hurdle.
- Take the **defocus OTF composed with a measured diffraction OTF** at the measured bellows factor `B ∈ [2.41, 3.06]` (facts 27, 28). Stokseth 1969 (`10.1364/josa.59.001314`) gives the closed form. **No published simulator does this either** — they all assume the marked aperture is the optical one.
- Take the **four structure classes** idea, which is the one thing in the Grand Challenge design that M25's pre-registration does not appear to have: a macro analogue would be *point-like* (dust, specular pinpoints), *filamentary* (hair, setae), *edge/membrane* (wing margins, chitin plates), and *dense texture* (compound eye). **Scoring per class is what exposes the content dependence that produced Sage's RL-TV inversion and Forster's Table 2 sign flip**, and both of those are exactly the kind of result a single-texture simulator cannot produce.
- Take the **"withhold the ground truth"** discipline: generate, score, and only then reveal — otherwise the simulator becomes a tuning set. Cheap version: fix the RNG seed and keep the truth in a file the tuning loop cannot read.

**Do not** attempt to adopt the Grand Challenge *data*: it is fluorescence microscopy at ≤ 1 MP with no occlusion, and per §0.4 the modality mismatch is fatal for merge evaluation.

---

## 7. Q7 — Licence reality check

**All licences below were read from repository metadata via `gh api repos/<owner>/<repo>` (field `.license.spdx_id`) or from a `LICENSE` file header of a permissive project. No source file of any GPL/AGPL project was opened at any point in this milestone.**

### 7.1 DO NOT READ — GPL/AGPL

| Implementation | Method it implements | SPDX | Note |
|---|---|---|---|
| **EPFL Extended Depth of Field plugin** (`bigwww.epfl.ch/demo/edf/`) | **Both** Forster et al. 2004 CWT-EDF **and** Aguet et al. 2008 2.5-D | **GPL-3.0** | Already on the `AGENTS.md` do-not-read list. **One plugin serves the two most relevant papers in this survey.** Papers only. |
| **`Biomedical-Imaging-Group/DeconvolutionLab2`** | RIF, TR, LW, TM, FISTA, RL, RL-TV, NIF — every algorithm in Sage Table 2 | **GPL-3.0** | **DO NOT READ.** The paper (`10.1016/j.ymeth.2016.12.015`) is the survey's most-cited source and is freely readable. |
| **`Biomedical-Imaging-Group/PSFGenerator`** | Gibson–Lanni, Born–Wolf, Richards–Wolf PSF models | **GPL-3.0** | **DO NOT READ.** Use Gibson & Lanni 1991/1992 and Stokseth 1969 directly from the papers. |
| **`python-microscopy/python-microscopy`** | Deconvolution, PSF tools | **GPL-3.0** | **DO NOT READ.** |

### 7.2 Safe to read (permissive)

| Implementation | Relevance | SPDX |
|---|---|---|
| `hammerlab/flowdec` | TensorFlow Richardson–Lucy, 2-D/3-D | Apache-2.0 |
| `rosalindfranklininstitute/RedLionfish` | GPU RL deconvolution | Apache-2.0 |
| `roflmaostc/DeconvOptim.jl` | Regularised deconvolution, multiple regularisers | MIT |
| `clij/clij2-fft` | GPU FFT + RL | BSD-3-Clause |
| `CSBDeep/CSBDeep` | CARE (Weigert et al. 2018) reference implementation | BSD-3-Clause |
| `scikit-image/scikit-image` | `restoration.wiener`, `unsupervised_wiener`, `richardson_lucy` | BSD-3-Clause (API reports NOASSERTION; the `LICENSE.txt` header states `License: BSD-3-Clause` — verified by reading the licence file only) |
| `imagej/imagej-ops`, `scijava/scijava-common` | ImageJ deconvolution ops | BSD-2-Clause |
| `royerlab/dexp`, `royerlab/aydin` | Large-scale deconvolution / denoising | BSD-3-Clause |
| `clEsperanto/pyclesperanto_prototype` | GPU image ops | BSD-3-Clause |
| `astropy/photutils` | PSF fitting utilities | BSD-3-Clause |
| `opencv/opencv` | FFT, general | Apache-2.0 |
| `PetteriAimonen/focus-stack` | Reference open-source stacker | MIT — already on the project's safe list |

### 7.3 Unresolved or restricted

| Implementation | SPDX | Disposition |
|---|---|---|
| `scopetools/cudadecon` | **NOASSERTION** | Licence unresolved via the API. **Treat as unknown = do not read** until confirmed. |
| `juglab/n2v` (Noise2Void) | **NOASSERTION** | Same. Do not read. |
| **Huygens / SVI**, **DeltaVision softWoRx**, **AutoQuant** | Commercial, **USD 5,000–10,000** per Sage et al. 2017 (full text) | Cite only. Note V5: Huygens CMLE placed 9th of 10 on Sage Table 2. |
| MOMFBD (van Noort et al. 2005) | Not audited this milestone | **could not confirm** — check before reading. |

### 7.4 The structural point

**The two papers this project most needs to learn from — Forster et al. 2004 and Aguet et al. 2008 — share a single GPL-3.0 reference implementation.** That is not an obstacle: both papers are unusually complete, giving the object model, the PSF normalisation, the optimisation schedule (B-spline basis, coarse-to-fine dyadic, Brent line search, ~5 topography sub-iterations, 2–3 texture gradient steps) and the simulator recipe. Everything §6.4 recommends can be built from the papers alone. **Record in the do-not-read list that `bigwww.epfl.ch/demo/edf/` covers *both* methods, since a future agent reading only the Aguet paper might not realise the code is the same forbidden artifact.**

---

## 8. The kill experiment — pre-registered

**Design goal:** the cheapest thing that could kill the multi-frame Wiener merge, on the project's own data, before any of it is built into the pipeline. Written to be handed to an implementation agent as-is. In the project's culture — *every headline number needs a control that could have failed* — this is designed so that **three separate outcomes kill it and one narrow outcome saves it.**

### 8.1 What is being tested

**H1 (the reviewer's claim):** a guarded multi-frame Wiener merge across the focus axis recovers mid-frequency contrast that no selector can, on real 22- and 33-frame stacks, at the project's calibrated σ.

**H0 (the null the project already believes, from M20/fact 141):** at this rig's apertures the OTFs of off-peak frames carry too little `Σ|H|²` in the surviving band, so the merge is at best a wash and at worst noisier than the shipped merge.

### 8.2 Data — all of it already exists, nothing new to capture

| Role | Stack | Frames | Why |
|---|---|---|---|
| Primary A | `109MSDCF` | **22** | The reference stack for facts 19, 23, 51; noise behaviour already characterised |
| Primary B | `119MSDCF` | **33** | Second scene, different frame count and drift regime (fact 44) |
| Occlusion probe | `coffee-bean` | — | Fact 150's 4.38× bimodality enrichment lives here; the merge must not get *worse* at depth steps |
| **Degenerate control — free and decisive** | **`coffee-bubbles`** | **19 at *constant* focus** (fact 49) | **All OTFs are equal by construction, so the estimator must reduce to the plain mean.** If it does not, the implementation is wrong. This is a null control that costs nothing and could have failed. |
| **Independent-realisation pair** | `112MSDCF` / `113MSDCF` | 79 / 63 | **Two independent captures of the same subject** (fact 52). Enables **FRC** scoring with no ground truth (§6.2). |

Everything runs through the existing decode path. **No new captures are required, which is the point: this experiment is cheap enough that refusing to run it would be the expensive choice.**

### 8.3 Arms

| Arm | Description |
|---|---|
| **A — shipped** | The current noise-gated merge. The baseline that matters. |
| **B — plain argmax** | Fact 19's reference point (1.253× noise). The naive floor. |
| **C — plain mean** | Fact 19's other reference point (0.534× noise). **The Häusler-1972 numerator** (§2.5), and the degenerate limit of arm D. |
| **D — guarded focus-axis RIF** | `L̂ = Σ H_k* Y_k / (Σ\|H_k\|² + σ²/S)`. `H_k` = defocus OTF at the pixel's frame offset **composed with the measured diffraction OTF** at the bellows-corrected aperture (facts 27, 28); `σ` from the photon-transfer calibration; `S(f)` a fixed 1/f² prior. **One FFT pair per tile, no iteration** — V5 says this captures the value. |
| **D′ — ablation: no diffraction term** | Identical to D but with `H_k` from the defocus model alone, i.e. what the estimator would be if the project had not measured fact 27. **Isolates the part that is actually the project's bet** (§2.8). |
| **E — ablation: unguarded** | D with the `σ²/S` term set to zero. **Expected to be catastrophic** (V1: −75 dB; fact 141: +31% RMSE). If E is *not* catastrophic, the guard is not load-bearing here and both M20's and this survey's central claim are wrong — a result that would be more interesting than the experiment's nominal outcome. |

### 8.4 Controls

| Control | Construction | What it kills if it fires |
|---|---|---|
| **Permutation null** | Shuffle frame order before building the per-frame OTFs, keeping pixels untouched. The through-focus structure is destroyed; the noise and the histogram are not. Run arm D on the permuted stack. | If D's advantage over A survives permutation, the "advantage" is a **processing artifact, not focus-axis information**. M21's placebo read **1.01×** — that is the target. **This is the single most important control.** |
| **Degenerate control** | Arm D on `coffee-bubbles` (constant focus). | Must reproduce arm C (plain mean) to within numerical tolerance. If not, the implementation is broken and every other number is void. |
| **Positive control (planted)** | Synthetic stack built to the Forster-2004 recipe (§6.4): known texture on a known height field, per-slice Gaussian PSF composed with a diffraction OTF, calibrated Poisson+Gaussian noise, **unit-sum normalisation per slice**. Sweep σ across the fact-142 crossover. **Do not build this from scratch — `experiments/m25-simulator/` already exists, is pre-registered, and already passes a port-check against real data.** Add the per-structure-class scoring of §6.4 to it rather than starting again. | Arm D **must** beat A and B here at low σ. **If it does not, the harness is broken, not the idea** — do not proceed to interpret the real-data arms. Project rule 13: check the plant can express the effect before concluding it is absent. |
| **Circularity control (rule 17)** | Run arm D twice: once with `H_k` widths self-calibrated from the through-focus curve, once with `H_k` from the *independent* Stokseth/defocus model at the measured `B`. | If the self-calibrated version wins and the independent-model version does not, the gain is coming from the OTF estimator agreeing with the focus measure, not from optics. **This is caveat 3 of §5.1 and the same circularity M20 §2 flagged in its own optics gate.** |
| **Band control (fact 143 / V6)** | Report all metrics **split at `f_sig = 0.2762 cyc/px`**: below the measured cutoff and above it. | Above `f_sig` **all arms must be statistically indistinguishable**. Any arm that "wins" above the measured optical cutoff is manufacturing detail. This control is free and it is the one most likely to catch a bug. |

### 8.5 Metrics — every one paired, per rules 9 and 18

| Metric | Direction it can be fooled | Its paired control |
|---|---|---|
| **Gradient *correlation*** with the reference (not `mean \|∇\|`) | Fact 145: `mean \|∇\|` is one-sided — Wiener output had **24% more** gradient magnitude but **12% less** gradient correlation at σ = 0.010, and at σ = 0.050 argmax read *above* ground truth. **Correlation is the two-sided version.** | flat-ROI noise ratio |
| **Flat-ROI noise ratio** vs a single frame | Can be improved by simply blurring | gradient correlation |
| **Out-of-range pixel fraction** | Forster 2004 MEASURED ≈30% for max-abs selection. Rises with ringing and with over-wide PSFs. | — (one-sided by design, and that is fine because it is a *guard*, not a score) |
| **FRC resolution (cyc/px)** on the `112`/`113` pair | **Cannot be fooled upward by noise amplification**, because invented detail is uncorrelated between independent realisations (§6.2) | — |
| **SNR/PSNR/SSIM** — planted control only | Requires ground truth | only reported on the synthetic arm |
| **Per-class scores** on the planted control | Content dependence (Sage's RL-TV row; Forster's Table 2 sign inversion) | point / filament / edge / dense-texture, scored separately |

**Report all of them for the whole frame *and* for the fact-142 candidate subset (the 15.1% of pixels past the σ ≈ 0.03 crossover) separately.** A whole-frame wash concealing a large win on 15% of pixels is a different result from a whole-frame wash concealing nothing, and the project needs to distinguish them.

### 8.6 Pre-registered decision rule

**The idea survives as a candidate core merge only if ALL of the following hold:**

1. The **positive control passes** — arm D beats A and B on the planted stack at low σ, per structure class.
2. The **degenerate control passes** — arm D ≡ arm C on `coffee-bubbles`.
3. Arm D beats arm A on **gradient correlation** on `109MSDCF` **and** `119MSDCF`, on the fact-142 candidate pixels, **below** `f_sig`.
4. That advantage **collapses to ≤ 1.05× under the permutation null**.
5. Arm D's **flat-ROI noise ratio does not exceed arm A's** at equal gradient correlation.
6. Arm D **does not degrade** the merge at `coffee-bean`'s depth steps relative to arm A.
7. The advantage **survives the circularity control** — the independent-OTF variant wins too.

**It is killed as a core merge (and stays an opt-in plugin) if ANY of 3–7 fails.**
**The experiment itself is void, and must be repaired before interpretation, if 1 or 2 fails.**
**It is killed outright — not even a plugin — if D also loses to A on the planted control at the project's calibrated σ**, since that would mean the estimator loses even where the forward model is exactly true.

### 8.7 What would make this cheap

- Arms C, D, D′, E differ only in the weight computation; one code path, four weight functions.
- Arm D is **one FFT pair per tile** — V5 says the 237× iterative machinery buys 0.19 dB, so do not build it.
- The permutation null is a `shuffle` on the frame index.
- The degenerate control is an existing stack.
- The positive control is an existing, pre-registered experiment (`experiments/m25-simulator/`).
- The band split is a mask on an FFT the arms already compute.
- **Estimated new code: the weight functions, a per-structure-class extension to M25, and the FRC scorer.** Everything else exists.

### 8.8 The result that would most change the project's mind

**Not** a win for arm D. A win for arm D **at a wider aperture**. Fact 144 measured that best-frame MTF at 0.25 cyc/px goes 0.046 (f/11) → 0.447 (f/5.6) — a **9.6×** contrast change — and that blur-per-focus-step in pixels is **aperture-invariant**, so wider apertures cost only frame count. **If arms A–E are re-run on a wider-aperture capture and D's margin grows superlinearly, that is the finding that reorders the roadmap**, because it says the estimator was never the problem: the ceiling was. Per §0.2 item 2 and `captures-needed.md` §0, that capture should be made regardless of this experiment's outcome.

---

## 9. Proposed SYNTHESIS facts (M19 owns 120–139)

**These are proposals for another agent to accept, edit or reject.** All are external-literature facts; none is an in-house measurement.

| # | Proposed fact | Label |
|---|---|---|
| 120 | **The multi-frame Wiener merge across a focal stack is published, with its error law.** Levin et al., MIT-CSAIL-TR-2009-019 (2009), Appendix B, Eq. (52) is the estimator verbatim; Eq. (53) gives `E[error] = (σ⁻²Σ_j\|φ̂_j\|² + σ_ω⁻²)⁻¹`. **The project's fact 140 re-derived a published result and `SYNTHESIS.md` §6 must not claim it as novel.** | VERIFIED (full text) |
| 121 | **Levin's Eqs. (54)–(57) evaluate that estimator for a focal stack and conclude *against* it** — focus sweep is better, by a factor `\|ω\|/Ω` — **but only under a fixed-total-exposure assumption (each of N frames gets 1/N of the light) that a static macro subject does not impose.** Removing it inverts the ordering by `N²`; at N = 22 that is 484×. | VERIFIED (their result) + DERIVED (the inversion, my algebra) |
| 122 | **Unregularised inversion is catastrophic by an externally measured 79 dB.** DeconvolutionLab2 synthetic microtubules: NIF **−75.45 dB**, RIF **+3.47 dB**, same data and PSF. Independent external corroboration of fact 141. | MEASURED (Sage et al. 2017 Table 2) |
| 123 | **Deconvolution measurably degrades the axis where the OTF is weakest.** Real 2.5 µm bead: acquisition axial FWHM **3979 nm**; all six deconvolution settings tested gave **4449–5909 nm**, while lateral improved ≤ **3.3%**. | MEASURED (Sage et al. 2017 Table 3) |
| 124 | **A 7-second regularised inverse filter is within 0.19 dB of Richardson–Lucy at 1661 s (237×), and beats commercial Huygens CMLE.** Do not build iterative deconvolution on the strength of this literature. | MEASURED (Sage et al. 2017 Table 2) |
| 125 | **Total variation is not a safe default: it MEASURED *worse* than plain RL (3.36 vs 3.66 dB) on a non-piecewise-constant object.** The authors state the ranking is not transferable between object types. | MEASURED (Sage et al. 2017 Table 2) |
| 126 | **A 30% error in the PSF σ costs no significant topography accuracy, but the in-focus PSF must be precise**; an over-wide PSF causes "out-of-focus information [to be] falsely reallocated to the texture". The accuracy budget along k is asymmetric and peaked. | MEASURED (Aguet et al. 2008) |
| 127 | **Max-absolute-value wavelet fusion puts ≈30% of pixels outside the dynamic range of every input frame**, boosting energy, noise and saturation. Measured by the authors of the method in 2004 — external corroboration of the selection-injects-energy thesis behind fact 19. | MEASURED (Forster et al. 2004) |
| 128 | **A merge expressed as a normalised weighted sum over frames is structurally range-safe; a merge containing a `1/Σ\|H\|²` division is not.** Aguet 2008 gets range safety for free because its texture update is an interpolation among slices. Forster 2004's "reassignment" clamp is the retrofit, MEASURED to reduce ringing (+0.37 to +0.64 dB). | DERIVED / MEASURED |
| 129 | **Transform-domain fusion's advantage over a plain focus measure is content-dependent and can invert sign on real data**: +2.49 to +4.70 dB on synthetic Brodatz textures, but **−0.58 dB vs the variance method** on real histological tissue without post-processing. | MEASURED (Forster et al. 2004 Tables 1–2) |
| 130 | **The three most relevant papers in three different fields each state that the depth-discontinuity case lies outside their forward model** — Levin et al. 2009 ("a general problem for all computational extended-DOF systems … most artifacts can be eliminated with simple manual layer refinement"), Nagahara et al. 2008 ("we have not explicitly modeled occlusions"), Aguet et al. 2008 ("ignores potential out-of-focus contributions from beneath the surface"). | VERIFIED (all three, full text) |
| 131 | **"First to model the occlusion halo" is FALSE and must not be claimed.** Prior art: Asada et al. 1995/1998 (RPB; explicitly predicts the **non-monotonic** brightness transition that fact 150 measured, 28 years earlier), Bhasin & Chaudhuri 2001, Favaro & Soatto 2003, McGuire et al. 2005, Hasinoff & Kutulakos 2007, McCloskey et al. 2011, Wang et al. 2015. **The defensible claim is "first shipping focus-stacking tool to model it", and even that is `could not confirm`.** | VERIFIED |
| 132 | **Wang et al. 2015 give a cheap published remedy for exactly fact 150's bimodality**: at an occlusion boundary the angular patch is bimodal, and splitting it by local edge orientation restores unimodality in each half. The focus-axis analogue is to partition frames by through-focus mode and merge within the mode — **no `α`, `F`, `B` unmixing required.** | VERIFIED |
| 133 | **Ringing has two distinct causes needing different fixes**: FFT circular periodicity ⇒ ghosts (fix: zero-padding or apodization) and band-limiting ⇒ Gibbs/Runge (intrinsic). Sage et al.: *"Fourier-related artifacts frequently appear, particularly in the axial direction since this direction is often sampled to a lesser extent"* — **for this project the under-sampled axis is the focus axis.** | MEASURED (Sage et al. 2017 §4.3.1) |
| 134 | **Blind PSF estimation is scale-degenerate**: `(a·h)*(x/a) = h*x`, and "setting a meaningful value to ‖h‖ is highly nontrivial". Both Forster 2004 and Aguet 2008 pin it by Köhler-style unit-sum-per-slice normalisation. Any self-calibrated OTF must do the same. | MEASURED (Sage et al. 2017 §6.1) |
| 135 | **MAP over image and kernel favours the no-blur explanation** (Levin et al. CVPR 2009). Levin et al.'s own tech report notes their depth search works *"because a delta explanation is absent from the search space"*. **Design rule: exclude the zero-blur hypothesis from any per-pixel OTF search.** | VERIFIED |
| 136 | **A calibrated physical EDOF simulator with withheld ground truth already exists**: the EPFL 3-D Deconvolution Grand Challenge (ISBI 2013/2014) — advanced PSF model plus a noise generator covering **shot noise, electronic noise and quantisation**, four structure classes, ground truth never disclosed. **Its design is transplantable; its microscopy data is not.** The one element M25's pre-registration does not appear to carry is **per-structure-class scoring** (point / filament / edge / dense texture), which is precisely what exposed the content-dependent sign inversions in facts 125 and 129. | VERIFIED (challenge page) |
| 137 | **Fourier Ring Correlation and image decorrelation analysis measure resolution with no ground truth** — FRC from two independent noisy realisations, decorrelation analysis from a single image. **FRC cannot be fooled upward by noise amplification**, which is precisely the defect fact 145 found in `mean \|∇\|`. The corpus already contains an independent pair (fact 52: `112MSDCF`/`113MSDCF`). | VERIFIED |
| 138 | **The reference implementation of *both* Forster 2004 CWT-EDF and Aguet 2008 2.5-D EDOF is the same GPL-3.0 ImageJ plugin** (`bigwww.epfl.ch/demo/edf/`). DeconvolutionLab2 and PSFGenerator are also GPL-3.0. All four papers are readable and complete enough to reimplement from; **none of the code may be read.** | VERIFIED (repo metadata) |
| 139 | **In astronomy the same select-vs-reconstruct choice has been live for 30+ years and both still ship** — lucky imaging (Fried 1978; Law et al. 2006) selects; MFBD/MOMFBD (Schulz 1993; van Noort et al. 2005) reconstructs. **The disanalogy: astronomy's PSFs vary randomly and are unknown, with no occlusion; a focus stack's vary systematically and are modellable, but the object occludes itself.** | VERIFIED / ARGUED |

---

## 10. Negative-search log (2026-08-23)

Recorded in the `B` §9.5 convention. **These are searches that returned nothing, not evidence of absence.**

| Query | Source | Result |
|---|---|---|
| `all:"extended depth of field" AND all:"deconvolution"` | arXiv API | 0 results |
| `all:"focus stacking" AND all:"deconvolution"` | arXiv API | 0 results |
| `all:"multi-frame Wiener" AND all:"focus"` | arXiv API | 0 results |
| `all:"focal stack" AND all:"Wiener"` | arXiv API | 0 results |
| `all:"through-focus" AND all:"PSF estimation"` | arXiv API | 0 results |
| `"occlusion" "focus stacking" "halo"` (the bare token searched deliberately as a literal query string; per rule 15 this document says **occlusion halo** everywhere else) | OpenAlex | nothing on structural occlusion modelling **inside a stacking tool** |
| `"focus stack" "photon transfer" deconvolution` | OpenAlex | no hits combining a calibrated photon-transfer noise model with a focus-stack merge |
| `"bellows factor" OR "effective aperture" deconvolution macro` | OpenAlex / Crossref | nothing applying a **measured** diffraction OTF at a bellows-corrected aperture to a stack merge |
| benchmark for 20–60 frame × 33 MP photographic focus stacks with merge-quality ground truth | OpenAlex, Crossref, GitHub | **none found** — confirms `B` §9.4's existing gap finding |
| Labeyrie 1970 speckle interferometry, *A&A* 6:85 | Crossref | **not resolvable to a DOI.** Omitted rather than guessed. |
| Licence of the MOMFBD reference implementation | not audited | not attempted this milestone |

**General observation, worth recording:** arXiv coverage of this literature is essentially nil. Widefield EDOF and microscopy deconvolution predate arXiv's adoption in optics and live in *JOSA A*, *Applied Optics*, *Journal of Microscopy*, *Microscopy Research and Technique*, *Methods*, *IEEE TIP* and ISBI. **Any future agent that searches only arXiv will conclude, wrongly, that this field does not exist.** Use Crossref and OpenAlex.

---

## 11. Could not verify

Stated explicitly, per the project's rule that a fabricated citation costs more than a missing one.

1. **Aguet et al. 2008, Table I** (SNR for variance / CWT-EDF / model-based methods) is an **embedded TIFF** with no text layer; `pypdf` lists 59 images on the page and no `dB` or `Variance` tokens. **I did not read those numbers and none are quoted here.** The paper's timing figures (64 s vs 16 s) came from the body text; the stack dimensions for that timing did not extract.
2. **Zhou Xu et al. 2020** — **abstract only.** Closed access; no OA copy found. Every claim attributed to it is an abstract claim, not a measurement I checked. Given it is the closest published match to the project's motivating argument, obtaining the full text is the highest-value follow-up.
3. **van Noort et al. 2005 (MOMFBD)** — **metadata only.** No abstract in OpenAlex and no OA PDF located. Cited for existence and lineage only.
4. **Abstract-only reads**, cited as claims and never as measurements: Harikumar & Bresler 1999; Hasinoff & Kutulakos 2007; Favaro & Soatto 2003; Asada et al. 1998; Arigovindan et al. 2013; Ikoma et al. 2018.
5. **Labeyrie 1970** (speckle interferometry) could not be resolved to a DOI in Crossref. **Omitted** rather than cited from memory.
6. **`scopetools/cudadecon` and `juglab/n2v` report SPDX `NOASSERTION`.** Licence unresolved ⇒ treated as do-not-read.
7. **The ISBI 2013 first-edition challenge paper** was never resolved to a citation; the challenge is cited from the EPFL challenge page and from Sage et al. 2017's reference to the **2014** edition.
8. **"No shipping focus-stacking tool models occlusion structurally"** — I did **not** audit the source of every stacker. Helicon Focus and Zerene Stacker are closed-source; `PetteriAimonen/focus-stack` is MIT and permitted but was not read this milestone. **Phrase the claim as "we know of no stacking tool that does this."**
9. **The `N²` exposure-assumption inversion of Levin's focal-stack verdict (§2.7.1) is my own algebra**, not a result stated in any paper. Labelled DERIVED. It has not been checked by anyone. Two named unquantified corrections (shot-noise-dominated scaling; the missing diffraction term) push in opposite directions.
10. **No published work was found** that does multi-frame Wiener with **per-frame, per-pixel defocus OTFs composed with a *measured* diffraction OTF, driven by a *calibrated photon-transfer* noise model, as the merge of a photographic focus stack.** Nearest neighbours are Levin's TR Appendix B (the estimator and error law, no calibration, geometric optics), Aguet 2008 (microscopy, 2.5-D, single depth per pixel), Zhou Xu 2020 (microscopy, parameter-free Gaussian) and Häusler 1972 / Nagahara 2008 (equal-weight, single deconvolution). **This is a statement about the boundary of my search, not a proof of novelty.**
11. **Nothing in this document is an independent verification of M20 or M21.** Where the literature agrees with them it is corroboration from a different modality, which is weaker than replication and stronger than nothing.

---

## 12. Citation ledger

Every DOI below was resolved live against Crossref or OpenAlex during this milestone. **Read depth: [F] = full or near-full text, [A] = abstract only, [M] = metadata only.**

**Microscopy deconvolution lineage.** Agard 1984, *Ann. Rev. Biophys. Bioeng.* 13:191–219, `10.1146/annurev.bb.13.060184.001203` [M] · Agard, Hiraoka, Shaw, Sedat 1989, *Methods Cell Biol.* 30:353–377, `10.1016/s0091-679x(08)60986-3` [M] · Streibl 1985, *JOSA A* 2(2):121, `10.1364/josaa.2.000121` [M] · Richardson 1972, *JOSA* 62(1):55, `10.1364/josa.62.000055` [M] · Lucy 1974, *Astron. J.* 79:745, `10.1086/111605` [M] · Holmes 1988, *JOSA A* 5(5):666, `10.1364/josaa.5.000666` [M] · Holmes 1992, *JOSA A* 9(7):1052, `10.1364/josaa.9.001052`, errata `10.1364/josaa.9.002097` [M] · Biggs & Andrews 1997, *Appl. Opt.* 36(8):1766, `10.1364/ao.36.001766` [M] · Verveer & Jovin 1998, *JOSA A* 15(5):1077, `10.1364/josaa.15.001077` [M] · Verveer, Gemkow, Jovin 1999, *J. Microsc.* 193(1):50–61, `10.1046/j.1365-2818.1999.00421.x` [M] · Wallace, Schaefer, Swedlow 2001, *BioTechniques* 31:1076–1097, `10.2144/01315bi01` [M] · Sibarita 2005, *Adv. Biochem. Eng. Biotechnol.*, `10.1007/b102215` [M] · Sarder & Nehorai 2006, *IEEE Signal Process. Mag.* 23(3):32–45, `10.1109/msp.2006.1628876` [M] · Dey et al. 2006, *Microsc. Res. Tech.* 69(4):260–266, `10.1002/jemt.20294` [M] · Laasmaa, Vendelin, Peterson 2011, *J. Microsc.* 243(2):124–140, `10.1111/j.1365-2818.2011.03486.x` [M] · Arigovindan et al. 2013, *PNAS* 110(43):17344–17349, `10.1073/pnas.1315675110` [A] · Lefkimmiatis, Ward, Unser 2013, *IEEE TIP* 22(5):1873–1888, `10.1109/tip.2013.2237919`; Poisson `10.1109/tip.2013.2271852`; ISBI `10.1109/isbi.2013.6556437` [M] · Preibisch et al. 2014, *Nat. Methods* 11:645–648, `10.1038/nmeth.2929` [M] · Soulez 2014, ISBI:1075–1078, `10.1109/isbi.2014.6868060` [M] · Soulez et al. 2012, ISBI:1735–1738, `10.1109/isbi.2012.6235915` [M] · Kim & Naemura 2015, *Sci. Rep.* 5:9894, `10.1038/srep09894` [M] · **Sage et al. 2017, *Methods* 115:28–41, `10.1016/j.ymeth.2016.12.015` [F]** · Ikoma, Broxton, Kudo, Wetzstein 2018, *Sci. Rep.* 8:11489, `10.1038/s41598-018-29768-x` [A].

**EPFL EDOF line (papers only — implementation is GPL-3.0).** Forster, Van De Ville, Berent, Sage, Unser 2004, *Microsc. Res. Tech.* 65(1–2):33–42, `10.1002/jemt.20092` **[F]** · Forster et al. 2004, ISBI vol. 2:660–663, `10.1109/isbi.2004.1398624` **[F]** · Aguet, Van De Ville, Unser 2006, ISBI:778–781, `10.1109/isbi.2006.1625032` [M] · **Aguet, Van De Ville, Unser 2008, *IEEE TIP* 17(7):1144–1153, `10.1109/tip.2008.924393` [F]** · Aguet, Van De Ville, Unser 2008, ISBI PSF model, `bigwww.epfl.ch/publications/aguet0801.pdf` [M] · **Zhou Xu, Molina, Ma, Wang, Ni 2020, *IEEE TIP* 29:3227–3238, `10.1109/tip.2019.2957941` [A]** · Valdecasas et al. 2001, *Micron* 32(6):559–569, `10.1016/s0968-4328(00)00061-5` [M].

**Computational photography EDOF.** Häusler 1972, *Opt. Commun.* 6(1):38–42, `10.1016/0030-4018(72)90243-x` [M] · Pieper & Korpel 1983, *Appl. Opt.* 22(10):1449, `10.1364/ao.22.001449` [M] · Sugimoto & Ichioka 1985, *Appl. Opt.* 24(14):2076, `10.1364/ao.24.002076` [M] · Dowski & Cathey 1995, *Appl. Opt.* 34(11):1859, `10.1364/ao.34.001859` [M] · **Nagahara, Kuthirummal, Zhou, Nayar 2008, ECCV, LNCS 5305:60–73, `10.1007/978-3-540-88693-8_5` [F]** · Kuthirummal et al. 2011, *IEEE TPAMI* 33(1):58–71, `10.1109/tpami.2010.66` [M] · Levin, Fergus, Durand, Freeman 2007, *ACM TOG* 26(3), `10.1145/1276377.1276464` [M] · **Levin, Hasinoff, Green, Durand, Freeman 2009, *ACM TOG* 28(3):1–14, `10.1145/1531326.1531403` [F]** · **Levin, Hasinoff, Green, Durand, Freeman, MIT-CSAIL-TR-2009-019, 8 May 2009, `hdl.handle.net/1721.1/45513` [F]** · Zhou & Nayar 2009, ICCV, `10.1109/iccv.2009.5459268`; IJCV 2010, `10.1007/s11263-010-0409-8` [M] · Cossairt, Zhou, Nayar 2010, *ACM TOG* 29(4), `10.1145/1833349.1778768` [M] · Hasinoff & Kutulakos 2008, ECCV, `10.1007/978-3-540-88693-8_4`; *IEEE TPAMI* 2011, `10.1109/tpami.2011.62` [M] · Agarwala et al. 2004, *ACM TOG* 23(3):294–302, `10.1145/1015706.1015718` [M] · Ogden, Adelson, Bergen, Burt 1985, *RCA Engineer* 30(5):4–15 — **no DOI** [M] · Horn 1968, MIT AIM-160 — **tech report, no DOI** [M].

**Astronomy / multi-frame.** Schulz 1993, *JOSA A* 10(5):1064, `10.1364/josaa.10.001064` [M] · Jefferies & Christou 1993, *ApJ* 415:862, `10.1086/173208` [M] · van Noort, Rouppe van der Voort, Löfdahl 2005, *Solar Phys.* 228:191–215, `10.1007/s11207-005-5782-z` [M] · Löfdahl 2002, *Proc. SPIE* 4792:146, `10.1117/12.451791` [M] · Fried 1978, *JOSA* 68(12):1651, `10.1364/josa.68.001651` [M] · Law, Mackay, Baldwin 2006, *A&A* 446:739–745, `10.1051/0004-6361:20053695` [M] · Harmeling, Hirsch, Sra, Schölkopf 2009, ICCP, `10.1109/iccphot.2009.5559014` [M] · Hirsch et al. 2010, CVPR, `10.1109/cvpr.2010.5540158` [M] · **Harikumar & Bresler 1999, *IEEE TIP* 8(2):202–219, `10.1109/83.743855` [A]** · Šroubek & Flusser 2003, *IEEE TIP* 12(9), `10.1109/tip.2003.815260`; 2005, *IEEE TIP* 14(7), `10.1109/tip.2005.849322` [M] · Šroubek & Milanfar 2012, *IEEE TIP* 21(4):1687–1700, `10.1109/tip.2011.2175740` [M].

**Occlusion / two-layer / matting / light field.** Asada, Fujiwara, Matsuyama 1995, ICCV, `10.1109/iccv.1995.466793`; **1998, *IEEE TPAMI* 20(2):155–167, `10.1109/34.659933` [A]** · Bhasin & Chaudhuri 2001, ICCV, `10.1109/iccv.2001.937556` [M] · **Favaro & Soatto 2003, CVPR, `10.1109/cvpr.2003.1211519` [A]** · McGuire, Matusik, Pfister, Hughes, Durand 2005, *ACM TOG* 24(3):567–576, `10.1145/1073204.1073231` [M] · Vaish, Szeliski, Zitnick, Kang, Levoy 2006, CVPR, `10.1109/cvpr.2006.244` [M] · **Hasinoff & Kutulakos 2007, ICCV, `10.1109/iccv.2007.4408898` [A]** · Levin, Lischinski, Weiss 2008, *IEEE TPAMI* 30(2):228–242, `10.1109/tpami.2007.1177` [M] · McCloskey, Langer, Siddiqi 2011, *IEEE TPAMI* 33(3):647–654, `10.1109/tpami.2010.187`; ICPR 2010, `10.1109/icpr.2010.1069`; ACCV 2007, `10.1007/978-3-540-76386-4_25` [M] · **Wang, Efros, Ramamoorthi 2015, ICCV, `10.1109/iccv.2015.398` [F, skimmed]**; TPAMI 2016, `10.1109/tpami.2016.2515615` [M].

**PSF models, blind estimation, regularisers, artifacts.** Stokseth 1969, *JOSA* 59(10):1314, `10.1364/josa.59.001314` [M] · Gibson & Lanni 1991, *JOSA A* 8(10):1601, `10.1364/josaa.8.001601`; 1992, *JOSA A* 9(1):154, `10.1364/josaa.9.000154` [M] · Fish, Walker, Brinicombe, Pike 1995, *JOSA A* 12(1):58, `10.1364/josaa.12.000058` [M] · Markham & Conchello 1999, *JOSA A* 16(10):2377, `10.1364/josaa.16.002377` [M] · Chan & Wong 1998, *IEEE TIP* 7(3):370–375, `10.1109/83.661187` [M] · Rudin, Osher, Fatemi 1992, *Physica D* 60:259–268, `10.1016/0167-2789(92)90242-f` [M] · Levin, Weiss, Durand, Freeman 2009, CVPR, `10.1109/cvpr.2009.5206815`; 2011, CVPR, `10.1109/cvpr.2011.5995308` [M] · Yuan, Sun, Quan, Shum 2008, *ACM TOG* 27(3), `10.1145/1360612.1360673` [M] · Cho, Wang, Lee 2011, ICCV, `10.1109/iccv.2011.6126280` [M] · Liu & Jia 2008, ICIP, `10.1109/icip.2008.4711802` [M] · Šorel 2012, *IEEE TIP* 21(4):2329–2334, `10.1109/tip.2011.2176344` [M] · "Learning Lens Blur Fields", arXiv `2310.11535`, 2023 [M].

**Metrics / resolution without ground truth.** Nieuwenhuizen et al. 2013, *Nat. Methods* 10:557–562, `10.1038/nmeth.2448` [M] · Banterle, Bui, Lemke, Beck 2013, *J. Struct. Biol.* 183(3):363–367, `10.1016/j.jsb.2013.05.004` [M] · Descloux, Grußmayer, Radenovic 2019, *Nat. Methods* 16:918–924, `10.1038/s41592-019-0515-7`, addendum `10.1038/s41592-020-0963-0` [M].

**Learned EDOF / restoration.** Weigert et al. 2018, *Nat. Methods* 15:1090–1097, `10.1038/s41592-018-0216-7` [M] · Wu et al. 2019, *Nat. Methods* 16:1323–1331, `10.1038/s41592-019-0622-5` [M] · arXiv `1906.07496`, `2012.11892` [M].

**Focal-stack datasets / depth from focus.** Ens & Lawrence 1993, *IEEE TPAMI* 15(2):97–108, `10.1109/34.192482` [M] · Xiong & Shafer 1993, CVPR, `10.1109/cvpr.1993.340977` [M] · Watanabe & Nayar 1998, *IJCV* 27(3):203–225, `10.1023/a:1007905828438` [M] · Suwajanakorn, Hernández, Seitz 2015, CVPR, `10.1109/cvpr.2015.7298972` [M] · Hazirbas, Soyer, Staab, Leal-Taixé, Cremers 2018, ACCV, LNCS 11363, `10.1007/978-3-030-20893-6_33` [M] · Maximov, Galim, Leal-Taixé 2020, CVPR, `10.1109/cvpr42600.2020.00115` [M] · Herrmann et al. 2020, CVPR, `10.1109/cvpr42600.2020.00230` [M].

**Web resources fetched.** EPFL 3-D Deconvolution Grand Challenge, `bigwww.epfl.ch/deconvolution/challenge/` · MIT DSpace item `hdl.handle.net/1721.1/45513` (MIT-CSAIL-TR-2009-019, PDF + extracted text) · GitHub repository licence metadata via `gh api repos/<owner>/<repo>`.
