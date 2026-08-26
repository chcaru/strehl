# V-BLEND - independent verification of ORCH's two multi-band blend claims

Verifier: V-RIM/V-BLEND. Author of the claims: ORCH. Nothing here was measured with
ORCH's code; their `clip_linear.py`, `clip_where.py`, `clip_map.py`, `flatnoise*.py`
and `noise_vs_detail.py` were left unread until after every number below existed.

## 1. Verdict

| claim | verdict |
| --- | --- |
| **C1** - the blend clamps a channel to zero on the subject | **CONFIRMED**, and stronger than stated. Also **already fixed** at HEAD `275fbd1`, with a residual deficit that is not. |
| **C2** - the blend's noise penalty is recovered detail, not noise | **REFUTED as stated.** The counterfactual it rests on is the wrong one, and its premise about the control arm is contradicted by the binary's own output. |

C1 survived every confound I could construct, including one ORCH did not use, and
reproduced on three subjects ORCH had never measured (four in total). C2 fails at two
independent points, and the second is decisive:

1. Its counterfactual is the wrong one. Real sensor noise in this pipeline does not
   arrive white - it reads `rho = +0.20` before any interpolation and `+0.35` after the
   demosaic, against the synthetic `-0.0035` the argument compares to. "It correlates,
   therefore it is not noise" does not follow (section 5.2).
2. **The calibrated noise model - the test ORCH nominated as strongest and did not run -
   refutes C2 outright.** On `bee-1-cpl`, ORCH's own strongest case, the blend's flat
   backdrop sits at **1.156x the model's prediction for a single raw frame**, in a region
   that is out of focus in all 299 frames of the bracket. A merge cannot recover detail
   that no input contains, and no averaging can be noisier than one exposure. The
   +1605% is a real noise penalty (I measure +1602% independently). Section 5.5.

The same model dissolves the premise of C2's step 2: `sigma = 7.8 DN` is not
implausible, it is what averaging ~240 frames produces, and "a single defocused frame"
cannot produce it because **defocus is applied before the sensor and cannot reduce
noise**. A real single defocused frame measures 111.6 DN here.

**The most useful thing in this document is probably section 4.4**: the hard clamp is
gone at HEAD, but at the exact pixels that used to read zero the fixed build still reads
a median of 805 DN where the ship path reads 2162 DN. The hull clamp bounds the error
without removing its cause.

**Two errors inside C1's supporting material, neither of which changes its verdict**
(section 9). `clip_linear.py` states that it measures upstream of the tone stage and then
opens the `--srgb` renders, which are downstream of it. And `clip_where.py` prints
`VERDICT: RINGING`, the opposite of what ORCH reported to me; its 5.8x "zeros sit at high
gradient" statistic falls to **1.17x** on `flower-bud` and **0.68x** on `dry-erase` when
recomputed in a linear space, because the sRGB curve amplifies gradients at dark pixels.
ORCH's spoken conclusion is the correct one; the scripts that support it are not.

## 2. What I measured with, and how it was commissioned

