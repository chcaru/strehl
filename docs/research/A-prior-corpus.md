# A — Prior Corpus Mining: `C:\dev\macro` (patched fork of PetteriAimonen/focus-stack)

**Scope.** Read-only extraction from a ~1.2 MB markdown corpus (AGENTS.md 193 KB, 35 `research/*.md`, 4 top-level PHASE reports, ~40 Python probes + JSON outputs) plus selective reads of the C++ source. Nothing in `C:\dev\macro` was modified.

**Evidence labels used throughout:**

| Label | Meaning |
|---|---|
| **MEASURED** | A number produced by running code against real or synthetic data, with the run recorded. |
| **ARGUED** | A conclusion reasoned from cited literature or from other measurements, not directly measured. |
| **ASSERTED** | Stated without evidence or derivation. |
| **UNVERIFIED** | Claimed as measured, but the run/artifact could not be located. |

**Reader's warning.** This corpus is a single-developer agentic log. It contains (a) genuinely excellent probe work with real numbers, (b) literature summaries with at least three **fabricated citations** that the corpus itself later caught, and (c) a pervasive baseline-drift problem where a measured win became a measured regression without the algorithm changing. Sections 2–4 are the load-bearing content. Sections 7 is what to throw away.

---

## 1. Map of the corpus

### 1.1 Top-level documents

| Document | Question asked | Conclusion | Evidence class |
|---|---|---|---|
| `AGENTS.md` (193 KB) | Running project log: pipeline anatomy, per-phase changelog, tuned flags, known caveats | The single densest source. Lines 1003–3198 are an undifferentiated changelog containing most of the corpus's real measurements. | **MEASURED** (changelog), **ASSERTED** (design rationale) |
| `PHASE8_RESEARCH.md` (66 KB) | Why is the stacked output noisier than the sources? | Wavelet softmax merge is a max-over-frames selector → amplifies noise. §1.1 numbers are identical to `empirical_findings.md §2b`. | **MEASURED** |
| `PHASE9_10_DELIVERABLE.md` (31 KB) | Robust depth fitting, temporal FM filtering, confidence channels, NLM | Mixed: 9.8 confidence channel is the cheap win; 9.3 IRLS backfires at severe spikes; 9.4 costs 17 GB. | **MEASURED** |
| `PHASE11_RESEARCH.md` (58 KB) | Broad forward-looking survey (raw sensor, algorithms, deep learning, novel, colour, performance) | Optimistic. Multiple headline claims later **falsified by measurement** (N2N, PDAF, per-channel WAVS). | **ARGUED / ASSERTED** |
| `PHASE12_RESEARCH.md` (77 KB) | Follow-up survey + literature audit | Contains the corpus's own catch of **fabricated citations**. Contains a wrong pixel pitch (6.0 µm). | **ARGUED**, self-correcting |
| `PHASE12_11_ARW_VS_TIFF_SHARPNESS.md` | Is the RAW path softer than a Lightroom TIFF export? | Yes, 30–44% softer. Root cause: LibRaw DHT is a pure interpolator; Lightroom adds proprietary sharpening. | **MEASURED** |
| `PHASE12_12_*` | Demosaic algorithm survey | Predicted RCD +20–25%. Wrong pixel pitch (3.76 µm). | **ARGUED** |
| `PHASE12_15_*` | RCD implementation result | **Measured +1.30% / +2.26%**, not +20–25%. Architecture caused the failure. | **MEASURED** |
| `research_focus_measures.md` | Survey of focus-measure operators | Standard survey (SML, Tenengrad, Helmli-Scherer, ISTD, MDDL, WAVS). | **ARGUED** |

### 1.2 `research/` — thread documents (Phase 11 survey threads)

| Document | Question | Conclusion | Evidence class |
|---|---|---|---|
| `thread_A_sensor_bayer.md` | Sensor/Bayer-domain opportunities | Bayer-domain processing is a quality win; PDAF mask is promising | **ARGUED**; PDAF claim later falsified |
| `thread_B_alignment.md` | Alignment state of the art | ECC + dense flow adequate; sub-pixel SR possible | **ARGUED** |
| `thread_C_focus_depth.md` | Focus measures & depth estimation | Multi-operator fusion + confidence channels | **ARGUED** |
| `thread_D_merging_PARTIAL.md` | Merge strategies | Softmax wavelet is noise-amplifying; SNR-weighted merge proposed | **ARGUED** (proposal), builds on MEASURED §1.1 |
| `thread_E_color_dng.md` | Colour pipeline & DNG output | Tone-curve fit beats DCP; DNG output written but never validated | **MEASURED** (ΔE), **UNVERIFIED** (DNG) |
| `thread_F_artifacts_denoise.md` | Halos, artifacts, denoise | Denoise placement is the crux | **ARGUED** |
| `thread_G_novel.md` | Novel/speculative approaches | Depth-from-CA, phase retrieval, plenoptic | **ASSERTED** |
| `thread_H_lens_optics.md` | Lens optical model | Breathing, CA, vignetting characterisation; uses 5.1 µm pitch | **MEASURED** (CA), **ASSERTED** (pitch) |
| `phase11_thread_A_raw_sensor.md` | RAW/sensor deep dive | Bayer-native pipeline recommended | **ARGUED** |
| `phase11_thread_B_algorithms.md` | Algorithm survey | Broad | **ARGUED** |
| `phase11_thread_C_deeplearning.md` | Deep learning options | "N2N is the single biggest denoise win, 2–3× σ reduction" | **ASSERTED** — later **falsified** |
| `phase11_thread_D_novel.md` | Novel approaches | "per-channel WAVS gives ~0.13 → ~0.05 frame depth precision" | **ASSERTED** — later **falsified** |
| `phase11_thread_E_color_dng.md` | Colour/DNG follow-up | Adobe Color not extractable | **MEASURED** (negative) |
| `phase11_thread_F_performance.md` | Performance opportunities | GPU is idle; CUDA/contrib would help | **ARGUED**, key number ASSERTED |

### 1.3 `research/` — PROBE documents (code that actually ran)

These are the corpus's genuine evidence base.

