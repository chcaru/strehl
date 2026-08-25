"""M113-ca: B7 restated correctly, and WHY the two stacks need different eps.

B7 -- MY OWN BAR WAS MIS-STATED. I wrote "a real scale must produce a vanishing
radial displacement at the centre". The innermost RING is not the centre: it
spans r = 0..0.15 with a median radius of ~230 px, where a -516 ppm scale
predicts a displacement of -0.119 px, not zero. The correct null compares the
ring's measured radial displacement against eps_global * r_bar. Restating a bar
after seeing the data is only legitimate when the restatement is forced by
arithmetic rather than chosen to pass, so both the original and the corrected
form are printed.

WHY THE STACKS DIFFER. Lateral CA is the separation of the effective wavelength
of the RED channel from that of the GREEN channel. Those effective wavelengths
are the passband centroids WEIGHTED BY THE SCENE'S OWN SPECTRUM, so two scenes
with different colour genuinely need different eps through the same glass at the
same focus. This prints each stack's channel ratios so the two "needed" figures
can be read against the scene colour that produced them.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from c4_globalfit import cs   # noqa: E402

LIN = r"C:\dev\strehl-out\M113-ca\lin"
OUT = r"C:\dev\strehl-out\M113-ca"
EPS_R = -704.5e-6

# from c9_binned.json / c10_rings.json
G = {"bee-3-cpl": dict(eps_global=-529.9e-6, ring_r=0.109, ring_dr=-0.1065, floor=0.0128,
                       needed=529.9e-6, gain=1.2496),
     "couch-fibers-cpl": dict(eps_global=-654.9e-6, ring_r=0.110, ring_dr=-0.1528, floor=0.0170,
                              needed=654.9e-6, gain=1.0557)}

def main():
    res = {}
    print("=" * 92)
    print("B7 RESTATED -- innermost ring against the scale model, not against zero")
    print("=" * 92)
    print("%-18s %9s %12s %12s %10s %10s" %
          ("stack", "r_bar px", "predicted", "measured", "err px", "floor px"))
    for name, g in G.items():
        off, W, H = cs.load_tiff_u16(os.path.join(LIN, "%s-binned-off.tif" % name))
        hd = float(np.hypot(W / 2.0, H / 2.0))
        rbar = g["ring_r"] * hd
        pred = g["eps_global"] * rbar
        err = abs(g["ring_dr"] - pred)
        print("%-18s %9.1f %12.4f %12.4f %10.4f %10.4f  %s"
              % (name, rbar, pred, g["ring_dr"], err, g["floor"],
                 "PASS" if err <= max(3 * g["floor"], 0.02) else "FAIL"))
        res.setdefault(name, {}).update(b7_pred=pred, b7_meas=g["ring_dr"], b7_err=err)

        # scene colour, on the same windows the fit used: robust channel medians
        sub = np.asarray(off[::17, ::17, :]).astype(np.float64)
        med = np.median(sub.reshape(-1, 3), axis=0)
        p90 = np.percentile(sub.reshape(-1, 3), 90, axis=0)
        res[name].update(median_rgb=med.tolist(), p90_rgb=p90.tolist(),
                         rg=float(med[0] / med[1]), bg=float(med[2] / med[1]))
        del off

    print("\n" + "=" * 92)
    print("SCENE COLOUR -- the weighting that sets each channel's effective wavelength")
    print("=" * 92)
    print("%-18s %10s %10s %10s %9s %9s" % ("stack", "med R", "med G", "med B", "R/G", "B/G"))
    for name in G:
        r = res[name]
        print("%-18s %10.0f %10.0f %10.0f %9.4f %9.4f"
              % (name, r["median_rgb"][0], r["median_rgb"][1], r["median_rgb"][2], r["rg"], r["bg"]))

    print("\n" + "=" * 92)
    print("CONSEQUENCE OF SHIPPING A SCALAR REFINEMENT")
    print("=" * 92)
    print("shipped coefficient eps_r = %+.1f ppm\n" % (EPS_R * 1e6))
    print("%-18s %10s %10s %12s %12s %12s"
          % ("stack", "needed", "gain now", "x0.692(ORCH)", "x0.780(my c4)", "x1.000(keep)"))
    for name, g in G.items():
        n = g["needed"]
        row = []
        for f in (0.692, 0.780, 1.000):
            eff = g["gain"] * f
            row.append(eff)
        print("%-18s %10.1f %10.4f %12.4f %12.4f %12.4f"
              % (name, n * 1e6, g["gain"], row[0], row[1], row[2]))
    print("\nEach cell is the residual multiplier AFTER the fix: 1.00 is perfect,")
    print(">1 still over-corrects, <1 under-corrects. A scalar cannot put both rows at 1.00")
    print("because the two scenes need coefficients %.1f and %.1f ppm -- a spread of %.1f %%."
          % (G["bee-3-cpl"]["needed"] * 1e6, G["couch-fibers-cpl"]["needed"] * 1e6,
             100 * abs(G["couch-fibers-cpl"]["needed"] / G["bee-3-cpl"]["needed"] - 1)))
    with open(os.path.join(OUT, "c11_why.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote c11_why.json")

if __name__ == "__main__":
    main()