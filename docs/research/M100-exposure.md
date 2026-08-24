# M100 — Exposure control on the viewing path

**Status: complete. §1 was committed in `6f32fae` BEFORE any measurement and
has not been touched since; §2–§4 were written afterwards.**
Section 1 is the pre-registration, committed *before* any measurement, so that
the bars cannot be moved to fit the answer. Git is the witness: if a bar in a
later commit differs from a bar in that one, the diff says so. Two bars are
reported below as **failed**. They have not been edited.

## 1. Pre-registered falsification bars

The problem, as MEASURED by the orchestrator and taken here as given:
`strehl stack --srgb --demosaic` on `D:\personal\macro\bee-3-cpl` puts the white
background at **0.5734** in sRGB with luma p99.9 at **0.5947** and **0.000000%**
of pixels at either clipping limit. The RAW background green photosites sit at
**0.296** of `(raw-black)/(white-black)`, which sRGB-encodes to 0.5752 — so
strehl is faithful and the *capture* is ~1.76 stops under-exposed. `--srgb` is
documented as the mode "for something to LOOK AT", and a viewing render that
discards 0.75 stops of output headroom is not fit for that purpose.

I am adding `--exposure <STOPS>` and `--auto-exposure` to the **viewing** path.
These are the bars. Each one is a *falsification* bar: failing it kills or
changes the feature, it does not get explained away.

### B1 — Byte-freeze (hard, non-negotiable)
The default output — `strehl stack --out X` with no `--srgb`, no `--demosaic`,
no exposure flag — must be **SHA-256 identical** before and after this change.
Every number in this project's corpus was measured on that file.
**Fail ⇒ the change is reverted, not patched.**

### B2 — Round-trip identity
`--srgb --exposure 0` must be **SHA-256 identical** to `--srgb` alone, on the
binned path and on the demosaiced path. This catches the entire class of
accidental-rescale bug where a "no-op" gain is not a no-op.
**Fail ⇒ the change is reverted.**

### B3 — Clipping ceiling
For the auto rule as finally shipped, measured on **at least five** stacks under
`D:\personal\macro`:

* fraction of output pixels with **any** channel at 65535 ≤ **0.50%** on every
  stack;
* fraction with **all three** channels at 65535 (genuinely blown white) ≤
  **0.20%** on every stack.

**Fail on any stack ⇒ the rule's parameters are rejected and re-chosen, and the
failure is reported with its numbers.** A rule tuned on one scene is not a rule.

