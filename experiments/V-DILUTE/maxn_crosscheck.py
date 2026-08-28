"""Cross-check of commit 8a480af9's max-of-N flat-field prediction, at 13.6x leverage.

That lane (owner's own, subject 113MSDCF) found that deepening a stack makes FLAT
fields NOISIER -- grain x1.1697 for N=63 vs N=32 -- and attributed it to
winner-take-all selecting the largest of N noisy candidates, for which
E[max of N] ~ sigma * sqrt(2 ln N) predicts x1.0934. Measured came in 7% above.

Their arms span 2.0x in depth. Mine span 13.6x (N=22 -> N=299) on a different
subject (bee-3-cpl), which is far more leverage on a sqrt(ln N) law: the
predicted effect grows from x1.093 to x1.358. If the mechanism is real it should
be much easier to see here, and on FLAT sites only -- textured sites should not
follow it.

Their prediction is also compounded here by a second effect I measured
independently: the `averaged` duty cycle at band 0 FALLS with N (30.8% at N=22),
so a larger fraction of coefficients come under winner-take-all as N grows, on
top of each one being a max of more candidates.
"""
import sys
import numpy as np

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-DILUTE")
import vd_metrics as vd

R = r"C:\dev\strehl-out\V-DILUTE\runs"
FALLBACK = {22: 0.9021}

ref = vd.green(rf"{R}\A_n299_default.tif")
tex, flat = vd.select_tiles(ref)
print(f"tiles: {len(tex)} textured, {len(flat)} flat (selected on one reference, "
      f"so both arms are scored at identical sensor locations)\n")

NS = [22, 33, 63, 105, 299]
rows = []
for n in NS:
    g = vd.green(rf"{R}\A_n{n}_default.tif")
    s = vd.fov_scale(rf"{R}\A_n{n}_default.log", FALLBACK.get(n))
    # grain = the high band, where read noise lives; measured on FLAT and on
    # TEXTURED sites separately, because the claim is that they move oppositely.
    rows.append(dict(
        n=n, s=s,
        flat_grain=vd.band_power(g, flat, 0.40 * s, 0.50 * s),
        flat_mid=vd.band_power(g, flat, 0.05 * s, 0.15 * s),
        tex_grain=vd.band_power(g, tex, 0.40 * s, 0.50 * s),
        tex_detail=vd.band_power(g, tex, 0.30 * s, 0.35 * s),
    ))

b = rows[0]
print("bee-3-cpl, shipping default, full focus range at every N, band edges scaled by each arm's own FOV")
print(f"{'N':>5} {'flat grain':>12} {'vs N=22':>9} {'flat 5-15':>12} {'vs N=22':>9} "
      f"{'tex grain':>12} {'vs N=22':>9}")
for r in rows:
    print(f"{r['n']:>5} {r['flat_grain']:>12.1f} {r['flat_grain']/b['flat_grain']:>9.4f} "
          f"{r['flat_mid']:>12.1f} {r['flat_mid']/b['flat_mid']:>9.4f} "
          f"{r['tex_grain']:>12.1f} {r['tex_grain']/b['tex_grain']:>9.4f}")

print("\nmax-of-N prediction, E[max] ~ sigma*sqrt(2 ln N), ratio vs N=22:")
print(f"{'N':>5} {'predicted':>11} {'measured flat grain':>21} {'measured/predicted':>19}")
for r in rows:
    pred = np.sqrt(np.log(r["n"]) / np.log(22))
    meas = r["flat_grain"] / b["flat_grain"]
    print(f"{r['n']:>5} {pred:>11.4f} {meas:>21.4f} {meas/pred:>19.4f}")

print("\nNOTE: band power is a VARIANCE-like quantity; the sqrt(2 ln N) law is on")
print("amplitude. Amplitude ratio = sqrt(power ratio):")
print(f"{'N':>5} {'predicted amp':>15} {'measured amp':>14} {'meas/pred':>11}")
for r in rows:
    pred = np.sqrt(np.log(r["n"]) / np.log(22))
    meas = np.sqrt(r["flat_grain"] / b["flat_grain"])
    print(f"{r['n']:>5} {pred:>15.4f} {meas:>14.4f} {meas/pred:>11.4f}")
