"""M68 step 03 - POST-HOC. Where in the chain does the 0.84 act?

THIS IS NOT CONFIRMATORY. The pre-registration in `01-dark-iso-sweep.py`
(committed 71cd54c, before the sweep ran) asked one question with three
answers, and C3 returned its third branch: alpha_B/alpha_G2 = 0.85235,
in NEITHER the {P1,P5} band (1.000 +/- 0.05) nor the {P2,P3,P4} band
(0.705 +/- 0.05). The pre-registered consequence was "report the number
and refuse the binary", and the report does that.

Everything below is hypothesis *generation* off the back of that refusal.
It is labelled DERIVED or ARGUED in the report, never MEASURED-confirmatory,
except the three raw quantities D1/D2/D3 which are measurements of the
already-decoded cache and are labelled MEASURED.

---------------------------------------------------------------- the idea

Both pre-registered endpoints are one-parameter special cases of a
two-parameter family. Let the 0.84 act at some point X in the read chain.
Split the ISO-scaling dark variance (the `alpha` term, everything generated
upstream of the programmable gain) into the part generated upstream of X
and the part generated downstream of X but still upstream of the gain:

    alpha_B / alpha_G = f * s^2 + (1 - f),      f = U / (U + D)          (3)

  f = 1  ->  every ISO-scaling dark electron/volt is born ahead of X.
             This is P2, the analog attenuation.  Ratio = s^2 = 0.705.
  f = 0  ->  none of it is.  This is P1 (sense-node conversion gain: the
             source-follower noise is generated downstream of q/C and is
             therefore untouched) and equally P5 (charge sharing: in the
             dark there is no photo-charge to share).  Ratio = 1.000.

The pre-registration named only the endpoints because the endpoints are
what the two commissioned hypotheses predict. Equation (3) is the family
that contains them, and inverting it for f is the natural reading of a
result that landed between them. f is a *position* statistic: it says how
much of the dark-noise power sits on each side of the scale point.

    f = (1 - alpha_B/alpha_G) / (1 - s^2)                                (4)

s comes from M61 fact 22, 0.8396 +/- 0.0112, and its error is propagated.

------------------------------------------------------- what can kill this

Equation (3) assumes the effect is (a) a linear scale, (b) uniform over the
array, and (c) that sigma^2 = alpha*G^2 + delta describes B as well as it
describes green. Three failable checks, declared here before this script is
run, each with a stated consequence:

  D1  SPATIAL UNIFORMITY.  Fit alpha independently on a 4x4 grid of blocks
      and form alpha_B/alpha_G2 per block. If (max - min) over the 16 blocks
      exceeds 0.05, the effect is not a uniform per-plane scale, it has
      readout-geometry structure, and f is meaningless. CONSEQUENCE: report
      the block map instead of f and withdraw the position claim.

  D2  PEDESTAL.  The PTC divides by a mean measured above an assumed black
      of 512. If the true per-plane dark mean differs, var/mean is biased
      and s itself is wrong. Report the per-plane dark mean. If
      |mean_B - mean_G2| > 1.0 DN, flag M61 fact 22 as needing a black-level
      correction before f is quoted. CONSEQUENCE: quote f with that caveat
      attached and say by how much s would move.

  D3  RESIDUAL SHAPE.  B's two-term fit had max residual 8.23% against
      1.8-2.0% for the greens. If B's 11 residuals are systematic in sign
      across ISO (a run of >= 9 of 11 with the same sign inside a gain mode,
      or a monotone trend) the model is misspecified for B and f is not
      trustworthy. CONSEQUENCE: withdraw f and report only the raw
      sigma-ratio ladder.

------------------------------------------------------------- geometry (E)

Free exclusion, arithmetic on numbers already printed by 02. The CFA is
R  (even row, even col) / G1 (even row, odd col)
G2 (odd  row, even col) / B  (odd  row, odd col)

so B shares ROWS with G2 and COLUMNS with G1, and R shares rows with G1 and
columns with G2. A per-ROW-parity readout effect would put the 0.705 on
G2/G1 and on B/R. A per-COLUMN-parity effect would put 1/0.705 = 1.418 on
R/G1. Both of those are measured and both are ~1. Printed here for the log.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("m68", HERE / "src" / "01-dark-iso-sweep.py")
m68 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m68)

RECUR = 6
GRID = 4
S_PTC, S_ERR = 0.8396, 0.0112


def main() -> int:
    blob = json.loads((HERE / "data" / "01-dark-iso-sweep.json").read_text())
    cache_of = {int(p.stem.split("-iso")[1]): p
                for p in (HERE / "cache").glob("*MSDCF-iso*.npz")}
    isos = sorted(cache_of)
    if isos != sorted(int(i) for i in blob["isos"]):
        raise RuntimeError(f"cache ISOs {isos} != sweep ISOs {blob['isos']}")
    g = np.maximum(np.array(isos, float), m68.BASE_ISO)
    mode = (np.array(isos) >= 400).astype(int)

    # ---------------------------------------------------------------- pass 1
    print("=== D2 per-plane dark level (median of the temporal-mean map, +512) ===")
    counts = {p: None for p in m68.PLANES}
    print(f"{'ISO':>5s} " + " ".join(f"{p:>10s}" for p in m68.PLANES))
    pedestal = {p: [] for p in m68.PLANES}
    for iso in isos:
        z = np.load(cache_of[iso])
        mean = z["mean"]
        row = []
        for p in m68.PLANES:
            mp = m68.split_plane(mean, p)
            med = float(np.median(mp)) + 512.0
            pedestal[p].append(med)
            row.append(med)
            fl = m68.defect_flags(mp)
            counts[p] = fl.astype(np.int16) if counts[p] is None else counts[p] + fl
        print(f"{iso:5d} " + " ".join(f"{v:10.4f}" for v in row))
        del z, mean
    for p in m68.PLANES:
        print(f"  {p:>3s} mean over ISOs {np.mean(pedestal[p]):9.4f} DN")
    d2 = abs(np.mean(pedestal["B"]) - np.mean(pedestal["G2"]))
    print(f"D2 |mean_B - mean_G2| = {d2:.4f} DN  (threshold 1.0)"
          f"  -> {'FLAG' if d2 > 1.0 else 'clear'}")

    masks = {p: (counts[p] >= RECUR) | ~m68.interior_mask(counts[p].shape)
             for p in m68.PLANES}
    print("\nexcluded per plane (recurrence>=%d + border): " % RECUR
          + ", ".join(f"{p} {int(masks[p].sum())}" for p in m68.PLANES))

    # ---------------------------------------------------------------- pass 2
    ny, nx = counts["R"].shape
    ry = np.linspace(0, ny, GRID + 1).astype(int)
    rx = np.linspace(0, nx, GRID + 1).astype(int)
    bvar = {p: np.zeros((len(isos), GRID, GRID)) for p in m68.PLANES}
    fvar = {p: np.zeros(len(isos)) for p in m68.PLANES}
    for i, iso in enumerate(isos):
        z = np.load(cache_of[iso])
        var = z["var"]
        for p in m68.PLANES:
            vp = m68.split_plane(var, p).astype(np.float64)
            keep = ~masks[p]
            fvar[p][i] = vp[keep].mean()
            for a in range(GRID):
                for b in range(GRID):
                    sl = (slice(ry[a], ry[a + 1]), slice(rx[b], rx[b + 1]))
                    bvar[p][i, a, b] = vp[sl][keep[sl]].mean()
        del z, var

    # ------------------------------------------------------------------- D3
    print("\n=== D3 per-ISO residual of sigma^2 = alpha*G^2 + delta (arm r6) ===")
    print(f"{'ISO':>5s} " + " ".join(f"{p:>9s}" for p in m68.PLANES))
    resid = {}
    for p in m68.PLANES:
        f = m68.fit_alpha_delta(g, mode, fvar[p])
        pred = np.where(mode == 0, f["alpha_low"], f["alpha_high"]) * g**2 + f["delta_low"]
        resid[p] = 100.0 * (fvar[p] - pred) / pred
    for i, iso in enumerate(isos):
        print(f"{iso:5d} " + " ".join(f"{resid[p][i]:+8.2f}%" for p in m68.PLANES))
    for p in m68.PLANES:
        r = resid[p]
        for lab, sel in (("low", mode == 0), ("high", mode == 1)):
            rr = r[sel]
            pos = int((rr > 0).sum())
            print(f"  {p:>3s} {lab:>4s}-mode residuals: {len(rr)} points, "
                  f"{pos} positive, max|r| {np.abs(rr).max():.2f}%")
    worst = max(np.abs(resid[p]).max() for p in m68.PLANES)
    same_sign = any(
        (int((resid[p][mode == m_].astype(float) > 0).sum()) in (0, int((mode == m_).sum()))
         and int((mode == m_).sum()) >= 5)
        for p in ["B"] for m_ in (0, 1))
    print(f"D3 B worst residual {np.abs(resid['B']).max():.2f}%, "
          f"single-signed inside a gain mode: {same_sign}")

    # ------------------------------------------------------------------- D1
    print(f"\n=== D1 spatial uniformity: alpha_high ratio on a {GRID}x{GRID} block grid ===")
    rat = np.zeros((GRID, GRID))
    ctl = np.zeros((GRID, GRID))
    for a in range(GRID):
        for b in range(GRID):
            fb = m68.fit_alpha_delta(g, mode, bvar["B"][:, a, b])
            f2 = m68.fit_alpha_delta(g, mode, bvar["G2"][:, a, b])
            f1 = m68.fit_alpha_delta(g, mode, bvar["G1"][:, a, b])
            rat[a, b] = fb["alpha_high"] / f2["alpha_high"]
            ctl[a, b] = f2["alpha_high"] / f1["alpha_high"]
    print("  B/G2:")
    for a in range(GRID):
        print("    " + " ".join(f"{rat[a, b]:7.4f}" for b in range(GRID)))
    print("  G2/G1 control:")
    for a in range(GRID):
        print("    " + " ".join(f"{ctl[a, b]:7.4f}" for b in range(GRID)))
    spread = float(rat.max() - rat.min())
    cspread = float(ctl.max() - ctl.min())
    print(f"D1 B/G2 block spread {spread:.4f} (threshold 0.05) -> "
          f"{'FAIL - withdraw f' if spread > 0.05 else 'PASS'}"
          f";  G2/G1 control spread {cspread:.4f}")
    for lab, sl in (("top", slice(0, GRID // 2)), ("bottom", slice(GRID // 2, GRID))):
        print(f"    {lab:>6s} half mean B/G2 {rat[sl, :].mean():.4f}")
    for lab, sl in (("left", slice(0, GRID // 2)), ("right", slice(GRID // 2, GRID))):
        print(f"    {lab:>6s} half mean B/G2 {rat[:, sl].mean():.4f}")

    # -------------------------------------------------------------------- f
    print("\n=== (4) position statistic f, POST-HOC ===")
    for num, den in (("B", "G2"), ("B", "G1"), ("B", "R")):
        fa = m68.fit_alpha_delta(g, mode, fvar[num])["alpha_high"]
        fb_ = m68.fit_alpha_delta(g, mode, fvar[den])["alpha_high"]
        rho = fa / fb_
        jk = m68.jackknife(g, mode, fvar[num])["alpha_high"] / fb_
        f_ = (1.0 - rho) / (1.0 - S_PTC**2)
        e_rho = jk / (1.0 - S_PTC**2)
        e_s = f_ * 2 * S_PTC / (1.0 - S_PTC**2) * S_ERR
        print(f"  {num}/{den}: alpha ratio {rho:.5f}  ->  f = {f_:.4f} "
              f"+/- {e_rho:.4f}(alpha) +/- {e_s:.4f}(s)  = {f_:.3f} "
              f"+/- {np.hypot(e_rho, e_s):.3f}")
    print(f"  endpoint predictions: f=1 -> ratio {S_PTC**2:.5f}, f=0 -> ratio 1.00000")
    print(f"  f=1/2 -> ratio {(1 + S_PTC**2) / 2:.5f}")

    # -------------------------------------------------------------------- E
    print("\n=== E readout-geometry exclusions (arithmetic on 02's numbers) ===")
    for pair, hyp, pred in (("G2/G1", "row-parity scale", S_PTC**2),
                            ("B/R", "row-parity scale", S_PTC**2),
                            ("R/G1", "column-parity scale", 1.0 / S_PTC**2),
                            ("B/G2", "column-parity scale", S_PTC**2)):
        a, b = pair.split("/")
        r = (m68.fit_alpha_delta(g, mode, fvar[a])["alpha_high"]
             / m68.fit_alpha_delta(g, mode, fvar[b])["alpha_high"])
        print(f"  {pair:>6s} measured {r:7.4f}   {hyp:<22s} predicts {pred:7.4f}"
              f"   -> {'consistent' if abs(r - pred) < 0.05 else 'EXCLUDED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
