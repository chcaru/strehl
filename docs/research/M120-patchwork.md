# M120 — the background patchwork: what it is, what it is not, and a number for it

**ORCH's fact 1604 is wrong in two of its three limbs. But fact 1603 is right, and it is
worse than ORCH thought: the patchwork is in the SHIPPED default render, not only in the
gate-0 image ORCH was shown, and M120's own intermediate claim that the shipped render was
clean is hereby RETRACTED.**

The through-focus response in the defocused background is **not** flat and **not**
noise-dominated — it stands **15.0×** above the pure-noise ceiling and swings **8.6 noise
SD** through focus (MEASURED). The shipped merge does **not** gather each polygon from a
different frame — at the shipped gate it averages **166.8 of 299** frames per pixel
(MEASURED). And per-frame brightness drift explains only **60.9%** of the effect; **39.1%
survives** removing it entirely (MEASURED).

What is true is the *class* of ORCH's claim. The merge manufactures the patchwork. In a
128×128 background ROI where **every one of the 299 input frames is featureless**, the
shipped default render carries **4.34×** more fine structure than the single noisiest
input frame — where the arithmetic mean of the same frames carries **0.34×**, and where
any spatially constant weighting is bounded above by **1.284**. That is a proof, not an
aesthetic judgement.

| | |
|---|---|
| Milestone | M120 |
| Owner | M120 (analysis only — no file under `crates/` was touched) |
| Stack | `bee-3-cpl`, 299 frames, ILCE-7CM2, ISO 100 |
| Pre-registration | `experiments/M120-patchwork/PREREGISTRATION.md`, committed `a6fdd74` **before any measurement** |
| Scripts | `experiments/M120-patchwork/0*.py`, `1*.py` |
| Artifacts | `C:\dev\strehl-out\M120\` |
| Renders consumed | none — every number below comes from artifacts M87, M93 and ORCH already produced |

---

## 1. Headline table

Band-pass contrast ratio over a 128×128 pure-background ROI, denominator = **all 299**
input frames on the **same grid** (see §3 for why that is exact):

```
Q(I) = ||B I||_ROI / mean(I)_ROI   ÷   max_k ( ||B f_k||_ROI / mean(f_k)_ROI )
B = gaussian(σ=2) − gaussian(σ=8)
```

| arm | Q(2–8 px) | verdict |
|---|---:|---|
| M87 Python gate 0 — **the image ORCH judged** | **7.166** | VIOLATES |
| Rust `armM-gate0-binlin.tif` (gate 0) | **7.166** | VIOLATES — *identical to 4 s.f.* |
| M87 Python gate 2 | 4.615 | VIOLATES |
| **`armM4-gate4-binlin.tif` — the SHIPPED default** | **4.337** | **VIOLATES** |
| `bee3-g0.tif` | 3.269 | VIOLATES |
| `bee3-g1.tif` | 2.269 | VIOLATES |
| `bee3-full.tif` | 2.149 | VIOLATES |
| NULL-1 — plain mean of all 299 (constant weights) | **0.343** | ok ✓ |
| NULL-2 — a single input frame | 0.308 | ok ✓ |
| PLACEBO — gate-4 admitted sets, all frames identical | **0.3085** | ok ✓ |
| POS — planted patchwork, 24 cells | **6.694** | VIOLATES ✓ |
| input frames, median | 0.490 | |
| **bound for any spatially constant convex weighting** | **1.284** | |

`ORCH-morning/bee-3-strehl.tif` scored 0.259 but is **4688 × 7032 — full resolution, not
binned**; NCC against the binned grid is **−0.267**. Its number is **not comparable** and
is excluded. (MEASURED)

---

## 2. Verdicts on R1–R7

| | rival | verdict | evidence |
|---|---|---|---|
| **R1** | polygons are in the elected-index field (ORCH) | **class CONFIRMED, mechanism REFUTED** | see below |
| R1a | response flat → noise-dominated → argmax near-random | **REFUTED** | winner **15.0×** the noise ceiling; **0.0%** of ROI at or below it; through-focus range **8.6 noise SD** |
| R1b | the regulariser snaps a random field into plateaus | **NOT SUPPORTED** | dominant scale **21–26 px** ≈ the **27×27** focus window, not the 17×17 regulariser; M111 P3 already refuted this on `marker` |
| R1c | each polygon gathers a different frame; exposure drift makes the step | **REFUTED at the shipped gate** | gate 4 averages **166.8 / 299** frames per ROI pixel, n_eff = 1 on **0.3%**; drift explains only **60.9%** |
| **R2** | tiling / block artifact of the implementation | **DEAD** | **26.2%** of edges within 10° of axis-aligned vs **22.2%** for uniform; spectral peaks at **25.6** and **21.3 px**, z = +3.20 / +4.15, non-matching, no integer pitch |
| **R3** | the polygons are real, in the input frames | **DEAD** | every one of 299 frames is featureless in the ROI; single-frame Q median **0.490**; see the two pictures in §4 |
| **R4** | photometric only (frame brightness drift) | **PARTIAL — necessary, not sufficient** | per-frame level normalisation cuts Q **4.337 → 1.697**; **39.1% survives** and is still above the 1.284 bound |
| **R5** | demosaic or the output colour/tone transform | **DEAD** | present in M87's Python green-luma path with **no demosaic and no colour transform**; the Rust binned-linear render reproduces it to 4 s.f. |
| **R6** (M120's addition) | argmax of an already-smoothed field sets the scale | **SUPPORTED** | 21–26 px dominant scale ≈ `WINDOW_RADIUS 13` → 27×27 |
| **R7** (M120's addition) | the gate is the dose knob | **CONFIRMED** | monotone Q 7.166 → 0.953 across gate 0 → 16 |

### The corrected mechanism (ARGUED, built on the MEASURED numbers above)

The response is strongly non-flat but **nearly degenerate near its maximum**. Median
winner-to-runner-up gap is **0.00464 = 0.216 gate units** while the response itself is
0.6685, 15× the noise floor. So the winner is chosen between frames that are genuinely,
measurably different — just barely — and the choice is *stable and repeatable*, not random.
Those near-tied frames differ in **background level by up to 28%** (2925–3756 DN across the
ROI) and in the **shape** of their defocus gradient. The gate then admits a set that varies
from pixel to pixel; the admitted sets' mean levels differ; the boundaries between
admitted-set regimes are the steps. Averaging 167 frames does not remove them because they
are a **bias**, not noise — which is precisely why 12.9× of noise averaging leaves Q at 4.34.

---

## 3. The geometry, and the retraction

M120's first headline — *"the three PNGs ORCH judged are not the shipped merge; the shipped
render's background is completely smooth"* — was **half right and consequentially wrong**,
and is **RETRACTED**.

- Right: the PNGs come from `experiments/M87-occlusion/src/04-through-focus.py`, a Python
  per-pixel argmax with **no gate**, traced to source. (MEASURED)
- Wrong: that Python arm is **bit-faithful to the Rust gate-0 path**. Cross-correlating
  M87's `bee3-leg-sel.npy` against `armM-gate0-binlin.tif` gives **NCC = 1.0000 at zero
  offset**, related by a pure gain of **4.4135**, constant to 4 s.f. across 23
  independently rendered frames. Their Q vectors are identical: 8.317 / 7.166 / 3.630 /
  2.105. (MEASURED)
- Wrong: the "smooth shipped background" was `ship-before-linear.tif`, which required a
  (dy = +33, dx = −29) registration — i.e. it is on a **different, aligned** geometry. Its
  provenance is **NOT VERIFIED**: it is byte-equal to none of `armM4-gate4-binlin.tif`,
  `armM-gate0-binlin.tif` or `armC-aligned-gate0.tif`. **Stated plainly: M120 could not
  establish what produced that file.**
- The correctly registered shipped default, `armM4-gate4-binlin.tif`
  (`gates : 4.00`, `alignment : OFF`, logged), sits at Q = **4.337** and shows the
  polygons plainly. §4.

`armM-gate0-binlin`, `armM4-gate4-binlin` and all 23 `armF-f*.tif` are logged
`alignment : OFF`, so they share one unwarped grid with the M87 cube:
M87 box pixel (y, x) = shipped-grid pixel (1178 + y, 278 + x), exactly. The ROI is
shipped-grid rows **1654:1782**, cols **720:848**.

**A second retraction.** `08_shipped_grid.py` reported the shipped default at Q = 15.7. That
number is **INVALID and must not be quoted**. Its denominator was the 23 `armF` frames,
whose indices span only 119–208, while the merge draws on all 299 (the elected-index field
uses 106 distinct indices spanning 7–298 inside the ROI). Worse, its ROI search — "the box
quietest in those 23 frames" — selected a box that is quiet in the 23 precisely because its
content is *sharp in the other 276*; looking at it shows the bee's hair-fringed silhouette,
not background. That is exactly the self-confirming control the brief warned about, and it
pointed **at** the alarming answer. It was caught by checking that the gate-4 minimum
(6646 DN) fell below every one of the 23 frames' minima (12217 DN), which a convex
combination cannot do.

---

## 4. Item 3 / R3 — the input frames (the one that would have embarrassed us)

`C:\dev\strehl-out\M120\R3-input-frames-sheet.png` — nine input frames spanning the stack,
the same crop, the same stretch. Every one is smooth. The defocused frames show a soft
diagonal luminance band and nothing else; the in-focus frames show the leg and clean white
around it. **No frame contains a polygon.** (OBSERVED + MEASURED: single-frame Q median 0.490.)

The pair that carries the whole argument, identical pixels, identical stretch:

| | |
|---|---|
| `FINAL-NULL-2-single-input-frame.png` | featureless white with photon grain |
| `FINAL-SHIPPED-default--gate-4--armM4-gate4-bin.png` | flat polygons with hard boundaries and visible steps |

**R3 is dead. The artifact is not photographic.**

---

## 5. Item 1 — the coincidence, and why it is not the whole hypothesis

Spearman ρ between |∇ elected-index| and |∇ output| over the ROI, with a 64-px-shift null:

| gate | mean n_eff | ρ | shift null | ratio, top-decile index edge / bottom half |
|---:|---:|---:|---:|---:|
| **0** | 1.0 | **+0.5465** | +0.0077 | **12.69×** |
| 1 | 9.9 | +0.0711 | +0.0633 | |
| 2 | 44.2 | −0.0725 | +0.0413 | 1.74× |
| **4 (shipped)** | 166.8 | **−0.2424** | −0.0240 | |
| 8 | 262.6 | −0.0553 | −0.0431 | |
| 16 | 295.1 | +0.0136 | −0.0576 | |

Decoupled controls at gate 0, same index field: plain mean **ρ = −0.0040** (p = 0.61),
single frame **ρ = +0.0022** (p = 0.77). So unlike M111 P8's case, the coincidence here is
**not** an artifact of scene structure — the decoupled arms are flat at zero. (MEASURED)

**The answer to item 1 is therefore split:** the boundaries coincide with the elected-index
field **in the gate-0 image ORCH judged** (ρ = +0.55 vs a 0.008 null, 12.7× edge ratio) and
**do not** in the shipped default (ρ = −0.24). The shipped patchwork's boundaries are
admitted-*set* boundaries, not winner-*index* boundaries.

**M111 P8 is upheld and extended.** A coincidence alone would not have settled this. What
settles it is the placebo below.

### The placebo (rule 11)

Take the gate-4 **admitted sets unchanged** — every polygon boundary still in place — and
replace every frame with one real frame, so inter-frame differences vanish.
**Q(2–8) = 0.3085**, comfortably under the 1.284 bound. (MEASURED)

**The election alone manufactures nothing.** The manufacture requires inter-frame
differences *and* a spatially varying admitted set. Neither is sufficient alone: constant
weights over the same differing frames give **0.343**.

---

## 6. Item 2 / R2 — tiling geometry

- Edge-orientation histogram, top-decile |∇ index|, 10° bins: **26.2%** within 10° of
  axis-aligned, against **22.2%** for a uniform distribution. A 1.18× excess, fully
  explained by gradient-operator anisotropy on a square grid.
- 1-D power spectra of |∇ index|: strongest peak at **25.6 px** horizontally (z = +3.20)
  and **21.3 px** vertically (z = +4.15). **Different pitches, non-integer, modest z.** A
  real tiling would give matched integer pitches at z ≫ 5 on both axes.

**R2 is dead. This is not a block/tile bug.** (MEASURED)

The 21–26 px scale is not noise, though: it matches `focus.rs WINDOW_RADIUS = 13` →
**27×27**, and not `REGULARISER_RADIUS = 8` → 17×17. That corroborates M111 P3 on a second
stack: **the focus window, not the regulariser, sets the plateau scale.** (MEASURED)

---

## 7. Item 4 — the invariant. It holds, and it should ship.

### Statement

Let `B` be any linear high-pass and `R` any region. For a merge with **spatially constant**
convex weights `w`:

```
||B (Σ w_k f_k)||_R  ≤  Σ w_k ||B f_k||_R  ≤  max_k ||B f_k||_R
mean(Σ w_k f_k)_R    ≥  min_k mean(f_k)_R
```

so the unit-free ratio obeys

```
Q  =  C(merge) / max_k C(f_k)   ≤   max_k mean(f_k)_R / min_k mean(f_k)_R   =:  Q_bound
```

**Q > Q_bound is a proof that the merge weights varied spatially**, i.e. that the merge
manufactured fine structure the inputs do not contain. It needs no aesthetic judgement and
no reference image.

### Its stated failure direction (rule 18)

It cannot tell manufactured structure from **legitimately recovered detail** — which is the
entire purpose of focus stacking. It is therefore admissible **only** on a region where the
inputs are smooth, and it must never be applied frame-wide. It is also sensitive to
resampling: warped arms need the caveat or `STREHL_ALIGN=0`. All numbers here are from
unaligned arms.

### Does it hold on `bee-3`?

**Yes, and the shipped default violates it.** Q_bound = 1.284; shipped Q(2–8) = **4.337**.
Controls: NULL-1 (plain mean) **0.343**, NULL-2 (single frame) **0.308**, placebo **0.3085**
— all quiet; POS (planted patchwork) **6.694** — fires. Determinism: `armM-gate0-binlin` and
`armM-gate0-binlin-REPEAT` agree to **4 significant figures in every band**. (MEASURED)

### Proposed shipped acceptance invariant

> **INV-PATCHWORK.** On any ROI where `max_k C(f_k) ≤ 3 × ` the model-predicted photon-noise
> band-pass contrast, the merged output must satisfy
> `C(out) ≤ Q_bound × max_k C(f_k)` with `Q_bound = max_k mean(f_k) / min_k mean(f_k)`,
> `C(I) = ||gaussian(I,2) − gaussian(I,8)||_ROI / mean(I)_ROI`.
>
> **The implementation must assert the input dtype before computing anything.** See §12:
> an 8-bit read of the same data inflates Q from 4.337 to 4.407, i.e. quantisation noise
> pushes this metric in the **false-alarm** direction. A narrowing reader would make this
> invariant fire on a clean merge.

**Named input that would make it FAIL (rule 20):** a stack of a genuinely textured subject
where the ROI selector mistakenly admits texture — the invariant then flags legitimate
detail recovery. The ROI gate above is the guard, and it must be evaluated per stack, not
assumed. **Second named failure:** a two-frame stack where one frame is grossly
mis-exposed; `Q_bound` inflates and the invariant goes blind.

**Implementation note (proposal only — M120 edited nothing under `crates/`).** This does
*not* require rendering 299 single-frame outputs. Pass two already visits every frame's
luma per tile; `max_k C(f_k)` can be accumulated there for a caller-supplied ROI at
negligible cost, and compared against the finished tile. That is the cheap form.

**A caveat I could not remove.** The project has never rendered all 299 frames singly
through the shipped pipeline, so the *only* complete-population denominator available today
is M87's binned green-luma cube. Step 9 shows that cube is the shipped grid exactly
(NCC 1.0000, gain 4.4135 constant to 4 s.f.), so the numbers above are sound — but a
future run should confirm with native single-frame renders.

---

## 8. Item 6 — the metric, with both controls

**Adopt `Q(2–8 px)` as the patchwork number.** Cheap (four Gaussian blurs), unit-free,
bounded above by a quantity computable from the inputs, and it comes with a proof.

Pre-registered directions, written down before the run (`PREREGISTRATION.md` §5):
null ≤ 1.00, positive control ≥ 1.5. Outcome:

| control | pre-registered | measured | |
|---|---|---:|---|
| NULL-1 plain mean, constant weights | ≤ 1.00 | **0.343** | ✓ |
| NULL-2 single input frame | ≤ 1.00 | **0.308** | ✓ |
| NULL-3 placebo, gate-4 sets, identical frames | ≤ 1.00 | **0.3085** | ✓ |
| POS planted patchwork | ≥ 1.5 | **6.694** | ✓ |
| determinism (gate-0 repeat render) | identical | identical to 4 s.f. | ✓ |

Two rivals were measured alongside and **both are worse**:

| metric | gate 0 | shipped gate 4 | mean | single frame | planted |
|---|---:|---:|---:|---:|---:|
| **Q(2–8)** | **7.17** | **4.34** | 0.34 | 0.31 | 6.69 |
| Laplacian kurtosis | 8.90 | — | 6.32 | 3.02 | 13.15 |
| flat-component count / 10k px | **0.00** | — | 3.05 | 5.49 | 10.38 |

Laplacian kurtosis **fails to separate** (gate-0 8.90 sits below the planted control's 13.15
and near the plain mean's 6.32). The connected-component count is **inverted** — it scores
the worst arm at 0.00, because a merge that plants steps everywhere leaves no locally-flat
component large enough to count. Neither should be adopted. (MEASURED)

**Pre-registered ROI rule fired its refusal, and that is reported rather than papered over.**
`04_roi.py`'s registered gate — "smooth in every frame at a 9×9 local sd, largest square
≥ 128 px" — refused: the largest square is **64 px**. The registered criterion measured
photon noise and the card's illumination gradient rather than structure at the artifact's
scale, and at a tightened 2–8 px band with an extreme-value-matched null **no pixel of the
crop qualifies at all** (p1 of max-over-299 band-pass local RMS = 6.71 DN against a
predicted floor of 3.32 DN). The ROI actually used is the **explicitly searched** cleanest
128×128 box; its frames sit **2.41× (median) to 3.20× (worst)** above the photon floor.
Disclosed, not hidden. The invariant does not need the smoothness assumption — the theorem
holds on any region — so this weakens the *interpretation*, not the proof.

---

## 9. Item 5 — the soft gate. A prediction, not a render.

M116 owns the A/B render. M120 computed the prediction from the cached focus field using the
kernels read out of the shipped source (`merge.rs:346` Gaussian `exp(−½(gap/T)²)`, support
4.71 T; `merge.rs:355` Exponential `exp(−gap/T)`, support 11.09 T; `merge.rs:1424`
`T = threshold·√2·FOCUS_NOISE_SD`). Stated **before** M116 reports, so M116's render is a
falsification test.

### PREDICTION (labelled ARGUED-from-MEASURED; falsifiable by M116)

| | mean n_eff | Q(2–8) | change | passes the 1.284 bound? |
|---|---:|---:|---:|---|
| hard gate 4 (shipped) | 166.8 | 4.337 | — | no |
| `STREHL_SOFT_GATE=gaussian` | 245.3 | **2.291** | **−47.2%** | **no** |
| `STREHL_SOFT_GATE=exponential` | 244.1 | **1.744** | **−59.8%** | **no** |

**The soft gate will roughly halve the patchwork and will not remove it.** Exponential beats
Gaussian here because its heavier tail admits the far-off frames that carry the opposite
level error.

**Fraction of the frame affected:** over the whole M87 box (4× decimated), soft `n_eff`
exceeds hard `n_eff` by more than 5% on **64.8%** of pixels. Hard gate 4 averages 31.77
frames box-wide and collapses to `n_eff = 1` on **38.8%** of it — so this is not a rare
corner. (MEASURED)

**Price.** M116 P3/P4 already measured, on this stack, gaussian ΔD = −0.01218 (real detail
lost, 99.1% unexplained by noise reduction) against ΔN = −0.02044 (the best flat-field
improvement measured). M120's prediction says the flat-field half of that trade buys a
2.3× cut in Q and still leaves a violation. **On this evidence the soft gate is a
worthwhile but partial mitigation, not the fix.**

### What the hard gate ladder says instead

| gate | mean n_eff | n_eff = 1 % | Q(2–8) |
|---:|---:|---:|---:|
| 0 | 1.0 | 100.0 | 7.166 |
| 1 | 9.9 | 2.4 | 4.904 |
| 2 | 44.2 | 0.6 | 4.615 |
| **4 (shipped)** | **166.8** | **0.3** | **4.337** |
| 8 | 262.6 | 0.1 | 2.825 |
| **16** | **295.1** | **0.0** | **0.953** ← first arm to pass |
| 32 | 297.0 | 0.0 | 0.699 |

**Q crosses the bound between gate 8 and gate 16** — i.e. only when the gate is wide enough
to admit essentially the whole stack, which is the arithmetic mean and throws away the
stacking. That is the real shape of the problem: **there is no gate width that both
preserves selectivity and satisfies the invariant.** (MEASURED)

---

## 10. Proposed facts

- **P1 (MEASURED).** In a 128×128 background ROI of `bee-3-cpl` where all 299 input frames
  are featureless, the shipped default render (`--gate 4`, alignment off) carries 4.337×
  the band-pass contrast of the noisiest single input frame, against an upper bound of
  1.284 for any spatially constant weighting. The merge manufactures the patchwork.
- **P2 (MEASURED).** ORCH's fact 1604 limb (a) is false: the through-focus response in that
  ROI stands 15.0× above the pure-noise ceiling (0.6685 vs 0.0445), swings 8.6 noise SD, and
  0.0% of ROI pixels sit at or below the ceiling. The argmax is not noise-driven.
- **P3 (MEASURED).** ORCH's fact 1604 limb (c) is false at the shipped gate: gate 4 averages
  166.8 of 299 frames per ROI pixel and reaches n_eff = 1 on 0.3%. It is true only at gate 0.
- **P4 (MEASURED).** Per-frame photometric normalisation removes 60.9% of the patchwork at
  gate 4 (Q 4.337 → 1.697) and leaves it above the bound. R4 is necessary but not sufficient.
- **P5 (MEASURED).** M87's Python gate-0 arm is bit-faithful to the Rust gate-0 path:
  NCC 1.0000 at zero offset, pure gain 4.4135 constant to 4 s.f. across 23 frames, identical
  Q in all four bands. The two implementations cross-validate.
- **P6 (MEASURED).** The polygon boundaries coincide with the elected-index field at gate 0
  (ρ = +0.5465 against a 0.0077 shift null, 12.69× edge ratio) and not at gate 4
  (ρ = −0.2424). The shipped patchwork's boundaries are admitted-set boundaries.
- **P7 (MEASURED).** The election alone manufactures nothing: gate-4 admitted sets applied to
  a stack of identical frames give Q = 0.3085.
- **P8 (MEASURED).** Not a tiling artifact: 26.2% of index edges axis-aligned vs 22.2%
  uniform; spectral peaks at 25.6 and 21.3 px, z = +3.20 / +4.15, unmatched, non-integer.
- **P9 (MEASURED).** The dominant patchwork scale (21–26 px) matches the 27×27 focus window,
  not the 17×17 regulariser — corroborating M111 P3 on a second stack.
- **P10 (MEASURED).** Not photographic: all 299 input frames are featureless in the ROI,
  single-frame Q median 0.490.
- **P11 (MEASURED).** Not demosaic or the colour transform: the artifact is fully present in
  a green-luma path with neither.
- **P12 (ARGUED from MEASURED).** `STREHL_SOFT_GATE` will cut Q(2–8) from 4.337 to 2.291
  (gaussian) or 1.744 (exponential), affecting 64.8% of the frame, and will not reach the
  1.284 bound. **A prediction for M116 to falsify.**
- **P13 (MEASURED).** No hard gate both preserves selectivity and satisfies the invariant:
  Q crosses 1.284 only between gate 8 and gate 16, where n_eff is 263–295 of 299.
- **P14 (MEASURED).** Laplacian kurtosis and locally-flat-component count both fail as
  patchwork metrics on this data; the component count is inverted.
- **P15 (retraction).** M120's own intermediate claim that the shipped render's background is
  clean is withdrawn. It rested on `ship-before-linear.tif`, which is on a different, aligned
  geometry and whose provenance M120 could not establish.
- **P16 (retraction).** `08_shipped_grid.py`'s ROI-A figures (shipped Q = 15.7) are invalid —
  under-sampled denominator, and an ROI objective that selected the bee's silhouette.

---

## 11. What M120 could not verify

- **The provenance of `ship-before-linear.tif`.** Byte-equal to none of the three candidate
  M93 renders. Its exact invocation was not recovered.
- **A native complete-population denominator.** No stack has had all 299 frames rendered
  singly through the shipped pipeline. The denominator here is M87's cube, shown equal to
  the shipped grid at NCC 1.0000, which is strong but is not the same as the native check.
- **The 0.1% gate reconstruction residual.** M120's gate-2 reconstruction from the cached
  field differs from M87's cached `bee3-leg-g2.npy` by at most 3.428 DN on a ~3300 DN signal
  (≈0.10%), presumably accumulation order or a `>=`/`>` boundary. Not chased down.
- **Whether this generalises beyond `bee-3-cpl`.** Every number here is one stack. M111
  measured `marker` and `lavendar` and never `bee-3`; M120 measured `bee-3` and neither of
  those. The R6/P9 window-scale result agrees across the two, which is one point of contact.
- **The shipped render at 1:1 across the whole frame.** M120 measured one 128×128 ROI, chosen
  by an explicit stated objective. The patchwork's frame-wide extent is OBSERVED from ORCH's
  crops, not measured.
- **Whether `bee3-full.tif` / `bee3-g0.tif` / `bee3-g1.tif` were rendered with alignment off.**
  No log was found for them, so their gate settings are inferred, not read. Their **geometry
  is verified**: all three are 2344 × 3516 binned and correlate with `armM-gate0-binlin` over
  the ROI at NCC +0.9998, +0.9046 and +0.8570 respectively — consistent with gate 0, gate 1
  and a wider gate, alignment off. (MEASURED)

---

## 12. PIL 16-bit-RGB hazard audit (ORCH fleet-wide alert)

Script: `experiments/M120-patchwork/13_pil_audit.py`. Run after the report was first
committed, in response to ORCH's finding that `PIL.Image.open()` silently returns `uint8`
for 16-bit **RGB** TIFFs.

**M120 is not exposed. (MEASURED)** Every `.tif` read in every M120 script is
`tifffile.imread` — `01_geometry.py:11`, `02_pc1_shipped.py:68`, `02b_register.py:53`,
`02c_coarse_register.py:36`, `03_pc1_crops.py:39`, `07_battery.py:132`,
`08_shipped_grid.py:51,56,58`, `09_geometry_fix.py:50,94`, `10_final.py:60`,
`11_mechanism.py:62,63`. PIL appears only as `Image.fromarray(...).save(...)` for PNG
previews. The single `Image.open` (`00_look.py:21`) reads ORCH's three 8-bit grayscale
**PNG** crops — the harmless preview case. The 299-frame denominator comes from
`m87lib.read_planes`, which is `rawpy.imread` on the ARW files (`m87lib.py:124,145`), never PIL.

**No file M120 consumed was laundered upstream. (MEASURED)** All eleven TIFFs read carry
6 199 – 15 019 distinct levels per channel in a 512×512 patch, against the ≤256 that an
8-bit round-trip would leave. This includes `ship-before-linear.tif` (13 479 levels), so
the §3 retraction stands on the geometry finding alone and is not a bit-depth artifact.

**The hazard reproduced on this project's own output, in M120's own ROI. (MEASURED)**
`armM4-gate4-binlin.tif`, green, rows 1654:1782 × cols 720:848:

| reader | dtype | min | max | sd | distinct levels |
| --- | --- | ---: | ---: | ---: | ---: |
| `tifffile` | `uint16` | 12081 | 15934 | 940.52 | 2989 |
| `PIL` | `uint8` | 47 | 62 | 3.70 | **16** |

A 187× loss of level resolution on the exact pixels this milestone's headline rests on.

**Counterfactual, and the part worth keeping. (MEASURED)** Recomputed against the same
true-16-bit denominator, the shipped default's headline number would have been
**Q = 4.407 via PIL against the 4.337 reported via `tifffile`** — the violation survives,
because the patchwork steps span ~3850 DN of a 15934 DN signal (~62 8-bit counts), far
above the quantisation floor. But note the **direction**: quantisation *added* band-pass
energy to the numerator and pushed Q **up**. For a small signal it would dominate. So the
narrowing reader is a **false-alarm** hazard for INV-PATCHWORK specifically, which is why
§7 now requires the invariant to assert its input dtype. M120 did not write that assert
either; the lesson is taken, not merely relayed.

**A confirmed downstream victim, for ORCH's triage. (MEASURED)**
`experiments/M87-occlusion/src/40-ship-delta.py:5-6` reads two 16-bit RGB shipped renders
through `np.asarray(Image.open(...)).astype(np.int32)` and persists their difference to
`cache/ship-delta.npy`. That file is `(4688, 7032) uint16, min 0, max 163, mean 1.621` —
a halo-fix delta whose values are in **8-bit** units despite the `uint16` dtype, with a
~257 DN-16 floor under every difference. A correction moving pixels by tens of 16-bit
counts is invisible in it. This is exactly ORCH's "most suspect of all" class.
Relatedly, `43-ship-crops.py:9` divides that PIL `uint8` array (max 255) by `257.0` and
casts back to `uint8`, giving max `0.992 → 0`: **those crops are black**. M120 could not
recompute the true delta — `30-SHIP-BEFORE-default.tif` and `31-SHIP-AFTER-fixhalo.tif`
are no longer on disk. Owner of M87 should re-render before trusting any halo-fix number.

---

# M120b — the mechanism. ORCH's regulariser hypothesis is refuted.

Pre-registered in `experiments/M120-patchwork/PREREGISTRATION-M120b-mechanism.md`
(commit `f30b513`), **before** any M120b measurement. Existence is settled by facts
1616–1620 and is not re-litigated. Scripts: `14_probe_field.py`, `15_operators.py`,
`16_p234.py`, `17_operator_price.py`.

## 13. Headline

**Turning the spatial regulariser completely off removes 3.7% of the visible defect and
leaves the crazy paving plainly visible. (MEASURED)** With **both** spatial-coherence
operators off — a pure per-pixel argmax whose index field is 2 px salt-and-pepper — the
render still violates the no-manufactured-structure invariant by **2.6×**. The regulariser
is not the cause. Neither is the focus window. **The cause is the election itself.**

ORCH's supporting argument — *"raw argmax noise would be pixel-scale salt-and-pepper…
the regulariser is the only thing in the pipeline that does that"* — rests on a premise
that is **false as a matter of code**, checkable without any pixels. The chain is:

| stage | operator | support | source |
| --- | --- | --- | --- |
| 1 | Sobel 3×3 magnitude | 3 px | `SOBEL_RADIUS = 1` |
| 2 | **`box_mean` over the focus window** | **27 × 27** | `WINDOW_RADIUS = 13`; 729 taps, `focus.rs:899` |
| 3 | `/ σ(luma)`, per pixel | 1 px | `focus.rs:219,272` |
| 4 | `regularise` = `box_mean` | 17 × 17 | `merge.rs:93,194` |
| 5 | argmax over frames | — | |

There are **two** coherence operators and the one applied **first is larger**. An argmax
over a field already box-summed across 27 px cannot be salt-and-pepper.

## 14. M1 — isolating the two operators (MEASURED)

Chain replicated from the 299-frame luma cube; the replication reproduces the shipped
`bee3-leg-argbest.npy` at **96.75%** exact index agreement over the background mask
(347,676 px, 40.8% of the plane, max-over-frames local sd < 250 DN). Arm C is taken from
the **exact cached shipped field**, not the replication, because it has the largest blobs
and is therefore the reference that argues *against* the prediction (discipline 829).

| arm | window | regulariser | #components | mean area | area-weighted | **eq. diameter** |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| **A** | OFF | OFF | 247,435 | 1.4 | 3.0 | **1.97 px** |
| **A′** | OFF | **ON** | 26,801 | 12.9 | 264.4 | **18.35 px** |
| **B** | **27×27** | OFF | 40,035 | 8.7 | 296.0 | **19.41 px** |
| **C** | 27×27 | ON | 3,331 | 104.3 | 639.5 | **28.54 px** |

- **Positive control passes.** Arm A is 1.97 px — the metric *can* read salt-and-pepper,
  and `M1-A-window-OFF-reg-OFF.png` is visibly exactly that. Without this arm, "arm B has
  blobs" would be unfalsifiable.
- **The window alone (B, 19.41 px) and the regulariser alone (A′, 18.35 px) produce blobs
  of nearly the same size.** Neither is "the" coherence source; they are interchangeable
  in magnitude, and the window is marginally the larger.
- **Pre-registered decision rule, honestly split.** `A(B)/A(C)` = **0.083** on mean area
  (⇒ "ORCH confirmed") but **0.463** on area-weighted (⇒ "partial"). I registered both and
  said I would disclose disagreement. The disagreement is explained: mean area is little
  more than the reciprocal of component count, and arm B fragments into many small
  components *and* retains large ones. **Neither statistic is decisive, so §16 replaces
  the whole question with a direct measurement on the render.**
- **Removing the regulariser does not re-elect a different stack.** Arm B vs shipped over
  the background: **56.2% identical index, 79.0% within ±3 frames** (64.6% / 83.2% after a
  5 px median). The macro-layout survives; the edges get ragged.

`M1-B-window-ON-reg-OFF.png` against `M1-C-shipped-window-ON-reg-ON.png` is the picture:
**the same regions in the same places**, ragged instead of clean.

## 15. P2 — the two quantities ORCH's wording conflates (MEASURED)

| region | winner response | **in noise σ** | margin | **in gate units** |
| --- | ---: | ---: | ---: | ---: |
| background | 8.5489 | **561.9** | 0.07365 | **3.42** |
| subject | 119.0914 | 7827.7 | 1.33043 | 61.84 |

**The data term does not vanish. (MEASURED)** The winner's response in the defocused
background is **562 noise σ**, and **0.00%** of background pixels fall below 3 σ. "The data
term is at the noise floor" is false by three orders of magnitude. This replicates M120's
R1a refutation on an independent construction.

**What *is* small is the margin.** 3.42 gate units against the subject's 61.84 — an **18×**
smaller discriminative signal — and below 1 gate unit on **21.2%** of background pixels
(subject: 1.1%). So the election is **degenerate near its peak**, not data-free. That
distinction is the whole mechanism, and ORCH's phrasing collapses it.

## 16. P3 — the regression. It fires hard, in the direction *opposite* to ORCH's prediction, and refutes my own too. (MEASURED)

Spearman **ρ = +0.6809** (p ≈ 0, n = 347,676) between local margin and the area of the
constant-index component a pixel belongs to.

| margin decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| margin (gate units) | 0.21 | 0.67 | 1.22 | 1.90 | 2.81 | 4.22 | 7.49 | 23.2 | 57.9 | 217.8 |
| **eq. diameter (px)** | **14.1** | 15.1 | 16.2 | 17.6 | 19.7 | 23.3 | 30.2 | 36.5 | 42.2 | **67.6** |

- ORCH pre-registered `ρ < −0.3`, monotone, *"where the data says less, the regulariser
  interpolates further"*. **The data says the exact reverse.** Blobs are **smallest**
  (14.1 px) where the margin is **lowest**, and largest (67.6 px) where it is highest.
- **My own pre-registered prediction (`|ρ| < 0.2`, size pinned at window scale) is also
  wrong.** The relationship is strong. What survives of my account is the *floor*: the
  lowest-margin decile does not fall below ~14 px, which is the window scale, not 1 px.
- The physical reading (ARGUED): a **high** margin means one frame genuinely dominates over
  a wide area, so the constant-index region is large. A **low** margin means near-tied
  frames trade the pixel back and forth, fragmenting the field at the smoothing scale.
  Region size therefore tracks *real* structure, and the regulariser is not interpolating
  into a vacuum.

## 17. The operator price, measured on the render, not the index field (MEASURED)

The index field is not the artifact. This gathers the merged luma under each arm's index
field and applies M120's shipped metric on the registered background ROI (M87-box rows
476:604, cols 442:570), denominator = max over all 299 single frames, `Q_bound = 1.284`.

| arm | window | reg | **Q** | vs bound | Δ vs shipped |
| --- | --- | --- | ---: | ---: | ---: |
| **C — shipped** | 27×27 | ON | **7.166** | 5.58× | — |
| **B** | 27×27 | **OFF** | **6.902** | 5.38× | **−3.7%** |
| **A′** | **OFF** | ON | 7.371 | 5.74× | +2.9% |
| **A** | **OFF** | **OFF** | **3.359** | **2.62×** | −53.1% |
| NULL-1 plain mean | — | — | 0.343 | ✓ | |
| NULL-2 single input frame | — | — | 0.308 | ✓ | |

**Every arm violates the invariant, including the one with no spatial coherence at all.**
`M3-render-B.png` (regulariser off) is still unmistakably crazy paving; `M3-render-A.png`
(both off) is grain rather than paving, and *still* manufactures 2.6× the bound.

**The lever comparison, which is the actionable number. (MEASURED)** Against M120 §9's
gate ladder on the identical ROI and denominator:

| lever | range | Q |
| --- | --- | --- |
| regulariser ON → OFF | — | 7.166 → 6.902 (**−3.7%**) |
| admission width, gate 0 → 16 | `STREHL_GATE` | 7.166 → **0.953** (**−86.7%**, first arm to pass) |

**Admission width is the lever; regularisation is not.**

## 18. P1 and P4

- **P1 — CONFIRMED, constructively rather than by correlation.** §17 *builds* the render by
  gathering pixels through the elected-index field and reproduces the paving. The blobs are
  constant-index regions by construction, which is stronger evidence than M120 §5's
  ρ = +0.5465 (null +0.0077) and supersedes the need for it here.
- **P4 — fires, but *against* ORCH's predicted direction. (MEASURED)** ORCH predicted the
  subject would show "small or no blobs". Using equal-area compact rectangles (the step-15
  masked comparison was confounded: the subject mask was 1.6% of the plane against the
  background's 40.8%, and mask truncation biases small masks' components downward):

  | side | background | subject | ratio |
  | --- | ---: | ---: | ---: |
  | 96 px | 16.0 px, margin 1.37 | **36.3 px**, margin 37.4 | 0.44× |
  | 128 px | 19.9 px, margin 1.61 | **35.3 px**, margin 31.6 | 0.56× |

  Subject blobs are **larger**, consistently with ρ = +0.68. The background is *not*
  distinguished by having big blobs; it is distinguished by having a **small margin**.
  The specificity the control was asked to establish holds on **margin** (1.4–1.6 vs
  31–37 gate units, a 20× separation), not on blob size.

## 19. Verdict on ORCH's hypothesis

**REFUTED.** Taking the hypothesis clause by clause:

| clause | verdict | evidence |
| --- | --- | --- |
| "the through-focus response is flat / the data term is at the noise floor" | **REFUTED** | winner response **562 σ**; 0.00% below 3 σ (§15) |
| "the regulariser then dominates completely" | **REFUTED** | regulariser OFF changes Q by **−3.7%** and leaves the paving visible (§17) |
| "the regulariser is the only thing imposing spatial coherence" | **REFUTED** | false in the source; the 27×27 window is larger, and alone yields 19.4 px blobs (§14) |
| "blob size grows as margin falls" | **REFUTED, sign reversed** | ρ = **+0.68**; lowest-margin decile has the **smallest** blobs (§16) |
| "each region gathers from a different frame, and inter-frame differences are the steps" | **CONFIRMED** | §17 reconstructs the paving by gathering through the index field |

The last row is the part worth keeping, and it was always the sound part.

**What M96 actually established, and why the hypothesis is a plausible over-reach of it.**
`M96-election-margin.md` §5.2 states *"spatial coherence of the elected-index map is
manufactured by the regulariser and is not evidence about the election."* That claim is
**correct and is reproduced here** — arm A′ turns 2 px salt-and-pepper into 18.4 px blobs
using the regulariser alone. But it is a statement about what the regulariser *can* do to
an arbitrary election, not about what *did* produce this artifact. The extension does not
survive contact with arm B.

## 20. The corrected mechanism (ARGUED, and it predicts)

> In the defocused background the through-focus response is **strong** (562 σ) but
> **nearly degenerate near its peak**: the top few frames are separated by ~3.4 gate units,
> against ~62 on the subject. Argmax over a near-tied set is therefore decided by small
> differences, and because the response has already been box-summed over 27 px, the winner
> is spatially coherent over roughly that scale *before the regulariser is reached*. Frames
> differ in background level, so each region gathers a different level and the region
> boundaries become the visible steps. **The spatial operators set the artifact's texture —
> grain → blocks → clean polygons — but not its magnitude.** Magnitude is owned by the
> single-winner election, which is why only admission width moves it.

**Falsifiable predictions this makes, in order of cheapness:**

1. **Regularising harder will not help, and may not hurt much either.** Widening
   `REGULARISER_RADIUS` should move Q by single-digit percent, not fold it.
2. **M116's soft gate should reduce Q substantially but not to the bound.** M120 §9
   predicts gaussian → **2.291** (−47.2%) and exponential → **1.744** (−59.8%) from
   gate 4's 4.337, against a bound of 1.284, affecting 64.8% of the frame. This mechanism
   is the reason: the soft gate acts on admission, the only lever with authority here.
3. **If M116's A/B shows no improvement, this mechanism is in trouble** and the next
   suspect is the *photometric* term — M120 §5 measured 60.9% of the step energy as
   frame-to-frame level drift, so per-frame photometric normalisation would be the
   remaining lever.
4. **A hard prediction that would kill this account:** if someone renders with
   `REGULARISER_RADIUS = 0` and the background comes out smooth, §17 is wrong. It predicts
   Q ≈ 6.9 and visible paving.

## 21. What M120b could not verify, and one correction to the brief

- **M96's `elected-index.tif`, `margin-q8.tif` and `confusion-radius.tif` cannot support
  the quantitative P1/P3 analysis, and the brief's description of them is wrong. (MEASURED)**
  ORCH's instruction was *"All 16-bit — read them with `tifffile`, not PIL."* Read with
  `tifffile` they are **`(2344, 3516, 3) uint8`** with R ≠ G ≠ B and **205 distinct RGB
  triples** — 8-bit **colour-mapped previews**, not index data. They are not PIL-narrowed;
  they are 8-bit on disk. P1–P4 were therefore run on the 299-frame cube, whose argmax
  reproduces the shipped `argbest` at 100%, which is better data than the maps would have
  been. **Anyone computing index statistics from those TIFFs is measuring a colormap.**
- **Arms A, A′ and B are M120b's replication, not Rust output.** The replication matches
  the shipped field at 96.75%; the residual 3.25% is unexplained and is most likely the
  noise-model constants, which were read from `noise.rs` rather than dumped from a run.
- **One stack.** Everything is `bee-3-cpl`. The M96 maps would have given seven, and they
  cannot.
- **The morphology claim is measured only by component count** (40,035 → 3,331, a 12×
  consolidation) **and by eye.** "The regulariser is what makes it look like *paving*
  rather than *grain*" is OBSERVED, not measured with a boundary-sharpness metric.
- **No render A/B was run.** `STREHL_SOFT_GATE` is M116's. The toggles here are the focus
  window and the regulariser, which nothing else is touching.
