# BUILD-HULL — is the merge non-convex?

**Agent:** BUILD-HULL. **Subject:** `docs/research/V-veiling.md` §5, the -805 DN
"unexplained residual", and the claim that it is larger than a convex merge can produce.
**Standing:** I did not write the merge and I did not write `V-veiling`. I built every
instrument in this report from scratch and did not open `V-veiling/r7_hull.py` or
`vv_core.py` until my own numbers on both stacks were final.
**Pin:** `C:\dev\strehl-out\pin-859edac\target\release\strehl.exe`,
sha256 `DF209CE0...F97DC70F`, verified before first use. All measurement on linear
16-bit TIFF. Nothing measured on an sRGB or JPEG render.
**Instruments:** `C:\dev\strehl-out\BUILD-HULL\` — `hull.py` (the out-of-hull
instrument), `rim.py` and `rimsens.py` (the election-record instrument of §12),
`exchange.py`, `residual.py`, `arms.py`, `strehlrun.py`, `commission_gate0.py`,
`probe13.py`, `halodiff2.py`. No file under `crates/` was edited or read for its logic
before the numbers were final.

## Verdict

| # | Question | Verdict |
|---|---|---|
| 1 | Does the merge produce values outside the hull of its inputs? | **NO.** 0 of 24,752,640 channel-samples on `flower-bud-alone-cpl` (205 frames); 0 of 24,724,512 on `109MSDCF` (22 frames). Registration held to the identity on both sides |
| 2 | Is the -805 DN residual evidence of non-convexity? | **NO.** Measured: subtracting 805 DN from the merged output in the very band it was measured leaves **93.2%** of those pixels still inside their own hull |
| 3 | Is any stage non-convex? | **YES — two, both named, both band-mean-neutral.** The MHC demosaic (measured, 0.171% of samples, net **-0.026 DN**) and the Catmull-Rom warp gather (arithmetic: two of four taps are negative) |
| 4 | Which outcome is this? | **Outcome 2** — the merge is convex and the -805 DN comparison was not apples-to-apples. §7 gives the three independent reasons |
| 5 | Scope limit | The **ALIGN=0** pipeline. The shipped *aligned* merge cannot be measured per-pixel by any route available from outside `crates/`. §4 proves why, rather than asserting it |
| 6 | Is the artifact real anyway? | **YES, and it is large.** §12. Against V-RIM's ground-truth frame the merge is **-4232.9 DN** at `d = 30-60 px`. The hull test reads **0** on that row. Convexity was the wrong invariant, not merely a satisfied one |
| 7 | Does ORCH's election mechanism hold? | **CONFIRMED from the election record.** At `d = 60-120 px`, **93.81%** of pixels elect a frame in which that pixel is covered by defocused subject, and the median elected frame is **6** — 104 frames from the in-focus silhouette |

This report is a **correction of V-veiling and of the brief that commissioned me**, and
I want to be exact about what it does and does not overturn. It does not touch
V-veiling's claim 1: the halo is real and it is worse than its inputs look. It refutes
only the arithmetic sub-claim that the excess is *larger than convexity permits*. That
sub-claim rested on a test that is not a hull test.

> **Amendment, added after V-RIM's frame-level measurement.** §12 is the most
> important section of this report and it partly corrects §11. The artifact is real,
> it is about **-4233 DN** against a measured ground truth, and **the hull invariant I
> proposed in §11 is blind to it.** The merge elects frames in which the pixel is not
> backdrop at all, so the offending value is inside the hull *by construction*. A
> convexity assertion would have passed this bug silently, and shipping it alone would
> have been worse than useless because it would have looked like a guarantee. §12.6
> gives the invariant that does catch it.

---

## 1. What convexity actually bounds — the arithmetic

The brief's argument is correct and I want to restate it precisely, because the whole
question turns on a quantifier.

An elect-then-average merge forms, at each output pixel `p`, a weighted mean
`merge(p) = sum_k w_k(p) x_k(p)` with `w_k(p) >= 0` and `sum_k w_k(p) = 1`. Therefore,
**pointwise**:

```
min_k x_k(p)  <=  merge(p)  <=  max_k x_k(p)          (TRUE, at every p)
```

Average that over a band `B` of pixels and you get the correct band-level consequence:

```
mean_B(merge)  >=  mean_B( min_k x_k )                 (TRUE)
```

The statement that was actually tested, and the one that fails, is a different one:

```
mean_B(merge)  >=  min_k mean_B( x_k )                 (NOT IMPLIED)
```

These differ because the minimum and the mean do not commute. In general

```
mean_B( min_k x_k )  <=  min_k mean_B( x_k )
```

and the gap between them — call it the **exchange term** — is strictly positive
whenever different pixels in `B` attain their minimum on different frames `k`. That is
precisely what a per-pixel selector arranges. The merge is *free*, while remaining
convex at every single pixel, to sit below every individual frame's band mean. It has
that freedom exactly to the extent that the winning frame varies across the band.

**This also explains why V-veiling's control came back clean and why it was not a
control for this mechanism.** An honest 7-frame *mean* was measured and read inside the
envelope of its inputs with 50 DN of bias. It had to. A uniform average uses the same
weights at every pixel, which collapses the exchange term to zero by construction. A
flat mean cannot exhibit the effect, so finding that it does not exhibit the effect
rules nothing out. The control was well-intentioned and structurally incapable of
firing.

*(Labelled: this section is **argued**. Everything below is **measured** unless it
says otherwise.)*

---

## 2. The instrument (Deliverable 1)

`C:\dev\strehl-out\BUILD-HULL\hull.py`. Pure Python, no changes to the Rust tree.

For each output pixel `p` and channel `c` it folds all `N` co-registered per-frame
renders into a streaming per-pixel `lo = min_k x_k(p,c)` and `hi = max_k x_k(p,c)`
(three planes of peak memory, not `N`), then partitions **every channel-sample** into
exactly one of three counted outcomes:

```
inside hull  +  BELOW hull  +  ABOVE hull  =  total channel-samples
```

and prints that the three sum to the total. It reports the signed violation magnitude
distribution in DN separately for each direction, writes a spatial map
(`viol-<tag>.png`, red above / blue below / green tint subject, plus the raw signed
`.npy`), and partitions violations by distance from the subject silhouette using the
same band edges as `V-veiling.md` so the tables can be laid side by side. The radial
table also prints an explicit **unbanded gap** count, so pixels that fall in no band are
counted rather than silently dropped:

```
radial bands + subject + gaps = 8221181 of 8250880; unbanded gap = 29699
```

Silhouette masking follows V-veiling's convention (low-luma threshold on normalised
luminance, largest connected component, holes filled, Euclidean distance outside).
One deliberate difference, stated for comparability: my `luma()` uses Rec.709 weights on
camera-native primaries where V-veiling used a plain mean of RGB. Both are monotone
binning devices, neither is colorimetry, and §6 shows the verdict does not depend on it
because the per-channel test is run independently of the luma test and agrees.

---

## 3. Getting co-registered samples — **route (a), achieved exactly**

The brief asked me to state plainly which of three routes I took. **I took route (a):
I emit genuinely co-registered per-frame samples.** There is no bound and no argument
in my hull, because there is no mis-registration in it.

**The mechanism.** `STREHL_ALIGN=0` sets the registration to the identity. I set it on
*both* sides — the merge and every one of the `STREHL_ONLY_FRAME=k` per-frame renders.
When the warp is the identity for everybody, the merge and the per-frame renders land on
the same canvas at the same pixel coordinates by construction. There is no sidecar to
be rejected, no reference frame to be re-solved, and no drift to bound.

**Why the obvious route is closed.** I checked before adopting the alternative.
`only_frame()` in `merge_cmd.rs` (~line 1431) returns a **1-element** path list, and
`alignment_for()` (~line 1939) requires both `map.check_stack(&identity)` and
`map.len() == paths.len()`. A 205-frame sidecar therefore cannot be attached to a
1-frame render: `STREHL_WARPMAP` + `STREHL_ONLY_FRAME` is closed by code, not by
policy. Hand-authoring a 1-frame warpmap is mechanically possible (warpmaps are plain
text and `StackIdentity::from_paths` digests filename and file size only, never
contents — `warpmap.rs:238`) but does not help: a 1-frame map lands on a *different
output canvas*, because aligned renders crop the valid rectangle by roughly 7-10%.
That route does not close either.

**Why routes (b) and (c) fail here, with numbers.** Route (c) — restrict to regions
where registration cannot matter — is not available in the band under investigation.
V-veiling measured **227 px** of silhouette-radius drift across the bracket, and the
veiling gradient in that region changes by roughly 1000 DN over 100 px. A mask
transferred across that drift moved one of V-veiling's own measurements by a factor of
**4.2**. There is no sub-region of the 120-200 px band where a 227 px drift is provably
negligible. Route (b) — bound the widening — would require a bound tighter than the
805 DN effect on a hull whose width I measure at 4037.5 DN in that band; the bound
would have to be better than 20% of the hull, which a 227 px drift across a 1000 DN
gradient cannot supply.

**The cost of route (a), stated plainly.** This measures the **ALIGN=0** pipeline. It
is the real merge, the real election, the real gate, the real code path — but with the
warp held to the identity. It is therefore *not* the shipped aligned pipeline, and
§9 states exactly what that leaves unmeasured. I judged an exactly co-registered
measurement of a slightly different pipeline to be worth more than a mis-registered
measurement of the right one, and I am flagging the choice rather than burying it.

**Validation that the identity really is an identity.** `commission_gate0.py` renders
the merge at `--gate 0` (pure selection: the output must be a *copy* of some input
sample) and checks it against the per-frame renders:

| stack | pixels | bit-exact | differing | uncovered |
|---|---|---|---|---|
| `109MSDCF` | 8,241,504 | 8,241,491 | 13 | 0 |
| `flower-bud-alone-cpl` | 8,250,880 | 8,250,849 | 31 | 0 |

The handful of exceptions are not registration error. `probe13.py` prints the full
value stack at every one: they are **exact election ties**. At `--gate 0` the tolerance
is `<= 0`, so every frame whose regularised response exactly equals the winner's is
admitted and averaged. Of the 93 channel-disagreements on flower-bud, **0 are outside
the all-frame hull and 93 are inside it**. Same on 109MSDCF. The identity holds to
99.99962% bit-exactness and the residue is explained, not waved at.

---

## 4. Commissioning the instrument — **before** trusting a zero

A detector that reports zero violations is indistinguishable from a detector that is
not looking. Every zero in §5 is backed by the following, all on the real pipeline.

**Planted defects.** `hull.py --plant` (rectangle) and `--plant-band` (radial band)
inject a known offset into the merged output *after* the pristine silhouette is
derived, then check hit rate, spill, and signed magnitude:

| stack | plant | planted px | detected | spill outside plant | worst DN seen |
|---|---|---|---|---|---|
| `flower-bud-alone-cpl` | **-5000 DN**, band 120-200 | 513,618 | **513,618 (100.000%)** | **0** | -5000 |
| `flower-bud-alone-cpl` | **-805 DN**, band 120-200 | 513,618 | 35,092 (6.832%) | **0** | -805 |
| `109MSDCF` | -805 DN, band 120-200 | 610,350 | 604,756 (99.083%) | **0** | -805 |
| `109MSDCF` | +400 DN, rect | — | 87.592% | **0** | +400 |

The -5000 DN row is the potency proof on the primary subject: **every planted
channel-sample detected, at its own location, with the right sign and the exact right
magnitude, and not one false positive anywhere else in the frame.** The instrument is
looking, on `flower-bud-alone-cpl`, at 205 frames. The 6.832% in the second row is
therefore not a weakness of the detector — it is the measurement, and it is the
headline result of this report. See §6.

**Real-pipeline positive controls**, which are worth more than plants because they
exercise code rather than my arithmetic:

| arm | stack | outcome |
|---|---|---|
| `STREHL_PHOTOMETRIC=on` | `109MSDCF` | **FIRED — 70,071 of 24,724,512 (0.2834%) out of hull.** Frames are scaled before merging, so the merge is convex in the scaled samples and not in the raw ones. Exactly the signature a real non-convexity produces |
| `STREHL_PHOTOMETRIC=on` | `flower-bud-alone-cpl` | **Refused to render**, rc=1: `U3 the eroded low-detail region keeps only 557 px (minimum 1024)`. A legitimate refusal on this scene, not a crash. The control is unavailable here and I am not counting it |
| `STREHL_FIX_HALO=1` | `109MSDCF` | **INERT — byte-identical output** (`EC06BECB...`) to the base merge while printing `halo fix : ON`. Not a missed detection. See §10 |
| `STREHL_FIX_HALO=1` | `flower-bud-alone-cpl` | **Potent as an edit, convex as a result.** Different sha256 (`571C2476...` vs `B5AEBF0E...`), 816,065 channel-samples changed (3.297%), excursions to **-13,101 / +13,111 DN** — and still 0 out of hull |

That last row deserves its own table, because "it changed the image by 13,000 DN and
your detector said zero" is the sort of thing that should be checked rather than
excused. `halodiff2.py`:

| band | pixels | median &#124;dLuma&#124; | max &#124;dLuma&#124; | hull width | max / width |
|---|---|---|---|---|---|
| 4-12 | 58,432 | 5301.4 | 12242.1 | 11436.8 | 1.070 |
| 12-30 | 121,186 | 2178.2 | 11669.7 | 10881.7 | 1.072 |
| 30-60 | 191,893 | 0.0 | 8874.7 | 9243.1 | 0.960 |
| 60-120 | 380,484 | **0.0** | **0.0** | 6236.4 | 0.000 |
| **120-200** | 513,618 | **0.0** | **0.0** | 4037.5 | 0.000 |
| 200-300 | 661,260 | 0.0 | 0.0 | 3779.3 | 0.000 |
| 300-420 | 724,247 | 0.0 | 0.0 | 3853.1 | 0.000 |

The halo fix is a large edit **confined to the rim** (`d < 60 px`), where the hull is
9,000-11,000 DN wide and easily absorbs it. In the band under investigation it changes
**exactly zero pixels**. Two consequences: the zero is explained, and the halo fix is
not a candidate explanation for a `d = 120-200` artifact.

---

## 5. Result: the merge is convex (Deliverable 1)

**`flower-bud-alone-cpl`, 205 frames, ALIGN=0, gate 4, binned plane 3520x2344.**

```
channel-samples total        : 24752640
inside hull                  : 24752640   (100.000000%)
BELOW hull (merge < min_k)   : 0   (0.000000%)
ABOVE hull (merge > max_k)   : 0   (0.000000%)
partition sums to            : 24752640  (must equal 24752640)
PIXELS with any channel out  : 0 of 8250880 (0.000000%)
```

By radial band, in absolute linear DN — the merge and the two hull surfaces:

| band | pixels | below | above | merge luma | mean min_k | mean max_k | in hull? |
|---|---|---|---|---|---|---|---|
| 4-12 | 58,432 | 0 | 0 | 15531.0 | 7418.5 | 18807.5 | YES |
| 12-30 | 121,186 | 0 | 0 | 14999.5 | 8768.5 | 19593.3 | YES |
| 30-60 | 191,893 | 0 | 0 | 14575.0 | 11136.7 | 20334.5 | YES |
| 60-120 | 380,484 | 0 | 0 | 15907.9 | 14528.4 | 20725.7 | YES |
| **120-200** | 513,618 | **0** | **0** | **18590.7** | **16831.3** | **20811.0** | YES |
| 200-300 | 661,260 | 0 | 0 | 19007.9 | 17168.6 | 20879.8 | YES |
| 300-420 | 724,247 | 0 | 0 | 19270.5 | 17392.7 | 21178.6 | YES |
| 420+ | 3,778,949 | 0 | 0 | 18885.7 | 17058.0 | 20735.3 | YES |

Also 0 of 24,752,640 at `--gate 0`, and 0 of 24,752,640 at `--gate 8`.
`109MSDCF` likewise: 0 of 24,724,512.

**The merge is convex. There is no violating pixel to find, and the instrument that
says so has been shown to find a planted one at a 100% rate on this exact stack.**

---

## 6. The decisive measurement: 805 DN is *comfortably* inside the hull

This is the single number that settles the question, and it is a direct experiment
rather than an inference.

Take the real merged output. Subtract **805 DN** — the exact disputed residual — from
every pixel in the exact band it was measured in, `d = 120-200 px`. Ask the instrument
how many of those pixels are now outside the hull of their own inputs.

```
planted pixels                 : 513618
planted AND detected           : 35092  (6.832% of the plant)
detected OUTSIDE the plant     : 0
```

**93.168% of them are still inside.** The hull in that band is **4037.5 DN** wide and
the merge sits **1706.8 DN** above its own convex floor. An 805 DN downward excursion
consumes 47% of the available headroom and leaves the output convex at fifteen pixels
out of every sixteen.

So the premise "a convex merge cannot be 805 DN below its inputs there" is false as
stated, and it is false by a wide margin rather than marginally. The `residual.py`
decomposition puts the same fact in V-veiling's own units — veiling relative to each
image's own far field:

| band | MERGE | most veiled of 205 | **true convex floor** |
|---|---|---|---|
| 4-12 | -3355 | -9626 | **-11450** |
| 12-30 | -3886 | -8287 | **-10102** |
| 30-60 | -4311 | -5939 | **-7735** |
| 60-120 | -2978 | -2574 | **-4333** |
| **120-200** | **-295** | **-254** | **-2002** |
| 200-300 | +122 | +110 | **-1652** |
| 300-420 | +385 | +335 | **-1428** |

Read the `120-200` row across. Against the most veiled single frame the merge is 41 DN
worse, which is the *shape* of V-veiling's finding. Against the floor that convexity
actually imposes it has **1707 DN of room to spare**. The two columns differ by an order
of magnitude, and the published test used the first one.

*(Both statistics agree. `residual.py --stat median`, which matches `vv_core.profile()`'s
default exactly, gives -439 / -409 / -2187 for the same row: same conclusion, 1748.6 DN
of headroom.)*

**A worked example where the published test fires on a provably convex merge.** On
`109MSDCF` I do not have to argue the mechanism, because it occurs:

| band | MERGE | min_k mean_B (the published floor) | mean_B min_k (the convex floor) | A: vs frame | B: vs hull | exchange |
|---|---|---|---|---|---|---|
| 12-30 | 7035.1 | 7065.1 | 6780.5 | **-29.9** | **+254.7** | 284.6 |
| 30-60 | 6953.0 | 6975.5 | 6660.5 | **-22.4** | **+292.5** | 314.9 |

Column A is negative: by the published comparison this merge is "impossible", sitting
below the darkest single frame's band mean. Column B is positive by 255-292 DN: it is
inside the hull at every pixel. And the per-pixel test on that same render reports **0
of 8,241,504 pixels** outside `[min_k, max_k]`. **The signature and the innocence
coexist in one real render.** That is an existence proof, not a model.

---

## 7. Why the published test read otherwise

I opened `C:\dev\strehl-out\V-veiling\r7_hull.py` only after the above was final. Its
section titled `"convex-hull test"` computes

```python
lo, hi = fr[:, i].min(), fr[:, i].max()
```

where `fr` is a **7 x 8 array of per-band statistics**, not pixels. There are three
independent reasons this cannot decide convexity, and each is sufficient on its own:

1. **It is a min over band statistics, not over pixels.** `lo` is
   `min_k median_B(x_k)`, which is the quantity §1 shows is not bounded by convexity.
   This is the min/median exchange, and §6 measures it firing on a convex merge.
2. **It uses 7 of 205 frames.** The supporting argument — the 7-frame profile is smooth
   and U-shaped, so no unsampled frame can be more veiled than -1528 DN — is sound for a
   *frame-level* profile and irrelevant to a *pointwise* minimum. The pointwise minimum
   over 205 frames is not the profile minimum over 7; it is a per-pixel infimum that no
   smoothness argument about frame-level means constrains.
3. **The bands are not the same pixel set.** `vv_core.subject_mask()` thresholds at
   `frac * median` of **each image's own** luminance and gives each image **its own**
   distance map — deliberately and correctly, since the frames are not co-registered.
   But that means the merge's band `B` and frame `k`'s band `B` are different sets of
   pixels. A statistic over one compared to a statistic over another is a comparison of
   two populations, not a containment test.

Reason 3 is a consequence of the very confound V-veiling correctly identified and
correctly worked around for claim 1. The workaround is right for measuring a profile and
fatal for testing a hull. **A hull test requires co-registration; that is why §3 is the
longest section of this report.**

---

## 8. The bisect: which stages *are* non-convex (Deliverable 2)

Ten arms on `109MSDCF`, each a real render with a real knob turned, hull-tested against
per-frame renders made with the *same* knob. Not code reading.

| arm | channel-samples | BELOW | ABOVE | % out | what it varies |
|---|---|---|---|---|---|
| base-gate4 | 24,724,512 | 0 | 0 | 0.0000% | shipped value path |
| gate0-selection | 24,724,512 | 0 | 0 | 0.0000% | pure selection |
| gate8 | 24,724,512 | 0 | 0 | 0.0000% | more frames averaged |
| edge-aware-off | 24,724,512 | 0 | 0 | 0.0000% | `STREHL_EDGE_AWARE=0` |
| window-radius-1 | 24,724,512 | 0 | 0 | 0.0000% | `STREHL_WINDOW_RADIUS=1` |
| soft-gate-gaussian | 24,724,512 | 0 | 0 | 0.0000% | `STREHL_SOFT_GATE=gaussian` |
| robust-election | 24,724,512 | 0 | 0 | 0.0000% | `STREHL_ROBUST_ELECTION=on` |
| **demosaic** | 98,898,048 | 108,262 | 60,868 | **0.1710%** | `--demosaic`, full-res MHC |
| **POSCTL-photometric** | 24,724,512 | 30,305 | 39,766 | **0.2834%** | positive control, fired |
| POSCTL-fix-halo | 24,724,512 | 0 | 0 | 0.0000% | inert on this stack (§4) |

**The election path is convex under every variation I can reach.** The brief's leading
hypothesis was `regularise_guided` — a guided filter is a local linear model `a*I + b`
and a linear model extrapolates. The hypothesis is sound in general and **not the
answer here**: `window-radius-1` and `edge-aware-off` produce radically different
elections and both give exactly 0 violations. The reason is structural and worth
recording: `regularise_guided` (`merge.rs:301`) takes `focus: &[f32]` and writes a
*focus field*. It re-routes **which** frame wins. It never touches a sample value, so
its extrapolation cannot leave the hull of the samples. The brief's specific worry —
that regularisation might emit fractional or out-of-range frame indices later used to
interpolate samples — would break convexity if it happened, and §11 proposes the
assertion that would catch it if it ever starts happening.

**Demosaic is genuinely non-convex, and cannot be the -805 DN.** Malvar-He-Cutler is
gradient-corrected: it adds a fraction of the Laplacian of a *known* channel, and that
kernel has negative lobes. Measured: 0.171% of channel-samples out of hull, worst
**-1150 / +2074 DN**. But it is **bidirectional and band-mean-neutral**:

```
108262 x (-38.483)  +  60868 x (+26.424)  =  -2.56e6 DN over 98,898,048 samples
                                          =  -0.026 DN