Four instruments, all written for this job, all under `C:\dev\strehl-out\V-BLEND\`
and mirrored into `experiments/V-BLEND/src/`.

| instrument | what it does |
| --- | --- |
| `zerocensus.py` | per-level histogram near zero and a spike ratio `p0 / (mass in levels 1..256 / 256)`. A hard clamp gives a spike; a dark scene gives ~1. |
| `noisefloor.py` | `sigma_std` (std after removing a fitted quadratic - exact for any noise) and `sigma_hf` (Immerkaer - correct only for white noise). |
| `whiteness.py` | lag-1 autocorrelation and fraction of residual power above half-Nyquist. |
| `armcompare.py` / `threeway.py` | compares arms on identical tiles under stated selection rules. |
| `noisemodel.py` | evaluates the project's calibrated sensor model `var = g*S + (RN_e*g)^2` at each tile's measured signal, giving an absolute physical floor rather than an arm-relative one. |
| `blobshape.py` | erosion survival and connected-component geometry of the zero mask, commissioned on a 2 px rim, a 4 px rim and a solid disc, so "rim" and "blob" are separated by measurement instead of by assertion. |

**Every instrument prints its whole evidence table above its verdict**, because a
detector built on a guessed threshold returns zero and looks exactly like a clean
negative. That failure happened to me anyway - see section 6.

### 2.1 The commission caught a real defect in my own instrument

`commission_noise.py`, 23 cases, all checking **magnitude** rather than sign, because a
null cannot catch an amplitude error. The first version **FAILED**:

```
3x3-box-smoothed noise (true sigma 90/3=30) -> immerkaer 6.649  MAD 22.380
FAIL  planted smoothing detected at right size   got 6.6493  want 30.0000
```

Immerkaer under-reports *correlated* noise by 4.5x. That is not a nuisance, it is the
whole subject of C2: **any estimator built on high-frequency energy scores a low-passed
arm as quieter**. I rebuilt around `sigma_std`, which is correlation-independent, and
turned the bias into the discriminator - `sigma_std / sigma_hf` is ~1.0 for white noise
and rises with smoothing. Final commission, all 23 PASS:

```
white noise sigma=50.00            49.912     49.966   1.000
3x3-box smoothed (true sigma 30)   29.848      6.649   4.489
gaussian sigma_s=2.5 px smoothed   32.359      0.102 318.098
average of N=139 (true sigma 10.178) 10.174   10.151   1.002
common field across R,G,B via green 64.999    64.601   1.006   <- not 0.750x
```

The last two lines are the ones that matter. **Averaging 139 frames leaves the ratio at
1.002; smoothing drives it to 4.5-318.** That is what separates "flat because n frames
were averaged" from "flat because it was low-passed". The final line is ORCH's own luma
trap: I read the green channel directly, never luma, so a common field returns at full
amplitude.

## 3. The measurement space, and why ORCH's was not one

ORCH rendered both arms with `--srgb`. The BEFORE binary's own help says of that flag:

> For looking at, NOT for measuring. [...] the transfer curve is a strong non-linearity
> that moves every ratio a metric computes; more than one result in this project has
> been retracted for exactly that.

and `ORCH-100/RUN.txt` carries its own warning: *"Do not measure absolute levels across
arms: the tone stage normalises each image to its own [black, white] window."* C1 is
exactly a cross-arm absolute level measurement on those files.

**A line of evidence ORCH did not use.** I extracted the `ImageDescription` tag from
both arms' TIFFs and diffed them (`tiffdesc.py`). Both self-declare the same sRGB space,
but their tone black points differ: **BEFORE `0.009846`, AFTER `0.000000`**. That
direction *helps* ORCH - BEFORE subtracts the larger black point, so it should clip
shadows more, and yet BEFORE has 174 zeros against AFTER's 723,429. The tone difference
works against the observed effect, so it cannot manufacture it.

Separately, AFTER's auto black point being **exactly** zero is itself corroboration:
black is `0.85 x p0.1(luminance)`, so p0.1 must already be <= 0. At least 0.1% of AFTER's
pixels were non-positive *before* the tone stage - while the same description asserts
"the toe is soft, so no channel is clamped to zero".

**So I did not measure there.** `strehl.exe`'s default output and `blend-render.exe
--camera-linear` both emit camera-native linear RGB: no colour matrix, no transfer
curve, no tone stage, and white balance with **green = 1** exactly. I measured the green
channel, which therefore carries no gain at all. Both arms 7040x4688; cross-correlation
of the two arms gives an integer shift of **(0, 0)**, so tile-wise comparison is valid.

One caveat I cannot remove: the commissioned AFTER binary (`3E903E99...`) supports only
`--linear`, not `--camera-linear`, so the clean-space arm is a **different build**
(`0d9fd28`). I therefore also measured the commissioned binaries in sRGB, and both agree
(section 4.1 vs 4.2). A build-vintage control shows the two BEFORE builds are **not**
byte-identical:

```
pin-1cacb61 : 92BECEA67C5017AB69266E3DA9CD83DCAA9EC825240117AAEE8EAFFD2C3D9684
0d9fd28     : F9B095D84C1144679A5DC3E39962EAD08F4049A82625429A9C1AD530038FFC15
```

so build vintage is a real variable and is reported rather than assumed away.

## 4. C1 - the clamp. CONFIRMED

### 4.1 It reproduces exactly, on ORCH's own subject and encoding

`flower-bud-alone-cpl`, the commissioned sRGB arms, my `zerocensus.py`:

| channel | AFTER count@0 | % frame | spike ratio | BEFORE count@0 |
| --- | --- | --- | --- | --- |
| R | 60,769 | 0.1841% | 3,159x | 13 |
| G | 98,989 | 0.2999% | 2,212x | 2 |
| B | **723,429** | **2.1920%** | **2,927x** | 174 |

ORCH's 723,429 and 2.192% reproduce **to the pixel**, and the BEFORE median at those
sites is **10,913 DN**, also an exact match. Commissioned smooth-darkening cases read
0.5-0.6x on the same statistic, against a 20x threshold.

**It is a clamp, not a dark scene, and my evidence is different from ORCH's.** ORCH
compared 2.192% at threshold 0 against 2.384% at threshold 256. I instead measured
cross-channel co-occurrence: **only 8.40% of blue zeros are black in all three
channels.** At the other 91.6%, R reads a median of **11,355 DN** and G **10,593 DN**.
A genuinely black scene region is black in every channel; these are pixels where blue
alone is pinned while red and green carry full signal.

### 4.2 It survives in a space with no encoding difference at all

This is the test that retires every encoding confound at once - no tone stage, no colour
matrix, no sRGB curve, both arms in the identical declared space:

| arm (camera-linear) | blue px at 0 | % frame | spike |
| --- | --- | --- | --- |
| AFTER `0d9fd28` | 350,596 | **1.0623%** | 211x |
| BEFORE | **15** | 0.0000% | - |

A ratio of **23,373x**. R and G clamp too (0.1809%, 0.3066%).

**A correction to ORCH's magnitude.** In the clean space the figure is **1.06%, not
2.19%**. The viewing render's tone stage roughly doubles it. The defect is real; the
headline number ORCH quoted is about 2x too large.

### 4.3 The four rival explanations, tested in the clean space

Camera-linear is the harder venue for this, because black subtraction means genuinely
below-black samples legitimately clip to zero. All four rivals still fail:

| rival | result |
| --- | --- |
| packaging / border | **0** of 350,596 zeros lie in an 8 px border band; 0.568% expected if uniform. |
| thin edge ringing | brightest 4-neighbour of a zero has median **10.0 DN**, p99 115; **0.000%** have any neighbour above 4000 DN. Independently, an erosion test commissioned on synthetic rims and discs puts 89.7% of the zero mass in components of >= 1000 px (largest 147,766 px), and on `dry-erase` 93.4% (largest 301,633 px) surviving erosion two thirds of the way to a solid disc. These are area fills. Section 9.3. |
| genuinely black scene | at those 350,596 sites the BEFORE arm reads median **2162 DN** (p10 644, p90 3400) and is itself zero **0.001%** of the time. A black scene is black in both arms. |
| a smooth encoding curve | BEFORE in [2000, 4000) maps to AFTER spanning p1 = **0** to p99 = **5387**, with 11.95% at exactly zero. No single-valued curve sends one input level to both zero and full signal. |

The map at `C:\dev\strehl-out\V-BLEND\pics\flower-bud-alone-cpl-clamp-map.png` shows
compact blobs **inside** the subject - the lower lobes and the right flank - and nothing
at the frame edge.

### 4.4 It generalises, and all three channels clamp

Both subjects ORCH flagged but had not analysed, camera-linear:

| subject | R | G | B | BEFORE R/G/B |
| --- | --- | --- | --- | --- |
| `dry-erase-marker-head-cpl` | 1.8376% (365x) | 2.0836% (427x) | 2.2675% (425x) | 4 / 9 / 59 px |
| `foam` | 0.7311% (138x) | 0.7078% (128x) | 1.0495% (160x) | 343 / 287 / 1,411 px |

**A refinement to ORCH's characterisation.** C1 is stated as "clamps *a channel*". On
`dry-erase` all three channels clamp within 0.43 points of each other. It is better
described as a **shadow clamp that hits whichever channels are dark** - blue happens to
be darkest on the blue-poor flower bud.

### 4.5 The mechanism, and the fact that HEAD has already fixed it

The AFTER binary prints its own base-band policy. At `0d9fd28` it reads:

```
base band       : weighted by the coarsest band's weight, reduced once onto the base grid
```

`pyramid.rs` has already measured that exact choice against the alternative, on this
very subject:

| base band | far-field offset | spatial structure, subject-free quadrant |
| --- | --- | --- |
| `WeightedFromCoarsest` | **-475.0 DN** | 835.0 DN |
| `Mean` | +11.0 DN | 45.0 DN |

A -475 DN level error on a region the ship path renders at ~2162 DN is most of the way
to zero. That is a mechanism, and it predicted where to look next.

**Two commits landed after `0d9fd28` and both bear on this** - `23ae8dc` *"the base band
flips to Mean on measurement"* and `275fbd1` *"confine the reconstruction to the hull of
its inputs, and retract the safety claim that said it already was"*. I built and
rendered `275fbd1`, which now reports:

```
base band       : plain mean across frames
hull clamp      : 8.647% 10.106% 10.105% 10.986%
                  per plane, the fraction of output pixels the reconstruction put outside
                  the range its own input frames support, and which were clamped back
