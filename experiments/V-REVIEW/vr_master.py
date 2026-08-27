r"""ARM MASTER -- reproduce the gate's own two numbers on the nine REVIEW rows.

If this table does not match `C:\dev\strehl-out\printready-v3.txt` digit for
digit then my harness is not measuring what flagged them and nothing after it
counts.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402

GATE = {   # transcribed from printready-v3.txt
    '109MSDCF': (0.00169, 0.0005),   # PASS-subject control row
    "112MSDCF": (0.14667, 0.0349), "113MSDCF": (0.25168, 0.0254),
    "coffee-bubbles": (0.09892, 0.0546), "couch-fibers-cpl": (0.04511, 0.0042),
    "flat-on-ruler-cpl": (0.18363, 0.0028), "flower-inner-edge-cpl": (0.09921, 0.0123),
    "foam": (0.46075, 0.0325), "lead-1-cpl": (0.00555, 0.0202),
    "leaf-2-cpl": (0.00448, 0.0197),
}


def main():
    subs = sys.argv[1:] or V.SUBJECTS
    out = {}
    print("%-22s %9s %9s  %9s %9s   %s" %
          ("subject", "blotch", "gate", "chroma", "gate", "windows (y,x)"))
    for s in subs:
        rgb = V.read_rgb(V.master_path(s))
        b = V.gate_blotch(rgb)
        c = V.gate_chroma(rgb)
        del rgb
        gb, gc = GATE[s]
        ok = abs(b["contrast"] - gb) < 5e-5 and abs(c["chroma"] - gc) < 5e-5
        print("%-22s %9.5f %9.5f  %9.4f %9.4f   blotch(%d,%d) chroma(%d,%d)  %s"
              % (s, b["contrast"], gb, c["chroma"], gc, b["y"], b["x"],
                 c["y"], c["x"], "MATCH" if ok else "*** MISMATCH ***"))
        out[s] = dict(blotch=b, chroma=c, gate_blotch=gb, gate_chroma=gc,
                      reproduced=bool(ok))
        sys.stdout.flush()
    p = os.path.join(V.OUT, "master_stats.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    print("\nwrote %s" % p)
    print("all reproduced: %s" % all(v["reproduced"] for v in out.values()))


if __name__ == "__main__":
    main()
