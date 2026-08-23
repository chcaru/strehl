# Workstream B — Algorithmic State of the Art for a Focus-Stacking Pipeline (2026)

Research subagent report. Target system: Rust, RAW-native (Sony ARW), wgpu/Vulkan baseline + optional CUDA, plugin architecture. Reference workload: **20–60 frames × 33 MP real Bayer RAW**, Sony A7C II + FE 100mm f/2.8 GM Macro, near 1:1.

---

## 0. How to read this report

### Evidence labels

| Label | Meaning |
|---|---|
| **MEASURED** | A number taken from the cited paper's own experiments. The benchmark is always named. |
| **VERIFIED** | Citation resolved against a primary source (arXiv API, Crossref, Unpaywall, CVF Open Access). Per-citation I state whether I read **full text** or **abstract/metadata only**. |
| **UNVERIFIED** | Named from background knowledge and *not* resolved against a primary source during this workstream. Treat as a lead to chase, **not** as a citation. |
| **could not confirm** | I searched, and found nothing. The exact query and source are recorded. This is *not* evidence of absence. |

### Method notes

- All arXiv IDs below were resolved through the arXiv API (`https://export.arxiv.org/api/query?id_list=...` / `search_query=ti:"..."`), not the HTML search UI.
- Paper bodies were read by downloading the PDF and extracting text with `pypdf` (helper `getpaper.py`, colocated with this report). `web_fetch` against `ar5iv` / `arxiv.org/html` truncated every paper to its Introduction and was abandoned.
- Non-arXiv citations were resolved through Crossref, and open-access status checked through Unpaywall.
- **Benchmark mismatch is called out inline every time.** Most MFIF papers evaluate on 2-image, low-resolution, synthetically-blurred datasets (Lytro, MFFW, MFI-WHU). Our workload is 20–60 frames of 33 MP real RAW. Results do not automatically transfer.
- Two numerical results in Section 5 are **my own simulation**, not from any paper. They are labelled `ORIGINAL EXPERIMENT` and must never be cited as literature.

### UNVERIFIED — named in the brief, not resolved in this workstream

These are widely-known methods that I did **not** get to a primary source. Do not put an ID, DOI, year or author list on any of them without re-resolving first.

| Method | Status |
|---|---|
| Farnebäck dense flow | UNVERIFIED |
| Phase correlation (Reddy & Chatterji) | UNVERIFIED |
| SIFT, ORB, SuperPoint | UNVERIFIED |
| Steerable pyramids (Simoncelli & Freeman) | UNVERIFIED |
| Contourlet / NSCT (Do & Vetterli) | UNVERIFIED |
| Graph cuts (Boykov / Kolmogorov / Veksler) | UNVERIFIED |
| Guided filter (He, Sun, Tang) | UNVERIFIED — note the *fusion* application (Li/Kang/Hu 2013) **is** verified, the filter paper itself is not |
| Brenner gradient, DCT-energy, GLCM focus measures | UNVERIFIED |
| Noise2Noise (Lehtinen et al.) | UNVERIFIED — `ti:"Noise2Noise"` returned 19 arXiv hits, the original was not in the first 8. **Do not cite.** Noise2Void (1811.10980) is verified and covers the self-supervised argument adequately. |

---

## 1. Alignment / registration for focus brackets

### 1.1 Why this is not ordinary image registration

Three effects stack on top of each other, and only the first is what generic registration solves:

| Effect | Model needed | Cause |
|---|---|---|
| Focus breathing | **similarity / affine** (scale + shift + small rotation), spatially global | Changing focus distance changes magnification. Internally-focusing lenses (the FE 100mm GM is one) breathe by a few percent over the focus range. |
| Rail parallax | **depth-dependent, non-global** | If the whole camera translates on a focus rail, near and far move by different amounts. This is *not* representable by any global 2D warp. |
| Content sharpness change | breaks the *data term*, not the motion model | The thing being matched literally changes appearance between frames. Gradient-based and feature-based costs are both biased by it. |

### 1.2 Verified evidence

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| Evangelidis & Psarakis, "Parametric Image Alignment Using Enhanced Correlation Coefficient Maximization", IEEE TPAMI, Oct 2008, DOI `10.1109/tpami.2008.113` | ECC: photometrically-invariant parametric alignment (translation / euclidean / affine / homography) | VERIFIED | metadata only (Crossref) |
| Araujo, Ponce, Mairal, arXiv **2311.17846** | The only real-world **raw focus-bracket** pipeline paper found. Uses OpenCV **ECC with an affine model**, chained frame-to-**immediate predecessor**, transforms estimated on RGB then scaled and applied to RGGB raw. | VERIFIED / MEASURED | **full text** |
| Monod, Delon, Veit, IPOL 11 (2021) 142–169, arXiv **2110.09354**, DOI `10.5201/ipol.2021.336` | Complete, reproducible spec of HDR+ tile-based pyramid alignment, incl. its failure modes | VERIFIED | **full text** |
| Wronski et al., arXiv **1905.03277** | Alignment error concentrates on edges (aperture problem); anisotropic merge kernels are the mitigation | VERIFIED / MEASURED | **full text** |
| Teed & Deng, RAFT, arXiv **2003.12039** | All-pairs correlation volume + recurrent GRU flow updates | VERIFIED / MEASURED | abstract + metadata |
| Wang et al., SEA-RAFT, arXiv **2405.14793** | Simpler/faster RAFT with the best reported cross-dataset generalization | VERIFIED / MEASURED | abstract + metadata |
| Kroeger, Timofte, Dai, Van Gool, "Fast Optical Flow using Dense Inverse Search" (DIS), ECCV 2016, DOI `10.1007/978-3-319-46493-0_29` | Real-time dense flow via patch inverse search + variational refinement | VERIFIED | metadata only |
| Sun et al., LoFTR, arXiv **2104.00680**; Wang et al., Efficient LoFTR, arXiv **2403.04765**; Lindenberger et al., LightGlue, arXiv **2306.13643** | Detector-free / learned matching; Efficient LoFTR reports ~2.5× speedup over LoFTR and surpassing SuperPoint+LightGlue accuracy | VERIFIED / MEASURED | abstract + metadata |
| Wu, Monno, Okutomi, arXiv **2402.18175** (ICASSP 2024) | Aberration-aware depth-from-defocus that explicitly "handle[s] the focus breathing phenomenon that occurs in real DfD situations" | VERIFIED | abstract only |

### 1.3 The load-bearing quotes (Araujo et al. 2311.17846, full text read)

> "Correct registration of the frames on each burst is crucial to avoid the magnification problem of images with different focus."

Figure 3 is captioned as showing "misalignment due to changing magnification during the focus bracketing."

They chain to the previous frame rather than to a global reference **because** "the first and last frames are difficult to align correctly due to the large blur between them" — i.e. the data term degrades as the sharpness gap grows, so you only ever compare neighbours.

Critically, **global affine was not enough**: they still observed residual *sub-pixel local* shifts after global ECC alignment, and added a learned deformable-convolution alignment module operating on 128×128 crops to absorb it. They also report that their fusion block had to replace an earlier Cross-Local-Fusion design because using the first frame as reference "induces a significant bias towards the first image of the burst".

**This is the single most important architectural fact in Section 1: global parametric alignment on a focus bracket leaves sub-pixel residual, and every downstream stage must be residual-tolerant rather than assume pixel-perfect registration.**

### 1.4 HDR+ alignment, and its documented failure modes (2110.09354, full text read)

4-level coarse-to-fine Gaussian pyramid, tile-based, alternating L1/L2 norms `{2,2,2,1}` by level, with sub-pixel refinement applied only when the integer displacement is interior (‖µ‖<1). The paper explicitly lists the failure modes: **motion not parallel to the image plane** (i.e. scale change — exactly focus breathing), **local minima**, **sensitivity to noise**, and **occlusions**.

Note the direct consequence for us: HDR+ alignment is *translation-per-tile*. A tile grid can approximate a global scale change piecewise, which is why it partially survives breathing, but it has no scale model and no regularizer across tiles.

### 1.5 Failure modes on macro subjects

Fine repeating structure — hairs, scales, ommatidia in a compound eye — produces:

1. **Aliasing-driven false matches.** A repeating period near the Nyquist limit of the sensor gives a correlation surface with many near-equal minima. HDR+'s own listed "local minima" failure. UNVERIFIED as a *measured* macro result — I found no paper that quantifies this on macro subjects.
2. **The aperture problem on hair-like structures.** Wronski et al. (full text) state alignment error concentrates on edges because they are locally ambiguous, and demonstrate that isotropic merge kernels then produce "heavy zipper artifacts along edges" while anisotropic kernels (k_stretch=4, k_shrink=2) fix them. That is a merge-side fix for an alignment-side problem, and it is the right pattern to copy.
3. **Sharpness-gradient bias.** A gradient-based cost between a sharp frame and a blurred frame is minimized by *shrinking* the sharp content toward the blurred one, biasing the estimated scale. Mitigation is Araujo's chaining (neighbouring frames differ least in sharpness) plus band-limiting the alignment signal so both frames are compared at a scale where both are effectively in focus.
4. **Rail parallax.** `all:"focus rail" OR all:"focus stacking parallax"` on the arXiv API (2026-08-22) → **0 results**. **could not confirm** any quantitative treatment of focus-rail parallax vs internal-focus breathing. Treat "a rail bracket needs a depth-dependent warp, an internal-focus bracket does not" as an **untested assumption** of this project.

### 1.6 Recommendation matrix

| Method | Models breathing? | Handles parallax? | Robust to sharpness change? | Cost @ 33 MP × 60 | Verdict |
|---|---|---|---|---|---|
| Phase correlation (global) | translation only | no | partial (can band-limit) | very cheap, FFT | good *initializer* only |
| **ECC, affine/similarity, coarse-to-fine, chained** | **yes** | no | yes if chained + band-limited | moderate, GPU-parallel | **primary** |
| Feature-based (SIFT/ORB/SuperPoint+LightGlue) | yes (fit similarity from matches) | partially (RANSAC rejects) | poor — detectors are sharpness-selective | moderate | fallback / sanity check |
| LoFTR / Efficient LoFTR | yes | partially | better (detector-free, semi-dense) | heavy at 33 MP | tile-wise refinement only |
| RAFT / SEA-RAFT / DIS (dense flow) | implicitly | **yes** | poor — trained on brightness-constant, sharpness-constant data | very heavy at 33 MP; DIS is the cheap one | **residual refinement after global**, never as the primary |
| HDR+ tile pyramid | piecewise | piecewise | moderate | cheap, tile-parallel | excellent *residual* stage; pairs naturally with the merge |

### 1.7 If we could only implement one method here, which and why

**ECC with a similarity/affine model, estimated coarse-to-fine on Bayer-quad luminance, chained frame-to-previous, followed by an HDR+-style tile-translation residual pass.**

Reasons, in order of weight:

1. It is what the only real-world raw focus-bracket paper actually used (Araujo et al., 2311.17846, full text) — the one paper whose data most resembles ours.
2. Focus breathing is a **scale** change. Translation-only methods (phase correlation, plain tile alignment) cannot represent it; a homography over-parameterizes it and will absorb genuine parallax into a bogus perspective term. Similarity/affine is the correct model class.
3. ECC's normalized correlation criterion is invariant to photometric gain/bias, which matters because focus change alters local contrast even when exposure is constant.
4. Chaining bounds the sharpness gap in every pairwise problem, which is the only structural defence against the sharpness-gradient bias.
5. The tile residual pass is nearly free if you are already doing a tile-based merge, and it gives you per-tile displacement statistics that the merge robustness mask needs anyway (Wronski Eq. 7 uses exactly this).

Explicitly **not** dense optical flow as the primary: RAFT/SEA-RAFT assume brightness constancy between frames whose content has the *same* sharpness. A focus bracket violates that by construction, and at 33 MP × 60 frames the cost is prohibitive versus its benefit.

### 1.8 What the pluggable interface for this stage must expose