```

One output pixel in ten was being reconstructed outside the range its own inputs
support. **The zero clamp is gone entirely:**

| build | R at 0 | G at 0 | B at 0 |
| --- | --- | --- | --- |
| `0d9fd28` | 59,689 | 101,176 | 350,596 |
| `275fbd1` | **0** | **0** | **0** |

The whole-frame minimum at `275fbd1` is 444 / 446 / 332 DN. Nothing reaches zero anywhere.

**But the fix bounds the error without removing its cause, and this is the part worth
acting on.** At the exact 350,596 sites the old build clamped:

| arm | median | p10 | p90 | % at 0 |
| --- | --- | --- | --- | --- |
| `0d9fd28` AFTER | 0 | 0 | 0 | 100.000% |
| `275fbd1` AFTER | **805** | 566 | 1063 | 0.000% |
| BEFORE (ship path) | **2162** | 644 | 3400 | 0.001% |

`275fbd1` minus BEFORE at those sites is a median of **-1320 DN**, with p90 = **-29**.
The depression is essentially **one-sided**: at almost every one of those pixels the
blend is still darker than the ship path, and only 40.1% now read within +/-30% of it.
The hull clamp stops the reconstruction leaving the frames' range; it does not stop the
reconstruction being wrong inside it. **MEASURED**; whether the residual -1320 DN is a
defect or a legitimate consequence of electing sharper (and darker) frames I did not
determine - see section 7.

## 5. C2 - "the noise penalty is recovered detail". REFUTED as stated

C2 is a three-step argument. Step 1 is a measurement I do not dispute. Steps 2 and 3
each fail on a measurement that was available and not taken.

### 5.1 Step 2's premise is contradicted by the binary's own output

ORCH: *"The control's 'flat' regions are flat because they are patches of a single
DEFOCUSED frame, and defocus is a low-pass filter."*

The control arm is not a patch of a single frame. Its own name for itself is
*"regularised winner + **noise-gated average**"*, and its render log for
`flower-bud-alone-cpl` reports:

```
  gate   tol(DN-norm)   mean n_eff   n_eff=1 %   boundary %   pred sigma gain (model)
  4.00       0.086063      138.719       8.75%        7.62%         0.2411x