| Document | Question | Result | Evidence class |
|---|---|---|---|
| `PROBE2_NOISE_AIC.md` | Which noise model fits A7C II ARW? | Foi-Mäkitalo `Var = a·I + b` wins by AIC (ΔAIC −37.8 G). Shipped profile is 17–20× too low. | **MEASURED** |
| `PROBE3_WRONSKI_SUBPIXEL.md` | Is there enough sub-pixel jitter for burst SR? | **No.** 0.075 px vs 0.3 px gate. | **MEASURED** |
| `PROBE5_DEPTHANYTHING_V2.md` | Does DA2 correlate with the pipeline depthmap? | Yes: Pearson 0.510/0.451/**0.607** vs 0.30 gate. | **MEASURED** |
| `PROBE7_LEE_TAI.md` | Is Lee & Tai 2016 reusable? | No public code; bibliography entry had wrong author initial *and* wrong title. | **MEASURED** (negative) |
| `PROBE8_FOCUSPOSITION2.md` | Can focus position be read from ARW? | Yes: `FocusPosition2` 56→57, ~3.1 mm/servo step. | **MEASURED** |
| `PROBE10_PDAF_MASK.md` | Can PDAF pixels be detected from ARW? | **0 candidate pixels** across 5 frames. Dead. | **MEASURED** (decisive negative) |
| `PROBE_DEPTH_FROM_CA.md` | Can longitudinal CA give depth? | Signal exists and is sign-correct on TIFF, but only +4.7% substrate σ; ARW path wrong-signed. | **MEASURED** |
| `PROBE_DUALFOCUS_PICK3.md` | Does DualFocus (NeurIPS 2025) joint AIF+depth work? | AIF term destroys edges (−85% Sobel); **depth term is a real −57.2% win**. | **MEASURED** |
| `PROBE_MDDL_CHANNEL_J.md` | Is MDDL a useful confidence channel? | No: Pearson 0.926 with ISTD, disjoint mass 0.14%. | **MEASURED** (negative) |
| `PROBE_N2N_PICK4.md` | Does Noise2Noise work on focus brackets? | **No, wrong direction at every pair distance.** Synthetic control proves the network is fine and the *pairs* are invalid. | **MEASURED** (decisive negative, with control) |
| `FIRMWARE_RECON.md` | Can Sony firmware be reverse-engineered for optical LUTs? | **Blocked.** FDAT entropy 7.9998/8.0; all 9 known crypters fail. | **MEASURED** (decisive negative) |
| `CODE_REVIEW_DA2_GUARDRAIL.md` | Is the DA2 sidecar safe? | HIGH bug: stale cache on sidecar failure. | **MEASURED** (code review) |

### 1.4 `research/` — analysis documents

| Document | Question | Conclusion | Evidence class |
|---|---|---|---|
| `empirical_findings.md` | Is the merge adding noise? | Yes, 2–5× source cross-frame σ; 11–22× off √N floor. | **MEASURED** |
| `NLM_MULTI_OBSOLESCENCE.md` | Does NLM-Multi still help after Phase 12.5? | **No — it inverted.** 1.38× win became +35% to +48% regression. | **MEASURED** (the most important methodological document in the corpus) |
| `PER_FRAME_DENOISE_OPPORTUNITY.md` (58 KB) | Where should denoise live? | Before merge — but that destroys the flat-detector's inputs. | **ARGUED** on MEASURED base |
| `PHASE10_DESIGN.md` (51 KB) | Design for phase 10 | §9.5 documents the denoise-placement bind. | **ARGUED** |
| `PHASE12_9_ANSCOMBE_VST_DESIGN.md` | Should the pipeline use a variance-stabilising transform? | Design doc; implementation measured **−65% Sobel**. | **ARGUED** (design), **MEASURED** (outcome) |
| `PHASE12_1_CODE_REVIEW.md`, `PHASE_12_2B_LITE_FINDINGS.md`, `PHASE12_FRESHNESS_SCAN.md` | Code/feature audits | 12.2b variational Jacobi: 12.46% vs 30% gate. | **MEASURED** |
| `PHASE12_LIBRAW022.md` | LibRaw 0.22.1 capabilities | Exposes `makernotes.sony.FocusPosition`. | **MEASURED** |

---

## 2. The measured facts

Every number below was produced by running something. Cite = file + section.

### 2.1 Sensor characterisation — Sony A7C II

| Quantity | Value | Source | Class |
|---|---|---|---|
| Black level | 512 DN, all channels | `PROBE2_NOISE_AIC.md`; AGENTS.md loadraw | MEASURED |
| White level | 16383 (14-bit) | same | MEASURED |
| LibRaw `linear_max` | (15360, 15360, 15360, 15360) | `PROBE2_NOISE_AIC.md` | MEASURED |
| Active area | **4672×7008** (AGENTS.md) vs **4688×7028** (rawpy probe) — *unresolved*, probe emits a WARNING | AGENTS.md; `probe_*` output | MEASURED, **conflicting** |
| Full read-out | 5120×7168 | AGENTS.md | MEASURED |
| CFA | RGGB | AGENTS.md | MEASURED |
| Pixel pitch | **≈5.12 µm** (35.9 mm / 7008 px, my own derivation). Corpus states 3.76 / 4.7 / 5.1 / 6.0 µm in four different places. | see §7.3 | DERIVED; corpus values ASSERTED |
| Best noise model | Foi-Mäkitalo `Var = a·I + b` (M3), AIC-best over 12 ARW frames | `PROBE2_NOISE_AIC.md` | MEASURED |
| ΔAIC vs next model | −37.8 (G, decisive), −6.3 (B) | `PROBE2_NOISE_AIC.md` | MEASURED |
| Fitted `a` (ARW domain) | G 1.84e-5, R 1.67e-5, B 1.45e-5 | `PROBE2_NOISE_AIC.md` | MEASURED |
| Fitted `b` (ARW domain) | ≈1.7e-6 (G) | `PROBE2_NOISE_AIC.md` | MEASURED |
| Shipped `presets/noise_profile.json` `a` | ≈1e-6 → **17–20× too low** (fit ran on Lightroom-denoised TIFFs, Color NR=25) | `PROBE2_NOISE_AIC.md` | MEASURED |
| Domain-mismatch penalty | Swapping ARW `a` into the rendered-Rec.2020 predictor over-predicts σ by **2.3×** (0.00295 predicted vs 0.00126 observed); engagement 86.0%→91.7%; visible regression | AGENTS.md Phase 12 noise-profile section | MEASURED |
| PDAF anomaly pixels (5-frame intersection) | **0** | `PROBE10_PDAF_MASK.md` | MEASURED |
| Per-frame green anomaly density | 0.022–0.024% (= noise floor); 0 rows above mean+3σ | `PROBE10_PDAF_MASK.md` | MEASURED |
| PDAF probe cost | 185.6 s | `PROBE10_PDAF_MASK.md` | MEASURED |
| `FocusPosition2` across DSC00024–28 | 56, 56, 56, 57, 57 | `PROBE8_FOCUSPOSITION2.md` | MEASURED |
| `FocusDistance2` | 0.2707 m → 0.2738 m ⇒ **≈3.1 mm per servo step** | `PROBE8_FOCUSPOSITION2.md` | MEASURED |
| FocusPosition range / sentinel | 0–~1023; LibRaw sentinel 0xFFFF | `PROBE8_FOCUSPOSITION2.md` | MEASURED |
| Sony MakerNote tags in ARW vs fork's DNG | 112 tags / 1639 lines → **0 tags / 63 lines** | `thread_E_color_dng.md` | MEASURED |

### 2.2 Noise & merge behaviour — the central result

Source: `PHASE8_RESEARCH.md §1.1` ≡ `empirical_findings.md §2b` (numbers identical in both).

| ROI | Output σ(G) | Source cross-frame σ(G) | Ratio | Off √33 floor |
|---|---|---|---|---|
| deep_shadow | 0.00055 | 0.00012 | **4.6×** | ~22× |
| mid_tone | 0.00206 | 0.00046 | **4.5×** | ~10× |
| highlight | 0.00213 | 0.00091 | **2.3×** | ~5× |

| Comparison | Value | Class |
|---|---|---|
| Output spatial σ vs **a single source frame** — highlight | **1.82×** worse | MEASURED |
| — midtone | 1.21× worse | MEASURED |
| — deep shadow | 1.43× worse | MEASURED |

Mechanism (MEASURED + code-confirmed): per-pixel, per-subband `max|c|²` selection in `task_merge.cc:246-280` is a max-over-frames order statistic, which is a *noise selector*. **INTRINSIC to the algorithm.**

**Phase 8.2 response** (flat-region cross-frame mean in compose + wavelet mean fallback), AGENTS.md `task_compose` section:

| ROI | σ before | σ after | Δ |
|---|---|---|---|
| deep shadow | 0.00067 | 0.00058 | −13% |
| mid-tone | 0.00361 | 0.00286 | −21% |
| highlight | 0.00426 | 0.00193 | **−55%** |

| Ancillary | Value | Class |
|---|---|---|
| Pixel engagement at α=2.0 | ~66% | MEASURED |
| Edge RMS\|Δ\| on top-1% gradient pixels | ≈0.0007 | MEASURED |
| Cost | ~1 s, ~1.3 GB | MEASURED |
| Predicted gain | √33 ≈ 5.7× | **ARGUED — never achieved** |
| Plain cross-frame mean, measured at N=5 | **1.10×** (vs theoretical √5 = 2.24×) | MEASURED, `PHASE9_10_DELIVERABLE.md §10.1` |

The 1.10×-vs-2.24× gap is the corpus's most under-appreciated result: **focus-bracket frames have correlated noise, so naive frame averaging under-delivers by ~2×.**

### 2.3 The baseline-inversion result (methodologically the most important)

`NLM_MULTI_OBSOLESCENCE.md`:

| Measurement | Flat ROI σ | Verdict |
|---|---|---|
| Phase 10.1 NLM-Multi, at ship time | 0.00527 → 0.00382 = **1.38× reduction**, edges −2.11% | Shipped as a win |
| Same feature after Phase 12.5 made the depthmap chain always-on (chain **on**) | 226 → **334 codes** = **+48% worse** | Regression |
| Same feature, chain **off** | 265 → **358 codes** = **+35% worse** | Regression |

Mechanism (ARGUED on MEASURED base): denoising *after* an already-applied 33-frame arithmetic mean adds patch-correlated noise, compounded by uint8 quantisation. **Every quality claim in this corpus is baseline-relative and can invert.**

### 2.4 Alignment & sub-pixel

| Quantity | Value | Source | Class |
|---|---|---|---|
| Wronski burst-SR gate | ≥0.3 px std-dev of sub-pixel shifts | `PROBE3_WRONSKI_SUBPIXEL.md §2.1` | literature gate |
| Measured shift σ, 3-frame near-burst window | **0.075 px** | `PROBE3_WRONSKI_SUBPIXEL.md §2.2` | MEASURED |
| Wider windows | 0.137 / 0.171 / 0.194 / 0.209 px | same | MEASURED |
| Relaxed all-33-frame filtered estimate | 0.273 px (still below gate) | same §2.3 | MEASURED |
| Naive unfiltered estimate | 0.42 px — **artifact**: defocus shifts correlation peaks monotonically with \|k−refidx\| | same §2.3 | MEASURED, self-diagnosed |
| ECC score, all 32 non-ref frames | 0.9999–1.0000 | `PROBE3_WRONSKI_SUBPIXEL.md` | MEASURED |
| Dense-flow median residual | 0.05–0.09 px | same | MEASURED |

### 2.5 Deep learning

**Noise2Noise on the real bracket** (`PROBE_N2N_PICK4.md`, RTX 5090):

| Pair distance d | Flat σ vs raw frame | Edge Sobel |
|---|---|---|
| 1 | **+4.6%** | −1.1% |
| 3 | **+18.1%** | −6.0% |
| 8 | **+9.2%** | — |
| 16 | **+15.3%** | — |

| Diagnostic | Value | Class |
|---|---|---|
| Val-loss floor, real bracket | ~6–10e-6 (RMS ≈0.003) | MEASURED |
| True cross-frame noise variance | 0.000208² ≈ **4.3e-8** | MEASURED |
| ⇒ loss is dominated by defocus-operator differences, not noise | ratio ~150–230× | MEASURED |
| Same net, synthetic σ=0.02 noise | **−84% flat σ**, val_loss = σ² exactly | MEASURED (control) |
| Test-bracket caveat | ISO 100 + LR Color NR=25; cross/spatial σ ratio = **19.88%**, i.e. only ~20% of spatial σ was removable | MEASURED |

**DepthAnything V2** (`PROBE5_DEPTHANYTHING_V2.md` + AGENTS.md:2133, :2185):

| Quantity | Value | Class |
|---|---|---|
| Pearson vs pipeline depthmap — whole / high-texture / low-texture | 0.510 / 0.451 / **0.607** (gate 0.30) | MEASURED |
| Spearman — whole / low-texture | 0.442 / 0.577 | MEASURED |
| Model size / forward time | 24.8 M params / 0.27 s (accidentally **CPU** — pip pulled a CPU-only torch wheel) | MEASURED |
| Downstream: smooth-region depth std @ sigma=0.05 | 112.7 → 99.1 = **+12.1%** | MEASURED (AGENTS.md:2133) |
| @ sigma=0.15 / 0.30 | +9.1% / +6.4% | MEASURED (AGENTS.md:2185) |
| Edge mean\|Δ\| | 0.303% of depth range | MEASURED |
| Cache size | 1.6 MB `.f32.bin` | MEASURED |

### 2.6 Depth, focus measures, confidence

| Feature | Result | Cost | Source | Class |
|---|---|---|---|---|
| Phase 9.8 Helmli-Scherer confidence channel | **19.7× smooth/edge discrimination** (66.6 vs 3.4 codes) | +2.6 s | `PHASE9_10_DELIVERABLE.md` | MEASURED |
| Phase 9.3 IRLS robust Guo | 1.36× bias reduction at mild 1.1× spike; **amplifies bias 0.80× (1261→1579 codes) at severe 1.5× spike** | +21 s, +4.2 GB | `PHASE9_10_DELIVERABLE.md` | MEASURED |
| Phase 9.4 temporal FM median5 | **4.2× depth-bias reduction** (1539→366 codes) on synthetic spikes | +20 s, **~17 GB transient RAM** | `PHASE9_10_DELIVERABLE.md` | MEASURED |
| Phase 12.2b variational Jacobi depthmap | 12.46% flat-σ drop vs a **30% gate** → RED; edge retention 136% | — | `PHASE_12_2B_LITE_FINDINGS.md` | MEASURED |
| — mechanism | Jacobi propagates 1 px/iter; 1000 iters ≈ 16 px diffusion radius on a 256-px ROI | | same | MEASURED/ARGUED |
| DualFocus, global run | Edge Sobel **−85.0%** (−77.8% to −87.5% over an 8-config sweep); flat σ only −20.5% | — | `PROBE_DUALFOCUS_PICK3.md` | MEASURED |
| DualFocus, mask-restricted hybrid | Depth σ **−57.2%** (827→354 codes) ✅; AIF flat σ −12.7% (gate 30%) ✗; edge −5.7% | — | same | MEASURED |
| MDDL as confidence channel | Pearson(MDDL, ISTD) = **0.926**; EDGE/SMOOTH ratio 1.4× vs Helmli-Scherer's 2.9×; disjoint mass 0.14% | — | `PROBE_MDDL_CHANNEL_J.md` | MEASURED |

### 2.7 Optics, colour, demosaic, sharpness

| Quantity | Value | Source | Class |
|---|---|---|---|
| Lateral CA correction (Phase 6.2) | corner \|R−G\| **2.0 px → 0.3 px** | AGENTS.md Phase 6.2 | MEASURED |
| CA coefficients (hardcoded, rig-specific) | ca_R_a=−1.515e−3, ca_R_b=+1.034e−3, ca_B_a=−4.500e−4, ca_B_b=+8.697e−4 | `task_loadraw.hh:99-118` | MEASURED |
| Colour ΔE76 vs LR export | 9.4 → **3.0** with a 5-anchor PCHIP tone curve (marker bracket only) | AGENTS.md Phase 6.1 | MEASURED |
| DCP (Adobe Standard) | **Worse** (~5 ΔE on saturated red) | AGENTS.md Phase 6.1 | MEASURED |
| Adobe Color profile | Compiled into the LR binary, not extractable | `phase11_thread_E_color_dng.md` | MEASURED (negative) |
| ARW path vs LR-export TIFF sharpness | Sobel_mean ratio **0.703**, Sobel_top5% **0.638**, Laplacian variance **0.559**; substrate_TL flat region 0.420 / 0.398 | `PHASE12_11_ARW_VS_TIFF_SHARPNESS.md` | MEASURED |
| TIFF→TIFF regression control | ratio **1.000** (no pipeline regression — the deficit is demosaic) | same | MEASURED (control) |
| Root cause | LibRaw DHT is a pure interpolator, no implicit edge enhancement; Lightroom's demosaic adds proprietary sharpening | same | ARGUED |
| RCD demosaic — predicted | +20–25% | `PHASE12_12` | ARGUED (literature) |
| RCD demosaic — **measured** | **+1.30%** (marker) / **+2.26%** (keep-micro) | `PHASE12_15` | MEASURED |
| — failure cause | "Approach B" synthesises Bayer from bilinear because `dcraw_process()` calls `raw2image_ex(1)`, overwriting any pre-filled `imgdata.image` | `PHASE12_15` | MEASURED (code) |
| Post-stack Wiener deconvolution (12.14) | **+25.4% Sobel top-5%** on marker (0.115→0.144); **+105.4%** on coffee-bean (0.0369→0.0759) | AGENTS.md:2621 area | MEASURED |
| — flat-ROI σ cost | **+6.8%** | same | MEASURED |
| — edge width | 13.10 → 12.49 px | same | MEASURED |
| — PSF / cost | Airy(r=2.1 px) ⊗ Gaussian(σ=0.7 px), 25×25; 3–5 s CPU | same | MEASURED |
| Anscombe VST (12.9) | Sobel mean 0.253 → 0.088 = **−65%** with the shipped `preset:iso_50` profile | AGENTS.md Phase 12.9 | MEASURED |
| — mechanism | with a≈1e-6 the stabilised range collapses to span ~1.15, so a constant `h` over-smooths everywhere | same | ARGUED |
| — round-trip RMS after bug fix | ~5e-7 (spurious `/a` divisor removed) | same | MEASURED |
| Phase 13 focus-aware flat AND-mask | substrate Sobel **+18.83%**, Lap-var **+40.1%**, σ cost only **+0.5%**; carves 72.9% of the Phase 8.2 flat mask | AGENTS.md Phase 13 | MEASURED |
| — cost | ~0.2% wall time, +128 MB | same | MEASURED |
| Compound RCD + Phase13 + gentle Wiener, 53-frame coffee-bean | **+22.7% Sobel at +23% Lap-var** | AGENTS.md Phase 13 | MEASURED |
| Vignetting / distortion (this rig) | <0.05 EV / <0.05% | AGENTS.md Phase 6.2 | MEASURED once, then re-asserted second-hand |

### 2.8 Depth-from-chromatic-aberration

`PROBE_DEPTH_FROM_CA.md`:

| Quantity | TIFF path | ARW path | Class |
|---|---|---|---|
| d_R − d_G | **+0.32 frames** (sign-correct) | **−0.51 frames** (wrong-signed) | MEASURED |
| d_B − d_G | **−0.37 frames** (sign-correct) | — | MEASURED |
| \|d_R − d_B\| at top-10% FM | 0.95 frames | — | MEASURED |
| Edge/flat ratio | **37.2×** | — | MEASURED |
| Gate C: substrate σ improvement | **+4.7%** (fails gate) | — | MEASURED |
| Edge sub-pixel dispersion | **worsens** 0.043 → 0.072 frames | — | MEASURED |
| Substrate σ | 3.87 frames | 9.03 frames | MEASURED |

**Counter-intuitive MEASURED finding:** Lightroom's denoise is an *enabler* of the CA signal, not an obstacle — the rawpy AHD path without denoise is noise-dominated and inverts the sign.

### 2.9 Firmware reverse-engineering (decisive negative)

`FIRMWARE_RECON.md`:

| Quantity | Value | Class |
|---|---|---|
| `BODYDATA.DAT` size | 1,139,929,560 bytes | MEASURED |
| FDAT entropy across 1,088 × 1 MiB windows | min **7.9985**, mean **7.9998** (max possible 8.0) | MEASURED |
| 64-KiB windows below 7.95 entropy | **0 / 17,394** | MEASURED |
| `UDTRFIRM` magic hits | **0** | MEASURED |
| Known fwtool crypters that succeed | **0 / 9** (all fail at the first 1024-byte block checksum) | MEASURED |
| Outer UFU container | **Parseable**: 17 USB descriptors, DEND CRC32 0xD191286B verified | MEASURED |
| Key location | `libupdatertalk.so` on the running camera | ARGUED |

### 2.10 Performance

AGENTS.md Performance table + per-phase timings. 33 frames × 32 MP unless noted.

| Configuration | Wall time | Class |
|---|---|---|
| Bundled v1.5, 8-bit | ~81 s | MEASURED |
| Patched 16-bit sRGB + OpenCL | ~88 s | MEASURED |
| ARW direct | ~75–86 s | MEASURED |
| 105 frames, cold | ~147 s | MEASURED |
| Hot cache | ~28 s | MEASURED |
| After feature accretion (default flags, ~Phase 12) | ~175 s | MEASURED |
| By Phase 12.15 | **426–456 s** | MEASURED |
| Peak RAM, 33×32 MP | ~6 GB baseline; **~23 GB** with all features; ~80 GB extrapolated at 105 frames | MEASURED / extrapolated |

Per-feature marginal cost (MEASURED): 9.3 **+21 s / +4.2 GB**; 9.4 **+20 s / +17 GB**; 9.8 **+2.6 s**; 10.1 **+41 s**; 12.1 +9 s; 12.5 +26 s; 12.8 +13 s; 12.10 +12 s; 12.14 +3–5 s; 13 +0.2%.

| GPU | Value | Class |
|---|---|---|
| RTX 5090 idle fraction | "~80–90%" | **ASSERTED — never profiled** |
| Actual OpenCL coverage | **Only the wavelet transform** uses OpenCV UMat/OpenCL | MEASURED (code) |
| CPU-only stages | ECC align, dense flow, focus measure, Guo depth fit, compose, NLM, guided-filter inpaint, tonemap, deconv, defringe, all I/O | MEASURED (code) |
| OpenCV prebuild | 15 modules (`opencv_modules.hpp:13-28`), **no CUDA, no contrib** → no BM3D/xphoto, no ximgproc guidedFilter (hand-rolled 50-line substitute) | MEASURED (code) |
| GPU serialisation | `m_opencl_users` gate in `worker.cc:237-253` allows one GPU task at a time | MEASURED (code) |

---

## 3. What was tried and FAILED — with diagnosed mechanism

**The INTRINSIC / ARTIFACT column is the point of this section.** ARTIFACT failures are re-openable in a new Rust implementation; INTRINSIC ones are not.

| # | Technique | Expected | Actual | Mechanism | Verdict |
|---|---|---|---|---|---|
| F1 | **Wavelet softmax merge** (per-pixel per-subband `max\|c\|²`) | √N noise reduction from 33 frames | **2.3–4.6× worse** than source cross-frame σ; 1.82× worse than a *single* frame in highlights | `max\|c\|` over frames is an order statistic → selects the noisiest coefficient wherever signal is focus-invariant. `task_merge.cc:246-280` | **INTRINSIC** to selector-style merging. A new merge must be an *estimator*, not a selector. |
| F2 | **Winner-copy colour output** | Merge determines output | `Task_Compose_Color::run_winner_copy()` does `argmin\|gray_k − merged_gray\|` then copies that frame's colour **verbatim** — the merge never contributes output colour | Architectural decision inherited from upstream | **INTRINSIC to that architecture**, trivially avoidable in a new one. Root cause of F1's visible symptom. |
| F3 | **Noise2Noise denoising on bracket pairs** | 2–3× σ reduction ("single biggest denoise win", phase11) | **Flat σ +4.6% to +18.1%** — wrong direction at *every* pair distance | Focus brackets violate N2N's i.i.d.-noise assumption: the L2 minimiser converges to E[f_j\|f_k] (a defocus average), not E[X\|n_k]. Val-loss floor 6–10e-6 vs true noise variance 4.3e-8 → loss is 150–230× dominated by defocus differences. **Synthetic-noise control achieved −84%**, proving the architecture is sound. | **INTRINSIC to using bracket frames as N2N pairs.** Re-openable only with genuinely-repeated same-focus captures. Corpus documents a revisit condition: ISO 6400+ with NR=0. |
| F4 | **PDAF-pixel masking** | ~759 PDAF points, "~85% probability of working, paper-worthy" | **0 candidate pixels** in a 5-frame cross-frame anomaly intersection; anomaly density 0.022–0.024% = noise floor | A7C II (BIONZ XR generation) uses dual-pixel / quad-Bayer PDAF with **no sparse-anomaly signature**. RawTherapee camconst.json covers only 25 *older* sparse-PDAF Sony bodies. | **INTRINSIC to this sensor generation.** Do not build a sparse-PDAF masker for modern Sony bodies. |
| F5 | **Wronski 2019 sub-pixel burst super-resolution** | Sub-pixel jitter → SR | Measured shift σ **0.075 px** vs the ≥0.3 px gate; 0.273 px even on the most relaxed 33-frame estimate | Tripod + electronic shutter = no hand jitter. The initially-encouraging 0.42 px was an artifact of defocus shifting correlation peaks monotonically with \|k−refidx\|. | **INTRINSIC to a tripod rig.** Re-openable only with a deliberate sub-pixel dither capture protocol (e.g. sensor-shift or a micro-jitter stage). |
| F6 | **NLM-Multi cross-frame denoise (Phase 10.1)** | 1.38× flat-σ reduction (as measured at ship) | After Phase 12.5, the **same code** measures **+35% to +48% worse** | Denoising *after* an already-applied 33-frame arithmetic mean adds patch-correlated noise; uint8 quantisation compounds it. | **ARTIFACT of placement + baseline drift.** Cross-frame denoise *before* merge is untested and still promising. |
| F7 | **Anscombe VST denoising (Phase 12.9)** | Variance stabilisation → uniform-`h` denoise | **Sobel −65%** (0.253 → 0.088) | With the shipped a≈1e-6 profile, the stabilised range collapses to span ~1.15, so a constant `h` over-smooths everything. | **INTRINSIC to Anscombe when the Poisson slope → 0** (already-denoised input). With the *correct* a≈1.84e-5 raw-domain coefficient on genuinely raw data, untested. Worth re-opening in a RAW-native design. |
| F8 | **RCD demosaic (Phase 12.15)** | +20–25% sharpness (literature) | **+1.30% / +2.26%** | "Approach B" synthesises Bayer from a bilinear render because `dcraw_process()` calls `raw2image_ex(1)`, which overwrites any pre-filled `imgdata.image`. RCD therefore ran on already-interpolated data. | **ARTIFACT of the demosaic-then-RGB-only architecture.** This is the corpus's clearest prediction-vs-measurement failure and it is *entirely* architectural. A Bayer-native design should re-test RCD. |
| F9 | **IRLS robust Guo depth fit (Phase 9.3)** | Robustness to FM spikes | 1.36× bias reduction at a mild 1.1× spike but **amplifies bias 0.80× (1261→1579 codes) at a severe 1.5× spike**; +21 s, +4.2 GB | Single-pass IRLS initialised from OLS reinforces a bad pass-1 fit when the outlier dominates the initial residuals. | **ARTIFACT of single-pass-from-OLS.** Proper multi-start / median-init / full IRLS convergence is untested. |
| F10 | **Variational Jacobi depthmap regularisation (12.2b)** | ≥30% flat-σ drop | **12.46%** | Jacobi propagates information 1 px/iteration; 1000 iterations ≈ 16 px diffusion radius on a 256-px ROI — the solve never reaches global scale. | **INTRINSIC to Jacobi.** Multigrid v-cycle (or a conjugate-gradient / FFT Poisson solve) is the untested fix and is likely to work. |
| F11 | **DualFocus joint AIF+depth (NeurIPS 2025)** | Joint all-in-focus + depth | AIF edge Sobel **−85.0%**; flat σ only −20.5%. Mask-restricted: depth σ **−57.2% (a real win)**, AIF flat σ −12.7% (misses 30% gate) | The Gaussian-weighted-mean data term is structurally a *blender*. | **INTRINSIC to that data term.** The fix — a defocus-blur-aware term `Σ_k‖I_k − AIF∗B_{d(k)}‖²` — needs a PSF model the fork never had. **The depth half is a genuine, large, unexploited win.** |
| F12 | **MDDL as an independent confidence channel** | New information vs ISTD | Pearson(MDDL, ISTD) = **0.926**; EDGE/SMOOTH ratio 1.4× vs Helmli-Scherer's 2.9×; disjoint mass 0.14% | Per-pixel **max** aggregation collapses MDDL's directional information into a texture-amplitude scalar, which is what ISTD already measures. | **INTRINSIC to scalar aggregation.** A direction-preserving *vector* fuse is untested. |
| F13 | **Depth-from-chromatic-aberration** | Independent depth cue | Signal is real and sign-correct on TIFF (d_R−d_G +0.32, d_B−d_G −0.37, edge/flat 37.2×) but Gate C fails at **+4.7%** substrate σ; edge dispersion **worsens** 0.043→0.072 | On the ARW path the sign inverts (−0.51) because rawpy AHD without denoise is noise-dominated. | **INCONCLUSIVE, not failed.** The cue exists. Untested: recapture with Defringe=0 plus a calibrated LCA-axis projection combiner. |
| F14 | **Sony firmware reverse-engineering for optical LUTs** | Extract vignetting/distortion/CA tables | FDAT entropy 7.9998/8.0; 0/17,394 low-entropy windows; 0 `UDTRFIRM` hits; 0/9 crypters work | Payload is encrypted with a key resident only in `libupdatertalk.so` on the camera. | **INTRINSIC / blocked.** Abandon. (Note the *alternative* route in §8: MakerNote 0x9050/0x9400 substitution-cipher decode.) |
| F15 | **DCP (Adobe Standard) colour profile** | Match Lightroom colour | ΔE ~5 on saturated red — **worse** than the 5-anchor PCHIP tone curve's ΔE 3.0 | Adobe Color (the actual LR default) is compiled into the LR binary and not extractable; Adobe *Standard* is a different, older profile. | **ARTIFACT of profile choice.** Not a reason to avoid DCP generally. |
| F16 | **Phase 9.2 halo-radius merge mask** | Halo suppression | **Never implemented** | Requires a *completed* depthmap at merge time; the task graph is a fixed DAG built entirely up front (`focusstack.cc:593-680`) with no feedback edges. | **ARTIFACT of the static task graph.** A new scheduler with multi-pass support removes this constraint entirely. |
| F17 | **Naive cross-frame mean for √N noise reduction** | √5 = 2.24× at N=5 | **1.10×** | Focus-bracket frames have **correlated** noise (shared read pattern, fixed-pattern noise, and — critically — the same scene re-imaged through a slowly-varying optical transfer function). | **MEASURED constraint, partly INTRINSIC.** A new design must not assume independent noise across bracket frames. |
| F18 | **Naively porting the ARW-domain noise coefficient into the rendered-domain predictor** | Correct σ prediction | Over-predicts σ by **2.3×** (0.00295 vs 0.00126); engagement 86.0%→91.7%; visible regression | WB multipliers and the colour matrix change signal amplitude, so raw-domain `a` ≠ rendered-domain `a`. | **INTRINSIC physics.** Any noise model must be attached to a declared colour/scale domain. |

---

## 4. What was tried and WORKED

| # | Technique | Measured benefit | Cost | Evidence class |
|---|---|---|---|---|
| W1 | **Phase 13 focus-aware flat AND-mask** | substrate Sobel **+18.83%**, Lap-var **+40.1%**, flat σ cost only **+0.5%**; carves 72.9% of the Phase 8.2 flat mask | ~0.2% wall time, +128 MB | **MEASURED** — best cost/benefit in the corpus |
| W2 | **Post-stack Wiener deconvolution (12.14)** | Sobel top-5% **+25.4%** (marker), **+105.4%** (coffee-bean); edge width 13.10→12.49 px | 3–5 s CPU; **flat σ +6.8%** | **MEASURED** — best sharpness win. Note the corpus text claims it "does not amplify flat-region noise", contradicting its own +6.8%. See §7.2. |
| W3 | **Phase 9.8 Helmli-Scherer confidence channel** | **19.7×** smooth/edge discrimination (66.6 vs 3.4 codes) | +2.6 s | **MEASURED** — cheapest real win |
| W4 | **Phase 8.2 flat-region cross-frame mean** | σ −13% / −21% / **−55%** (shadow/mid/highlight); edge RMS\|Δ\| ≈0.0007 | ~1 s, ~1.3 GB | **MEASURED** for the before/after ROI numbers; but **no standalone before/after run was ever published**, and the predicted 5.7× was never approached. Partially **UNVERIFIED**. |
| W5 | **Lateral CA correction (Phase 6.2)** | corner \|R−G\| **2.0 px → 0.3 px** | negligible | **MEASURED** — but coefficients are hardcoded, rig-specific (A7C II + SEL100F28GM + SEL20TC) |
| W6 | **5-anchor PCHIP tone curve (Phase 6.1)** | ΔE76 **9.4 → 3.0** vs LR export | negligible | **MEASURED**, but on the marker bracket **only** — single-scene fit, generalisation untested |
| W7 | **Phase 9.4 temporal FM median5** | **4.2×** depth-bias reduction (1539→366 codes) | +20 s, **~17 GB transient RAM** | **MEASURED**, but on **synthetic** spikes only. Real-data benefit unverified. RAM cost is prohibitive. |
| W8 | **DepthAnything V2 as a soft depth prior** | Pearson 0.607 low-texture (gate 0.30); downstream smooth-region depth std **+12.1%** @σ=0.05 | 0.27 s forward (on CPU); sidecar process | **MEASURED**. Shipped with a known **HIGH** bug (stale cache on sidecar failure). |
| W9 | **DualFocus depth term, mask-restricted** | Depth σ **−57.2%** (827→354 codes) | — | **MEASURED**. The AIF half failed (F11); the depth half is a real unexploited win. |
| W10 | **Compound RCD + Phase 13 + gentle Wiener** | **+22.7% Sobel at +23% Lap-var** on a 53-frame coffee-bean bracket | — | **MEASURED** |
| W11 | **ECC + dense-flow alignment** | ECC 0.9999–1.0000 on all 32 non-ref frames; dense-flow median residual 0.05–0.09 px | — | **MEASURED**. Alignment is *not* a problem area on this rig. |
| W12 | **`FocusPosition2` extraction via LibRaw 0.22.1** | 56→57 across 5 frames; **≈3.1 mm per servo step** | negligible | **MEASURED**. Real, usable optical metadata. |
| W13 | **Foi-Mäkitalo noise model selection by AIC** | ΔAIC −37.8 (G) decisive over alternatives | probe-only | **MEASURED** |
| W14 | **Anscombe round-trip correctness** (after removing a spurious `/a` divisor) | RMS ~5e-7 | — | **MEASURED**. The *transform* is correct; the *denoise application* failed (F7). |

**Flagged as claimed-to-work-without-measurement:**

| Claim | Why flagged |
|---|---|
| "DHT preserves more high-frequency detail than AHD on low-ISO macros" | **ASSERTED**, never measured — and `PHASE12_11` later measured the DHT path as 30–44% softer than Lightroom. |
| "Vignetting <0.05 EV, distortion <0.05%" | **MEASURED once** in Phase 6.2, then re-asserted second-hand in `thread_A` and `thread_H` without re-verification. |
| NLM POC "σ = 0.0000, infinite improvement" | The ROI variance was 0.0055 in **uint8** units — the result is dominated by 8-bit quantisation, not by NLM quality. Would not hold at 16 bits. |
| "RTX 5090 idle 80–90%" | **ASSERTED**, never profiled (directionally certain from the code, but the number is invented). |

---

## 5. Open problems the corpus identified but never solved

| # | Problem | Status in corpus | Class |
|---|---|---|---|
| O1 | **DNG output never validated in Lightroom.** The fork writes a DNG but no one ever opened it in the target application. | Known defect, `thread_E_color_dng.md` | **UNVERIFIED output format** |
| O2 | **DNG strips all 112 Sony MakerNote tags** (1639 lines → 63). | Known defect | MEASURED |
| O3 | **Depthmap noise-floor heuristic is unprincipled** — a hand-tuned threshold with no derivation from the noise model. | Flagged, never solved | ASSERTED heuristic |
| O4 | **`--vignette-correct` / `--distortion-correct` are accept-and-warn stubs.** | Unimplemented | MEASURED (code) |
| O5 | **Noise profile is in the wrong domain.** Shipped `a`≈1e-6 is 17–20× too low; the correct ARW-domain value cannot be used because the predictor runs in rendered Rec.2020. Documented as a multi-week architectural fix, **never done**. | Known defect | MEASURED |
| O6 | **Active-area disagreement**: AGENTS.md 4672×7008 vs rawpy 4688×7028. The probe emits a WARNING. Never resolved. | Open | MEASURED, conflicting |
| O7 | **No standalone before/after measurement for Phase 8.2** was ever published, so its true contribution to the shipped pipeline is unknown. | Open | UNVERIFIED |
| O8 | **The √N floor was never approached.** Best measured plain-mean gain: 1.10× at N=5 vs 2.24× theoretical. The correlated-noise mechanism was identified but never characterised or defeated. | Open, **highest-value open problem** | MEASURED |
| O9 | **DA2 sidecar stale-cache bug (HIGH severity)** — a sidecar failure leaves a stale `.f32.bin` that is silently reused. | Known, unfixed | MEASURED (code review) |
| O10 | **Denoise-placement bind** (`PHASE10_DESIGN.md §9.5`): pre-denoising destroys the raw noise levels that the Phase 8.2 flat-detector and the Phase 9.1 confidence channel depend on. No resolution proposed. | Open, **architecturally decisive** | ARGUED on MEASURED base |
| O11 | **Phase 9.2 halo-radius merge mask** — designed, never implementable in a static DAG. | Deferred permanently | ARTIFACT |
| O12 | **Depth-chain ordering is non-monotone** (outward from refidx: 16,15,17,14,18…), forcing a 17 GB full-bracket FM buffer for any temporal filter. Never restructured. | Open | MEASURED |
| O13 | **Memory does not scale.** ~23 GB peak at 33 frames with all features; ~80 GB extrapolated at 105 frames. No streaming, no spill-to-disk. | Open | MEASURED / extrapolated |
| O14 | **Wall time regressed 5×** (81 s → 426–456 s) through feature accretion with no performance budget. | Open | MEASURED |
| O15 | **Pixel pitch is wrong and inconsistent throughout** — every diffraction/PSF budget in the corpus except the 12.14 deconv PSF is built on a wrong number. | Open (undetected by the corpus) | see §7.3 |
| O16 | **Correlated-noise characterisation across a focus bracket** — identified as the cause of the 1.10× result, never modelled. | Open | MEASURED symptom, no model |
| O17 | **No PSF / defocus model anywhere.** This blocked the DualFocus fix (F11), blocked principled deconvolution, and blocked depth-from-defocus. | Open | ARGUED |

---

## 6. Architectural mistakes to avoid

Each entry names the **coupling**, not just the symptom.

| # | Mistake | The coupling | What it cost, measured |
|---|---|---|---|
| A1 | **Winner-copy colour output is the root defect.** `Task_Compose_Color::run_winner_copy()` does `argmin\|gray_k − merged_gray\|` and then copies that frame's colour **verbatim**. | The wavelet merge only influences the *argmin*; it never contributes output colour. Output colour is therefore always exactly one source frame's pixel. | This is why flat regions carry one random frame's noise (§2.2). **Phases 8.2, 9.1, 11.7.3, 12.1e, 12.6 and 13 are all patches around this single decision.** |
| A2 | **The grayscale / wavelet / focus-measure chain is permanently 8-bit.** `task_grayscale.cc` divides 16-bit input by 257 to stay in 0–255. | Every downstream stage — depth precision, focus-measure SNR, Guo fitting — inherits 8-bit quantisation regardless of a 32-bit float input. | Hard quality ceiling. Directly caused the bogus "σ = 0.0000" NLM POC result (§4). |
| A3 | **Demosaic-then-RGB-only.** `dcraw_process()` runs before any pipeline stage, and `raw2image_ex(1)` overwrites pre-filled buffers. | Bayer-domain focus measure, alignment, denoise and merge are **structurally impossible** without replacing LibRaw's pipeline. FBDD is the only pre-demosaic exception. | Directly caused RCD's **+1.30% instead of +20–25%** (F8). Also forecloses the projected ~1 dB Bayer-domain merge win. |
| A4 | **Denoise placed after merge, not cross-frame before it.** | NLM-Multi (10.1) runs post-compose and therefore competes with an already-applied 33-frame mean. Phase 12.8 moved *per-frame* NLM before compose (better), but `PHASE10_DESIGN.md §9.5` documents the real bind: pre-denoising destroys the raw noise levels the Phase 8.2 flat-detector and Phase 9.1 confidence channel consume. | 1.38× win → **+35–48% regression** (F6). **A new design needs a noise-robust-by-design focus measure, or an explicit two-pass architecture, to escape this.** |
| A5 | **Only the wavelet transform is on OpenCL**, and a serialising `m_opencl_users` gate in `worker.cc:237-253` allows one GPU task at a time. | No CPU/GPU pipeline interleaving; no way to add a second GPU stage without contending on the gate. | RTX 5090 essentially idle; wall time 426–456 s on a machine that should be GPU-bound. |
| A6 | **Fixed acyclic task graph built entirely up front** (`focusstack.cc:593-680`). | No feedback edges, no multi-pass. | Phase 9.2's halo-radius merge mask was **permanently deferred** (F16). Also caused Phase 12.5's discovery that the entire confidence pipeline had been **silently no-opping at default flags for its whole pre-12.5 life** — a whole-graph correctness failure invisible to the developer. |
| A7 | **`release_temporaries()` keeps all aligned frames live** when `keep_compose_color=true` (the default). | 6.3 GB colour + 12.6 GB HDR float for 33×32 MP; ~23 GB peak with all features. No streaming, no spill. | Hard frame-count ceiling; ~80 GB extrapolated at 105 frames. |
| A8 | **Precision downcasts around NLM**: float → uint8 (÷257) → NLM → uint16 (×257), i.e. **~7.8 effective bits**, applied precisely in the precision-critical in-focus pinch zone. | OpenCV's `fastNlMeansDenoisingColoredMulti` is CV_8UC3-only, so the dependency dictated the pipeline's precision. | Compounded F6. |
| A9 | **HDR-preserve is a bolted-on parallel buffer** (`m_result_hdr` CV_32FC3 alongside the encoded CV_16UC3). | Every quality stage needs two code paths; HDR pixels >1.0 skip NLM entirely. | Permanent maintenance tax and silent per-stage coverage holes. |
| A10 | **No plugin or extension points anywhere.** Every Phase 8–13 feature was added by directly editing `task_compose.cc`, `task_depthmap.cc`, `focusstack.cc`, `main.cc`. | No focus-measure, merge, alignment, demosaic or output interface; CLI flags added ad hoc with no registration mechanism. | Feature accretion with no isolation → the baseline-inversion problem (§2.3) became undetectable until a dedicated audit found it. |
| A11 | **Optical-model coupling is hostile to any lens/body plugin.** `RawExifInfo` has **no focus-position field**; `read_raw_exif()` reads only the **first** ARW of a bracket; `apply_lateral_ca_correction` / `fit_radial_breathing` hardcode `cx=(cols-1)*0.5`; CA coefficients are compile-time constants in `task_loadraw.hh:99-118`. | Per-frame optical state cannot enter the pipeline at all; optical centre cannot be calibrated; coefficients cannot be swapped per rig. | `FocusPosition2` was *measurable* (W12) but **unusable**. `--vignette-correct`/`--distortion-correct` remained stubs (O4). |
| A12 | **Depth-chain ordering is non-monotone** (outward from refidx). | Prevents streaming for any temporal filter. | Forced the **~17 GB** transient buffer for Phase 9.4 (W7). |
| A13 | **OpenCV prebuild without CUDA or contrib** (`opencv_modules.hpp:13-28`, 15 modules). | No BM3D/xphoto, no ximgproc guidedFilter → a hand-rolled 50-line substitute. | The dependency's build configuration silently determined which algorithms were even *available* to try. |

---

## 7. Claims I believe are WRONG or unsupported

### 7.1 Falsified by later measurement within the corpus

| Claim | Source | Falsified by |
|---|---|---|
| "N2N is the single biggest denoise win, 2–3× σ reduction" | `phase11_thread_C_deeplearning.md` | `PROBE_N2N_PICK4.md`: +4.6% to +18.1%, wrong direction at every d |
| "~759 PDAF points, ~85% probability of working, paper-worthy" | `phase11` / `thread_A` | `PROBE10_PDAF_MASK.md`: **0** candidate pixels |
| "Per-channel WAVS gives ~0.13 → ~0.05 frame depth precision" | `phase11_thread_D_novel.md §5` | `PROBE_DEPTH_FROM_CA.md`: edge dispersion **worsens** 0.043 → 0.072 |
| "Phase 8.2 will give √33 ≈ 5.7× improvement" | Phase 8.2 design | `PHASE9_10_DELIVERABLE.md §10.1`: plain mean measured **1.10×** at N=5 |
| RCD demosaic "+20–25%" | `PHASE12_12` | `PHASE12_15`: **+1.30% / +2.26%** |
| "DHT preserves more high-frequency detail than AHD on low-ISO macros" | AGENTS.md | `PHASE12_11`: the DHT path is **30–44% softer** than Lightroom |

### 7.2 Internally inconsistent

| Claim | Contradiction |
|---|---|
| Deconv "does not amplify flat-region noise" | The **same section** reports measured flat-ROI σ **+6.8%**. Take the number, discard the sentence. |
| DA2 cache-miss run "~213 s, faster than the 235 s baseline" | **Impossible** — the sidecar *adds* ~1.3 s. Almost certainly a different flag set. Documentation artifact; discard the timing. |
| NLM POC "σ = 0.0000, infinite improvement" | ROI variance was 0.0055 in **uint8** units. The result measures 8-bit quantisation, not denoise quality. |
| NLM-Multi "1.38× flat-σ reduction" (shipped claim) | The identical feature measures **+35% to +48% worse** post-12.5. Both are MEASURED; the *claim* is only valid relative to a baseline that no longer exists. |

### 7.3 Wrong physical constants

**Pixel pitch is stated four different ways and every one of them is used in a downstream calculation:**

| Value | Where | Status |
|---|---|---|
| 3.76 µm | `PHASE12_12` | **wrong** |
| 4.7 µm | `AGENTS.md:2621` | **wrong** (closest) |
| 5.1 µm | `thread_H_lens_optics.md` | essentially right, unsourced |
| 6.0 µm | `PHASE12_RESEARCH.md` | **wrong** |
| **≈5.12 µm** | 35.9 mm / 7008 px — my derivation | correct |

Consequence: **every diffraction-limit and PSF budget in the corpus is built on a wrong number.** The one exception is accidental — the 12.14 deconv Airy radius of 2.1 px was computed as 10.7 µm ÷ 4.7 µm = 2.28 and then "rounded conservatively" to 2.1, which happens to equal 10.7 ÷ 5.12. **The deconv result (W2) is safe; the surrounding optical reasoning is not.**

### 7.4 Fabricated or misattributed citations

The corpus **caught these itself** in PHASE12, which is to its credit — but the implication is broad.

| Citation | Reality |
|---|---|
| "Liu, CFS-FocusNet, 2024" | **Does not exist** |
| "Yang, FocusOnMe, 2023" | **Does not exist** |
| "MaCFNet 2024" | Real paper, but it is **retinal optic-disc segmentation**, not multi-focus image fusion |
| "Lee & Tai 2016, Matlab implementation available" | **False.** `PROBE7_LEE_TAI.md`: zero public code; the bibliography entry had the **wrong author initial** *and* the **wrong title** (real title: *Robust All-in-Focus Super-Resolution for Focal Stack Photography*); 18 lifetime citations, 0 influential |

**⇒ Treat every uncited literature number in this corpus as suspect.** Only numbers produced by the corpus's own probes should be carried forward.

### 7.5 Asserted, never verified

| Claim | Problem |
|---|---|
| "RTX 5090 idle 80–90%" | Never profiled. Directionally certain from the code (only the wavelet is on OpenCL) but the number is invented. |
| "Vignetting <0.05 EV / distortion <0.05%" | Measured once in Phase 6.2, then re-asserted second-hand in `thread_A` and `thread_H` without re-verification, and used as a justification not to implement O4. |
| Active area 4672×7008 | Contradicted by the rawpy probe (4688×7028), which itself emits a WARNING. Unresolved. |

### 7.6 Disagreements between documents — adjudicated

| Disagreement | Documents | Which has the evidence |
|---|---|---|
| **Pixel pitch** | `PHASE12_12` (3.76) vs `AGENTS.md:2621` (4.7) vs `thread_H` (5.1) vs `PHASE12` (6.0) | **None.** Correct value ≈5.12 µm from sensor dimensions. `thread_H` is closest. |
| **Active area** | AGENTS.md (4672×7008) vs rawpy probe (4688×7028) | **Unresolved.** The probe is the direct measurement and emits its own warning; AGENTS.md's number matches the nominal 33 MP spec. Re-measure. |
| **DA2 downstream quality probe** | One extraction pass claimed it was never run; `AGENTS.md:2133` and `:2185` report it *was*, with numbers (+12.1% / +9.1% / +6.4%) | **AGENTS.md wins** — verified by direct grep. |
| **Phase 8.2 expected gain** | Design doc (5.7×) vs `PHASE9_10_DELIVERABLE.md §10.1` (1.10× measured for plain mean at N=5) | **§10.1 wins** — it is the measurement. |
| **Deconv flat-region noise** | Narrative ("does not amplify") vs the section's own table (**+6.8%**) | **The table wins.** |
| **NLM-Multi value** | Phase 10.1 (1.38× win) vs `NLM_MULTI_OBSOLESCENCE.md` (+35–48% regression) | **Both are correct measurements against different baselines.** This *is* the finding. |
| **CA-depth sign** | TIFF path (+0.32, sign-correct) vs ARW path (−0.51, wrong-signed) | **TIFF wins** — the ARW path is noise-dominated (substrate σ 9.03 vs 3.87 frames). |

---

## 8. Ideas the corpus raised but never tested

Ordered by my estimate of value to the new Rust design. "What would settle it" is the experiment.

| # | Idea | What it is | What would settle it |
|---|---|---|---|
| I1 | **HDR+/Wiener per-subband SNR-weighted merge** | Replace `max\|c\|` selection with a per-subband, per-pixel SNR-weighted *estimator*. It degenerates to √N averaging where the signal is focus-invariant and to winner-take-all where it varies. | Directly attacks F1/A1, the corpus's root defect. Settle by implementing the Wiener weight `w_k = \|c_k\|²/(\|c_k\|²+σ²)` normalised over k, and measuring flat-ROI σ against the §2.2 table. **The corpus's single most promising untested idea.** |
| I2 | **Bayer-domain merge before a single demosaic** | Do focus measure, align, denoise and merge on CFA data; demosaic once at the end. | Projected ~1 dB (ARGUED). Blocked entirely by A3. Settle by building it Bayer-native and re-running the RCD comparison that failed as F8. |
| I3 | **Cross-frame denoise *before* merge, with a noise-robust focus measure** | Escapes the A4/O10 bind by making the focus measure not depend on raw noise levels. | Settle by choosing a focus measure whose response is calibrated against the noise model (rather than thresholded against raw σ), then re-running the F6 comparison. |
| I4 | **Sony MakerNote 0x9050 / 0x9400 substitution-cipher decode** | These tags carry the camera's own distortion / vignetting / CA LUTs. The cipher is public knowledge; LibRaw does not expose them. Estimated ~30 LOC decoder + ~100 LOC parser. | **Highest-value untested optical-metadata source**, and the live alternative to the dead firmware route (F14). Settle by decoding one ARW and comparing the LUT against the Phase 6.2 measured CA correction. |
| I5 | **DualFocus with a defocus-blur-aware data term** | Replace the Gaussian-weighted-mean term with `Σ_k‖I_k − AIF ∗ B_{d(k)}‖²`. | Fixes the F11 mechanism. Requires a PSF model (O17). Settle by fitting a per-frame PSF from the bracket and re-running the 8-config sweep. The depth half already works (**−57.2%**). |
| I6 | **Multigrid v-cycle depthmap solve** | Replaces Jacobi, whose 1 px/iteration propagation caused F10. | Settle by re-running the 12.2b ROI test with a v-cycle; the 30% gate is plausibly reachable since edge retention was already 136%. |
| I7 | **DfD blur-radius cross-check as a confidence tiebreaker** | Estimate blur radius per frame and use disagreement with the FM-argmax as a confidence signal. | Needs a PSF model. Settle against the Phase 9.8 Helmli-Scherer channel's 19.7× discrimination as the baseline to beat. |
| I8 | **LCA-axis projection combiner + Defringe=0 recapture** | Project the R/G/B focus estimates onto the calibrated longitudinal-CA axis instead of differencing them pairwise. Recapture without Lightroom defringe. | Settle F13. The signal is measured and sign-correct (+0.32/−0.37, edge/flat 37.2×); only the combiner failed the +4.7% gate. |
| I9 | **DINOv2 / foundation-feature focus measure for textureless regions** | Use self-supervised features as a focus measure where gradient operators have no signal. | DA2 already showed foundation models help most in **low texture** (Pearson 0.607 vs 0.451 high-texture). Settle by measuring depth σ in flat ROIs against the ISTD baseline. |
| I10 | **MDDL as a direction-preserving vector** | Keep the directional components instead of per-pixel max aggregation. | Settle F12. Disjoint mass was only 0.14% *after* scalar collapse; measure it before collapse. |
| I11 | **Empirical `FocusPosition2` → mm calibration on a focus rail** | Turn the measured ~3.1 mm/step (W12) into a calibrated, per-frame absolute depth scale. | Settle with a rail traverse at known displacements. Would give the depthmap true metric units and a per-frame optical state — but requires fixing A11 first. |
| I12 | **Optical-centre offset estimation from the CA null point** | Replace the hardcoded `cx=(cols-1)*0.5` (A11) with a measured optical centre. | Settle by fitting the radius at which lateral CA crosses zero; compare corner \|R−G\| against W5's 0.3 px residual. |
| I13 | **N2N revisited at ISO 6400 with in-camera/LR NR off** | The F3 test bracket was ISO 100 + Color NR=25, where only **19.88%** of spatial σ was removable noise. The corpus explicitly documents this revisit condition. | Settle by recapturing at ISO 6400, NR=0, and re-running the pair-distance sweep. **Note: the i.i.d. violation (F3's mechanism) is still present**, so I rate this lower than the corpus does. |
| I14 | **Gerchberg-Saxton phase retrieval from defocus planes** | Recover the wavefront from the focus bracket itself, giving a PSF model for free. | Would resolve O17 and unlock I5/I7. Settle with a synthetic bracket generated from a known PSF. |
| I15 | **Tomographic / plenoptic reconstruction of the focal stack** | Treat the bracket as a sampled light field. | **ASSERTED** in `thread_G_novel.md` with no development. Settle by checking whether the angular sampling implied by an f/2.8 macro bracket is sufficient — likely not, but cheap to determine analytically. |
| I16 | **Correlated-noise model across the bracket** | Characterise *why* plain averaging gives 1.10× instead of 2.24× (O8/O16, F17). | Settle by measuring the frame-to-frame noise covariance matrix directly on a dark/flat bracket. **This is a prerequisite for any principled merge**, including I1. |

---

## 9. What this means for the new design (my synthesis)

Three conclusions I would carry into the Rust implementation, each traceable to measurements above:

1. **Make the merge an estimator, not a selector.** F1/A1 are the corpus's root defect: `max|c|` selection plus winner-copy colour means flat regions receive one random frame's noise, measured at **1.82× worse than a single source frame** in highlights. The fix is a per-subband, per-pixel SNR/Wiener-weighted estimator (I1) that degenerates to √N averaging where the signal is focus-invariant. Everything the fork built in Phases 8–13 was a patch around this.

2. **Be Bayer-native, full-precision, and put cross-frame denoise before merge — which forces a noise-robust focus measure.** A2 (8-bit chain), A3 (demosaic-first) and A4/O10 (denoise placement) are three faces of one problem. A3 alone cost the RCD experiment its entire predicted benefit (**+1.3% vs +20–25%**). But note the trap in O10: pre-denoising destroys the noise levels the flat-detector consumes. The new focus measure must be calibrated against an explicit noise model rather than thresholded against observed raw σ — and that noise model must declare its colour/scale domain (F18: a domain mismatch cost a **2.3×** σ over-prediction).

3. **Treat measurement infrastructure as a first-class component, not an afterthought.** `NLM_MULTI_OBSOLESCENCE.md` is the corpus's most transferable lesson: an honestly-measured **1.38× win** became an honestly-measured **+48% regression** without the algorithm changing. In a plugin architecture where third parties contribute merge and focus-measure implementations, this failure mode is not incidental — it is the default. The system needs a permanent, versioned, automated A/B harness (ROI flat-σ, edge Sobel, Laplacian variance, depth σ, wall time, peak RSS) that every plugin is scored against on a fixed reference bracket set, with results attached to a *named baseline revision*. Also budget performance from day one: the fork went **81 s → 456 s** and **6 GB → 23 GB** by accretion, with no gate.

---

## Appendix: reliability notes on this corpus

- **The probes are trustworthy.** The nine `PROBE*` documents ran real code against real data, reported gates in advance, and reported negative results honestly (F3's synthetic control and F5's self-diagnosed 0.42 px artifact are both excellent practice).
- **The `thread_*` and `PHASE*_RESEARCH` survey documents are not.** They contain fabricated citations, invented constants, and confident probability estimates that measurement later falsified (F3, F4).
- **AGENTS.md is mixed** but its changelog entries are generally MEASURED and are the primary source for most of §2.
- **Anything comparing two pipeline states is only valid relative to a named baseline**, and the corpus rarely names one.

---

# Follow-up 1

Three targeted re-reads against the corpus, done directly (not via sub-agents). `C:\dev\macro` unmodified.

## FU1.1 — The "correlated noise" finding is an ARTIFACT OF THE METRIC. Retract it.

**Verdict: my earlier fact #2 was wrong, and your suspicion is right — but the mechanism is worse (and simpler) than Lightroom processing. The 1.10× number does not measure cross-frame noise reduction at all.**

### What the N=5 measurement actually was

Source: `research\poc_nlmeans_multi.py` (the Phase 10.1 POC that produced the number quoted in `PHASE9_10_DELIVERABLE.md §10.1`).

| Property | Value | Line | Consequence |
|---|---|---|---|
| Input data | `C:\dev\macro\test\*.tif` — **Lightroom-exported 32-bit float Linear Rec.2020 TIFFs** | `TEST_DIR`, `load_quarter_res_uint8` docstring | Never touched an ARW. Your hypothesis confirmed on the data-path question. |
| Frames used | central 5 of a **focus bracket** (`refidx±2`) | `selected = files[refidx-half : refidx+half+1]` | Not repeats. Content genuinely differs frame to frame. |
| Preprocessing | `cv2.resize(..., INTER_AREA)` **4× downsample** | `QUARTER_RES` | A 4×4 box average. Suppresses independent per-pixel noise ~4× *before* the measurement, leaving residual scene structure as the dominant spatial variance. |
| Quantisation | `(img*255).astype(np.uint8)` | same | σ reported in uint8 units; the flat ROI variance was **0.0055**, i.e. σ ≈ 0.074 — **an order of magnitude below one quantisation step.** |
| **`single_sigma`** | `centre[roi].var()` → **spatial** σ within a 32×32 patch of one frame | `single_roi` | **Includes scene structure.** |
| **`mean_sigma`** | `stack.mean(axis=0)[roi].var()` → **spatial** σ of the same patch in the mean image | `mean_roi` | **Also includes scene structure — and averaging frames does not reduce structure.** |
| Reported ratio | `single_sigma / mean_sigma` = **1.10×** | | **Structure-floored by construction.** |

**Mechanism of the artifact (MEASURED, from the script itself):** the ratio `single_sigma/mean_sigma` is mathematically bounded above by the fraction of spatial variance that is noise. After a 4× INTER_AREA box-average of an already Lightroom-denoised (Color NR=25) TIFF, quantised to uint8 at σ≈0.074 codes, essentially **none** of the residual spatial variance in the "smoothest patch" is temporal noise — it is residual scene texture plus quantisation. The correct measurement of cross-frame averaging gain is the **temporal** σ at a fixed pixel as a function of N. This script never computed it. **The 1.10× is a measurement of scene structure, not of noise correlation.** Label: the number is MEASURED, the *interpretation* was ASSERTED and is wrong.

### Was cross-frame σ ever measured properly? Yes — and it was measured *temporally*.

`research\probe_noise_tonal.py:77` computes `sigma_src = src_patch.std(axis=0).mean(axis=(0,1))` — **standard deviation across the frame axis at each pixel**. That is a genuine temporal cross-frame σ. It is the source of `empirical_findings.md §2 / §2b`.

| Quantity | Value | Cite | Class |
|---|---|---|---|
| Cross-frame (temporal) σ per pixel, deep-shadow patch, B/G/R | 0.00019 / 0.00025 / 0.00021 | `empirical_findings.md §2` | **MEASURED** (temporal) |
| Cross-frame σ(G), deep_shadow / mid_tone / highlight | 0.00012 / 0.00046 / 0.00091 | `empirical_findings.md §2b` | **MEASURED** (temporal) |
| "√33 ideal output σ" 0.00003–0.00004; "√5 ideal σ(G)" column | — | `empirical_findings.md §2`, `probe_noise_tonal.py:87` (`sigma_src[1]/np.sqrt(N)`) | **DERIVED — assumes independence. Not a measurement.** |
| Output σ | **intra-patch spatial** σ (`sigma_out = out_patch.std(axis=(0,1))`, line 80) | `probe_noise_tonal.py` | MEASURED, but note §2b compares a *temporal* source σ against a *spatial* output σ |

**Critical consequence:** the corpus's √N columns are arithmetic, not observation. **Nowhere in the corpus is the actual σ-vs-N curve measured.** There is therefore *no evidence in this corpus that bracket noise is correlated across frames.* The claim rests entirely on the flawed POC.

### Was it ever measured on ARW? No.

Every cross-frame statistic I can find — `empirical_findings §2/§2b`, `probe_noise_tonal.py`, `PROBE_N2N_PICK4`'s 0.000208 cross-frame σ, the Phase 10.1 POC — runs on `C:\dev\macro\test\*.tif`, the LR-export TIFFs. The only ARW-domain noise work is `PROBE2_NOISE_AIC` / `calibrate_noise.py`, which fits `Var = a·I + b` from **intensity-binned variance**, not from a temporal σ-vs-N sweep.

### Stated mechanism for the correlation? None. It was never even asserted as a mechanism.

I could find no document that proposes *why* bracket noise would be correlated. `PHASE9_10_DELIVERABLE §10.1` reports the ratio; the "correlated noise" reading is an inference (mine, in the original report — I am withdrawing it). The corpus's own explanation for NLM-Multi's obsolescence in fact **assumes the opposite**: `NLM_MULTI_OBSOLESCENCE.md` § Root cause states "Arithmetic mean over 33 frames gives ~5.7× shot-noise reduction" — i.e. full √33 independence. **Two documents disagree, and neither measured it.**

### Alternative explanations, adjudicated

| Hypothesis | Verdict | Evidence |
|---|---|---|
| **Metric floored by scene structure + uint8 quantisation + 4× box downsample** | **CONFIRMED — this is the explanation** | `poc_nlmeans_multi.py` source, above. Sufficient on its own. |
| **Lightroom demosaic + NR correlating noise spatially** | **Real and contributory, but not needed to explain 1.10×.** Independently corroborated: the shipped noise profile `a≈1e-6` is 17–20× below the ARW fit *precisely because* LR NR removed the shot noise (`PROBE2_NOISE_AIC.md`). And `PROBE_N2N_PICK4` measured cross-frame/spatial σ = **19.88%** on this data — only ~20% of spatial variance was removable noise. | MEASURED |
| **LR correlating noise *across frames*** | **Plausible but UNTESTED.** LR applies deterministic content-dependent processing, so near-identical frames get near-identical treatment. No measurement exists either way. | UNVERIFIED |
| **Residual misalignment** | **RULED OUT.** ECC 0.9999–1.0000; dense-flow residual 0.05–0.09 px; sub-pixel shift σ 0.075 px (`PROBE3_WRONSKI_SUBPIXEL.md §2.1–2.3`). Also the POC used the central 5 frames "where alignment is near identity". | MEASURED |
| **LP-band running mean already applied** | **Not applicable to the POC** — it read source TIFFs directly, not pipeline output. It *does* confound `empirical_findings §2` ("LP-mean helps a little"). | MEASURED |
| **Patches not actually flat** | **CONFIRMED contributory** — this is the same thing as the structure floor. The POC picked the min-variance 32×32 block from a 4×-downsampled image; "flattest available" ≠ "flat". | MEASURED |
| **PRNU / multiplicative FPN** | **Largely RULED OUT at these levels, on ARW data.** `PROBE2_NOISE_AIC.md` fitted M4 = `Var = a·I + b + c·I²` (the PRNU model) and it **never wins by AIC** on any channel: *"PRNU is not detectable at these intensities"* (peak I = 0.42). Predicted contribution **< 0.5%** of total variance at peak. | **MEASURED** |
| **Additive FPN / dark-current shading** | **OPEN — this is the one live fixed-pattern risk.** Any additive fixed pattern is absorbed indistinguishably into the fitted `b ≈ 1.7e-6` (G). The corpus contains **no dark-frame capture and no temporal/fixed split of `b`.** This matters: at mid_tone I = 0.037, `a·I` = 6.8e-7 vs `b` = 1.7e-6, so **the read/offset floor dominates over shot noise across most of this scene**, and whatever share of `b` is fixed-pattern will not average down. | **UNVERIFIED — the real open question** |

### Can the fixed-pattern fraction be estimated from the corpus? Partially.

- **Multiplicative (PRNU):** yes — **< 0.5% of variance at I = 0.42**, AIC-undetectable (MEASURED, `PROBE2_NOISE_AIC.md`). Not a cap.
- **Additive (offset/dark FPN):** **no.** Nothing in the corpus separates it from temporal read noise. The corpus has no dark frames, and the AIC probe used only 12 illuminated ARW frames from one bracket.

### My estimate of achievable cross-frame noise gain on RAW data

**ARGUED, from measured inputs.** At N = 33, on genuinely raw ARW, per-pixel temporal averaging:

| Regime | Estimate | Reasoning |
|---|---|---|
| Shot-noise-dominated (highlights, I ≳ 0.2 where `a·I` ≫ `b`) | **4.5–5.7× (i.e. 80–100% of √33)** | PRNU measured undetectable; alignment measured near-identity; shot noise is Poisson and independent per exposure. |
| Read/offset-dominated (deep shadow and much of mid-tone on this scene, where `b` dominates) | **2–5.7×, wide** | Entirely determined by the unmeasured temporal/fixed split of `b`. If `b` is mostly temporal read noise, ~√33; if half of it is fixed-pattern, the asymptote is ~1.4× at best without calibration. |
| **Overall honest range** | **3–5.5×**, with the low end only if additive FPN turns out to dominate `b` | |

**Confidence that it is materially better than 1.10×: very high (>95%).** The 1.10× is a metric artifact, and its own source document elsewhere assumes 5.7×. **The design pillar is not in danger.** And note the asymmetry: additive FPN is the *one* residual risk, and it is **calibratable** — a master bias/dark subtraction removes it, which a RAW-native pipeline can do and the fork could not.

### The single measurement that settles it

**Capture ≥64 frames of a static scene at fixed focus (no bracket, no LR, straight ARW), plus a matched dark-frame set. Then plot per-pixel temporal σ against N on log–log.**

- Slope **−0.5** ⇒ independent noise; the pillar is fully sound.
- Slope flattening to an **asymptote** ⇒ that asymptote *is* the fixed-pattern floor. Its magnitude directly quantifies the cap.
- Re-run after subtracting a master bias/master dark. **The amount the asymptote drops is the calibratable fraction.**

One capture session, three analyses, no pipeline needed. This should be the **first** measurement the new project makes — it is the go/no-go, it is cheap, and every merge design decision depends on it. Do it in the raw ARW domain, with in-camera NR and long-exposure NR **off**, and repeat at ISO 100 and ISO 6400.

---

## FU1.2 — The ARW-softness finding is NOT the RCD bug. It is mostly *sharpening*, and the corpus proves it with its own control.

### Are the two measurements the same code path? No.

| Fact | Value | Cite |
|---|---|---|
| Sharpness measurement date / binary | **2026-05-17**, Phase 12.10 binary | `PHASE12_11_ARW_VS_TIFF_SHARPNESS.md` header + artefact table |
| Demosaic used on the ARW path in that test | **LibRaw DHT** (`--lr-match` auto ⇒ DHT for DNG output) | `PHASE12_11.md §Factor 1`; AGENTS.md:598 |
| RCD introduced | **Phase 12.15** — *later* | AGENTS.md:2783 |
| Is the `user_qual=0` bilinear override global? | **No.** *"The entire RCD block is gated on `m_raw_params.demosaic == RawDemosaic::RCD`, so every other `--demosaic=` value follows the exact pre-Phase-12.15 code path and produces bit-identical output."* Verified by three MD5 bit-identity contracts against Phase 12.14 baselines. | AGENTS.md:2944–2953, 2838–2857 |

**Conclusion (MEASURED): the 30–44% deficit was measured with DHT, months before the bilinear-override bug existed, and the bug is flag-gated so it could not have contaminated it.** The two failures are independent. **The RCD bug does not explain the softness — but the softness is still not an argument against RAW-native, for a different and better reason.**

### The corpus's own control shows the deficit is mostly cosmetic

`PHASE12_11.md §"What the user perceives as super resolution"`:

> *"the `substrate_TL` ROI (flat foam, no real detail) shows the 8.6 stack has **2.4× more top-5% gradient** than the ARW stack. **There is no real signal there — it's noise being boosted by the sharpening passes.** 'More of everything' is the hallmark signature of high-pass / unsharp-mask amplification."*

**This is a proper control and it is decisive.** A flat ROI with no detail cannot contain 2.4× more *information*; the extra gradient is amplified noise. The document's own headline states: *"No super resolution... It is conventional unsharp-mask-style high-frequency boost... The result looks better than the raw sensor data because Lightroom does an excellent job at making sharp-looking images, not because more real information was recovered."*

**I am correcting my original fact #8.** The correct statement is: *the ARW path produced a less-sharpened, not a less-detailed, image.* Framing it as an information deficit was my error and overstates the case against RAW-native.

### Four confounds, per the corpus, in impact order

| Factor | What it is | Is it an information loss? |
|---|---|---|
| 1. Demosaic (DHT vs LR proprietary) | LR recovers **~1.4–1.6× more Sobel top-5%**; DHT is a pure interpolator with no edge enhancement | **Partly yes** — this is the one real component, and it is fixable by a better demosaic (see below) |
| 2. LR bakes demosaic-stage sharpening into TIFF exports even at Sharpening=0 and Output Sharpening=None | not user-controllable | **No** — cosmetic |
| 3. Compose picks winners from an already-sharpened set on the TIFF path | compose adds no sharpness either way | **No** — inherited from (1)+(2) |
| 4. **LR treats the two outputs differently on import**: LinearRaw DNG gets one pass of raw-default sharpening (Amount=40/R=1.0/D=25); the rendered TIFF *"was already sharpened by LR twice"* | *"two-and-a-half passes worth of sharpening accumulated"* | **No — and this makes the comparison non-apples-to-apples at the measurement level** |

Factors 2–4 are all sharpening. Only Factor 1 is real, and the corpus estimates it at 1.4–1.6× Sobel top-5%, not the headline 0.638.

### Demosaic algorithms: what was available, what ran, what was ranked

| Algorithm | Available in the fork? | Actually exercised? | Measured quality? |
|---|---|---|---|
| **AHD** | Yes — default when `lr-match=off` (AGENTS.md:598) | Yes (legacy/bit-identical path) | **Never measured against DHT** |
| **LINEAR** (bilinear) | Yes | Only as the accidental substrate of the broken RCD path | No |
| **DHT** | Yes — default for raw→tone-curved/DNG (AGENTS.md:598) | Yes, extensively; it is the ARW path | **Only vs Lightroom** (`PHASE12_11`): 0.703 Sobel-mean, 0.638 Sobel-top5%, 0.559 lap-var |
| **RCD** | Ported in 12.15 (`demosaic_rcd.{cc,hh}`), clean-room, ~250 LOC, `<math.h>` only | Yes, but on bilinear-derived synth-Bayer | **+1.30% / +2.26%** — invalid as an RCD measurement |
| **AMaZE** | **Not available.** Proposed as Phase 12.17 (`+5% over RCD`, 3 d) | No | No |
| **ARI (Monno 2017)** | Not available. Proposed Phase 13b (`+0.5 dB over AMaZE`) | No | No |

**There is no measured quality ranking between any two demosaic algorithms anywhere in the corpus.** `PHASE12_12.md:66` states DHT is *"20–30% worse than RCD/AMaZE"* — **ARGUED from RawTherapee documentation, never measured.** AGENTS.md:598's *"DHT preserves more high-frequency detail on low-ISO macros"* is **ASSERTED**.

### Net verdict for the new architecture

**RAW-native is vindicated, with one genuine obligation.** The 30–44% figure conflates a ~1.4–1.6× demosaic gap (real, and addressable with RCD/AMaZE/ARI or a joint Bayer-domain reconstruction) with two-and-a-half accumulated passes of Lightroom unsharp masking (cosmetic, and something a pixel-truthful stacker should *decline* to imitate by default). The obligation is: **ship a genuinely competitive demosaic, and validate it on a flat control ROI** — because the corpus has proven that Sobel on textured ROIs cannot distinguish recovered detail from amplified noise. **Any demosaic or sharpness metric in the new system must be paired with a no-signal flat-ROI control.** That single methodological rule is worth more than the demosaic choice itself.

---

## FU1.3 — Fabricated citations, and the full anatomy of the NLM-Multi inversion

### The fabricated citations

| # | Citation as it appears | Where it appears | What it claimed | Load-bearing? |
|---|---|---|---|---|
| 1 | **"Liu, CFS-FocusNet, 2024"** | `PHASE11_RESEARCH.md` algorithms thread §3, quoted into `PHASE12_RESEARCH.md:311, 712, 1018` | A CNN focus-stacking network | **No.** Quarantined: *"No matching ArXiv ID, no Google Scholar hit. Likely confabulated."* Listed in the Phase 12 reject list. |
| 2 | **"Yang, FocusOnMe, 2023"** | same | A multi-focus fusion network | **No.** *"Does not exist. The agent appears to have hallucinated a name from 'FocusOn' / 'Me-focus' papers."* Rejected. |
| 3 | **"MaCFNet 2024 for MFIF"** | same | Multi-focus image fusion network | **No.** Real paper (Tan et al. 2024) but it is **optic-disc segmentation in retinal images**. Rejected as "wrong domain". |

`PHASE12_RESEARCH.md:315`: *"These three should not appear anywhere in Phase 12 implementation work. The rest of the algorithms thread is solid."* **Nothing was built on any of the three.** The corpus caught and quarantined them before implementation. Credit where due.

### ⚠️ But a FOURTH bad citation WAS load-bearing — flag this loudly

**"Lee & Tai 2016"** was not merely miscited; it was **selected as Top-10 pick #7** and scheduled for Phase 13 implementation before anyone checked it existed.

| Fact | Detail | Cite |
|---|---|---|
| Bibliography entry | Wrong author initial **and** wrong title. Claimed title *"...image"* **"does not exist in DBLP or any author bibliography"** | `PROBE7_LEE_TAI.md:23, 102` |
| Real paper | *Robust All-in-Focus Super-Resolution for Focal Stack Photography* — 18 lifetime citations, **0 influential** | `PROBE7_LEE_TAI.md` |
| Claimed "Matlab implementation available" | **False** — zero public code found | `PROBE7_LEE_TAI.md` |
| Probe author's own reading | *"a private/lost intermediate document **or a hallucination**"* | `PROBE7_LEE_TAI.md:105` |
| Consequence | The plan had to be **"re-anchored from Lee & Tai 2016"** to Lin et al. 2025 *Learning Lens Blur Fields* | `PHASE12_RESEARCH.md:~322` |

**This is the failure mode that matters:** the three obvious fabrications were caught by name-checking, but Lee & Tai passed review because the *author* was real, and it reached a scheduled implementation slot. **Rule for the new project: every citation that reaches a design decision must be resolved to a DOI/arXiv ID and a retrievable artifact before the decision is made, not after.** The corpus's own probe-before-commit discipline is what caught it — one probe, ~a day, killed a scheduled multi-week work item.

**Nothing currently standing in the corpus rests on a fabricated source**, as far as I can establish. The three hallucinations are in reject lists; Lee & Tai was re-anchored to a real 2025 paper (which I have **not** independently verified — treat `Lin et al. 2025, Learning Lens Blur Fields` as UNVERIFIED until checked).

### Full anatomy of the NLM-Multi inversion

Source: `research\NLM_MULTI_OBSOLESCENCE.md` (dated "2026, Round 8, Phase 12.5").

**Timeline**

| Stage | Event | Measured state |
|---|---|---|
| **Phase 10.1** | `--cross-frame-denoise=light` added as the "Tier 2.2 ML-free denoise lever". Measured **1.38× σ reduction** in the P9.1 confidence-blend zone against baseline artifact `out2/stack_phase8_2_compose.tif`. Shipped **default-OFF** for compute reasons (+41 s). | Baseline σ = **689 codes** at the reference ROI |
| **Phase 12.1** | Noise model added | baseline moves |
| **Phase 12.5** | **The decisive change.** Made the depthmap chain **default-ON**, which activated P8.2 noise-floor substitution + P9.1 low-confidence soft blend at default flags — i.e. **cross-frame arithmetic mean colour now already occupies the same ~80% override mask NLM-Multi was written to clean up.** | chain-off σ = 265; chain-on σ = **226 codes** — 2.6× and **3.0× cleaner than the Phase 10.1 baseline** |
| **Phase 12.5, Round 8** | Deliberate re-measurement probe (`out2/probe_p125_nlm.py`) | NLM on: **358 codes (+35%)** chain-off; **334 codes (+48%)** chain-on |

**Elapsed:** Phase 10.1 → Phase 12.5. Interleaved: 12.1 noise model, DA2, and the chain default flip.

**Was it noticed at the time? No — only in retrospect, and only because of a deliberate audit.** The document is framed as a probe re-measuring an existing feature, not as a bug report; the sibling `PHASE12_FRESHNESS_SCAN.md` is the systematic "are old conclusions still true?" pass. **No automated signal fired.** Nothing in the build or test system compared a feature's measured benefit against its original claim.

**The three mechanisms, per §Root cause** (each independently instructive):

1. **The feature's premise was invalidated, not its implementation.** NLM substitutes pixels *inside* the P8.2+P9.1 union override mask (~80% of the image, measured: 80.9% NLM coverage, 65.7% P8.2 engagement, 69.9% P9.1 engagement — `out2/qa_p125_nlm_light.log`). In Phase 10.1 that zone held the noisy winner-copy. After 12.5 it holds a 33-frame arithmetic mean. *"Arithmetic mean over 33 frames gives ~5.7× shot-noise reduction; NLM-Multi's T=5 patch average gives at most ~2.2×. NLM cannot improve over what's already there."*
2. **Quantisation tax.** `fastNlMeansDenoisingColoredMulti` is CV_8UC3-only ⇒ ÷257 → denoise → ×257. *"Quantisation adds ~128 codes of noise per channel."* At a 226-code baseline this alone is fatal.
3. **Signal mismatch.** Inside the override mask the signal *is* the arithmetic mean — no per-pixel high-frequency content for NLM to match patches on. It smooths what is already smooth and *"introduc[es] patch-correlated spatial noise"*, plus double-edge artefacts at the mask boundary.

**Mitigating fact I under-reported originally:** the flag was **default-OFF throughout**, so **shipped output never regressed**. This was a *latent* inversion in an opt-in feature. That makes it a *better* argument for the harness, not a worse one: **a regression suite that only exercises default flags would never have caught it.**

### Harness requirements this specific failure implies

| # | Requirement | Because |
|---|---|---|
| H1 | **Every measured claim is stored as a record**: `{feature, flag-set, metric, ROI, value, baseline-artifact-hash, pipeline-revision, date}`. A claim without a named baseline artifact is not a claim. | Phase 10.1's 1.38× was true against `stack_phase8_2_compose.tif` and meaningless without it. |
| H2 | **Re-measure every stored claim on every release**, not just the default configuration. Fail the build when a stored benefit **changes sign**. | The inversion lived in a default-OFF flag. Default-only CI is blind to it. |
| H3 | **Flag-combination coverage, not just flag coverage.** The 12.5 chain flip changed what a *different* feature was operating on. | +35% (chain off) vs +48% (chain on) — the interaction is the effect. |
| H4 | **Score features on marginal contribution against the current baseline, and auto-retire negatives.** A plugin whose marginal benefit goes negative should be reported, not silently retained. | *"The cleaner the baseline gets, the worse NLM-Multi looks."* |
| H5 | **Track and gate precision loss at plugin boundaries.** | The ~128-code uint8 quantisation tax was invisible at a 689-code baseline and dominant at 226. In a plugin ecosystem, format conversions at boundaries are the default hazard. |
| H6 | **Pair every sharpness metric with a no-signal flat-ROI control**, and every noise metric with a temporal (not spatial) estimator. | FU1.2 (2.4× gradient in featureless foam) and FU1.1 (the structure-floored 1.10×) are the same class of error: a metric measuring something other than what it is named for. |
| H7 | **Record marginal wall-time and peak RSS alongside every quality number, with a budget gate.** | 81 s → 456 s and 6 GB → 23 GB by accretion, unnoticed. |

**H6 is the one I would emphasise.** Both of the corpus's two most consequential mis-readings — the "correlated noise" cap and the "ARW is 30–44% softer" deficit — were **metric-validity failures, not measurement failures**. The numbers were computed correctly. They just did not measure the quantity in their own column heading. A harness that enforces controls would have caught both.