```rust
/// A registration plugin maps every frame into a common reference lattice.
pub trait Aligner {
    /// Declared motion model. The pipeline uses this to decide whether a
    /// depth-dependent stage (parallax handling) is required downstream.
    fn model(&self) -> MotionModel; // Translation | Similarity | Affine | Homography | Dense

    /// Preferred input domain. Plugins that want CFA get CFA; plugins that
    /// need RGB get a cheap half-res demosaic, never a full one.
    fn input_domain(&self) -> InputDomain; // BayerQuadLuma | HalfResRgb | FullRgb

    /// Estimate the warp field for the whole stack at once. Whole-stack, not
    /// pairwise, so that chained/global/graph strategies are all expressible.
    fn estimate(
        &self,
        stack: &StackView,          // lazily-decoded frames + focus metadata
        reference: ReferencePolicy, // Fixed(idx) | Chained | Median | Synthetic
        ctx: &mut GpuCtx,
    ) -> Result<WarpField, AlignError>;
}

/// The warp must be *queryable at sub-pixel resolution*, and must report its
/// own uncertainty — downstream merge robustness depends on it.
pub trait WarpField {
    fn warp(&self, frame: usize, p: Vec2) -> Vec2;
    /// Per-pixel (or per-tile) confidence, 0..1. Merge uses this to gate.
    fn confidence(&self, frame: usize, p: Vec2) -> f32;
    /// Local motion span in a neighbourhood — Wronski Eq. 7's motion prior.
    fn local_motion_magnitude(&self, frame: usize, p: Vec2) -> f32;
    /// Jacobian, so the merge can compensate for magnification-induced
    /// resampling density changes instead of double-counting them.
    fn jacobian(&self, frame: usize, p: Vec2) -> Mat2;
}
```

Non-negotiable properties of the interface:

- **Warps are queried, never baked.** Resampling every 33 MP frame to disk destroys sub-pixel information that the merge (and any super-resolution side effect, §6) needs. The merge must sample source pixels through the warp.
- **Confidence is mandatory, not optional.** Every downstream stage in this report degrades gracefully only if it knows where alignment is untrustworthy.
- **The Jacobian is mandatory** specifically because of focus breathing: a scale change means different frames contribute samples at different densities, and a merge that ignores this will be biased toward whichever frames are locally magnified.

---

## 2. Focus / sharpness measures

### 2.1 The core problem: a focus measure is a *noise* measure in flat regions

In a texture-free region every frame contains the same (zero) high-frequency signal plus independent sensor noise. Any operator that reports "energy in a high-pass band" therefore reports *noise power*, and `argmax` over frames selects the noisiest frame. This is the mechanism behind the prior project's headline defect (quantified in §5.3).

### 2.2 Verified evidence

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| **Surh, Jeon, Park, Im, Ha, Kweon, "Noise Robust Depth from Focus Using a Ring Difference Filter", CVPR 2017, DOI `10.1109/cvpr.2017.262`** | **The** quantitative analysis of focus-measure behaviour under noise. Introduces the ring/disk **gap space**. | VERIFIED / MEASURED | **full text** (CVF Open Access) |
| Pertuz, Puig, Garcia, "Analysis of focus measure operators for shape-from-focus", Pattern Recognition 46(5):1415–1432, 2013, DOI `10.1016/j.patcog.2012.11.011` | The standard comparative survey of ~36 focus measures | VERIFIED (metadata, 3 independent resolutions) | **metadata only — the paper is closed access** (Unpaywall: `is_oa: false`, `oa_status: "closed"`, `best_oa_location: null`). **Nothing may be quoted from it.** |
| Jeon et al., IEEE TIP 2020, DOI `10.1109/tip.2019.2937064` | Journal extension of the RDF line of work | VERIFIED | metadata only |
| **DDL-SFF**, arXiv **2512.10498**, IJCV 2026, DOI `10.1007/s11263-025-02596-z` | Generalizes RDF into multi-scale **Directional Dilated Laplacian** kernels computed *outside* the learned network | VERIFIED | abstract + introduction |
| Nayar & Nakagawa, IEEE TPAMI 1994, DOI `10.1109/34.308479` | Sum-Modified-Laplacian (SML), the canonical SFF operator | VERIFIED | metadata only |
| Subbarao & Choi, IEEE TPAMI Mar 1995, DOI `10.1109/34.368191` | Focused-image-surface / SFF theory | VERIFIED | metadata only |
| Pech-Pacheco et al., ICPR 2000, DOI `10.1109/icpr.2000.903548` | Source of "variance of Laplacian" | VERIFIED | metadata only |
| Ashfaq & Mahmood, SSRN 2023, DOI `10.2139/ssrn.4436889` | Later focus-measure work in the same line | VERIFIED | metadata only |

`all:"ring difference filter"` on the arXiv API → **0 results** (it is IEEE-only). The CVF Open Access PDF is the readable primary source.

### 2.3 The decisive measurement (Surh et al., CVPR 2017, Table 1 — MEASURED)

Metrics: **Winner Margin** `WM = (c₁ − c₂ₘ)/Σ_l c(l)` (gap between the best and second-best-mode focus response, normalized) and **Curvature** `CUR = 2c(l_max) − c(l_max−1) − c(l_max+1)` (sharpness of the focus peak). Higher is better for both; **negative means the measure is confident about the wrong answer**.

Winner Margin (×10⁻³) vs. added noise σ:

| Focus measure | σ = 0 | σ = 0.005 | σ = 0.01 | σ = 0.02 |
|---|---|---|---|---|
| Laplacian | 0.137 | 0.002 | **−0.228** | **−0.212** |
| Naive (dilated) | 0.227 | 0.424 | 0.552 | 0.674 |
| **RDF** | **0.321** | **0.483** | **0.584** | **0.697** |

Curvature (×10⁻⁵):

| Focus measure | σ = 0 | σ = 0.005 | σ = 0.01 | σ = 0.02 |
|---|---|---|---|---|
| Laplacian | 0.881 | −0.287 | −2.354 | −2.848 |
| Naive (dilated) | 1.880 | 4.372 | 5.998 | 7.518 |
| **RDF** | **2.599** | **4.779** | **6.355** | **7.999** |

**The Laplacian's winner margin and curvature both go negative at σ ≥ 0.01.** That is not "degraded accuracy"; it is a measure that has inverted. Any pipeline whose focus measure is variance-of-Laplacian or SML on real RAW is, in noisy regions, actively anti-correlated with focus.

Why a larger support helps, verbatim:

> "if the image were to contain noise... the error due to this noise would be greater than if more pixels are compared... By sampling more pixels, the effects of noise is distributed amongst a larger set of sampled points, suppressing its effects."

And why you cannot simply dilate the Laplacian kernel — the reason for the **gap** between ring and disk:

> "Similar pixel values from nearby regions are redundant and only decreases the confidence of the measurement since the gradient is maximized when the pixel is in focus."

**Benchmark caveat (important):** evaluated on 7 light-field datasets ≥768×768 with 30 depth labels, using *synthetic* depth-dependent blur and *synthetic* signal-dependent Gaussian noise, over 4,276,224 pixel locations. It is not real camera RAW and not 33 MP. The *ordering* is credible and the mechanism is physically sound; the absolute numbers should not be transferred.

### 2.4 The 2026 successor: DDL-SFF (2512.10498)

Generalizes the ring-difference idea into a bank of **multi-scale, directional, dilated Laplacian kernels**, chosen because (verbatim from the abstract/intro I read) handcrafted kernels

> "are robust to noise, capture long-range dependencies, and account for directional focus variations"

and are computed

> "outside the learning framework via simple convolution operations"

That last property is exactly what a plugin architecture wants: the focus volume is a deterministic, cheap, GPU-friendly convolution stage, and only the *regularizer* on top of it is learned (see §4).

### 2.5 Classical operator triage for our workload

| Operator | Noise behaviour | Bayer-friendly | Verdict for 33 MP RAW |
|---|---|---|---|
| Variance of Laplacian / modified Laplacian / SML | **inverts under noise** (Surh Table 1) | yes, per-plane | **do not use alone** |
| Tenengrad (Sobel energy) | same failure class, slightly larger support | yes | no |
| Brenner gradient | UNVERIFIED; 2-pixel difference ⇒ maximal noise sensitivity | yes | no |
| Wavelet / DWT subband energy | selection on subbands is what caused the prior project's defect (§5) | yes | only as a *representation*, never as a selector |
| DCT-based | UNVERIFIED | block-based | not evaluated |
| Steerable pyramid | UNVERIFIED source; directional selectivity is the same idea DDL-SFF formalizes | yes | good representation, use DDL kernels instead |
| GLCM | UNVERIFIED; expensive at 33 MP | no | no |
| **Ring Difference Filter / DDL** | **best WM and CUR at every σ tested** | yes, per-plane | **primary** |
| Learned (DefocusNet, DFV, DEReD, FOSSA §4) | domain-gap dominated | needs RGB | as a *prior*, not as the measure |

### 2.6 If we could only implement one method here, which and why

**A multi-scale ring-difference / directional-dilated-Laplacian focus response, computed per Bayer colour plane, on aligned but un-demosaiced data.**

1. It is the only focus measure in this survey with a published measurement showing it stays *positively* informative as noise rises, while the Laplacian family inverts (Surh Table 1, MEASURED).
2. The gap-space construction is a principled answer to the exact failure our workload has: it increases the sample count (noise averaging) without including redundant nearby pixels (which would flatten the peak).
3. It is a plain convolution bank — trivially GPU-parallel, deterministic, no training data, no domain gap, and it is what the 2026 SOTA learned method (DDL-SFF) still uses as its front end.
4. Multi-scale is not optional at 33 MP: a single kernel size cannot simultaneously resolve a hair (a few pixels) and a smooth chitin surface (hundreds of pixels).

**Corollary that governs the whole architecture:** the focus measure must output not just a response but a *confidence*, and the confidence must be **calibrated against the sensor noise floor**. A focus response whose inter-frame variation is smaller than the noise-induced variation carries zero information and must be reported as such. This is the hook that §5's merge uses.

### 2.7 What the pluggable interface for this stage must expose

```rust
pub trait FocusMeasure {
    fn input_domain(&self) -> InputDomain;   // CfaPlane | Luma | Rgb
    /// Scales (in source pixels) at which this measure reports. Multi-scale
    /// measures return >1; the pipeline is required to keep them separate
    /// rather than collapsing them, so §3 can fuse per band.
    fn scales(&self) -> &[f32];

    /// Per-frame, per-scale, per-CFA-plane response over a tile.
    /// NOTE: per-plane is mandatory, not a nicety — see §7, longitudinal CA
    /// means R, G and B peak at *different* frames.
    fn response(
        &self,
        tile: &AlignedTileStack, // N frames, warped-sampled, still CFA
        noise: &NoiseModel,      // calibrated λ_shot, λ_read for this ISO
        out: &mut FocusVolume,   // [frame][scale][plane][y][x]
        ctx: &mut GpuCtx,
    ) -> Result<(), FocusError>;

    /// Expected response of this operator on *pure noise* at the given
    /// signal level. This is what makes "is this peak real?" answerable.
    /// A plugin that cannot supply this must declare it and will be
    /// restricted to non-selective roles.
    fn noise_floor(&self, noise: &NoiseModel, signal_level: f32, scale: f32) -> f32;
}
```

Required properties:

- **`noise_floor` is the whole point.** Without it, the pipeline cannot distinguish "frame 12 is sharpest" from "frame 12 got lucky". Make it part of the trait, not an afterthought.
- **Per-plane output** (§7).
- **Per-scale output kept separate** (§3): fusion decisions are per band, and collapsing scales in the focus measure destroys the information the merge needs to decide *which bands* differ meaningfully between frames.
- Responses are written into a caller-owned `FocusVolume` so the memory layout is the pipeline's decision — at 60 × 33 MP × 4 scales × 4 planes this is the dominant allocation in the system and cannot be left to plugins.

---

## 3. Merging / fusion

### 3.1 Verified evidence

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| Burt & Adelson, "The Laplacian Pyramid as a Compact Image Code", IEEE Trans. Communications, Apr 1983, DOI `10.1109/tcom.1983.1095851` | The Laplacian pyramid | VERIFIED | metadata only |
| Burt & Kolczynski, ICCV 1993, DOI `10.1109/iccv.1993.378222` | Pyramid fusion with local salience + match measures — the ancestor of every band-selective merge | VERIFIED | metadata only |
| Mertens, Kautz, Van Reeth, "Exposure Fusion", PG'07, DOI `10.1109/pg.2007.17` | Weighted Laplacian-pyramid blending with per-pixel quality weights | VERIFIED | metadata only |
| Li, Kang, Hu, "Image Fusion with Guided Filtering", IEEE TIP, Jul 2013, DOI `10.1109/tip.2013.2244222` | Guided-filter weight-map refinement — the standard classical seam fix | VERIFIED | metadata only |
| Pérez, Gangnet, Blake, "Poisson image editing", SIGGRAPH 2003, DOI `10.1145/1201775.882269` | Gradient-domain compositing | VERIFIED | metadata only |
| Liu et al., "Multi-focus image fusion: A Survey of the state of the art", Information Fusion, Dec 2020, DOI `10.1016/j.inffus.2020.06.013` | The reference MFIF survey | VERIFIED | metadata only |
| **MFIFB**, arXiv **2005.01116** | The MFIF benchmark: "a test set of 105 image pairs, a code library of 30 MFIF algorithms, and 20 evaluation metrics" | VERIFIED | abstract |
| **GMFF / StackMFF V4**, arXiv **2512.21495** | 2026 generative MFIF; states the "no frame is in focus" problem explicitly | VERIFIED | **full text** |
| **IPS**, arXiv **2603.07120** | Trains MFIF *without* real multi-focus data by pixel-shuffling an image with its low-pass copy | VERIFIED | abstract |
| Araujo, Ponce, Mairal, arXiv **2311.17846** | Raw-domain deep focus-stacking with measured PSNR/SSIM on 20+-frame real bursts | VERIFIED / MEASURED | **full text** |
| Wronski et al., arXiv **1905.03277** | Anisotropic kernel merge; the zipper/halo mechanism and its fix | VERIFIED / MEASURED | **full text** |

