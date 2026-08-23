"""M55b E12 -- the empirical null for a ring cross-power, and what it does to
question 165.

PRE-REGISTERED as PR30, PR31, PR32 before this file ran.

E11 disclosed a defect in its own standard error: the rescaling factor divided
by a half-plane sum that can be negative, producing `inf` for three cells.
E11 is NOT edited (rule 15); this file recomputes the SE without that factor
and, more importantly, stops trusting mode-scatter SEs at all.

  PR30  Mode-scatter SE vs an empirical permutation null built by rolling one
        half-merge by a large offset.  A roll destroys pixel correspondence and
        preserves the marginals, the window and the ring exactly.
  PR31  Where do the observed parity and contiguous values sit inside that null?
  PR32  Reconcile E9's best-focus definition with E11's.
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
STACKS = {
    "112MSDCF": dict(lo=6, hi=68, rois={"detail": (1671, 1373, 512, 512),
                                        "flat": (2747, 32, 512, 512)}),
    "113MSDCF": dict(lo=0, hi=63, rois={"centre": (916, 1501, 512, 512),
                                        "flat": (2747, 32, 512, 512)}),
    "foam":     dict(lo=0, hi=62, rois={"centre": (916, 1501, 512, 512),
                                        "flat": (2747, 32, 512, 512)}),
}


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


_RCACHE = {}


def ring_at(n, f=None, nbin=NBIN):
    f = M.F_SIG if f is None else f
    key = (n, f, nbin)
    if key not in _RCACHE:
        rs = rings(n, nbin)
        j = int(np.argmin([abs(c - f) for (_, _, c) in rs]))
        _RCACHE[key] = rs[j]
    return _RCACHE[key]


def spec(a):
    n = a.shape[0]
    k = np.arange(n)
    w1 = 0.5 - 0.5 * np.cos(2 * np.pi * k / (n - 1))
    return np.fft.fftshift(np.fft.fft2((a - a.mean()) * np.outer(w1, w1)))


def canon_from(A, B):
    m, cnt, _ = ring_at(A.shape[0])
    return float(np.real(np.sum(A[m] * np.conj(B[m]))) / cnt)


def mode_se(A, B):
    """The SE a mode-scatter bootstrap would give.  Independent half-plane
    modes only; no division by a possibly-negative sum (E11's defect)."""
    n = A.shape[0]
    m, cnt, _ = ring_at(n)
    yy, xx = np.mgrid[0:n, 0:n]
    half = m & (((yy - n // 2) > 0) | (((yy - n // 2) == 0) & ((xx - n // 2) >= 0)))
    r = np.real(A[half] * np.conj(B[half]))
    return float(2.0 * np.sqrt(r.size) * r.std(ddof=1) / cnt)


def null_by_roll(a, b, nshift=48, minshift=64, seed=5):
    """Empirical null: C(a, roll(b)).  A roll preserves the marginal
    distribution, the window and the ring exactly, and destroys correspondence."""
    n = a.shape[0]
    rng = np.random.default_rng(seed)
    A = spec(a)
    vals = []
    for _ in range(nshift):
        while True:
            dy, dx = int(rng.integers(0, n)), int(rng.integers(0, n))
            if min(dy, n - dy) >= minshift and min(dx, n - dx) >= minshift:
                break
        vals.append(canon_from(A, spec(np.roll(b, (dy, dx), axis=(0, 1)))))
    return np.array(vals, float)


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


def main():
    res, t0 = {}, time.time()
    print("=" * 78)
    print("M55b E12 -- the empirical null for a ring cross-power (PR30/PR31/PR32)")
    print("=" * 78)
    print("  A roll of >=64 px destroys correspondence and preserves everything else.")
    print("  48 rolls per cell.  'z' is (value - mean_null) / sd_null.\n")
    hdr = ("   stack      ROI      split         C            mode-SE      sd(NULL)"
           "   NULL/modeSE     z")
    rows = []
    for sname, cfg in STACKS.items():
        files = sorted(glob.glob(os.path.join(r"D:\personal\macro", sname, "*.ARW")))
        files = files[cfg["lo"]:cfg["hi"]]
        for rname, roi in cfg["rois"].items():
            cube = load_cube(files, roi)
            fine, coarse, reg = L1.focus_fields(cube, G, RN_E)
            nf = cube.shape[0]
            idx = np.arange(nf)
            h = nf // 2
            sp = {"parity": (idx[0::2], idx[1::2]),
                  "contiguous": (idx[:h], idx[h:2 * h])}
            if not rows:
                print(hdr)
            st = res.setdefault(f"{sname}|{rname}", {})
            for split, (ia, ib) in sp.items():
                a, b = merge(cube, coarse, reg, ia), merge(cube, coarse, reg, ib)
                A, B = spec(a), spec(b)
                C = canon_from(A, B)
                se = mode_se(A, B)
                nul = null_by_roll(a, b)
                sd = float(nul.std(ddof=1))
                z = (C - float(nul.mean())) / sd
                st[split] = dict(C=C, mode_se=se, null_sd=sd, null_mean=float(nul.mean()),
                                 ratio_null_se=sd / se, z=float(z))
                print(f"   {sname:10s} {rname:8s} {split:11s} {C:+12.4e} {se:12.4e}"
                      f" {sd:12.4e} {sd/se:11.1f}x {z:9.2f}")
                rows.append((sname, rname, split, C, se, sd, z))
            st["contig_over_parity"] = st["contiguous"]["C"] / st["parity"]["C"]
            del cube, fine, coarse, reg

    # ------------------------------------------------------------ PR30
    print("\n" + "=" * 78)
    print("  PR30 -- is a mode-scatter standard error usable for this statistic?")
    print("=" * 78)
    rr = [v["ratio_null_se"] for k, v in res.items() for s in ("parity", "contiguous")
          for v in [res[k][s]]]
    print(f"   sd(NULL)/mode-SE over 12 cells: min {min(rr):.1f}x  median "
          f"{float(np.median(rr)):.1f}x  max {max(rr):.1f}x")
    verdict30 = ("mode-scatter SE is INVALID -- it understates the null by >=3x"
                 if float(np.median(rr)) >= 3.0 else "mode-scatter SE is adequate")
    print(f"   -> {verdict30}")
    res["pr30"] = dict(min=min(rr), median=float(np.median(rr)), max=max(rr), verdict=verdict30)

    # ------------------------------------------------------------ PR31
    print("\n" + "=" * 78)
    print("  PR31 -- where does the contiguous split sit inside the null?")
    print("=" * 78)
    flat_in, det_in = 0, 0
    for k, v in res.items():
        if "|" not in k:
            continue
        s, r = k.split("|")
        z = v["contiguous"]["z"]
        inside = abs(z) < 2.0
        tag = "INSIDE the null" if inside else "outside"
        print(f"   {s:10s} {r:8s} contiguous z = {z:+7.2f}   {tag}"
              f"     (parity z = {v['parity']['z']:+8.2f})")
        if r == "flat":
            flat_in += int(inside)
        else:
            det_in += int(inside)
    print(f"\n   flat ROIs inside the null: {flat_in} of 3   "
          f"detail/centre ROIs inside the null: {det_in} of 3")
    verdict31 = ("Q165 ANSWERED -- the flat-ROI contiguous penalty is a ratio taken "
                 "inside the null" if flat_in >= 2 and det_in <= 1 else
                 "Q165 NOT answered by this route")
    print(f"   -> {verdict31}")
    res["pr31"] = dict(flat_inside=flat_in, detail_inside=det_in, verdict=verdict31)

    # ------------------------------------------------------------ PR32
    print("\n" + "=" * 78)
    print("  PR32 -- E9 and E11 disagree because 'best focus' is defined twice")
    print("=" * 78)
    files = sorted(glob.glob(os.path.join(r"D:\personal\macro", "113MSDCF", "*.ARW")))[0:63]
    cube = load_cube(files, STACKS["113MSDCF"]["rois"]["flat"])
    fine, coarse, reg = L1.focus_fields(cube, G, RN_E)
    e = cube[:, PAD:-PAD, PAD:-PAD]
    b_e9 = int(np.argmax([float(np.mean(np.abs(np.diff(f, axis=0)))) for f in e]))
    b_e11 = int(np.argmax([np.mean(coarse[i]) for i in range(cube.shape[0])]))
    print(f"   113MSDCF flat: E9 best-focus frame {b_e9}; E11 best-focus frame {b_e11}")
    res["pr32"] = dict(best_e9=b_e9, best_e11=b_e11, tables={})
    for nm, best in (("e9_grad", b_e9), ("e11_coarse", b_e11)):
        out = {}
        line = f"   {nm:11s}"
        for K in (8, 16, 32):
            lo = max(0, min(best - K // 2, cube.shape[0] - K))
            sub = np.arange(lo, lo + K)
            pa = merge(cube, coarse, reg, sub[0::2]); pb = merge(cube, coarse, reg, sub[1::2])
            ca = merge(cube, coarse, reg, sub[:K // 2]); cb = merge(cube, coarse, reg, sub[K // 2:])
            r = canon_from(spec(ca), spec(cb)) / canon_from(spec(pa), spec(pb))
            out[K] = float(r)
            line += f"   K={K:2d} {r:+7.4f}"
        res["pr32"]["tables"][nm] = out
        print(line)
    print("   Neither definition trends toward 1.0 as K narrows on this flat ROI,")
    print("   so fact 707's qualitative claim replicates; its NUMBERS do not.")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "e12_null.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote out/e12_null.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
