r"""ORCH job 1 -- run V-RIM's OWN falsification #1 against V-RIM's report.

The report acquitted coffee-bean (shoulder sd ~0.199) and leaf-2-cpl (~0.302)
by comparing each to a rim-free pedestal read off the Arm A ladder with
np.interp.  The ladder topped out at sd 0.1957, so np.interp CLAMPED and both
pedestals were extrapolated.  An extrapolated pedestal supporting an acquittal
is the weakest joint in that report.  This closes it two independent ways.

ROUTE 1 -- EXTEND THE LADDER BY DIRECT MEASUREMENT.
  Same synthetic scene, same roughener, same pipeline.  The nominal roughness
  amplitude is NOT the achieved shoulder sd (profile sampling low-passes it by
  about 0.65x), so each target sd is reached by BISECTION on the amplitude and
  the ACHIEVED sd is reported next to it.  No interpolation anywhere.

ROUTE 2 -- MEASURE THE PEDESTAL ON THE MASTER ITSELF.  No synthetic scene at
  all, hence no extrapolation possible.  rimv6 hands back the (n_edges x 25)
  array of normalised profiles.  Write P = m + Rres where m is the median
  profile and Rres the per-edge residual.  A rim is a COHERENT non-monotone
  excursion in m; roughness lives in Rres and is incoherent across edges.
  Replace m by its isotonic (non-decreasing) projection mtil and rebuild
  Ptil = Rres + mtil.  Every edge keeps its own residual row EXACTLY, so its
  shoulder sd and its t-to-t correlation are unchanged to the last bit, and
  the only thing removed is the coherent bump -- the rim.  max-then-median on
  Ptil is therefore what this master would read if its edges were monotone and
  its texture were untouched: the rim-free pedestal, measured in place.

MATCHED CONTROL FOR ROUTE 2.  The isotonic operation is applied to the Arm B
  planted-rim images as well.  If it is doing what is claimed, the raw reading
  must climb with planted rim amplitude while the isotonic pedestal stays put.
  If the pedestal climbs too, route 2 is subtracting the rim it is meant to
  leave alone and its numbers must be discarded.
"""
import io
import json
import os
import sys

import numpy as np

import vr_lib as V
import vr_specificity as S
import rimaxis
import rimv6

OUT = os.path.join(V.SCRATCH, "ladder.json")

# the two subjects whose acquittal rested on a clamp, plus the rest of the 13
THIRTEEN = ["bee-1-cpl", "couch-fibers-cpl", "lead-1-cpl", "flowers-cpl",
            "pencil-steep-angle-cpl", "wrapped-text-1", "lavendar-cpl",
            "wrapped-text-2", "flat-on-ruler-cpl", "coffee-bean",
            "leaf-2-cpl", "112MSDCF", "113MSDCF"]
CONTROLS = ["109MSDCF", "119MSDCF"]          # PASS subjects, matched control


def pav(y):
    """Pool-adjacent-violators: least-squares non-decreasing fit. Plain
    implementation so nothing depends on a sklearn version."""
    y = np.asarray(y, float)
    v = list(y)
    w = [1.0] * len(y)
    i = 0
    while i < len(v) - 1:
        if v[i] <= v[i + 1] + 1e-15:
            i += 1
            continue
        tw = w[i] + w[i + 1]
        tv = (v[i] * w[i] + v[i + 1] * w[i + 1]) / tw
        v[i:i + 2] = [tv]
        w[i:i + 2] = [tw]
        i = max(i - 1, 0)
    out = []
    for val, wt in zip(v, w):
        out.extend([val] * int(round(wt)))
    return np.array(out[:len(y)])


def iso_pedestal(em):
    """Route 2. Returns (raw max-then-median, isotonic pedestal, sd)."""
    if em is None or not len(em["prof"]):
        return None
    P = np.asarray(em["prof"], float)
    ib = rimv6.IB
    m = np.median(P, axis=0)
    R = P - m[None, :]
    mt = pav(m)
    Pt = R + mt[None, :]
    raw = float(np.median(P[:, ib].max(axis=1) - 1.0))
    ped = float(np.median(Pt[:, ib].max(axis=1) - 1.0))
    sd = float(np.median(P[:, ib].std(axis=1, ddof=1)))
    return dict(raw=raw, pedestal=ped, shoulder_sd=sd,
                excursion=float((m[ib] - mt[ib]).max()),
                n=int(P.shape[0]))


def sd_of(amp, base, seed):
    g = S.roughen(base, amp, seed=seed)
    rec, sel, ref, em = V.run_pipeline(g, np.zeros(g.shape, bool), ntile=40)
    coh = rec.get("coh_master")
    sd = coh["shoulder_sd_median"] if coh else None
    if sd is None and em is not None and len(em["prof"]):
        P = np.asarray(em["prof"], float)
        sd = float(np.median(P[:, rimv6.IB].std(axis=1, ddof=1)))
    return sd, rec, em


def main():
    doc = {}
    base = S.scene()

    print("=" * 78)
    print("ROUTE 1 -- EXTENDED LADDER, ACHIEVED sd MEASURED NOT ASSUMED")
    print("=" * 78)
    print("%9s %10s %11s %12s %10s %8s" % ("amp", "achieved sd", "corrected",
                                           "med-then-max", "n_sel", "verdict"))
    doc["ladder"] = []
    amps = [0.0, 0.012, 0.048, 0.090, 0.110, 0.130, 0.150, 0.170, 0.200, 0.240]
    for amp in amps:
        sd, rec, em = sd_of(amp, base, S.SEED + 1)
        if "corrected_bright" not in rec:
            print("%9.4f %10s   REFUSED %s" % (amp, "%.4f" % sd if sd else "-",
                                               rec.get("refused")))
            doc["ladder"].append(dict(amp=amp, sd=sd,
                                      refused=rec.get("refused")))
            continue
        cm = rec["coh_master"]
        v = V.verdict(rec)[0]
        print("%9.4f %10.4f %10.3f%% %11.3f%% %10d %8s"
              % (amp, sd, 100 * rec["corrected_bright"],
                 100 * cm["median_then_max"], rec["n_sel"], v))
        doc["ladder"].append(dict(amp=amp, sd=sd,
                                  corrected=rec["corrected_bright"],
                                  mtm=cm["median_then_max"],
                                  n=rec["n_sel"], verdict=v))
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
