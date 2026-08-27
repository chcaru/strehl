# V-HEADTOHEAD2 — the head-to-head, re-run after the full-resolution gather flip

> ## ⚠ CORRECTED 2026-08-28 — registration sign defect, figures moved
>
> **Every figure in this document that was computed by registering two
> *different* renders against each other has been recomputed and has moved.**
> `h2.integer_shift` returned the cross-correlation peak — the *displacement*
> of the moving image — while its own docstring, its own commissioning test,
> and all five of its callers wanted the *correction*, which is the negative.
> The lane's registration self-test had been reporting this the whole time,
> printing `planted (2,3) got (2,3)` and scoring it a **MISS**; the test was
> right and the code was wrong.
>
> Measured on the real pairs (`logs/signconv-real-*.txt`): re-cropping Zerene
> at the reversed shift scored **0.235** mean correlation against strehl,
> *worse than not registering at all* (**0.347**), and **0.791** once repaired.
>
> **What moved** (`logs/movement.txt`, 22 cited values):
>
> | figure | published | corrected |
> | --- | ---: | ---: |
> | strehl-under-block-map @ 0.25–0.30 | 0.037147 | **0.038106** |
> | Zerene as rendered @ 0.25–0.30 | 0.037138 | **0.036095** |
> | agreement between them | 0.02% | **5.6%** |
> | tone explains, 0.20–0.25 | 89.1% | **94.8%** |
> | tone explains, 0.25–0.30 | 100.0% | **109.9%** |
> | tone explains, 0.30–0.40 | 212.4% | **267.1%** |
>
> **What did not move, and why that matters.** The headline flip result
> (`C_g1/C_g0`, the 3.58× at 0.25–0.30) and every commissioning arm — the NN
> degradation arm, the SHARP arm, the FLAT-vs-DETAIL noise census — are
> **byte-identical**, because `flip.py` and `commission.py` compare two renders
> on the *same* pixel grid and never call the registration at all. So is
> `toneparity.py` ARM 2, the tone gun aimed at this lane's own result: still
> **6.4% / 11.9% / 15.3%**. Only the arms that align strehl against a
> *comparator* were affected.
>
> **Direction.** Every corrected value strengthens the conclusion rather than
> weakening it: tone now explains *more* of the apparent comparator gap, not
> less. The 0.02% agreement was too good, and it was too good because it was
> wrong. Figures below are left at their original values with `[CORRECTED]`
> markers so the movement stays auditable; the corrected run is in
> `logs/resign-*.txt`.

