"""Append section 57 to docs/research/ORCH-veiling.md.

Anchor-checked and idempotent: refuses to run unless the file still ends with
section 56's closing text, and refuses to run twice.
"""
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[2] / "docs" / "research" / "ORCH-veiling.md"

ANCHOR = (
    "So the remaining quality work is not a five-stage port. It is: whether the gate\n"
    "blurs the dark side, and whether the unwired restoration recovers the 1.43x the\n"
    "gather throws away. Two questions, both in flight, both with registered tests.\n"
)

MARKER = "## 57. Two audits, and the shape of the project changes"

BODY = """

## 57. Two audits, and the shape of the project changes

Two verifiers reported within an hour of each other. Neither was asked the
question it ended up answering, and between them they overturn section 54,
correct section 56's table, and settle an architectural question I had been
treating as open.

### 57.1 The restoration module's mathematics is exact and its safety case is worthless

V-RESTORE audited `restore.rs` from first principles at `a2582514`, with probe
binaries built into a scratch tree and nothing under `crates/` touched.

What it confirmed matters, because it means the module is worth repairing
rather than discarding. It did not read `align.rs` and trust it. It pushed a
delta through the product's own `Resampler::sample` at 8 phases across 5
resamplers, extracted the taps the sampler *actually applies*, and compared
`gather_mtf` against its own DTFT on a 201-point grid:

| resampler | max abs difference |
| --- | --- |
| nearest | 0.000e+00 |
| bilinear | 0.000e+00 |
| catmull-rom | 0.000e+00 |
| lanczos2 | 3.331e-16 |
| lanczos3 | 4.441e-16 |

The Wiener algebra is equally sound: at infinite SNR the gain converges to
exactly `1/MTF` to six places, `f=0` is exactly 1.0 for every signal power, and
the noise-floor subtraction is present at `design_fir:412`. On real pixels the
mean shifts by -3.2 ppm and the 50% edge crossing does not move at all,
550.000 DN before and 550.000 DN after. **This filter cannot move an edge or
change exposure.** The loss it corrects is real.

Then four defects, and the third is the one that matters.

**The gain cap bounds half the filter.** `restore_plane` convolves separably in
x then y with the same taps, but `design_fir` caps only the 1-D response.
Pushed a checkerboard at exactly fx=fy=0.5 through the shipped code: the report
says `max_gain=1.430534`, the pixels get `2.046517`, and `max_gain^2` is
2.046429. A caller asking for 1.7 gets 2.89.

**At the noise floor the shipped merge actually has, it rings.** The module
header claims that on a real hard edge "the largest profile change anywhere is
0.0035 of the step, and there is no ringing to see." Measured on `lavendar-cpl`:
**7.82% in 1-D, 16.25% at a 2-D corner** -- 22x the module's own claim. The
shape is a multi-lobed decaying ring, `107.95, 89.01, 137.33, 29.62`, because
taps k=2 and k=4 are both positive. On real camera-linear pixels at a real
silhouette, **3.75% of pixels are driven outside the min/max of their own 9-tap
input support**, worst excursion 7107.7 DN; one 13594 DN pixel between two
highlights lands at 6119.9 DN.

That is a halo. On the owner's subject. In the one place this project has just
finished proving it had removed one.

**And the reason the module did not know is that its verdict was measured at a
noise level the product does not have.** The docs reach "measured never to bind"
at sigma^2 = 691.6 and 4983.0. The actual HF noise floor of the shipped
`lavendar-cpl` green plane is **82.15 DN^2** -- 8x to 60x smaller, because the
merge averages frames and its output is quieter than any input. Across that
range `max_gain` swings from 1.005, which is inert, to 1.536, which is nearly
full strength. Nothing in `restore.rs` estimates sigma^2. It is a free parameter,
and whatever the wiring passes decides the entire behaviour of the feature.

**A fifth way for work to fail to reach the product**, and it is the subtlest so
far. The module was not unmeasured. It was measured, honestly, by a competent
author, and the verdict is void because the conditions were not the product's.

> **A module that takes a free parameter has no safety verdict until the product
> pins that parameter.** Its verdict is a claim about the values it was run at
> and about nothing else. Where the parameter is a noise level, note that the
> merge's output is quieter than its inputs, so a value measured on a frame is
> the wrong value for a merge.

> **When a guard is applied per-axis and the operator is separable, the guard
> bounds the square root of what the picture gets.** Assert on the realised
> quantity, never on the designed one.

Two more, both cheap and both of the silent class. `sigma2 = NaN` NaNs all 4096
pixels while `max_gain` reports a reassuring 1.0, because Rust's `f64::max`
ignores NaN and the cap loop never engages. A single NaN input pixel makes
`power_at`'s `p.max(0.0)` clamp the signal power to 1e-12, so the gain is 1.0
everywhere and the designed filter is the identity -- and the report is then
indistinguishable from a legitimate refusal to sharpen, while the NaN still
spreads to a 9x9 block.

### 57.2 The self-test passes a kernel the product does not use

`restore.rs:110-116` claims to pin agreement with `align.rs`'s samplers.
V-RESTORE mutated the Keys inner branch `2.5 -> 2.6`, and separately changed the
kernel outright with `a = -0.5 -> -0.75`. Both move MTF(0.25) from 0.9402 to
about 0.986. Both are a **different kernel from the one the product gathers
with**. `selftest()` returned GREEN for both.

The mechanism is worth stating because it is general. Arm 1 asserts `M(0) == 1`,
but `gather_mtf` divides by the tap sum before evaluating at f=0, so it computes
`sum/sum` and is 1 for any partition-of-unity kernel whatsoever. Arm 2 probes
only integer offsets, where the inner cubic contributes nothing but its constant
term and the outer branch takes over. The entire inner branch is invisible to
the test that exists to pin it. Only the hard-coded constants at line 573 catch
the mutation, and they cover `CatmullRom` alone.

> **A self-test that divides by the quantity it then checks is tautological.**
> The division launders any input into the expected answer.

**And my line 573 claim is withdrawn.** I routed it to an implementer as a
defect. The constants `(0.25, 0.9402), (0.40, 0.7425), (0.50, 0.6251)` are all
correct to five places against an independent DTFT, and 0.7425 is correctly
labelled f=0.40. What is wrong is any document quoting 0.7425 at f=0.35. The
per-axis value there is **0.8211**; the **1.43x everyone has been citing is the
two-dimensional figure**, 0.69776 measured on the real warpmap against 0.6743
under uniform phase.

That is the second unchecked number I relayed in one night, after the
magnification claim in section 55. Both arrived with my authority attached and
neither had my verification attached, and the receiving agent had no way to
tell them apart from something I had measured.

> **A relayed number carries the relayer's authority but not the relayer's
> verification.** Mark every routed claim as measured-by-me, measured-by-named-
> agent, or unchecked -- and instruct the recipient to reject unmarked ones.

### 57.3 The default backend is the least capable one

V-REACH audited reachability across both crates: a 366-item public-symbol census
and an independent 746-function call graph, the latter over-approximating
reachability by letting comment text create call edges, so its complement is a
sound dead set.

| census A: public items | count |
| --- | --- |
| LIVE-DEFAULT | 175 |
| LIVE-BY-FLAG | 154 |
| LIVE-BUT-INERT | 1 |
| TEST-ONLY | 14 |
| DEAD | 22 |
| UNRESOLVED | 0 |
| **total** | **366** |

Census B: 663 functions reachable from `main`, 83 not, totalling 746. One known
false positive among the 83 (`parse_roi`, referenced by a clap attribute rather
than a call), so at least 82 are genuine.

Section 54 found one module with no callers and treated it as an anomaly. It is
not an anomaly. **About 180 KB of finished, tested Rust never executes.**

- **`outlier.rs`, 51 KB, 13 of 13 public items, has zero references from any
  `src/` file in the repository.** No `use`, no path reference, nothing. Only
  four example binaries touch it. It is strictly worse off than `restore.rs`,
  which at least appears in a `pub mod` line. The four `outlier` hits elsewhere
  in the tree are the aligner's own unrelated `outlier_mads`.
- `through_focus.rs`, 90 KB, 12 of 12 public items, live only by flag on a
  backend the product does not use.
- `halo.rs`, 23 KB, estimator-only **and** additionally gated off by env.
- The whole M89 robust-election family is dead on **both** backends.
  `FocusStats::new_robust` has no callers anywhere; it is the only caller of
  `active_arm()`, which is the only reader of `STREHL_ROBUST_ELECTION`; so every
  public item of `robust.rs` is unreachable at runtime. Proved, not inferred:
  the env var gives byte-identical output on both backends against controls that
  differ.
- The measured PRNU is never attached on any path by any flag. This one is
  deliberate -- `profile.rs:778` asserts that the shipped profile must not
  attach a pattern -- but it strands the M71 gain correction with it.

The banner has been telling us this every single run. `not applied : photometric
gain, clip census, outlier rejection, halo correction, through-focus`. Four of
those five are fully written and live inside `run_estimator`; the fifth is
written and wired to nothing. The line is not a status. It is a confession, and
it has been printing on every render for weeks.

**So the project's shape is two merge backends: one holds the quality machinery
and stamps visible slabs, the other merges well and has none of it.** The
estimator is additionally broken out of the box -- `--merge estimator` on
`coffee-bubbles` exits rc=1 with `U3 the eroded low-detail region keeps only
0 px` unless `STREHL_PHOTOMETRIC=off` is pinned.

**The call, made now so it stops being re-litigated: pyramid is the product.**
It wins on picture quality, verified numerically and by eye on two subjects, and
it is about 25% faster. The estimator will not be fixed. Capability comes to
pyramid or it does not ship. And the ranking rule for what comes across is not
code volume:

> **"This is finished and tested, therefore we should use it" is the reasoning
> that put five stages behind a backend that stamps slabs.** Stranded code is a
> sunk cost, not an argument. The only question is whether wiring it changes
> pixels for the better on the owner's own captures.

### 57.4 A dead diagnostic on a live lossy operation

`Hull::InputRange` is the default and clamps every output pixel on the product
path. Its only measurement, `pyramid::clamped_fraction`, is called from an
example binary and from pyramid's own tests, and from nowhere else. **The clamp
fires silently on every shipped render and the number that would say how hard is
never computed.**

Worse, `Hull::Unclamped`'s doc comment claims it is "kept reachable because a
fix whose defect can no longer be reproduced cannot be measured
interventionally." For the product binary that claim is **false**: there is no
`--pyramid-hull` flag and no env var, and the only construction site outside
`pyramid.rs` is an example. The comment is a claim by an absent author about a
reachability that does not exist.

> **A dead diagnostic on a live lossy operation is worse than no diagnostic.**
> Its presence in the source reads as evidence the loss is being watched.

Section 56's table said the clip census was "not needed" because the hull clamp
was already verified live on the delivered masters. That was too quick.
Verifying that a clamp fires is not the same as knowing how much it takes, and
the instrument that would say is the dead one.

### 57.5 What is actually gone

Two things in this audit are not unwired but absent. **No hot-pixel or
defect-pixel correction exists anywhere in either crate** -- every textual hit is
prose. And `restore.rs` is the only MTF-restoration capability in the binary, so
the gather's two-dimensional amplitude loss is uncorrected on every shipped
frame and nothing else could correct it.

One thing I expected to find dead is alive, and it is worth recording because
the auditor checked it specifically for that reason. The lateral CA correction's
*accessors* have no non-test callers, which makes the module look stranded. The
correction itself runs on the product path via `warp_frame_in_place`, and the
ship log proves it: `lateral CA : CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl"
(gear matched; default on)`. Reporting it as dead on the strength of the
accessors would have been exactly the error this section is about, in reverse.
"""


def main() -> int:
    if not CORPUS.is_file():
        print(f"FAIL: corpus not found at {CORPUS}")
        return 1
    text = CORPUS.read_text(encoding="utf-8")

    if MARKER in text:
        print("SKIP: section 57 already present, nothing written")
        return 0

    if ANCHOR not in text:
        print("FAIL: anchor text not found -- corpus tail is not what section 56 left")
        return 1
    if not text.rstrip().endswith(ANCHOR.rstrip()):
        print("FAIL: anchor is present but is not the final text -- refusing to append")
        return 1

    before = len(text)
    CORPUS.write_text(text.rstrip("\n") + BODY, encoding="utf-8")
    after = len(CORPUS.read_text(encoding="utf-8"))
    print(f"OK: {before} -> {after} chars (+{after - before})")

    check = CORPUS.read_text(encoding="utf-8")
    if MARKER not in check:
        print("FAIL: marker absent after write")
        return 1
    if check.count(MARKER) != 1:
        print(f"FAIL: marker appears {check.count(MARKER)} times")
        return 1
    print("OK: marker present exactly once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
