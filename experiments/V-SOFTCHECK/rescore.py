"""rescore.py -- re-score MY measured band qualification under the CORRECTLY ATTRIBUTED rule.

ORCH corrected the attribution: noisefloor.py's boundary is r < 1.3 (noise/detail), while
the >= 2.0 eligibility bar belongs to bandsignal.py. I verified both at the primary source
before using either:

  experiments/V-LINEAR/noisefloor.py:93
      v = ("NOISE-DOMINATED above 0.20 cyc/px" if r < 1.3 else
           "carries real detail above 0.20 cyc/px")

  experiments/V-LINEAR2/bandsignal.py:94-99
      def verdict(r, lo):
          if r >= 2.0 and lo >= 1.5: return "PASS"
          if r >= 1.3:               return "MARGINAL"
          return "FAIL(noise)"

  experiments/V-LINEAR2/PREREGISTRATION.md sec.2
      PASS  R >= 2.0 and bootstrap CI low >= 1.5   -- eligible to be the comparison band
      MARGINAL  1.3 <= R < 2.0                     -- reported, never the headline
      FAIL      R < 1.3                            -- noise, no comparison may be reported
      "The comparison band is the HIGHEST-frequency PASSing band."

Nothing here is re-measured. The arms, the probes and the ratios are unchanged; only the
scoring rule and its attribution moved. My own pre-registered PASS condition (R >= 2.0
AND CI low > 1.5), fixed at 11ede945 before I had read either instrument, is the same
condition bandsignal.py encodes -- which is worth stating as an independent convergence
and not as agreement I arranged.
"""
import os, sys, numpy as np
import dmeasure as DM, d113recon as RC, bandqual as BQ

E = DM.E; NB = DM.NB
DIL = r"C:\dev\strehl-out\V-SOFTCHECK\dilut"
CAND = {"113MSDCF": ["bandqual-113MSDCF.npz", "bandqual.npz"],
        "bee-1-cpl": ["bandqual-bee-1-cpl.npz"]}

def verdict(r, lo):
    """Transcribed from bandsignal.py:94-99. Not imported: that file belongs to V-LINEAR2."""
    if r >= 2.0 and lo >= 1.5: return "PASS"
    if r >= 1.3: return "MARGINAL"
    return "FAIL(noise)"

def noisefloor_call(r):
    """Transcribed from noisefloor.py:93. A DIFFERENT question with a DIFFERENT boundary."""
    return "NOISE-DOMINATED" if r < 1.3 else "carries real detail"

def bname(b): return "%.2f-%.2f" % (E[b], E[b+1])

def main():
    print("RE-SCORING V-SOFTCHECK's measured qualification under two correctly named rules")
    print("No re-measurement: same probes, same arms, same ratios. Only the rule moved.\n")
    for subj, names in CAND.items():
        path = None
        for n in names:
            q = os.path.join(DIL, subj, n)
            if os.path.exists(q): path = q; break
        if path is None:
            print("%s: npz absent, skipped" % subj); continue
        z = np.load(path)
        P = z["P"]; TOP = z["TOP"]; FLAT = z["FLAT"]
        print("%s   (%s, %d probes, %d TOP tiles)" % (subj, os.path.basename(path), P.shape[0], len(TOP)))
        print("  %-11s %8s %19s  %-12s  %s" % ("band", "R", "95% CI", "bandsignal.py", "noisefloor.py"))
        rows = []
        for b in range(NB):
            r, ci, _ = BQ.ratio(P, TOP, BQ.SEL, b)
            v = verdict(r, ci[0])
            rows.append((b, r, ci, v))
            print("  %-11s %8.4f  [%7.4f,%7.4f]  %-12s  %s%s" %
                  (bname(b), r, ci[0], ci[1], v, noisefloor_call(r),
                   "   <-- V-SOFTCHECK operating band" if b == 5 else ""))
        ps = [b for b, r, ci, v in rows if v == "PASS"]
        hi = max(ps) if ps else None
        print("  -> highest-frequency PASSing band (PREREGISTRATION.md sec.2): %s"
              % (bname(hi) if hi is not None else "NONE"))
        b5 = rows[5]
        print("  -> 0.30-0.35 is %s by bandsignal.py, and %s by noisefloor.py."
              % (b5[3], noisefloor_call(b5[1])))
        print("     CI low %.4f %s 1.3, so the noise boundary is %s.\n"
              % (b5[2][0], ">" if b5[2][0] > 1.3 else "<=",
                 "EXCLUDED" if b5[2][0] > 1.3 else "not excluded"))

if __name__ == "__main__":
    main()
