# M29 — Static multiplicative defects (dust): the detection limit, and the free lunch that isn't

> **NOT INDEPENDENTLY VERIFIED.** Every number below was produced and written up by
> the same agent. Per rule 12 and the project's standing discipline, treat it as a
> hypothesis with a script attached, not as a conclusion. The scripts are committed
> exactly as run.

Review item **R11** had two halves. M22 measured the additive half (hot pixels:
11,393 = 0.0346% of the sensor). This is the multiplicative half — dust — and the
claim that motivated it:

> A **selector** copies one frame's pixel into the output, so a dust shadow arrives at
> full contrast. An **estimator** averages `n_eff` frames, and because the warp displaces
> the dust relative to the scene by a different amount in every frame, the shadow lands
> in `n_eff` different places and is diluted. If that is real, every shipping stacker puts
> dust in the output at full strength and strehl suppresses it without doing anything.

That is an attractive claim: a free, unclaimed advantage falling out of the thesis. It
is also false, and the interesting part of this milestone is that establishing that did
not require detecting a single speck of dust.

Six scripts. Four of them exist because of defects in the three before them, all mine.

---

## 1. The instrument, and why the first two versions of it could not work

A static multiplicative defect is fixed in **sensor** coordinates while the scene moves
(slightly) under the warp. Dividing each frame by a blurred copy of itself removes scene
content at scales above σ=24 green px and leaves small-scale multiplicative structure;
averaging that ratio over frames and highpassing gives the **static map**

```
m = mean_k[ g_k / blur24(g_k) ] − 1 ,   then   m ← m − blur24(m)
```

**Script 01** correlated whole static maps across the six stacks. Result: cross-stack
`r` = 0.002–0.016 against shift nulls of 0.001–0.008. A bare null — and uninterpretable,
for two reasons I only saw with the numbers in front of me.

**Defect (a) — the positive control validated a statistic I do not use.** A planted 4.0%
shadow was recovered at **259.6σ** — but against the rms of the *difference* between the
planted and unplanted maps of the same stack, which is an oracle nobody has. Against the
quantity actually available at inference time, the map's own rms of 0.1475, the same
plant is 1.096% deep, i.e. **0.074σ**. Invisible. This is **discipline 121** in a second
costume: a control divided by a quantity unavailable at inference time.

**Defect (b) — a global correlation cannot see a sparse localised defect.** For dust of
depth `A` covering a fraction `f` of the sensor,

```
r ≈ f·A² / σ_map²
```

For a generous `f = 0.0017`, `A = 0.04`, `σ_map = 0.15`: `r ≈ 1.3e-4` — more than an
order of magnitude *below* the measured shift nulls. Reaching null level would need a 32%
shadow or 11% sensor coverage. **The instrument was never capable of answering the
question it was pointed at.** Computing that number before running the correlation would
have cost one line of algebra.

### One incidental result worth keeping

Script 01's Q3 control asked whether same-subject stacks correlate more than
different-subject ones — if so, the map is measuring residual scene structure, not sensor.

| pair | r | shift null |
|---|---|---|
| `112MSDCF` × `113MSDCF` (same session) | **0.9370** | 0.0845 |
| `coffee-bean` × `coffee-bubbles` | 0.0001 | — |
| different-subject pairs | 0.002–0.016 | 0.001–0.008 |

Same-ish median 0.4685 vs different-subject median 0.0017 — a ratio of **271.92×**. Q3
fails outright: the static map is dominated by scene, and two stacks shot in the same
session of the same subject share 94% of it. Section 4 turns that from a nuisance into
the milestone's actual finding.

---

## 2. Two more defects, and the mechanism they exposed

**Script 02** replaced the global correlation with the right family of statistic — the
**per-location conjunction** M22 used for hot pixels: standardise each map, take the
per-pixel minimum across stacks, smooth at the dust scale. `min(a₁…a₆) < t` requires
*every* stack to show a shadow at least that deep, which is the definition of a defect
fixed in sensor coordinates. It also swept plant depth, and the sweep is what exposed it:

```
 frame depth  plant value
        0.0%       -3.923
        4.0%       -3.924
       16.0%       -3.928
```

**The plant moved the statistic by 0.005 over a 32× range of depth.**

**Defect (c) — a window extremum is pinned by the scene, not by the plant.** Script 02
read the plant as the minimum over a 60×60 window, i.e. an extremum over 3,600 correlated
pixels. The window's minimum lives wherever the scene happens to be most negative; adding
a small dip at the exact centre does not move it.

