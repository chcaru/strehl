"""S3 — the confound-free version: compare each channel against ITSELF.

WHY S2 WAS THE WRONG QUESTION
-----------------------------
S2 registered the red channel against the blue channel on a real photograph.
On a coloured subject those are not shifted copies of one image, they are two
different images, and the fit is dominated by the scene's own colour structure.
Measured per-ROI scatter was sd ~= 0.5 binned px, as large as the effect, and
the fitted constants disagreed between the two image pairs. That arm is
retired; it is reported as a failure, not as a weak result.

THE CONFOUND-FREE VERSION
-------------------------
Box-average the demosaiced render over each 2x2 quad. Malvar-He-Cutler
estimates all three channels at every photosite, so the box average of a quad
puts every channel at the SAME point -- the quad centre -- at the same scale as
the binned render.

Now compare each channel to ITSELF:

    shift(ground_R, binned_R)     ground_G vs binned_G     ground_B vs binned_B

Same scene content, same colour, same everything -- the only difference is
where the sample was taken. The chroma confound is gone by construction.

THE PREDICTION, AND THE INTERNAL NULL
-------------------------------------
Relative to the quad centre the binned render samples red at (-0.5, -0.5)
sensor px, green at the centre, and blue at (+0.5, +0.5) sensor px, i.e.
(-0.25, -0.25), (0, 0) and (+0.25, +0.25) binned px.

So the three channels must read a SIGNED, ORDERED signature:

    red     ~ -0.25        green ~ 0        blue ~ +0.25   (up to overall sign)

Green is the internal null. It runs through the identical code path with the
identical data, so if green also reads +-0.25 the measurement is an artifact of
the method rather than of the sampling geometry. A single number could be
noise; this three-point signature with a zero in the middle cannot easily be.

C10 settles the overall sign by construction on a synthetic mosaic, exactly as
C6 did, rather than by doing the algebra again.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402

S = 256
COH_MIN = 0.5
PAIRS = {
    "frame-183": ("armF-f183.tif", "armF-f183-demo.tif"),
    "merged-gate0": ("armM-gate0-binlin.tif", "armM-gate0-demo.tif"),
}


def box2(a):
    """Average each 2x2 block. Symmetric, so it blurs but introduces no shift."""
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    t = a[:h, :w].astype(np.float64)
    return 0.25 * (t[0::2, 0::2] + t[0::2, 1::2] + t[1::2, 0::2] + t[1::2, 1::2])


# ------------------------------------------------------------------ C10
def c10_synthetic():
    """Same pipeline on a synthetic mosaic whose truth is known by construction.

    A mono band-limited scene is mosaicked, binned exactly as `merge_cmd.rs`
    bins, and compared against the same scene box-averaged per quad. Because
    the scene is mono, `ground` here is just the quad mean of the scene, which
    is the co-sited reference the demosaic approximates.
    """
    print("== C10: synthetic, truth by construction ==")
    rows = []
    for seed in (11, 12, 13, 14, 15):
        rng = np.random.default_rng(seed)
        n = 1024
        a = rng.standard_normal((n, n))
        fy = np.fft.fftfreq(n)[:, None]
        fx = np.fft.fftfreq(n)[None, :]
        r = np.sqrt(fy**2 + fx**2)
        f = np.real(np.fft.ifft2(np.fft.fft2(a) * (r <= 0.20)))

        ground = box2(f)
        bin_r = f[0::2, 0::2]
        bin_g = 0.5 * (f[0::2, 1::2] + f[1::2, 0::2])
        bin_b = f[1::2, 1::2]

        dr = C.phase_ramp_shift_robust(ground, bin_r)[:2]
        dg = C.phase_ramp_shift_robust(ground, bin_g)[:2]
        db = C.phase_ramp_shift_robust(ground, bin_b)[:2]
        rows.append({"seed": seed, "R": list(dr), "G": list(dg), "B": list(db)})
        print("  seed %d  R (%+.4f,%+.4f)  G (%+.4f,%+.4f)  B (%+.4f,%+.4f)"
              % (seed, dr[0], dr[1], dg[0], dg[1], db[0], db[1]))

    mr = np.mean([r_["R"] for r_ in rows], axis=0)
    mg = np.mean([r_["G"] for r_ in rows], axis=0)
    mb = np.mean([r_["B"] for r_ in rows], axis=0)
    print("  mean  R (%+.4f,%+.4f)  G (%+.4f,%+.4f)  B (%+.4f,%+.4f)"
          % (mr[0], mr[1], mg[0], mg[1], mb[0], mb[1]))
    ok = (
        np.all(np.abs(np.abs(mr) - 0.25) < 0.02)
        and np.all(np.abs(mg) < 0.02)
        and np.all(np.abs(np.abs(mb) - 0.25) < 0.02)
        and float(mr[0]) * float(mb[0]) < 0
    )
    print("  C10: %s (|R|=|B|=0.25, G=0, R and B opposite in sign)"
          % ("PASS" if ok else "FAIL"))
    return ok, rows, mr.tolist(), mg.tolist(), mb.tolist()


# ------------------------------------------------------------------ real
def field_rois(h, w, s, nx, ny, margin=64):
    ys = np.linspace(margin, h - s - margin, ny).astype(int)
    xs = np.linspace(margin, w - s - margin, nx).astype(int)
    return [(int(y), int(x)) for y in ys for x in xs]


def run_pair(name, binf, demof):
    print("\n" + "=" * 72)
    print("PAIR: %s" % name)
    ib = C.load_tif(os.path.join(C.OUT, binf)).astype(np.float64)
    idm = C.load_tif(os.path.join(C.OUT, demof)).astype(np.float64)
    ground = np.stack([box2(idm[:, :, c]) for c in range(3)], axis=2)
    assert ground.shape == ib.shape, (ground.shape, ib.shape)

    h, w = ib.shape[0], ib.shape[1]
    rois = field_rois(h, w, S, nx=7, ny=5)
    per = {"R": [], "G": [], "B": []}
    kept = 0
    for y, x in rois:
        gr = ground[y : y + S, x : x + S, :]
        bn = ib[y : y + S, x : x + S, :]
        cohs = [C.coherence(gr[:, :, c], bn[:, :, c]) for c in range(3)]
        if min(cohs) < COH_MIN:
            continue
        kept += 1
        for c, nm in enumerate("RGB"):
            d = C.phase_ramp_shift_robust(gr[:, :, c], bn[:, :, c])
            per[nm].append({"y": y, "x": x, "dy": d[0], "dx": d[1], "coh": cohs[c]})

    print("  ROIs: %d offered, %d kept (coherence >= %.2f in all three channels)"
          % (len(rois), kept, COH_MIN))
    if kept < 6:
        print("  too few coherent ROIs; skipped")
        return {"n_kept": kept, "skipped": True}

    summ = {}
    for nm in "RGB":
        a = np.array([[r["dy"], r["dx"]] for r in per[nm]])
        m, sd = a.mean(axis=0), a.std(axis=0)
        se = sd / np.sqrt(len(a))
        summ[nm] = {
            "mean_dy": float(m[0]), "mean_dx": float(m[1]),
            "sd_dy": float(sd[0]), "sd_dx": float(sd[1]),
            "se_dy": float(se[0]), "se_dx": float(se[1]),
            "n": int(len(a)),
        }
        print("  %s  mean (%+.4f, %+.4f)   sd (%.4f, %.4f)   se (%.4f, %.4f)  n=%d"
              % (nm, m[0], m[1], sd[0], sd[1], se[0], se[1], len(a)))

    dRB = np.hypot(summ["R"]["mean_dy"] - summ["B"]["mean_dy"],
                   summ["R"]["mean_dx"] - summ["B"]["mean_dx"])
    print("  separation of R from B = %.4f binned px  (predicted 0.7071 = 0.5*sqrt2)" % dRB)
    print("  green internal null    = %.4f binned px"
          % np.hypot(summ["G"]["mean_dy"], summ["G"]["mean_dx"]))
    return {"n_offered": len(rois), "n_kept": kept, "summary": summ,
            "per_channel": per, "sep_R_to_B": float(dRB)}


def main():
    out = {}
    ok, rows, mr, mg, mb = c10_synthetic()
    out["C10"] = {"rows": rows, "mean_R": mr, "mean_G": mg, "mean_B": mb, "pass": bool(ok)}
    if not ok:
        C.jdump("s3_cositing.json", out)
        print("\nC10 FAILED -- pipeline invalid on data whose answer I built. Stopping.")
        return 1
    out["pairs"] = {n: run_pair(n, b, d) for n, (b, d) in PAIRS.items()}
    C.jdump("s3_cositing.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
