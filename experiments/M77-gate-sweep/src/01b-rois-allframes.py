"""M77 arm G0' -- ROI selection over ALL frames. DECLARED DEVIATION, post hoc.

WHY THIS ARM EXISTS. The registered arm G0 (01-rois.py) sampled >= 12 frames at a
fixed stride, which PREREGISTRATION.md section 4 step 2 permits. Section 4 step 4
states the rule's purpose in its own words: the flat tile must be flat "in EVERY
sampled frame rather than on average -- a tile that is flat in most frames and
textured in one is not a flat ROI for a sweep that averages frames". The stride
defeated that purpose: on `foam` the shipped CLI reported the selected tile's
reference hp sd running 28.761 DN (frame 1) to 502.786 DN (frame 44), and frame
44 was not among the 15 sampled. This arm closes that loophole and changes
nothing else -- same 256x256 grid, same stride 128, same edge margin, same two
statistics, same max-over-frames reduction.

It is POST HOC and is labelled as such wherever it is reported. It is judged by
the SAME pre-registered K3 bar as arm G0, so the diagnosis can fail.

Everything per tile and per frame is saved to 00-scan-<stack>.npz so that any
later selection rule costs nothing further and no further decode is spent.

Speed: the per-tile statistics are exact but computed from PLANE-WIDE integral
images rather than per-tile filters. For the high-pass this is EXACTLY equal to
the per-tile computation, because box9's valid interior of a 256-px tile reads
only in-tile samples.
"""

import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m77  # noqa: E402

TILE = 256
STRIDE = 128
EDGE = 32
R = m77.HP_BOX_RADIUS


def tiles_for(h, w):
    ys = list(range(EDGE, h - TILE - EDGE + 1, STRIDE))
    xs = list(range(EDGE, w - TILE - EDGE + 1, STRIDE))
    return [(x, y) for y in ys for x in xs]


def integral(a):
    s = np.zeros((a.shape[0] + 1, a.shape[1] + 1), dtype=np.float64)
    np.cumsum(np.cumsum(a, axis=0), axis=1, out=s[1:, 1:])
    return s


def rect(s, x, y, w, h):
    return s[y + h, x + w] - s[y, x + w] - s[y + h, x] + s[y, x]


def scan_frame(path, iso, tl):
    a = m77.green_luma_plane(path)
    h, w = a.shape
    resid = a - m77.box_mean(a, R)
    s1, s2 = integral(resid), integral(resid * resid)
    sm = integral(a)

    dx = a[:-1, 1:] - a[:-1, :-1]
    dy = a[1:, :-1] - a[:-1, :-1]
    sg = integral(dx * dx + dy * dy)
    sig2 = m77.plane_variance(a, iso) * 0.5  # green_luma_sigma^2 = 0.25*(v+v)
    sn = integral(2.0 * sig2[:-1, :-1] + sig2[:-1, 1:] + sig2[1:, :-1])

    side = TILE - 2 * R
    npx = float(side * side)
    ng = float((TILE - 1) * (TILE - 1))
    contam = np.empty(len(tl))
    cg = np.empty(len(tl))
    for t, (x, y) in enumerate(tl):
        xi, yi = x + R, y + R
        m1 = rect(s1, xi, yi, side, side) / npx
        m2 = rect(s2, xi, yi, side, side) / npx
        hp = float(np.sqrt(max(0.0, m2 - m1 * m1)))
        mu = rect(sm, x, y, TILE, TILE) / float(TILE * TILE)
        msig = float(m77.green_luma_sigma(mu, iso))
        contam[t] = hp / (m77.HP_NOISE_GAIN * msig) if msig > 0 else np.inf
        raw2 = rect(sg, x, y, TILE - 1, TILE - 1) / ng
        noi2 = rect(sn, x, y, TILE - 1, TILE - 1) / ng
        cg[t] = float(np.sqrt(max(0.0, raw2 - noi2)))
    return contam, cg, (h, w)


