import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB
for s in sys.argv[1:]:
    print("### building band cache:", s, flush=True)
    try:
        SB.build(s)
        print("### done:", s, flush=True)
    except Exception as e:
        print("### FAILED:", s, type(e).__name__, e, flush=True)
