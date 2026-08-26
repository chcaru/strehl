# V-softness: independent verification of the library-wide sharpness regression

Status: complete. Verifier: V-SOFTNESS. Subject: BUILD-RENDER.md sections 12.1-12.3,
and the proposed revert of `57e4554`. **Part II below answers the halo cost that
Part I left open, and reports a defect in the blend measurement it was compared
against.**

I did not edit `crates/`, `SYNTHESIS.md`, `AGENTS.md`, `README.md` or
`docs/captures-needed.md`. Everything below is measured from pinned `git archive`
builds under `C:\dev\strehl-out\`, or from the archived gallery runs.

## 0. Bottom line

**The regression is real, it is larger than reported, and it bisects to `57e4554`.
The revert is justified on the measurements. But `57e4554` is not a pure deletion,
so "revert the commit" and "restore the noise-driven shrink" are not the same
operation, and only the second is supported by what I measured.**

Four independent statistics agree, including two that cannot see a tone change,
and a single-commit isolation on two subjects rendered to the byte-frozen linear
output reproduces the loss and hands over the mechanism.

The mechanism is not in dispute once you read the binaries' own diagnostics:

| | parent `526c727` | child `57e4554` |
| --- | --- | --- |
| mean focus-window radius, bee-1-cpl | 2.14 px | **7.74 px** |
| mean focus-window radius, bee-2-cpl | 2.05 px | **8.28 px** |
| share of pixels at r13, bee-1-cpl | 4.33% | **47.17%** |

The window that regularises the focus election grew by 3.6x-4.0x. A wider window
blurs the depth decision, and a blurred depth decision softens the merge wherever
detail is fine or depth changes. That is the whole effect.

## 1. Is the metric sound? CONFOUNDED AS USED, BUT THE FINDING SURVIVES

BUILD-RENDER measured section 12.1 on the gallery JPEGs, which are `--srgb`
renders. The project forbids this in two places the agent had already written or
read. `strehl stack --help` on `--linear-srgb`:

> THIS IS THE MODE TO MEASURE IN. The standing rule is that quality is never
> judged on an `--srgb` render, because the transfer curve is a strong
> non-linearity that moves every ratio a metric computes; more than one result in
> this project has been retracted for exactly that.

And every `RUN.txt` in `gallery-history` ends:

> `--srgb` is correct HERE and only here: this is a viewing render, and the tone
> rendering rides with it. **Never measure on one of these files.**

So section 12.1 violated a standing rule, and section 14 later diagnosed the
consequence independently. I commissioned my own instruments against that failure
mode before using them (`experiments/V-softness/src/vlib.py`), on
`couch-fibers-cpl` run 1:

| planted arm | raw gradient RMS | contrast-normalised | HF fraction |
| --- | --- | --- | --- |
| null: identical image | 1.0000 | 1.0000 | 1.0000 |
| blur sigma 0.5 (must detect) | 0.8477 | 0.8586 | 0.8256 |
| blur sigma 1.0 (must detect) | 0.6247 | 0.6489 | 0.3949 |
| linear gain x0.95 (must ignore) | **0.9500** | 1.0000 | 1.0000 |
| gamma 1.20, nonlinear (must ignore) | **1.0818** | 0.9965 | 1.0048 |
| gamma 0.85, nonlinear (must ignore) | **0.9261** | 1.0051 | 1.0008 |
| S-curve, nonlinear (must ignore) | **1.2885** | 1.0024 | 0.9624 |

The raw statistic swings by up to 29% on a pure tone change with no blur anywhere.
Section 14 is right about that and right about the mechanism.

**I expected to find that section 14's fix was insufficient, and I was wrong.** I
predicted that standardising to zero mean and unit variance removes only the
affine part of a tone change and would still be fooled by a curve. Measurement
says otherwise: the normalised statistic holds 0.9965-1.0051 across three
nonlinear curves. The reason is that these images have narrow histograms, so a
smooth curve is locally affine over the occupied range. I record the prediction
and its refutation because the refutation is the useful half.

**Re-running the corrected statistic on section 12.1's exact run pair gives 19 of
26 softer and 0 sharper**, with magnitudes equal to or larger than the raw ones:

| subject | raw (section 12.1) | contrast-normalised | HF fraction |
| --- | --- | --- | --- |
| bee-1-cpl | 0.9287 | **0.9236** | **0.8376** |
| highly-angled-ruler-mm-cpl | 0.9398 | **0.9244** | **0.8260** |
| dry-erase-marker-head-cpl | 0.9398 | **0.9342** | **0.8373** |
| couch-fibers-cpl | 0.9604 | **0.9569** | **0.9175** |

Verdict on my own third statistic: 22 of 26 below 1, median 0.9599.

**Section 14's caveat is therefore wrong in direction.** It says the section 12
magnitude "should be treated as an upper bound until it is re-measured with the
normalised ratio". I have re-measured it with the normalised ratio, and the
losses are larger, not smaller. Section 14's own re-measurement (20 softer to 11)
was on a different run pair, the one carrying the section 13 tone fix; `a59ad57`
is not in the `5d7a7ba..859edac` window, so that correction never applied to
section 12 in the first place.

## 2. Is the comparison paired? YES. ORCH's predicted failure mode did not recur

ORCH expected mixed provenance. It is not there.

| | run 1 `2026-08-25-tone-fix` | run 2 `2026-08-25-1327` |
| --- | --- | --- |
| binary | `pin-5d7a7ba` | `pin-859edac` |
| sha256 | `AE5F7FA28C4ABA45...` | `DF209CE003E2E6B9...` |
| subjects | 26 | 26 |
| manifest rows | 26 + header | 26 + header |
| JPEGs on disk | 26 | 26 |

One binary each, one pin each, complete manifests. I also audited the JPEG
container, which nobody had: **all 52 files share one quantisation-table hash
`b40e056724db`**, identical dimensions and identical subsampling, so the encoder
is not a variable.

An unplanned fourth instrument fell out of that audit. At a fixed quantisation
table, JPEG size is a proxy for high-frequency content, and run 2 is smaller on
24 of 26 subjects: bee-1 -4.9%, leaf-2 -9.2%, lead-1 -8.1%. `coffee-bubbles` is
the exception at +47%, which matches section 14's note that its "before" carried
88% zero-blue clipping.

A third archive exists that the briefing did not mention, `2026-08-25-1554`,
rendered from `vtone-after`. It is the section 14 run, not a third arm of section 12.

## 3. Does `57e4554` carry the loss on a second subject? YES, AND WORSE

BUILD-RENDER bisected on one subject. I isolated the single commit against its own
parent `526c727`, built from pinned `git archive`, and rendered to the
**byte-frozen default output** (binned, linear, camera-native) rather than to an
`--srgb` JPEG, so no tone curve, no JPEG and no 8-bit quantisation can enter.

| | bee-1-cpl | bee-2-cpl | couch-fibers (BUILD-RENDER) |
| --- | --- | --- | --- |
| whole-image gradient RMS | **0.8934** | **0.9300** | 0.9342 |
| most-detailed 20% of pixels | **0.8912** | **0.9314** | not measured |
| flattest 20% of pixels | 1.0054 | 1.0026 | not measured |
| pixels changed | 37.9% | 41.3% | not measured |

`bee-1-cpl` loses **10.7%**, against the 6.6% reported on `couch-fibers-cpl`.

**The loss is not a noise artifact.** This was the live alternative explanation
and it had to be excluded, because gradient RMS and HF energy both rise with
noise, so a change that quietened the background would read as a blur on every
statistic used so far, BUILD-RENDER's and mine. Binning pixels by local variance
measured on the parent only, so the treatment cannot move the partition, puts the
loss in the **detailed** bins and leaves the flat bins at or above 1.0. Blur
attenuates detail; denoising would have moved the flat bins down. It did not.

## 4. Was the deletion reasonable? IT WAS JUSTIFIED BY A QUANTITY IT DID NOT MEASURE

`57e4554` cites one measurement: background standard deviation on three flat
patches of one subject, `bee-2-cpl`. It never measured sharpness on detail. The
quantity that regressed is one the commit did not look at.

Worse, **the commit's own claim does not reproduce on the commit's own subject.**
Its table implies the child should carry 11-16% less background noise than the
parent (0.878/0.986, 1.005/1.070, 0.996/1.187). Measured over the flattest
fraction of the whole frame:

| aperture | bee-2-cpl child/parent | bee-1-cpl child/parent |
| --- | --- | --- |
| flattest 2% | **1.0187** | **1.0048** |
| flattest 5% | 1.0092 | - |
| flattest 10% | 1.0056 | - |
| flattest 20% | 1.0037 | - |

Deleting the shrink made background noise very slightly **worse**, at every
aperture, on the subject chosen to justify the deletion. The sign is opposite to
the commit's. Three hand-picked patches disagreed with 165k pixels.

So on both subjects the deletion is a **pure loss on both axes**: it spent 7-11%
of gradient energy and bought nothing measurable in background noise.

One point in BUILD-RENDER's favour, against my own suspicion. Section 12.2's first
rung jumps `5d7a7ba` to `57e4554`, which is three commits, so I expected an
unattributed step. It is clean: `47c48a7` touches only `scripts/`, `526c727` only
`docs/`, and neither changes crate code. My `526c727` binary is byte-size
identical to run 1's `pin-5d7a7ba` binary at 9135104 bytes, which corroborates it.

## 5. Costing the revert: cheap on noise, UNRESOLVED on halo

The noise side is settled above: restoring the shrink costs nothing in background
noise and on these two subjects slightly improves it.

**The halo side I could not settle, and I am not going to pretend otherwise.**
`57e4554` is a halo commit, and its stated gain is that "the broad veiling aura is
gone at full-frame scale". My halo instrument segmented 48.8% of `bee-1-cpl` into
"subject" and returned a *negative* near-edge excess, meaning it read a scene
luminance gradient rather than an aura. An uncommissioned instrument's output is
not evidence and I am not reporting a halo verdict from it.

The one solid result from that run is a clean paired null: **beyond 150 px from
any silhouette the two renders agree to +0.3 DN on 16773, or 0.002%.** All
measured differences are confined to detail and to within about 20 px of
silhouettes, which is consistent with a focus-window effect and rules out any
global gain or tone difference between the two pins.

**The load-bearing caveat for whoever orders the revert.** `57e4554` is not a pure
deletion. It also replaced `SelectionScale::from_acuity` with `from_silhouettes`,
deleted the confidence veto, `FLOOR_Q` and `conf`, and changed `regularise_guided`
to average along the background instead of across the silhouette. The commit
attributes the aura removal to that last downstream change, not to the deletion:

> What changed is not the cap but what happens downstream: `regularise_guided`
> averages along the background instead of across the silhouette.

If that attribution is right, the noise-driven shrink can be restored without
giving back the aura, because the aura fix lives in a different part of the same
commit. **A wholesale `git revert` would take both.** What the measurements
support is restoring the shrink term, with the halo re-measured afterwards by
BUILD-HALO, who owns that lane and has a commissioned aura instrument.

## 6. Defects

1. **Section 12.1 measured on `--srgb` JPEGs**, which the CLI help and every
   `RUN.txt` forbid. The conclusion survives correction; the magnitudes there
   should not be quoted.
2. **Section 14's "upper bound" caveat on section 12 is wrong in direction.**
   Re-measured with the normalised ratio, section 12's losses grow. Section 14's
   correction was measured on a different run pair and never applied to section 12.
3. **`57e4554`'s cited measurement does not reproduce on its own subject**, at the
   opposite sign, over a far larger sample than the three patches it used.
4. **Neither section 12 nor `57e4554` separated blur from noise.** Both used
   whole-frame statistics that move with either.
5. Mine: the `eq_sigma` column in `out/library26.json` has a floor artifact from a
   sigma grid that is too coarse near zero. `wrapped-text-1` reads 0.252 px at an
   HF ratio of 0.9986, which is a null. Do not use that column.

## 7. Gaps

- ~~The halo cost of restoring the shrink is **unmeasured**.~~ **Closed by Part II
  section 10**: measured on three subjects with dose. It is 0 DN on the band
  merge, 48-92 DN on `coffee-bean` and `bee-1-cpl`, and +444 DN *favourable* on
  `flower-bud-with-background-fern-cpl`.
- I isolated the commit on two subjects, not 26. The other 24 rest on the gallery
  comparison, which is now corroborated by four statistics but is still a two-pin
  comparison spanning 18 commits.
- ~~Section 12.2's ladder reports 0.9376 ... Unreconciled.~~ **Closed by Part II
  section 13**: it is a statistic-and-medium artifact, not a tone artifact. The
  proposed tone explanation is refuted -- global contrast between the two runs
  differs by 0.36% and mean level by 0.5 DN.
- `foam`, `leaf-2` and `lead-1` read softer on the normalised statistic and
  *sharper* on the HF fraction. Two of my instruments disagree on three subjects
  and I did not chase it.

---

# Part II: the halo cost of restoring the shrink

Status: complete. Second assignment, same verifier. Everything below is measured
from a pinned `git archive` of HEAD `2981354` patched under
`C:\dev\strehl-out\V-shrink\tree`. I did not edit the shared `crates/`.

## 8. The one sentence you asked for

**Restoring the shrink term costs no measurable aura on the multi-band merge at
all -- the two arms are byte-identical there -- and on the shipped estimator path
it moves the backdrop by at most +444 DN of 14617 (3.0%) on
`flower-bud-with-background-fern-cpl`, 92 DN of 18362 (0.50%) on `bee-1-cpl` and
48 DN of 55896 (0.086%) on `coffee-bean`, with the large `flower-bud` change
POSITIVE, i.e. filling the veil in rather than deepening it.**

The trade, one binary, two arms, paired geometry, full frame, 16-bit linear
camera-native, gate 4:

| subject | mean radius A -> B | r1 share A -> B | grad RMS B/A | HF power B/A | max abs aura change | as % of far field | ring prominence A -> B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bee-1-cpl` | 12.81 -> **6.10 px** | 0.06% -> 49.13% | **1.1618** | **1.3510** | 92 DN | 0.50% | 76 -> 76 DN |
| `flower-bud-...-fern-cpl` | 12.98 -> **8.61 px** | 0.00% -> 31.69% | 1.1025 | 1.1150 | 444 DN | 3.04% | 1205 -> 1302 DN |
| `coffee-bean` | 12.98 -> **5.91 px** | 0.00% -> 56.47% | 1.0292 | 1.0633 | 48 DN | 0.086% | 130 -> 134 DN |
| `109MSDCF` | 13.00 -> 13.00 px | 0.00% -> 0.00% | 1.0000 | 1.0000 | 0 DN | 0% | 2173 -> 2173 DN |

