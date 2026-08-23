"""M55 E9 -- attack A.3's split contract on stacks the author did not use,
plus the depth-window mechanism discriminator and the swap-asymmetry check.

PRE-REGISTERED as PR17, PR18, PR19, PR22, PR24 before this file ran.
ROIs are fixed by PR24 in advance: 112MSDCF uses M46's sanctioned ROIs; every
other stack uses the geometric centre of the quad plane (916,1501) and the same
flat ROI (2747,32).  No ROI is chosen on its result.

A.3.3 states the per-frame focus fields are properties of a FRAME, not a stack.
So focus_fields is computed ONCE on the full cube and sliced per split.  That
is both what A.3.3 asserts and what makes the split comparison clean.
"""
import os, sys, glob, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
M46SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m46-detail-metric", "src")
M41SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m41-r3-kill", "src")
for p in (M46SRC, M41SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
import m46lib as M
import m41lib as L1
sys.path.insert(0, HERE)
from e8_canonical_plant import canon, _rings, _spectra   # MY implementation

PAD, G, RN_E, NBIN = 32, 1.14469, 1.47, 64
STACKS = {
    "112MSDCF": dict(rois={"detail": (1671, 1373, 512, 512), "flat": (2747, 32, 512, 512)},
                     lo=6, hi=68),
    "113MSDCF": dict(rois={"centre": (916, 1501, 512, 512), "flat": (2747, 32, 512, 512)},
                     lo=0, hi=63),
    "foam":     dict(rois={"centre": (916, 1501, 512, 512), "flat": (2747, 32, 512, 512)},
                     lo=0, hi=62),
}


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


def old_sigpow(a, b):
    n = a.shape[0]
    W = np.outer(np.hanning(n), np.hanning(n))
    rs = _rings(n, NBIN)
    A, _ = _spectra(a, b)
    j = int(np.argmin([abs(c - M.F_SIG) for (_, _, c) in rs]))
    m, cnt, _ = rs[j]
    return M.frc_at(a, b) * float(np.mean(np.abs(A[m]) ** 2))


def frc_ring(a, b):
    rs = _rings(a.shape[0], NBIN)
    A, B = _spectra(a, b)
    j = int(np.argmin([abs(c - M.F_SIG) for (_, _, c) in rs]))
    m, cnt, _ = rs[j]
    num = float(np.real(np.sum(A[m] * np.conj(B[m]))))
    den = float(np.sqrt(np.sum(np.abs(A[m]) ** 2) * np.sum(np.abs(B[m]) ** 2)))
    return num / den


def splits(nf, seed=7):
    idx = np.arange(nf)
    h = nf // 2
    out = {"parity": (idx[0::2], idx[1::2]),
           "contiguous": (idx[:h], idx[h:2 * h])}
    for blk in (2, 4, 8):
        grp = (idx // blk) % 2
        out[f"block-{blk}"] = (idx[grp == 0], idx[grp == 1])
    r = np.random.default_rng(seed).permutation(idx)
    out["random"] = (np.sort(r[:h]), np.sort(r[h:2 * h]))
    return out


res, t0 = {}, time.time()
for sname, cfg in STACKS.items():
    files = sorted(glob.glob(os.path.join(r"D:\personal\macro", sname, "*.ARW")))
    files = files[cfg["lo"]:cfg["hi"]]
    print("\n" + "=" * 78)
    print(f"M55 E9 -- {sname}, {len(files)} frames"
          + ("   (the author's stack)" if sname == "112MSDCF" else "   (NOT used by the author)"))
    print("=" * 78)
    for rname, roi in cfg["rois"].items():
        cube = load_cube(files, roi)
        fine, coarse, reg = L1.focus_fields(cube, G, RN_E)
        nf = cube.shape[0]

        # ------------------------------------------------ PR18 split table
        print(f"\n  ROI {rname} {roi}   level {np.median(cube):.1f} DN")
        print("     split          n_A  n_B   FRC(f_sig)     canonical sigpow   vs parity")
        rows, par = {}, None
        for k, (ia, ib) in splits(nf).items():
            a, b = merge(cube, coarse, reg, ia), merge(cube, coarse, reg, ib)
            v = canon(a, b)[0]
            fr = frc_ring(a, b)
            if k == "parity":
                par = v
                sw = old_sigpow(a, b), old_sigpow(b, a)
            rows[k] = dict(na=len(ia), nb=len(ib), frc=fr, sigpow=v)
            print(f"     {k:<13} {len(ia):4d} {len(ib):4d}   {fr:+10.6f}   {v:16.5e}"
                  f"   {v/par:9.4f}")
        for k in rows:
            rows[k]["vs_parity"] = rows[k]["sigpow"] / par
        # ------------------------------------------------ PR22 swap
        asym = abs(sw[0] - sw[1]) / abs(0.5 * (sw[0] + sw[1]))
        ca, cb = canon(merge(cube, coarse, reg, splits(nf)["parity"][0]),
                       merge(cube, coarse, reg, splits(nf)["parity"][1]))[0], None
        cb = canon(merge(cube, coarse, reg, splits(nf)["parity"][1]),
                   merge(cube, coarse, reg, splits(nf)["parity"][0]))[0]
        print(f"     PR22 swap asymmetry:  OLD form {asym:.4e}"
              f"   CANONICAL {abs(ca-cb)/abs(ca):.4e}   (A.0.2 reports 1.96e-02)")

        # ------------------------------------------------ PR19 depth window
        e = cube[:, PAD:-PAD, PAD:-PAD]
        sharp = np.array([float(np.mean(np.abs(np.diff(f, axis=0)))) for f in e])
        best = int(np.argmax(sharp))
        print(f"\n     PR19 depth-window discriminator (best-focus frame index {best} of {nf})")
        print("     window K   frames    parity sigpow    contiguous/parity    FRC contig")
        pr19 = {}
        for K in (8, 16, 32, nf):
            lo = max(0, min(best - K // 2, nf - K)); hi = lo + min(K, nf)
            sub = np.arange(lo, hi)
            sp = splits(len(sub))
            pa, pb = merge(cube, coarse, reg, sub[sp["parity"][0]]), merge(cube, coarse, reg, sub[sp["parity"][1]])
            ca_, cb_ = merge(cube, coarse, reg, sub[sp["contiguous"][0]]), merge(cube, coarse, reg, sub[sp["contiguous"][1]])
            vp, vc = canon(pa, pb)[0], canon(ca_, cb_)[0]
            print(f"     {K:8d}   {len(sub):6d}   {vp:14.5e}   {vc/vp:17.4f}    {frc_ring(ca_, cb_):+10.6f}")
            pr19[K] = dict(lo=int(lo), hi=int(hi), parity=vp, contig=vc, ratio=vc / vp)

        # ------------------------------------------------ PR17 separation
        q = [np.arange(nf)[i::4] for i in range(4)]
        base_a, base_b = merge(cube, coarse, reg, q[0]), merge(cube, coarse, reg, q[1])
        sm_a = merge(cube, coarse, reg, np.sort(np.concatenate([q[0], q[2]])))
        sm_b = merge(cube, coarse, reg, np.sort(np.concatenate([q[1], q[3]])))
        h0 = M.hp_sd(base_a); h1 = M.hp_sd(sm_a)
        lo, hi = 0.0, 2.0
        for _ in range(34):
            mid = 0.5 * (lo + hi)
            if M.hp_sd(M.blur(base_a, mid)) > h1:
                lo = mid
            else:
                hi = mid
        sb = 0.5 * (lo + hi)
        bl_a, bl_b = M.blur(base_a, sb), M.blur(base_b, sb)
        vb, vs, vl = canon(base_a, base_b)[0], canon(sm_a, sm_b)[0], canon(bl_a, bl_b)[0]
        db, ds = (vb - vl) / abs(vb), (vb - vs) / abs(vb)
        Sv = abs(db) / (abs(db) + abs(ds))
        print(f"\n     PR17 real separation, canonical, k=sqrt2 of REAL photons")
        print(f"       hp_sd {h0:.3f} -> {h1:.3f}, matched blur sb = {sb:.5f} px")
        print(f"       baseline {vb:.5e}  BLUR {vl:.5e}  SMOOTH {vs:.5e}")
        print(f"       d_blur {db:+.5f}   d_smooth {ds:+.5f}   S(canonical) = {Sv:.3f}")
        res.setdefault(sname, {})[rname] = dict(splits=rows, swap_old=asym,
            swap_canon=abs(ca - cb) / abs(ca), pr19=pr19,
            pr17=dict(sb=sb, d_blur=db, d_smooth=ds, S=Sv, base=vb, blur=vl, smooth=vs))
        del cube, coarse, reg, fine

with open(os.path.join(OUT, "e9_split.json"), "w") as fh:
    json.dump(res, fh, indent=2, default=float)
print(f"\nwrote out/e9_split.json  ({time.time()-t0:.1f}s)")
