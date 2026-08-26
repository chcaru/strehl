# V-softness: independent verification of the library-wide sharpness regression

Status: complete. Verifier: V-SOFTNESS. Subject: BUILD-RENDER.md sections 12.1-12.3,
and the proposed revert of `57e4554`.

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

- The halo cost of restoring the shrink is **unmeasured**. This is the one thing
  that could still make the revert wrong, and it needs BUILD-HALO.
- I isolated the commit on two subjects, not 26. The other 24 rest on the gallery
  comparison, which is now corroborated by four statistics but is still a two-pin
  comparison spanning 18 commits.
- Section 12.2's ladder reports 0.9376 for `859edac` on `couch-fibers-cpl` while
  section 12.1's table reports 0.9604 for what is nominally the same comparison.
  The report does not say which files the ladder was measured on. Unreconciled.
- `foam`, `leaf-2` and `lead-1` read softer on the normalised statistic and
  *sharper* on the HF fraction. Two of my instruments disagree on three subjects
  and I did not chase it.