Read the last row as an instrument check, not as a placebo result. See 10.3.

## 9. The premise of the assignment is false, and I measured that rather than arguing it

The assignment says to measure the aura cost "on top of the multi-band merge, not
on top of the old merge path". **The shrink term cannot execute on the multi-band
merge.** `merge_cmd.rs` branches on the backend at 2203-2206; `run_estimator`
begins at 2209 and `run_pyramid` at 3586, and the `from_silhouettes` call that
elects the focus window is at 2548, inside `run_estimator`. The pyramid backend
never reaches the election.

Structure is not proof, so I executed it. One binary, one subject, 40 frames, the
same `V_RESTORE_SHRINK` env var, four arms:

```
GATE LIVE on estimator : est-A sha256 9B777C0B90489602C312474D0B2111F52015F0D85A3D2630AE7EEF111F51139D
                         est-B sha256 75AE09E053DC3FA3D4B93D0EDEA9B3AB5D640CD5D673D0336D31195474AF2009
INERT on pyramid       : pyr-A sha256 F267BD8243BD7DE982B9A369315DCE7BD87C0E408318F7B26E19E798E39C13C9
                         pyr-B sha256 F267BD8243BD7DE982B9A369315DCE7BD87C0E408318F7B26E19E798E39C13C9
```

The estimator arms differ. The pyramid arms are **byte-identical**. The pyramid
logs contain no `pass zero: depth guide for the edge-aware election` section at
all, so there is no radius histogram to move. This is the distinction your own
broadcast drew -- "a structurally inert gate and a measurably useless gate produce
the same number and mean opposite things" -- settled by having a live positive
control in the same binary at the same moment.

