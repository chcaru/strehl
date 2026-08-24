# M109 — blown highlights render magenta

**Status: FIXED on the paths I own; BLOCKED from the shipped default by file ownership.**
Pre-registration: `experiments/M109-highlights/PREREGISTRATION.md`, written before any build or render.

---

## 1. The render path, read from source

`strehl stack` does **not** go through `stack.rs`. `main.rs:410` dispatches it to `merge_cmd::run` →
`merge_cmd::write_merged` (`merge_cmd.rs:2733`). `stack.rs` serves `argmax-baseline`. Both writers
share `image_out`. The order, for `--srgb` (which implies `--demosaic`):

1. `norm(raw, gain) = (raw - levels.black).max(0.0) * gain * exposure_gain / levels.range()`,
   where `range = white - black = 15360 - 512 = 14848`. **Deliberately not clamped above.**
2. Malvar–He–Cutler demosaic (`image_out::write_demosaiced`), or Keys co-siting
   (`image_out::develop_binned`, red `+0.25`, blue `-0.25`) under `--binned`.
3. `color::apply(matrix, lin)` — camera RGB → linear sRGB.
4. `clamp(0, 1)`.
5. `color::srgb_encode`, then `(x * 65535 + 0.5) as u16`.

**black → as-shot green-normalised WB → exposure gain → resample → matrix → clamp → curve → quantise.**
MEASURED, in the sense that the binary says so itself — `stack --srgb` prints
`Order: black, as-shot WB, demosaic, matrix, clamp, sRGB curve.`, which agrees with the source read.

The only clamp is at step 4, **after** the matrix. `image_out.rs`'s module doc defends that placement
and is right to: the matrix has negative off-diagonal terms and legitimately drives a saturated
scene colour out of gamut, so clamping before it would shift hue. It is wrong only for a sample that
is not a colour measurement at all.

## 2. Mechanism (MEASURED, and independently reconfirmed)

`Levels::white` is 15360 but the sample container saturates at `CONTAINER_MAX_DN = 16383`. `clip.rs`
says in bold that these are different numbers and must not be unified. They are, and this fix uses
both for what each one is. A container-pinned sample therefore lands not at 1.0 but at

    K0 = (16383 - 512) / (15360 - 512) = 1.068898

times its WB gain and the exposure gain. Green's as-shot gain is 1.0 by construction; red's is 2.687
and blue's 1.532. Green stops at `1.0689 x eg` while white balance carries red to `2.87 x eg` and
blue to `1.64 x eg`. The matrix's green row `[-0.1152, +1.4890, -0.3738]` is then dominated by the
two unpinned terms, green lands below 1, red and blue clamp at 1 — **magenta**.

I re-derived ORCH's population independently, with `rawpy`/LibRaw, letting the predicate
"both greens of the quad at `CONTAINER_MAX_DN`" find the region rather than typing in an ROI
(`experiments/M109-highlights/src/libraw_crosscheck.py`). 583 873 quads, 7.09 % of `DSC00150.ARW`:

| channel | mean raw DN | at saturation |
|---|---|---|
| R | 7186.0 | 0.00 % |
| G1 | 16383.0 | 100.00 % |
| B | 13184.9 | 0.00 % |
| G2 | 16383.0 | 100.00 % |

Same shape as ORCH's hand-placed region (R 7673.2, B 14116.0); the small differences are the
difference between a sub-region and the whole predicate-selected population. **The mechanism ORCH
measured is confirmed, not refuted.**

LibRaw also reports this body's white level as **16383** — it normalises by the container maximum,
which is exactly why its pinned samples land at 1.0 and clip together instead of shearing apart.

## 3. The fix

**Where any channel is at or above its own container ceiling, clamp every channel to the neutral
ceiling, in white-balanced camera space, before the matrix. Elsewhere, identity.**

```
ceil_c = K0 * gain_c * exposure_gain
K      = min_c ceil_c
if any_c ( v_c >= ceil_c )  then  v_c := min(v_c, K)   for all c
```

`color::Render` (new) carries the matrix and the ceiling together, because they are one decision:
the type is what stops a caller supplying the matrix and silently forgetting the ceiling.
`color::saturation_ceiling` computes it from `Levels`, the WB gains and the exposure gain.

Three properties, all asserted in `color.rs`'s tests rather than argued:

* **Blown neutral renders neutral.** Every row of `camera_to_srgb` sums to 1, so an equal-channel
  input is an equal-channel output by construction. All three channels of a blown neutral are above
  `K`, so all three land on `K` exactly.
* **The null is an identity, not an observation.** Where nothing is pinned the branch never fires,
  so an unsaturated stack cannot move by one bit. This is why the fix is *conditional*: an
  unconditional clamp at `K` would clip real red above about 6420 DN and real blue above 10863 DN,
  and `109MSDCF`'s maxima are 39–61 % of white, so it would have eaten live data.
* **The ceiling commutes with the exposure gain**, `clip_{K*g}(g*v) == g*clip_K(v)`, so folding the
  gain into `norm` is still valid and the fix does not depend on where the exposure was applied.

**Cost, stated plainly.** At a pinned pixel the headroom above `K` in the unpinned channels is
discarded, which slightly desaturates a strongly clipped colour — `mechanism.py` prices a pinned
red at green rising `0.0000 → 0.2681`. A pinned channel is not a measurement of how saturated the
object was; keeping that headroom would be fabricating saturation the sensor never recorded.

### Alternatives rejected

1. **Clamp camera space at 1.0 as well.** Rejected on measurement. At `eg = 1` it happens to work,
   but the defect is exposure-dependent, so a fixed 1.0 is the right ceiling at exactly one
   exposure. It also discards more in-gamut headroom than `K` does.
2. **Post-matrix desaturation keyed on out-of-gamut output.** Rejected: after the matrix a blown
   neutral and a genuinely magenta object are indistinguishable. The ceiling is the only thing that
   still carries "this was pinned".
3. **Data-derived ceiling (green histogram plateau).** Rejected as too clever for the evidence: it
   swaps two numbers the decoder knows exactly for an estimator with real failure modes (partial
   pinning across 299 frames, G1/G2 averaging, plateaus that are not clipping).
4. **Highlight reconstruction.** Recovers detail instead of discarding it, but invents pixels the
   sensor never measured and needs a neighbourhood pass plus validation this milestone cannot
   afford. Recorded as follow-up, not attempted.

## 4. Bars, as written

