"""h10 -- the frame-wide output-clip census, for the ORCH cross-cut with BUILD-ELECT.

WHY THIS EXISTS. BUILD-ELECT measured that the pyramid arm pins `== 65535` on
4.65% of the frame where the estimator pins 1.87%. That is the *writer's*
clamp, which is precisely the second of the two ceilings BUILD-HIGHLIGHT
identified -- so their statistic and my defect are the same pixels seen from
two sides. ORCH asked whether my roll-off's correctness depends on the clip
rate. This counts it, on both arms, on the subjects I already rendered.

WHAT IT IS NOT. BUILD-ELECT's headline is a *band* statistic (47-93 px) whose
ROI definition I do not have. I do not reproduce it and I do not guess at it.
This is frame-wide only, and is comparable to their frame-wide row (1.87% /
4.65%) and to nothing else in their report.

SELF-TEST. `--selftest` plants three arrays with known pinned fractions and
requires the counter to recover them, and requires it to report exactly zero
on an array with no pinned pixel. A counter that has never been shown to
return non-zero AND zero on demand is not an instrument. This mirrors the trap
BUILD-CHROMA fell into: a gate that removed zero pixels on all eight rows and
still printed a verdict.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import tifffile

PIN = 65535


def census(img: np.ndarray) -> dict:
    """Fraction of pixels pinned at the container top, frame-wide.

    `img` is (H, W, 3) uint16. Returns per-channel and any-channel fractions.
    """
    if img.ndim != 3 or img.shape[2] != 3:
        raise ValueError(f"expected (H,W,3), got {img.shape}")
    if img.dtype != np.uint16:
        raise ValueError(f"expected uint16, got {img.dtype}")
    pinned = img == PIN
    n = img.shape[0] * img.shape[1]
    return {
        "r": float(pinned[:, :, 0].sum()) / n,
        "g": float(pinned[:, :, 1].sum()) / n,
        "b": float(pinned[:, :, 2].sum()) / n,
        "any": float(pinned.any(axis=2).sum()) / n,
        "all": float(pinned.all(axis=2).sum()) / n,
        "px": n,
        "max": [int(img[:, :, c].max()) for c in range(3)],
    }


def selftest() -> None:
    """Show the counter can return both zero and a known non-zero value."""
    rng = np.random.default_rng(20260826)

    # 1. Clean array: must report EXACTLY zero. This is the case BUILD-CHROMA's
    #    gate silently produced and never checked for.
    clean = rng.integers(0, 60000, size=(200, 300, 3), dtype=np.uint16)
    c = census(clean)
    assert c["any"] == 0.0, f"clean array reported {c['any']}, expected 0"
    assert c["all"] == 0.0

    # 2. Planted array: a known fraction pinned on ALL channels.
    planted = clean.copy()
    planted[:20, :, :] = PIN  # 20/200 rows = exactly 10%
    p = census(planted)
    assert abs(p["any"] - 0.10) < 1e-12, f"planted any={p['any']}, expected 0.10"
    assert abs(p["all"] - 0.10) < 1e-12, f"planted all={p['all']}, expected 0.10"
    assert abs(p["g"] - 0.10) < 1e-12

    # 3. One-sided plant: blue only. `any` must move, `all` must NOT -- this is
    #    the channel asymmetry the whole lane is about, so the counter has to
    #    distinguish them or it cannot see the defect.
    one = clean.copy()
    one[:10, :, 2] = PIN  # 5% of pixels, blue channel only
    o = census(one)
    assert abs(o["b"] - 0.05) < 1e-12, f"one-sided b={o['b']}, expected 0.05"
    assert o["r"] == 0.0 and o["g"] == 0.0
    assert abs(o["any"] - 0.05) < 1e-12
    assert o["all"] == 0.0, "a blue-only plant must not register as all-channel"

    # 4. The counter must be sensitive to a SINGLE pixel -- otherwise a low
    #    true rate reads as zero and we repeat the "removed zero pixels" error.
    solo = clean.copy()
    solo[7, 11, 1] = PIN
    s = census(solo)
    assert s["g"] == 1.0 / (200 * 300), f"single-pixel plant read {s['g']}"
    assert s["any"] > 0.0

    print("h10 selftest: PASS -- counter returns exact zero on clean, 0.10 on")
    print("  an all-channel plant, 0.05 blue-only with all=0, and resolves a")
    print("  single pinned pixel (1/60000).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pair", nargs=3, action="append", metavar=("NAME", "BEFORE", "AFTER"))
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        if not a.pair:
            return 0

    rows = {}
    hdr = f"{'subject':<16} {'arm':<7} {'any%':>8} {'R%':>8} {'G%':>8} {'B%':>8} {'all%':>8}"
    print(hdr)
    print("-" * len(hdr))
    for name, before, after in a.pair or []:
        rec = {}
        for arm, path in (("before", before), ("after", after)):
            c = census(tifffile.imread(path))
            rec[arm] = c
            print(
                f"{name:<16} {arm:<7} {100 * c['any']:>8.4f} {100 * c['r']:>8.4f} "
                f"{100 * c['g']:>8.4f} {100 * c['b']:>8.4f} {100 * c['all']:>8.4f}"
            )
        b, f = rec["before"]["any"], rec["after"]["any"]
        rec["delta_any"] = f - b
        rec["ratio_any"] = (f / b) if b > 0 else None
        rows[name] = rec
        if b > 0:
            print(f"{name:<16} {'->':<7} any-channel clip {100 * b:.4f}% -> {100 * f:.4f}%  ({f / b:.3f}x)")
        else:
            print(f"{name:<16} {'->':<7} any-channel clip 0.0000% -> {100 * f:.4f}%  (no clipping either side)")
        print()

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1, sort_keys=True)
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
