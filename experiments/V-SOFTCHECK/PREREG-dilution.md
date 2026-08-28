# PRE-REGISTRATION: is the N-softening a gate-clearing-competitor effect?

**Written before any statistic was computed.** Renders were already running when this
was written; rendering is not measuring, and no arm had been opened.

**Lane:** V-SOFTCHECK. **Pin:** `9b05d0b7`, binary sha256 `44C2F2CD2E5B2894...`,
verified by hash inside every render script. **Subject:** `bee-1-cpl`, 299 frames,
`--srgb --exposure 1.50` on every arm and every probe. `--auto-exposure` forbidden.

## 1. The model, verified at the pin rather than taken

`git show 9b05d0b7:crates/strehl-core/src/pyramid.rs`:

    L1359    let floor = gate * beta * v.max(0.0);
    L1360    let excess = (*e - floor).max(0.0);
    L1361    *w = select_weight(excess, floor, p);
    L2093    if excess <= 0.0 { return 0.0; }
    L2099    let r = excess / floor.max(1.0) / SNR_REF;

Confirmed: a frame whose band energy sits below its own noise floor contributes
**exactly zero** weight, so it adds no term to the normalising sum. That is the fact
the whole hypothesis rests on and it is real.

One correction to the claim as relayed. It was given as `r = excess / floor /
SNR_REF`; the pin clamps the denominator, `floor.max(1.0)`. Where `floor < 1` -- the
clamped-black pixels the comment at L2096-2098 describes -- the weight is not
scale-free and `SNR_REF` does not cancel. This does not touch the N-dependence
argument. Separately, the relayed form `(e_k / e_winner)^p` assumes `floor` is common
across frames at a pixel; the code takes each frame's own `floor`, so the true ratio
is `(excess_k/floor_k) / (excess_w/floor_w)`. Again this does not change the
counting argument, which is about how many terms the sum has.

**The prediction under test:** softening tracks *how many frames clear the gate at
the same pixel*, which is set by focus step relative to depth of field, **not** by N.

## 2. THE THREAT: both range-varying arms are confounded in favour of the model

The proposed third arm is *every 2nd frame of bee (N=150, step x2)* against *the
first 150 frames (N=150, step x1, half the range)*, with the model predicting the
step-x2 arm is sharper.

**Measured globally that arm cannot fail.** The step-x1 arm covers only frames
0-149, so every site whose focus lies in frames 150-298 is never in focus in it at
all. Those sites are catastrophically soft for a reason that has nothing to do with
dilution, and they drag the step-x1 arm down. **The confound points in exactly the
direction the model predicts.**

The same is true of the matched-step arm, in the same direction: the fewer-frames arm
is the one missing range, so its handicap reads as *the extra frames not costing
anything*, which is the model's prediction again.

**Any arm in this experiment that varies the focus RANGE is rigged toward confirming
the hypothesis unless the measurement region is restricted to depths both arms can
resolve.** This is registered as the primary threat and is the reason for section 3.

## 3. Design

Four merges. `Q` and `R` already exist from earlier lanes (`nrender.py`,
`linspace(0, 298, n)` with first/last asserted on disk).

| arm | frames | N | step | range |
|---|---|---:|---:|---|
| `S` = `R075x2` | 0,2,...,148 | 75 | 2 | 0-148 |
| `P` = `R150x1` | 0..149 | 150 | 1 | 0-149 |
| `Q` = `master-N149` | linspace(0,298,149) | 149 | 2 | 0-298 |
| `R` = `master-N299` | 0..298 | 299 | 1 | 0-298 |

**The NEAR mask.** 13 `STREHL_ONLY_FRAME` probes (k = 0,25,...,275,298) render single
bracket frames with no election through the identical pipeline. Per tile, the
argmax over probes gives a coarse focus index. `NEAR` = tiles whose focus peak is at
probe index <= 100, i.e. comfortably inside the shared range 0-149, with the 125/150
probes left as a margin so boundary tiles are excluded rather than assigned. Tiles
with no resolvable focus peak (peak/min sharpness below a fixed ratio) are excluded:
a flat tile has no depth and cannot be masked into either half honestly.
The mask is built from renders that are **not** either arm of any comparison, so no
comparison selects on its own dependent variable.