### 3.2 Benchmark mismatch — say this out loud every time

MFIFB is **105 image *pairs***. Lytro, MFFW and MFI-WHU are 2-image, low-resolution, mostly synthetically-blurred. Araujo et al. put it plainly (full text):

> "most datasets with simulated blur have been designed with only two images and low resolution, which makes them unsuitable for high-resolution micro and macro photography where focus bursts are usually large (i.e., more than 20 images)."

and

> "only one approach [61] proposed a deep learning architecture that can take more than two images, however, they experiment with multi-focus image fusion datasets with 2 and 3 images by burst."

and on the most-cited MFIF test set:

> "quantitative comparison is unfortunately impossible on the Lytro dataset because this dataset does not have any ground truth."

**Consequence for us: no published MFIF metric is evidence about our workload.** Any claimed SOTA from that literature must be re-validated at 20–60 frames × 33 MP before it earns a place in the pipeline.

### 3.3 The one measurement on real multi-frame focus bursts (Araujo et al., Table 3 — MEASURED)

Ground truth is **HeliconFocus output**, i.e. pseudo-GT, on real bursts. PSNR↑ / SSIM↑, reported train/test:

| Method | PSNR (train/test) | SSIM (train/test) |
|---|---|---|
| RGB Laplacian pyramid | 25.92 / 26.88 | 0.659 / 0.712 |
| RGB Wavelets | 26.27 / 27.65 | 0.797 / 0.828 |
| RGB U-Net | 35.13 / 36.29 | 0.899 / 0.922 |
| **RGB FocusDeep** | **36.99 / 38.47** | **0.942 / 0.965** |
| Raw U-Net | 30.01 / 30.21 | 0.759 / 0.767 |
| Raw FocusDeep | 33.47 / 32.89 | 0.882 / 0.898 |

**Read the caveat before the numbers.** The "ground truth" is HeliconFocus's *demosaiced RGB* output. A raw-domain method is therefore scored on how well it reproduces a demosaiced RGB pipeline's result. **The lower raw numbers are a property of the metric, not evidence that raw-domain fusion is worse.** This table is best read as: classical Laplacian/wavelet selection is ~10 dB behind a learned merge against a commercial reference, and the wavelet merge — the prior project's approach — is the second-worst entry.

Araujo et al. also document HeliconFocus's own failure modes (Fig. 8): "a superposition between the foreground and background not respecting the real depth of the scene", and "HeliconFocus confuses blurry pixels with sharp ones in a saturated setting."

### 3.4 Halo and seam artifacts: mechanism and fixes

| Artifact | Mechanism | Verified fix |
|---|---|---|
| **Halo** around a sharp foreground edge over a blurred background | The blurred frame's out-of-focus foreground *bleeds outward*; if the merge selects that frame's pixels just outside the edge, the foreground's blur ring is composited into the background | Band-limited (pyramid) blending rather than pixel selection — Burt & Kolczynski; plus label smoothing so the decision boundary follows the *edge*, not the blur ring |
| **Seam / discontinuity** in the index map | Independent per-pixel `argmax` with a noisy focus measure | Guided-filter weight-map refinement (Li/Kang/Hu 2013, VERIFIED metadata); MRF/graph-cut smoothing (mechanism UNVERIFIED here) |
| **Zipper / checkerboard along edges** | Sub-pixel misalignment on locally-ambiguous edge structure | **Wronski et al., full text:** isotropic kernels (k_stretch=1, k_shrink=1) cause "small misalignments cause heavy zipper artifacts along edges"; anisotropic kernels from the local gradient structure tensor (k_stretch=4, k_shrink=2) remove them |
| **Edge artifacts that get *worse* with more frames** | Hard selection + uncertain focus estimation | **GMFF (2512.21495, full text):** artifacts "worsen as the number of focal planes increases", and decision-map methods are the worst affected. **This is a direct warning about our 60-frame workload.** |
| **Tone/level discontinuity between regions from different frames** | Exposure/illumination drift across a long bracket | Gradient-domain / Poisson compositing (Pérez et al. 2003, VERIFIED metadata) as a *final* pass |

### 3.5 The two degenerate regions

**(a) No frame is in focus.** GMFF (2512.21495, full text) is the only source found that states this explicitly:

> "Existing fusion algorithms generally assume that, for every spatial location in the scene, there is at least one input image in which that location is in focus. Furthermore, current fusion models often suffer from edge artifacts caused by uncertain focus estimation or hard-selection operations in complex real-world scenarios."

Their answer is a two-stage system: a deterministic pre-fusion (StackMFF V4) followed by **IFControlNet**, a latent-diffusion generative restoration. The StackMFF lineage they describe: V1 = 3D CNN; V2 = focal-plane depth regression; V3 = pixel-level classification; V4 = V3 with ~4× lower cost. They also criticize Araujo et al.'s supervision: "Since these supervisory images are not true ground truth and the training data are limited, the fusion performance is constrained."

**My position for this project:** generative hallucination is unacceptable as a default in a scientific/macro imaging tool. The correct behaviour when no frame is in focus is to (i) detect it — the focus peak is at the boundary of the sampled z-range or the peak is below the noise floor from §2.7 — (ii) **average all frames** there (which is optimal for noise, §5), and (iii) **report it in a confidence map** so the user knows to shoot more slices. Deconvolution or generative restoration should be an opt-in plugin, never the default path.

**(b) Many frames in focus** (flat, low-texture, or deep-DoF regions). Here the frames are, to within the noise floor, *identical*. Selection is not merely unnecessary, it is actively harmful — it throws away N−1 independent noise realizations. This region should be a straight (robustness-weighted) average, giving the √N gain. This is the entire subject of §5.

### 3.6 If we could only implement one method here, which and why

**A band-selective, noise-gated accumulation over all N frames — HDR+'s per-frequency Wiener gate (§5.4) applied inside a Laplacian/steerable pyramid, with Wronski-style anisotropic structure-tensor kernels for the spatial resampling — in the CFA domain.**

The single sentence version: **selection must be conditional on the frames actually differing by more than the noise floor; everywhere else, average.**

1. It is the only formulation in this survey that is simultaneously correct in *both* degenerate regions of §3.5: it converges to selection where defocus genuinely attenuates a band, and to averaging where it does not.
2. It is provably non-amplifying (my simulation, §5.3: Wiener shrinkage output std ≤ 1.0 for every τ and N tested), unlike the softmax/argmax wavelet merges that produce 1.9–2.6× single-frame noise.
3. The anisotropic-kernel component is the one *measured* halo/zipper fix in this survey (Wronski, full text) and it is a gather-style GPU kernel.
4. It subsumes demosaicing (§8), so it removes a whole pipeline stage rather than adding one.
5. It requires no training data, so it has no domain gap — which matters given §3.2.

Deep MFIF is deliberately **not** the primary recommendation: every measured result in that literature is on 2–3 image, low-resolution, mostly-synthetic data (§3.2), and GMFF itself reports that hard-selection artifacts worsen as the frame count grows.

### 3.7 What the pluggable interface for this stage must expose

```rust
pub trait Merger {
    fn input_domain(&self) -> InputDomain;      // Cfa | Rgb
    fn output_domain(&self) -> OutputDomain;    // Rgb (may bypass demosaic entirely)

    /// Whether this merger produces its own noise reduction. The pipeline
    /// uses this to decide whether a separate denoise stage is even legal.
    fn noise_behaviour(&self) -> NoiseBehaviour; // Averaging | Selective | Hybrid

    fn merge(
        &self,
        tile: &AlignedTileStack,
        focus: &FocusVolume,      // from §2, per-frame/scale/plane + confidence
        warp: &dyn WarpField,     // queried, not baked (§1.8)
        noise: &NoiseModel,       // calibrated, per-ISO, per-CFA-plane
        out: &mut MergedTile,
        ctx: &mut GpuCtx,
    ) -> Result<MergeReport, MergeError>;
}

pub struct MergeReport {
    /// Per-pixel effective number of frames averaged. THE key diagnostic:
    /// n_eff ≈ 1 means "we selected" (noise unchanged), n_eff ≈ N means
    /// "we averaged" (noise / sqrt(N)). Regression-test this directly.
    pub n_eff: Map<f32>,
    /// Per-pixel predicted output noise sigma, so the pipeline can verify
    /// it never exceeded the input noise floor.
    pub predicted_sigma: Map<f32>,
    /// Where no frame was in focus (§3.5a).
    pub unfocused_mask: Map<bool>,
}
```

Required properties:

- **`n_eff` and `predicted_sigma` are mandatory outputs.** They are what turn "our merge is noisy" from a subjective complaint into an automated test. A merge plugin that cannot report them cannot be validated and should be marked experimental.
- **The merger owns tiling, not the pipeline** — overlap, window function and tile size are algorithm-specific (HDR+ uses raised-cosine half-overlapping tiles; a pyramid merge does not tile the same way).
- **The merger may output RGB from CFA input** (§8), so demosaicing cannot be a fixed earlier stage.
- Artifact suppression (guided-filter refinement, graph-cut smoothing, Poisson compositing) belongs in a **separate `PostMerge` trait** operating on `MergedTile + MergeReport`, so third parties can contribute seam fixes without reimplementing the merge.

---

## 4. Depth-map estimation from the focus stack (shape-from-focus)

### 4.1 Verified evidence

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| **FOSSA**, "Zero-Shot Depth from Defocus", arXiv **2603.26658v2** (ECCV 2026) | Focus-stack transformer **initialized from the Depth Anything V2 metric checkpoint** — the direct answer to the "can monocular depth priors regularize SFF?" question | VERIFIED / MEASURED | **full text** (intro, related work, implementation, results) |
| **DDL-SFF**, arXiv **2512.10498**, IJCV 2026, DOI `10.1007/s11263-025-02596-z` | Why naive one-step index extraction (argmax / soft-argmin) amplifies noise, and a GRU-based multi-scale fix | VERIFIED | abstract + introduction |
| Moeller, Benning, Schönlieb, Cremers, "Variational Depth from Focus Reconstruction", arXiv **1408.0173**, DOI `10.1109/TIP.2015.2479469` | Nonconvex data fidelity + convex nonsmooth regularizer, solved with linearized ADMM; "robust to noise and leads to more realistic depth maps" | VERIFIED | abstract only |
| **AWGIF**, arXiv **2201.06823** | Adaptive weighted guided filtering for SFF depth-map enhancement | VERIFIED | abstract only |
| Minimal Focal Stack SFF, arXiv **2604.01603** (CVPRW 2026) | Physics-based augmentation (all-in-focus estimate + Energy-of-Difference maps) enabling SFF from as few as 2 images; ConvGRU refinement | VERIFIED | abstract only |
| **Depth Anything V2**, arXiv **2406.09414** | The monocular depth prior in question | VERIFIED | abstract + metadata |
| EDFF, arXiv **2405.06944** | Depth from focus on an *event* focal stack | VERIFIED | abstract only |
| Wu, Monno, Okutomi, arXiv **2402.18175** | Aberration-aware DfD that models focus breathing | VERIFIED | abstract only |
| arXiv **2203.02953** | PSF estimation of defocus | VERIFIED | abstract only |
| Surh et al., CVPR 2017, DOI `10.1109/cvpr.2017.262` | See §2.3 — the focus volume this stage consumes | VERIFIED / MEASURED | **full text** |

### 4.2 Can a monocular depth prior regularize shape-from-focus? Yes — with precedent

FOSSA (2603.26658, full text) answers this directly and affirmatively:

> "We initialize the ViT blocks from the pretrained DepthAnything v2 [51] indoor metric checkpoint, and zero-initialize the MLP in the stack attention layers."

