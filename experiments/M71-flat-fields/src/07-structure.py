"""M71 step 07 -- spatial character of the fixed pattern, scale invariance,
dust, and inter-pixel correlation.

Three independent discriminators between per-photosite PRNU and resolved
subject texture, none of which relies on the two-green cancellation argument
being exact:

1. SCALE. Recompute kappa with the high-pass box swept 15 -> 241 px. White
   per-pixel PRNU is unaffected by where the smooth surface is cut. Paper
   fibre, correlated over tens of microns, feeds in as the cut widens.

2. SPECTRUM. The CROSS-spectrum between the two independent 20-frame halves
   kills the temporal noise (independent realisations) and leaves only the
   fixed pattern. Flat in spatial frequency = white = per-photosite. Falling =
   correlated structure. Method borrowed from M5 (facts 27, 29): Hann-windowed
   Welch periodograms, radially averaged. M5's §2.5 trap -- a boxcar's sinc
   sidelobes inflate the floor 1.6-1.8x and fake a knee -- applies verbatim
   here, so Hann it is.

3. The same cross-spectrum computed against the SHARPEST sweep frame, where
   paper is fully resolved, gives the paper spectrum for contrast.

Plus a dust map (PR-7) and the inter-pixel correlation that a PTC gain needs
if charge sharing is moving variance between neighbours.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "out" / "cache"
OUT = HERE / "data" / "07-structure.json"
BLACK = 512.0

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "k5", Path(__file__).resolve().parent / "05-kappa.py")
_k5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_k5)
smooth, highpass_response = _k5.smooth, _k5.highpass_response

PAIRS = [("e0.004-A", "e0.004-B"), ("e0.008-A", "e0.008-B"),
         ("e0.016666666666666666-A", "e0.016666666666666666-B"),
         ("e0.03333333333333333-A", "e0.03333333333333333-B"),
         ("e0.05-A", "e0.05-B")]


def resid_at(tag, plane, box, npass):
    m = np.load(CACHE / f"{tag}-{plane}-mean.npy")
    return _k5.residual(m, box, npass)


# ---------------------------------------------------------------- 1. scale
def scale_sweep(out):
    print("=== 1. SCALE INVARIANCE of kappa (high-pass cut swept 16x)")
    print("    White per-pixel PRNU does not care where the smooth surface is")
    print("    cut. Correlated paper texture does.")
    rows = {}
    for box in (15, 31, 61, 121, 241):
        F = highpass_response(box=box)
        ks = []
        for ta, tb in PAIRS:
            da = resid_at(ta, "G1", box, 3) - resid_at(ta, "G2", box, 3)
            db = resid_at(tb, "G1", box, 3) - resid_at(tb, "G2", box, 3)
            a, b = da.ravel(), db.ravel()
            cov = float(np.mean(a * b) - np.mean(a) * np.mean(b)) / F
            ks.append(np.sqrt(max(cov, 0.0) / 2.0))
        k = float(np.sqrt(np.mean(np.square(ks))))
        rows[box] = {"kappa": k, "F": F, "per_pair": [float(x) for x in ks]}
        print(f"    box {box:4d} px (sigma ~{0.5 * np.sqrt(3 * (box * box - 1) / 12):5.1f} px):  "
              f"kappa = {k * 100:.4f}%   F = {F:.5f}   "
              + " ".join(f"{x * 100:.3f}" for x in ks))
    kk = np.array([rows[b]["kappa"] for b in rows])
    span = kk.max() / kk.min()
    print(f"    kappa spans {span:.4f}x over a 16x change in cut scale "
          f"({kk.min() * 100:.4f}% .. {kk.max() * 100:.4f}%)")
    out["scale"] = {"rows": {str(b): rows[b] for b in rows}, "span": float(span)}
    return rows


# ------------------------------------------------------------- 2. spectrum
def radial_cross_spectrum(a, b, tile=256, stride=352):
    """Hann-windowed Welch cross-periodogram of two maps, radially averaged.

    Independent temporal-noise realisations in a and b make the expected
    cross-spectrum of the noise zero, so what is left is the fixed pattern
    with no floor subtraction anywhere.
    """
    h, w = a.shape
    win = np.outer(np.hanning(tile), np.hanning(tile)).astype(np.float32)
    wnorm = float(np.mean(win * win))
    fy = np.fft.fftfreq(tile)[:, None]
    fx = np.fft.rfftfreq(tile)[None, :]
    r = np.sqrt(fy * fy + fx * fx)
    nb = 48
    idx = np.clip((r / 0.5 * nb).astype(int), 0, nb - 1)
    acc = np.zeros(nb)
    cnt = np.zeros(nb)
    n = 0
    for y in range(0, h - tile, stride):
        for x in range(0, w - tile, stride):
            ta = (a[y:y + tile, x:x + tile] - a[y:y + tile, x:x + tile].mean()) * win
            tb = (b[y:y + tile, x:x + tile] - b[y:y + tile, x:x + tile].mean()) * win
            cs = np.real(np.fft.rfft2(ta) * np.conj(np.fft.rfft2(tb)))
            np.add.at(acc, idx.ravel(), cs.ravel())
            np.add.at(cnt, idx.ravel(), 1.0)
            n += 1
    prof = acc / np.maximum(cnt, 1) / (tile * tile * wnorm) / n
    freqs = (np.arange(nb) + 0.5) / nb * 0.5
    return freqs, prof, n


def spectra(out):
    print("\n=== 2. SPECTRUM of the fixed pattern (M5 method: Hann Welch,")
    print("       radially averaged; cross-spectrum so no floor is subtracted)")
    ta, tb = "e0.05-A", "e0.05-B"
    da = np.load(CACHE / f"{ta}-Dgreen.npy")
    db = np.load(CACHE / f"{tb}-Dgreen.npy")
    f, p_prnu, ntile = radial_cross_spectrum(da, db)
    print(f"    {ntile} tiles of 256x256 per map")

    # the same, against the sharpest in-focus sweep frame -> paper spectrum
    ds = np.load(CACHE / "sweep-subject-focus-sweep-no-cpl-sharp.npy")
    # auto-spectrum of the sharp frame carries paper + PRNU + white noise;
    # its cross-spectrum with an independent flat carries only PRNU.
    _, p_sharp, _ = radial_cross_spectrum(ds, ds)
    _, p_common, _ = radial_cross_spectrum(ds, da)

    # normalise each to its own value in the lowest measured bin
    print("\n    f (cyc/px)   PRNU cross(A,B)   sharp-frame auto   common(sharp,flat)")
    print("                  [normalised to the first bin of each]")
    keep = (f > 0.02) & (f < 0.5)
    n0 = p_prnu[keep][0]
    n1 = p_sharp[keep][0]
    n2 = p_common[keep][0]
    for i in np.where(keep)[0][::4]:
        print(f"    {f[i]:8.4f}      {p_prnu[i] / n0:9.4f}          "
              f"{p_sharp[i] / n1:9.4f}         {p_common[i] / n2:9.4f}")

    # flatness: ratio of the top-quartile mean to the bottom-quartile mean
    def flatness(p):
        k = np.where(keep)[0]
        lo = p[k[:len(k) // 4]].mean()
        hi = p[k[-len(k) // 4:]].mean()
        return float(hi / lo)

    fl_prnu, fl_sharp = flatness(p_prnu), flatness(p_sharp)
    fl_common = flatness(p_common)
    print(f"\n    flatness (top-quartile mean / bottom-quartile mean):")
    print(f"      PRNU cross-spectrum (flats A x B)     {fl_prnu:8.4f}   "
          f"{'WHITE' if 0.5 < fl_prnu < 2.0 else 'NOT WHITE'}")
    print(f"      in-focus sweep frame auto-spectrum    {fl_sharp:8.4f}   "
          f"{'WHITE' if 0.5 < fl_sharp < 2.0 else 'NOT WHITE -- correlated structure'}")
    print(f"      common(sharp sweep, flat)             {fl_common:8.4f}   "
          f"{'WHITE' if 0.5 < fl_common < 2.0 else 'NOT WHITE'}")
    out["spectra"] = {"freq": f.tolist(), "prnu_cross": p_prnu.tolist(),
                      "sharp_auto": p_sharp.tolist(), "common": p_common.tolist(),
                      "n_tiles": ntile, "flatness_prnu": fl_prnu,
                      "flatness_sharp_auto": fl_sharp, "flatness_common": fl_common}


# ------------------------------------------------------------------ 3. dust
def dust(out):
    print("\n=== 3. PR-7 DUST MAP (fixed in sensor coordinates)")
    maps = {}
    for tag in ("e0.05-A", "e0.05-B"):
        acc = None
        for pl in ("R", "G1", "G2", "B"):
            m = np.load(CACHE / f"{tag}-{pl}-mean.npy")
            r = m / smooth(m, 61, 3) - np.float32(1.0)
            acc = r if acc is None else acc + r
        maps[tag] = acc / 4.0
    a, b = maps["e0.05-A"], maps["e0.05-B"]
    N = a.size
    ta = a < -0.03
    tb = b < -0.03
    n_a, n_b = int(ta.sum()), int(tb.sum())
    seed = ta & tb
    n_seed = int(seed.sum())
    # The correct null is the CHANCE COINCIDENCE rate, not min() of a rolled
    # pair -- min() of two uncorrelated maps is biased low by construction and
    # the first version of this control failed for that reason, not for a
    # physical one.
    chance = n_a * n_b / N
    n_roll = int((ta & np.roll(tb, 314, axis=0)).sum())
    print(f"    pixels below -3% in A: {n_a}   in B: {n_b}   of {N}")
    print(f"    coincident in BOTH CPL states:              {n_seed}")
    print(f"    expected by chance if independent:          {chance:.1f}"
          f"   -> enrichment {n_seed / max(chance, 1e-9):.0f}x")
    print(f"    ROLL CONTROL (B rolled 314 rows, CFA phase preserved): {n_roll}"
          f"   -> {'PASS' if n_roll < 0.1 * n_seed else 'FAIL'}")

    per_plane_ok = np.zeros(a.shape, dtype=np.int8)
    for pl in ("R", "G1", "G2", "B"):
        acc = None
        for tag in ("e0.05-A", "e0.05-B"):
            m = np.load(CACHE / f"{tag}-{pl}-mean.npy")
            r = m / smooth(m, 61, 3) - np.float32(1.0)
            acc = r if acc is None else np.minimum(acc, r)
        per_plane_ok += (acc < -0.015).astype(np.int8)
    hit = seed & (per_plane_ok >= 3)
    n_hit = int(hit.sum())
    frac = n_hit / N
    depths = np.minimum(a, b)[hit]
    print(f"    confirmed (also < -1.5% in >= 3 of 4 planes): {n_hit}"
          f"   = {frac * 100:.5f}% of the plane")
    print(f"    depth: median {np.median(depths) * 100:.2f}%, "
          f"worst {depths.min() * 100:.2f}%")
    cov = smooth(hit.astype(np.float32), 31, 1) > 0
    print(f"    area within ~15 px of a confirmed defect: {cov.mean() * 100:.4f}% "
          f"of the plane")
    # how deep does the WORST 61x61 neighbourhood go? that is the scale a
    # flat-field correction would actually have to fix.
    blur = smooth(np.minimum(a, b), 15, 1)
    print(f"    worst 15x15-averaged residual anywhere in the frame: "
          f"{blur.min() * 100:.3f}%")
    print("    CAVEAT: shot at f/5.6. Dust shadows sharpen and deepen as the")
    print("    aperture stops down, and the corpus shoots f/8-f/11, so this is")
    print("    a LOWER bound on what those stacks carry.")
    out["dust"] = {"n_below_A": n_a, "n_below_B": n_b, "n_seed": n_seed,
                   "chance_coincidence": float(chance),
                   "enrichment": float(n_seed / max(chance, 1e-9)),
                   "n_rolled": n_roll, "roll_pass": bool(n_roll < 0.1 * n_seed),
                   "n_confirmed": n_hit, "frac": frac,
                   "median_depth": float(np.median(depths)),
                   "worst_depth": float(depths.min()),
                   "area_within_15px": float(cov.mean()),
                   "worst_15x15_mean": float(blur.min())}
    np.save(CACHE / "dust-mask.npy", hit)


# ------------------------------------------- 4. inter-pixel correlation (IPC)
def ipc(out, rows):
    print("\n=== 4. INTER-PIXEL CORRELATION -- does charge sharing bias the PTC?")
    print("    A frame difference removes every fixed pattern and leaves 2x the")
    print("    temporal noise. Its autocorrelation at small CFA lags is charge")
    print("    sharing (brighter-fatter / IPC), which moves variance out of the")
    print("    per-pixel term and biases a PTC gain LOW.")
    import csv
    from fractions import Fraction
    src = list(csv.DictReader((HERE / "data" / "exif-all.csv").open(encoding="utf-8-sig")))
    grp = sorted([r for r in src if Path(r["Directory"]).name == "flat-fields"
                  and abs(float(Fraction(r["ExposureTime"])) - 0.05) < 1e-6],
                 key=lambda r: r["SubSecDateTimeOriginal"])
    assert len(grp) == 40, len(grp)
    fs = []
    for r in (grp[8], grp[9]):
        with rawpy.imread(r["SourceFile"]) as raw:
            fs.append(raw.raw_image_visible.astype(np.float32).copy())   # rule 32
    d = fs[0] - fs[1]
    res = {}
    for name, sl in (("G1", (slice(0, None, 2), slice(1, None, 2))),
                     ("G2", (slice(1, None, 2), slice(0, None, 2)))):
        p = d[sl][200:-200, 200:-200]
        p = p - p.mean()
        v0 = float(np.mean(p * p))
        lags = {}
        for (dy, dx) in ((0, 1), (1, 0), (1, 1), (0, 2), (2, 0)):
            q = p[dy:, dx:] if (dy or dx) else p
            pp = p[:q.shape[0], :q.shape[1]]
            lags[f"{dy},{dx}"] = float(np.mean(pp * q) / v0)
        res[name] = {"var": v0, "acf": lags}
        print(f"    {name}: var(diff) = {v0:8.2f} DN^2   "
              + "  ".join(f"r({k})={v:+.5f}" for k, v in lags.items()))
    # cross-green noise correlation (fact 895/958 says ~ +0.073)
    g1 = d[0::2, 1::2][200:-200, 200:-200]
    g2 = d[1::2, 0::2][200:-200, 200:-200]
    g1 = g1 - g1.mean()
    g2 = g2 - g2.mean()
    rho = float(np.mean(g1 * g2) / np.sqrt(np.mean(g1 * g1) * np.mean(g2 * g2)))
    print(f"    rho(G1 noise, G2 noise) = {rho:+.5f}   "
          f"(corpus facts 895/958 say ~ +0.073)")
    # total correlated fraction: sum of the 4 nearest CFA neighbours in-plane
    for name in res:
        s = 2 * (res[name]["acf"]["0,1"] + res[name]["acf"]["1,0"])
        print(f"    {name}: sum of 4 in-plane nearest-neighbour ACF = {s:+.5f}  "
              f"-> PTC gain bias {100 * s:+.3f}%")
        res[name]["nn_sum"] = s
    out["ipc"] = {"planes": res, "rho_g1g2_noise": rho,
                  "frames": [Path(grp[8]["FileName"]).name, Path(grp[9]["FileName"]).name]}


def main() -> None:
    out = {}
    rows = scale_sweep(out)
    spectra(out)
    dust(out)
    ipc(out, rows)
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
