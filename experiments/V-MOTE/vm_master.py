"""V-MOTE P5 -- the mote in the DELIVERED masters, and the mechanism of the 17x.

Three statistics on the same pixels so they can be compared rather than argued:

  DV5   DELIVER-V5's exact statistic, transcribed from experiments/DELIVER-V5/
        dust_patch.py: 8-bit green, mean over r<22 divided by mean over
        40<r<70, at a FIXED coordinate.
  VM    my commissioned statistic: mean over r<=16 px divided by a quadratic
        fitted to 90<=r<=160 px.  Master pixels are photosites, so every radius
        is exactly 2x the quad radii vm_profile.py commissioned.
  SEARCH  min of VM over a +-170 px window -- V-EYES's search radius -- run BOTH
        at the mote and at K control anchors, because a minimum over a search is
        a biased statistic and the bias must be priced, not assumed away.
"""
import os, sys
import numpy as np
import tifffile

MAST = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
SITE_P = (6868, 4610)     # 2 x BUILD-DEFECT quad (3434,2305)
SITE_M = (7008, 4450)     # V-EYES / DELIVER-V5
R_CORE, R_IN, R_OUT = 16, 90, 160
SEARCH = 170


def vm_depth(g, cx, cy, r_core=R_CORE, r_in=R_IN, r_out=R_OUT):
    h, w = g.shape
    y0, y1 = max(0, cy - r_out), min(h, cy + r_out + 1)
    x0, x1 = max(0, cx - r_out), min(w, cx + r_out + 1)
    sub = g[y0:y1, x0:x1]
    dy = (np.arange(y0, y1) - cy)[:, None] * np.ones((1, x1 - x0))
    dx = np.ones((y1 - y0, 1)) * (np.arange(x0, x1) - cx)[None, :]
    r = np.hypot(dx, dy)
    ann = (r >= r_in) & (r <= r_out)
    core = r <= r_core
    if ann.sum() < 200 or core.sum() < 20:
        return float("nan"), float("nan")
    A = np.stack([np.ones(ann.sum()), dx[ann], dy[ann], dx[ann]**2,
                  dx[ann]*dy[ann], dy[ann]**2], 1)
    c, *_ = np.linalg.lstsq(A, sub[ann], rcond=None)
    bg = float(c[0])
    if bg <= 1.0:
        return float("nan"), float("nan")
    pred = (c[0] + c[1]*dx + c[2]*dy + c[3]*dx**2 + c[4]*dx*dy + c[5]*dy**2)
    rough = float(np.std(sub[ann] / pred[ann] - 1.0)) * 100.0
    return 100.0 * (float(sub[core].mean()) / bg - 1.0), rough


def dv5(g8, cx, cy):
    """DELIVER-V5 dust_patch.py, transcribed."""
    P = 256
    h, w = g8.shape
    x0 = max(0, min(w - P, cx - P // 2))
    y0 = max(0, min(h - P, cy - P // 2))
    patch = g8[y0:y0 + P, x0:x0 + P].astype(np.float32)
    px, py = cx - x0, cy - y0
    yy, xx = np.mgrid[0:P, 0:P]
    r = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
    inner = patch[r < 22].mean()
    outer = patch[(r > 40) & (r < 70)].mean()
    return 100.0 * (inner / max(outer, 1.0) - 1.0), float(outer), float(patch[(r > 40) & (r < 70)].std()), (x0, y0)


def to8(a16):
    return np.clip(a16.astype(np.float32) / 257.0, 0, 255)


def main():
    names = sorted(n[:-5] for n in os.listdir(MAST) if n.endswith(".tiff"))
    print("masters: %d" % len(names))
    hdr = ("%-36s %5s %7s %7s   %8s %8s %6s   %8s %-13s" %
           ("subject", "width", "DV5@VE", "DV5@BD", "VM@VE", "VM@BD", "rough",
            "VMmin", "at"))
    print(hdr)
    rows = []
    for n in names:
        a = tifffile.imread(os.path.join(MAST, n + ".tiff"))
        h, w = a.shape[:2]
        g16 = a[..., 1].astype(np.float64)
        del a
        g8 = to8(g16)
        d_ve = dv5(g8, *SITE_M)[0]
        d_bd = dv5(g8, *SITE_P)[0]
        v_ve, _ = vm_depth(g16, *SITE_M)
        v_bd, rough = vm_depth(g16, *SITE_P)
        # search: min of VM over +-SEARCH about BUILD-DEFECT's site, 10 px grid
        best, bx, by = 1e9, -1, -1
        for cy in range(SITE_P[1] - SEARCH, SITE_P[1] + SEARCH + 1, 10):
            for cx in range(SITE_P[0] - SEARCH, SITE_P[0] + SEARCH + 1, 10):
                if not (R_CORE < cx < w - R_CORE and R_CORE < cy < h - R_CORE):
                    continue
                v, _ = vm_depth(g16, cx, cy)
                if np.isfinite(v) and v < best:
                    best, bx, by = v, cx, cy
        print("%-36s %5d %+7.2f %+7.2f   %+8.2f %+8.2f %6.2f   %+8.2f (%d,%d)"
              % (n, w, d_ve, d_bd, v_ve, v_bd, rough, best, bx, by))
        rows.append((n, w, d_ve, d_bd, v_ve, v_bd, rough, best, bx, by))
        del g16, g8
    np.save(r"C:\dev\strehl-out\V-MOTE\cache\master_rows.npy",
            np.array(rows, dtype=object), allow_pickle=True)

    print("\n== flat+bright subset (DELIVER-V5's own admissibility rule: bg>=90 DN8, sd<=8) ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