Architecture, as read: L₁ = 4 focus-stack feature layers with **stack attention plus a focus-distance embedding**, a collapse along the stack dimension, L₂ = 8 refinement ViT layers, and a DPT head. Trained on Hypersim (66k) + TartanAir (307k) with **stack size 5** and randomized focus distances, apertures and PSFs. 40 epochs, 2 days on 4×L40.

**MEASURED:** AbsRel **−55.7%** vs DepthPro on their ZEDD benchmark; MSE **−40.4%** on DDFF vs DualFocus.

**Domain gap — this is the load-bearing caveat.** ZEDD is 100 scenes at 4104×2736, F/1.4–16, with focus distances of **0.8–8.1 m** and 9 images per stack, with Ouster Lidar ground truth. Our workload is a **1:1 macro stack whose total depth range is millimetres**, with 20–60 slices, at magnifications where the thin-lens approximations underpinning these models are least valid. The *architectural* lesson (initialize from a monocular prior, zero-init the stack-attention path so the prior is preserved at step 0) transfers. The *weights* almost certainly do not.

Prior art FOSSA names: DefocusNet, DFV, HybridDepth, DualFocus, DEReD, DDFS. (Named in the paper; individually UNVERIFIED here.)

### 4.3 Why naive index extraction is wrong (DDL-SFF, 2512.10498)

Verbatim from the text I read:

> "they estimate depth via a simple one-step aggregation technique that often introduces artifacts and amplifies noise in the depth map"

> "This one-step reduction can amplify noise, discard important spatial context, and lead to inaccurate depth predictions, particularly around object boundaries and in regions with subtle focus transitions."

The methods it groups as "one-step aggregation" (softmax / soft-argmin over the focus volume) are attributed to Wang et al. 2021, Won & Jeon 2022, Yang/Huang/Zhou 2022 and Fujimura et al. 2024. Its fix: multi-scale **GRU iterative refinement at low resolution** followed by **learned convex upsampling** — i.e. the RAFT update-operator pattern applied to a focus volume.

### 4.4 Sub-frame focus-peak interpolation

The bracket samples focus at discrete z. The true peak lies between slices. Standard practice is to fit the three responses around the argmax:

- **Parabolic (quadratic) fit** on raw responses: `δ = 0.5·(c₋₁ − c₊₁)/(c₋₁ − 2c₀ + c₊₁)`, peak index `l_max + δ`.
- **Gaussian fit** = parabolic fit on `log c`, which is the standard choice when the focus response is modelled as approximately Gaussian in z.

I did **not** find a paper in this workstream that measures parabolic-vs-Gaussian sub-frame interpolation accuracy specifically on a focus stack. Mark the choice **UNVERIFIED** and settle it empirically on our own data.

> **SETTLED by [M33](M33-subframe-offset-measured.md) — use the Gaussian (log-domain) fit, with baseline subtraction.**
> *Annotation added by the orchestrator at fold time; the original text above is left as written.*
> The parabolic fit's **peak position** is adequate at operational sampling (4.03× better than the
> trivial argmax, only 9.4% worse than the log fit), but its **peak height** is anti-correlated with
> the truth — on a synthetic Gaussian its predicted deficit falls 21× while the true deficit rises 8×.
> The log fit is exact on a Gaussian response and reaches calibration 0.710 / 51.2%-within-2× on real
> data, against the parabola's 0.457 / 37.5%. Baseline subtraction is required because `log` is not
> shift-invariant and the focus measure does not reach zero when defocused. Facts 271-274.

Two things the literature *does* make clear are prerequisites for this fit to mean anything:

1. The response must be **positively curved at the peak** — Surh's CUR metric. At σ ≥ 0.01 the Laplacian's curvature is **negative** (§2.3), so a parabolic fit on a Laplacian focus volume in noisy regions fits a *minimum* and returns garbage. Sub-frame interpolation is only valid on a noise-robust measure.
2. The peak must be interior. A peak at l = 0 or l = N−1 means the true focus is outside the sampled range (§3.5a) and must be flagged, not extrapolated.

### 4.5 Regularization ladder

| Stage | Method | Cost | Status |
|---|---|---|---|
| 0 | Raw argmax over focus volume | trivial | baseline; noisy, artifact-prone (§4.3) |
| 1 | Confidence-weighted argmax + parabolic sub-frame fit, confidence from §2.7 `noise_floor` | trivial | **minimum viable** |
| 2 | Guided-filter smoothing of the index map, guided by the merged all-in-focus image (AWGIF 2201.06823, abstract) | cheap, GPU | strong default |
| 3 | Variational: nonconvex data term + TV-like regularizer, linearized ADMM (Moeller et al., 1408.0173) | moderate, iterative | best classical, "robust to noise" per abstract |
| 4 | MRF / graph-cut label smoothing on the discrete index map | expensive at 33 MP | mechanism UNVERIFIED here |
| 5 | Learned GRU refinement at low res + convex upsampling (DDL-SFF) | needs training | 2026 SOTA, domain gap |
| 6 | Monocular prior fusion (Depth Anything V2 as initialization or as a shape regularizer) | needs training | precedent exists (FOSSA), macro domain gap unquantified |

**A specific, cheap, low-risk idea for this project:** use a monocular prior *not* as depth but as an **ordinal/shape regularizer**. Monocular models are unreliable in absolute scale (especially at macro distances they never saw in training) but are good at relative ordering and at surface smoothness. Penalize disagreement in the *gradient* or *rank* of the SFF depth map against the prior's, not in absolute depth. This preserves the metric information that only the focus stack has, while borrowing the prior's spatial regularity. I found **no paper doing this on a macro focus stack** — see §9.

### 4.6 If we could only implement one method here, which and why

**A confidence-weighted, sub-frame-interpolated peak over a ring-difference/DDL focus volume, followed by guided-filter regularization using the merged all-in-focus image as the guide.**

1. It reuses the §2 focus volume and the §3 merge output — zero additional heavy computation, which matters at 60 × 33 MP.
2. The guide image is the *sharpest* estimate of scene structure available, so guided filtering aligns depth discontinuities to real edges — the exact place where DDL-SFF says one-step methods fail.
3. It is deterministic, has no training data and no domain gap, which is decisive given §4.2's 0.8–8.1 m vs millimetres mismatch.
4. Everything more sophisticated (variational, GRU, monocular prior) is a strict *upgrade path* on the same interface, not a rewrite.

### 4.7 What the pluggable interface for this stage must expose

```rust
pub trait DepthEstimator {
    fn estimate(
        &self,
        focus: &FocusVolume,        // §2 output, per-scale, per-plane
        merged: Option<&MergedTile>,// all-in-focus guide, if available
        z: &FocusGeometry,          // per-frame focus distance / magnification
        ctx: &mut GpuCtx,
    ) -> Result<DepthMap, DepthError>;
}

pub struct DepthMap {
    /// Continuous frame index (NOT integer) after sub-frame interpolation.
    pub index: Map<f32>,
    /// Per-pixel confidence, derived from the focus-measure noise floor.
    pub confidence: Map<f32>,
    /// True where the peak was at the stack boundary or below the noise
    /// floor — i.e. depth is unknown, not zero. Must be distinguishable.
    pub unresolved: Map<bool>,
    /// Metric depth, only if FocusGeometry was calibrated.
    pub metric_z: Option<Map<f32>>,
}
```

Required properties:

- **Continuous index, not an integer label.** An integer index map is a lossy quantization that no downstream regularizer can undo.
- **`unresolved` must be a separate channel from low confidence.** "No frame was in focus here" and "several frames were equally in focus here" are different states requiring different handling (§3.5).
- **`FocusGeometry` is an input, not an assumption.** Focus breathing means magnification varies per frame; the same data that lets §1 model the scale change also converts frame index to physical z. Keep them in one struct.
- The trait takes the *whole* focus volume, so plugins implementing global regularizers (variational, MRF, learned) are expressible on the same signature as a trivial argmax.

---

## 5. Noise — the √N question, and the principled fix

**This is the most important section in the report.** The prior project's measured headline defect was that a wavelet-softmax merge made flat regions **2–5× noisier** than the source frames. That is not a tuning bug; it is the mathematically expected behaviour of the merge rule that was chosen.

### 5.1 Verified evidence

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| Hasinoff et al., "Burst photography for high dynamic range and low-light imaging on mobile cameras" (HDR+), ACM TOG, Nov 2016, DOI `10.1145/2980179.2980254` | The original burst align-and-merge system | VERIFIED | metadata only |
| **Monod, Delon, Veit, IPOL 11 (2021) 142–169, arXiv 2110.09354, DOI `10.5201/ipol.2021.336`** | **Complete, reproducible specification of HDR+'s per-frequency Wiener merge and its noise model.** Reference code: `github.com/amonod/hdrplus-python` | VERIFIED | **full text** |
| Wronski et al., arXiv **1905.03277** | Robustness model with noise-corrected Wiener shrinkage; anisotropic kernels | VERIFIED / MEASURED | **full text** |
| Brooks et al., "Unprocessing Images for Learned Raw Denoising", arXiv **1811.11127** | Realistic raw noise synthesis (shot/read parameter sampling) | VERIFIED | abstract + metadata |
| Foi et al., IEEE TIP, Oct 2008, DOI `10.1109/tip.2008.2001399` | Poissonian–Gaussian noise modelling for raw sensor data | VERIFIED | metadata only |
| Mäkitalo & Foi, IEEE TIP, Jan 2011, DOI `10.1109/tip.2010.2056693` | Optimal inverse of the Anscombe transform | VERIFIED | metadata only |
| **RPG-VST**, arXiv **2607.24291** (IEEE SPL 2026) | Robust per-CFA-plane Student-t generalized-Anscombe fitting | VERIFIED / MEASURED | abstract |
| BM3D — Dabov et al., IEEE TIP, Aug 2007, DOI `10.1109/tip.2007.901238`; VBM4D — Maggioni et al., IEEE TIP, Sep 2012, DOI `10.1109/tip.2012.2199324` | Collaborative-filtering single-frame / video denoising baselines | VERIFIED | metadata only |
| Krull, Buchholz, Jug, **Noise2Void**, arXiv **1811.10980**; PN2V arXiv **1906.00651**; fully-unsupervised PN2V arXiv **1911.12291** | Self-supervised denoising with no clean targets | VERIFIED | abstract + metadata |
| Mildenhall et al., KPN, arXiv **1712.02327**; Godard et al., Deep Burst Denoising, arXiv **1712.05790**; NAN arXiv **2204.04668**; DenoiseGS arXiv **2511.22939** | Learned burst denoising lineage | VERIFIED | abstract + metadata |
| Noise2Noise (Lehtinen et al.) | **UNVERIFIED — could not resolve.** `ti:"Noise2Noise"` returned 19 arXiv hits; the original was not among the first 8 examined. **Do not cite.** | UNVERIFIED | — |

### 5.2 Why a focus stack *is* a burst, and what that buys you

For a static macro subject on a tripod, 20–60 frames of the same scene differing only in focus is, in every region where defocus does not attenuate the local band, **exactly a burst**: N independent noise realizations of the same signal. The theoretical gain from averaging is **√N**: for N = 30, that is 5.5× lower noise, ≈ 14.8 dB.

The tension the brief names — "get √N noise reduction from the *overlap* while still selecting the sharpest frame" — dissolves once you stop thinking in pixels and start thinking in **bands**. In a Laplacian/steerable decomposition:

- **Bands where defocus attenuates content** (fine scales, in-focus vs out-of-focus regions): frames genuinely differ → *selection* is required, and averaging would blur.
- **Bands where defocus does not attenuate content** (coarse scales everywhere; all scales in flat/textureless regions): frames are noisy copies of the same signal → *averaging* is required, and selection is pure noise amplification.

A pixel-domain or naively-band-selective merge applies one rule everywhere. That is the bug.

### 5.3 ORIGINAL EXPERIMENT — quantifying the defect

**These numbers are my own numpy simulation, not from any paper. Do not cite them as literature.** Setup: a flat region, so the true detail coefficient is 0; N i.i.d. N(0,1) detail coefficients per site; 400,000 sites. Output std is reported in units where **1.0 = as noisy as a single source frame**.

| N | softmax T=0.1 | softmax T=1 | hardmax (argmax\|c\|) | mean | ideal 1/√N |
|---|---|---|---|---|---|
| 2 | 1.253 | 0.973 | 1.280 | 0.707 | 0.707 |
| 5 | 1.587 | 0.847 | 1.665 | 0.447 | 0.447 |
| 10 | 1.820 | 0.711 | 1.949 | 0.317 | 0.316 |
| 20 | 2.030 | 0.568 | 2.217 | 0.224 | 0.224 |
| 30 | 2.145 | 0.489 | 2.367 | 0.183 | 0.183 |
| 60 | 2.320 | 0.367 | 2.607 | 0.129 | 0.129 |