**Second false premise: the band merge is not the default and was not wired in
tonight.** `a306982` made it default and **`c42cd75` reverted that flip**.
`merge_cmd.rs:275` reads `pub const DEFAULT_MERGE_BACKEND: MergeBackend =
MergeBackend::Estimator;`. Your own `38ad133` gives the reason: the pyramid clips
2.9920% of pixels to exact zero on `flower-bud-alone-cpl` and 1.6777% on
`dry-erase`, and "a clipped-to-zero pixel holds no recoverable information, which
is strictly worse than a halo".

So the decision-relevant measurement is on the estimator, which is what ships
today, and that is what section 10 reports.

## 10. Aura cost on the shipped path

### 10.1 Method

Eight full-frame renders, `--gate 4 --demosaic`, no `--srgb`, 16-bit linear
camera-native, from one binary carrying both arms behind `V_RESTORE_SHRINK`.
Arm A is HEAD as shipped; arm B restores the noise-driven shrink **only**,
leaving `from_silhouettes`, the collapse veto, `FLOOR_Q`, `conf` and
`regularise_guided` exactly as `57e4554` left them.

I used your `rimprofile.py` for the headline numbers and reproduced your control
column from it exactly (39402 / 54725 / 54871 / 55516 / 56706 / 57912, far field
59630). I then added one paired variant, because `rimprofile.py` recomputes its
subject mask from whichever image it is handed: an A/B through it is not strictly
paired, since a treatment that moves the silhouette threshold moves the distance
bins with it. `paired_rim.py` takes the mask and the signed-distance field from
arm A and reads **both** arms through it. All section 10 numbers are absolute
median DN, per your standing rule.

