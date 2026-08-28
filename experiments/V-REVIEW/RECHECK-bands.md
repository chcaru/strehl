# V-REVIEW re-check against CORRECTION #4 (per-subject band boundaries)

ORCH's correction #4 refutes the fixed band criterion I was given and applied:
band 0 (0.25-0.50) as NOISE and band 1 (0.17-0.25) as SIGNAL, corpus-wide.
V-LINEAR `31eda43a` measures the boundary at 0.17-0.48 cyc/px, a 2.8x spread.

ORCH asked for one thing specifically: for every number I reported that used a
fixed band, state whether it moves, and make "re-checked and unchanged"
distinguishable from "not re-checked". Every row below is one or the other.

---

## 0. Verdict

**The adjudication in `ADJ-ndepth.md` does not move. Two of its supporting
characterisations do: one is confirmed and now properly qualified, one I
withdraw as unqualified.**

The headline rested on two legs, and CORRECTION #4 touches neither:

1. **The two lanes measured different subjects.** Documentary, from their own
   pre-registrations. No band involved. The correction makes this leg
   *stronger*, not weaker -- see section 4.
2. **Both comparisons are VOID on the instrument null.** The null is the
   coarsest band, `0.010-0.020 cyc/px`, which is 8.5x below the lowest boundary
   V-LINEAR measured on any subject. Section 2.

The `fit_to_cover` refutation also holds, and I re-measured it so that it no
longer rests on a band at all. Section 3.

---

## 1. Every band-dependent number I reported, re-checked

| # | number | where | qualified? | moves? |
| --- | --- | --- | --- | --- |
| 1 | null `0.9866` (113MSDCF), VOID | `ADJ-ndepth.md:47` | band-independent | **unchanged** |
| 2 | null `1.0213` (bee-3-cpl), VOID | `ADJ-ndepth.md:48` | band-independent | **unchanged** |
| 3 | "`0.30-0.35` is NOISE" for **113MSDCF** | `:18`, `:63` | **yes, 0.25** | **unchanged, now qualified** |
| 4 | "`0.30-0.35` is NOISE" for **bee-3-cpl** | `:18`, `:147` | **NO** | **WITHDRAWN** |
| 5 | acuity `1.0102` (113MSDCF) | `:47`, `:69` | **yes, 0.25** | **unchanged, now qualified** |
| 6 | acuity `1.2433` (bee-3-cpl) | `:48`, `:69` | **NO** | **WITHDRAWN as an acuity reading** |
| 7 | joint claim "neither subject shows deeper as softer" | `:69-72` | half unqualified | **narrowed to one subject** |
| 8 | round trip costs `1.6-2.1%` of band-1 EDGE | `:20`, `:117` | measured on one subject | **unchanged, no longer load-bearing** |
| 9 | arm differential `0.0027` / `0.0018`, `274x` too small | `:121-122` | re-measured in **all six bands** | **unchanged, now band-independent** |
| 10 | round trip passes the null at every `k` | `:126-128` | band-independent | **unchanged** |
| 11 | magnification `1.0011` -> null `1.0025` | `:140-141` | band-independent | **unchanged** |
| 12 | k-vs-N table | `:80-100` | read from render banners | **unchanged, no band** |

Nine unchanged, two withdrawn, one narrowed. Nothing here was left un-re-checked.

---

## 2. Why the VOID verdicts are band-independent (DERIVED, from V-LINEAR's table)

