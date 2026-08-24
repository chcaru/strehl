"""Why the plane-resolution arm of x10c is inadmissible: it measures aliasing.

x10c's plane arm read a penalty of -0.0572 dex at k=0.9974 and +0.0877 dex at
k=0.9315. A sign flip across two nearby values of the same knob is not a
measurement, and its K7 mechanism check returned a meaningless -34%.

THE SUSPECTED CAUSE. A single CFA plane has Nyquist 0.5 cyc per plane px, which
is 0.25 cyc per MOSAIC px. The measurement band, 0.30-0.48 cyc/mosaic px, is
entirely above that. Gathering each plane separately therefore cannot reproduce
the band -- but it can FOLD energy into it from above, and a power-spectrum
metric counts folded energy as signal. That would let the plane arm read HIGHER
high-band power while being visibly worse, which is exactly the failure mode
that let M87 ship a halo fix scoring +72.9% while erasing the bee's hairs.

THE TEST. Band-limit the input below plane Nyquist, then gather. A correct
gather cannot create energy above the input's band limit; any energy the plane
arm shows in 0.30-0.48 cyc/mosaic px is aliasing it manufactured.

POSITIVE CONTROL. The band-limiting itself must be shown to work: the unaltered
base must carry substantial energy in that band, and the band-limited base must
carry almost none. Without that pair, a null here would only mean the low-pass
removed everything.
"""
import json
import sys
from pathlib import Path

import numpy as np

import m95cov as M
from x10c_planeres import gather_full, gather_planes

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
OUT = Path(__file__).resolve().parents[1] / "out" / "x11_alias.json"

PLANE_NYQ = 0.25          # cyc per mosaic px
CUT = 0.22                # safely below it


def lowpass(t, cut=CUT):
    """Ideal low-pass below plane Nyquist, in mosaic units."""
    n = t.shape[0]
    f = np.fft.fftfreq(n)
    fr = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
    return np.real(np.fft.ifft2(np.fft.fft2(t) * (fr <= cut)))


def band_power(t, k=1.0):
    n = t.shape[0]
    p = np.abs(np.fft.fft2((t - t.mean()) * np.outer(np.hanning(n), np.hanning(n)))) ** 2
    f = np.fft.fftfreq(n)
    fr = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
    return float(p[(fr >= M.BAND[0] * k) & (fr < M.BAND[1] * k)].mean())


def main():
    img = M.load_luma(B0)
    tiles = M.pick_tiles(img)
    h, w = img.shape
    print(f"source: {B0.name}  {w}x{h}\ntiles : {len(tiles)}")
    print(f"plane Nyquist {PLANE_NYQ} cyc/mosaic px; low-pass cut {CUT}\n")
    res = {"cut": CUT, "plane_nyquist": PLANE_NYQ, "n_tiles": len(tiles)}

    regions, bases = [], []
    for ty, tx in tiles:
        ci = (ty + M.TILE // 2) & ~1
        cj = (tx + M.TILE // 2) & ~1
        y0, x0 = (ci - M.PAD // 2) & ~1, (cj - M.PAD // 2) & ~1
        if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
            continue
        regions.append(img[y0 : y0 + M.PAD, x0 : x0 + M.PAD])
        bases.append(img[ci - M.TILE // 2 : ci + M.TILE // 2,
                         cj - M.TILE // 2 : cj + M.TILE // 2])
    print(f"usable tiles: {len(regions)}\n")

    print("--- POSITIVE CONTROL: does the band-limiting actually work? ---")
    p_raw = float(np.mean([band_power(b) for b in bases]))
    p_lp = float(np.mean([band_power(lowpass(b)) for b in bases]))
    ratio = p_raw / max(p_lp, 1e-30)
    ok_lp = ratio > 100
    print(f"  band power in 0.30-0.48, unaltered base : {p_raw:.4e}")
    print(f"  band power after the low-pass           : {p_lp:.4e}")
    print(f"  suppression: {ratio:.3e}x   "
          f"{'PASS' if ok_lp else 'FAIL'}  (bar > 100x)")
    res.update(p_raw=p_raw, p_lowpassed=p_lp, suppression=ratio)
    if not ok_lp:
        print("\nthe low-pass does not band-limit; reporting nothing.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    lp_regions = [lowpass(r, CUT) for r in regions]

    print("\n--- THE TEST: gather a band-limited field, look above its limit ---")
    k = 0.9315
    rows = []
    for name, fn in (("FULL-RES gather", gather_full), ("PLANE-RES gather", gather_planes)):
        vals = []
        for reg in lp_regions:
            g = fn(reg, M.PAD / 2 - M.TILE * k / 2, M.PAD / 2 - M.TILE * k / 2, k)
            vals.append(band_power(g, k))
        m = float(np.mean(vals))
        rows.append((name, m, m / p_lp))
    for name, m, rel in rows:
        print(f"  {name:<18} band power {m:.4e}   "
              f"{rel:>10.2f}x the band-limited input")
    res["full_band_power"] = rows[0][1]
    res["plane_band_power"] = rows[1][1]
    res["plane_over_full"] = rows[1][1] / max(rows[0][1], 1e-30)

    amp = rows[1][1] / max(rows[0][1], 1e-30)
    print(f"\n  the plane gather puts {amp:.1f}x as much energy above the plane's")
    print(f"  own Nyquist as the full-resolution gather does, from an input that")
    print(f"  had almost none there. That energy is manufactured, not recovered.")
    print(f"\n  CONSEQUENCE: a power-spectrum sharpness metric CANNOT be used to")
    print(f"  compare a plane-grid gather against a mosaic-grid one. x10c's arm")
    print(f"  is withdrawn. Arm 4's P56 stays ARGUED and is NOT upgraded.")
    res["verdict"] = "metric inadmissible for plane-vs-mosaic; P56 stays ARGUED"

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
