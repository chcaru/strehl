"""O15 -- re-probe o12's arrays with the SPACING test, because o12's bar was wrong.

o12 called an array narrowed if it held < 4096 distinct levels. o14 showed that
bar is wrong in BOTH directions:

  - it CONVICTS low-contrast native data. ROI-FLAT is native (modal gap 1,
    97.3 % unit gaps) and holds 1110 levels. o12's bar would have failed it for
    being flat, which is the property it was selected for.
  - it CLEARS narrowed data that spans a wide range. A 16-bit array rescaled
    from 8 bits over a wide span still has only ~256 distinct values, but one
    quantised over a very wide range can exceed a naive count bar while sitting
    on a coarse lattice.

o12's conclusion may still be right; it was reached with a blunt instrument, and
"probably still right" is not a measurement. This re-reads the same arrays under
the spacing test, with the same planted 8-bit power control.

Integer and float arrays need different tests and this says which it used:
  - INTEGER: modal gap between consecutive distinct levels must be 1 (a lattice
    stride > 1 is the signature of a rescaled 8-bit stage).
  - FLOAT: no lattice to measure, but an 8-bit stage caps distinct values at
    ~256 regardless of range, so a count bar IS decisive here. Bar: > 4096.

BAR: every array o12 cleared must also clear under the correct test for its
dtype, and the planted arm must fail on every one of them.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import numpy as np
import tifffile

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

OUTD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
OUT_ROOT = pathlib.Path(r"C:\dev\strehl-out")
SAMPLE = 4_000_000
FLOAT_BAR = 4096
GAP1_BAR = 0.90


def sample(a):
    f = a[..., 0].reshape(-1) if a.ndim == 3 else a.reshape(-1)
    return f[:: max(1, f.size // SAMPLE)]


def verdict(s: np.ndarray) -> dict:
    u = np.unique(s)
    if np.issubdtype(s.dtype, np.floating):
        return dict(test="float-count", levels=int(u.size),
                    native=bool(u.size > FLOAT_BAR), modal_gap=None, gap1_frac=None)
    g = np.diff(u.astype(np.int64))
    vals, cnts = np.unique(g, return_counts=True)
    modal = int(vals[int(np.argmax(cnts))])
    f1 = float((g == 1).sum() / g.size)
    return dict(test="int-spacing", levels=int(u.size), modal_gap=modal,
                gap1_frac=f1, native=bool(modal == 1 and f1 >= GAP1_BAR))


def plant8(s: np.ndarray) -> np.ndarray:
    lo, hi = float(s.min()), float(s.max())
    if hi <= lo:
        return s.copy()
    q = np.round((s.astype(np.float64) - lo) / (hi - lo) * 255.0)
    r = q / 255.0 * (hi - lo) + lo
    return r.astype(s.dtype)


def main() -> int:
    targets = []
    d = OUT_ROOT / "M95-demosaic" / "scratch"
    for alg in ["AHD", "VNG", "LINEAR"]:
        targets.append((f"truth_{alg}.npy", d / f"truth_{alg}.npy", "npy"))
    targets.append(("M95-resample/rawpy-A.npy",
                    OUT_ROOT / "M95-resample" / "rawpy-A.npy", "npy"))
    for n in ["merge-g0-linear.tif", "merge-g0-noalign.tif"]:
        targets.append((f"M95-resample/{n}", OUT_ROOT / "M95-resample" / n, "tif"))

    rows, ctrl = [], 0
    print(f"BARS: int -> modal gap 1 and >= {GAP1_BAR:.0%} unit gaps; "
          f"float -> > {FLOAT_BAR} distinct\n")
    print(f"{'array':34s} {'arm':7s} {'test':13s} {'levels':>8s} "
          f"{'gap':>5s} {'gap==1':>8s}  verdict")
    for label, p, kind in targets:
        if not p.exists():
            raise SystemExit(f"COVERAGE FAILURE: {p} missing")
        a = tifffile.imread(str(p)) if kind == "tif" else np.load(p, mmap_mode="r")
        s = np.asarray(sample(a))
        for arm, ss in (("real", s), ("plant8", plant8(s))):
            v = verdict(ss)
            v.update(array=label, arm=arm, dtype=str(ss.dtype))
            rows.append(v)
            mg = "-" if v["modal_gap"] is None else str(v["modal_gap"])
            gf = "-" if v["gap1_frac"] is None else f"{v['gap1_frac']:.1%}"
            print(f"{label:34s} {arm:7s} {v['test']:13s} {v['levels']:8d} "
                  f"{mg:>5s} {gf:>8s}  {'NATIVE' if v['native'] else 'NARROWED'}")
            if arm == "plant8" and not v["native"]:
                ctrl += 1
        print()

    real = [r for r in rows if r["arm"] == "real"]
    print("=" * 84)
    print(f"POWER CONTROL: planted arm read NARROWED on {ctrl}/{len(targets)} arrays")
    if ctrl != len(targets):
        print("INSTRUMENT FAILED -- real-arm reading proves nothing.")
        return 1
    n = sum(r["native"] for r in real)
    print(f"REAL ARM: NATIVE on {n}/{len(real)}")
    print("VERDICT:", "o12's conclusion CONFIRMED under the correct test"
          if n == len(real) else "o12 WAS WRONG -- narrowing present")
    with open(os.path.join(OUTD, "o15_reprobe.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    return 0 if n == len(real) else 1


if __name__ == "__main__":
    raise SystemExit(main())
