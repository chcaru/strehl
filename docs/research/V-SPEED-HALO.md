# V-SPEED-HALO — the halo, audited before it was fixed

**Lane:** V-SPEED. **Assignment:** ORCH, "diagnose the mechanism, rule out the
instrument first, then fix it, and do not regress the seven clean subjects."

**Status of the premise: substantially refuted.** The four HALO verdicts I was
handed came from an instrument that measures a background gradient, could only
score 11 of 26 subjects, and disagrees with itself on 3 of its own 4 targets.
Two of the four are lighting arches. Five real halos were invisible to it.

**Status of the fix: a mechanism is confirmed but it is a minority of the
defect, and the best-looking candidate fix was not doing what it appeared to.**
Removing per-pixel selection *entirely* — which makes selection ringing
impossible by construction — still leaves **84–90%** of the measured halo on
four of five tonally-comparable subjects. And `--pyramid-bands 5`, whose
headline was −91.2% on one subject, achieves that by **tilting the background
until an existing decline stops being a local maximum**, not by removing a
ring. Across twelve subjects it performs a genuine localised ring removal on
**one**, makes one worse, and re-renders ORCH's showcase `bee-1-cpl`. **I am
not recommending a default change.**

---

## 0. Provenance

| | |
|---|---|
| repo HEAD at time of writing | `5f25a5d8` |
| binary under test | `target-vspeed\release\strehl.exe` |
| binary SHA-256 | `7252AF9C19A5BFE28789662E88D157D079A26C0689B7956D81153E26E32FEA8F` |
| `--version` | `strehl 0.0.0 (cc98561582ab-dirty)` |
| render recipe | `stack <dir> --out <f> --srgb`, **no `--auto-exposure`** |
| corpus under test | `C:\dev\strehl-out\ORCH-FAITHFUL\faithful\`, 26 masters |
| outputs | `C:\dev\strehl-out\V-SPEED-HALO\` |

**Two confounds I do not control and must state.**

1. The binary is `-dirty`. Its working tree included BUILD-CROP's uncommitted
   `merge_cmd.rs`, which I am forbidden to touch and could not exclude. Every
   arm in every sweep shares that state, so *differences between arms* are
   attributable to the flags; *absolute* numbers are not comparable to another
   lane's binary.
2. It was built at `cc985615` and HEAD has since moved to `5f25a5d8`.
   Everything below is internally consistent and none of it is quotable
   against numbers taken at a different commit.

I am in ORCH's **case 3**: rendered at HEAD *without* `--auto-exposure`, which
is the faithful-corpus recipe (fact 1823). The exposure regression does not
touch this work, and I verified that rather than assuming it — see §2.

---

## 1. The instrument was wrong, and it was wrong in a specific, checkable way

`halo_profile.py` computes

```
overshoot = max(band median over 0..120 px) - median(far field 400..900 px)
```

That is the height of the *highest* radial band above the far field. It is not
a rim detector. A rim is a **local** excursion — a bump with background on both
sides — and this statistic never asks for the "both sides" part.

**Measured, and this is the whole conviction: on 11 of 11 scorable subjects the
argmax lands in the outermost band (80–120 px).** The statistic reports the
outer end of the penumbra on every subject in the corpus. It cannot report an
interior feature because it never looks for one.

Two corroborating measurements:

- `dry-erase-marker-head-cpl` flips verdict from **+236.7 (HALO)** to
  **−325.7 (clean)** purely by moving the reference annulus. A verdict that
  depends on the choice of a free parameter that is not part of the definition
  of the defect is not a verdict.
- Its own header states a halo "raises both" `overshoot` and `bump`. On **3 of
  its 4 targets the two statistics disagree in sign.** The instrument
  contradicts its own stated model.

`halo_profile.py`'s header already concedes that "a radial-profile detector
cannot see a rim close to a steep penumbra". That concession is correct, and
§3 measures exactly how far it extends. It is the honest part of an instrument
whose headline numbers are not.

**I also refuted one of its skips.** It dismissed `tweezers-cpl` for a
gap-crossing condition; `tweezers.py` (commission 2/2 PASS) shows the
dismissal does not hold and the subject is scorable. `tweezers-cpl` turned out
to be the single most merge-driven halo in the corpus, so the skip was not
harmless.

---

## 2. Ruling out the exposure confound — VERIFIED, not assumed

ORCH's warning was specific: a blown highlight next to a dark edge reads as
enormous overshoot and would manufacture this exact signature.

**Measured.** `clipaudit.py` over 139 masters plus the 26 faithful ones:
every faithful master clips **≤0.135%** of samples. None is blown. The four
HALO verdicts are not clipping artifacts.

Two instrument details from that audit, both of which changed a number:

- `enfuse` writes 4-channel RGBA with fully opaque alpha, which is exactly
  25.0000% of samples at 65535. Counting alpha as image data reports every
  enfuse output as 25% clipped. The fix was commissioned **in both
  directions**, so that "exclude alpha" could not have been silently
  implemented as "ignore 4-channel files".
- The `109MSDCF` pin median I measured independently, hours before ORCH's
  exposure broadcast and on a different errand, was **60918** — identical to
  the value ORCH later reported for the pin. That is independent corroboration
  of the pin/HEAD exposure diagnosis by a measurement that could not have been
  tuned to it.

---

## 3. `aura.py` — the replacement, and what it cost to get right

A halo is a **local radial excursion**: a bump or a dip with the background on
both sides of it, narrow, and near the subject. So the statistic is
prominence, not height:

```
prominence(v)[i] = min(max(v[:i]), max(v[i+1:])) - v[i]
```

This is immune to a monotone trend by construction, which is the property the
old instrument lacked. `deficit` is a dark ring, `surplus = deficit(-v)` a
bright one. Four gates decide the verdict, each with its provenance recorded
in the source: amplitude ≥ 200 DN (deliberately `halo_profile.py`'s own
threshold, so verdicts differ only by *what is measured*), width ≤ 120 px,
distance ≤ 200 px (the project's own documented "80–200 px aura zone" from
`stack --help`), and the feature must sit inside half the measured field.

**Commission: 8/8 PASS.** Plants 1–2 recover 3000 DN rings exactly; 3–4 are
negative controls (a bare penumbra and a 6000 DN monotone gradient must both
read 0.0, and do); 5 detects a ring on a steep penumbra; 6 separates a
true rim from the edge transition; 7 separates a ring from a lighting arch by
width, 36.2 px against 242.5 px, **stated as a ≥3× ratio so single-sided
tuning cannot fake it**; 8 fires the field-fraction guard only outside it.

**Measured sensitivity envelope, reported rather than claimed:**

| condition | result |
|---|---|
| flat ground | exact (3000 → 3000.0) |
| on an 18000 DN penumbra | 81% recovery; detection floor between 750 and 1500 DN |
| Gaussian ring σ=4 at d=60 | detected (268.6) |
| Gaussian ring σ≥12 at d=60 | **MISSED** |
| Gaussian ring σ=18–30 at d=150 | detected (1159.6 / 751.6) |

So `halo_profile.py`'s structural-limitation claim is **vindicated in a
narrower form than it stated it**: a ring gentler than the penumbra it sits on
shelves the profile instead of turning it over, and no dip detector escapes
that. This design does not either.

### Four defects I had to find in my own instrument first

Recorded because each one produced a *confident wrong answer*, not an error.

1. **Scale units.** `radial()` multiplied distance by `SUB=4` because `main`
   feeds it a 4× subsampled master, while `commission` feeds it a
   full-resolution synthetic. Every plant was looked for 4× further out than
   its label, fell off the end of the band table, and **read a clean 0.0** —
   an instrument reporting "no defect" for a defect it was pointed away from.
   Fixed by making `scale` an explicit parameter at all six call sites.
2. **Plant geometry must match partition geometry.** A top-hat ring at
   135–165 px straddled the 150 px band boundary, so no band median landed
   inside it and a 3000 DN plant read 0.0. Separately, a plant peaking in the
   *outermost* band is invisible to `prominence`, which has no outer shoulder
   there.
3. **Interpolate, don't snap.** Snapping half-prominence crossings to band
   midpoints gave the narrowest real feature a width of 0.0 px — identical to
   no feature at all.
4. **Don't tune a gate to make your own test pass.** Plant 7's arch measured
   242.5 px against an arbitrary 250 px gate. I re-derived both gates from the
   plants' *analytic* widths and made the load-bearing assertion a ratio.

### Three confounds found by looking at real profiles

Every one of these was found by printing the profile (`auradump.py`) and none
by reasoning about it. Reasoning failed three times out of three.

- **Edge-transition double-count.** `aura == rim` to 0.1 DN on 14 of 26
  subjects. `bee-1-cpl` rises monotonically 40281 → 58863 DN except a single
  813 DN dip at 14 px, and a one-band wiggle is *both* a valley and a peak of
  the same amplitude. Fixed with a 30 px minimum-distance zone split.
- **Lighting arch.** `flat-on-ruler-cpl` rises 37317 → 50604 DN from 5 to
  168 px and falls to 45024 by 255 px; `lavendar-cpl` rises 41972 → 51650 and
  falls to 46937. Both are single smooth arches spanning the entire field.
  `prominence` is immune to a monotone trend but not to an arch, which has a
  genuine interior maximum. Fixed by width.
- **Field truncation.** `112`/`113MSDCF` score the corpus's two largest rims
  (8680 / 8469 DN) at only 64 px width — but they peak at 90 px in a field
  reaching just 135 px. A prominence needs shoulders on both sides.

---

## 4. Baseline: what is actually there

`aura.py` scores **26 of 26** subjects. `halo_profile.py` scored 11.

**7 HALO, 7 gradient-only, 12 clean.**

| subject | aura DN | w px | @px | rim DN | w px | @px | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| tweezers-cpl | 2621.7 | 28 | 56 | 2621.7 | 22 | 36 | HALO pair |
| lead-1-cpl | 1848.4 | 68 | 56 | 1233.2 | 33 | 36 | HALO pair |
| leaf-2-cpl | 1766.9 | 62 | 56 | 1137.9 | 34 | 36 | HALO pair |
| 109MSDCF | 1260.3 | 6 | 36 | 69.4 | 68 | 135 | HALO dark |
| coffee-bean | 728.0 | 15 | 36 | 105.6 | 39 | 310 | HALO dark |
| dry-erase-marker-head-cpl | 20.2 | 44 | 310 | 694.9 | 78 | 135 | HALO bright |
| 119MSDCF | 305.3 | 6 | 36 | 503.1 | 108 | 71 | HALO pair |
| 112MSDCF | 0.0 | 0 | 36 | 8679.8 | 64 | 90 | gradient |
| 113MSDCF | 0.0 | 0 | 135 | 8468.9 | 65 | 90 | gradient |
| flat-on-ruler-cpl | 334.3 | 35 | 255 | 5579.3 | 172 | 168 | gradient |
| lavendar-cpl | 702.7 | 89 | 310 | 4713.3 | 124 | 110 | gradient |
| wrapped-text-2 | 0.0 | 0 | 310 | 1525.9 | 108 | 255 | gradient |
| pencil-flatter-angle-cpl | 0.0 | 0 | 56 | 464.8 | 48 | 310 | gradient |
| wrapped-text-1 | 91.1 | 44 | 310 | 284.9 | 44 | 255 | gradient |
| *12 clean* | | | | | | | bee-1/2/3-cpl, coffee-bubbles, couch-fibers-cpl, flower-bud-alone-cpl, flower-bud-with-background-fern-cpl, flower-inner-edge-cpl, flowers-cpl, foam, highly-angled-ruler-mm-cpl, pencil-steep-angle-cpl |

### Against ORCH's four

| ORCH verdict | mine | why |
|---|---|---|
| `flat-on-ruler-cpl` +4481.8 HALO | **REFUTED** | 172 px-wide lighting arch spanning the field |
| `tweezers-cpl` bump 1542.3 HALO | **CONFIRMED** | 22 px bright peak at 36 px, 28 px dark trough at 56 px |
| `lavendar-cpl` +527.3 HALO | **REFUTED** | 124 px-wide arch |
| `dry-erase-marker-head-cpl` +236.7 HALO | **CONFIRMED** | 78 px bright rim at 135 px |

Five halos `halo_profile.py` never flagged: `lead-1-cpl`, `leaf-2-cpl`,
`109MSDCF`, `coffee-bean`, `119MSDCF`.

Note the direction of the error: the instrument's **loudest** verdict
(`flat-on-ruler-cpl`, +4481.8 DN, "the one that matters most") is a lighting
gradient, and it was silent on the subject that turned out to be the most
merge-driven halo in the corpus.

### One defect or two?

**Two shapes, one of which has two causes.** The three loudest — `tweezers`,
`lead-1`, `leaf-2` — share one signature: a bright peak at 36 px immediately
followed by a dark trough at 56 px. An overshoot/undershoot **pair**. This is
also why `aura == rim` on so many subjects and why that equality is a
*signature rather than a bug*: for an adjacent peak/trough pair whose outer
shoulders are more extreme, both statistics compute the same peak-to-trough
difference.

The gradient class is a different thing entirely and is not a rim at all.

---

## 5. Two hypotheses killed by clean nulls

### The hull is not the mechanism

`pyramid.rs`'s own doc records hull violations of 0 / 72 / 511 pixels at
exponents 1 / 8 / 16 — the merge emits values outside the range of every input
frame. That is a plausible ringing source, so I made the clamp switchable
(`STREHL_HULL`, `input-range` | `per-level` | `unclamped`) and commissioned it
behaviourally, **5/5 PASS**: the renderer is byte-deterministic run to run;
unset is byte-identical to `input-range`; the other two are each distinct; a
bogus value aborts rc=101. The determinism arm is what makes the other four
interpretable.

**Result, `109MSDCF`:**

| hull | aura DN |
|---|---:|
| `input-range` (shipping) | 1260.3 |
| `per-level` | 1263.3 |
| `unclamped` | 1298.8 |

Hull clamping accounts for ~38 DN of a 1260 DN aura. **It cannot be the
mechanism for a thousands-of-DN halo.** Clean null.

### Alignment drift is not the mechanism

Refuted separately in the V-DRIFT lane (`ca8818bf`).

---

## 6. The knob sweep, and the trap arm that proves it was needed

Every knob in this sweep moves the merge along one axis: how hard it selects.
An average has no halo because it has no structure, so a sweep scored on the
halo alone ranks the blurriest arm first. **Every arm therefore carries
sharpness on the same pixels** (`sharp.py`, commission 3/3 including a planted
*improvement*, not only a planted defect) **and black level** — because
`stack --help` warns a shallow pyramid trades "grey ink instead of black",
which is a low-frequency failure a high-pass statistic is blind to by
construction. Textured sites and the subject mask are fixed once from the
baseline arm and reused for every arm, so a softer arm cannot move its own
measurement window.

**`tweezers-cpl`, 100 frames, shipping merge vs each knob:**

| arm | halo DN | Δ halo | Δ sharp | Δ black DN |
|---|---:|---:|---:|---:|
| **plainmean** *(reference, not a candidate)* | **654.9** | **−75.0%** | **−81.4%** | −722.0 |
| bands5 | 1577.2 | −39.8% | +0.2% | −143.3 |
| baseweighted | 1860.5 | −29.0% | +0.2% | −12.8 |
| exp1 | 2060.0 | −21.4% | −0.2% | −248.4 |
| sharpen1 | 2315.8 | −11.7% | **−18.0%** | −650.6 |
| hullperlevel | 2548.4 | −2.8% | +0.0% | +148.0 |
| gate8 | 2572.2 | −1.9% | +0.5% | +122.1 |
| **baseline (7 bands)** | **2621.7** | — | — | — |
| bands9 | 2841.7 | +8.4% | −0.2% | +76.7 |
| exp4 | 2978.8 | +13.6% | −0.3% | +158.7 |

**The plain-mean arm independently reproduces ORCH's warning.** ORCH: "on
blotch alone the worst arm wins — a plain mean scored best and destroyed 78%
of the sharpness." Measured here on a different subject with a different
statistic: **−75.0% halo for −81.4% sharpness.** Without the counterweight
this sweep would have ranked it first with total confidence.

Response is **monotone in band count** (5 < 7 < 9) and **monotone in
exponent** (1 < 2 < 4), and the halo sits at 36–56 px — a coarse pyramid band.
That is consistent with **coarse-band selection ringing**, and it corroborates
ORCH's separate finding that the plateau sits in the 20–60 px band.

### The generalisation test, which weakened the headline

**`lead-1-cpl`, 123 frames**, same nine arms: `bands5` gives **−8.7%**, not
−39.8%, at **+266.7 DN of black density** — blacks going *grey*, the opposite
sign to tweezers. `gate8` destroys **85.4%** of sharpness here having cost
+0.5% on tweezers.

**The knob response is strongly subject-dependent. A number from one subject
is not a corpus result.**

---

## 7. The decisive measurement: how much of a "halo" is even the merge?

`--pyramid-exponent 0.001 --pyramid-sharpen 1.0` makes every band's selection
weight `excess^0.001`, which is ≈1 for any frame above the gate: a plain
average, with the **same frames, same alignment, same tone pipeline** as every
other arm. Whatever radial structure survives that is **not selection
ringing**, because there is no selection.

This is the arm that says how much of a measured halo any selection change
could even in principle remove.

| subject | total DN | no-selection floor | merge excess | floor % | bands5 Δ merge |
|---|---:|---:|---:|---:|---:|
| **tweezers-cpl** | 2621.7 | 654.8 | **1966.9** | **25.0%** | **−53.1%** |
| 112MSDCF | 8679.9 | 7819.4 | 860.5 | 90.1% | −18.6% |
| 119MSDCF | 503.0 | 447.8 | 55.2 | 89.0% | −14.9% |
| 109MSDCF | 1260.4 | 1109.0 | 151.4 | 88.0% | −20.3% |
| dry-erase-marker-head-cpl | 695.0 | 584.5 | 110.5 | 84.1% | **−573.8%** |
| bee-1-cpl | 46.0 | *withheld* | — | — | — |
| coffee-bean | 728.0 | *withheld* | — | — | — |
| flat-on-ruler-cpl | 5579.3 | *withheld* | — | — | — |
| leaf-2-cpl | 1766.9 | *withheld* | — | — | — |

Floor median **88.0%** (n=5); merge-excess change median **−20.3%**.

**On four of five scorable subjects, 84–90% of the measured halo survives with
selection completely removed.** Only `tweezers-cpl` is majority-merge, at 25%.

### The model refuted itself, and that is the most useful thing in this section

`dry-erase-marker-head-cpl` reads **−573.8%**, which is not a large
improvement — it is an impossibility. The fix arm scored **61.0 DN**, *below*
the no-selection floor of **584.5 DN**. If the floor were a floor, no
selection setting could go under it.

I chased that rather than rounding it off, and it is real. Printing the radial
profiles of all three arms on **one shared mask** (`armprofile.py`; the
baseline's mask, which is also what `abscore.py` uses) shows:

```
  d px      baseline   plainmean      bands5     d bands5
     71      39919.7     37609.9     38697.4      -1222.4
    135      41316.0     40786.7     40350.2       -965.8
    310      40621.0     40262.4     40501.3       -119.8
