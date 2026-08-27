import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V

SUBJ = ["109MSDCF","112MSDCF","113MSDCF","coffee-bubbles","couch-fibers-cpl","flat-on-ruler-cpl",
        "flower-inner-edge-cpl","foam","lead-1-cpl","leaf-2-cpl"]

print("%-22s %3s %8s %8s %6s | %8s %8s %6s | %8s %8s %6s | %8s %8s %8s %6s %6s"
      % ("subject","nOK","B_M","B_smax","r_ctr","bandM","bandSmx","r_band",
         "meanM","meanSmd","r_mean","C_M","C_smax","C_smin","rc_mx","rc_mn"))
for s in SUBJ:
    d = json.load(open(os.path.join(V.OUT, "source_%s.json" % s)))
    ok = [r for r in d["rows"] if r["state"] == "OK"]
    m  = d["master"]
    bands = sorted(r["band"] for r in ok)
    means = sorted(r["mean"] for r in ok)
    med = lambda v: v[len(v)//2]
    bM, bS = m["blotch"]["contrast"], d["src_blotch_max"]
    dM, dS = m["blotch"]["band"], max(bands)
    mM, mS = m["blotch"]["mean"], med(means)
    cM, cX, cN = m["chroma"]["chroma"], d["src_chroma_max"], d["src_chroma_min"]
    print("%-22s %3d %8.5f %8.5f %6.3f | %8.1f %8.1f %6.3f | %8.1f %8.1f %6.3f | %8.6f %8.6f %8.6f %6.3f %6.3f"
          % (s, len(ok), bM, bS, bM/bS, dM, dS, dM/dS, mM, mS, mM/mS,
             cM, cX, cN, cM/cX, cM/cN))
