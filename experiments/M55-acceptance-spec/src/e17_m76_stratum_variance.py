"""M76 Q1 -- per-cell B7 repetition variance against B9 |z|.

Pre-registered in docs/research/M76-stratum-gate-residuals.md at f1da8e5
before this file existed and before any held-out pixel was decoded by M76.
"""
import glob
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
ROOT = r"D:\personal\macro"
sys.path.insert(0, HERE)
EXP = os.path.dirname(os.path.dirname(HERE))
for path in (os.path.join(EXP, "m46-detail-metric", "src"),
             os.path.join(EXP, "m41-r3-kill", "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

import m41lib as L1
import ref_metrics as R
import spec_v1 as S

PAD = 32
G = 1.14469
RN_E = 1.47
NREP = 64
MASTER_SEED = 760055
BOOT_SEED = 760056
PERM_SEED = 760057
NBOOT = 10_000
NPERM = 100_000
NOISE_SD_DN = 2.0 * S.TH["plant_noise_e"] * G


def load_cubes(files, rois):
    import rawpy
    import m46lib as M
    with rawpy.imread(files[0]) as raw:
        shape = raw.raw_image_visible.shape
    cubes, errors = [], []
    for x, y, w, h in rois:
        x0, y0 = x - PAD, y - PAD
        x1, y1 = x + w + PAD, y + h + PAD
        required = (2 * y1, 2 * x1)
        if x0 < 0 or y0 < 0 or required[0] > shape[0] or required[1] > shape[1]:
            cubes.append(None)
            errors.append(
                f"ROI {(x, y, w, h)} requires raw extent {required}, "
                f"visible shape is {shape}")
        else:
            cubes.append(np.empty((len(files), h + 2 * PAD, w + 2 * PAD),
                                  np.float32))
            errors.append(None)
    for i, path in enumerate(files):
        with rawpy.imread(path) as raw:
            visible = raw.raw_image_visible
            for cube, (x, y, w, h) in zip(cubes, rois):
                if cube is None:
                    continue
                x0, y0 = x - PAD, y - PAD
                x1, y1 = x + w + PAD, y + h + PAD
                g1 = visible[2*y0:2*y1:2, 2*x0+1:2*x1+1:2].astype(np.float32)
                g2 = visible[2*y0+1:2*y1+1:2, 2*x0:2*x1:2].astype(np.float32)
                cube[i] = 0.5 * (g1 + g2) - M.BLACK
    return cubes, errors


def merge(cube, coarse, reg, idx):
    c, cf, rg = cube[idx], coarse[idx], reg[idx]
    winner = np.argmax(rg, axis=0)
    peak = np.take_along_axis(cf, winner[None], 0)[0]
    accepted = cf >= (0.5 * peak)[None]
    accepted[winner, np.arange(c.shape[1])[:, None], np.arange(c.shape[2])[None]] = True
    n = accepted.sum(0).astype(np.float32)
    return ((c * accepted).sum(0) / np.maximum(n, 1.0))[PAD:-PAD, PAD:-PAD]


def b9_raw(cand, a, b):
    observed, status = cand.value(a, b)
    null = np.array([cand.value(a, rolled)[0]
                     for rolled in S.roll_null(a, b, seed=5)], float)
    sd = float(null.std(ddof=1))
    z = (observed - float(null.mean())) / sd if sd > 0 else float("inf")
    return float(observed), status, null, float(z)


def d_repetitions(candidates, a, b, seed):
    rng = np.random.default_rng(seed)
    out = {cand.name: [] for cand in candidates}
    statuses = {cand.name: [] for cand in candidates}
    for _ in range(NREP):
        an = a + rng.standard_normal(a.shape) * NOISE_SD_DN
        bn = b + rng.standard_normal(b.shape) * NOISE_SD_DN
        ta, tb = S.blur(an, S.sd_for_mtf(0.9)), S.blur(bn, S.sd_for_mtf(0.9))
        for cand in candidates:
            ref, sr = cand.value(an, bn)
            test, st = cand.value(ta, tb)
            out[cand.name].append(float(cand.d_signed(ref, test)))
            statuses[cand.name].append((sr, st))
    return out, statuses


def fixed_stack_beta(rows, x_values=None, y_values=None):
    x = np.array([np.log10(abs(r["z"])) for r in rows]) if x_values is None \
        else np.asarray(x_values, float)
    y = np.array([np.log10(r["sd_d"]) for r in rows]) if y_values is None \
        else np.asarray(y_values, float)
    xc, yc = np.empty_like(x), np.empty_like(y)
    slopes = {}
    for stack in sorted({r["stack"] for r in rows}):
        idx = np.array([i for i, r in enumerate(rows) if r["stack"] == stack])
        xc[idx], yc[idx] = x[idx] - x[idx].mean(), y[idx] - y[idx].mean()
        den = float(np.dot(xc[idx], xc[idx]))
        slopes[stack] = float(np.dot(xc[idx], yc[idx]) / den) if den else float("nan")
    den = float(np.dot(xc, xc))
    return float(np.dot(xc, yc) / den) if den else float("nan"), slopes


def rankdata(values):
    values = np.asarray(values, float)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), float)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        ranks[order[i:j]] = 0.5 * (i + j - 1) + 1.0
        i = j
    return ranks


