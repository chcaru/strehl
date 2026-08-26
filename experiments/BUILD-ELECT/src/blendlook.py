"""Look at the blend arm: full frames, 1:1 linear crops, and do-no-harm in DN.

The owner's standing rule is that this project has shipped defects that were
obvious in three seconds of looking at a full frame while scalar metrics said
fine. So: full frames first, then 1:1 crops at the place the two arms actually
differ most (an argmax of the real difference, not a guessed threshold), then
the do-no-harm number.

Everything is linear 16-bit. Nothing here is measured on an sRGB or JPEG file.
Levels are reported in absolute DN as well as ratios, because an additive bias
is invisible in both an error and a ratio.
"""
import json
import pathlib
import sys
import numpy as np
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\pics")
B = pathlib.Path(r"C:\dev\strehl-out\BUILD-BLEND")
HALF = 160          # 1:1 crop is 320 px across, shown at 1:1


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a.astype(np.float32)


def luma(a):
    return a.mean(axis=2) if a.ndim == 3 else a


def show(ax, a, lo, hi, title):
    """Display stretch only. Never used for measurement."""
    v = np.clip((luma(a) - lo) / max(hi - lo, 1e-6), 0, 1) ** (1 / 2.2)
    ax.imshow(v, cmap="gray")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=9)


def worst_diff_centre(ca, ba, margin=400):
    """Where do the two arms disagree most? An argmax of the actual difference,
    scale-matched first so a global gain difference cannot dominate it."""
    c, b = luma(ca), luma(ba)
    g = float(np.median(b[b > 0]) / max(np.median(c[c > 0]), 1e-6))
    d = np.abs(b - c * g)
    d = ndimage.uniform_filter(d, 33)
    d[:margin] = d[-margin:] = 0
    d[:, :margin] = d[:, -margin:] = 0
    y, x = np.unravel_index(int(np.argmax(d)), d.shape)
    return int(y), int(x), g, float(d.max())


def gradient_energy(a):
    l = luma(a)
    gx = ndimage.sobel(l, axis=1) * 0.125
    gy = ndimage.sobel(l, axis=0) * 0.125
    return np.hypot(gx, gy)


def pair(name, ctrl, blend, fig_path, subject_hint=None):
    ca, ba = load(ctrl), load(blend)
    assert ca.shape == ba.shape, f"{ctrl} {ca.shape} vs {blend} {ba.shape}"
    y, x, gain, dmax = worst_diff_centre(ca, ba)
    print(f"\n{'=' * 74}\n{name}")
    print(f"  ctrl  {pathlib.Path(ctrl).name}")
    print(f"  blend {pathlib.Path(blend).name}   shape {ca.shape}")
    print(f"  median level   ctrl {np.median(luma(ca)):9.0f} DN"
          f"   blend {np.median(luma(ba)):9.0f} DN"
          f"   ratio {gain:.4f}")
    print(f"  largest local disagreement at (y={y}, x={x}), "
          f"{dmax:.0f} DN over a 33 px window")

    ge_c, ge_b = gradient_energy(ca), gradient_energy(ba)
    # Compare on the structured part of the frame only: the top decile of the
    # control's own gradient. Comparing over the whole frame lets a smooth
    # backdrop dominate and hides softening of real detail.
    hi = ge_c > np.percentile(ge_c, 90)
    mc, mb = float(ge_c[hi].mean()), float(ge_b[hi].mean() / gain)
    print(f"  gradient energy on the control's top-decile edges:")
    print(f"    ctrl  {mc:8.1f} DN/px    blend {mb:8.1f} DN/px (gain-corrected)"
          f"    ratio {mb / mc:.4f}")
    print(f"    -> blend is {'SHARPER' if mb > mc else 'SOFTER'} by "
          f"{abs(mb - mc):.1f} DN/px = {abs(mb / mc - 1) * 100:.1f}%")

    sl = (slice(max(y - HALF, 0), y + HALF), slice(max(x - HALF, 0), x + HALF))
    lo = float(np.percentile(luma(ca), 1))
    hi_c = float(np.percentile(luma(ca), 99.5))
    hi_b = hi_c * gain
    fig, ax = plt.subplots(2, 3, figsize=(16.5, 9.4))
    show(ax[0][0], ca, lo, hi_c, f"CONTROL full frame\nmedian {np.median(luma(ca)):.0f} DN")
    show(ax[0][1], ba, lo * gain, hi_b, f"BLEND full frame\nmedian {np.median(luma(ba)):.0f} DN")
    dv = np.abs(luma(ba) - luma(ca) * gain)
    ax[0][2].imshow(np.clip(dv / np.percentile(dv, 99.9), 0, 1), cmap="inferno")
    ax[0][2].set_xticks([]); ax[0][2].set_yticks([])
    ax[0][2].set_title(f"|blend - ctrl| (gain-matched)\np99.9 = "
                       f"{np.percentile(dv, 99.9):.0f} DN", fontsize=9)
    ax[0][2].plot([x], [y], "c+", ms=14, mew=2)
    show(ax[1][0], ca[sl], lo, hi_c, f"CONTROL 1:1 at (y={y}, x={x})")
    show(ax[1][1], ba[sl], lo * gain, hi_b, "BLEND 1:1, same pixels")
    ax[1][2].imshow(np.clip(dv[sl] / np.percentile(dv, 99.9), 0, 1), cmap="inferno")
    ax[1][2].set_xticks([]); ax[1][2].set_yticks([])
    ax[1][2].set_title("|difference| 1:1", fontsize=9)
    fig.suptitle(f"{name}: control vs blend, linear 16-bit, display stretch only",
                 fontsize=14)
    plt.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT / fig_path, dpi=78)
    print(f"  wrote {OUT / fig_path}")
    return {"name": name, "gain": gain, "y": y, "x": x,
            "grad_ctrl": mc, "grad_blend": mb, "grad_ratio": mb / mc,
            "median_ctrl": float(np.median(luma(ca))),
            "median_blend": float(np.median(luma(ba)))}


def main():
    jobs = [
        ("flower-bud-alone-cpl", B / "bm/flower-bud-alone-cpl-ctrl.tif",
         B / "bm/flower-bud-alone-cpl-blend.tif", "BLEND-fb.png"),
        ("lavendar-cpl  (the polygonal patches)", B / "bm/lavendar-cpl-ctrl.tif",
         B / "bm/lavendar-cpl-blend.tif", "BLEND-lavendar.png"),
        ("couch-fibers-cpl  (DO NO HARM)", B / "bm/couch-fibers-cpl-ctrl.tif",
         B / "bm/couch-fibers-cpl-blend.tif", "BLEND-couch.png"),
    ]
    want = sys.argv[1:] or [j[0] for j in jobs]
    res = [pair(*j) for j in jobs if any(w in j[0] for w in want)]
    (OUT.parent / "blendlook.json").write_text(json.dumps(res, indent=1))
    print(f"\nwrote {OUT.parent / 'blendlook.json'}")


if __name__ == "__main__":
    main()