**Defect (d) — standardising makes a common defect non-common.** Dust is a *common
fractional depth*. Dividing each map by its own rms divides that common quantity by a
per-stack scene number that ranges 6.5× across this corpus (`coffee-bean` 0.053,
`coffee-bubbles` 0.345), so the same physical dust becomes six different signals.

**Script 03** then reconciled a discrepancy I had been carrying without noticing. Script
02 used `ATTEN = 0.274`, script 01's measured map-domain trough for a 4% frame-domain
plant. Writing down the pipeline's algebra afterwards predicts **0.885**:

```
blur24(σ=6 Gaussian) at centre = 36/(36+576) = 0.0588
ratio step keeps      (1−A)/(1−0.0588A) ≈ 1 − 0.941A
highpass step keeps   0.941A·(1−0.0588)  ≈ 0.885A
```

A factor of 3.2 is not a rounding disagreement. Measured, on real data through script
01's exact code path:

| depth | σ=3 | σ=6 | σ=12 |
|---|---|---|---|
| 1.0% | 0.342 | 0.324 | 0.254 |
| 4.0% | 0.342 | 0.324 | 0.255 |
| 16.0% | 0.342 | 0.325 | 0.258 |

The response is **dead linear in depth** (three decimal places over a 16× range) — which
matters later — but it sits at 0.32, not 0.885, and it falls with plant radius.

**The missing factor is `g/blur(g)` at the defect.** The plant's contribution to the map
is modulated by the scene's own local relative brightness:

```
map response  R ≈ 0.92 · (g/blur24(g)) at the defect location
```

Script 04 confirms this directly by measuring both quantities at three locations in six
stacks: where `g/blur = 0.29` the response is `R = 0.274`; where `g/blur = 1.16` it is
`R = 1.065`; where `g/blur ≈ 1.00` it is `R ≈ 0.89–0.95`.

**My algebra was right. My calibration constant was an accident of location.** Script 01
happened to plant at a pixel sitting at 29% of its local mean, measured that pixel's
response, and I globalised it — a 3.4× underestimate everywhere else.

The consequence is the physical heart of this milestone: **a self-ratio static map
responds to defect depth × local scene brightness relative to its neighbourhood. A shadow
on a dark pixel is attenuated in proportion.** This is exactly why a flat field is the
right instrument and a subject frame is not — a flat has `g/blur(g) ≡ 1` everywhere by
construction, so the response is uniform and maximal.

---

## 3. The detection limit

**Script 04** uses the measured linearity to make the sweep exact and cheap: one
frame-domain plant per (stack, location) measures the response coefficient `R_ij`, and
every depth after that is arithmetic on the base map, with no approximation beyond a
linearity that was *measured* rather than assumed. Readout is at the planted pixel — not
a window extremum. Three locations, spanning the scene-brightness modulation.

| statistic | shift-null p0.001 | unplanted p0.001 | **Q9 excess** |
|---|---|---|---|
| raw conjunction | −1.0140 | −1.0141 | **−0.0001** |
| standardised conjunction | −5.3672 | −5.3666 | **+0.0006** |

**Q9: no excess over the shift null anywhere in the tail** (raw excess −0.0001 to −0.0018;
standardised +0.0006 to −0.0145). No localised, sensor-fixed, common structure is present
above the noise of this instrument.

The plant sweep says how weak that statement is:

| depth | loc0 | loc1 | loc2 |
|---|---|---|---|
| 4% | −3.00 | −0.72 | −0.50 |
| 16% | −3.19 | −1.96 | −1.22 |
| 32% | −4.52 | −3.99 | −3.33 |
| **50%** | **−6.89 FIRE** | **−6.32 FIRE** | **−6.08 FIRE** |

**Detection limit: between 32% and 50% shadow depth.** Real sensor dust is 1–15% at
working apertures. **Q7 holds** (the 50% positive control fires at all three locations, so
the statistic is not simply broken). **Q8 holds in the sense that a limit exists**, though
the sweep is too coarse to separate the three locations.

The **raw** conjunction never fires, even at 50%, and the reason is structural: `min`
across heterogeneous instruments is bounded by the worst member, and `coffee-bubbles`'
map rms is 6.5× `coffee-bean`'s, so it alone sets the tail at −1.014 while the deepest
plant can only push the minimum to −0.55. The per-stack drop is bounded below by
`min_i(R_i)`, which at loc0 is 109MSDCF's 0.274 — and 0.274 × 0.50 × 0.8 (the σ=3
smoothing loss on a σ=6 shadow) = 0.11, exactly the measured −0.107 shift. The statistic
behaves precisely as modelled; the model just says it cannot work here.

