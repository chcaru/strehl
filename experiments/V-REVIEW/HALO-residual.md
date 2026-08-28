# Closing the residual risk: the blind 4, the unscored 7, and the broad-rim blind spot

**Headline: no halo is demonstrated anywhere in the 26-master corpus -- and I
could not commission an instrument entitled to say "no halo" either.** Those
are different statements and I am not going to let the first stand in for the
second.

`leaf-2-cpl` is **acquitted of halo**: its +5721 DN is a walk artifact, proven
by a mechanism that reproduces on a second subject.

---

## 1. The 4 clean-but-blind: re-walked past the pinch

The cell-pinch truncation is not arbitrary -- its comment says the surviving
pixels are "a directional sliver". So I did not delete it, I tested it. A real
rim surrounds a silhouette; a sliver points one way. MEASURED (`vh_blind.py`),
azimuthal coverage about the dominant part's centroid, 16 bins:

| subject | 50-80 px median | coverage | azimuthal spread | verdict |
|---|---|---|---|---|
| **leaf-2-cpl** | **+5721** | **44%** (7/16) | **18845 DN** | walk artifact |
| **lead-1-cpl** | **+4447** | **44%** | 18626 DN | walk artifact |
| couch-fibers-cpl | -6172 | 100% | 4149 DN | genuinely clean |
| pencil-flatter-angle-cpl | -5234 | 94% | 9740 DN | genuinely clean |
| *bee-1-cpl (control, 7/7)* | *-5601* | *100%* | *17680 DN* | *clean* |

**`leaf-2-cpl`'s +5721 is not a halo.** Its per-direction medians disagree by
**18845 DN, 3.3x the signal itself**, drawn from **44% of directions** at a
cell density of 2.5%. And `lead-1-cpl` reproduces the identical signature --
positive spike at exactly 50-80 px, crash at 80-120, the same 44% coverage.
Two unrelated subjects producing the same excursion at the same radius as
their cells pinch is the walk geometry, not either scene.

Note the control carefully: **spread alone does not discriminate** (bee-1 is
17680 DN at 100% coverage). Coverage does. Had I used spread, as my rejected
`vh_sector.py` did, I would have convicted a clean subject.

`couch-fibers-cpl` and `pencil-flatter-angle-cpl` are monotone and negative
throughout: clean, and simply never reported as such.

**For ORCH's note that `leaf-2-cpl` is also visibly soft and sits high on the
band-0 table: those instruments are not corroborated by this one.** Softness
and halo are different defects. This lane finds no halo on that subject.

---

## 2. The 7 UNSCORED: taxonomy, and they are not passes

Three causes, not one (MEASURED, `vh_trunc2.py`):

| cause | subjects | why | what would fix it |
|---|---|---|---|
| **No far field** -- subject fills the frame | 112MSDCF, 113MSDCF, foam | far field 0 px; subject reaches only 167/181/42 px | re-capture with background margin, or reference a local annulus instead of 400-900 px |
| **Background not uniform** | coffee-bean (3659 DN), flower-inner-edge-cpl (3147 DN) | far field's own halves differ beyond the 3000 DN limit | flat-field correction, or a per-direction local reference |
| **No dominant silhouette** | coffee-bubbles (backdrop 1.5% of frame), wrapped-text-1 (largest of 79 parts is 1.7%) | there is no single occluding boundary to walk outward from | needs a different statistic entirely; no radial method applies |

These must be counted as UNSCORED, never clean. The instrument did not look.

---

## 3. The radial-profile approach cannot do this job. Measured, not argued.

I built the decay/shape test ORCH approved (`halo2.py`) and **commissioned it,
and the commission killed it**: a planted rim of **3200 DN, narrow AND broad,
read "profile is monotone; no local rim"**. Requiring a peak above both
neighbours cannot work, because the subject's own penumbra rises ~3600 DN per
band and the rim never breaks monotonicity.

So I replaced the statistic with a residual from a robust smooth trend, and
swept the trend stiffness, measuring both failure modes on one axis
(`vh_degsweep.py`). MEASURED:

| trend degree | worst residual on 5 UNPLANTED clean hosts | planted narrow 3200 | planted broad 3200 | separation |
|---|---|---|---|---|
| 2 | 5069 DN | 5474 | 4160 | 1.02x / 0.82x |
| 3 | 4380 DN | 1883 | 2628 | 0.43x / 0.60x |
| 4 | 2613 DN | 1323 | 3305 | 0.51x / **1.26x** |
| 5 | 5913 DN | 3202 | 1140 | 0.54x / 0.19x |
| 6 | 2516 DN | 1237 | 985 | 0.49x / 0.39x |

**At every stiffness, an unplanted clean subject produces a residual as large
as a planted 3200 DN rim.** Best separation 1.26x. There is no usable setting.

This independently reproduces `halo_profile.py`'s own header claim -- "a radial
profile detector cannot see a rim close to a steep penumbra, and no amount of
band tuning changes that" -- by a **different statistic and a different failure
axis**. I did not take that claim on trust and it survived.

---

## 4. `halo3.py`: edge-normal overshoot. Better, and still not commissioned.

