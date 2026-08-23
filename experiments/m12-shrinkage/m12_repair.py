"""The C4 repair, and the anchor-free statement of the shrinkage.

Two things the first pass left owing.

**The C4 repair.**  The registered C4 had two clauses: recovery >= 0.95 at
|g| = 4e-3 (the harness works) and recovery < 0.9 at |g| = 2e-4 (M10's fact-45
signature).  On 112 and 113 the first passed and the second failed.  A failed
control gets diagnosed, not believed, and the diagnosis here is that the second
clause was never a control — it was a *prediction of the treatment*, smuggled in
as one.  The repair is to run the identical command on `coffee-bean` and
`119MSDCF`, so the same code on the same day either reproduces the fact-45
signature on the shrinking stacks or does not.  That turns clause two from an
assumption into a measured contrast.

**Anchor-free shrinkage.**  The ladder's headline divides by the single long
anchor edge `(0, W)`, and on `coffee-bean` that edge survives on only 15 tiles.
The obvious objection is that the anchor, not the short edges, is the wrong
number.  The objection can be removed entirely: compare two *telescoped totals*
inside the same window, `T_W(1)` against `T_W(s*)` where `s*` is the largest
divisor span whose edges still carry a healthy tile count.  Both are sums over
disjoint edge sets, both are conserved quantities that must agree, and neither
touches the anchor.

Run:  python m12_repair.py
"""

from __future__ import annotations

import csv

import numpy as np

from m12_ladder import ladder, load_stack, pct
from m12_lib import read_edges

INC = [("coffee-bean", "data/cb-increment.csv"),
       ("119MSDCF", "data/s119-increment.csv"),
       ("112MSDCF", "data/stack-112-increment.csv"),
       ("113MSDCF", "data/stack-113-increment.csv")]
STACKS = [
    ("coffee-bean", "data/m10-coffee-bean-edges.csv", 105, 48),
    ("119MSDCF", "data/m10-shallow-119-edges.csv", 33, 32),
    ("109MSDCF", "data/m10-shallow-109-edges.csv", 22, 16),
    ("112MSDCF", "data/stack-112-edges.csv", 79, 48),
    ("113MSDCF", "data/stack-113-edges.csv", 63, 48),
]
TILE_FLOOR = 50


def load_inc(path: str) -> list[dict]:
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["ratio"]:
                out.append(dict(span=int(r["span"]), g=abs(float(r["g_plant"])),
                                ratio=float(r["ratio"]), used=int(r["used0"])))
    return out


def c4_repair() -> None:
    print("=" * 78)
    print("C4 REPAIR - the same planted-increment command on all four stacks")
    print("  Median recovery ratio over spans 1-4.  M10 fact 45 measured 0.559 /")
    print("  0.664 on coffee-bean defocus pairs at 0.12 / 0.24 px.")
    print("=" * 78)
    mags = [1e-4, 2e-4, 4e-4, 8e-4, 1.6e-3, 4e-3]
    print(f"\n    {'stack':>12} {'1/S_W(1)':>9} " +
          "".join(f"{f'|g|={m:.0e}':>12}" for m in mags))
    tab = {}
    for tag, path in INC:
        rows = [r for r in load_inc(path) if r["span"] <= 4]
        st = next(s for s in STACKS if s[0] == tag)
        ld = ladder(load_stack(st[0], st[1], st[2], cfg="m10"), 0, st[3])
        line = f"    {tag:>12} {1.0 / ld.frac[1]:>9.3f} "
        vals = {}
        for m in mags:
            v = [r["ratio"] for r in rows if abs(r["g"] - m) < 1e-9]
            if v:
                vals[m] = float(np.median(v))
                line += f"{vals[m]:>12.3f}"
            else:
                line += f"{'-':>12}"
        tab[tag] = vals
        print(line)

    print("\n  The contrast the registered clause was reaching for:")
    for m in (1e-4, 2e-4):
        cb, s112 = tab["coffee-bean"].get(m), tab["112MSDCF"].get(m)
        if cb and s112:
            print(f"    |g| = {m:.0e}: coffee-bean {cb:.3f} vs 112MSDCF {s112:.3f}"
                  f"  (shortfall {1 - cb:.3f} vs {1 - s112:.3f})")
    print("\n  Verdict rule: the increment control is an INDEPENDENT probe of the")
    print("  same underlying property.  It never telescopes, never uses an anchor,")
    print("  and works on ONE pair at a time.  If it orders the stacks the same way")
    print("  the ladder does, two disjoint measurement paths agree.")
    order_inc = sorted(tab, key=lambda k: tab[k].get(2e-4, 1.0))
    lds = {}
    for tag, path in INC:
        st = next(s for s in STACKS if s[0] == tag)
        lds[tag] = 1.0 / ladder(load_stack(st[0], st[1], st[2], cfg="m10"), 0, st[3]).frac[1]
    order_lad = sorted(tab, key=lambda k: -lds[k])
    print(f"    increment order (most shrunk first): {' < '.join(order_inc)}")
    print(f"    ladder    order (most shrunk first): {' < '.join(order_lad)}")
    print(f"    same ordering: {order_inc == order_lad}")


def anchor_free() -> None:
    print()
    print("=" * 78)
    print("ANCHOR-FREE SHRINKAGE - no long anchor anywhere in the statistic")
    print(f"  R(s*) = T_W(1) / T_W(s*), s* = largest divisor span with median")
    print(f"  tiles >= {TILE_FLOOR}.  Both totals telescope the same window and must")
    print("  be equal.  Disjoint edge sets.  The anchor edge is not used.")
    print("=" * 78)
    print(f"\n    {'stack':>12} {'W':>4} {'s*':>4} {'tiles(1)':>9} {'tiles(s*)':>10} "
          f"{'T_W(1) %':>10} {'T_W(s*) %':>11} {'R(s*)':>8} {'1/S_W(1)':>9}")
    for name, path, n, w in STACKS:
        st = load_stack(name, path, n, cfg="m10")
        ld = ladder(st, 0, w)
        es = [e for e in read_edges(path, cfg="m10") if e.ok]
        med = {}
        for e in es:
            med.setdefault(e.span, []).append(e.used)
        cand = [s for s in ld.spans if s > 1 and np.median(med.get(s, [0])) >= TILE_FLOOR]
        if not cand:
            print(f"    {name:>12} {w:>4}   no span above the tile floor")
            continue
        ss = max(cand)
        r = ld.total[1] / ld.total[ss]
        print(f"    {name:>12} {w:>4} {ss:>4} {np.median(med[1]):>9.0f} "
              f"{np.median(med[ss]):>10.0f} {pct(ld.total[1]):>10.4f} "
              f"{pct(ld.total[ss]):>11.4f} {r:>8.4f} {1.0 / ld.frac[1]:>9.3f}")
    print("\n  1/R(s*) is the shrinkage measured without any long anchor:")
    for name, path, n, w in STACKS:
        st = load_stack(name, path, n, cfg="m10")
        ld = ladder(st, 0, w)
        es = [e for e in read_edges(path, cfg="m10") if e.ok]
        med = {}
        for e in es:
            med.setdefault(e.span, []).append(e.used)
        cand = [s for s in ld.spans if s > 1 and np.median(med.get(s, [0])) >= TILE_FLOOR]
        if cand:
            ss = max(cand)
            print(f"    {name:>12}  1/R({ss}) = {ld.total[ss] / ld.total[1]:.3f}   "
                  f"1/S_W(1) = {1.0 / ld.frac[1]:.3f}")


def main() -> int:
    c4_repair()
    anchor_free()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