---

## 4. Why the limit cannot be bought with more frames

Two candidates for the floor, with opposite consequences: shot noise falls as `1/√n` and
the limit is a budget problem; scene texture does not fall at all, because **the scene is
common to every frame of a stack**, and the limit is structural.

**Script 05** sweeps `n` and reads the exponent — discipline 131 used as an instrument.

| n | map rms | if 1/√n | pair-diff rms |
|---|---|---|---|
| 1 | 0.14412 | 0.14412 | — |
| 2 | 0.14545 | 0.10191 | 0.01609 |
| 4 | 0.14841 | 0.07206 | 0.01519 |
| 8 | 0.15343 | 0.05095 | 0.02200 |
| 16 | 0.15447 | 0.03603 | 0.02951 |

**Q10 holds decisively: exponent +0.025 over a 16× range.** Dead flat — it even *rises*
slightly, because more frames span more focus positions and the defocus spread is itself
part of the scene term. The floor is scene, not noise, and **no amount of shooting the
subject will move it.**

**Q11 refuted, and instructively.** I predicted the pair-difference would isolate the
stochastic part and fall as `1/√n`. It *rises*, exponent **+0.292** — because the two
halves being differenced sit at *different focus positions*, so the difference contains
defocus change, not just noise. This is **discipline 130 in my own script**: I chose the
reference to maximise sample count instead of to minimise the nuisance term. The `n=2`
entry, which differences two *adjacent* frames, is the only one near the true stochastic
floor: **1.6%**, against a scene term of 15.4% — a ~10× separation.

### What a flat field buys, from the calibrated model with no free parameters

`σ²(S) = g·S + (RN_e·g)²`, `g = ISO/436.8`. A flat has `g/blur(g) ≡ 1`, so its map floor
is pure photon noise:

| ISO | level DN | per frame | n=20 | n=64 | 5% dust at n=20 |
|---|---|---|---|---|---|
| 100 | 8000 | 0.535% | **0.120%** | 0.067% | **42σ** |
| 100 | 12000 | 0.437% | 0.098% | 0.055% | 51σ |
| 160 | 8000 | 0.677% | 0.151% | 0.085% | 33σ |

> The final column is printed by script 05 with a trailing `s`, which is a formatting
> defect in a script that has been run and must therefore not be edited. The values are
> multiples of σ, not seconds.

**Subject-stack floor 0.15447 vs best flat floor at n=20 of 0.00098 — a 158× improvement.**
This converts the standing request in `captures-needed.md` §4 from an assertion into a
specification (§6 below).

---

## 5. The claim itself, priced — and refuted

The dilution claim does not require detecting dust. It is a statement about geometry:
given how far the warp moves sensor coordinates relative to scene coordinates *between
the frames a merge actually averages*, a shadow of known radius is diluted by a computable
factor. **Script 06** measures the displacements by phase correlation of 256 px tiles on
rings at four radii, then evaluates

```
D = max_x (1/n) · Σ_k exp( −|x − d_k|² / (2σ_d²) )
```

`D = 1` is no suppression, and a selector is `D = 1` by definition.

Measured adjacent-frame displacement, median over tiles:

| stack | r=0.15 | r=0.35 | r=0.55 | r=0.75 |
|---|---|---|---|---|
| `109MSDCF` sep 1 | 0.15 px | 0.18 px | 0.19 px | 0.22 px |
| `coffee-bean` sep 1 | 0.12 px | 0.11 px | 0.12 px | 0.07 px |

**Adjacent-frame warp is sub-pixel** — 0.07–0.22 green px, consistent across two stacks,
four radii and sixteen tiles each. That independently corroborates M28's finding that the
adjacent-frame residual sits at 1.099× the pure-noise expectation.

| σ_d | n=3 span1 | n=5 span1 | n=5 span4 | n=9 span8 |
|---|---|---|---|---|
| 5 px | 0.999–1.000 | 0.998–1.000 | 0.68–1.00 | 0.25–1.00 |
| 10 px | 1.000 | 1.000 | 0.90–1.00 | 0.50–1.00 |
| 20 px | 1.000 | 1.000 | 0.97–1.00 | 0.80–1.00 |

**Q13: the claim does not survive. `D = 0.999` at `n_eff = 3`.**

