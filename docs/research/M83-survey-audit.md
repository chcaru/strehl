# M83 — Audit of the six foundational survey reports

**Status: LITERATURE AND SOURCE AUDIT.** This milestone audits the eighteen
architecturally load-bearing claims frozen in
`experiments/M83-survey-audit/PREREGISTRATION.md`. The sample was committed as
`f1637de` before any external source was checked. M83 does not edit the six
surveys, the ledger, the project rules, or code.

**Tagging convention.** A tag at the start of a paragraph or table cell governs
every factual claim in that paragraph or cell. **MEASURED** means read and
quoted at a primary paper, specification, licence, API/vendor document,
first-party source tree, or project measurement record. **DERIVED** means the
arithmetic or logical consequence is shown. **ARGUED** is an interpretation.
Evidence depth is a separate axis:
**VERIFIED-AT-PRIMARY-SOURCE**, **READ-AT-PROJECT-SOURCE**, or
**TAKEN-FROM-SECONDARY**.

---

## 0. VERDICT

> **VERDICT**
>
> **DERIVED.** At the exact strength frozen before source review, **5/18
> (27.8%) survive unchanged**. Twelve are **OVERSTATED**, one is **REFUTED**,
> five are **VERIFIED**, and none is unverified. The preregistered adverse
> fraction, `(OVERSTATED + REFUTED) / adjudicated`, is therefore **13/18 =
> 72.2%**. The strict `OVERSTATED / adjudicated` fraction is **12/18 = 66.7%**.
>
> **ARGUED.** This is not a random-sample base rate for every sentence in the
> corpus. It is the **architectural-exposure overstatement rate** among the
> three most load-bearing claims in each report. Calling 13/18 a general
> corpus-wide base rate would repeat the very scope error this audit finds.
>
> **ARGUED.** The architecture survives much better than the quotations:
> **17/18 claims retain some narrower support** and only C2 is wholly refuted.
> The result is not “the architecture is 72.2% wrong.” It is: **72.2% of the
> survey propositions carrying the architecture were stated more strongly
> than their primary evidence permits.**

| Report | Raw verdicts | Strict overstatement | Adverse fraction | Survives unchanged |
| --- | --- | ---: | ---: | ---: |
| A — prior corpus | **MEASURED:** 1 VERIFIED, 2 OVERSTATED | **DERIVED:** 2/3 | **DERIVED:** 2/3 | **DERIVED:** 1/3 |
| B — algorithms/SOTA | **MEASURED:** 3 OVERSTATED | **DERIVED:** 3/3 | **DERIVED:** 3/3 | **DERIVED:** 0/3 |
| C — landscape | **MEASURED:** 1 VERIFIED, 1 OVERSTATED, 1 REFUTED | **DERIVED:** 1/3 | **DERIVED:** 2/3 | **DERIVED:** 1/3 |
| D — Rust/hardware | **MEASURED:** 1 VERIFIED, 2 OVERSTATED | **DERIVED:** 2/3 | **DERIVED:** 2/3 | **DERIVED:** 1/3 |
| E — plugin architecture | **MEASURED:** 1 VERIFIED, 2 OVERSTATED | **DERIVED:** 2/3 | **DERIVED:** 2/3 | **DERIVED:** 1/3 |
| F — camera/lens optics | **MEASURED:** 1 VERIFIED, 2 OVERSTATED | **DERIVED:** 2/3 | **DERIVED:** 2/3 | **DERIVED:** 1/3 |
| **Pooled M83** | **MEASURED:** 5 VERIFIED, 12 OVERSTATED, 1 REFUTED, 0 UNVERIFIABLE | **DERIVED:** **12/18 = 66.7%** | **DERIVED:** **13/18 = 72.2%** | **DERIVED:** **5/18 = 27.8%** |

**DERIVED.** M79's claim 1 and claim 3 were OVERSTATED while M79's claim 2 was
confirmed only in a narrowed form, so M79's comparison remains **2/3 adverse**.
M83 does not show that G-edof was an outlier: five of the six newly audited
reports are also 2/3 adverse (C through one overstatement and one outright
refutation), and B is 3/3 adverse.

**MEASURED; READ-AT-PROJECT-SOURCE.** M79 also records the defects named in
question 201: one supposed independent negative was configuration-specific,
the survey missed Schechner, Kiryati and Basri 1998 (DOI
`10.1109/ICCV.1998.710848`), and its three routes shared three assumptions.
M83 uses M79's 2/3 only as a comparison, not as one of the eighteen
observations.

**ARGUED.** Equal allocation of three claims per report was the right unit for
question 201's operational purpose because it prevents the longest report from
dominating and measures exposure at architectural decision points. It is the
wrong unit for inferential language such as “the base rate in all survey
prose.” There was no random sampling frame, claims differ in breadth, and
reports were deliberately sampled at their highest-consequence points. No
sampling confidence interval is reported because one would imply randomness
that does not exist.

---

## 1. Method and evidence boundary

### 1.1 Frozen sample and adjudication

**MEASURED; READ-AT-PROJECT-SOURCE.** The preregistration identifies the exact
quotation, downstream dependency, and adverse condition for A1–F3. Git commit
`f1637de` contains that file alone. External papers, vendor pages, licences, and
repositories were not consulted until after the commit. The frozen file was
not amended during adjudication.

**DERIVED.** The headline fraction follows the preregistered rule:

```text
adverse fraction =
    (OVERSTATED + REFUTED)
    ---------------------------------------------
    (VERIFIED + OVERSTATED + REFUTED)
```

**ARGUED.** A factual verdict answers whether the proposition survives at the
scope used downstream. Evidence depth answers how close the audit came to the
thing itself. For example, D3 has primary support for the capabilities of wgpu
and CUDA but no primary measurement for the claimed 1.1× relationship; those
are not collapsed into one label.

### 1.2 Primary sources read