```

**Mean n_eff is 138.7 frames averaged per pixel**, and only 8.75% of pixels are
single-frame. The binary even prints the noise model's own prediction for the resulting
sigma reduction: **0.2411x**.

So an implausibly clean floor needs no defocus to explain it. I measured it directly
against a single frame (below): the control sits at **0.345x** a single exposure in the
backdrop. Averaging, not smoothing. **ORCH's stated reason for distrusting the metric is
factually wrong about what the control arm does.**

### 5.2 Step 3's counterfactual is the wrong one - and this is the refutation

ORCH's discriminator: noise is white, so push a synthetic white field through the same
high-pass, get `rho = -0.0035`, and conclude that a measured `rho_add` of +0.45 to +0.94
cannot be noise. *"White noise cannot correlate at 0.45."*

True, and irrelevant, because **the noise in these renders is not white when it arrives**.
Every render passes through a Malvar-He-Cutler demosaic and a CatmullRom resample, and
both are low-pass filters. The honest counterfactual is not a synthetic white field; it
is **real sensor noise that has been through the same chain**. That is measurable: it is
a single-frame render, `STREHL_ONLY_FRAME=102`, which performs no election at all.

Bright backdrop, 616 tiles at 16000-32000 DN, `whiteness.py`:

| signal | sigma | rho_lag1 | HF frac |
| --- | --- | --- | --- |
| synthetic white (ORCH's reference) | 49.96 | **-0.0013** | 0.807 |
| **FRAME102 - one real frame, no election** | 111.57 | **+0.3514** | 0.558 |
| BEFORE | 38.44 | +0.4635 | 0.453 |
| AFTER | 69.76 | +0.6652 | 0.270 |
| the change (AFTER - BEFORE) | 48.65 | +0.6984 | 0.241 |

My synthetic white reads **-0.0013** against ORCH's -0.0035, so the two statistics agree
in the white limit and the comparison is fair. But **pure sensor noise, no merge, no
election, reads +0.3514** - about 100x ORCH's counterfactual and most of the way to the
figures the argument treats as proof of optical detail. A causal control isolates the
interpolator: the *same frame* rendered **binned**, one RGB sample per real 2x2 sensor
quad with no interpolation at all, still reads

```
frame 102 DEMOSAICED (Malvar-He-Cutler)   tiles 617  sigma 106.826  rho 0.3526  HF frac 0.5499
frame 102 BINNED (no interpolation)       tiles 151  sigma  82.786  rho 0.2025  HF frac 0.6917
```

so roughly half the correlation is made by the demosaic and the rest is there before it.
Either way the reference value is **+0.20 to +0.35, not +0.002**. The inference
"it correlates, therefore it is not noise" does not survive its own control.

For completeness, these backdrop tiles really are noise-dominated: correlating frame
102's residual against frame 103's - two adjacent exposures of the same defocused
backdrop - gives a median of **+0.1420** (p10 +0.1133, p90 +0.1696), so about 86% of the
residual does not reproduce between exposures.

### 5.3 Where there is provably no detail, the blend still adds energy

A single frame is two bounds at once. It is one real exposure with no election and no
averaging, so its noise is the sensor's actual floor **in this exact domain**; and it
already contains every bit of scene detail any merge could recover.

`threeway.py`, same tiles for all three, selector belonging to none of them:

| signal bin | ntile | FRAME102 | BEFORE | AFTER | BEFORE/FRAME | AFTER/FRAME |
| --- | --- | --- | --- | --- | --- | --- |
| 1000-2000 | 89 | 29.63 | 69.96 | 70.85 | 2.361 | 2.392 |
| 2000-4000 | 65 | 36.03 | 103.89 | 87.39 | 2.884 | 2.426 |
| 4000-8000 | 14 | 84.02 | 424.46 | 253.19 | 5.052 | 3.014 |
| 8000-16000 | 19 | 96.71 | 40.14 | 129.73 | 0.415 | 1.341 |
| **16000-32000** | **616** | **111.57** | **38.44** | **69.76** | **0.345** | **0.625** |

The 16000-32000 bin is 77% of the selected tiles and it is the **out-of-focus backdrop,
defocused in every frame of the bracket**. There is no detail there for any merge to
recover, by construction. In that bin:

- BEFORE sits at **0.345x** a single exposure - real averaging, close to the model's own
  printed prediction of 0.2411x, and nothing to do with defocus.
- AFTER sits at **0.625x** - it averages too, just less.
- **AFTER carries 1.815x BEFORE's noise in a region where recovered detail cannot exist.**

That is the core of the refutation. Whatever the blend adds *here* is not recovered
detail, because there is nothing here to recover. The lower bins do show both merges
above the single frame, but those are subject tiles where the merge is legitimately
sharper than a defocused frame, so I draw no conclusion from them.

**This is unchanged by the HEAD fix.** Re-measured on `275fbd1`: AFTER 69.609 (vs
69.757), rho 0.6653 (vs 0.6652), HF frac 0.2694 (vs 0.2695). The base-band fix cured the
clamp and left the noise penalty exactly where it was.

### 5.4 ORCH's flat-tile selection: not unbiased, but the sign survives

ORCH asked directly whether selecting tiles on the arm-average biases the result. It
does. `armcompare.py`, identical tiles within each rule, AFTER/BEFORE ratio of
`sigma_std`:

| selector | weighted AFTER/BEFORE |
| --- | --- |
| arm-average (ORCH's rule) | **1.401** |
| BEFORE only | **2.021** |
| AFTER only | **1.208** |

The headline penalty moves between **+21% and +102%** on selection rule alone, a factor
of 1.7. ORCH's arm-average rule lands between the two extremes, which is the best that
can be said for it. **The sign is robust - AFTER is noisier under all three rules - but
the magnitude is not, and no single number should be quoted without its rule.** This
also puts BUILD-BLEND's +12.3% and ORCH's +32%/+105% inside one instrument's range of
free choice.

### 5.5 The calibrated noise model - the test ORCH rated strongest, and it refutes C2

ORCH wrote that comparing against the project's calibrated noise model *"is probably
stronger than anything I did"*, and did not run it. I ran it.

`crates/strehl-core/src/noise.rs` gives `var = g*S + (RN_e*g)^2` with measured green gain
`g = 0.221113 DN/e-`, `RN_e = 1.47 e-`, black 512, white 15360. Camera-linear TIFFs carry
`k = 65535/14848 = 4.4137` TIFF-DN per raw DN, and green's white-balance multiplier is
**exactly 1.0**, so the green channel needs no gain correction at all.

`noisemodel.py` is commissioned on synthetic Poisson+read fields at three levels, on
2- and 16-fold averaging, on a noiseless null, and on the DN scaling - **7/7 PASS**,
worst error 0.44%. Validated against reality on the **binned** single frame (one RGB
sample per real 2x2 sensor quad, no interpolation anywhere):

```
fb-FRAME102-BINNED.tiff  nsamp=2
     signal bin  ntile  meas sigma  model 1-frame  meas/model
  16000-  32000     98      76.853         95.356      0.8060