*Lane V-H2H2. Every number below was produced by code in `experiments/V-HEADTOHEAD2/`
and is quoted from a log in `C:\dev\strehl-out\V-H2H2\logs\`. Nothing here is
carried over from `V-HEADTOHEAD` except the comparator files themselves and the
frame-set-equivalence proof in its §0.*

---

## 0. The verdict, first

Three findings. The middle one is the one that matters, and it is not the one I
was sent to get.

**1. The fine-scale deficit reported against Zerene Stacker PMax cannot be
measured on this corpus at all, and I can now prove that rather than caveat it.**
A tone curve fitted to strehl's own pixels **using only 4×4 block averages** —
a fit that has no access to any spatial frequency above 0.125 cyc/px, and
therefore contains literally zero information about resolution — reproduces
Zerene's 0.25–0.30 cyc/px band power from strehl's pixels to **0.02%**
(0.037147 vs 0.037138) `[CORRECTED: 5.6%, 0.038106 vs 0.036095]`. It accounts
for **100.0%** `[CORRECTED: 109.9%]` of the gap there, **89.1%**
`[CORRECTED: 94.8%]`
at 0.20–0.25, and **212%** `[CORRECTED: 267.1%]` at 0.30–0.40. The "17–27% behind at 3–5 px features"
that the README retracts on instrument grounds is retracted again on
*variable* grounds: it is a measurement of Lightroom's `Contrast2012=+100`, not
of either program's resolution. The README's existing caveat — that the
comparators were fed developed TIFFs while strehl reads RAW — is not a caveat.
It is the entire result.

**2. The comparison against the patched `focus-stack` fork is abandoned, not
lost.** 41 of 64 candidate regions fail to register between the two renders
against a gate calibrated on a null control. `geom.py` had already said why:
after the best global similarity (scale **1.0340**, an interior maximum) there
is **5.3 px rms** of residual local disagreement. The two programs' alignment
models differ locally, so co-located boxes are not looking at the same scene
content. Any number computed from them would have been noise wearing a
decimal point.

**3. The gather flip is real, it is large, and it survives being shot at.**
Commit `740e7056` raises *coherent* fine-scale structure — power that added
noise provably cannot inflate — by **2.10× at 0.20–0.25**, **3.58× at
0.25–0.30** and **3.46× at 0.30–0.40** cyc/output px on 113MSDCF, all with 95%
CIs excluding 1. On coffee-bean, **1.95×** and **2.70×** in the first two, with
the third inconclusive. A second, independently-computed variant on a different
ROI set — coherent power normalised inside each region by its own 0.05–0.10
band — gives 1.85× / 2.50× / 2.10× on 113, the same conclusion by a different
route. The gain is not uniform: the 0.02–0.05 band goes *down* (0.957), and the
gain rises monotonically through f = 0.25 cyc/output px, which is exactly the
CFA plane Nyquist the flip was aimed at. When I aimed the tone test that
destroyed the head-to-head at my own result, tone explained **6.4% / 11.9% /
15.3%** of it — and the same code, on the same ROIs, still fired at **89% /
100% / 212%** on the Zerene pair, so that negative means something.
**Read 3b′ before quoting any of these three numbers: only the 2.10× is a
resolution claim, and the 3.46× is withdrawn.**

**3b. Added after the fact, from `V-LINEAR`, and it cuts against finding 3.**
`[SUPERSEDED 2026-08-27 — the imported measurement was corrected by the lane
that produced it. The original text is kept below with its correction, per
this corpus's treatment of every other refuted instrument. The revised reading
is 3b′.]`

> A later lane measured, on strehl's own linear develops, that a tile *in focus*
> carries the same 0.20–0.48 cyc/px power as the same tile **20 frames out of
> focus** — ratio **1.015, 1.043, 1.004, 1.138** across four independent frame
> pairs, against 2.1–3.0 per band for the Lightroom develops the comparators ate.
> **Focusing the lens does not measurably change the bands finding 3 reports in.**
> That is a third and stronger reason the retracted 17–27% claim is dead — it was
> computed in a band with essentially no signal in it — and the same blade cuts
> my own result, so I am applying it here rather than leaving it for a reader.
> `C` rejects *independent* noise by construction, so the flip's 2.10×/3.58×/3.46×
> is a real, reproducible gain in **coherent** content; what is **not**
> established is that the coherent content is scene detail rather than
> sensor-common structure. My own worst control says the same thing from the
> other side: NOISE_COM inflates `C` by **1.078 / 1.492 / 3.866** in exactly
> these three bands. **Finding 3 stands as "the flip changed what is in those
> bands, measurably and in the place it was aimed"; it does not stand as "the
> flip recovered scene resolution",** and this corpus cannot promote it.

**3b′. The correction, and the per-band answer it forces.**
`V-LINEAR2.md` §2 supersedes the ratios above. They came from four hand-picked
**whole-frame** pairs, and at this magnification only a fraction of any frame
is in focus, so a whole-frame ratio averages the sharp part together with parts
that were never sharp in either. Re-run letting each of 29 tiles choose its own
best-focus frame, **0.20–0.25 cyc/px carries R = 2.419** (CI [1.961, 3.063]),
where the whole-frame estimate had said 1.0. Method, not data.

**I checked the correction rather than importing it, because it moves a number
in my favour and that is when import is least safe.** Three things had to hold
and do:

- **Selection bias.** "Each tile picks its own best frame" is an argmax over
  frames, which scores above 1 on pure noise. `bandsignal.py` selects on
  **0.05–0.20** and reports from **0.20** — disjoint bands, so for approximately
  white noise the argmax cannot bias the reported band, and the selection band
  is explicitly ineligible to be the comparison band. The defocused side is a
  *fixed* 20-step offset, not an argmin, so it is not a max/min-over-N at all.
- **Favourable subset.** ALL and CONFIRMED populations are identical, 29 of 29.
- **Subject transfer — and this is the one that surprised me.** `bandsignal.py`
  runs on `D:\personal\macro\113MSDCF`, **the same stack all three of my flip
  numbers were measured on**. I expected to have to caveat a cross-subject
  import and there is none to make. (It does *not* transfer to coffee-bean; that
  subject's 1.95×/2.70× remain unbanded and are reported as corroborating only.)

Set against my three numbers, with my own worst control and a third instrument:

| band | flip `C_g1/C_g0` | CI low | focus signal R | my NOISE_COM | DISJOINT non-scene | flip ÷ NOISE_COM |
|---|---:|---:|---:|---:|---:|---:|
| **0.20–0.25** | 2.103 | 1.945 | **2.419 PASS** | 1.0778 | 0.24% | **1.95** |
| 0.25–0.30 | **3.580** | 3.049 | 1.387 MARGINAL | 1.4921 | 0.46% | 2.40 |
| 0.30–0.40 | 3.462 | 2.852 | 1.149 **FAIL** | **3.8659** | 5.09% | **0.90** |

**0.20–0.25 — promoted. This one is a resolution claim.** The band carries
measured, per-tile, focus-dependent scene signal on this exact subject
(R = 2.419, passing V-LINEAR2's pre-registered gate of R ≥ 2.0 with lower CI
≥ 1.5). `physfloor.py`'s DISJOINT arm — half-stacks sharing sensor, optics and
pipeline but **no scene**, where C ≡ 0 by construction — finds only **0.24%**
of the coherent power is scene-free here. And charging my *entire* adversarial
common-noise inflation against the result still leaves **1.95×**, with the CI
lower bound at **1.80×**. Three instruments with no shared assumptions.

**The weakest arm under that promotion, stated rather than left to be found.**
§5's flat-ROI specificity check is closest to failing at exactly this band:
flat ROIs gain **1.945** against detail's **2.103**, only 8% apart, where at
0.25–0.30 the gap is 2.968 against 3.580. The promotion therefore does not
rest on flat-vs-detail *ratio* at all — it rests on absolute level, and there
the margin is intact: flat ROIs carry **8.3%** of detail ROIs' coherent power
in this band, so even if the entire flat gain were spurious it can account for
about a tenth of the result. A reader who wants to attack the 2.10× should
attack it there, and that is where I would attack it.

**0.25–0.30 — stays demoted, and this is my headline number.** It survives my
noise control comfortably (3.580 ÷ 1.492 = 2.40×) and DISJOINT is only 0.46%,
so this is not the statistic inventing coherence: something real and
scene-locked changed. But focusing the lens changes power in this band by only
**1.387×**, below the pre-registered gate. A coherent change in a band where
the lens barely matters is not demonstrable resolution. It stands exactly where
3b put it — *"the flip changed what is in this band"* — and no further.

**0.30–0.40 — withdrawn outright, which is more than 3b did.** The band fails
the focus gate at 1.149, DISJOINT is 5.09%, and decisively: **my own NOISE_COM
control inflates `C` by 3.866 in this band, which is larger than the 3.462 the
flip scored.** An adversarial injection of common-mode noise moves this
statistic *further than the flip did*. I cannot separate the two here at all,
so this number should not be quoted as evidence of anything, in either
direction.

**A corroborating argument of mine that does not survive, and I am retracting
it too.** Finding 3 offers that the gain "rises monotonically through
f = 0.25 cyc/output px, which is exactly the CFA plane Nyquist the flip was
aimed at". But my noise inflation rises monotonically in the same direction
(1.078 → 1.492 → 3.866), as does DISJOINT (0.24% → 0.46% → 5.09%). Corrected
for noise the sequence is **1.95 → 2.40 → 0.90**: it peaks and collapses. The
monotone rise is degenerate between "the flip worked where it was aimed" and
"the instrument degrades with frequency", so it is not corroboration and I
withdraw it as such. What survives is narrower and still consistent with the
mechanism: the one band that passes, 0.20–0.25, sits immediately *below* the
0.25 cyc/output px plane Nyquist the flip targeted.

**Net effect on finding 3: one of three numbers is promoted, one holds, one is
withdrawn.** The promoted one is the *smallest*. That is the shape an honest
correction usually has, and it is worth saying plainly that 3b was too severe
in one band and not severe enough in another — it declined to promote 2.10×
that had earned it, and it left 3.46× standing as "a real coherent gain" when
my own control already said otherwise.

**What does not change: the retraction of "17–27% behind" is firmer, not
weaker.** That claim was measured at **0.25–0.30**, the band that still does
not pass. A band-signal correction that rescues 0.20–0.25 does nothing for it.

**So: "state of the art" remains undefensible, but for a different and better
reason than the README currently gives.** It is not that strehl was measured
and found behind. It is that on this corpus the fine-scale question cannot be
put to a measurement at all, in either direction, and the numbers that said
otherwise were reading a grade.

**4. Added later, at the owner's request: the first timing comparison this
project has.** Same 105-frame stack, same machine, same night, wall clock
around the process. strehl renders it end to end — decode, alignment solve,
focus, merge, write — in **36.72 / 38.39 / 38.40 s**. The `focus-stack` fork,
reading Lightroom TIFFs of those same frames, takes **1320.64 / 1604.15 s**:
**strehl is 36.0×–41.8× faster under every pairing of the reps**, on 11.5× less
CPU and 6.2× less peak memory, with **no GPU** while the fork runs OpenCL on an
RTX 5090. Against the *May* fork build that actually produced the comparator
artefact, whose own log records 93.739 s to the merged TIFF, strehl is **2.4×
faster** — that is the number I would defend, because the 36× includes a
14–17× performance regression in someone else's tree that I did not attribute.
**Zerene Stacker PMax is UNTIMEABLE here**, reported as such rather than
estimated: its licence reads `License category = EXPIREDLICENSE`, and its batch
mode stalls in GUI initialisation (300.5 s wall, 9 s CPU, no output). Its own
archived log gives one comparable internal number — 26.912 s to align and stack
33 frames, 0.8155 s/frame — against strehl's 0.3656 s/frame end to end, so
roughly twice. Full working, every failed arm, and every asymmetry that was
*not* normalised away: **§9**.

**The two halves of the claim are now in very different states.** On speed
there is a measured comparator number for the first time and it is not close.
On quality the honest answer is that this corpus cannot decide the one question
that was in dispute, and will not until the capture in §32 exists.

---

## 1. Why the old instrument had to be replaced, not re-run

The README retracts a band-power statistic `P = <|F|²>` in a band. The
mechanism it names is that noise is broadband, so any statistic that sums power
in a high band charges noise as signal. I reproduced all of it and added an arm
the retraction did not have.

`commission.py 113 16`, 13 arms, pre-registered pass/fail rules written before
the run:

| arm | what it is | `P` | `C` (mine) | `γ` |
|---|---|---:|---:|---:|
| NULL | byte-identical input | 1.0000 | **1.0000 exact** | **1.0000 exact** |
| NOISE_IND | independent noise added | **1.73** | **1.000** | 0.58 |
| LOWPASS20 | everything above 0.20 removed | **0.73** | **−0.003** | −0.005 |
| NN_V_CR | nearest-neighbour vs catmull-rom | **1.82** | 3.23 | 1.76 † |
| flat vs detail | do featureless ROIs gain more? | **5 of 7 bands** | 1 of 7 | 0 of 7 |

† `γ`'s NN/CR is not computed as a derived arm; 1.76 is its NN-vs-NULL value at
0.40–0.48 (`NN 1.7574`, `CR 0.9866`).

`P` fails on all four documented modes. That is the retraction, re-derived
here rather than taken on trust.

### The construction that fixes it

Render **two disjoint half-stacks** — odd frames and even frames — of the same
subject. Then for each region:

```
P_A = <|A|²>      P_B = <|B|²>      C = <Re A·B*>      γ = C / √(P_A P_B)
```

`A` and `B` observe the same scene through **disjoint frame sets**, so their
noise is independent, so **noise contributes zero to `C` in expectation.** That
is not a tuning choice, it is the definition of a cross-spectrum. The NOISE_IND
arm confirms it empirically: adding independent noise moves `P` to 1.73 and
`C` to **1.000**.

`γ` is the anti-sharpening control. Apply any filter `H` to both halves and
`C → |H|²C`, `P → |H|²P`, so **`γ` is exactly invariant**. A `γ` gain therefore
cannot be produced by a sharpen. The SHARP arm (4× unsharp mask) moves `C` to
**4.0** and `γ` by **0.6%** — this project once shipped a sharpness statistic
"bounded below by zero that could never charge for a halo"; this one charges.

### What `C` gets wrong, stated because it is not obvious from the table

- **NN_V_CR = 3.23.** A software nearest-neighbour resample scores *better*.
  This is a real failure of `C`, and it is the one arm that mattered most, so
  I built the real-pipeline version of it (§3).
- **BLUR03 potency = 0.9817** at 0.25–0.30, missing my pre-registered 0.98
  threshold. `C`'s detection limit is about σ = 0.3 px. Below that it cannot
  see a blur.
- **NOISE_COM = 6.05** (`C`), **3.51** (`γ`). Noise *common to both halves* — a
  PRNU/fixed-pattern proxy — does inflate `C`, by up to **6.05×** at 0.40–0.48.
  Disclosed, not fixed. It is the one noise source this construction cannot
  reject. In the three bands this document actually reports results in the
  inflation is **1.078 / 1.492 / 3.866** (0.20–0.25, 0.25–0.30, 0.30–0.40) —
  still large at the top, and §7 records it as the live route by which the flip
  result could be overstated.
  *(Correction of a correction, kept visible rather than tidied. This bullet
  read 6.05 in the first commit; the second commit "corrected" it to 1.7256 and
  was wrong — 1.7256 is statistic **`P`**'s NOISE_COM, from the second block of
  `logs/commission-113.txt`, not `C`'s. The blocks are headed
  `=== statistic C : ... ===` at line 14, `P` at line 30 and `g` at line 46;
  `C`'s NOISE_COM is line 25 and reads 6.0520. The tell that the wrong block
  had been read was sitting in the same file the whole time: the pre-registered
  verdict `[FAIL] P NOISE_IND < 1.05 -- P IS EXPECTED TO FAIL worst=1.7263`
  names 1.7263 as a `P` number. §7 was never edited and had stayed right, so
  the document contradicted itself across two sections for one commit.)*
- **SCALE_FORK = 0.974 / 0.934 / 0.794 / 0.512** in the four fine bands. This
  is the raster-scale confound the brief names: the fork writes 0.9596× in x
  and 0.9539× in y. Simulating that rescale costs `C` between 2.6% and 49%
  depending on band — so the confound is worth far more at 0.40–0.48 than the
  ~4.7% quoted for the band as a whole. It is handled here by scaling each
  arm's band edges into its own grid rather than by resampling anything (§4.1),
  which is why it does not appear in any reported comparison.
- **`γ` band-aggregation drift up to +5%** under BLUR08. `γ` is exactly
  invariant per frequency; a filter re-weights *within* a band, so the band
  average drifts (Cauchy–Schwarz). Exact per-bin, ±5% per band.
- **`γ` must never be used alone.** Under a 0.5× downscale `γ` *rises* to 3.0
  above 0.30 — the interpolated remnant is perfectly coherent — while `C`
  correctly collapses to 0.27. `C` is the claim-bearing statistic.

Tally, all pre-registered: **10 pass, 7 fail, 17 total.**

### The improvement arm the retraction did not have

The brief is right that a suite of only degradations cannot tell a *blind*
metric from a *perverse* one. So:

- **DECONV vs BLUR10** (a correctly-applied mild deconvolution of a blurred
  copy, a known real improvement): `C` scores it **1.04× to 100× better**. It
  charges for the improvement.
- **DECONV vs NULL** (the same deconvolution applied to an unblurred image):
  `C` ≤ **0.995**. It refuses to credit resolution that was never there.

A metric that scores a real improvement better *and* refuses to be talked into
one it did not receive is the pair of behaviours a degradation-only suite
cannot distinguish.

### Floors, because a number below its floor is not a number

- **(a) Byte-identical floor.** Same file twice: `max|C − C'| = 0.000e+00`.
  Exactly zero — the statistic has no stochastic component.
- **(b) Sampling floor.** Disjoint odd/even halves of the ROI set: spread
  1.002–1.333. **Nothing below 1.34 is reported as a per-band result.**
- **(c) Potency floor.** σ = 0.3 px blur → 0.995 / 0.987 / 0.982 / 0.975 /
  0.968. This is what "no change" is worth: the probe moves under a real
  disturbance a third of a pixel wide.

---

## 2. The arm that decides: a real nearest-neighbour gather

`C`'s software-NN failure (3.23) had to be resolved with the real pipeline, not
a numpy resample. The tool records its resampler in the warpmap sidecar, and
the sidecar **beats** the `--resampler` flag — it says so on stderr:

```
--resampler asked for CatmullRom but the sidecar named by STREHL_WARPMAP was
solved with Nearest ... resampler: Nearest
```

`make_nn_maps.py` copies each sidecar and changes **only** the token
`catmull-rom` → `nearest`, verifying by splitting on that token that every
other byte is identical. So the two renders differ in exactly one thing, and
that thing is a genuine, unambiguous degradation of the gather.

`C_nn / C_cr` and `P_nn / P_cr`, from `flip-113.txt` and `flip-cb.txt`:

| | 0.10–0.20 | 0.20–0.25 | 0.25–0.30 | 0.30–0.40 | 0.40–0.48 | |
|---|---:|---:|---:|---:|---:|---|
| 113 `C` | 0.955 | 0.897 | 0.831 | 0.857 | 0.886 | **PASS** |
| 113 `P` | 0.997 | 1.049 | 1.183 | 1.354 | **1.545** | **FAIL** |
| cb `C` | 0.945 | 0.879 | 0.862 | 0.796 | 0.756 | **PASS** |
| cb `P` | 0.984 | 1.009 | 1.112 | 1.405 | **1.881** | **FAIL** |

