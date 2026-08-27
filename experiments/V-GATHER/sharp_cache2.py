import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands2 as B2
for s in sys.argv[1:]:
    t = time.time()
    try:
        z = B2.build(s)
        print("%-20s built %d frames %d sites in %.0f s"
              % (s, z["A"].shape[0], z["A"].shape[1], time.time()-t), flush=True)
    except Exception as e:
        print("%-20s FAILED %s" % (s, e), flush=True)
