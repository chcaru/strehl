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

### 14.11 The placebo is not established

ORCH's standing constraint is that `couch-fibers-cpl` reads exactly 0 clipped pixels,
0 of 33 million, in both arms, therefore it is a placebo and any proposal that moves it
is wrong. That argument requires couch-fibers to be genuinely insensitive to the merge
backend. It is not. **MEASURED**, same binary, `STREHL_ALIGN=0`, shipped defaults, only
`--merge` differing:

| quantity | estimator | pyramid |
|---|---|---|
| samples identical between arms | 21911 (0.0885%) | -- |
| samples differing between arms | **24730729 (99.9115%)** | -- |
| mean level | 8208.6 DN | 8218.1 DN |
| p1 / p50 / p99 | 3032 / 8108 / 13825 | 2838 / 8137 / 13788 |
| min / max | 373 / 40309 | **0** / 46790 |
| `np.any(im == 0)` black pixels | **0** | **268** |
| `np.any(im >= 65535)` white pixels | 0 | 0 |

Signed difference pyramid minus estimator: mean **+9.5689 DN** over every sample, p1
-1631, p50 +22, p99 +1577, worst -18588 and +36592 DN.

Two things follow. **MEASURED:** on this configuration couch-fibers is not insensitive
to the backend at all -- the two arms disagree on 99.91% of samples, and the pyramid
arm reaches black on 268 pixels where the estimator's minimum is 373 DN. **ARGUED:** a
predicate that returns 0 on both arms while the arms differ on 99.91% of samples is
reporting the location of its own threshold, not the behaviour of the merge, and
cannot support an inference of insensitivity.

**A configuration caveat I want on the record rather than buried.** ORCH's count is
"33 million" pixels; mine is 8,250,880, exactly one quarter, which means ORCH measured
a full-resolution demosaiced render and I measured a binned one. That is a real
difference and it is the most likely reconciliation of 0 against 268. I am **not**
claiming ORCH's number was wrong on ORCH's configuration. I am claiming the placebo
status has not been established on mine, and that a subject this sensitive to the
backend should not be used to veto a fix until it has been hull-tested rather than
clip-tested.

### 14.12 What section 14 did not measure

- **The couch-fibers hull test is still pending.** Its 299-frame co-registered basis
  was still rendering when this was written (`couch.ps1`). 14.11 is a merge-versus-merge
  comparison, which needs no hull; the out-of-hull fraction for couch-fibers is
  genuinely unmeasured and is not asserted anywhere above.
- **`dry-erase-marker-head-cpl` was not measured here**, so ORCH's attribution ladder
  is neither confirmed nor contradicted on its own subject.
- **The weights themselves were never observed.** Everything in 14.4 through 14.6 is
  inferred from output pixels under knob changes. I never read a weight, because
  doing so needs a change in `crates/` and that tree is contested.
- **Every number in section 14 is from binned renders**, no `--demosaic`, so that the
  merge output and its hull basis share one geometry. Section 14.11 shows this can
  differ materially from a full-resolution measurement.

### 14.13 Reproducing section 14

```
cd C:\dev\strehl-out\BUILD-HULL
python pyrbasis.py                                   # basis transfers, <= 1 DN
python pyrhull.py fold --frames commission-flower-bud-alone-cpl\frames --n 205
python pyrhull.py test --merged pyr\merge-A-default.tiff --tag A-default
python pyrhull.py test --merged pyr\merge-A-default.tiff --tag PLANT-pos \
                       --plant 5000 --plant-box "150,350,150,350"   # +120000 exactly
powershell -File .\pyr_arms.ps1                      # the 2x2, hard-max, estimator
powershell -File .\pyr_ladder.ps1 ; python pyr_ladder.py             # the dose curve
python couchdiff.py                                  # 14.11, needs no hull
```

All renders use `STREHL_ALIGN=0` on both the merge and every single-frame render, so
the merge and its hull basis are co-registered by construction -- route (a) of section
3, unchanged.

## 15. The aligned, warped hull: the measurement ORCH asked for

Sections 1--14 built the hull from renders made with `STREHL_ALIGN=0`, which co-registers
merge and basis by turning alignment off on both sides. That is defensible but it is not
the shipped configuration. ORCH asked for the hull over the **aligned, warped** frames as
the merge actually sees them, and warned that comparing against unwarped frames would
manufacture violations everywhere and is the main way this instrument could lie.

This section does that. Everything below is **measured** unless a line begins with
*Argued*.

### 15.1 Getting genuinely co-registered warped frames

`alignment_for` (`merge_cmd.rs:2051`) refuses a sidecar unless the stack digest matches
**and** `map.len() == paths.len()`. `STREHL_ONLY_FRAME=k` makes `paths.len() == 1`, so a
205-frame sidecar is refused for both the cache path and the `STREHL_WARPMAP` override.
That is the confound named in the brief, and it is real.

The route around it: the sidecar is a documented text format, and `StackIdentity`
(`warpmap.rs:194`) is FNV-1a 64-bit over `(file name, file size)` per frame.
`warpframes.py` synthesises a **one-frame sidecar carrying frame k's own placement**,
copied verbatim as f64 bit patterns from the real 205-frame solve, with a digest computed
over the one-frame listing. Each frame then renders through strehl's own gather and its
own Catmull-Rom kernel onto the reference grid.

