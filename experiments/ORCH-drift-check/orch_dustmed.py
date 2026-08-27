"""Cross-master dust detector: exploit the one property dust has and scenes do not.

The per-master tail statistic failed on its first row -- the detector was deaf (gain
0.001 on a 60 DN plant) because a 900px block high-passed at 201px is dominated by scene
structure, not noise, so both the threshold and the tail measured subject contrast.

The fix is not a better threshold. It is a better discriminator, and the physics supplies
one: dust sits on the sensor or the rear element, so it lands at the SAME array coordinate
in every stack ever shot, while subject structure is independent between subjects. Take
the median across masters and scene structure is rejected by construction (a feature
present in 1 of 15 cannot survive a median) while dust is reinforced (present in 15 of
15). No size prior, no depth prior, no per-master noise calibration.

This is also the exact physical claim BUILD-BLEND's defect_map.rs is built on -- that the
stack is its own flat field -- so measuring it here tests their design before they finish
implementing it.

COMMISSIONING (runs first, always): three arms, of which the middle one is the whole
point.
  COMMON : plant discs at identical coordinates in every master -> median MUST show them.
  INDEP  : plant discs at random coordinates per master         -> median MUST NOT.
  NULL   : no plant                                             -> the real measurement.
The INDEP arm is what certifies the discrimination rather than the sensitivity. A detector
that fires on both arms is a dark-blob detector that has learned nothing about sensor
coordinates, and its NULL reading would be meaningless.
"""
import pathlib
import sys

import numpy as np
import tifffile

DS = 4
HP = 51
PLANT_DN = 80.0
PLANT_R = 8
N_PLANT = 12


