# V-REVIEW — adjudication of the nine SHIP-V3 REVIEW rows

Verifier's report. Every number below is labelled **MEASURED** (I ran it and read
the output), **DERIVED** (arithmetic on measured numbers), or **ARGUED** (reasoning,
no measurement). Scripts: `experiments\V-REVIEW\vr_*.py`. Scratch:
`C:\dev\strehl-out\V-REVIEW\`.

---

## 1. Verdict

**Nine ACQUIT, zero CONVICT.** No localisation section is required because no
subject was convicted. `foam` — nominated in the charge as the most likely
genuine conviction — is the *cleanest* acquittal in the table: its master carries
**47% less** mid-scale band energy than its own best source frame.

One row per flagged statistic (four subjects were flagged on both). "source-frame
stat" is the **maximum over registered source frames** — the most hostile
single-frame baseline available, i.e. the merge is compared against the *worst*
frame the bracket offered, exactly as `orch_blotch.py` does.

| subject | stat | master stat | source-frame stat | ratio | verdict | evidence |
|---|---|---|---|---|---|---|
| 112MSDCF | blotch | 0.14667 | 0.14042 (max of 18) | **1.044** | ACQUIT | band DN 2064.8 vs 2181.6 = 0.946x; excess is the denominator (mean 0.922x) |
| 112MSDCF | chroma | 0.034851 | 0.029848 (max of 18) | **1.168** | ACQUIT | absolute chroma DN 0.919x; ratio driven by 1/Y weighting, decile signature is d1-only |
| 113MSDCF | blotch | 0.25168 | 0.23554 (max of 16) | **1.069** | ACQUIT | band DN 2170.9 vs 2398.8 = 0.905x; mean 0.917x |
| 113MSDCF | chroma | 0.025379 | 0.023207 (max of 16) | **1.094** | ACQUIT | absolute chroma 0.907x; d1 carries 31.8% of the excess |
| coffee-bubbles | blotch | 0.09892 | 0.09252 (max of 12) | **1.069** | ACQUIT | band DN 233.8 vs 235.3 = **0.994x**, inside the +-17% frame-to-frame band spread |
| coffee-bubbles | chroma | 0.054596 | 0.060564 (max of 12) | **0.901** | ACQUIT | master below the worst frame outright |
| couch-fibers-cpl | blotch | 0.04511 | 0.05560 (max of 17) | **0.811** | ACQUIT | master below the worst frame outright; band 0.830x |
| flat-on-ruler-cpl | blotch | 0.18363 | 0.19942 (max of 20) | **0.921** | ACQUIT | master below the worst frame outright; band 0.842x |
| flower-inner-edge-cpl | blotch | 0.09921 | 0.09114 (max of 20) | **1.089** | ACQUIT | band 0.972x; an **independent** all-in-focus composite of the same frames reads **0.12097** — 1.22x the master |
| foam | blotch | 0.46075 | 0.52049 (max of 12) | **0.885** | ACQUIT | band DN 3663.7 vs 6950.8 = **0.527x** — the merge removed half the band energy |
| foam | chroma | 0.032503 | 0.036918 (max of 12) | **0.880** | ACQUIT | master below the worst frame outright |
| lead-1-cpl | chroma | 0.020208 | 0.022374 (max of 20) | **0.903** | ACQUIT | master below the worst frame outright |
| leaf-2-cpl | chroma | 0.019727 | 0.022334 (max of 20) | **0.883** | ACQUIT | master below the worst frame outright |

All thirteen: MEASURED (`vr_master.py`, `vr_source.py`, `vr_final.py`;
`C:\dev\strehl-out\V-REVIEW\source_<subject>.json`).

**Seven of the thirteen rows need no argument at all**: the master reads *below*
the worst single source frame. The remaining six (112 blotch+chroma, 113
blotch+chroma, coffee-bubbles blotch, flower blotch) sit between 1.04x and 1.17x
and are adjudicated in sections 4-6.

Not a flagged statistic, recorded for completeness: `lead-1-cpl` blotch 0.00555
(r 1.258) and `leaf-2-cpl` blotch 0.00448 (r 1.138) are 4x *below* the gate's own
0.02 REVIEW threshold. They are not on trial and the ratio there is arithmetic on
numbers near zero.

### The gate's own decision rule, applied

`orch_blotch.py:197`:

> `if r <= 1.3 * mx:` -> `"mid-scale contrast is NOT elevated ... NOT a blotch defect."`

**No subject reaches 1.3x.** The maximum over all thirteen flagged rows is 1.168
(112 chroma); the maximum blotch ratio among flagged rows is 1.089 (flower).
DERIVED from the measured table.

---

## 2. Method — the two arms, and why the source arm is not `orch_blotch.py`'s

`orch_blotch.py`'s built-in source arm reads three frames through **rawpy in
linear light** and its own output says so:

> `band DN master ... source max ... raw, NOT comparable`

It is not comparable *because it compares across a transfer curve* — the exact
failure that invalidated two published numbers in ORCH-veiling.md section 99. The
masters are sRGB-encoded; a linear source frame is a different measurement.

So the source arm here renders **each source RAW through the same pinned binary,
same flags, same exposure stops as the master**:

```
STREHL_ONLY_FRAME=<k>
C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe stack <dir>
    --out <tiff> --srgb --exposure=<the master's own stops, read from its log>
