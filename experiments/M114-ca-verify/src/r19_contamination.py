"""M114 r19: is the scene-to-scene gain agreement real, or two contaminated
numbers whose ratio happens to be stable?

r18 returned gain 1.421 (bee-3-cpl) and 1.493 (119MSDCF) -- inside ORCH's
predicted band. Three things in that table say do not report it yet:

  (i)   measured `applied` = R_on - R_off differed 1.38x between scenes
        (3.325 vs 4.575 px at r=0.92). The SAME coefficient acting on the SAME
        geometry cannot differ. So at least one measurement is scene-contaminated.
  (ii)  native CA slope differed 1.56x between two stacks on the same lens at
        the same aperture.
  (iii) V3 (centre must read 0) FAILED on both scenes.

r18's V2 control plants a shift on the SAME channel, so it proves the searcher
is exact on CORRELATED content. It says nothing about CROSS-CHANNEL bias, which
is where R-vs-G lives. That is the hole.

  A  SAME-CHANNEL applied (R_on vs R_off). Correlated content, so this is the
     V2-exact regime. The same coefficient on the same geometry must give the
     same applied/declared in both scenes. RED IF the scenes disagree.
  B  LINEARITY of R_off in r. A pure radial scale is linear THROUGH THE ORIGIN.
     A non-zero intercept is a constant channel offset or estimator bias, and it
     does NOT cancel in gain = 1 - R_on/R_off.
  C  CENTRE OFFSET AS A VECTOR. r18's V3 projected onto the radial direction,
     which for a CONSTANT translation averages to zero over azimuth -- so with
     n=16 clustered windows its failure may be azimuthal sampling, not bias.
     Measuring (dx,dy) directly removes that artefact.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage
from pathlib import Path

R17 = Path(r"C:\dev\strehl-out\M114-ca-verify\r17")
NOMINAL, WIN = 704.5e-6, 96
RINGS = [(0.10, 0.25), (0.25, 0.38), (0.38, 0.50), (0.50, 0.62),
         (0.62, 0.74), (0.74, 0.86), (0.86, 0.98)]

def gmag(a):
    return ndimage.gaussian_gradient_magnitude(a, 1.0)

def std(a):
    s = a.std()
    return (a - a.mean()) / s if s > 1e-9 else a * 0.0

def _ssd(a, b, ux, uy, ds, order):
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float64)
    best, bd = None, 0.0
    for d in ds:
        w = ndimage.map_coordinates(b, [yy + d * uy, xx + d * ux], order=order, mode="nearest")
        s = float(np.mean((a - w) ** 2))
        if best is None or s < best:
            best, bd = s, float(d)
    return bd

def disp(a, b, ux, uy):
    c = _ssd(a, b, ux, uy, np.arange(-6.0, 6.01, 0.5), 1)
    return -_ssd(a, b, ux, uy, np.arange(c - 0.5, c + 0.501, 0.05), 3)

OUT = {}
for scene in ("bee-3-cpl", "119MSDCF"):
    off = tifffile.imread(str(R17 / (scene + "-off.tif"))).astype(np.float64)
    on = tifffile.imread(str(R17 / (scene + "-on.tif"))).astype(np.float64)
    H, W, _ = off.shape
    cx, cy, RC = W / 2.0, H / 2.0, np.hypot(W / 2.0, H / 2.0)
    G = off[:, :, 1]
    rng = np.random.default_rng(1919)
    samp = [float(np.mean(gmag(G[y:y+WIN, x:x+WIN])))
            for y, x in zip(rng.integers(0, H-WIN, 400), rng.integers(0, W-WIN, 400))]
    thresh = float(np.percentile(samp, 75))
    print("\n=== %s   edge gate %.1f ===" % (scene, thresh), flush=True)

    def wins(rlo, rhi, n, th):
        got, tries = [], 0
        while len(got) < n and tries < 40000:
            tries += 1
            y = int(rng.integers(8, H-WIN-8)); x = int(rng.integers(8, W-WIN-8))
            my, mx = y+WIN/2-cy, x+WIN/2-cx
            rr = np.hypot(mx, my)
            if not (rlo <= rr/RC < rhi) or rr < 1e-6:
                continue
            sl = (slice(y, y+WIN), slice(x, x+WIN))
            if float(np.mean(gmag(G[sl]))) < th:
                continue
            got.append((sl, mx/rr, my/rr, rr/RC))
        return got

    rows = []
    for rlo, rhi in RINGS:
        ws = wins(rlo, rhi, 40, thresh)
        if len(ws) < 8:
            continue
        rm = float(np.median([w[3] for w in ws]))
        # A: SAME-CHANNEL applied -- correlated content, the V2-exact regime
        app = float(np.median([disp(std(gmag(on[sl][:, :, 0])), std(gmag(off[sl][:, :, 0])), ux, uy)
                               for sl, ux, uy, _ in ws]))
        # cross-channel native CA in the off arm
        roff = float(np.median([disp(std(gmag(off[sl][:, :, 0])), std(gmag(off[sl][:, :, 1])), ux, uy)
                                for sl, ux, uy, _ in ws]))
        decl = NOMINAL * rm * RC
        rows.append((rm, len(ws), app, decl, app/decl, roff))
        print("r=%.3f n=%2d  applied(same-ch) %+.3f  declared %+.3f  ratio %.3f   R_off %+.3f"
              % (rm, len(ws), app, decl, app/decl, roff), flush=True)

    rmv = np.array([r[0] for r in rows]); appv = np.array([r[2] for r in rows])
    ratv = np.array([r[4] for r in rows]); roffv = np.array([r[5] for r in rows])
    sl_, ic_ = np.polyfit(rmv, roffv, 1)
    pred = sl_*rmv + ic_
    r2 = 1 - np.sum((roffv-pred)**2)/np.sum((roffv-roffv.mean())**2)
    sl0 = float(np.sum(rmv*roffv)/np.sum(rmv*rmv))
    r2_0 = 1 - np.sum((roffv-sl0*rmv)**2)/np.sum((roffv-roffv.mean())**2)
    print("  A applied/declared: mean %.3f  spread %.3f-%.3f" % (ratv.mean(), ratv.min(), ratv.max()))
    print("  B R_off fit: slope %+.3f intercept %+.3f R2 %.4f | THROUGH-ORIGIN slope %+.3f R2 %.4f"
          % (sl_, ic_, r2, sl0, r2_0))

    # C: centre offset as a VECTOR, n=60, azimuth-free
    wc = wins(0.0, 0.08, 60, thresh*0.5)
    dx = float(np.median([disp(std(gmag(off[sl][:, :, 0])), std(gmag(off[sl][:, :, 1])), 1.0, 0.0) for sl, _, _, _ in wc]))
    dy = float(np.median([disp(std(gmag(off[sl][:, :, 0])), std(gmag(off[sl][:, :, 1])), 0.0, 1.0) for sl, _, _, _ in wc]))
    print("  C centre R-G vector: dx %+.3f  dy %+.3f  |t| %.3f px (n=%d)" % (dx, dy, np.hypot(dx, dy), len(wc)))
    OUT[scene] = dict(rows=[list(map(float, r)) for r in rows], applied_ratio=float(ratv.mean()),
                      ratio_spread=[float(ratv.min()), float(ratv.max())],
                      slope=float(sl_), intercept=float(ic_), r2=float(r2),
                      slope0=sl0, r2_0=float(r2_0), centre=[dx, dy])

a, b = OUT["bee-3-cpl"], OUT["119MSDCF"]
print("\n=== A: does the DELIVERED correction match between scenes? ===")
print("bee-3-cpl applied/declared %.3f   119MSDCF %.3f   difference %+.1f%%"
      % (a["applied_ratio"], b["applied_ratio"], 100*(b["applied_ratio"]/a["applied_ratio"]-1)))
print("=== B: native CA slope ===")
print("bee-3-cpl %+.3f px/unit-r   119MSDCF %+.3f   ratio %.3f"
      % (a["slope0"], b["slope0"], b["slope0"]/a["slope0"]))
(R17 / "r19.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")
