"""Append section 14 to docs/research/BUILD-BLEND.md (idempotent)."""

import io
import os

DOC = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "research", "BUILD-BLEND.md")
DOC = os.path.normpath(DOC)
MARK = "## 14. A census instead of a fourth assertion"

NOTE = """

## 14. A census instead of a fourth assertion, and a correction on my own commit

ORCH has now reported four times that `merge_cmd.rs` contains no reference to
the pyramid backend. Three times the report traced to a stale pinned tree and
three times I answered by re-counting references at HEAD. That answer has now
failed to persuade three times, which makes it the wrong answer regardless of
whether it is true. This section stops asserting and measures the environment
instead.

### 14.1 There are 105 copies of `merge_cmd.rs` on this machine

ORCH supplied a fingerprint without intending to: *"the four `blend` matches are
`support.blend()`, the edge-aware mask."* Zero `pyramid`, a few `blend`, at least
one `support.blend(`. That identifies a file by content, so the tree can be found
rather than argued about. `experiments/BUILD-BLEND/treecensus.py` walks the disk
and fingerprints every copy.

| | count |
|---|---:|
| copies of `merge_cmd.rs` under `C:\\dev` | **108** |
| copies with **zero** `pyramid` references | **72** |
| copies matching ORCH's fingerprint (0 `pyramid`, has `support.blend()`) | **34** |
| the live repository, `blog\\death-of-software\\projects\\strehl` | **100 `pyramid`** |

The count was 105 when I first ran it and 108 twenty minutes later, because other
lanes are creating trees while this is being written. The unwired copies are pins
and worktrees: `tree-ca-6a51e43`, `pin-1cacb61`, `vtone-pin`,
`BUILD-SHARP\\pin-aac3ee8`, `pure-head`, and three dozen more. Several are mine.
The wired copies run 22 -> 25 -> 28 -> 35 -> 50 -> 52 -> 70 -> 100 references,
which is the backend being built out commit by commit, and the live repository
sits at the top of that ladder.

**The conclusion is not that ORCH was careless.** Any agent in this workspace can
open a real file, read it correctly, and be wrong about the product, because
there are 105 candidates and nothing in a path like
`C:\\dev\\strehl-out\\pure-head\\crates\\strehl-cli\\src\\merge_cmd.rs` announces
that it is not the product. A name containing `head` is actively misleading. This
is an environment defect that has now consumed four exchanges across two agents,
and re-asserting a reference count does nothing about it. What does: quoting the
absolute path and `git rev-parse HEAD` beside any claim about what ships.

The live path, stated once so it can be copied:

    C:\\dev\\blog\\death-of-software\\projects\\strehl

### 14.2 The `--camera-linear` confound: chronology refutes it

ORCH asked, reasonably, whether my own pre-`0d9fd28` comparisons carry the
cross-space confound they had just caught in their own tooling -- specifically
the `+12.3%` flat-region noise number. It is a good question and it was cheap to
answer. It does not apply, for two independent reasons.

**Chronology.** `0d9fd28` (`--camera-linear`) is 08-25 **18:10**. `275fbd17` is
08-25 **23:05**, five hours *later*, and `git merge-base --is-ancestor 275fbd1
0d9fd28` returns false in that direction and true in the other. The reading that
shows the noise -- `1.1179` -- is the **later** pin. The clean reading, `1.0015`,
is the earlier one. So the number ORCH suspects was measured on a tree that
already contained the fix; the confound cannot reach it.

**Direct control, already run.** Section 7 tested measurement space explicitly at
a fixed pin: sRGB `4.6660` against linear `4.1718`, recorded there as *"not the
cause"*. The space was controlled by measurement, not by assumption.

### 14.3 The correction I owe, and it is against my own arm

Section 7 closes the noise investigation with this sentence:

> *"The difference is therefore between pins, in shared code I do not own, and I
> am not able to attribute it further."*

That is wrong, and it is wrong in the one direction an agent should never be
wrong in -- it moved a defect out of my own lane. `275fbd17` touched exactly two
files:

    crates/strehl-cli/examples/blend-render.rs |  32 ++-
    crates/strehl-core/src/pyramid.rs          | 341 ++++++++++++++++++++++++++++-

**Both are mine.** It is my commit, in my module, and it made `Hull::InputRange`
the *default* rather than adding an opt-in flag. The regression bisects to me. I
disowned it in writing while holding the commit that caused the pin boundary.

### 14.4 The mechanism I then proposed -- and its refutation

The module's own docstring argues the clamp "cannot cost anything real," on the
grounds that a value outside `[min_k, max_k]` is unsupported by the data. Reading
it again with 14.3 in hand, that argument is about **bias** and is silent on
**variance**, and there is a mechanism it does not exclude: where the clamp
binds, the output is no longer the reconstruction but an *extreme order statistic
of N noisy frames*. Extreme order statistics have high variance. Substituting one
for a smooth reconstruction is a plausible way to add high-frequency energy in
exactly the flat regions where `min_k` and `max_k` are pure noise.

`experiments/BUILD-BLEND/hullnoise.py` tests it. One binary at HEAD, one flag
apart, `couch-fibers-cpl` (299 frames, the do-no-harm control subject),
`--camera-linear` so no tone stage is in the path. The design carries an internal
control that the cross-pin comparisons never had: **the arms differ by one flag,
so `A != B` is exactly the set of pixels where the clamp bound**, and every other
pixel is byte-identical by construction. A tile's bind fraction is therefore a
within-image dose. If the clamp is responsible, the effect must concentrate where
the dose is high.

Commissioned before the verdict was read:

| control | expected | read | |
|---|---|---|---|
| null: arm A against itself | exactly 1.0000 | **1.0000** | exact |
| positive: synthetic Gaussian base, 120 DN plant | 1.1670 | **1.1653** | **1.0% of the effect** |
| sensitivity: real photograph, 81.4 DN plant | > 1 | 1.1009 | correct sign |

*The first positive control failed*, reading 1.1003 against a predicted 1.0198 --
406% of the effect. The failure was mine, not the instrument's: I predicted with
`sqrt(s^2 + amp^2)/s`, which is quadrature for two Gaussians, while measuring
with MAD on the highpass of real photographic detail, which is heavy-tailed. On a
heavy-tailed base MAD under-reads the base scale, so an added white component
inflates the ratio faster than quadrature predicts. Moving the positive control
onto a Gaussian base -- where the formula it uses is actually the right model --
brings it to 1.0% error. The real-data reading is kept as a *sensitivity*, not a
gate, because it bounds how far a quoted magnitude can be trusted.

The result, `couch-fibers-cpl`, 200 flattest 96 px tiles, clamped / unclamped:

| channel | dose | overall A/B | lowest-dose quartile | highest-dose quartile |
|---|---:|---:|---:|---:|
| R | 12.33% | 0.9841 | 0.9993 *(dose 1.60%)* | **0.9555** *(dose 27.22%)* |
| G |  9.40% | 0.9647 | 0.9980 *(dose 1.07%)* | **0.9076** *(dose 21.50%)* |
| B | 14.33% | 0.9770 | 0.9983 *(dose 2.03%)* | **0.9425** *(dose 30.57%)* |

**The hypothesis is refuted, and cleanly.** Every ratio is below 1.0: the clamped
arm is *quieter* than the unclamped one. The dose-response runs the right way in
all three channels -- tiles where the clamp barely bound read 0.998-0.999, i.e.
indistinguishable, as they must be since those pixels are nearly identical, while
tiles where it bound on 21-31% of pixels read 0.91-0.96. The clamp is not
injecting noise; it is removing excursions that were noise, and it removes more
of it exactly where it acts more.

So the docstring's conclusion survives -- but it survives for a reason it did not
state. Its argument was that the clamp cannot cost anything because the values it
removes are unjustified. The measured reason is stronger and different: the
values it removes are *noisier* than what replaces them. I have now corrected
that docstring once for overstating how inert the clamp is (section 13); this is
the opposite correction, and both came from measuring rather than from reading.

### 14.5 What this leaves open, now correctly scoped as mine

The `0d9fd28` -> `275fbd17` noise regression is **real and still unexplained, and
the clamp is not it** -- turning the clamp off makes flat regions worse, not
better, so it cannot be why noise rose at the commit that introduced it. Since
that commit touched only two files and both are mine, the remaining candidates
are inside my lane. It is not bisected. It is no longer disowned.

Also unchanged from section 13 and still the largest open number in this report:
the reconstruction puts **8.6-11.0%** of pixels outside the hull its own inputs
support on `flower-bud-alone-cpl`, and **2.1-7.0%** even on the flat control
subject. The clamp is load-bearing rather than a safety net, and 14.4 says it is
a *good* load-bearing part. The indicated attack remains the coarse-band
selection exponent, which is what generates the excursions in the first place.

*Nothing in this section was verified by its author beyond the commands quoted.
The renders, the instrument and its controls are committed and re-runnable:
`experiments/BUILD-BLEND/hullnoise.py`, `experiments/BUILD-BLEND/treecensus.py`.*
"""


def main():
    src = io.open(DOC, encoding="utf-8").read()
    if MARK in src:
        print("section 14 already present; nothing to do")
        return
    io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
    print(f"appended section 14 to {DOC}")
    print(f"now {len(io.open(DOC, encoding='utf-8').read().splitlines())} lines")


if __name__ == "__main__":
    main()
