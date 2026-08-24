# M107-chroma — pre-registration

Committed **before** any number in this milestone was computed. Rule 20 / rule 39:
every bar below names the value that would falsify it, and every gate below has an
input that could make it fail.

**Question.** Colour fringing on high-contrast edges in the shipped `--srgb` render
(`C:\dev\strehl-out\ORCH-gallery3\CROPS-100.png`): magenta/orange on `bee-3-cpl` bee
hairs, cyan on the `leaf-2-cpl` leaf edge. Attribute it across four candidate
mechanisms. **Diagnosis only — no `crates/` file is edited by this milestone.**

Candidates:

- **(a)** lateral (transverse) chromatic aberration — per-channel magnification
- **(b)** longitudinal (axial) CA baked in by a *single* per-quad focus election
- **(c)** demosaic / CFA co-siting
- **(d)** the resampler (gather kernel + coverage rescale)

## Prior work found by the rule-40 search (searched before writing this)

- `docs/research/M95-chroma-cositing.md` — measured and **fixed** the binned-path
  co-siting defect (R at (−0.25,−0.25), B at (+0.25,+0.25) binned px). Facts P18–P29.
  **Its fix is on the `--binned` path only** and is therefore inert in the render under
  investigation.
- SYNTHESIS fact **1378** — the shipped `--srgb` path demosaics with Malvar-He-Cutler;
  `--binned` is the demosaic-free arm; and the registered hazard that the `--binned`
  control itself contains `COSITE_SHIFT`.
- SYNTHESIS facts **1363–1366** (resolution/interleave), **1373/1376** (the sidecar is a
  single-variable experiment handle), **1377** (the output is genuinely full resolution).
- SYNTHESIS **§6** already records *"Per-channel focus stacking exploiting longitudinal
  CA"* as an **unverified novelty bet** with 0 arXiv hits. Hypothesis (b) is therefore
  not new to this project as an *idea*; it has never been measured.
- SYNTHESIS facts **26, 28, 832, 1147, 1150** — optical path: ILCE-7CM2 + FE 100mm F2.8
  Macro GM OSS + **2× Viltrox** teleconverter, marked f/5.6, CPL (Breakthrough X4) on
  7 of 12 stacks. **All CA measured here is system CA, not lens CA.**

## Instruments

### Instrument A — per-channel edge-spread fit on **raw CFA planes**

Rationale: it removes the demosaic, the colour matrix, the resampler and the merge from
the loop entirely, so whatever it reads is optics + sensor.

For an ROI containing one straight high-contrast edge, in a single decoded frame:

1. `raw_image_visible`, copied inside the `with` block (rule 32).
2. Split RGGB into four planes. Each sample carries its **true sensel coordinate**:
   R at `(2px, 2py)`, G1 at `(2px+1, 2py)`, G2 at `(2px, 2py+1)`, B at `(2px+1, 2py+1)`.
   Co-siting is therefore handled exactly, by construction, and **any residual
   per-channel displacement is optical, not lattice.**
3. Estimate the edge line from the two green planes only (blind to R/B).
4. Project every sample onto the edge normal, fit
   `I(d) = a + b·erf((d − d0)/(√2·w))` per plane.
5. Report `d0` (edge position, **sensel**) and `w` (edge width sigma, **sensel**).

**Free internal null:** G1 and G2 are the *same wavelength* on *different lattice
sites*. `d0_G1 − d0_G2` and `w_G1 − w_G2` must read zero. Any offset they read is
instrument error and applies equally to R and B.

### Instrument B — per-channel argmax over the focus stack

Per frame `k`, per CFA plane `c`, focus measure `F_c(x,y,k)` = box-mean of Sobel
gradient magnitude. Argmax over `k` with parabolic sub-frame refinement gives four
index maps `k_R, k_G1, k_G2, k_B`.

**Free internal null:** `k_G1 − k_G2` is a same-wavelength pair with independent noise
and different lattice sites. It carries every channel-dependent-SNR and lattice bias
the instrument has, and **none** of the axial-CA signal. It is the null that
`k_R − k_Ḡ` must beat.