The defect in every radial method is azimuthal averaging: it pools edges whose
penumbra depth differs by tens of thousands of DN. So `halo3.py` samples along
the **outward normal** at every boundary point and scores each edge against
**its own** profile. Three defects found and fixed in it by commissioning, each
recorded in the file:

1. **Max-of-noise.** Taking the max per-edge first read **HALO 7745 DN on
   known-clean `bee-1-cpl`** -- the max of noise over 135 samples is always
   positive. Fixed by averaging aligned profiles before any maximum.
2. **Wrong reference.** Scoring against the far plateau missed a 3200 DN rim
   inside a deep penumbra while firing on a 6000 DN gradient. Replaced with
   drawdown from the profile's own running maximum, which is local.
3. **Truncated window.** A gradient still falling at 200 px looks narrow.

MEASURED detection floors (`vh_commission3.py`), the first ever stated for a
broad rim on this project:

| host | narrow sigma14 | broad sigma40 | gradient false positives |
|---|---|---|---|
| bee-1-cpl | **1600 DN** | 400 DN | 1 of 4 (at 3000 DN) |
| bee-2-cpl | **1600 DN** | 1600 DN* | 0 of 4 |

**COMMISSION FAILED**, and I will not present its corpus table as certified.
The residual failure is structural: with the width gate alone, gradients fire;
adding a trough-inside-window gate stops them but also stops broad-rim
detection (*bee-2 broad drops to NOT DETECTED). **At a 200 px window a broad
rim and a backdrop gradient both trough near the window edge and cannot be
separated.** Separating them needs a longer clear background run than these
subjects have -- at 200 px, 8 of 26 already UNSCORE for lack of one.

**This is nonetheless a large improvement on the shipping instrument, which
could not detect a broad rim at 9000 DN by either statistic.**

---

## 5. The corpus through `halo3` -- suggestive, NOT certified

| verdict | n | subjects |
|---|---|---|
| HALO | **1** | lavendar-cpl (1410 DN @ 65 px, width 20, floor 610) |
| CLEAN | 17 | incl. all four old false positives: flat-on-ruler 437 (floor 437), tweezers **0.0**, 119MSDCF 77, plus wrapped-text-1, coffee-bean, flower-inner-edge |
| UNSCORED | 8 | 112MSDCF, 113MSDCF, foam, coffee-bubbles, couch-fibers, lead-1, leaf-2, pencil-flatter-angle |
| **total** | **26** | |

**`lavendar-cpl` is the one reading, and I looked at it.** 1:1 crops
(`crop1to1.py --mode halo`, fixed transform, no autoscale) show a bud wrapped
in **white trichomes radiating outward from the silhouette** -- real scene
structure at exactly the tens-of-pixels scale the statistic reads as a rim. At
site 3 the bud sits against clean white background with **no bright ring**.
This is ORCH's candidate mechanism 2, subject texture entering the annulus.
It is also **below the 1600 DN floor I demonstrated**, from the fewest edges of
any scored subject (404). **Not a halo, and not evidence for one.**

---

## 6. Three-way partition, all 26

| category | n |
|---|---|
| VISIBLE defect | **0** |
| MEASURED-but-not-visible (old false positives) | **4** |
| clean | **14** |
| UNSCORED, per-subject reason in section 2 | **8** |
| **total** | **26** |

---

## 7. What I am and am not entitled to say

**ENTITLED (measured):**
- The four HALO verdicts are false positives (previous report, unchanged).
- `leaf-2-cpl`'s +5721 is a walk artifact; no halo on any of the blind 4.
- A radial profile cannot detect a rim near a steep penumbra at any tuning.
- `halo3` detects narrow rims at 1600 DN and broad rims at 400-1600 DN on the
  hosts tested -- the shipping instrument detects neither.

**NOT ENTITLED:**
- "The corpus has no halo." No instrument passed commissioning, so absence of
  detection is not evidence of absence. **Do not put "no demonstrated halo"
  in a README on my authority.**
- Any statement about the 8 UNSCORED subjects.

**For V-SPEED's `STREHL_HULL`:** nothing here puts the fix back on the table.
I found no rim on `leaf-2-cpl` and none among the unscored that I could
measure. Routed through ORCH, not to V-SPEED.

**What would settle it:** captures with >=400 px of clear background around the
subject would let the window separate a broad rim from a backdrop gradient, and
would rescue most of the 8 UNSCORED. That is a capture change, not a code
change, and it is the single highest-value thing that could be done for halo
measurement on this project.

---

## 8. Disclosure of my own errors this round

1. `halo2.py` local-max statistic -- **built, commissioned, refuted.** Kept.
2. First `halo3` statistic read **HALO 7745 DN on a clean subject** (max of
   noise). Caught by commissioning, not by inspection.
3. Second `halo3` statistic used the wrong reference and was refuted by the
   gradient arm.
4. Reported "0 HALO / 16 CLEAN" from `halo2` **before commissioning it**. That
   table was worthless and is withdrawn here. The lesson is the one ORCH
   stated: an uncommissioned instrument reporting zero defects is
   indistinguishable from a broken one.