The instrument null is `contrast_ms.py`'s coarsest EDGE band, `0.010-0.020
cyc/px`. Every boundary V-LINEAR measured lies between `0.17` and `0.48`. The
null band's **top** edge is `0.020`, which is **8.5x below the lowest boundary
on any subject**.

That the null band carries signal is not merely an argument from distance.
V-LINEAR's own `R` values rise monotonically toward coarse scales on four of
five subjects, and near-monotonically on the fifth:

| subject | 0.40-0.48 | 0.30-0.40 | 0.25-0.30 | 0.20-0.25 | 0.17-0.20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `113MSDCF` | 1.105 | 1.149 | 1.387 | 2.419 | **4.874** |
| `119MSDCF` | 1.242 | 1.273 | 1.624 | 2.790 | **5.898** |
| `bee-1-cpl` | 3.629 | 4.732 | 10.728 | 27.993 | **58.740** |
| `flower-bud-alone-cpl` | 1.066 | 1.035 | 1.108 | 1.342 | **2.015** |
| `leaf-2-cpl` | 1.040 | 1.068 | 1.171 | 1.512 | **2.218** |

`flower-bud-alone-cpl` is the exception and it is trivial: `1.035 -> 1.066`
between the two finest bands, against the `2.015` it reaches at the coarse end.
The direction is unambiguous on all five. A band 8.5x coarser again is
therefore signal on every subject measured, so **a null failure means a real
global difference regardless of where a subject's boundary sits.**

This is DERIVED from V-LINEAR's measurements, not measured by me. I did not
re-run `bandsignal.py` at `0.010-0.020`; qualifying that band directly would
need per-frame linear develops that do not exist for either subject (section 4).

---

## 3. The `fit_to_cover` refutation, re-measured in every band (MEASURED)

My attribution quoted band-0 FLAT and band-1 EDGE only, so under correction #4
it was only as good as those bands' qualification. I re-ran the round trip at
the two `k` values V-DILUTE's arms actually had and read **all six bands on
both site classes**, so the verdict cannot hinge on band choice.

`experiments\V-REVIEW\vk_allbands.py`, source `A_n63_default.tif`,
`k = 0.9198` (N=33) vs `k = 0.9208` (N=63):

| band | cyc/px | FLAT .9198 | FLAT .9208 | d FLAT | EDGE .9198 | EDGE .9208 | d EDGE |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.250-0.500 | 0.6683 | 0.6710 | 0.0027 | 0.9343 | 0.9365 | 0.0022 |
| 1 | 0.170-0.250 | 0.8385 | 0.8402 | 0.0017 | 0.9802 | 0.9820 | 0.0018 |
| 2 | 0.080-0.170 | 0.9872 | 0.9887 | 0.0015 | 0.9973 | 0.9989 | 0.0016 |
| 3 | 0.040-0.080 | 0.9997 | 1.0013 | 0.0016 | 0.9998 | 1.0014 | 0.0016 |
| 4 | 0.020-0.040 | 1.0000 | 1.0016 | 0.0016 | 1.0000 | 1.0016 | 0.0016 |
| 5 | 0.010-0.020 | 1.0000 | 1.0016 | 0.0016 | 1.0000 | 1.0016 | 0.0016 |

**Largest differential in any band, either site class: `0.0027`.** V-DILUTE's
claim is `1.74x`, i.e. `0.74`. That is **274x** larger than the biggest effect
the mechanism produces anywhere in the spectrum.

So the refutation no longer depends on a band being qualified: `fit_to_cover`
cannot account for the claimed effect **in any band, on either site class**.
Previously this was one number in one band; it is now the whole spectrum.

---

## 4. `bee-3-cpl` is unqualified, and I could not cheaply qualify it (MEASURED)

V-LINEAR's five subjects are `113MSDCF`, `119MSDCF`, `bee-1-cpl`,
`flower-bud-alone-cpl`, `leaf-2-cpl`; round 2 adds `112MSDCF`,
`flat-on-ruler-cpl`, `tweezers-cpl`. **`bee-3-cpl` is in neither.**

I searched for its develops rather than assuming:

- every `bandsweep*.json` record, all twelve, listing subject keys -- **no
  `bee-3-cpl` in any of them**;
- every `lintiff` tree under `C:\dev\strehl-out` -- four exist
  (`V-LINEAR\lintiff` 63 tif, `V-NOISE2\leaf\lintiff` 182 tif, and the three
  round-2 trees which are **0 tif, i.e. not yet developed**). None is
  `bee-3-cpl`;
- every directory named `*bee-3*` -- eight hits, all other lanes' caches
  (`BUILD-SHARP`, `V-GATHER`), none a linear develop.

Qualifying it needs ~63 per-frame linear develops that do not exist. **I
therefore declare V-DILUTE's subject unqualified rather than substituting the
fixed band, and rather than borrowing `bee-1-cpl`'s `0.48`** -- V-LINEAR's rule
is that a band qualified on one subject transfers to no other, and `bee-1-cpl`
is a different subject from `bee-3-cpl`.

**The direction of the risk, stated plainly.** `bee-1-cpl` sits at `0.48`. If
`bee-3-cpl` is anywhere near its sibling, then `0.30-0.35` is **SIGNAL** on that
subject and V-DILUTE scored a legitimate band -- the opposite of what I wrote.
I have no measurement either way and I am not going to guess.

**This does not leave my adjudication hanging.** The V-DILUTE comparison is VOID
on the instrument null, which section 2 shows is band-independent. An unqualified
boundary cannot un-void it. What the missing measurement blocks is **V-DILUTE's
own finding**, not my verdict on it.

---

## 5. Self-corrections

**Two, both mine.**

**(a) I drew a joint conclusion across two subjects.** `ADJ-ndepth.md:69-72`
reads "on the qualified acuity bar, neither subject shows deeper as softer:
band-1 EDGE is `1.0102` and `1.2433`". I did not divide one by the other, so it
is not literally a cross-subject ratio -- but it is a single claim resting on two
subjects' band readings, and half of it is now unqualified. **It narrows to:**
on `113MSDCF`, whose boundary is measured at `0.25`, band 1 is `0.17-0.25` and
is qualified SIGNAL, and its acuity ratio is `1.0102 >= 1` -- deeper is not
softer on the qualified band on that subject. The `bee-3-cpl` half is withdrawn.

**(b) The fixed band was right on `113MSDCF` by construction, and I should not
take credit for that.** V-LINEAR section 1 records that the `0.25` boundary was
originally established on `113MSDCF` itself. So the criterion I applied to
V-SOFTCHECK's subject was that subject's own measured value -- correct, but by
coincidence of provenance rather than because I qualified anything. Rows 3 and 5
survive on V-LINEAR's measurement, not on my having checked.

---

## 6. What I am NOT claiming

- I have **not** qualified `bee-3-cpl` and make no band claim about it.
- I have **not** re-run `bandsignal.py` at `0.010-0.020 cyc/px`; section 2 is
  DERIVED from V-LINEAR's table, and labelled as such.
- The `1.6-2.1%` round-trip cost is measured on one subject's pixels and I do
  **not** transfer it to any other subject. Section 3's verdict does not use it.
- Nothing here revisits whether deeper stacks are softer. Both comparisons
  remain VOID; that question is still open and still needs BUILD-CROP.
