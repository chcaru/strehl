"""Same planted blur, same source subject, ON the grid vs ACROSS the rescale.

Their CTRL-* controls plant blur with both arms on one grid (FOV 1.0000).
My VCTRL-s-* plant the same blur across leaf-2's real 6.6% rescale.
Both were measured by THEIR unmodified measure.py. Invert both with THEIR
unmodified blureq.invert() and compare the recovered blur to the truth.
"""
import json, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path("experiments/BUILD-THESIS").resolve()))
import blureq  # noqa: E402

BT = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS")
V = pathlib.Path(r"C:\dev\strehl-out\V-THESIS")
STATS = ["S1_norm", "S2_f50", "S3_acf"]


def load(p):
    return {r["subject"]: r for r in json.loads(p.read_text(encoding="utf8"))}


same = load(BT / "measure-mean.json")
across = load(V / "measure-vctrl.json")

print(f"{'control':<22}{'truth':>7}", end="")
for k in STATS:
    print(f"{k+' ratio':>16}{'-> px':>9}", end="")
print()
print("-" * 100)

pairs = [("CTRL-identity", 0.0, same), ("CTRL-blur0.8", 0.8, same), ("CTRL-blur1.5", 1.5, same),
         ("VCTRL-s-blur0.0", 0.0, across), ("VCTRL-s-blur0.4", 0.4, across),
         ("VCTRL-s-blur0.8", 0.8, across)]

out = []
for name, truth, src in pairs:
    r = src.get(name)
    if r is None:
        print(f"{name:<22}  MISSING"); continue
    print(f"{name:<22}{truth:>7.2f}", end="")
    rec = {}
    for k in STATS:
        g = float(np.median([t[f"{k}_gain"] for t in r["tiles"]]))
        px = blureq.invert(k, g)
        rec[k] = (g, px)
        print(f"{g:>16.4f}{px:>9.3f}", end="")
    print()
    out.append(dict(control=name, truth=truth,
                    **{k: dict(ratio=rec[k][0], px=rec[k][1]) for k in STATS}))

print("\n--- sensitivity actually retained across the rescale ---")
for k in STATS:
    on = next(o for o in out if o["control"] == "CTRL-blur0.8")[k]["px"]
    ac = next(o for o in out if o["control"] == "VCTRL-s-blur0.8")[k]["px"]
    print(f"{k:<10} planted 0.800 px -> on-grid {on:.3f} px, across a 6.6% rescale "
          f"{ac:.3f} px   ({100*ac/max(on,1e-9):5.1f}% retained)")

(V / "ctrl_compare.json").write_text(json.dumps(out, indent=1), encoding="utf8")
