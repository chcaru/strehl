import sys
import ladder
D = r"C:\dev\strehl-out\V-KILLB0"
print("FLAT = least-structured quartile (the win); STRUCT = most-structured quartile (the cost)")
for nm in sys.argv[1:]:
    for arm in ("b0x2", "b0x4"):
        import os
        pa = os.path.join(D, "default", nm + ".tiff")
        pb = os.path.join(D, arm, nm + ".tiff")
        if os.path.exists(pa) and os.path.exists(pb):
            ladder.run(pa, pb, nm, arm)
    print()
