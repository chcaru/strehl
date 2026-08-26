"""Whole-subject fingerprint on bee-1-cpl: elected index vs distance from silhouette.

Phase 1 on flower-bud found that the elected frame index decays monotonically from
the silhouette inward -- 120 at the edge to 34 deep inside -- asymptoting at the
true surface focus, while a backdrop control has a completely different, non-monotone
shape. That is the signature of veiling glare being scored as focus: the defocused
bright surround casts a smooth luminance ramp inward across the subject, the ramp
outscores real texture, and its reach sets how far in the damage goes.

This asks whether the same fingerprint is present on the bee, which is the one thing
the committed report lists as unverified. The bee is a much harder test: dark subject
on a white paper sweep, so the veil contrast is extreme, and the silhouette is long
and convoluted.

Measured on the align-off render, so no warp resampling sits between the mask and
the election. Four ROI-independent curves, all from the same distance transform:
inward from the silhouette (the claim), outward into the backdrop (the control),
and the interquartile spread of each so a flat median cannot hide a wide spread.
"""
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile
from scipy import ndimage

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee")
PICS = OUT / "pics"
REF = np.array([19093.0, 20163.0, 21361.0])
MAXD = 320          # plane px, how far in/out to profile
BIN = 8
Y_KEEP = 0.86       # fraction of frame height above the sweep lip, chosen by eye
SEVER = 30          # plane px; erosion depth used to sever thin mask bridges


