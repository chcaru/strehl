"""Locate the d~275 px profile feature in the frame, so it can be looked at.

Section 15.9 left one number for the owner to adjudicate: the blend's largest
surviving local maximum in the radial backdrop profile, +1.24% of far field at
d = 275 px.  He has adjudicated it by publishing both readings, and asked for
the subject, the master path and a crop box so he can open it at 1:1 himself.

A radial profile is an azimuthal average.  A 1.24% feature in the average is
either a weak ring all the way round or a strong arc somewhere, and those need
completely different crop boxes.  This finds out which, by cutting the frame
into sectors about the subject centroid and running the same peak-and-outward-
trough prominence measure inside each sector separately.

The whole sector table is printed above any recommendation, because a sector
with too few pixels and a sector with no feature produce the same row otherwise.

    python peaksite.py <blend.tif> --mask-from <control.tif> [--out <png>]

SIGN CONVENTION, which has already misled one reader: `ringprofile.signed_
distance` returns d_out - d_in, so **positive d is OUTWARD, into the backdrop**.
`ring()` says "interior local maximum" meaning interior to the profile array --
not an endpoint -- NOT inside the silhouette.  d = +275 px is 275 px out into
the backdrop.
"""

import pathlib
import sys

import numpy as np

import ringprofile as rp

TARGET = 275.0          # the feature to localise, px outward
LO, HI = 150, 500       # radial window the sector profiles cover
NULL_LO, NULL_HI = 700, 1050    # a window with no silhouette feature expected
STEP = 5                # radial bin, px
NSECT = 24              # 15 degrees each
MIN_PX = 400


def sector_profile(lum, signed, sect, s, lo, hi):
    ds, vals = [], []
    for d in range(lo, hi, STEP):
        m = (signed >= d) & (signed < d + STEP) & (sect == s)
        n = int(m.sum())
        if n < MIN_PX:
            continue
        ds.append(d + 0.5 * STEP)
        vals.append(float(np.median(lum[m])))
    return np.array(ds), np.array(vals)


def prominence_near(ds, vals, target, ref):
    """Prominence over the OUTWARD trough of the local max nearest `target`."""
    best = None
    for i in range(1, len(vals) - 1):
        if vals[i] >= vals[i - 1] and vals[i] > vals[i + 1]:
            trough = float(vals[i + 1:].min())
            cand = (abs(ds[i] - target), float(ds[i]),
                    100.0 * (vals[i] - trough) / ref)
            if best is None or cand[0] < best[0]:
                best = cand
    return best


