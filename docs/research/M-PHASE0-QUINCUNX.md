# M-PHASE0-QUINCUNX — C12's go/no-go, and a bracket on a constant M129 left open

Lane: `experiments/M-PHASE0-QUINCUNX/`
Status: steps 1–2 complete. Zero decodes, zero captures, zero frames read.

---

## 0. What this lane found

C12 proposes reading the Bayer green pair's disagreement as a super-Nyquist
focus cue, as a per-tile alias census gating super-resolution, and as a
per-frame noise probe. Its phase-0 kill condition is whether the optics put
measurable energy past the green plane's own Nyquist at corpus apertures.

**The kill condition is not met. C12 survives.** Energy past plane Nyquist is
detected at **4 of 5** corpus apertures — f/5.6, f/8, f/11 and f/14 — at
**12.0×, 15.3×, 17.8× and 1.8×** a detection threshold measured from the data
rather than chosen.

**But C12's per-aperture prediction is backwards at one end.** It says "f/5.6
should; f/11 should not". Measured, **f/11 is the strongest aperture in this
band** (median power SNR 0.823 against f/5.6's 0.557), and the cut falls between
f/14 and f/18, two full stops further down than C12 places it.

**And a constant fell out.** The aperture at which that energy disappears is a
cutoff detector. It brackets the bellows factor `B` to **1.994 – 2.512**,
excluding two of M129's three standing hypotheses at every wavelength across
that lane's stated ±50 nm systematic. This was not pre-registered and is
reported as a lead, not a result.

**No frames were read.** Every number here comes from a spectral survey M129
computed for an unrelated purpose. This is the second phase-0 lane running that
answered its question from evidence the corpus already held.

---

## 1. The measurement already existed

M129 computed a radial power spectrum on the green quincunx lattice for 30 cells
— 5 apertures × 6 ROIs — and banded it. Its `high` band is
**(0.260, 0.330) sensor cyc/px**.

The green plane's own Nyquist is **0.25 sensor cyc/px**. So M129's `high` band
lies entirely above plane Nyquist and below the quincunx radial reach. It *is*
C12's band, already measured, already noise-subtracted, sitting in
`M129-fabric-spectral-ladder/out/snr-w2.json`.

The units were verified rather than assumed. `m129/src/snr_survey.py` line 67
states the bands are in sensor cyc/px, and the three lattice Nyquists re-derive
from the corpus's own pitch constant:

| lattice | pitch µm | Nyquist cy/mm | Nyquist sensor cyc/px |
| --- | --- | --- | --- |
| full sensor | 5.1200 | 97.66 | 0.50000 |
| GQ quincunx | 7.2408 | 69.05 | 0.35355 |
| G1 or G2 alone | 10.2400 | 48.83 | 0.25000 |

A factor of two on this axis would have moved the band somewhere else entirely
and every number downstream would still have looked reasonable, which is why it
is checked first and by control C4 again afterwards.

**Coverage limit, load-bearing.** C12's band is 0.25 → 0.50 cyc/px, because the
quincunx union reaches full sensor Nyquist *along the axes*. This radial
spectrum reaches only **0.35355**, the inscribed diagonal limit. Energy between
0.354 and 0.500 lives near the axes and is not sampled here. **This lane
measures the isotropic part of C12's band, not all of it** — which makes its
positive finding a lower bound on the available energy, and makes any negative
finding it produced weaker than it looks.

---

## 2. The kill condition, answered against a measured null

C12's own words: *"Kill: if the optics at corpus apertures never put measurable
energy past plane Nyquist … consumers 1–2 die."*

The natural-looking bar is power SNR > 1. That bar is arbitrary, and using it
would have produced the wrong answer — only 2 of 30 cells clear it.

The data carries a better one. **f/18 cannot transmit into this band under any
of M129's three bellows hypotheses**, so its six cells measure the instrument's
zero:

- f/18 high-band SNR: mean **−0.0198**, sd **0.0088** over 6 cells.
- The noise floor estimate is therefore good to about **2%**.
- Detection threshold `|mean| + 3sd` = **0.0462**.

Against that threshold:

| aperture | N | cells detected | median SNR | × threshold |
| --- | --- | --- | --- | --- |
| f/5.6 | 5.657 | 6/6 | +0.557 | 12.0 |
| f/8 | 8.000 | 6/6 | +0.708 | 15.3 |
| f/11 | 11.314 | 6/6 | +0.823 | 17.8 |
| f/14 | 14.254 | 5/6 | +0.083 | 1.8 |
| f/18 | 17.959 | 0/6 | −0.021 | −0.4 |

Judged by the arbitrary bar this lane would have reported "2 of 30 cells";
judged by its own null it reports detection at four of five apertures. The
difference is not a matter of taste. **The null is a property of the
instrument and the bar was a property of my expectations.**

The f/18 null is not a sensitivity failure. f/18 has the **lowest** noise floor
of the five apertures (99.3 against f/5.6's 3762.2), so it is the most
sensitive cell in the ladder. Its zero is an absence of signal.

---

## 3. Where C12 puts the cut, and where it actually falls

C12 predicts f/5.6 yes and f/11 no. Both halves of that are wrong in the same
direction: there is **more** energy past plane Nyquist than C12 expects, and it
survives **further down** the aperture ladder.

Diffraction cutoffs, `f_c = PITCH_UM / (λ·B·N)`, carried across all three of
M129's standing bellows hypotheses so that nothing depends on which is right:

| aperture | N | H1 (B=3.732) | H2 (B=3.076) | H3 (B=2.402) | band 0.26–0.33 |
| --- | --- | --- | --- | --- | --- |
| f/5.6 | 5.657 | 0.4410 | 0.5350 | 0.6851 | full / full / full |
| f/8 | 8.000 | 0.3118 | 0.3783 | 0.4844 | part / full / full |
| f/11 | 11.314 | 0.2205 | 0.2675 | 0.3426 | none / part / full |
| f/14 | 14.254 | 0.1750 | 0.2123 | 0.2719 | none / none / part |
| f/18 | 17.959 | 0.1389 | 0.1685 | 0.2158 | none / none / none |

The correct statement is **the cut falls between f/14 and f/18**, not between
f/5.6 and f/11. For C12's consumers this matters concretely: the alias census
(consumer 2) and the super-Nyquist focus cue (consumer 1) are live across the
whole working range of this rig, not only at its widest apertures.

---

## 4. The subject-limited confound, which this lane cannot remove

The subject is one fabric weave. *"This subject puts little energy past plane
Nyquist"* and *"the optics cannot deliver energy past plane Nyquist"* are
different claims, and one subject cannot separate them.

What makes the aperture trend interpretable anyway is that **the subject is
identical across all five apertures**. Anything that moves with f-number is
optical. The measured transfer — the fraction of the subject's own power landing
past plane Nyquist, which divides out both exposure and subject contrast — moves
by a factor of **−25.7** from f/5.6 to f/18 and changes sign. That trend is
optical whatever the subject is.

The finding that would not survive a subject change is the *absolute* level. A
subject with finer structure would put more energy in this band at every
aperture. That direction only strengthens C12.

---

## 5. An anomaly this lane reports and does not explain

Transfer past plane Nyquist **rises 1.916×** from f/5.6 to f/8 before falling
monotonically thereafter.

Both apertures transmit the entire band under every bellows hypothesis, so this
is not a cutoff effect — it is MTF *shape*: aberration, or residual focus error
at the shallowest depth of field in the ladder. A macro lens that improves from
f/5.6 to f/8 is entirely ordinary.

It is recorded because **it carries the same sign as M129's own unexplained
aperture trend in `B`**, and because it is the reason one of this lane's
controls failed on its first run (§7).

---

## 6. Unregistered: a bracket on the bellows factor

**This was not predicted before looking at the data.** It is in its own file,
labelled, and it is a lead with a number attached rather than a settled result.

If energy is detected at one aperture and absent at the next, the diffraction
cutoff crossed the band's lower edge between them. That brackets `B` from both
sides, with no fit, no subject model, and no assumption about MTF shape below
cutoff:

```
detected at f/14  =>  f_c(14.254) > 0.26  =>  B < 2.5118
absent   at f/18  =>  f_c(17.959) < 0.26  =>  B > 1.9936
```

| hypothesis | B | inside 1.994 – 2.512? |
| --- | --- | --- |
| H1 | 3.732 | no — excluded |
| H2 | 3.076 | no — excluded |
| H3 | 2.402 | yes |

**Robust:** H1 and H2 are excluded at every λ across m5_lib's stated ±50 nm
systematic (brackets 2.193–2.763 at 0.500 µm and 1.827–2.302 at 0.600 µm), and
the hard-cutoff idealisation biases both bounds *away* from H1 and H2 rather
than toward them.

**Not robust:** H3 sits inside only for λ up to about 0.57 µm; at 0.600 µm it
falls just outside. **This evidence does not elect H3.** It says `B` lies near
2.0–2.8, which is H3's neighbourhood and nobody else's.

**It rests on one point.** The upper bound comes entirely from f/14 being a
detection. If f/14 were null, only `B > 1.994` would survive and neither H1 nor
H2 would be excluded. f/14 stands **11.7 null sd** above the null mean, and its
noise floor is within 50% of f/18's, so the null scale measured at f/18 is the
right scale to judge it by. That is firm — but it is one point, from one
subject, found after the fact, and it should be pre-registered and re-run on a
second subject before it settles anything.

---

## 7. My own errors, disclosed

**The monotonicity control had a wrong premise.** Control C3 required high-band
transfer to fall monotonically with f-number because "diffraction is monotone".
It rose 1.739× from f/5.6 to f/8 and the run recorded a control failure.
Diffraction sets a *cutoff*; it governs the level inside a band only once the
cutoff has entered that band. At f/5.6 and f/8 the band is fully transmitted
under every hypothesis, so its level is set by MTF shape. The control now
applies only where the cutoff is actually in play, and the rise is reported as a
finding instead of swallowed as a failure.

**The detection bar was arbitrary.** Scoring against SNR > 1 would have reported
"2 of 30 cells detected" and made C12 look nearly dead. The measured null says
the real threshold is 0.0462, and four apertures clear it by 1.8× to 18.4×.

Both errors ran in the same direction — **they made the instrument look blinder
than it is** — and neither was found by a control passing. The first was found
by a control failing on a premise I had not examined; the second by asking what
the f/18 cells were for.

**Every reported "median" was biased upward, and no control caught it.** The
first two runs of this lane summarised each aperture with `sorted(v)[len(v)//2]`.
On the even n = 6 used throughout, that returns the **4th smallest** — an order
statistic sitting above the middle, not a median. Every headline figure
inherited the bias: f/5.6 read 0.567 instead of 0.557, f/11 0.849 instead of
0.823, the f/5.6→f/8 rise 1.739× instead of 1.916×, the f/14 margin 11.9 null sd
instead of 11.7.

None of the five controls could see it, because all five compare the lane to
itself. It was found by `check_note.py`, which re-derives the same quantities
from M129's raw spectra with independently written code and refuses to agree
with the run by construction. The corrected numbers are the ones above.

The verdict does not move: detections are counted per cell and the bracket
depends only on which apertures detect, so neither depends on the summary
statistic at all. That is luck rather than design — the bias happened to land in
the reported figures and not in the load-bearing ones.

**A second discrepancy in the same run was my checker's fault, not the lane's.**
The first version of `check_note.py` banded on a half-open interval with
count weighting and disagreed with the stored spectra by about 7%.
`snr_survey.py` is the authority: the band is closed at both ends and the mean
is unweighted. The lane had this right and control C1 had already demonstrated
it to 8.13e-15. Two independent implementations disagreed; **the disagreement
was resolved by going to the source rather than by picking a winner**, and each
side turned out to be wrong about a different thing.

**What this lane did not do.** It did not re-measure M129's spectra from frames.
It verified that its own banding reproduces M129's stored band summaries to
8.13e-15 relative (control C1), which establishes that it reads the file
correctly, not that the file is correct.

---

## 8. What this changes in the proposal

| § | Change | Why |
| --- | --- | --- |
| C12 kill condition | **Not met — mark C12 as surviving phase 0.** | Energy detected at 4 of 5 apertures at 1.8–18.4× a measured null. |
| C12 "f/11 should not" | **Strike.** Replace with "the cut falls between f/14 and f/18". | f/11 is the strongest aperture in the band, not an absent one. |
| C12 phase-0 scope | Note that the isotropic part of the band was measured; 0.354–0.500 cyc/px near the axes remains unmeasured. | The radial spectrum stops at the quincunx inscribed limit. |
| C12 consumers 1–2 | Live across the full working aperture range, not only wide open. | Follows from the corrected cut. |
| M129 `B` | Flag the bracket 1.994–2.512 as independent evidence excluding H1 and H2. | Unregistered; needs pre-registration and a second subject. |
| §9 sequencing | M-PHASE0-QUINCUNX needs no captures and is complete. | Ran on existing corpus data. |

---

## 9. Reproduction

```
cd experiments/M-PHASE0-QUINCUNX/src
python q1_band.py          # census + physical frame, controls C1-C5
python q2_bhyp.py          # unregistered bracket on B, controls C6-C10
python check_note.py       # 68 checks against this note -> GREEN
python commission_note.py  # 52 planted defects -> 52 caught, COMMISSIONED
```

`q1_band.py` reads `M129-fabric-spectral-ladder/out/snr-w2.json` and nothing
else. `q2_bhyp.py` reads `out/q1-band.json` and measures nothing new.

`check_note.py` does not trust either of them. Its 35 DERIVED checks re-band
M129's raw per-cell spectra with independently written code and recompute the
lattice geometry and diffraction cutoffs from `PITCH_UM`; its 23 PINNED checks
then require the lane's stored output to agree with that re-derivation to 1
part in 10⁹. Its 10 CLAIM checks assert the disclosures in §7 are present.

`commission_note.py` plants 52 defects in three families: 41 in the note, 10 in
the lane's stored JSON, and 2 planted in both at once so that the run and the
note agree with each other and are both wrong. Each plant must drive the checker
RED **and name the specific check that should have caught it**; a plant that
merely turns something else red is recorded as `WRONG`, not as caught. Anchors
are whitespace-insensitive regexes that must resolve to exactly one site, and a
plant that fails to apply aborts the run rather than counting as a success.
