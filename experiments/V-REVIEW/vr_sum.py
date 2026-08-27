import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V
for s in ["112MSDCF","113MSDCF","coffee-bubbles","flower-inner-edge-cpl","foam",
          "couch-fibers-cpl","flat-on-ruler-cpl","lead-1-cpl","leaf-2-cpl"]:
    with open(os.path.join(V.OUT, "source_%s.json" % s)) as fh:
        d = json.load(fh)
    ok = [r for r in d["rows"] if r["state"] == "OK"]
    ok.sort(key=lambda r: r["frame"])
    print("%-22s n=%-4d ok=%-3d  blotch M %.5f Smax %.5f  chroma M %.6f Smax %.6f"
          % (s, d["n_frames"], len(ok), d["master"]["blotch"]["contrast"],
             d.get("src_blotch_max", float("nan")), d["master"]["chroma"]["chroma"],
             d.get("src_chroma_max", float("nan"))))
    print("   frames  " + " ".join("%d:%.4f/%.4f" % (r["frame"], r["blotch"], r["relhf"]) for r in ok))
