"""M20 verification -- the crossover calibration done at MATCHED spatial scale.

v6 calibrates per-pixel at the simulation's own (sensor-pitch) scale.  The real
measurement is made on the CFA green plane, whose pixels are 2x the sensor pitch, so a
W=9 window there spans 18 sensor px.  Here the merge still runs at sensor scale (that is
the physics) but the sigma_rel statistic AND the error accounting are both reduced to the
CFA grid, so the calibration and its application are measured the same way.

Also reports the crossover implied by the report's own (inconsistent) recipe, for
comparison: sigma_crossover / median-local-std-of-the-LATENT.
"""
import numpy as np
from scipy.ndimage import uniform_filter1d
from v4_sim import NPX, build_plant, depth_map, observe, rmse
from v6_mapping import run_one

W = 9


def rel_and_err(Y, sigma, merged_a, merged_b, latent, decimate):
    """sigma_rel and both merges' squared error, both reduced to the same grid."""
    rels = []
    for k in range(Y.shape[0]):
        y = Y[k, ::decimate]
        m = uniform_filter1d(y, W, mode="nearest")
        m2 = uniform_filter1d(y * y, W, mode="nearest")
        v = np.maximum(m2 - m * m, 0.0) * (W / (W - 1.0))
        sig = np.sqrt(np.maximum(v - sigma ** 2, 0.0))
        rels.append(sigma / np.maximum(sig, 1e-6))
    rel = np.min(np.stack(rels), axis=0)
    # error, box-averaged over the same physical extent then sampled on the same grid
    ea = uniform_filter1d((merged_a - latent) ** 2, W * decimate, mode="nearest")[::decimate]
    eb = uniform_filter1d((merged_b - latent) ** 2, W * decimate, mode="nearest")[::decimate]
    return rel, ea, eb


def calibrate(decimate, mode, edges):
    latent = build_plant()
    depth = depth_map("slabs")
    ag = np.zeros(len(edges) - 1)
    asel = np.zeros(len(edges) - 1)
    an = np.zeros(len(edges) - 1)
    for sg in (0.005, 0.010, 0.020, 0.030, 0.050, 0.080, 0.120):
        for s in range(6):
            Y, sel, wie, gua = run_one(latent, depth, sg, mode, 3.0, 6000 + s)
            rel, eg, es = rel_and_err(Y, sg, gua, sel, latent, decimate)
            idx = np.digitize(rel, edges) - 1
            for b in range(len(edges) - 1):
                m = idx == b
                if m.any():
                    ag[b] += eg[m].sum()
                    asel[b] += es[m].sum()
                    an[b] += m.sum()
    rows = []
    for b in range(len(edges) - 1):
        if an[b] < 300:
            continue
        rg = np.sqrt(ag[b] / an[b])
        rs = np.sqrt(asel[b] / an[b])
        rows.append((0.5 * (edges[b] + min(edges[b + 1], 3.0)), int(an[b]), rg, rs, rg / rs))
    cross = None
    for i in range(len(rows) - 1):
        if rows[i][4] < 1.0 <= rows[i + 1][4]:
            x0, y0 = rows[i][0], rows[i][4]
            x1, y1 = rows[i + 1][0], rows[i + 1][4]
            cross = x0 + (1.0 - y0) * (x1 - x0) / (y1 - y0)
    return rows, cross


if __name__ == "__main__":
    edges = np.array([0.0, 0.05, 0.10, 0.17, 0.25, 0.34, 0.45, 0.6, 0.8, 1.1, 1.5, 2.2, 1e9])
    print("=" * 96)
    print("CROSSOVER CALIBRATION AT MATCHED SPATIAL SCALE")
    print("  decimate=1 : statistic measured on the sensor grid (what the sim natively is)")
    print("  decimate=2 : statistic measured on the CFA green grid (what contrast2.py does)")
    print("=" * 96)
    out = {}
    for mode in ("est-sel", "oracle"):
        for dec in (1, 2):
            rows, cross = calibrate(dec, mode, edges)
            out[(mode, dec)] = cross
            print(f"\n  prior={mode:<8} decimate={dec}")
            print(f"  {'sigma_rel mid':>14} {'n':>9} {'RMSE gua':>10} {'RMSE sel':>10} {'gua/sel':>9}")
            for r in rows:
                print(f"  {r[0]:>14.3f} {r[1]:>9d} {r[2]:>10.4f} {r[3]:>10.4f} {r[4]:>9.4f}")
            print(f"  --> crossover = {cross:.4f}" if cross else "  --> no crossover in range")
    print()
    print("=" * 96)
    print("SUMMARY -- crossover in sigma_local/signal_local units")
    print("=" * 96)
    print(f"  {'prior':>10} {'sensor grid':>13} {'CFA grid':>10} {'report':>9}")
    print(f"  {'est-sel':>10} {out[('est-sel',1)]:>13.4f} {out[('est-sel',2)]:>10.4f} {0.3440:>9.4f}")
    print(f"  {'oracle':>10} {out[('oracle',1)]:>13.4f} {out[('oracle',2)]:>10.4f} {0.5734:>9.4f}")
    print()
    print("  The report's recipe was sigma_crossover / median-local-std-of-the-LATENT")
    print("  = 0.03 / 0.0872 = 0.3440.  That pairs an UNBLURRED, NOISE-FREE contrast in the")
    print("  simulation against a BLURRED, NOISE-SUBTRACTED OBSERVED contrast on the real")
    print("  data.  The same recipe using the observed in-focus frame gives 0.03/0.0642 = 0.467.")
