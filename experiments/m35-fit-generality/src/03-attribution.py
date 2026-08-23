"""M35 step 3: why M33 and M35 disagree by 20% on the same pixels.

M33 fact 272 publishes a calibration ratio of 0.710 for the log-baseline fit on
coffee-bean at x2, with the parabola at 0.457.  M35 script 02, running over the
same cached dense volume, got 0.841 and 0.549.  Neither is a bug: they are
different statistics, and this script measures which difference contributes what
rather than asserting an explanation.

Three factors differ between the two scripts.  All eight combinations are run.

  STATISTIC   M33: median over pixels of (estimate / truth), a median of ratios.
              M35: mean(estimate) / mean(truth), a ratio of means.
              These are not estimates of the same quantity.  Discipline 180
              already fired once in M33 for exactly this family of mistake, and
              the deficit distribution has ~49% of its mass at or near zero, so
              the two cannot be assumed close.

  BASELINE    M33: 5th percentile along k of the DECIMATED stack.
              M35: minimum along k of the DENSE stack.
              log is not shift-invariant, so the baseline is part of the
              estimator, not a detail of the harness.

  PIXEL SET   M33: 40,000 randomly chosen pixels, interior judged by the DENSE
              argmax, keeping any pixel with true deficit > 1e-12.
              M35: all 1,048,576 pixels, interior judged by the DECIMATED argmax.

The cell matching M33's choices must reproduce 0.457 / 0.710, and the cell
matching M35's must reproduce 0.549 / 0.841.  If neither reproduces, one of the
two milestones has a real defect and this script has found it.
"""
import numpy as np, os, json, itertools

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "out")
M33 = os.path.join(HERE, "..", "..", "m33-subframe-offset", "out", "cache", "dense_focus.npy")

V = np.asarray(np.load(M33, mmap_mode="r"), np.float32)
nd = V.shape[0]
STEP = 2


def three_point(am_, a0, ap):
    dn = am_ - 2 * a0 + ap
    ok = dn < -1e-12
    sh = np.where(ok, -0.5 * (ap - am_) / np.where(ok, dn, 1), 0.0)
    return ok, np.where(ok, a0 + 0.25 * (ap - am_) * sh, a0)


def predict(am_, a0, ap, mode, base=0.0):
    if mode == "parabola":
        ok, pk = three_point(am_, a0, ap)
        return ok, 1 - a0 / np.maximum(pk, 1e-12)
    lo = 1e-9
    xm, x0, xp = (np.maximum(v - base, lo) for v in (am_, a0, ap))
    ok, pk = three_point(np.log(xm), np.log(x0), np.log(xp))
    return ok, 1 - x0 / np.maximum(np.exp(pk), 1e-12)


rows = {}
for pixset, baseline, stat in itertools.product(("m33_40k", "m35_all"),
                                                ("p5_decimated", "min_dense"),
                                                ("median_of_ratios", "ratio_of_means")):
    if pixset == "m33_40k":
        r2 = np.random.default_rng(20260812)          # M33's stream, same pixels
        b = 8
        iy = r2.integers(b, V.shape[1] - b, 40000)
        ix = r2.integers(b, V.shape[2] - b, 40000)
        D = V[:, iy, ix].astype(np.float64)
        dense_max = D.max(0)
        k_dense = D.argmax(0)
        interior = (k_dense >= 2) & (k_dense <= nd - 3)
        S = D[list(range(0, nd, STEP))]
        ar = np.arange(D.shape[1])
        m = S.shape[0]
        j = S.argmax(0)
        true_def = 1 - S.max(0) / dense_max
        jj = np.clip(j, 1, m - 2)
        a0, am_, ap = S[jj, ar], S[jj - 1, ar], S[jj + 1, ar]
        base = np.percentile(S, 5, axis=0) if baseline == "p5_decimated" else D.min(0)
        inner = interior & (j >= 1) & (j <= m - 2)
        keep = true_def > 1e-12
    else:
        S = V[::STEP]
        m = S.shape[0]
        base_dense = V.min(0)
        tp = np.maximum(V.max(0) - base_dense, 1e-6)
        true_def = np.clip(1 - np.maximum(S.max(0) - base_dense, 1e-6) / tp, 0, 1).ravel()
        j = S.argmax(0)
        yy, xx = np.mgrid[0:V.shape[1], 0:V.shape[2]]
        jj = np.clip(j, 1, m - 2)
        a0 = S[jj, yy, xx].astype(np.float64).ravel()
        am_ = S[jj - 1, yy, xx].astype(np.float64).ravel()
        ap = S[jj + 1, yy, xx].astype(np.float64).ravel()
        base = (np.percentile(S, 5, axis=0) if baseline == "p5_decimated" else base_dense).ravel()
        inner = ((j >= 1) & (j <= m - 2)).ravel()
        keep = true_def > 1e-12

    cell = {}
    for mode in ("parabola", "log_baseline"):
        ok, pd = predict(am_, a0, ap, "parabola" if mode == "parabola" else "log",
                         0.0 if mode == "parabola" else base)
        g = inner & ok & keep
        if stat == "median_of_ratios":
            cell[mode] = float(np.median(pd[g] / true_def[g]))
        else:
            cell[mode] = float(pd[g].mean() / max(true_def[g].mean(), 1e-12))
    cell["n"] = int((inner & keep).sum())
    key = f"{pixset}|{baseline}|{stat}"
    rows[key] = cell
    print(f"{key:48s} parabola {cell['parabola']:.3f}   log {cell['log_baseline']:.3f}"
          f"   n={cell['n']}")

m33_cell = rows["m33_40k|p5_decimated|median_of_ratios"]
m35_cell = rows["m35_all|min_dense|ratio_of_means"]
print(f"\nM33 published        parabola 0.457  log 0.710")
print(f"M33's cell here      parabola {m33_cell['parabola']:.3f}  log {m33_cell['log_baseline']:.3f}")
print(f"M35 script 02        parabola 0.549  log 0.841")
print(f"M35's cell here      parabola {m35_cell['parabola']:.3f}  log {m35_cell['log_baseline']:.3f}")

# one-factor-at-a-time attribution, starting from M33's cell
base_key = "m33_40k|p5_decimated|median_of_ratios"
attrib = {}
for k, alt in (("statistic", "m33_40k|p5_decimated|ratio_of_means"),
               ("baseline", "m33_40k|min_dense|median_of_ratios"),
               ("pixel_set", "m35_all|p5_decimated|median_of_ratios")):
    attrib[k] = {mo: float(rows[alt][mo] - rows[base_key][mo])
                 for mo in ("parabola", "log_baseline")}
    print(f"changing {k:10s} alone moves parabola {attrib[k]['parabola']:+.3f}"
          f"   log {attrib[k]['log_baseline']:+.3f}")

json.dump(dict(cells=rows, attribution=attrib,
               m33_published=dict(parabola=0.457, log=0.710),
               m35_script02=dict(parabola=0.549, log=0.841)),
          open(os.path.join(OUT, "03-attribution.json"), "w"), indent=1)
print("wrote 03-attribution.json")
