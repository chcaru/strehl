import json, pathlib
import numpy as np
d = json.loads(pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\measure-subjects.json").read_text())
print("Half-energy frequency f50 (cyc/px), BUILD-THESIS's own S2, median over their tiles.")
print("My spectral fit band spans 0.031 to 0.25 cyc/px (period 32 to 4 merge px).")
print()
print(f"{'subject':<19}{'f50 merge':>10}{'f50 argmax':>11}{'period px':>11}   in my band?")
for r in d:
    fm = float(np.median([t["S2_f50_merge"] for t in r["tiles"]]))
    fa = float(np.median([t["S2_f50_argmax"] for t in r["tiles"]]))
    print(f"{r['subject']:<19}{fm:>10.4f}{fa:>11.4f}{1/fm:>11.2f}   "
          f"{'YES' if 0.031 < fm < 0.25 else 'NO'}")
