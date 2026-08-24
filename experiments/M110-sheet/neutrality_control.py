#!/usr/bin/env python
"""Controls for the blown-highlight neutrality readout in sheet.py.

The readout printed on the `clipped` tile is a claim about the render, so it
needs to be a claim about the instrument first. Reading ~0 on a neutral tile
shows only that the instrument is quiet; it does not show it can respond at
all. So: a null, a planted positive, a sign check, and a mask check.

Registered bars, fixed before running:
  N1  null      unmodified tile reproduces the sheet's printed value exactly
  P1  positive  planting -0.10 on blown pixels reads back -0.10 +/- 0.002
  P2  linearity three plants (-0.02, -0.05, -0.10) each recovered +/- 0.002
  S1  sign      from a planted magenta baseline, a +0.06 move reads back as a
                POSITIVE change of +0.06, not merely as "nonzero"
  H1  headroom  green headroom on blown pixels is < 1%, so the readout is
                ONE-SIDED BY CONSTRUCTION: it measures green deficit (magenta)
                faithfully and is structurally blind to green excess. Registered
                as a bar rather than a caveat because it bounds what the sheet
                can be trusted to show.
  M1  mask      planting on NON-blown pixels only must NOT move the readout,
                or the readout is measuring the whole tile and not the
                highlight it claims to measure

Run:  python neutrality_control.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheet import CROP, FULL, HOT, load_raw, neutrality  # noqa: E402

TILE = (5320, 560)                       # bee-3-cpl `clipped`, frozen in subjects.json
SRC = Path(r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif")
TOL = 0.002


def plant(win: np.ndarray, delta: float, on_blown: bool = True) -> np.ndarray:
    """Add `delta` (in full-scale units) to green, on blown or on non-blown pixels."""
    out = win.copy()
    r = out[:, :, 0].astype(np.float32)
    b = out[:, :, 2].astype(np.float32)
    blown = (r >= HOT) & (b >= HOT)
    mask = blown if on_blown else ~blown
    g = out[:, :, 1].astype(np.float32)
    g[mask] = np.clip(g[mask] + delta * FULL, 0, FULL)
    out[:, :, 1] = g.astype(np.uint16)
    return out


def main() -> int:
    if not SRC.exists():
        sys.exit(f"missing {SRC} -- run `python sheet.py render` first")
    raw = load_raw(SRC)
    x, y = TILE
    win = raw[y:y + CROP, x:x + CROP]
    del raw

    frac, base = neutrality(win)
    print(f"tile @{TILE}  blown {frac * 100:.3f}% of tile  green offset {base:+.6f}\n")
    if base is None:
        sys.exit("tile has too few blown pixels to score -- control cannot run")

    results: list[tuple[str, bool, str]] = []

    # N1 -- null.
    f2, again = neutrality(win.copy())
    ok = (again == base) and (f2 == frac)
    results.append(("N1 null", ok, f"recomputed {again:+.6f} vs {base:+.6f}"))

    # P1 / P2 -- planted magnitude and linearity.
    for d in (-0.02, -0.05, -0.10):
        _, got = neutrality(plant(win, d))
        rec = got - base
        ok = abs(rec - d) <= TOL
        tag = "P1 positive" if d == -0.10 else "P2 linearity"
        results.append((f"{tag} {d:+.2f}", ok,
                        f"recovered {rec:+.6f}, want {d:+.2f} +/- {TOL}"))

    # S1 -- sign, not merely magnitude. A sign-blind readout would pass P1 and
    # still be unable to tell a magenta highlight from a green one.
    #
    # This MUST be tested from a planted magenta baseline, not from the render.
    # On a genuinely blown pixel green is already at or next to full scale, so a
    # positive plant has nowhere to go and saturates -- an earlier version of
    # this bar planted +0.06 directly and recovered +0.000344, which is not a
    # sign-blindness defect but the clip ceiling, and is measured by H1 below.
    _, got = neutrality(plant(plant(win, -0.10), +0.06))
    rec = got - base
    ok = rec > -0.10 and abs(rec - (-0.04)) <= TOL
    results.append(("S1 sign", ok,
                    f"recovered {rec:+.6f} from a -0.10 baseline, want ~-0.04 "
                    f"(i.e. moved POSITIVE by +0.06)"))

    # H1 -- the ceiling that S1 tripped over, measured rather than asserted.
    g = win[:, :, 1].astype(np.float32)
    r0, b0 = win[:, :, 0].astype(np.float32), win[:, :, 2].astype(np.float32)
    m = (r0 >= HOT) & (b0 >= HOT)
    head = float(((FULL - g[m]) / FULL).mean())
    at_full = float(np.mean(g[m] >= FULL))
    ok = head < 0.01
    results.append(("H1 headroom", ok,
                    f"mean green headroom {head:.5f}, {at_full * 100:.1f}% of blown "
                    f"px already at full scale -> readout is one-sided"))

    # M1 -- mask discrimination.
    _, got = neutrality(plant(win, -0.10, on_blown=False))
    rec = got - base
    ok = abs(rec) <= 1e-9
    results.append(("M1 mask", ok, f"moved {rec:+.9f} when planting off-mask; want 0"))

    print(f"{'bar':<22} {'verdict':<7} detail")
    for name, ok, detail in results:
        print(f"{name:<22} {'PASS' if ok else 'FAIL':<7} {detail}")

    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - n_fail}/{len(results)} bars passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