```

Every band mean stays inside the hull. Local kernel ringing at edges averages out at
band scale to **26 thousandths of a DN**. It cannot supply 805 DN of band-mean bias, and
it is short by a factor of about 31,000.

This matters more than it looks, because **V-veiling measured on full-resolution
demosaiced renders** — the 198 MB `vf*-lin.tif` files — which is the same path. The two
investigations converge on the same non-convex stage. The convergence is real; the
magnitude is not remotely sufficient.

**Not common-mode.** The brief warned that demosaic might be common-mode with the
single-frame renders and therefore not the answer. I checked rather than assumed: the
per-frame renders in that arm were also `--demosaic`, so the demosaic non-convexity is
present on *both* sides of the comparison and the 0.171% is what survives after it
cancels. It is a real residue, not an artifact of comparing a demosaiced merge against
non-demosaiced frames.

**A third non-convex stage, reachable by arithmetic but not by my instrument.** The
shipped default resampler is Catmull-Rom (`align_cmd.rs:59`,
`DEFAULT_RESAMPLER_NAME = "catmull-rom"`), a cubic with `a = -1/2`. Its weights
(`align.rs:2664`) are, for phase `f` in `[0,1)`:

```
w0 = -0.5f^3 +      f^2 - 0.5f  =  -0.5 f (f-1)^2   <= 0
w1 =  1.5f^3 -  2.5 f^2 + 1
w2 = -1.5f^3 +  2.0 f^2 + 0.5f
w3 =  0.5f^3 -  0.5 f^2         =   0.5 f^2 (f-1)   <= 0
```

Two of the four taps are non-positive on the whole phase range, so the gather is **not a
convex combination** and can overshoot: `m95-kernel.rs` already reports a peak-overshoot
figure for the Lanczos-3 variant of the same machinery. But the four weights sum to
**exactly 1** (the `f^3`, `f^2` and `f` coefficients cancel: `-0.5+1.5-1.5+0.5 = 0`,
`1-2.5+2-0.5 = 0`, `-0.5+0+0.5+0 = 0`), so the kernel is exact on constants and its
error is proportional to local curvature. *(Labelled: this paragraph is **argued** from
the shipped coefficients, not measured — my instrument runs at ALIGN=0, where this
kernel is bypassed.)* Like demosaic it should be edge-local and DC-neutral in a flat far
field, and for the same reason; unlike demosaic I have not measured that, and §9 lists
it as the principal open item.

---

## 9. What I did **not** measure

Stated separately so it cannot be read as covered.

1. **The shipped aligned merge, per-pixel.** Everything above holds the warp to the
   identity. §3 proves the aligned pipeline cannot be sampled per-frame in a
   co-registered way from outside `crates/`. What I have shown is that **the merge
   arithmetic is convex**, and that **the evidence offered for non-convexity does not
   establish it**. I have *not* shown that the full RAW-to-TIFF aligned pipeline is
   convex — and §8 gives a concrete reason to expect it is not, in the Catmull-Rom
   gather.
2. **The magnitude of the Catmull-Rom gather's out-of-hull excursion on a real bracket.**
   Argued to be DC-neutral, not measured. This is the one number that would close the
   remaining gap, and it needs a hook inside `crates/` that dumps warped samples — which
   I was instructed not to add.
3. **The demosaic arm on `flower-bud-alone-cpl`.** Measured on `109MSDCF` only. It needs
   205 full-resolution per-frame renders at ~198 MB each (~40 GB) and I judged the cost
   not worth it given that the effect is a factor of 31,000 short of mattering. **I am
   flagging this as a skip, not a pass.** If the -0.026 DN neutrality is ever load-
   bearing for a decision, re-run it on the real subject before relying on it.
4. **`STREHL_PHOTOMETRIC` as a positive control on `flower-bud-alone-cpl`.** It refuses
   to render on this scene (557 px of eroded low-detail region against a 1024 px
   minimum). The plants in §4 carry the commissioning burden on that stack instead, and
   the -5000 DN plant carries it at 100%.

---

## 10. Incidental findings

**`STREHL_FIX_HALO=1` is a byte-identical no-op on `109MSDCF` while announcing itself as
on.** The render printed `halo fix : ON (STREHL_FIX_HALO=1)` and wrote a file with the
same sha256 (`EC06BECB...`) as the base merge. `scripts/check-defaults.py` records a
weaker version of this (`'=1' without --out`); this instance had `--out` and still did
nothing. On `flower-bud-alone-cpl` the same flag changes 816,065 channel-samples, so it
is not universally inert — the null on `109MSDCF` is plausibly legitimate for a flat
subject with no depth separation and therefore no halo to fix. Recorded so that whoever
owns that flag can decide whether a silent no-op should announce itself as `ON`.

**`--index-map` and `--n-eff-map` together did not reproduce the `0xC0000409`
stack-buffer-overrun.** I ran them together on both stacks, including the full 205-frame
`flower-bud-alone-cpl` render, and all expected TIFFs were written at the expected
sizes. Not reproduced; not refuted either, since it was reported as intermittent.

**At `--gate 0` the merge is not strictly pure selection.** The tolerance test is
`<= 0`, so exact ties admit multiple frames and average them. This is why 13 pixels on
`109MSDCF` and 31 on `flower-bud-alone-cpl` are not bit-exact copies of any input. All
are inside the hull; it is a curiosity, not a defect.

---

## 11. Proposed permanent invariant (Deliverable 3)

**Proposal only. I have not implemented this, because `crates/` is contested.** It is
specified below tightly enough to apply in one sitting.

> **Read §12.6 before applying this.** This invariant is necessary and **not
> sufficient**. It reads zero on the -4233 DN artifact that ORCH and V-RIM are
> actually chasing, because that artifact is inside the hull by construction. Ship it
> only together with §12.6's backdrop-deficit detector, or with a doc comment that
> states in terms what it does not cover. A convexity check that passes is easily
> misread as a guarantee of correctness, and here it is not one.

**The invariant.** *The merge shall not produce a value outside the hull of the samples
it elected at that pixel, except at named stages where non-convexity is intended and
documented.*

**Where it belongs.** In `crates/strehl-core/src/merge.rs`, at the end of pass two, on
the accumulator output — **before** demosaic and before any post-merge stage. That is
the last point at which the output is, by design, a pure convex combination.

**What it must be over: the *elected* samples, not all N.** This is the important design
point. Checking against `min/max` over all `N` frames is the weaker test and is nearly
useless as a guard: it would not catch a bug in the election indexing, because an
out-of-range or fractional frame index still yields a value inside the all-frame hull.
Accumulating `lo`/`hi` over exactly the samples that received non-zero weight makes the
assertion catch precisely the failure mode the brief was worried about — a regularised
field emitting a frame index that is then used to index or interpolate samples. Concretely,
alongside the existing weighted sum, accumulate for each output pixel and channel:

```
lo = min over {k : w_k > 0} of x_k      hi = max over {k : w_k > 0} of x_k
assert(lo - TOL <= out && out <= hi + TOL)
```

**Tolerance: 1 DN in the u16 output domain.** Justified, not guessed. The merge
accumulates in `f32` and writes `u16`, so the only legitimate excursion is float rounding
on a weighted mean of at most `N` samples plus the round-to-`u16`. The measured excursion
at zero tolerance is **exactly zero** across 24,752,640 + 24,724,512 = 49,477,152
channel-samples on two stacks, and the gate-0 selection identity reproduces bit-exactly
at 8,250,849 of 8,250,880 pixels. 1 DN therefore has margin over everything observed
while remaining **805x smaller than the smallest defect anyone in this investigation
cared about**. A tolerance expressed as a fraction of the hull width would be wrong here:
the hull is 4037 DN wide in the band of interest and 11437 DN wide at the rim, so any
percentage tolerance would be enormous in absolute DN — and absolute DN is the unit in
which the defects show up.

**Cost and gating.** Two extra planes of `f32` accumulator and one comparison per
admitted sample. That is not free on a 205-frame bracket, so it should sit behind
`debug_assert!` plus an opt-in `STREHL_ASSERT_HULL=1` for release builds, registered in
`scripts/check-defaults.py` with the other 23. CI should run it on the small stack, where
it costs seconds.

**Named exemptions, with their measured numbers, in the assertion's doc comment** — so
the exemption is auditable rather than a blanket:

| stage | non-convex because | measured | band-mean effect |
|---|---|---|---|
| MHC demosaic (`demosaic.rs`) | gradient correction adds a Laplacian; negative lobes | 0.171% of samples, -1150 / +2074 DN | **-0.026 DN** |
| Catmull-Rom gather (`align.rs:2688`) | cubic `a = -1/2`; taps `w0, w3 <= 0` | not measured (§9) | argued 0 by partition of unity |

**What the invariant buys.** It converts "the merge is convex" from a claim someone has
to re-derive every time a halo appears, into a property the machine checks. Had it been
in place, the -805 DN residual would have been attributed to the exchange term on the
first day instead of the third, and this report would not have needed writing.

---

## 12. V-RIM's corroboration — the artifact is real, and convexity was the wrong invariant

V-RIM measured the backdrop profile in **individual frames** rather than merges and
found the frames flat where the merge sags. ORCH proposed the mechanism: in a smooth
bright backdrop the focus measure has no real signal, so near a silhouette the
defocused subject spills contrast *into* the backdrop, frames where that pixel is
covered by defocused subject score highest, and the merge elects a frame in which the
pixel is not backdrop at all.

**I can test that directly, because `--index-map` records which frame won at every
pixel.** All of the following is measured on the same ALIGN=0 205-frame render as §5,
so it is directly comparable to the zero in §5 rather than to a different run.

### 12.1 V-RIM's ground truth reproduces on an independent pipeline

V-RIM used the pinned `1cacb61` binary, full resolution, green channel, its own
segmentation. I used pin `859edac`, ALIGN=0, binned, Rec.709 luma. Frame 110's excess
over **its own** far field (18974.5 DN):

| band | 4-12 | 12-30 | 30-60 | **60-120** | 120-200 | 300-420 |
|---|---|---|---|---|---|---|
| excess DN | -3293.8 | -1196.8 | -166.6 | **-1.2** | +59.9 | +381.4 |
| % of far | -17.36% | -6.31% | -0.88% | **-0.01%** | +0.32% | +2.01% |

**The frame is flat to 0.01% from 60 px out.** V-RIM reported -0.22% for this frame;
I measure -0.88% at 30-60 and -0.01% at 60-120 on a different binary, a different
resolution and a different colour channel. That is corroboration, not agreement by
construction. The two dark inner bands are the silhouette edge itself and are expected.

### 12.2 The sag, against two ground truths. Absolute linear DN

| band | pixels | MERGE | frame110 (GT) | all-frame mean | max_k | min_k | vs GT | vs mean | vs max_k |
|---|---|---|---|---|---|---|---|---|---|
| 4-12 | 58,432 | 15531.0 | 15680.7 | 13660.5 | 18807.5 | 7418.5 | -149.7 | **+1870.5** | -3276.5 |
| 12-30 | 121,186 | 14999.5 | 17777.7 | 15560.9 | 19593.3 | 8768.5 | -2778.2 | -561.4 | -4593.9 |
| **30-60** | 191,893 | 14575.0 | 18807.9 | 17288.1 | 20334.5 | 11136.7 | **-4232.9** | -2713.2 | -5759.5 |
| 60-120 | 380,484 | 15907.9 | 18973.3 | 18456.7 | 20725.7 | 14528.4 | -3065.4 | -2548.8 | -4817.8 |
| 120-200 | 513,618 | 18590.7 | 19034.4 | 18882.3 | 20811.0 | 16831.3 | -443.6 | -291.5 | -2220.3 |
| 200-300 | 661,260 | 19007.9 | 19095.9 | 18967.3 | 20879.8 | 17168.6 | -88.0 | +40.7 | -1871.9 |
| 300-420 | 724,247 | 19270.5 | 19355.9 | 19225.6 | 21178.6 | 17392.7 | -85.3 | +44.9 | -1908.1 |

**The sag is confirmed at -4232.9 DN, or -22.3% of far field, at `d = 30-60 px`.**
V-RIM reported -18.94% for this subject. Two independent instruments, same artifact.

**And the `min_k` column is the whole story.** At `d = 30-60` the hull floor is
11136.7 DN. The merge at 14575.0 sits 3438 DN above it. It is inside the hull with
room to spare *while being 4233 DN below the correct value*, because frames exist in
which that pixel is not backdrop. The hull is contaminated by the very frames the
mechanism implicates.

### 12.3 The mechanism, read off the election record

A pixel is called COVERED when the elected frame's value sits more than half the hull
width below the pointwise max — that is, the merge chose a frame that did not see the
backdrop. Every pixel is partitioned and the partition is asserted in code:

| band | pixels | saw backdrop | **COVERED** | % covered | median deficit DN |
|---|---|---|---|---|---|
| 4-12 | 58,432 | 52,317 | 6,115 | 10.47% | 3443.3 |
| 12-30 | 121,186 | 86,813 | 34,373 | 28.36% | 4824.4 |
| 30-60 | 191,893 | 37,520 | 154,373 | **80.45%** | 5656.8 |
| **60-120** | 380,484 | 23,545 | 356,939 | **93.81%** | 5350.1 |
| 120-200 | 513,618 | 213,928 | 299,690 | 58.35% | 2250.9 |
| 200-300 | 661,260 | 372,171 | 289,089 | 43.72% | 1619.0 |

**Commissioned against its own threshold.** Half the hull width is a choice, so it was
swept. The peak at 30-120 px and the ordering across bands survive every column:

| band | frac=0.20 | frac=0.35 | frac=0.50 | frac=0.65 | frac=0.80 |
|---|---|---|---|---|---|
| 4-12 | 64.08% | 41.53% | 10.47% | 2.21% | 0.67% |
| 30-60 | 98.91% | 98.09% | 80.45% | 36.88% | 16.78% |
| **60-120** | 97.48% | 95.71% | 93.81% | 85.46% | **67.18%** |
| 200-300 | 77.50% | 59.75% | 43.72% | 28.61% | 15.03% |

At the most conservative threshold the contaminated band still reads 67.18% against
15.03% in the far field. The conclusion is not a property of the threshold.

### 12.4 A falsifiable prediction of the mechanism, and it holds

If defocus spill is the cause, the contaminated bands must elect frames **far** from
the one in which the silhouette is in focus, because those are the frames whose
subject has blurred wide enough to cover the pixel. If instead the elections clustered
around frame 110, the mechanism would be wrong. Measured:

| band | median elected frame | median &#124;k - 110&#124; | far-field baseline |
|---|---|---|---|
| 4-12 | 107 | 23 | 50 |
| 12-30 | 83 | 32 | 50 |
| 30-60 | 48 | 62 | 50 |
| **60-120** | **6** | **104** | 50 |
| 120-200 | 84 | 68 | 50 |
| 200-300 | 119 | 52 | 50 |
| 300-420 | 122 | 50 | 50 |

At `d = 60-120 px` the median elected frame is **6** — the extreme end of a 205-frame
bracket, 104 frames from the in-focus silhouette, with `p10 = 0` and `p90 = 57`. The
far field elects at a median distance of 50, which is what an unstructured election
over 205 frames gives. **The contaminated band is systematically electing the most
defocused end of the bracket.** The prediction was specific, falsifiable and confirmed.

### 12.5 Sign and spatial location, as asked

ORCH asked for these rather than magnitude alone, and predicted undershoot on the
bright side within about 300 px with a local recovery in the last ~20 px. The detector
this artifact needs is not the hull but the **backdrop deficit excess**:

```
BDE(p) = ( max_k x_k(p) - merge(p) ) - D_far        D_far = the same, far field
```

`D_far = 1849.5 DN` here. That baseline is **not** an error: it is the bias of a
max-over-205 estimator against a noise-averaged merge. The excess over it is.

| band | 4-12 | 12-30 | **30-60** | 60-120 | 120-200 | 200-300 | 300-420 |
|---|---|---|---|---|---|---|---|
| BDE, DN | +1426.9 | +2744.3 | **+3909.9** | +2968.3 | +370.8 | +22.3 | +58.5 |
| % of far | +7.56% | +14.53% | **+20.70%** | +15.72% | +1.96% | +0.12% | +0.31% |

**Sign: undershoot, uniformly — the merge is darker than the backdrop everywhere in
the band. Location: peaks at `d = 30-60 px`, essentially gone by `d = 200 px`
(+0.12% at 200-300).** And the innermost band recovers: +1426.9 DN at 4-12 against
+2744.3 at 12-30. **That is ORCH's predicted local recovery in the last ~20 px, and it
appears in the election record too** — only 10.47% of pixels are COVERED at 4-12,
because right at the silhouette there is a genuine in-focus edge for the focus measure
to lock onto. The artifact lives exactly where there is real spill and no real signal.

The one correction to the prediction: the excursion dies by 200 px, not 300 px.

### 12.6 The invariant that catches this, correcting §11

**§11's hull assertion reads zero on every row of §12.5.** It is still worth having —
it is cheap, it caught the photometric control, and it would catch a fractional frame
index — but on its own it is **actively dangerous**, because a passing convexity check
looks like a guarantee of exactly the property that is failing. If §11 ships, it must
ship with §12.5's detector or with a doc comment saying in terms what it does not
cover.

The second invariant, proposed on the same terms as §11 and equally not implemented:

> **In a region with no genuine focus signal, the merge shall not elect a frame that
> did not see that region.**

Machine-checkable form, needing only the index map and the per-frame samples that
`hull.py` already folds:

```
BDE(p) = (max_k x_k(p) - merge(p)) - D_far   <=   TOL_BDE
```

evaluated over pixels classified as smooth backdrop, with `D_far` computed from the
same render's own far field so the test is self-calibrating and needs no reference
image. **Tolerance: 400 DN**, which is 2.1% of this subject's far field. Justified
from the measurement rather than guessed: the far field itself reads +22.3 and +58.5
DN in the two outermost bands, so the noise floor of the statistic is under 60 DN; the
artifact reads +3909.9 DN. A 400 DN threshold sits about seven times above the noise
floor and about ten times below the defect, which is the widest separation the data
supports. `d = 120-200` reads +370.8 DN and would sit just inside it — correctly, since
that band is where V-veiling's -805 DN was measured and where the artifact is already
fading.

This detector is strictly stronger than the hull test for this class of bug, and it
is the one I would gate CI on.

### 12.7 For BUILD-BLEND: the mean base band helps, and it is not a cure

ORCH asked me to coordinate rather than duplicate. BUILD-BLEND is taking the
low-frequency base band from a noise-gated mean instead of an election, on the grounds
that a mean cannot leave the hull. **That reasoning is correct and insufficient, and
the `all-frame mean` column of §12.2 says why: the contaminating frames are in the mean
too.** Taking the mean's own sag against the same ground truth:

| band | merge sag vs GT | mean sag vs GT | sag removed |
|---|---|---|---|
| **4-12** | **-149.7** | **-2020.2** | **-1249% (the mean is 1870.5 DN WORSE)** |
| 12-30 | -2778.2 | -2216.8 | 20.2% |
| 30-60 | -4232.9 | -1519.8 | 64.1% |
| 60-120 | -3065.4 | -516.6 | 83.1% |
| 120-200 | -443.6 | -152.1 | 65.7% |

**Measured: a mean base band removes 64-83% of the sag at `d = 30-120 px`, which is
where the artifact is worst, and is a real improvement there. It removes only 20% at
`d = 12-30`. And at `d = 4-12` it is a regression of 1870.5 DN**, because right at the
silhouette the election is doing the correct thing — locking onto the genuine in-focus
edge — and a mean smears every defocused-subject frame back in.

So the honest read for BUILD-BLEND: **land it, but check the innermost 12 px.** The
same evidence that vindicates the fix in the mid-band predicts it will darken the rim.
That is a testable prediction and §12.5's BDE detector will measure it in one render.

**This is not the same event as my finding.** The excursion is not a hull violation at
any frequency, so it does not go away merely because a mean cannot leave the hull. It
goes away only to the extent that the mean happens to weight uncontaminated frames more
heavily than the election does, which the table above quantifies band by band.

### 12.8 What this does and does not change

**Unchanged and still measured:** the merge is convex. 0 of 24,752,640 channel-samples
outside their hull. §7's three defects in the published hull test stand. The -805 DN
residual is not evidence of non-convexity, and §6's plant experiment stands.

**Changed:** I framed §11 as the permanent gate this question needed. It is not, on its
own. The artifact ORCH and V-RIM are chasing is real, is roughly five times the -805 DN
that started this, and is **invisible to a convexity check**. Convexity was not merely
satisfied here; it was the wrong question, and I should have noticed that a hull whose
floor is 11136.7 DN in a backdrop band is a hull that cannot constrain anything.

**On ORCH's suspect:** `regularise_guided` remains refuted as the cause (§8 — seven
election-path arms, including two that radically change the election, all read exactly
0). The affine `a*I + b` argument is sound in general, but the stage re-routes *which*
frame wins and never touches a sample value. The mechanism is in **what the focus
measure rewards**, not in the arithmetic that follows it. That is consistent with
everything in §12: the elections are not corrupted values, they are confident
elections of the wrong frame.

**And do not clamp.** ORCH is right, and more strongly than stated: clamping to the
hull would be a no-op here, since every offending pixel is already inside the hull.

## 13. Reproducing this



```
cd C:\dev\strehl-out\BUILD-HULL
python commission_gate0.py flower-bud-alone-cpl      # the identity holds
python probe13.py          flower-bud-alone-cpl      # the residue is ties, in hull
python hull.py     --merged commission-flower-bud-alone-cpl\merge_gate4.tiff \
                   --frames commission-flower-bud-alone-cpl\frames --n 205 \
                   --out outflower --tag flower-gate4-REAL
