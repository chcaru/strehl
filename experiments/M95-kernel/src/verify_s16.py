"""Verify M95-kernel.md section 16 against the JSON its runs wrote.

Same PRESENT / DISCRIMINATE discipline as verify_s14/s15, and the same two
defects already paid for: the section is sliced with a line-anchored regex
(splitting on "## 16." also matches "### 16.N" and truncates the section to
its first paragraph), and short tokens discriminate on a context anchor.

S1 is checked in the JSON as an exact float equality, not as a printed string,
because the claim is that a monotone kernel's overshoot is EXACTLY zero. A
report saying "0.000000" over a JSON holding 1e-9 would be a false green, and
that is the whole load-bearing control of section 16.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
OUT = ROOT / "experiments" / "M95-kernel" / "out"

k13 = json.loads((OUT / "k13_chroma_ring.json").read_text(encoding="utf-8"))
t = k13["table"]

raw = REPORT.read_text(encoding="utf-8", errors="replace")
m = re.search(r"^## 16\. ", raw, re.M)
if not m:
    raise SystemExit("section 16 not found")
sec = raw[m.start() :]
if len(sec.splitlines()) < 60:
    raise SystemExit(f"section 16 implausibly short ({len(sec.splitlines())} lines)")
flat = re.sub(r"\s+", " ", sec)


def decoy(s: str) -> str:
    mm = re.search(r"\d(?=[^\d]*$)", s)
    if not mm:
        return s + "0"
    i = mm.start()
    return s[:i] + str((int(s[i]) + 1) % 10) + s[i + 1 :]


claims = []


def claim(label, text, ctx=None):
    claims.append((label, text, ctx))


cr = t["catmull-rom"]
for k in k13["kernels"]:
    claim(f"DCO {k}", f"{t[k]['DCO']:.6f}", f"| {k} | **{t[k]['DCO']:.6f}**"
          if t[k]["DCO"] == 0.0 else f"| {k} | {t[k]['DCO']:.6f} |")
    claim(f"band {k}", f"{t[k]['band']:.4f}".replace("-", "\u2212"),
          f"{t[k]['band']:.4f}".replace("-", "\u2212"))
    d = t[k]["band"] - cr["band"]
    claim(f"dband {k}", f"{d:+.4f}".replace("-", "\u2212"),
          f"{d:+.4f}".replace("-", "\u2212"))

claim("ratio lz/cr", f"{k13['controls']['lz_over_cr']:.4f}", "1.9563\u00d7")
p = k13["paired"]
claim("paired wins", f"{p['wins']}/{p['n']}", "120/120")
claim("paired pct", f"{p['pct']:.2f}", "100.00%")
claim("ci lo", f"{p['ci'][0]:.4f}", "[1.9045")
claim("ci hi", f"{p['ci'][1]:.4f}", "2.0104]")
claim("tiles", str(k13["n_tiles"]), "24 tiles")
claim("tile size", str(k13["tile"]), "512 px")
claim("edge pct", "1%", "top 1% of")

ok = True
print("=" * 78)
print("verify M95-kernel.md section 16  (PRESENT / DISCRIMINATE)")
print("=" * 78)
for label, text, ctx in claims:
    present = text in flat
    target = ctx if ctx else text
    if ctx and ctx not in flat:
        present = False
    dec = decoy(target)
    discriminates = dec not in flat if dec != target else True
    good = present and discriminates
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<24} {text!r:>14}  present={present} disc={discriminates}")

print("-" * 78)
s1_json = t["nearest"]["DCO"] == 0.0 and t["bilinear"]["DCO"] == 0.0
print(f"  {'OK ' if s1_json else 'BAD'}  S1 exact-zero holds in the JSON as a float, not a string")
ok &= s1_json
s3_json = t["lanczos3"]["DCO"] > cr["DCO"]
print(f"  {'OK ' if s3_json else 'BAD'}  S3 ordering holds in the JSON")
ok &= s3_json
brackets = ((t["nearest"]["band"] > cr["band"]) and (t["bilinear"]["band"] < cr["band"]))
print(f"  {'OK ' if brackets else 'BAD'}  the two zero-DCO kernels bracket the default in sharpness")
ok &= brackets

structural = [
    ("K12 declared void", "ARM VOID"),
    ("K12 bar not moved", "The bar was not moved"),
    ("K12 plant defect owned", "resample-matched"),
    ("K12 diagnosis", "A coloured edge is not a fringe"),
    ("K12 monotone response", "495.15 \u2192 503.82 \u2192 524.54"),
    ("K12 best reading", "+0.0598"),
    ("kernels cannot create CA", "cannot create lateral chromatic aberration"),
    ("DCO defined differentially", "differs *between* channels"),
    ("mask fixed on source", "held fixed across kernels"),
    ("S1 is falsifiable", "could have failed"),
    ("S3 predicted from luma", "1.7826"),
    ("not a sharpness restatement", "opposite ends"),
    ("cost per dex", "8.8328"),
    ("fringe reinterpreted", "not created by `nearest`"),
    ("two fringes distinguished", "call for opposite remedies"),
    ("evidence against own case", "evidence against my own recommendation"),
    ("default unchanged", "default stays Catmull-Rom"),
    ("capture request", "lateral-CA target"),
    ("bee contrast figure", "0.0345%"),
]
for label, text in structural:
    good = text in flat
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<34} {text!r}")

print("=" * 78)
print(f"verdict: {'GREEN' if ok else 'RED'}")
print("=" * 78)
sys.exit(0 if ok else 1)
