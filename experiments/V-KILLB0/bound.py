"""V-KILLB0 bound.py -- the MAXIMUM AMPLITUDE LOSS A PURE DENOISER MAY CAUSE.

V-LINEAR's R at a site population is in-focus band power over defocused band
power.  Reading the defocused tile as signal-free in that band, R = (S+N)/N, so
the NOISE fraction of total power is 1/R and the signal fraction is 1-1/R.

An arm that removes 100% of the noise and not one photon of signal therefore
lands at exactly

        floor = sqrt(1 - 1/R)

in amplitude.  Anything BELOW that floor cannot be explained by denoising at
all: the missing energy has to have come out of the qualified signal.  This is
a bound, not an estimate, and it is conservative in three separate ways:

 1. R is measured on a SINGLE linear develop, whereas the merged master has
    already had noise reduced by averaging (leaf-2 default is 54.4% averaged),
    so the master's true noise fraction is LOWER than 1/R and the floor is
    HIGHER than printed;
 2. no real gate removes 100% of noise;
 3. defocused tiles retain some signal, which inflates the denominator, lowers
    R, and again makes the printed floor too generous.

So "observed < floor" is a hard finding and "observed > floor" is not a clean
acquittal -- it only means this particular bound does not fire.

R values are pasted from flatanalyze.py runs (which import V-LINEAR's rule
unmodified) and the observed ratios from spectrum.py.  Both are printed so the
arithmetic can be checked by hand.
"""
import numpy as np

FINE = [(0.02, 0.05), (0.05, 0.08), (0.08, 0.11), (0.11, 0.14), (0.14, 0.17),
        (0.17, 0.20), (0.20, 0.25), (0.25, 0.30), (0.30, 0.40), (0.40, 0.48)]

# R at STRUCTURED sites, from flatanalyze.py (V-LINEAR rule, imported)
R_STRUCT = {
    "leaf-2-cpl": [266.923, 48.088, 19.115, 9.772, 5.935, 3.719, 2.202, 1.464, 1.167, 1.104],
    "bee-1-cpl":  [381.191, 608.576, 506.554, 426.527, 265.391, 149.055, 69.022, 24.078, 8.795, 5.442],
}
# observed STRUCT B/A from spectrum.py, arm b0x4 vs default
OBS = {
    "leaf-2-cpl": [0.9042, 0.6913, 0.5789, 0.5520, 0.5559, 0.5526, 0.5482, 0.5140, 0.5143, 0.5553],
    "bee-1-cpl":  [1.0015, 1.0023, 1.0021, 1.0027, 1.0033, 1.0041, 1.0057, 1.0088, 1.0107, 1.0085],
}
# V-LINEAR PASS rule, restated for the printout only
def verd(r):
    return "PASS" if r >= 2.0 else ("MARG" if r >= 1.3 else "fail")


for key in ("bee-1-cpl", "leaf-2-cpl"):
    print(f"\n== {key}   b0x4 vs default, STRUCTURED sites")
    print(f"   {'band':<12} {'R':>9} {'qual':>5} {'noise%pwr':>10} "
          f"{'denoise floor':>14} {'observed':>9} {'verdict':>28}")
    for (f0, f1), r, o in zip(FINE, R_STRUCT[key], OBS[key]):
        nf = 1.0 / r
        floor = np.sqrt(max(0.0, 1.0 - nf))
        if verd(r) == "fail":
            msg = "band is noise here - no claim"
        elif o >= floor:
            msg = "within denoise budget"
        else:
            # how much qualified signal amplitude must be gone
            sig = 1.0 - nf
            lost = 1.0 - (o * o) / sig if sig > 0 else float("nan")
            msg = f"SIGNAL DESTROYED: >={100*lost:.0f}% of signal power"
        print(f"   {f0:.2f}-{f1:.2f}  {r:9.3f} {verd(r):>5} {100*nf:9.2f}% "
              f"{floor:14.4f} {o:9.4f} {msg:>28}")