def main():
    m77.banner("M77 arm G0' -- ROI selection over ALL frames (DECLARED DEVIATION)")
    print(f"  tile {TILE}  stride {STRIDE}  edge {EDGE}  ALL frames")
    out = {}
    for stack in m77.STACKS:
        files = m77.stack_files(stack)
        iso = m77.iso_of(files[0])
        a0 = m77.green_luma_plane(files[0])
        tl = tiles_for(*a0.shape)
        del a0
        contam = np.zeros((len(tl), len(files)))
        cg = np.zeros((len(tl), len(files)))
        t0 = time.time()
        for j, f in enumerate(files):
            contam[:, j], cg[:, j], shape = scan_frame(f, iso, tl)
        dt = time.time() - t0
        np.savez_compressed(m77.OUT / f"00-scan-{stack}.npz",
                            contam=contam, cg=cg, tiles=np.array(tl), iso=iso,
                            shape=np.array(shape))
        fs = contam.max(axis=1)
        ds = cg.max(axis=1)
        fi, di = int(np.argmin(fs)), int(np.argmax(ds))
        # temporal spread of the winning tile's hp energy, the CLI's own diagnostic
        row = contam[fi]
        spread = float(row.max() / row.min())
        print(f"\n  --- {stack}  ISO {iso:g}  {len(tl)} tiles x {len(files)} frames"
              f"  ({dt:.0f}s, {dt / len(files):.2f}s/frame)")
        print(f"      FLAT   x{tl[fi][0]},y{tl[fi][1]}  contam(max over ALL frames)"
              f" = {fs[fi]:.4f}  [K1 bar < 1.10 -> "
              f"{'MET' if fs[fi] < 1.10 else 'NOT MET'}]"
              f"   temporal spread {spread:.3f}x")
        print(f"      DETAIL x{tl[di][0]},y{tl[di][1]}  cg(max over ALL frames)"
              f"  = {ds[di]:.4f}")
        best = int(np.argmax(cg[di]))
        k2 = cg[di, best] / cg[fi, best] if cg[fi, best] > 0 else np.inf
        ev, od = slice(0, None, 2), slice(1, None, 2)
        fe = int(np.argmin(contam[:, ev].max(axis=1)))
        fo = int(np.argmin(contam[:, od].max(axis=1)))
        de = int(np.argmax(cg[:, ev].max(axis=1)))
        do = int(np.argmax(cg[:, od].max(axis=1)))

        def adj(p, q):
            return abs(p[0] - q[0]) <= STRIDE and abs(p[1] - q[1]) <= STRIDE

        k5f, k5d = adj(tl[fe], tl[fo]), adj(tl[de], tl[do])
        print(f"      K2 detail/flat cg = {k2:.2f}x  [bar >= 3x -> "
              f"{'MET' if k2 >= 3.0 else 'NOT MET'}]")
        print(f"      K5 even/odd: flat {'MET' if k5f else 'NOT MET'}"
              f"   detail {'MET' if k5d else 'NOT MET'}")
        out[stack] = {
            "iso": iso, "plane": list(shape), "n_tiles": len(tl),
            "n_frames": len(files),
            "flat_roi": {"x": tl[fi][0], "y": tl[fi][1], "w": TILE, "h": TILE,
                         "contam_max": float(fs[fi]), "temporal_spread": spread},
            "detail_roi": {"x": tl[di][0], "y": tl[di][1], "w": TILE, "h": TILE,
                           "cg_max": float(ds[di])},
            "k1_met": bool(fs[fi] < 1.10), "k2_ratio": float(k2),
            "k2_met": bool(k2 >= 3.0),
            "k5_flat_met": bool(k5f), "k5_detail_met": bool(k5d),
            "contam_range": [float(fs.min()), float(fs.max())],
        }
    (m77.OUT / "01b-rois.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n  wrote out/01b-rois.json")


if __name__ == "__main__":
    main()
