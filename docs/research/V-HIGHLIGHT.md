# V-HIGHLIGHT: independent verification of the highlight chroma roll-off

Adversarial re-test of `56a21571` and `cdec22e1` (`docs/research/BUILD-HIGHLIGHT.md`,
`crates/strehl-core/src/highlight.rs`), by someone who did not write the fix and
whose brief was to break it. Harness: `experiments/V-HIGHLIGHT/`. Outputs:
`C:\dev\strehl-out\V-HIGHLIGHT\`.

Every number below marked *independent* was measured by this lane from its own
renders with its own scripts. Where the author's figure is reproduced to the digit
it is marked *reproduced*.

## Verdict on each claim

| # | claim | verdict |
| --- | --- | --- |
| 1 | gates: 480 lib / 651 workspace / 104+5 cli / clippy / corpus_lint | **CONFIRMED** |
| 2 | `109MSDCF` null is byte-identical | **CONFIRMED, and widened to 8 subjects** |
| 3 | negative control at knee 0.05 moves 26x further | **CONFIRMED exactly (25.8x)** |
| 4 | containment: lowest moved pixel 42448/42796/42657/42162 DN | **CONFIRMED to the DN** |
| 5 | `STREHL_HIGHLIGHT_KNEE=off` restores the previous render bit-exactly | **CONFIRMED cross-build, all 3 planes** |
| 6 | camera-linear byte-frozen corpus untouched | **CONFIRMED — not a ship blocker** |
| 7 | 96.6 % of `coffee-bean`'s clipped pixels were coloured | **CONFIRMED exactly (96.592 %)** |
| 8 | the roll-off is pointwise, so the clip rate cannot change it | **CONFIRMED (structural + empirical)** |
| - | the change is potent on real data | **CONFIRMED — it is not inert** |

Two defects found, both provenance rather than pixels. Neither blocks the ship.

## 0. Potency first: the code path is reached

A null is worth nothing until the instrument is shown able to fail it. One binary
(`471D50DA...`), one subject, one banner, one variable:

| arm | SHA-256 (first 16) |
| --- | --- |
| `coffee-bubbles --merge pyramid --linear-srgb`, `KNEE=off` | `4549005F3433AE7B` |
| the same, knee at its default | `5B2C6E7944B2303A` |

Banner on both arms: `merge backend   : pyramid (--merge)`. **0.2807 % of pixels
move** (*independent*, and *reproduced* — the author reports 0.2807 %). The change
is live on shipping data.

## 1. The gates, re-run

| command | result |
| --- | --- |
| `cargo test -p strehl-core --lib` | `480 passed; 0 failed` |
| `cargo test --workspace` | `104+5+480+35+26+0+1+0 = 651 passed; 0 failed` (1 ignored) |
| `cargo test -p strehl-cli` | `104 passed` + `5 passed` (byte-freeze, 608 s) |
| `cargo clippy -p strehl-core --lib --all-targets` | 31 warnings, **0 of them in `highlight.rs`** |
| `python scripts/corpus_lint.py --root .` | `OK - no violations` |

Clippy's 31 warnings are all pre-existing, in `edgeaware.rs`, `merge.rs`,
`pyramid.rs`, `restore.rs` and `softgate.rs`. The claim was scoped to
`highlight.rs` and is true as scoped; the crate as a whole is not clippy-clean and
never was.

## 2. Claims 5 and 6: the off switch, and the frozen corpus

`--merge pyramid`, `coffee-bubbles`, pre-fix binary built from `948ab303`
(`78DA8159...`, no `highlight.rs` in its tree) against the current binary
(`471D50DA...`):

| file | SHA-256 |
| --- | --- |
| camera-linear, **pre-fix binary** | `414331E605A9C829E6962E8A72F176AB4EF97F374305A94658E927B55ED0CBB8` |
| camera-linear, post-fix, default knee | `414331E605A9C829E6962E8A72F176AB4EF97F374305A94658E927B55ED0CBB8` |
| camera-linear, post-fix, `KNEE=off` | `414331E605A9C829E6962E8A72F176AB4EF97F374305A94658E927B55ED0CBB8` |
| linear-sRGB, **pre-fix binary** | `4549005F3433AE7BB33FE799877CB3ADA72DACC8A3A6A2A8189C9D1C07C4A6F9` |
| linear-sRGB, post-fix, `KNEE=off` | `4549005F3433AE7BB33FE799877CB3ADA72DACC8A3A6A2A8189C9D1C07C4A6F9` |
| linear-sRGB, post-fix, default knee | `5B2C6E7944B2303A2E2FF35FA67A210A525AC65B4AB4445D3F5576D29FA7571D` |

**The byte-frozen default path did not move**, on a subject that demonstrably
saturates. Verified three ways: same-binary knee on/off, cross-build pre/post, and
the `byte-freeze.rs` integration test, whose 2 registry rows are both `srgb=no`
and which passes. **Not a ship blocker.**

`KNEE=off` restores the pre-fix render **bit-exactly across builds on all three
planes** — the green-only restriction the house rules impose on cross-build
readings was not needed, because the result is equality rather than a difference.

## 3. Claim 2: the null, commissioned

`109MSDCF`, same binary, `--merge pyramid --linear-srgb`:

| arm | SHA-256 (first 16) |
| --- | --- |
| `KNEE=off` | `B33B53DFABCFD082` |
| default knee 0.60 | `B33B53DFABCFD082` |
| `KNEE=0.05` | `E6DA462C42E2D83A` |

The null holds, **and the same instrument on the same subject moves 67.5582 % of
the frame when the knee is dropped to 0.05** (*independent*). The null is a
measurement, not an absence of wiring.

I then screened seven subjects the author never tested (`--limit 10`, otherwise
identical arms): `112MSDCF`, `113MSDCF`, `119MSDCF`, `wrapped-text-1`,
`bee-3-cpl`, `flowers-cpl`, `lavendar-cpl`. **All eight subjects byte-identical.**
The null's support is materially wider than the report claims. *Caveat: these are
10-frame stacks, not full ones.*

## 4. Claims 3, 4 and 7: reproduced to the digit

*Independent* re-measurement, `--merge pyramid --linear-srgb`, one binary per pair:

| subject | pixels moved | author | lowest moved pixel | author |
| --- | --- | --- | --- | --- |
| `foam` | 0.6444 % | 0.6444 % | 42448 DN | 42448 |
| `coffee-bubbles` | 0.2807 % | 0.2807 % | 42796 DN | 42796 |
| `tweezers-cpl` | 0.0076 % | 0.0076 % | 42657 DN | 42657 |
| `coffee-bean` | 35.4010 % | 35.4010 % | 42162 DN | 42162 |

Clip census, measured at `== 65535` in the written file:

| subject | any-channel clipped | of which COLOURED, before | after |
| --- | --- | --- | --- |
| `coffee-bean` | 5.0732 % -> 2.1657 % | **96.592 %** | 0.007 % |
| `foam` | 0.5535 % -> 0.3812 % | 53.005 % | 6.335 % |
| `coffee-bubbles` | 0.2995 % -> 0.1988 % | 54.420 % | 5.073 % |

Claim 7's 96.6 % is **96.592 %**. `foam`'s stated cost — green clipping rising
0.2989 % -> 0.3579 % — reproduces to four decimals.

Negative control on `foam`: knee 0.05 moves **16.6357 %** against the default's
0.6444 %, a factor of **25.8x**. The author's "26x" is correct.

### Is claim 4 a measurement or a restatement of the constant?

It is a real measurement, and it is **commissioned**: at knee 0.05 the same
statistic reports a lowest moved pixel of **3582 DN** instead of 42448. The
instrument tracks the knee rather than echoing it.

It is nevertheless *arithmetically entailed* by the early return in
`desaturate_with`, so what it proves is that the implementation honours its own
constant — not that 0.60 is the right constant. Those are different claims and the
report runs them close together.

## 5. The knee value: "anchored, not tuned" is half true

No sweep artifacts exist anywhere in `experiments/BUILD-HIGHLIGHT/`; only 0.60 and
the 0.05 control were ever rendered. There is **no evidence of tuning**.

But the anchor is **one-sided**. It says `109MSDCF` reaches `u <= 0.5707`, so 0.60
preserves that null. Every value in `[0.5707, 1)` preserves it equally. Nothing in
the record distinguishes 0.60 from 0.75 or 0.85, and the choice is exactly what
decides how much of each frame is desaturated. The margin is 0.029, about 5 %.

My eight-subject null (section 3) is the evidence that would actually support the
value, and it did not exist until this lane ran it.

## 6. The classic failure mode: over-reach and the seam

**There is no seam.** Level-binned response on `foam`, on the BEFORE image:

| level bin | frac moved | max abs dRGB |
| --- | --- | --- |
| 41000-42000 | 0.0000 % | 0 |
| 42000-42500 | 0.2079 % | **1** |
| 42500-43000 | 5.6522 % | 9 |
| 43000-43500 | 16.6049 % | 35 |
| 43500-44000 | 26.3554 % | 75 |
| 44000-45000 | 39.1724 % | 251 |
| 45000-46000 | 53.6474 % | 590 |

The correction enters at **1 DN** and grows continuously. The smoothstep does what
it is documented to do. Visual inspection of a 400 px crop straddling the boundary
on both `foam` and `coffee-bean` (`experiments/V-HIGHLIGHT/seam-*.png`) shows no
contour ring and no banding; the moved-pixel mask follows the subject's texture
rather than an iso-level contour.

**Over-reach is real, and larger than the report's framing suggests.** On `foam`,
**55.92 % of the pixels the roll-off moves are not clipped in any channel, in
either arm**, and on those 29 698 pixels mean chroma falls **0.2333 -> 0.1696, a
27.3 % removal** (*independent*). On `coffee-bubbles --srgb` the same figure is
73.87 % of moved pixels and a 39.3 % chroma removal.

This is *by design* — the module's whole premise is that the merge lands strictly
below the ceiling, so a fix that only touched clipped pixels would miss the defect.
The report discloses the effect as whole-frame means (`foam` -0.28 % saturation)
and as a hot-edge statistic, which are honest but dilute it. The subpopulation
number is the one an owner should see, and it is not in the report.

## 7. Claim 8: pointwise

Structurally confirmed by reading `desaturate_with`: its arguments are the pixel's
own `v`, plus `ceiling`, `top`, `knee` and the matrix, all of which are derived
from file metadata and a constant. There is no neighbourhood term and no aggregate.
The exposure gain is the one image-derived input that reaches `ceiling`, and `u` is
invariant to it because `v` and `ceiling` carry it identically.

Two *independent* empirical corroborations:

1. **The containment floor is invariant to the clip rate.** The four subjects span
   any-channel clip rates from 0.0031 % (`tweezers-cpl`) to 5.07 % (`coffee-bean`)
   — a 1600x range that brackets BUILD-ELECT's 1.87 %/4.65 % — and the lowest moved
   pixel sits within 1.5 % on all four. A clip-rate dependence would move it.
2. **The `--srgb` tone curve does not move.** `tone : black 0.01259, white
   1.18627 (linear), contrast 0.55` on both arms, byte-identical. This is the one
   genuine global statistic downstream of `develop`, and I expected it to shift;
   it does not, because the blend is luminance-preserving exactly. Below the knee
   the `--srgb` output is bit-identical too (0 moved pixels in every level bin
   below 52000).

## 8. Both backends, both writers — verified rather than asserted

| arm | knee off | knee default | differ? |
| --- | --- | --- | --- |
| `--merge estimator --linear-srgb` (binned) | `EA1BEBC51572B051` | `795C5042DB38C0B8` | yes |
| `--merge pyramid --srgb` (7032x4688 demosaic) | `683BA2CD2B75124A` | `667BABABD74312FF` | yes |

The estimator arm needed `STREHL_PHOTOMETRIC=off` in **both** arms to run at all,
because the tree I built from carries another lane's uncommitted change forcing
photometric normalisation on; that is not this lane's defect and is held constant
across the pair.

## 9. Defects found

### D1 (MEDIUM, provenance): the banner does not declare the roll-off

Two runs of one binary differing only in `STREHL_HIGHLIGHT_KNEE` emit
**byte-identical banners** — 4676 bytes each, equal modulo timings — and
**different pixels**:

| arm | banner | output SHA-256 (first 20) |
| --- | --- | --- |
| `KNEE=off` | identical | `043D6114C05999280122` |
| default | identical | `54AF15A99595B0F89855` |

Neither run prints any line containing `highlight`, `knee`, `roll-off` or
`chroma`. Only a *non-default numeric* knee announces itself. The two settings
that matter most — on-by-default, and the off switch this report tells readers to
use — are both silent.

This contradicts rule 47 as quoted in `byte-freezes.tsv`: *"record the WHOLE
invocation beside every hash — the flags you left at their default AND the
environment you ran it in. A hash without its command is not a weak record, it is
not a record at all."* An A/B on this switch cannot be audited from its own logs.

Reproduce: render any saturating subject twice with `--merge pyramid
--linear-srgb`, once with `KNEE=off`, and diff the stderr against the hashes.

### D2 (MEDIUM, latent): `STREHL_HIGHLIGHT_KNEE` is not in `RENDER_ENV`

`crates/strehl-cli/tests/byte-freeze.rs:410-473` lists the environment variables
cleared before every frozen render. The new variable is absent; the only two
occurrences of the string in the whole Rust tree are in `highlight.rs` itself
(lines 103 and 113).

The list's own closing comment, written twice already, predicts this exactly:
*"a default flip can turn a dormant unrecorded input into a live one without
anything in this file changing. The list is not made safe by being complete on the
day it was written — and it is not made safe by having said so, either."* This is
a new, on-by-default, render-changing environment variable added without
registering it. That is the third occurrence of the defect the file documents.

**It is latent, not live**: both frozen rows are `srgb=no`, and section 2 proves
camera-linear is immune, so no frozen hash can move today. It becomes live the
moment any colorimetric row is frozen.

### D3 (LOW): `0` disables the roll-off but `0.0` does not

Measured across the parsing matrix, one binary, `coffee-bubbles --limit 4`:

| value | result |
| --- | --- |
| `off`, `OFF`, `" off "`, `0` | roll-off DISABLED, **silently** |
| `0.0`, `0.00`, `1`, `1.0`, `abc`, `-0.5`, `nan` | ON at default 0.60, with a stderr warning |
| `0.60` | ON, prints `knee moved to 0.6 (was 0.6)` |

`highlight.rs:151` special-cases the literal string `"0"` but the numeric branch
requires `x > 0.0`, so `0.0` falls through to the default. A harness writing
`0.0` to mean "off" gets the roll-off at full strength. It does warn on stderr, so
it is not silent — which is why this is LOW and not MEDIUM.

## 10. What remains unverified

* **"The null was predicted before rendering."** Unfalsifiable from the artifacts.
  The substance — that the null holds — is confirmed; the ordering claim is not
  checkable and I make no finding on it.
* The seven-subject null widening used `--limit 10`, not full stacks.
* My post-fix binary was built from a working tree carrying three other lanes'
  uncommitted changes (`main.rs`, `merge_cmd.rs`, `photometric.rs`). Every A/B
  above is same-binary and therefore immune; the two cross-build comparisons came
  out bit-identical, which independently shows those changes do not reach this
  render path.
* No test anywhere asserts the end-to-end behaviour this lane measured — that a
  saturating subject changes and `109MSDCF` does not. `highlight.rs` has twelve
  unit tests covering the arithmetic (luminance preservation, the below-knee null,
  exposure commutation, endpoint degradation), and they are good, but the
  corpus-level null and potency exist only in this report and in
  `docs/research/BUILD-HIGHLIGHT.md`. A future edit could make the roll-off inert
  on real data and every test would still pass.

---

# Phase 2 — the pre-registered flower-bud prediction

ORCH registered a prediction before I tested it: `flower-bud-alone-cpl` carries a
visible magenta/violet fringe where the pale bud lobe meets blown-out white
background, seen on a pre-fix pin (`C46BDF06A7136F54`) an hour before
BUILD-HIGHLIGHT reported and without knowledge of that work. The prediction was
that a post-fix binary at the default knee should measurably reduce that fringe,
and that `STREHL_HIGHLIGHT_KNEE=off` should bring it back. Two failure modes
were named in advance and I was told to report either as loudly as a success.

## Verdict: REFUTED, failure mode 1. The fringe is unchanged — bit-exactly.

All four arms below are the **same binary**
`471D50DA15D1575916AC16D3338C497F1CD18D09511873E56F972119AA110432`, same subject,
same flags, one environment variable varied.

| arm | flags | knee | SHA-256 (first 16) |
|---|---|---|---|
| `fba-srgb-off`     | `--merge pyramid --pyramid-gate 4.5 --srgb` | `off` | `DC5135A714F90E87` |
| `fba-srgb-default` | `--merge pyramid --pyramid-gate 4.5 --srgb` | default 0.60 | `DC5135A714F90E87` |
| `fba-lin-off`      | `--merge pyramid --pyramid-gate 4.5 --linear-srgb` | `off` | `5154995376C34865` |
| `fba-lin-default`  | `--merge pyramid --pyramid-gate 4.5 --linear-srgb` | default 0.60 | `5154995376C34865` |

Banners were identical across each pair apart from the varied knee:

```
merge backend   : pyramid (--merge)
lateral CA      : CORRECTING (gear matched; default on)
noise gate      : 4.50
tone            : black 0.01259, white 1.18627 (linear), contrast 0.55
```

The roll-off does not touch this subject at all, in either the measurement
render or the viewing render ORCH actually looked at.

## The null is commissioned — this is not broken wiring

A null is worthless unless the instrument could have failed it. On the **same
subject, same flags, same binary**, knee `0.05`:

```
python experiments/V-HIGHLIGHT/diffstat.py fba-lin-off.tiff fba-lin-k005.tiff
pixels moved      : 6611150 / 8250880 = 80.1266%
  R max|d|    384   G max|d|    139   B max|d|    639