**This reproduces the prior project's reported 2–5× defect exactly.** `argmax` over N noise-only coefficients yields ~1.9–2.6× single-frame noise at N = 10–60, versus 1/√N for averaging — a swing of roughly **6× to 20× versus ideal**. Note also that a low-temperature softmax is *not* a fix: it behaves like hardmax. Only a temperature large enough to make the weights nearly uniform (T ≳ 1) avoids amplification, and at that point it is just an average with extra steps.

Now the same experiment with **Wiener shrinkage** instead of selection (output std, flat region, σ = 1):

| N | τ=0.5 | τ=1 | τ=2 | τ=4 | τ=8 | τ=16 | τ=32 | ideal 1/√N |
|---|---|---|---|---|---|---|---|---|
| 10 | 0.876 | 0.802 | 0.705 | 0.592 | 0.484 | 0.400 | 0.350 | 0.316 |
| 20 | 0.870 | 0.790 | 0.684 | 0.560 | 0.436 | 0.334 | 0.270 | 0.224 |
| 30 | 0.866 | 0.784 | 0.675 | 0.547 | 0.417 | 0.309 | 0.237 | 0.183 |
| 60 | 0.864 | 0.781 | 0.669 | 0.536 | 0.400 | 0.282 | 0.200 | 0.129 |

**Wiener shrinkage never amplifies** — output std ≤ 1.0 for every τ and N tested — and monotonically approaches 1/√N as τ grows. τ is the safety/aggression dial, and it is bounded on the safe side by construction. This is the structural property the merge rule must have.

### 5.4 The HDR+ Wiener merge, in full (Monod et al. 2110.09354, full text read)

**Noise model.** `σ²(x) = λ_s·x + λ_r` (Poissonian–Gaussian). Parameters obtained three ways: gray-patch regression; the **DNG `NoiseProfile` tag**; or ISO scaling — with `α_ISO = ISO/100`, `λ'_s = α_ISO·λ_s`, `λ'_r = α_ISO²·λ_r` (their Eq. 8). They report that metadata/ISO-derived values gave "more consistent results" than blind estimation. **For a Sony ARW pipeline this is a solved problem: read `NoiseProfile` or calibrate once per ISO.**

**Per-plane processing.** Noise estimation and merging are done **separately per Bayer colour plane, treating both greens independently**, "to avoid potential problems due to the undersampled nature of the red and blue channels".

**Per-tile intensity uses RMS, not mean** (their Eq. 9): a higher-contrast tile gets a higher estimated variance, "which will allow a more aggressive temporal denoising".

**The merge itself** (their Eq. 10–11), computed in the 2D DFT of each tile:

```
T̃₀(ω) = (1/N) · Σ_z [ (1 − A_z(ω))·T_z(ω) + A_z(ω)·T₀(ω) ]
A_z(ω) = |D_z(ω)|² / ( |D_z(ω)|² + c·σ²(ρ(T₀)) )
D_z(ω) = T₀(ω) − T_z(ω)
```

Working per frequency bin is deliberate — verbatim:

> "useful in cases where alignment failure is partial (i.e. some frequencies match well while others don't) as not all the content of the tiles will be discarded."

**The single most important quote in this report, for our purposes:**

> "if T₀ is sharp, and it is still matched to a blurry tile T_z after alignment, the frequency content corresponding to the blurry elements of T_z will be discarded... On the contrary, if we have a blurry T₀, but a sharp T_z, there is also a strong frequency mismatch and we will not merge that content either. In effect, the Wiener filter does not introduce additional blur from other images, but it does not remove blur either."

Read that carefully. HDR+'s merge **already does the right thing on defocus mismatch** — it refuses to average sharp with blurred — but it is *reference-frame-anchored*, so it inherits the reference's sharpness. That is precisely the gap a focus stacker must close: **replace the fixed reference `T₀` with a per-band, per-tile reference chosen by the §2 focus measure**, and HDR+'s merge becomes a focus-stacking merge that also denoises.

Limits: `τ → 0` ⇒ output equals the reference (no denoising); `τ → ∞` ⇒ plain average. Monod et al. also flag HDR+'s `k = n²·(1/4²)·2` scaling as "questionable, because they are trying to scale a single variance value computed in the spatial domain to a per-frequency-bin Wiener filter of the squared difference of two images." **Do not copy that constant; derive it.**

### 5.5 Wronski's robustness model (1905.03277, full text read)

Complementary, and spatial rather than spectral:

- Robustness `R = s·exp(−d²/σ²) − t` (Eq. 5).
- Noise-corrected: `σ = max(σ_ms, σ_md)` and `d = d_ms · d²_ms/(d²_ms + d²_md)` (Eq. 6) — again Wiener shrinkage, now on the *color difference* used to decide whether a frame contributes at all.
- Guide is a half-res RGB image formed from each Bayer quad.
- Motion prior `M = √(M_x² + M_y²)` from the 3×3 local span of alignment vectors (Eq. 7), switching `s` between `s₁` and `s₂` (Eq. 8).
- Final morphological erosion `R̂ = min over 5×5` (Eq. 9) — expands distrust around any suspect pixel.

### 5.6 Where the other denoising families fit

| Family | Role in this pipeline | Why not primary |
|---|---|---|
| **Multi-frame/burst averaging with a Wiener gate** (HDR+, Wronski) | **Primary.** It *is* the merge. | — |
| Anscombe / generalized Anscombe VST (Foi 2008; Mäkitalo & Foi 2011; RPG-VST 2607.24291) | **Variance stabilization before any thresholding**, so a single σ is valid across the tonal range | Not a denoiser itself; it makes the others correct |
| BM3D / VBM4D | Optional single-frame or residual pass on the merged result | Redundant if n_eff is high; expensive at 33 MP |
| KPN / Deep Burst Denoising / NAN / DenoiseGS | Strong learned burst denoisers | Trained on bursts with *constant* sharpness — a focus bracket violates that assumption |
| Noise2Void / PN2V (1811.10980, 1906.00651, 1911.12291) | Self-supervised, no clean targets; PN2V models a real per-pixel noise distribution | Blind-spot networks lose high-frequency fidelity — bad for a tool whose whole point is resolution |
| Unprocessing (1811.11127) | Realistic noise synthesis for training/validation | Tooling, not a denoiser |

Note Araujo et al. (full text) trained with sampled raw noise — `log(λ_shot) ~ U(log 0.0001, log 0.012)`, `log(λ_read)|log(λ_shot) ~ N(2.18·log(λ_shot) + 1.2, σ = 0.26)` — and report qualitatively that their noise-augmented model "recovers the same level of detail as HeliconFocus, but achieves a significant level of noise reduction" on 30 raw iPhone 12 frames at ISO 1000. **Qualitative only — no PSNR is given for that comparison.**

### 5.7 The principled fix, stated plainly

*(This synthesis is my analysis, built on the verified sources above; it is not a claim from any single paper.)*

> **The merge must be band-selective and noise-gated, not pixel-selective.**
>
> Decompose each aligned frame into a Laplacian/steerable pyramid (or work in the DFT of overlapping tiles). For each band, tile and CFA plane, compute the inter-frame difference. Compare it against the **calibrated** Poissonian–Gaussian noise floor for that signal level and ISO.
>
> - Where the difference **exceeds** the noise floor, the frames genuinely differ in focus → select (or strongly weight) using the §2 focus measure.
> - Where the difference is **within** the noise floor, the frames carry no differential information → average all N.
>
> HDR+'s `A_z(ω) = |D|²/(|D|² + c·σ²)` is exactly this gate. The prior project's error was applying a *selection* rule to bands where the frames carry no differential information, i.e. selecting on noise.

Three corollaries that should be treated as design rules:

1. **Never use a temperature-annealed softmax as a "safer argmax".** §5.3 shows T = 0.1 is indistinguishable from hardmax (1.82 vs 1.95 at N = 10). The parameter that makes softmax safe is the one that makes it an average.
2. **`n_eff` is the acceptance test.** In a flat patch, `n_eff` must approach N. Write that as a unit test on synthetic flat-field RAW before writing the merge.
3. **Calibrate, don't estimate.** Use the ARW/DNG `NoiseProfile` or a one-off per-ISO calibration. Monod et al. found metadata-derived parameters "more consistent" than blind estimation, and every gate above is only as good as its σ.

### 5.8 If we could only implement one method here, which and why

**HDR+-style per-frequency Wiener-gated accumulation over all N frames, driven by a calibrated per-ISO, per-CFA-plane Poissonian–Gaussian noise model — with the reference chosen per band and per tile by the focus measure rather than fixed to one frame.**

1. It is the only rule in this survey with a *structural* guarantee against noise amplification (§5.3: ≤ 1.0 for all τ, N).
2. It converges to 1/√N in flat regions — the exact defect the prior project had.
3. Monod et al. verify it already refuses to average sharp with blurred content, so it does not fight the focus-stacking objective; it only needs its reference generalized.
4. It is fully specified in an IPOL paper with reference code, so it is reproducible rather than reverse-engineered.
5. It is one pass over the data, in the CFA domain, and it subsumes denoising, merging and (with §8) demosaicing.

### 5.9 What the pluggable interface for this stage must expose

Noise is not a stage — it is a **calibrated object that every other stage consumes**. That is the architectural point.

```rust
/// Supplied once per stack, from DNG/ARW NoiseProfile or per-ISO calibration.
/// Every stage above takes &NoiseModel. None of them may estimate their own.
pub trait NoiseModel: Send + Sync {
    /// Variance at a given signal level, for a given CFA plane.
    /// Both greens are distinct planes (Monod et al.).
    fn variance(&self, plane: CfaPlane, signal: f32) -> f32;

    /// Variance-stabilizing transform and its optimal inverse
    /// (generalized Anscombe). Optional: a plugin may decline.
    fn vst(&self) -> Option<&dyn VarianceStabilizer>;

    /// Provenance, so the pipeline can warn when it is guessing.
    fn source(&self) -> NoiseSource; // DngNoiseProfile | Calibrated{iso} | IsoScaled | Estimated
}

/// Optional post-merge denoiser, applied to residual noise only.
pub trait Denoiser {
    /// Must declare whether it is safe to run after an averaging merge:
    /// double-denoising is the standard way to destroy fine detail.
    fn expects(&self) -> DenoiseInput; // SingleFrame | MergedWithNEff
    fn denoise(&self, img: &mut MergedTile, report: &MergeReport,
               noise: &NoiseModel, ctx: &mut GpuCtx) -> Result<(), DenoiseError>;
}
```

Required properties:

- **`NoiseModel` is injected, never inferred locally.** If two stages estimate noise independently they will disagree, and every gate in the pipeline silently miscalibrates.
- **Per-CFA-plane, both greens separate.** Directly from Monod et al.
- **`source()` must be exposed** so the UI can say "noise model estimated, results may be suboptimal" rather than silently degrading.
- **`Denoiser` receives `MergeReport`** (hence `n_eff`) so it can back off where the merge already achieved √N reduction. A denoiser that ignores `n_eff` will over-smooth exactly the flat regions the merge just cleaned.

---

## 6. Super-resolution as a side effect of focus bracketing

### 6.1 The negative search result (report this as a finding, not a gap in effort)

Exact queries, all against the arXiv API (`https://export.arxiv.org/api/query?search_query=...`), executed 2026-08-22:

| Query | Results |
|---|---|
| `all:"focal stack" AND all:"super-resolution"` | **0** |
| `all:"multi-frame super-resolution" AND all:"focus"` | **0** |
| `all:"focus stack" AND all:"super-resolution"` | **1** — arXiv 2007.13701, "Deep learning Framework for Mobile Microscopy": mobile-microscopy SR *and*, separately, FuseGAN stacking. **Not** SR derived *from* a stack. |
| `all:"focus bracketing" AND all:"resolution"` | **1** — arXiv 2311.17846 (Araujo et al.), focus stacking, not SR |

**Conclusion: could not confirm any published work that exploits the sub-pixel shifts inherent in a focus bracket for resolution gain.** Per the discipline rules this is not proof of absence — the search was arXiv-only and English-only — but it is a strong signal.

### 6.2 The closest analogue, and why it *doesn't* cover our case