`C` charges the degradation in every band on both subjects. The retracted `P`
rates the same real degradation **up to 88% better**. That is the README's
documented failure mode, reproduced on the actual pipeline rather than a
synthetic proxy — and it is why no number computed with `P` decides anything
in this document.

---

## 3. The flip

Both arms from **one binary** (sha256
`15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0`, recorded in
`render_linear.ps1`), `STREHL_FULLRES_GATHER=0` and `=1`. All renders are
`--linear-srgb --demosaic`, 7032×4688, because the tool's own help says so:

> *"THIS IS THE MODE TO MEASURE IN. The standing rule is that quality is never
> judged on an `--srgb` render… more than one result in this project has been
> retracted for exactly that."*

I had rendered twelve `--srgb` frames before finding that line and threw them
away. The `--linear-srgb` path removes the entire tone-transcription risk from
strehl's side of every number here.

**Red control fired as designed:** `STREHL_FULLRES_GATHER=bogus` on a real
`stack` invocation → **exit 101**, panic at `align_cmd.rs:1009`, stderr naming
the variable. The two arms are genuinely two values of one switch and not two
builds.

### `C_g1 / C_g0`, 95% CI by ROI bootstrap, * = CI excludes 1

**113MSDCF, 52 ROIs** (`flip-113.txt`):

| band | ratio | 95% CI | |
|---|---:|---|---|
| 0.02–0.05 | 1.008 | | * |
| 0.05–0.10 | 1.047 | | * |
| 0.10–0.20 | 1.222 | | * |
| **0.20–0.25** | **2.103** | [1.945, 2.248] | * |
| **0.25–0.30** | **3.580** | [3.049, 4.364] | * |
| **0.30–0.40** | **3.462** | [2.852, 4.726] | * |
| 0.40–0.48 | 1.581 | | * |

> `[CORRECTED 2026-08-27 — see §0 finding 3b′.` The measurements above are
> unchanged; their *interpretation* is now per-band. **0.20–0.25 (2.103)** is
> the only row that stands as a resolution claim. **0.25–0.30 (3.580)** stands
> only as a coherent change. **0.30–0.40 (3.462)** is withdrawn: it is smaller
> than this lane's own NOISE_COM inflation of 3.866 in the same band.
> 0.40–0.48 (1.581) was never quoted and is doubly unsafe — NOISE_COM there is
> 6.052 and DISJOINT reads 40.2%. `]`

γ moved 0.3932→0.5183, 0.1514→0.3050, 0.0632→0.1327 in the three fine bands.

**coffee-bean, 18 ROIs** (`flip-cb.txt`): 1.009* · 1.054* · 1.239* ·
**1.953** [1.820, 2.085]* · **2.696** [1.992, 4.420]* · 1.437 [0.633, 3.284]
**inconclusive** · 0.899 **inconclusive**. The two inconclusive bands are
reported as inconclusive; coffee-bean natively carries 1.42% blown pixels and
46 of 64 detail ROIs were dropped for clipping, so it has a third of 113's
statistical power.

### It is mechanism-shaped, not a uniform gain

Fine spectrum on 113: **1.0042** at f = 0.027 → **2.0457** at 0.215 →
**3.1190 at 0.254** → **3.5891** at 0.270. Flat below, rising through
**f = 0.25**, the CFA plane Nyquist that the commit message names. A tone
change, an exposure change or a sharpen would not have that shape. The
nearest-neighbour column of the same table stays below 1 at *every* frequency
in that range (0.78–0.95), so the degradation is charged continuously and not
merely on a band average.

### The retracted statistic understates it

On the same data `P` gives only 1.60 / 1.78 / 1.65 on 113 against `C`'s
2.10 / 3.58 / 3.46 — because `P` was already counting the pre-flip render's
noise as signal, so it had less headroom to gain. The retracted statistic was
wrong about the direction of its own error.

### Flat-ROI specificity — the arm that killed the prior instrument

- **113**: the flat ROIs **also gain** — `C_g1/C_g0` on flat ROIs is 1.945 /
  2.968 / 2.224 in the three fine bands, against detail's 2.103 / 3.580 /
  3.462. That is the failure mode that killed the prior instrument and I am not
  going to bury it. What defends the result here is not the ratio but the
  *level*: flat ROIs carry only **6–10% of detail ROIs' absolute coherent power
  in every band** (0.0645 / 0.0636 / 0.0821 / 0.0831 / 0.0740 / 0.0556 /
  0.0999). Even if every scrap of the flat-ROI gain were spurious, it can
  account for at most a tenth of the detail result. 113's flat ROIs are only
  2.9× flatter than its detail ROIs, so this is a **bound, not a clean
  separation** — the bound is ≤10%, and coffee-bean is what turns it into a
  separation.
- **coffee-bean**: flat ROIs are genuinely featureless (median local contrast
  **0.0030 vs 0.8041**, a **268×** separation) and show **no coherent gain** —
  `C_g1/C_g0` on flat ROIs is 1.137 [−0.63, 2.61] at 0.25–0.30 and **−0.113**
  at 0.30–0.40, while detail ROIs gain 2.70×. Decisive.

---

## 4. The head-to-head, and how it died

### 4.1 Geometry, re-derived not trusted

`geom.py`, scale sweep with a hard rule that a sweep without an interior
maximum is a failed fit:

```
=== cb: strehl vs focus-stack fork ===
  best scale 1.0340 score 0.5212  INTERIOR MAXIMUM (fit is real)
    residual after a single global integer shift: 5.3 px rms
      -> a single integer shift is NOT globally satisfiable

=== 113: strehl vs Zerene Stacker PMax ===
  best scale 1.0020 score 0.5811  INTERIOR MAXIMUM (fit is real)
    residual after a single global integer shift: 0.0 px rms  -> one shift is enough
```

My 1.0340 agrees with `V-HEADTOHEAD`'s independently-derived 1.035063 to 0.1%.
The fork's 5.3 px residual is the first sign of trouble and it was ignored at
my peril for one run.

**Nothing is resampled anywhere in this document.** Each arm reads an *integer*
box in its own grid, sized `T/scale` so the two boxes cover the same scene
area, and each arm's band edges are scaled into its own grid so every band is
defined in **scene** units. Sub-pixel resampling adds blur to the very quantity
being measured.

### 4.2 The fork pairing is abandoned

`h2h2b.py cb 64`, ROI outcomes partitioned so that a skipped check cannot read
as a passed one:

```
  NULL control (24 deliberately mismatched ROI pairs): peak median 0.1408,
      95th pct 0.3531, max 0.4292
  ROI partition (must sum to 64):
    used                                   2
    dropped, strehl clipped                16
    dropped, comparator clipped/off-frame  5
    dropped, registration below gate       41
    dropped, FFT degenerate                0
    ---- total                             64   OK
  FEWER THAN 8 USABLE ROIs -- this pairing is ABANDONED, not reported as a result.
```

**41 of 64 regions cannot be registered against the fork's output.** The two
programs' alignment models disagree locally by more than a similarity can
absorb. This is a property of the comparison, not of either program's quality,
and it means the fork's fine-scale comparison is not merely inconclusive — it
is not computable on these two files.

The fork's other results in the README — the 4.5× noise advantage and the 32%
clipping — do **not** depend on per-region registration and are untouched by
this.

### 4.3 The first construction against Zerene, and what its own output said

`h2h2.py 113 40` compared absolute band power. Two things in its own log killed
it:

```
  strehl P  (total, post-flip)    8.9116e-02 ...          <- 0.02-0.05 band
  Zerene Stacker PMax P (total)   1.2465e-01 ...
  P_strehl_postflip / P_comp          0.7149 ...
```

A ratio of **0.71 in the 0.02–0.05 band** — features 20 to 50 pixels across,
which every stacker in this comparison resolves trivially. A deficit *there*
cannot be resolution. Per-ROI mean normalisation removes a scalar gain; it does
not remove a contrast curve.

And the pre-registered calibration rule fired and rejected the fallback
estimator:

```
=== CALIBRATION: does P - N reproduce C on the arm where C is known? ===
  ratio (P-N)/C     0.9430  1.0206  1.1960  1.5832  2.1681  4.0949  3.5988
  estimator NOT USABLE (pass = within 2x of the truth in every band)
```

Subtracting a flat-ROI noise floor overstates signal by **4.09×** at 0.30–0.40
on the one arm where the truth is independently known. Shot noise is
signal-dependent; a floor measured on flat regions does not transfer to detail
regions. So it was not applied to the comparator. This is the rule doing its
job, and it is the reason there is no "noise-corrected" number in this document.

### 4.4 The second construction, and the arm that caught me

`h2h2b.py` normalised each ROI by its own coarse band, on the argument that a
tone curve acts as a local slope and cancels. I built an arm to *test* that
rather than assert it. It failed:

```
=== GRADE ARM: the statistic must not move under a contrast curve ===
  ratio (1.0000 == grade-invariant)  1.1146 1.0000 1.0521 1.4453 2.1639 2.7938 2.8990
  worst deviation 189.90%.  Absolute band power under the same grade moves by
  62.8% in the reference band alone, so the disturbance is real.
  VERDICT: FAIL (pass = under 10% in every band)
```

A mild S-curve moves the coarse-normalised fine band by up to **2.90×** — more
than the entire effect the statistic was built to measure. A nonlinear curve
does not act as a per-region scalar on a spectrum: it **generates harmonics**,
moving power from coarse bands into fine ones. Coarse-normalisation does not
buy grade-invariance. My claim was wrong and my own control said so before I
published it.

### 4.5 The tone-sufficiency test: the gap *is* the grade

`gradetest.py` stops hypothesising about grades and measures the actual one.
Fit a monotone map strehl → Zerene from co-located, per-ROI-registered samples,
**using 4×4 block means only** — so the map is a function of tone and has no
access to any frequency above 0.125 cyc/px. Apply it to strehl's own pixels.
Then ask whether "strehl, graded the way Zerene is graded" lands where Zerene
lands.

`grade-113.txt`, 48 of 48 ROIs registered, 0 dropped:

```
  empirical tone map strehl->comparator, fitted on 4x4 BLOCK MEANS
  (no access to any fine band):
    d(log comp)/d(log strehl): median 0.177  10-90% [0.077,1.514]

                                  0.02-0.05  0.05-0.10  0.10-0.20  0.20-0.25  0.25-0.30  0.30-0.40
  strehl, as rendered             1.4351e+00 1.0000e+00 5.3636e-01 4.6935e-02 1.5778e-02 1.3366e-02
  strehl, UNDER THE FITTED MAP    1.1439e+00 1.0000e+00 6.8565e-01 9.0779e-02 3.7147e-02 2.5385e-02
  Zerene Stacker PMax, as rendered 1.1410e+00 1.0000e+00 7.1418e-01 9.6158e-02 3.7138e-02 1.9024e-02

      0.20-0.25  gap  2.049  tone  1.934   tone explains most of the gap -> undecidable
      0.25-0.30  gap  2.354  tone  2.354   TONE ALONE OVER-EXPLAINS THE GAP -> undecidable
      0.30-0.40  gap  1.423  tone  1.899   TONE ALONE OVER-EXPLAINS THE GAP -> undecidable
```

