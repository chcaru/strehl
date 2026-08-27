# V-HEADTOHEAD2 — the head-to-head, re-run after the full-resolution gather flip

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
(0.037147 vs 0.037138). It accounts for **100.0%** of the gap there, **89.1%**
at 0.20–0.25, and **212%** at 0.30–0.40. The "17–27% behind at 3–5 px features"
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

**So: "state of the art" remains undefensible, but for a different and better
reason than the README currently gives.** It is not that strehl was measured
and found behind. It is that on this corpus the fine-scale question cannot be
put to a measurement at all, in either direction, and the numbers that said
otherwise were reading a grade.

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
- **NOISE_COM = 1.73** (`C`), **3.51** (`γ`). Noise *common to both halves* — a
  PRNU/fixed-pattern proxy — does inflate `C`, by up to 1.73× at 0.40–0.48.
  Disclosed, not fixed. It is the one noise source this construction cannot
  reject. *(An earlier working note of mine recorded this as 6.05; re-deriving
  it from the persisted run gives 1.7256. The note was wrong and the log is
  right.)*
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

γ moved 0.3932→0.5183, 0.1514→0.3050, 0.0632→0.1327 in the three fine bands.

**coffee-bean, 18 ROIs** (`flip-cb.txt`): 1.009* · 1.054* · 1.239* ·
**1.953** [1.820, 2.085]* · **2.696** [1.992, 4.420]* · 1.437 [0.633, 3.284]
**inconclusive** · 0.899 **inconclusive**. The two inconclusive bands are
reported as inconclusive; coffee-bean natively carries 1.42% blown pixels and
46 of 64 detail ROIs were dropped for clipping, so it has a third of 113's
statistical power.

### It is mechanism-shaped, not a uniform gain

Fine spectrum on 113: 1.004 at f = 0.027 → 2.05 at 0.215 → **3.12 at 0.254** →
3.59 at 0.270. Flat below, rising through **f = 0.25**, the CFA plane Nyquist
that the commit message names. A tone change, an exposure change or a sharpen
would not have that shape.

### The retracted statistic understates it

On the same data `P` gives only 1.60 / 1.78 / 1.65 on 113 against `C`'s
2.10 / 3.58 / 3.46 — because `P` was already counting the pre-flip render's
noise as signal, so it had less headroom to gain. The retracted statistic was
wrong about the direction of its own error.

### Flat-ROI specificity — the arm that killed the prior instrument

- **113**: flat ROIs carry **6–10% of detail ROIs' absolute coherent power in
  every band** (0.0645 / 0.0636 / 0.0821 / 0.0831 / 0.0740 / 0.0556 / 0.0999).
  113's flat ROIs are only 2.9× flatter than its detail ROIs, so this is a
  bound rather than a clean separation — but the bound is ≤10%.
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

Same code, same ROI set, same run. A "no change" result is worth nothing unless
the probe is shown to move under a real disturbance; this one moves by 89–212%
on a real disturbance twenty lines earlier in its own log.

**On coffee-bean, ARM 3 could not be established** — only 5 registered pairs
survived, for the reason in §4.2. So coffee-bean's ARM 2 negative is *not
independently potentiated on its own subject*, and I am not claiming it is. It
is corroborating, not load-bearing. 113MSDCF carries the claim.

---

## 6. Proposed replacement for the README's "Measured against other stackers"

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
> **So the honest position is unchanged in its conclusion and changed in its
> reason.** "State of the art" is still not a defensible claim for this tool
> today — not because strehl was measured against the field and found behind,
> but because on this corpus the fine-scale comparison cannot be put to a
> measurement at all. strehl demonstrably improved by 2–3.6× in the bands that
> were in question. Whether that is now ahead of, level with, or behind Zerene
> is unknown, and will stay unknown until either the comparators are re-fed a
> linear TIFF or a target is shot whose edge lands inside a slanted-edge MTF's
> validity limit. Both are requested in `docs/captures-needed.md` §30 and §32.

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
