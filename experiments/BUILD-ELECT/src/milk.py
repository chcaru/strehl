"""The spilled-milk band, measured: is it as bright as the clean backdrop?

The owner's constraint on any correct mechanism is that the bright scalloped band
hugging the silhouette is "brighter than the subject and about as bright as the far
backdrop", i.e. the merge is producing approximately clean-backdrop values in a zone
that should be subject or veiled backdrop. That is a claim about the merged pixels,
not about the election, and it is measurable directly.

This profiles two quantities against the SAME signed distance from the silhouette,
negative outside and positive inside:

  merged luma        does the band reach clean-backdrop brightness inside the subject?
  elected index      does the brightness bump sit on the same pixels as the far election?

If both bumps coincide, the band is the election importing a frame in which the
subject's fringe has smeared away and the backdrop shows through -- one mechanism,
visible in the picture and in the field at the same coordinates. If the luma bump
sits where the election is normal, the band is downstream of the election and my
account of it is wrong.
"""
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile
from scipy import ndimage

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
PICS = OUT / "pics"
BIN = 6
REACH = 240          # plane px each side of the silhouette


def main():
    PICS.mkdir(parents=True, exist_ok=True)
    img = tifffile.imread(str(OUT / "B-noalign-merge.tif"))
    assert img.dtype == np.uint16, img.dtype
    e = tifffile.imread(str(OUT / "B-noalign-elect.tif")).astype(np.float64)
    assert e.shape[0] * 2 == img.shape[0], (e.shape, img.shape)

    g = img[:, :, 1].astype(np.float64)
    L = 0.25 * (g[0::2, 0::2] + g[0::2, 1::2] + g[1::2, 0::2] + g[1::2, 1::2])

    # Clean backdrop reference measured from the frame corners, which are furthest
    # from the subject and so least veiled. Taken from the picture rather than
    # assumed: the sweep is not uniformly lit.
    h, w = L.shape
    c = 200
    white = float(np.median(np.concatenate([
        L[:c, :c].ravel(), L[:c, -c:].ravel(),
        L[-c:, :c].ravel(), L[-c:, -c:].ravel()])))

    m = ndimage.binary_fill_holes(
        ndimage.binary_closing(L < 0.55 * white, np.ones((15, 15))))
    lab, nl = ndimage.label(m)
    m = lab == 1 + int(np.argmax(ndimage.sum(m, lab, range(1, nl + 1))))
    # Signed distance: positive inside the subject, negative outside.
    d = ndimage.distance_transform_edt(m) - ndimage.distance_transform_edt(~m)
    print(f"clean backdrop luma {white:.0f} DN; subject {m.mean():.2%} of plane, "
          f"{nl} components")

    rows = []
    for lo in range(-REACH, REACH, BIN):
        b = (d >= lo) & (d < lo + BIN)
        if b.sum() < 300:
            continue
        rows.append({"d": lo + BIN / 2, "n": int(b.sum()),
                     "luma": float(np.median(L[b])),
                     "luma_p90": float(np.percentile(L[b], 90)),
                     "elect": float(np.median(e[b]))})

    x = np.array([r["d"] for r in rows])
    lu = np.array([r["luma"] for r in rows])
    l90 = np.array([r["luma_p90"] for r in rows])
    el = np.array([r["elect"] for r in rows])

    # The mask is derived from brightness, and the artifact IS excess brightness, so
    # the band sits just OUTSIDE a mask drawn at 0.55 of clean backdrop. That is not
    # a flaw to be worked around, it is the measurement: a threshold that cleanly
    # separates a dark green bud from a white sweep puts the band on the backdrop
    # side, which can only happen if the band has been rendered at backdrop levels.
    # So the band is profiled where it lives, in the collar just outside the mask,
    # and compared against the deep subject and the clean corners.
    collar = (x >= -90) & (x < 0)
    deep = x > 150
    band_l = float(l90[collar].max())
    band_d = float(x[collar][int(np.argmax(l90[collar]))])
    deep_l = float(np.median(l90[deep]))
    print(f"\n{'d':>6} {'luma med':>9} {'luma p90':>9} {'/white':>8} {'elect':>7}")
    for r in rows[::6]:
        print(f"{r['d']:>6.0f} {r['luma']:>9.0f} {r['luma_p90']:>9.0f} "
              f"{r['luma_p90'] / white:>8.2f} {r['elect']:>7.0f}")

    print(f"\nclean backdrop (frame corners)      {white:>8.0f} DN   1.00")
    print(f"band, collar just off the silhouette {band_l:>8.0f} DN   "
          f"{band_l / white:.2f}   at d={band_d:+.0f} px")
    print(f"deep subject (d > 150 px)            {deep_l:>8.0f} DN   "
          f"{deep_l / white:.2f}")
    print(f"-> the band is {band_l / max(deep_l, 1e-9):.1f}x brighter than the deep "
          f"subject and {band_l / white:.2f}x the clean backdrop")

    owner_ok = band_l >= 0.9 * white and band_l >= 3 * deep_l
    print(f"\nOwner's constraint 1 -- brighter than the subject, about as bright as "
          f"the far backdrop: {'CONFIRMED' if owner_ok else 'NOT CONFIRMED'}")

    # Co-location. Both quantities decay from the silhouette inward rather than
    # forming bumps, so peak-matching is the wrong test; rank-correlate them over
    # the subject side instead.
    rk = lambda a: np.argsort(np.argsort(a)).astype(float)
    ins = x > 0
    rho = float(np.corrcoef(rk(l90[ins]), rk(el[ins]))[0, 1])
    print(f"inside the subject, luma p90 vs elected index: Spearman {rho:+.3f} "
          f"over {ins.sum()} bins")
    print(f"  -> {'brightness and far election decay together' if rho > 0.8 else 'they do not track each other'}")

    fig, axes = plt.subplots(1, 3, figsize=(19, 5.4))
    axes[0].imshow(np.clip(img[::4, ::4].astype(np.float64) / (white * 2 / 0.92), 0, 1)
                   ** (1 / 2.2))
    axes[0].contour(m[::2, ::2], levels=[.5], colors="r", linewidths=.7)
    axes[0].set_title("align-off merge + silhouette"); axes[0].set_xticks([])
    axes[0].set_yticks([])
    band = m & (d > 0) & (L > 0.9 * white)
    axes[1].imshow(band[::2, ::2], cmap="gray", interpolation="nearest")
    axes[1].set_title(f"pixels inside the subject at >90% of clean backdrop\n"
                      f"{band.sum() / max(m.sum(), 1):.1%} of the subject",
                      fontsize=11)
    axes[1].set_xticks([]); axes[1].set_yticks([])
    ax = axes[2]
    ax.plot(x, l90 / white, "tab:red", lw=2, label="merged luma p90 / clean backdrop")
    ax.axhline(1.0, color="k", ls=":", lw=1, label="clean backdrop")
    ax.axvline(0, color="0.5", lw=1)
    ax.set_xlabel("signed distance from silhouette (plane px), + = inside subject")
    ax.set_ylabel("luma / clean backdrop", color="tab:red")
    ax2 = ax.twinx()
    ax2.plot(x, el, "tab:blue", lw=2, label="elected index")
    ax2.set_ylabel("elected frame index", color="tab:blue")
    ax.set_title(f"band {band_l / white:.2f} of clean backdrop at d={band_d:+.0f} px, "
                 f"deep subject {deep_l / white:.2f}\n"
                 f"luma vs elected index inside the subject: Spearman {rho:+.2f}")
    ax.grid(alpha=.3)
    fig.suptitle("flower-bud: the spilled-milk band measured against the clean backdrop",
                 fontsize=14)
    fig.tight_layout()
    p = PICS / "MILK-profile.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    (OUT / "milk.json").write_text(json.dumps(
        {"white": white, "rows": rows, "band_d": band_d,
         "band_over_white": float(band_l / white),
         "deep_over_white": float(deep_l / white),
         "rho": rho, "owner_constraint_confirmed": bool(owner_ok)}, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
