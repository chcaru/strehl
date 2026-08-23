import numpy as np
b=np.load(r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files\best_rel.npy")
print("=== ROBUSTNESS: how wrong would my crossover calibration have to be to flip the verdict? ===")
print("  crossover 0.3440 is the weakest link (1-D sim window vs 2-D CFA window). Sweep it.")
print(f"{'crossover':>10} {'x error':>8} | {'% pixels where deconvolution WINS':>34}")
for mult in (0.5,1.0,2.0,3.0,4.0,6.0,10.0):
    c=0.3440*mult
    print(f"{c:>10.4f} {mult:>7.1f}x | {float(np.mean(b<c))*100:>33.1f}%")
print()
print(f"  median pixel sits at sigma_rel = {float(np.median(b)):.4f}, which is {float(np.median(b))/0.3440:.1f}x PAST the crossover.")
print("  To make deconvolution the right default (>50% of pixels) the crossover would have to be")
print(f"  wrong by {float(np.median(b))/0.3440:.1f}x in the favourable direction.")