def downsample(a, f):
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def boxblur(a, win):
    r = win // 2
    pad = np.pad(a, ((r, r), (r, r)), mode="edge")
    c = np.cumsum(np.cumsum(pad, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    s = c[win:win + h, win:win + w] - c[0:h, win:win + w] \
        - c[win:win + h, 0:w] + c[0:h, 0:w]
    return s / (win * win)


def load_residual(p):
    a = tifffile.imread(str(p))
    rgb = a[:, :, :3].astype(np.float32)
    del a
    lum = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    del rgb
    small = downsample(lum, DS).astype(np.float32)
    del lum
    res = small - boxblur(small, HP)
    mad = float(np.median(np.abs(res - np.median(res))))
    return res / max(mad, 1e-6), small


def add_discs(res, coords):
    yy, xx = np.mgrid[0:res.shape[0], 0:res.shape[1]]
    for cy, cx in coords:
        res[((yy - cy) ** 2 + (xx - cx) ** 2) < PLANT_R ** 2] -= PLANT_DN / 50.0
    return res


def depth_at(med, coords):
    """Median normalised depth at the planted sites, against a local annulus."""
    out = []
    yy, xx = np.mgrid[0:med.shape[0], 0:med.shape[1]]
    for cy, cx in coords:
        d2 = (yy - cy) ** 2 + (xx - cx) ** 2
        core = med[d2 < PLANT_R ** 2]
        ring = med[(d2 >= (PLANT_R * 2) ** 2) & (d2 < (PLANT_R * 3) ** 2)]
        if core.size and ring.size:
            out.append(float(np.median(ring) - np.median(core)))
    return float(np.median(out)) if out else 0.0


def main(argv):
    group = int(argv[0]) if argv else 7032
    d = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")
    paths = []
    for p in sorted(d.iterdir()):
        if p.suffix.lower() != ".tiff":
            continue
        with tifffile.TiffFile(str(p)) as tf:
            if tf.series[0].shape[1] == group:
                paths.append(p)
    print(f"group width {group}: {len(paths)} masters")
    if len(paths) < 5:
        print("REFUSE: fewer than 5 masters; a median cannot reject scene structure")
        return 2

    rng = np.random.default_rng(2024)
    resids = []
    for p in paths:
        r, _ = load_residual(p)
        resids.append(r)
        print(f"  loaded {p.stem[:44]:46s} {r.shape}")
    stack = np.stack(resids)
    del resids
    h, w = stack.shape[1], stack.shape[2]
    common = [(int(rng.integers(40, h - 40)), int(rng.integers(40, w - 40)))
              for _ in range(N_PLANT)]

    print("\ncommissioning:")
    med_null = np.median(stack, axis=0)

    sc = stack.copy()
    for i in range(sc.shape[0]):
        add_discs(sc[i], common)
    med_common = np.median(sc, axis=0)
    d_common = depth_at(med_common, common)
    del sc

    si = stack.copy()
    for i in range(si.shape[0]):
        indep = [(int(rng.integers(40, h - 40)), int(rng.integers(40, w - 40)))
                 for _ in range(N_PLANT)]
        add_discs(si[i], indep)
        if i == 0:
            first_indep = indep
    med_indep = np.median(si, axis=0)
    d_indep = depth_at(med_indep, first_indep)
    del si

    base = depth_at(med_null, common)
    print(f"  ARM COMMON (same coords in all {len(paths)}) : depth {d_common:8.4f}")
    print(f"  ARM INDEP  (random coords per master)   : depth {d_indep:8.4f}")
    print(f"  ARM NULL   (same sites, unplanted)      : depth {base:8.4f}")
    sens = d_common - base
    ok_sens = sens > 0.30
    ok_disc = abs(d_indep) < 0.25 * sens if sens > 0 else False
    print(f"  sensitivity  (COMMON - NULL) : {sens:8.4f}  {'PASS' if ok_sens else 'FAIL'}")
    print(f"  discrimination (INDEP/sens)  : "
          f"{(d_indep / sens if sens > 0 else float('nan')):8.4f}  "
          f"{'PASS' if ok_disc else 'FAIL'}")
    if not (ok_sens and ok_disc):
        print("\nNOT COMMISSIONED - the census below certifies nothing")
        return 1
    print("  COMMISSIONED")

    print("\nreal measurement (unplanted cross-master median):")
    m = med_null
    mad = float(np.median(np.abs(m - np.median(m))))
    lo = float(np.percentile(m, 0.02))
    print(f"  median-image robust sigma : {1.4826 * mad:.4f} (normalised units)")
    print(f"  0.02th percentile         : {lo:.4f}")
    thr = np.median(m) - 6.0 * 1.4826 * mad
    hits = m < thr
    print(f"  pixels below median-6sigma: {int(hits.sum())} "
          f"({100.0 * hits.mean():.4f}% of {m.size})")

    lab = np.zeros(m.shape, np.int32)
    ys, xs = np.nonzero(hits)
    seen = set()
    blobs = []
    hs = set(zip(ys.tolist(), xs.tolist()))
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if (sy, sx) in seen:
            continue
        stackq = [(sy, sx)]
        seen.add((sy, sx))
        cells = []
        while stackq:
            cy, cx = stackq.pop()
            cells.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    n = (cy + dy, cx + dx)
                    if n in hs and n not in seen:
                        seen.add(n)
                        stackq.append(n)
        if len(cells) >= 4:
            arr = np.array(cells)
            blobs.append((len(cells), int(arr[:, 0].mean()), int(arr[:, 1].mean()),
                          float(m[arr[:, 0], arr[:, 1]].min())))
    blobs.sort(key=lambda b: b[3])
    print(f"  connected blobs >= 4 px   : {len(blobs)}")
    print(f"\n  strongest (coords are /{DS} downsampled; multiply by {DS} for master px):")
    for n, by, bx, depth in blobs[:20]:
        print(f"    {n:5d} px  at ({bx * DS:5d},{by * DS:5d})  depth {depth:8.3f}")
    np.save(r"C:\dev\strehl-out\dustmed_%d.npy" % group, m.astype(np.float32))
    print(f"\n  saved median image -> C:\\dev\\strehl-out\\dustmed_{group}.npy")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