Wronski et al. (1905.03277, full text read) achieve multi-frame SR from a handheld burst, and are explicit that the sub-pixel diversity comes from **hand tremor**. They note that the alternative — deliberate sensor-shift pixel shift, as in the Sony A6000, Pentax K-1, Olympus E-M1 and Panasonic G9 — requires "the use of a tripod or a static scene".

Their forward-looking remark is worth recording because it is unusually candid about the mechanism:

> "depending on handshake to place red, green, and blue samples below each pixel site suggest that perhaps the design of color filter arrays should be reconsidered."

**A tripod-mounted focus bracket appears, at first glance, to have no sub-pixel diversity at all** — which is presumably why nobody has looked. That reasoning is wrong, and that is the opportunity.

### 6.3 The argument that a focus bracket *does* carry sub-pixel diversity

*(My analysis. UNVERIFIED — no source found either supporting or refuting it. It is a hypothesis for the project to test, not a literature claim.)*

1. **Focus breathing is a magnification change** (§1.1, verified in Araujo et al.). A scale change of even 1–3% across the bracket moves a pixel at radius r by `Δr = r·Δs`. At 33 MP (≈ 7008 × 4672, so r up to ≈ 2800 px from centre), a **0.05% incremental** scale change between adjacent frames already moves outer pixels by more than a pixel, and moves *some* radius band by an arbitrary sub-pixel fraction.
2. Because the shift is a smooth function of radius, **across 20–60 frames every pixel site is sampled at many distinct sub-pixel phases** — a richer and more *structured* sampling than random hand tremor, and one whose geometry we already estimate in §1.
3. The Wronski merge (§8) is already a **non-parametric kernel regression onto an arbitrary output lattice**. Making that lattice 2× finer is a change to one parameter, not a new algorithm. The robustness mask (Eq. 5–9) already suppresses frames that don't agree.
4. The catch, and it is a real one: SR gain requires the contributing frames to be **sharp at the target frequency**. Only frames near the local focus peak qualify. So the effective N for super-resolution is not 60 but the width of the focus peak — maybe 3–8 frames — and it is *spatially varying*. Regions with a broad focus peak (low-magnification, small aperture, flat surfaces) get more SR; sharply-peaked regions get less. The centre of the frame, where `Δr ≈ 0`, gets **none** from breathing alone.
5. Practical remedy for the frame-centre dead zone: deliberately add a tiny amount of sensor-shift or rail-induced lateral dither if the hardware allows it, or accept radially-varying SR gain and report it.

### 6.4 If we could only implement one method here, which and why

**Merge onto a 2× finer output lattice using Wronski-style anisotropic kernel regression, with the SR gain gated by the robustness mask and by per-pixel focus-peak width.**

1. It is nearly free: the merge (§3/§5/§8) is already a scattered-sample kernel regression, so the output grid resolution is a parameter.
2. It degrades gracefully. Where sub-pixel diversity or sharp-frame count is insufficient, anisotropic kernel regression falls back to a good upsampler rather than producing artifacts — Wronski's λ₁ parameter explicitly trades SR against denoising.
3. It is honest: `n_eff` from §3.7 and the focus-peak width from §4.7 together give a per-pixel measure of how much SR was actually achieved, which can be surfaced rather than claimed.

**Ship it disabled by default, with a measured report.** Claiming SR without per-pixel evidence is exactly the kind of unmeasured claim the prior project got burned by.

### 6.5 What the pluggable interface for this stage must expose

There should be **no separate super-resolution stage**. SR is a property of the merge, and factoring it out would force a resample-then-merge pipeline that destroys the sub-pixel information SR depends on.

```rust
pub struct OutputLattice {
    pub scale: f32,          // 1.0 = sensor native; 2.0 = 2x SR
    pub offset: Vec2,
}

// Merger::merge gains a lattice parameter; MergeReport gains:
pub struct MergeReport {
    // ... as in §3.7 ...
    /// Number of frames that contributed at a frequency above the source
    /// Nyquist limit. This is the honest per-pixel SR gain metric.
    pub sr_contributing_frames: Map<f32>,
    /// Estimated sub-pixel phase coverage, 0..1. Low = no SR possible here.
    pub phase_coverage: Map<f32>,
}
```

The only hard requirement: **`Merger` must accept an arbitrary output lattice and must sample source frames through the `WarpField` rather than from pre-warped buffers** (§1.8). Any plugin that bakes warps is permanently excluded from SR.

---

## 7. Chromatic aberration, defringing, and diffraction

### 7.1 Verified evidence

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| Trouvé et al., "Passive depth estimation using chromatic aberration and a depth from defocus approach", Applied Optics, 2013-10-09, DOI `10.1364/ao.52.007152` | Depth from **longitudinal** CA via DfD — direct prior art for exploiting rather than correcting LCA | VERIFIED | metadata only |
| Chang & Wetzstein, "Deep Optics for Monocular Depth Estimation and 3D Object Detection", arXiv **1904.08601** | "chromatic aberration from a singlet lens offers significantly improved performance as well. We build a physical prototype and validate that chromatic aberrations improve depth estimation on real-world results." | VERIFIED | abstract only |
| Zia, Zhou, Gao, IEEE TIP 2021, DOI `10.1109/tip.2021.3071682` | CA-based computational imaging | VERIFIED | metadata only |
| arXiv **1802.08805** | Multispectral focal stack from a camera whose chromatic aberration is *deliberately enlarged* — CA used as a spectral-depth encoder | VERIFIED | abstract only |
| **DCA-LUT**, arXiv **2511.12066** | First deep framework specifically for purple-fringing (LCA) removal; Chromatic-Aware Coordinate Transformation + 5D LUT | VERIFIED | abstract only |
| Zhou et al., arXiv **2309.04342** | Ranks aberration-correction priority: **longitudinal CA first**, then lateral CA, spherical, field curvature, coma, astigmatism | VERIFIED | abstract only |
| Wu, Monno, Okutomi, arXiv **2402.18175** | Aberration-aware DfD including focus breathing | VERIFIED | abstract only |
| "Correcting lateral chromatic aberration using orthogonal fringe patterns", Applied Optics 2020, DOI `10.1364/ao.394936` | The only lateral-CA source resolved — and it is **metrology**, not a photographic pipeline | VERIFIED | metadata only |

### 7.2 Negative searches

| Query | Source | Result |
|---|---|---|
| `all:"depth from chromatic aberration"` | arXiv API | **0 results** |

**could not confirm** any arXiv paper under that exact phrase. The concept *is* published off-arXiv (Trouvé et al. 2013, Applied Optics — verified metadata), so this is an arXiv-coverage artifact, not absence of the idea.

I also **could not find** any paper that runs a focus measure **per colour channel across a focus stack** in order to exploit longitudinal CA. Searches covering focus stacking (11 arXiv results), MFIF (49 results) and SFF (7 results) surfaced none. Report as could not confirm.

### 7.3 The two CAs behave completely differently in a focus stack

| | Lateral CA (transverse) | Longitudinal CA (axial) |
|---|---|---|
| Physical effect | R/G/B focus at different *radial positions* — magnification differs per channel | R/G/B focus at different *z* |
| Appearance | Colour fringing that grows with distance from the optical axis, symmetric about focus | Purple/green fringing on out-of-focus edges, **asymmetric** — colour flips sign on either side of focus |
| Behaviour across a focus stack | Essentially constant (a fixed per-channel scale factor) | **Varies with z — this is the exploitable signal** |
| Correction | Per-channel radial scale, estimated once for the stack | Per-channel deblur / desaturation of fringes |
| Interaction with §1 alignment | Can be folded into the alignment warp as a per-channel scale term, for free | Cannot; it is a focus-domain, not a geometry-domain, effect |
| Aberration-correction priority (2309.04342) | second | **first** |

**Key structural observation for this project:** if alignment (§1) already estimates a per-frame similarity transform, then estimating **three** per-channel scale factors instead of one costs almost nothing and corrects lateral CA as a side effect of registration — no separate defringing stage, no extra resample. This should be the design.

### 7.4 Longitudinal CA in a focus stack is a *feature*

Because R, G and B focus at different z, a focus stack captures **three focus sweeps of the same scene, offset along z by the LCA of the lens**. That means:

1. **Per-channel focus peaks give three depth estimates** at every pixel, from one bracket. Their *mean* is a lower-variance depth estimate than any single channel's (three quasi-independent measurements); their *spread* is a direct, per-pixel measurement of the lens's longitudinal CA at that field position and z.
2. **Defringing becomes a by-product.** If you know the per-channel focus peaks, you know which channel is defocused by how much at each pixel — that is exactly the information a defringing algorithm has to *infer* from a single image. Purple/green fringe removal becomes a lookup rather than an estimation.
3. **The all-in-focus merge should select per channel**, not per pixel. Selecting one frame index per pixel for all three channels forces a compromise between three different optimal z values, guaranteeing residual LCA fringing in the output. Selecting per channel eliminates it structurally.
4. This is why the §2.7 interface mandates **per-CFA-plane focus response**, and it is also why §5's per-plane noise model matters: R and B planes are half-sampled and noisier, so their focus peaks are less certain and should be weighted accordingly.

The supporting evidence that LCA genuinely carries depth signal is Trouvé et al. 2013 (verified metadata) and Chang & Wetzstein's verbatim claim (§7.1) that a physical singlet-lens prototype confirmed it. **Applying this inside a focus stack, per Bayer plane, is a design I found no prior work for (§7.2). It is a candidate contribution.**

Caveat to test: a *good* macro lens is apochromatic-ish precisely to minimize LCA. The FE 100mm f/2.8 GM's residual LCA may be small enough that the three per-channel focus peaks are separated by less than one bracket step, in which case the depth-redundancy benefit collapses (though the defringing benefit remains, since sub-frame interpolation §4.4 can resolve sub-step offsets). **Measure the per-channel peak separation on real ARW data before building on it.**

### 7.5 Diffraction

At macro magnifications the *effective* aperture is `N_eff = N·(1 + m)`, so at 1:1 (m = 1) an f/8 setting behaves like f/16, and the Airy disk can exceed the pixel pitch. Consequences that are structural, not cosmetic:

- The per-frame PSF is **not** the ideal defocus disk assumed by most DfD/SFF models; it is a convolution of defocus with diffraction, which **flattens the focus peak** and directly degrades §4's sub-frame interpolation.
- Diffraction is roughly *isotropic and depth-independent*, so unlike defocus it cannot be removed by frame selection. It is a candidate for a deconvolution pass on the merged result — an **opt-in `PostMerge` plugin**, not a default.
- It sets a hard floor on the achievable §6 super-resolution gain: you cannot recover frequencies the optics never transmitted.

I did **not** find a paper in this workstream that models diffraction-plus-defocus PSFs for shape-from-focus at macro magnification. arXiv 2203.02953 (PSF estimation of defocus, abstract only) and 2402.18175 (aberration-aware DfD, abstract only) are the nearest verified sources. **could not confirm.**

### 7.6 If we could only implement one method here, which and why

**Run the focus measure per Bayer colour plane and keep three per-channel focus peaks per pixel; fold lateral CA into the alignment warp as three per-channel scale factors.**

1. It costs essentially nothing — §2.7 already mandates per-plane responses, and §1 already estimates a scale.
2. It corrects lateral CA *without a resample*, because it happens inside the warp that was going to be applied anyway. Every separate defringing stage costs an interpolation and therefore sharpness.
3. It structurally eliminates longitudinal CA from the merged output (per-channel selection, §7.4 point 3) rather than cosmetically desaturating fringes after the fact.
4. It yields a free redundant depth estimate and a per-pixel LCA measurement — a genuine capability no stacker in this survey has.

Explicitly **not** a learned defringer (DCA-LUT, 2511.12066) as the primary: it solves the single-image problem, where the per-channel focus state is unknown. In a focus stack we *measure* it. Using an inference model where a measurement exists is backwards.

### 7.7 What the pluggable interface for this stage must expose

```rust
/// Lens/optics model. Supplied per stack; consumed by alignment, focus
/// measure, depth and merge. Not a pipeline stage of its own.
pub trait OpticsModel: Send + Sync {
    /// Per-channel radial magnification (lateral CA), estimated from the
    /// stack or loaded from a lens profile. Folded into the WarpField.
    fn lateral_ca_scale(&self, plane: CfaPlane) -> f32;

    /// Per-channel focus-distance offset (longitudinal CA), in the same
    /// units as FocusGeometry. May be measured from the stack itself.
    fn longitudinal_ca_offset(&self, plane: CfaPlane, field_radius: f32) -> f32;

    /// Effective aperture including the magnification factor N*(1+m),
    /// so downstream stages can predict the diffraction-limited PSF.
    fn effective_aperture(&self, frame: usize) -> f32;

    fn psf(&self, plane: CfaPlane, defocus: f32, field_radius: f32) -> Psf;
}
```