Every render below: `CARGO_TARGET_DIR=...\.cargo-target-m109`, `STREHL_ALIGN` unset,
`STREHL_FIX_HALO` unset, `STREHL_WARPMAP` unset, `$ErrorActionPreference="Continue"`, tree at
`2c13138b4ac6b5e5588ae3f40ebbd001de8e2ce3` plus this milestone's edits. "before" and "after" are the
**same source tree** built twice, differing only in whether `saturation_ceiling` returns a ceiling
or `+inf`.

### B1 — headline: magenta must go

Predicate, ORCH's, verbatim: on the 16-bit output over `/65535`, `(R-G > 0.06) && (B-G > 0.06)`,
whole frame, no ROI.

**B1-stack — BLOCKED, as declared in advance.** The fix cannot reach `merge_cmd.rs` (§6). Running
ORCH's exact command with my binary reproduces the defect *and* validates my harness against ORCH's
independent measurement:

| statistic | ORCH | this harness |
|---|---|---|
| magenta fraction | 2.002 % | **2.0017 %** |
| max(R-G) | 0.4490 | **0.4490** |
| magenta mean RGB | 0.9944 / 0.8915 / 0.9943 | **0.9944 / 0.8915 / 0.9943** |

    strehl.exe stack "D:\personal\macro\dry-erase-marker-head-cpl" --srgb --auto-exposure
        --gate 4 --out C:\dev\strehl-out\M109\marker-stack-after.tif
    defaults in force: --limit unset (299 frames), --demosaic implied, --binned false,
        --memory-model m8; chose --exposure=-0.24; 7040 x 4688; 198 022 898 bytes

**B1-argmax — SPLIT: the fraction bar PASSES, the deficit bar FAILS.**

    strehl.exe argmax-baseline "D:\personal\macro\dry-erase-marker-head-cpl" --srgb
        --exposure=-0.24 --out ...
    defaults: --limit unset (299 frames), --demosaic implied, --binned false, --index-map none,
        --flat-roi none, --memory-model m8; 7040 x 4688; 198 022 898 bytes

| bar, as pre-registered | before | after | verdict |
|---|---|---|---|
| magenta fraction < 0.10 % | 0.3378 % | **0.0944 %** | **PASS** |
| max(R-G) < 0.10 | 0.3722 | **0.3722** | **FAIL** |
| p99 green within ±0.02 (guard) | 0.9474 | 0.9571 (Δ 0.0096) | PASS |

**The deficit bar failed and it has done its job** (discipline 710). It failed for the reason
pre-registration predicted, and the diagnosis confirms the prediction exactly:

| population | count | before RGB | after RGB |
|---|---|---|---|
| cleared | 80 329 | 0.9997 / 0.9017 / 1.0000 | **0.9576 / 0.9576 / 0.9576** |
| residual | 31 162 | 0.8407 / 0.7422 / 0.8376 | unchanged |
| newly magenta | **0** | — | — |

100 % of the cleared pixels were blown (max channel > 0.99) and land **exactly neutral**. The
residual is **73.5 % edge/fringe-like** (≤ 2 of 8 magenta neighbours) against only 2.2 % blob-like,
where the before-population was 87.1 % blob-like. **The blob is gone; the fringing is not.** The
fringe is made of partially pinned pixels — green averaged over frames or over G1/G2 lands just
below `K` — which a hard threshold cannot reach. The fix creates no magenta anywhere.

### B2 — null: an unsaturated stack must not move by one byte — **PASS**

    strehl.exe argmax-baseline "D:\personal\macro\109MSDCF" --srgb --out ...
    22 frames; defaults as above; 7032 x 4688; 197 797 874 bytes
    before SHA-256 4B7779AAB2AC3717B113DD5D04C8507A5EB357D3442FA1617EC7B981B1A011F5
    after  SHA-256 4B7779AAB2AC3717B113DD5D04C8507A5EB357D3442FA1617EC7B981B1A011F5

Byte-identical. `clip.rs` documents `109MSDCF` as having zero saturated pixels, and the conditional
form makes this an identity rather than a coincidence.

### B3 — negative control, SHOWN RED — **PASS**

The plant: `saturation_ceiling`'s `k0` line replaced by `f32::INFINITY`, disabling the ceiling while
leaving every other line of the fix in place. Anchored on the unique full line
`    let k0 = (f32::from(clip::CONTAINER_MAX_DN) - levels.black) / range;`; the script counts
occurrences and **hard-errors unless exactly one matches**, verifies the plant landed, restores from
`$env:TEMP` (never `git checkout`), re-verifies the anchor is back, asserts the plant string is
absent, and sets `LastWriteTime = Get-Date` so cargo cannot reuse a stale build.

With the plant in, B1-argmax reads **0.3378 %**, which is above the 0.10 % bar: **the harness goes
red**. Every "before" number in this report *is* the planted build, so the control is not a separate
ritual — it is the comparison itself.

### B4 — byte-freeze — **PASS**

`cargo test --release` with `STREHL_FREEZE_REQUIRE=1` (skips made fatal): `tests\byte-freeze.rs`
**5 passed, 0 failed, 0 ignored**. Whole workspace: 62 + 5 + 279 + 35 + 11 + 1 = 393 pass, 0 fail.
Predicted to hold by construction — both `byte-freezes.tsv` rows are `srgb=no` and take the
`write_rgb16` branch — and run anyway, because predicted-by-construction is not evidence.

### B5 — LibRaw cross-check — **PASS**

LibRaw renders the 583 873 container-pinned quads at **R 0.9986 / G 1.0000 / B 1.0000**,
mean `R-G = -0.0014`, max `R-G = +0.0010`, magenta by strehl's own predicate **0.0000 %**.
strehl after the fix renders its cleared blob at exactly neutral. Residual disagreement on
`mean |Δ(R-G)|` is **0.0014**, far below the 0.05 "must explain" threshold. The brightness
difference (LibRaw ~1.000, strehl 0.9576) is exposure and normalisation, not colour.

### B6 — the owner's eye

* `C:\dev\strehl-out\M109\M109-highlights-montage-100pct.png` — 100 % (1:1) three-panel crop:
  before, after, LibRaw. The crop is placed by the predicate on the centroid of the largest cleared
  component (16 908 px at 6695, 2237), not by hand — discipline 713, and fact 1434 is what happens
  otherwise. Both strehl panels are the same binary, frames and exposure; only the ceiling differs,
  which is discipline 708's exposure-matched control.
