"""M120b step 15 -- M1: isolate the two spatial-coherence operators.

ORCH: "raw argmax noise would be pixel-scale salt-and-pepper, not blobs tens of
pixels across. Something is imposing spatial coherence. The regulariser is the
only thing in the pipeline that does that."

The pipeline actually has two, and the FIRST one is LARGER:
    Sobel 3x3 -> box_mean(., WINDOW_RADIUS=13)  [27x27]  -> / sigma(luma)
              -> regularise = box_mean(., 8)    [17x17]  -> argmax

So toggle them independently and see which one the blobs need.

    C   window ON,  regulariser ON     -- shipped. Taken from the EXACT cached
                                         argbest, not from this replication,
                                         because that is the reference that
                                         argues AGAINST the prediction below
                                         (discipline 829): it has the largest blobs.
    B   window ON,  regulariser OFF    -- the decisive arm.
    A   window OFF, regulariser OFF    -- positive control: MUST be ~pixel scale,
                                         or the component metric cannot show
                                         salt-and-pepper and nothing else counts.
    A'  window OFF, regulariser ON     -- the regulariser acting alone.

Pre-registered (PREREGISTRATION-M120b-mechanism.md):
    ORCH's hypothesis  => A(B) < 0.10 * A(C)
    M120b's prediction => A(B) > 0.50 * A(C)
"""
import json
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from pathlib import Path
from PIL import Image

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
OUT.mkdir(parents=True, exist_ok=True)

WINDOW_RADIUS = 13
REGULARISER_RADIUS = 8
SUPPORT = WINDOW_RADIUS + 1 + REGULARISER_RADIUS  # 22
# noise.rs: PlaneNoise(dn_per_e=0.229, read_noise_e=1.47), black 100
DN_PER_E, READ_E, BLACK = 0.229, 1.47, 100.0


def sigma_luma(dn):
    e = np.maximum((dn - BLACK) / DN_PER_E, 0.0)
    return (DN_PER_E * np.sqrt(e + READ_E * READ_E)) / np.sqrt(2.0)


def grad_mag(a):
    gx = ndi.sobel(a, axis=1, mode="nearest")
    gy = ndi.sobel(a, axis=0, mode="nearest")
    return np.hypot(gx, gy)


def box(a, r):
    return ndi.uniform_filter(a, size=2 * r + 1, mode="nearest")


def components(idx, mask):
    """Connected components of constant elected index, restricted to `mask`."""
    lab = measure.label(idx, connectivity=1)
    lab = np.where(mask, lab, 0)
    areas = np.bincount(lab.ravel())
    areas[0] = 0
    areas = areas[areas > 0]
    n = areas.size
    mean_a = float(areas.mean())
    # area-weighted: the size of the region an average PIXEL finds itself in
    aw = float((areas.astype(np.float64) ** 2).sum() / areas.sum())
    return dict(n=int(n), mean_area=mean_a, aw_area=aw,
                eq_diam=float(np.sqrt(4 * aw / np.pi)),
                median_area=float(np.median(areas)))


