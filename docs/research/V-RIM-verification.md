# V-RIM — independent verification of ORCH-veiling section 12

Status: MEASURED. Author: V-RIM (independent verifier). Subject: section 12 of
`docs/research/ORCH-veiling.md` at commit `eff23fb`, written by the
orchestrator. Binary: pinned `1cacb61`, sha256 `AAB9E331…86FC5`. All
measurements on **linear** renders (`--demosaic`, no `--srgb`), full
resolution, green channel. Raw artifacts `C:\dev\strehl-out\V-RIM\`,
instruments `experiments/V-RIM/src/`, classification frozen in
`experiments/V-RIM/preregistration.md` before any number was read.

No number below was produced by `rimprofile.py`. Every instrument here was
written for this verification with deliberately different choices of
segmentation, binning, reference and detector, so that agreement means
agreement and disagreement is informative.

## Verdict

| claim | verdict |
| --- | --- |
| **C1** — the darkening is an optical veiling term, evidenced by −38.2% and −36.5% agreeing within 1.7 points | **REFUTED as stated** |
| **C2** — the bright ring appears only where the silhouette carries a fine fringe | **REFUTED** |

What survives, and is worth keeping: **fringe amplifies the ring, it does not
cause it.** Within a single subject, with scene, exposure, magnification and
frame count held exactly constant, the most-fringed quartile of the silhouette
shows the larger ring in **8 of 9** subjects. And C2's *mechanism* — that the
merge emits the ring — is **confirmed**, by a control ORCH did not run.

One finding is unambiguously positive and should be recorded. **The pipeline is
bit-reproducible.** Rendering both anchors from the library with the pinned
binary produced files byte-identical to ORCH's:

| render | sha256 | bytes |
| --- | --- | --- |
| `coffee-bean` | `BD7B07BB…C397A0` | 197798267 |
| `flower-bud-alone-cpl` | `E52FADCE…15F2CE` | 198023291 |

ORCH's provenance claim is confirmed exactly. The disagreements below are about
interpretation, never about which pixels were measured.

## C1 — the agreement is a property of the instrument

### The reported quantity is pinned by the threshold

ORCH's mask boundary is the contour where luminance crosses `0.5*(p5+p95)` — a
half-contrast threshold. The 0–4 px bin therefore sits, by construction, just
outside a contour placed half way between subject and backdrop, so its value is
forced toward

    darkening as a fraction of far field  ≈  −0.5 * (1 − inner / far)

for any image at all, with no optics involved. Measured on the nine
like-polarity subjects in the library:

| subject | class | −38.2% statistic | pinned prediction | as % of contrast |
| --- | --- | --- | --- | --- |
| `coffee-bean` | SMOOTH | −38.78 | −42.09 | −46.06 |
| `119MSDCF` | SMOOTH | −37.07 | −40.96 | −45.25 |
| `bee-3-cpl` | FRINGED | −35.36 | −42.37 | −41.73 |
| `109MSDCF` | SMOOTH | −35.32 | −39.71 | −44.47 |
| `flower-bud-alone-cpl` | FRINGED | −35.20 | −39.24 | −44.85 |
| `flower-bud-with-background-fern-cpl` | FRINGED | −32.54 | −38.68 | −42.07 |
| `bee-2-cpl` | FRINGED | −31.77 | −38.83 | −40.92 |
| `lavendar-cpl` | FRINGED | −25.13 | −26.52 | −47.37 |
| `bee-1-cpl` | FRINGED | −21.90 | −24.57 | −44.56 |
| **spread** | | **16.88 points** | | **6.46 points** |

Two subjects agreeing to 1.7 points is what drawing two samples from a
**16.9-point** spread looks like. It is not evidence about a lens.

This cuts *against* the suspicion in the brief. Contrast normalisation is
arguably the more physical choice and it agrees **better**, not worse. ORCH did
not pick the flattering normalisation; ORCH picked a slightly worse one. The
defect is not cherry-picking — it is that **no normalisation of this quantity
is informative**, because the quantity is set by where the threshold was put.

### The agreement is smaller than the instrument's own free parameters

| perturbation, `coffee-bean` | darkening | swing |
| --- | --- | --- |
| as reported, far field from the 600–1400 px band (57686 DN) | −42.79% | — |
| far field from the outer 20% of available distance instead (60887 DN) | −40.54% | **2.25 points** |
| mask grown by 10 px | −29.35% | **13.44 points** |

Merely choosing a different, equally defensible far-field band moves the number
by **more than the 1.7-point agreement C1 rests on**. Moving the mask by 10 px,
on a feature about 250 px wide, moves it by eight times that agreement.

### Where the veil actually lives, the merge makes it

`coffee-bean` was re-rendered from single frames of its own bracket with
`STREHL_ONLY_FRAME` and profiled by the identical registered-ray method, each
image segmented and registered on its own terms so neither inherits the other's
geometry. Masks agree at IoU 0.95–0.99 with zero best shift, so the arms share
a geometry.

| image | 10–90 edge width | ring in t ≤ 140 px | backdrop at t = 50 px |
| --- | --- | --- | --- |
| merged output | **120.6 px** | **+7.13%** at t = 34 px | **−13.6%** |
| frame 52, silhouette in focus | **27.9 px** | **+0.00%**, monotone | **−0.7%** |
| frame 10 | too defocused to resolve 34 px | none | — |
| frame 30 | backdrop clipped at 65535, unusable | — | — |
| frame 95 | 82.2 px | none | — |

Frame 52 is the frame in which the silhouette is genuinely in focus: its edge
is **four times sharper than the merged output's**. It shows a clean monotone
step onto a flat backdrop, with no veil and no ring. The merge, built from that
frame among others, has both.

An optical veiling term belongs to the scene and the lens. It would appear in
every frame, most clearly in the sharp one. It is absent from the sharp one.
**Therefore it is not optical.**

The edge widths are the sharper indictment. The merged silhouette is four times
softer than the single best frame of its own bracket, which is the same
"estimator losing to its own inputs" failure this document's Summary already
reports at −4293 DN on `flower-bud`. Section 12's C1 and the document's opening
paragraph disagree about the origin of the same band.

Picture: `pics/merge-vs-frame52.png`.

## C2 — `coffee-bean` has a ring

ORCH reports `coffee-bean`'s only interior peak as 0.23% at 450 px, calls it
far-field wobble, and offers the subject as a free negative control. Measured
with rays registered individually on their own 50% edge crossing, which removes
mask placement, azimuthal mixing and curvature weighting together:

| ray set | anchored on | rays | ring | that subject's own null |
| --- | --- | --- | --- | --- |
| straightest quartile | V-RIM mask | 2030 | **+7.13% at t = 34 px** | 0.59% |
| straightest quartile | **ORCH's own mask** | 2480 | **+6.67% at t = 32 px** | 0.32% |
| all rays | V-RIM mask | 2971 | +6.90% at t = 34 px | — |
| all rays | ORCH's own mask | 1056 | +6.74% at t = 32 px | 2.82% |

The ring survives when the rays are anchored on **ORCH's own mask**, so it is
not an artifact of my segmentation. It is twelve to twenty times the subject's
own noise floor, it is at 34 px rather than 450 px, and it sits on the
**straightest quarter** of the silhouette — the part with no fringe at all. It
is visible to the eye in linear data with no tone curve.

### The predicted separation does not appear

C2's evidence is 12.0% against 0.23%, "52x apart". On the straightest quartile
of each subject, which is the like-for-like comparison:

- `coffee-bean` (smooth): **+7.13%**
- `flower-bud-alone-cpl` (fringed): **+3.18%**

The smooth subject's ring is the **larger** of the two. The ordering C2 predicts
is reversed.

### Why ORCH's instrument missed it

Not the bin width alone. Rebinning **my own** ray-registered `coffee-bean`
profile onto ORCH's exact bin edges still leaves a ring of **+5.54% at 35 px**.
The larger error is the annulus method itself: the merged silhouette is 120.6 px
wide from 10% to 90%, so "the silhouette" is not a well-defined location,
mask-derived zero points scatter by tens of pixels around the perimeter, and
averaging over an annulus smears a 34 px feature away. Registering each ray on
its own crossing recovers it.

## Part 3 — the pre-registered n=26 test

The classification was written and committed (`2f658a0`) **before any
measurement**, with an inclusion rule stated in advance. 26 subjects: 14
MEASURABLE (7 FRINGED, 7 SMOOTH), 12 EXCLUDED (8 dense filament fill, 3 planar,
1 no dominant subject).

Two further rules were applied before any ring number was read:

- **R1 polarity.** C1 and C2 are claims about the backdrop outward from a
  subject *darker* than its backdrop. Four subjects are the opposite geometry,
  where the outward profile falls and the dip statistic would score the edge
  transition itself. They are excluded and reported separately.
- **R2 every subject lands in a counted outcome.** A subject whose rays fail to
  register is NOT MEASURED, which is not the same as no ring.

| outcome over the 14 MEASURABLE subjects | n |
| --- | --- |
| ring detected | 5 |
| backdrop too noisy to decide | 4 |
| excluded by R1 polarity | 4 |
| not measured, rays did not register (`tweezers-cpl`) | 1 |
| **total** | **14** |

### The correlation C2 predicts

Across the nine like-polarity subjects, straight-quartile ring:

| class | n | mean | max |
| --- | --- | --- | --- |
| SMOOTH | 3 | +3.02% | **+7.13%** (`coffee-bean`) |
| FRINGED | 6 | +4.40% | +9.76% (`flower-bud-with-background-fern-cpl`) |

The groups overlap almost completely, and **the strongest SMOOTH subject
exceeds 5 of the 6 FRINGED subjects**. C2 predicts the smooth group sits near
zero. It does not. The correlation **fails**.

### The correlation that does hold

Within a subject, comparing the most-fringed quartile of its own silhouette
against the straightest quartile of the same silhouette in the same frame:

| subject | fringed | straight | ratio |
| --- | --- | --- | --- |
| `flower-bud-alone-cpl` | +17.01% | +3.18% | 5.4x |
| `bee-1-cpl` | +9.79% | +0.97% | 10.1x |
| `109MSDCF` | +8.68% | +1.36% | 6.4x |
| `119MSDCF` | +3.86% | +0.56% | 6.9x |
| `coffee-bean` | +11.74% | +7.13% | 1.6x |
| `lavendar-cpl` | +6.04% | +2.93% | 2.1x |
| `bee-3-cpl` | +6.00% | +4.48% | 1.3x |
| `bee-2-cpl` | +6.53% | +5.06% | 1.3x |
| `flower-bud-with-background-fern-cpl` | +3.97% | +9.76% | 0.4x |

Fringe raises the ring in **8 of 9** subjects. That is a real effect and it is
the defensible residue of C2. It is a claim about *amplification within a
silhouette*, not about which subjects have rings, and it does not license
either the acceptance test or the negative control.

## Consequences for the election lane

Both artifacts named in section 12 come out of the merge, so the two
"acceptance tests" it hands downstream are unsafe as written:

- **The target is mis-set.** "A fix must drive `flower-bud`'s ring prominence
  from 12.0% toward `coffee-bean`'s 0.23%" names a floor that does not exist.
  `coffee-bean`'s own ring is +6.7% measured on ORCH's mask.
- **The free negative control is not a control.** "`coffee-bean` has no ring to
  remove, so any change that moves *its* profile is doing something other than
  what it claims" inverts the truth. `coffee-bean` has a ring, so a genuine fix
  **should** move its profile, and this rule would reject it.

## The seven attacks

| # | attack | landed? | what it showed |
| --- | --- | --- | --- |
| 1 | normalisation is doing the work | **partly, not as suspected** | Contrast normalisation is arguably more correct and agrees better. ORCH did not cherry-pick. The real defect is that the quantity is pinned by the threshold, so no normalisation of it is informative. |
| 2 | n = 2 | **landed** | The statistic spreads 16.88 points across nine like-polarity subjects. A 1.7-point agreement between two of them is a sampling coincidence. |
| 3 | absolute pixel bins on two magnifications | **landed** | `coffee-bean`'s ring is at 34 px at +7.13%, not 450 px at 0.23%. Rebinning alone recovers +5.54%, so the bins are part of the cause but not all of it. |
| 4 | the mask | **landed, against V-RIM** | ORCH's 59.55% **is** genuinely the bean, tight to the silhouette. It carries 121745 px of interior holes and 46.35% of its 0–4 px bin lies inside the outer silhouette, so that bin is a mixture — but the sub-population medians are 34520 and 34589 DN against 34550 overall, so the number survives. My own Otsu mask is the defective one, over-reaching 7.7 points of frame into the dim corner of the sweep at 48061 DN. Re-anchoring on ORCH's mask left my result unchanged. |
| 5 | the far-field reference | **landed** | The 600–1400 px band is subject-free. But the four defensible references span 57686 to 65519 DN, and swapping ORCH's band for the outer 20% moves the C1 number by 2.25 points — more than the agreement it rests on. `coffee-bean`'s backdrop also wanders by several percent over comparable spans, so the reported 0.23% ring is **below the instrument's own floor** and measures nothing. |
| 6 | bin population and curvature | **landed, and superseded** | Replaced by per-ray selection on measured local straightness, which removes azimuthal mixing and curvature weighting together. That instrument produced the C2 refutation. |
| 7 | demosaic bias near high-contrast edges | pending | See Gaps. |

## Defects found in my own instruments, disclosed

An adversarial verifier that reports only the other party's errors is not
measuring, so:

- **My placebo was wrong first.** `np.argmax` of the distance transform put the
  synthetic disc at image corner (7031, 0) — the documented corner-maximum trap
  — and its reference band ran into the subject's own veil, reporting a
  nonsense +45.22% darkening. Fixed by requiring 60 px border clearance and
  350 px subject clearance; the corrected placebo reads **−0.18% edge, +0.14%
  ring**, which is the method's true noise floor and is what makes the −42.79%
  and +7.13% credible.
- **My first ring statistic had the same disease I diagnosed in ORCH's.** Peak
  minus distant minimum let backdrop structure inflate it, scoring `109MSDCF`
  at +72.65% because its plateau falls into an unrelated dark object at 200 px.
  Replaced by a bounded dip-plus-recovery statistic with a per-subject null.
- **My segmentation is worse than ORCH's on `coffee-bean`**, as above.
- **`sample()` subsamples to 4000 rays before geometric rejection**, so the
  `all` and `straight` groups are independent draws rather than nested sets.
  This is visible as a subset larger than its parent in the frame-52 table. It
  does not bias the medians, but the counts are not comparable between groups.

## Gaps

- **Attack 7 is not yet closed.** Binned-mode renders, which are genuinely
  un-interpolated, were queued but had not completed. Demosaic bias near
  high-contrast edges therefore remains **unverified**, not refuted. It is the
  one attack that could still move the numbers, since it acts exactly where I
  measure.
- **The single-frame control is one sharp frame on one subject.** Frame 30 was
  unusable (backdrop clipped at 65535) and frames 10 and 95 are too defocused
  at the silhouette to resolve a 34 px feature — a defocused frame cannot show
  a ring and would fake a clean negative. Only frame 52 is a real test. The
  same control on `flower-bud` was queued and had not completed.
- **The renderer aborted twice with `0xC0000409`** under memory pressure from
  concurrent agents, on `dry-erase-marker-head-cpl` and on `cb-frame75`. The
  former succeeded on retry and is included in the tables above; the latter was
  not retried. This is machine contention rather than a defect in the merge, but
  a renderer that fail-fasts instead of reporting an allocation failure is worth
  someone's attention.
- **`tweezers-cpl` registers zero rays** and is genuinely unmeasured.
- **Four subjects have backdrops too structured to decide**, including one
  (`109MSDCF`) whose null is 40%.
- **I did not verify anything inside `crates/`.** The brief made it read-only.
  The proposed mechanism — that a box-summed gradient focus measure scores edge
  density rather than sharpness — is untested here.
- **ORCH's committed `rimprofile.log` and `rimprofile-fb.log` print a
  superseded verdict** ("NO local maximum … the bright rim seen in the gallery
  is the tone curve") from before the prominence detector was corrected; script
  mtime 4:00 PM against log mtime 3:57 PM. The document's numbers are
  reproducible from the profiles those logs print, so this is a stale artifact
  rather than a defect, but the logs as committed contradict the document.

## Pictures

| path | what it shows |
| --- | --- |
| `pics/merge-vs-frame52.png` | The whole finding in one frame. Same crop, same linear stretch, no gamma: the merged output has a dark band, a bright band and a second dark band; the in-focus single frame has a clean step onto flat backdrop. |
| `pics/coffee-bean-ring.png` | The ring hugging a smooth silhouette, with the registered ray profiles beside it. |
| `pics/mask-disagreement.png` | Why attack 4 landed against me. ORCH's mask is tight to the bean; mine swallows the dim corner of the sweep. |

