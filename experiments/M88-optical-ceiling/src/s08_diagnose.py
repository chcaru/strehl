"""s08: diagnose why the real-capture ESF misbehaves.

The pre-registered run reported sigma_fit of 6-8 um everywhere and E2 bounds
of 200-580 cy/mm, which is above the 195.3 cy/mm pixel-aperture zero and
therefore physically impossible.  Something in the chain is wrong on real data
that was not wrong on the plants.  Find it before drawing any conclusion.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

ROOT = Path("D:/personal/macro")
OUT = Path(__file__).resolve().parents[1] / "out"
BIN_UM, HALF_UM, TAPER = 0.64, 192.0, 0.10
NROW, NCOL = 160, 400


def main():
    path = sorted((ROOT / "119MSDCF").glob("*.ARW"))[6]
    active = L.load_active(path)
    sub, xs, ys = L.green_sites(active, "G1")
    r0, c0 = 1280, 0
    s = sub[r0:r0 + NROW, c0:c0 + NCOL].astype(float)
    xr, yr = xs[c0:c0 + NCOL], ys[r0:r0 + NROW]
    print(f"{path.name}  ROI A1  values min {s.min():.0f} max {s.max():.0f} "
          f"median {np.median(s):.0f}")

    print("\n-- outlier census (hot pixels destroy an ESF) --")
    med = np.median(s)
    mad = 1.4826 * np.median(np.abs(s - med))
    for z in (5, 10, 20, 50):
        n = int(np.sum(np.abs(s - med) > z * mad))
        print(f"   |v-median| > {z:2d} MAD : {n:6d} of {s.size} "
              f"({100*n/s.size:.3f}%)")
    print(f"   MAD = {mad:.1f} DN, median = {med:.1f} DN")
    print(f"   top 8 values: {np.sort(s.ravel())[-8:].astype(int)}")
    print(f"   saturation check: white level 15360-512=14848; "
          f"n at >14000 = {int(np.sum(s > 14000))}")

    line = L.fit_edge_line(s, xr, yr, axis="horizontal")
    print(f"\n-- edge line --")
    print(f"   angle {line['angle_deg']:+.3f} deg  resid sd "
          f"{line['resid_sd_px']:.3f} px  contrast {line['contrast']:.0f} "
          f"(lo {line['lo_dn']:.0f} hi {line['hi_dn']:.0f})")

    XX, YY = np.meshgrid(xr, yr)
    d = ((XX - line["x0"]) * line["nx"] + (YY - line["y0"]) * line["ny"]) * L.PITCH_UM
    v = s.ravel()
    dd = d.ravel()
    m = np.abs(dd) <= HALF_UM
    print(f"\n-- ESF window --")
    print(f"   samples in +/-{HALF_UM} um: {int(m.sum())} of {v.size}")
    nb = int(round(2 * HALF_UM / BIN_UM))
    idx = np.clip(((dd[m] + HALF_UM) / BIN_UM).astype(int), 0, nb - 1)
    cnt = np.bincount(idx, minlength=nb)
    print(f"   bins {nb}, occupancy min {cnt.min()} median "
          f"{int(np.median(cnt))} max {cnt.max()}, empty {int((cnt==0).sum())}")

    mean_esf = np.bincount(idx, weights=v[m], minlength=nb) / np.maximum(cnt, 1)
    # robust alternative
    order = np.argsort(idx)
    med_esf = np.empty(nb)
    st = np.searchsorted(idx[order], np.arange(nb + 1))
    for i in range(nb):
        seg = v[m][order][st[i]:st[i + 1]]
        med_esf[i] = np.median(seg) if seg.size else np.nan

    print("\n-- ESF wings: is the window clean of other structure? --")
    k = nb // 10
    print(f"   left  outer 10%: mean {mean_esf[:k].mean():8.1f} "
          f"sd {mean_esf[:k].std():7.1f}")
    print(f"   right outer 10%: mean {mean_esf[-k:].mean():8.1f} "
          f"sd {mean_esf[-k:].std():7.1f}")
    print(f"   contrast {line['contrast']:.0f}; wing sd as % of contrast: "
          f"{100*mean_esf[:k].std()/line['contrast']:.2f} / "
          f"{100*mean_esf[-k:].std()/line['contrast']:.2f}")

    print("\n-- ESF profile, every 12th bin (um : mean : median) --")
    c_um = -HALF_UM + (np.arange(nb) + 0.5) * BIN_UM
    for i in range(0, nb, 24):
        print(f"   {c_um[i]:+8.2f} : {mean_esf[i]:8.1f} : {med_esf[i]:8.1f}")

    print("\n-- per-bin scatter vs photon expectation --")
    # within-bin sd should be sqrt(signal in e-) * gain if only shot noise
    gain = 50.0 / 436.8
    sd_in = np.empty(nb)
    for i in range(nb):
        seg = v[m][order][st[i]:st[i + 1]]
        sd_in[i] = seg.std() if seg.size > 3 else np.nan
    exp_sd = np.sqrt(np.maximum(mean_esf, 1) / gain) * gain
    j = nb // 6
    print(f"   left wing : observed sd {np.nanmedian(sd_in[:j]):7.1f}  "
          f"photon-only {np.nanmedian(exp_sd[:j]):7.1f}  ratio "
          f"{np.nanmedian(sd_in[:j])/np.nanmedian(exp_sd[:j]):.2f}")
    print(f"   right wing: observed sd {np.nanmedian(sd_in[-j:]):7.1f}  "
          f"photon-only {np.nanmedian(exp_sd[-j:]):7.1f}  ratio "
          f"{np.nanmedian(sd_in[-j:])/np.nanmedian(exp_sd[-j:]):.2f}")
    print("   ratio >> 1 means the ROI carries real along-edge structure, "
          "not just noise")

    print("\n-- MTF from mean-binned vs median-binned ESF --")
    for tag, e in (("mean", mean_esf), ("median", med_esf)):
        f, mtf = L.sfr_from_esf(c_um, e, TAPER)
        fl, flat = L.noise_floor_curve(f, mtf, BIN_UM, (250.0, 380.0))
        fit = L.fit_fc(f, mtf, 10.0, 150.0)
        def rd(fr):
            i = int(np.argmin(np.abs(f - fr)))
            return mtf[i], fl[i]
        m40 = rd(40.0)
        m86 = rd(86.3)
        m97 = rd(97.66)
        print(f"   {tag:>7}: fc {fit['fc_cymm']:7.2f} sigma "
              f"{fit['sigma_um']:6.2f} amp {fit['amp']:.3f} | "
              f"MTF40 {m40[0]:.4f} MTF86 {m86[0]:.4f}/{m86[1]:.4f} "
              f"MTF97 {m97[0]:.4f}/{m97[1]:.4f} | flat floor {flat:.5f}")

    print("\n-- through-focus of the same ROI: is frame 6 really best? --")
    for k in range(0, 33, 2):
        p = sorted((ROOT / "119MSDCF").glob("*.ARW"))[k]
        a = L.load_active(p)
        sb, xs2, ys2 = L.green_sites(a, "G1")
        ss = sb[r0:r0 + NROW, c0:c0 + NCOL].astype(float)
        try:
            ln = L.fit_edge_line(ss, xs2[c0:c0 + NCOL], ys2[r0:r0 + NROW],
                                 axis="horizontal")
            X2, Y2 = np.meshgrid(xs2[c0:c0 + NCOL], ys2[r0:r0 + NROW])
            rr = L.sfr_from_sites(ss.ravel(), X2.ravel(), Y2.ravel(), ln,
                                  BIN_UM, HALF_UM, TAPER)
            ft = L.fit_fc(rr["freq_cymm"], rr["mtf"], 10.0, 150.0)
            i40 = int(np.argmin(np.abs(rr["freq_cymm"] - 40.0)))
            print(f"   f{k:3d}: MTF40 {rr['mtf'][i40]:.4f}  fc "
                  f"{ft['fc_cymm']:7.2f}  sigma {ft['sigma_um']:6.2f}  "
                  f"contrast {ln['contrast']:6.0f}")
        except L.EdgeFitError as e:
            print(f"   f{k:3d}: {e}")
        del a, sb


if __name__ == "__main__":
    main()