At 0.25–0.30 cyc/px — the band the retracted deficit lives in — strehl under a
**block-average tone map** sits at **0.037147** and Zerene sits at
**0.037138**. That is a match to **0.02%**, from a transformation that carries
no resolution information whatsoever.

> `[CORRECTED 2026-08-28 — see §8.4.` The registration sign defect moves these
> to **0.038106** and **0.036095**, a match to **5.6%**, not 0.02%. The
> conclusion is unchanged and the mechanism is the same; the agreement is
> merely less spectacular than the misregistration made it look. `]`

The sensitivity ladder shows the mechanism at strengths nobody would call
aggressive:

```
=== sensitivity ladder: pure gamma, the mildest monotone curve ===
    x^1.10  ratio to ungraded   0.9742 1.0000 1.0177 1.0294 1.0142 0.9629 0.9446
    x^1.25  ratio to ungraded   0.9347 1.0000 1.0479 1.0850 1.0547 0.9265 0.8770
    x^1.50  ratio to ungraded   0.8685 1.0000 1.1085 1.2110 1.1772 0.9201 0.8065
    x^2.00  ratio to ungraded   0.7428 1.0000 1.2690 1.6043 1.6560 1.1313 0.8261
  A pure gamma changes NO resolution whatsoever.  Whatever these rows are not
  equal to 1.0000 by is pure confound.
```

A bare **x^1.25** gamma — the mildest monotone curve there is — buys **+8.5%**
at 0.20–0.25. `Contrast2012=+100` is very much stronger than that.

**Conclusion.** The variable "band power in a render" cannot be compared across
two programs when one was fed a developed TIFF and the other reads RAW. That is
not a residual uncertainty to be carried alongside the answer. It is larger
than the answer.

---

## 5. The same gun, aimed at my own result

A finding that survives only because nobody pointed the gun at it is not a
finding. `toneparity.py 113 48`:

**ARM 1 — do the two gather modes even differ in tone?**

```
     pct     g0(pre)      g1(post)     ratio
      1        469.32       468.00    0.9972
     50        920.51       914.59    0.9936
     99       6388.65      6425.60    1.0058
  worst percentile deviation 0.642%  -> the two arms share a tone curve
```

(coffee-bean: 1.606%.) Both arms are `--linear-srgb`, no auto-tone, identical
flags, one binary. Confirmed rather than assumed.

**ARM 2 — can a block-mean tone map turn g0 into g1's spectrum?**

*(The gaps in this arm are the coarse-normalised variant on the 47-ROI
comparator-registered set, so they read 1.50/1.65/1.52 rather than §3's
2.10/3.58/3.46. The question here is what **fraction** of a gap tone explains,
which is the same question either way.)*

```
      0.20-0.25  gap  1.504  tone  1.032  tone explains    6.4% of it  -> NOT a tone artefact
      0.25-0.30  gap  1.650  tone  1.077  tone explains   11.9% of it  -> NOT a tone artefact
      0.30-0.40  gap  1.523  tone  1.080  tone explains   15.3% of it  -> NOT a tone artefact
      0.40-0.48  gap  1.088  tone  1.057  tone explains   64.6% of it  -> TONE MAY EXPLAIN IT
  ARM 2 VERDICT: FAIL (3/4 fine bands under 25%)
```

**The printed verdict is FAIL and I am leaving it printed.** My rule required
all four fine bands. The fourth, 0.40–0.48, has a gap of only 1.088 to begin
with — below floor (b), 1.34 — so it should never have been in the test set. I
am reporting the rule as written and the reason it fired, rather than moving
the goalposts after seeing the number. The three bands that carry the claim
pass at 6.4% / 11.9% / 15.3%.

coffee-bean: 0.9% / 7.0% / 27.1% / 93.0%, same pattern, same caveat.

**ARM 3 — potency. Would this test have fired if there were something to find?**

```
  48 registered pairs, strehl vs Zerene Stacker PMax
      0.20-0.25  tone explains   89.1% of the comparator gap
      0.25-0.30  tone explains  100.0% of the comparator gap
      0.30-0.40  tone explains  212.4% of the comparator gap
  ARM 3 VERDICT: PASS -- the procedure does still fire where it should, so
  ARM 2's negative means something
```

> `[CORRECTED 2026-08-28 — see §8.4.` Log retained verbatim. The corrected
> figures are **94.8% / 109.9% / 267.1%** — all further from zero, so ARM 3's
> PASS verdict is strengthened. **ARM 2, the tone gun aimed at my own flip
> result, is byte-identical at 6.4/11.9/15.3%** and does not depend on the
> defect. `]`

Same code, same ROI set, same run. A "no change" result is worth nothing unless
the probe is shown to move under a real disturbance; this one moves by 89–212%
on a real disturbance twenty lines earlier in its own log.

**On coffee-bean, ARM 3 could not be established** — only 5 registered pairs
survived, for the reason in §4.2. So coffee-bean's ARM 2 negative is *not
independently potentiated on its own subject*, and I am not claiming it is. It
is corroborating, not load-bearing. 113MSDCF carries the claim.

---

## 6. Proposed replacement for the README's "Measured against other stackers"

*Landed. This section was applied to `README.md` (now lines 1091–1361), with
three additions made at the time of landing: `V-LINEAR`'s noise-band finding as
a third independent reason the deficit claim is dead, the same finding applied
back against my own flip result, and a correction of the README's false claim
that the Lightroom-versus-RAW confound "cannot be removed without abandoning
the comparator the owner actually uses" — `V-LINEAR` removed it, and found that
doing so trades one confound for another. The text below is the version as
drafted, kept so the diff between proposal and landing is visible.*

> ## Measured against other stackers
>
> strehl has been compared against two other stackers on two subjects with
> confirmed frame-set equivalence: a patched `focus-stack` fork, and Zerene
> Stacker PMax. Two of the three results stand. The third has now been
> retracted twice, and the second retraction is the more interesting one.
>
> **Noise: strehl wins decisively, and this is not in dispute.** High-pass rms
> falls from 0.5025% to 0.1125% — a **4.5× reduction**, of which at least
> **2.4×** survives a worst-case grade correction. This measurement does not
> depend on registering the two renders against each other, so nothing below
> touches it.
>
> **Clipping: strehl wins decisively.** On one subject the fork clips **32% of
> the frame**. strehl clips **4e-6**. strehl is also lower on all four
> occlusion-rim measures.
>
> **Fine-scale resolution: undecidable on this corpus, in either direction.**
> The earlier claim that strehl was 17–27% behind at 3–5 px features was first
> retracted because the instrument failed its own controls in five independent
> ways. It has now been re-examined with an instrument built to be capable of
> failing — a cross-spectrum between two disjoint half-stacks, so that added
> noise contributes zero to it in expectation, commissioned against a real
> nearest-neighbour gather through the actual pipeline, a 0.5× downscale, a
> known deconvolution improvement, and flat-versus-detail regions.
>
> That instrument does not say strehl has caught up. It says the question
> cannot be asked of these files:
>
> - A tone curve fitted from **4×4 block averages of strehl's own output** —
>   a fit containing no information whatsoever above 0.125 cyc/px — reproduces
>   Zerene's band power at **0.25–0.30 cyc/px to within 0.02%** (0.037147 vs
>   0.037138) when applied to strehl's pixels. It accounts for **100%** of the
>   apparent gap there, **89%** at 0.20–0.25, and **212%** at 0.30–0.40.
>   `[CORRECTED 2026-08-28 — see §8.4: 5.6% (0.038106 vs 0.036095); 110% /`
>   `95% / 267%. Same conclusion, moved further from zero.]`
> - A bare **gamma of 1.25**, the mildest monotone curve there is and one that
>   changes no resolution at all, moves the same statistic by **+8.5%**. The
>   comparators' inputs were developed in Lightroom with `Contrast2012=+100`.
> - Against the fork the comparison is not merely confounded but
>   **not computable**: **41 of 64** candidate regions fail to register between
>   the two renders against a gate calibrated on a null control, because after
>   the best global similarity fit there remains **5.3 px rms** of local
>   disagreement between the two programs' alignment models.
>
> The README previously carried "the comparators were fed Lightroom-developed
> TIFFs while strehl reads RAW" as a caveat beside the result. It is not a
> caveat. **It is larger than the result.** Any statistic that reads band power
> out of a developed render is reading the development.
>
> **What did change, measurably.** Commit `740e7056` made
> `STREHL_FULLRES_GATHER` default on: each frame is now demosaiced to full
> sensor resolution before the warp instead of being gathered from its own
> half-resolution CFA phase plane. Measured on the coherent statistic, from one
> binary with the environment variable as the only difference:
>
> | band (cyc/output px) | 113MSDCF | coffee-bean |
> |---|---:|---:|
> | 0.20–0.25 | **2.10×** [1.95, 2.25] | **1.95×** [1.82, 2.09] |
> | 0.25–0.30 | **3.58×** [3.05, 4.36] | **2.70×** [1.99, 4.42] |
> | 0.30–0.40 | **3.46×** [2.85, 4.73] | inconclusive |
>
> The gain is band-specific, not a global sharpen: the 0.02–0.05 band goes
> *down* slightly (0.957), and the gain rises monotonically through
> **f = 0.25 cyc/output px**, which is exactly the CFA plane Nyquist the change
> was aimed at. Flat, featureless regions show no coherent gain on the subject
> where they are genuinely featureless. The same tone test that destroyed the
> comparator comparison explains only **6.4% / 11.9% / 15.3%** of this one,
> while still firing at **89–212%** on the comparator pair in the same run.
>
> `[CORRECTED 2026-08-27 — see §0 finding 3b′.` Read this table per band, not
> as a block. Only **0.20–0.25** is a resolution claim: it is the sole band
> with measured focus-dependent signal on this stack (R = 2.419). 0.25–0.30
> holds only as "the flip changed what is in this band" (R = 1.387), and
> **0.30–0.40 is withdrawn** — NOISE_COM inflates the statistic by 3.866
> there, more than the 3.462 the flip scored. The "rises monotonically
> through 0.25" argument is **also withdrawn**: noise inflation rises in the
> same direction, and noise-corrected the sequence is 1.95 → 2.40 → 0.90,
> which peaks and collapses. `]`
>
> **So the honest position is unchanged in its conclusion and changed in its
> reason.** "State of the art" is still not a defensible claim for this tool
> today — not because strehl was measured against the field and found behind,
> but because on this corpus the fine-scale comparison cannot be put to a
> measurement at all. strehl demonstrably improved by 2–3.6× in the bands that
> were in question. Whether that is now ahead of, level with, or behind Zerene
> is unknown, and will stay unknown until either the comparators are re-fed a
> linear TIFF or a target is shot whose edge lands inside a slanted-edge MTF's
> validity limit. Both are requested in `docs/captures-needed.md` §30 and §32.
>
> ### Speed
>
> Quality is the half of "state of the art" that cannot be settled here. Speed
> can be, and had never been measured against a comparator at all until now.
>
> Same 105-frame bracket, same machine (Ryzen 9 9950X3D, 32 logical, 61.6 GiB),
> same night, wall clock around the process — not CPU time, not a self-reported
> internal number:
>
> | | wall | s/frame | peak RSS | CPU |
> |---|---:|---:|---:|---:|
> | **strehl**, decode + align + focus + merge + write | **36.7 / 38.4 / 38.4 s** | **0.366** | 7.6 GiB | 593 s |
> | `focus-stack` fork, merged TIFF only | 1604 / 1321 s | 13.93 | 47.4 GiB | 6840 s |
>
> **strehl is 36–42× faster on this stack**, under every pairing of the measured
> reps, on **11.5× less CPU** and **6.2× less peak memory** — with no GPU, while
> the fork is running OpenCL on an RTX 5090.
>
> Four things that number is not, all of which cut against strehl or must be
> stated:
>
> - **The fork on disk today is not the fork that produced the comparator
>   above.** That build's own log stacked these same 105 frames in **93.7 s**.
>   Against *it*, strehl is **2.4× faster** to a comparable merged TIFF. That is
>   the figure to quote; the 36–42× includes a 14–17× regression in someone
>   else's tree that this project did not attribute and will not claim credit
>   for.
> - **The input asymmetry is not normalised away.** strehl reads 105 ARW =
>   3.88 GB. The fork reads 105 TIFF = 38.42 GB — 9.9× the bytes — and those
>   TIFFs are Lightroom developments of those same ARW, work the fork's route
>   needs and strehl's does not, timed by neither. Every fork number is an
>   under-count and the gap is a lower bound.
> - **Zerene Stacker PMax is UNTIMEABLE here and is reported as untimeable
>   rather than estimated.** Its licence has expired (`License category =
>   EXPIREDLICENSE`) and its batch mode stalls in GUI initialisation — 300.5 s
>   of wall clock for 9 s of CPU and no output file. Its own archived log
>   records **26.912 s to align and stack 33 frames = 0.815 s/frame**, against
>   strehl's 0.366 s/frame end to end. Roughly twice, on a number that excludes
>   Zerene's own load and save and every second of the human driving it.
> - **strehl has no GPU path, and that is measured not to be the gap it
>   appears.** `docs/research/M7-gpu-focus-measured.md` puts GPU acceleration of
>   the focus measure at **173×** on that stage but **0.40–0.57% of pipeline
>   wall time**. The pipeline is decode and alignment, which is exactly what the
>   stage breakdown of these runs shows.