def main():
    argv = sys.argv[1:]
    out, mask_src = "peaksite.png", None
    for flag in ("--out", "--mask-from"):
        if flag in argv:
            i = argv.index(flag)
            if flag == "--out":
                out = argv[i + 1]
            else:
                mask_src = argv[i + 1]
            del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1 or mask_src is None:
        print(__doc__)
        return 2

    path = args[0]
    lum = rp.load_luma(path)
    mask, thr, kept, found = rp.subject_mask(rp.load_luma(mask_src))
    signed = rp.signed_distance(mask)
    far = (signed > rp.FAR_LO) & (signed < rp.FAR_HI)
    ref = float(np.median(lum[far]))

    cy, cx = [float(v) for v in np.argwhere(mask).mean(axis=0)]
    yy, xx = np.mgrid[0:lum.shape[0], 0:lum.shape[1]]
    ang = np.degrees(np.arctan2(yy - cy, xx - cx)) % 360.0
    sect = (ang / (360.0 / NSECT)).astype(np.int32)

    print(f"subject file : {pathlib.Path(path).name}")
    print(f"mask from    : {pathlib.Path(mask_src).name}")
    print(f"  frame {lum.shape[1]} x {lum.shape[0]}, "
          f"mask {mask.mean() * 100:.2f}% of frame, "
          f"{kept} component kept of {found} found")
    print(f"  subject centroid (x={cx:.0f}, y={cy:.0f})")
    print(f"  far field {rp.FAR_LO}-{rp.FAR_HI} px = {ref:.0f} DN")
    print(f"  POSITIVE d IS OUTWARD, into the backdrop.")
    print()

    print(f"  prominence of the local maximum nearest d={TARGET:.0f} px, "
          f"per {360 // NSECT}-degree sector, over its own outward trough")
    print(f"  {'sector':>7} {'deg':>9} {'bins':>6} {'d at pk':>9} "
          f"{'prom %':>8} {'peak DN':>9}")
    rows = []
    for s in range(NSECT):
        ds, vals = sector_profile(lum, signed, sect, s, LO, HI)
        deg = f"{s * 360 // NSECT}-{(s + 1) * 360 // NSECT}"
        if len(vals) < 4:
            print(f"  {s:>7} {deg:>9} {len(vals):>6} {'--':>9} {'--':>8} "
                  f"{'too few':>9}")
            continue
        got = prominence_near(ds, vals, TARGET, ref)
        if got is None:
            print(f"  {s:>7} {deg:>9} {len(vals):>6} {'none':>9} "
                  f"{'0.00':>8} {'monotone':>9}")
            rows.append((s, None, 0.0))
            continue
        _, d_pk, prom = got
        pk_dn = float(vals[int(np.argmin(np.abs(ds - d_pk)))])
        print(f"  {s:>7} {deg:>9} {len(vals):>6} {d_pk:>9.1f} "
              f"{prom:>8.2f} {pk_dn:>9.0f}")
        rows.append((s, d_pk, prom))
    print()

    # --- THE NULL --------------------------------------------------------
    # The same machinery, same bin width, same sectors, same prominence rule,
    # on a radial window where no silhouette-related feature is expected. If it
    # returns the same prominence there, the signal window's number is the noise
    # floor of a peak-picker running on 5 px medians and means nothing.
    null_mid = 0.5 * (NULL_LO + NULL_HI)
    null_rows = []
    print(f"  NULL: identical statistic on d={NULL_LO}-{NULL_HI} px, where no "
          f"silhouette feature is expected. Target d={null_mid:.0f}.")
    print(f"  {'sector':>7} {'bins':>6} {'d at pk':>9} {'prom %':>8}")
    for s in range(NSECT):
        ds, vals = sector_profile(lum, signed, sect, s, NULL_LO, NULL_HI)
        if len(vals) < 4:
            print(f"  {s:>7} {len(vals):>6} {'--':>9} {'too few':>8}")
            continue
        got = prominence_near(ds, vals, null_mid, ref)
        if got is None:
            print(f"  {s:>7} {len(vals):>6} {'none':>9} {'0.00':>8}")
            null_rows.append(0.0)
            continue
        _, d_pk, prom = got
        print(f"  {s:>7} {len(vals):>6} {d_pk:>9.1f} {prom:>8.2f}")
        null_rows.append(prom)
    print()

    have = [r for r in rows if r[1] is not None]
    if not have:
        print("  NO sector carries a local maximum near the target at all.")
        return 0
    proms = np.array([r[2] for r in have])
    nulls = np.array(null_rows) if null_rows else np.array([0.0])
    print(f"  sectors with a peak near d={TARGET:.0f}: {len(have)} of {NSECT}")
    print(f"  SIGNAL window {LO}-{HI}: min {proms.min():.2f}%, "
          f"median {np.median(proms):.2f}%, max {proms.max():.2f}%")
    print(f"  NULL   window {NULL_LO}-{NULL_HI}: min {nulls.min():.2f}%, "
          f"median {np.median(nulls):.2f}%, max {nulls.max():.2f}%, "
          f"p90 {np.percentile(nulls, 90):.2f}%")
    print(f"  SIGNAL median / NULL median = "
          f"{np.median(proms) / max(np.median(nulls), 1e-9):.1f}x")
    print(f"  sectors whose signal exceeds the NULL's p90: "
          f"{int((proms > np.percentile(nulls, 90)).sum())} of {len(have)}")
    print(f"  A statistic that returns the same value in both windows is "
          f"measuring its own noise floor, not a feature.")
    print(f"  ARC vs RING: max/median = "
          f"{proms.max() / max(np.median(proms), 1e-9):.1f}x. Near 1 is a ring "
          f"and any sector will do; large is an arc and only the top sectors "
          f"are worth opening.")
    print()

    have.sort(key=lambda r: -r[2])
    print("  crop boxes for the strongest sectors, as (x, y, w, h), clipped to "
          "frame. Each is centred on the sector's mid-angle at its own peak "
          "radius and is 1200 x 900.")
    boxes = []
    for s, d_pk, prom in have[:4]:
        mid = np.radians((s + 0.5) * 360.0 / NSECT)
        # walk outward from the mask edge along the sector's mid-angle
        px = cx + (d_pk + _edge_radius(mask, cx, cy, mid)) * np.cos(mid)
        py = cy + (d_pk + _edge_radius(mask, cx, cy, mid)) * np.sin(mid)
        w, h = 1200, 900
        x0 = int(np.clip(px - w / 2, 0, lum.shape[1] - w))
        y0 = int(np.clip(py - h / 2, 0, lum.shape[0] - h))
        boxes.append((s, prom, d_pk, x0, y0, w, h, int(px), int(py)))
        print(f"    sector {s:>2} ({s * 360 // NSECT}-{(s + 1) * 360 // NSECT} deg)"
              f"  prom {prom:>5.2f}%  d={d_pk:>5.1f}  "
              f"centre (x={int(px)}, y={int(py)})  "
              f"crop ({x0}, {y0}, {w}, {h})")
    print()

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                # pragma: no cover
        print(f"  no picture: {exc}")
        return 0

    fig, ax = plt.subplots(2, 3, figsize=(16.5, 9.5))
    band = (signed >= TARGET - 15) & (signed <= TARGET + 15)
    small = lum[::6, ::6]
    v0, v1 = np.percentile(small, [1, 99])
    ax[0, 0].imshow(small, cmap="gray", vmin=v0, vmax=v1)
    ax[0, 0].set_title(f"{pathlib.Path(path).name}\nwhole frame, 1/6", fontsize=9)
    ax[0, 1].imshow(band[::6, ::6], cmap="gray")
    ax[0, 1].set_title(f"the d={TARGET:.0f}+-15 px annulus\n"
                       f"positive d is OUTWARD", fontsize=9)
    for s, prom, d_pk, x0, y0, w, h, px, py in boxes:
        ax[0, 0].add_patch(plt.Rectangle((x0 / 6, y0 / 6), w / 6, h / 6,
                                         fill=False, ec="red", lw=1.4))
        ax[0, 0].text(x0 / 6, y0 / 6 - 6, f"s{s} {prom:.2f}%",
                      color="red", fontsize=7)
    ax[0, 2].bar([r[0] for r in rows if r[1] is not None],
                 [r[2] for r in rows if r[1] is not None])
    ax[0, 2].set_title(f"prominence near d={TARGET:.0f} by sector\n"
                       f"flat = ring, spiky = arc", fontsize=9)
    ax[0, 2].set_xlabel("sector")
    ax[0, 2].set_ylabel("% of far field")
    for j, (s, prom, d_pk, x0, y0, w, h, px, py) in enumerate(boxes[:3]):
        c = lum[y0:y0 + h, x0:x0 + w]
        c0, c1 = np.percentile(c, [1, 99])
        ax[1, j].imshow(c, cmap="gray", vmin=c0, vmax=c1)
        ax[1, j].set_title(f"sector {s}, prom {prom:.2f}% at d={d_pk:.0f}\n"
                           f"crop ({x0}, {y0}, {w}, {h})", fontsize=9)
    for a_ in list(ax[0]) + list(ax[1]):
        a_.set_xticks([])
        a_.set_yticks([])
    ax[0, 2].set_xticks(range(0, NSECT, 4))
    fig.suptitle(f"Where the d={TARGET:.0f} px feature lives. "
                 f"Crops are stretched to their own 1-99 percentile, so they "
                 f"EXAGGERATE; the master must be judged at 1:1.", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"  wrote {out}")
    return 0


def _edge_radius(mask, cx, cy, ang, step=4.0, lim=4000.0):
    """Distance from the centroid to the mask boundary along `ang`."""
    r = 0.0
    h, w = mask.shape
    while r < lim:
        x, y = int(cx + r * np.cos(ang)), int(cy + r * np.sin(ang))
        if not (0 <= x < w and 0 <= y < h) or not mask[y, x]:
            return r
        r += step
    return r


if __name__ == "__main__":
    sys.exit(main())