```

0.81x, with my flattest-25% rank rule biasing measurement low by construction. **The
model is calibrated for this sensor and this data**, so its predictions can be used as a
physical floor.

**First result: a defocused frame is not a quiet frame, and this is where C2 step 2
breaks.** Defocus is an optical low-pass applied *before* the sensor. Shot noise and read
noise are added *at* the sensor. **Defocus cannot reduce noise.** Measured, not argued:
frame 102's backdrop is defocused in every frame of the bracket and reads **sigma
111.57 DN**, against the model's 95-136 DN for one frame. A single defocused frame is
exactly as noisy as a focused one.

So `sigma = 7.8 DN` cannot be produced by "a patch of a single defocused frame" - that
patch would read ~110 DN. It can only be produced by averaging, which is what the control
arm's own log says it does.

**Second result, on ORCH's strongest subject.** `bee-1-cpl`, camera-linear, my code:

| bin | ntile | BEFORE sigma | AFTER sigma | model, 1 frame | BEFORE/model | AFTER/model |
| --- | --- | --- | --- | --- | --- | --- |
| 8000-16000 | ~185 | 8.855 | 137.737 | 120.9 | **0.073** | **1.156** |
| **16000-32000** | ~120 | **8.746** | **148.861** | **135.9** | **0.064** | **1.156** |

I reproduce ORCH's own figure independently: 8.746 -> 148.861 is **+1602%** against ORCH's
+1605%. The numbers agree; the interpretation inverts.

- BEFORE sits at **0.064x** the single-frame floor, an implied ~240 averaged frames out of
  299 available. Entirely physical: in a defocused backdrop every frame agrees, so the
  noise gate admits nearly all of them. Its log reports `mean n_eff 72.085` frame-wide,
  and the backdrop is exactly where that average is highest. **Nothing implausible
  remains to be explained.** The premise of C2 step 2 dissolves.
- AFTER sits at **1.156x** the single-frame floor - it is **noisier than one raw
  exposure** in a region that is out of focus in all 299 frames. No merge can recover
  detail that is not in any input, and no merge that averages can exceed the noise of a
  single input. Whatever the blend adds here is neither detail nor averaged noise; it is
  generated by the merge.

That is C2 refuted on the instrument ORCH nominated, on the subject ORCH considered
strongest, using ORCH's own magnitude.

### 5.6 C1 also holds on bee-1, giving four subjects

| subject (camera-linear) | AFTER R / G / B at 0 | BEFORE R / G / B |
| --- | --- | --- |
| `flower-bud-alone-cpl` | 0.1809% / 0.3066% / 1.0623% | 2 / 1 / 15 px |
| `dry-erase-marker-head-cpl` | 1.8376% / 2.0836% / 2.2675% | 4 / 9 / 59 px |
| `foam` | 0.7311% / 0.7078% / 1.0495% | 343 / 287 / 1,411 px |
| `bee-1-cpl` | 0.0551% / 0.0998% / 0.1224% | 105 / 32 / 84 px |

## 6. Defects found in my own instruments

Reported because an unstated instrument failure is worth more to the next agent than a
clean-looking result.

1. **The Immerkaer estimator under-reports correlated noise by 4.5x.** Caught by the
   commission's planted smoothing, not by any null. Rebuilt around `sigma_std`.
2. **My first flat-tile rule was a guessed threshold and it returned a clean-looking
   nothing.** `structure index < 1.5` selected **0 of 8030** tiles on the BEFORE arm and
   1 of 8030 on AFTER, printing a table of "(too few)" and a verdict of `nan`. The rule
   normalises by what *white* noise would do under downsampling, and real demosaiced
   noise is correlated, so the index exceeds 1.5 everywhere. This is exactly the failure
   ORCH warned about, committed anyway. Replaced with a threshold-free rank rule (the
   flattest K% within each signal bin).
3. **My spectral discriminator failed its own positive control and I discarded it.** I
   predicted that recovered focus detail must be high-frequency, so a low HF fraction
   would mark the added energy as artifact. Measured, genuine recovered detail
   (`BEFORE - FRAME102` on subject tiles) reads **HF frac 0.0274**, *lower* than the
   added energy's 0.241 - because the difference between a sharp image and a defocused
   one is dominated by the broad blur bowl, not by fine detail. **The HF-fraction
   argument does not work and no conclusion here rests on it.**
4. `zerocensus.py`'s `p0 > 1e-4` guard is slightly too low: `foam`-before trips the CLAMP
   label at 0.0111% on 3,657 pixels. The spike ratio alone can fire on negligible
   populations. It did not affect any verdict here, since every AFTER arm is 60-200x
   above that.

## 7. What I could not decide

- **Whether the residual -1320 DN shadow deficit at `275fbd1` (section 4.4) is a defect.**
  It is one-sided and large, but a blend that elects genuinely sharper frames could
  legitimately land darker. Distinguishing those needs a per-pixel comparison against the
  elected frames, which I did not build.
- **What the blend's added backdrop energy actually is.** The noise model settles that
  it is not recovered detail and not merely under-averaged noise - on `bee-1-cpl` the
  blend exceeds a single raw exposure (1.156x), which averaging cannot do, so the merge
  is generating energy. Its rho of +0.70 against a single frame's +0.35 says the
  generated energy is coarser than sensor noise, which is consistent with the -475 DN /
  835 DN base-band structure `pyramid.rs` measured. I did not isolate the term
  responsible, and I did not check whether it persists at HEAD in the same form on
  subjects other than `flower-bud-alone-cpl` (there it does: section 5.3).
- **C2 outside flat regions.** Everything in section 5.3 is argued on backdrop tiles,
  where the absence of detail is what makes the test decisive. I have **not** shown that
  the blend recovers no real detail anywhere - only that its measured noise penalty in
  flat regions is not explained by detail recovery.
- **ORCH's `rho_add` algebra.** I did not check it, because I did not need to: I measured
  the literal difference between the arms instead. If the algebra is right, the
  conclusion still fails on the counterfactual (section 5.2).

## 8. Files, and the pictures to look at

Scratch, instruments and logs live in `C:\dev\strehl-out\V-BLEND\`; the instruments
and their logs are mirrored into `experiments/V-BLEND/src/` and `experiments/V-BLEND/logs/`.
Pictures stay in scratch because `*.png` is gitignored repo-wide.

**Look at this one first:**

```
C:\dev\strehl-out\V-BLEND\pics\flower-bud-alone-cpl-clamp-map.png
```

Left, the BEFORE arm's blue channel; right, every pixel the AFTER arm sets to exactly
zero. The zeros are compact blobs **inside** the subject - the lower lobes and the right
flank - with nothing at the frame edge and no edge-following ring. That single picture
disposes of the packaging and edge-ringing rivals visually, and it is what a print would
show as blocked-up black.

```
C:\dev\strehl-out\V-BLEND\pics\fb-spectrum.png
```

Radially averaged power spectra of the two arms' backdrop residual against a synthetic
white field. Included for completeness; the spectral argument failed its positive control
(section 6.3) and no conclusion rests on it.

## 9. Reconciliation with ORCH's own code, and two errors in it

Read only after every number above existed, as commissioned. The **conclusion** of C1
holds. Two things ORCH told me about it do not, and one of them is the same class of
error ORCH withdrew earlier tonight.

### 9.1 `clip_linear.py` is not measuring where it says it is

Its docstring states the method plainly:

> The linear 16-bit TIFF sits upstream of the tone stage, so it separates them.

It then reads `TIFF_DIR = C:\dev\strehl-out\ORCH-100\_tiff`, which holds the
**`--srgb`** renders. I extracted their `ImageDescription`:

```
sRGB (IEC 61966-2-1) ... sRGB transfer curve. For viewing.
Tone rendering: black 0.000000, white 0.361854 (linear, luminance percentiles
0.1/99.9 with white mapped to 0.9), black fraction removed 0.85,
display-space contrast 0.550.
```

Those files are **downstream** of the tone stage, not upstream of it. The separation the
script says it performs is not performed by the file it opens. ORCH's separate
tone-stage control (same binary, same merge, tone the only difference, 0.0077 pt against
2.192 pt) rescues the conclusion empirically, and my camera-linear repeat settles it
independently - but the reasoning as written in the script is invalid on its own input.

### 9.2 ORCH's own script prints the opposite verdict to the one ORCH reported

I ran `clip_where.py` unmodified:

```
> python clip_where.py
  pixels at exactly 0 : 723,429  (2.1920%)
  brightest 4-neighbour of a zero pixel: median 0.0 DN
  control-arm gradient magnitude: at the zero pixels median 282.0, image-wide 48.6
    ratio 5.8x
