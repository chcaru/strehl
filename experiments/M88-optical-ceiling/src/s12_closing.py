"""s12: model-free closing measurements and the arithmetic of clause (a).

1. Model-free ESF 10-90 rise distance on matched ROIs of 109MSDCF (f/11) and
   119MSDCF (f/5.6).  No fit, no model, no sigma/f_c trade.  If diffraction
   dominated, the f/11 rise must be 1.9643x the f/5.6 rise.
2. The highest frequency carrying significant energy, using the larger of the
   band floor and the split-half floor.
3. The broadband arithmetic of fact 1149 clause (a): the Bayer green channel
   is not monochromatic, so "MTF at sensor Nyquist is exactly zero" has to be
   evaluated over the channel's actual passband.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

ROOT = Path("D:/personal/macro")
OUT = Path(__file__).resolve().parents[1] / "out"
BIN_UM, TAPER, CORE_UM = 0.64, 0.10, 24.0
NROW, NCOL = 160, 400
NYQ = 97.65625

BEST = {("119MSDCF", "A1", 1280, 0): 6, ("119MSDCF", "A2", 1280, 200): 6,
        ("119MSDCF", "A3", 1280, 400): 5, ("119MSDCF", "A4", 1280, 600): 9,
        ("109MSDCF", "C1", 1280, 0): 17, ("109MSDCF", "C2", 1280, 200): 8,
        ("109MSDCF", "C3", 1200, 400): 9, ("109MSDCF", "C4", 1200, 600): 6}


def rise_1090(centres, esf):
    """Model-free 10-90 percent rise distance of a monotone-ish ESF."""
    e = np.asarray(esf, float)
    c = np.asarray(centres, float)
    k = max(3, len(e) // 40)
    lo = np.median(e[:k])
    hi = np.median(e[-k:])
    if hi < lo:
        e, lo, hi = -e, -lo, -hi
    span = hi - lo
    if span <= 0:
        return np.nan
    t10, t90 = lo + 0.1 * span, lo + 0.9 * span
    # monotone envelope so the crossing is unique
    em = np.maximum.accumulate(e)
    x10 = np.interp(t10, em, c)
    x90 = np.interp(t90, em, c)
    return float(x90 - x10)


def measure(stack, frame, r0, c0, half_um):
    files = sorted((ROOT / stack).glob("*.ARW"))
    active = L.load_active(files[frame])
    sub, xs, ys = L.green_sites(active, "G1")
    s = sub[r0:r0 + NROW, c0:c0 + NCOL].astype(float)
    xr, yr = xs[c0:c0 + NCOL], ys[r0:r0 + NROW]
    line = L.fit_edge_line(s, xr, yr, axis="horizontal")
    XX, YY = np.meshgrid(xr, yr)
    r = L.sfr_from_sites2(s.ravel(), XX.ravel(), YY.ravel(), line, BIN_UM,
                          half_um, TAPER, core_um=CORE_UM)
    halves = []
    for off in (0, 1):
        Xh, Yh = np.meshgrid(xr[off::2], yr)
        halves.append(L.sfr_from_sites2(s[:, off::2].ravel(), Xh.ravel(),
                                        Yh.ravel(), line, BIN_UM, half_um,
                                        TAPER, core_um=CORE_UM))
    f = r["freq_cymm"]
    split = np.abs(halves[0]["mtf"] - halves[1]["mtf"]) / 2.0
    fl, _ = L.noise_floor_curve(f, r["mtf"], BIN_UM, (250.0, 380.0))
    use = np.maximum(fl, split)
    bound = L.signal_bound_curve(f, r["mtf"], use, 3.0, 3)
    del active, sub
    return dict(rise=rise_1090(r["centres_um"], r["esf"]),
                bound=bound, contrast=line["contrast"],
                angle=line["angle_deg"], f=f, mtf=r["mtf"], floor=use)


def main():
    log = {}
    print("=" * 78)
    print("1. MODEL-FREE ESF 10-90% RISE DISTANCE  (half-width 96 um)")
    print("=" * 78)
    print(f"{'stack':>13} {'roi':>3} {'frm':>4} {'rise_um':>8} "
          f"{'contrast':>9} {'E2':>7}")
    rise = {"119MSDCF": [], "109MSDCF": []}
    for (stack, roi, r0, c0), k in BEST.items():
        d = measure(stack, k, r0, c0, 96.0)
        rise[stack].append(d["rise"])
        print(f"{stack:>13} {roi:>3} {k:4d} {d['rise']:8.2f} "
              f"{d['contrast']:9.0f} {d['bound']:7.1f}")
    a = np.array(rise["119MSDCF"])
    b = np.array(rise["109MSDCF"])
    ra, rb = float(np.median(a)), float(np.median(b))
    print(f"\n  f/5.6 median rise = {ra:6.2f} um   (n={a.size})")
    print(f"  f/11  median rise = {rb:6.2f} um   (n={b.size})")
    print(f"  measured ratio    = {rb/ra:6.3f}")
    print(f"  predicted if diffraction-limited = 1.964")
    print(f"  predicted if an aperture-independent blur dominates -> 1.000")
    log["rise"] = dict(f56=a.tolist(), f11=b.tolist(), ratio=rb / ra)

    print("\n  what an aperture-independent blur of size o would give:")
    for o_rel in (0.0, 0.5, 1.0, 2.0, 3.0, 5.0):
        r = np.sqrt(1.9643 ** 2 + o_rel ** 2) / np.sqrt(1.0 + o_rel ** 2)
        print(f"    o = {o_rel:4.1f} x (f/5.6 diffraction blur) -> "
              f"ratio {r:5.3f}")
    # solve for o given the measured ratio
    R = rb / ra
    if 1.0 < R < 1.9643:
        o2 = (1.9643 ** 2 - R ** 2) / (R ** 2 - 1.0)
        print(f"  -> the measured ratio {R:.3f} implies an "
              f"aperture-independent blur {np.sqrt(o2):.2f}x the f/5.6 "
              f"diffraction blur")
        log["o_rel"] = float(np.sqrt(o2))
    else:
        print(f"  -> the measured ratio {R:.3f} lies outside "
              f"[1.0, 1.964]; no positive solution")
        log["o_rel"] = None

    print()
    print("=" * 78)
    print("2. WHAT THE DATA BOUNDS: highest frequency with 3 bins above "
          "3x floor")
    print("=" * 78)
    for stack in ("119MSDCF", "109MSDCF"):
        v = []
        for (st, roi, r0, c0), k in BEST.items():
            if st != stack:
                continue
            d = measure(st, k, r0, c0, 64.0)
            v.append(d["bound"])
        v = np.array(v, float)
        vv = v[np.isfinite(v)]
        print(f"  {stack:>13}: E2 = {np.array2string(v, precision=1)}  "
              f"median {np.median(vv) if vv.size else float('nan'):.1f}")
        log[f"E2_{stack}"] = v.tolist()

    print()
    print("=" * 78)
    print("3. CLAUSE (a) ARITHMETIC: is MTF at sensor Nyquist 'exactly zero'?")
    print("=" * 78)
    print("  Diffraction MTF at the 97.66 cy/mm sensor Nyquist, by wavelength,")
    print("  for two values of N_eff: fact 1149's own 21.07, and the value")
    print("  implied by M5's MEASURED B <= 3.064, namely N_eff = 17.16.")
    print(f"\n  {'lambda':>7} {'fc@21.07':>9} {'MTF@Nyq':>8} | "
          f"{'fc@17.16':>9} {'MTF@Nyq':>8}")
    tab = []
    for lam_nm in (450, 500, 530, 550, 600, 650):
        lam = lam_nm * 1e-6  # mm
        row = [lam_nm]
        for neff in (21.0672, 17.1584):
            fc = 1.0 / (lam * neff)
            mt = float(L.mtf_diffraction(np.array([NYQ]), fc)[0])
            row += [fc, mt]
        tab.append(row)
        print(f"  {lam_nm:5d}nm {row[1]:9.2f} {row[2]:8.4f} | "
              f"{row[3]:9.2f} {row[4]:8.4f}")
    log["clause_a"] = tab

    print("\n  Broadband Bayer-green average (Gaussian weight, centre 535 nm,")
    print("  sd 35 nm, truncated at +/-2.5 sd):")
    lam_nm = np.linspace(535 - 87.5, 535 + 87.5, 401)
    w = np.exp(-0.5 * ((lam_nm - 535.0) / 35.0) ** 2)
    w /= w.sum()
    for neff, tag in ((21.0672, "fact 1149  N_eff=21.07"),
                      (17.1584, "M5 bound   N_eff=17.16")):
        fc = 1.0 / (lam_nm * 1e-6 * neff)
        mt = np.array([float(L.mtf_diffraction(np.array([NYQ]), c)[0])
                       for c in fc])
        m86 = np.array([float(L.mtf_diffraction(np.array([86.30]), c)[0])
                        for c in fc])
        print(f"    {tag}: broadband MTF(97.66) = {float((w*mt).sum()):.4f}, "
              f"MTF(86.30) = {float((w*m86).sum()):.4f}, "
              f"max fc in band = {fc.max():.1f} cy/mm")
        log[f"broadband_{neff:.2f}"] = dict(mtf_nyq=float((w * mt).sum()),
                                            mtf_863=float((w * m86).sum()),
                                            fc_max=float(fc.max()))

    (OUT / "s12_closing.json").write_text(json.dumps(log, indent=1,
                                                     default=float),
                                          encoding="utf-8")
    print("\nwrote out/s12_closing.json")


if __name__ == "__main__":
    main()
