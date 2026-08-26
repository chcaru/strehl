import json, os, numpy as np, tri
print("noise_ratio = frame_noise / merge_noise   (>1 means the merge is cleaner)")
print("FLAT is the designated low-detail reference site; DETAIL sites contain")
print("real structure that a median-residual statistic counts as noise.")
print()
print(f"{'subject':<38}{'FLAT':>9}{'DETAIL':>9}{'SRC-BEST':>10}{'DEFICIT':>9}")
flats, dets = [], []
for s in tri.SUBJECTS:
    d = json.load(open(os.path.join(tri.OUT, "compare", s + ".json")))
    row = {}
    for lab, v in d["sites"].items():
        e = v.get("edge") or {}
        if e.get("noise_ratio"):
            row[lab] = e["noise_ratio"]
    if "FLAT" in row: flats.append(row["FLAT"])
    if "DETAIL" in row: dets.append(row["DETAIL"])
    print(f"{s:<38}" + "".join(
        f"{row.get(k, float('nan')):>{w}.2f}"
        for k, w in (("FLAT",9),("DETAIL",9),("SOURCE-BEST",10),("DEFICIT",9))))
print()
print(f"FLAT   sites: median {np.median(flats):.2f}x  "
      f"({sum(1 for x in flats if x>1)}/{len(flats)} have the merge cleaner)")
print(f"DETAIL sites: median {np.median(dets):.2f}x  "
      f"({sum(1 for x in dets if x>1)}/{len(dets)} have the merge cleaner)")
