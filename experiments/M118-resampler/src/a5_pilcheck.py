"""M118 arm 7 -- ORCH's PIL 16-bit RGB hazard, checked against my own outputs.

Two questions, both answered by running rather than by reasoning:

  Q1  What do MY measurement TIFFs actually contain, and what does each reader
      return for them?
  Q2  I hold the ground-truth uint16 answer for a real kernel A/B, so I can
      measure what the PIL defect WOULD have done to it. That turns ORCH's
      "will read as zero, as noise, or as a clean null" into a number.

Q2 is the point. My five arms span two orders of magnitude of effect size
(lanczos2 +0.003 dex, lanczos3 +0.087, bilinear -0.218), so this milestone is a
ready-made calibration of the defect against signal size -- exactly the axis
ORCH flagged as most suspect.

The whole pipeline is re-run per reader, including the cross-arm stratification,
because the strata are themselves computed from pixels.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from a1_metrics import (ARMS, BASELINE, DECILE, TILE, grad_mag,  # noqa: E402
                        tile_bandpowers, tile_origins)

HERE = Path(__file__).parent.parent
SUBJECT = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
rec = json.loads((HERE / "out" / f"r1_{SUBJECT}.json").read_text())

print(f"=== Q1. {SUBJECT}: what my measurement TIFFs contain, both readers")
print()
print(f"  {'arm':<13}{'tifffile':<26}{'PIL':<22}{'levels tf':>10}{'levels PIL':>12}")
q1 = {}
for arm in ARMS:
    p = Path(rec["arms"][arm]["measure"])
    tf = tifffile.imread(str(p))
    im = Image.open(str(p))
    pil = np.asarray(im)
    tf_lv = len(np.unique(tf[:, :, 1]))
    pil_lv = len(np.unique(pil[:, :, 1] if pil.ndim == 3 else pil))
    print(f"  {arm:<13}{str(tf.dtype) + ' ' + str(tf.shape):<26}"
          f"{str(pil.dtype) + ' mode=' + im.mode:<22}{tf_lv:>10}{pil_lv:>12}")
    q1[arm] = {"tifffile_dtype": str(tf.dtype), "pil_dtype": str(pil.dtype),
               "pil_mode": im.mode, "levels_tifffile": int(tf_lv),
               "levels_pil": int(pil_lv), "tf_max": int(tf.max())}

hit = [a for a in ARMS if q1[a]["pil_dtype"] == "uint8" and q1[a]["tifffile_dtype"] != "uint8"]
print()
print(f"  ORCH's defect reproduces on my own files: {len(hit)}/5 arms")
if hit:
    r = q1[hit[0]]
    print(f"  level resolution lost: {r['levels_tifffile']} -> {r['levels_pil']} "
          f"= {r['levels_tifffile'] / max(r['levels_pil'], 1):.0f}x")
print()
print("  Every TIFF read in this milestone goes through tifffile.imread, so the")
print("  published numbers are the LEFT column. Q2 measures the right one.")
print()

# Is PIL's downconversion a >>8 truncation? Q2 must not rest on a straw man.
_p = Path(rec["arms"][BASELINE]["measure"])
_tf = tifffile.imread(str(_p))
_pil = np.asarray(Image.open(str(_p)))
shift8 = bool((_pil == (_tf >> 8).astype(np.uint8)).all()) if _pil.ndim == 3 else False
print(f"  PIL output == (uint16 >> 8) exactly: {shift8}")
if not shift8 and _pil.ndim == 3:
    d = np.abs(_pil.astype(int) - (_tf >> 8).astype(int))
    print(f"    max |diff| {d.max()}, mean {d.mean():.4f}"
          f" -- Q2 below uses PIL's real output, not this model")
print()


def plane(path, via_pil):
    a = np.asarray(Image.open(str(path))) if via_pil else tifffile.imread(str(path))
    return a[:, :, 1].astype(np.float64)


def run_pipeline(via_pil):
    """a1_metrics.analyse's M1/M2/M4, end to end, for one reader."""
    planes = {a: plane(Path(rec["arms"][a]["measure"]), via_pil) for a in ARMS}
    origins = tile_origins(*planes[BASELINE].shape)
    gm = grad_mag(np.mean([planes[a] for a in ARMS], axis=0))
    tile_grad = np.array([gm[y:y + TILE, x:x + TILE].mean() for y, x in origins])
    order = np.argsort(tile_grad)
    n = max(1, int(len(origins) * DECILE))
    flat_idx, detail_idx = order[:n], order[-n:]
    bp = {a: tile_bandpowers(planes[a], origins) for a in ARMS}
    base = bp[BASELINE]
    out = {a: {"M1": float(np.log10(bp[a][detail_idx] / base[detail_idx]).mean()),
               "M2": float(np.log10(bp[a][flat_idx] / base[flat_idx]).mean()),
               "sd": float(np.mean([planes[a][y:y + TILE, x:x + TILE].std()
                                    for y, x in np.array(origins)[flat_idx]]))}
           for a in ARMS}
    out["_sep"] = float(tile_grad[detail_idx].mean() / max(tile_grad[flat_idx].mean(), 1e-9))
    return out


