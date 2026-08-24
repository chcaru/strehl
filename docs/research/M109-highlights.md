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