### 10.2 `flower-bud-with-background-fern-cpl`, the subject you care about

Far field 600-1400 px: arm A 14617 DN, arm B 14617 DN, **pedestal +0 DN** over
5443150 px. The treatment is exactly null where it must be.

| d (px) | A, no shrink | B, shrink | B - A |
| --- | --- | --- | --- |
| 0-4 | 9795 | 10027 | **+231** |
| 4-8 | 11659 | 12103 | **+444** |
| 8-12 | 12551 | 12800 | +249 |
| 12-16 | 13011 | 13111 | +100 |
| 25-30 | 13134 | 13417 | +282 |
| 50-65 | 12097 | 12114 | +17 |
| 80-100 | 12440 | 12441 | +1 |
| 150-200 | 13888 | 13888 | +0 |
| 500-600 | 14256 | 14256 | +0 |

Every near-silhouette bin goes **up**. The veil deficit at d = 4-8 px is -2957 DN
in arm A and the shrink returns +444 DN of it, about 15%. The effect is dead by
d = 80 px and exactly zero past 150 px.

The one adverse reading: the interior ring gets slightly stronger, prominence
1205 -> 1302 DN (+8.0%), and moves outward one bin, from 20-25 px to 25-30 px.
Against
the band merge's effect on the same ring (section 12: 3739 -> 268 DN, -93%) this
is small and in the opposite direction.