The mechanism is the one I pre-registered as my doubt, and it is worth stating plainly
because it generalises: **an averaging estimator suppresses a sensor-fixed defect only to
the extent that the frames it averages are displaced relative to one another — and a focus
merge averages adjacent frames precisely because they agree.** M27 measured `n_eff ≈ 3` at
full sampling density; M28 measured that pairwise disagreement grows near-linearly with
separation. The merge gathers the frames with the *least* warp between them. A 0.2 px
displacement does not move a shadow 10–40 px across.

> **Measurement defect, disclosed.** The `sep 8` and `sep 16` columns are unreliable —
> phase correlation loses lock as the defocus difference grows and the peak collapses onto
> zero lag (visible as implausible 0.04–0.10 px medians at large separation). The `n=9
> span8` column therefore is **indicative only**. The Q13 result depends on the `sep 1`
> column alone, which is clean, and is robust: any displacement below ~1 px gives
> `D > 0.98` for every dust radius considered.

**Q14 is unresolved for the same reason** — the direction is clear (dilution is bought by
*span*, not by *count*) but the numbers that would price it rest on the broken columns.

---

## 6. Consequences

1. **Dust must be handled explicitly.** The merge does not remove it, does not dilute it,
   and cannot detect it. Flat-field division or an explicit defect map is required. This is
   now a design decision, not an open question.
2. **Dust cannot be characterised from subject stacks — with a number.** The limit is
   32–50% shadow depth against real dust of 1–15%, the floor is scene texture, and it does
   not improve with frame count.
3. **`captures-needed.md` §4 gets a specification, not a request:** ≥16 flats **per working
   aperture**, ISO 100, mid-tone at 8,000–12,000 DN. That reaches a 0.10–0.12% floor, at
   which a 5% shadow is a 42–51σ detection. Eight flats still gives ~26σ. The per-aperture
   requirement matters because dust visibility scales with aperture.
4. **The static-map response is scene-modulated** (`R ≈ 0.92·g/blur(g)`), so any future
   defect map built from subject frames — dust, PRNU, anything multiplicative — must
   divide by the local relative brightness or it will report a defect field shaped like
   the scene.
5. **Not falsified, and now cheaply falsifiable:** once flats land, re-run script 04's
   conjunction with the flats included. At a 0.12% floor the same statistic is 400× more
   sensitive and either finds dust or bounds it below 1%.

---

## 7. My errors in this milestone

Five, all caught by controls or by algebra I should have done first:

1. **A global correlation for a sparse localised defect** (script 01) — one line of algebra
   would have shown the statistic was ~10× below its own null before it was run.
2. **A positive control scored against an oracle** (script 01) — 259.6σ against a
   difference map nobody has; 0.074σ against the available quantity. Discipline 121.
3. **A window-extremum readout** (script 02) — moved 0.005 over a 32× depth range.
4. **Standardising a common fractional defect** (script 02) — divided a common quantity by
   a per-stack number varying 6.5×.
5. **Adopting an empirical constant that disagreed with my own algebra** (scripts 01→02) —
   0.274 vs 0.885, carried unexamined into a second script. The algebra was right; the
   constant was one pixel's scene brightness.
6. **Q11: choosing a reference to maximise sample count** (script 05) — the exact error
   discipline 130 was written to prevent, committed two milestones later in my own script.

The one that generalises furthest is (5): **when a measured constant disagrees with the
algebra, the algebra usually has a hidden factor that varies. Find it before adopting the
empirical number** — otherwise a local accident is promoted to a global constant, and
every downstream number inherits it silently.

---

## 8. Scripts

| script | what it does | status |
|---|---|---|
| `01-static.py` | global cross-stack correlation, frame-domain plant | ran; **result uninterpretable**, defects (a),(b) |
| `02-conjunction.py` | standardised conjunction, window-min readout | ran; **result invalid**, defects (c),(d) |
| `03-atten.py` | pipeline response vs depth and radius | ran; linearity + the `g/blur` mechanism |
| `04-limit.py` | corrected conjunction, exact linear plant, 3 locations | ran; **the detection limit** |
| `05-floor.py` | floor attribution by n-sweep; flat-field budget | ran; **scene, exponent +0.025** |
| `06-dilution.py` | displacement measurement; dilution factor | ran; **claim refuted, D=0.999** |

Scripts 01 and 02 are committed despite being wrong. They are the evidence for the four
defects, and deleting them would leave §1–2 unsupported.
