"""The fix-ca check applied to my own Experiment C null.

ORCH: "A zero from a flag can mean the stage is already doing the work. Before
you conclude any arm of yours is inert, check whether the behaviour is on by
default and the flag merely re-requests it."

That is exactly my C null, and this makes the diagnosis explicit rather than
asserted. exponent_at(k, nb) = exponent * sharpen^(nb-1-k), k=0 FINEST, capped at
MAX_EXPONENT = 8.0 (pyramid.rs, read at pin 9b05d0b7).

If the shipped ladder is already AT the cap in the bands that carry acuity, then
--pyramid-exponent 8 --pyramid-sharpen 1.0 re-requests, in those bands, exactly
what the default already does -- and its 0.997 is the fix-ca signature: redundant
flag, potent stage. The test is whether the metric MOVES in the coarse bands,
where the two ladders genuinely differ.
"""
import sys
import numpy as np

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-DILUTE")
import vd_metrics as vd

R = r"C:\dev\strehl-out\V-DILUTE\runs"
MAX_EXPONENT = 8.0


def ladder(exponent, sharpen, nb=7):
    return [min(exponent * sharpen ** (nb - 1 - k), MAX_EXPONENT) for k in range(nb)]


d = ladder(2.0, 1.4)
u = ladder(8.0, 1.0)
lo = ladder(0.5, 1.4)
print("PER-BAND EXPONENT LADDER (k=0 finest). Level k spans ~[0.5/2^(k+1), 0.5/2^k] cyc/px.\n")
print(f"{'k':>2} {'band cyc/px':>16} {'default 2.0/1.4':>16} {'uniform 8.0/1.0':>16} {'low 0.5/1.4':>13}  same?")
for k in range(7):
    f_hi, f_lo = 0.5 / 2 ** k, 0.5 / 2 ** (k + 1)
    same = "IDENTICAL" if abs(d[k] - u[k]) < 1e-9 else ""
    print(f"{k:>2} {f_lo:>7.4f}-{f_hi:<8.4f} {d[k]:>16.3f} {u[k]:>16.3f} {lo[k]:>13.3f}  {same}")

print("\n-> My reported detail bands 0.30-0.35 and 0.20-0.25 cyc/px lie in k=0 and k=1,")
print("   which are ALREADY PINNED AT THE CAP by the shipped default. The uniform-high")
print("   arm cannot differ from the default there. That is why C read 0.997.\n")

ref = vd.green(rf"{R}\A_n299_default.tif")
tex, flat = vd.select_tiles(ref)
arms = {
    "default 2.0/1.4": ("A_n299_default", 0),
    "uniform 8.0/1.0": ("C_e8_s1p0", 0),
    "low     0.5/1.4": ("C_e0p5_s1p4", 0),
}
imgs, scales = {}, {}
for k, (tag, _) in arms.items():
    imgs[k] = vd.green(rf"{R}\{tag}.tif")
    scales[k] = vd.fov_scale(rf"{R}\{tag}.log")

# Coarse bands where the ladders DO differ, plus the fine bands where they do not.
BANDS = [((0.0156, 0.0312), "k=4  coarse   (3.92 vs 8.0)"),
         ((0.0312, 0.0625), "k=3  coarse   (5.49 vs 8.0)"),
         ((0.0625, 0.1250), "k=2  mid      (7.68 vs 8.0)"),
         ((0.2000, 0.2500), "k=1  fine     (8.0  vs 8.0)"),
         ((0.3000, 0.3500), "k=0  finest   (8.0  vs 8.0)")]

print("BAND POWER vs DEFAULT, bee-3-cpl N=299, same textured tiles (rule 3 pairs noise below)\n")
print(f"{'band':<30} {'uniform/default':>16} {'low/default':>13}")
for (f1, f2), lbl in BANDS:
    vals = {}
    for k in arms:
        s = scales[k]
        vals[k] = vd.band_power(imgs[k], tex, f1 * s, f2 * s)
    dfl = vals["default 2.0/1.4"]
    print(f"{lbl:<30} {vals['uniform 8.0/1.0']/dfl:>16.4f} {vals['low     0.5/1.4']/dfl:>13.4f}")

nz = {}
for k in arms:
    s = scales[k]
    nz[k] = vd.band_power(imgs[k], tex, 0.40 * s, 0.50 * s)
dfl = nz["default 2.0/1.4"]
print(f"\n{'NOISE 0.40-0.50, same tiles':<30} {nz['uniform 8.0/1.0']/dfl:>16.4f} {nz['low     0.5/1.4']/dfl:>13.4f}")
