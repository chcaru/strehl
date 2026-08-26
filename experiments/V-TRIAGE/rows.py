import json
d = json.load(open(r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json", encoding="utf-8"))
for s in ("dry-erase-marker-head-cpl", "bee-2-cpl"):
    r = next(x for x in d["rows"] if x["subject"] == s)
    e = r["evidence"]
    print("=== %s ===  verdict: %s" % (s, r["verdict"]))
    for k in ("merge_edge_dnpx","frame_edge_dnpx","edge_ratio_min","worst_site",
              "n_sites_used","n_sites_dropped","worst_blur_px"):
        print("   %-22s %s" % (k, e.get(k)))
    print("   m/f = %.4f   stated = %.4f   error = %.1f%%"
          % (e["merge_edge_dnpx"]/e["frame_edge_dnpx"], e["edge_ratio_min"],
             100*abs((e["merge_edge_dnpx"]/e["frame_edge_dnpx"])/e["edge_ratio_min"]-1)))
    print()
print("field definitions for the three edge fields:")
for k in ("merge_edge_dnpx","frame_edge_dnpx","edge_ratio_min"):
    print("  %s:\n     %s" % (k, d["fields"][k]))
