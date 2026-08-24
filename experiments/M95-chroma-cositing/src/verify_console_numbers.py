"""Verify the report's console-only numbers -- the ones not in a results table.

The report quotes instrument-control figures and a derived R-B separation that
did not come from `report_numbers.py`. A number recalled from a session
transcript is no better than a number recalled from a note, so each is
recomputed here from the stored JSON and printed.
"""

import json
import math
import os
import statistics as st

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def j(n):
    with open(os.path.join(OUT, n), encoding="utf-8") as f:
        return json.load(f)


def main():
    c1, c2, s3 = j("c1_controls.json"), j("c2_controls.json"), j("s3_cositing.json")

    print("== C1: planted shifts ==")
    worst = max(r["worst_err"] for r in c1["C1"])
    null = [r for r in c1["C1"] if r["plant_dx"] == 0.0 and r["plant_dy"] == 0.0][0]
    print("   worst error over all plants : %.5f px   (report says 0.00543)" % worst)
    print("   zero-shift null worst error : %.4g px   (report says 2.07e-16)"
          % null["worst_err"])

    for k in ("C2", "C3", "C5"):
        if k in c1:
            print("== %s ==\n   %s" % (k, json.dumps(c1[k])[:400]))

    print("\n== C7: naive vs robust ==")
    print("   naive worst  %.4f   (report says 4.2101)" % c2["C7"]["naive_worst"])
    print("   robust worst %.3g   (report says 3.89e-09)" % c2["C7"]["robust_worst"])
    for r in c2["C7"]["rows"]:
        print("      plant %.1f  naive %+.4f  robust %+.4f"
              % (r["plant"], r["naive_dy"], r["robust_dy"]))

    for k in ("C8", "C9"):
        if k in c2:
            print("\n== %s ==\n   %s" % (k, json.dumps(c2[k])[:500]))

    print("\n== R-B separation, recomputed from S3 ==")
    for pair, p in s3["pairs"].items():
        mean = {ch: (st.mean(r["dy"] for r in p["per_channel"][ch]),
                     st.mean(r["dx"] for r in p["per_channel"][ch]))
                for ch in "RGB"}
        sep = math.hypot(mean["R"][0] - mean["B"][0], mean["R"][1] - mean["B"][1])
        print("   %-13s R-B separation %.4f binned px  (prediction %.4f)"
              % (pair, sep, 0.5 * math.sqrt(2)))
    print("   report says 0.6637 and 0.6691, prediction 0.7071")

    print("\n== C10 vs C6 sign, from the stored synthetic runs ==")
    print("   C10 mean R %s" % [round(v, 4) for v in s3["C10"]["mean_R"]])
    print("   C10 mean G %s" % [round(v, 7) for v in s3["C10"]["mean_G"]])
    print("   C10 mean B %s" % [round(v, 4) for v in s3["C10"]["mean_B"]])

    print("\n== green null vs signal separation, S3 ==")
    for pair, p in s3["pairs"].items():
        g = max(abs(st.mean(r[ax] for r in p["per_channel"]["G"])) for ax in ("dy", "dx"))
        r_ = max(abs(st.mean(r[ax] for r in p["per_channel"]["R"])) for ax in ("dy", "dx"))
        print("   %-13s green %.5f px, red %.4f px -> %.0fx separation"
              % (pair, g, r_, r_ / g))
    print("   report says 0.0005-0.0020 px and a 100-450x separation")


if __name__ == "__main__":
    main()
