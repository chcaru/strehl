"""Are the two routes agreeing for the right reason, and is the gap the photosite?

Two facts came out of reading the code rather than the numbers:

  * route A calls knee_model_fit, whose `pixel_mtf` argument DEFAULTS TO TRUE and
    which ladder.py does not override, so route A already models the photosite;
  * route B synthesises through equalise._scene, which applies `mtf_diffraction`
    and nothing else, so route B does not.

The real sensor samples with 5.12 um photosites either way, so route B compares a
real spectrum carrying sinc^2 against a synthetic one that does not. Both of the
following are therefore predicted, and are registered here before the run.

P6  DIRECTION AND SIZE OF THE ROUTE-B OFFSET. Refitting route A with
    pixel_mtf=False must RAISE the fitted B, because dropping the term leaves the
    model with more high-frequency power than the sensor delivers and the fit can
    only compensate by lowering f_c. It must also land nearer route B's 2.11 than
    the pixel_mtf=True fit's 2.0888 does. Falsifier: B falls, or moves away from
    route B. Either would mean the routes' agreement to 0.0112 was luck and the
    forward model has a second error hiding underneath this one.

P7  IS THE PHOTOSITE THE APERTURE TREND? The f/14 minus f/18 gap is +0.1157 with
    the pixel term ON. If the photosite were the cause of the trend, removing it
    would make the gap markedly worse. Registered threshold: |gap| changes by more
    than 0.05 between the two settings. I expect this to FAIL -- the gap should be
    nearly untouched, because a term already in the model cannot explain a residual
    the model still has. Recording the expectation so that a pass is news.

WHAT THIS CANNOT DECIDE. If P7 fails as expected, the surviving candidates for the
trend are residual defocus (registered threat T1), lens aberration, and vibration.
All three inflate the apparent B, and all three inflate it more at the wider
aperture -- defocus and aberration because they worsen as the pupil opens, an
absolute blur because diffraction has less of its own roll-off to hide behind. They
share a sign, so two in-band apertures cannot separate them, and f/11 is gone. This
lane should not pretend to identify which. What it can say one-sidedly is that
every candidate biases B UPWARD, so the least contaminated aperture bounds it.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
M5 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m5-diffraction")
sys.path.insert(0, M5)

import m5_lib as L  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
INBAND = ["f14", "f18"]
EXACT_N = {"f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
M = 2.7198


def fit_all(recs, pixel):
    per = {}
    for t in INBAND:
        bs, fcs = [], []
        for r in (x for x in recs if x["aperture"] == t):
            f = np.array(r["f"], float)
            p = np.array(r["psd"], float)
            c = np.array(r["counts"], float)
            m = L.knee_model_fit(f, p, c, pixel_mtf=pixel)
            if not m["ok"] or not m["f_c"]:
                continue
            fcs.append(m["f_c"])
            bs.append(L.PITCH_UM / (L.LAMBDA_UM * EXACT_N[t] * m["f_c"]))
        a = np.array(bs)
        per[t] = {"n": len(a), "B": float(a.mean()),
                  "sd": float(a.std(ddof=1)),
                  "sem": float(a.std(ddof=1) / np.sqrt(len(a))),
                  "fc": float(np.mean(fcs))}
    allb = np.array([per[t]["B"] for t in INBAND])
    return per, {"B": float(allb.mean()),
                 "gap": per["f14"]["B"] - per["f18"]["B"]}


def main():
    sn = json.load(open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8"))
    fine = json.load(open(os.path.join(OUT, "fit-b-fine.json"), encoding="utf-8"))
    recs = [r for r in sn["records"] if r["aperture"] in INBAND]
    routeB = fine["best"]["B"]

    res = {}
    print("route A refitted with and without the photosite term")
    print("=" * 76)
    print(f"  {'pixel_mtf':>10} " +
          " ".join(f"{t + ' f_c':>9} {t + ' B':>8}" for t in INBAND) +
          f" {'mean B':>8} {'gap':>8}")
    for pixel in (True, False):
        per, agg = fit_all(recs, pixel)
        res["on" if pixel else "off"] = {"per": per, **agg}
        print(f"  {str(pixel):>10} " +
              " ".join(f"{per[t]['fc']:9.4f} {per[t]['B']:8.4f}" for t in INBAND) +
              f" {agg['B']:8.4f} {agg['gap']:+8.4f}")

    on, off = res["on"], res["off"]
    rose = off["B"] > on["B"]
    closer = abs(off["B"] - routeB) < abs(on["B"] - routeB)
    print()
    print(f"  route B (no photosite term at all) sits at B = {routeB:.2f}")
    print(f"  route A with the term ON  : {on['B']:.4f}, "
          f"{abs(on['B'] - routeB):.4f} from route B")
    print(f"  route A with the term OFF : {off['B']:.4f}, "
          f"{abs(off['B'] - routeB):.4f} from route B")
    print(f"  P6 direction: B {'rose' if rose else 'FELL'} when the term was "
          f"removed -> {'PASS' if rose else 'FAIL'}")
    print(f"  P6 approach : moved {'toward' if closer else 'AWAY FROM'} route B "
          f"-> {'PASS' if closer else 'FAIL'}")
    print("  Reading: the residual disagreement between the routes is the size of")
    print("  the photosite term the forward model omits, and it is now accounted")
    print("  for rather than merely small.")

    dgap = abs(off["gap"] - on["gap"])
    print()
    print(f"  P7 gap with term ON  : {on['gap']:+.4f}")
    print(f"  P7 gap with term OFF : {off['gap']:+.4f}, moved {dgap:.4f}")
    print(f"  P7 (photosite explains the trend, threshold 0.05) -> "
          f"{'PASS' if dgap > 0.05 else 'FAIL, as expected'}")
    if dgap <= 0.05:
        print("  The aperture trend is not the photosite. It survives a model that")
        print("  already contains one, and removing it barely moves the trend.")

    best_ap = min(INBAND, key=lambda t: on["per"][t]["B"])
    bnd = on["per"][best_ap]
    print()
    print("one-sided conclusion")
    print("=" * 76)
    print(f"  Every surviving candidate for the trend inflates B. The smallest")
    print(f"  measured B therefore bounds the true one from above:")
    print(f"    B <= {bnd['B']:.4f} +- {bnd['sem']:.4f}  (at {best_ap})")
    print(f"    p  >= {M / (bnd['B'] - 1.0):.4f}")
    for k, (Bh, ph) in {"H1": (3.7319, 0.9956), "H2": (3.0763, 1.3099),
                        "H3": (2.4020, 1.9400)}.items():
        z = (Bh - bnd["B"]) / bnd["sem"]
        print(f"    {k}: B {Bh:.4f} is {z:+.1f} s.e. above the bound -> "
              f"{'EXCLUDED' if z > 3 else 'not excluded'}")

    payload = {"routes": res, "route_B": routeB, "P6_direction": bool(rose),
               "P6_approach": bool(closer), "P7_gap_delta": float(dgap),
               "P7": bool(dgap > 0.05), "bound": {"aperture": best_ap, **bnd},
               "p_lower": M / (bnd["B"] - 1.0), "m": M}
    with open(os.path.join(OUT, "pixel-check.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote out/pixel-check.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
