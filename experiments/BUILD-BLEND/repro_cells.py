"""ORCH's corrected clip cells + band table, on the pin AND on HEAD.

Two jobs.

1. REPRODUCE ORCH's corrected measurement. The correction that matters: the
   lit/dark partition is taken from the REFERENCE arm only. Taking it from the
   arm under test lets a clamp that drives lit pixels to black re-classify
   them as "dark", and the defect deletes itself from its own measurement.

2. TEST A REGISTERED PREDICTION. ORCH measures, on the pin, that excluding 3
   clipped tiles of 154 moves the sharpest quintile's low band from 0.7889 to
   0.9789 -- i.e. the clamp IS essentially the whole low-band deficit. I have
   already measured that HEAD clips zero pixels on this subject.

   PREDICTION, registered before running: if ORCH's attribution is right, then
   HEAD's ALL-tiles band row must land on the PIN's CLIP-FREE row (low ~0.98),
   because at HEAD every tile is a clip-free tile.

   FALSIFIER: if HEAD's low band stays near 0.79 while clipping zero pixels,
   the low-band deficit is NOT the clamp and ORCH's attribution fails.

   This is a real test. It costs no renders and it can come out either way.

Band edges are mine, not ORCH's -- they gave a 12-point f/Nyq curve but no cut
points -- so ABSOLUTE agreement with their band numbers is not expected. What
must reproduce is the STRUCTURE: a large low-band gap between all-tiles and
clip-free on the pin.
"""

import numpy as np
import tifffile
from pathlib import Path

TILE = 128
BANDS = (("low", 0.0, 1 / 3), ("MID", 1 / 3, 2 / 3), ("high", 2 / 3, 1.01))


def laplacian(g):
    p = np.pad(g, 1, mode="edge")
    return p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] - 4.0 * p[1:-1, 1:-1]


def tiles_of(a, t=TILE):
    h, w = a.shape
    nh, nw = h // t, w // t
    return a[: nh * t, : nw * t].reshape(nh, t, nw, t).transpose(0, 2, 1, 3)


def radial_mask():
    fy = np.fft.fftfreq(TILE)[:, None] * 2
    fx = np.fft.fftfreq(TILE)[None, :] * 2
    r = np.sqrt(fy ** 2 + fx ** 2)
    return [(n, (r > lo) & (r <= hi)) for n, lo, hi in BANDS]


def clip_cells(ref, test):
    """Four clip cells, lit/dark partition taken from the REFERENCE ONLY."""
    rg = ref[..., 1].astype(np.float64)
    lit = rg > np.percentile(rg, 20.0)
    out = {}
    for name, im in (("ref", ref), ("test", test)):
        blk = (im == 0).any(axis=2)
        wht = (im == 65535).any(axis=2)
        n = blk.size
        out[name] = {
            "black_lit": (blk & lit).sum() / n * 100,
            "black_dark": (blk & ~lit).sum() / n * 100,
            "white_lit": (wht & lit).sum() / n * 100,
            "white_dark": (wht & ~lit).sum() / n * 100,
        }
    return out


def band_table(ref, test, label):
    rg = ref[..., 1].astype(np.float64)
    tg = test[..., 1].astype(np.float64)
    lit = rg > np.percentile(rg, 20.0)
    blk_t = (test == 0).any(axis=2)

    lit_frac = tiles_of(lit.astype(np.float64)).mean(axis=(2, 3))
    amp = np.sqrt((tiles_of(np.abs(laplacian(rg))) ** 2).mean(axis=(2, 3)))
    dirty = tiles_of(blk_t.astype(np.float64)).sum(axis=(2, 3)) > 0

    sel = lit_frac >= 0.90
    if sel.sum() == 0:
        print(f"  {label}: no lit tiles"); return
    thr = np.percentile(amp[sel], 80.0)
    sharp = sel & (amp >= thr)

    rt, tt = tiles_of(rg), tiles_of(tg)
    masks = radial_mask()

    print(f"  {'group':<22}{'nTiles':>7}" + "".join(f"{n:>10}" for n, _, _ in BANDS))
    for gname, m in (("ALL sharp tiles", sharp), ("CLIP-FREE only", sharp & ~dirty)):
        idx = np.argwhere(m)
        if len(idx) == 0:
            print(f"  {gname:<22}{0:>7}"); continue
        pr = np.zeros(len(BANDS)); pt = np.zeros(len(BANDS))
        for i, j in idx:
            a = rt[i, j] - rt[i, j].mean()
            b = tt[i, j] - tt[i, j].mean()
            Pa = np.abs(np.fft.fft2(a)) ** 2
            Pb = np.abs(np.fft.fft2(b)) ** 2
            for k, (_, msk) in enumerate(masks):
                pr[k] += Pa[msk].sum(); pt[k] += Pb[msk].sum()
        row = "".join(f"{np.sqrt(pt[k] / pr[k]):>10.4f}" for k in range(len(BANDS)))
        print(f"  {gname:<22}{len(idx):>7}{row}")


def run(tag, ref_p, test_p):
    ref = tifffile.imread(str(ref_p)); test = tifffile.imread(str(test_p))
    print(f"\n{'='*70}\n{tag}\n  test = {test_p.name}")
    # NULL CONTROL: an arm against itself must give exactly 1.0 in every band.
    if tag.endswith("NULL"):
        band_table(ref, ref, "null"); return
    c = clip_cells(ref, test)
    print(f"  {'cell':<14}{'ref %':>9}{'test %':>9}{'rise':>10}")
    tot_r = tot_t = 0.0
    for k in ("black_lit", "black_dark", "white_lit", "white_dark"):
        r, t = c["ref"][k], c["test"][k]
        tot_r += r; tot_t += t
        print(f"  {k:<14}{r:9.4f}{t:9.4f}{t - r:+10.4f}")
    print(f"  {'TOTAL':<14}{tot_r:9.4f}{tot_t:9.4f}{tot_t - tot_r:+10.4f}")
    band_table(ref, test, tag)


def main():
    pin = Path(r"C:\dev\strehl-out\ORCH-CLAMP\clean")
    head = Path(r"C:\dev\strehl-out\BUILD-BLEND\hullfrom")
    fb = "flower-bud-alone-cpl"
    run(f"PIN  {fb}  NULL", pin / f"{fb}--ctrl.tiff", pin / f"{fb}--ctrl.tiff")
    run(f"PIN  {fb}", pin / f"{fb}--ctrl.tiff", pin / f"{fb}--blend.tiff")
    run("PIN  couch-fibers-cpl", pin / "couch-fibers-cpl--ctrl.tiff",
        pin / "couch-fibers-cpl--blend.tiff")
    for arm in ("ref", "noca"):
        p = head / f"{fb}--{arm}.tiff"
        if p.exists():
            run(f"HEAD {fb}  arm={arm}", pin / f"{fb}--ctrl.tiff", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