Commissioning of the digest: my Python FNV-1a reproduced the solver's own
`stack-digest 2da87e45b71aed22` exactly. Acceptance is self-commissioning, because
`alignment_for` answers a bad sidecar with a hard error and never silently re-solves
("Refusal instead of recovery", `merge_cmd.rs:2034`).

The merge itself was rendered under the full 205-frame sidecar and logs:

```
alignment : ON (sidecar-override), reference frame 102, 205 placed / 0 refused
```

Merge and frames both come out `2344 x 3520 x 3`, so **the aligned merge does not crop
relative to the basis**. This was an open risk; it is now closed by measurement.

### 15.2 The registration fear in the brief was overstated by ~300x

The brief cited "227 px of silhouette-radius drift" as grounds to distrust any
non-co-registered hull. `strehl align` on this stack reports **total corner drift frame 0
to 204 of 0.715 plane px**, held-out median 0.352 px, cycle floor 0.052 px.

*Argued:* 227 px is defocus blur changing the silhouette's apparent radius, which is a
photometric effect, not geometric registration. A silhouette-radius measurement moves with
blur; the plane does not.

Independently, `coreg.py` measured registration directly by normalised cross-correlation
of high-pass tiles, integer shifts only:

| tile | hp energy | peak dy,dx | ncc | surface median | status |
|---|---|---|---|---|---|
| y362 x1322 | 88.9 | +0,+0 | 0.6214 | -0.0184 | usable |
| y682 x1962 | 82.7 | +0,+0 | 0.5057 | -0.0039 | usable |
| y682 x2122 | 74.7 | +0,+0 | 0.4793 | -0.0055 | usable |
| y362 x1802 | 73.9 | -1,+0 | 0.3636 | 0.0037 | usable |
| y1482 x2442 | 68.2 | +0,+0 | 0.4993 | -0.0031 | usable |
| y202 x1642 | 65.2 | +0,+0 | 0.2431 | 0.0092 | usable |
| y682 x2442 | 64.5 | +0,+0 | 0.1942 | -0.0004 | usable |
| y682 x522 | 63.8 | +0,+0 | 0.1694 | -0.0005 | usable |

Tiles examined 8 = usable 8 + unusable 0. **Seven of eight peaks at exactly (0,0)**,
worst 1 px.

**The first version of this detector was wrong and its control caught it.** Correlating
raw luma gave NCC ~0.98 at every offset with peaks pinned to the search boundary, because
raw luma is dominated by smooth content and because a single frame in a focus bracket is
defocused nearly everywhere. It reported "misregistered by up to 12 px". That number was
never used. The fix was to high-pass both images and to select tiles by the high-pass
energy of the warped frame, i.e. only where that frame is genuinely in focus.

A second bug in the same script: the plant check compared the planted peak to zero
instead of to each tile's own baseline peak, and reported six spurious misses. Corrected,
the planted shift of `dy=+3 dx=-2` is recovered on **8/8 usable tiles**. Sensitivity is
proven, so the registration number is reportable. When sensitivity is not proven the
script exits non-zero and refuses to print a registration number.

This is route **(a)** of the brief's three options: co-registered per-frame samples,
measured rather than asserted.

### 15.3 Why my Laplacian does not need to match the Rust one

This is the load-bearing argument for every per-band number below, so it is stated in
full.

Let `L` be **any** linear operator. Suppose the merge were a single convex combination
with one weight vector `w_k >= 0`, `sum_k w_k = 1`, **shared across all bands**, so
`O = sum_k w_k F_k`. Then by linearity

```
L(O) = L(sum_k w_k F_k) = sum_k w_k L(F_k)
```

which is a convex combination of `{L(F_k)}` and therefore lies inside
`[min_k L(F_k), max_k L(F_k)]` -- necessarily, for every band, every linear `L`, every
pixel.

So a per-band violation under **my** Laplacian proves the merge is not a single convex
combination with weights shared across bands. My decomposition need not match
`pyramid.rs`'s; it need only be linear, and blur, decimate, upsample and subtract all are.
This turns "I cannot read the merge's internal coefficients without editing BUILD-BLEND's
file" from a limitation into an irrelevance.

What the per-band numbers do **not** do: identify which internal Rust band carries the
defect. The claim is about which **octave** the excursion occupies, not about their array
indices.

### 15.4 Commissioning, before any result

**Synthetic, `commission_bands.py`.** Same frames in every arm; only the weighting differs.

| arm | below | above | worst/span |
|---|---:|---:|---:|
| C1 shared weights, fixed | **0** | **0** | 0.000 |
| C5 shared weights, data-dependent | **0** | **0** | 0.000 |
| M independent per-band weights | 5,840 | 5,824 | 6.573 |
| C2 single-frame passthrough | **0** | **0** | 0.000 |
| C3 telescoping `sum(bands) - frame` | max abs error **0.000e+00** | | |