* `C:\dev\strehl-out\M109\M109-highlights-wholeframe.png` — whole frame at 1/6, for context.

**Judged honestly: the montage is a large improvement, not a clean sweep.** Crop magenta falls
11.13 % → 2.53 %, the big magenta patches go white, and the remaining pink is thin, textured and
edge-following. LibRaw's panel is clean. A viewer will still see pink at 100 %.

## 5. A follow-up, priced — and the price could not be measured

The obvious next move is to trigger at `Levels::white` (15360) instead of `CONTAINER_MAX_DN`, on the
argument that a sample above the calibrated white level is already not a trustworthy measurement.
Probed by the same anchored-mutation machinery (`k0 = 1.0`):

| | magenta | p99 green | px changed |
|---|---|---|---|
| before | 0.3378 % | 0.9474 | — |
| shipped fix | 0.0944 % | 0.9571 | 104 549 (0.32 %) |
| probe at `white` | **0.0260 %** | 0.9299 | 2 166 608 (**6.56 %**) |

The probe is better on the metric and leaves the `109MSDCF` null byte-identical too. Its risk is
that it clamps genuinely bright saturated colour, not just pinned samples — it touches twenty times
as many pixels.

**I could not price that risk on this corpus.** On `marker`, 0 of the 2.17 M changed pixels were
strongly coloured (chroma spread > 0.25). On `lavendar-cpl` — picked because lavender is strongly
saturated — the probe changed **0 pixels**, because at +1.82 stops that capture has 1207 strongly
coloured pixels in 33 MP and nothing clipped. So: **the corpus contains almost no saturated,
clipped colour, and therefore cannot falsify the aggressive variant.** Shipping it would trade a
measured defect for an unmeasured risk. I recommend the conservative trigger stays until a capture
exists that can price the other one, and I have not shipped the probe.

The residual fringing is also 73.5 % edge-following, which is the same neighbourhood M107 is
working in. Two overlapping fixes would confound both milestones.

## 6. What I need routed (merge_cmd.rs, M97's file)

The fix is built so `merge_cmd.rs` **compiles and renders byte-identically without being touched** —
`camera_to_srgb` only changed element type, and a `Render` with no stated ceiling is arithmetically
what shipped. So the shipped default `strehl stack --srgb` still has the defect. Activating it is
three lines:

    DELETE line 2803   let dev = image_out::Develop { matrix, srgb };
    DELETE line 2958   let dev = image_out::Develop { matrix, srgb };
    INSERT immediately before `if demosaic {` (after the exposure block, where `applied` exists):

        // M109: the sensor's saturation ceiling, in the render's own units. The
        // matrix mixes channels, so it must not be handed a triple in which one
        // channel is pinned and white balance has carried the others past it.
        let dev = image_out::Develop {
            matrix: matrix.map(|r| {
                r.with_ceiling(color::saturation_ceiling(levels, gains, applied.gain()))
            }),
            srgb,
        };

`levels`, `gains` and `applied` are in scope there; `matrix` is `Copy` and is still read afterwards
by `if matrix.is_some()`. The byte-frozen `write_rgb16` branch is not reached when a matrix exists,
so both freeze rows are untouched by construction.

## 7. One thing ORCH said that measurement qualified

> "That run chose `--exposure=-0.24`."

The auto-exposure did not cause the defect but **amplifies it 2.8x**. At `eg = 1` the same blob
renders `(1.0000, 0.9629, 1.0000)`, `R-G = 0.0371` — **below the 0.06 predicate**; at `eg = 0.8467`
it is 0.1053. The two clamped channels cannot move down while the pinned one can. Measured
end-to-end: `argmax-baseline --srgb` at `eg = 1` reads 0.0349 % magenta on the same scene where the
same binary at `-0.24` reads 0.3378 %. The headline 2.002 % is therefore partly a function of the
exposure, and any future comparison must hold exposure fixed. This is why `argmax-baseline` gained
`--exposure` / `--auto-exposure` in this milestone: without it the baseline could only be compared
with `stack` at a different gain, which M104c already established is a thumb on the scale.

---

## 8. Against ORCH's LibRaw control (B7-B9)

ORCH supplied the control this milestone lacked: a single unstacked LibRaw
frame of the same scene, D1 magenta 0.0061%, D8 partial-clip 1.6941%
(`cca4157`). Bars registered in PREREGISTRATION.md's addendum before any of
the runs below.

**Reproduction first.** Running ORCH's own script and importing ORCH's own
`d1_magenta` / `d8_partial_clip` rather than reimplementing them:
control 0.0061% / 1.6941% and unfixed `stack` 2.0017% / 2.1585%, both to four
decimals. Independent instrument, same numbers.

### The confound I registered, and its refutation

I registered in advance that the 328x mixes exposure with the defect: ORCH's
control is `no_auto_bright=True` (gain 1.0) while the 2.0017% was measured at
`-0.24` stops (gain 0.8467), and I had already measured a 9.7x swing from
exposure alone. So I built an exposure-matched control.

**The concern was refuted, and in the direction that strengthens ORCH's claim.**

| pipeline | gain 1.0 | gain 0.8467 | ratio |
|---|---|---|---|
| LibRaw control | 0.0052 % | 0.0036 % | **1.44x** |
| strehl BEFORE | 0.0349 % | 0.3378 % | **9.68x** |
| strehl AFTER | 0.0346 % | 0.0944 % | **2.73x** |

Exposure-matching **lowers** the control (0.0061% -> 0.0036%), so the excess for
the unfixed stack grows from ORCH's 328x to **556x**. I expected matching to
close the gap; it widened it. MEASURED.

The reason is the finding, not the arithmetic: **a pipeline that clips channels
together is exposure-invariant in magenta, and one that does not is not.** The
exposure dependence is not a confound to be controlled away -- it is a symptom.
That makes ORCH's un-matched comparison sound despite the mismatch.

### B7 exposure-invariance -- PASS, PASS, MISSED

- LibRaw within 2x: **1.44x PASS**
- strehl BEFORE above 5x: **9.68x PASS**
- strehl AFTER below 2x: **2.73x -- prediction MISSED**

Reported as written. The fix cuts exposure-dependence 9.68x -> 2.73x, a 3.5x
improvement, but does not reach LibRaw's invariance. My registered failure
condition was ">3x", so the failure clause did not fire either: **I left a gap
between the 2x prediction and the 3x failure line, and the result landed in
it.** That is a defect in my bar-writing, recorded rather than repaired.

