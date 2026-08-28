"""Score the HEAD k-sweep against the MEASURED floor.

ORCH's revised ask. Columns, all on the same masters:

  blotch     sigma_mid 20-60 px, ORCH's statistic, imported.
  sharp/tex  band 0.20-0.25 cyc/px on TEXTURED sites -- the amended
             requirement, after the flat-site column was shown to correlate
             0.985-0.997 with grain and be a second noise column.
  grain      sigma_hp, same pixels.
  r(sharp,grain)  per subject across arms, so a grain move cannot be read as a
             sharpness move. This is the column that makes the other two
             interpretable.
  avg@L0     the gate's own duty cycle, parsed out of each run's banner, so the
             quality columns can be read against whether the gate fired at all.
  runtime    the measured floor probes every frame; ORCH measured ~1.9x.

Ratios are against WHITE200 (white floor, k=2.0) = the PRE-FIX shipping
default, so the shipping default G200 appears as a scored arm rather than as
the baseline. That is deliberate: the question is whether the landed fix
regressed us, and a baseline cannot answer a question about itself.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
import tifffile                                                   # noqa: E402
from ceiling import pick_sites                                    # noqa: E402
from blotch_sweep import fine_on                                  # noqa: E402

AB = r"C:\dev\strehl-out\BUILD-GATE\head\ab"
ARMS = ["WHITE200", "G090", "G100", "G129", "G140", "G160", "G200", "G260"]
KS = {"WHITE200": "2.0w", "G090": "0.9", "G100": "1.0", "G129": "1.29",
      "G140": "1.4", "G160": "1.6", "G200": "2.0", "G260": "2.6"}
SUBJECTS = ["coffee-bubbles", "109MSDCF", "119MSDCF",
            "flower-bud-alone-cpl", "bee-1-cpl"]


def banner(arm, subject):
    """avg@L0 and the measured floor ratio, read from the run's OWN log."""
    p = os.path.join(AB, arm, subject + ".log")
    if not os.path.exists(p):
        return None, None
    t = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"^averaged\s*:\s*([\d.]+)%", t, re.M)
    avg = float(m.group(1)) if m else None
    m = re.search(r"x white\s*:\s*([\d.]+)", t)
    return avg, (float(m.group(1)) if m else None)


def score(subject):
    ref = os.path.join(AB, "WHITE200", subject + ".tiff")
    if not os.path.exists(ref):
        return None
    flat, _, _ = bl.pick_flat_sites(ref)
    tex, _ = pick_sites(tifffile.imread(ref)[..., :3].astype(np.float64))
    rows = {}
    for arm in ARMS:
        p = os.path.join(AB, arm, subject + ".tiff")
        if not os.path.exists(p):
            continue
        mid, hp = [], []
        for (y, x) in flat:
            c = bl.codes(p, y, x)
            mid.append(np.mean([bl.sigma_mid(c[..., k]) for k in range(3)]))
            hp.append(np.mean([bl.sigma_hp(c[..., k]) for k in range(3)]))
        ft = [fine_on(bl.codes(p, y, x)) for (y, x) in tex]
        avg, xw = banner(arm, subject)
        rows[arm] = (float(np.mean(mid)), float(np.mean(hp)),
                     float(np.mean(ft)), avg, xw)
    return rows


def main():
    print("HEAD k-sweep against the MEASURED floor (the default; no env var).")
    print("Ratios vs WHITE200 = white floor at k=2.0 = the PRE-FIX shipping "
          "default.")
    print("G200 is TODAY'S SHIPPING DEFAULT and appears as a scored arm, not "
          "as the baseline.\n")
    for s in SUBJECTS:
        rows = score(s)
        if not rows:
            print("%s: not rendered yet\n" % s)
            continue
        b = rows["WHITE200"]
        print("%s  N=%d" % (s, bl.NFRAMES[s]))
        print("  %-9s %5s | %9s %9s %11s | %8s %8s"
              % ("arm", "k", "blotch x", "grain x", "sharp/tex x",
                 "avg@L0", "xwhite b0"))
        for a in ARMS:
            if a not in rows:
                continue
            r = rows[a]
            note = ""
            if a == "WHITE200":
                note = "  <- pre-fix ship"
            elif a == "G200":
                note = "  <- SHIPS TODAY"
            elif a == "G129":
                note = "  <- landmark, not a recommendation"
            print("  %-9s %5s | %9.4f %9.4f %11.4f | %7s%% %8s%s"
                  % (a, KS[a], r[0] / b[0], r[1] / b[1], r[2] / b[2],
                     ("%.1f" % r[3]) if r[3] is not None else "n/a",
                     ("%.4f" % r[4]) if r[4] is not None else "white",
                     note))
        av = [rows[a] for a in ARMS if a in rows]
        if len(av) < len(ARMS):
            print("  INCOMPLETE: %d/%d arms rendered; correlations withheld "
                  "(a partial r is not the sweep's r)." % (len(av), len(ARMS)))
            print()
            continue
        g = np.array([x[1] for x in av])
        t = np.array([x[2] for x in av])
        m = np.array([x[0] for x in av])
        print("  r(sharp/tex, grain) = %+.4f    r(blotch, grain) = %+.4f"
              % (np.corrcoef(g, t)[0, 1], np.corrcoef(g, m)[0, 1]))
        print()


if __name__ == "__main__":
    main()
