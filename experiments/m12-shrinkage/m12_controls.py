"""M12 controls C3 and C4, and the `wide64` robustness arm.

**C3 (null).**  Two synthetic stacks, `n = 79` and `n = 63`, built by resampling
a real 112 / 113 base frame along a *planted* magnification path whose total is
set to that stack's own measured total.  The geometry is therefore planted at the
same magnitude as the real thing, and the per-frame differential displacement
matches, so the control is not answering an easier question than the treatment.
Fact 45 says the shrinkage needs a real inter-frame content change; a planted
warp has none of the right kind, so the ladder must come back flat.

**C4 (positive).**  A known magnification increment planted on *real*
defocus-mismatched pairs from 112 and 113.  M10's P7.  Ratio 1.000 means the
estimator responds correctly to a small geometric change at that span.

**`wide64` robustness.**  `wide64` reports 0 no-fit pairs on both new stacks.
SYNTHESIS §5 item 19: that is not evidence.  It is scored here on the
independent metric of whether its ladder agrees with `m10`'s.

Run:  python m12_controls.py
"""

from __future__ import annotations

import csv
from collections import defaultdict

import numpy as np

from m12_ladder import ladder, load_stack, pct

SYNTH = [("synth-112 (n=79, planted -3.7448%)", "data/synth-112-edges.csv", 79),
         ("synth-113 (n=63, planted -3.0210%)", "data/synth-113-edges.csv", 63)]
REAL = [("112MSDCF", "data/stack-112-edges.csv", 79),
        ("113MSDCF", "data/stack-113-edges.csv", 63)]
C3_LO, C3_HI = 0.85, 1.20


def c3() -> int:
    print("=" * 78)
    print("C3  NULL - planted geometry, no real defocus change")
    print(f"  Pass condition (registered): S_48(1) in [{C3_LO}, {C3_HI}].")
    print("=" * 78)
    bad = 0
    for name, path, n in SYNTH:
        st = load_stack(name, path, n, cfg="m10")
        ld = ladder(st, 0, 48)
        print(f"\n  {name}")
        print(f"    anchor A_48 = {pct(ld.anchor):+.4f}%  "
              f"({ld.anchor_used} tiles, rms {ld.anchor_rms:.2f})")
        print(f"    {'span':>5} {'T_48(s) %':>12} {'S_48(s)':>9} {'1/S':>7}")
        for s in ld.spans:
            print(f"    {s:>5} {pct(ld.total[s]):>12.4f} {ld.frac[s]:>9.4f} "
                  f"{1.0 / ld.frac[s]:>7.3f}")
        ok = C3_LO <= ld.frac[1] <= C3_HI
        bad += 0 if ok else 1
        print(f"    S_48(1) = {ld.frac[1]:.4f}   {'PASS' if ok else 'FAIL'}")
    print(f"\n  C3 {'PASS' if bad == 0 else 'FAIL'} - the harness does not manufacture "
          "a ladder.")
    return bad


def c4() -> int:
    print()
    print("=" * 78)
    print("C4  POSITIVE - known increment planted on REAL defocus-mismatched pairs")
    print("  Registered: ratio >= 0.95 at |g| = 4e-3, and < 0.9 at |g| = 2e-4.")
    print("=" * 78)
    bad = 0
    for tag, path in [("112MSDCF", "data/stack-112-increment.csv"),
                      ("113MSDCF", "data/stack-113-increment.csv")]:
        rows = []
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if not r["ratio"]:
                    continue
                rows.append(dict(span=int(r["span"]), g=float(r["g_plant"]),
                                 ratio=float(r["ratio"]), used=int(r["used0"])))
        mags = sorted({abs(r["g"]) for r in rows})
        print(f"\n  {tag}")
        print(f"    {'span':>5} {'med_used':>9} " +
              "".join(f"{f'|g|={m:.0e}':>13}" for m in mags))
        cell = defaultdict(list)
        for r in rows:
            cell[(r["span"], round(abs(r["g"]), 9))].append(r["ratio"])
        for s in sorted({r["span"] for r in rows}):
            used = [r["used"] for r in rows if r["span"] == s]
            line = f"    {s:>5} {np.median(used):>9.0f} "
            for m in mags:
                v = cell.get((s, round(m, 9)), [])
                line += f"{np.median(v):>13.3f}" if v else f"{'-':>13}"
            print(line)
        big = [r["ratio"] for r in rows if abs(abs(r["g"]) - 4e-3) < 1e-9 and r["span"] <= 4]
        small = [r["ratio"] for r in rows if abs(abs(r["g"]) - 2e-4) < 1e-9 and r["span"] <= 4]
        mb, ms = float(np.median(big)), float(np.median(small))
        ok_b, ok_s = mb >= 0.95, ms < 0.9
        bad += 0 if (ok_b and ok_s) else 1
        print(f"    spans 1-4: median ratio at |g|=4e-3 = {mb:.3f} "
              f"{'PASS' if ok_b else 'FAIL'}   at |g|=2e-4 = {ms:.3f} "
              f"{'PASS' if ok_s else 'FAIL'}")
    print(f"\n  C4 {'PASS' if bad == 0 else 'FAIL'}")
    return bad


def wide64_arm() -> None:
    print()
    print("=" * 78)
    print("ROBUSTNESS ARM - wide64 scored on an independent metric, not on its")
    print("  own 0-no-fit count (SYNTHESIS section 5 item 19)")
    print("=" * 78)
    print(f"    {'stack':>12} {'cfg':>8} {'S_48(1)':>9} {'1/S':>7} {'A_48 %':>9} "
          f"{'anchor tiles':>13} {'anchor rms':>11}")
    for name, path, n in REAL:
        for cfg in ("m10", "wide64"):
            st = load_stack(name, path, n, cfg=cfg)
            ld = ladder(st, 0, 48)
            print(f"    {name:>12} {cfg:>8} {ld.frac[1]:>9.4f} "
                  f"{1.0 / ld.frac[1]:>7.3f} {pct(ld.anchor):>9.4f} "
                  f"{ld.anchor_used:>13} {ld.anchor_rms:>11.2f}")


def main() -> int:
    bad = c3() + c4()
    wide64_arm()
    print()
    print("ALL CONTROLS PASS" if bad == 0 else f"{bad} CONTROL(S) FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