```

Demosaic, CA correction, tone curve and encode are then **common mode**. The only
difference between the arms is the merge. `band_DN` therefore **is** comparable
here, which is what makes section 5 possible. (`vr_lib.py: render_frame`,
`EXPOSURE`.)

The statistics are **imported** from the gate, never retyped:
`vr_lib.py` calls `orch_blotch.py`'s `blotch_ratio`/`flattest` (WIN=900, LO_R=50,
HI_R=400) and `orch_chroma.py`'s `relative_chroma` (WIN=1200, LO_R=50, HI_R=300)
unmodified.

**Master arm reproduces the gate digit-for-digit on all nine rows** — MEASURED,
`vr_master.py`:

```
112MSDCF   0.14667 gate 0.14667   0.0349 gate 0.0349   MATCH
113MSDCF   0.25168 gate 0.25168   0.0254 gate 0.0254   MATCH
...
all reproduced: True
```

Geometry is **measured, not assumed**: the master applies a fit-to-cover crop
(k = 0.8429-0.9887 across subjects) while a one-frame render uses k ~ 0.9974, so
every source frame is registered to the master's window (ORB with >=40 inliers, or
model-initialised phase+ECC; the higher blurred-context NCC wins; floor
`NCC_MIN = 0.75` declared before the run, frames below it excluded and counted).
`vr_lib.py`, `vr_reg2.py`.

---

## 3. Commissioning — proof the instrument can convict

*A comparison needs a control.* Before any verdict, `vr_commission.py` /
`vr_commission_e.py`:

| arm | test | result | MEASURED |
|---|---|---|---|
| A | master warped to itself -> ratio | **1.000000** exactly | yes |
| B | plant a known similarity, recover it | recovered | yes |
| C | warp round-trip bias | 0.9994-0.9995x (blotch), 0.991-0.993x (chroma) | yes |
| D | plant a blotch ladder | monotone **1.004 -> 1.794x** | yes |
| E | plant a chroma ladder | **FAILED as first written** | yes |

**ARM E failed and the failure is reported, not buried.** Mechanism found: the
planted field adds to the existing chroma in RMS quadrature, `sqrt(s^2 + p^2)`, so a
small plant on a large signal is nearly invisible and my linear expectation was
wrong. Rewritten in `vr_commission_e.py`, E1/E2 now match the quadrature
prediction to **0.33%** and **0.9%**. The instrument's blotch detection floor is
therefore quantified (ARM D) and its chroma floor is quantified-with-a-caveat.

Instrument spread, to be respected when comparing two numbers (MEASURED):

* warp round-trip: **0.05%** (blotch), **0.8%** (chroma)
* frame-to-frame scatter among near-peak frames: **~1%**
* **frame-to-frame band spread within one bracket: +-17%** (coffee-bubbles band DN
  ranges 167.5-235.3 across its own frames)

**Consequence, applied throughout:** coffee-bubbles' band ratio of 0.994x and
flower's 0.972x are *not distinguishable from 1.0* at this spread, and are not
claimed to be. They are claimed to be *not above 1.0*, which is all the verdict
requires.

---

## 4. The control that decides the six unresolved rows: a PASS subject

The six rows above 1.0 all rest on the same statistic — "the master's mid-scale
*contrast* exceeds its best frame's by 4-17%". So I ran the identical instrument
on a subject **the gate PASSED**: `109MSDCF` (gate blotch 0.00169, chroma 0.0005 —
12x and 30x *below* the REVIEW thresholds; same rig and same directory family as
112/113).

MEASURED (`vr_source.py 109MSDCF`, 13 frames registered of 13 rendered):

```
BLOTCH  master   0.00169  source max   0.00150 (frame 4)  med   0.00147  RATIO 1.132
CHROMA  master  0.000506  source max  0.000555 (frame 7)  med  0.000512  RATIO 0.911
```

**A gate-PASSED, uncontested master reads 1.132x its own best source frame.**
That is a *higher* ratio than 112MSDCF (1.044), 113MSDCF (1.069), coffee-bubbles
(1.069) and flower-inner-edge (1.089), and effectively equal to leaf-2 (1.138).

The consequence is decisive and it is measured, not argued: **"master contrast >
best-frame contrast" is not a defect marker.** A criterion that convicts
109MSDCF cannot convict 112MSDCF on a smaller number. Every one of the nine
subjects sits inside the range a known-clean master already occupies.

Caveat, stated because it matters: 109MSDCF's flattest window is near-white (mean
63361.8 DN = 96.7% of full scale) so its absolute band energy is trivially small
(107.4 DN). The control establishes the behaviour of the **ratio**, which is the
gate's tone-invariant statistic and the one on trial; it does not claim 109's
window is texturally like 112's.

---

## 5. Why the ratio exceeds 1 — mechanism, measured

A ratio is a fraction. `blotch_ratio = std(band) / mean(window)`. Splitting it
(`vr_bandtable.py`, `vr_final.py`) — MEASURED:

| subject | band DN master / source max | window mean master / source median |
|---|---|---|
| 112MSDCF | **0.946** | 0.922 |
| 113MSDCF | **0.905** | 0.917 |
| coffee-bubbles | **0.994** | 1.070 |
| couch-fibers-cpl | **0.830** | 0.960 |
| flat-on-ruler-cpl | **0.842** | 0.890 |
| flower-inner-edge-cpl | **0.972** | 1.004 |
| foam | **0.527** | 0.930 |
| lead-1-cpl | 1.174 | 0.911 |
| leaf-2-cpl | 1.027 | 0.893 |

**On every blotch-flagged subject the master's actual band energy in DN is at or
below the worst source frame's.** There is no extra structure in the master. The
elevated *ratio* is the smaller denominator.

### Why the denominator is smaller: sharp is dark (Jensen through a concave curve)

Optical defocus averages light **linearly**; the sRGB encode is concave, so
`E[f(x)] > f(E[x])` — a defocused frame's *encoded* window mean sits higher than a
focused one's. A merge that picks focus everywhere therefore lands at the lowest
mean in the bracket, and a ratio with a mean in the denominator rises.

MEASURED (`vr_jensen.py`), correlation across frames between relative HF energy
(sharpness) and encoded window mean:

```
112MSDCF               -0.880   master  14077.5, frames  14403.8.. 18527.8,  0 frame(s) darker  n=18
113MSDCF               -0.226   master   8625.5, frames   8854.6.. 11312.0,  0 frame(s) darker  n=16
coffee-bubbles         +0.243   master   2363.6, frames   2120.6..  2636.5,  9 frame(s) darker  n=12
couch-fibers-cpl       -0.591   master  45867.6, frames  44857.5.. 50142.0,  3 frame(s) darker  n=17
flat-on-ruler-cpl      -0.640   master  47518.1, frames  50856.2.. 56461.3,  0 frame(s) darker  n=20
flower-inner-edge-cpl  -0.963   master  12640.9, frames  11744.9.. 21474.4, 12 frame(s) darker  n=20
foam                   -0.764   master   7951.8, frames   7976.6.. 18568.5,  0 frame(s) darker  n=12
lead-1-cpl             -0.962   master  45909.9, frames  47546.1.. 56714.2,  0 frame(s) darker  n=20
leaf-2-cpl             -0.965   master  45181.1, frames  46275.1.. 55500.7,  0 frame(s) darker  n=20
```

Sharper frame -> darker encoded mean, on 8 of 9 subjects, and on 6 of 9 the master
is darker than **every** frame in its own bracket. That is the merge landing where
the mechanism predicts.

**Where the mechanism does NOT hold, I say so.** `coffee-bubbles` is +0.243: its
master is *brighter* than 9 of 12 frames. The Jensen explanation is unavailable
there — and coffee-bubbles does not need it, because its band ratio is **0.994**,
i.e. the master's band energy equals its worst frame's within an instrument
spread of +-17%. It is acquitted directly on the numerator.

### A second, independent line on flower-inner-edge

flower is the strongest blotch row above 1.0 (1.089). I built an **independent**
all-in-focus composite of its registered frames in numpy — no strehl merge code —
and measured the same statistic (`vr_indep.py`, MEASURED):

```
MASTER                     0.09921    band 1254.2
best single frame          0.09246    band 1226.9
INDEPENDENT hard60         0.12097    band 1541.2      master/this  0.820
INDEPENDENT hard15         0.11454    (band not recorded) master/this  0.866
INDEPENDENT soft60         0.09030    band 1146.8      master/this  1.099
```

A naive per-site sharpest-frame composite of the very same inputs reads **0.121**,
**22% above** the master. Selection over a window whose bracket blotch swings
0.0157 -> 0.0911 *must* raise mid-scale contrast; strehl's master lands well below
the naive version of exactly that operation. Directionally this arm is one-sided
by declaration: reaching the master proves the mechanism; falling short would
prove nothing. Here it overshoots the master, which is the strong outcome.

### The merge is sharper than every input it was given

MEASURED (source_*.json, relative HF energy at the master's own blotch window):

| subject | source frames relHF (min .. max) | span | **master relHF** |
|---|---|---|---|
| 109MSDCF (PASS control) | 0.00243 .. 0.00271 | 1.12x | **0.00287** |
| 112MSDCF | 0.05992 .. 0.07093 | 1.18x | **0.10241** |
| 113MSDCF | 0.07473 .. 0.09050 | 1.21x | **0.14666** |
| coffee-bubbles | 0.12938 .. 0.14655 | 1.13x | **0.17798** |
| couch-fibers-cpl | 0.01001 .. 0.01646 | 1.64x | **0.01875** |
| flat-on-ruler-cpl | 0.00358 .. 0.02097 | 5.85x | **0.02660** |
| flower-inner-edge-cpl | 0.00610 .. 0.01096 | 1.80x | **0.01863** |
| foam | 0.03272 .. 0.12366 | 3.78x | **0.20728** |
| lead-1-cpl | 0.00835 .. 0.00979 | 1.17x | **0.01791** |
| leaf-2-cpl | 0.01468 .. 0.01713 | 1.17x | **0.03277** |

On all ten subjects the master carries **more** high-frequency energy than any
single frame it was built from (1.06x to 1.83x). That is the merge working, and
it is the same fact that depresses the window mean through the concave encode and
so inflates a ratio whose denominator is that mean.

### The merge is sharper than every input it was given

MEASURED (source_*.json, relative HF energy at the master's own blotch window):

| subject | source frames relHF (min .. max) | span | **master relHF** |
|---|---|---|---|
| 109MSDCF (PASS control) | 0.00243 .. 0.00271 | 1.12x | **0.00287** |
| 112MSDCF | 0.05992 .. 0.07093 | 1.18x | **0.10241** |
| 113MSDCF | 0.07473 .. 0.09050 | 1.21x | **0.14666** |
| coffee-bubbles | 0.12938 .. 0.14655 | 1.13x | **0.17798** |
| couch-fibers-cpl | 0.01001 .. 0.01646 | 1.64x | **0.01875** |
| flat-on-ruler-cpl | 0.00358 .. 0.02097 | 5.85x | **0.02660** |
| flower-inner-edge-cpl | 0.00610 .. 0.01096 | 1.80x | **0.01863** |
| foam | 0.03272 .. 0.12366 | 3.78x | **0.20728** |
| lead-1-cpl | 0.00835 .. 0.00979 | 1.17x | **0.01791** |
| leaf-2-cpl | 0.01468 .. 0.01713 | 1.17x | **0.03277** |

On all ten subjects the master carries **more** high-frequency energy than any
single frame it was built from (1.06x to 1.83x). That is the merge working, and
it is the same fact that depresses the window mean through the concave encode and
so inflates a ratio whose denominator is that mean.

---

## 6. Chroma adjudication

Four of the six chroma rows are below their worst source frame outright
(coffee-bubbles 0.901, foam 0.880, lead-1 0.903, leaf-2 0.883). Two are above:
112MSDCF 1.168 and 113MSDCF 1.094.

`orch_chroma.py`'s statistic is `(R-Y)/Y, (B-Y)/Y` — **relative** chroma. Splitting
relative from absolute (`vr_chroma2.py`, MEASURED):

| subject | relative chroma ratio | **absolute** chroma DN ratio |
|---|---|---|
| 112MSDCF | 1.142 | **0.919** |
| 113MSDCF | 1.089 | **0.907** |
| coffee-bubbles | 0.844 | 0.987 |

The master carries **less** colour excursion in DN than its frames. `(R-Y)/Y` is
invariant to a per-pixel gain on all three channels, so "the master is darker"
cannot by itself raise it; what raises it is `1/Y` **weighting** — the same colour
structure divided by a deeper shadow. At 112's chroma window the master's 5th
luminance percentile is **9166 DN** against **10287+ DN** for every frame.

A weighting effect and a manufactured mottle have different signatures, so I
measured the signature (`vr_ydecile.py`, MEASURED). Master/frame chroma ratio by
master luminance decile, 112MSDCF:

```
d1 1.581  d2 1.145  d3 1.043  d4 1.004  d5 0.980  d6 1.182  d7 1.152  d8 1.087  d9 1.082  d10 1.078
```

The excess is concentrated in **d1 — the darkest decile, 18% of the window
variance** (113: d1 1.219, carrying 31.8%). A blotch planted as a positive
control instead lifts the **mid** deciles: d4 **1.31**, d5 **1.43**, d6 **1.33**,
d7 **1.29**. The observed signature is the `1/Y` signature, not the plant's.

**The one control here that did not work, reported as such:** blurring the master
to imitate a defocused frame. v1 blurred an *already encoded* image, which is
mean-preserving and proved nothing (window mean Y moved 0.003%). The fixed
version decodes -> blurs -> re-encodes and does move the mean, but at sigma <= 10 px
it closes only about a third of the gap, and real frames are far more defocused
than sigma=10. **That control is INCONCLUSIVE** and is not counted as evidence.

### A note on the gate's chroma baseline rule

`orch_chroma.py`'s header states the source baseline is the **minimum** over
frames, and gives its reason:

> "because a merge that averages N frames should beat every one of them on colour noise."

strehl does not average; it **elects**. Under the minimum rule **all ten subjects
I measured fail** (master/min 1.043 to 3.843, MEASURED, `vr_final.py` column
`rc_mn`) — including gate-PASSED `109MSDCF` at 1.043. I did not measure the other
16 masters, so I claim it for ten, not for the corpus. Both baselines are therefore reported above (`rc_mx`, `rc_mn` in
`vr_final.py`), and the verdicts are taken on the max — the same baseline
`orch_blotch.py` uses for its own verdict line.

Partial support for why the minimum is the wrong baseline, MEASURED
(`vr_minrule.py`, Pearson r between per-frame chroma and per-frame sharpness):
**+0.730 foam, +0.675 leaf-2, +0.658 flower, +0.619 lead-1** — on these four the
minimum-chroma frame is literally the least sharp frame, so no in-focus image can
meet it. But it is **-0.698 on coffee-bubbles and -0.665 on couch-fibers**, where
that explanation does not hold. Reported per subject; not generalised.

---

## 7. Instruments that failed their own controls (rejected, not used as evidence)

*A search that cannot fail is not a search.* Four instruments were built and
discarded because their own positive controls refused them:

1. **`vr_grid.py`** (first-difference comb for merge-tile seams) — FAILED its
   plant. Mechanism: `mean|delta|` is dominated by pixel noise; a coherent step `b`
   raises `E|a+b|` by only `b^2/2*sigma^2`.
2. **`vr_grid2.py`** (spectral version) — FAILED. A 113 DN comb is ~0.5% of a
   per-bin noise floor that itself fluctuates 3.3%.
3. **The sharpen-model fit in `vr_novel.py`** — R^2 = 0.001-0.03 everywhere
   *including the null*. Dropped.
4. **The blur control in `vr_blurtest.py`** — inconclusive, see section 6.

The **cross-hatch** visible in the contact sheets was chased to ground and is
*not* evidence of a defect (MEASURED, `vr_pitch.py`, `vr_hatch.py`): real, pitch
33-37 px, not a float32 artefact of the gate's boxblur (that contributes 0.034% of
the band). But a **single-frame render's** hatch is **1.170** against the master's
**1.125** — the merge *reduces* it — and it carries ~0.1% of band power, far too
little to move any flag. Detection floor of that instrument, from its own plant
ladder: 24 DN -> 1.228, 71 DN -> 2.318, 142 DN -> 6.161, 284 DN -> 21.80.

The **novel-structure discriminator** (`vr_novel.py`) did work and did convict its
plant: 112MSDCF master-vs-frame band correlation **+0.994 / +0.993 / +0.995** with
11-12% residual (113: +0.992, 14%), while a planted 2-sigma mottle collapses the same
statistic to **+0.664 with 74.9% residual**. Viewed as pictures: the clean
residual is the subject's own dendrites; the planted one is leopard blobs.
On **coffee-bubbles** the discriminator is **uninformative** — a frame put in the
master's chair scores +0.66..+0.76 / 68-79% residual, indistinguishable from the
master's +0.67..+0.71 / 75-77% — and it is reported as uninformative there, not
as a finding.

---

## 8. The envelope test, and its honest limit

`vr_envelope.py` asks a harder question than the ratio: does the master's band
field leave the per-pixel **envelope** of its own frames? Leave-one-out null =
each frame judged against the others. MEASURED:

| subject | master outside | LOO null median | ratio | master mean excess | null median | plant (1 sigma) |
|---|---|---|---|---|---|---|
| 112MSDCF | 40.19% | 8.38% | 4.79x | **0.0253 sd** | 0.0016 sd | **0.2977 sd** (79.84%) |
| 113MSDCF | 41.23% | 6.47% | 6.37x | 0.0269 sd | 0.0009 sd | — |
| coffee-bubbles | 22.23% | 11.06% | 2.01x | 0.0552 sd | 0.0315 sd | **0.4180 sd** (69.65%) |
| flower-inner-edge | 16.77% | 5.10% | 3.29x | 0.0226 sd | 0.0009 sd | — |

The master leaves the envelope more *often* than a held-out frame does. Two
measurements bound what that means:

1. **Magnitude.** The master's mean excursion is **0.023-0.055 sd**. A planted
   1-sigma mottle is **0.2977 sd** (112) and **0.4180 sd** (coffee-bubbles) — **8x to
   12x larger**. The master's excursions are an order of magnitude below the
   level at which this instrument convicts.
2. **Sampling bias, measured rather than asserted.** The envelope is built from a
   *subsample* of the bracket while the master used all of it, and a thinner
   envelope is narrower — the test is biased toward conviction. Thinning it
   proves the bias is large (MEASURED):

```
112MSDCF   envelope from  5 of 20 frames: master outside 56.91%  mean excess 0.0394 sd
           envelope from 10 of 20 frames: master outside 47.45%  mean excess 0.0313 sd
           envelope from 20 of 20 frames: master outside 40.19%  mean excess 0.0253 sd