C5 exists because C1 and M alone confound "shared vs independent" with "fixed vs
data-dependent". That is precisely the flaw I reported in ORCH's `hullproof.py` (attack
A2), and my own harness must not carry it. With the cell filled: shared+fixed = 0,
shared+data-dependent = 0, independent+data-dependent = 11,664. **The operative variable
is shared vs independent per-band weighting, not data-dependence.**

**On real data, the null.** `--pyramid-exponent 0` is refused by the CLI ("must be finite
and positive"). The reachable point is exponent `1e-6` with `--pyramid-sharpen 1.0`, which
the merge logs as `exponent : 0.00` and `sharpness ramps 1.0x per octave` -- a flat ramp,
so every band shares one near-uniform weighting. Through the real pipeline, on the real
warped basis, that arm reads **0.0002%** (25 below, 19 above of 24,752,640; worst 0.127
hull spans). It is not exactly zero and is not claimed to be: exponent `1e-6` is not `0`,
and the output is quantised to `uint16`.

**On real data, the plant.** `plantcheck.py` predicts the count from the hull alone,
before consulting the detector:

| quantity | predicted | measured |
|---|---:|---:|
| ABOVE, whole frame | 90,330 | **90,330** |
| of which inside the plant box | 90,311 | -- |
| of which outside the box | 19 (= unplanted baseline) | -- |
| BELOW, unchanged | 25 | **25** |

Exact on all four checks. The plant recovers 90,330 rather than the 120,000 samples
planted because the hull is wide (mean span 4042 DN) and +5000 DN does not clear `hi`
where the merge already sat far below it -- and the headroom accounting confirms that
exactly.

**Hull sanity.** Mean span 4042.0 DN, median 3761.0, min 123, max 18829.
**Degenerate (span == 0) samples: 0 of 24,752,640.** No violation anywhere can be an
artifact of a zero-width interval.

### 15.5 Whole-image result, per channel

205 warped frames, guard +/- 1 DN, arms requested 5 = scored 5 + missing 0.

| arm | region | rate | below | above | worst/span | mean DN |
|---|---|---:|---:|---:|---:|---:|
| **W-pyramid (shipped)** | whole | **10.1590%** | 2,281,305 | 233,317 | 7.051 | **-398.0** |
| W-pyramid | bbox | **24.7028%** | 2,281,305 | 230,871 | 7.051 | -398.7 |
| W-uniform (null) | whole | 0.0002% | 25 | 19 | 0.127 | -2.3 |
| W-e1s1 | whole | 4.2810% | 1,025,929 | 33,721 | 4.560 | -273.6 |
| W-bands1 | whole | 0.0116% | 2,564 | 297 | 0.372 | -91.1 |
| W-estimator | whole | 0.4103% | 73,403 | 28,146 | 0.327 | -13.2 |

Shipped arm per channel, whole frame: R 8.8323%, G 10.5310%, **B 11.1137%**. Worst single
sample -4513 DN. Net over the frame **-1,000,920,704 DN**, i.e. the excursion is a
darkening, which is the direction of the complaint that opened this investigation.

Two things worth stating precisely:

- **Every one of the 2,281,305 below-hull samples lies inside ORCH's bbox.** Whole-frame
  below and bbox below are the same number. Of the above-hull samples, 230,871 of 233,317
  (98.95%) are inside it. ORCH predicted "heavily concentrated inside the bbox";
  measured, the below-hull concentration is total.
- **The estimator is not exactly clean here.** Section 14.3 reported the estimator at
  exactly 100.000000% inside on `109MSDCF`. On this subject with the warped basis it reads
  0.4103%. That earlier claim was measured on a different subject and an unaligned basis
  and should not be generalised. The estimator's excursion is nonetheless ~25x rarer and
  ~30x shallower than the pyramid's, and section 15.7 shows it is a different phenomenon.

### 15.6 Per octave, matched to the merge's own band geometry

My first decomposition held the Laplacian at full resolution. It is linear, so the theorem
applied and the numbers were real -- but seven repeated 5-tap blurs reach an effective
sigma of only ~2.6 px, so its "base" meant "coarser than 2.6 px", **not** the merge's
coarsest octave. Reporting that as a per-band result would have implied a correspondence
with `pyramid.rs`'s levels that did not exist. I discarded it and rebuilt a properly
decimated pyramid matching what the merge logs, `7 Laplacian levels + 1 base, coarsest
28 x 19`:

```
3520x2344 -> 1760x1172 -> 880x586 -> 440x293 -> 220x147 -> 110x74 -> 55x37 -> 28x19
```

Shipped arm, violation rate by octave and channel:

| octave | grid | R | G | B | worst/span |
|---|---|---:|---:|---:|---:|
| detail0 (finest) | 3520x2344 | 0.8102% | 12.1627% | 1.0990% | 1.248 |
| detail1 | 1760x1172 | 0.6212% | 6.9783% | 0.7833% | 1.305 |
| detail2 | 880x586 | 1.5756% | 13.7000% | 1.7303% | 1.479 |
| detail3 | 440x293 | 2.2332% | 19.2616% | 2.3162% | 1.842 |
| detail4 | 220x147 | 5.6463% | 18.7910% | 6.4471% | 3.137 |
| detail5 | 110x74 | 14.9877% | 22.7027% | 16.2408% | 5.443 |
| detail6 | 55x37 | 28.0590% | 32.2359% | 28.4521% | 5.509 |
| **base** | **28x19** | **7.5188%** | **7.8947%** | **9.3985%** | 1.256 |

Rate and relative depth both escalate monotonically toward the coarse octaves. And in the
base octave the violations are **132 below, 0 above** across all three channels -- every
single coarse-scale excursion is a darkening, with no brightening anywhere to balance it.

The same table for the null arm reads `0` below and `0` above in the base octave, and
`0 DN` of violation, exactly.

### 15.7 Footprint-weighted attribution, and the common-mode trap

Raw per-octave DN shares must not be reported alone: detail0 has 8,250,880 samples per
channel and the base has 532, so detail0 dominates any unweighted sum by existing. What
reaches the viewer is the reconstruction, where one base coefficient lands on ~128x128
output pixels. `footprint.py` upsamples each octave's violation field back to full
resolution and subtracts the null arm octave by octave.

The null subtraction matters because **detail0 violates in every arm including the
near-uniform-mean null** (null detail0 = 98.798% of its own tiny total). That is
common-mode -- demosaic and CFA interpolation, not per-band selection. The brief warned
about exactly this trap for demosaic, and it is real: crediting the pyramid for detail0
would have been wrong.

| octave | grid | rate | net DN full-res | null net | excess over null | share |
|---|---|---:|---:|---:|---:|---:|
| detail0 | 3520x2344 | 4.691% | +3,491,521 | +1,252,907 | +2,238,614 | 0.387% |
| detail1 | 1760x1172 | 2.794% | +424,216 | -36,891 | +461,107 | 0.080% |
| detail2 | 880x586 | 5.669% | -1,133,855 | -31,696 | -1,102,159 | 0.191% |
| detail3 | 440x293 | 7.937% | -2,259,931 | -26,475 | -2,233,456 | 0.387% |
| detail4 | 220x147 | 10.295% | -12,375,836 | -19,449 | -12,356,387 | 2.139% |
| detail5 | 110x74 | 17.977% | -39,966,568 | -6,074 | -39,960,494 | 6.917% |
| detail6 | 55x37 | 29.582% | -61,195,388 | -4,232 | -61,191,156 | 10.592% |
| **base** | **28x19** | **8.271%** | **-458,193,248** | **0** | **-458,193,248** | **79.308%** |

Total excess over null, full-res weighted: **577,736,622 DN**.

- detail0, the finest octave and common-mode with the null: **0.387%**
- detail1 through base, the coarser octaves: **99.613%**
- the three coarsest octaves alone (detail5, detail6, base): **96.817%**

For contrast, the estimator's excursion sits at the opposite end of the spectrum:
detail0 54.255%, detail1 23.905%, base **0.001%**. The estimator's violations are a
high-frequency phenomenon, almost certainly its sharpening stage. **The pyramid's are
low-frequency and are a darkening.** These are two different defects and should not be
conflated.

### 15.8 ORCH's registered prediction, scored

ORCH registered, before I ran anything: *"violations concentrated in the three finest
bands, blue worst, and heavily concentrated inside the bbox."*

| claim | verdict | evidence |
|---|---|---|
| concentrated in the three finest bands | **REFUTED** | three finest octaves carry **0.658%** of the null-subtracted excess; three coarsest carry **96.817%** |
| blue worst | **CONFIRMED, whole-image and base octave** | whole frame B 11.1137% > G 10.5310% > R 8.8323%; base octave B 9.3985% > G 7.8947% > R 7.5188% |
| heavily concentrated inside the bbox | **CONFIRMED, and stronger than predicted** | 100% of below-hull samples lie inside the bbox; rate 24.70% inside vs 10.16% whole-frame |

The band localisation is inverted, by roughly 147x. Green is worst in the fine octaves
(consistent with the Bayer CFA sampling green twice, though that is *argued*, not
measured); blue is worst where the magnitude actually lives.

ORCH's earlier "52x step on the seventh band" (section 14.4) remains overturned, and the
"dark flat cliff" (section 14.7) remains falsified.

### 15.9 What this means for BUILD-BLEND's fix

**This is the operationally important paragraph.** The shipped pyramid arm already logs

```
base band : plain mean across frames
```

`--pyramid-base mean` is the default and it is in effect in the 10.1590% arm. So taking
the low-frequency base band from a mean is **already shipped**, and the output's
coarse-scale content is *still* below the hull on 8.27% of base coefficients, carrying
79.3% of the darkening. ORCH's coordination note said that if my excursion turned out to
be entirely low-frequency, my finding and BUILD-BLEND's fix would be the same event. It is
low-frequency, and they are **not** the same event: a mean base band does not prevent it.

*Argued:* the mechanism is that Laplacian detail bands are not exactly zero-mean at coarse
scale. Selecting a different frame per band leaves a DC residue in each reconstructed
detail band, and those residues accumulate into the output's low-frequency content even
though the base band itself is an honest mean. This is ORCH's "a sum of convex
combinations under different weightings is not convex", realised at low frequency rather
than at edges.

I cannot attribute this to a specific line in `pyramid.rs` without instrumenting it, and
that file is BUILD-BLEND's. What I can say from outside, by measurement, is that the
constraint must be applied to the **reconstruction**, not to the base band alone.

And per ORCH's instruction: do not simply clamp the reconstruction to the hull. Clamping
would move 10.16% of the frame and leave the wrong value at the clamp. The 79.3% figure
says where to look -- the coarse octaves' selection, where the shipped exponent ramp
`2 3 4 5 8 8 8` is at its floor and the noise gate has the least real signal to work with.

### 15.10 Verdict

Restating the three outcomes the brief asked me to decide between:

1. **The merge is genuinely non-convex.** **This one.** 10.1590% of output samples lie
   outside the hull of the aligned, warped, strehl-rendered input samples at that pixel,
   net -1.0009e9 DN of darkening, worst sample -4513 DN, on a hull with zero degenerate
   intervals. The same binary, same basis, same subject, with weights made uniform across
   bands, reads 0.0002% and exactly 0 in the base octave.
2. The merge is convex and the comparison was not apples-to-apples. **Rejected for the
   pyramid backend**, on the null arm and the exact plant. It remains the correct verdict
   for the original -805 DN claim, which section 13 refuted on separate grounds (its
   "hull" was a 7x8 array of per-band medians, not pixels).
3. Could not be determined. **No.**

The stage is per-band selection with independently-solved weights, and the excursion is
**low-frequency and negative**: 79.3% of it in the coarsest octave, 96.8% in the three
coarsest, 0.387% in the finest once the common-mode demosaic component is subtracted.

### 15.11 Reproduction

```
cd C:\dev\strehl-out\BUILD-HULL
python commission_bands.py                 # synthetic 2x2, must print GREEN
python warpframes.py --sidecar warp\flower-205.warpmap.txt ^
       --subject D:\personal\macro\flower-bud-alone-cpl --outdir warp ^
       --binary C:\dev\strehl-out\VERIFY-WIRE\target-a\release\strehl.exe
powershell -File .\warp_merges.ps1 ; powershell -File .\warp_nulls.ps1
python coreg.py --merge warp\merge-W-pyramid.tiff --warped warp\frames\f0102.tiff
python bfold.py --frames warp\frames --n 205 --cache warp\cache --bands
python btest.py --cache warp\cache --dir warp                      # 15.5
python btest.py --cache warp\cache --dir warp --plant 5000 --plant-arm W-uniform
python plantcheck.py                                               # must print GREEN
python octave.py                                                   # 15.6
python footprint.py --arm W-pyramid --null W-uniform               # 15.7
```

Binary `C:\dev\strehl-out\VERIFY-WIRE\target-a\release\strehl.exe`, sha256
`6E4B369664F1E75321B669EDAADDDB9DC6B23A444F01DDBF41833C6E70B59419`. The pinned
`859edac` binary cannot be used for any of this: it predates the `--merge` flag and has no
pyramid backend.

### 15.12 What I did not measure

- **A second subject through the warped route.** Only `flower-bud-alone-cpl` has a warped
  205-frame basis; rendering one costs ~56 minutes. `couch-fibers-cpl` has both merges
  rendered but 0 of 299 warped frames, so it is **requested, not scored**, and nothing in
  section 15 should be read as cross-subject.
- **Which internal Rust band carries the defect.** My octaves are my operator. The
  attribution is to spatial frequency, not to `pyramid.rs` array indices.
- **Whether the base-octave result survives a larger coefficient count.** The base octave
  has 1,596 samples across three channels and 132 of them violate. The contrast against
  the null's exact 0 is clean, but 132 is a small number and a second subject should
  confirm it before anyone treats 79.3% as precise.

## 16. Which arm, which hull, and what the clamp costs

ORCH asked four questions after section 15, on the grounds that my headline was one
careless reading away from being taken as a product measurement. The concern was correct
and the label was mine to fix. This section answers all four by measurement.

### 16.1 The correction, in one line

**The 10.1590% is the UNCLAMPED reconstruction.** The shipped default clamps, and against
the same hull the clamped arm reads 5.3126% with its worst excursion cut 21x. No number in
section 15 describes a delivered master.

Section 15 should be read throughout as a measurement of *the defect the clamp exists to
remove*, not of the product. I did not label it that way because when I rendered it the
clamp did not yet exist, and I did not re-check that assumption when ORCH's ship snapshot
landed four hours later. That is the same class of error the rest of this document exists
to catch, and it is worth recording that it was caught by someone else reading my summary
rather than by me.

### 16.2 Which arm: measured, not inferred

I did not reason about which arm it was from flags. I read the binary.

Every number in section 15 came from
`C:\dev\strehl-out\VERIFY-WIRE\target-a\release\strehl.exe`, sha256
`6E4B369664F1E75321B669EDAADDDB9DC6B23A444F01DDBF41833C6E70B59419`, built 2026-08-25
22:55. Scanning its image for the clamp's vocabulary:

| token | occurrences in VERIFY-WIRE | occurrences in ORCH-SHIP |
|---|---:|---:|
| `pyramid-hull` | 0 | 0 |
| `InputRange` | **0** | 1 |
| `Unclamped` | **0** | 1 |
| `hull` / `Hull` | **0** | 1 |

`strehl stack --help` on that binary lists no `--pyramid-hull` flag. The binary predates
the clamp entirely: it does not contain the code and there is no argument, environment
variable or default that could switch it on. **The 10.1590% arm is unclamped by
construction of the build, not by a flag I chose.**

The comparison binary is ORCH's pinned ship tree,
`C:\dev\strehl-out\ORCH-SHIP\src\target\release\strehl.exe`, sha256
`705C22D5AD484434B638CA8903E118476AA4C037F618064F49B15AF5DCD13E6E`, source 03:48, binary
03:52. Arms rendered from it are tagged `S-`; arms from the older binary are tagged `W-`.

### 16.3 Where the clamp is applied on the product path

ORCH asked for the call site traced through dispatch, not the enum. In the pinned ship
tree:

| step | file:line | what |
|---|---|---|
| 1 | `pyramid.rs:823` | `hull: Hull::InputRange` inside `impl Default for MergeConfig` |
| 2 | `main.rs:775` | `let mut pyramid = MergeConfig::default();` -- the product path's config |
| 3 | `main.rs:776-793` | six `if let Some(v)` assignments: `bands`, `gate`, `exponent`, `sharpen_per_octave`, `select`, `base`. **`hull` is not among them** |
| 4 | `merge_cmd.rs:220` | carried as `pub pyramid: MergeConfig` on `MergeOptions` |
| 5 | `merge_cmd.rs:3954` | `BandMerge::new(geom.width, geom.height, BAND_PLANES, cfg)` |
| 6 | `pyramid.rs:1002` | the hull is folded, per frame, as each frame is absorbed |
| 7 | **`pyramid.rs:1189`** | **`*p = p.clamp(*l, *h);`** -- the clamp, applied to the collapsed image |

`.hull` is never reassigned anywhere in `strehl-cli/src`, so the product path takes
`Hull::InputRange` unconditionally. In the live tree the same wiring sits at
`main.rs:861` and `pyramid.rs:902` / `pyramid.rs:1286`; only the line numbers move.

**It is not a `restore.rs`.** ORCH's worry was that a documented, tested,
defaulted-looking capability might simply not run. It runs, and the evidence is a rendered
pixel rather than a call graph: on `flower-bud-alone-cpl` the unclamped arm emits 233,075
exact-zero samples and the clamped arm emits **0**.

### 16.4 My hull is NOT the object the clamp enforces

ORCH's third possibility was the correct one, and it is the most important paragraph here.

`merge_cmd.rs:3524` sets `const BAND_PLANES: usize = 4`, and `merge_cmd.rs:3530-3535` maps
those four slots to `CfaPlane::R`, `G1`, `G2`, `B`. **The pyramid merge runs on Bayer CFA
quad planes, not on RGB.** `merge.finish()` is called at `merge_cmd.rs:4116` and
`opts.demosaic` is applied afterwards at `merge_cmd.rs:4137`.

So the clamp confines the reconstruction to the hull of the **CFA samples, before
demosaic**. My instrument measures the hull of **demosaiced RGB**. Those are two different
objects separated by the demosaic and by the quad-to-RGB recombination, and the gap has a
sign I can state exactly. Green is `0.5 * (G1 + G2)` (`merge_cmd.rs:3607`), and for any
frames

```
min_k (G1_k + G2_k)  >=  min_k G1_k + min_k G2_k
```

so the clamp's constraint, transported into my domain, is **strictly weaker than my hull**.
A correctly clamped render can sit outside my hull without ever leaving its own.

The codebase already knows this hazard in its own words, at `merge_cmd.rs:5346`:

> The statistic is ALWAYS taken on the binned quad grid, even under `--demosaic`. The
> demosaic is an interpolation and must not be able to [affect the statistic].

**So: no. My hull basis and the clamp's hull basis are not the same object.** This is the
fourth instance in this project of an instrument and its subject sitting on opposite sides
of a transformation, and this one is mine.

*What survives this.* Section 15's headline does **not** depend on the two hulls being the
same object, because section 15 never compared across a clamp -- it compared an unclamped
merge against a hull built from frames that went through the *same* demosaic, with a null
arm through the same path reading 0.0002%. The null is what bounds the demosaic's own
contribution, and it bounds it at essentially zero. The 10.1590% remains a real
non-convexity in the reconstruction.

### 16.5 The build control failed, and that is why the price comes from one binary

The two binaries differ by a night of other agents' commits, not only by the clamp. The
estimator backend contains no hull code in either build, so differencing the two estimator
renders measures the intervening commits alone. Both on the same 205-frame aligned basis:

| channel | samples | identical | differing | pct | max abs diff | mean abs diff, edges | flat | ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R | 8,250,880 | 193,818 | 8,057,062 | 97.651% | **3902** | 143.26 | 41.67 | 3.4x |
| **G** | 8,250,880 | **8,250,880** | **0** | **0.000%** | **0** | 0.00 | 0.00 | -- |
| B | 8,250,880 | 647,081 | 7,603,799 | 92.157% | 1326 | 34.49 | 9.68 | 3.6x |

Green is **bit-identical**, R and B moved on most of the frame, and the movement
concentrates about 3.5x on gradient. That is the signature of a geometric correction
applied to R and B against G as reference -- a chromatic-aberration correction -- and not
of a level change.

Two consequences, and both matter beyond this section:

1. **Cross-build comparisons tonight are unsafe on R and B and exact on G.** Any agent
   differencing renders from binaries either side of that change is measuring the CA
   correction unless it restricts to green.
2. A clamped-vs-unclamped comparison across these two binaries cannot price the clamp. The
   price below therefore comes from **one binary and one flag**.

### 16.6 The clamped arm, measured against a build-matched hull

To remove the confound entirely I rendered a second 205-frame warped basis with the ship
binary and folded a build-matched hull (0 degenerate intervals of 24,752,640; span min 123
DN, mean 4041.2). Whole image, all channels, guard +/- 1 DN:

| arm | clamp | rate | below | above | worst/span | worst DN | exact zeros |
|---|---|---:|---:|---:|---:|---:|---:|
| W-pyramid | **UNCLAMPED** | **10.1581%** | 2,279,008 | 235,380 | 6.527 | -4513 | 233,075 |
| S-pyramid | **CLAMPED** | **5.3126%** | 1,185,102 | 129,903 | **0.307** | **-953** | **0** |
| W-uniform | null | 0.0002% | 24 | 16 | 0.085 | -35 | -- |

Scored against the older basis instead, the same arms read 10.1590% and 5.2476%, so the
headline is robust to which build supplied the frames. Green, where the two builds are
bit-identical and the comparison is exact, reads 10.5310% unclamped and 8.4056% clamped.

The clamp roughly halves the rate, cuts the worst excursion **21x** and the worst
darkening **4.7x**, and removes every exact-zero sample. It does not reach the null,
because of section 16.4.

**The residual keeps the coarse-scale character.** Footprint-weighted and null-subtracted,
as in section 15.7:

| octave | unclamped share | clamped share |
|---|---:|---:|
| detail0 (finest) | 0.387% | 0.527% |
| detail5 | 6.917% | 23.518% |
| detail6 | 10.592% | 25.834% |
| base (coarsest) | 79.308% | 41.871% |
| **three coarsest** | **96.817%** | **91.223%** |
| total excess, full-res weighted | 577,736,622 DN | 265,068,899 DN |

I predicted before running this that if the clamp were airtight in its own domain and the
residual were demosaic overshoot, the clamped profile would become **finest**-dominated,
because interpolation overshoot is a fine-scale phenomenon. **That prediction is refuted.**
The clamped residual is still 91.2% coarse. Demosaic does not explain it; the quad
recombination of section 16.4 is the remaining explanation and I have not isolated it.

### 16.7 The clamp's price, and it is not free

ORCH asked for the clamp's price on a subject that does not clip, noting that "clamping
cannot cost anything real" is an argument rather than a measurement. It is a measurement
now, and **the argument does not survive it.**

`blend-render` is the only binary in the tree where `Hull::Unclamped` is reachable
(`blend-render.rs:124`), so each pair below is one build, one flag, identical alignment,
camera-linear, no tone curve anywhere.

**Determinism null, run first:** the same subject rendered twice with identical flags
differs in **0 samples, max abs diff 0 DN**. The pipeline is deterministic, so everything
below is the flag and not run-to-run noise.

What the merge says its own clamp did, per CFA plane, in its own domain:

| subject | clipping to fix? | `hull clamp` self-report |
|---|---|---|
| `flower-bud-alone-cpl` | yes, 1.4075% | 8.647% 10.106% 10.105% 10.986% |
| `coffee-bean` | essentially none, 0.0010% | 15.510% 18.911% 18.897% 18.171% |
| `couch-fibers-cpl` | **none, 0.0000%** | 2.076% 7.021% 7.048% 3.972% |

The clamp binds **more** on the subject with nothing to fix than on the one that clips.

Scored on ORCH's own commissioned `ORCH-CLAMP\accept.py`, with its own pre-registered
thresholds, unclamped as the reference so every ratio reads directly as the clamp's cost:

| subject | arm | clip% | acuity | microC | verdict |
|---|---|---:|---:|---:|---|
| `coffee-bean` | unclamped | 0.0010 | 736.5 | 520.72 | (reference) |
| `coffee-bean` | clamped | 0.0000 | 724.9 | **440.66** | **FAIL: micro 84.6%** |
| `couch-fibers-cpl` | unclamped | 0.0000 | 380.7 | 347.81 | (reference) |
| `couch-fibers-cpl` | clamped | 0.0000 | 373.2 | **339.73** | **FAIL: micro 97.7%** |
| `flower-bud-alone-cpl` | unclamped | 1.4075 | 224.1 | 118.49 | (reference) |
| `flower-bud-alone-cpl` | clamped | 0.0000 | 223.4 | 117.55 | **PASS** |

Subjects requested 3, scored 3, missing 0. Gate verdict: **FAIL, 1 pass / 2 fail.**

The pattern is clean and it inverts the doc comment's claim:

- **Where there is clipping to fix, the clamp is nearly free.** flower-bud: removes
  1.4075% clipping for 0.8% of microcontrast and 0.3% of acuity.
- **Where there is nothing to fix, the clamp still costs.** couch-fibers removes 0.0000%
  clipping for 2.3% of microcontrast; coffee-bean removes 0.0010% for **15.4%**.

`pyramid.rs:666-674`, under the heading "Why clamping cannot cost anything real", argues
that "where the frames agree the hull is tight and the clamp binds constantly while
changing nothing". The first half is right and the second is
false: a tight hull is not a safe hull, it is a *restrictive* one, and on subjects whose
frames agree the clamp binds constantly **and moves the value**, by a mean of 348 DN and up
to 7304 DN on coffee-bean.

ORCH's own standing rule was that `couch-fibers-cpl` "is the placebo. A proposal that
moves it is wrong regardless of what it does elsewhere." **The clamp moves it**, below the
98% bar ORCH registered.

*Argued, not measured:* microcontrast is a local standard deviation and the clamp removes
variance by construction, so some of that 2.3% and 15.4% may be noise rather than detail.
I have not separated them. What defeats the post-hoc version of that defence is that the
98% bar was registered in advance, by ORCH, for exactly this comparison.

### 16.8 Commissioning

Every instrument in this section was commissioned before its result was believed.

| control | requirement | result |
|---|---|---|
| determinism null | two identical runs must agree exactly | 0 differing samples, max 0 DN -- **PASS** |
| potency control | the pair instrument must read non-zero where the clamp is known to act | flower-bud 11.8587% of samples moved, max 4457 DN -- **PASS** |
| build control | isolates the intervening commits from the clamp | **FAILED as a control**, and the failure is the finding of 16.5 |
| binary provenance | the clamp's presence read from the image, not from flags | 0 vs 1 occurrences -- **PASS** |
| hull sanity | no degenerate intervals in the build-matched basis | 0 of 24,752,640 -- **PASS** |
| null arm | uniform weights through the real pipeline | 0.0002% -- **PASS** |

The `hull clamp` self-report initially read `NOT REPORTED` on every subject while the
number was sitting in the log. PowerShell's `*>` redirection writes **UTF-16LE with a
BOM**, and decoding that as UTF-8 with `errors="replace"` yields plausible-looking garbage
with no exception raised. Had I trusted it I would have reported that the ship binary does
not instrument its own clamp, which is false. `pairprice.py:read_log` now detects the BOM.

### 16.9 Verdict

Answering ORCH's four questions in order:

1. **The 10.1590% arm is `Hull::Unclamped`** -- and not by a flag, but because the binary
   contains no clamp code at all. It is the defect the clamp removes, not a product
   measurement.
2. **The clamp is applied at `pyramid.rs:1189`**, reached from `main.rs:775` via
   `MergeConfig::default()` with `hull` never reassigned. It runs: 233,075 exact zeros
   become 0.
3. **No, my hull is not the object the clamp enforces.** The clamp bounds CFA quad planes
   pre-demosaic; I bound demosaiced RGB. For green the clamp's transported constraint is
   *strictly weaker* than mine, so 5.3126% is a real number about a quantity nobody
   enforces. Section 15's result is unaffected, because it never compared across a clamp.
4. **The clamp is not free.** It fails ORCH's pre-registered acceptance gate on two of
   three subjects, including ORCH's own nominated placebo, and it costs most exactly where
   it has least to fix.

### 16.10 What I did not measure

- **The clamp inside its own domain.** Confirming it is airtight against the CFA hull
  needs a 205-frame basis rendered without `--demosaic`, on the binned quad grid. I have
  not rendered one, so "the clamp is exact in its own domain" remains *unverified* -- I
  showed only that my RGB-domain residual cannot be attributed to demosaic overshoot.
- **Whether the microcontrast the clamp removes is signal or noise.** See 16.7.
- **Which commit produced the R/B build difference.** I characterised it as geometric and
  CA-shaped from its own signature; I did not bisect the history to name it.
- **A second subject for the octave attribution.** Unchanged from 15.12.

### 16.11 Proposal for BUILD-BLEND, who owns the fix

I have not edited `pyramid.rs` and this is a proposal, not a change.

1. **Do not ship the clamp unconditionally.** On the evidence above it earns its place on
   dark-subject-on-bright-ground stacks and loses microcontrast everywhere else. The gate
   it fails is ORCH's own.
2. **Clamp the CFA-domain reconstruction only where the reconstruction is actually
   leaving the hull downward into darkness**, which is where the artifact lives and where
   the measured cost is near zero, rather than on every coefficient in the frame.
3. **If the invariant is to be asserted rather than enforced**, assert it in the CFA
   domain the merge actually works in, with the tolerance expressed in hull spans and not
   in DN, and exclude nothing -- an assertion that is cheap and always true is worth more
   than a correction that is expensive and sometimes wrong.
4. **Do not extend the clamp to RGB to make my 5.3126% go to zero.** That number is
   measured against a hull nobody enforces and the right response is to decide whether the
   RGB hull *should* be enforced, not to chase the number.