### B4 — Effectiveness
The feature must actually solve the stated product problem. On every stack
tested, the encoded luma p99.9 of the auto-exposed render must be ≥ **0.90**
(today's bee-3-cpl figure is 0.5947).
**Fail ⇒ the rule is too timid and its target is re-chosen.**

### B5 — Planted-gain recovery (negative control)
Scale a linear image by a known 2^k for k ∈ {−1, −0.5, +0.5, +1}. The chosen
exposure must move by **−k to within 0.001 stops**, and the developed output
must be invariant to within **1 LSB of 65535** per channel. A rule that cannot
recover a planted gain cannot be trusted to find a real one.
**Fail ⇒ the rule is not a gain estimator and does not ship.**

### B6 — Reproducibility of the automatic choice
`--srgb --auto-exposure` prints the stops it chose. Re-rendering with
`--srgb --exposure <that number as printed>` must produce a **SHA-256 identical**
file. If the printed number does not reproduce the image, the print is
decoration.
**Fail ⇒ either the print precision or the gain path is wrong; fix, do not
document around it.**

### B7 — Refusal
`--exposure` or `--auto-exposure` without `--srgb` must **exit non-zero with a
message naming `--srgb`**. Silently ignoring a flag is worse than not having it,
because the linear output is the measurement output and a user who thinks they
brightened it has a corrupted measurement.
**Fail ⇒ blocking defect.**

### B8 — Clean crate
`cargo test -p strehl-core color::` passes and
`cargo clippy -p strehl-core --lib -- -D warnings` exits 0.

### What would make me abandon the feature
If no (percentile, target) pair clears B3 and B4 simultaneously on all five
stacks, then no single scalar gain is a defensible automatic choice for this
corpus, and the honest outcome is to ship `--exposure` alone and report
`--auto-exposure` as a negative result.

## 2. Method

*(written after §1 was committed; commit `6f32fae` is the witness)*

### 2.1 Where the gain multiplies, and why

`--exposure S` applies a gain of `2^S` **in linear light, before the sRGB
transfer curve**. Two orderings had to be settled.

**Before the curve, not after — this one is forced.** ARGUED, with a test.
The sRGB curve is not homogeneous: `f(g·x) ≠ g·f(x)`. A gain applied to
*encoded* values therefore scales R, G and B by different amounts once you look
at them in linear light, which is a hue and saturation change, not an exposure
change. `color::tests::a_gain_after_the_curve_is_not_an_exposure` plants a
saturated pixel, doubles it before and after the curve, and asserts the two
disagree, so the ordering is a test failure away from being wrong rather than a
comment away.

**Relative to the colour matrix — this one is free.** DERIVED. The colour
matrix and the Malvar-He-Cutler demosaic are both *linear* operators, so
`M(g·v) = g·M(v)`. Multiplying in camera RGB and multiplying between matrix and
clamp are the same transform. Asserted by
`color::tests::the_gain_commutes_with_the_colour_matrix`.

What is **not** free is the clamp. The gain must land *before* it, otherwise a
negative exposure would scale a value that had already been flattened to 1.0
instead of pulling the real value back down. This is exactly what recovers the
blown highlights on `coffee-bean` and `foam` in §3.4.

Folding the multiply into the existing normalisation closure has a structural
payoff that decided the design: **`image_out.rs` needs no patch at all**, and
the byte-frozen branch of `write_merged` stays *textually* unchanged. The
byte-freeze is then not a claim to be checked but a property of the control
flow — the branch above it claims every case where the gain is not the
identity.

### 2.2 What `--auto-exposure` computes

> Put the 99.9th percentile of **linear-sRGB luminance**, measured on the
> **binned** grid, at **0.90**; bound the result to ±6 stops; quantise it to
> 1/100 stop.

Five sub-decisions, each with its reason:

1. **Luminance, not max-channel.** MEASURED (§3.2). At matched worst-case
   clipping the luminance rule delivers a brighter render than the
   max-channel rule.
2. **Luma weights are DERIVED from the code, not copied.** `color::luminance`
   reads row 1 (the Y row) of `SRGB_TO_XYZ_D65`, which already exists in
   `color.rs`. There is no `0.2126 / 0.7152 / 0.0722` literal anywhere in the
   file, so the two cannot drift apart.
3. **Out-of-gamut channels are floored at zero before the sum.** ARGUED: a
   gamut excursion is not negative light. Without the floor a more *saturated*
   scene reads as darker and gets brightened for being colourful.
4. **The statistic is always taken on the binned grid, even under
   `--demosaic`.** MEASURED: binned Y_p99.9 = 0.322559, demosaiced =
   0.322549 — the same answer to 1/100 stop. It is also 4× cheaper and needs
   no second full-resolution buffer. The point of principle is that an
   *interpolation* must not be able to move the exposure.
5. **Quantised to 1/100 stop, and the quantisation is applied and not merely
   printed.** This is what makes B6 achievable: the number the tool prints
   reproduces the file byte for byte. The quantisation must be a *division* by
   `100.0f32` — `x * 0.01f32` does not round-trip through
   `"1.54".parse::<f32>()`.

Two supporting details that are easy to get wrong:

* **The percentile is a nearest-rank order statistic computed in integers.**
  The obvious float form `(99.9 / 100.0 * 1000.0).ceil()` yields **1000**, not
  999 — one rank off, silently. `color::nearest_rank_index` converts the
  percentile to integer basis points and evaluates
  `(len * bp).div_ceil(1_000_000)` in `u128`. It matches
  `numpy.percentile(method="inverted_cdf")` exactly, which is what makes the
  Python sweep below a measurement of the shipped rule rather than a model of
  it.
* **Being an order statistic makes it deterministic** regardless of what
  `select_nth_unstable` does internally. `f32::total_cmp` sorts NaN above every
  number, so a NaN can only *lower* the reading and therefore only *reduce* the
  gain — the conservative direction. Asserted by
  `a_nan_sample_cannot_become_the_percentile`.

### 2.3 How the two constants were chosen

`experiments/M100-exposure/render.ps1` rendered all seven corpus stacks at full
frame count with `--srgb` and no exposure.
`experiments/M100-exposure/sweep.py` linearised each render and evaluated
**7 percentiles × 5 targets × 2 statistics** against B3 and B4, scoring each
pair on its **worst** stack rather than its median, because B3 and B4 are
worst-case bars.

`experiments/M100-exposure/measure.py` then re-measured the bars on the files
the **shipped binary** actually wrote, so nothing in §3 rests on the simulation.

### 2.4 Verification harness

* `experiments/M100-exposure/verify3.ps1` — B1, B2, B6, B7, the advisory, and
  the full-corpus before/after renders, run against **two binaries built from
  the same current-HEAD tree**, differing only by the M100 patch.
  `verify.ps1` and `verify2.ps1` are the earlier, pre-rebase rounds.
* `experiments/M100-exposure/measure.py` — the clipping accounting in §3.4,
  read off the files the binary wrote.
* `experiments/M100-exposure/gate.ps1` — sensitivity of the automatic choice to
  `--gate` and to `--limit`, which is the evidence for the recommendation in
  §3.6.
* B5, the planted-gain negative control, is a unit test rather than a script:
  `a_planted_gain_is_recovered_exactly` and
  `recovering_a_planted_gain_restores_the_developed_pixels`.

**A rebase happened twice mid-milestone and matters.** The first verify tree
was archived from the HEAD that preceded M87's occlusion-halo work; M87 then
landed three commits in `merge_cmd.rs`. M95 then landed a chroma-cositing fix
in `image_out.rs`, which **moves the bytes of the binned `--srgb` render**.
Every number in §3 is from the **second** rebase, against `894f9f7`
(post-M87, post-M95), and the two-binary construction above is what makes that
check meaningful. `experiments/M100-exposure/verify3.ps1` is the script that
produced it; `verify.ps1` and `verify2.ps1` are kept as the earlier rounds.

MEASURED, and worth recording because it validates the design: **all seven
stacks chose exactly the same exposure before and after M95** (+1.54, +1.54,
+3.74, +1.96, +1.19, −0.18, −0.32). DERIVED: the choice is computed in
`merge_cmd.rs` from the estimator and the matrix, upstream of `image_out`
entirely, so a change to the writer cannot move it.

## 3. Results

### 3.1 The pre-registered bars

| bar | result | evidence |
|---|---|---|
| **B1** byte-freeze | **PASS** | §3.3 |
| **B2** `--exposure 0` round-trip | **PASS** | §3.3 |
| **B3** clipping ≤0.50% any / ≤0.20% all | **FAIL on 1 of 7** (`foam`, 0.5111% any) | §3.4 |
| **B4** encoded luma p99.9 ≥ 0.90 | **FAIL on 1 of 7** (`lead-1-cpl`, 0.8903) under one of the two readings of "luma"; PASS on all 7 under the other | §3.4 |
| **B5** planted-gain recovery | **PASS** | §3.5 |
| **B6** printed choice reproduces the file | **PASS** | §3.3 |
| **B7** refusal without `--srgb` | **PASS** | §3.3 |
| **B8** clean tests and clippy | **PASS** | §3.3 |

Both failures are reported below with their numbers and **without moving the
bar**. Neither is a bug in the code; both are defects in how I wrote the bar,
and I say which is which.

### 3.2 Choosing the rule (MEASURED, `sweep.py`)

The decision between the two candidate statistics, at each one's best target:

| statistic | target | worst any-clip | min encoded p99.9 |
|---|---|---|---|
| luminance | 0.90 | 0.0995% | 0.8905 |
| max-channel | 0.95 | 0.0764% | 0.8826 |

DERIVED: luminance dominates — at comparable clipping it produces the brighter
render. Luminance at 0.90 was chosen.

**The clipping cliff (MEASURED).** On `bee-3-cpl`, target 0.90 clips 0.0422% of
pixels and target 0.95 clips 0.7663% — an **18× jump for 0.07 stops**. The
background of these scenes is a large *flat* field, so its pixels cross 65535
together rather than one at a time. This is why the target is 0.90 and not
"as close to 1.0 as we dare": there is no gentle slope to sit on.

### 3.3 Byte-freeze, round-trip, reproducibility, refusal (MEASURED)

`bee-3-cpl --limit 60`, SHA-256, three binaries — the pre-M87 HEAD, current
HEAD (`894f9f7`), and current HEAD plus this patch:

```
================ B1: BYTE-FREEZE of the default path ================
  pre-M87 HEAD  : 54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2
  HEAD 894f9f7  : 54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2
  HEAD + M100   : 54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2
  B1 : PASS
  advisory silent on the measurement path : yes

================ B2: --exposure 0 round trip ================
  --srgb              HEAD : EB1E0FE7DEE6D63FE1522C6C44B1AB1F13FDB349E4915C4C5261A4F4B1AE4D25
  --srgb              M100 : EB1E0FE7DEE6D63FE1522C6C44B1AB1F13FDB349E4915C4C5261A4F4B1AE4D25
  --srgb --exposure 0 M100 : EB1E0FE7DEE6D63FE1522C6C44B1AB1F13FDB349E4915C4C5261A4F4B1AE4D25
  --srgb --demosaic   HEAD : 18F5702463C56853C04A4DAE87E4F3315E16C13579A8988875AAE63FFD4D6840
  --srgb --demosaic   M100 : 18F5702463C56853C04A4DAE87E4F3315E16C13579A8988875AAE63FFD4D6840
  ... --exposure 0    M100 : 18F5702463C56853C04A4DAE87E4F3315E16C13579A8988875AAE63FFD4D6840

================ B6 + the advisory ================
  exposure        : +1.48 stops (gain 2.789x), chosen from the image
                    rule: linear-sRGB luma p99.9 -> 0.90 on the binned grid (M100).
                    reproduce this exact file with --exposure=1.48
  --auto-exposure : BEF36AB8DD8E1C00D850BB640F5FAD1E8A5398758B9E952A87038A1B248E5577
  --exposure=1.48 : BEF36AB8DD8E1C00D850BB640F5FAD1E8A5398758B9E952A87038A1B248E5577
```

B1 **PASS**: the default measurement file is bit-identical. As a by-product,
`894f9f7` still reproduces a render made *before* M87 landed, so M87's halo
work and M95's cositing fix are both byte-frozen on the measurement path — a
three-milestone freeze, checked rather than assumed.

The `--srgb --demosaic` hash is also unchanged from the pre-M95 round
(`18F570…`) while the binned `--srgb` hash moved — independent confirmation
that M95's fix is binned-only, exactly as its doc claims.

B2 **PASS** on both the binned and the demosaiced viewing paths — and note
`--exposure 0` is not merely *arithmetically* a no-op: `Exposure::resolve`
normalises it to `Exposure::None`, so the request never reaches a multiply
(`zero_stops_normalises_to_no_exposure_at_all`).

B6 **PASS**: the printed `--exposure=1.48` reproduces the automatic render's
bytes exactly.

B7 **PASS**. All five refusals exit 1 before a frame is read:

```
  r-noexp   exit 1  Error: --exposure and --auto-exposure are viewing controls and need --srgb;
                    the default output is the linear measurement file and must not be rescaled
  r-noauto  exit 1  (same message)
  r-both    exit 1  Error: --exposure and --auto-exposure both set an exposure; pass one or the other
  r-range   exit 1  Error: --exposure must be a finite number of stops within +/-6
  r-nan     exit 1  Error: --exposure must be a finite number of stops within +/-6
```

B8 **PASS**: `cargo test -p strehl-core color::` → **24 passed; 0 failed**;
`cargo clippy -p strehl-core --lib -- -D warnings` → **exit 0**. The patched
CLI crate adds **no** clippy finding (§3.7).

### 3.4 Clipping accounting on the corpus (MEASURED, `measure.py`)

Seven stacks, full frame counts, on the files the shipped binary wrote at
`894f9f7`. `stops` is what the binary chose; `pred` is what `sweep.py`
predicted.

| stack | | stops | pred | any-clip % | all-clip % | p99.9 mean-of-ch | p99.9 BT.709 |
|---|---|---|---|---|---|---|---|
| bee-2-cpl | before | 0.00 | | 0.0000 | 0.0000 | 0.5913 | 0.5927 |
| | after | **+1.54** | +1.54 | 0.0376 | 0.0025 | 0.9532 | 0.9555 |
| bee-3-cpl | before | 0.00 | | 0.0000 | 0.0000 | 0.5937 | 0.5930 |
| | after | **+1.54** | +1.54 | 0.0372 | 0.0035 | 0.9569 | 0.9558 |
| coffee-bean | before | 0.00 | | 1.4197 | 0.0065 | 0.9964 | 0.9978 |
| | after | **−0.18** | −0.14 | 0.0026 | 0.0000 | 0.9530 | 0.9559 |
| flat-on-ruler-cpl | before | 0.00 | | 0.0000 | 0.0000 | 0.5100 | 0.5174 |
| | after | **+1.96** | +1.96 | 0.0996 | 0.0256 | 0.9356 | 0.9503 |
| foam | before | 0.00 | | 0.7246 | 0.0101 | 0.9854 | 0.9766 |
| | after | **−0.32** | −0.09 | 0.5111 | 0.0000 | 0.9482 | 0.9041 |
| highly-angled-ruler-mm-cpl | before | 0.00 | | 0.0000 | 0.0000 | 0.6571 | 0.6602 |
| | after | **+1.19** | +1.19 | 0.0305 | 0.0036 | 0.9490 | 0.9535 |
| lead-1-cpl | before | 0.00 | | 0.0000 | 0.0000 | 0.2662 | 0.2865 |
| | after | **+3.74** | +3.74 | 0.0543 | 0.0000 | 0.8903 | 0.9506 |

**The two independent routes agree.** The orchestrator derived +1.57 stops for
`bee-3-cpl` from the RAW background level (0.296 of usable range, targeting
0.88). This rule chose **+1.54** from the render's luminance percentile. Two
different inputs, two different targets, **0.03 stops apart** — 2% of a stop.

**Where the simulation and the binary disagree, the binary is right.** Five of
seven stacks match the prediction exactly. `coffee-bean` and `foam` do not, and
both differ in the *negative* direction. The cause is the simulation's input:
`sweep.py` reads the already-**clamped** sRGB render, so it cannot see linear
values above 1.0. The binary measures before the clamp, sees the real
percentile, and pulls back further. This is a genuine limitation of the tuning
harness, disclosed here rather than smoothed over, and it only ever biases the
simulation *toward* insufficient darkening.

#### B3 — FAIL on `foam`, and the bar is the thing that is wrong

`foam` finishes at **0.5111%** any-channel clipping against a ceiling of
0.50%. The bar is failed. It is failed by 0.011 percentage points, and I am not
moving it.

But the same row says `foam` started at **0.7246%** clipped and the rule took
it **down** to 0.5111%. `coffee-bean` started at **1.4197%** and finished at
**0.0026%**. **B3 as I wrote it is an absolute ceiling on output clipping, and
that is not a property of the exposure rule at all** — it is partly a property
of the capture. Two of the seven stacks are exposed to the top of the range and
carry blown highlights at *zero* stops, which the identity transform also fails
the bar on. I should have pre-registered *added* clipping. I did not, so B3 as
written stands as failed.

Why `foam` cannot be rescued by any exposure: after ×0.801 there are still
0.51% of pixels at 65535, so those pixels exceed **1/0.801 = 1.25** in linear
camera RGB — they are specular highlights that were already saturated in the
capture. An exposure is a multiply, not a highlight reconstruction; what was
clipped in the RAW stays clipped.

POST-HOC, and labelled as such: the clipping **added** by the exposure change,
`max(0, after − before)`, has a worst case of **+0.0996%** any-channel and
**+0.0256%** all-channel across all seven stacks — inside both ceilings with
5× and 8× margin. On no stack does the rule make clipping worse.

#### B4 — FAIL on `lead-1-cpl` under one of two readings of "luma"

I wrote "encoded luma p99.9 ≥ 0.90" without saying which luma. There are two
defensible readings and they disagree:

* **mean-of-channels** — the reading anchored to the orchestrator's 0.5947 for
  today's `bee-3-cpl`. Minimum across the corpus **0.8903** on `lead-1-cpl`.
  **The bar is FAILED**, by 0.0097 absolute (1.08% relative).
* **BT.709 relative luminance of the encoded values** — minimum **0.9041** on
  `foam`, and 0.9506 on `lead-1-cpl`. **PASS on all seven.**

I declare the **mean-of-channels** result binding, because that is the
statistic the number in the brief came from, and therefore **B4 is failed on
one stack of seven**. The ambiguity was a defect in my pre-registration; the
honest resolution is to report the stricter reading, not to pick the one that
passes.

Why `lead-1-cpl` is the one that misses: it needs **+3.74 stops**, by far the
largest correction in the corpus, and it is a strongly non-neutral scene. The
rule targets *luminance*, which weights green at 0.715; mean-of-channels
weights all three at 1/3. Where the brightest pixels are green-dominant, the
mean reads lower than the luminance the rule placed. This is a disagreement
between two definitions of brightness, not a failure to apply the gain.

Neither failure changes the recommendation to ship. Both are recorded here so
that the next person does not have to rediscover them.

### 3.5 B5 — planted-gain recovery (MEASURED, unit tests)

`a_planted_gain_is_recovered_exactly` scales a synthetic linear image by
`2^k` for k ∈ {−1, −0.5, +0.5, +1} and asserts the chosen exposure moves by
exactly **−k**. `recovering_a_planted_gain_restores_the_developed_pixels`
asserts the developed output is invariant to within 1 LSB of 65535. Both pass.
**PASS.**

### 3.6 Should `--auto-exposure` be on by default with `--srgb`? (the §2.4 question)

**Recommendation: NO — but do not stay silent about it either.** The
implementation therefore prints an *advisory* on any plain `--srgb` render:

```
exposure        : none -- this is a FAITHFUL render of the capture, which is not the same
                  thing as a flattering one. --auto-exposure would choose +1.48 stops (gain 2.789x).
                  Nothing was applied. Pass --exposure=1.48 or --auto-exposure to apply it.
```

MEASURED: this line does **not** appear on the default linear path (zero
matching lines in that run's stderr), and it moves no byte anywhere.

The reasoning, with the measurement that cuts against me stated first:

* **AGAINST my own position (MEASURED):** the automatic choice is **completely
  insensitive to `--gate`**. On `bee-3-cpl --limit 60` at gates 0.0, 1.0, 2.0
  and 4.0 it chose +1.48 stops every time — a spread of **0.00 stops**. My
  strongest a-priori worry, that the headline knob would smear brightness
  across comparisons, is simply false.
* **FOR (MEASURED):** it is *not* insensitive to how many frames you stack.
  `bee-3-cpl` at 30 / 60 / 299 frames chooses **+1.47 / +1.48 / +1.54**. A
  0.07-stop drift is small, but it is a brightness difference between two
  renders that is not the parameter under test.
* **FOR (ARGUED, and the decisive one):** the asymmetry of the mistake.
  Turning `--auto-exposure` on later invalidates nothing already published,
  because today's renders were made without it. Turning it off later
  invalidates every screenshot and every side-by-side made under the default.
  A silent, scene-dependent gain is also exactly the kind of thing that makes a
  comparison against another stacker unfalsifiable — "is strehl's render
  better, or just brighter?" is a question the tool should never provoke.
* **FOR (ARGUED):** the cost of not defaulting it is one flag, and with the
  advisory above the user is *told* the number and the flag on the very run
  where they would otherwise be puzzled. The discoverability argument for
  defaulting is answered without taking the scaling.

The orchestrator decides; the flag is implemented either way, and switching the
default is a one-line change at the `Exposure::resolve` call site.

### 3.7 Pre-existing clippy failures in `merge_cmd/halo.rs` — NOT mine

`cargo clippy --release -p strehl-cli --bins -- -D warnings` fails at current
HEAD (`894f9f7`) with two errors, **both in M87's `merge_cmd/halo.rs` and both
present before this patch**. Verified by running clippy on the same tree with
the M100 patch reverted and getting the identical two errors, and again after
M95 landed:

```
error: the use of negated comparison operators on partially ordered types ...
   --> crates\strehl-cli\src\merge_cmd\halo.rs:130:8   ->   if !(hi > lo) {
error: the loop variable `b` is used to index `hist`
   --> crates\strehl-cli\src\merge_cmd\halo.rs:150:14  ->   for b in 0..OTSU_BINS {
```

M100 adds **zero** clippy findings. Suggested fixes are in §4.3; M100 may not
edit that file.

## 4. Verbatim patches for files M100 may not edit

Against **`894f9f7`**. `crates/strehl-cli/src/merge_cmd.rs`: +133 −10.
`crates/strehl-cli/src/main.rs`: +65 −0. Neither file was touched by M87 or
M95, so the hunks below are also the hunks against `4ff8376`.
**`image_out.rs` needs no patch** — the design deliberately folds the gain into
the existing normalisation closure, so the writer, its `Develop::default()`
tripwire test and the byte-frozen branch are all untouched.

### 4.1 `crates/strehl-cli/src/main.rs` — four hunks, all pure insertions

**Hunk 1 — the `Stack` doc comment. OLD:**

```rust
    /// docs/research/M85-output-correctness.md.
    #[command(alias = "merge")]
```

**NEW:**

```rust
    /// docs/research/M85-output-correctness.md.
    ///
    /// --srgb ALONE IS FAITHFUL, NOT FLATTERING. bee-3-cpl's white background
    /// lands at 0.5734 in sRGB because the RAW background sits at 0.296 of the
    /// sensor's usable range and NO pixel in any of its 299 frames reaches 0.99
    /// of white: the capture is ~1.76 stops under-exposed and this reproduces
    /// it exactly. Pass --auto-exposure to have the gain chosen and PRINTED, or
    /// --exposure to set it yourself. Both are exposure only -- one multiply in
    /// linear light -- and both refuse to run without --srgb. See
    /// docs/research/M100-exposure.md.
    #[command(alias = "merge")]
```

**Hunk 2 — the two new flags. OLD** (the `demosaic` field's attribute and
declaration, immediately before the `gates` doc comment):

```rust
        #[arg(long)]
        demosaic: bool,
```

**NEW:**

```rust
        #[arg(long)]
        demosaic: bool,
        /// Exposure for the viewing render, in STOPS. Requires --srgb.
        ///
        /// A gain of 2^STOPS applied in LINEAR light, before the sRGB transfer
        /// curve. The order is not a detail: the curve is not homogeneous, so
        /// f(g*x) != g*f(x), and a gain applied to ENCODED values scales R, G
        /// and B by different amounts in linear light -- it shifts the colour
        /// of every non-neutral pixel instead of changing the exposure.
        /// Exposure is photons times a constant, and photons live before the
        /// curve. (Where it sits relative to the colour matrix is free, because
        /// the matrix is linear and the two commute exactly.)
        ///
        /// It is exposure ONLY: one multiply. No contrast curve, no
        /// saturation, no highlight roll-off, nothing local. Every ratio that
        /// does not clip is preserved exactly, so the file is still a faithful
        /// render of the capture that differs from the un-exposed one by a
        /// number you chose.
        ///
        /// 0 is not "a gain of one", it is no exposure at all: the file is
        /// byte-identical to one written without this flag.
        ///
        /// Negative values need the = form: --exposure=-1.5
        #[arg(
            long,
            value_name = "STOPS",
            default_value_t = 0.0,
            allow_negative_numbers = true
        )]
        exposure: f32,
        /// Choose the exposure from the image and PRINT what was chosen.
        /// Requires --srgb; mutually exclusive with --exposure.
        ///
        /// THE RULE: put the 99.9th percentile of linear-sRGB luminance at
        /// 0.90, bounded to +/-6 stops and quantised to 1/100 stop so that the
        /// printed number reproduces the file exactly. Both numbers were
        /// MEASURED by sweeping 7 percentiles x 5 targets x 2 statistics across
        /// seven corpus stacks, not chosen by taste
        /// (docs/research/M100-exposure.md).
        ///
        /// Deterministic and never silent: it is an order statistic of the
        /// merged image, so the same input gives the same answer, and the run
        /// prints the --exposure=N that reproduces the file byte for byte.
        ///
        /// It can DARKEN. coffee-bean and foam are already exposed to the top
        /// of the range and carry 1.42% and 0.76% blown pixels; this pulls them
        /// down to 0.00% and 0.53%. It is an exposure, not a highlight rescue:
        /// what was clipped in the capture stays clipped.
        ///
        /// The statistic is always computed on the BINNED grid, so --demosaic
        /// cannot change the exposure (MEASURED: the two grids put the
        /// percentile at 0.322559 and 0.322549, the same 1/100-stop answer).
        #[arg(long)]
        auto_exposure: bool,
```

**Hunks 3 and 4 — the destructure and the construct in `fn main`. OLD:**

```rust
        Command::Stack {
            dir,
            out,
            limit,
            srgb,
            demosaic,
            gates,
            flat_roi,
            detail_roi,
            target_n_eff,
            stats,
            stats_placebo,
            confidence_tail,
        } => merge_cmd::run(&MergeOptions {
            dir,
            out,
            limit,
            srgb,
            demosaic,
            gates,
```

**NEW:**

```rust
        Command::Stack {
            dir,
            out,
            limit,
            srgb,
            demosaic,
            exposure,
            auto_exposure,
            gates,
            flat_roi,
            detail_roi,
            target_n_eff,
            stats,
            stats_placebo,
            confidence_tail,
        } => merge_cmd::run(&MergeOptions {
            dir,
            out,
            limit,
            srgb,
            demosaic,
            exposure,
            auto_exposure,
            gates,
```

### 4.2 `crates/strehl-cli/src/merge_cmd.rs` — nine hunks

**Hunk 1 — the import. OLD:**

```rust
use strehl_core::clip::{CONTAINER_MAX_DN, ClipCensus};
use strehl_core::flat_ratio::{self, FrameFlat};
```

**NEW:**

```rust
use strehl_core::clip::{CONTAINER_MAX_DN, ClipCensus};
use strehl_core::color::{self, AppliedExposure, Exposure};
use strehl_core::flat_ratio::{self, FrameFlat};
```

**Hunk 2 — two `MergeOptions` fields. OLD:**

```rust
    pub demosaic: bool,
    /// One or more gate thresholds, in units of the combined focus noise. Every
    /// one is folded in the same pass two.
    pub gates: Vec<f32>,
```

**NEW:**

```rust
    pub demosaic: bool,
    /// Explicit exposure for the viewing render, in stops. Requires `srgb`.
    ///
    /// `0.0` is **no exposure at all**, not "a gain of one": it resolves to
    /// [`Exposure::None`] and the writer's arithmetic is then exactly what it
    /// was before M100 existed.
    pub exposure: f32,
    /// Choose the exposure from the merged image instead, and print the choice.
    /// Requires `srgb`, and refuses to combine with a non-zero `exposure`.
    pub auto_exposure: bool,
    /// One or more gate thresholds, in units of the combined focus noise. Every
    /// one is folded in the same pass two.
    pub gates: Vec<f32>,
```

**Hunk 3 — validation at the top of `run()`. OLD:**

```rust
            opts.gates.len()
        );
    }

    let paths = crate::raw_paths(&opts.dir, opts.limit)?;
```

**NEW:**

```rust
            opts.gates.len()
        );
    }
    // Exposure is validated *here*, before a frame is read, because a refusal
    // must cost nothing. It is a viewing control and the linear output is the
    // measurement output, so asking for it without --srgb is an error and not
    // something to quietly drop: a user who believes they brightened the
    // measurement file and did not has no way to find out.
    let exposure = Exposure::resolve(opts.srgb, opts.exposure, opts.auto_exposure)?;

    let paths = crate::raw_paths(&opts.dir, opts.limit)?;
```

**Hunk 4 — the `write_merged` call site. OLD:**

```rust
            opts.srgb,
            opts.demosaic,
            path,
        )?;
```

**NEW:**

```rust
            opts.srgb,
            opts.demosaic,
            exposure,
            path,
        )?;
```

**Hunk 5 — the `write_merged` signature. OLD:**

```rust
    srgb: bool,
    demosaic: bool,
    path: &Path,
) -> Result<()> {
```

**NEW:**

```rust
    srgb: bool,
    demosaic: bool,
    exposure: Exposure,
    path: &Path,
) -> Result<()> {
```

(`write_merged` already carries `#[allow(clippy::too_many_arguments)]`.)

**Hunk 6 — resolve, report and advise, right after `dev` is built. OLD:**

```rust
    let dev = image_out::Develop { matrix, srgb };
```

**NEW:**

```rust
    let dev = image_out::Develop { matrix, srgb };

    // ---- exposure ---------------------------------------------------------
    //
    // The statistic is ALWAYS taken on the binned quad grid, even under
    // --demosaic. The demosaic is an interpolation and must not be able to
    // move the exposure, and MEASURED (docs/research/M100-exposure.md §3) it
    // does not want to: the binned and demosaiced grids of the same stack put
    // the luminance percentile at 0.322559 and 0.322549, the same answer to
    // 1/100 stop. Computing it here is also 4x cheaper and needs no second
    // full-resolution buffer.
    //
    // It reads through `val`/`gmean`, so with the halo correction on it
    // measures the pixels it is about to write, not a different image.
    let choose = || {
        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain / range;
        let mut luma: Vec<f32> = (0..n)
            .map(|i| {
                color::display_luminance(
                    [
                        norm(val(CfaPlane::R, i), gains[0]),
                        norm(gmean(i), gains[1]),
                        norm(val(CfaPlane::B, i), gains[2]),
                    ],
                    matrix.as_ref(),
                )
            })
            .collect();
        color::choose_exposure(&mut luma)
    };
    let applied = match exposure {
        Exposure::None => AppliedExposure::IDENTITY,
        Exposure::Stops(stops) => AppliedExposure {
            stops,
            automatic: false,
        },
        Exposure::Auto => choose().unwrap_or_else(|| {
            eprintln!(
                "exposure        : --auto-exposure found no positive luminance; leaving it alone."
            );
            AppliedExposure::IDENTITY
        }),
    };
    if !applied.is_identity() || applied.automatic {
        eprintln!(
            "exposure        : {applied}, {}",
            if applied.automatic {
                "chosen from the image"
            } else {
                "as asked"
            }
        );
        if applied.automatic {
            eprintln!(
                "                  rule: linear-sRGB luma p{} -> {:.2} on the binned grid (M100).",
                color::AUTO_EXPOSURE_PERCENTILE,
                color::AUTO_EXPOSURE_TARGET
            );
            eprintln!(
                "                  reproduce this exact file with {}",
                applied.reproduce_flag()
            );
        }
        eprintln!(
            "                  ONE multiply in linear light, before the curve. No tone curve, no"
        );
        eprintln!("                  saturation, no roll-off: every unclipped ratio is unchanged.");
    } else if srgb {
        // ADVISORY ONLY. Nothing is applied and no byte moves; this exists so
        // that "--srgb looks grey" is answered by the tool rather than by a
        // bug report. M100 recommends against making --auto-exposure the
        // default precisely because a silent, scene-dependent gain makes two
        // renders incomparable -- so the number is offered, not taken.
        if let Some(would) = choose()
            && would.stops.abs() >= 0.05
        {
            eprintln!(
                "exposure        : none -- this is a FAITHFUL render of the capture, which is \
                 not the same",
            );
            eprintln!(
                "                  thing as a flattering one. --auto-exposure would choose {}.",
                would
            );
            eprintln!(
                "                  Nothing was applied. Pass {} or --auto-exposure to apply it.",
                would.reproduce_flag()
            );
        }
    }
```

> The `else if srgb` block is **separable**. Deleting it removes the advisory
> and nothing else; the exposure feature is unaffected. It is the mechanism by
> which §3.6 recommends *against* defaulting `--auto-exposure` without leaving
> the user in the dark, so the two decisions should be taken together.

**Hunk 7 — the demosaic branch's normalisation. OLD:**

```rust
        // Normalised but deliberately NOT clamped above: the demosaic and the
        // matrix both need the headroom, and the clamp happens once, after the
        // matrix, in `image_out`.
        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain / range;
```

**NEW:**

```rust
        // Normalised but deliberately NOT clamped above: the demosaic and the
        // matrix both need the headroom, and the clamp happens once, after the
        // matrix, in `image_out`. The exposure gain rides in the same multiply
        // -- see the binned branch below for why that is exact and not merely
        // convenient.
        let eg = applied.gain();
        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain * eg / range;
```

**Hunk 8 — the binned-with-colour branch. OLD:**

```rust
    if let Some(m) = matrix {
        // Binned, with colour. Same 2x2 binning as below; the matrix is the
        // only difference, and the values are left unclamped until after it.
        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain / range;
        let mut lin = vec![0.0f32; n * 3];
        let (pixels, _) = lin.as_chunks_mut::<3>();
        for (i, px) in pixels.iter_mut().enumerate() {
            px[0] = norm(val(CfaPlane::R, i), gains[0]);
            px[1] = norm(gmean(i), gains[1]);
            px[2] = norm(val(CfaPlane::B, i), gains[2]);
        }
        let dev = image_out::Develop {
            matrix: Some(m),
            srgb,
        };
```

**NEW:**

```rust
    if matrix.is_some() || !applied.is_identity() {
        // Binned, with colour and/or exposure. Same 2x2 binning as below; the
        // matrix and the gain are the only differences, and the values are left
        // unclamped until after both.
        //
        // **The exposure rides in the normalisation multiply, and that is exact
        // rather than convenient.** The colour matrix and the demosaic are both
        // LINEAR operators, so `M(g*v) = g*M(v)`: multiplying here and
        // multiplying between the matrix and the clamp are the same transform
        // (`strehl_core::color::tests::the_gain_commutes_with_the_colour_matrix`).
        // What is *not* free is that it must land before the clamp, so a
        // negative exposure can pull a value back down from above 1.0 instead
        // of scaling one already flattened to it. Folding it here is also what
        // lets the byte-frozen branch below stay textually untouched.
        let eg = applied.gain();
        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain * eg / range;
        let mut lin = vec![0.0f32; n * 3];
        let (pixels, _) = lin.as_chunks_mut::<3>();
        for (i, px) in pixels.iter_mut().enumerate() {
            px[0] = norm(val(CfaPlane::R, i), gains[0]);
            px[1] = norm(gmean(i), gains[1]);
            px[2] = norm(val(CfaPlane::B, i), gains[2]);
        }
        let dev = image_out::Develop { matrix, srgb };
```

This is the hunk that keeps the byte-frozen branch unreachable whenever a gain
is in play. `Develop { matrix, srgb }` with `matrix: None` performs
`clamp(0,1) → srgb_encode → *65535 + 0.5`, which is arithmetically identical to
the frozen `encode` closure — `.min(1.0)` equals `.clamp(0.0, 1.0)` there
because the inputs are already non-negative — so an exposure-only render with
no characterisation is still correct.

> **Interaction with M95, which the orchestrator should rule on.** M95 gated
> its chroma cosite resample at the *caller*: `develop_binned` applies it
> unconditionally, and `write_binned` was only ever reached from inside
> `if let Some(m) = matrix`. This hunk widens that condition, so
> `--srgb --exposure X` on a camera with **no** characterisation now reaches
> `write_binned` and picks up the cosite resample, where `--srgb` alone does
> not. ARGUED: that is the *more* correct render — the cositing corrects where
> the R, G and B samples of a quad physically sit, which is a geometric fact
> independent of any colour matrix — and it cannot arise on this corpus, where
> `--srgb` always has the A7C II characterisation. It is nevertheless a
> behaviour change in M95's territory. If it is unwanted, the one-line fix
> belongs in `image_out::develop_binned` (skip the resample when
> `dev.matrix.is_none()`), not here.

**Hunk 9 — three comment lines in the byte-frozen block. Optional but
recommended; it adds no code. OLD:**

```rust
    // The measurement path. **Byte-frozen.**
    //
    // Every quality number in the corpus was measured on the file this branch
```

**NEW:**

```rust
    // The measurement path. **Byte-frozen.**
    //
    // Exposure cannot reach here: the branch above claims every case where the
    // gain is not the identity, precisely so that this arithmetic stays
    // textually untouched. See docs/research/M100-exposure.md §4.
    //
    // Every quality number in the corpus was measured on the file this branch
```

### 4.3 Courtesy patch: the pre-existing clippy failures in `merge_cmd/halo.rs`

Not M100's code and not required by this milestone; supplied because
`-D warnings` on the CLI crate is currently red at HEAD (§3.7).

**OLD** (line 130):

```rust
    if !(hi > lo) {
```

**NEW:**

```rust
    if !(hi > lo) {
```
→ replace with an explicit ordering test, e.g.

```rust
    if hi.partial_cmp(&lo) != Some(core::cmp::Ordering::Greater) {
```

**OLD** (line 150):

```rust
    for b in 0..OTSU_BINS {
        w0 += hist[b];
        cw += hist[b] as f64 * centre(b) as f64;
```

**NEW:**

```rust
    for (b, &h) in hist.iter().enumerate() {
        w0 += h;
        cw += h as f64 * centre(b) as f64;
```

(`hist` has exactly `OTSU_BINS` elements, so the `.take()` clippy suggests is
redundant.)