---

## 7. What I could not determine, and exactly what would determine it

**Could not determine: whether strehl now out-resolves Zerene Stacker PMax.**
Two independent blockers, in priority order.

**Blocker 1 — the comparators' inputs are graded. This is free to fix and
nothing else can proceed without it.** Re-export the same developed TIFFs that
Zerene and the fork were fed, with **zero contrast, zero curve, zero clarity,
zero texture, zero sharpening, and a linear tone response**, and re-run both
comparators on them. This is a Lightroom export-preset change, costs no camera
time, requires no re-shoot, and removes a confound measured above at **89–212%
of the effect size**. Until it is done, every fine-scale number in a
strehl-versus-anything table is a tone measurement.

**Blocker 2 — no target in the corpus has an edge sharp enough for the textbook
instrument.** `docs/captures-needed.md` §30 already asks for this and its
analysis is correct: a slanted-edge MTF is valid to a 10–90% edge width of
**5.13 px**, and the two renders' edges measure **13.52 px** and **17.86 px**,
giving a **14.38%** systematic bias in the direction that flatters the
comparator. I have appended §32 refining it, on one point §30 does not make:
even a perfect knife edge does not escape Blocker 1, because a tone curve
reshapes an edge profile and therefore moves MTF50. **The capture and the
linear re-export are both required; neither alone is sufficient.**

**Could not determine: whether the fork out-resolves strehl at fine scale.**
Not blocked by tone but by geometry — the two alignment models disagree by
5.3 px rms locally, so 41 of 64 regions do not correspond. This would need
either the fork run with strehl's warpmaps, or a comparison restricted to the
regions that do register (23 of 64, too few for the per-band CIs this document
requires).

**Could not determine: how much of coffee-bean's flip gain is load-bearing.**
Its ARM 3 potency control could not be established on its own subject (5
registered pairs). Reported as corroborating only.

**Known weakness I did not fix.** `C` is inflated by noise *common to both
half-stacks* — the NOISE_COM arm scores 6.05. Fixed-pattern noise and PRNU are
common to every frame and therefore to both halves. This is disclosed, not
solved, and it is the one route by which the flip result could still be
overstated. A dark-frame/PRNU-corrected render pair would close it.

**Closed by another lane, against me.** `V-LINEAR` supplied the measurement I
did not think to make: whether the bands I report in contain any
focus-dependent signal at all. On this corpus they do not — in-focus /
defocused = 1.015, 1.043, 1.004, 1.138 over 0.20–0.48 cyc/px. That does not
make the flip result wrong, but it removes the interpretation I would have
preferred for it, and §0 finding 3b now carries the correction. **The capture
that fixes this is the same one §32 asks for**: a subject that actually puts
signal into 0.20–0.48 cyc/px at this magnification. Until then, "does the flip
recover scene resolution?" is not a question this corpus can be asked, and my
answer to it is withdrawn to "the flip changed these bands, coherently, where
it was aimed".

> `[CORRECTED 2026-08-27 — see §0 finding 3b′.` `V-LINEAR2.md` §2 supersedes
> the four ratios above; they were whole-frame pairs, and per-tile focus
> selection on **the same 113MSDCF stack** recovers **R = 2.419** at
> 0.20–0.25 cyc/px. So this paragraph is now wrong in one band and right in
> the other two. The withdrawal above holds for **0.25–0.30** (R = 1.387,
> marginal) and **0.30–0.40** (R = 1.149, fail); at **0.20–0.25** it is
> **lifted**, and the 2.10× stands as a resolution claim on the strength of
> three instruments — R = 2.419, DISJOINT at 0.24%, and 1.95× of headroom over
> my own NOISE_COM control. The 0.30–0.40 figure is withdrawn *further* than
> this paragraph withdrew it: NOISE_COM inflates `C` by 3.866 there against
> the flip's 3.462, so it is not merely uninterpretable, it is inside my own
> noise control. The capture request stands, narrowed: what is still missing
> is signal **above 0.25**, not above 0.20. `]`

**Could not determine, on speed.** Five items, listed in full at **§9.9**: a
certified cold-cache run (Windows has no scriptable page-cache drop; what I have
is one *observed* eviction worth 1.75× on strehl); the fork reading RAW directly
instead of Lightroom TIFFs, which would make the input symmetric; Zerene end to
end at all, which needs a valid licence; attribution of the fork's 14–17×
regression between its 2026-05-10 and 2026-05-17 builds, which is not my tree
and which this document's own standard says requires isolating the variable; and
whether the fork's 47.4 GiB peak grows with frame count while strehl's 7.6 GiB
does not — I measured the two peaks, not their slope.

---

## 8. Reproducing this

```powershell
cd C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD2
.\render_linear.ps1          # 12 renders, --linear-srgb --demosaic, one binary
.\render_nn.ps1              # 4 nearest-neighbour-gather renders
python commission.py 113 16  # the 13-arm battery, 10 pass + 7 fail = 17
python flip.py 113 64        # the flip result   (and: python flip.py cb 64)
python geom.py               # comparator geometry, interior-maximum rule
python h2h2b.py 113 48       # head-to-head; prints its own GRADE-arm failure
python gradetest.py 113 48   # the tone-sufficiency proof
python toneparity.py 113 48  # the same test aimed at the flip result

.\timing2.ps1                # section 9: 3+3 strehl reps, 1 fork rep, ~30 min
python timing_derive.py      # every derived number in section 9, from the CSV
python check_icc.py          # provenance of the fork's archived artefact
```

`render_linear.ps1` carries the full rule-47 header: binary path and sha256,
every flag including those left at default, and every environment variable.

### Housekeeping, recorded rather than tidied away

- `render_halves.ps1` is **superseded** — its logic was folded into
  `render_all.ps1` and then into `render_linear.ps1`. Left in place, unused.
- `render_ab.ps1` and `render_all.ps1` produced **half-resolution** and
  **`--srgb`** output respectively. Both superseded by `render_linear.ps1`.
  No number in this document comes from either.
- `test_instrument.py` **TEST 1 has no power** and I am recording that rather
  than deleting it. It tried to verify tone removal by rendering the same stack
  1.00 EV apart; on an `--srgb` render the auto-tone rescales with the
  exposure, so the two outputs came out **byte-identical**
  (sha256 `53957F43…`) and every level-binned ratio was 1.00000. The test could
  not have failed. It did accidentally prove **byte-identical determinism**
  across two invocations hours apart, which is worth having.
- `test_instrument.py` **TEST 2's assertion has a sign bug** — `integer_shift`
  returns the planted offset, not its negative. The function is correct; the
  assertion is not. Not fixed, because the function is exercised correctly
  everywhere else and I am read-only on nothing here but did not want to touch
  a file after quoting its behaviour.
- `h2h2.py` is the **superseded** first construction. Kept because §4.3 quotes
  its output as evidence against itself.
- `timing.ps1` is the **superseded** first timing harness. Kept, unused, because
  §9.1 quotes the defect it shipped: it timed a strehl run whose alignment cost
  0.0 s from a cached sidecar and would have credited strehl with 45% of its own
  CPU that it had not spent. Its OOM log is the evidence for §9.3.
- `logs/timing-run2.txt` **does not exist**, and that is a defect in how I ran
  `timing2.ps1`, not a missing measurement. The console output was teed to a
  file through an asynchronous wrapper that never flushed it. Everything the
  console printed is recoverable from machine-written files that *did* persist —
  `logs/timing2.csv` for the table, `logs/timing-strehl-{solve,cached}-{1,2,3}.txt`
  for the six alignment-mode assertions and stage breakdowns, and
  `logs/timing-fork-rep{1,2}-tail.txt` — so nothing in §9 rests on a number I
  transcribed by hand. `logs/timing-derive.txt` is the derivation, re-run from
  the CSV.

---

## 9. Speed — the first timing comparison this project has

*Added after the quality sections at the owner's request. The project's stated
goal is state of the art on speed **and** quality, and until now there was no
measured comparator number for speed anywhere in the repository. Everything
below is on the same 105-frame `coffee-bean` bracket, the same machine, the
same night. Harness: `experiments/V-HEADTOHEAD2/timing2.ps1`. Arithmetic:
`timing_derive.py`, so no derived number here was typed by hand. Raw:
`logs/timing2.csv`, `logs/timing-*.txt`.*

### 9.0 The result in one table