def main():
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    argbest = np.load(C / "bee3-leg-argbest.npy")
    K, H, W = luma.shape
    assert luma.dtype == np.float32, luma.dtype

    # ---- masks: background = smooth in EVERY probe frame -------------------
    probe = np.linspace(0, K - 1, 12).astype(int)
    sdmax = np.zeros((H, W), np.float32)
    for k in probe:
        f = np.array(luma[k], np.float32)
        m = box(f, 16)
        sdmax = np.maximum(sdmax, np.sqrt(np.maximum(box(f * f, 16) - m * m, 0)))
    interior = np.zeros((H, W), bool)
    interior[SUPPORT + 4:H - SUPPORT - 4, SUPPORT + 4:W - SUPPORT - 4] = True
    bg = (sdmax < 250.0) & interior
    subj = (sdmax > 800.0) & interior
    bg = ndi.binary_erosion(bg, np.ones((9, 9)))
    subj = ndi.binary_erosion(subj, np.ones((9, 9)))
    print(f"plane {H}x{W} | background mask {bg.sum():,} px ({100*bg.mean():.1f}%) "
          f"| subject mask {subj.sum():,} px ({100*subj.mean():.1f}%)")
    print(f"  sdmax over background: p50 {np.percentile(sdmax[bg],50):.1f} "
          f"p95 {np.percentile(sdmax[bg],95):.1f}   (max-over-12-frames local sd)")
    print(f"  sdmax over subject   : p50 {np.percentile(sdmax[subj],50):.1f}")

    # ---- one pass over frames, four running argmaxes -----------------------
    arms = ["A", "Ap", "B", "Crep"]
    bestv = {a: np.full((H, W), -np.inf, np.float32) for a in arms}
    besti = {a: np.zeros((H, W), np.int32) for a in arms}
    for k in range(K):
        f = np.array(luma[k], np.float32)
        sig = sigma_luma(f)
        g = grad_mag(f)
        rA = g / sig
        rB = box(g, WINDOW_RADIUS) / sig
        cand = {"A": rA, "Ap": box(rA, REGULARISER_RADIUS),
                "B": rB, "Crep": box(rB, REGULARISER_RADIUS)}
        for a in arms:
            hit = cand[a] > bestv[a]
            bestv[a][hit] = cand[a][hit]
            besti[a][hit] = k
        if k % 60 == 0:
            print(f"  frame {k:3d}/{K}", flush=True)

    # ---- faithfulness of the replication -----------------------------------
    agree = float(np.mean(besti["Crep"][bg] == argbest[bg]))
    near = float(np.mean(np.abs(besti["Crep"][bg].astype(int) - argbest[bg].astype(int)) <= 2))
    print(f"\nreplication check over background: arm C-replicated vs cached argbest")
    print(f"  exact index agreement {100*agree:.2f}%   within +-2 frames {100*near:.2f}%")

    # ---- the numbers -------------------------------------------------------
    res = {}
    res["C"] = components(argbest, bg)            # EXACT shipped, the hostile reference
    for a in arms:
        res[a] = components(besti[a], bg)
    res["C_subject"] = components(argbest, subj)  # P4
    res["B_subject"] = components(besti["B"], subj)

    print(f"\n{'arm':6}{'window':>8}{'reg':>6}{'#comp':>9}{'mean area':>11}"
          f"{'area-wtd':>10}{'eq diam':>9}")
    rows = [("A", "OFF", "OFF"), ("Ap", "OFF", "ON"), ("B", "27x27", "OFF"),
            ("Crep", "27x27", "ON"), ("C", "27x27", "ON")]
    for a, w, r in rows:
        d = res[a]
        tag = "  <- SHIPPED (exact)" if a == "C" else ("  <- decisive" if a == "B" else "")
        print(f"{a:6}{w:>8}{r:>6}{d['n']:>9,}{d['mean_area']:>11.1f}"
              f"{d['aw_area']:>10.1f}{d['eq_diam']:>9.1f}{tag}")

    ratio_mean = res["B"]["mean_area"] / res["C"]["mean_area"]
    ratio_aw = res["B"]["aw_area"] / res["C"]["aw_area"]
    print(f"\nPRE-REGISTERED DECISION (arm B vs exact shipped arm C):")
    print(f"  A(B)/A(C) mean-area      = {ratio_mean:.3f}")
    print(f"  A(B)/A(C) area-weighted  = {ratio_aw:.3f}")
    for nm, r in (("mean-area", ratio_mean), ("area-weighted", ratio_aw)):
        v = ("ORCH CONFIRMED" if r < 0.10 else
             "ORCH REFUTED" if r > 0.50 else "PARTIAL")
        print(f"    {nm:16s} -> {v}")
    print(f"\npositive control, arm A (no window, no reg): mean area "
          f"{res['A']['mean_area']:.2f} px, eq diam {res['A']['eq_diam']:.2f} px "
          f"-- {'PASS (can show salt-and-pepper)' if res['A']['mean_area'] < 5 else 'FAIL'}")
    print(f"regulariser acting ALONE, arm A' : eq diam {res['Ap']['eq_diam']:.1f} px")
    print(f"\nP4 subject control: shipped eq diam background {res['C']['eq_diam']:.1f} px "
          f"vs subject {res['C_subject']['eq_diam']:.1f} px")

    json.dump(res, open("m1_operators.json", "w"), indent=1)

    # ---- pictures ----------------------------------------------------------
    def save(idx, name, m):
        v = (idx.astype(np.float32) % 32) / 32.0
        rgb = (np.stack([v, np.roll(v, 3), 1 - v], -1) * 255).astype(np.uint8)
        rgb[~m] = 30
        Image.fromarray(rgb).save(OUT / name)
    save(argbest, "M1-C-shipped-window-ON-reg-ON.png", bg)
    save(besti["B"], "M1-B-window-ON-reg-OFF.png", bg)
    save(besti["A"], "M1-A-window-OFF-reg-OFF.png", bg)
    save(besti["Ap"], "M1-Ap-window-OFF-reg-ON.png", bg)
    np.save(OUT / "m1_besti_B.npy", besti["B"])
    np.save(OUT / "m1_bg_mask.npy", bg)
    np.save(OUT / "m1_subj_mask.npy", subj)
    np.save(OUT / "m1_sdmax.npy", sdmax)
    print(f"\nwrote pictures + arrays to {OUT}")


if __name__ == "__main__":
    main()