VERDICT
  RINGING. The zeros sit at high-gradient sites where the control arm is bright.
  ... This is a real defect in the merge, it is upstream of the tone stage ...
```

ORCH reported to me "**Not** thin edge ringing". The instrument says RINGING. ORCH
reached the better answer by overriding their own verdict on the neighbour statistic,
which the verdict expression never consults - it tests only `median(B[zero]) > 2000 and
gradient ratio > 2.0`. **ORCH is right and the script is wrong**, but the script is the
artifact that would be read next.

### 9.3 The 5.8x gradient association is an artifact of the sRGB curve

This is the substantive part. `blobshape.py` recomputes the same gradient statistic in
camera-linear, and adds an erosion test that can actually tell a rim from a blob. It is
commissioned on synthetic shapes - a 2 px rim, a 4 px rim and a solid disc - **4/4 PASS**,
with the thresholds set from the shapes' measured behaviour rather than guessed. (My
first thresholds *were* guessed and the commission failed 2/4; discrete erosion leaves
9% of a 2 px annulus at k1.)

| | sRGB (ORCH) | camera-linear (mine) |
| --- | --- | --- |
| `flower-bud-alone-cpl` gradient ratio at zeros | **5.8x** | **1.17x** |
| `dry-erase-marker-head-cpl` gradient ratio at zeros | - | **0.68x** |

The association vanishes. It has to: the sRGB curve's slope is steepest approaching
black, so gradients measured at dark pixels are amplified relative to a frame-wide
median dominated by bright ones. Measuring gradient in a display space manufactures a
correlation between darkness and gradient. In the linear space `dry-erase`'s zeros sit
at **lower** gradient than the image median.

The erosion test says the same thing about geometry:

| shape | k1 | k2 | k3 | k6 |
| --- | --- | --- | --- | --- |
| synthetic 2 px rim | 0.095 | **0.000** | 0.000 | 0.000 |
| synthetic 4 px rim | 0.543 | 0.087 | **0.000** | 0.000 |
| synthetic solid disc | 0.940 | 0.882 | **0.826** | 0.664 |
| `dry-erase` zeros | 0.779 | 0.644 | **0.551** | 0.357 |
| `flower-bud` zeros | 0.320 | 0.178 | **0.149** | 0.112 |

`dry-erase`'s zeros survive erosion two thirds of the way to a solid disc and 93.4% of
their mass sits in components of 1000 px or more, the largest **301,633 px**.
`flower-bud`'s are thinner but still put 89.7% of their mass in components of 1000 px or
more, largest 147,766 px. **Neither is a rim.** These are solid area fills, which is what
a base-band level error produces and not what Laplacian overshoot produces.

So ORCH's stated mechanism in `clip_where.py` - band-pass undershoot at edges - is
**refuted**, while ORCH's summary characterisation to me ("a hard clamp, not thin edge
ringing") is **confirmed**. The mechanism is the one in section 4.5: a base band that
carries a measured -475 DN offset, which `pyramid.rs` had already quantified and HEAD has
since replaced.

### 9.4 Where we agree

- 723,429 blue zeros, 2.1920% of frame, BEFORE median 10,913 DN - **to the pixel and to
  the DN**, from independently written code.
- The border test, the brightest-neighbour test and the threshold ramp all reproduce.
- Both of ORCH's excluded confounds hold. I added a third line of evidence on the
  encoding one - the arms' declared tone black points differ in the direction that works
  *against* the claim (section 3).
- On C2 I did not use ORCH's `rho_add` estimator and I make no claim about its algebra.
  The disagreement is not arithmetic; it is that the reference it is compared against is
  not the right reference (section 5.2), and that the calibrated model settles the
  question without it (section 5.5).