| Claim | Source actually read | Evidence boundary |
| --- | --- | --- |
| A1–A3 | `C:\dev\macro` at commit `864ff08862414682e75d58245a1e7f1d25cf3315`: measurement scripts, implementation, design notes, and its ledger | **MEASURED; READ-AT-PROJECT-SOURCE.** These claims describe that project, so its first-party records are the primary source. |
| B1 | Surh, Jeon, Im and Kweon, **“Noise Robust Depth from Focus Using a Ring Difference Filter,”** CVPR 2017, full paper, especially §3.2 and Table 1 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Full paper and experiment configuration read. |
| B2 | Monod, Delon and Veit, **“An Analysis and Implementation of the HDR+ Burst Denoising Method,”** IPOL 2021, DOI `10.5201/ipol.2021.336`, especially §4.2 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Full paper and equations read. |
| B3 | Wronski et al., **“Handheld Multi-Frame Super-Resolution,”** *ACM TOG* 38(4), 2019, DOI `10.1145/3306346.3323024`, especially §6 and Table 1 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Full paper and supplement read. |
| C1 | Zerene Stacker's official RAW workflow; Helicon Focus's official RAW-in/DNG-out documentation; publisher record for Yang and Chen 2015 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** for the two products. **TAKEN-FROM-SECONDARY** for the inaccessible Yang paper body; only its bibliographic existence is used. |
| C2 | `PetteriAimonen/focus-stack` commit `0cd289e224fe24aead5b146faeaa46950775f346`, especially `src/task_depthmap.cc` and save-step outputs | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** First-party implementation source read; no code was copied. |
| C3 | crates.io metadata for `rawler` 0.7.2 and GNU LGPL version 2.1, especially §6 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Immutable package metadata and full licence text read. This report is not legal advice. |
| D1 | NVIDIA CUDA Math API, `__half` structure and binary16 representation | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Vendor API documentation read; the sensor-code spacing is derived below. |
| D2 | D's own roofline arithmetic, compared with the implementation shape and later project memory records | **DERIVED; TAKEN-FROM-SECONDARY** for time neutrality. No paired gather/materialise benchmark exists. |
| D3 | Official wgpu backend documentation and NVIDIA CUDA programming/API documentation | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** for capabilities; **TAKEN-FROM-SECONDARY** for 1.1×. |
| E1 | WebAssembly Component Model Canonical ABI; Wasmtime support table at `e6b33de5139d915a48127fc78b790e2d306cf896`; official `wasi-webgpu` README | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Specification and first-party status records read. |
| E2 | Shi, Zhang and Cui, **“A Programming Paradigm for Spatiotemporal Composability,”** full 88-page Cordis paper, especially Definition 39 and Theorem 73 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Full paper read, not only E's summary. |
| E3 | `M52-gate-cluster-verified.md`, its artifacts, and the shipped calibration source | **MEASURED; READ-AT-PROJECT-SOURCE.** The later project experiment directly exercises the claimed seam. |
| F1 | `M25-simulator-measured.md`, `M48-read-noise-measured.md`, and `M61-ptc-high-iso-measured.md` | **MEASURED; READ-AT-PROJECT-SOURCE.** The later project measurements test the camera model directly. |
| F2 | Edmund Optics, **“System Throughput, f/#, and Numerical Aperture”**; paraxial derivation; `M5-diffraction-measured.md` | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** for the symmetric working-f-number case; **TAKEN-FROM-SECONDARY** in F's chain but independently **DERIVED** for the general pupil-ratio equation; **READ-AT-PROJECT-SOURCE** for this rig. |
| F3 | `M3-alignment-measured.md` and `M12-shrinkage-measured.md` | **MEASURED; READ-AT-PROJECT-SOURCE.** They directly test the warp and metadata propositions. |

**MEASURED.** All eighteen frozen claims were adjudicated. No claim is
UNVERIFIABLE. The full body of Yang and Chen 2015 could not be legitimately
obtained, so no body-level claim is attributed to it; its title, authors, date,
venue, DOI, and existence come from the publisher/Crossref record only.

**MEASURED.** No third-party implementation code was copied into the
repository. `focus-stack` was read only to establish observable first-party
behaviour. Papers, specifications, licence text, API documentation, and
bibliographic metadata were used as evidence.

### 1.3 Source locators

**MEASURED.** Stable identifiers for papers appear in §1.2 and §1.4. The
non-paper primary sources are:

- Zerene's [official FAQ](https://zerenesystems.com/cms/stacker/docs/faqlist)
  and Helicon's [RAW-in/DNG-out
  documentation](https://www.heliconsoft.com/raw-in-dng-out/);
- [`focus-stack` at the audited
  commit](https://github.com/PetteriAimonen/focus-stack/tree/0cd289e224fe24aead5b146faeaa46950775f346),
  [`rawler` 0.7.2](https://crates.io/crates/rawler/0.7.2), and the
  [LGPL-2.1 text](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html);
- NVIDIA's [`__half` API
  documentation](https://docs.nvidia.com/cuda/cuda-math-api/cuda_math_api/struct____half.html),
  [CUDA Programming
  Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/), and
  [`wgpu` 30.0.1 documentation](https://docs.rs/wgpu/30.0.1/wgpu/);
- the Component Model [Canonical
  ABI](https://github.com/WebAssembly/component-model/blob/main/design/mvp/CanonicalABI.md),
  Wasmtime's [pinned proposal support
  table](https://github.com/bytecodealliance/wasmtime/blob/e6b33de5139d915a48127fc78b790e2d306cf896/docs/stability-wasm-proposals.md),
  the official [`wasi-webgpu`
  repository](https://github.com/WebAssembly/wasi-webgpu), and the Cordis
  [paper source](https://github.com/cordiverse/paper/blob/main/paper.pdf);
- Edmund Optics' [working-f-number
  page](https://www.edmundoptics.com/knowledge-center/application-notes/imaging/lens-iris-aperture-setting/).

### 1.4 Nearest-prior-art search and stopping boundary

**MEASURED.** Each report received three mechanism-specific query families in
Crossref and OpenAlex, followed by backward-reference and available
forward-citation checks. The query families were:

| Report | Query families |
| --- | --- |
| A | **MEASURED:** `focus-measure maximisation noise all-in-focus`; `noise-robust selective fusion limited depth of field`; `multi-focus noisy images criterion function` |
| B | **MEASURED:** `depth from focus Laplacian noise robustness`; `burst raw CFA joint demosaicing multiframe`; `defocus mismatch Wiener reference focus fusion` |
| C | **MEASURED:** `raw Bayer multi-focus fusion`; `Bayer-domain focus stacking`; `focus stack confidence uncertainty map` |
| D | **MEASURED:** `binary16 14-bit sensor-code precision`; `gather aligned frame on demand GPU materialise`; `wgpu CUDA image-pipeline benchmark` |
| E | **MEASURED:** `WebAssembly canonical ABI borrowed buffer zero copy`; `Wasmtime shared-everything threads memory-control WebGPU`; `plugin registry confluence ordered chain` |
| F | **MEASURED:** `macro effective f-number pupil magnification`; `focus breathing similarity transform internal focus`; `FocusPosition2 focus-bracket rail classifier` |

**MEASURED.** The search stopped after two successive query/reference passes
produced no closer source. It found three material omissions:

1. **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Pertuz, Puig, Garcia and Fusiello,
   **“Generation of All-in-Focus Images by Noise-Robust Selective Fusion of
   Limited Depth-of-Field Images,”** *IEEE TIP* 22(3):1242–1251, 2013, DOI
   `10.1109/TIP.2012.2231087`. The full paper says that, in noise,
   maximising a focus measure “will also add noise to the final result” and
   builds a selective average for unreliable regions. It is nearer to A1 and
   to B2's proposed focus/noise adaptation than the sources those reports use.
2. **MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Farsiu, Elad and Milanfar,
   **“Multiframe Demosaicing and Super-Resolution of Color Images,”** *IEEE
   TIP* 15(1):141–159, 2006, DOI `10.1109/TIP.2005.860336`. The full paper
   calls super-resolution on pre-demosaiced images “suboptimal” and evaluates
   a unified reconstruction from raw CFA frames. Wronski cites it; B does not.
3. **MEASURED; bibliographic record only.** Yang and Chen,
   **“Multi-Focus Raw Bayer Pattern Image Fusion for Single-Chip Camera,”**
   *Sensing and Imaging* 16, article 3, 2015, DOI
   `10.1007/s11220-015-0105-4`. Its existence is enough to defeat the adjacent
   “untested by anyone” rhetoric and makes it mandatory prior art for C's
   landscape. Its inaccessible body does not prove that a shipping product
   existed or establish its quality.

**ARGUED.** No comparably close omitted work was found for D, E, or F inside
the stated boundary. This is a bounded search result, not proof that no such
work exists. C2's missed `focus-stack` implementation is adjacent product
prior art rather than literature.

---

## 2. A — `A-prior-corpus.md`

| Claim | Frozen quotation | Primary source consulted | Classification | What the source actually supports |
| --- | --- | --- | --- | --- |
| A1 | “`max\|c\|` selection plus winner-copy colour means flat regions receive one random frame's noise, measured at **1.82× worse than a single source frame** in highlights”; therefore “**Make the merge an estimator, not a selector**” | `probe_noise_tonal.py`; `poc_nlmeans_multi.py`; `task_merge.cc`; Pertuz et al. 2013 | **OVERSTATED; READ-AT-PROJECT-SOURCE**, with the qualitative mechanism **VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED.** Selector/maximisation fusion is noise-sensitive. The named 1.82× result is not a controlled measurement of that mechanism and must not be used as its magnitude. |
| A2 | “**The 1.10× is a measurement of scene structure, not of noise correlation**” | `poc_nlmeans_multi.py`, `PHASE9_10_DELIVERABLE.md`, and the input/output domains | **VERIFIED; READ-AT-PROJECT-SOURCE** | **MEASURED.** The script measures spatial variance after rendering/downsampling/quantisation. It never estimates temporal covariance, so it cannot establish frame-correlated noise. |
| A3 | “the fork went **81 s → 456 s** and **6 GB → 23 GB** by accretion, with no gate” | Prior ledger timing rows; `PHASE10_DESIGN.md`; workload/flag records | **OVERSTATED; READ-AT-PROJECT-SOURCE** | **MEASURED.** Feature accretion plausibly raised cost, but the quoted endpoints are different workloads and the 23 GB value is a design estimate, not the observed peak of the named run. |

### 2.1 A1 — the mechanism survives; the 1.82× does not

**MEASURED; READ-AT-PROJECT-SOURCE.** `probe_noise_tonal.py` computes
`src_patch.std(axis=0).mean(...)`, a temporal per-pixel statistic over five
middle frames, but obtains the claimed output ratio from
`sigma_out_spatial / sigma_single_spatial`, two spatial patch standard
deviations. It does not remove scene structure, does not use repeated
same-focus captures, and despite its docstring does not warp the input TIFFs.
The numerator and denominator therefore cannot isolate noise selected by the
merge.

**MEASURED; READ-AT-PROJECT-SOURCE.** The implementation is also not one
unqualified hard selector. `task_merge.cc` contains max-centred exponential
weights of the form `exp(beta * (m_k - M) / M)`, optional alignment weights,
fallback paths, and later compose logic. Calling the whole output a direct
measurement of `max-absolute-coefficient` selection attributes all intervening
processing to one mechanism.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Pertuz et al. supply the missing
general evidence: *“in the presence of noise, the maximization of the focus
measure will also add noise to the final result.”* Their remedy averages over
the focus sequence where the focus signal is unreliable. That supports
“selection needs noise-aware regularisation,” not the prior project's 1.82× as
a portable constant.

### 2.2 A2 — the retraction is correct

**MEASURED; READ-AT-PROJECT-SOURCE.** The 1.10× script first forms an averaged
render, then computes variance across pixels inside an ROI. Scene texture,
resampling, rendering, and 8-bit quantisation remain in the statistic. No term
computes covariance between repeated captures of the same signal. A's
retraction and project rule 10 are therefore confirmed.

### 2.3 A3 — incomparable endpoints

**MEASURED; READ-AT-PROJECT-SOURCE.** The approximately 81 s row is 33
pre-converted 8-bit frames in bundled v1.5. The 456 s row is a 53-frame
coffee-bean subset with different flags and eight threads. A later
same-33-frame marker row is 426 s under yet another feature/input path. These
records show that the project became expensive; they do not form a controlled
81→456 causal comparison.

**MEASURED; READ-AT-PROJECT-SOURCE.** `PHASE10_DESIGN.md` derives the 23 GB
number as approximately 21 GB retained by compose in an HDR-on worst case plus
approximately 2 GB of NLM scratch. It is not a recorded peak-RSS measurement
for the 33-frame baseline. The supported correction is “unratcheted feature
growth created large time and memory risks,” with each cost delta measured on
a common workload before attribution.

---

## 3. B — `B-algorithms-sota.md`

| Claim | Frozen quotation | Primary source consulted | Classification | What the source actually supports |
| --- | --- | --- | --- | --- |
| B1 | “**The Laplacian's winner margin and curvature both go negative at σ ≥ 0.01**”; therefore any variance-of-Laplacian or SML pipeline on real RAW is “actively anti-correlated with focus” | Surh et al. 2017, §3.2 and Table 1 | **OVERSTATED; VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED.** One Laplacian configuration loses Surh's two confidence statistics on seven synthetic light-field scenes with 30 synthetic depth labels and signal-dependent Gaussian noise. That is not all Laplacian/SML variants and not real RAW. |
| B2 | HDR+ “**already does the right thing on defocus mismatch**”; replace fixed `T₀` with a per-band/per-tile focus-selected reference and it becomes a denoising focus stacker | Monod et al. 2021, §4.2, Eqs. 10–11 | **OVERSTATED; VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED.** HDR+ preserves the fixed reference's blur state: it rejects blur absent from a sharp reference and also rejects sharp detail absent from a blurry reference. Per-band reference substitution is an unevaluated project hypothesis. |
| B3 | Wronski et al. bypass demosaicing and are “**over 3 dB better than the next best one, DeepJoint, on both datasets**” | Wronski et al. 2019, §6.1, Table 1, Figs. 14/16; Farsiu et al. 2006 | **OVERSTATED; VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED.** Direct multiframe CFA reconstruction is real and well supported. The >3 dB table compares a 15-frame method with single-frame demosaicers, not direct CFA with merge-then-demosaic. |

### 3.1 B1 — Surh's result is synthetic and configuration-specific

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Surh Table 1 reports Laplacian Winner
Margin `0.137, 0.002, -0.228, -0.212` and Curvature
`0.881, -0.287, -2.354, -2.848` at noise σ `0, 0.005, 0.01, 0.02`.
The paper immediately specifies signal-dependent Gaussian noise, seven
light-field datasets, depth-dependent blur, and 30 equally spaced quantised
depth labels.

**ARGUED; VERIFIED-AT-PRIMARY-SOURCE.** Negative values in those two confidence
statistics show failure for the tested Laplacian response under that synthetic
construction. Winner Margin and Curvature are not correlation coefficients or
focus-error rates, so a negative value is not itself “anti-correlated with
focus.” The result does not establish universal inversion for modified
Laplacian, SML, windowed variance, differently normalised operators, or a real
sensor pipeline. `SYNTHESIS.md` fact 6 and risk 2 need the configuration
attached. M11 and M13 independently preserve the Tenengrad choice on real RAW.

### 3.2 B2 — fixed-reference blur rejection is not focus fusion

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Monod et al. explicitly evaluate both
directions. If `T₀` is sharp, blurry alternate content is discarded because it
does not match. If `T₀` is blurry and `Tz` sharp, the sharp content is also
discarded. Their conclusion is exact: *“the Wiener filter does not introduce
additional blur from other images, but it does not remove blur either.”*

**ARGUED.** Choosing a different reference independently by tile and frequency
band changes the estimator and creates unresolved consistency, seam,
occlusion, and registration questions. It may be a good design; Monod is not
an experiment on it. Pertuz et al.'s noise-robust selective fusion is the
closer prior mechanism and should frame such a design.

### 3.3 B3 — the >3 dB comparator is wrong

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Wronski §6.1 creates synthetic
15-offset bursts and says it compares the full algorithm against “direct
single frame demosaicing techniques.” Table 1 contains ADMM, VNG, FlexISP,
DeepJoint, and “Ours”; DeepJoint scores 39.67/37.58 dB and the 15-frame method
42.86/41.26 dB. The >3 dB is therefore multiframe versus single-frame.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Merge-then-demosaic appears in visual
figures and an end-to-end/user comparison, not as the paired >3 dB ablation.
The paper supports a direct CFA burst reconstruction that dispenses with an
explicit demosaic step. It does not price that choice independently of having
fourteen additional observations.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Farsiu et al. had already stated that
using pre-demosaiced images for multiframe reconstruction is “suboptimal” and
evaluated a unified raw-CFA reconstruction on synthetic and real sequences.
It is the nearest omitted antecedent. Neither paper is a direct focus-stack
benchmark, so the >3 dB number must be removed from the “never demosaic”
decision until that paired experiment exists.

---

## 4. C — `C-landscape.md`

| Claim | Frozen quotation | Primary source consulted | Classification | What the source actually supports |
| --- | --- | --- | --- | --- |
| C1 | “Is any tool RAW-native / Bayer-domain? **No. Not one.**” and “**No shipping tool has tried it**” | Official Zerene and Helicon workflows; Yang and Chen bibliographic record | **OVERSTATED; VERIFIED-AT-PRIMARY-SOURCE** for named products | **MEASURED.** Zerene develops RAW before stacking; Helicon invokes Adobe DNG Converter before alignment. Those two product records cannot prove a universal negative. The supportable claim is bounded to the surveyed products and date. |
| C2 | “**The central finding: no tool emits a confidence map. Nothing even close**” | `PetteriAimonen/focus-stack` at commit `0cd289e...` | **REFUTED; VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED.** The public stacker fits per-pixel Gaussian focus profiles and can emit Gaussian mean, deviation, and amplitude maps. They are not Strehl's calibrated confidence vector, but they are “close.” |
| C3 | “**LGPL-2.1 is not fatal, and for a project like ours it is close to free**”; “**Verdict: use `rawler`**” | crates.io `rawler` 0.7.2 metadata; LGPL-2.1 §6 | **VERIFIED at the architectural decision; VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED.** `rawler` is LGPL-2.1 and can remain the decoder. Distribution requires notices, licence/source access, modification/reverse-engineering permission for debugging, and a relinking path/materials. “Close to free” must not erase release work. |

### 4.1 C1 — two checked products do not establish “not one”

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Zerene's official workflow instructs
users to convert RAW files before stacking and says its own alignment needs are
“fundamentally incompatible” with the one-value-per-photosite Bayer layout.
Helicon's official RAW-in/DNG-out description says source data *“should be
converted ... to so called interpolated RGB image”* and that Helicon uses
**Adobe DNG Converter** to perform that demosaic before alignment. Those
records verify the report's characterization of Zerene and Helicon.

**ARGUED.** A finite product survey can support “none among the surveyed
shipping tools as of the survey date.” It cannot support an unbounded “No. Not
one.” Yang and Chen's 2015 raw-Bayer multifocus paper is mandatory adjacent
prior art, but its bibliographic existence is not evidence that it shipped as
a product. The product claim narrows; it is not reversed.

### 4.2 C2 — a direct public counterexample

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** At the pinned `focus-stack` commit,
`src/task_depthmap.cc` fits a Gaussian focus profile per pixel. With
`--save-steps`, first-party source writes `gauss_mean.png`, `gauss_dev.png`,
and `gauss_amp.png`. Deviation and amplitude are uncertainty- and
reliability-adjacent diagnostic surfaces.

**ARGUED.** These are not a calibrated predicted-sigma map, `n_eff`, or
Strehl's intended through-focus confidence vector. The defensible
differentiation is therefore: **no surveyed commercial stacker exposes a
calibrated, actionable uncertainty product comparable to Strehl's planned
vector.** “Nothing even close” is false.

### 4.3 C3 — viable dependency, nonzero release obligations

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** crates.io declares `rawler` 0.7.2 as
`LGPL-2.1`. LGPL-2.1 §6 permits distributing a work using the library under
*“terms of your choice,”* but requires, among other conditions, materials
*“so that the user can modify the Library and then relink”* the executable,
plus notice, the licence text, library source availability, and
modification/reverse-engineering permission for debugging modifications.

**ARGUED.** Open publication of ordinary Rust source is not by itself a
universal substitute for every binary-distribution obligation. The
architectural verdict “use `rawler`” survives because the duties are
manageable and the current project rules already describe dynamic-link or
reproducible-relink paths. Release packaging must implement and verify that
process; this paragraph is an engineering audit, not legal advice.

---

## 5. D — `D-rust-and-hardware.md`

| Claim | Frozen quotation | Primary source consulted | Classification | What the source actually supports |
| --- | --- | --- | --- | --- |
| D1 | `f16` has a quantisation step of roughly **8 LSB** near full-scale 14-bit data; “**Keep CFA/linear-scene-referred data in u16 (storage) and f32 (arithmetic)**” | NVIDIA CUDA Math API `__half` documentation | **VERIFIED; VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED/DERIVED.** Binary16 has eleven bits of precision including the implicit bit. Immediately below unity its spacing corresponds to approximately eight 14-bit sensor codes, so it cannot preserve the raw code lattice. |
| D2 | “**option (c) is a wash on time and saves 4 GB**” | D's roofline arithmetic and the consumer graph | **OVERSTATED; TAKEN-FROM-SECONDARY** for time | **DERIVED.** Sixty 66 MB materialised frames occupy 3.96 GB. No paired implementation establishes time neutrality; cache traffic, repeated interpolation, halos, synchronization, CPU work, and consumer count remain unmeasured. |
| D3 | “**Estimated end-to-end speedup of a CUDA fast path over a well-written wgpu implementation: ~1.1x**”; “**cut CUDA from v1 entirely**” | Official wgpu and CUDA documentation | **OVERSTATED; capability premises VERIFIED-AT-PRIMARY-SOURCE, 1.1× TAKEN-FROM-SECONDARY** | **MEASURED.** wgpu exposes the required native graphics/compute backends and CUDA exposes lower-level NVIDIA-specific controls. **ARGUED.** Deferring CUDA is a defensible scope choice, not a measured 1.1× result. |

### 5.1 D1 — binary16 spacing

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** NVIDIA documents `__half` as IEEE
binary16: *“1 sign bit, 5 bits for the exponent, and the significand is being
stored in 10 bits. The total precision is 11 bits.”*

**DERIVED.** In the bin immediately below normalized value 1, adjacent binary16
values are separated by `2^-11`. Mapping a 14-bit code range of 0–16383 to
0–1 gives `16383 / 2048 = 7.9995` sensor codes per step. The report's “roughly
8 LSB” is correct in the stated region. Keeping sensor storage as `u16` and
doing the current arithmetic in `f32` remains justified.

### 5.2 D2 — memory arithmetic is not a time benchmark

**DERIVED.** At the report's own units, `60 × 66 MB = 3.96 GB`, so avoiding one
fully materialised aligned stack saves approximately 4 GB. That portion is
sound.

**ARGUED; TAKEN-FROM-SECONDARY.** “A wash on time” is a roofline projection for
exactly the assumed consumers. Gathering can repeat interpolation, change
locality and halo traffic, contend on synchronization, and move work between
CPU and GPU. No same-pixel, same-consumer paired run was found. Later peak-RSS
measurements independently support O(workers) streaming; they do not
retroactively benchmark gather versus materialise.

### 5.3 D3 — APIs do not imply a 1.1× end-to-end ratio

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Official wgpu documentation confirms
native Vulkan, Metal, D3D12, and OpenGL backends. Official CUDA documentation
confirms NVIDIA-specific memory, scheduling, graph, and kernel controls. These
are capability facts, not application timings.

**ARGUED.** A 1.1× end-to-end ratio requires equivalent implementations,
identical image semantics, the same hardware and workload, and measured wall
time. None exists in D or the project. CUDA can remain outside v1 to reduce
surface area while the backend seam remains; the speed rationale must be
restated as unknown.

---

## 6. E — `E-plugin-architecture.md`

| Claim | Frozen quotation | Primary source consulted | Classification | What the source actually supports |
| --- | --- | --- | --- | --- |
| E1 | Canonical ABI is a **copy** boundary, required Wasmtime memory/thread features are unimplemented, and `wasi-webgpu` is Phase 2; Wasm is wrong for a pixel stage in 2026 | Canonical ABI; Wasmtime support table at `e6b33de...`; `wasi-webgpu` README | **VERIFIED; VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED.** Canonical lifting/lowering may fuse work into “a single direct copy,” not zero copies. The cited memory/thread/GPU facilities are not at the maturity required for a 528 MB pixel boundary. Control-plane Wasm remains plausible. |
| E2 | Cordis Thm 73 makes quiescent state a function of final configuration; registries commute while “**pipeline order must be explicit data, never an emergent consequence of load order**” | Cordis full paper, Definition 39, Theorem 40, Theorem 73 | **OVERSTATED; VERIFIED-AT-PRIMARY-SOURCE** | **MEASURED.** The table-versus-ordered-chain distinction is real. Theorem 73 is conditional lifecycle-schedule confluence and preserves orchestration order; it is not arbitrary registry or pixel-stage permutation equivalence. |
| E3 | `tol = t·√2·calibrate(op,cfg)` is “**correct by construction for any operator at any window with any regulariser**”; “Fault 5 becomes unrepresentable” | M52 experiment and calibration implementation | **OVERSTATED; READ-AT-PROJECT-SOURCE** | **MEASURED.** Host calibration removes a scalar response-unit declaration. Unit-sigma calibration cannot detect a wrong homogeneous degree and does not make gate semantics portable across operators. |

### 6.1 E1 — the pixel boundary remains impractical

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** The Canonical ABI says an
implementation can fuse lifting/lowering into *“a single direct copy.”* That is
a useful optimization, but it is still a copy rather than shared borrowed
access to the host's native pixel allocation.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Wasmtime's pinned support table marks
the Component Model tier 1 while recording incomplete Phase 4/fuzzing/C API
work; threads are tier 2 and unfinished, and `memory-control` plus
`shared-everything-threads` are unimplemented. The official `wasi-webgpu`
README remains at Phase 2.

**DERIVED.** One 33 MP, four-channel `f32` working frame is approximately
528 MB. Canonical lowering/lifting across separate memories moves at least one
such full buffer for each value crossing unless a host resource replaces the
pixel value with a handle. The audited standards/status do not yet supply the
mature portable GPU resource contract E would need. The static native pixel
seam and possible Wasm control-plane seam survive.

### 6.2 E2 — Cordis's theorem has five load-bearing conditions

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Cordis Definition 39 says a table
whose entries are independently added/removed is commutative, while *“a key
whose value is an ordered chain is not.”* This directly supports separating a
registry from an ordered processing pipeline.

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Theorem 73 starts with a sequence
that reaches a **quiescent** state with **no failed fiber**, requires
**pairwise-independent steps** and **every component total on its provision**,
and compares sequences taking **the same orchestration steps in their original
order**. Its conclusion is equivalence of the resulting lifecycle states under
the paper's relations.

**ARGUED.** E's summary drops the conditions and turns scheduling confluence
into a broader semantic permutation claim. Explicit pipeline order remains
correct architecture. Registry permutation tests remain useful local tests,
but Cordis Thm 73 does not prove them without first establishing the project's
operations satisfy the theorem's definitions.

### 6.3 E3 — scalar calibration is not semantic calibration

**MEASURED; READ-AT-PROJECT-SOURCE.** M52 supplies a direct counterexample.
Calibrating at unit sigma cannot distinguish a response homogeneous of degree
one from degree two because `1^1 = 1^2`. At the measured real sigma, a wrong
degree changes the gate scale by M52's **17.480×**.

**MEASURED; READ-AT-PROJECT-SOURCE.** M52 also runs five operators that are
correctly scalar-calibrated and observes up to M52's **4.54×** spread in
`n_eff`. Equal response standard deviation does not give equal selectivity,
tail behaviour, spatial correlation, or gate meaning.

**ARGUED.** The supported proposition is: host calibration makes one response
scale unnecessary in the public interface. It does not make every declaration
error unrepresentable or every operator interchangeable. A second calibration
at non-unit sigma can test the declared homogeneous degree; operator changes
still require gate re-solving.

---

## 7. F — `F-camera-lens-optics.md`

| Claim | Frozen quotation | Primary source consulted | Classification | What the source actually supports |
| --- | --- | --- | --- | --- |
| F1 | `g(ISO)=ISO/436.8` is “trustworthy”; ISO 160 agrees within 2%; “**the photon-transfer model is validated. Ship it**” | M25, M48, and M61 measurement reports | **OVERSTATED; READ-AT-PROJECT-SOURCE** | **MEASURED.** The green-plane gain relation survives the dual-gain switch, but ISO 50 needs a base-ISO floor, ISO 160 misses the old value materially, high-mode read noise changed, and blue gain is about 0.84 of green. |
| F2 | “**Effective aperture: `N_eff = N·(1+m/p)`**”; pupil magnification “genuinely needs `p`” | Edmund Optics working-f-number equation; paraxial derivation; M5 | **VERIFIED for project use; VERIFIED-AT-PRIMARY-SOURCE for `p=1`, TAKEN-FROM-SECONDARY but independently DERIVED for general `p`, READ-AT-PROJECT-SOURCE for this rig** | **MEASURED/DERIVED.** The symmetric `p=1` equation is primary-source supported, the general equation follows from the stated pupil-ratio convention, and M5 measures this rig's composite factor near the `p≈1` prediction. `p` itself was not separated from magnification. |
| F3 | Focus-driven capture has an exact global similarity transform; rail capture cannot use a global 2-D warp; detection from `FocusPosition2` plus scale drift is “**free and reliable**” | M3 and M12 | **OVERSTATED; READ-AT-PROJECT-SOURCE** | **MEASURED.** Similarity is the best tested low-parameter model for the in-camera bracket, not exact; rail geometry is depth-dependent; `FocusPosition2` is too coarse to be a reliable automatic classifier by itself. |

### 7.1 F1 — one divisor is not one universal camera model

**MEASURED; READ-AT-PROJECT-SOURCE.** M25 directly measures ISO-160
photon-transfer gain as **0.3273 DN/e⁻**, versus the old relation's **0.3663**,
and finds Sony ISO 50 is a pulled/extended setting requiring a base-ISO floor.
That is not agreement within 2%.

**MEASURED; READ-AT-PROJECT-SOURCE.** M48 revises high-mode read noise from
**1.47 e⁻** to **1.2392 e⁻**. M61 then measures ISO 500 and 1000: the green
conversion gain supports the divisor relation through the dual-gain switch,
while the blue-plane gain is **0.840 ± 0.011** of green across ISO 50–1000.

**ARGUED.** The replacement is: the relation is a useful green-plane gain
model with an extended-ISO floor and measured mode-specific read noise. It is
not one all-plane, all-ISO validation. Per-plane gain or a documented blue
exception is required before the noise model can carry colour-wide claims.

### 7.2 F2 — the equation survives, with evidence depth disclosed

**MEASURED; VERIFIED-AT-PRIMARY-SOURCE.** Edmund Optics defines working
f-number for the symmetric case as
`(f/#)_w ≈ (1 + m) × (f/#)`, where `m` is image/object magnification. This is
the `p=1` form used by F.

**DERIVED.** With pupil magnification defined as exit-pupil diameter divided
by entrance-pupil diameter, paraxial image-side cone geometry replaces `m`
with `m/p`, yielding `N_eff ≈ N(1 + m/p)`. Reversing the pupil-ratio convention
would invert `p`; the project's convention is therefore part of the formula,
not an optional notation.

**MEASURED; TAKEN-FROM-SECONDARY.** F's own citation chain does not reach a
primary optics source for the generalized `p` form. M83's derivation checks the
equation but does not retroactively upgrade F's evidence depth.

**MEASURED; READ-AT-PROJECT-SOURCE.** M5 measures the composite bellows factor
`B = 1 + m/p` in **[2.41, 3.06]** on the relevant rig. The `B=3` prediction
for approximately 2:1 and `p=1` survives; `B=5`, corresponding to `p=0.5`, is
refuted 5/5 by M5's model-free frequency test. M5 explicitly cannot separate
`m` from `p`, so this is validation of the project-relevant composite, not a
direct pupil measurement.

**ARGUED.** Facts 12, 27, and 28 and the need for a lens-profile `p` survive.
The ledger should distinguish the primary-source symmetric equation, the
general paraxial derivation, and M5's measured composite rather than presenting
all three as one citation.

### 7.3 F3 — useful mode seam, unreliable automatic detector

**MEASURED; READ-AT-PROJECT-SOURCE.** M3 tests one 22-frame in-camera bracket.
A similarity model is adequate relative to affine and homography alternatives,
but per-frame residuals remain **0.56–1.33 px**. Defocus, internal focus,
occlusion, pupil shift, and distortion prevent “exact” from being a measured
description.

**MEASURED; READ-AT-PROJECT-SOURCE.** M12 finds only three distinct
`FocusPosition2` values across a 79-frame sweep and identifies it as a coarse
encoder. Constancy does not prove rail capture; variation does not by itself
prove focus-driven capture. Rail translation genuinely creates
depth-dependent parallax, although a single-depth planar scene can still admit
a global warp.

**ARGUED.** Keep `CaptureMode::{FocusBracket,Rail}` and keep rail support
deferred. Automatic classification must use explicit capture metadata/user
knowledge plus fitted pixel residual signatures. `FocusPosition2` may be one
weak feature, not a free reliable oracle. The current project rule is already
closer to this supported form than F's original statement.

---

## 8. Downstream artefacts to reopen or narrow

**ARGUED.** This is the action list produced by the audit. “Survives” means the
decision has independent later evidence; it does not mean the cited survey
sentence should remain unchanged.

### 8.1 A — prior-project evidence

1. **A1 — narrow `SYNTHESIS.md` §§1.1–1.2.** Remove A's 1.82× as independent
   quantitative corroboration for the selector-noise thesis. M2's project
   baseline and later merge measurements preserve estimator architecture,
   `n_eff`, the named argmax negative control, and project rule 4.
2. **A2 — no reopening.** Preserve the §4.1 retraction and project rule 10.
   They are confirmed at the source script.
3. **A3 — narrow `SYNTHESIS.md` §3.2 and performance history.** Do not call
   23 GB an observed peak for the 33-frame workload and do not present 81→456 s
   as a controlled causal regression. Rule 2, O(workers) streaming, and the
   memory ratchet survive on independent arithmetic and later measurements.

### 8.2 B — algorithmic justification

4. **B1 — narrow `SYNTHESIS.md` fact 6 and risk 2's historical rationale.**
   Attach Surh's seven synthetic light-field datasets, 30 labels, one
   Laplacian configuration, and signal-dependent Gaussian noise. Do not
   generalise to all Laplacian/SML operators or real RAW. Risk 2 remains
   closed because M11/M13 independently selected Tenengrad on real RAW.
5. **B2 — narrow `SYNTHESIS.md` §§1.1 and 3.3.** Label per-band/per-tile HDR+
   reference substitution as a project hypothesis. Monod proves fixed-reference
   blur preservation, not focus fusion. The current estimator can stand on its
   later project measurements rather than this transfer.
6. **B3 — reopen the numerical justification in `SYNTHESIS.md` §1.2, the CFA
   architecture row, and any “never demosaic because >3 dB” wording.** Remove
   >3 dB as a direct-CFA-versus-merge-then-demosaic result. Preserve mosaiced
   `u16` storage and CFA-native reconstruction as supported directions, but
   require a paired focus-stack benchmark before assigning the advantage.
   Add Farsiu 2006 to the prior-art chain.

### 8.3 C — product and licence claims

7. **C1 — narrow `SYNTHESIS.md` §§1.2 and 6 product positioning.** Say “none
   among the surveyed shipping products as of the search date,” name the
   products, and add Yang and Chen 2015 as raw-Bayer multifocus prior art.
8. **C2 — replace the confidence novelty claim in `SYNTHESIS.md` §§6 and 9.**
   `focus-stack` is a direct counterexample to “nothing even close.” Preserve
   the stronger differentiation: a calibrated, actionable confidence vector
   with `n_eff` and predicted sigma was not found in the surveyed commercial
   products.
9. **C3 — keep `rawler`; narrow `SYNTHESIS.md` risk 6's “link-freely” wording.**
   Replace “LGPL satisfied by publishing our source” with an explicit binary
   release checklist covering notices, licence/library source, modification
   rights, and a working relink mechanism. The current `AGENTS.md` licence
   rule is already substantially closer to the primary text.

### 8.4 D — execution architecture

10. **D1 — no reopening.** Project rule 1, mosaiced `u16` storage, and `f32`
    arithmetic are confirmed for the current pipeline.
11. **D2 — reopen gather-versus-materialise performance equivalence in
    `SYNTHESIS.md` §9 and any performance budget that prices it as free.** Keep
    the O(workers) memory architecture and rule 2 on later evidence. If time
    neutrality matters, run one paired implementation with identical pixels
    and all consumers.
12. **D3 — reopen the wgpu-only speed justification in the compute-backend row
    and §9.** CUDA may remain deferred as v1 scope control. Replace 1.1× with
    “unmeasured” and retain the backend seam until an equivalent benchmark
    exists. Risk 6 already correctly says the future path is not runtime-tested.

### 8.5 E — plugin contracts

13. **E1 — no reopening.** The static native v1 pixel-stage seam and omission
    of dynamic/Wasm pixel plugins remain supported. Keep Wasm as a possible
    future control-plane mechanism, not a permanent impossibility claim.
14. **E2 — narrow Cordis citations in `SYNTHESIS.md` and the rationale around
    `strehl-plugin/src/registry.rs`.** State Theorem 73's quiescence,
    no-failure, independence, totality, and same-orchestration-order premises.
    Registry permutation tests are project properties, not theorem corollaries
    until those premises are mapped. Explicit pipeline order stands
    independently on the paper's table/ordered-chain distinction.
15. **E3 — reconcile `SYNTHESIS.md` facts 438–439 and 502 with facts 630–635,
    especially fact 633.** Narrow “correct by construction” and
    “unrepresentable” claims in `strehl-plugin/src/measure.rs` and
    `calibrate.rs`. Question 145 remains the direct remedy: a second
    non-unit-sigma calibration can detect wrong degree. Operator swaps still
    require gate re-solving because scalar calibration does not transfer gate
    semantics.

### 8.6 F — camera and capture modelling

16. **F1 — replace stale all-ISO/all-plane wording in `SYNTHESIS.md` §3.3 and
    the A7C II profile rationale.** Link fact 550's ISO floor, facts 557/659's
    read-noise revision, and facts 920/921's high-ISO and blue-plane results.
    Review `CameraProfile::gain_dn_per_e` wherever one scalar is treated as all
    planes. Question 184 is not reopened: M61 already answered its dual-gain
    premise.
17. **F2 — retain `SYNTHESIS.md` facts 12, 27, and 28 and the future lens
    profile's `p`.** Add evidence-depth labels: Edmund supports the symmetric
    case, the general equation is derived under an explicit pupil-ratio
    convention, and M5 measures only the composite `1 + m/p`.
18. **F3 — retain `CaptureMode`, focus-bracket v1 scope, and rail deferral in
    `SYNTHESIS.md` §9.** Remove universal “exact similarity” and “free and
    reliable” detection language. Require explicit capture metadata/user
    knowledge plus fitted residual signatures; do not trust EXIF variation
    alone. The current `AGENTS.md` rule already warns not to trust a flag alone.

### 8.7 Question 201

**ARGUED.** Question 201 is answered with a renamed quantity:

```text
M83 architectural-exposure adverse fraction = 13/18 = 72.2%
M83 strict overstatement fraction           = 12/18 = 66.7%
M83 exact-strength survival fraction         =  5/18 = 27.8%
```

**ARGUED.** The question should close as an audit of the specified
load-bearing sample, not as an estimate of all prose in the six reports. The
actionable result is the eighteen-item revision list above. A true
corpus-sentence base rate would require a claim inventory, a random sampling
unit, multiple adjudicators, and a policy for bundled claims; that is a
different and much less architecturally useful experiment.

---

## 9. Candidate facts for the ledger

**ARGUED.** These are candidates, not ledger assignments. IDs are local to
M83. Every **MEASURED** row names and quotes the primary record carrying it.

| Candidate | Class | Candidate fact |
| --- | --- | --- |
| P1 | **DERIVED** | M83's preregistered load-bearing sample contains 12/18 strict overstatements, 13/18 adverse findings including one refutation, and 5/18 claims surviving unchanged. This is an architectural-exposure rate, not a random corpus-wide base rate. |
| P2 | **MEASURED; READ-AT-PROJECT-SOURCE** | A's 1.82× ratio is computed from output spatial patch sd divided by one frame's spatial patch sd, while the same script computes source temporal sd separately. The ratio does not isolate selector noise. |
| P3 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | Pertuz et al. 2013 state that in noise, maximising a focus measure “will also add noise to the final result,” and selectively average unreliable regions. |
| P4 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | Surh Table 1's negative Laplacian Winner Margin/Curvature result uses seven synthetic light-field datasets, 30 quantised depth labels, depth-dependent blur, and signal-dependent Gaussian noise. |
| P5 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | Monod et al. state that HDR+'s fixed-reference Wiener merge “does not introduce additional blur from other images, but it does not remove blur either.” |
| P6 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | Wronski Table 1's >3 dB result compares a 15-frame method with single-frame demosaicers. It is not a paired direct-CFA-versus-merge-then-demosaic ablation. |
| P7 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | Farsiu et al. 2006 call multiframe reconstruction from pre-demosaiced images “suboptimal” and evaluate unified reconstruction from raw CFA frames. |
| P8 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | `focus-stack` commit `0cd289e...` fits per-pixel Gaussian focus profiles and emits mean, deviation, and amplitude maps when save-steps is enabled, refuting “nothing even close” to confidence diagnostics. |
| P9 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | `rawler` 0.7.2 declares LGPL-2.1; LGPL-2.1 §6 permits application distribution under chosen terms only with the section's notice, source, modification, and relinking conditions. |
| P10 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE / DERIVED** | Binary16 has eleven total precision bits. Immediately below unity, one step spans `16383 / 2048 = 7.9995` normalized 14-bit sensor codes. |
| P11 | **ARGUED** | D's 3.96 GB materialisation saving is valid arithmetic, but no paired implementation supports “time-neutral”; gather-versus-materialise performance remains unmeasured. |
| P12 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | The Canonical ABI permits fused lifting/lowering as “a single direct copy”; Wasmtime's pinned status leaves required memory/thread facilities unfinished, and `wasi-webgpu` remains Phase 2. |
| P13 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE** | Cordis Theorem 73 requires a quiescent nonfailed result, pairwise-independent steps, total components, and the same orchestration steps in original order. It proves conditional lifecycle confluence, not arbitrary pipeline permutation. |
| P14 | **MEASURED; READ-AT-PROJECT-SOURCE** | M52 shows unit-sigma calibration cannot detect a wrong homogeneous degree; that error costs M52's 17.480× at the measured real sigma, while five scalar-calibrated operators still span M52's 4.54× in `n_eff`. |
| P15 | **MEASURED; READ-AT-PROJECT-SOURCE** | M25 measures ISO-160 gain at 0.3273 rather than the old 0.3663 and requires an ISO floor; M48 revises high-mode read noise to 1.2392 e⁻; M61 confirms the green divisor across the gain switch but measures blue gain at 0.840 ± 0.011 of green. |
| P16 | **MEASURED; VERIFIED-AT-PRIMARY-SOURCE / READ-AT-PROJECT-SOURCE** | Edmund Optics gives the symmetric working-f-number equation `N_eff ≈ N(1+m)`. M5 measures this rig's composite `1+m/p` in [2.41, 3.06], supports the approximately-3 prediction, and refutes the 5 prediction 5/5. |
| P17 | **MEASURED; READ-AT-PROJECT-SOURCE** | M3's in-camera bracket is adequately modelled by similarity relative to richer tested warps but retains 0.56–1.33 px residuals; M12 finds only three `FocusPosition2` values across 79 frames. Similarity is not exact and that EXIF field is not a reliable mode oracle. |
| P18 | **ARGUED** | Seventeen of eighteen audited propositions retain a narrower architectural core, so the audit calls for widespread citation and scope repair, not wholesale architectural reversal. |

---

## 10. Final answer

**DERIVED.** The requested number has three honest forms:

- **72.2% adverse** at the preregistered load-bearing claim level;
- **66.7% strictly OVERSTATED**;
- **27.8% survived unchanged**.

**ARGUED.** The six-report result is slightly worse than M79's 2/3 adverse
comparison, not reassuringly lower. Yet the narrower architecture survives in
17/18 cases. The corpus's main defect is therefore not that it repeatedly chose
the opposite architecture from its sources. It is that it turned bounded
experiments, incomparable measurements, conditional theorems, product samples,
and API capabilities into universal or quantitative warrants. The repair is
specific: make the bounds visible, remove unsupported magnitudes, add the
missed nearest prior art, and reopen only the decisions identified in §8.