### B8 partial-clip must fall -- PASS

At matched exposure D8 falls **1.7517% -> 0.4126%**, crossing ORCH's 0.5% bar
from FIRED to **clear**, and landing below the control's 1.6941%. Both clauses
pass. This is the mechanism check: the fix converts partial clipping into full
clipping, so a fall in D8 is what "the ceiling is doing what I claim" looks
like. Had D1 fallen while D8 held still, I would have been recolouring clipped
pixels rather than clipping them together.

At gain 1.0 D8 barely moves (5.4228% -> 5.1511%), and that is predicted by the
arithmetic: `K = 1.0689 x eg`, so at eg=1 the ceiling sits **above** 1.0 and
blown pixels still clamp at the output. Below eg = 0.9355 the ceiling drops
under 1.0 and they stop clamping entirely. The fix's effect on D8 is therefore
exposure-dependent by construction, which is worth knowing before anyone quotes
a single D8 number.

### B9 D1 against the matched control -- PASS on magnitude, FAIL on ratio

- Predicted 0.03%-0.10% at -0.24 stops: measured **0.0944% -- inside, PASS**
- Predicted 5x-16x the control: measured **26x -- FAIL as written**

The ratio failed for a reason I did not anticipate: I anchored it to ORCH's
0.0061%, and the correctly matched control is 0.0036%. **As predicted in
advance, this is a PARTIAL fix.** On the path I can reach, the excess over the
matched control falls from 93.8x to 26.2x.

### The precise localisation: the surviving channel is INVERTED

ORCH's "not which pixels clip, but what happens to them" is confirmed and
sharpened. Among partial-clipped pixels, which channel is pinned at 1.0 and
which is left lowest:

| render | R at 1.0 | G at 1.0 | B at 1.0 | lowest channel |
|---|---|---|---|---|
| LibRaw control, gain 1.0 | 0.0 % | 55.7 % | 99.6 % | **R 99.9 %** |
| strehl `stack` -0.24, unfixed | 91.5 % | **0.0 %** | 99.8 % | **G 99.1 %** |

In LibRaw, red is the deficit channel in 99.9% of clipped pixels and red is
**never** pinned -- a warm highlight leaning cyan, which is what an
over-exposed tungsten-lit white actually does. In strehl, red and blue are both
pinned and **green is the deficit in 99.1%**. Green is the channel that
physically cannot rise. This is the magenta signature at population scale, and
it is an inversion of the control, not a difference of degree.

After the fix the residual population shrinks 578,126 -> 136,189 (-76%) but its
composition is unchanged (G lowest in 98.0%) -- consistent with section 4's
finding that the blob clears and the fringe, which is made of partially pinned
pixels below the threshold, does not.

### What this does NOT license

`argmax-baseline` at -0.24 reads 0.3378% where `stack` at the same exposure
and scene reads 2.0017% -- **5.9x more**, on a code path my fix does reach
versus one it does not. So my before/after on argmax **does not support a
predicted after-number for `stack`**. The mechanism is identical and the fix
is the same three lines of arithmetic, but the population it acts on is six
times larger there and I have not measured it. I can produce that number within
minutes of the §6 patch being routed; I have not applied it locally even
temporarily, because M97 may commit `merge_cmd.rs` while my edit is in the
tree and would carry it in unknowingly.

---

## 9. Correction to section 6's routing request -- it had already rotted

Section 6 gave the activation patch as `DELETE line 2803` / `DELETE line
2958`. **Both numbers were stale within hours.** `merge_cmd.rs` has since
grown to 4125 lines and the two sites are now at **2924** and **3079**. Anyone
applying section 6 literally would have edited the wrong lines.

Replaced by `experiments/M109-highlights/src/activate_stack_fix.py`, which is
anchored on unique full lines and hard-errors unless each lands exactly once.
`--check` verifies without writing; `--apply` patches; `--revert` undoes.

**The anchoring has now been vindicated twice.** `merge_cmd.rs` was 4125 lines
when section 6 was written and is **4287** as of this revision -- M97 has added
162 lines in between, and its uncommitted delta has grown from 31 insertions to
100. Every line number in section 6 has therefore rotted a second time, while
all four anchors still land exactly once (`--check` clean at that size). Line
numbers into a file another agent is actively editing have a shelf life
measured in hours.

**The guard caught a defect in my own anchors, which is the point of having
it.** My first anchor set used the bare line `    let dev = image_out::Develop
{ matrix, srgb };`. The two sites differ only in indentation -- 4 spaces in the
early binding, 8 in the binned branch -- so the 4-space anchor is a **substring
of the 8-space line** and matched BOTH. `--check` reported
`expected 1 occurrence(s), found 2` and refused. A naive
`replace(old, new, 1)` would have silently patched the wrong site. Fixed by
anchoring on the preceding newline, so the indentation is load-bearing. The
guard itself was then shown to fire on a deliberate miss.

Two corrections to what section 6 claimed:

1. **The early binding must be DELETED, not shadowed.** Verified by
   enumerating every reader of `dev` from line 2900 on: they are the demosaic
   write (3042), a `caveat()` (3047), and the binned branch's own shadowed
   binding and its two uses (3079-3087). **Nothing reads the early binding
   between where it is bound and `if demosaic {`**, so shadowing it would
   leave an unused variable, and this workspace builds clippy with
   `-D warnings`.
2. **The binned branch needs its own edit.** It re-binds `dev` at 3079, so
   the inserted block does not reach it. Section 6 said "delete both, insert
   one"; that is right in effect but the binned site needs a REPLACEMENT rather
   than a deletion, because `eg` is already bound there and the surrounding
   code reads the new binding immediately.

The byte-frozen path is still untouchable by construction, now verified by
reading rather than by argument: it calls `write_rgb16` at 3119 and never
constructs a `Develop` at all.

**I have not applied it, even temporarily.** `merge_cmd.rs` is DIRTY as I
write this -- `git diff --numstat` reports 31 uncommitted insertions from M97.
A temporary local edit would be carried into M97's next commit without M97
knowing. This is the routing request, not a patch I can land.

## 10. Cache-contamination control (fact 1446) -- every arm CLEAN

ORCH raised a severity-1 warning: `StackIdentity` keys the frame set but not
`reference` and not `resampler`, so an identical command line can return bytes
produced under different inputs depending on what ran earlier. Every A/B in
this milestone is exactly the shape that corrupts.