113MSDCF   envelope from  6 of 21 frames: 51.52% / 0.0385 sd -> 21 of 21: 41.23% / 0.0269 sd
flower     envelope from  6 of 21 frames: 26.37% / 0.0481 sd -> 21 of 21: 16.77% / 0.0226 sd
```

Every doubling of envelope density removes ~21% of the excess; 112's true bracket
is 79 frames, roughly two further doublings (DERIVED: 0.0253 x 0.79^2 ~ 0.016).

My reading is that this test detects **selection**, not invention: the master
takes a different frame at each site, so wherever depth varies it necessarily
steps outside the *local* envelope of any single frame while remaining made
entirely of frame content. That reading is **ARGUED**, and I mark it as such. It
does not change any verdict, because the two measurements above show the
excursion magnitude is 8-12x below the instrument's own conviction level and
still falling as the envelope is filled in. **If it is to be relied on for
anything, it needs a full-density envelope; that is a stated gap, not a result.**

---

## 9. Per-subject notes

* **112MSDCF / 113MSDCF (both)** — band DN 0.946x / 0.905x, absolute chroma 0.919x
  / 0.907x. Discriminator: +0.994 / +0.992 correlation with frame band structure
  (plant control collapses to +0.664). Chroma excess is d1-only (darkest decile).
* **coffee-bubbles (both)** — chroma 0.901x outright. Blotch band 0.994x, inside
  the +-17% spread. **Two of my instruments do not apply here and I say so**: the
  Jensen mechanism (corr +0.243, master brighter than 9/12 frames) and the
  novel-structure discriminator (frame-in-master's-chair null is
  indistinguishable). Acquitted on the numerator, which needs neither.
* **couch-fibers-cpl (blotch)** — 0.811x. Below the worst frame outright.
* **flat-on-ruler-cpl (blotch)** — 0.921x, band 0.842x. Below outright.
* **flower-inner-edge-cpl (blotch)** — 1.089x contrast but band 0.972x, and an
  independent all-in-focus composite of the same frames reads **1.22x the
  master**. Window bracket blotch swings 0.0157 -> 0.0911: this is a genuine
  multi-depth window and selection is doing its job.
* **foam (both)** — nominated as the likely conviction; it is the strongest
  acquittal. Blotch 0.885x, **band DN 0.527x**, chroma 0.880x. The stack did move
  during capture, and the visible consequence is in the *frames*: foam's
  frame-to-frame sharpness range is the second widest measured here (relHF
  0.03272 -> 0.12366, span 3.78x; only flat-on-ruler-cpl is wider at 5.85x)
  and its worst frame carries **6950.8 DN** of band energy against the master's
  **3663.7**. The merge did not manufacture foam's reading; it halved it. What
  remains at 0.46075 is the subject: foam is 900 px of bubble wall at every depth
  in the window.
* **lead-1-cpl / leaf-2-cpl (chroma)** — 0.903x / 0.883x outright. Their blotch
  numbers (0.00555, 0.00448) are 4x below the REVIEW threshold and are not on
  trial.

---

## 10. Declared gaps — what this report does NOT establish

1. **The pyramid is common mode.** Both arms run the same Laplacian analysis and
   synthesis (a single-frame render goes through it too). Any defect intrinsic to
   analysis/synthesis is therefore **invisible to this comparison by
   construction**. This adjudication answers "did the *merge selection* invent
   this?", not "is the pyramid perfect?".
2. **The source max is over a sampled bracket** (12-21 frames of brackets up to
   79), chosen coarse-then-refine around the peak. A frame I did not render could
   read higher, which would only *strengthen* an acquittal — but the baseline is
   a sampled maximum, not a true one.
3. **Frames below NCC 0.75 were excluded** (floor declared before the run, counts
   recorded per subject in `source_*.json`). foam and coffee-bubbles lost the most.
4. **`orch_chromapair.py` was never run.** It hard-codes SHIP-V2 paths; using it
   would have meant copying and editing it. The chroma statistic was instead
   imported directly from `orch_chroma.py` and reproduced the gate's printed
   chroma value for all nine rows (MATCH), so the adjudicated quantity is the
   same number the gate printed — but the pair tool itself is unexercised.
5. **The blur control is inconclusive** (section 6). The sharp-is-dark mechanism
   rests on the measured correlation table, not on that control.
6. **The envelope test needs a full-density envelope** (section 8) before it can
   be relied on for anything.
7. **Partially closed — see section 12.** `vr_baseline.json` +
   `vr_recheck.py` now freeze the ruling and re-derive it on demand, commissioned
   with three RED cases and one GREEN. **What remains open:** the checker
   re-derives only the MASTER half (the source-frame comparison is frozen), and
   its measured detection floor is coarse — reliable only at >= 3200 DN of planted
   mid-scale mottle, with detection at 400-800 DN a coin flip decided by a
   cross-term whose sampling sd is ~0.22. It will catch a rebuilt or altered
   master; it will not catch a subtle one. It is not wired into
   `orch_printready.py` (that file belongs to another agent).

---

## 11. File ownership

Everything created is inside `experiments\V-REVIEW\` (scripts, this report) or
`C:\dev\strehl-out\V-REVIEW\` (scratch JSON/PNG/NPY). **No file under `crates\`,
`scripts\`, `docs\`, `README.md` or `experiments\ORCH-drift-check\` was created,
modified or deleted**; `orch_blotch.py` and `orch_chroma.py` were *imported* and
read only. No `git add -A` and no `git commit` was run. `D:\` was read only. No
existing script needed a modified copy: the gate's statistics were usable by
import as they stand.

`git status` at the end of this work does show modifications under `crates\` and
`docs\research\BUILD-DEFECT.md`. **Those are other agents' — this is a shared
working tree.** Their timestamps (02:12-02:39) fall inside this session's window
(01:15-02:39) precisely because other agents were editing concurrently. The only
paths this work wrote are `experiments\V-REVIEW\` and `C:\dev\strehl-out\V-REVIEW\`.

That concurrency does **not** contaminate the measurements: both arms used the
**pinned** binary `acceptance-pins\740e7056\target\release\strehl.exe`
(built 26 Aug 23:49:22, 9 568 768 bytes — before this session began and untouched
throughout), and the masters under `acceptance\SHIP-V3\` are dated 27 Aug 00:04.
Neither is the working-tree build the other agents are changing.




---

## 12. The standing check (closes gap 7, partially)

Gap 7 said these nine verdicts were perishable — they lived only in scripts and
nothing would notice if a merge change moved them. Three artifacts now stand:

* **`vr_baseline.json`** — the frozen ruling. Per subject: the adjudicated master
  statistics, the source-frame value each was ruled against, the ratio, and the
  one-line acquittal reason. 10 subjects (the 9 REVIEW rows plus the `109MSDCF`
  PASS control, which is the load-bearing evidence and must not rot either).
  Schema `vr-baseline/1`.
* **`vr_freeze.py`** — regenerates it from the measured `source_*.json`.
* **`vr_recheck.py`** — re-derives the master half from any masters directory and
  partitions every baseline subject into **HELD / MOVED / MISSING / NOT-EXAMINED**.
  The partition is asserted to sum to the baseline count before anything prints.

**GREEN requires `held == total AND total > 0`.** An empty directory, an empty
baseline, or a filter that matches nothing all exit RED — a count that did not
move is not a pass.

**Scope limit, printed on every run:** this re-derives the **master** half only.
The source-frame comparison is frozen. GREEN means "the masters still read what
was adjudicated", **not** "the merge is still innocent". If the merge changes,
`vr_source.py` must be re-run.

### Commissioning — the RED runs

An uncommissioned checker is one green light of unknown meaning.

| case | setup | expected | MEASURED |
|---|---|---|---|
| C1 | real `SHIP-V3\`, all 10 | GREEN | `held 10 moved 0 missing 0 not-examined 0`, every delta **0.000%**, exit **0** |
| C2 | 1 perturbed + 1 clean copy + 8 absent | RED, naming both | `held 1 moved 1 missing 8 not-examined 0`, exit **2** |
| C4 | empty directory | RED | `held 0 moved 0 missing 10`, exit **2** |
| C5 | `--only no-such-subject` | RED | `held 0 ... = 0 subjects`, `RED no subjects examined`, exit **2** |

C2 verbatim — the case that matters, because a missing master must not read as a
held one:

```
112MSDCF               MOVED           0.14169   0.033877   3.399%  blotch 0.14667 -> 0.14169 (-3.40%); chroma 0.034851 -> 0.033877 (-2.80%)
leaf-2-cpl             HELD            0.00448   0.019727   0.000%  r_blotch 1.138 r_chroma 0.883 vs frozen source max
...8 MISSING...
PARTITION  held 1  moved 1  missing 8  not-examined 0  = 10 subjects in baseline
RED    MOVED: 112MSDCF -- acquittal is STALE, re-adjudicate
       MISSING: 109MSDCF, 113MSDCF, coffee-bubbles, couch-fibers-cpl, flat-on-ruler-cpl, flower-inner-edge-cpl, foam, lead-1-cpl
