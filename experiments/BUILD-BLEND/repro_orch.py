"""Independent reproduction of ORCH's clamp findings 1 and 2, on BOTH builds.

ORCH asked for reproduction before anything else, and warned that a failure to
reproduce means one of us has a broken instrument. There is a third
possibility their protocol cannot see: we are measuring different BINARIES.
ORCH renders from pin tree-lin-0d9fd28; my sweep renders from HEAD and reads
0.0000% clip on the same subject with the same flags.

So this runs the same two measurements over both sets of TIFFs. If the pin
reproduces 1.4015% and HEAD reads 0.0000%, both of us are right and the defect
was fixed between the two commits.

Written from ORCH's PROSE description, not from their code, so a shared bug
cannot reproduce itself:

  finding 1  black-rail and white-rail clip%, split into the lit population
             (green above its own 20th percentile) and the dark population.
  finding 2  128px tiles restricted to >=90% lit; amplitude proxy is the RMS
             of the 3x3 Laplacian; report blend/ctrl for tiles containing any
             clipped pixel against clip-free tiles.

NULL CONTROL: every pair is preceded by a ref-vs-ref comparison which must
return exactly 1.000000 amplitude ratio. A ratio instrument that cannot return
exactly 1 on identical input has no business reporting 0.4495.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile

TILE = 128
BLACK, WHITE = 0, 65535


def laplacian(g):
    p = np.pad(g, 1, mode="edge")
    return p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] - 4.0 * p[1:-1, 1:-1]


def rails(im):
    """Per-pixel masks: any channel at the black rail / at the white rail."""
    return (im == BLACK).any(axis=2), (im == WHITE).any(axis=2)


def tile_rms(a, t=TILE):
    h, w = a.shape
    nh, nw = h // t, w // t
    v = a[: nh * t, : nw * t].reshape(nh, t, nw, t)
    return np.sqrt((v ** 2).mean(axis=(1, 3)))


def tile_frac(m, t=TILE):
    h, w = m.shape
    nh, nw = h // t, w // t
    return m[: nh * t, : nw * t].reshape(nh, t, nw, t).mean(axis=(1, 3))


def report(tag, ctrl_p, blend_p):
    ctrl = tifffile.imread(str(ctrl_p))
    blend = tifffile.imread(str(blend_p))
    if ctrl.shape != blend.shape:
        raise SystemExit(f"{tag}: SHAPE MISMATCH {ctrl.shape} vs {blend.shape}")
    # The binning trap ORCH flagged: full res is 4688x7040. A binned arm would
    # silently make every gradient statistic meaningless.
    if ctrl.shape[0] < 4000:
        raise SystemExit(f"{tag}: shape {ctrl.shape} looks BINNED, refusing to measure")

    print(f"\n{'='*72}\n{tag}\n  ctrl  {ctrl_p.name}\n  blend {blend_p.name}\n  shape {ctrl.shape}")

    cg = ctrl[..., 1].astype(np.float64)
    bg = blend[..., 1].astype(np.float64)

    # --- NULL CONTROL, before any real number is read ---
    cl = tile_rms(np.abs(laplacian(cg)))
    null = float(np.sqrt((cl ** 2).sum() / (cl ** 2).sum()))
    print(f"  null control (ctrl vs itself, must be exactly 1.000000): {null:.6f}")
    if null != 1.0:
        raise SystemExit("null control failed; instrument is not trustworthy")

    # --- finding 1: rails x population ---
    print(f"  {'arm':<8}{'black%':>10}{'white%':>10}{'blk lit%':>11}{'blk dark%':>11}")
    for name, im, g in (("ctrl", ctrl, cg), ("blend", blend, bg)):
        blk, wht = rails(im)
        lit = g > np.percentile(g, 20.0)
        n = g.size
        print(
            f"  {name:<8}{blk.mean()*100:10.4f}{wht.mean()*100:10.4f}"
            f"{(blk & lit).sum()/n*100:11.4f}{(blk & ~lit).sum()/n*100:11.4f}"
        )

    # --- finding 2: amplitude in clipped vs clip-free tiles, >=90% lit ---
    blk_b, _ = rails(blend)
    lit_c = cg > np.percentile(cg, 20.0)
    t_lit = tile_frac(lit_c)
    t_clip = tile_frac(blk_b) > 0
    ca = tile_rms(np.abs(laplacian(cg)))
    ba = tile_rms(np.abs(laplacian(bg)))

    sel = t_lit >= 0.90
    print(f"  {'group':<20}{'nTiles':>8}{'ampRatio':>11}{'refAmp':>10}")
    for gname, m in (("clip-free", sel & ~t_clip), ("any clipped pixel", sel & t_clip)):
        n = int(m.sum())
        if n == 0:
            print(f"  {gname:<20}{n:>8}{'--':>11}{'--':>10}")
            continue
        r = float(np.sqrt((ba[m] ** 2).sum() / (ca[m] ** 2).sum()))
        print(f"  {gname:<20}{n:>8}{r:11.4f}{float(ca[m].mean()):10.1f}")


def main():
    pin = Path(r"C:\dev\strehl-out\ORCH-CLAMP\clean")
    head = Path(r"C:\dev\strehl-out\BUILD-BLEND\hullfrom")
    for subj in ("flower-bud-alone-cpl", "couch-fibers-cpl"):
        c, b = pin / f"{subj}--ctrl.tiff", pin / f"{subj}--blend.tiff"
        if c.exists() and b.exists():
            report(f"PIN tree-lin-0d9fd28  {subj}", c, b)
    c = pin / "flower-bud-alone-cpl--ctrl.tiff"
    for arm in ("ref", "noca"):
        b = head / f"flower-bud-alone-cpl--{arm}.tiff"
        if c.exists() and b.exists():
            report(f"HEAD build 8F8DECAE  flower-bud-alone-cpl  arm={arm}", c, b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
