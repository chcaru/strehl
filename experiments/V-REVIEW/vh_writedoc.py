import io, os
DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-REVIEW-halo.md"
T = """# V-REVIEW-halo: is the gallery downscale the halo source?

**VERDICT: CONFIRMED-BUT-WEAKER.**

The mechanism is confirmed and localised to the resampling kernel. The scope is
narrower than "the halos were manufactured by the gallery downscale, not by the
stacker", because I measured the reduction, not the master.

**The exact sentence that is safe to say to the owner:**

> The 5x Lanczos reduction the old gallery applied provably injects bright rims
> at subject edges that are not present in the master -- up to 37 DN out of 255,
> concentrated where the gradient is highest, and *exactly zero* when the same
> reduction is done with a kernel that has no negative lobes. The gallery images
> he judged therefore cannot distinguish a merge halo from a resampling halo.

What that sentence does **not** say, and what I cannot support: that the merge is
free of halos. I did not measure the master's own halo content, and I explain in
section 6 why my attempt to do so failed rather than succeeded quietly.

All measurements are mine. I did not read `experiments/V-EYES/` or
`docs/research/V-EYES.md` before producing the numbers below, and I did not need
to read them afterwards -- I reach the same *direction* by a different route, so
there was no disagreement to reconcile. My numbers are not comparable to theirs:
mine are 8-bit gallery DN, theirs are in unstated units at unstated sites.

---

## 1. Why I abandoned edge profiles for a theorem

My first instrument was a conventional one: find step edges, sample the profile
along the normal, measure overshoot past the plateau. It **refused to seat**. On
`lead-1-cpl` it accepted **0 of 1176** candidate sites. The reason is visible in
the raw profiles and is a property of the subject, not a bug: a macro edge has no
flat plateau to overshoot *past*. The best decile of candidate sites had plateau
noise of **12.1%** of step height against a declared flatness floor of 6%.

I report this because it is the honest outcome of the approach the claim itself
used, and because loosening the floor until sites appeared is exactly how this
project previously manufactured two false convictions.

The replacement needs no edge finder, no plateau, and no site picking, so it has
no phantom-site failure mode at all.

**The bound.** PIL resize is separable and normalises each 1-D kernel to sum 1,
so every output pixel is a weighted sum of master pixels inside the kernel
support with weights summing to one. If all weights were non-negative the output
would lie within the min and max of the master pixels it read. `BOX` and
`BILINEAR` have no negative lobes; `BICUBIC` and `LANCZOS` do. **An output value
outside the local master range is therefore information that was not in the
master, and its existence proves a negative weight.** That is a theorem, not a
heuristic, and it is measured per pixel.

Units are 8-bit DN throughout, because `scripts/viewable.py` reduces *after* the
16-to-8 conversion, so 8-bit DN is what the owner's eye actually received.

## 2. Commissioning, in both directions

The instrument is `experiments/V-REVIEW/vh_hull.py`; the bench is
`vh_commission_hull.py`. Every arm is MEASURED.

| arm | input | box | bilinear | bicubic | lanczos | required |
|---|---|---|---|---|---|---|
| H1 must catch | hard step 40-200 | 0.000 | 0.000 | 2.047 | 2.752 | only negative-lobe kernels fire |
| H2 must not fire | constant 128 | 0.000 | 0.000 | 0.000 | 0.000 | nothing to ring |
| H2 must not fire | linear ramp 20-230 | 0.000 | 0.000 | 0.043 | 0.074 | nothing to ring |
| H3 must not fire | step + **real** 40 DN rim in the master | 0.000 | 0.000 | 2.559 | 3.439 | a real rim is not scored as manufactured |
| H4 must track | amplitude 20/40/80/160 DN | 0.000 | 0.000 | rises | 0.344/0.688/1.376/2.752 | ratios 2.000, 2.000, 2.000 |

**H3 is the arm that decides between the two hypotheses.** A bright rim planted
*into the master* is reproduced by box reduction and scores **0.000** -- the
instrument cannot mistake a halo that exists for a halo that was made. **H4**
kills the amplitude-invariance failure mode that made `overshoot_frac`
worthless: the ratios are exactly 2.000.

## 3. The kernel envelope, and a defect in my own bench

H1's 2.752 DN on an ideal 160 DN step is far below the corpus results in section
4, and I chased that before reporting anything.

Deriving PIL's actual weights at the gallery's scale of 5.0286 gives **31 taps**
and a 1-D negative weight mass of **N = 0.179**, so the provable 1-D envelope is
**45.65 DN** on a 0-255 range. Building the adversarial input whose sign matches
the kernel's negative lobes measures **44.265 DN for lanczos -- 97% of the
derived envelope -- and 0.000 for box and bilinear**. My statistic reaches the
theoretical ceiling without exceeding it, which is the strongest validation of it
I can construct.

The remaining gap was **my own commissioning error**. An ideal step sampled at one
sub-pixel phase does not sample the ringing peak. Sweeping the edge across one
output pixel in twelve steps measures overshoot from **2.752 to 11.367 DN**, and
**ARM H1 sampled phase 0, the minimum of the sweep**. My headline commissioning
arm understated the kernel by **4.1x**. This is the same single-draw defect class
I reported against the gate's own statistic, committed by me, one task later.

## 4. Result on the 26-master corpus

`vh_run_hull.py`, all 26 SHIP-V4 masters, all three channels, max over channels.

| kernel | negative lobes | max manufactured DN over corpus |
|---|---|---|
| box | no | **0.000000** |
| bilinear | no | **0.000000** |
| bicubic | yes | 17.126 |
| lanczos | yes | **36.997** (median 13.424, min 1.962) |

**Two kernels without negative lobes produce exactly zero on every master and
every channel; the two with negative lobes do not.** The mechanism is localised
with no residual ambiguity. Running the real gallery code path -- 8-bit RGB
resize exactly as `scripts/viewable.py` does it -- reproduces the effect at 1 to
22 DN; it reads lower than the float measurement because the real path clips at
255 and truncates the brightest overshoot.

The bound is insensitive to my one free parameter. Varying the support window
over 16, 18, 24 and 32 px leaves box at 0.0000 and lanczos at **4.280 at every
setting**.

## 5. Magnitude, character, and incidence

Manufactured excess sits at edges. Mean gradient at excess pixels against image
mean gradient: `109MSDCF` **4.87x**, `lavendar-cpl` **3.76x**, `foam` **3.26x**,
`tweezers-cpl` **1.86x**. That is rim character, not a global shift.

| subject | max bright DN | max dark DN | px above 2 DN | ppm of gallery |
|---|---|---|---|---|
| foam | 34.46 | 18.41 | 2686 | 2056.3 |
| coffee-bubbles | 34.55 | 21.40 | 859 | 657.6 |
| tweezers-cpl | 19.60 | 9.38 | 621 | 475.9 |
| lavendar-cpl | 22.85 | 20.25 | 280 | 214.6 |
| 109MSDCF | 16.00 | 11.75 | 245 | 187.6 |
| lead-1-cpl | 16.54 | 0.67 | 30 | 23.0 |
| flowers-cpl | 1.96 | 3.67 | 6 | 4.6 |

**This qualifies the claim and I will not round it off.** `lead-1-cpl` is the
headline example -- the reported sign flip from a dark edge to a bright rim -- and
on my measurement it carries provably-manufactured excess on **30 gallery pixels
out of 1.3 million**. The claim's strongest single illustration is its weakest
subject under a test that cannot be argued with.

**The incidence figures are a floor, not an estimate.** The hull test only sees
ringing that escapes the master's local range; ringing that stays inside it is
real, invisible here, and uncounted. A softer statement of the same data: the
difference between the ringing and non-ringing kernel exceeds 2 DN on **14.2%**
of `lead-1-cpl` gallery pixels and **31.2%** of `tweezers-cpl` -- but that
difference also contains legitimate sharpening, so it is an upper bound in the
same way the hull figure is a lower one. The truth is between them and I did not
measure where.

## 6. What I did not measure

I did not measure whether the master itself has halos. The instrument that would
have answered it is the one that refused to seat in section 1. Nothing in this
document constrains the merge's own overshoot, and the claim must not be stated
as though it does.

Establishing that would need the master compared against the aligned source
frames it was built from, which is the source-arm method used for the earlier
nine-subject adjudication. I did not attempt it here: without the stacker's own
alignment, frame misregistration would produce false positives at exactly the
edges under examination, which is the failure mode this report exists to avoid.

## 7. Errors I made

- **ARM H1 was a single-phase draw and understated the kernel by 4.1x** (section
  3). It is stated here at its measured value with the sweep beside it rather
  than silently replaced.
- My first instrument accepted zero sites and I initially read that as a bug in
  the site picker rather than a property of macro edges (section 1).
- The support parameter of the hull bound is conservative for bright excess but
  slightly anti-conservative for dark deficit: widening the window from 18 to 32
  px drops `lead-1-cpl`'s deficit from 0.673 to 0.000 while leaving excess
  unchanged at 4.280. Deficit figures in section 5 should be read with that in
  mind; the bright-rim figures, which carry the claim, are stable.

## 8. Scripts

All under `experiments/V-REVIEW/`, all mine, none of them modifying anything
outside that directory: `vh_hull.py` (instrument), `vh_commission_hull.py`
(bench), `vh_kernel.py` (envelope derivation), `vh_run_hull.py` (corpus),
`vh_phase.py` (phase sweep and kernel difference), `vh_local.py` (localisation
and support sensitivity), `vh_incidence.py` (per-subject incidence). Scratch and
JSON output under `C:\\dev\\strehl-out\\V-REVIEW\\halo`.
"""
os.makedirs(os.path.dirname(DOC), exist_ok=True)
with io.open(DOC, "w", encoding="utf-8", newline="\n") as f:
    f.write(T)
print("wrote", DOC, len(T), "chars")
