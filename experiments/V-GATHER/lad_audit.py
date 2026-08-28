r"""Audit the ladder's own controls: self-consistency, registration, sanity.

Three questions the headline table cannot answer for itself.

  DOES THE DEFAULT ARM REPRODUCE sharp.json? The ladder re-renders the shipping
  master and re-measures it at the frozen sites. That number must agree with the
  one the sharpness axis recorded for the same master at the same sites. If it
  does not, the ladder is measuring something other than what the sharpness axis
  measured and no comparison between them is admissible.

  DID THE SITES MOVE BETWEEN ARMS? All arms merge one source set into one
  reference grid, so the frozen coordinates ought to point at the same content
  in every arm. arm_shifts measures it. A site that moved was measured in the
  wrong place, and the difference between arms would then carry the
  displacement rather than the exponent.

  ARE THE EXTREME e16 READINGS REAL NUMBERS? +344% median and +5069% p90 on one
  subject is either the ringing the tool's own help text predicts for near-argmax
  selection, or an instrument breaking down. This prints the raw per-site bands
  so the reading can be checked against the ceiling it is divided by rather than
  taken on trust.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lad_measure as lm                                           # noqa: E402

ARMS = ["default", "e1", "e2", "e4", "e8", "e16"]


def main():
    doc = json.load(io.open(os.path.join(HERE, "ladder.json"), encoding="utf-8"))
    print("=== SELF-CONSISTENCY: default arm vs sharp.json, same sites ===")
    for sub, e in doc.items():
        d = e.get("arms", {}).get("default", {})
        v = d.get("reproduces_sharp_json_maxrel")
        print("  %-26s max rel band difference: %s"
              % (sub, ("%.3e" % v) if v is not None else "NOT COMPUTED"))

    print("\n=== REGISTRATION: sites that moved between arms ===")
    total_bad = 0
    for sub, e in doc.items():
        for a in ARMS[1:]:
            bad = e.get("arms", {}).get(a, {}).get("shift_bad")
            if bad is None:
                continue
            total_bad += len(bad)
            if bad:
                print("  %-26s %-4s %d site(s) moved: %s" % (sub, a, len(bad), bad[:3]))
    print("  total sites that moved across all arms and subjects: %d" % total_bad)

    print("\n=== SANITY: is the e16 reading a real number? ===")
    for sub, e in doc.items():
        a = e.get("arms", {}).get("e16", {})
        d = e.get("arms", {}).get("default", {})
        if "median" not in a:
            continue
        print("  %-26s n=%d/%d  e16 min %+.3f%%  median %+.3f%%  p90 %+.3f%%  max %+.3f%%"
              % (sub, a["n"], a["n_offered"], 100 * a["min"], 100 * a["median"],
                 100 * a["p90"], 100 * a["max"]))
        print("  %-26s          default min %+.3f%% median %+.3f%% max %+.3f%%"
              % ("", 100 * d["min"], 100 * d["median"], 100 * d["max"]))

    print("\n=== COUNTED PARTITION: every site accounted for, per arm ===")
    for sub, e in doc.items():
        for a in ARMS:
            r = e.get("arms", {}).get(a, {})
            if "n" not in r:
                print("  %-26s %-8s NOT MEASURED" % (sub, a))
                continue
            meas, off = r["n"], r["n_offered"]
            ok = (meas + (off - meas)) == off
            print("  %-26s %-8s measured %2d + refused %2d = offered %2d  %s"
                  % (sub, a, meas, off - meas, off, "OK" if ok else "*** DOES NOT SUM ***"))


if __name__ == "__main__":
    main()
