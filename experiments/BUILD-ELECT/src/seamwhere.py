"""Where do the winner-field excursions actually live, and what shape are they?

seamshape.py returned "SEAMS" and the picture said otherwise. The failure is
instructive and it is mine: I compared the excursion set against a null that
scattered pixels over the WHOLE frame, while the real excursions are confined to
the backdrop. A confined set percolates inside its region, so the component test
was reporting "these pixels are clustered into a region" -- true, and trivial --
and not "these pixels form curvilinear seams", which is the claim on trial.

The null has to be matched to the region. This script splits subject from
backdrop and asks the shape question separately inside each, against a null drawn
from the same region at the same density.
"""
import json
import pathlib
import numpy as np
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

IDX = r"C:\dev\strehl-out\BUILD-CHROMA\render\lavendar-index.tif"
MRG = r"C:\dev\strehl-out\BUILD-CHROMA\render\lavendar-idx-merge.tif"
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\pics")
BIG = 50
SEED = 20260826


def jump(idx):
    f = idx.astype(np.int32)
    j = np.zeros_like(f)
    for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
        j = np.maximum(j, np.abs(f - np.roll(f, sh, axis=ax)))
    j[0, :] = j[-1, :] = j[:, 0] = j[:, -1] = 0
    return j


def shape_stats(mask, region):
    """Component shape of `mask`, and of a null drawn inside `region` at the
    same density. Returns (measured, null) dicts."""
    rng = np.random.default_rng(SEED)
    st = np.ones((3, 3), int)

    def stats(m):
        lab, n = ndimage.label(m, structure=st)
        if n == 0:
            return {"n": 0, "mean": 0.0, "max": 0, "frac_ge8": 0.0}
        s = np.bincount(lab.ravel())[1:]
        return {"n": int(n), "mean": float(s.mean()), "max": int(s.max()),
                "frac_ge8": float(s[s >= 8].sum() / s.sum())}

    real = stats(mask)
    idxs = np.flatnonzero(region)
    pick = rng.choice(idxs, int(mask.sum()), replace=False)
    nm = np.zeros(region.size, bool)
    nm[pick] = True
    null = stats(nm.reshape(region.shape))
    return real, null


