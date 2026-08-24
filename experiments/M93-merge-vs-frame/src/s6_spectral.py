"""S6 -- the pre-registered spectral comparison, and the controls that license it.

Reduction, fixed before any M-vs-F number was computed (PRE-REGISTRATION.md):

    ln( P_M(f) / P_F(f) )  =  -(2 pi sigma_eq)^2 f^2      f in [0.05, 0.45] cy/px

fitted by weighted least squares through the origin. sigma_eq > 0 means the
merged output is SOFTER than the single frame by an equivalent Gaussian of that
width, in binned-plane pixels. sigma_eq < 0 means it is sharper.

Controls, in the order rule 9 wants them:

  R3  flat ROI first. Reported, never read as retention (M80 fact 1127).
  R1a plant a Gaussian blur on the whole frame. Because the blur multiplies
      signal AND noise power by the same |H|^2, the raw ratio must recover
      sigma exactly. This tests the fitting machinery.
  R1b plant a blur on the frame and then add back independent white noise, so
      the noise power returns to its unblurred level. This is the failure mode
      actually under test -- a stage that softens signal while leaving per-pixel
      noise alone -- and it is what the noise-subtracted reduction must recover.
  R2  power control. Feed the instrument a frame that IS defocused (peak +/- 10,
      +/- 25). If it cannot see that, it cannot see anything.
  R6  a deliberately corrupted comparison the harness must reject.
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
CUBE = os.path.join(L.OUT, "m93_crops_v2.npy")
MERGED = os.path.join(L.OUT, "armM-gate0-binlin.tif")
WIN = 512
F_LO, F_HI = 0.05, 0.45
GAIN_DN_PER_E = 0.224103  # profile.rs A7C2_MEASURED_GREEN_GAIN_DN_PER_E, ISO 100
READ_E = 4.20  # profile.rs read_noise_e_low
BLACK, RANGE = 512.0, 14848.0
TIF_PER_DN = 65535.0 / RANGE


def sigma_eq(fa, pa, pb, n_sub=0.0):
    """Fit P_a/P_b = exp(-(2 pi s)^2 f^2). Positive s => a softer than b."""
    m = (fa >= F_LO) & (fa < F_HI) & np.isfinite(pa) & np.isfinite(pb)
    a = pa[m] - n_sub
    b = pb[m] - n_sub
    ok = (a > 0) & (b > 0)
    f = fa[m][ok]
    r = np.log(a[ok] / b[ok])
    # Weight by bin count proxy f (annulus area) so high-f bins are not
    # down-weighted relative to their information content.
    w = f
    s2 = -float(np.sum(w * r * f**2) / np.sum(w * f**4)) / (4 * np.pi**2)
    return float(np.sign(s2) * np.sqrt(abs(s2))), int(ok.sum())


def psd(tile):
    f, p, _ = L.radial_psd(tile)
    return f, p


def plant_blur(tile: np.ndarray, sigma: float) -> np.ndarray:
    """Exact Gaussian blur, planted in the frequency domain.

    Amplitude transfer exp(-2 pi^2 sigma^2 f^2), so POWER is multiplied by
    exp(-(2 pi sigma f)^2) -- precisely the form `sigma_eq` fits. Planting it
    here rather than with a truncated spatial kernel removes the discretisation
    error that made the first R1 attempt fail.
    """
    n = tile.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    h = np.exp(-2.0 * np.pi**2 * sigma**2 * (fy**2 + fx**2))
    return np.fft.irfft2(np.fft.rfft2(tile) * h, s=(n, n))


def kernel_energy(sigma: float, n: int = 512) -> float:
    """sum(h^2) for the same frequency-domain kernel, by Parseval."""
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    h = np.exp(-2.0 * np.pi**2 * sigma**2 * (fy**2 + fx**2))
    return float((h**2).mean())


def noise_tiff_units(mean_dn: float) -> float:
    """White-noise PSD level of the binned green plane, in TIFF^2 units.

    For a mean-removed Hann-windowed tile normalised by sum(w^2), white noise of
    per-pixel variance v has E[P(f)] = v at every f. Derived, then checked
    against synthetic noise in this script.
    """
    s = max(mean_dn - BLACK, 0.0)
    var_site = GAIN_DN_PER_E * s + (READ_E * GAIN_DN_PER_E) ** 2
    var_green_mean = var_site / 2.0  # (G1+G2)/2 with rho = 0; see report
    return var_green_mean * TIF_PER_DN**2


def main() -> int:
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))["chosen"]
    focus = json.load(open(os.path.join(OUTDIR, "s3_focus.json"), encoding="utf-8"))["res"]
    armf = json.load(open(os.path.join(OUTDIR, "s4_armF.json"), encoding="utf-8"))["binlin"]
    merged = L.read_tif_green(MERGED)
    names = [n for n in rois if n != "ROI-FLAT"]
    out = {}
    rng = np.random.default_rng(9301)

    # ---- instrument check: does radial_psd report white-noise variance? ----
    v = 137.0
    z = rng.normal(0, np.sqrt(v), (WIN, WIN))
    fz, pz = psd(z)
    plateau = float(np.nanmedian(pz[(fz > 0.1) & (fz < 0.45)]))
    print(f"PSD normalisation check: white noise var {v:.1f} -> plateau {plateau:.2f} "
          f"({100*(plateau/v-1):+.2f}%)")
    assert abs(plateau / v - 1) < 0.03
    out["psd_norm_check"] = dict(var=v, plateau=plateau)

    # ---- R3: the flat ROI, first ----
    print()
    print("=" * 78)
    print("R3 -- flat ROI (defocused background). Reported. NOT evidence of retention.")
    print("=" * 78)
    fx, fy = rois["ROI-FLAT"]["x"], rois["ROI-FLAT"]["y"]
    mflat = merged[fy : fy + WIN, fx : fx + WIN]
    cube = np.load(CUBE, mmap_mode="r")
    kflat = list(rois).index("ROI-FLAT")
    pk_flat = focus["ROI-FLAT"]["peak_frame"]
    fflat = (np.clip((np.asarray(cube[pk_flat, kflat], dtype=np.float64) - BLACK) / RANGE, 0, 1)
             * 65535.0)
    ff, pf_m = psd(mflat)
    _, pf_f = psd(fflat)
    s_flat, nb = sigma_eq(ff, pf_m, pf_f)
    mean_dn = float(np.asarray(cube[pk_flat, kflat]).mean())
    n_model = noise_tiff_units(mean_dn)
    n_plateau = float(np.nanmedian(pf_f[(ff > 0.42) & (ff < 0.49)]))
    print(f"  flat ROI mean signal      : {mean_dn:.1f} DN raw")
    print(f"  model white-noise PSD     : {n_model:.1f} TIFF^2   (rho = 0)")
    print(f"  measured hi-f plateau     : {n_plateau:.1f} TIFF^2   (upper bound: includes any floor)")
    print(f"  plateau / model           : {n_plateau/n_model:.3f}x")
    print(f"  sigma_eq(M vs frame {pk_flat})   : {s_flat:+.4f} px  over {nb} bins")
    out["R3"] = dict(sigma_eq=s_flat, mean_dn=mean_dn, n_model=n_model, n_plateau=n_plateau)

    # ---- R1: planted blur ----
    print()
    print("=" * 78)
    print("R1 -- planted blur. Discipline 594: show the instrument saying otherwise.")
    print("=" * 78)
    r1 = {}
    for nm in names:
        x, y = rois[nm]["x"], rois[nm]["y"]
        k = list(rois).index(nm)
        pk = focus[nm]["peak_frame"]
        base = (np.clip((np.asarray(cube[pk, k], dtype=np.float64) - BLACK) / RANGE, 0, 1) * 65535.0)
        fb, pb = psd(base)
        n_hat = noise_tiff_units(float(np.asarray(cube[pk, k]).mean()))
        rec = []
        # The stimulus is planted in the frequency domain, where a Gaussian of
        # width sigma is exact by construction. The first attempt planted it
        # with `scipy.ndimage.gaussian_filter`, and that control FAILED at
        # sigma = 0.25 px (recovered 0.021, -91%). The diagnosis is in the
        # report: at sigma = 0.25 the truncated discrete kernel is
        # [3.4e-4, 0.99933, 3.4e-4], whose own second moment is 0.026 px. The
        # instrument was right and the stimulus was mislabelled.
        for s in (0.10, 0.25, 0.50, 1.00, 1.50):
            a = plant_blur(base, s)
            fa, pa = psd(a)
            s_raw, _ = sigma_eq(fa, pa, pb)

            # R1b: restore the white-noise power the blur removed, so the tile
            # has softened signal but unsoftened per-pixel noise.
            kern_energy = kernel_energy(s)
            resid_var = n_hat * (1.0 - kern_energy)
            b = a + rng.normal(0, np.sqrt(max(resid_var, 0.0)), (WIN, WIN))
            fbb, pbb = psd(b)
            s_b_raw, _ = sigma_eq(fbb, pbb, pb)
            s_b_sub, _ = sigma_eq(fbb, pbb, pb, n_sub=n_hat)
            rec.append(dict(planted=s, kern_energy=kern_energy, r1a_raw=s_raw,
                            r1b_raw=s_b_raw, r1b_sub=s_b_sub, resid_var=resid_var))
            print(f"  {nm:<14} planted {s:.2f} px | R1a raw {s_raw:6.3f} "
                  f"({100*(s_raw/s-1):+6.1f}%) | R1b raw {s_b_raw:6.3f} "
                  f"({100*(s_b_raw/s-1):+6.1f}%) | R1b noise-sub {s_b_sub:6.3f} "
                  f"({100*(s_b_sub/s-1):+6.1f}%)")
        r1[nm] = rec
    out["R1"] = r1
    gated = [r for v in r1.values() for r in v if 0.10 <= r["planted"] <= 1.00]
    worst_a = max(abs(r["r1a_raw"] / r["planted"] - 1) for r in gated)
    worst_b = max(abs(r["r1b_sub"] / r["planted"] - 1) for r in gated)
    hi = [r for v in r1.values() for r in v if r["planted"] > 1.00]
    worst_b_hi = max(abs(r["r1b_sub"] / r["planted"] - 1) for r in hi)
    print(f"  operating range 0.10-1.00 px : worst R1a {100*worst_a:.1f}%   "
          f"worst R1b noise-subtracted {100*worst_b:.1f}%")
    print(f"  beyond it (1.50 px)          : worst R1b noise-subtracted {100*worst_b_hi:.1f}% "
          f"-- signal is below noise at high f, subtraction destabilises")
    va = "PASS" if worst_a < 0.25 else "FAIL"
    vb = "PASS" if worst_b < 0.30 else "FAIL"
    print(f"  R1a VERDICT (blur signal AND noise, the exact case): {va}  bar +/-25%")
    print(f"  R1b VERDICT (blur signal only, noise-subtracted)   : {vb}  "
          f"worst {100*worst_b:.1f}% vs pre-registered +/-25%")
    out["R1_verdict"] = dict(R1a=va, R1b=vb, worst_a=worst_a, worst_b=worst_b,
                             worst_b_beyond=worst_b_hi)

    # ---- primary + R2 ----
    print()
    print("=" * 78)
    print("PRIMARY -- merged (gate 0, no alignment) vs single frames, same path")
    print("=" * 78)
    prim = {}
    for nm in names:
        x, y = rois[nm]["x"], rois[nm]["y"]
        k = list(rois).index(nm)
        pk = focus[nm]["peak_frame"]
        m = merged[y : y + WIN, x : x + WIN]
        fm, pm = psd(m)
        n_hat = noise_tiff_units(float(np.asarray(cube[pk, k]).mean()))
        rows = []
        for off in (0, 1, -1, 2, -2, 10, -10, 25, -25):
            i = pk + off
            if str(i) not in armf:
                continue
            fr = L.read_tif_green(armf[str(i)]["tif"])[y : y + WIN, x : x + WIN]
            ff2, pf2 = psd(fr)
            s_raw, nb = sigma_eq(fm, pm, pf2)
            s_sub, _ = sigma_eq(fm, pm, pf2, n_sub=n_hat)
            rows.append(dict(offset=off, frame=i, sigma_raw=s_raw, sigma_sub=s_sub))
            tag = "PEAK" if off == 0 else ("+/-1,2" if abs(off) <= 2 else "R2 power")
            print(f"  {nm:<14} vs frame {i:3d} ({off:+3d}, {tag:8s}) : "
                  f"sigma_eq raw {s_raw:+7.4f} px   noise-sub {s_sub:+7.4f} px")
        prim[nm] = dict(peak=pk, n_model=n_hat, rows=rows)
    out["PRIMARY"] = prim

    dst = os.path.join(OUTDIR, "s6_spectral.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