Required properties:

- **`OpticsModel` is measured from the stack where possible, not just loaded from a profile.** A focus bracket is an unusually good calibration target for LCA — better than a single image — and the estimate should feed back into it.
- **Lateral CA is expressed as a warp modifier, not a separate correction**, so it composes with §1 and costs no extra resample.
- **`psf()` is what makes a deconvolution plugin possible at all**, and it must include diffraction, not just defocus.

---

## 8. Bayer-domain vs demosaiced processing

### 8.1 Verified evidence

| Ref | What it establishes | Label | Read |
|---|---|---|---|
| **Wronski et al., "Handheld Multi-Frame Super-Resolution", arXiv 1905.03277** | Merging raw Bayer frames **directly onto a full RGB output, bypassing demosaicing**, beats both SOTA demosaicing and merge-then-demosaic pipelines | VERIFIED / MEASURED | **full text** |
| Monod, Delon, Veit, arXiv **2110.09354** | HDR+ aligns, estimates noise and merges **per Bayer plane**, both greens separately | VERIFIED | **full text** |
| Araujo et al., arXiv **2311.17846** | Builds a raw-domain focus-stacking network; estimates transforms on RGB, scales them, applies to RGGB | VERIFIED / MEASURED | **full text** |
| Brooks et al., arXiv **1811.11127** | Raw-domain denoising outperforms sRGB-domain denoising because the noise model is simple and known in raw | VERIFIED | abstract + metadata |

Negative search: `abs:"raw domain" AND abs:"alignment" AND abs:"burst"` on the arXiv API → **0 results**.

### 8.2 The load-bearing claim (Wronski et al., full text)

> "Our approach extends existing non-parametric kernel regression to merge Bayer raw images directly onto a full RGB frame, bypassing single-frame demosaicing altogether. We have demonstrated (on both synthetic and real data) that the proposed method achieves better image quality than (a) state of the art demosaicing algorithms, and (b) state of the art burst processing pipelines that first merge raw frames and then demosaic (e.g. Hasinoff et al. [2016])."

**MEASURED, their Table 1.** Synthetic 15-frame bursts from Kodak (25 images) and McMaster (18 images); bivariate Gaussian offsets σ = 2 px; nearest-neighbour resample then Bayer mosaic:

| Method | Kodak PSNR | Kodak SSIM | McM PSNR | McM SSIM | MPix/s |
|---|---|---|---|---|---|
| ADMM | 31.79 | 0.935 | 32.66 | 0.957 | 0.0005 (CPU) |
| VNG | 34.71 | 0.978 | 32.74 | 0.961 | 3.22 (CPU) |
| FlexISP | 35.08 | 0.967 | 35.15 | 0.975 | 3.07 (GPU) |
| DeepJoint | 39.67 | 0.991 | 37.58 | 0.986 | 0.33 (GPU) |
| **Ours** | **42.86** | **0.996** | **41.26** | **0.993** | **1756.9 (GPU)** |

They describe this as "over 3 dB better than the next best one, DeepJoint, on both datasets".

**Caveats, stated honestly:**
- This is a **multi-frame** method compared against mostly **single-frame** demosaicers. That is not apples-to-apples; some of the 3 dB is simply "15 frames beat 1 frame".
- The comparison that actually matters for claim (b) — merge-then-demosaic (Hasinoff) vs merge-into-RGB — is presented **qualitatively (Fig. 14), not in a table**. So "CFA merge beats merge-then-demosaic" is VERIFIED as an author claim with visual evidence, but **not MEASURED**.
- The throughput figure (1756.9 MPix/s on GPU) is the strongest number for us regardless: it is ~3500× the DeepJoint rate and makes 60 × 33 MP tractable.

### 8.3 The mechanism (Wronski, full text)

Merge (their Eq. 1), per output colour channel:

```
C(x,y) = Σ_n Σ_i c_{n,i} · w_{n,i} · R̂_n  /  Σ_n Σ_i w_{n,i} · R̂_n
```

over a 3×3 neighbourhood, gather-style (GPU-friendly — every output pixel reads, nothing scatters).

Kernel (Eq. 2): unnormalized anisotropic Gaussian RBF `w = exp(−½·dᵀΩ⁻¹d)`, with Ω from the eigendecomposition of the **local gradient structure tensor** (Eqs. 3–4). The structure tensor is computed **at half resolution on a luminance image formed by combining each 2×2 Bayer quad**, verbatim "to improve runtime performance and resistance to image noise... and with improved signal-to-noise ratio", then bilinearly upsampled. `λ₁` drives spatial support (the SR-vs-denoise trade-off); `(λ₁−λ₂)/(λ₁+λ₂)` drives anisotropy.

**The anisotropy is the artifact fix** (§3.4): isotropic kernels ⇒ "small misalignments cause heavy zipper artifacts along edges"; `k_stretch = 4, k_shrink = 2` removes them.

### 8.4 Why CFA-domain is right specifically for a *focus* stack

Beyond the general burst arguments, three reasons that are specific to us:

1. **Demosaicing is an interpolation, and interpolation is a low-pass filter.** A focus measure applied to demosaiced data measures the sharpness of the *demosaicer's guess*, not of the sensor data. That systematically biases the focus peak — and the bias varies with local colour and edge orientation, i.e. it is structured, not random.
2. **Demosaicing correlates noise between neighbouring pixels.** The §2.7 noise-floor calibration and the §5 Wiener gate both assume per-pixel independent noise with a known Poissonian–Gaussian variance. That assumption is exactly true in raw and false after demosaicing. Every gate in the pipeline is miscalibrated on demosaiced data.
3. **Longitudinal CA (§7.4) is per channel.** Demosaicing mixes channels. Doing it before the focus measure destroys the per-channel focus information the CA exploitation depends on.

