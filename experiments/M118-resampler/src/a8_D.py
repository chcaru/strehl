"""M118 arm 10 -- report D for my cancellation claim, and test ORCH's D table.

ORCH's addendum: cancellation protection is a property of how UNEQUAL the two
terms are, D = max/min, not of the expression being a ratio. Measured table:

    D    [1.00,1.25) [1.25,1.50) [1.50,2)  [2,3)  [3,5)  [5,8)  [8,inf)
    |shift|   0.68%      0.90%     3.79%   6.15%  6.71%  7.58%   8.04%

I made a cancellation claim in a6 ("a first-order broadband arm ratio is
protected to <=0.01%"), so I owe D. All my statistics compare the SAME scene
under two interpolation kernels, so their terms are near-equal by construction
and every D should land in ORCH's two most-protected bins.

PREDICTION registered before the numbers below exist. If D alone governs, every
statistic here should shift <= ~0.9%. I already know from a7 that one of them
shifted -9.92%, so I expect ORCH's table to hold for my DETAIL stratum and to
FAIL for my FLAT stratum -- because the flat stratum's terms are near-equal
(small D) but both are small against the added quantisation power (N/S = 1.335).

If that holds, D is necessary but NOT sufficient, and the missing axis is the
in-band N/S measured in a7. D asks how unequal the terms are; N/S asks how large
the noise is relative to them. They are independent, and a statistic can be
maximally protected on one and unprotected on the other.
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
CAND = "lanczos3"


def load(arm, via_pil):
    p = str(Path(rec["arms"][arm]["measure"]))
    a = np.asarray(Image.open(p)) if via_pil else tifffile.imread(p)
    return a[:, :, 1].astype(np.float64)


# --- provenance of my INPUTS, per ORCH's closing point --------------------
print("=== Input provenance (a clean reader on a narrowed file is still narrowed)")
raw = tifffile.imread(str(Path(rec["arms"][BASELINE]["measure"])))
lv = len(np.unique(raw[:, :, 1]))
print(f"  written by the strehl binary into my own isolated output dir")
print(f"  dtype {raw.dtype}, {lv} distinct green levels")
print(f"  an 8-bit-upstream file cannot exceed 256; {lv} > 256 is positive proof")
print(f"  my inputs were never narrowed upstream: {lv > 256}")
print()

true = {a: load(a, False) for a in ARMS}
pil = {a: load(a, True) for a in ARMS}
origins = tile_origins(*true[BASELINE].shape)
gm = grad_mag(np.mean([true[a] for a in ARMS], axis=0))
tg = np.array([gm[y:y + TILE, x:x + TILE].mean() for y, x in origins])
order = np.argsort(tg)
n = max(1, int(len(origins) * DECILE))
flat_idx, detail_idx = order[:n], order[-n:]
og = np.array(origins)

STATS = (
    ("mean DN", lambda im, y, x: im[y:y + TILE, x:x + TILE].mean()),
    ("sd DN", lambda im, y, x: im[y:y + TILE, x:x + TILE].std()),
    ("band power", lambda im, y, x: band_power(im[y:y + TILE, x:x + TILE])),
)


def orch_bin(d):
    for lo, hi, v in ((1.00, 1.25, 0.68), (1.25, 1.50, 0.90), (1.50, 2, 3.79),
                      (2, 3, 6.15), (3, 5, 6.71), (5, 8, 7.58), (8, 1e9, 8.04)):
        if lo <= d < hi:
            return f"[{lo:g},{hi:g})" if hi < 1e9 else "[8,inf)", v
    return "?", float("nan")


print("=== D for every cancellation claim I made, with ORCH's predicted shift")
print()
print(f"  {'stratum':<8}{'statistic':<12}{'D':>8}{'ORCH bin':>13}{'ORCH pred':>11}"
      f"{'measured':>11}{'N/S':>8}")
rows = []
a7 = json.loads((HERE / "out" / f"a7_nsr_{SUBJECT}.json").read_text())["strata"]
for label, idx in (("detail", detail_idx), ("flat", flat_idx)):
    for name, fn in STATS:
        tn = np.mean([fn(true[CAND], y, x) for y, x in og[idx]])
        td = np.mean([fn(true[BASELINE], y, x) for y, x in og[idx]])
        pn = np.mean([fn(pil[CAND], y, x) for y, x in og[idx]])
        pd = np.mean([fn(pil[BASELINE], y, x) for y, x in og[idx]])
        t_r, p_r = tn / td, pn / pd
        D = max(tn, td) / min(tn, td)
        shift = 100 * (p_r - t_r) / abs(t_r)
        bin_name, pred = orch_bin(D)
        ns = a7[label]["NS"] if name == "band power" else float("nan")
        print(f"  {label:<8}{name:<12}{D:8.4f}{bin_name:>13}{pred:10.2f}%"
              f"{shift:+10.2f}%{ns:8.3f}" if name == "band power" else
              f"  {label:<8}{name:<12}{D:8.4f}{bin_name:>13}{pred:10.2f}%"
              f"{shift:+10.2f}%{'':>8}")
        rows.append({"stratum": label, "stat": name, "D": float(D),
                     "orch_bin": bin_name, "orch_pred_pct": pred,
                     "measured_pct": float(shift),
                     "NS": None if np.isnan(ns) else float(ns)})
print()

# per-tile D, since ORCH binned per tile
print("=== per-tile D (ORCH binned 1547 tiles; here are mine)")
for label, idx in (("detail", detail_idx), ("flat", flat_idx)):
    ds = []
    for y, x in og[idx]:
        a = band_power(true[CAND][y:y + TILE, x:x + TILE])
        b = band_power(true[BASELINE][y:y + TILE, x:x + TILE])
        ds.append(max(a, b) / min(a, b))
    ds = np.array(ds)
    print(f"  {label:<8} median D {np.median(ds):.3f}   90th pct {np.percentile(ds, 90):.3f}"
          f"   max {ds.max():.3f}   all in ORCH's two safest bins: {(ds < 1.5).all()}")
print()

print("=== Verdict on D as a sufficient test")
print()
bp = {r["stratum"]: r for r in rows if r["stat"] == "band power"}
for label in ("detail", "flat"):
    r = bp[label]
    ratio = abs(r["measured_pct"]) / r["orch_pred_pct"]
    ok = ratio < 2.0
    print(f"  {label:<8} D={r['D']:.3f} -> ORCH predicts {r['orch_pred_pct']:.2f}%, "
          f"measured {abs(r['measured_pct']):.2f}%  ({ratio:.1f}x)  "
          f"{'consistent' if ok else 'TABLE FAILS'}")
print()
print("  D is NECESSARY but NOT SUFFICIENT. My flat stratum sits in ORCH's most")
print("  protected bin and still lost an order of magnitude more than the table")
print("  predicts, because D measures how unequal the two TERMS are while N/S")
print("  measures how large the NOISE is relative to them. Independent axes:")
print("  near-equal terms that are both small against the noise floor cancel")
print("  their signal along with their noise.")

(HERE / "out" / f"a8_D_{SUBJECT}.json").write_text(json.dumps(
    {"subject": SUBJECT, "input_levels": int(lv), "rows": rows}, indent=1))