**I did not run ORCH's literal control, and I am saying so rather than
implying I did.** It prescribes running `align --reference <other frame>`
between arms. `strehl align` has a documented history of dropping
`warpmap.txt` sidecars into the source directory -- 11 were quarantined -- and
`D:\personal\macro` is strictly read-only. I substituted a perturbation that
tests the same dependency without write risk: run each arm with the warpmap
cache **hidden** (`STREHL_CACHE_DIR` pointed at an empty directory, forcing a
fresh solve) and again with it **visible** (default, holding a
`dry-erase-marker-head-cpl` warpmap written at 11:53, before any of my runs).

**The perturbation was genuine, and strehl says so itself.** On the `stack`
arm the hidden run reported `alignment : ON (solved)`; the visible run
reported `alignment : ON (sidecar)`, in 111 s against 63 s. Different code
path, 1.8x different runtime. The `argmax-baseline` arms report no alignment
stage at all, which is the structural immunity below showing up in the
instrument rather than in an argument.

**The control poisons itself on re-run, and its own guard caught that.** The
forced-solve arm *writes* its freshly solved warpmap into the redirect
directory. On a second run the "hidden" arm therefore reads back its own
output and reports `(sidecar)`, so both arms take the same path and `A == B`
becomes vacuous. The first run of `cache_control.ps1` printed
`CONTROL INERT: both arms reported align=sidecar` for the `stack` arm, which
is how this was found. Fixed by emptying the redirect directory before every
hidden arm; the guard is now an error, not a note, so an inert control fails
loudly instead of reporting a clean result. **Anyone else running a
cache-visibility control needs this -- a stale redirect directory turns it
into a control that cannot go red.**

| arm | cache hidden | cache visible | vs. the render I reported |
| --- | --- | --- | --- |
| `argmax` AFTER | `4EDD689B...B25E0C` | same | identical |
| `argmax` BEFORE | `57D935E8...51B876` | same | identical |
| `stack` AFTER | `DB7BAAD2...A1DDDC` | same | identical |
| null `109MSDCF` | `4B7779AA...1A011F5` | -- | identical |

**A == B on every arm, and every arm reproduces the exact file the reported
numbers were computed from.**

The `stack` arm is the one that was at risk by timeline: it is the only
command I ran that touches `StackIdentity` at all, and the cached marker
warpmap (11:53) pre-dated my render (12:40). That is now resolved by
measurement rather than by argument -- **the freshly solved warpmap is
byte-identical to the cached one**, SHA-256
`1864A370AE92B377DFF6408ACD06E3FD7088446634B93D50BBEEE4FB95E8F4D0`, 41 027
bytes. The 11:53 entry was solved under the same reference (149) and the same
resampler my command implies, so the unkeyed collision never had an
opportunity to bite.

Read-only corpus re-verified after the control: 0 non-ARW files in the marker
directory (299 files, all `.ARW`), and nothing under `D:\personal\macro`
modified in the preceding two hours.

**What this does NOT license.** It is not a refutation of fact 1446. I did not
vary `reference` or `resampler`, so I did not exercise the collision; I showed
that *my* session never exercised it either. The bug is real and M97 should
still fix it. Separately, most of my bars were structurally immune rather than
luckily clean: `StackIdentity` appears only in `align_cmd.rs` and
`merge_cmd.rs`, while `stack.rs`, `image_out.rs` and `color.rs` contain zero
warpmap, cache or `StackIdentity` references -- so `argmax-baseline`, which
produced B1, B2, B3, B7, B8 and B9, has no cache path to be poisoned through.
B5 is pure `rawpy` and never invokes strehl at all.

## 11. Standing by to measure `strehl stack` (patch routed, not landed)

ORCH routed section 6's patch to M97. As of this revision M97 has committed
its in-flight work -- `merge_cmd.rs` is clean at `8e5eb6e` -- and the patch is
**not yet applied**: `saturation_ceiling` and `with_ceiling` occur **0 times**
in that file. I have still not touched it.

**I authored the patch, so what follows will be a measurement and not a
verification.** ORCH is treating M110's independent 1:1 sheet, which includes a
specular-highlight crop, as the independent read. I am the wrong party to
certify my own fix and am not attempting to.

`experiments/M109-highlights/src/measure_stack.ps1` is written and armed. It
**refuses to run** unless the patch is present, so it cannot quietly measure
the unpatched path and report the resulting null as a finding; demonstrated
just now, exiting 2 with
`merge_cmd.rs does not contain the section 6 patch yet`.

**Both arms will be built from one tree, and this is not the obvious choice.**
The convenient "before" is the binary already sitting in `C:\dev\strehl-out\M109`.
That would be **confounded**: `optics.rs` (+73) and `robust.rs` (+12) are
currently dirty with another agent's in-flight work, so a rebuild after M97
lands would differ from the stored binary by *their* changes as well as by the
patch, and a moved pixel could not be attributed. Instead both binaries are
built from the same tree at the same moment, differing only in whether
`color::saturation_ceiling` returns a real ceiling or `+inf` -- the B3 control
mechanism, already shown able to go red, in **my own** file. The restore path
copies to `$env:TEMP` and back rather than using `git checkout --`, then
**touches** the file, because `Copy-Item` preserves mtime and cargo would
otherwise reuse the stale build.

`montage.py` was parameterised rather than duplicated, so both montages place
their crop by the same predicate-driven rule -- a second script would be a
second opportunity to aim at a flattering ROI. The refactor was checked
byte-neutral: run with defaults it reproduces the committed artefacts exactly,
`575045B5...0BD851B9` and `C38167BD...A20E6834`.

**On the clippy attribution.** ORCH asked me to drop its `align.rs:2108` /
`pen_w` attribution from this report. **It was never recorded here** -- it
appeared only in a chat message, so it has not propagated into the corpus;
grep for `2108`, `pen_w` and `M110` across this file and
`experiments/M109-highlights/` returns nothing. Rather than swap one unverified
attribution for another I measured it: `cargo clippy --all-targets -- -D warnings`
exits **101** with **4** errors -- `optics.rs:459` (hex literal grouping) and
`robust.rs:409`, `:451`, `:464` (`useless use of vec!`) -- and **zero in
`align.rs`**, reproducing ORCH's corrected figure exactly. None are in the four
files this milestone touches, all of which have zero uncommitted delta. The
unrelated claim on line 430, that this workspace builds clippy with
`-D warnings`, is separately confirmed at `AGENTS.md:954` and stands.

