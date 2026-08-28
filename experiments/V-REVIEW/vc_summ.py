import json, numpy as np
rows = [r for r in json.load(open("vc_score.json")) if r["verdict"] == "SCORED"]
print("%-30s %9s %8s %9s %8s %8s" % ("subject","d_ppmR","nsigR","d_ppmB","nsigB","|dB/dR|"))
print("-"*78)
for r in rows:
    print("%-30s %+9.1f %8.1f %+9.1f %8.1f %8.3f" %
          (r["subject"], r["d_ppmR"], r["nsigma"], r["d_ppmB"], r["nsigmaB"],
           abs(r["d_ppmB"]/r["d_ppmR"])))
dr = np.array([r["d_ppmR"] for r in rows]); db = np.array([r["d_ppmB"] for r in rows])
ra = np.array([r["ratio"] for r in rows])
print("\nn scored              : %d" % len(rows))
print("delta_R  median       : %+.1f ppm   range %+.1f .. %+.1f" % (np.median(dr), dr.min(), dr.max()))
print("delta_B  median       : %+.1f ppm   range %+.1f .. %+.1f" % (np.median(db), db.min(), db.max()))
print("|dB/dR|  median       : %.3f   -> blue moves ~%.0fx less than red" %
      (np.median(np.abs(db/dr)), 1.0/np.median(np.abs(db/dr))))
print("ratio    median       : %.3f   range %.3f .. %.3f" % (np.median(ra), ra.min(), ra.max()))
print("subjects with ratio<1 : %d of %d" % (int((ra < 1).sum()), len(ra)))
print("subjects with ratio>1 : %d of %d" % (int((ra > 1).sum()), len(ra)))
wr = np.array([r["width_ratio"] for r in rows])
print("width_ratio range     : %.4f .. %.4f  (worst = %s)" %
      (wr.min(), wr.max(), rows[int(np.argmax(np.abs(wr-1)))]["subject"]))
