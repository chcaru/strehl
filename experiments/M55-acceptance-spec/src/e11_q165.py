"""M55b E11 -- bound SYNTHESIS question 165: why is the flat-ROI contiguous
penalty K-independent?

PRE-REGISTERED as PR25 and PR26 before this file ran (session store m55b_prereg).

  PR25  H1 NOISE.  Ring-mode bootstrap SE on the contiguous-split cross-power C
        for the three flat ROIs at K = 8, 16, 32, full.  If |C|/SE < 3 in >= 2
        of 3 stacks at full K, the flat-ROI contiguous/parity ratio is a noise
        residual and the K-independence is not a finding at all.
        FALSIFIER: |C|/SE >= 3 in >= 2 of 3 -> the component is real.

  PR26  FLOOR.  Cross-STACK cross-power at the SAME quad ROI coordinates but
        DIFFERENT subjects.  Anything shared there is sensor-fixed, not scene.
        If cross-stack |C| >= 10% of within-stack parity |C|, the flat-ROI
        cells of any real-data battery are partly measuring the sensor.

  PR29  What MTF loss does M46's 0.05 px reference blur actually correspond to
        at f_sig?  Arithmetic, then confirmed by direct measurement.

Read-only with respect to D:\personal\macro.  No existing script is modified.
"""
import os, sys, glob, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "m46-detail-metric", "src"),
          os.path.join(ROOT, "m41-r3-kill", "src")):
    if p not in sys.path:
        sys.path.insert(0, p)
import m46lib as M
import m41lib as L1

PAD, G, RN_E, NBIN = 32, 1.14469, 1.47, 64
FLAT = (2747, 32, 512, 512)
STACKS = {"112MSDCF": (6, 68), "113MSDCF": (0, 63), "foam": (0, 62)}


def rings(n, nbin=NBIN):
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    e = np.linspace(0, n // 2, nbin + 1)
    out = []
    for i in range(nbin):
        m = (rr >= e[i]) & (rr < e[i + 1])
        if int(m.sum()) < 8:
            continue
        out.append((m, int(m.sum()), 0.5 * (e[i] + e[i + 1]) / n))
    return out


def spectra(a, b):
    n = a.shape[0]
    k = np.arange(n)
    w1 = 0.5 - 0.5 * np.cos(2 * np.pi * k / (n - 1))
    w = np.outer(w1, w1)
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * w))
    return A, B


def ring_index(n, f=None, nbin=NBIN):
    f = M.F_SIG if f is None else f
    rs = rings(n, nbin)
    j = int(np.argmin([abs(c - f) for (_, _, c) in rs]))
    return rs[j]


def canon_with_se(a, b, nboot=400, seed=11):
    """Canonical sigpow plus a bootstrap SE taken over INDEPENDENT half-plane
    modes.  The full ring is Hermitian-symmetric, so its modes come in
    conjugate pairs with identical Re(A conj B); resampling all of them would
    understate the SE by sqrt(2)."""
    n = a.shape[0]
    m, cnt, fc = ring_index(n)
    A, B = spectra(a, b)
    r_full = np.real(A[m] * np.conj(B[m]))
    val = float(r_full.sum() / cnt)
    yy, xx = np.mgrid[0:n, 0:n]
    ky, kx = yy - n // 2, xx - n // 2
    half = m & ((ky > 0) | ((ky == 0) & (kx >= 0)))
    r_half = np.real(A[half] * np.conj(B[half]))
    rng = np.random.default_rng(seed)
    nh = r_half.size
    boot = r_half[rng.integers(0, nh, size=(nboot, nh))].mean(axis=1)
    scale = r_full.sum() / max(r_half.sum(), 1e-300) if abs(r_half.sum()) > 0 else 2.0
    se = float(boot.std(ddof=1) * abs(scale) * nh / cnt)
    return val, se, cnt, nh, float(fc)


