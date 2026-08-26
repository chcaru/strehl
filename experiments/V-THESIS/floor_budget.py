"""Two things.

(A) The load-bearing sentence: "0.5 px is also what the same instrument reports
    for the arms' NOISE GAP ALONE". Summarise their own limits.json noise_null
    table and set it beside the two other floor terms I have now measured, which
    their yardstick never counted.

(B) The last piece of the alignment confound: if BT's ECC fit had MISSED by the
    6.6% it missed by on EST-leaf-2-cpl, how much would MY headline move?
    Deliberately corrupt the scale on the real subjects and re-read.
"""
import json, pathlib, sys
import numpy as np, tifffile

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import va_blur_px  # noqa: E402

BT = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS")
R = BT / "renders"
GREEN, TILE = 1, 512
STATS = ["S1_norm", "S2_f50", "S3_acf"]

print("=" * 78)
print("(A)  what their 0.5 px yardstick was actually made of")
print("=" * 78)
lim = json.loads((BT / "limits.json").read_text(encoding="utf8"))
nn = lim["noise_null"]
print(f"\ntheir noise_null table, n={len(nn)} rows, |px| by statistic:")
for k in STATS:
    v = np.abs([r[k] for r in nn])
    print(f"   {k:<10} median {np.median(v):.3f}   max {v.max():.3f}")
allv = np.abs([r[k] for r in nn for k in STATS])
print(f"   {'ALL':<10} median {np.median(allv):.3f}   max {allv.max():.3f}"
      f"   <- the number rounded up to '0.5 px'")

print("\nthe floor has at least three terms. Their yardstick counted one:")
print(f"   noise gap        {np.median(allv):.3f} px median, {allv.max():.3f} px max   COUNTED")
print( "   kernel truncation 0.155-0.184 px                     NOT COUNTED (V-THESIS floor_exact.py)")
print( "   arm rescale       0.310-0.460 px (leaf-2 geometry)    NOT COUNTED (V-THESIS VCTRL-s-blur0.0)")
print( "                     0.320-0.361 px (ruler  geometry)    NOT COUNTED (V-THESIS VCTRL-r-blur0.0)")

print("\n" + "=" * 78)
print("(B)  would a 6.6% scale miss have changed MY headline?")
print("=" * 78)
reg = json.loads((pathlib.Path(r"C:\dev\strehl-out\V-THESIS") / "register.json").read_text(encoding="utf8"))
fit = {r["subject"]: r for r in reg} if isinstance(reg, list) else reg


def read(subj, s):
    m = tifffile.imread(str(R / subj / "merge.tif"))[:, :, GREEN].astype(np.float64)
    a = tifffile.imread(str(R / subj / "argmax.tif"))[:, :, GREEN].astype(np.float64)
    h, w = m.shape
    cy, cx = h / 2.0, w / 2.0
    Ta = int(round(TILE * s))
    vals = []
    for gy in range(TILE, h - 2 * TILE, TILE):
        for gx in range(TILE, w - 2 * TILE, TILE):
            tm = m[gy:gy + TILE, gx:gx + TILE]
            if tm.shape != (TILE, TILE) or tm.std() < 40:
                continue
            ax, ay = int(round(s * gx + cx * (1 - s))), int(round(s * gy + cy * (1 - s)))
            ta = a[ay:ay + Ta, ax:ax + Ta]
            if ta.shape != (Ta, Ta):
                continue
            v = va_blur_px(tm, ta, denoise=False)
            if v is not None and np.isfinite(v):
                vals.append(float(v))
    return float(np.median(vals)) if vals else float("nan"), len(vals)


rows = []
for subj in ("bee-3-cpl", "leaf-2-cpl", "flat-on-ruler-cpl"):
    key = [k for k in fit if k == subj]
    s0 = float(fit[subj]["scale_anchor"]) if key and "scale_anchor" in fit[subj] else \
         {"bee-3-cpl": 0.93554, "leaf-2-cpl": 0.95399, "flat-on-ruler-cpl": 0.97073}[subj]
    line = f"{subj:<20} fitted s={s0:.5f}  "
    rec = {"subject": subj, "s": s0}
    for tag, mult in (("correct", 1.0), ("-3.3%", 0.967), ("+3.3%", 1.033),
                      ("-6.6%", 0.934), ("+6.6%", 1.066)):
        v, n = read(subj, s0 * mult)
        line += f"| {tag} {v:+.3f} "
        rec[tag] = v
    rows.append(rec)
    print(line)

print("\n(a scale MISS shifts the reading by the amounts above; compare with the"
      "\n effect being argued about, which is 0.2-0.8 px)")
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\floor_budget.json").write_text(
    json.dumps(dict(noise_null_median=float(np.median(allv)), noise_null_max=float(allv.max()),
                    scale_sensitivity=rows), indent=1), encoding="utf8")