```

80.13% of the frame moves. The code path is reached on this subject; it declines
to act at 0.60 because of level, not because of plumbing.

## Why: the subject never approaches the container

`strehl probe D:\personal\macro\flower-bud-alone-cpl`:

```
levels          : black 512, white 15360
wb coeffs       : [2.6464844, 1, 1.4589844, NaN]
```

so `k0 = (16383-512)/14848 = 1.068898` and the per-channel ceilings are
R 2.8288 / G 1.0689 / B 1.5595. Measuring `u = v_c / ceil_c` directly off the
camera-linear render (`experiments/V-HIGHLIGHT/umeasure.py`):

```
frame max u            : 0.3125
   p99.99  u = 0.3106       p100 u = 0.3125
argmax channel of u    : R 0.00%  G 100.00%  B 0.00%
KNEE = 0.60. Pixels above it: 0 (0.000000%)
brightest pixel: raw DN = 5471 DN of a 16383 container
pixels at 65535 in camera-native: 0.000000%
```

**The brightest pixel in the frame uses 31% of the sensor's raw container.**
Nothing is clipped. The "blown-out white background" is not blown — it is a
heavily under-exposed capture that the `--srgb` tone curve lifts to white with a
`1/0.36547 = 2.74x` gain. Green is indeed the first channel to run out of
headroom (it is the `argmax` of `u` on 100% of pixels, exactly as the author's
mechanism predicts) — it simply never gets close to running out.

So the roll-off is behaving correctly. Its null here is principled and exact.

## Failure mode 2 (lateral CA): supported in part, NOT established

I ran the discriminator ORCH specified. First with a raw magenta index
`(R+B)/2 - G` minus a local mean, it looked strongly CA-like: T1 antisymmetry
`-483.8` outward vs `+483.6` inward, T2 separation growing `-174 -> -1294` with
radius. **That result is contaminated and I am discarding it.** The confound
check shows `corr(normalised chroma, luminance) = +0.7320` on edge pixels, so a
pure intensity edge at constant hue fakes the antisymmetry.

Re-run with a scale-invariant chroma metric (`experiments/V-HIGHLIGHT/radial2.py`):

* **T1 antisymmetry** — shipping arm gives outward `-0.00067`, inward `+0.02928`.
  That is "inward edges are magenta, outward edges are neutral", not the clean
  sign reversal CA requires. With CA correction **off** the two sides have the
  **same** sign (`+0.021`, `+0.007`) — the antisymmetry does not survive.
* **T2 radial growth** — shipping arm is **flat**: `-0.0275, -0.0237, -0.0305,
  -0.0308, -0.0280, -0.0269` across radius octiles, a trend of `-0.00029`/octile,
  about 1% of the value. No radial growth.
* Disabling CA correction removes only **19.7%** of the magenta excess at the
  fringe, and that A/B is itself unclean because the correction resamples
  99.9988% of pixels.
* **Demosaic is excluded**: the binned arm (`--linear-srgb`, one sensor quad per
  pixel, no interpolation) carries *more* edge chroma than the Malvar-He-Cutler
  arm, `0.03530` vs `0.02829`. Caveat: the two arms differ in tone as well as
  demosaic, so this is suggestive rather than conclusive.

## What IS solid

**T3 rules out clipping asymmetry on its own.** Mean absolute chroma excess at
edges, by luminance quintile, shipping arm:

```
lum  3182-26698 : 0.04649
lum 26698-36599 : 0.03522
lum 36599-44214 : 0.02573
lum 44214-50404 : 0.01917
lum 50404-60527 : 0.01486
```

It decreases monotonically with level, by 3.1x from darkest to brightest. A
clipping-driven chroma error must do the opposite. Identical shape in the CA-off
arm. Combined with `max u = 0.3125`, the artefact ORCH saw **cannot** be the
mechanism `highlight.rs` addresses.

The fringe is real — I can see it in my own render on the upper lobe rim, and it
is visually unchanged between CA-on and CA-off. It belongs to a different lane
and it is currently **unattributed**. I could not identify its cause and I am not
going to guess.

## Consequences for the author's claims

Nothing in Phase 1 is overturned. Claims 1-8 stand as verified. But two of them
now read differently:

* Claim 7, "96.6% of `coffee-bean`'s clipped pixels were coloured, not blown", is
  arithmetically true and I reproduced it exactly. It does **not** generalise to
  "the coloured highlight artefacts a viewer notices are this defect". The one
  artefact in the corpus that a human independently flagged is not this defect,
  and the fix is bit-exactly inert on it.
* The corpus null is now 9 subjects wide, and for `flower-bud-alone-cpl` I can
  state the reason numerically rather than by absence: `max u = 0.3125` against a
  `0.60` knee.

I did not measure sharpness on this subject and make no claim about it.

---

# Correction — my own seven-subject null was outside the instrument's range

Prompted by the fleet standing question: *what property of the input decides
whether this check can see anything, and have I varied it?* Applied to my own
Phase 1 work it has one obvious target, and the answer was no.

In section 3 I wrote that claim 2 was **"CONFIRMED, and widened to 8 subjects"**,
having screened seven the author never tested and found all byte-identical. For a
knee-gated roll-off the property that decides whether byte-identity means
anything is the subject's **max `u`**. I never measured it for those seven.

Measured now — same pinned binary `471D50DA...`, same `--merge pyramid
--limit 10`, per-subject WB and levels from `strehl probe`:

```
subject               max u   p99.99   raw DN   verdict
112MSDCF             0.1086   0.0796     2236   below knee -- roll-off CANNOT fire
113MSDCF             0.2304   0.1674     4168   below knee -- roll-off CANNOT fire
119MSDCF             0.5449   0.2919     9159   below knee -- roll-off CANNOT fire
wrapped-text-1       0.1488   0.1459     2874   below knee -- roll-off CANNOT fire
flowers-cpl          0.2659   0.2590     4732   below knee -- roll-off CANNOT fire
lavendar-cpl         0.2236   0.2167     4060   below knee -- roll-off CANNOT fire
bee-3-cpl            0.3188   0.3123     5571   below knee -- roll-off CANNOT fire

