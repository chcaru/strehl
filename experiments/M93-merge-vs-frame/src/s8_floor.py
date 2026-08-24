"""S8 -- what the 74 cy/mm floor is.

M85 found a floor in the spectrum near 74 cy/mm and could not attribute it. The
optics still deliver 19-34% MTF there, so it is not the diffraction cutoff.

Hypothesis, from S0's geometry: green occupies half the CFA sites on a
checkerboard. That quincunx lattice can represent spatial frequencies only
inside a DIAMOND, |fx| + |fy| <= 0.5 cycles per sensor pixel. Its short radius
lies along the image diagonals at 0.25*sqrt(2) = 0.3536 cy/px = 69.2 cy/mm; its
long radius lies along the axes at 0.5 cy/px = 97.9 cy/mm. A radial average over
that boundary lands at 77.7 cy/mm.

The two candidate explanations make OPPOSITE predictions about shape, and the
shape is measurable:

    optics  ->  the floor is a CIRCLE. Isotropic. The frequency at which the
                spectrum stops decaying is the same along the axes and along
                the diagonals.

    lattice ->  the floor is a DIAMOND. Anisotropic by a factor of sqrt(2). The
                diagonals reach their floor at 0.354 cy/px while the axes are
                still decaying out to 0.5.

Controls:
  C1  the same measurement on a DEFOCUSED region. The optics deliver almost
      nothing there, so any anisotropy that survives is instrumental.
  C2  an isotropy null: white noise through the identical reduction must read
      no anisotropy.
  C3  a planted anisotropy the reduction must detect, with the sign it is given.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m93lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
N = 1024


def sector_psd(tile, nbins=192, half_deg=12.0):
    """Radial power profiles in the AXIS and DIAGONAL sectors of a square tile."""
    t = tile.astype(np.float64)
    n = t.shape[0]
    w = L.hann2(n)
    F = np.fft.fftshift(np.fft.fft2((t - t.mean()) * w))
    P = np.abs(F) ** 2 / (w**2).sum()
    fy = np.fft.fftshift(np.fft.fftfreq(n))[:, None]
    fx = np.fft.fftshift(np.fft.fftfreq(n))[None, :]
    R = np.hypot(fy, fx)
    TH = np.degrees(np.arctan2(fy, fx)) % 90.0  # 0..90, fourfold symmetric
    axis = np.minimum(TH, 90.0 - TH) <= half_deg
    diag = np.abs(TH - 45.0) <= half_deg
    edges = np.linspace(0.0, 0.5, nbins + 1)
    idx = np.digitize(R.ravel(), edges) - 1
    ok = (idx >= 0) & (idx < nbins)
    prof = {}
    for nm, m in (("axis", axis), ("diag", diag)):
        sel = ok & m.ravel()
        tot = np.bincount(idx[sel], weights=P.ravel()[sel], minlength=nbins)
        cnt = np.bincount(idx[sel], minlength=nbins)
        with np.errstate(invalid="ignore", divide="ignore"):
            prof[nm] = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    return 0.5 * (edges[:-1] + edges[1:]), prof


def anisotropy(f, pr, cut_lo=0.38, cut_hi=0.46, ref_lo=0.10, ref_hi=0.20):
    """Diagonal-to-axis power ratio in the cut band, normalised by the same
    ratio at low frequency.

    The normalisation removes whatever anisotropy the SCENE has, which is
    arbitrary. What is left is anisotropy introduced between the reference band
    and the cut band.

        planted diamond (quincunx lattice) -> A near 0
        planted circle  (diffraction)      -> A near 1
    """
    def band(p, lo, hi):
        m = (f >= lo) & (f < hi) & np.isfinite(p)
        return float(np.nanmean(p[m]))

    cut = band(pr["diag"], cut_lo, cut_hi) / band(pr["axis"], cut_lo, cut_hi)
    ref = band(pr["diag"], ref_lo, ref_hi) / band(pr["axis"], ref_lo, ref_hi)
    return cut / ref, cut, ref


def knee(f, p, lo=0.15, hi=0.495):
    """Frequency at which the profile has fallen to within 1.15x of its own
    floor, the floor being the median over the top 4% of the band.

    RETIRED as the anisotropy statistic: control C3 handed it a planted diamond
    whose true axis/diag ratio is 1.414 and it read 0.973, indistinguishable
    from the 0.979 it read on a planted circle. It degenerates because a hard
    spectral cut makes the floor identically zero, so `1.15 * floor` is passed
    by every bin. Kept, and kept reported, because a retired instrument is a
    result. `anisotropy` replaces it.
    """
    m = (f >= lo) & (f <= hi) & np.isfinite(p)
    fl = float(np.nanmedian(p[(f >= 0.48) & np.isfinite(p)]))
    q = p[m]
    ff = f[m]
    above = np.where(q > 1.15 * fl)[0]
    if above.size == 0:
        return float("nan"), fl
    return float(ff[above.max()]), fl


def main() -> int:
    opt = json.load(open(os.path.join(OUTDIR, "s0_optics.json"), encoding="utf-8"))
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))["chosen"]
    focus = json.load(open(os.path.join(OUTDIR, "s3_focus.json"), encoding="utf-8"))["res"]
    armf = json.load(open(os.path.join(OUTDIR, "s4_armF.json"), encoding="utf-8"))
    pitch = opt["pitch_um"]
    cymm = 1000.0 / pitch  # multiply cy/sensor-px by this
    print(f"pitch {pitch:.4f} um  ->  1.0 cy/sensor-px = {cymm:.2f} cy/mm")
    print(f"quincunx diamond: diag {0.25*np.sqrt(2)*cymm:.2f} cy/mm, axis {0.5*cymm:.2f} cy/mm")

    rng = np.random.default_rng(9308)
    out = {}

    # ---- C2: isotropy null ----
    print()
    print("=" * 78)
    print("C2 -- isotropy null: white noise must read no anisotropy")
    print("=" * 78)
    f, pr = sector_psd(rng.normal(0, 100.0, (N, N)))
    band = (f > 0.25) & (f < 0.45)
    a = float(np.nanmean(pr["axis"][band]))
    d = float(np.nanmean(pr["diag"][band]))
    print(f"  white noise  axis {a:9.1f}  diag {d:9.1f}  ratio {d/a:.4f}  "
          f"({'PASS' if abs(d/a - 1) < 0.05 else 'FAIL'}, bar 5%)")
    out["C2"] = dict(axis=a, diag=d, ratio=d / a)

    # ---- C3: planted anisotropy ----
    print()
    print("=" * 78)
    print("C3 -- planted anisotropy: a diamond-shaped cut the reduction must see")
    print("=" * 78)
    z = rng.normal(0, 100.0, (N, N))
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.fftfreq(N)[None, :]
    # The quincunx diamond is |fx| + |fy| <= 0.5 cy/sensor-px. Its DIAGONAL
    # radius is 0.5/sqrt(2) = 0.3536 and its AXIS radius is 0.5. The first
    # attempt at this control planted |fx| + |fy| <= 0.3536, a diamond of
    # diagonal radius 0.25, which put the whole cut band outside BOTH sectors;
    # the circle arm then read A = 0.484 instead of 1 and C3 failed. That was a
    # defect in the control, not in the statistic, and it is reported as one.
    diamond = (np.abs(fy) + np.abs(fx)) <= 0.5
    zc = np.fft.ifft2(np.fft.fft2(z) * diamond).real
    f, pr = sector_psd(zc)
    Ad, cutd, refd = anisotropy(f, pr)
    ka, _ = knee(f, pr["axis"])
    kd, _ = knee(f, pr["diag"])
    # Two circular controls: a hard circular cut at the diamond's LONG radius,
    # and a smooth isotropic rolloff of diffraction shape. Both must read A = 1.
    z2 = np.fft.ifft2(np.fft.fft2(z) * (np.hypot(fy, fx) <= 0.5)).real
    f2, pr2 = sector_psd(z2)
    Ac, cutc, refc = anisotropy(f2, pr2)
    ka2, _ = knee(f2, pr2["axis"])
    kd2, _ = knee(f2, pr2["diag"])
    nu = np.minimum(np.hypot(fy, fx) / 0.45, 1.0)
    hdiff = 2 / np.pi * (np.arccos(nu) - nu * np.sqrt(np.maximum(1 - nu**2, 0)))
    z3 = np.fft.ifft2(np.fft.fft2(z) * hdiff).real
    f3, pr3 = sector_psd(z3)
    Ao, _, _ = anisotropy(f3, pr3)
    print(f"  planted DIAMOND (quincunx)      : A = {Ad:.4f}   "
          f"[retired knee stat: axis/diag {ka/kd:.3f}]")
    print(f"  planted CIRCLE  (hard cut)      : A = {Ac:.4f}   "
          f"[retired knee stat: axis/diag {ka2/kd2:.3f}]")
    print(f"  planted CIRCLE  (diffraction)   : A = {Ao:.4f}")
    print(f"  separation on A                  : {Ac/max(Ad,1e-12):.1f}x  "
          f"(the retired knee statistic separated the same two by "
          f"{max(ka/kd, ka2/kd2)/min(ka/kd, ka2/kd2):.3f}x)")
    ok3 = Ad < 0.5 and Ac > 0.7 and Ao > 0.7
    print(f"  C3 VERDICT: {'PASS' if ok3 else 'FAIL'}   "
          f"(bars: diamond A < 0.5, both circles A > 0.7)")
    out["C3"] = dict(diamond_A=Ad, circle_hard_A=Ac, circle_diffraction_A=Ao,
                     diamond_knee_ratio=ka / kd, circle_knee_ratio=ka2 / kd2,
                     verdict="PASS" if ok3 else "FAIL")
    assert ok3, "C3 positive control failed; the statistic cannot see the effect"

    # ---- C2b: does the reduction read isotropy on a real, unaliased scene? ----
    print()
    print("=" * 78)
    print("C2b -- the same statistic on the BINNED plane, which has no quincunx")
    print("=" * 78)
    print("  the binned plane averages G1 and G2 to one sample per 2x2 quad, so it")
    print("  is a plain square lattice. If A is a quincunx signature it must be")
    print("  absent here.")
    binlin = {}
    for nm in list(rois):
        pk = focus[nm]["peak_frame"]
        cand = sorted((k for k in armf["binlin"]), key=lambda s: abs(int(s) - pk))
        tif = armf["binlin"][cand[0]]["tif"]
        g = L.read_tif_green(tif)
        x0, y0 = rois[nm]["x"], rois[nm]["y"]
        tile = g[y0 : y0 + 512, x0 : x0 + 512]
        fb, prb = sector_psd(tile)
        Ab, _, _ = anisotropy(fb, prb)
        binlin[nm] = dict(frame=int(cand[0]), A=Ab)
        print(f"  {nm:<14} (frame {cand[0]}) binned-plane A = {Ab:.4f}")
    out["C2b_binned"] = binlin

    # ---- the real thing ----
    print()
    print("=" * 78)
    print("MEASURED -- demosaiced single frame, full sensor grid")
    print("=" * 78)
    res = {}
    for nm in list(rois):
        pk = focus[nm]["peak_frame"]
        # Demosaic renders exist for the three detail peaks only; the flat ROI
        # is read off the nearest rendered frame, which is honest because it has
        # no focus structure to lose (S3: 1.18x contrast over 299 frames).
        cand = sorted(armf["demosaic"], key=lambda s: abs(int(s) - pk))
        idx = cand[0]
        tif = armf["demosaic"][idx]["tif"]
        import tifffile

        img = tifffile.imread(tif)
        g = img[:, :, 1].astype(np.float64)
        x0, y0 = rois[nm]["x"] * 2, rois[nm]["y"] * 2
        tile = g[y0 : y0 + N, x0 : x0 + N]
        f, pr = sector_psd(tile)
        A, cut, ref = anisotropy(f, pr)
        ka, fla = knee(f, pr["axis"])
        kd, fld = knee(f, pr["diag"])
        print(f"  {nm:<14} (frame {idx})  A = {A:.4f}   "
              f"[diag/axis in cut band {cut:.4f}, in reference band {ref:.4f}]")
        res[nm] = dict(frame=int(idx), A=A, cut=cut, ref=ref,
                       knee_axis=ka, knee_diag=kd, floor_axis=fla, floor_diag=fld,
                       axis=[float(v) for v in pr["axis"]],
                       diag=[float(v) for v in pr["diag"]],
                       f=[float(v) for v in f])
    out["measured"] = res

    print()
    print("  PREDICTIONS:  quincunx lattice -> A near 0 ;  optics/diffraction -> A near 1")
    dets = [n for n in res if n != "ROI-FLAT"]
    print(f"  MEASURED   :  detail ROIs {[round(res[n]['A'],3) for n in dets]}, "
          f"flat control {res['ROI-FLAT']['A']:.3f}")

    # ---- does the high-frequency plateau follow focus? ----
    print()
    print("=" * 78)
    print("PLATEAU vs FOCUS -- is the floor aliased scene detail, or fixed?")
    print("=" * 78)
    print("  aliased detail -> the plateau tracks the through-focus curve")
    print("  fixed artifact -> the plateau is flat across the stack")
    cube = np.load(os.path.join(L.OUT, "m93_crops_v2.npy"), mmap_mode="r")
    pf = {}
    for nm in ("ROI-LOWDRIFT", "ROI-FLAT"):
        k = list(rois).index(nm)
        pk = focus[nm]["peak_frame"]
        idxs = sorted({0, pk - 60, pk - 30, pk - 15, pk, pk + 15, pk + 30, pk + 60, 298})
        idxs = [i for i in idxs if 0 <= i < cube.shape[0]]
        vals = []
        for i in idxs:
            t = np.asarray(cube[i, k], dtype=np.float64)
            ff, pp, _ = L.radial_psd(t)
            hi = float(np.nanmean(pp[(ff > 0.42) & (ff < 0.49)]))
            mid = float(np.nanmean(pp[(ff > 0.15) & (ff < 0.25)]))
            vals.append((i, hi, mid))
        base = min(v[1] for v in vals)
        print(f"  {nm}")
        for i, hi, mid in vals:
            print(f"     frame {i:3d}  hi-f plateau {hi:11.1f} ({hi/base:5.2f}x min)   "
                  f"mid-band {mid:12.1f}")
        pf[nm] = dict(frames=[v[0] for v in vals], hi=[v[1] for v in vals],
                      mid=[v[2] for v in vals], span=max(v[1] for v in vals) / base)
        print(f"     hi-f plateau spans {pf[nm]['span']:.2f}x across the stack")
    out["plateau_vs_focus"] = pf

    dst = os.path.join(OUTDIR, "s8_floor.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
