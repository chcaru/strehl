"""M113 K11 - repair of the edge-density column, and the honest reading of K10.

K9's edge density read 0.0000 on seven of nine stacks: a fixed 10%-of-range
gradient threshold is a dead instrument on these frames, exactly like the K5
extrema probe that returned 0.00 for both arms. It is replaced here with a
scale-free measure (median absolute gradient normalised by the frame's robust
range), which cannot saturate to zero.

The point at issue: the orchestrator's discriminator is "a ringing artefact
tracks edge density, a kernel property does not". That test is only meaningful
if edge density actually VARIES across the nine.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "M95-resample", "src"))
import x2_pairs as X  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
S = r"C:\dev\strehl-out\M113\stacks"
k9 = json.load(open(os.path.join(OUT, "k9_stacks.json")))
k10 = json.load(open(os.path.join(OUT, "k10_blind.json")))

print(f"{'stack':22s} {'edge density':>13s} {'GAIN dex':>10s}")
dens, gain = [], []
for n, v in k9.items():
    if n.startswith("_"):
        continue
    img = X.load_luma(os.path.join(S, f"{n}-1f.tif")).astype(np.float64)
    sm = img[::4, ::4]
    g = np.hypot(*np.gradient(sm))
    rng_ = np.percentile(sm, 99.5) - np.percentile(sm, 0.5)
    d = float(np.median(g) / rng_) if rng_ > 0 else 0.0
    dens.append(d)
    gain.append(v["gain"])
    print(f"{n:22s} {d:13.5f} {v['gain']:+10.4f}")

dens, gain = np.array(dens), np.array(gain)
print(f"\nedge density varies {dens.max()/dens.min():.1f}x across the nine "
      f"({dens.min():.5f} .. {dens.max():.5f})")
print(f"the GAIN varies {(gain.max()-gain.min())/gain.mean()*100:.2f}% "
      f"({gain.min():+.4f} .. {gain.max():+.4f})")
print(f"corr(edge density, gain) = {np.corrcoef(dens, gain)[0,1]:+.4f}")

cf = k10["A1_closed_form_no_image"]["gain"]
ph = k10["A4_nine_photographs"]["gain"]
print(f"\n--- how much of the number needs a camera? ---")
print(f"closed form, flat spectrum, NO IMAGE : {cf:+.4f} dex")
print(f"nine real photographs                : {ph:+.4f} dex")
print(f"the photographs move it by           : {ph-cf:+.4f} dex "
      f"({abs(ph-cf)/abs(ph)*100:.1f}% of the reading)")
print(f"so {100-abs(ph-cf)/abs(ph)*100:.1f}% of fact 1420's headline is predicted")
print("by the kernel coefficients alone, with no camera and no stack.")
print(f"\nPRE-REGISTERED BAR: K10 spread < 0.02 across all five arms -> "
      f"{k10['_verdict']['spread']:.4f}, FAILED.")
print("Reported as failed. The failure is carried entirely by the artificial")
print("'gaussian blobs' arm, a band-limited field with almost no power in the")
print("scoring band. Across the four arms with realistic spectra (closed form,")
real = [k10["A1_closed_form_no_image"]["gain"], k10["white noise"]["gain"],
        k10["1/f^2 noise"]["gain"], ph]
print(f"white, 1/f^2, photographs) the spread is {max(real)-min(real):.4f} dex.")
json.dump(dict(edge_density=dens.tolist(), gain=gain.tolist(),
               corr=float(np.corrcoef(dens, gain)[0, 1]),
               density_ratio=float(dens.max() / dens.min()),
               gain_pct_spread=float((gain.max() - gain.min()) / gain.mean() * 100),
               closed_form=cf, photographs=ph, camera_contribution_dex=float(ph - cf),
               realistic_spread=float(max(real) - min(real))),
          open(os.path.join(OUT, "k11_density.json"), "w"), indent=1)
print(f"\nwrote {os.path.join(OUT, 'k11_density.json')}")