The counter-argument — Araujo et al.'s raw results are *worse* than their RGB results (§3.3, Raw FocusDeep 32.89 vs RGB FocusDeep 38.47 test PSNR) — **does not survive inspection**: their ground truth is HeliconFocus's demosaiced RGB output, so the raw pipeline is scored on reproducing a demosaiced pipeline. Note also that they themselves estimate alignment transforms **on RGB** and then scale them to RGGB, i.e. even the raw pipeline uses a demosaiced guide for registration — which is a pragmatic pattern worth copying (see also Wronski's half-res Bayer-quad guide).

### 8.5 If we could only implement one method here, which and why

**Do everything in the CFA domain, and let the merge produce RGB directly — Wronski-style anisotropic kernel regression from Bayer samples onto the output lattice, with no separate demosaicing stage at all.**

1. It is the only configuration where the noise model (§5) is exactly valid, which is what makes every gate in the pipeline correct rather than approximately correct.
2. It removes a stage instead of adding one — fewer resamples, less low-pass, less memory traffic at 60 × 33 MP.
3. It is measured at 1756.9 MPix/s on a GPU (Table 1), i.e. clearly fast enough for our workload on an RTX 5090.
4. It preserves the per-channel focus information §7 depends on.
5. It composes with §6: the same kernel regression that skips demosaicing also produces super-resolution.

**Use a half-resolution Bayer-quad luminance image as the *guide* for alignment, structure tensors and robustness** — this is what both Wronski (structure tensor, robustness guide) and Araujo (transform estimation) actually do, and it gives you a clean, noise-suppressed, demosaic-free proxy image at a quarter of the cost.

### 8.6 What the pluggable interface for this stage must expose

The correct architectural answer is that **there is no `Demosaic` trait**. Demosaicing is a *capability of a merger*, not a stage. Forcing it into the pipeline as a stage is what makes CFA-domain processing impossible.

```rust
pub enum InputDomain {
    /// Raw CFA samples plus the pattern. The default for this pipeline.
    Cfa { pattern: CfaPattern },
    /// Half-res luminance from 2x2 Bayer quads. Cheap, low-noise, no
    /// interpolation. The standard guide image (Wronski, Araujo).
    BayerQuadLuma,
    /// Half-res RGB from 2x2 Bayer quads. No interpolation either.
    HalfResRgb,
    /// Fully demosaiced. Available, but the pipeline warns that noise
    /// calibration and focus-measure bias guarantees no longer hold.
    FullRgb,
}

pub trait Pipeline {
    /// A merger that declares output_domain() == Rgb from input_domain()
    /// == Cfa causes the demosaic stage to be skipped entirely.
    fn requires_demosaic(&self) -> bool {
        !self.merger().input_domain().is_cfa()
            || self.merger().output_domain() != OutputDomain::Rgb
    }
}
```

Required properties:

- **Every stage declares its `input_domain()`**, and the pipeline inserts the *cheapest sufficient* conversion — never a full demosaic when a Bayer-quad guide suffices.
- **A CFA→RGB merger legally replaces the demosaic stage.** If the type system cannot express that, the architecture has pre-committed to the wrong pipeline.
- **`FullRgb` consumers must be marked**, so the pipeline can report "noise-model guarantees void" rather than silently producing miscalibrated gates.
- The CFA pattern must be carried as data (RGGB/BGGR/GRBG/GBRG, and ideally X-Trans as a future variant), not hardcoded.

---

## 9. Cross-cutting synthesis

### 9.1 One-line recommendation per stage

| # | Stage | Recommended method | Why (one line) |
|---|---|---|---|
| 1 | Alignment | ECC similarity/affine, coarse-to-fine on Bayer-quad luma, **chained frame-to-previous**, + HDR+ tile residual | Focus breathing is a scale change; chaining bounds the sharpness gap; it is what the only real raw focus-bracket paper used |
| 2 | Focus measure | Multi-scale **ring-difference / directional-dilated-Laplacian**, per CFA plane, with a calibrated `noise_floor()` | The only measure with a published measurement showing it stays positive under noise while the Laplacian family *inverts* |
| 3 | Merge | **Band-selective, noise-gated accumulation** (HDR+ Wiener gate) inside a pyramid, with Wronski anisotropic kernels, in CFA | The only rule that is correct in both degenerate regions and provably never amplifies noise |
| 4 | Depth | Confidence-weighted sub-frame peak on the §2 focus volume, guided-filter regularized by the merged image | Free (reuses §2/§3 outputs), deterministic, no domain gap; everything better is an upgrade on the same interface |
| 5 | Noise | The merge **is** the denoiser; `NoiseModel` injected from DNG `NoiseProfile`, per CFA plane | 1/√N comes from averaging where frames don't differ — the prior project selected there instead |
| 6 | Super-resolution | Merge onto a 2× lattice, gated by robustness and focus-peak width; **off by default** | Free parameter on a merge that is already kernel regression; honest per-pixel reporting |
| 7 | CA / diffraction | Per-plane focus peaks (LCA as signal); lateral CA folded into the alignment warp | Costs nothing, removes a resample, and turns an aberration into a measurement |
| 8 | Bayer vs RGB | **CFA throughout; merge outputs RGB directly, no demosaic stage** | The only configuration where the noise model is exactly valid and per-channel focus survives |

### 9.2 The one architectural consequence that matters most

Six of the eight stages above want the same thing: **a calibrated noise model, injected from above, that every stage consumes and none estimates locally.**

- §2 needs it to know whether a focus peak is real (`noise_floor`).
- §3 needs it to decide select-vs-average.
- §4 needs it to weight the sub-frame peak fit.
- §5 *is* it.
- §6 needs it to know when sub-pixel diversity is above the noise.
- §8 is only valid because raw noise is modellable and demosaiced noise is not.

If `NoiseModel` is not a first-class, injected, per-CFA-plane object in the very first version of the architecture, every one of those stages will grow its own private, inconsistent estimate — and the prior project's 2–5× defect is the exact failure mode that produces.

### 9.3 The three biggest open algorithmic risks

| # | Risk | Evidence | Mitigation |
|---|---|---|---|
| **1** | **Every focus-measure noise analysis in the literature is synthetic.** Surh et al.'s Table 1 (the result the entire §2 recommendation rests on) uses synthetic depth-dependent blur and synthetic signal-dependent Gaussian noise on light-field data ≥768×768. **No source measures focus-measure behaviour on real camera RAW at 33 MP.** | Surh CVPR 2017, full text; Pertuz 2013 is closed access and unquotable | Build the noise-vs-focus-measure benchmark on our own ARW data *first*, before choosing the operator. This is a prerequisite, not a nice-to-have. |
| **2** | **All deep MFIF / DfD SOTA is trained far outside our regime.** MFIF: 2–3 images, low resolution, synthetic blur (MFIFB is 105 image *pairs*; Lytro has no ground truth at all). DfD: FOSSA trains at stack size 5 and evaluates at focus distances of 0.8–8.1 m. **Our workload is 20–60 frames at 33 MP over a millimetre-scale depth range at 1:1.** GMFF further reports that hard-selection edge artifacts "worsen as the number of focal planes increases". | Araujo 2311.17846 full text; MFIFB 2005.01116; GMFF 2512.21495 full text; FOSSA 2603.26658 full text | Keep every learned component behind the plugin boundary and off the default path. Prefer deterministic methods whose behaviour is analytically predictable at N = 60. |
| **3** | **Alignment residual silently poisons every downstream stage.** Araujo et al. found residual *sub-pixel local* shifts even after careful global ECC on real focus brackets, and had to add a learned deformable-convolution module. Sub-pixel misalignment looks exactly like a focus difference to a focus measure, and exactly like signal to a Wiener gate. And focus-rail parallax is completely unquantified: `all:"focus rail" OR all:"focus stacking parallax"` → **0 arXiv results**. | Araujo 2311.17846 full text; HDR+ IPOL lists "motion not parallel to the image plane" as a failure mode; negative search recorded | Make `WarpField::confidence()` mandatory (§1.8); make the merge robustness mask (Wronski Eqs. 5–9) non-optional; validate `n_eff` on synthetic flat fields *with deliberately injected sub-pixel error*. |

### 9.4 Genuine gaps in the literature this project could fill

Each of these is a "could not confirm" with the exact query recorded, not a claim of novelty.

| Gap | Search evidence | Why it is tractable here |
|---|---|---|
| **Super-resolution from focus-breathing-induced sub-pixel diversity.** Handheld MFSR relies on hand tremor; a tripod focus bracket is assumed shift-free. But breathing is a *scale* change, so it induces smoothly-varying, radially-increasing sub-pixel resampling across the stack — free, structured sub-pixel diversity that nobody appears to have exploited. | 4 arXiv queries (§6.1), 0 relevant results. Wronski explicitly attributes sub-pixel diversity to handshake and notes the alternative "requires the use of a tripod or a static scene". | The merge is already kernel regression onto an arbitrary lattice (§8.3). Enabling this is a parameter change plus an honest per-pixel gain metric. |
| **Per-channel focus stacking exploiting longitudinal CA.** R/G/B focus at different z, so one bracket is three z-offset focus sweeps: three depth estimates, a per-pixel LCA measurement, and structurally fringe-free output. | `all:"depth from chromatic aberration"` → 0 arXiv results; no per-channel focus-stack paper found across the focus-stacking (11), MFIF (49) and SFF (7) result sets. Trouvé et al. 2013 and Chang & Wetzstein 1904.08601 confirm LCA carries depth signal, but neither does it *in a focus stack*. | §2.7 already mandates per-plane focus responses. The marginal cost is bookkeeping. |
| **Focus-measure noise robustness measured on real high-resolution camera RAW.** Everything published is synthetic (§9.3 risk 1). | Surh 2017 (synthetic light-field); Pertuz 2013 closed access | We have the hardware, the sensor and the workload. This is a publishable benchmark in its own right and we need it internally anyway. |
| **Monocular depth prior as an *ordinal/shape* regularizer for macro SFF**, rather than as a metric initializer. FOSSA initializes from the Depth Anything V2 metric checkpoint at 0.8–8.1 m — meaningless at 1:1 macro — but the prior's *relative* ordering and surface smoothness should still transfer. | FOSSA 2603.26658 (full text) is the only verified precedent, and it is metric-initialization at macroscopic range | Cheap to test: penalize disagreement in depth *gradient/rank*, not absolute depth, against the SFF map. |
| **Diffraction-plus-defocus PSF modelling for SFF at macro magnification** (`N_eff = N(1+m)`), which flattens the focus peak and degrades sub-frame interpolation. | could not confirm; nearest verified sources are 2203.02953 and 2402.18175, abstract only | We know m and N per frame from EXIF; the correction is a per-frame PSF-width prior on the peak fit. |

### 9.5 Negative-search log (exact queries, arXiv API, 2026-08-22)

| Query | Results | Section |
|---|---|---|
| `all:"focus rail" OR all:"focus stacking parallax"` | 0 | §1.5 |
| `all:"ring difference filter"` | 0 (IEEE-only; CVF PDF used instead) | §2.2 |
| `all:"all-in-focus" AND all:"halo"` | 0 | §3.4 |
| `all:"focal stack" AND all:"super-resolution"` | 0 | §6.1 |
| `all:"multi-frame super-resolution" AND all:"focus"` | 0 | §6.1 |
| `all:"focus stack" AND all:"super-resolution"` | 1 (2007.13701, not relevant) | §6.1 |
| `all:"focus bracketing" AND all:"resolution"` | 1 (2311.17846, not SR) | §6.1 |
| `all:"depth from chromatic aberration"` | 0 | §7.2 |
| `abs:"raw domain" AND abs:"alignment" AND abs:"burst"` | 0 | §8.1 |
| `ti:"Noise2Noise"` | 19 hits, original not in first 8 examined ⇒ **unresolved, do not cite** | §5.1 |

All zero-result rows mean **could not confirm**, not "does not exist". All searches were arXiv-only and English-only.

---

## 10. Citation ledger

Every entry below was resolved against a primary source during this workstream. **Read** = full text / abstract / metadata only.

### arXiv (resolved via `export.arxiv.org/api/query`)

| ID | Short name | Read | Section |
|---|---|---|---|
| 2311.17846 | Araujo, Ponce, Mairal — raw focus stacking (FocusDeep) | **full text** | 1, 3, 5, 8 |
| 1905.03277 | Wronski et al. — Handheld Multi-Frame Super-Resolution | **full text** | 1, 3, 5, 6, 8 |
| 2110.09354 | Monod, Delon, Veit — HDR+ (IPOL) | **full text** | 1, 5, 8 |
| 2603.26658 | FOSSA — Zero-Shot Depth from Defocus (ECCV 2026) | **full text** | 4 |
| 2512.21495 | GMFF / StackMFF V4 | **full text** | 3 |
| 2512.10498 | DDL-SFF (IJCV 2026) | abstract + intro | 2, 4 |
| 2003.12039 | RAFT | abstract | 1 |
| 2405.14793 | SEA-RAFT | abstract | 1 |
| 2104.00680 | LoFTR | abstract | 1 |
| 2403.04765 | Efficient LoFTR | abstract | 1 |
| 2306.13643 | LightGlue | abstract | 1 |
| 2402.18175 | Aberration-aware DfD w/ focus breathing (ICASSP 2024) | abstract | 1, 4, 7 |
| 2005.01116 | MFIFB benchmark | abstract | 3 |
| 2603.07120 | IPS — MFIF without real multi-focus data | abstract | 3 |
| 2604.01603 | Minimal focal stack SFF (CVPRW 2026) | abstract | 4 |
| 1408.0173 | Variational Depth from Focus | abstract | 4 |
| 2201.06823 | AWGIF | abstract | 4 |
| 2405.06944 | EDFF — event focal stack DfF | abstract | 4 |
| 2203.02953 | PSF estimation of defocus | abstract | 4, 7 |
| 2406.09414 | Depth Anything V2 | abstract | 4 |
| 1811.11127 | Unprocessing Images for Learned Raw Denoising | abstract | 5, 8 |
| 2607.24291 | RPG-VST (IEEE SPL 2026) | abstract | 5 |
| 1811.10980 | Noise2Void | abstract | 5 |
| 1906.00651 | Probabilistic Noise2Void | abstract | 5 |
| 1911.12291 | Fully-unsupervised PN2V | abstract | 5 |
| 1712.02327 | KPN — burst denoising | abstract | 5 |
| 1712.05790 | Deep Burst Denoising | abstract | 5 |
| 2204.04668 | NAN | abstract | 5 |
| 2511.22939 | DenoiseGS | abstract | 5 |
| 1904.08601 | Deep Optics for Monocular Depth | abstract | 7 |
| 2309.04342 | Aberration-correction priority ranking | abstract | 7 |
| 2511.12066 | DCA-LUT — purple fringing removal | abstract | 7 |
| 1802.08805 | Multispectral focal stack via enlarged CA | abstract | 7 |
| 2007.13701 | Deep learning framework for mobile microscopy | abstract | 6 (negative) |
| 2506.00716 | Fovea Stacking | metadata | 3 (context) |
| 2606.31679 | Lepidoptera macro imaging pipeline | metadata | 3 (context) |

### Non-arXiv (resolved via Crossref / Unpaywall / CVF Open Access)

| DOI | Short name | Read | Section |
|---|---|---|---|
| `10.1109/cvpr.2017.262` | Surh et al., Ring Difference Filter, CVPR 2017 | **full text** (CVF OA) | 2, 4 |
| `10.1109/tpami.2008.113` | Evangelidis & Psarakis, ECC, TPAMI 2008 | metadata | 1 |
| `10.1007/978-3-319-46493-0_29` | Kroeger et al., DIS flow, ECCV 2016 | metadata | 1 |
| `10.1016/j.patcog.2012.11.011` | Pertuz et al. 2013 — **closed access, unquotable** | metadata | 2 |
| `10.1109/tip.2019.2937064` | Jeon et al., IEEE TIP 2020 | metadata | 2 |
| `10.1007/s11263-025-02596-z` | DDL-SFF, IJCV 2026 | metadata | 2, 4 |
| `10.1109/34.308479` | Nayar & Nakagawa, SML, TPAMI 1994 | metadata | 2 |
| `10.1109/34.368191` | Subbarao & Choi, TPAMI 1995 | metadata | 2 |
| `10.1109/icpr.2000.903548` | Pech-Pacheco et al., variance-of-Laplacian, ICPR 2000 | metadata | 2 |
| `10.2139/ssrn.4436889` | Ashfaq & Mahmood, SSRN 2023 | metadata | 2 |
| `10.1109/tcom.1983.1095851` | Burt & Adelson, Laplacian pyramid, 1983 | metadata | 3 |
| `10.1109/iccv.1993.378222` | Burt & Kolczynski, ICCV 1993 | metadata | 3 |
| `10.1109/pg.2007.17` | Mertens et al., Exposure Fusion, PG'07 | metadata | 3 |
| `10.1109/tip.2013.2244222` | Li, Kang, Hu, guided-filter fusion, TIP 2013 | metadata | 3 |
| `10.1145/1201775.882269` | Pérez et al., Poisson image editing, 2003 | metadata | 3 |
| `10.1016/j.inffus.2020.06.013` | Liu et al., MFIF survey, Information Fusion 2020 | metadata | 3 |
| `10.1109/TIP.2015.2479469` | Moeller et al., Variational DfF, TIP 2015 | metadata | 4 |
| `10.1145/2980179.2980254` | Hasinoff et al., HDR+, TOG 2016 | metadata | 5 |
| `10.5201/ipol.2021.336` | Monod et al., IPOL 2021 | **full text** | 5 |
| `10.1109/tip.2008.2001399` | Foi et al., Poissonian–Gaussian noise, TIP 2008 | metadata | 5 |
| `10.1109/tip.2010.2056693` | Mäkitalo & Foi, optimal inverse Anscombe, TIP 2011 | metadata | 5 |
| `10.1109/tip.2007.901238` | Dabov et al., BM3D, TIP 2007 | metadata | 5 |
| `10.1109/tip.2012.2199324` | Maggioni et al., VBM4D, TIP 2012 | metadata | 5 |
| `10.1364/ao.52.007152` | Trouvé et al., depth from CA, Applied Optics 2013 | metadata | 7 |
| `10.1109/tip.2021.3071682` | Zia, Zhou, Gao, TIP 2021 | metadata | 7 |
| `10.1364/ao.394936` | Lateral CA correction via fringe patterns, Applied Optics 2020 | metadata | 7 |

### Not literature

| Item | Nature |
|---|---|
| §5.3 merge-rule noise tables (softmax/hardmax/mean; Wiener τ sweep) | **My own numpy simulation** (`noisesim.py`, colocated). 400,000 sites, i.i.d. N(0,1). **Not from any paper — never cite as such.** |
| §5.7 band-selective merge formulation | My synthesis over Surh 2017 + Monod 2021 + Wronski 2019. Presented as analysis, not as a published result. |
| §6.3 focus-breathing sub-pixel diversity argument | My hypothesis. **UNVERIFIED** — no supporting or refuting source found. |
| §7.4 per-channel focus stacking for LCA | My proposal, built on verified evidence that LCA carries depth signal. No prior work found doing it in a focus stack. |

