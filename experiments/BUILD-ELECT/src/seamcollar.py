"""Roughness and elected index as a function of distance from the silhouette.

SEAM-where.png showed two different regimes in the backdrop: salt-and-pepper
noise far out, and large coherent lobes pinned near the silhouette. If that is
real, then roughness must be LOW near the silhouette and HIGH far from it, and
the near-field index must sit at an extreme of the bracket rather than near the
subject's own depth. A hard boundary is then simply where the coherent lobe
hands over to the noise field.

Prints the whole profile above any verdict, by house rule.
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


def main():
    idx = tifffile.imread(IDX)
    assert idx.dtype == np.uint16
    mrg = tifffile.imread(MRG).astype(np.float32)
    lum = mrg.mean(axis=2) if mrg.ndim == 3 else mrg
    assert lum.shape == idx.shape

    loc = ndimage.uniform_filter(lum, 9)
    tex = np.sqrt(np.maximum(ndimage.uniform_filter(lum * lum, 9) - loc * loc, 0))
    subj = ndimage.binary_closing(tex > np.percentile(tex, 70), np.ones((9, 9), bool))
    subj = ndimage.binary_opening(subj, np.ones((9, 9), bool))
    lab, n = ndimage.label(subj)
    s = ndimage.sum(subj, lab, range(1, n + 1))
    subj = ndimage.binary_fill_holes(lab == (1 + int(np.argmax(s))))

    # distance_transform_edt saturates at array borders unless the mask is padded
    pad = np.zeros((subj.shape[0] + 2, subj.shape[1] + 2), bool)
    pad[1:-1, 1:-1] = subj
    dist = ndimage.distance_transform_edt(~pad)[1:-1, 1:-1]

    f = idx.astype(np.float64)
    rough = np.mean([np.abs(f - np.roll(f, sh, axis=a))
                     for a, sh in ((0, 1), (0, -1), (1, 1), (1, -1))], axis=0)
    interior = np.zeros(idx.shape, bool)
    interior[2:-2, 2:-2] = True

    sub_med = float(np.median(idx[subj]))
    print(f"median elected index ON the subject = {sub_med:.0f} of 0..{idx.max()}")
    print(f"\nBACKDROP, binned by distance outward from the silhouette")
    print(f"{'d (px)':>10}{'n':>10}{'median idx':>13}{'roughness':>12}"
          f"{'>50 jumps':>12}{'luma (DN)':>12}")
    edges = [0, 4, 8, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1200]
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (~subj) & interior & (dist > lo) & (dist <= hi)
        if m.sum() < 200:
            continue
        r = {"d": (lo + hi) / 2, "n": int(m.sum()),
             "idx": float(np.median(idx[m])), "rough": float(rough[m].mean()),
             "gt50": float((rough[m] > 25).mean() * 100),
             "luma": float(np.median(lum[m]))}
        rows.append(r)
        print(f"{r['d']:>10.0f}{r['n']:>10}{r['idx']:>13.0f}{r['rough']:>12.2f}"
              f"{r['gt50']:>11.1f}%{r['luma']:>12.0f}")

    near = [r for r in rows if r["d"] <= 24]
    far = [r for r in rows if r["d"] >= 384]
    rn = float(np.mean([r["rough"] for r in near]))
    rf = float(np.mean([r["rough"] for r in far]))
    inear = float(np.mean([r["idx"] for r in near]))
    ifar = float(np.mean([r["idx"] for r in far]))
    print(f"\n  VERDICT")
    print(f"    roughness  near field (d<=24px) {rn:6.2f} frames"
          f"   far field (d>=384px) {rf:6.2f} frames  -> far is {rf / rn:.1f}x rougher")
    print(f"    median idx near {inear:.0f}   far {ifar:.0f}   subject {sub_med:.0f}")
    print(f"    -> the near-silhouette backdrop is {'COHERENT' if rf / rn > 3 else 'not coherent'}"
          f", and it is pinned {abs(inear - sub_med):.0f} frames off the subject's own depth")

    fig, ax = plt.subplots(1, 3, figsize=(17, 4.8))
    d = [r["d"] for r in rows]
    ax[0].semilogx(d, [r["rough"] for r in rows], "o-", color="crimson")
    ax[0].set_xlabel("distance outward from silhouette (px)")
    ax[0].set_ylabel("mean |neighbour index difference| (frames)")
    ax[0].set_title("winner-field roughness vs distance")
    ax[0].grid(alpha=.3)
    ax[1].semilogx(d, [r["idx"] for r in rows], "o-", color="navy",
                   label="backdrop median elected index")
    ax[1].axhline(sub_med, color="green", ls="--", label=f"subject median = {sub_med:.0f}")
    ax[1].set_xlabel("distance outward from silhouette (px)")
    ax[1].set_ylabel("elected frame index")
    ax[1].set_title("what the backdrop elects")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
    band = (~subj) & (dist > 0) & (dist <= 64)
    show = np.where(band | subj, idx, np.nan)
    ax[2].imshow(show, cmap="turbo")
    ax[2].set_xticks([]); ax[2].set_yticks([])
    ax[2].set_title("subject + the 64 px near-field collar")
    fig.suptitle("lavendar-cpl: the near-silhouette backdrop elects coherently, "
                 "and wrongly", fontsize=14)
    plt.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "SEAM-collar.png"
    plt.savefig(p, dpi=80)
    print(f"\nwrote {p}")
    (OUT.parent / "seamcollar.json").write_text(json.dumps(
        {"rows": rows, "subject_median": sub_med,
         "rough_near": rn, "rough_far": rf}, indent=1))


if __name__ == "__main__":
    main()