### 10.3 The controls, and which one actually carries weight

`coffee-bean` is the control that counts. Its dose is the **heaviest** of the four
(mean radius 12.98 -> 5.91 px, 56.47% of pixels driven to r1) and its response is
**48 DN, 0.086% of the 55896 DN far field**, with a +3 DN far-field pedestal. A
heavy dose producing nothing is a real null.

It also reproduces your own characterisation of the subject independently: veil
34550/55896 = **-38.2%** at d = 0-4, ring prominence 130/55896 = **+0.23%** at
d = 450 px. Both match the figures in your brief.

**`109MSDCF` does not carry weight and I am not going to let it.** Its response is
exactly 0 DN in every bin, but arm B's radius histogram there is r8 0.05%,
r13 99.95%, mean radius 13.00 px, and the collapse veto admitted 0 px on both
arms. **The treatment did not act, so the outcome could not move.** That is a null
of the probe, not a null of the response, and it reads identically to a passing
placebo. What it does establish is that the shrink is subject-gated: it does not
fire on a stack with no depth separation. Its profile is also wildly non-monotone
(7930 at d = 22, 6197 at d = 225, 8392 at d = 275), so `rimprofile.py`'s uniform
backdrop assumption does not hold there either.

`bee-1-cpl` is the third data point: 92 DN of 18362 (0.50%), ring prominence
unchanged at 76 -> 76 DN, far-field pedestal +0 DN, and the sign is mostly
negative in the 8-50 px band rather than positive.

