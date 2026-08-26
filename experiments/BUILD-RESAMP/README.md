# BUILD-RESAMP — the gather resampler, and what the band metric could not say

Instruments from the run that priced the two candidate causes of
`V-HEADTOHEAD`'s 0.20–0.40 cyc/px deficit. The report is
`docs/research/BUILD-RESAMP.md`; this directory is the machinery, kept so the
numbers can be re-derived rather than believed.

## What is here

| file | what it is |
|---|---|
| `../../crates/strehl-cli/examples/build-resamp-mtf.rs` | the isolated kernel MTF, measured **through `align.rs`'s own `Resampler::sample`** rather than a re-implementation, so it cannot drift from the shipping sampler |
| `band_ratio.py` | band-power ratio between two renders, green channel, with the flat-ROI control and the band-composition decomposition printed on every run |
| `commission.py` | commissions `band_ratio.py`: NULL, a σ=0.5 px Gaussian POTENCY arm scored against the Gaussian's own analytic MTF, and a SIGN arm |
| `spectrum.py` | the same transfer as a 0.01-wide curve instead of five wide bands — this is what made the merge plane's Nyquist visible |
| `render.ps1` | kernel A/B, four subjects × up to four kernels, one pinned binary |
| `render2.ps1` | byte-level commissioning of `--resampler`, plus the `STREHL_ALIGN=zoom` arms |
| `render3.ps1` | the `STREHL_COVER` A/B: the coverage enlargement priced against the identical render |
| `render4.ps1` | the 2×2 headroom grid — kernel and enlargement, separately and together |

## The one thing to know before reusing any of it

**`band_ratio.py` is not a resolution metric and must not be cited as one.** It is
band power. Band power rises under ringing, under aliasing and under noise
exactly as it rises under preserved detail. Measured on this corpus, it awards
`--resampler nearest` — the worst gather in the enum — **+29% at 0.20–0.30 and
+42% at 0.30–0.40** against the shipping Catmull-Rom, a margin larger than the
entire deficit it was built to investigate. Its flat-decile control fails on
every subject.

It is admissible as a *comparison between two kernels whose ringing is
separately bounded*, printed alongside its own controls. It is not admissible as
evidence that one render resolves more than another. For that, use a slanted
edge.

## The trap that would have voided the whole run

`merge_cmd.rs::alignment_for` — if `STREHL_WARPMAP` is set, **the sidecar's own
recorded resampler beats `--resampler`**, and the run says so on stderr. Every
driver here begins by removing that variable. AGENTS.md rule 45 now carries the
warning.

## `STREHL_COVER`

`align_cmd.rs` gained one measurement control: `STREHL_COVER=0` skips
`fit_to_cover` while keeping registration. It is **not a shipping option** — a
render made with it has edge pixels no frame covers, and it says so on stderr.
It exists because the enlargement and the per-frame warp fuse into one matrix
and are paid in one resample, so the only honest way to price the enlargement is
against the identical render with the identical solve from the identical binary.
It is deliberately absent from `SOLVE_ENV`, so both arms share one cached solve.

Commissioned: with `STREHL_ALIGN=0` there is no map to fit, so the switch must be
inert — and the two renders are byte-identical, SHA256 `8AC0AB71…3698`.

## Binaries these numbers came from

| SHA256 | what |
|---|---|
| `0DEBD94E0F26BE5720CE84EA32798ACB558DCFA536F08907A3F27C9331FABD1E` | `strehl.exe` at commit `a7017331`, the kernel A/B |
| `3B3B386DD3F45B7F823D53F1613D280BD8F7A5D494073EF490F4F732290B92E5` | the same plus `STREHL_COVER`, the enlargement A/B |
| `29E6E3F69A0C0E28404F4239FB34F4200174974A7AD8A0FB0B14F8EA6DDB5A20` | `build-resamp-mtf.exe` |

With `STREHL_COVER` unset the first two produce **byte-identical output** on all
four checked pairs, so comparisons spanning them are single-binary in effect.

---

# Phase 2 — the slanted-edge instrument, and why it could not be commissioned

Phase 1 showed the band-power ratio that produced the reported 17–27% deficit
awards a **nearest-neighbour gather +29% / +42%** — more than the whole gap.
Phase 2 was asked to re-price that deficit with a statistic that cannot be
fooled that way: **slanted-edge MTF (ISO 12233)**, which measures resolution
rather than energy.

`slanted_edge.py` is that instrument. `commission_edge.py` commissions MTF50;
`commission_curve.py` commissions the MTF **curve ratio** at fixed frequency.

**Neither statistic passed its controls on this corpus.** Both are committed
anyway, with their failing arms, because the failure is the result.

## The controls, as run

