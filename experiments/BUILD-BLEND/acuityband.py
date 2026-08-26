"""Is `accept.py`'s acuity deficit DETAIL or NOISE?

`acuitymap.py` measured the pyramid merge holding 1.1035 of the reference's
fine-band energy on couch-fibers-cpl, with 94.3% of tiles having MORE. Yet
`accept.py` reads acuity 0.898. Both cannot describe the same quantity, and
the commissioning check in `acuitymap.py` said so rather than letting the
flattering number stand.

The difference is the BAND, and it is not subtle:

  accept.py   mean |Laplacian(3x3)| over lit pixels.  Peaks at NYQUIST.
  acuitymap   RMS of (I - box_blur(I, r=2)).          Peaks around 2-4 px.

So the pyramid merge has MORE 2-4 px structure and LESS Nyquist-band content.
That is a coherent physical picture rather than a contradiction, and it has a
mundane candidate explanation:

  The legacy path is a per-pixel GATHER. It copies pixels from elected frames,
  so it carries each frame's full per-pixel noise, plus a hard step wherever
  the election changes. Both live at Nyquist.

  The pyramid merge combines BANDS across frames. At every level that is an
  average over frames, which suppresses independent noise by ~sqrt(N).

If that is what is happening, `accept.py`'s acuity is partly a NOISE meter,
and a merge is being penalised for denoising. Its docstring anticipates the
concern -- "measured away from the shadows so it reports subject detail rather
than noise in the black" -- but noise is not confined to the shadows.

THE TEST. Split the frame by whether it contains structure at all, using a
scale far coarser than either statistic so the split cannot be circular:

  FLAT tiles  -- low coarse-scale variance. Contains no real detail. Any
                 Nyquist-band energy here is noise, near enough.
  BUSY tiles  -- high coarse-scale variance. Real subject texture.

  If ctrl >> blend on FLAT tiles  -> acuity is counting noise.
  If ctrl >> blend on BUSY tiles  -> the deficit is real lost detail.

The falsifying outcome is a deficit concentrated on BUSY tiles: that would
mean the pyramid merge genuinely loses subject texture at Nyquist, `accept.py`
is right, and this whole line of argument is special pleading.

Usage:  python acuityband.py <CTRL.tiff> <BLEND.tiff>
"""

import sys

import numpy as np
import tifffile

from acuitymap import box_blur, tile_sum

TILE = 128


def laplacian(g):
    """3x3 Laplacian, matching accept.py's operator (edge-replicated)."""
    p = np.pad(g, 1, mode="edge")
    return (
        p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] - 4.0 * p[1:-1, 1:-1]
    )


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    ctrl = tifffile.imread(sys.argv[1])
    blend = tifffile.imread(sys.argv[2])
    if ctrl.shape != blend.shape:
        raise SystemExit(f"SHAPE MISMATCH {ctrl.shape} vs {blend.shape}")

    cg = ctrl[..., 1].astype(np.float64)
    bg = blend[..., 1].astype(np.float64)

    # COMMISSIONING: reproduce accept.py's number. Same operator, same lit
    # population (green above the 20th luminance percentile of that image).
    # If this does not land on 0.898 the rest of the script is describing some
    # other statistic and must not be read as a decomposition of the gate's.
    def acuity(g):
        lit = g > np.percentile(g, 20.0)
        return float(np.abs(laplacian(g))[lit].mean())

    ca, ba = acuity(cg), acuity(bg)
    print(f"accept.py-style acuity   ctrl {ca:8.2f}   blend {ba:8.2f}   ratio {ba/ca:.4f}")
    print("  (commissioning: must reproduce the gate's ~0.898, or this is not")
    print("   a decomposition of the gate's number and proves nothing about it)\n")

    # Structure classifier at a scale far coarser than EITHER statistic under
    # test, so the split cannot be circular: a 16 px blur knows nothing about
    # Nyquist or about 2 px.
    coarse = box_blur(cg, 16)
    struct = tile_sum((coarse - box_blur(coarse, 16)) ** 2, TILE)
    lo, hi = np.percentile(struct, 25), np.percentile(struct, 75)
    flat = struct <= lo
    busy = struct >= hi

    cl = tile_sum(np.abs(laplacian(cg)), TILE)
    bl = tile_sum(np.abs(laplacian(bg)), TILE)

    print(f"tiles {struct.size}   flat {flat.sum()}   busy {busy.sum()}   (coarse-structure quartiles)\n")
    print(f"{'population':<12}{'ctrl |Lap|':>14}{'blend |Lap|':>14}{'ratio':>10}")
    rows = []
    for name, m in (("FLAT", flat), ("BUSY", busy), ("all", np.ones_like(flat, bool))):
        c, b = cl[m].sum(), bl[m].sum()
        rows.append((name, b / c))
        print(f"{name:<12}{c:14.4e}{b:14.4e}{b/c:10.4f}")

    r_flat = dict(rows)["FLAT"]
    r_busy = dict(rows)["BUSY"]
    print("\nVERDICT")
    if r_flat < r_busy - 0.03:
        print(f"  The deficit is concentrated on FLAT tiles ({r_flat:.4f}) and is")
        print(f"  much milder on BUSY tiles ({r_busy:.4f}). Flat tiles contain no")
        print("  detail to lose, so the energy the pyramid merge is 'missing'")
        print("  there is NOISE. accept.py's acuity is partly a noise meter and")
        print("  is penalising the merge for averaging noise away.")
    elif r_busy < r_flat - 0.03:
        print(f"  The deficit is concentrated on BUSY tiles ({r_busy:.4f}) while")
        print(f"  flat tiles hold up ({r_flat:.4f}). This is REAL LOST TEXTURE.")
        print("  accept.py is right, the pyramid merge is genuinely softer at")
        print("  Nyquist on subject detail, and this must be fixed not argued.")
    else:
        print(f"  FLAT {r_flat:.4f} and BUSY {r_busy:.4f} agree. The deficit is")
        print("  band-limited but not structure-selective; neither story holds.")

    # A noise estimate that does not depend on the classifier at all, as a
    # cross-check: the per-tile MINIMUM of |Lap| over the frame is close to a
    # pure noise floor wherever any tile is genuinely featureless.
    n = max(1, int(0.02 * cl.size))
    cq = np.sort(cl.ravel())[:n].mean()
    bq = np.sort(bl.ravel())[:n].mean()
    print(f"\nquietest 2% of tiles (independent noise-floor proxy):")
    print(f"  ctrl {cq:.4e}   blend {bq:.4e}   ratio {bq/cq:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