## 11. The other side of the trade, measured at HEAD

The sharpness gain from restoring the shrink survives at HEAD and is **larger than
the loss `57e4554` caused**:

| subject | grad RMS B/A | contrast-normalised | HF power fraction B/A |
| --- | --- | --- | --- |
| `bee-1-cpl` | **1.1618** | 1.1654 | **1.3510** |
| `flower-bud-...-fern-cpl` | 1.1025 | 1.1063 | 1.1150 |
| `coffee-bean` | 1.0292 | 1.0296 | 1.0633 |
| `109MSDCF` | 1.0000 | 1.0000 | 1.0000 |

Part I measured the `57e4554` loss on `bee-1-cpl` as 0.8934, whose reciprocal is
1.1193. The surgical restore returns **1.1618**, more than the whole original
loss, because it now acts on top of `from_silhouettes` and the collapse veto
rather than the older `from_acuity`.

`109MSDCF` reading exactly 1.0000 on both sharpness statistics and exactly 0 DN
on the aura statistic is the coherence check: the subject where the treatment did
nothing shows nothing on every instrument, and the subjects where it acted show
movement on all of them.

## 12. DEFECT: the blend arms you measured are sRGB, not linear

**Your brief states "Paired linear 16-bit TIFFs are on disk now at
`C:\dev\strehl-out\BUILD-BLEND\ca-{ctrl,blend}-*.tiff`" and "I measured its paired
linear output". Both files are sRGB-encoded.**

At source, `blend-render.rs:543-549`:

```rust
let space = if camera_linear { image_out::OutputSpace::CameraLinear }
            else if linear   { image_out::OutputSpace::LinearSrgb }
            else             { image_out::OutputSpace::Srgb };
```

`run-bm.ps1`, which produced them, renders the control with `--srgb` explicitly
and invokes `blend-render` with neither `--linear` nor `--camera-linear`, so it
takes that `else` branch. `rimprofile.py`'s docstring says it "Measures on the
LINEAR 16-bit render only", but its only guard is `assert img.dtype == np.uint16`.
It accepted both files silently and printed the column header "linear DN".

**Correcting the space inverts the instrument's own central verdict.** The script
exists to separate "an interior local maximum in linear -> the merge emitted it,
an election defect" from "a monotone veil -> one optical term, already owned":

| control arm, same file | interior peaks (d px, prominence DN) |
| --- | --- |
| as measured, sRGB-encoded | `[(275, 403)]` |
| sRGB-decoded to true linear | **`[(22, 3739), (275, 765)]`** |

In the space you read, the control's only interior peak sits at d = 275 px with
403 DN of prominence, far from the silhouette and easy to dismiss. In true linear
a ring appears at **d = 22 px with 3739 DN of prominence**, 9.3x larger and right
where the defect would be. The sRGB curve is nearly flat across 0.6-0.9 of full
scale, which is exactly where this backdrop sits, so it compressed the bump below
detectability while leaving the broad far-field trend visible.

**Independently corroborated.** My own arm A render of the same subject is
camera-native linear by a different route -- rendered, not decoded -- and finds
the same ring at the same place: `[(22, 1205), (275, 224)]`, prominence
1205/14617 = **8.2%** of far field against the decoded file's 3739/52945 =
**7.1%**. Two routes to linear agree; the sRGB reading agrees with neither.

Your magnitudes move accordingly, at d = 50-65 px:

| | as you read it (sRGB) | true linear |
| --- | --- | --- |
| control veil vs its own far field | -4759 DN | **-8218 DN** |
| blend veil vs its own far field | -2551 DN | -4255 DN |
| blend - control, absolute | +2837 DN | **+5313 DN** |
| far-field pedestal, blend - control | +630 DN | +1350 DN |
| blend - control, pedestal-corrected | +2207 DN | **+3963 DN** |