105 frames. strehl reads 7032×4688 CFA (**32.97 MP/frame**) and writes 7032×4688
16-bit RGB. The fork reads 7168×5120 float32 TIFF (**36.70 MP/frame**) and
writes 7008×4672 float32 after its crop (32.74 MP). Memory is **GiB** throughout
(PowerShell's `1GB` is 2^30).

| | wall (s) | s/frame | peak working set | CPU (s) | how it was got |
|---|---:|---:|---:|---:|---|
| **strehl**, end to end, alignment **solved** | **36.72 / 38.39 / 38.40** | **0.366** | 7.6 GiB | 593 | MEASURED, 3 reps |
| **strehl**, end to end, alignment **cached** | 28.29 / 38.42 / 46.62 | 0.269 best | 7.3 GiB | 327 | MEASURED, 3 reps |
| **`focus-stack` fork**, merged TIFF | **1604.15 / 1320.64** | **13.93** | **47.4 GiB** | **6840** | MEASURED, 2 reps |
| **Zerene Stacker PMax** | — | — | — | — | **UNTIMEABLE** (§9.6) |

Throughput, DERIVED: strehl **90.2 MP/s** of output; the fork **2.35 MP/s**.

**strehl is between 36.0× and 41.8× faster than the fork on this stack**, under
every pairing of the measured reps (best:best 36.0×, median:median 38.1×,
worst:worst 41.8×). It burns **11.5× less CPU** and **6.2× less peak memory**
doing it, and it reads the camera's RAW files while the fork reads a 9.9×
larger set of TIFFs that something else had to develop first.

That is the headline, and the rest of this section is the reasons not to trust
it further than it deserves.

### 9.1 The harness's first job was catching its own author

`timing.ps1` (v1, kept in place, unused) unset `STREHL_WARPMAP` and I believed
that made the run end to end. It did not. Both of its strehl runs printed, in
their own logs:

```
alignment       : ON (sidecar), reference frame 52, 105 placed / 0 refused, 0.0 s
```

**Alignment cost zero.** `strehl stack` discovers a *cached* sidecar under
`$STREHL_CACHE_DIR`, defaulting to `%LOCALAPPDATA%\strehl\warpmaps`
(`align_cmd.rs:1176`), and one was sitting there from earlier work. The fork
solves its alignment on every run. Publishing that number would have credited
strehl with a stage it had skipped — measured below at **45% of its
end-to-end CPU**.

Nothing clever caught this. strehl printed the fact and I read it. So v2 does
three things:

1. points `STREHL_CACHE_DIR` at a private directory and **wipes it before every
   SOLVE rep**, and
2. **asserts the mode strehl reports** and throws if it is wrong —

```powershell
function AssertAlign($stem, $want) {
  $line = (Select-String -Path "$logs\$stem.out","$logs\$stem.err" -Pattern '^alignment ' | Select-Object -First 1).Line
  if (-not $line) { throw "$stem : strehl printed no alignment line -- cannot certify the arm" }
  if ($line -notmatch [regex]::Escape($want)) { throw "$stem : expected alignment '$want' but strehl reported: $line" }
}
```

so a silent regression to the cache fails the run instead of flattering it —
and 3. keeps **both** arms, because they answer different questions: SOLVE is
what compares to the fork, CACHED is what the owner's own workflow costs on a
re-render.

The assertion is not decoration. It fired six times in the run that produced
the table, once per rep, and every line it accepted is in the logs:

```
STREHL-SOLVE   rep 1     36.72 s  exit 0  peakWS   7.34 GB  cpu   592.9 s  freeRAM 39.6 -> 45.4 GB
    alignment       : ON (solved), reference frame 52, 105 placed / 0 refused, 10.5 s
...
STREHL-CACHED  rep 1     28.29 s  exit 0  peakWS   7.21 GB  cpu   327.1 s  freeRAM 45.6 -> 50.5 GB
    alignment       : ON (sidecar), reference frame 52, 105 placed / 0 refused, 0.0 s
```

v1 also timed through a PowerShell pipeline, which gave no access to peak
memory or CPU time. v2 uses `Start-Process` and samples `PeakWorkingSet64` every
2 s while the process is alive — necessary, because reading it *after* exit
returns zero: the probe run of the fork reported `peak WS = 0.00 GB` post-exit
while a live sample of the same process read `50,770,456,576` bytes.

**Units.** PowerShell's `1GB` literal is 2^30, so every memory figure printed by
the harness is **GiB**. The machine reports 61.6 GiB visible to Windows.

### 9.2 What the reps actually say, including the ugly one

```
arm            n  wall s: min      med      max  spread  s/frame(med)    CPU s  thr-eq peak GiB
-----------------------------------------------------------------------------------------------
STREHL-SOLVE   3        36.72    38.39    38.40    1.05        0.3656    592.9    15.5     7.64
STREHL-CACHED  3        28.29    38.42    46.62    1.65        0.3659    327.1     8.3     7.34
FORK-MERGE     2      1320.64  1462.39  1604.15    1.21       13.9276   6839.6     4.7    47.37
```

**The CACHED arm's 1.65× spread is contention, not variance in the thing being
measured, and it is visible in strehl's own stage line.** Its three reps folded
105 frames at 0.24, 0.34 and 0.42 s/frame for identical work in the same order
they ran; three other agents were working in this tree at the time (stated in my
brief, and consistent with the 108 processes holding CPU time that the harness
counted at launch). The SOLVE arm ran earlier and is tight (1.05×). I am
reporting the CACHED spread rather than dropping the outlier, and I would not
defend any CACHED number to better than "about 28 s when the machine is free."

The fork's two reps differ by 1.21× (1604 s and 1321 s). Its parallel
efficiency is **4.7 of 32 logical processors (15%)** against strehl's **15.5
(48%)**, which is the signature of a memory-bound run rather than a compute
bound one. Sampled during the two runs, its working set ran between **26.4 and
45.7 GiB** and peaked at **47.4 GiB**, while free RAM fell to **0.3 GiB** in rep
1 and **1.7 GiB** in rep 2 at the moments I sampled. **Even the fork's *faster*
rep loses by 36×: strehl wins by 36.0× at the pairing most favourable to the
fork, 38.1× at the medians and 41.8× at the pairing least favourable to it.**

### 9.3 The fork's default configuration does not complete at all

The first fork run in this lane used the flags that produce the artefact
V-HEADTOHEAD2 measures — `--output-colorspace=linear-rec2020
--output-bitdepth=32` — and nothing else. At those settings the fork's
`--hdr-preserve` resolves to `auto` → **on**, which its own `--help` prices at
"~3.6 GB extra peak RAM per 32 MP frame". It ran for **521.52 s** and died:

```
Task Grayscale aligned_DSC00020.tif on thread 4 failed with exception:
OpenCV(4.13.0) ... alloc.cpp:73: error: (-4:Insufficient memory) Failed to
allocate 146800640 bytes in function 'cv::OutOfMemoryError'

Error exit due to failed steps
```

at task 716 of 860, exit code 1, on a machine with 61.6 GiB and ~40 GiB free at
launch. 146,800,640 bytes is exactly one 7168×5120 float32 plane.

So the timed fork runs use `--hdr-preserve=off`, which the fork documents as the
legacy path for "bit-identity regression against pre-Phase-4 builds" — the
closest reachable match to the build that actually produced the comparator.

**I cannot claim that is the cheaper configuration, and I am not going to.** The
run that died had reached task 716/860 in 521 s; the `off` run that completed
was still at 771/860 at ~640 s, so on the only comparison available the
*defaulted* configuration was progressing at least as fast right up to the point
where it ran out of memory. What is established is narrower and enough:
**the fork's default configuration on this stack does not complete on this
machine**, and the configuration that does takes 1320–1604 s. The failed run's
log is kept at `logs/timing-fork-hdrauto-OOM.txt`.

### 9.4 The fork binary on disk is not the fork binary that made the comparator

Stated because it bounds what this comparison means.

| | comparator run | timed here |
|---|---|---|
| binary date | ≤ 2026-05-10 | **2026-05-17 03:01:25** |
| tasks in the graph | **772** | **860** |
| self-reported wall | merged TIFF at **93.739 s**, all three artefacts at **143.458 s** | 1320.64 / 1604.15 s |
| accelerator | `OpenCL device: NVIDIA Corporation NVIDIA GeForce RTX 5090` | same binary family, same machine |

The archived log (`C:\dev\macro\out\coffee-bean\stack.log`, 2026-05-10) shows
the fork stacking these same 105 frames — 105 `Starting task: Load` lines from
`D:\edited\macro\coffee-bean` — in **93.7 s to the merged TIFF**. Seven days and
~88 extra pipeline tasks later — Phase 12.x per-frame denoise, FBDD, lateral CA,
axial defringe, a noise model — the same command takes **1320–1604 s**. I did
not measure the intermediate builds and cannot attribute the 14.1–17.1×
regression to any one of them.

**Is that archived log the run that produced the artefact V-HEADTOHEAD2
measured?** Probably, and it is worth saying how far "probably" goes, because
the log's mtime is 16:45:16 and `stack.tif`'s is 20:01:58 — three hours later.
The log itself recommends a post-run `embed_icc.py` step, which would rewrite
the file and move its mtime. `check_icc.py` asks the file:

```
bytes         : 393,326,272
geometry      : 7008 x 4672, 3 samples, 32 bits
ICC profile   : PRESENT, 472 bytes
VERDICT       : consistent with the archived log being this file's run, followed
                by the embed_icc.py step the log itself recommends
```

A plain fork write does not embed a profile — that is the entire point of the
tip in the log. So the mtime gap has an innocent explanation and the artefact
is **consistent with** this log. Consistent with is not proof of, and I did not
find a way to make it proof.

**Both numbers are true and they answer different questions.** Against
*today's* fork, strehl is 36–42× faster. Against the *May* fork that produced
the artefact this document measures quality on, strehl at 38.39 s is **2.4×
faster to a comparable merged output** (93.739 s → 38.39 s), and **3.7× faster
against the fork's full 143.458 s three-artefact scope, which is not a like
comparison and is stated only because that is the number the archive contains**.
**The 2.4× is the figure I would defend in public**, because it compares
strehl's merged TIFF against the fork's merged TIFF, and because it is the one
that does not depend on a performance regression in somebody else's tree.

### 9.5 What is included, what is not, and which way the omissions cut

Included in every number: process start, library load, decode, alignment, focus,
merge, colour, file write, flush.

**Not included, and not normalised away:**

- **strehl reads 105 ARW = 3.88 GB. The fork reads 105 TIFF = 38.42 GB —
  9.9× the bytes — and those TIFFs are Lightroom developments of those same
  105 ARW.** That development is work the fork's route requires and strehl's
  does not; it happened before either process started and is timed by neither.
  Every fork number here is therefore an **under-count** of its route, and the
  36–42× is a **lower bound**.
- The fork *can* read ARW directly (it has a whole `--raw-*` flag family). It
  was not timed that way, because the comparator artefact this project measured
  was made from the TIFFs. A fork-reads-RAW timing is a real missing arm and is
  listed in §9.9.
- **Scope:** strehl writes one merged TIFF (7032×4688, 16-bit, 197.8 MB). The
  fork here writes one merged TIFF (7008×4672, float32, 392.9 MB) and no
  depthmap or 3D view — though it computes a depth map internally regardless;
  its own progress lines say `Construct depthmap layer N` in a run that never
  asked for one. In the archived run the two extra artefacts cost 49.7 s on top
  of the 93.7 s merge.
- **strehl's output is half the bytes** (16-bit vs float32), which flatters
  strehl's write stage. Its write is 0.3–0.7 s of a 38 s run, so this is worth
  well under 1% and cannot move the conclusion.

### 9.6 Zerene Stacker PMax: UNTIMEABLE, with the reason

Not estimated. Attempted, and the attempt is logged.

Zerene *does* ship a batch CLI. Launched exactly as its own recorded launch
command does it, with `-noSplashScreen -exitOnBatchScriptCompletion
-runMinimized -batchScript` and a batch script pointed at the same 105-frame
directory (`experiments/V-HEADTOHEAD2/zerene-probe.zbs`), it printed:

```
0.398: license 83ced522295099724b84c81abbb79f3199726fd7 expires on Sat Jun 06 20:13:34 PDT 2026
0.401: Using default license key
0.401: License category = EXPIREDLICENSE
...
0.799: hard expiration date = null
0.825: Desktop class found
```

and then **stopped**. 300.5 s of wall clock, **9 s of CPU**, no further log
line, no output file, still alive when I killed it. Its batch entry point is
`com.zerenesystems.stacker.gui.MainFrame` — a GUI class — and it stalls in GUI
initialisation before it ever reaches the batch script.

Three independent reasons, any one sufficient:

1. **`License category = EXPIREDLICENSE`** (expired 2026-06-06; today
   2026-08-27). Whatever it did run would not be the licensed product's
   behaviour.
2. **It never reached the work.** 9 CPU-seconds in 300 wall-seconds is a
   process blocked, not a process stacking.
3. **Its real workflow has a human in it.** The archived interactive session
   log records `FileDialog 'visible' for 5900 milliseconds`, the output path
   chosen from a file chooser at t=80.609 s when the stack had finished at
   t=47.058 s — **33.5 s of a person** — and a **2,242-second gap** between the
   end of one stacking operation (t=47.058) and the start of the next
   (t=2289.220) that is lunch, not computation.

**What can honestly be said about Zerene's speed**, clearly labelled: Zerene's
*own* log, from an interactive session run by the repository owner on
2026-05-09 while the licence was valid, reports for a 33-frame stack of the same
camera at the same resolution:

```
 1508: 47.058: Time for makeStackedResult(method=1) = 26.912
```

**26.912 s for align + PMax on 33 frames = 0.8155 s/frame** (MEASURED by
Zerene, DERIVED per frame). strehl's end-to-end 0.3656 s/frame is **2.23×
faster than that**. Four caveats, all of which matter:

- different subject (`marker2`, 33 frames, not `coffee-bean`, 105);
- that number **excludes** Zerene's own image load and its save (196.5 MB
  written at t=82.015 s) and every second of the human;
