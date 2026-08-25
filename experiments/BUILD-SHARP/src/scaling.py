"""Scaling control: how much of the flat-window difference is really noise?

Two merges from disjoint HALVES differ by noise of variance u plus any
scale-independent floor S (signal that fails to cancel -- different elections, and
sub-pixel misregistration between the two arms, neither of which depends on how
many frames went in).  Two merges from disjoint QUARTERS have half as many frames
admitted per pixel, so the noise term doubles while the floor does not:

    P_half    = u + S
    P_quarter = 2u + S

Writing f = S / (u + S) for the contaminated fraction of the half-difference,

    r = P_quarter / P_half = 2 - f          =>       f = 2 - r

so the ratio measures the contamination directly.  r = 2.0 means pure noise;
r = 1.0 means the difference contains no frame-count-dependent component at all and
is entirely signal.

The windows are identical between the two runs by construction: pick_flat_windows
reads only the full merge, which is the same file in both cases.
"""

from __future__ import annotations

import json

HALF = "experiments/BUILD-SHARP/out/flatspec-bee1.json"
QUART = "experiments/BUILD-SHARP/out/flatspec-bee1-Q.json"

# Windows judged clean by LOOKING at the difference crops (top row of
# pictures/halves/bee1-flatdiff.png): grainy mottle, no legible structure.  The
# remaining windows contain visible hairs and ommatidia and are excluded here --
# they are reported separately rather than silently dropped.
CLEAN = [0, 1, 2, 3]


def main() -> None:
    h = json.load(open(HALF, encoding="utf-8"))
    q = json.load(open(QUART, encoding="utf-8"))
    hs, qs = h["window_diff_sd"], q["window_diff_sd"]
    assert h["windows"] == q["windows"], "window sets differ; comparison invalid"

    print(f"half  offset {h['offset']}      quarter offset {q['offset']}")
    print("\n  win   sd_half   sd_quarter   power ratio r   f = 2 - r   verdict")
    fs = []
    for i, (a, b) in enumerate(zip(hs, qs)):
        r = (b / a) ** 2
        f = 2.0 - r
        tag = "clean" if i in CLEAN else "CONTAMINATED by eye"
        if i in CLEAN:
            fs.append(f)
        print(f"  {i:3d}   {a:7.0f}   {b:10.0f}   {r:13.3f}   {f:9.3f}   {tag}")

    fbar = sum(fs) / len(fs)
    print(f"\nclean windows: mean r = {2-fbar:.3f}, mean f = {fbar:.3f}")
    print(f"  -> {100*fbar:.0f}% of the flat-window difference power does NOT scale")
    print(f"     with frame count, so it is not noise.")
    print(f"  -> genuine noise is {100*(1-fbar):.0f}% of the measured difference;")
    print(f"     P_noise should be scaled by {1-fbar:.3f}.")

    print("\nCAVEAT that limits this: the two comparisons needed DIFFERENT integer")
    print(f"offsets ({h['offset']} vs {q['offset']}), so the two arms are not in the")
    print("same geometry in both runs and the floor S is not guaranteed equal")
    print("between them.  f = 2 - r assumes it is.  Treat f as indicative, not exact.")


if __name__ == "__main__":
    main()
