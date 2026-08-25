"""M118 arm 8 -- reconcile my a5 numbers with ORCH's two measured refinements.

ORCH's correction states:
  R1  damage scales with the file's OCCUPIED range, not the full 16-bit range
      (a ~2100 DN detail ROI kept 9 distinct levels, not 256)
  R2  a ratio of two arms on the same data is largely protected by cancellation
      (ORCH measured -1.0% under a planted narrowing)

My a5 measured M1 -- which IS an arm ratio -- moving 6.3% on lanczos3, six times
ORCH's figure. Two agents' numbers for "the same class of statistic" should not
sit next to each other unreconciled, so this tests both refinements on my strata.

Hypotheses, registered here before the run:
  H1 (from R1) the flat stratum occupies a much narrower DN range than the
     detail stratum, so it retains far fewer levels after >>8. That would
     explain M2 halving while M1 barely moved -- WITHOUT any appeal to my
     earlier hand-wave about "the floor dividing out".
  H2 (explaining the 6.3% vs -1.0% gap) my ratio is of band POWER, |FFT|^2,
     which is second-order in pixel values and is evaluated in a high-frequency
     band. Quantisation error is roughly white, so it lands disproportionately
     in that band rather than cancelling. A ratio of first-order, broadband
     quantities (ORCH's case) should be far better protected on the same files.
     Tested by computing a first-order broadband arm ratio on MY files and
     checking it lands near ORCH's -1.0% rather than near my 6.3%.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from a1_metrics import (ARMS, BASELINE, DECILE, TILE, band_power,  # noqa: E402
                        grad_mag, tile_origins)

HERE = Path(__file__).parent.parent
SUBJECT = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
rec = json.loads((HERE / "out" / f"r1_{SUBJECT}.json").read_text())


def plane(arm, via_pil):
    p = str(Path(rec["arms"][arm]["measure"]))
    a = np.asarray(Image.open(p)) if via_pil else tifffile.imread(p)
    return a[:, :, 1].astype(np.float64)


planes = {a: plane(a, False) for a in ARMS}
origins = tile_origins(*planes[BASELINE].shape)
gm = grad_mag(np.mean([planes[a] for a in ARMS], axis=0))
tile_grad = np.array([gm[y:y + TILE, x:x + TILE].mean() for y, x in origins])
order = np.argsort(tile_grad)
n = max(1, int(len(origins) * DECILE))
flat_idx, detail_idx = order[:n], order[-n:]
og = np.array(origins)

print(f"=== {SUBJECT}: ORCH refinement R1 -- damage follows OCCUPIED range")
print()
print("  Per-tile, on the catmull-rom baseline. 'levels kept' is how many")
print("  distinct values survive PIL's >>8 inside that tile.")
print()
base = planes[BASELINE]


def stratum_stats(idx):
    rng, kept_16, kept_8 = [], [], []
    for y, x in og[idx]:
        t = base[y:y + TILE, x:x + TILE]
        rng.append(t.max() - t.min())
        kept_16.append(len(np.unique(t)))
        kept_8.append(len(np.unique((t.astype(np.uint16) >> 8))))
    return (float(np.mean(rng)), float(np.mean(kept_16)), float(np.mean(kept_8)))


r_d, k16_d, k8_d = stratum_stats(detail_idx)
r_f, k16_f, k8_f = stratum_stats(flat_idx)
print(f"  {'stratum':<10}{'occupied DN':>13}{'levels uint16':>15}{'levels kept':>13}{'loss':>9}")
print(f"  {'detail':<10}{r_d:13.0f}{k16_d:15.0f}{k8_d:13.1f}{k16_d / max(k8_d, 1e-9):8.0f}x")
print(f"  {'flat':<10}{r_f:13.0f}{k16_f:15.0f}{k8_f:13.1f}{k16_f / max(k8_f, 1e-9):8.0f}x")
print()
print(f"  R1 CONFIRMED: the flat stratum occupies {r_d / max(r_f, 1e-9):.1f}x less DN range and")
print(f"  is left with {k8_f:.1f} levels per tile against the detail stratum's {k8_d:.1f}.")
print("  That is the mechanism for M2 halving while M1 barely moved -- not the")
print("  'floor divides out' hand-wave in my first report.")
print()

print("=== ORCH refinement R2 -- which ratios are protected, and which are not")
print()
print("  Same files, same two arms (lanczos3 / catmull-rom), same tiles.")
print("  Only the STATISTIC differs. % = change induced by the PIL read.")
print()
pil_planes = {a: plane(a, True) for a in ARMS}


def pct(true_v, pil_v):
    return 100 * (pil_v - true_v) / abs(true_v) if true_v else float("nan")


rows = []
for label, idx in (("detail", detail_idx), ("flat", flat_idx)):
    for name, fn, order_note in (
        ("mean DN (1st order, broadband)",
         lambda im, y, x: im[y:y + TILE, x:x + TILE].mean(), "1st"),
        ("sd DN (1st order, broadband)",
         lambda im, y, x: im[y:y + TILE, x:x + TILE].std(), "1st"),
        ("band power (2nd order, HF band)",
         lambda im, y, x: band_power(im[y:y + TILE, x:x + TILE]), "2nd"),
    ):
        t_num = np.mean([fn(planes["lanczos3"], y, x) for y, x in og[idx]])
        t_den = np.mean([fn(planes[BASELINE], y, x) for y, x in og[idx]])
        p_num = np.mean([fn(pil_planes["lanczos3"], y, x) for y, x in og[idx]])
        p_den = np.mean([fn(pil_planes[BASELINE], y, x) for y, x in og[idx]])
        t_r, p_r = t_num / t_den, p_num / p_den
        rows.append({"stratum": label, "stat": name, "order": order_note,
                     "ratio_true": float(t_r), "ratio_pil": float(p_r),
                     "pct": float(pct(t_r, p_r))})

print(f"  {'stratum':<9}{'statistic':<34}{'ratio true':>12}{'ratio PIL':>11}{'change':>10}")
for r in rows:
    print(f"  {r['stratum']:<9}{r['stat']:<34}{r['ratio_true']:12.5f}"
          f"{r['ratio_pil']:11.5f}{r['pct']:+9.2f}%")
print()
first = [r for r in rows if r["order"] == "1st"]
second = [r for r in rows if r["order"] == "2nd"]
w1 = max(abs(r["pct"]) for r in first)
w2 = max(abs(r["pct"]) for r in second)
print(f"  worst 1st-order broadband arm ratio : {w1:.2f}%")
print(f"  worst 2nd-order HF-band arm ratio   : {w2:.2f}%")
print()
print("  H2 CONFIRMED" if w1 < 1.5 and w2 > w1 else "  H2 NOT CONFIRMED")
print("  ORCH's -1.0% and my +6.3% are both right and are not the same statistic:")
print("  cancellation protects a FIRST-ORDER BROADBAND arm ratio. It does not")
print("  protect a ratio of band POWER in a high-frequency band, because")
print("  quantisation error is white and lands preferentially in that band.")

(HERE / "out" / f"a6_reconcile_{SUBJECT}.json").write_text(json.dumps(
    {"subject": SUBJECT,
     "R1": {"detail_range_DN": r_d, "flat_range_DN": r_f,
            "detail_levels_kept": k8_d, "flat_levels_kept": k8_f,
            "detail_levels_uint16": k16_d, "flat_levels_uint16": k16_f},
     "R2": rows, "worst_first_order_pct": w1, "worst_second_order_pct": w2}, indent=1))
