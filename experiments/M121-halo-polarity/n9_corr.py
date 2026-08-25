"""N9 -- is quantisation error correlated ACROSS EDGES, and does that break N8?

ORCH withdrew the triage rule entirely (2026-08-24 21:57) and reported a result
that lands directly on M121's N8 claim:

    "Quantisation error is not noise.  It is correlated across frames, and it
     disables the very estimators you would use to detect it."
     cross-half r = +0.5109 for 8-bit narrowing vs -0.0007 for random dither.

N8 argued the M121 headline is protected by AVERAGING over n = 70 edges.  If
quantisation error were as correlated across those edges as ORCH measured it
across frames, averaging would buy almost nothing and N8's central claim would
be wrong.

**The number that does not fit, reported first.**  N8's measured pooled shift of
2.4% between the fully-independent bound (0.96%) and the fully-correlated bound
(8.04%) implies, via SE(mean) = sigma * sqrt((1 + (N-1)*rho) / N),

        rho_implied  ~  0.076

against ORCH's measured **r = +0.5109**.  That is a 6.7x discrepancy in the same
physical quantity, and one of the two numbers is measuring something the other
is not.  This script chases it rather than banking the favourable half.

**The hypothesis.**  Rounding is a deterministic function of PIXEL VALUE.  So
two samples share a rounding error when they share a *value*, not when they
share an image.  ORCH's frames are the same scene at the same exposure -- the
same pixel holds nearly the same value in every frame, so the errors coincide
almost perfectly, and r is high.  M121's 70 edges sit at *different brightness
levels* spread across the frame, so their rounding errors should be nearly
independent, and rho should be low.

If that is right, the two numbers are not in conflict at all, and the rule is:

    quantisation error correlates across samples that share a VALUE,
    not across samples that share a FRAME.

**Predictions, stated before the measurement:**

  P-A. Per-edge shifts should be weakly correlated overall (rho << 0.51).
  P-B. Edges whose levels sit close together should have MORE similar shifts
       than edges far apart -- a measurable dependence of shift similarity on
       level proximity.  If P-B fails, the value-sharing explanation is dead
       and the rho discrepancy needs another mechanism.
  P-C. Restricting to a narrow band of edge levels should RAISE the implied
       rho toward ORCH's figure.

P-B is the falsifier.  If shift similarity is flat in level proximity, say so.

Outputs: C:\\dev\\strehl-out\\M121\\n9\\n9-corr.json
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from m121_io import OUT, arm_path, load_u16, luma  # noqa: E402
from runner import scan  # noqa: E402
import e2_polarity as E2  # noqa: E402

N9 = OUT / "n9"
BITS = 8  # exactly the PIL defect commissioned in N5


def narrow(a, bits):
    return (a >> bits).astype(np.uint32) * (1 << bits)


def implied_rho(pooled_pct, per_edge_pct, n):
    """Invert SE(mean) = sigma*sqrt((1+(N-1)rho)/N) for rho."""
    f = (pooled_pct / per_edge_pct) ** 2
    return (f * n - 1.0) / (n - 1.0)


def main():
    N9.mkdir(parents=True, exist_ok=True)
    out: dict = {"bits": BITS}

    p = arm_path("armM4-gate4-binlin")
    print(f"loading {p.name} ...")
    rgb = load_u16(p)
    clean = luma(rgb)
    dirty = luma(narrow(rgb, BITS))
    del rgb

    frames = [luma(load_u16(arm_path(f))) for f in E2.FRAMES]
    fmax = np.max(np.stack([E2.focus_field(f) for f in frames]), axis=0)
    classify = E2.make_classifier(fmax)
    del frames, fmax

    kw = dict(isolation_frac=E2.ISO, flat_tol=E2.FLAT_TOL, classify=classify,
              min_amplitude=E2.MIN_AMPLITUDE)

    det = scan(clean, label="N9 detect", grad_percentile=E2.GRAD_PCT,
               max_edges=E2.MAX_EDGES, collect_edges=True, verbose=False,
               max_rise=E2.commissioned_max_rise(), **kw)
    donor = det["kept_edges"]
    print(f"donor edges: {donor.shape[0]}")

    a = scan(clean, label="N9 clean", edges=donor, max_rise=None,
             verbose=False, **kw)
    b = scan(dirty, label="N9 narrowed", edges=donor, max_rise=None,
             verbose=False, **kw)

    # Exact pairing on (y, x): same seeds, so any edge present in both runs is
    # the same edge.  Acceptance can differ by an edge or two under narrowing.
    sa, sb = a["bright"], b["bright"]
    ka = {(int(y), int(x)): i for i, (y, x) in enumerate(zip(sa["ys"], sa["xs"]))}
    kb = {(int(y), int(x)): i for i, (y, x) in enumerate(zip(sb["ys"], sb["xs"]))}
    common = sorted(set(ka) & set(kb))
    if len(common) < 20:
        raise SystemExit(f"N9 HARD ERROR: only {len(common)} paired edges; "
                         "cannot measure a correlation structure on this.")
    ia = np.array([ka[k] for k in common])
    ib = np.array([kb[k] for k in common])
    print(f"paired edges: {len(common)} "
          f"(clean had {len(ka)}, narrowed {len(kb)})")

    ra = np.asarray(sa["per_edge_band"])[ia]
    rb = np.asarray(sb["per_edge_band"])[ib]
    hi = np.asarray(sa["hi"])[ia]
    lo = np.asarray(sa["lo"])[ia]
    delta = rb - ra
    n = delta.size

    # P-A: how big is the per-edge perturbation, and how much does pooling help?
    per_edge_pct = 100.0 * np.median(np.abs(delta)) / abs(np.median(ra))
    pooled_pct = 100.0 * abs(np.median(rb) - np.median(ra)) / abs(np.median(ra))
    rho = implied_rho(pooled_pct, per_edge_pct, n) if per_edge_pct > 0 else float("nan")

    print("\n" + "=" * 76)
    print("P-A -- per-edge perturbation and the correlation it implies")
    print("=" * 76)
    print(f"  paired edges n                 : {n}")
    print(f"  median per-edge |shift|        : {per_edge_pct:.2f}%")
    print(f"  pooled shift                   : {pooled_pct:.2f}%")
    print(f"  averaging gain                 : {per_edge_pct / max(pooled_pct, 1e-9):.2f}x "
          f"(sqrt(n) = {np.sqrt(n):.2f}x if independent)")
    print(f"  implied rho across edges       : {rho:+.4f}")
    print(f"  ORCH's cross-FRAME r           : +0.5109")
    out["P_A"] = {"n": int(n), "per_edge_pct": per_edge_pct,
                  "pooled_pct": pooled_pct, "implied_rho": float(rho),
                  "orch_cross_frame_r": 0.5109,
                  "averaging_gain": float(per_edge_pct / max(pooled_pct, 1e-9)),
                  "sqrt_n": float(np.sqrt(n))}

    # P-B, the falsifier: do edges at similar LEVELS get similar shifts?
    # Compare |delta_i - delta_j| for close-in-level pairs vs far-in-level pairs.
    print("\n" + "=" * 76)
    print("P-B -- does shift similarity depend on LEVEL proximity?  (falsifier)")
    print("=" * 76)
    step = float(1 << BITS)
    lvl = hi / step                      # where each edge's top sits, in units
    D = np.abs(lvl[:, None] - lvl[None, :])
    S = np.abs(delta[:, None] - delta[None, :])
    iu = np.triu_indices(n, k=1)
    dv, sv = D[iu], S[iu]
    qs = np.quantile(dv, [0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    print(f"  {'level gap (units)':<26}{'pairs':>8}{'median |d_i - d_j|':>22}")
    bands = []
    for k in range(5):
        m = (dv >= qs[k]) & (dv <= qs[k + 1] if k == 4 else dv < qs[k + 1])
        if m.sum() < 10:
            continue
        med = float(np.median(sv[m]))
        bands.append({"gap_lo": float(qs[k]), "gap_hi": float(qs[k + 1]),
                      "pairs": int(m.sum()), "median_abs_diff": med})
        print(f"  [{qs[k]:7.1f},{qs[k+1]:7.1f})       {int(m.sum()):>8}{med:>22.5f}")
    out["P_B"] = {"bands": bands}
    if len(bands) >= 3:
        x = np.array([b["median_abs_diff"] for b in bands])
        trend = float(x[-1] / x[0]) if x[0] > 0 else float("nan")
        # Spearman without scipy: rank correlation of gap vs dissimilarity.
        gv = np.array([0.5 * (b["gap_lo"] + b["gap_hi"]) for b in bands])
        rg, rx = np.argsort(np.argsort(gv)), np.argsort(np.argsort(x))
        sp = float(np.corrcoef(rg, rx)[0, 1])
        out["P_B"]["far_over_near"] = trend
        out["P_B"]["spearman_gap_vs_dissimilarity"] = sp
        print(f"\n  far/near ratio of dissimilarity : {trend:.3f}")
        print(f"  Spearman(level gap, dissimilarity): {sp:+.3f}")
        if trend > 1.15 and sp > 0.5:
            print("  -> P-B SURVIVES: edges close in level do get more similar "
                  "shifts, so the error is value-locked, not frame-locked.")
        else:
            print("  -> P-B FAILS: shift similarity is flat in level proximity. "
                  "The value-sharing explanation is DEAD and the rho gap needs "
                  "another mechanism.  Report it as unexplained.")

    # P-C: restrict to a narrow level band and see whether rho climbs.
    print("\n" + "=" * 76)
    print("P-C -- does rho rise inside a narrow level band?")
    print("=" * 76)
    order = np.argsort(lvl)
    rows = []
    for frac in (1.0, 0.5, 0.25):
        k = max(int(round(n * frac)), 12)
        # centre window of the level ordering
        s = (n - k) // 2
        idx = order[s:s + k]
        d2, r2a, r2b = delta[idx], ra[idx], rb[idx]
        pe = 100.0 * np.median(np.abs(d2)) / abs(np.median(r2a))
        po = 100.0 * abs(np.median(r2b) - np.median(r2a)) / abs(np.median(r2a))
        rr = implied_rho(po, pe, k) if pe > 0 else float("nan")
        span = float(lvl[idx].max() - lvl[idx].min())
        rows.append({"frac": frac, "n": int(k), "level_span_units": span,
                     "per_edge_pct": pe, "pooled_pct": po, "implied_rho": float(rr)})
        print(f"  frac={frac:<5} n={k:<4} level span={span:8.1f}  "
              f"per-edge={pe:6.2f}%  pooled={po:6.2f}%  rho={rr:+.4f}")
    out["P_C"] = rows
    ns = [r["n"] for r in rows]
    print(f"\n  sample count across rungs: {ns} -> "
          f"{'varies' if len(set(ns)) > 1 else 'SATURATED -- tests nothing'}")

    with open(N9 / "n9-corr.json", "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {N9 / 'n9-corr.json'}")


if __name__ == "__main__":
    main()
