import sys, os
sys.path.insert(0, "src")
import importlib.util, glob, numpy as np, rawpy
spec = importlib.util.spec_from_file_location("m", "src/22-selfvalidating.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
arw = sorted(glob.glob(os.path.join(m.SRC_ROOT, "coffee-bean", "*.ARW")))
print("coffee-bean total frames:", len(arw))
rng = np.random.default_rng(16180)
for label, sel in (("first 20 (freeze config)", arw[:20]), ("all 105", arw)):
    idx = np.linspace(0, len(sel)-1, 8).astype(int)
    qs = []
    for i in idx:
        with rawpy.imread(sel[i]) as r:
            qs.append(m.quad_mean(r.raw_image_visible, float(np.mean(r.black_level_per_channel))))
    R = m.pooled(qs)
    d, p, fire = m.score(R, *m.MOTES["mote2"], rng)
    print("  %-24s depth %8.3f%%  p %.4f  FIRES %s" % (label, d*100, p, fire))