## 12. Is the residual fringe radial? UNDECIDABLE ON THIS ARTEFACT

ORCH asked a read-only question: does the residual that survives my fix rise
toward the corners, as lateral CA must, in which case it is M107's object and
the two milestones collide? Three bars were registered in advance. **The
question turned out not to be answerable on this subject, and the interesting
part is why.**

### B10 -- FAILED AS WRITTEN, and is reported failed

Both controls failed and the instrument disqualified itself, exit 4. Per its
own registered consequence **none of its readings may be quoted**, and I am not
quoting them.

**It failed for a reason I did not anticipate, which is what a control is
for.** On the eligibility denominator only **2 of 20** annuli cleared
`MIN_DENOM`, both outer, so Spearman rho came out `+1.0000` degenerately on two
points and outer/inner was `nan` for want of any inner annulus. The uniform-
random null returned `rho = +1.0000` as well -- an instrument that reports
perfect radial correlation for a population with no radial structure at all.
Had I run only the real arm I would have read `+1.0000` and called it RADIAL.

`radial.py` is **left exactly as written**. Editing it now would convert a
reported failure into a silent repair.

### B11 -- UNDECIDABLE-BY-SUPPORT, as predicted before the run

I registered "PREDICT: undecidable" in advance, so this is a confirmation and
not a discovery. The partial-clip population contains **zero pixels in 11 of 20
annuli** and **90.1 %** of itself in two adjacent bins at r 0.775-0.825. There
is no radial lever arm because the population does not sample field height.

It did split the residual into two spatially disjoint parts:

| population | share | where it lives |
| --- | --- | --- |
| clipping-coupled | 72.5 % (22 582 px) | r 0.52-0.88, 90 % in r 0.75-0.85 |
| not clipping-coupled | 27.5 % (8 580 px) | annuli with **zero** eligible px, r 0.02-0.93 |

### B12 -- UNDECIDABLE-BY-SUPPORT AGAIN, from the opposite end

Only the non-coupled 27.5 % could be lateral CA, and it does span field height,
so B12 asked the question against a denominator that also spans the frame:
luminance edge pixels, Sobel magnitude above p99 with luma > 0.15.

**It hit the same wall from the other side.** The edge population collapses in
the outer field:

| r | edge px | | r | edge px |
| --- | --- | --- | --- | --- |
| 0.225 | 47 597 | | 0.775 | 572 |
| 0.475 | 15 356 | | 0.825 | **88** |
| 0.625 | 10 552 | | 0.925 | 303 |

From 47 597 to 88 -- a factor of 540 -- across annuli of comparable area. No
annulus beyond r = 0.85 reaches the registered 5 000-pixel support floor, so no
rho and no ratio was computed. Exit 4.

### The answer

**Two independent denominators, chosen for different reasons, collapse in the
same place. The outer field of this frame contains neither blown highlights nor
bright edges** -- it is a macro subject occupying a band, with defocused
background beyond r = 0.7. The radial question is therefore **undecidable on
this artefact by any denominator**, not merely by the two I tried.

What this does establish: **the dominant 72.5 % of the residual is
clipping-coupled and co-located with the blown region, not distributed by field
height.** Whatever it is, it tracks saturation rather than field position.

What it does not establish: that lateral CA is absent. The corners are untested
because there is nothing there to fringe -- not because fringing was looked for
and not found. **A NOT-RADIAL verdict was never reached and must not be
attributed to me.**

**Consequence for ORCH's composition question.** Whether M109's residual and
M107's object are the same thing cannot be settled on `dry-erase-marker-head-cpl`.
It needs a subject with high-contrast content out to the frame corners. I note
without having looked at M107's work, and without coordinating with it, that
**any CA measurement made on this same subject faces the identical support
limit** -- the constraint is a property of the frame, not of either method.

## 13. Job 1 -- LANDED in `strehl stack`. MEASUREMENT, NOT VERIFICATION.

**I authored this patch. What follows is a measurement of it, not an independent
verification of it.** M110's 1:1 crop sheet is the independent read.

ORCH granted me `merge_cmd.rs` and I applied the section 6 patch with
`activate_stack_fix.py --apply`, anchored on unique full-line content with an
assertion that each anchor matched exactly once. All four anchors landed against
a file that had rotted to **4516 lines** (a third rot datum after 4125 and 4287).

### Method: one tree, one moment, one toggle

Both arms were built from a single working tree at one moment, toggling only
`color.rs`'s ceiling to `+inf`. **The stored binary was deliberately not used as
"before"** -- at the moment of measurement other agents were `+73` in `optics.rs`
and `+12` in `robust.rs`, so a stored-binary comparison would have credited their
work to my patch (discipline 741).

### Result

| bar | before | after | verdict |
|---|---|---|---|
| B1-stack magenta fraction | **2.0017 %** | **0.5060 %** | **PARTIAL** -- 3.96x |
| B8-stack D8 partial-clip | 2.1585 % | 0.5225 % | 4.13x |
| B1-stack `max(R-G)` deficit | 0.4490 | 0.4490 | **FAILED, not retro-fitted** |
| B2-stack null, `109MSDCF` | `298EE4F6..706C58` | `298EE4F6..706C58` | **byte-identical** |
| B4 byte-freeze, `STREHL_FREEZE_REQUIRE=1` | 5/5 | 5/5 | PASS |
| B6-stack montage crop | 80.36 % | 19.89 % | still visibly pink |

Arm hashes: before `DB7BAAD2..A1DDDC`, after `559407FE..AD12E5`.

### The honest part

**0.5060 % is not LibRaw's 0.0061 %, and at 1:1 the region is still visibly pink.**
I looked at the montage rather than only the number. This is a large improvement
and it is not a cure. The untested hypothesis for the residual is in section 5:
the trigger keys on `CONTAINER_MAX_DN`, so a sample saturated in the sensor's
sense but landing between `Levels::white` and the container max is missed --
plausibly worsened because the merge averages pinned and unpinned frames
together. The aggressive variant remains unshipped for the reason given in
section 5, which has not changed: **the corpus contains almost no saturated
clipped colour and therefore cannot falsify it.**

`max(R-G)` is unchanged at 0.4490. The single worst pixel is untouched; what
moved is the population. That is the same shape as the argmax result and I am
reporting it as a failed bar rather than rewriting the bar.

