"""Side-by-side: the same tile and statistic on the default and argmax paths."""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
a = json.loads((H / "highlight_after.json").read_text(encoding="utf-8"))
g = json.loads((H / "argmax_control.json").read_text(encoding="utf-8"))

hdr = (f"{'subject':<20} {'default':>9} {'argmax':>9} {'swing':>9} "
       f"{'def 1-sided':>12} {'arg 1-sided':>12} {'def c_g':>8} {'arg c_g':>8}")
print(hdr)
print("-" * len(hdr))
for k, v in a["subjects"].items():
    o = g["subjects"].get(k)
    if not o or not o.get("ok"):
        continue
    d1 = v["one_sided_off"]
    a1 = o["one_sided_off"]
    print(f"{k:<20} {v['off']:>+9.4f} {o['off']:>+9.4f} "
          f"{o['off'] - v['off']:>+9.4f} "
          f"{('%+.4f' % d1) if d1 is not None else 'n/a':>12} "
          f"{('%+.4f' % a1) if a1 is not None else 'n/a':>12} "
          f"{v['c_g']:>8.3f} {o['c_g']:>8.3f}")
print("\noff < 0 magenta, off > 0 green. Same tile, same raws, same statistic;")
print("the only difference is which merge command produced the pixels.")
