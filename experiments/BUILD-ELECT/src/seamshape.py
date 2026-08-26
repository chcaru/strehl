"""Shape of the winner-field excursions: seams, or speckle?

The owner's argument that the artifact is an election defect rests entirely on
MORPHOLOGY -- straight and scalloped boundaries do not occur in defocus. He has
now retracted the claim that anyone verified it, and BUILD-CHROMA's roughness
statistic (mean absolute 4-neighbour difference) reports a long straight seam and
an isolated bad pixel IDENTICALLY. So the shape question is open and this is the
first look at it.

The instrument is a spatial null, because "the excursion pixels form connected
structures" is meaningless without knowing what connectivity the same number of
randomly scattered pixels would produce by chance at the same density. Random
placement in a 3.5 Mpx plane makes clusters on its own. The null is the control
and it is the whole experiment.

Reads BUILD-CHROMA's already-dumped 1:1 linear field. No render cost.
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
BIG = 50          # frames; an "excursion" between 4-neighbours
SEED = 20260826


def neighbour_jump(idx):
    """Max absolute 4-neighbour difference at each pixel."""
    f = idx.astype(np.int32)
    j = np.zeros_like(f)
    for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
        j = np.maximum(j, np.abs(f - np.roll(f, sh, axis=ax)))
    j[0, :] = j[-1, :] = j[:, 0] = j[:, -1] = 0
    return j


def morphology(mask, tag):
    """Connected-component shape of a binary set, 8-connected."""
    lab, n = ndimage.label(mask, structure=np.ones((3, 3), int))
    if n == 0:
        return {"tag": tag, "n_px": 0, "n_comp": 0}
    sizes = np.bincount(lab.ravel())[1:]
    objs = ndimage.find_objects(lab)
    elong = []
    for i, sl in enumerate(objs):
        if sizes[i] < 8:
            continue
        ys, xs = np.nonzero(lab[sl] == i + 1)
        c = np.cov(np.vstack([ys, xs]).astype(np.float64))
        if c.shape != (2, 2):
            continue
        w = np.linalg.eigvalsh(c)
        if w[0] <= 1e-9:
            continue
        elong.append(float(np.sqrt(w[1] / w[0])))
    return {"tag": tag, "n_px": int(mask.sum()), "n_comp": int(n),
            "max_comp": int(sizes.max()), "mean_comp": float(sizes.mean()),
            "frac_in_comp_ge8": float(sizes[sizes >= 8].sum() / sizes.sum()),
            "n_comp_ge8": int((sizes >= 8).sum()),
            "median_elong": float(np.median(elong)) if elong else float("nan"),
            "n_elong_ge3": int(sum(e >= 3.0 for e in elong))}


def show(d):
    print(f"  {d['tag']:<22} px={d['n_px']:>8} comps={d['n_comp']:>7} "
          f"mean={d['mean_comp']:>7.2f} max={d['max_comp']:>7} "
          f"comps>=8px={d['n_comp_ge8']:>5} px in them={d['frac_in_comp_ge8'] * 100:>5.1f}% "
          f"median elong={d['median_elong']:.2f} elong>=3={d['n_elong_ge3']}")


def main():
    idx = tifffile.imread(IDX)
    assert idx.dtype == np.uint16, f"expected uint16, got {idx.dtype}"
    print(f"index map {idx.shape} {idx.dtype}  range {idx.min()}..{idx.max()}")

    j = neighbour_jump(idx)
    interior = np.zeros_like(j, bool)
    interior[1:-1, 1:-1] = True
    # BUILD-CHROMA's statistic, reproduced for continuity.
    f = idx.astype(np.float64)
    mad = np.mean([np.abs(f - np.roll(f, s, axis=a))[1:-1, 1:-1].mean()
                   for a, s in ((0, 1), (0, -1), (1, 1), (1, -1))])
    print(f"mean |4-neighbour difference| = {mad:.3f} frames   "
          f"max single-step jump = {j.max()} frames")
    for t in (1, 10, 50, 100, 150):
        print(f"  pixels with a jump > {t:3d} frames: "
              f"{(j > t).sum():>9} = {(j > t).mean() * 100:7.4f}%")

    mask = (j > BIG) & interior
    print(f"\nMORPHOLOGY of the {mask.sum()} pixels with a jump > {BIG} frames")
    real = morphology(mask, "measured")
    show(real)

    rng = np.random.default_rng(SEED)
    nulls = []
    for k in range(3):
        flat = np.zeros(idx.size, bool)
        flat[rng.choice(idx.size, int(mask.sum()), replace=False)] = True
        nulls.append(morphology(flat.reshape(idx.shape), f"random null {k + 1}"))
        show(nulls[-1])

    nn = {k: float(np.mean([x[k] for x in nulls]))
          for k in ("mean_comp", "max_comp", "frac_in_comp_ge8", "n_comp_ge8")}
    print("\n  VERDICT")
    print(f"    mean component size   measured {real['mean_comp']:.2f} "
          f"vs null {nn['mean_comp']:.2f}  -> {real['mean_comp'] / nn['mean_comp']:.2f}x")
    print(f"    largest component     measured {real['max_comp']} "
          f"vs null {nn['max_comp']:.0f}  -> {real['max_comp'] / max(nn['max_comp'], 1):.1f}x")
    print(f"    px in components >=8  measured {real['frac_in_comp_ge8'] * 100:.1f}% "
          f"vs null {nn['frac_in_comp_ge8'] * 100:.1f}%")
    seamy = (real["frac_in_comp_ge8"] > 4 * max(nn["frac_in_comp_ge8"], 1e-6)
             and real["max_comp"] > 10 * max(nn["max_comp"], 1))
    print(f"    -> {'SEAMS: excursions are connected, far beyond chance' if seamy else 'SPECKLE: excursions are scattered, consistent with chance'}")

    # ---- look at it -------------------------------------------------------
    mrg = tifffile.imread(MRG).astype(np.float32)
    lum = mrg.mean(axis=2) if mrg.ndim == 3 else mrg.astype(np.float32)
    white = float(np.percentile(lum, 99.5))
    view = np.clip(lum / white, 0, 1) ** (1 / 2.2)

    lab, _ = ndimage.label(mask, structure=np.ones((3, 3), int))
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    order = np.argsort(sizes)[::-1][:3]

    fig, ax = plt.subplots(2, 4, figsize=(21, 10))
    ax[0][0].imshow(idx, cmap="turbo"); ax[0][0].set_title(
        f"elected frame index, 1:1 plane grid\nrange {idx.min()}-{idx.max()}")
    ax[0][1].imshow(view, cmap="gray"); ax[0][1].set_title("matching linear merge")
    ax[0][2].imshow(mask, cmap="gray")
    ax[0][2].set_title(f"jump > {BIG} frames: {mask.sum()} px "
                       f"({mask.mean() * 100:.4f}%)")
    ax[0][3].hist(sizes[sizes > 0], bins=np.arange(1, 30), log=True)
    ax[0][3].set_title("component size histogram\n(1 = isolated pixel)")
    ax[0][3].set_xlabel("pixels in component")

    for k, comp in enumerate(order[:3]):
        ys, xs = np.nonzero(lab == comp)
        cy, cx = int(ys.mean()), int(xs.mean())
        H = 90
        cy = int(np.clip(cy, H, idx.shape[0] - H)); cx = int(np.clip(cx, H, idx.shape[1] - H))
        sl = (slice(cy - H, cy + H), slice(cx - H, cx + H))
        ax[1][k].imshow(idx[sl], cmap="turbo")
        ax[1][k].contour(mask[sl], levels=[0.5], colors="w", linewidths=0.7)
        ax[1][k].set_title(f"largest excursion #{k + 1}: {sizes[comp]} px\n"
                           f"index {idx[sl].min()}-{idx[sl].max()} in a {2*H}px crop")
    ax[1][3].imshow(view[sl], cmap="gray")
    ax[1][3].set_title("the merge under excursion #3")
    for r in ax:
        for a_ in r:
            if a_ is not ax[0][3]:
                a_.set_xticks([]); a_.set_yticks([])
    fig.suptitle("lavendar-cpl: do the winner-field excursions form seams, or speckle?",
                 fontsize=15)
    plt.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "SEAM-shape.png"
    plt.savefig(p, dpi=76)
    print(f"\nwrote {p}")
    (OUT.parent / "seamshape.json").write_text(
        json.dumps({"mad": mad, "max_jump": int(j.max()), "real": real,
                    "nulls": nulls}, indent=1))


if __name__ == "__main__":
    main()