`python commission_edge.py <render.tiff>` — MTF50, 421 sites on
`wrapped-text-1`, ESF support ±32 px, 4× bins, slant 2–10°:

| arm | required | measured | |
|---|---|---|---|
| NULL — a render against itself | ratio 1.000 | `max|ΔMTF50| = 0.000e+00`, 1.000000 | **PASS** |
| POTENCY — Gaussian σ=0.5 px, curve vs `exp(−2π²σ²f²)` | err < 0.05 | worst 0.0272 | **PASS** |
| POTENCY — Gaussian σ=1.0 px | err < 0.05 | worst 0.0743 | **FAIL** |
| SCALE — band-limited 1.2× enlargement | 0.8333 | 1.1672 | **FAIL** |
| NOISE — band power ×46 | ratio 1.00 | 0.7327 | **FAIL** |

`python commission_curve.py <render.tiff>` — curve ratio, 718 sites:

| arm | required | measured | |
|---|---|---|---|
| NULL | 1.0000 at every f | 1.0000, worst err 0.0000 | **PASS** |
| SCALE — 1.2×, predicted from the base's own curve as `M(1.2f)/M(f)` | err < 0.06 | worst 0.3241 | **FAIL** |
| NOISE — band power ×1.45 | err < 0.05 | 0.1160 | **FAIL** |
| NOISE — band power ×47 | err < 0.05 | 0.4016 | **FAIL** |

## Why it fails, which is a fact about the corpus and not about the code

**This corpus contains no ISO 12233-valid slanted-edge target**, including in
the pair the original finding was computed on.

* `flat-on-ruler-cpl`, `highly-angled-ruler-mm-cpl` — the graduations are
  **engraved trenches** with ~20 px sloped walls and a bright specular rim, not
  steps. Per-row edge-centroid scatter 1.95 px on an edge that is straight.
* `C:\dev\macro\out\coffee-bean\stack.tif` — the fork render the original
  finding used — has **no straight edge anywhere**, only the curved bean
  silhouette.
* `wrapped-text-1` — usable, and the best available, but at 1:1 the ink
  boundary is a **stochastic dither** with several px of physical edge wander
  and a wide soft skirt.

The consequence is measurable and it is the whole story: the 50% crossing lands
at **0.011–0.025 cyc/px**, a 40–90 px period inside a 64–128 px ESF support.
Only 1.4–1.6 periods fit, so the **window, not the raster, sets the answer** —
which is exactly what the SCALE arm reports when a 1.2× enlargement moves a
*cycles-per-pixel* read-out by 1.04–1.17× instead of the required 0.833×.

That matters far beyond MTF50: the deficit under investigation lives at
**0.20–0.40 cyc/px**, and on this corpus the edges carry almost no modulation
up there to measure with.

## Four instrument bugs, all found by controls

1. **Per-row centroids do not survive this corpus.** A row's edge gradient is
   ~180 DN/px against dither speckle of several hundred — per-row SNR below 1.
   Replaced with a global angle search minimising the weighted variance of the
   gradient about the candidate line; verified on a synthetic edge to recover
   slope exactly and intercept to 0.01 px.
2. **ROIs must be re-centred on the located edge**, not rejected for landing
   off-centre — that alone discarded ~70% of candidates.
3. **The angle-search score was biased to slope 0 by bin count.** Scoring a
   binned profile over its own natural support penalises shear mechanically.
4. **The comb artefact.** At slope exactly 0 every row projects to the same
   abscissae, so the histogram is a comb whose sum of squares beats anything a
   sheared profile can reach. **3568 of 3570 ROIs fitted below 0.03°** and the
   instrument silently reported that a page of text contains no slanted edge.

## The comparator render

`render7-h2h.ps1` stages one identical stride-6 ARW subset and renders **both**
tools from it. The prior fork
(`C:\dev\macro\focus-stack\dist\focus-stack.exe`, SHA256
`0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D`) holds every
input frame as a full-raster float32 3-channel image, ~396 MB each. Measured on
this machine: **6 / 12 / 24 frames succeed** (48 s / 86 s / 211 s); 33 frames
dies `0xC0000005`; and it OOMs at 22 frames whenever anything else on the
machine is using memory. It is renderable only when the box is otherwise idle.

Two PowerShell traps cost renders here and are fixed in the driver:
`$ErrorActionPreference = 'Stop'` turns a native tool's **stderr progress** into
a terminating `NativeCommandError`, and `STREHL_WARPMAP` silently **beats
`--resampler`**, so every driver clears it first.

## The comparator renders exist, and the first thing they show is a raster mismatch

22 identical ARW from `wrapped-text-1`, one staged directory, both tools linear:

