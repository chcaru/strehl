"""Print every number this report quotes, from the JSON the experiments wrote.

Discipline: a number recalled from a note is not a measurement. This is the
single place the report's figures are read from, so any drift between the
report and the artifacts is visible in one diff.
"""

import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def j(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    print("=" * 72)
    print("S3 -- co-siting displacement, real data")
    d = j("s3_cositing.json")
    print("  C10 synthetic, truth by construction, 5 seeds:")
    for k in ("R", "G", "B"):
        v = d["C10"]["mean_" + k]
        print("     %s  (%+.4f, %+.4f)" % (k, v[0], v[1]))
    for pair, p in d["pairs"].items():
        print("  %s: %d/%d ROIs coherent" % (pair, p["n_kept"], p["n_offered"]))
        for k in ("R", "G", "B"):
            rows = p["per_channel"][k]
            import statistics as st
            dy = [r["dy"] for r in rows]
            dx = [r["dx"] for r in rows]
            print("     %s  (%+.4f, %+.4f)  sd (%.4f, %.4f)"
                  % (k, st.mean(dy), st.mean(dx), st.pstdev(dy), st.pstdev(dx)))

    print("=" * 72)
    print("S4 -- benefit of co-siting, Python simulation")
    d = j("s4_benefit.json")
    for pair, p in d.items():
        print("  %s" % pair)
        for variant, v in p.items():
            print("     %-13s regR %.4f  regG %.4f  regB %.4f   edge %8.2f DN"
                  % (variant, v["reg_R"], v["reg_G"], v["reg_B"], v["chroma_rms_edge_DN"]))

    print("=" * 72)
    print("S5 -- replacement controls")
    d = j("s5_controls.json")
    print("  C11 synthetic end-to-end, no demosaic: mean ratio %.4f  pass=%s"
          % (d["C11"]["mean_ratio"], d["C11"]["pass"]))
    for r in d["C11"]["rows"]:
        print("     seed %d  %.5f -> %.5f  (%.1f%% lower)"
              % (r["seed"], r["chroma_shipped"], r["chroma_fixed"],
                 100 * (1 - r["ratio"])))
    print("  N4 correction applied to green: pass=%s" % d["N4"]["pass"])
    for pair, v in d["N4"]["rows"].items():
        print("     %-13s %.4f -> %.4f px" % (pair, v["green_before"], v["green_after_shift"]))
    print("  N3: %s" % d["N3_retired"])

    print("=" * 72)
    print("S6 -- shipped renders, end to end")
    d = j("s6_shipped.json")
    print("  N5 null (reference vs itself): R %.5f G %.5f B %.5f"
          % (d["N5_null"]["R"], d["N5_null"]["G"], d["N5_null"]["B"]))
    for tag in ("before", "after"):
        v = d[tag]
        print("  %-7s regR %.4f  regG %.4f  regB %.4f   chroma %8.1f DN   edge %8.1f DN"
              % (tag, v["reg_R"], v["reg_G"], v["reg_B"],
                 v["chroma_rms_DN"], v["chroma_rms_edge_DN"]))
    b, a = d["before"], d["after"]
    print("  red  %.4f -> %.4f  (%.1f%% removed)"
          % (b["reg_R"], a["reg_R"], 100 * (1 - a["reg_R"] / b["reg_R"])))
    print("  blue %.4f -> %.4f  (%.1f%% removed)"
          % (b["reg_B"], a["reg_B"], 100 * (1 - a["reg_B"] / b["reg_B"])))
    print("  green (matrix-mediated) %.4f -> %.4f  (%.1f%% removed)"
          % (b["reg_G"], a["reg_G"], 100 * (1 - a["reg_G"] / b["reg_G"])))
    print("  chroma edge %.1f -> %.1f DN  (%.1f%% lower)"
          % (b["chroma_rms_edge_DN"], a["chroma_rms_edge_DN"],
             100 * (1 - a["chroma_rms_edge_DN"] / b["chroma_rms_edge_DN"])))
    print("  chroma all  %.1f -> %.1f DN  (%.1f%% lower)"
          % (b["chroma_rms_DN"], a["chroma_rms_DN"],
             100 * (1 - a["chroma_rms_DN"] / b["chroma_rms_DN"])))
    print("  did-anything: max |dR| %d DN, max |dB| %d DN"
          % (d["did_anything_happen"]["max_dR_DN"], d["did_anything_happen"]["max_dB_DN"]))
    print("  figure crop: %s" % j("s10_figure.json")["crop"])

    print("=" * 72)
    print("C1/C2 -- instrument controls")
    for f in ("c1_controls.json", "c2_controls.json"):
        print("  %s:" % f)
        print("    " + json.dumps(j(f))[:900])


if __name__ == "__main__":
    main()
