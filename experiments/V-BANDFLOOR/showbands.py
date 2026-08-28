import json, os, sys
OUT = r"C:\dev\strehl-out\V-BANDFLOOR"
SCALE = ["2-4px", "4-8px", "8-16px", "16-32px", "32-64px", "64-128px", "128-256px"]
for s in sys.argv[1:]:
    p = os.path.join(OUT, "%s__bandmetrics.json" % s)
    if not os.path.exists(p):
        print("MISSING %s" % s); continue
    d = json.load(open(p))
    print("\n%s   clipA %.4f%%  clipB %.4f%%   (%d flat / %d textured tiles)"
          % (s, 100*d["clipA"], 100*d["clipB"], d["n_flat"], d["n_tex"]))
    print("  %-4s %-10s %-26s %-26s %s"
          % ("band", "scale", "FLAT tiles  B-A [95% CI]", "TEXTURED   B-A [95% CI]",
             "flat/tex"))
    for k in range(7):
        f = d["per_band"][str(k)]["flat"]
        t = d["per_band"][str(k)]["tex"]
        ratio = (f[0]/t[0]) if abs(t[0]) > 1e-9 else float("nan")
        print("  %-4d %-10s %+7.2f%% [%+6.2f,%+6.2f]     %+7.2f%% [%+6.2f,%+6.2f]     %6.2f"
              % (k, SCALE[k], f[0], f[1], f[2], t[0], t[1], t[2], ratio))
