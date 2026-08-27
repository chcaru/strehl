"""ROI selection for V-H2H2, as a COUNTED PARTITION.

Rule 9 needs a flat control and the project standard needs "counted outcomes
that sum to the total, so a skipped check cannot read as a passed one".  So
this does not "find some detail ROIs": it lays a non-overlapping grid over the
whole image, assigns EVERY cell to exactly one outcome, and prints the census.

    total = margin + clipped + flat + mid + detail

`clipped` is exact, measured on the full-resolution u16 samples, because the
gamut map and the u16 ceiling are the two stages of the viewing render that are
not invertible.  A clipped ROI is dropped, never silently included.
"""
import numpy as np

import h2


def census(render, t=256, margin=64, pad=32, detail_frac=0.30, flat_frac=0.25,
           verbose=True):
    """Grid the image, classify every cell, return (detail, flat, counts).

    `pad` is the extra border every consumer needs to apply a filter without
    edge effects, so cells are placed so that [y0-pad, y0+t+pad) is in bounds.
    """
    h, w = render.h, render.w
    lo = margin + pad
    ys = list(range(lo, h - lo - t + 1, t))
    xs = list(range(lo, w - lo - t + 1, t))
    total_grid = (h // t) * (w // t)
    cells = [(y, x) for y in ys for x in xs]
    n_margin = total_grid - len(cells)

    step = 8
    g = render.coarse(step=step, chan=1)          # u16 green, strided
    energy = np.zeros(len(cells))
    level = np.zeros(len(cells))
    clipped = np.zeros(len(cells), bool)
    ts = t // step
    for i, (y, x) in enumerate(cells):
        blk = g[y // step:y // step + ts, x // step:x // step + ts]
        if blk.size == 0:
            clipped[i] = True
            continue
        level[i] = blk.mean()
        d = np.diff(blk, axis=0)
        e = np.diff(blk, axis=1)
        energy[i] = np.sqrt((d ** 2).mean() + (e ** 2).mean()) / max(blk.mean(), 1.0)

    # exact clip test at full resolution on the cells that survive the cheap one
    for i, (y, x) in enumerate(cells):
        if clipped[i]:
            continue
        blk = render.raw_crop(y - pad, x - pad, t + 2 * pad)
        if blk.max() >= 65535 or blk.min() == 0:
            clipped[i] = True

    ok = ~clipped
    e_ok = energy[ok]
    if e_ok.size == 0:
        raise RuntimeError("every ROI clipped")
    hi = np.quantile(e_ok, 1.0 - detail_frac)
    lo_q = np.quantile(e_ok, flat_frac)

    detail, flat, mid = [], [], []
    for i, (y, x) in enumerate(cells):
        if clipped[i]:
            continue
        if energy[i] >= hi:
            detail.append((y, x))
        elif energy[i] <= lo_q:
            flat.append((y, x))
        else:
            mid.append((y, x))

    counts = dict(total_grid=total_grid, margin=n_margin, considered=len(cells),
                  clipped=int(clipped.sum()), detail=len(detail),
                  flat=len(flat), mid=len(mid))
    assert counts["margin"] + counts["considered"] == counts["total_grid"]
    assert (counts["clipped"] + counts["detail"] + counts["flat"] + counts["mid"]
            == counts["considered"])
    if verbose:
        print(f"ROI census on {render.name} at {t}x{t} (+{pad} pad):")
        print(f"  grid cells in image        {counts['total_grid']}")
        print(f"  - dropped for margin/pad   {counts['margin']}")
        print(f"  = considered               {counts['considered']}")
        print(f"      clipped (u16 0 or max) {counts['clipped']}")
        print(f"      FLAT   (bottom {flat_frac:.0%})     {counts['flat']}")
        print(f"      mid                    {counts['mid']}")
        print(f"      DETAIL (top {detail_frac:.0%})       {counts['detail']}")
        assert (counts['clipped'] + counts['flat'] + counts['mid']
                + counts['detail'] == counts['considered'])
        if detail and flat:
            de = np.array([energy[cells.index(c)] for c in detail])
            fe = np.array([energy[cells.index(c)] for c in flat])
            print(f"  median local contrast: DETAIL {np.median(de):.4f}  "
                  f"FLAT {np.median(fe):.4f}  ratio {np.median(de)/max(np.median(fe),1e-9):.1f}x")
    return detail, flat, counts