### A neighbour's uncommitted work was in both arms, and is a proven no-op

`optics.rs` (15:00:31) and `align_cmd.rs` (15:00:45) were modified by another
agent **before** either of my arms was built (15:01:35 and 15:02:41), so both
binaries contain that uncommitted work. This was caught by timestamp, not by
assumption, and it is decidable rather than merely arguable:

> the ceiling-disabled arm, built **with** the neighbour's wiring, renders
> `DB7BAAD2..A1DDDC` -- **byte-identical** to the same render made at ~13:45,
> **before** that wiring existed.

A no-op that is byte-proven is not a no-op that is claimed. My delta is
attributable to the ceiling toggle alone.

### The patch was committed by another agent, out from under me

`git commit -- crates/strehl-cli/src/merge_cmd.rs` returned **EXIT=1, "no changes
added to commit"**: M97 had already committed my working-tree bytes as
**`e9ad010`**, 15 insertions / 2 deletions, message *"M109: clip blown highlights
together in strehl stack (applied by M97)"*. I verified the commit contains
exactly my diff and nothing else, and its message credits me as author and M97
as applier only, and declines to claim the magenta delta.

**I recommend accepting `e9ad010` as-is.** It is accurate and honest; re-committing
identical bytes under my own message would be churn for attribution's sake.

The generalisable hazard is not M97's: **in a shared working tree an uncommitted
change is not private. Any agent that path-scope-commits that file will sweep it,
correctly and silently, because a path-scoped commit takes the file's whole
working-tree state and not just the hunks its author wrote.** Path-scoping
protects against committing *other files*; it does not protect against committing
*other authors' hunks in the same file*.

## 14. Job 2 -- NOT DONE. Blocked, deliberately, on an active collision.

ORCH's instruction for this exact case was *"If you nonetheless find uncommitted
changes in either file, stop and tell me."* I found them. I stopped.

### Two corrections to fact 1476, both material

**(a) `merge_config` is not in `merge_cmd.rs`. It is at `align_cmd.rs:915`,**
called once at `align_cmd.rs:1071`. Fact 1476 quotes the function correctly and
attributes it to the wrong file. Job 2's target is therefore the **contested**
file of the two I was granted, not the clean one.

**(b) A canonical string-to-`Resampler` mapping already exists in core** --
`warpmap.rs:537` `resampler_name` and `warpmap.rs:547` `resampler_from_name`.
`align_cmd.rs:150` is itself a *duplicate* of it. So "reuse `align_cmd.rs:150`
rather than writing a second one" would have created a **third**. Two further
facts: the core pair is `pub(crate)`, so it is **not reachable from
`strehl-cli`** without widening it, and the two disagree -- core handles five
variants, `align_cmd.rs:150` only four (**no `lanczos2`**). Whichever is chosen,
the other should be deleted rather than left to drift.

### Why I did not simply edit it anyway

`align_cmd.rs` acquired another agent's lateral-CA wiring at **15:00:45**,
roughly two minutes after ORCH verified the lane clean at ~14:58. The grant was
stale on arrival through nobody's fault.

The hazard is not hypothetical: **it is the same hazard that had already consumed
my job-1 commit an hour earlier** (section 13). Had I edited and committed
`align_cmd.rs`, `git commit -- crates/strehl-cli/src/align_cmd.rs` would have
swept a half-wired CA correction into a commit titled "add `--resampler`" -- and
ORCH has explicitly gated the Lanczos default flip on CA landing *properly*.
Committing someone else's unfinished optics under my message is a worse outcome
than shipping nothing, particularly for a flag that **changes no rendered pixel
by design**.

That last point is what makes the decision cheap rather than brave: job 2's
default is `catmull-rom`, so a correct job 2 is **byte-identical to today** and
has **zero owner-visible value tonight**. Nothing the owner can see is being held
back. The visible win, job 1, is landed.

### The collision is at commit granularity, not at hunk granularity

Measured, and it is the useful part for whoever picks this up:

| | lines |
|---|---|
| other agent's hunks | 1252-1279, all inside `warp_frame_in_place` |
| job 2's targets | 915 (`merge_config`), 1071 (its only call) |

**They do not overlap and they are not even in the same function.** Both changes
can coexist in the file; what cannot coexist is two agents *committing* it. The
constraint is git's, not the code's.

### The design, ready for whoever owns the file

1. `fn merge_config(n: usize, resampler: Resampler)` -- take the choice instead
   of returning the literal, keeping the "one value so lookup and solve cannot
   drift apart" property its doc comment asserts.
2. Thread from the `stack` CLI arg down to the single call at 1071. It already
   feeds `solve_config_key(want_ref, &spans, want_resampler)`, so **the cache
   keys itself correctly with no further work** -- M97's `69f7b4c` did that part.
3. Default `catmull-rom`, giving a byte-identical default render.
4. Parse via **one** mapping. Widening `warpmap.rs`'s pair to `pub` is the
   better of the two, being complete and already canonical.
5. Verify: byte-freeze, plus a default-render hash equal to `559407FE..AD12E5`.

**I have not written this and I claim no measurement of it.** Step 5's predicted
hash is a prediction, not a result.

## 15. Which path was the defect measured on? BOTH. And no green overshoot.

ORCH asked whether the magenta figures were measured on `argmax-baseline` or on
`strehl stack`. **Both, on the same subject, and the `strehl stack` numbers are
in section 13.**

| quantity | argmax-baseline | `strehl stack` |
|---|---|---|
| argv | `argmax-baseline <dir> --srgb --auto-exposure --gate 4` | `stack <dir> --srgb --auto-exposure --gate 4` |
| subject | `dry-erase-marker-head-cpl` | `dry-erase-marker-head-cpl` |
| magenta before | 0.3378 % | **2.0017 %** |
| magenta after | 0.0944 % | **0.5060 %** |
| green offset before | -- | **-0.1028** |

**ORCH's `2.002 %` and `-0.10` are `strehl stack` numbers and they are correct.**
They were ORCH's own, from the reproduce command in the original brief, and I
reproduced both. The `0.3378 % -> 0.0944 %` pair is the argmax one and was always
labelled as such.

**The clip is not inert on the default path.** The two arms of an identical
`strehl stack --srgb --auto-exposure --gate 4` command line render
`DB7BAAD2..A1DDDC` and `559407FE..AD12E5`. Different bytes, same command line,
one toggle.

### Why byte-freeze 5/5 is not evidence of inertness

