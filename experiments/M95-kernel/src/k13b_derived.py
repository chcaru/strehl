"""K13b -- derived quantities for section 16, printed from k13's stored JSON.

Every number quoted in the report has to be printed by code run in this
session. These are differences of numbers k13 already measured; deriving them
in prose by hand is exactly the transcription route that put +8.43 dB into an
earlier report when the measurement said +5.54.
"""

import json
from pathlib import Path

OUT = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M95-kernel\out")
d = json.loads((OUT / "k13_chroma_ring.json").read_text(encoding="utf-8"))
t = d["table"]
cr = t["catmull-rom"]

print("=" * 82)
print("K13b  derived: band sharpness relative to the shipped default, vs colour cost")
print("=" * 82)
print(f"  {'kernel':<14} {'d band vs cr':>14} {'DCO':>10} {'DCO vs cr':>12}")
for k in d["kernels"]:
    db = t[k]["band"] - cr["band"]
    r = (t[k]["DCO"] / cr["DCO"]) if cr["DCO"] else float("nan")
    print(f"  {k:<14} {db:>+14.4f} {t[k]['DCO']:>10.6f} {r:>12.4f}x")

lz = t["lanczos3"]
gain = lz["band"] - cr["band"]
print(f"\n  Lanczos-3 buys {gain:+.4f} dex of band sharpness over Catmull-Rom")
print(f"  and pays {lz['DCO'] / cr['DCO']:.4f}x its differential chroma overshoot.")
print(f"  Cost per unit gain: {(lz['DCO'] - cr['DCO']) / gain:.4f} DN of new")
print("  colour fringe per dex of band sharpness.")

nn, bl = t["nearest"], t["bilinear"]
print(f"\n  Nearest is {nn['band'] - cr['band']:+.4f} dex sharper than Catmull-Rom")
print(f"  at DCO exactly {nn['DCO']:.6f}; bilinear is {bl['band'] - cr['band']:+.4f} dex")
print(f"  softer, also at exactly {bl['DCO']:.6f}. Monotone kernels sit at both")
print("  ends of the sharpness range while creating zero colour fringe, which is")
print("  what shows DCO is not a restatement of sharpness.")

p = d["paired"]
print(f"\n  paired: {p['wins']}/{p['n']} = {p['pct']:.2f}%, 95% CI "
      f"[{p['ci'][0]:.4f}, {p['ci'][1]:.4f}]")