subjects able to reach the 0.60 knee: 0 of 7
max u across all seven          : 0.5449
```

**All seven sit below the knee.** Their byte-identity was guaranteed a priori by
the arithmetic and carries no information about whether the roll-off is correct.
A null is only evidence if the instrument could have failed it, and on these
seven it could not.

**I retract "widened to 8 subjects."** The correct statement is that the null
rests on the author's `109MSDCF` — the one subject whose headroom was actually
measured (`u <= 0.5707`) — plus seven subjects that were never in the sensitive
range. The null's support is **not** materially wider than the author's report
claimed, and my sentence saying otherwise should not be relied on.

The rest of section 3 stands: potency was established separately on
`coffee-bubbles` (0.2807% of pixels moved, same binary, one env var), and the
knee-0.05 negative control moved 67.5582% of `109MSDCF`. Those are real. It is
only the *widening* that was empty.

Worth naming precisely, because it is the same error I flagged in others twice
tonight. I credited the author for predicting `109MSDCF`'s null from measured `u`
*before* rendering, and I refuted their `bee-2-cpl` worst case by recomputing
what they had asserted. Then I extended their null by seven subjects without
performing the measurement I had just praised them for. The check I ran could not
have come out any other way, and I reported its result as though it could.

`119MSDCF` at `0.5449` is the closest of the seven and still short of `0.60`. The
corpus subject that comes nearest the knee remains the author's own `109MSDCF` at
`0.5707`. Finding a corpus subject that genuinely crosses the knee, other than
the saturating ones already known (`coffee-bubbles`, `coffee-bean`, `foam`,
`tweezers-cpl`), remains open.
