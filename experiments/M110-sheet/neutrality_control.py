#!/usr/bin/env python
"""Controls for the blown-highlight readouts in sheet.py.

Two instruments are under test:

  neutrality()      the original ONE-SIDED readout. Selects on red AND blue
                    pinned, measures green against them.
  highlight_stats() the two-sided replacement. Selects channel-agnostically on
                    "blown in at least one channel", so neither failure
                    direction can empty the mask.

Why the replacement exists, in one line: `e9ad010` applies a saturation ceiling,
so a ceiling computed too low clamps RED AND BLUE DOWN -- dropping them below
the one-sided mask entirely. The old instrument would not merely under-report a
bad port, it would fall silent and print "too few blown px to score".

PLANTS ARE APPLIED BY LOWERING A CHANNEL, never by raising one. That is not a
convenience: it is how both real failures arise -- magenta leaves green low, a
low ceiling leaves red and blue low -- and lowering has room where raising hits
the container ceiling. Raising is what made the earlier sign bar fail.

Registered bars, fixed before running:
  N1   null       unmodified tile reproduces its own value exactly
  P1   magenta    planting -0.10 recovers -0.10 +/- 0.002
  P2   green      planting +0.10 recovers +0.10 +/- 0.002   <- the new direction
  P3   symmetry   |recovered(+0.10)| - |recovered(-0.10)| <= 0.002, so the
                  instrument has the SAME gain in both directions
  P4   linearity  +/-0.02 and +/-0.05 recovered +/- 0.002
  B1   shift      the systematic from letting the mask float, as a NUMBER
  B2   bias-only  that systematic is a constant offset, not a gain error:
                  it must not grow with plant size (spread <= 0.002)
  H1   headroom   BOTH directions have >= 0.30 of range at the 5th percentile
  H2   contrast   the OLD readout fails to report the same green plant --
                  demonstrating the blindness rather than asserting it
  D1   diagnosis  a green plant lowers c_r and c_b while leaving c_g alone, so
                  the pinned-channel fractions identify the failure direction
  M1   mask       planting outside the region must not move the readout

P1-P4 and D1 run on a FROZEN mask. The mask is not invariant under the thing it
measures -- lowering a channel can push a pixel below HOT and out of the
population, moving the mean for a reason that is not the neutrality of the
pixels that remain. Freezing it separates gain from that shift. B1/B2 then
measure the shift itself on the free mask that actually ships, so the
systematic is reported rather than hidden by the freeze.

Run:  python neutrality_control.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheet import CROP, FULL, HOT, highlight_stats, load_raw, neutrality  # noqa: E402

TILE = (5320, 560)                       # bee-3-cpl `clipped`, frozen in subjects.json
SRC = Path(r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif")
TOL = 0.002


def plant(win: np.ndarray, delta: float, off_region: bool = False) -> np.ndarray:
    """Plant a neutrality error of `delta` full-scale units, by LOWERING.

    delta < 0  magenta         -> lower green
    delta > 0  green overshoot -> lower red and blue

    Both are applied on the channel-agnostic blown region, or on its complement
    when `off_region` is set.
    """
    out = win.copy()
    ch = [out[:, :, i].astype(np.float32) for i in range(3)]
    region = np.maximum(np.maximum(ch[0], ch[1]), ch[2]) >= HOT
    mask = ~region if off_region else region
    if delta < 0:
        ch[1][mask] = np.clip(ch[1][mask] + delta * FULL, 0, FULL)
    else:
        for i in (0, 2):
            ch[i][mask] = np.clip(ch[i][mask] - delta * FULL, 0, FULL)
    for i in range(3):
        out[:, :, i] = ch[i].astype(np.uint16)
    return out


def main() -> int:
    if not SRC.exists():
        sys.exit(f"missing {SRC} -- run `python sheet.py render` first")
    raw = load_raw(SRC)
    x, y = TILE
    win = raw[y:y + CROP, x:x + CROP]
    del raw

    s = highlight_stats(win)
    base = s["off"]
    if base is None:
        sys.exit("tile has too few blown pixels to score -- control cannot run")
    print(f"tile @{TILE}   blown region {s['region_frac'] * 100:.3f}% of tile "
          f"({s['region_n']} px)")
    print(f"  two-sided off {base:+.6f}   pinned r{s['c_r']:.3f} g{s['c_g']:.3f} "
          f"b{s['c_b']:.3f}   asym {s['asym']:+.3f}")
    core = s["core_off"]
    print(f"  one-sided core {core:+.6f} over {s['core_n']} px\n"
          if core is not None else f"  one-sided core n/a ({s['core_n']} px)\n")

    R: list[tuple[str, bool, str]] = []

    # The mask frozen on the unplanted tile. P1-P4 and D1 measure the
    # instrument's GAIN against a fixed population; B1/B2 then measure what
    # letting it float costs.
    ch0 = [win[:, :, i].astype(np.float32) for i in range(3)]
    region0 = np.maximum(np.maximum(ch0[0], ch0[1]), ch0[2]) >= HOT
    base_f = highlight_stats(win, region=region0)["off"]

    def rec(w, frozen: bool = True) -> float:
        if frozen:
            return highlight_stats(w, region=region0)["off"] - base_f
        return highlight_stats(w)["off"] - base

    # N1
    again = highlight_stats(win.copy())["off"]
    R.append(("N1 null", again == base, f"recomputed {again:+.6f} vs {base:+.6f}"))

    # P1 / P2 -- both directions, the same fidelity demanded of each.
    got_m, got_g = rec(plant(win, -0.10)), rec(plant(win, +0.10))
    R.append(("P1 magenta -0.10", abs(got_m + 0.10) <= TOL,
              f"recovered {got_m:+.6f}, want -0.10 +/- {TOL}"))
    R.append(("P2 green   +0.10", abs(got_g - 0.10) <= TOL,
              f"recovered {got_g:+.6f}, want +0.10 +/- {TOL}"))

    # P3 -- equal gain in both directions, not merely nonzero in each.
    R.append(("P3 symmetry", abs(abs(got_g) - abs(got_m)) <= TOL,
              f"|{got_g:+.6f}| - |{got_m:+.6f}| = {abs(got_g) - abs(got_m):+.6f}"))

    # P4 -- linearity, both signs.
    for d in (-0.05, -0.02, +0.02, +0.05):
        gg = rec(plant(win, d))
        R.append((f"P4 linearity {d:+.2f}", abs(gg - d) <= TOL,
                  f"recovered {gg:+.6f}, want {d:+.2f} +/- {TOL}"))

    # B1/B2 -- the cost of letting the mask float, which is what ships.
    free = {d: rec(plant(win, d), frozen=False) - d for d in
            (-0.10, -0.05, -0.02, +0.02, +0.05, +0.10)}
    bias_m = [v for d, v in free.items() if d < 0]
    bias_g = [v for d, v in free.items() if d > 0]
    worst = max(abs(v) for v in free.values())
    R.append(("B1 mask-shift", worst <= 0.01,
              f"free mask biases the reading by {min(bias_m):+.5f}..{max(bias_m):+.5f} "
              f"(magenta) and {min(bias_g):+.5f}..{max(bias_g):+.5f} (green); "
              f"worst {worst:.5f}, want <= 0.01"))
    spread = max(max(bias_m) - min(bias_m), max(bias_g) - min(bias_g))
    R.append(("B2 bias-only", spread <= TOL,
              f"bias varies by {spread:.6f} across plants 0.02..0.10, so it is a "
              f"constant offset and not a gain error; want <= {TOL}"))

    # H1 -- dynamic range, in both directions, as a number.
    hm, hg = s["head_magenta"], s["head_green"]
    R.append(("H1 headroom", min(hm, hg) >= 0.30,
              f"magenta {hm:.4f}, green {hg:.4f} (p05 of range); want both >= 0.30"))

    # H2 -- the blindness, demonstrated on the old instrument rather than argued.
    _, old_base = neutrality(win)
    _, old_green = neutrality(plant(win, +0.10))
    if old_green is None:
        blind, how = True, ("went SILENT -- its red-AND-blue mask emptied, so it "
                            "reports nothing at all")
    else:
        moved = abs(old_green - (old_base or 0.0))
        blind, how = moved < 0.01, f"moved only {moved:.6f}"
    R.append(("H2 old-readout blind", blind,
              f"one-sided readout {how}, on a +0.10 green plant the two-sided one "
              f"recovered as {got_g:+.4f}"))

    # D1 -- the pinned-channel fractions must identify the direction.
    sg = highlight_stats(plant(win, +0.10), region=region0)
    ok = (sg["c_r"] < s["c_r"] - 0.05 and sg["c_b"] < s["c_b"] - 0.05
          and abs(sg["c_g"] - s["c_g"]) < 1e-9)
    R.append(("D1 diagnosis", ok,
              f"green plant: c_r {s['c_r']:.3f}->{sg['c_r']:.3f}, "
              f"c_b {s['c_b']:.3f}->{sg['c_b']:.3f}, c_g {s['c_g']:.3f}->{sg['c_g']:.3f}"))

    # M1 -- off-region plants must not move it, in either direction.
    m_off = max(abs(rec(plant(win, -0.10, off_region=True))),
                abs(rec(plant(win, +0.10, off_region=True))))
    R.append(("M1 mask", m_off <= 1e-9, f"max move off-region {m_off:+.9f}; want 0"))

    print(f"{'bar':<22} {'verdict':<7} detail")
    for name, ok, detail in R:
        print(f"{name:<22} {'PASS' if ok else 'FAIL':<7} {detail}")
    n_fail = sum(1 for _, ok, _ in R if not ok)
    print(f"\n{len(R) - n_fail}/{len(R)} bars passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