**Byte-freeze exercises the measurement path -- default, binned, linear,
camera-native RGB. The fix is a viewing-path fix and deliberately does not touch
it.** ORCH's own brief required exactly this: *"The byte-frozen measurement
output must not change by a single byte."* So 5/5 HOLD is the **designed** result
and is evidence the fix did **not** leak where it must not go. It carries no
information about `--srgb`, because byte-freeze never renders `--srgb`.

A pass on a test that cannot see the change is not a null.

### B14 -- the mirror predicate. ORCH's overshoot caution, measured.

Run because ORCH observed that M110's readout is one-sided by construction. The
predicate is the **exact mirror** of the registered B1 predicate with the
channels swapped -- `G-R > 0.06 && G-B > 0.06` -- so it is not a statistic chosen
after seeing the data. It was, however, **not pre-registered**, and I mark it as
such rather than implying otherwise.

| | before | after |
|---|---|---|
| green excess | 0.0113 % | 0.0113 % |
| delta | | **-0.0000 pp** |
| pixels turned green-excess by the clip | | **0** |
| green offset in the magenta region | -0.1028 | **-0.0260** |
| most positive green offset, after | | **+0.0000** |

**NO OVERSHOOT, and it is structural rather than lucky.** `K = min_c ceil_c` and
green's ceiling is the minimum by construction (its WB gain is 1.0), so `K` *is*
green's ceiling. The clip only ever lowers a channel to `K`, and green already
sits at or below `K`. Green can therefore never be raised above red or blue by
this operation. The measured `max` green offset after the clip is exactly
`+0.0000` -- it lands on neutral and does not cross it.

### A hypothesis of mine that the measurement killed

I predicted M110's selector (R and B >= 99 % full scale) was **structurally
blind** to this population, reasoning from the raw DN in ORCH's diagnosis: R at
46.8 % and B at 86.2 % of container full scale. **Measured: it covers 99.04 % of
the magenta population.** I was wrong, and wrong for a specific reason worth
recording -- I compared a *raw* criterion against an *output* population. Raw R
is 46.8 % FS, but after a 2.687x white-balance gain, exposure, the colour matrix
and the sRGB curve, output R is 0.9944. The same pixel is far from clipping in
one domain and above 99 % in the other.

So M110's instrument would have found these pixels. **The reason its four
subjects read neutral is that none of them is this subject.** Subject choice, not
selector blindness, and it means the two results do not conflict at all.

## 16. B15 -- why 0.5060 % survives. H-merge SUPPORTED; my own quantitative bar FAILED.

ORCH's fourth hypothesis -- the merge averaging clipped with unclipped frames --
is the one specific to strehl, and it is **supported**. Read-only, 75 of 299
frames of `dry-erase-marker-head-cpl`, green sensels only.

**Definition.** `f` = fraction of sampled frames in which a green sensel is
pinned at `CONTAINER_MAX_DN`, over the 848,807 sensels pinned in at least one
frame (**10.31 %** of the green plane).

| | count | share |
|---|---|---|
| `f == 1` -- pinned in **every** frame | 178,402 | **21.02 %** |
| `0 < f < 1` -- pinned in **some** | 670,405 | **78.98 %** |

mean `f` = 0.6464, median 0.6667.

**Nearly four fifths of the saturated population is pinned only part of the
time.** For those sensels the merged value is a blend of pinned and unpinned
samples and therefore lands **strictly below** the ceiling, so a guard written as
`v_c >= ceil_c` never fires -- while green remains suppressed relative to red and
blue. That is the residual magenta.

**The guard asks a per-frame question of a post-merge value.** That is the defect
in my fix, and it is not a threshold that needs tuning.

### My registered quantitative bar FAILED, and I am not rewriting it

B15 predicted in advance that if H-merge were the whole story, the `f == 1` share
would be **comparable to the ~74.7 % of the defect the clip cleared**.

**Measured 21.02 % against a predicted ~74.7 %.** That is not a near miss and it
is in the wrong direction. By the criterion I registered before looking, H-merge
is therefore **a mechanism, not the only mechanism** -- the weaker claim.

**The most likely reason is a denominator error of mine**, and it is a real
limitation rather than a rescue: I computed `f` over *all* sampled frames, but
the merge is focus-gated and averages `n_eff` ~ 55 **contributing** frames per
pixel, not 299. The frames contributing to a pixel are the ones in focus there,
which are plausibly the ones where a specular highlight is pinned. `f` over the
correct denominator would be **higher** than 0.6464. I have not measured it,
because doing so needs the gate's per-pixel frame set, and I am not going to
assert a number I did not compute.

### An unregistered observation that matters

The pinned population grows monotonically across the sweep -- **178,987 sensels
in `DSC00001` to 816,158 in `DSC00281`, a 4.6x increase.** Whether a given sensel
is clipped is thus strongly frame-dependent across the stack. Whatever its cause
(defocus spreading the specular highlight, or illumination drift), it is exactly
the condition that makes a post-merge equality test fail, and it was not
something I predicted.

### What this implies for the fix -- and it reopens ORCH's original sentence

ORCH's opening brief said the gap was that **"nothing carries the consequence
into the colour path."** My fix addressed that only where the *merged* value
happens to remain pinned. For 78.98 % of the population the consequence is
destroyed by averaging **before** the colour path can see it.

So the correct fix is not a better threshold, it is **carrying per-frame clip
state through the merge** -- and `clip.rs` already computes exactly that for the
focus path via `ClipCensus`. Its own doctrine, that a clipped sample is not a
focus measurement, extends without strain: a clipped sample is not a **colour**
measurement either.

Three candidates, in the order I would try them:

1. **Propagate a per-pixel clipped count through the merge** and trigger the
   existing clip on it. Precise, and it cannot move an unclipped pixel, so the
   byte-identical null survives by construction.
2. **Exclude pinned samples from the colour merge** where unpinned ones exist.
   Most principled, closest to `clip.rs`'s stated doctrine, largest behavioural
   change.
3. **Lower the trigger** toward `Levels::white`. Cheapest and I already measured
   it on argmax (0.0944 % -> 0.0260 %), but it touched 6.56 % of the frame, and
   B15 now suggests why: 10.31 % of the green plane is pinned somewhere in the
   stack, so a low trigger reaches far beyond the defect. **I still decline it**
   for the reason in section 5, now with a mechanism attached.

I have implemented none of these and claim no measurement of any.
