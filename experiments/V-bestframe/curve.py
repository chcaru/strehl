"""Threshold-free comparison, plus the commissioning plant.

flowers-cpl's frame-signal distribution sits almost entirely on the fixed-pattern
floor, so ANY binary content threshold drives the answer. Drop the threshold.
Ask instead how the merge/best-frame ratio behaves AS A FUNCTION of how much
detail the best frame actually has, in units of that subject's own measured
fixed-pattern floor, and put both subjects on the same axis.

If flowers-cpl's curve lies on the control's curve, the merge is treating
flowers exactly as it treats a subject known to be excellent, and flowers simply
has fewer tiles above the crossover -- a property of the CAPTURE. If flowers'
curve lies below the control's, the merge is losing detail the frames hold and
that is a defect.

--plant blurs the merge over a known tile block and requires those tiles, and
only those, to move. A checker that has never gone red is not a checker.
"""
import argparse
import os
import numpy as np
from pathlib import Path
from scipy import ndimage
import bestframe as B

OUT = Path(os.environ.get("VBF_OUT", r"C:\dev\strehl-out\V-BESTFRAME"))
GAL = Path(os.environ.get("VBF_GAL", r"C:\dev\strehl-out\GALLERY-FIXED-SRGB"))
SUBPIX = 0.8126
DISP_MIN = 20.0
EDGES = np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 1e9])


def arms(subj, Em_override=None, peak_min=0.0):
    """peak_min gates PAIRS by registration quality, never by detail. A frame the
    phase correlation could not lock onto is extracting a different patch of scene
    than the merge tile, so comparing them measures misregistration. Reported both
    gated and ungated everywhere."""
    z0 = np.load(OUT / f"{subj}__paircov_fine.npz")
    S = z0["S"]; anch = z0["anchors"]
    ngate = 0
    if peak_min > 0:
        from peaks import peaks_for
        pk = peaks_for(subj, anch)
        keep = ~(np.isfinite(pk) & (pk < peak_min))
        if keep.sum() >= 2:
            ngate = int((~keep).sum()); S = S[keep]; anch = anch[keep]
    z = {k: z0[k] for k in z0.files}; z["S"] = S; z["anchors"] = anch
    Sf = np.nanmax(S, 0) / SUBPIX
    Em = z0["merge_tiles"][:, :, 1] ** 2 if Em_override is None else Em_override
    f = np.load(sorted(OUT.glob(f"{subj}__fpn_k*.npz"))[0])
    F = np.where(f["disp"] >= DISP_MIN, np.maximum(f["Z"], 0.0), np.nan)
    F = np.where(np.isfinite(F), F, np.nanmedian(F))
    Sft = np.maximum(Sf - F, 0.0)                       # frame detail power
    snr = np.sqrt(Sft / np.maximum(F, 1e-9))            # in floor units
    empty = snr < 0.5
    Fm = np.nanmedian(Em[empty]) if empty.sum() >= 8 else np.nanpercentile(Em, 5)
    Smt = np.maximum(Em - Fm, 0.0)                      # merge detail power
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.sqrt(Smt) / np.sqrt(np.maximum(Sft, 1e-12))
    return dict(snr=snr, ratio=ratio, Sft=Sft, Smt=Smt, F=F, Fm=Fm, Em=Em,
                z=z, nd=int(z0["n_on_disk"]), na=len(anch), ngate=ngate)