| | raster | wall | exit |
|---|---|---|---|
| fork `0ABA0CF0…` | **6748 x 4472** float32 Rec.2020 | 389.5 s | 0 |
| strehl `0DEBD94E…`, `merge backend : pyramid (--merge)`, `resampler: CatmullRom`, `coverage 0.9476` | **7032 x 4688** uint16 linear camera-native | 21.2 s | 0 |

The fork writes **0.9596x in x and 0.9539x in y** — not even the same factor on
the two axes, so it crops asymmetrically. A band ratio in cycles per **pixel**
is scale-sensitive, so this alone moves the statistic with no resampling
involved. `scale_confound.py` measures it on the real render, nothing assumed
about the spectrum's slope:

| k | 0.20–0.40 band power vs k=1 | what |
|---:|---:|---|
| 1.0000 | **1.0000** | NULL — exact |
| 0.9596 | 0.9530 | strehl resampled to the fork's raster |
| 0.9476 | 0.8753 | strehl's own coverage k |
| 0.5000 | **4.3506** | absurd-value arm |

Two readings, both damaging to the statistic that produced the deficit:

1. The raster mismatch is worth **4.7%** of the 0.20–0.40 band, about a fifth of
   the reported 17–23% gap — and it runs the *flattering* way for strehl, so a
   scale-corrected comparison would report a slightly **larger** deficit, not a
   smaller one.
2. A **0.5x downscale — an unambiguous, catastrophic loss of real resolution —
   scores 4.35x BETTER.** Together with Phase 1's nearest-neighbour result
   (+29%/+42%), the band statistic now demonstrably rewards two separate,
   unambiguous degradations, one of them by more than four times the entire
   effect under investigation.

## Does ISO 12233 share BUILD-SHARP's sensitivity confound? Measured: YES

BUILD-SHARP's ringing detector recovered **1.00x** of a planted overshoot on
synthetic steps, **0.38x** on the fork's render and **0.08x** on ours — 4.75x
more sensitive on one arm than the other, with no ringing anywhere. The
question put to this lane was whether a slanted-edge MTF is immune.

The theory says it should be. In a ratio of two arms

    MTF_blurred(f) / MTF_base(f) = [O.P.G] / [O.P] = G(f)

the object's transfer `O` and the pipeline's transfer `P` cancel identically,
and nothing is compared against an externally calibrated amplitude. The NULL
confirms the cancellation is *exact*: `worst |ratio-1| = 0.000e+00` on **both**
renders.

**The theory is right about the estimand and wrong about the estimator.**
`commission_per_render.py` plants the same Gaussian in each render separately
and reports how much each gives back — BUILD-SHARP's statistic exactly,
`recovery = (1 - measured) / (1 - predicted)`.

`wrapped-text-1`, 22 identical ARW, both renders linear, 400 / 209 sites:

| σ | f=0.100 | f=0.150 | f=0.200 | render |
|---|---:|---:|---:|---|
| 0.5 | 1.139 | 0.962 | 1.042 | strehl `7032x4688` |
| 0.5 | 0.752 | 0.878 | 0.679 | fork `6748x4472` |
| 0.5 | **1.514** | **1.096** | **1.535** | ratio |
| 1.0 | 0.916 | 1.139 | 1.116 | strehl |
| 1.0 | 1.058 | 0.852 | 0.870 | fork |
| 1.0 | 0.866 | **1.337** | **1.283** | ratio |

The instrument is **1.1–1.5x more sensitive on our render than on the fork's**,
and it runs the flattering way round: a cross-render MTF ratio would report
strehl as *more* degraded than it is, manufacturing a deficit in exactly the
direction the premise expected.

The mechanism is in the same table. **ESF fit residual / contrast**, the new
per-edge fit-quality figure:

| render | median | IQR | p95 | usable sites |
|---|---:|---:|---:|---:|
| strehl | **0.1495** | 0.1112–0.2128 | 0.4523 | 400 (capped) |
| fork | **0.3793** | 0.2536–0.5479 | 1.0796 | 209 |

The fork's edges are **2.54x less well described by a 1-D edge model**, and
recovery falls as that residual rises. The estimand cancels; the *estimator's
variance does not*, and its variance is set by the render's own noise and edge
quality — which is the quantity in dispute. Same disease, different organ.

**Consequence: the correction is larger than the effect.** Dividing a
cross-render ratio by a per-render recovery ratio of 1.1–1.5 with this scatter
cannot resolve a 17–23% difference. This instrument, on this corpus, **cannot
price that deficit**, and no absolute MTF magnitude from it may cross an image
boundary.

`MIN_ATTEN = 0.04` was added after the run above: at f=0.05 a σ=0.5 Gaussian
attenuates only 1.2%, so the recovery divides by 0.0123 and the first run duly
printed **−0.967x, a negative sensitivity**. That is arithmetic, not evidence,
and the gate suppresses the column rather than letting it be read.