def spearman(x, y):
    rx, ry = rankdata(x), rankdata(y)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def analyse(rows, full_uncertainty=True):
    finite = [r for r in rows if np.isfinite(r["z"]) and abs(r["z"]) > 0
              and np.isfinite(r["sd_d"]) and r["sd_d"] > 0]
    x = np.array([abs(r["z"]) for r in finite], float)
    y = np.array([r["sd_d"] for r in finite], float)
    rho = spearman(x, y)
    beta, slopes = fixed_stack_beta(finite)
    result = dict(n=len(finite), rho=rho, beta=beta, within_stack_slopes=slopes,
                  z_span=float(x.max() / x.min()) if len(x) else float("nan"),
                  sd_span=float(y.max() / y.min()) if len(y) else float("nan"))
    if not full_uncertainty or len(finite) < 2:
        return result

    rng = np.random.default_rng(BOOT_SEED)
    brho, bbeta = np.empty(NBOOT), np.empty(NBOOT)
    for k in range(NBOOT):
        bz, bsd = [], []
        for row in finite:
            ds = np.asarray(row["d_reps"], float)
            null = np.asarray(row["null"], float)
            dsb = ds[rng.integers(0, len(ds), len(ds))]
            nb = null[rng.integers(0, len(null), len(null))]
            nsd = float(nb.std(ddof=1))
            bz.append(abs((row["observed"] - float(nb.mean())) / nsd)
                      if nsd > 0 else float("nan"))
            bsd.append(float(dsb.std(ddof=1)))
        brho[k] = spearman(bz, bsd)
        bbeta[k] = fixed_stack_beta(
            finite, np.log10(np.asarray(bz)), np.log10(np.asarray(bsd)))[0]

    prng = np.random.default_rng(PERM_SEED)
    extreme = 0
    stack_indices = [[i for i, r in enumerate(finite) if r["stack"] == stack]
                     for stack in sorted({r["stack"] for r in finite})]
    for _ in range(NPERM):
        yp = y.copy()
        for idx in stack_indices:
            yp[idx] = yp[prng.permutation(idx)]
        extreme += int(abs(spearman(x, yp)) >= abs(rho))
    p_perm = (extreme + 1.0) / (NPERM + 1.0)

    bmean, bsd = float(np.nanmean(bbeta)), float(np.nanstd(bbeta, ddof=1))
    ci_beta = [float(v) for v in np.nanpercentile(bbeta, [2.5, 97.5])]
    ci_rho = [float(v) for v in np.nanpercentile(brho, [2.5, 97.5])]
    three_sd = [bmean - 3.0 * bsd, bmean + 3.0 * bsd]
    result.update(
        rho_ci95=ci_rho, beta_ci95=ci_beta, beta_boot_mean=bmean,
        beta_boot_sd=bsd, beta_3sd=three_sd,
        factor_per_decade_3sd=[float(10.0 ** v) for v in three_sd],
        p_within_stack_permutation=float(p_perm), nboot=NBOOT, nperm=NPERM)
    return result


def synthetic_control(cand):
    plant = S.Plant(seed=0)
    rows = []
    for contrast in (2.5, 5, 10, 20, 80, 320):
        a, b = plant.pair(mtf=1.0, noise_e=S.TH["plant_noise_e"],
                          rep=0, contrast=contrast)
        observed, status, null, z = b9_raw(cand, a, b)
        ds = []
        for rep in range(NREP):
            ra, rb = plant.pair(mtf=1.0, noise_e=2*S.TH["plant_noise_e"],
                                rep=rep, contrast=contrast)
            ta, tb = plant.pair(mtf=0.9, noise_e=2*S.TH["plant_noise_e"],
                                rep=rep, contrast=contrast)
            ds.append(float(cand.d_signed(cand.value(ra, rb)[0],
                                          cand.value(ta, tb)[0])))
        rows.append(dict(stack="plant", roi=str(contrast), contrast=contrast,
                         observed=observed, status=status, null=null.tolist(), z=z,
                         d_reps=ds, sd_d=float(np.std(ds, ddof=1))))
    result = analyse(rows, full_uncertainty=False)
    result["passed"] = bool(result["n"] == 6 and result["z_span"] >= 4.0
                            and result["sd_span"] >= 4.0)
    return rows, result