def curve(subj, a=None, label=None, quiet=False):
    a = a or arms(subj)
    rows = []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        m = (a["snr"] >= lo) & (a["snr"] < hi) & np.isfinite(a["ratio"])
        rows.append((lo, hi, int(m.sum()),
                     float(np.nanmedian(a["ratio"][m])) if m.sum() else np.nan,
                     float(np.nanmedian(np.sqrt(a["Sft"][m]))) if m.sum() else np.nan,
                     float(np.nanmedian(np.sqrt(a["Smt"][m]))) if m.sum() else np.nan,
                     float(np.mean(a["ratio"][m] >= 1.0)) if m.sum() else np.nan))
    if not quiet:
        print(f"\n--- {label or subj}   {a['nd']} frames on disk, {2*a['na']} READ   "
              f"floor {np.sqrt(np.nanmedian(a['F'])):.2f} DN (frame) / "
              f"{np.sqrt(a['Fm']):.2f} DN (merge)")
        print(f"    {'bestframe SNR':>16} {'n':>4} {'frameDetail':>12} {'mergeDetail':>12} "
              f"{'merge/frame':>12} {'merge>=frame':>13}")
        for lo, hi, n, r, fd, md, w in rows:
            if n == 0:
                continue
            print(f"    {lo:6.2f}-{hi if hi < 1e8 else 99:6.2f} {n:4d} {fd:12.2f} "
                  f"{md:12.2f} {r:12.3f} {100*w:12.1f}%")
        tot = sum(x[2] for x in rows)
        hi_n = sum(x[2] for x in rows if x[0] >= 1.0)
        print(f"    tiles above SNR 1.0 (real frame detail): {hi_n}/{tot} = {100*hi_n/tot:.1f}%")
    return rows, a


def plant(subj, i0, i1, j0, j1, sigma):
    """Blur the merge over a known tile block. Those tiles must move, others must not."""
    base = arms(subj)
    mL = B.luma(B.read_merge(GAL / f"{subj}.tiff")).astype(np.float32)
    ye, xe = base["z"]["ye"], base["z"]["xe"]
    msk = np.zeros(mL.shape, np.float32)
    msk[ye[i0]:ye[i1], xe[j0]:xe[j1]] = 1.0
    msk = ndimage.gaussian_filter(msk, 48.0)          # feather: a step edge is HF
    mL = mL * (1 - msk) + ndimage.gaussian_filter(mL, sigma) * msk
    Em2 = B.tile_stats(mL, ye, xe)[:, :, 1] ** 2
    del mL
    pl = arms(subj, Em_override=Em2)
    inb = np.zeros(base["ratio"].shape, bool); inb[i0:i1, j0:j1] = True
    real = base["snr"] >= 3.0   # the crossover measured on BOTH subjects
    d = pl["ratio"] / np.maximum(base["ratio"], 1e-9)
    hit = np.isfinite(d) & real & (d < 0.70)
    print(f"\nPLANT sigma={sigma}  tiles [{i0}:{i1},{j0}:{j1}] = {int(inb.sum())} of "
          f"{inb.size}   ({int((inb&real).sum())} of them have real frame detail)")
    print(f"  ratio dropped >30% in {int(hit.sum())} tiles: "
          f"{int((hit&inb).sum())} INSIDE the plant, {int((hit&~inb).sum())} outside")
    print(f"  detected {int((hit&inb).sum())}/{int((inb&real).sum())} planted tiles that "
          f"had detail to lose   |   false positives {int((hit&~inb).sum())}/"
          f"{int((~inb&real).sum())} = {100*(hit&~inb).sum()/max((~inb&real).sum(),1):.1f}%")
    print(f"  median ratio inside plant  {np.nanmedian(base['ratio'][inb&real]):.3f} "
          f"-> {np.nanmedian(pl['ratio'][inb&real]):.3f}")
    print(f"  median ratio outside plant {np.nanmedian(base['ratio'][~inb&real]):.3f} "
          f"-> {np.nanmedian(pl['ratio'][~inb&real]):.3f}")
    ok = (hit & inb).sum() >= 0.8 * (inb & real).sum() and \
         (hit & ~inb).sum() <= 0.05 * (~inb & real).sum()
    print(f"  -> {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--plant", type=float, default=0.0)
    ap.add_argument("--tiles", default="4,10,6,14")
    a = ap.parse_args()
    for s in a.subjects:
        curve(s)
    if a.plant:
        i0, i1, j0, j1 = map(int, a.tiles.split(","))
        for s in a.subjects:
            plant(s, i0, i1, j0, j1, a.plant)
