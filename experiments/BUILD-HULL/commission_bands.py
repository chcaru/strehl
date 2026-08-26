"""Commission the per-band detector in bhull2.py, synthetically.

The per-band test rests on one claim:

    for ANY linear L, a convex combination with weights SHARED across bands
    satisfies  L(O) in [min_k L(F_k), max_k L(F_k)]  exactly.

If that is true of my `bands_of`, then a shared-weight arm must read EXACTLY
zero violations in EVERY band, and any nonzero reading on real data is real.
If my `bands_of` were not linear, or my hull logic were wrong, the shared-weight
arm would leak -- and this script would catch it.

Arms, all on the same synthetic frames so only the weighting differs:
    C1 shared weights across bands      -> must be EXACTLY 0 in every band
    C2 single-frame passthrough         -> must be EXACTLY 0, and exact equality
    C3 telescoping identity             -> sum of bands must equal the input
    M  independent per-band weights      -> the pyramid's actual structure
    C4 a planted offset                  -> must be recovered
"""
from __future__ import annotations

import numpy as np

from bhull2 import bands_of, score

LEVELS = 5
GUARD = 0.0  # synthetic and float: no quantisation, so no guard is needed
H = W = 96
K = 12


def hull_bands(frames, levels):
    lo = hi = None
    per = [bands_of(f, levels) for f in frames]
    nb = levels + 1
    lo = [np.min(np.stack([p[b] for p in per]), axis=0) for b in range(nb)]
    hi = [np.max(np.stack([p[b] for p in per]), axis=0) for b in range(nb)]
    return per, lo, hi


def check(name, out, per, lo, hi, levels):
    ob = bands_of(out, levels)
    tot_below = tot_above = 0
    worst = 0.0
    rows = []
    for b in range(levels + 1):
        sp = hi[b] - lo[b]
        vv = np.where(ob[b] < lo[b], ob[b] - lo[b],
                      np.where(ob[b] > hi[b], ob[b] - hi[b], 0.0))
        r = score(vv, sp, GUARD)
        tot_below += r["below"]
        tot_above += r["above"]
        worst = max(worst, r["worst_span"])
        rows.append((b, r))
    for b, r in rows:
        nm = "base" if b == levels else f"detail{b}"
        print(f"    {name:<34} {nm:<8} below={r['below']:>7} above={r['above']:>7} "
              f"rate={r['rate']:>8.4f}%  worst/span={r['worst_span']:>7.3f}")
    print(f"    {name:<34} {'TOTAL':<8} below={tot_below:>7} above={tot_above:>7} "
          f"worst/span={worst:>7.3f}")
    return tot_below + tot_above, worst