def main():
    t0 = time.time()
    candidates = [R.RefSigpow(), R.RefNoisePow(), R.RefBandRatio()]
    rows = {cand.name: [] for cand in candidates}
    decode_failures = []
    print("=" * 78)
    print("M76 E17 -- per-cell B7 variance against B9 |z|")
    print(f"24 held-out cells; REPS={NREP}; noise SD={NOISE_SD_DN:.6f} DN")
    print("=" * 78)
    rois = S.roi_rule()
    for si, stack in enumerate(S.HELD_OUT):
        files = sorted(glob.glob(os.path.join(ROOT, stack, "*.ARW")))[:S.B6_FRAMES]
        if len(files) != S.B6_FRAMES:
            raise RuntimeError(f"{stack}: found {len(files)} files, need {S.B6_FRAMES}")
        cubes, errors = load_cubes(files, rois)
        for ri, (roi, cube, error) in enumerate(zip(rois, cubes, errors)):
            if error:
                message = f"{stack:14s} roi{ri} DECODE-BLOCKED: {error}"
                print(message)
                decode_failures.append(dict(stack=stack, roi=ri,
                                            coordinates=list(roi), error=error))
                continue
            fine, coarse, reg = L1.focus_fields(cube, G, RN_E)
            idx = np.arange(cube.shape[0])
            a = merge(cube, coarse, reg, idx[0::2])
            b = merge(cube, coarse, reg, idx[1::2])
            ds, statuses = d_repetitions(
                candidates, a, b, MASTER_SEED + 1000 * si + ri)
            line = f"{stack:14s} roi{ri}"
            for cand in candidates:
                observed, status, null, z = b9_raw(cand, a, b)
                dvals = ds[cand.name]
                row = dict(stack=stack, roi=ri, coordinates=list(roi),
                           observed=observed, status=status, null=null.tolist(), z=z,
                           d_reps=dvals, sd_d=float(np.std(dvals, ddof=1)),
                           statuses=statuses[cand.name])
                rows[cand.name].append(row)
                line += f"  {cand.name[:7]} z={z:+7.2f} sd(d)={row['sd_d']:.3e}"
            print(line)
            del cube, fine, coarse, reg, a, b
        del cubes

    analyses = {name: analyse(candidate_rows) for name, candidate_rows in rows.items()}
    control_rows, control = synthetic_control(R.RefSigpow())
    primary = analyses["sigpow-canonical"]
    signs = [np.sign(v) for v in primary["within_stack_slopes"].values()
             if np.isfinite(v) and v != 0]
    same_sign = max(signs.count(1.0), signs.count(-1.0)) if signs else 0
    ci_excludes = primary["beta_ci95"][0] > 0 or primary["beta_ci95"][1] < 0
    permutation_sig = primary["p_within_stack_permutation"] < 0.05
    contradiction = ci_excludes != permutation_sig
    if not control["passed"] or primary["n"] < 20 or contradiction:
        decision = "INCONCLUSIVE"
    elif ci_excludes and permutation_sig and same_sign >= 5:
        decision = "YES, PARTLY CELL"
    else:
        decision = "NO ASSOCIATION RESOLVED"

    print("\nRESULTS")
    for name, result in analyses.items():
        print(f"  {name:22s} n={result['n']:2d} rho={result['rho']:+.4f} "
              f"95% [{result['rho_ci95'][0]:+.4f},{result['rho_ci95'][1]:+.4f}] "
              f"beta={result['beta']:+.4f} "
              f"95% [{result['beta_ci95'][0]:+.4f},{result['beta_ci95'][1]:+.4f}] "
              f"perm-p={result['p_within_stack_permutation']:.6f}")
        print("    within-stack " + ", ".join(
            f"{k}={v:+.3f}" for k, v in result["within_stack_slopes"].items()))
    print(f"  positive control: z span {control['z_span']:.2f}x, "
          f"sd(d) span {control['sd_span']:.2f}x -> "
          f"{'PASS' if control['passed'] else 'FAIL'}")
    print(f"  registered decision: {decision}")

    output = dict(
        registration="f1da8e5e9a95e2765ca0bd23eccc9b34a4d322a2",
        nrep=NREP, noise_sd_dn=NOISE_SD_DN,
        seeds=dict(master=MASTER_SEED, bootstrap=BOOT_SEED, permutation=PERM_SEED),
        rows=rows, analyses=analyses, positive_control_rows=control_rows,
        positive_control=control, same_sign_count=same_sign,
        decode_failures=decode_failures,
        uncertainty_contradiction=contradiction, decision=decision,
        elapsed_seconds=time.time() - t0)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "e17_m76_stratum_variance.json"), "w",
              encoding="utf-8") as handle:
        json.dump(output, handle, indent=1, default=float)
    print(f"wrote out/e17_m76_stratum_variance.json ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