```

The baseline background rises to a maximum at 135 px and then declines 695 DN
to 310 px — that decline *is* the "695 DN HALO". `bands5` darkens 135 px by
966 DN more than it darkens 310 px, which turns the local maximum into a
monotone rise, so the prominence clamps to zero.

**Nothing was removed from a ring. The background was tilted until an existing
decline stopped being a local maximum.** The additive model
`total = floor + merge excess` is therefore wrong in general: the plain-mean
arm bounds what *selection* knobs can do, but `--pyramid-bands` is not a
selection knob — it moves the pyramid's base band from 1/128 to 1/32 of full
scale and so re-renders the background's low frequencies by construction.

I have left the −573.8% in the table rather than deleting the row, because a
number that falsifies the model it appears in is evidence, and hiding it would
leave the model looking unopposed.

**Naming discipline.** The floor arm removes per-pixel selection and *nothing
else*, so what survives is everything that is not selection — veiling glare
around a dark subject, the lighting field, and any residual misregistration.
It is **not** evidence that the scene alone causes the structure, only that
the merge's selection does not. I have called it the *no-selection floor* for
that reason and avoided the word "scene" in the statistic's name.

Four subjects are **withheld rather than reported**: the no-selection arm also
moved their black level by more than 1000 DN (`bee-1-cpl` +1839,
`coffee-bean` +1490, `flat-on-ruler-cpl` +4173, `leaf-2-cpl` +4207), so it is
not the same picture at a different selection and its profile is not a floor.
The guard lives in `decompose.py`, not in prose, because a caveat that lives
only in prose gets dropped when the table is copied.

Two of those withheld rows are the most dramatic in the run — `leaf-2-cpl`
−100.0% and `coffee-bean` −95.8% — and I want to be explicit that withholding
them **costs me my best evidence for the merge hypothesis**, not my worst. A
tone shift of +4207 DN is 6.4% of full scale and could mechanically shrink a
prominence by roughly that much; it cannot mechanically produce −100%. So
those two subjects are probably genuinely merge-driven and the guard is being
conservative against my own case. I would rather report a defensible n=5 than
an n=9 I would have to defend.

**One direction-of-bias check.** The floor arm is much blurrier (−45% to −81%
sharpness). Blur would tend to *reduce* a narrow ring, so a floor measured
this way is if anything an **under**-estimate, and the ~89% figure is
conservative rather than flattering.

---

## 8. The verdict on the candidate fix

The complete A/B, 12 subjects, `baseline` vs `--pyramid-bands 5`, both arms
rendered by **the same binary** so the flag is not confounded with commit
drift:

| statistic | median | range |
|---|---:|---|
| raw halo | **−5.5%** | −100.0% .. **+8.8%** |
| sharpness | +0.04% | −2.87% .. +3.61% |
| black level | +113.7 DN | −143.3 .. **+1412.3 DN** |

### The shape test, which removed the best number in the table

`bands5`'s largest apparent win was `dry-erase-marker-head-cpl` at **−91.2%**,
and §7 showed that it is a background tilt rather than a ring removal. That
raised an obvious question about every other row: **how many of these are
tilts too?**

A prominence cannot answer it, because a tilt and a ring removal both lower a
prominence. The width of the *difference* profile can. `armprofile.py`
measures each arm's difference from baseline the same way `aura.py` measures
an image's own profile — extremum, prominence, full width at half prominence —
and classifies it `local` (≤80 px, a few adjacent annuli, so a ring really
changed) or `broad` (the background was tilted).

Commissioned 5/5 on four plants, including two shapes of tilt and a flat-offset
null, with **6.9×** separation between the narrow and broad plants. The first
run **failed**, correctly: my "broad tilt" plant had a `0.3` multiplier on the
inner bands, which put a cliff at 36 px and made it measure 66.8 px FWHM. The
plant was not the thing it claimed to be. Rebuilt from the shape actually
observed on `dry-erase`.

| subject | Δ peak DN | at px | FWHM px | shape | far-field Δ DN |
|---|---:|---:|---:|---|---:|
| **tweezers-cpl** | −984.1 | 36 | **31.7** | **local** | −305.5 |
| leaf-2-cpl | −218.5 | 29 | 22.1 | local | **+676.7** |
| lead-1-cpl | −174.1 | 10 | 12.3 | local | **+720.5** |
| flat-on-ruler-cpl | −139.4 | 29 | 46.1 | local | +257.0 |
| 119MSDCF | −112.8 | 14 | 18.1 | local | +3.4 |
| 109MSDCF | −104.6 | 14 | 15.0 | local | +13.5 |
| 112MSDCF | −124.1 | 29 | 79.2 | local | — |
| **dry-erase-marker-head-cpl** | −1139.9 | 71 | **152.7** | **broad** | −119.8 |
| **bee-1-cpl** | **−1613.5** | 71 | **107.6** | **broad** | −320.6 |
| coffee-bean | −371.4 | 56 | 92.8 | **broad** | +392.0 |

**`tweezers-cpl` is the only subject in the corpus where `bands5` performs a
clean, localised ring removal** — −984 DN concentrated at 36 px, collapsing to
−15 DN one annulus away at 56 px, with a modest far field. Everywhere else it
either tilts the background broadly or shifts the far field by 250–720 DN.

### Not recommended as a default. Four reasons, all measured

1. **The raw corpus median is −5.5%**, and once the tilt rows are set aside
   the only genuine ring removal is on one subject out of twelve.
2. **It fails ORCH's own acceptance condition on the showcase subject.** On
   `bee-1-cpl` it lifts black level **+1412.3 DN**, costs **−2.87%**
   sharpness, and darkens the near background by **−1613.5 DN** across a
   broad 107 px band. It does not put a rim on `bee-1-cpl`, but it visibly
   re-renders it, and that was the named acceptance criterion.
3. **It makes a subject worse.** `coffee-bean` halo **+8.8%**.
4. **Its tone cost flips sign between subjects** — +266.7 DN of black density
   on `lead-1-cpl` (the "grey ink instead of black" the CLI warns about) while
   *gaining* 143 DN on `tweezers-cpl`. Sharpness spans −2.87% to +3.61%
   against a metric resolution of ≈±0.2%.

The consistency check that makes me believe the table rather than the
headline: the two subjects whose halo `bands5` barely moves (`112MSDCF`
−1.8%, `flat-on-ruler-cpl` −0.2%) are **exactly the two I had independently
classified as lighting gradient before running any sweep**. A selection knob
cannot move a lighting arch, and it did not.

---

## 9. What this means for the assignment

1. **"Four subjects halo" was an instrument artifact in half its cases.** Two
   of four are lighting arches; the instrument could score 11 of 26 subjects
   and was blind to five real halos, including the corpus's most merge-driven
   one.
2. **The mechanism is real but minority.** Coarse-band selection ringing is
   confirmed — monotone in band count, monotone in exponent, sitting in a
   coarse band, and removable by removing selection. But on four of five
   scorable subjects **84–90% of what the halo statistic reports survives
   with selection completely switched off**, so it is not what a selection
   knob can reach.
3. **The cheap knobs are not a corpus fix, and the one that looked best was
   not doing what it appeared to.** `--pyramid-bands 5` scored −91.2% on
   `dry-erase-marker-head-cpl` by tilting the background, not by removing a
   ring. Across twelve subjects it performs a genuine localised ring removal
   on **one**, makes one worse, and re-renders the showcase subject.
4. **The largest remaining term is not the merge**, and if the owner's
   complaint is about the biggest numbers in this corpus (`112`/`113MSDCF` at
   ~8600 DN, `flat-on-ruler-cpl` at 5579 DN) then it is a **capture and
   lighting** problem, not a merge problem, and no amount of work in
   `pyramid.rs` will address it.

**The honest answer to "then fix it" is that on this corpus there is much less
merge-caused halo to fix than the instrument reported, and I would rather say
that than ship a default change that buys 5.5% on the median, one real
subject, and a re-rendered `bee-1-cpl`.**

### The methodological point, which outlives this corpus

Three of the four numbers I was ready to report as results did not survive
being checked against a printed profile:

| I was going to report | what it actually was |
|---|---|
| four subjects halo | two are lighting arches |
| `dry-erase` −91.2% halo fix | a background tilt |
| `total = floor + merge excess` | falsified by its own −573.8% row |

Each was caught by the same move: **stop reasoning about the shape of a
profile and print it.** On this task reasoning about profile shapes has been
wrong every time it was checked and printing them has been right every time.
That is now four for four, and it is the only technique in this document I
would carry unchanged to a different problem.

---

## 10. VERIFIED vs ASSUMED

**VERIFIED** — a command was run and its output read:

- The 7/4/15/26 partition from `halo_profile.py`, reproduced exactly.
- argmax in the outermost band on 11/11 scorable subjects.
- `dry-erase-marker-head-cpl` verdict flip under a reference-annulus change.
- ≤0.135% clipping on all 26 faithful masters and 139 masters overall.
- `aura.py` 8/8, `sharp.py` 3/3, `annulus.py` 5/5, `abscore.py` 4/4,
  `armprofile.py` 5/5, `hullcommission.ps1` 5/5, `tweezers.py` 2/2,
  `noiseaudit.py` 8/8 grain estimator + 7/7 verdict rule.
- Renderer byte-determinism run to run.
- Every number in every table above.

## 12. The sharpness column, priced against grain

ORCH's rule: no sharpness claim without naming the band and the subject's
qualification at it. And its warning: raw band power counts noise as
sharpness — one lane read +0.142 sharper raw and −0.134 softer corrected, a
sign flip. I told ORCH my sharpness column was untrustworthy under that
warning. **I then measured it, and that self-flag was right in one place,
wrong in another, and I could not have known which by reasoning.**

**Naming the band.** `sharp.py` has no band. It is the median of |Laplacian|
over the most textured decile — a spatial-domain operator, not a band power.
The two accumulate noise differently: a band power is a sum of squares and
rises with grain by construction, while a median over the highest-signal
sites moves only if grain becomes comparable to signal *there*. What can be
named is the operator's weighting: the discrete Laplacian's gain rises
monotonically to Nyquist (|H| = 2.618 at 0.30 cyc/px, 4.000 at 0.50), so it
weights most heavily exactly the frequencies most likely to be grain.

**Method** (`noiseaudit.py`). Measure each arm's grain, inject white noise
into the quieter arm by binary search until its grain *matches* the noisier
one, re-measure sharpness on identical sites. The resulting change is the
part of the observed gap grain can account for. The verdict rule asks
whether grain could have *manufactured* the effect — which requires it to
push the same direction — rather than comparing magnitudes, because the sign
is the whole question.

**`bands5` vs baseline — grain OPPOSES my conclusion, so it stands:**

| subject | N | qual @0.30–0.40 | grain base | grain bands5 | Δ obs | Δ grain | Δ corrected |
|---|---:|---|---:|---:|---:|---:|---:|
| `bee-1-cpl` | 299 | PASS (R=4.732) | 249.00 | 267.31 | −2.868% | +0.529% | **−3.397%** |
| `dry-erase-marker-head-cpl` | 300 | PASS (R=4.877) | 158.68 | 169.76 | −1.593% | +0.813% | **−2.406%** |

`bands5` is the *noisier* arm and reads *softer*. Grain would inflate it, so
it cannot be manufacturing the loss; correcting makes `bands5` look **worse**.
My rejection of `bands5` strengthens.

**The no-selection floor — here the confound runs my way, and it bites:**

| subject | qual | grain base | grain mean | Δ obs | Δ grain | Δ corrected | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `bee-1-cpl` | PASS | 249.00 | 154.43 | −83.746% | −14.845% | **−68.901%** | CLEAN |
| `dry-erase-marker-head-cpl` | PASS | 158.68 | 94.21 | −82.406% | −13.194% | **−69.212%** | CLEAN |
| `tweezers-cpl` | **UNLICENSED** | 99.35 | 86.78 | −81.369% | −0.666% | **−80.702%** | CLEAN |
| `coffee-bean` | **UNLICENSED** | 143.59 | 76.49 | −82.657% | −4.923% | **−77.734%** | CLEAN |
| `leaf-2-cpl` | **UNLICENSED** | 597.45 | 554.63 | −0.953% | −1.924% | **+0.971%** | **CONFOUNDED** |

A plain mean of N frames is ~√N quieter, so *quieter and softer* is the
confoundable direction. Three consequences:

1. **My headline −81.4% was inflated.** On the two deep qualified subjects
   the true loss is **−68.9%/−69.2%**, ~14 points less. The −81.4% I quoted
   for `tweezers-cpl` survives almost intact (−80.7%) because that subject is
   quiet, which is luck, not method.
2. **`leaf-2-cpl` sign-flips**: −0.953% observed becomes **+0.971%**
   corrected. That is ORCH's warned failure occurring in my own data, on the
   noisiest subject in the set (grain 597 DN). No conclusion of mine rests on
   it — `leaf-2-cpl`'s load-bearing number is its **−100.0% halo** — but it
   is the proof that the correction is not cosmetic.
3. **The corrected range −68.9%…−80.7% brackets ORCH's independently measured
   −78%** for a true plain mean, which is better corroboration for the
   "exponent 0.001 ≈ plain mean" assumption below than the raw −81.4% was.

**Unlicensed, stated rather than hidden.** `tweezers-cpl`, `lead-1-cpl`,
`coffee-bean` and `leaf-2-cpl` are not in V-LINEAR's qualification table, so
under ORCH's rule their sharpness numbers are unlicensed as stated. The grain
confound is priced above without knowing the band; the band itself is not
measured and this lane does not claim it.

**ASSUMED** — reasoned, not measured:

- That `--pyramid-exponent 0.001 --pyramid-sharpen 1.0` is *exactly* a plain
  mean. It is a weight of `excess^0.001`, which is ≈1 but not 1, and a frame
  with exactly zero excess still gets weight 0. Corroborated indirectly: its
  grain-corrected loss of −68.9%…−80.7% (§12) brackets ORCH's independently
  measured −78% for a true plain mean.
- That the no-selection floor contains no pyramid reconstruction artifact.
  Uniform weights should reconstruct near-exactly; I did not measure it.
- That `bands5`'s behaviour on the twelve A/B subjects extrapolates to the 14
  faithful-corpus subjects not rendered in that sweep.

**NOT MEASURED**, and I am flagging rather than hiding them:

- `109MSDCF` and `119MSDCF` read aura widths of **6 px** — single-band spikes
  that may be band-median noise rather than real rings. Their merge-excess
  percentages (−20.3%, −14.9%) rest on differences of ~30 DN and should be
  treated as the weakest rows in the decomposition table.
- The `LOCAL_PX = 80` gate in `armprofile.py` separates the two commissioning
  plants by 6.9× and the real subjects by 4.8× (`tweezers` 31.7 px vs
  `dry-erase` 152.7 px), but the broad *plant* lands at 88.9 px — only 11%
  clear of the gate. The gate is placed from annulus geometry rather than
  tuned to a subject, and the real separation is comfortable, but a subject
  landing at 70–95 px FWHM should not be classified from this number alone.
  `112MSDCF` (79.2 px) is exactly such a case and I have not called it either
  way.
- No visual confirmation. Every number here is a statistic; I cut no crops and
  the owner's complaint is visual. A lane that owns quality should look.

---

## 13. After V-REVIEW's adjudication: what my instrument can and cannot see

V-REVIEW adjudicated all four of ORCH's HALO verdicts as false positives, on
the mechanism that `halo_profile.py` walks 2–120 px and then takes its far
field at 400–900 px, **never measuring 120–400 px**.

**I agree, and two of the four I had already refuted independently.** §1
called `flat-on-ruler-cpl` a 172 px arch and `lavendar-cpl` a 124 px arch
before that adjudication existed. The reason is structural rather than lucky:
`aura.py`'s `EDGES` run **2 → 420 px continuously** (…100, 120, 150, 185, 230,
280, 340, 420), so it samples the exact interval the other instrument skips,
and an arch peaking at 168 px is visible as an arch.

### Detection floors, measured by planting rims into a real master

`plantrim.py`, on `tweezers-cpl` baseline. Every plant is verified to have
moved the image's own radial profile by ≥50% of its nominal amplitude at the
planted radius before its detection result counts — an instrument that is
blind and a plant that never landed produce the same clean reading.

| rim shape | span | `aura.py` floor | `halo_profile.py` |
|---|---:|---|---|
| narrow (σ 12 px @ 30 px) | ~72 px | **250 DN** | 4500 DN |
| wide (σ 60 px @ 120 px) | ~360 px | **not detected ≤9000 DN** | — |
| broad (σ 150 px @ 120 px) | ~900 px | **not detected ≤9000 DN** | missed at 9000 DN |

**On a narrow rim this instrument is ~18× more sensitive**, detects at every
amplitude, localises to 36 px, and its rise tracks the landed amplitude
(+209 DN for 217 landed; +7245 for 7751). **On a broad rim it is exactly as
blind as the instrument it replaced.**

### The finding that matters more than the floor

A broad rim does not merely go undetected — **it actively suppresses a real
narrow rim that is present.** As broad amplitude rises, the measured rim
*falls*:

| broad plant | measured rim at 36 px |
|---:|---:|
| 0 DN (baseline) | 2621.7 DN |
| 2000 DN | 2153.2 DN |
| 4500 DN | **1556.7 DN (−41%)** |
| 9000 DN | 1990.9 DN |

`prominence` measures a feature against its two shoulders; a broad rim lifts
the outer shoulder, so the real narrow feature reads smaller. Since most
studio shots carry a scene gradient, **this instrument under-reports real
narrow halos on exactly the subjects most likely to have one.** ORCH placed
residual risk on 11 subjects; on this evidence that risk is not merely
unmeasured there, it is *biased downward*.

### Does the clamp justify itself? No.

`aura.py` across the four hull arms on the same real render (109MSDCF,
`stack --srgb`):

| arm | rim DN @135 px | aura DN @36 px |
|---|---:|---:|
| unset | 69.4 | 1260.3 |
| `input-range` | 69.4 | 1260.3 |
| `per-level` | 69.5 | 1263.3 |
| `unclamped` | 70.6 | 1298.8 |

**Rim spread across all hull modes: 1.2 DN.** Turning the clamp entirely off
moves the rim by 1.7%. Whatever `Hull::InputRange` does, it is not halo
suppression on this subject — so **no halo justification for `STREHL_HULL`
survives**, independently of whether any halo exists. It stays opt-in.

### `STREHL_HULL` is pixel-inert when unset — measured across the commit

Commission arm B proved *unset == explicit `input-range`*, which shows the
routing is self-consistent but **not** that the default was preserved across
the commit. `inertness.ps1` answers the actual question: build both commits in
detached worktrees (the shared tree is never checked out) and render with the
variable unset. `pyramid.rs` is the only compiled file that differs.

**0 of 98,898,048 samples differ.**

**And the first version of that check read FAIL.** It compared SHA-256 of the
TIFFs, which differ at byte offset 3375 because the writer stamps the git hash
(`649e35620f02` vs `6341a7a4b7e9`) into the header. A file hash was the wrong
instrument: it would have had me report a regression in every re-rendered
master that does not exist. Same family as ORCH's own note about clearing an
`--exposure` defect on a file hash when 0 of 98,898,048 samples actually
differed — the identical count, because it is the identical corpus.

---

## 11. Files

| path | what | commission |
|---|---|---|
| `experiments/V-SPEED/aura.py` | the replacement halo detector | 8/8 |
| `experiments/V-SPEED/sharp.py` | sharpness counterweight, textured sites | 3/3 |
| `experiments/V-SPEED/annulus.py` | removed-vs-scattered discriminator, radial profiles | 5/5 |
| `experiments/V-SPEED/abscore.py` | corpus A/B, fixed-window statistic | 4/4 |
| `experiments/V-SPEED/armprofile.py` | prints arm profiles on one shared mask; local-vs-broad shape test | 5/5 |
| `experiments/V-SPEED/decompose.py` | halo = no-selection floor + merge excess (**model refuted in §7**) | — (joins two scored runs) |
| `experiments/V-SPEED/auradump.py` | prints band medians; found all three confounds | — |
| `experiments/V-SPEED/halodiag.py` | convicts `halo_profile.py`'s `overshoot` | — |
| `experiments/V-SPEED/tweezers.py` | refutes the gap-crossing skip | 2/2 |
| `experiments/V-SPEED/sweep.ps1` | render harness: `knobs`, `depth`, `ab`, `scene` | — |
| `experiments/V-SPEED/ab.ps1` | corpus driver, cheapest subject first | — |
| `experiments/V-SPEED/hullcommission.ps1` | behavioural commission of `STREHL_HULL` | 5/5 |
| `crates/strehl-core/src/pyramid.rs` | `STREHL_HULL` env var + `hull_default()` | 5/5 |

`STREHL_HULL` is left in the tree deliberately: it is default-off, byte-identical
to the shipping behaviour when unset, and it is the arm that produced the clean
null in §5. A default chosen by measurement needs the arm it beat to remain
runnable — the same argument `pyramid.rs` already makes for keeping
`--pyramid-base weighted`.