def main():
    PICS.mkdir(parents=True, exist_ok=True)
    img = tifffile.imread(str(OUT / "E-noalign-merge.tif"))
    assert img.dtype == np.uint16, img.dtype
    e = tifffile.imread(str(OUT / "E-noalign-elect.tif")).astype(np.float64)
    assert e.shape[0] * 2 == img.shape[0], (e.shape, img.shape)

    # Subject mask on the plane grid. Dark bee on a white sweep, so a luma threshold
    # at a fraction of measured paper white separates them; close the hair fringe.
    # The first version then took the largest component and got 53.93% of the frame,
    # because the shaded foreground edge of the sweep is also below threshold and is
    # joined to the bee through a single leg. Erode to sever thin bridges, keep the
    # largest body, dilate back, and intersect with the original mask so the true
    # silhouette is preserved rather than the eroded one.
    g = img[:, :, 1].astype(np.float64)
    L = 0.25 * (g[0::2, 0::2] + g[0::2, 1::2] + g[1::2, 0::2] + g[1::2, 1::2])
    thr = 0.55 * REF[1]
    m0 = ndimage.binary_fill_holes(ndimage.binary_closing(L < thr, np.ones((15, 15))))
    core = ndimage.binary_erosion(m0, np.ones((3, 3)), iterations=SEVER)
    lab, nl = ndimage.label(core)
    if nl == 0:
        raise SystemExit("mask erosion left nothing; lower SEVER")
    core = lab == 1 + int(np.argmax(ndimage.sum(core, lab, range(1, nl + 1))))
    m = ndimage.binary_dilation(core, np.ones((3, 3)), iterations=SEVER) & m0
    # Erosion did not sever it: the shaded foreground lip of the paper sweep runs
    # the full width of the frame and joins the bee across a wide front, not a thin
    # leg, so no morphological rule separates them. The brief's instruction applies
    # -- when a threshold rule fails, use a fixed region chosen by eye. Everything
    # below Y_KEEP of the frame is sweep in this capture and is excluded from both
    # the subject and the backdrop, so neither curve is measuring it.
    keep = np.zeros_like(m)
    keep[:int(Y_KEEP * m.shape[0])] = True
    m &= keep
    print(f"threshold {thr:.0f} DN; before sever {m0.mean():.2%} of plane "
          f"({nl} cores); after sever and sweep exclusion {m.mean():.2%}")

    din = ndimage.distance_transform_edt(m)          # inward, 0 at silhouette
    dout = ndimage.distance_transform_edt(~m)        # outward into backdrop

    rows = []
    for lo in range(0, MAXD, BIN):
        for tag, d, sel in (("inward", din, m), ("backdrop", dout, (~m) & keep)):
            b = sel & (d >= lo) & (d < lo + BIN)
            if b.sum() < 400:
                continue
            v = e[b]
            rows.append({"tag": tag, "d": lo + BIN / 2, "n": int(b.sum()),
                         "med": float(np.median(v)),
                         "q1": float(np.percentile(v, 25)),
                         "q3": float(np.percentile(v, 75))})

    inw = [r for r in rows if r["tag"] == "inward"]
    bak = [r for r in rows if r["tag"] == "backdrop"]
    print(f"\n{'d(px)':>7} {'inward med':>11} {'IQR':>13} {'n':>9}")
    for r in inw[::4]:
        print(f"{r['d']:>7.0f} {r['med']:>11.1f} "
              f"{r['q1']:>6.0f}-{r['q3']:<6.0f} {r['n']:>9}")

    d = np.array([r["d"] for r in inw]); med = np.array([r["med"] for r in inw])
    edge, deep = med[0], np.median(med[-6:])
    # Monotone decay is the claim; measure it rather than eyeball it. Spearman on
    # the ranks, plus the fraction of adjacent bins that fall.
    rk = lambda a: np.argsort(np.argsort(a)).astype(float)
    rho = float(np.corrcoef(rk(d), rk(med))[0, 1])
    falling = float(np.mean(np.diff(med) < 0))
    bd = np.array([r["med"] for r in bak])
    rho_b = float(np.corrcoef(rk(np.array([r["d"] for r in bak])), rk(bd))[0, 1])
    print(f"\ninward : edge f{edge:.0f} -> deep f{deep:.0f}   drop {edge - deep:.0f} "
          f"frames   spearman {rho:+.3f}   falling bins {falling:.0%}")
    print(f"backdrop control: spearman {rho_b:+.3f}  "
          f"range f{bd.min():.0f}-f{bd.max():.0f}")
    verdict = ("veiling fingerprint PRESENT: elected index decays monotonically "
               "inward from the silhouette"
               if rho < -0.8 and edge - deep > 40 and rho_b > -0.8 else
               "veiling fingerprint NOT reproduced on this subject")
    print(f"\nVERDICT: {verdict}")

    fig, axes = plt.subplots(1, 3, figsize=(19, 5.4))
    axes[0].imshow(np.clip(img[::4, ::4].astype(np.float64) / (REF / .92), 0, 1)
                   ** (1 / 2.2))
    axes[0].contour(m[::2, ::2], levels=[.5], colors="r", linewidths=.8)
    axes[0].set_title("align-off merge + subject mask"); axes[0].set_xticks([])
    axes[0].set_yticks([])
    im = axes[1].imshow(np.where(m, e, np.nan)[::2, ::2], cmap="turbo",
                        interpolation="nearest")
    axes[1].set_title("elected index, subject only"); axes[1].set_xticks([])
    axes[1].set_yticks([]); plt.colorbar(im, ax=axes[1], fraction=.03)
    for r, c, lbl in ((inw, "tab:red", "inward from silhouette"),
                      (bak, "tab:blue", "outward into backdrop (control)")):
        x = np.array([q["d"] for q in r])
        axes[2].plot(x, [q["med"] for q in r], c, lw=2, label=lbl)
        axes[2].fill_between(x, [q["q1"] for q in r], [q["q3"] for q in r],
                             color=c, alpha=.15)
    axes[2].set_xlabel("distance from silhouette (plane px)")
    axes[2].set_ylabel("elected frame index")
    axes[2].set_title(f"inward spearman {rho:+.3f}, drop {edge - deep:.0f} frames\n"
                      f"backdrop spearman {rho_b:+.3f}")
    axes[2].grid(alpha=.3); axes[2].legend(fontsize=9)
    fig.suptitle("bee-1-cpl: does the elected index decay inward from the silhouette?",
                 fontsize=14)
    fig.tight_layout()
    p = PICS / "BEE-depthprofile.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    (OUT / "bee-depthprofile.json").write_text(json.dumps(
        {"rows": rows, "rho": rho, "rho_backdrop": rho_b, "edge": edge,
         "deep": deep, "falling": falling, "verdict": verdict}, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