true = run_pipeline(False)
pil = run_pipeline(True)

print("=== Q2. What the defect WOULD have done to this kernel A/B")
print()
print("  Same metric, same band, same code. Only the reader differs.")
print()
print(f"  {'arm':<13}{'M1 published':>14}{'M1 via PIL':>13}{'error':>10}{'% of eff':>10}"
      f"     {'M2 pub':>9}{'M2 PIL':>9}")
rows = []
for a in ARMS:
    if a == BASELINE:
        continue
    t, p = true[a]["M1"], pil[a]["M1"]
    err = p - t
    pct = 100 * abs(err) / abs(t) if t else float("nan")
    print(f"  {a:<13}{t:+14.4f}{p:+13.4f}{err:+10.4f}{pct:9.1f}%     "
          f"{true[a]['M2']:+9.4f}{pil[a]['M2']:+9.4f}")
    rows.append({"arm": a, "M1_published": t, "M1_via_pil": p, "error": err,
                 "pct_of_effect": pct, "M2_published": true[a]["M2"],
                 "M2_via_pil": pil[a]["M2"]})

# The consequence that matters. M3 = M1 - M2 is rule 9's control: "is the gain
# concentrated where the detail is?" The flat decile is by definition the
# low-signal stratum, so an 8-bit floor bites it hardest and drags M2 toward
# zero -- which INFLATES M3 and manufactures a passing control.
print()
print("  -- rule 9's control, M3 = M1 - M2, computed both ways")
print()
print(f"  {'arm':<13}{'M3 published':>14}{'M3 via PIL':>13}   verdict flip?")
for r in rows:
    a = r["arm"]
    t3 = true[a]["M1"] - true[a]["M2"]
    p3 = pil[a]["M1"] - pil[a]["M2"]
    r["M3_published"], r["M3_via_pil"] = t3, p3
    r["M3_sign_flip"] = bool(np.sign(t3) != np.sign(p3))
    flip = ("SIGN REVERSED -- control verdict inverted" if r["M3_sign_flip"]
            else f"same sign, {abs(p3) / max(abs(t3), 1e-9):.1f}x magnitude")
    print(f"  {a:<13}{t3:+14.4f}{p3:+13.4f}   {flip}")
n_flip = sum(r["M3_sign_flip"] for r in rows)
print()
print(f"  M3 sign reverses on {n_flip}/{len(rows)} arms.")
if any(r["arm"] == "lanczos3" and r["M3_sign_flip"] for r in rows):
    print("  Including lanczos3 -- i.e. this milestone's central finding (that the")
    print("  gain is NOT concentrated in detail) would have been INVERTED by PIL.")

print()
print(f"  flat-decile spatial sd (M4), catmull-rom : published {true[BASELINE]['sd']:8.1f} DN"
      f"   via PIL {pil[BASELINE]['sd']:.2f} DN")
print(f"  detail/flat stratum separation           : published {true['_sep']:8.2f}x"
      f"   via PIL {pil['_sep']:.2f}x")
print()
worst = max(rows, key=lambda r: r["pct_of_effect"])
best = min(rows, key=lambda r: r["pct_of_effect"])
print(f"  worst distortion : {worst['arm']:<12}{worst['pct_of_effect']:7.1f}% of its own effect"
      f"   ({worst['M1_published']:+.4f} -> {worst['M1_via_pil']:+.4f})")
print(f"  least distortion : {best['arm']:<12}{best['pct_of_effect']:7.1f}%"
      f"   ({best['M1_published']:+.4f} -> {best['M1_via_pil']:+.4f})")
print()
print("  The defect is a fixed quantisation floor, so read the % column against")
print("  effect size: mildest on the largest effect, worst on the smallest.")

(HERE / "out" / f"a5_pilcheck_{SUBJECT}.json").write_text(json.dumps(
    {"subject": SUBJECT, "q1": q1, "pil_is_shift8": shift8, "q2": rows,
     "sep_published": true["_sep"], "sep_via_pil": pil["_sep"],
     "sd_published": true[BASELINE]["sd"], "sd_via_pil": pil[BASELINE]["sd"]}, indent=1))