**Your conclusion survives and in fact strengthens.** The blend removes a ring
that is real rather than a shoulder that was not, prominence 3739 -> 268 DN,
**-93%**, and lifts the mid-field by 1.9x more than you measured on the absolute
difference, 1.8x once the pedestal is removed. Nothing here
argues against wiring it. But every DN figure in that table is in the wrong
transfer space, and the "visible deficit at d = 90 px goes from -6.90 to -0.94 of
255" line is computed by `rimprofile.py` applying a **second** sRGB encode on top
of the first, so it is not what a viewer is shown.

This is the hazard you broadcast tonight, landing in your own headline: you made
absolute DN a hard requirement because an additive bias hides inside an error or a
ratio, and the absolute DN were reported in a nonlinear space.

**One prediction of mine, refuted.** I first suspected the two arms were in
*different* spaces -- an sRGB control against a linear blend -- which would have
broken the pairing outright. Measured: binning one arm against the other, the raw
ratio has CV 0.0907 across the tone range while the sRGB-decoded ratio has CV
0.5879. Decoding makes the mismatch **6.5x worse**, so the two are in the same
space and the pairing is intact. The defect is the space, not the pairing.

## 13. `couch-fibers-cpl`, 0.9376 vs 0.9604: it is not the tone change

You asked me to chase this only if cheap, on the hypothesis that the two numbers
reconcile via the tone fix, which would also explain BUILD-RENDER's guard firing
on an intended change. It was cheap. **The hypothesis is refuted.**

Measured on the two archived gallery runs of section 12.1's own pair:

| statistic, run2 / run1 | value |
| --- | --- |
| raw gradient RMS | **0.9604** (reproduces section 12.1 exactly) |
| contrast-normalised | 0.9569 |
| HF power fraction | 0.9175 |
| global contrast, sd ratio | **1.0036** |
| mean level | **+0.5 DN** |

Global contrast differs between the two runs by 0.36% and mean level by 0.5 DN on
a 0-255 scale. **A tone difference that small cannot produce a 4% gradient-RMS
move.** The section 12.1/12.2 gap is a statistic-and-medium artifact, not a tone
artifact: the pinned-linear 0.9376 sits between the JPEG raw 0.9604 and the JPEG
HF 0.9175, because gradient RMS and HF fraction weight the spectrum differently
and 8-bit sRGB JPEG is not 16-bit linear TIFF.

**Do not tell BUILD-RENDER the `couch-fibers-cpl` guard is firing on an intended
tone change.** On this evidence it is firing on a real softening.

## 14. Defects, part II

6. **`ca-{ctrl,blend}-*.tiff` are sRGB-encoded, not linear** (section 12).
   `rimprofile.py` labels its output "linear DN" while guarding only on dtype.
   Every DN figure measured through it on those files is in the wrong space, and
   its ring-versus-veil verdict inverts when the space is corrected.
7. **`rimprofile.py` re-derives its subject mask per image**, so an A/B through it
   is unpaired. On the sRGB control the mask is 33.68% of frame and on the linear
   one 37.41%, from the same scene. Use one geometry for both arms.
8. Mine: my 40-frame commissioning run under-dosed the treatment and I nearly
   read it as weak. On `flower-bud-...-fern-cpl` the shrink moves the mean radius
   12.54 px at 40 frames but **8.61 px at 299**, because the geometric cap
   saturates when there are few depth steps. A commissioning subset can
   misrepresent dose as well as response.

## 15. Gaps, part II

- **Aura measured on three subjects with dose, not 26.** `coffee-bean` and
  `bee-1-cpl` are near-nulls at heavy dose and `flower-bud-...-fern-cpl` moves
  +444 DN favourably. I did not test a subject where the veil is deep *and* the
  ring is strong.
- **`109MSDCF` did not test anything** (section 10.3). A placebo with a strong
  dose and no depth separation does not exist in the corpus as far as I can tell.
- **The ring at d = 22 px is now attributed to the merge rather than to tone, on
  two independent linear routes, and nobody owns that finding.** It was invisible
  in the space it was previously measured in.
- I did not re-measure the band merge's own clipping after `2981354`'s hull-clamp
  fix was routed to BUILD-BLEND, so section 9's 2.99%/1.68% figures are as of
  `38ad133` and may already be stale.
