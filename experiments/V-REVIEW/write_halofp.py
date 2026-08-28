# -*- coding: utf-8 -*-
import io, os
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\HALO-falsepositive.md"
T = """# Are the four HALO verdicts false positives?

**Answer: yes. All four. Measured, each by a different mechanism.**
ORCH's eyes were right, and the reason he could not see the defect is that the
statistic named "halo" is not measuring a halo on any of these four subjects.

I also found a second defect he did not ask about, in the opposite direction:
**four subjects report clean from a partial walk**, and the output cannot be
distinguished from a full one.

I changed nothing in `halo_profile.py` this round. The 11-subject regression
gate therefore holds by construction, and the instrument has not become more
permissive. This is diagnosis; the fix is specified at the end, not applied.

---

## 1. The test that settles it

The instrument walks d = 2..120 px, then references a far field at 400-900 px.
**Nothing between 120 and 400 px is ever measured.** That hole is where the
answer was.

A halo is a *local* rim: it must decay to background within roughly 100 px of
the silhouette. A lighting falloff declines smoothly across the whole frame.
Inside 120 px the two are indistinguishable. Across 400 px they are trivially
distinguishable. So I filled the hole (`vh_hole.py`), same Voronoi restriction
and same far field as the instrument, and added four known-clean controls.

MEASURED, DN relative to each subject's own 400-900 far field. The instrument
sees only the columns left of the bar.

| subject | 2-6 | 12-20 | 32-50 | 50-80 | 80-120 &#124; | 120-170 | 170-230 | 230-300 | 300-400 | 400-550 | 550-700 | 700-900 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **flat-on-ruler-cpl** *(HALO)* | -8368 | -3879 | +4713 | +5283 | **+5680** | **+6098** | +5593 | +1452 | +901 | +533 | -98 | . |
| **tweezers-cpl** *(HALO)* | -21258 | -20443 | -16108 | -17675 | -15519 | -13254 | -11051 | -8312 | -6062 | -2246 | +332 | +1203 |
| **lavendar-cpl** *(HALO)* | -9023 | -6009 | -1284 | -284 | **+351** | -101 | -1351 | -651 | -232 | +352 | +1023 | +1528 |
| **119MSDCF** *(HALO)* | -13811 | -1550 | +287 | +734 | **+820** | +944 | +926 | +914 | +979 | +1155 | +1168 | +1065 |
| bee-1-cpl *(clean)* | -18390 | -15781 | -9102 | -5601 | -3441 | -2493 | -1497 | -702 | -374 | -403 | -739 | -1349 |
| bee-2-cpl *(clean)* | -19257 | -14809 | -6909 | -5060 | -4307 | -3699 | -3284 | -3016 | -2584 | -2547 | -1844 | -865 |
| flower-bud-alone-cpl *(clean)* | -19943 | -5019 | -1205 | -777 | -471 | -251 | -99 | +20 | -54 | -200 | -30 | +85 |
| leaf-2-cpl *(clean)* | -8890 | -2660 | -71 | **+5721** | -4524 | -2319 | -1991 | -1669 | -3631 | -3102 | . | . |

### The four verdicts

**`flat-on-ruler-cpl` -- FALSE POSITIVE.** Its "rim" peaks at **+6098 DN at
120-170 px, which is 107% of the value it was flagged on and lies OUTSIDE the
region the instrument measured.** It then decays over ~300 px. A rim that is
still rising past 120 px and takes 400 px to fall is not a rim. This is a
lighting falloff across a flat card. MEASURED.

**`119MSDCF` -- FALSE POSITIVE.** The elevation never decays *at all*:
+287, +734, +820, +944, +926, +914, +979, +1155, +1168, +1065 from 32 px to
900 px. It is flat across the entire frame. There is no rim; the whole
background sits above the reference. MEASURED.

**`lavendar-cpl` -- FALSE POSITIVE.** Flagged at +351 DN against a 200 DN
threshold. Its own background varies from **-1351 to +1528 DN** across
120-900 px. The detection is roughly 8x smaller than the variation of the
thing it is measured against. Per this project's rule -- *do not compare two
numbers closer together than the spread you printed* -- this reading has no
standing. MEASURED.

**`tweezers-cpl` -- FALSE POSITIVE.** ORCH's read of the sign was correct.
Overshoot is **-15519**: the near-silhouette backdrop is far DARKER than the
far field, which cannot be a bright halo. The whole profile is a smooth
monotone recovery from -21258 to +1203 -- a graduated backdrop, visible in
the scene. `bump` 1567.0 is **one** non-monotone step (32-50: -16108 ->
50-80: -17675) inside a ramp spanning **22,461 DN**: a 7% wiggle on a huge
gradient. MEASURED.

**A statistic that fires on a graduated backdrop will fire on most studio
shots.** Three of these four fire on a scene gradient; the fourth fires below
its own noise floor.

---

## 2. The defect in the other direction: clean verdicts from partial walks

`vals` in `profile()` **`break`s at the first band that pinches off**, but
`bands` still gets all seven entries appended (pinched ones as `None`). So the
number of bands the statistic actually examined is `len(vals)`, and **it is
printed nowhere.** A partial walk and a full walk both print `MEASURED ... 0.0`.

MEASURED (`vh_trunc2.py`), coverage across all 26:

| subject | bands used | deepest band examined | reported |
|---|---|---|---|
| lead-1-cpl | **4/7** | 20-32 px | clean |
| leaf-2-cpl | **4/7** | 20-32 px | clean |
| couch-fibers-cpl | **5/7** | 32-50 px | clean |
| pencil-flatter-angle-cpl | **5/7** | 32-50 px | clean |
| (15 others) | 7/7 | 80-120 px | 11 clean, 4 flagged |

**`leaf-2-cpl` proves this is not hypothetical.** It reports clean with
overshoot -1808.6 -- which is exactly its 20-32 px value -- while carrying a
**+5721 DN excursion at 50-80 px that the statistic never looked at.** I do
not claim that excursion is a halo; I claim the instrument did not examine it
and reported clean anyway.

This is the same family as "a skip is not a pass", except it hides *inside* a
MEASURED verdict, where no summary can show it.

---

## 3. Calibration ladder: what these amplitudes look like

Planted rims of known amplitude into a clean host, full-resolution distance
field, fixed crop box and fixed gamma across rungs, no per-crop autoscale
(`vh_ladder2.py`; sheets at `D:\\strehl-out\\V-REVIEW\\halo\\crops\\`).

- **Narrow rim (sigma 14 px):** detected. `bump` 0.0 at 2000 DN, 14.3 at 4500,
  1138.9 at 9000. **Stated detection floor: ~4500 DN planted narrow amplitude
  on this host, and only via `bump`.** MEASURED.
- **Broad rim (sigma 40 px):** **`bump` stayed 0.0 at every amplitude up to
  9000 DN and the verdict never left clean.** MEASURED.
- Visually, 9000 DN broad is *perceptible side-by-side and easy to miss alone*
  -- consistent with ORCH being unable to see +5680 spread over 400 px.

**The instrument is least sensitive to exactly the shape it flagged
`flat-on-ruler-cpl` on.** It cannot detect a broad halo, and it reports broad
*gradients* as halos. Both errors have the same root: no shape test.

Ladder caveat, disclosed: on this host `overshoot` could not fire at any
amplitude, because the host's near background sits 7002 DN *below* its far
field. `overshoot` is an absolute comparison, so its floor depends entirely on
the subject's penumbra depth. The floor above is therefore a `bump` floor.

---

## 4. The partition, all counted, summing to 26

| category | n | subjects |
|---|---|---|
| **VISIBLE defect** | **0** | none |
| **MEASURED-but-not-visible** (all four = false positives) | **4** | flat-on-ruler-cpl, tweezers-cpl, lavendar-cpl, 119MSDCF |
| **clean, full 7-band walk** | **11** | 109MSDCF, bee-1/2/3-cpl, dry-erase-marker-head-cpl, flower-bud-alone-cpl, flower-bud-with-background-fern-cpl, flowers-cpl, highly-angled-ruler-mm-cpl, pencil-steep-angle-cpl, wrapped-text-2 |
| **clean but BLIND beyond 32-50 px** (not a pass) | **4** | lead-1-cpl, leaf-2-cpl, couch-fibers-cpl, pencil-flatter-angle-cpl |
| **UNMEASURABLE** | **7** | 112MSDCF, 113MSDCF, coffee-bean, coffee-bubbles, flower-inner-edge-cpl, foam, wrapped-text-1 |
| **total** | **26** | |

**Corpus-wide halo status: I have no subject on which a halo is demonstrated.**
The print-ready decision should not be carrying four halo failures.

The honest residual risk is **11 subjects**, not 4: the 7 unmeasurable plus the
4 blind. That is where an undetected halo could still be hiding.

---

## 5. Disclosure: a defect in my own measurement

My first coverage test (`vh_trunc.py`) counted `len(bands)` and reported
**"TRUNCATED WALKS: 0 of 26"**. That is wrong. `bands` is always 7 because
pinched bands are appended as `None` and `continue`d. The correct count is
`len(vals)`, and it is 4/7 or 5/7 on four subjects. I caught it only because
`leaf-2-cpl`'s reported overshoot equalled its 20-32 px value exactly, which
it should not have if seven bands had been used. The corrected test is
`vh_trunc2.py`. Both are kept.

I also previously built and **rejected** `vh_sector.py`: known-clean
`leaf-2-cpl` scored higher than three of the four flagged subjects, so it
failed its own control and its numbers carry no verdict.

---

## 6. What I recommend, and what I did not do

I did **not** change any threshold. Loosening thresholds would not fix these
four; the readings are real numbers, correctly computed, that do not mean
"halo". The defect is the absence of a shape test.

1. **Add a decay requirement.** A rim must fall to a stated fraction of its
   peak by ~2x its peak distance. Measured against the table in section 1 this
   alone acquits all four, and it *tightens* rather than loosens the instrument.
2. **Extend the walk through 120-400 px.** Cheap, and it is where three of the
   four were exposed.
3. **Report `len(vals)` per subject** and count partial walks separately from
   clean. A clean verdict from 4/7 bands must not print like one from 7/7.
4. **Gate on the background's own variation.** `lavendar-cpl` at +351 against
   a 2879 DN background spread should never have been flagged.

Items 1, 3 and 4 all make the instrument stricter. None of them can move the
7 known-clean subjects, because none of those is near a threshold.

**Unverified and stated as such:** I have not implemented these, so I have not
re-run the 11-subject regression gate against a modified instrument. The
four acquittals rest on the section 1 measurement, not on a rebuilt detector.
"""
io.open(P, "w", newline="\n", encoding="utf-8").write(T)
print("wrote", P, os.path.getsize(P), "bytes")