```

### The detection floor, and the seed-luck trap I walked into

The first ladder (`vr_perturb.py`, seed 7) planted mid-scale mottle into
112MSDCF and the checker went RED at 400 DN. **That number was luck and I nearly
reported it.** Two things were wrong with it.

First, the reading moved the **wrong way** — planting *energy* at 800 DN
*lowered* blotch 0.14667 -> 0.14169. Mechanism, MEASURED (`vr_whydown.py`,
`vr_whydown2.py`): not window relocation (the picker moved 16 px), not clipping
(**0.000%** of the window clipped, and clipped and unclipped results are
identical to 8 significant figures). It is the **cross-term**. At the frozen
window:

```
clean                  band  2064.80    PLANT ALONE  band 444.20
clean+plant            band  2014.82    quadrature would predict 2112.04
=> corr(plant, existing band) = -0.219
```

Second, that correlation is **sampling noise**, and seed 7 was its worst draw. A
900 px window band-passed at 50-400 px holds only ~20 independent blobs, so the
expected sampling sd of that correlation is ~1/sqrt(20) = 0.22. MEASURED over 8
seeds: corr ranges **-0.219 to +0.132**, and seed 7 is the most negative of the
eight.

Detection rate, MEASURED across 8 seeds at 112MSDCF, tol = 2%:

| plant sd | resulting blotch, min .. max | \|delta\| min .. max | **fires** |
|---|---|---|---|
| 400 DN | 0.14353 .. 0.15061 | 0.15% .. 2.69% | **3 of 8** |
| 800 DN | 0.14209 .. 0.15685 | 0.26% .. 6.94% | **3 of 8** |
| 1600 DN | 0.14435 .. 0.17533 | 1.59% .. 19.54% | **7 of 8** |
| 3200 DN | 0.16646 .. 0.22940 | 13.49% .. 56.40% | **8 of 8** |
| 6400 DN | 0.24830 .. 0.37196 | 69.29% .. 153.59% | **8 of 8** |

**Honest floor: reliable (8/8) only at >= 3200 DN of planted mid-scale mottle** —
which is 23% of that window's mean and 1.55x its entire band energy. At 400-800
DN detection is a coin flip whose outcome is decided by the cross-term, not by
the plant's own power. This is a coarse instrument and it is stated as one.

Two consequences I am obliged to carry back:

1. **It qualifies my own ARM D ladder** in `vr_commission.py`, which used a
   single fixed seed. Its monotone 1.004 -> 1.794x is real but its low rungs
   inherit this +-2-3% seed scatter; only the high rungs are seed-independent.
2. **It is a property of the gate's statistic, not just of my checker.** Any
   single-realisation plant against a 900 px / 50-400 px window carries ~+-0.22 of
   cross-term correlation with whatever is already there. Anyone commissioning an
   instrument on this statistic with one seed will get a number they cannot
   reproduce.

### Format, if the gate should consume it

`vr_baseline.json` is `{"schema","arm","gate_rule","provenance","subjects":{...}}`;
each subject carries `flagged_for`, `verdict`, `reason`,
`n_source_frames_registered`, `master{blotch, blotch_band_dn, blotch_mean_dn,
blotch_window_yx, chroma, chroma_window_yx}`, `source_frame_max{blotch, chroma,
blotch_band_dn}` and `ratio{blotch, chroma, blotch_band_dn}`. `orch_printready.py`
was **not** modified — it is yours and you are editing it. If you want the gate to
read this, the smallest wiring is: on a REVIEW row, look up `subjects[<name>]`,
and if `master.blotch` still matches within tolerance, print `reason` and
`ratio.blotch` beside the REVIEW instead of re-deriving anything. Tell me if you
want a different shape and I will re-emit it; nothing depends on the current one
but `vr_recheck.py`.