def load_cube(files, roi, pad=PAD):
    import rawpy
    x, y, w, h = roi
    x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
    out = np.empty((len(files), y1 - y0, x1 - x0), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
            g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
        out[i] = 0.5 * (g1 + g2) - M.BLACK
    return out


def merge(cube, coarse, reg, idx):
    c, cf, rg = cube[idx], coarse[idx], reg[idx]
    w = np.argmax(rg, axis=0)
    peak = np.take_along_axis(cf, w[None], 0)[0]
    acc = cf >= (0.5 * peak)[None]
    acc[w, np.arange(c.shape[1])[:, None], np.arange(c.shape[2])[None]] = True
    n = acc.sum(0).astype(np.float32)
    return ((c * acc).sum(0) / np.maximum(n, 1.0))[PAD:-PAD, PAD:-PAD].astype(np.float32)


def plain_mean(cube, idx):
    return cube[idx].mean(axis=0)[PAD:-PAD, PAD:-PAD].astype(np.float32)


def main():
    res, t0 = {}, time.time()
    print("=" * 78)
    print("M55b E11 -- question 165: the flat-ROI contiguous penalty")
    print("=" * 78)

    # ---------------------------------------------------------------- PR29
    f = M.F_SIG
    for sd in (0.05, 0.1245, 0.2645, 0.5):
        mtf = float(np.exp(-2.0 * np.pi ** 2 * sd ** 2 * f ** 2))
        print(f"   PR29  Gaussian sigma {sd:6.4f} px -> true MTF at f_sig={f:.4f} is {mtf:.6f}"
              f"   (loss {100*(1-mtf):6.3f} %)")
    res["pr29_mtf_of_sigma"] = {str(sd): float(np.exp(-2*np.pi**2*sd**2*f**2))
                                for sd in (0.05, 0.1245, 0.2645, 0.5)}

    keep = {}
    for sname, (lo, hi) in STACKS.items():
        files = sorted(glob.glob(os.path.join(r"D:\personal\macro", sname, "*.ARW")))[lo:hi]
        print("\n" + "=" * 78)
        print(f"  {sname}  flat ROI {FLAT}  {len(files)} frames")
        print("=" * 78)
        cube = load_cube(files, FLAT)
        fine, coarse, reg = L1.focus_fields(cube, G, RN_E)
        nf = cube.shape[0]
        best = int(np.argmax([np.mean(coarse[i]) for i in range(nf)]))
        st = res.setdefault(sname, {"nframes": nf, "best": best, "K": {}})
        print(f"     best-focus frame {best} of {nf}; median level {np.median(cube):8.2f} DN")
        print("      K   split        C (canon)        SE        |C|/SE   contig/parity"
              "    level_a   level_b")
        for K in (8, 16, 32, nf):
            half = K // 2
            lo_ = max(0, min(best - K // 2, nf - K))
            sub = np.arange(lo_, lo_ + K) if K < nf else np.arange(nf)
            row = {}
            for split in ("parity", "contiguous"):
                if split == "parity":
                    ia, ib = sub[0::2], sub[1::2]
                else:
                    ia, ib = sub[:len(sub) // 2], sub[len(sub) // 2:2 * (len(sub) // 2)]
                a = merge(cube, coarse, reg, ia)
                b = merge(cube, coarse, reg, ib)
                v, se, cnt, nh, fc = canon_with_se(a, b)
                row[split] = dict(C=v, se=se, tstat=abs(v) / se if se > 0 else float("inf"),
                                  level_a=float(a.mean()), level_b=float(b.mean()))
                if K == nf and split == "parity":
                    keep[sname] = a.copy()
            ratio = row["contiguous"]["C"] / row["parity"]["C"]
            row["contig_over_parity"] = float(ratio)
            st["K"][str(K)] = row
            for split in ("parity", "contiguous"):
                r = row[split]
                extra = f"{ratio:14.4f}" if split == "contiguous" else " " * 14
                print(f"   {K:4d}   {split:11s} {r['C']:+13.5e} {r['se']:11.4e} "
                      f"{r['tstat']:9.2f} {extra}  {r['level_a']:9.2f} {r['level_b']:9.2f}")
        del cube, fine, coarse, reg

    # ---------------------------------------------------------------- PR25
    print("\n" + "=" * 78)
    print("  PR25 -- is the flat-ROI contiguous cross-power distinguishable from zero?")
    print("=" * 78)
    nsig = 0
    for sname in STACKS:
        nf = res[sname]["nframes"]
        r = res[sname]["K"][str(nf)]["contiguous"]
        ok = r["tstat"] >= 3.0
        nsig += int(ok)
        print(f"   {sname:10s} full K: C {r['C']:+12.5e}  SE {r['se']:10.4e}  "
              f"|C|/SE {r['tstat']:8.2f}   {'REAL (>=3)' if ok else 'consistent with 0'}")
    verdict = ("H1 REFUTED -- the component is real" if nsig >= 2
               else "H1 SUPPORTED -- the flat-ROI ratio is a noise residual")
    print(f"\n   {nsig} of 3 stacks significant  ->  {verdict}")
    res["pr25"] = dict(n_significant=nsig, verdict=verdict)

    # ---------------------------------------------------------------- PR26
    print("\n" + "=" * 78)
    print("  PR26 -- the cross-STACK floor: same ROI coordinates, different subjects")
    print("=" * 78)
    names = list(keep)
    res["pr26"] = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            x, y = names[i], names[j]
            v, se, cnt, nh, fc = canon_with_se(keep[x], keep[y])
            base = min(abs(res[x]["K"][str(res[x]["nframes"])]["parity"]["C"]),
                       abs(res[y]["K"][str(res[y]["nframes"])]["parity"]["C"]))
            frac = abs(v) / base
            print(f"   {x:10s} x {y:10s}  C {v:+12.5e}  SE {se:10.4e}  |C|/SE {abs(v)/se:7.2f}"
                  f"   = {100*frac:7.3f} % of the smaller within-stack parity C")
            res["pr26"][f"{x}|{y}"] = dict(C=float(v), se=float(se), frac_of_within=float(frac))
    worst = max(v["frac_of_within"] for v in res["pr26"].values())
    print(f"\n   worst cross-stack fraction {100*worst:.3f} %  ->  "
          + ("FLOOR MATERIAL (>=10%)" if worst >= 0.10 else "floor immaterial (<10%)"))
    res["pr26_worst"] = float(worst)

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "e11_q165.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote out/e11_q165.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