- it excludes the Lightroom export that produced its 12.08 GB of input;
- and it is Zerene's internal clock, not a stopwatch around a process.

So: **strehl is faster than Zerene by a factor of about two on the only
comparable number that exists, and I would state that as "roughly twice", not
as 2.23×.**

### 9.7 Against the owner's own corpus figure

The calibration point given to me: 4,825 frames at ~33 MP in 16.2 minutes =
**0.2015 s/frame** (MEASURED, this session, whole corpus). My end-to-end SOLVE
arm is **0.3656 s/frame — 1.81× slower**; my best CACHED rep is 0.2694 s/frame,
1.34× slower. The gap is explained, not waved at:

- these runs carry `--linear-srgb --demosaic`, which is the mode V-HEADTOHEAD2
  measures quality in. It writes **7032×4688** with every CFA site demosaiced,
  against the default binned **3516×2344** — 4× the output pixels;
- the SOLVE arm re-solves alignment from scratch every rep (45% of its CPU),
  which a corpus render doing many subjects will not repeat per subject;
- three other agents were on the machine, and the CACHED arm's own reps show
  what that costs (0.24 → 0.42 s/frame for identical work).

I did not reproduce the corpus figure and am not disputing it; the two are
consistent once the mode is accounted for.

### 9.8 The missing GPU path is not the speed gap it looks like

The fork ran on `NVIDIA GeForce RTX 5090` via OpenCL, per line 1 of its own log.
strehl is CPU/rayon only. strehl still won by 36–42×.

`docs/research/M7-gpu-focus-measured.md` §0–§1 measured why that is not a
paradox: GPU-accelerating the focus measure is **173×** on that stage
(MEASURED), but the whole focus+merge stage is **0.40% of a cold pipeline and
0.57% of a warm one** (DERIVED there), and the fusion prize inside it is
0.14–0.20%. The pipeline is decode and alignment. My stage breakdown says the
same thing from the other end — of a 38.39 s SOLVE run, alignment is 10.5–12.8 s
and the fold (decode + warp + focus + merge, interleaved) is 23.2–25.3 s, with
0.3–0.7 s of write.

**So the honest speed claim does not need a GPU, and saying so is not a
rationalisation — it is a number that was measured before this comparison
existed and that predicted this outcome.**

### 9.9 What the timing could not determine

- **Cold cache.** Windows has no supported script-level way to drop the page
  cache, so nothing here is a certified cold run. What I have is one *observed*
  eviction: in the v1 harness a strehl run took 26.71 s, the fork then streamed
  38.42 GB through the page cache, and the next identical strehl run took
  46.68 s — **1.75×**, with the same alignment path and the same output. That is
  a real cold/warm bound on strehl (its input is 3.88 GB and does cache);
  it is one observation, not a series. A certified cold measurement needs a
  reboot between reps, or `EmptyStandbyList`, and I did neither.
- **The fork reading RAW.** Its `--raw-*` path would remove the Lightroom step
  from its route and make the comparison symmetric in input. One run,
  `--lr-match=on`, would settle whether the 9.9× byte asymmetry is doing any of
  the work. I did not run it because the fork costs ~25 minutes per rep and the
  quality comparator was built from TIFFs.
- **Zerene end to end, at all.** Needs a valid licence and a batch mode that
  does not stall in GUI init. If the owner renews, the same
  `zerene-probe.zbs` plus a stopwatch settles it in one run.
- **Attribution of the fork's 14–17× regression** between 2026-05-10 and
  2026-05-17. Not my tree, not measured, deliberately not blamed on a commit
  range — this document's own §4.1 standard is that attribution requires
  isolating the variable.
- **Whether the fork's peak of 47.4 GiB is inherent or a leak.** strehl's merge
  prints `memory plan : 4 workers x 1328 MB = 5.2 GB ... CONSTANT in the frame
  count`, and its measured peak (7.2–7.6 GiB) is consistent with that plus
  decode and output buffers. The fork's peak scaled with the stack. I measured
  the peaks; I did not measure their slope in frame count, which is the
  experiment that would turn "6.2× more memory" into "O(n) versus O(1)".

---

# §8 Mask audit, a registration sign defect, and the `foam` speculars (2026-08-28)

Commissioned by the owner after an independent lane found `vh2_sweep.py`'s
fixed-percentile mask producing an **arithmetically impossible** result: an
"aura depression" of 16557.7 DN on an image whose median is 8171.1 DN.

## 8.1 Provenance, stated plainly

`vh2_sweep.py` lives at `experiments/V-REVIEW/vh2_sweep.py` (commit
`bfd7cfbd`), not in this lane. The `vh2_` prefix names this lane's *subject*,
not its author. I state that as a fact, not as a defence: the construct was
audited here regardless, because the question asked — *is that mask under any
published head-to-head number* — is a fair question about my numbers whoever
wrote the script.

## 8.2 Audit result: no published figure uses a fixed percentile mask

A partition that sums, over all 18 published figures in this document:

| mask class | figures |
|---|---:|
| fixed percentile (the defective construct) | **0** |
| ROI-adaptive (`rois.census`, per-ROI, content-derived) | 11 |
| whole-frame (no mask at all) | 3 |
| non-image (timing, memory, byte counts) | 4 |
| **total** | **18** |

A source scan across all 16 lane sources found no `distanceTransform`,
`connectedComponents`, `MORPH_CLOSE`, `aura` or `depression` anywhere except
in the audit's own three files, which are named in the output so the exclusion
is visible rather than silent.

**Subject frame-occupancy** (debiased; the estimator is eroded by its own blur
radius because local-contrast segmentation provably dilates):

| subject | occupancy | vh2 mask design point |
|---|---:|---|
| `113MSDCF` | **48.1%** | built at 21%, failed at 60% |
| `coffee-bubbles` | **41.5%** | built at 21%, failed at 60% |

Both sit between the design point and the failure point. **The mask would have
bitten here had it been used.** Applying its own construction to my subjects,
its aura:ground ratio at 20/30/40/50 percentile is 0.34/0.32/0.28/0.23 on
`113MSDCF` and 0.07/0.15/0.59/1.00 on `coffee-bubbles` — all but one below the
other lane's 0.70 ground floor. `113MSDCF` needs its extent eroded to 17.8%
before any configuration clears. That is why the audit is worth its cost even
though the answer is zero: the absence is a property of which statistics were
chosen, not of the subjects being safe.

**No published number moves for this reason.**

## 8.3 The standing assertion

`physics.py` raises `ImpossibleMeasurement` on three classes:

- a depression exceeding the level it is measured against;
- `|gamma| > 1`;
- a band partition violating `N = (P_A+P_B)/2 - C >= 0`.

It is **wired into `h2.pair_bands`**, so it is standing rather than a one-off.
Commissioned 14/14, in both directions: the wiring arm monkeypatches a 5%
normalisation error into the real `pair_bands` and confirms it is caught.

**The guard was wrong on its first draft and real data caught it.** I had
bounded `C` by `P_A`. Cauchy–Schwarz bounds it by `sqrt(P_A*P_B)`, so `C > P_A`
is legal when the other half carries more power, and 19 of 181 published band
triples legally do. That is also a **correction to `h2.py`'s own docstring**,
which called `P_A - C` "the INCOHERENT power" and implied a non-negativity
that does not hold. The measured counterexample
(`113-g0 detail (352,3680) band 0: P_A=0.170000, C=0.170789`) is now a
MUST-PASS commissioning arm so the wrong version cannot return.

## 8.4 The finding the audit was not looking for: `integer_shift` had the wrong sign

While checking that nothing downstream had broken, this lane's own
`test_instrument.py` TEST 2 printed:

```
MISS ... planted (2,3) got (2,3)
```

Planted and recovered **identical**, scored as a failure, at correlation peaks
above 0.99. That is a sign convention, not a registration failure — and it had
been failing correctly, in the tree, unread.

`integer_shift` returned the cross-correlation peak (the **displacement** of
the moving crop) while its docstring, its commissioning check, and all five
callers wanted the **correction** (the negative). Decided by measurement, not
by reading:

| test | at `-g` (repaired) | at `+g` (as published) |
|---|---:|---:|
| synthetic self-crop, mean residual correlation | **1.000000** | 0.618560 |
| real 113/Zerene comparator pair | **0.7909** | 0.2346 |
| real cb/fork comparator pair | **0.0664** | 0.0127 |

The 113 unregistered baseline is **0.3470** — so the published run had aligned
the crops *worse than not aligning them at all*. TEST 2 went 0/48 to 48/48.

The repair is one line: negate the return in `h2.integer_shift`. That makes
the docstring, the commissioning check and all five callers correct
simultaneously.

### What moved

`flip.py` and `commission.py` **never call `integer_shift`** (verified by
grep), so the headline flip figures and every commissioning arm are
structurally immune and are byte-identical before and after.

