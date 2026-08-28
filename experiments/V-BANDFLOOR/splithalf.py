r"""ARE THE FLAT SITES ACTUALLY FLAT AT BAND-0 FREQUENCIES?

Real scene texture is REPRODUCIBLE from disjoint subsets of frames; noise is
INDEPENDENT between them. Render the EVEN-index and ODD-index frames as two
disjoint stacks of the same scene at matched focus range and correlate their
band-0 fields tile by tile. r^2 is the fraction of band-0 variance at a site
that is REAL; 1 - r^2 is the fraction that is noise.

COMMISSIONING NOTES (v2). v1 failed two arms and both failures were the
harness, not the statistic:
  * plants were allowed to RE-CLASSIFY the tiles, so a big planted noise field
    changed which tiles counted as flat and the arms were not comparable. Class
    is now computed ONCE on the clean pair and frozen for every arm.
  * the negative control was a 37 px roll, which leaves scene self-similarity
    intact and read r=+0.74 at detail sites. Replaced with a WITHIN-TILE
    PERMUTATION, which preserves the marginal distribution exactly and destroys
    all spatial correspondence, so it must read ~0 at every site class.
Arms are judged against the MEASURED clean baseline, not against thresholds
guessed in advance.

FOOLING DIRECTIONS: (a) misregistration between halves decorrelates REAL
texture and would make everything look like noise -- the detail column is the
control, since detail must come back high; (b) anything shared for a non-scene
reason (fixed-pattern noise, a hot pixel) correlates and reads as "real": this
measures REPRODUCIBILITY, not sceneness.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402
import nscale as ns                                                # noqa: E402


def band0(g):
    return bm.smooth(g, bm.RADII[0]) - bm.smooth(g, bm.RADII[1])


def tiles_of(a, y0, x0, ty, tx):
    A = a[y0:y0 + ty * bm.TILE, x0:x0 + tx * bm.TILE].reshape(ty, bm.TILE, tx, bm.TILE)
    return A.transpose(0, 2, 1, 3).reshape(ty * tx, -1)


def tile_corr(a, b, y0, x0, ty, tx):
    A = tiles_of(a, y0, x0, ty, tx)
    B = tiles_of(b, y0, x0, ty, tx)
    A = A - A.mean(1, keepdims=True)
    B = B - B.mean(1, keepdims=True)
    return ((A * B).sum(1) /
            np.maximum(np.sqrt((A * A).sum(1) * (B * B).sum(1)), 1e-30))


def boot(v, seed=5, nboot=4000):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(nboot, len(v)))
    m = np.median(v[idx], axis=1)
    return float(np.median(v)), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def geom(shape):
    return bm.tile_grid(shape)


def masks(ge, go, cm, pct):
    y0, x0, ty, tx = geom(ge.shape)
    cl = bm.tile_rms(cm.astype(np.float32), ty, tx, y0, x0)
    ok = (cl == 0.0).ravel()
    t, _ = ns.classify([ge, go], y0, x0, ty, tx)
    t = t.ravel()
    return (ok & (t <= np.percentile(t[ok], pct)),
            ok & (t >= np.percentile(t[ok], 100 - pct)))


def score(ge, go, flat, tex, tag, quiet=False):
    y0, x0, ty, tx = geom(ge.shape)
    r = tile_corr(band0(ge), band0(go), y0, x0, ty, tx)
    rf, rt = boot(r[flat]), boot(r[tex])
    if not quiet:
        print("  %-48s FLAT r %+.4f [%+.4f,%+.4f] r2 %.4f | DETAIL r %+.4f [%+.4f,%+.4f] r2 %.4f"
              % (tag, rf[0], rf[1], rf[2], max(rf[0], 0) ** 2,
                 rt[0], rt[1], rt[2], max(rt[0], 0) ** 2))
    return rf, rt


def permute_tiles(a, y0, x0, ty, tx, rng):
    out = a.copy()
    for iy in range(ty):
        for ix in range(tx):
            s = (slice(y0 + iy * bm.TILE, y0 + (iy + 1) * bm.TILE),
                 slice(x0 + ix * bm.TILE, x0 + (ix + 1) * bm.TILE))
            blk = out[s]
            out[s] = rng.permutation(blk.ravel()).reshape(blk.shape)
    return out


def commission(pe, po, pct=10.0):
    print("COMMISSIONING v2: split-half band-0 reproducibility, on real pixels")
    ge, cme, cfe = ns.load64(pe)
    go, cmo, cfo = ns.load64(po)
    print("  clip: EVEN %.4f%%  ODD %.4f%%" % (100 * cfe, 100 * cfo))
    flat, tex = masks(ge, go, cme | cmo, pct)          # frozen for every arm
    y0, x0, ty, tx = geom(ge.shape)
    rng = np.random.default_rng(11)
    print("  tile class computed ONCE on the clean pair and frozen (%d flat / %d detail)"
          % (int(flat.sum()), int(tex.sum())))

    b0 = band0(ge)
    loc = np.sqrt(np.mean(tiles_of(b0, y0, x0, ty, tx)[flat] ** 2))
    print("  planted noise is sized in the FLAT SITES' own band-0 units (rms %.3f DN)" % loc)

    base_f, base_t = score(ge, go, flat, tex, "BASELINE clean pair (the number under test)")
    rows = []
    rf, rt = score(ge, ge, flat, tex, "POSITIVE identical -> r must be +1.0000")
    rows.append(("identical", rf[0] > 0.999 and rt[0] > 0.999))
    rf, rt = score(ge, permute_tiles(go, y0, x0, ty, tx, rng), flat, tex,
                   "NEGATIVE within-tile permutation -> r ~ 0 in BOTH classes")
    rows.append(("permuted", abs(rf[0]) < 0.05 and abs(rt[0]) < 0.05))
    rf, rt = score(ge + rng.normal(0, 3 * loc, ge.shape),
                   go + rng.normal(0, 3 * loc, go.shape), flat, tex,
                   "DEFECT   independent noise 3x flat band0 -> FLAT r must FALL")
    rows.append(("indep noise", rf[2] < base_f[0]))
    shared = rng.normal(0, 3 * loc, ge.shape)
    rf, rt = score(ge + shared, go + shared, flat, tex,
                   "IMPROVE  SHARED texture 3x flat band0 -> FLAT r must RISE")
    rows.append(("shared texture", rf[1] > base_f[0]))
    ok = sum(1 for _, v in rows if v)
    print("\n  COMMISSIONED %d/%d arms (judged against the MEASURED baseline r=%+.4f)"
          % (ok, len(rows), base_f[0]))
    for n, v in rows:
        if not v:
            print("    NOT COMMISSIONED: %s" % n)
    return 0 if ok == len(rows) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", nargs=2)
    ap.add_argument("--even")
    ap.add_argument("--odd")
    ap.add_argument("--tile", type=int, default=128)
    ap.add_argument("--pct", type=float, default=25.0)
    a = ap.parse_args()
    bm.TILE = a.tile
    if a.commission:
        return commission(a.commission[0], a.commission[1], a.pct)
    ge, cme, cfe = ns.load64(a.even)
    go, cmo, cfo = ns.load64(a.odd)
    print("split-half band-0 reproducibility   clip EVEN %.4f%%  ODD %.4f%%"
          % (100 * cfe, 100 * cfo))
    for pct in (25, 10, 5):
        flat, tex = masks(ge, go, cme | cmo, pct)
        score(ge, go, flat, tex, "flattest / most-textured %g%% of tiles" % pct)
    return 0


if __name__ == "__main__":
    sys.exit(main())

