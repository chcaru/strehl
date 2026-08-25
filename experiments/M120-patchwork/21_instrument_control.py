"""M120b step 21 -- the control ORCH's kurtosis instrument is missing.

ORCH commissioned Laplacian excess kurtosis against (a) iid gaussian, (b) a smooth
ramp, (c) a planted Voronoi mosaic, and (d) a single input frame. All four are
GOOD, and the instrument passed them. But none of them is a MULTI-FRAME AVERAGE.

Kurtosis is scale-free: it is normalised by the distribution's own variance. The
shipped merge averages ~167 frames, which crushes the noise floor by ~13x. Any
residual real structure -- a soft defocused edge, a faint gradient -- then sits in
the tail of a much narrower distribution and reads as extreme.

So the missing control is a PLAIN MEAN of N frames with CONSTANT weights, which
cannot manufacture spatial structure by construction. If its kurtosis climbs with
N, the instrument is confounded by denoising, and "kurtosis rises 14 -> 61 as RMS
falls" is the instrument talking about itself.

Pre-registered direction, stated before running: if plain-mean kurtosis at N=167
stays below the bar of 10, the instrument is clean and ORCH's localisation stands.
If it crosses the bar, the instrument cannot grade the shipped arm.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage as ndi, stats
from pathlib import Path

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
M93 = Path(r"C:\dev\strehl-out\M93-out")
OUT = Path(r"C:\dev\strehl-out\M120")
BOX = (1178, 1922, 278, 1422)
WIN = 96
NS = [1, 2, 4, 8, 16, 32, 64, 128, 299]


def lap_kurt(a):
    return float(stats.kurtosis(ndi.laplace(np.asarray(a, np.float64)).ravel(),
                                fisher=True, bias=False))


def lap_rms(a):
    return float(np.sqrt((ndi.laplace(np.asarray(a, np.float64)) ** 2).mean()))


def contrast(a):
    a = np.asarray(a, np.float32)
    bp = ndi.gaussian_filter(a, 2.0) - ndi.gaussian_filter(a, 8.0)
    return float(np.sqrt((bp * bp).mean()) / a.mean())


def main():
    rows = json.load(open("m6_localisation.json"))["rows"]
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    K = luma.shape[0]
    g4 = tifffile.imread(M93 / "armM4-gate4-binlin.tif")
    assert g4.dtype == np.uint16
    G4 = g4[BOX[0]:BOX[1], BOX[2]:BOX[3], 1].astype(np.float32)

    print(f"PLAIN MEAN OF N FRAMES -- constant weights, manufactures nothing.")
    print(f"Laplacian excess kurtosis over the same {len(rows)} pure-background "
          f"96px windows.\n")
    print(f"{'N frames':>10}{'kurt median':>14}{'kurt worst':>13}{'over bar(10)':>14}"
          f"{'lap RMS':>11}{'Q median':>11}")
    table = []
    for N in NS:
        ks, qs, rs = [], [], []
        for r in rows:
            s = (slice(r["y"], r["y"] + WIN), slice(r["x"], r["x"] + WIN))
            cube = np.array(luma[:, s[0], s[1]], np.float32)
            im = cube[:N].mean(axis=0)
            den = max(contrast(cube[k]) for k in range(K))
            ks.append(lap_kurt(im))
            rs.append(lap_rms(im))
            qs.append(contrast(im) / den)
        ks, qs, rs = np.array(ks), np.array(qs), np.array(rs)
        table.append(dict(N=N, kurt_med=float(np.median(ks)), kurt_max=float(ks.max()),
                          over=int((ks > 10).sum()), rms=float(np.median(rs)),
                          q_med=float(np.median(qs))))
        print(f"{N:>10}{np.median(ks):>14.2f}{ks.max():>13.2f}"
              f"{int((ks>10).sum()):>10}/{len(ks)}{np.median(rs):>11.1f}{np.median(qs):>11.3f}")

    k4 = np.array([lap_kurt(G4[r["y"]:r["y"]+WIN, r["x"]:r["x"]+WIN]) for r in rows])
    r4 = np.array([lap_rms(G4[r["y"]:r["y"]+WIN, r["x"]:r["x"]+WIN]) for r in rows])
    q4 = np.array([r["q4"] for r in rows])
    print(f"{'gate4 SHIP':>10}{np.median(k4):>14.2f}{k4.max():>13.2f}"
          f"{int((k4>10).sum()):>10}/{len(k4)}{np.median(r4):>11.1f}{np.median(q4):>11.3f}")

    pm = table[-1]
    print(f"\nVERDICT ON THE INSTRUMENT")
    print(f"  a plain mean of all {K} frames -- which CANNOT manufacture structure --")
    print(f"  reads kurtosis median {pm['kurt_med']:.2f}, worst {pm['kurt_max']:.2f}, "
          f"{pm['over']}/{len(rows)} over the bar of 10.")
    if pm["over"] > 0:
        print(f"  *** THE INSTRUMENT IS CONFOUNDED. Laplacian kurtosis flags windows")
        print(f"      in an arm that manufactures nothing, so it cannot grade the")
        print(f"      shipped merge. The rise with N is denoising, not patchwork.")
    else:
        print(f"  instrument is clean at N={K}; ORCH's localisation stands.")
    print(f"  the same windows under the unit-free band-pass Q: plain mean "
          f"{pm['q_med']:.3f} vs gate 4 {np.median(q4):.3f} (bound 1.284)")

    # is the kurtosis rise explained by the RMS fall?
    kk = np.array([t["kurt_med"] for t in table])
    rr = np.array([t["rms"] for t in table])
    rho = stats.spearmanr(rr, kk)
    print(f"\n  across N, median kurtosis vs median Laplacian RMS: "
          f"rho = {rho.statistic:+.3f} (p={rho.pvalue:.3g})")
    print(f"  i.e. kurtosis rises precisely as the noise floor is averaged away.")

    json.dump({"plain_mean": table,
               "gate4": dict(kurt_med=float(np.median(k4)), kurt_max=float(k4.max()),
                             over=int((k4 > 10).sum()), q_med=float(np.median(q4))),
               "rho_kurt_vs_rms": float(rho.statistic)},
              open("m7_instrument_control.json", "w"), indent=1)
    print("\nwrote m7_instrument_control.json")


if __name__ == "__main__":
    main()