def main():
    idx = tifffile.imread(IDX)
    assert idx.dtype == np.uint16
    mrg = tifffile.imread(MRG).astype(np.float32)
    lum = mrg.mean(axis=2) if mrg.ndim == 3 else mrg
    assert lum.shape == idx.shape, f"grid mismatch {lum.shape} vs {idx.shape}"

    # The subject is where the merge has local structure. Thresholding brightness
    # would fail here (a lavender head on a bright sweep is not cleanly bimodal),
    # so segment on local contrast instead, which is what "has any detail" means.
    loc = ndimage.uniform_filter(lum, 9)
    var = np.maximum(ndimage.uniform_filter(lum * lum, 9) - loc * loc, 0)
    tex = np.sqrt(var)
    t = float(np.percentile(tex, 70))
    subj = ndimage.binary_closing(tex > t, np.ones((9, 9), bool))
    subj = ndimage.binary_opening(subj, np.ones((9, 9), bool))
    lab, n = ndimage.label(subj)
    if n > 1:
        s = ndimage.sum(subj, lab, range(1, n + 1))
        subj = lab == (1 + int(np.argmax(s)))
    subj = ndimage.binary_fill_holes(subj)
    back = ~subj
    print(f"subject = {subj.mean() * 100:.1f}% of the plane "
          f"(local-contrast segmentation, threshold p70)")

    j = jump(idx)
    interior = np.zeros_like(j, bool)
    interior[1:-1, 1:-1] = True

    print(f"\n{'region':<12}{'mean |4-nbr diff|':>20}{'>50 frame jumps':>18}"
          f"{'>150 frame jumps':>19}{'median index':>15}")
    f = idx.astype(np.float64)
    res = {}
    for tag, m in (("SUBJECT", subj & interior), ("backdrop", back & interior)):
        d = np.mean([np.abs(f - np.roll(f, s, axis=a))[m].mean()
                     for a, s in ((0, 1), (0, -1), (1, 1), (1, -1))])
        res[tag] = {"mad": float(d),
                    "gt50": float((j[m] > 50).mean() * 100),
                    "gt150": float((j[m] > 150).mean() * 100)}
        print(f"{tag:<12}{d:>20.3f}{res[tag]['gt50']:>17.2f}%"
              f"{res[tag]['gt150']:>18.2f}%{np.median(idx[m]):>15.0f}")

    print(f"\nthe backdrop is {res['backdrop']['mad'] / res['SUBJECT']['mad']:.1f}x "
          f"rougher than the subject by mean neighbour difference")

    print(f"\nSHAPE of >{BIG}-frame excursions, against a null drawn from the "
          f"SAME region at the SAME density")
    print(f"  {'region':<12}{'px':>10}{'comps':>9}{'mean sz':>10}{'max sz':>10}"
          f"{'% px in comps>=8':>19}")
    verdict = {}
    for tag, region in (("SUBJECT", subj & interior), ("backdrop", back & interior)):
        m = (j > BIG) & region
        real, null = shape_stats(m, region)
        verdict[tag] = {"real": real, "null": null,
                        "density": float(m.sum() / max(region.sum(), 1) * 100)}
        print(f"  {tag:<12}{m.sum():>10}{real['n']:>9}{real['mean']:>10.2f}"
              f"{real['max']:>10}{real['frac_ge8'] * 100:>18.1f}%   measured")
        print(f"  {'':<12}{m.sum():>10}{null['n']:>9}{null['mean']:>10.2f}"
              f"{null['max']:>10}{null['frac_ge8'] * 100:>18.1f}%   null (same region)")

    print("\n  VERDICT")
    for tag in ("SUBJECT", "backdrop"):
        v = verdict[tag]
        r, nl = v["real"], v["null"]
        ratio = r["mean"] / max(nl["mean"], 1e-9)
        print(f"    {tag:<10} density {v['density']:5.2f}%   "
              f"mean component {r['mean']:.2f} vs null {nl['mean']:.2f} "
              f"= {ratio:.2f}x  -> "
              f"{'organised' if ratio > 3 else 'indistinguishable from scatter at this density'}")

    fig, ax = plt.subplots(1, 4, figsize=(21, 5.6))
    ax[0].imshow(idx, cmap="turbo")
    ax[0].contour(subj, levels=[0.5], colors="k", linewidths=0.8)
    ax[0].set_title("elected index, subject outlined")
    sh = np.where(subj, idx, np.nan)
    ax[1].imshow(sh, cmap="turbo"); ax[1].set_title(
        f"index ON THE SUBJECT only\nmean neighbour diff {res['SUBJECT']['mad']:.2f} frames")
    bk = np.where(back, idx, np.nan)
    ax[2].imshow(bk, cmap="turbo"); ax[2].set_title(
        f"index ON THE BACKDROP only\nmean neighbour diff {res['backdrop']['mad']:.2f} frames")
    ax[3].imshow(np.clip(lum / np.percentile(lum, 99.5), 0, 1) ** (1 / 2.2), cmap="gray")
    ax[3].contour(subj, levels=[0.5], colors="r", linewidths=0.8)
    ax[3].set_title("the merge, subject outlined")
    for a_ in ax:
        a_.set_xticks([]); a_.set_yticks([])
    fig.suptitle("lavendar-cpl: the excursions are in the featureless backdrop, "
                 "not on the subject", fontsize=15)
    plt.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "SEAM-where.png"
    plt.savefig(p, dpi=76)
    print(f"\nwrote {p}")
    (OUT.parent / "seamwhere.json").write_text(
        json.dumps({"regions": res, "shape": verdict}, indent=1))


if __name__ == "__main__":
    main()