**The four comparisons**, all in the same band, on the same tiles, with the same
noise handling:

| id | comparison | held fixed | mask | model predicts |
|---|---|---|---|---|
| A1 | `S` -> `P` | range 0-149, N doubles 75->150 | NEAR | **P softer** |
| A1' | `Q` -> `R` | range 0-298, N doubles 149->299 | none needed, both full range | **R softer** |
| A2 | `P` -> `R` | **step 1**, N doubles 150->299 | NEAR | **equal** |
| A3 | `P` -> `Q` | **N ~150**, step doubles | NEAR | **Q sharper** |

A1' and A2 are the pair that matters. Both end at `R`. Both add ~150 frames. A1'
holds the range and halves the step; A2 holds the step and doubles the range. The
model predicts a large effect in one and none in the other.

## 4. Pre-registered decision rule

Let `D` be softening in dex, `D = log10( S_scene(fewer frames) / S_scene(more frames) )`
at 0.30-0.35 cyc per OUTPUT pixel (where the standing 0.114 result lives), reported
alongside 0.20-0.25 (the promotable band). `D > 0` means adding frames cost sharpness.

- **MODEL SURVIVES** if `D(A2) <= 0.35 * D(A1')`.
- **MODEL DIES** if `D(A2) >= 0.70 * D(A1')`. Adding 149 frames the model says
  contribute no term would have cost as much as halving the step.
- **INDETERMINATE** in between, and I will report it as such rather than round to
  whichever side is nearer.

The band 0.35-0.70 is deliberately wide. A narrower rule would decide this on
measurement error.

**Refusal conditions, registered now.**
- If `D(A1') <= 0.02` dex the reference effect is not present on this subject and no
  ratio is formed -- a ratio to a null denominator is not a result.
- If the NEAR mask holds fewer than 60 tiles, refuse: the mask has eaten the sample.
- If A3 and A2 disagree in sign about whether step or N drives it, report both and
  claim neither.

## 5. Noise, and the one property that makes this robust

Every sharpness number here needs a noise number on the same pixels, because more
frames means less output noise, less noise means less band energy, and **that alone
reads as softening.** The depth-softening result could be a noise artifact and this
experiment must not assume otherwise.

`S_total` is band power at the masked tiles. `S_noise` is estimated from the flattest
tiles by the 0.02-0.05 cyc/px stratifier -- a band disjoint from every reported band,
so the stratifier cannot be the thing measured -- and scaled by local mean for photon
scaling. `S_scene = S_total - S_noise`. Commissioned in both directions before use:
a **planted noise** addition must leave `S_scene` unchanged while `S_total` rises, and
a **planted blur** must lower `S_scene`. A statistic that only ever moves one way is
the failure this project has convicted twice.

**The design property:** A1' and A2 both double N by about the same amount, so
whatever noise reduction a doubling buys is present in *both*. The **difference**
`D(A1') - D(A2)` is therefore first-order insensitive to the noise term even if each
number individually is not. The decision rule is a ratio of the two for exactly this
reason. I will still report `S_total` and `S_scene` separately, and if they disagree
in sign I will refuse rather than pick.

**Standing warning reproduced by this lane already:** on a coherence statistic alone
the planted `(A+B)/2` scores perfectly while destroying 29.6% of delivered band
power. No single statistic here is allowed to stand as an acceptance criterion.

## 6. What would make me wrong

- If the flat-tile noise proxy understates noise at high-contrast NEAR tiles (photon
  noise scales with signal), `S_scene` is biased and both `D` values move together.
  Mitigated by the difference property, not eliminated.
- The probe ladder is coarse (25 frames). A tile whose true peak is at frame 110
  could be assigned to probe 100 and admitted, when `Q`'s step-2 sampling near it
  differs from `P`'s. The margin at 125/150 is there to absorb this and its width is
  registered here, not chosen later.
- `bee-1-cpl` carries 8.9 px median residual warp between independently merged
  half-stacks (this lane, `hwarp.py`). Arms merged from different subsets may sit on
  slightly different geometry. Band **power** is shift-invariant, unlike the
  coherence statistic that finding came from, so this experiment is chosen to be
  insensitive to it -- but tile-level content mismatch at large shifts is not zero
  and is registered as a known limit.