## Registered bars

**B1 — single-frame control (run FIRST).**
Instrument A on a single in-focus raw frame at an edge showing the fringing.
- **Stacking is NOT the cause** if the single-frame per-channel edge position offset
  `max(|d0_R−d0_Ḡ|, |d0_B−d0_Ḡ|)` is ≥ **0.30 sensel**, i.e. ≥ 50 % of a co-siting
  half-step, *and* the same-edge measurement on the merged render agrees within 2×.
- **Stacking IS implicated** if the single-frame offset is < **0.12 sensel** while the
  merged render reads ≥ 0.30 sensel.
- The instrument is **broken** and nothing after this is admissible if
  `|d0_G1 − d0_G2|` ≥ **0.10 sensel** or `|w_G1 − w_G2|` ≥ **0.10 sensel**.

**B2 — radius sweep, for (a).**
Instrument A on ≥ 6 edges spanning image radius on one frame of an achromatic subject.
- **(a) CONFIRMED** if the *radial* component of `d0_R − d0_B` is linear in radius with
  R² ≥ **0.5**, an intercept at r = 0 consistent with zero (|intercept| < **0.15
  sensel**), and a corner extrapolation ≥ **0.30 sensel**.
- **(a) DEAD** if the mean |offset| on edges at r < 0.35·r_max is ≥ **50 %** of the mean
  on edges at r > 0.75·r_max, or R² < 0.2.

**B3 — per-channel argmax, for (b). The core experiment.**
Instrument B on ≥ 1 stack, restricted to pixels where all four planes have a confident
unimodal focus response.
- **(b) CONFIRMED** if `median(k_R − k_Ḡ)` and `median(k_B − k_Ḡ)` are **non-zero with
  opposite signs**, each `|median|` ≥ **0.5 frames**, and each `|median|` ≥ **3×**
  `|median(k_G1 − k_G2)|`.
- **(b) KILLED** if both `|median|` < **0.5 frames**, or if neither exceeds 3× the null.
- **Instrument broken** if `|median(k_G1 − k_G2)|` ≥ **0.25 frames**.
- **Subject-colour confound control:** the same measurement must be run on
  `tweezers-cpl`, whose subject is achromatic metal. A result that appears only on a
  coloured subject is a chroma-SNR artifact, not axial CA.
- Every map is **rendered and looked at** before any median is quoted.

**B4 — demosaic path comparison, for (c).**
Same stack, same ROI, `--srgb` (Malvar-He-Cutler) vs `--srgb --binned`.
- **(c) IMPLICATED** if edge chroma RMS differs by ≥ **30 %** between the two arms.
- **(c) BOUNDED SMALL** if they differ by < **15 %**.
- **Registered hazard (fact 1378):** the `--binned` arm contains `COSITE_SHIFT`. Its
  sign is checked directly — Instrument A on the binned render must read
  `|d0_R − d0_Ḡ|` < **0.15 binned px**. If it reads ≈ 0.5 binned px the control is
  contaminated and is reported as such rather than used.

**B5 — CPL and subject-colour control.**
Instrument A on `wrapped-text-1` — **no CPL**, achromatic black-on-white, high contrast.
- **The CPL is exonerated** if lateral CA there is within **2×** of the CPL stacks.
- **The CPL is implicated** if the non-CPL stack reads < **0.3×** the CPL stacks.

## What would make me report a null

If B3's medians land inside the G1–G2 null, I report **(b) killed** and say so in the
headline. The orchestrator has stated a preference for hypothesis (b); a soft
confirmation is worth less than a clean null and I will not manufacture one.

## Ownership

Writes only to `experiments/M107-chroma/` and `C:\dev\strehl-out\M107-chroma\`, plus
`docs/research/M107-chroma.md`. **No file under `crates/` is edited.** `align.rs`,
`align_cmd.rs`, `merge_cmd.rs`, `merge_cmd/halo.rs`, `SYNTHESIS.md`, `AGENTS.md`,
`README.md`, `lib.rs`, `main.rs` are read-only to me.