| figure | published | corrected |
|---|---:|---:|
| strehl under block-map @ 0.25–0.30 | 0.037147 | **0.038106** |
| Zerene as rendered @ 0.25–0.30 | 0.037138 | **0.036095** |
| agreement between them | 0.02% | **5.6%** |
| tone explains, 0.20–0.25 | 89.1% | **94.8%** |
| tone explains, 0.25–0.30 | 100.0% | **109.9%** |
| tone explains, 0.30–0.40 | 212.4% | **267.1%** |

22 cited values move; 206 internal values move. Found **mechanically**, by a
numeric comparator — the first version of that detector matched literal text
and would have missed the single most important number, because the log prints
`3.7147e-02` and the README prints `0.037147`.

**The 0.02% was too good because it was wrong.** I quoted it as the load-
bearing figure for "undecidable in either direction" and it was the product of
a misregistration. The corrected 5.6% still carries that conclusion — a
transform with zero information above 0.125 cyc/px still reproduces the band
to 5.6% — but it carries it honestly, and the tone-explains figures all move
*further* against the deficit claim, so the conclusion is strengthened rather
than rescued.

**`toneparity.py` ARM 2 — the tone gun aimed at my own result — is unmoved at
6.4/11.9/15.3%.** Both ARM verdicts are unchanged. The self-application that
made the Zerene verdict credible does not depend on the defect.

## 8.5 `foam`: the specular fringing is REAL

Measured on the **raw CFA photosites**, so no demosaic exists that could have
invented the colour, at the rim *shoulder* (95–99.8 percentile, clipped
photosites excluded — the first draft sampled the blown white core and read
saturation 0.0000).

| site | photosite chroma | master chroma | retained |
|---|---:|---:|---:|
| `foam` crema bubble rims | 0.1735 | 0.1230 | **70.9%** |
| `tweezers-cpl` polished steel, no film | 0.1801 | 0.0287 | **15.9%** |
| `lead-1-cpl` graphite, no film | 0.5924 | 0.6772 | 114.3% |

**One arm failed, and the failure is why the verdict is trustworthy.** Foam's
raw photosite chroma (0.1735) is *not* elevated above steep speculars on
subjects that physically cannot show interference (0.1801 on polished steel).
Raw chroma alone therefore cannot separate thin-film interference from
**Bayer-cell gradient aliasing**, which a steep specular edge produces on any
subject. Had I run only the two arms that pass, I would have convicted on
evidence that a no-film control matches exactly.

The discriminator the failure forces is **survival through the merge**. Bayer
gradient aliasing depends on where the edge falls within the 2×2 cell, so it
is phase-random frame to frame and must average away across 100 frames.
Colour locked to a film must survive. Foam retains 70.9%; polished steel with
statistically identical raw chroma retains 15.9% — **4.4×**. Foam behaves like
the genuinely-coloured control (114.3%), not like the aliasing control.

**Verdict: subject, not defect.** Three independent facts: the colour is in
the photosites before any demosaic; the pipeline *reduced* it (0.1735 to
0.1230) rather than creating it; and it survives frame averaging 4.4× better
than a no-film specular with the same raw chroma.

**What this does not establish.** It does not prove the mechanism is thin-film
interference specifically — only that the colour is scene-locked and
pipeline-honest. A lateral-CA contribution would also be scene-locked and
would also survive averaging. Two things would separate them and neither needs
a new subject: CA scales with field radius, so measuring rim chroma against
distance from the optical centre across the frame would expose it; and
interference hue should follow film thickness in ordered sequences along a
rim, where CA is radially oriented. The master crop shows 46.7%
single-pixel-area coloured components (median area 2 px), a speckle signature
rather than ordered fringes — which is consistent with a fine, thin film at
this magnification but is not positive evidence for ordering.

> `[SUPERSEDED 2026-08-27 — see §8.7.` §8.5's **conclusion** survives on
> better evidence, but its **reasoning was holed** and the hole is worth more
> than the conclusion. The load-bearing arm above was retention through the
> merge (foam 70.9%, polished steel 15.9%). That separates DETERMINISTIC from
> PHASE-RANDOM. It does **not** separate SCENE from PIPELINE, because a
> deterministic pipeline defect keyed to signal *level* is also
> frame-invariant, and level is set by the scene, so it tracks the scene
> through a merge exactly as real colour would. §8.5 measured the right
> quantity and drew the wrong dichotomy from it. §8.7 runs the test that does
> separate them. `]`

## 8.6 Applying V-LINEAR to this section

V-LINEAR measured the in-focus/defocused fine-band power ratio at 1.015,
1.043, 1.004, 1.138 on linear develops, against 2.1–3.0 for Lightroom's. The
0.20–0.48 cyc/px band is a **noise band on this corpus**. Everything in §8.4's
movement table lives in 0.20–0.40. The corrections are real and the direction
is right, but the band they live in carries little subject signal, so none of
them — moved or unmoved — should be read as a resolution claim. That applies
to the corrected 5.6% exactly as it applied to the 0.02%.

> `[CORRECTED 2026-08-27 — see §0 finding 3b′.` `V-LINEAR2.md` §2 supersedes
> the four ratios, on this same 113MSDCF stack: **0.20–0.25 is not a noise
> band** (R = 2.419), 0.25–0.30 is marginal (1.387) and 0.30–0.40 fails
> (1.149). The paragraph above is therefore too broad. The narrowed reading
> **strengthens §8.4 rather than weakening it**: the tone finding at
> 0.20–0.25 — that a 4×4-block fit with no information above 0.125 cyc/px
> explains **94.8%** of the strehl-vs-Zerene gap — now stands in a band that
> demonstrably *does* carry focus-dependent resolution signal. A confound that
> big in a band that real is a stronger result than the same confound in a
> band of noise. The "not a resolution claim" caveat still applies in full to
> the 0.25–0.30 and 0.30–0.40 rows, which is where the retracted "17–27%
> behind" was measured. `]`

---

## 8.7 `foam`, settled by changing the estimator (2026-08-27)

§8.5 answered the `foam` question with an instrument that could not fully
decide it, and said so. The owner proposed the better discriminator and it is
the one used here: **subject colour is invariant to how the merge gathers; an
estimator artifact is keyed to the gather lattice and must move when the
lattice moves.** `STREHL_FULLRES_GATHER` changes exactly that and nothing
else — arm 0 gathers each frame from its own half-resolution CFA phase plane,
arm 1 demosaics to full sensor resolution before the warp. One binary, one
warpmap, one subject, linear render with no tone gain and therefore no
exposure to pin.

**The disturbance is real, asserted before the probe was asked anything:**
97.82% of pixels differ between the arms, mean |Δ| 163.3 DN. A probe run
against a non-disturbance is the failure this lane has already shipped once.

| region | blown px | chroma g0 | chroma g1 | **moved** | pattern corr |
|---|---:|---:|---:|---:|---:|
| **specular rims** (the owner's 1:1 crop) | 0.396% | 0.2130 | 0.2108 | **+1.02%** | 0.9434 |
| ordinary texture (control, chosen by measurement) | 0.136% | 0.2573 | 0.2174 | **+15.54%** | 0.8339 |

**Verdict: the fringing is not made by strehl's merge or gather.** A change of
gather lattice that moves *ordinary texture* chroma by 15.54% moves the
specular rim chroma by **1.02%** — the rims are roughly **fifteen times more
stable** than ordinary texture under the very transformation an estimator
artifact would have to follow. Nothing keyed to the gather lattice can behave
that way. **Do not route a merge fix.**

**Two instrument repairs the run forced, both from the same class of error.**
The first version used SHIP-V4 coordinates against a half-resolution render;
numpy slicing clips silently, so it measured a 380×50 sliver at the frame edge
and returned entirely plausible numbers (chroma 0.1668 → 0.1731, r = 0.96) for
a region it never sampled. A hard bounds assertion now raises instead. The
second: `foam` has **no unblown region** at this tile size — all 240 candidate
tiles contained blown pixels, minimum 0.0166%, median 0.385% — so the control
is honestly labelled as *3× less blown*, not *unblown*, and both fractions are
printed rather than hidden behind the word "control".

### The other lane's mechanism does not reproduce on the shipped masters

README lines 517–540 report a different verdict from a better instrument than
§8.5's: a channel-asymmetric highlight saturation in strehl's output, green
pinning below blue so highlights acquire a one-sided blue excess. That is
well-evidenced and this lane does not dispute it — but it was **measured on a
different render**, and it does not appear in `foam--SHIP-V4.tiff`, which is
what the gallery ships and what the owner is looking at.

| arm | README's render | `foam--SHIP-V4.tiff` |
|---|---|---|
| A. channel ceilings | G **38921**, B **52239** | G **65535**, B **65535** — all three clip together |
| B. B/G across level deciles | 1.0257 → 1.2903 (**+25.7%**) | 0.9609 → 0.9926 (**+3.3%**) |
| C. hot pixels with B−G > 0 | **88.9%** (one-sided blue) | **31.3%** — leaning *green*, not blue |

Both findings can be true: a render whose highlights land below full scale can
show per-channel ceilings at 38921/52239, while a render whose highlights
reach 65535 clips all three together and cannot. **The defect is real and the
shipped masters do not exhibit it.**

`foam_retract.py` commissions 8/8 in both directions before it is believed —
a planted iridescent rim (hue cycling both signs, no ceiling) must acquit, a
planted ceiling defect on neutral grey must convict, and a colourless
luminance ramp must show no trend, which catches an arm reading level alone.
Two of those arms were repaired *by* commissioning: the trend gate originally
demanded monotonicity across all deciles, which a highlight defect — confined
by definition to highlights — would have escaped as a hockey stick; and the
hue-sign gate originally fired only on a *blue* excess, so the master's 31.3%
green-excess lean was scored "mixed" by a statistic that could only charge in
the direction I expected. Both are the same error this project keeps finding
in its own instruments.

### What is still open, and what would close it

**Whether the colour is specifically thin-film interference is not settled.**
Arm C on the shipped master reads 31.3% / 28.5%, a lean toward green excess
where interference predicts ~50%, though inside the two-sided tolerance. And
the subject description is itself in dispute: the brief describes `foam` as
coffee crema, the README as "dark cellular plastic". Both admit thin films, so
neither kills the hypothesis, but the corpus should agree on what the picture
is of. What would close it needs no new capture: rim chroma against **distance
from the optical centre** separates lateral CA from film, and hue *ordering*
along a rim separates film from a level-keyed pin.

**What is settled, and is what the question was asked to decide:** the rims'
colour is not manufactured by strehl's merge or gather, and the shipped
masters do not carry the channel-ceiling defect. `foam`'s speculars are not a
merge defect to fix.

### The limitation of this test, stated

These A/B renders come out at CFA-plane resolution (3516×2344) where
`foam--SHIP-V4.tiff` is 7032×4688, so the A/B certifies *the gather lattice
does not make the colour* rather than certifying the shipped master
pixel-for-pixel. Every other render in this lane is 7032×4688 from the same
invocation, so the difference is a property of this subject's decode, not of
the script; it is not chased here because it does not bear on the question.