python hull.py     ... --tag flower-PLANT-5000 --plant-band "120,200,-5000"   # 100.000%
python hull.py     ... --tag flower-PLANT-805  --plant-band "120,200,-805"    # 6.832%
python exchange.py ... --tag flower-gate4-EXCHANGE
python residual.py ... --stat median
python arms.py     109MSDCF

# section 12 -- the election record, the mechanism, and the BDE detector
python rim.py      --subject flower-bud-alone-cpl \
                   --merged commission-flower-bud-alone-cpl\merge_gate4.tiff \
                   --index  commission-flower-bud-alone-cpl\merge_gate4.index.tiff \
                   --frames commission-flower-bud-alone-cpl\frames --n 205 \
                   --out outflower --tag flower-gate4
python rimsens.py                                   # threshold sweep + prediction
```

`strehlrun.py` clears all 25 `STREHL_*` variables before every render and applies only
the requested ones, so no number here depends on the ambient shell of the five other
agents working in this tree. Every render caches to a `.json` sidecar recording its
exact argv, env and wall clock.

## 14. There are two merge backends, and the answer is different for each

Everything in sections 1 through 13 was measured with the pinned binary `859edac`.
That binary **predates the `--merge` flag**. It can only run one of the two merges
this project ships, and it is not the one the artifact lives in. That single fact
reconciles my zero with ORCH's clamping, and it means neither of us was wrong.

`crates/strehl-cli/src/merge_cmd.rs` declares two backends:

- `MergeBackend::Estimator` -- the regularised-winner, noise-gated, elect-then-average
  merge. This is what sections 1 through 13 measured.
- `MergeBackend::Pyramid` -- a Laplacian multi-band merge where **selection happens per
  band and per coefficient, not per pixel**. In the binary used below it is marked
  `(DEFAULT)`.

**MEASURED.** All numbers in this section come from
`C:\dev\strehl-out\VERIFY-WIRE\target-a\release\strehl.exe`, sha256
`6E4B369664F1E75321B669EDAADDDB9DC6B23A444F01DDBF41833C6E70B59419`, mtime
2026-08-25 22:55:34, hash re-verified immediately before these numbers were written
down. Shipped pyramid defaults read from `pyramid.rs:136` and `pyramid.rs:795-809`:
`bands 7`, `gate 2.0`, `exponent 2.0`, `sharpen 1.4`, `base mean`, and
`MAX_EXPONENT 8.0`, giving a per-octave exponent ramp of `2, 3, 4, 5, 8, 8, 8` from
coarsest to finest.

### 14.1 The hull basis transfers, and by how much

A pyramid render decomposes and reconstructs, so it is not obliged to return a
single frame unchanged. I checked rather than assumed. `pyrbasis.py` renders frames
0, 110 and 204 through `--merge pyramid` at `STREHL_ALIGN=0` and compares them to the
estimator-path single-frame renders that section 5 already folded:

| frame | samples | identical | differing | worst abs |
|---|---|---|---|---|
| 0 | 24752640 | 24752636 | 4 | 1 DN |
| 110 | 24752640 | 24752615 | 25 | 1 DN |
| 204 | 24752640 | 24752630 | 10 | 1 DN |

At most 25 samples in 24.7 million, never more than 1 DN. **MEASURED.** So the
existing 205-frame co-registered basis is valid for the pyramid backend provided
violations of 1 DN or less are not attributed. `pyrhull.py` therefore carries a
`GUARD_DN = 1` band and counts guard-band samples as their own outcome rather than
folding them into either verdict.

### 14.2 Commissioning the detector on this backend

A detector that reports zero is indistinguishable from a detector that is not
looking, and a detector that reports 9% is indistinguishable from a detector that is
miscounting. Planted +5000 DN into rows 150:350, columns 150:350 of the baseline
pyramid output -- 40,000 pixels, 120,000 samples, sited inside the `420+ far` band
which reads exactly 0.0000% clean:

| quantity | clean | planted | delta |
|---|---|---|---|
| ABOVE hull, > 1 DN | 216338 | 336338 | **+120000** |
| BELOW hull, > 1 DN | 2229804 | 2229804 | 0 |
| violating pixels in `420+ far` | 0 | 40000 | +40000 |

Exactly the planted sample count, in the right direction, at the right place, with
zero spill into the opposite direction. **MEASURED.** The detector sees what it
claims to see.

### 14.3 The controlled A/B: only `--merge` differs

`109MSDCF`, 22 frames, `STREHL_ALIGN=0`, one binary, one hull basis, one demosaic,
one clip path, one output path. The two arms differ in exactly one CLI token.

| arm | inside hull | guard +-1 DN | BELOW > 1 DN | ABOVE > 1 DN | total | net DN/sample |
|---|---|---|---|---|---|---|
| `--merge estimator` | 24724512 (100.000000%) | 0 | **0** | **0** | 24724512 | 0.000 |
| `--merge pyramid` | 22844310 (92.395393%) | 41174 | **1178284 (4.765651%)** | **660744 (2.672425%)** | 24724512 | **-1.7248** |

Pyramid BELOW: mean -65.49 DN, worst -1304 DN. Pyramid ABOVE: mean +52.24 DN, worst
+1020 DN. **MEASURED.**

This is the whole answer to Deliverable 2. Demosaic, clip, pedestal subtraction, the
camera-to-sRGB matrix, the Catmull-Rom resampler and the 16-bit output quantiser are
byte-identical code in both arms. A stage common to both arms cannot explain a
difference between them. **The non-convex stage is the pyramid merge itself.**

On `flower-bud-alone-cpl`, 205 frames, same conditions, shipped pyramid defaults:

| outcome | samples | fraction |
|---|---|---|
| inside hull (exactly) | 22300944 | 90.095214% |
| below hull, <= 1 DN (guard) | 4323 | 0.017465% |
| above hull, <= 1 DN (guard) | 1231 | 0.004973% |
| **BELOW hull, > 1 DN** | **2229804** | **9.008348%** |
| **ABOVE hull, > 1 DN** | **216338** | **0.874000%** |
| TOTAL | 24752640 | 100.000000% |

BELOW: mean -483.46 DN, p50 -358, p99 -1851, worst **-4362 DN**. ABOVE: mean +462.84
DN, p50 +286, p99 +1857, worst **+2788 DN**. Net signed violation over every sample in
the image: **-39.5067 DN/sample**. **MEASURED.**

The merge is producing pixels up to 4362 DN below every one of the 205 frames it had
to work with, on 9% of the image. This is the arithmetic impossibility the brief went
looking for, and it is real.

### 14.4 Which knob makes it: the band ladder

**MEASURED.** `--pyramid-bands` swept 1 to 7, everything else at shipped defaults,
each rung run through the commissioned detector against the same 205-frame basis.

| rung | inside % | BELOW % | ABOVE % | below n | above n | worst- | worst+ | net DN/px |
|---|---|---|---|---|---|---|---|---|
| bands 1 | 99.9894 | 0.0092 | 0.0011 | 2287 | 267 | -1659 | +221 | **-0.011** |
| bands 2 | 99.8709 | 0.0953 | 0.0315 | 23596 | 7800 | -2860 | +1364 | -0.112 |
| bands 3 | 99.5956 | 0.2700 | 0.1282 | 66820 | 31731 | -3230 | +1568 | -0.365 |
| bands 4 | 99.1222 | 0.6092 | 0.2585 | 150794 | 63980 | -3730 | +1798 | -1.248 |
| bands 5 | 97.3233 | 2.1475 | 0.5126 | 531574 | 126881 | -3877 | +2435 | -5.915 |
| bands 6 | 94.0554 | 5.1118 | 0.8114 | 1265305 | 200831 | -4273 | +2748 | -19.669 |
| bands 7 (**shipped**) | 90.0952 | 9.0083 | 0.8740 | 2229804 | 216338 | -4362 | +2788 | **-39.507** |

`bands 1` is a **structural-zero control**, not just a low rung. With one band there is
no Laplacian detail band to select in: the output is the coarsest residual, and the
coarsest residual is combined by `mean` (`--pyramid-base mean`, the shipped default).
A mean cannot leave the hull. That rung runs through identical demosaic, clip and
output code as every other rung and differs only in whether per-band selection
happens. It reads -0.011 DN/sample against the shipped -39.507, a factor of 3592.

**This overturns ORCH's "52x step on the seventh band alone."** The hull violation
grows **smoothly and monotonically** with band count. Rung-to-rung multipliers on the
BELOW fraction are 10.4x, 2.83x, 2.26x, 3.53x, 2.38x, 1.76x -- and the seventh band
has the **smallest** multiplier of the six. There is no step. **ARGUED, from the
measured ladder:** the 52x step is a property of the clamp counter, not of the
violation. Clamping fires only where a smoothly growing excursion happens to cross
zero, which is a threshold on top of a smooth curve, and a threshold manufactures a
step out of a ramp.

### 14.5 The 2x2: neither the ramp nor the coarse level is the cause

ORCH could not separate "a new coarse level" from "a shifted exponent ramp" from
outside the code. Both knobs exist: `--pyramid-bands` sets the level count, and
`--pyramid-sharpen 1.0` disables the per-octave ramp and restores a single global
exponent. **MEASURED**, flower-bud, 205 frames:

| arm | bands | sharpen | inside % | BELOW % | ABOVE % | net DN/px | vs A |
|---|---|---|---|---|---|---|---|
| A (shipped) | 7 | 1.4 | 90.0952 | 9.0083 | 0.8740 | -39.507 | -- |
| B | 7 | **1.0** | 92.0262 | 7.5174 | 0.4361 | -29.411 | -17% |
| C | **6** | 1.4 | 94.0554 | 5.1118 | 0.8114 | -19.669 | -43% |
| D | **6** | **1.0** | 95.2333 | 4.2965 | 0.4520 | -15.528 | -52% |

**Neither knob eliminates it, and with both turned off the merge still leaves the
hull on 4.3% of samples.** Both are dose amplifiers on one mechanism, not two rival
causes. That is why they did not separate: there was nothing to separate.

**A precision note against my own arm B.** `--pyramid-sharpen 1.0` flattens the
*exponent* across bands. It does **not** make the *weights* band-independent, because
the weights are a normalised function of each band's own energy and the band energies
differ regardless of the exponent. ORCH's exact arithmetic claim -- that
`sum_b convex_k(band_b,k)` need not equal `convex_k(sum_b band_b,k)` -- is therefore
**not directly falsifiable from the CLI**, since no shipped flag makes the weights
band-consistent. Arm B tests the dose, not the mechanism. **ARGUED, not measured.**

### 14.6 The causal test: `hard-max`

`--pyramid-select` changes **only** the per-band selection rule. `soft` is a convex
combination weighted by excess band power; `hard-max` is textbook PMax argmax, which
is the maximally band-varying selection available. Everything downstream is identical
code. If the mechanism is per-band selection, hard-max must be worse. It was
pre-registered as a falsification arm before rendering.

| arm | inside % | BELOW % | ABOVE % | BELOW mean | ABOVE mean | worst- | worst+ | net DN/px |
|---|---|---|---|---|---|---|---|---|
| `soft` (shipped) | 90.0952 | 9.0083 | 0.8740 | -483.46 | +462.84 | -4362 | +2788 | -39.507 |
| `hard-max` | 84.5905 | **13.4335** | **1.9577** | -716.94 | +626.37 | -4992 | +3829 | **-84.048** |

**MEASURED.** 1.49x more below-hull, 2.24x more above-hull, 2.13x the net bias. The
arm passed its pre-registered prediction. Combined with 14.3 and 14.4, per-band
selection is isolated as the cause by three independent routes: removing it entirely
(bands 1) takes the violation to near zero, replacing it with a pixel-wise election
(the estimator) takes it to exactly zero, and making it more aggressive makes the
violation worse in proportion.

### 14.7 Two corrections to the spatial picture

**The white rail is real and the clamp counter cannot see it.** `merge_cmd.rs` states
that `accept.py`'s clip predicate is `np.any(im == 0, axis=2)`, black only. On
flower-bud the pyramid merge puts **216,338 samples ABOVE the hull ceiling**, mean
+462.84 DN, worst +2788 DN; on 109MSDCF, **660,744 samples**, and there the ABOVE
count is more than half the BELOW count. None of these have ever been counted.
**MEASURED.**

**"Darkness is a cliff" is partly the detector.** Binning every pixel on local
luminance x local gradient, both axes measured on the **205-frame mean** so they are
independent of every merge arm and the binning cannot be circular. Cell values are
the percentage of pixels in that cell that leave the hull. Luminance quintile edges
908 / 7237 / 17662 / 18853 / 19846 / 20912 DN; gradient edges 0.0 / 12.3 / 22.0 /
32.1 / 46.3 / 530.1 DN.

| lum quintile | g1 | g2 | g3 | g4 | g5 | row rate | row mean violation |
|---|---|---|---|---|---|---|---|
| q1 (darkest) | 49.969 | 56.830 | 64.278 | 61.629 | 47.445 | **52.434%** | -468.8 DN |
| q2 | 0.011 | 0.019 | 0.046 | 0.187 | **13.735** | 4.542% | +126.2 DN |
| q3 | 0.061 | 0.109 | 0.166 | 0.403 | **4.152** | 0.806% | **+744.7 DN** |
| q4 | 0.331 | 0.414 | 0.487 | 0.712 | **1.668** | 0.710% | +370.1 DN |
| q5 (brightest) | 0.002 | 0.002 | 0.001 | 0.002 | 0.001 | 0.002% | +71.4 DN |

**MEASURED.** Three things follow.

1. ORCH measured "luminance quintiles 2 through 4 read *exactly* 0.000." On a
   level-independent detector those same quintiles read **4.542%, 0.806% and 0.710%**.
   The exact zeros were the visibility threshold of an `im == 0` predicate, not an
   absence of violation.
2. The mean violation in q3 is **+744.7 DN**, larger in magnitude than q1's -468.8 DN.
   Mid-tone excursions are **bigger per event**, merely rarer, and they never reach
   zero so nothing counts them.
3. Within q2, q3 and q4 the rate **rises steeply with gradient** -- q2 goes 0.011% to
   13.735%, a factor of 1250 across the gradient axis. Outside the darkest quintile
   this **is** an edge phenomenon. ORCH's "do not build an edge-gated anything" was
   inferred from a detector blind to everything except black clipping, and on this
   evidence it should be reconsidered rather than treated as settled.

**Where it sits relative to the silhouette.** Radial partition of arm A, summing to
all 8,250,880 pixels:

| band | pixels | violating | rate | mean violation | worst |
|---|---|---|---|---|---|
| subject | 1785047 | 896774 | 50.2381% | -469.6 | -4362 |
| 4-12 | 58550 | 15295 | 26.1230% | +676.9 | +2788 |
| 12-30 | 122193 | 29124 | 23.8344% | +698.8 | +2617 |
| 30-60 | 193917 | 21864 | 11.2749% | +409.0 | +1907 |
| 60-120 | 383920 | 669 | 0.1743% | +79.9 | +371 |
| 120-200 | 516697 | 0 | 0.0000% | 0.0 | 0 |
| 200-300 | 664791 | 0 | 0.0000% | 0.0 | 0 |
| 300-420 | 729323 | 0 | 0.0000% | 0.0 | 0 |
| 420+ far | 3767084 | 0 | 0.0000% | 0.0 | 0 |
| unbanded gap | 29358 | 1512 | 5.1502% | +491.9 | +2674 |

**This is a partial negative for V-RIM's prediction, which ORCH explicitly asked for.**
V-RIM predicted undershoot on the bright side within about 300 px of the silhouette.
**MEASURED:** outside the subject the excursion is confined to within 60 px, it is
**positive** (the backdrop side goes *above* its hull, not below), and from 120 px
outward it is **exactly zero across 5,677,895 pixels**. The negative excursion lives
**inside** the subject, which is the dark side. So the out-of-hull excursion is not the
mechanism behind the far-field veiling measured in section 12; those remain two
separate findings, and section 12's is still the one that explains the backdrop sag.

### 14.8 It survives the mean base band

ORCH asked whether this finding and BUILD-BLEND's are the same event. They are not.
`--pyramid-base mean` is **already the shipped default** in the measured binary, so
every number in this section was produced with a base band that is a mean and
therefore convex by construction. The violations are what remains **after** that fix.
**MEASURED.** Per ORCH's own framing, that makes this independent and important.

### 14.9 Verdict

The brief asked which of three statements is true. The answer is that it depends on
the backend, and that is why the question was hard.

- **`--merge estimator`: outcome 2.** The merge is convex, it was measured convex on
  two stacks at 0 violations in 24,752,640 and 24,724,512 samples, and the -805 DN
  comparison was not apples-to-apples. The flaw is in section 7: `r7_hull.py` built
  its "hull" from a 7x8 array of per-band medians rather than from pixels.
- **`--merge pyramid`: outcome 1.** The merge is genuinely non-convex. The stage is
  the pyramid merge's own per-band coefficient selection, isolated by a
  single-token A/B against the estimator, a monotone seven-rung dose-response in band
  count with a structural-zero control at the bottom, and a pre-registered `hard-max`
  arm that made it worse in the predicted direction and proportion.

**ARGUED.** The reason both were true at once is that the pinned measurement binary
`859edac` cannot express the flag that selects the backend. Every number this project
produced with the pin describes a merge that is not the shipped default.

### 14.10 Revised proposal for the permanent gate (supersedes section 11)

Section 11 proposed a hull assertion. Section 12 showed it was necessary but not
sufficient. Section 14 shows something section 11 got positively wrong: **a hard hull
assertion would fail the shipped default on 9% of samples and could not be merged.**

The honest reading of 14.4 and 14.6 is that **non-convexity is not incidental to the
pyramid merge, it is the mechanism by which it buys acuity.** Per-band selection is
what lets a depth boundary be a transition inside each band rather than a step in the
image, and it is the same property that lets the reconstruction leave the hull. A gate
that forbids it forbids the merge. The defect is not that the merge is non-convex; it
is that its non-convexity is **unbudgeted, undirected and unmeasured**, so nothing
notices when it grows.

So the invariant should be a **budget with a named exception**, exactly as the brief
phrased it. Proposed precisely enough to apply in one sitting:

1. **Where.** Inside the pyramid merge, immediately after band reconstruction and
   **before** the `max(0.0, ·)` clamp at `blend-render.rs:572`. The clamp is
   downstream of the fault and destroys the evidence; measuring after it can only ever
   see the black-only shadow that `accept.py` already sees.
2. **What.** For each output sample, the interval `[min_k x_k, max_k x_k]` over the
   frames that received **non-zero weight in any band** at that pixel. Not over all
   frames -- over the frames actually combined. Report five counted outcomes that sum
   to the sample total: inside, guard-below, guard-above, below, above. A count that
   does not partition can hide a skipped region as a clean one.
3. **Tolerance.** Two numbers, both measured here rather than chosen. The **guard band
   is 1 DN**, the reconstruction round-trip floor from 14.1. The **budget** is a
   fraction-of-samples ceiling and a net-bias ceiling, registered per subject from
   the current shipped defaults so that regressions are visible immediately: on
   `flower-bud-alone-cpl` the current state is 9.0083% below / 0.8740% above /
   -39.5067 DN per sample, and on `109MSDCF` 4.7657% / 2.6724% / -1.7248 DN. The gate
   should fail on an increase, not on a non-zero.
4. **Both directions, always.** The above-hull count must be reported with equal
   standing. It is currently 216,338 samples on flower-bud and 660,744 on 109MSDCF
   and no existing instrument in this project can see any of it.
5. **Do not clamp to the hull.** ORCH is right and 14.7 sharpens why: clamping would
   alter 9% of samples, leave the wrong value at the clamp, and convert a measurable
   excursion into an unmeasurable one.
6. **Commission it before trusting it.** The plant in 14.2 is the pattern: a known
   offset into a region that reads clean, checked for exact recovered count, correct
   sign, correct location and zero spill.

**For whoever owns the fix.** The direction 14.5 and 14.6 point at is making the
selection weights **consistent across bands** -- deriving one per-pixel weight set
from the pooled band evidence and applying it to every band -- which restores
convexity by construction, because a single convex combination applied to all bands
commutes with the reconstruction sum. **ARGUED, not measured.** I did not test it
because no shipped flag expresses it and I am read-only in `crates/`. It is also not
free: it moves the pyramid merge toward the estimator's behaviour, and the estimator
is the arm that loses the acuity. That tradeoff is a real decision and should be made
with a paired cost column, not assumed away.

### 14.11 What section 14 did not measure

- **`couch-fibers-cpl`, the placebo, is not in this section.** It is 299 frames and
  its hull basis had not finished rendering when this was written. **This matters
  more than it looks:** ORCH's constraint that "a proposal that moves couch-fibers is
  wrong" rests on it reading exactly 0 clipped pixels in both arms, and 14.7 shows
  that predicate is blind to above-hull excursions and to any below-hull excursion
  that does not reach zero. Until couch-fibers is hull-tested, **it is unproven that
  it is a placebo at all**, and it should not be used to reject a fix. Render is
  running under `couch.ps1`.
- **`dry-erase-marker-head-cpl` was not measured here**, so ORCH's attribution ladder
  is neither confirmed nor contradicted on its own subject.
- **The weights themselves were never observed.** Everything in 14.4 through 14.6 is
  inferred from output pixels under knob changes. I never read a weight, because
  doing so needs a change in `crates/` and that tree is contested.

### 14.12 Reproducing section 14

```
cd C:\dev\strehl-out\BUILD-HULL
python pyrbasis.py                                   # basis transfers, <= 1 DN
python pyrhull.py fold --frames commission-flower-bud-alone-cpl\frames --n 205
python pyrhull.py test --merged pyr\merge-A-default.tiff --tag A-default
python pyrhull.py test --merged pyr\merge-A-default.tiff --tag PLANT-pos \
                       --plant 5000 --plant-box "150,350,150,350"   # +120000 exactly
powershell -File .\pyr_arms.ps1                      # the 2x2, hard-max, estimator
powershell -File .\pyr_ladder.ps1 ; python pyr_ladder.py             # the dose curve
```

All renders use `STREHL_ALIGN=0` on both the merge and every single-frame render, so
the merge and its hull basis are co-registered by construction -- route (a) of section
3, unchanged.
