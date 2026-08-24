"""Verify M95-kernel.md section 15 against the JSON its runs wrote.

Same two-pass PRESENT / DISCRIMINATE discipline as verify_s14.py, and the same
two defects already paid for once: the section is sliced with a line-anchored
regex (splitting on "## 15." also matches every "### 15.N" subheading and
silently truncates the section to its first paragraph), and short tokens
discriminate on a context anchor rather than on the bare digits.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
OUT = ROOT / "experiments" / "M95-kernel" / "out"

k11 = json.loads((OUT / "k11_exitcode.json").read_text(encoding="utf-8"))

raw = REPORT.read_text(encoding="utf-8", errors="replace")
m = re.search(r"^## 15\. ", raw, re.M)
if not m:
    raise SystemExit("section 15 not found")
sec = raw[m.start() :]
if len(sec.splitlines()) < 40:
    raise SystemExit(f"section 15 implausibly short ({len(sec.splitlines())} lines)")
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


shells = k11["shells"]
for name, blk in shells.items():
    claim(f"version {name}", blk["version"], blk["version"])

total_arms = sum(len(b["rows"]) for b in shells.values())
claim("total arms", str(total_arms), f"{total_arms} arms")
claim("verdict", k11["verdict"], "NO-FALSE-GREEN")

# Every row quoted in the report's table must match the JSON exactly.
quoted = [
    ("pwsh (7.x)", "slow exit1  no pipeline"),
    ("pwsh (7.x)", "slow exit1  | -First 3 of 10"),
    ("pwsh (7.x)", "slow exit0  | -First 3 of 10"),
    ("pwsh (7.x)", "slow exit1  | -First 99"),
    ("powershell (5.1)", "slow exit1  | -First 3 of 10"),
    ("powershell (5.1)", "slow exit0  | -First 3 of 10"),
    ("powershell (5.1)", "fast exit1  | -First 3 of 10"),
]
for shell, arm in quoted:
    row = next(r for r in shells[shell]["rows"] if r["arm"] == arm)
    claim(f"{shell[:4]} {arm[:22]} secs", f"{row['seconds']:.1f}", None)
    if row["read_code"] is not None and row["read_code"] < 0:
        claim(f"{shell[:4]} {arm[:22]} code", str(row["read_code"]), "-1")

# The headline: no arm may have read 0 for a true code of 1.
bad = [
    (s, r["arm"])
    for s, b in shells.items()
    for r in b["rows"]
    if r["true_code"] == 1 and r["read_code"] == 0
]

ok = True
print("=" * 78)
print("verify M95-kernel.md section 15  (PRESENT / DISCRIMINATE)")
print("=" * 78)
for label, text, ctx in claims:
    present = text in flat
    target = ctx if ctx else text
    dec = decoy(target)
    discriminates = dec not in flat if dec != target else True
    if ctx and ctx not in flat:
        present = False
    good = present and discriminates
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<34} {text!r:>12}  present={present} disc={discriminates}")

structural = [
    ("headline verdict stated", "NO-FALSE-GREEN"),
    ("remedy endorsed", "capture first, then filter"),
    ("5.1 fails closed", "fails closed"),
    ("7.x real hazard named", "never executes"),
    ("truncation control", "must finish in ~1"),
    ("output half confirmed", "3 of 10 lines"),
    ("own gates audited", "subprocess.run"),
    ("corpus_lint recheck", "1235 facts"),
    ("library still clean", "count = 0"),
    ("frames-40 file identified", "112MSDCF-A"),
    ("cache entry unchanged", "10:39:03"),
    ("complementary not alternatives", "complementary, not alternatives"),
    ("stale binary residual", "8118dd7"),
]
print("-" * 78)
for label, text in structural:
    good = text in flat
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<34} {text!r}")

print("-" * 78)
print(f"  {'OK ' if not bad else 'BAD'}  headline holds in the JSON: no true-1 arm read 0  ({len(bad)} violations)")
ok &= not bad

print("=" * 78)
print(f"verdict: {'GREEN' if ok else 'RED'}")
print("=" * 78)
sys.exit(0 if ok else 1)