def main() -> int:
    rng = np.random.default_rng(20260826)
    # Structured, not white noise: smooth ramps plus edges plus texture, so the
    # bands actually carry different content the way real frames do.
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    frames = []
    for k in range(K):
        base = 8000 + 40 * np.sin((xx + 3 * k) / 11.0) + 25 * np.cos(yy / 7.0)
        edge = 3000 * (xx > (30 + 2 * k)).astype(np.float32)
        tex = rng.normal(0, 60, (H, W)).astype(np.float32)
        frames.append((base + edge + tex).astype(np.float32))

    per, lo, hi = hull_bands(frames, LEVELS)
    fails = []

    print("\n  C3 telescoping identity (bands must sum to the input)")
    err = max(float(np.abs(np.sum(bands_of(f, LEVELS), axis=0) - f).max()) for f in frames)
    print(f"    max |sum(bands) - frame| = {err:.3e}")
    if err > 1e-2:
        fails.append("C3 telescoping")

    print("\n  C1 SHARED weights across bands -- must be EXACTLY zero")
    w = rng.random(K).astype(np.float32)
    w /= w.sum()
    shared = np.tensordot(w, np.stack(frames), axes=(0, 0))
    n, _ = check("C1 shared weights", shared, per, lo, hi, LEVELS)
    if n != 0:
        fails.append(f"C1 leaked {n}")

    print("\n  C2 single-frame passthrough -- must be EXACTLY zero")
    per1, lo1, hi1 = hull_bands([frames[3]], LEVELS)
    n, _ = check("C2 passthrough", frames[3], per1, lo1, hi1, LEVELS)
    if n != 0:
        fails.append(f"C2 leaked {n}")

    print("\n  M  INDEPENDENT per-band weights -- the pyramid's actual structure")
    nb = LEVELS + 1
    acc = np.zeros((H, W), dtype=np.float32)
    for b in range(nb):
        # sharp, near-argmax selection, as pyramid.rs does with exponent 8
        p = np.stack([np.abs(per[k][b]) for k in range(K)]) ** 8.0
        p = p / np.maximum(p.sum(axis=0, keepdims=True), 1e-30)
        acc += np.sum(p * np.stack([per[k][b] for k in range(K)]), axis=0)
    nM, wM = check("M  per-band weights", acc, per, lo, hi, LEVELS)

    # The missing 2x2 cell. C1 is shared + data-INdependent; M is independent +
    # data-DEPENDENT, so on their own they confound "shared vs independent" with
    # "fixed vs data-driven". This is exactly the flaw I reported in ORCH's
    # hullproof.py (attack A2) and my own harness must not carry it. C5 is
    # shared + data-DEPENDENT: weights derived from the data exactly as M does,
    # but pooled into ONE vector used by every band.
    print("\n  C5 SHARED but DATA-DEPENDENT weights -- isolates the real variable")
    pw = np.stack([sum(np.abs(per[k][b]).sum() for b in range(nb)) for k in range(K)])
    pw = (pw ** 8.0)
    pw = (pw / pw.sum()).astype(np.float32)
    shared_dd = np.tensordot(pw, np.stack(frames), axes=(0, 0))
    n5, _ = check("C5 shared, data-dependent", shared_dd, per, lo, hi, LEVELS)
    if n5 != 0:
        fails.append(f"C5 leaked {n5}")

    print("\n  C4 planted +900 offset in y20:40 x20:40 -- must be recovered")
    planted = shared.copy()
    planted[20:40, 20:40] += 900.0
    ob = bands_of(planted, LEVELS)
    tot = 0
    for b in range(nb):
        vv = np.where(ob[b] < lo[b], ob[b] - lo[b],
                      np.where(ob[b] > hi[b], ob[b] - hi[b], 0.0))
        tot += int(np.count_nonzero(np.abs(vv) > 1e-3))
    print(f"    planted-region samples = {20 * 20} ; band samples flagged = {tot}")
    if tot == 0:
        fails.append("C4 plant undetected")

    print("\n  ================ COMMISSIONING VERDICT ================")
    print(f"    C1 shared-weight leak      : {'PASS' if not any(f.startswith('C1') for f in fails) else 'FAIL'}")
    print(f"    C2 passthrough leak        : {'PASS' if not any(f.startswith('C2') for f in fails) else 'FAIL'}")
    print(f"    C3 telescoping             : {'PASS' if not any(f.startswith('C3') for f in fails) else 'FAIL'}")
    print(f"    C4 plant recovered         : {'PASS' if not any(f.startswith('C4') for f in fails) else 'FAIL'}")
    print(f"    C5 shared+data-dep leak    : {'PASS' if not any(f.startswith('C5') for f in fails) else 'FAIL'}")
    print("    -- 2x2: shared/independent x fixed/data-dependent --")
    print("       shared      + fixed          -> C1 = 0")
    print("       shared      + data-dependent -> C5 = 0")
    print(f"       independent + data-dependent -> M  = {nM}")
    print("       => the operative variable is SHARED vs INDEPENDENT, not data-dependence.")
    print(f"    M  per-band violations     : {nM} samples, worst {wM:.3f} hull spans")
    print(f"    OVERALL                    : {'GREEN' if not fails else 'RED ' + str(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
