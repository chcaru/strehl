"""V-M116 probe 3b: the merge against the BEST of all 100 frames, not against
the frame the merge itself elected."""
import csv, json
from pathlib import Path
import numpy as np

OUT = Path(r"C:\dev\strehl-out\V-M116")
rows = list(csv.DictReader(open(OUT / "frame_sweep.csv")))
scores = json.load(open(r"C:\dev\strehl-out\M116\scores.json"))
picks = json.load(open(r"C:\dev\strehl-out\M116\single-frame-picks.json"))
mine = json.load(open(OUT / "indep_score.json"))

for s in ["bee-3-cpl", "foam", "tweezers-cpl"]:
    r = [x for x in rows if x["subject"] == s]
    assert len(r) == 100, f"{s}: {len(r)} rows"
    D = np.array([float(x["D"]) for x in r])
    N = np.array([float(x["N"]) for x in r])
    Q = D - N
    kD, kQ = int(np.argmax(D)), int(np.argmax(Q))
    u = scores[s]["unaligned"]["arms"]
    D_b1, N_b1 = u["B1u"]["D"], u["B1u"]["N"]
    kpick = picks[s]["frame_index_0based"]
    D_pick = D[kpick]
    print(f"\n=== {s} ===")
    print(f"  M116's B0 pick            : frame {kpick:3d} ({picks[s]['file']}), "
          f"{100*picks[s]['pixel_share']:.2f}% of the election map")
    print(f"  cross-check D(pick)        : {D_pick:+.5f}  vs M116's D(B0) "
          f"{u['B0']['D']:+.5f}  (delta {D_pick-u['B0']['D']:+.7f})")
    print(f"  BEST frame by D            : frame {kD:3d}  D {D[kD]:+.5f}"
          f"   (pick ranks {int((D > D_pick).sum())+1} of 100 by D)")
    print(f"  BEST frame by Q            : frame {kQ:3d}  Q {Q[kQ]:+.5f}"
          f"   (pick ranks {int((Q > (D_pick-N[kpick])).sum())+1} of 100 by Q)")
    print(f"  D over the 100 frames      : min {D.min():+.5f} median "
          f"{np.median(D):+.5f} max {D.max():+.5f}  sd {D.std():.5f}")
    print(f"  M116 headline  dD = D(B1u) - D(B0)        = {D_b1 - D_pick:+.5f} dex")
    print(f"  ADVERSARIAL    dD = D(B1u) - max_k D(k)   = {D_b1 - D[kD]:+.5f} dex")
    print(f"  ADVERSARIAL    dQ = Q(B1u) - max_k Q(k)   = "
          f"{(D_b1 - N_b1) - Q[kQ]:+.5f} dex")
    print(f"  rule-9 flat control dN = N(B1u) - N(pick) = {N_b1 - N[kpick]:+.5f} dex "
          f"({'FIRES: merge is noisier/rougher in the flat mask' if N_b1 > N[kpick] else 'passes'})")
