"""gen_counts.py — emit the boundary-aware occurrence table for verify_patch.

Registered counts are maintained, not guessed. This prints the current count
for every token verify_patch pins, so an edit that legitimately adds or removes
a site is a deliberate one-line change rather than an invitation to loosen the
check. Identical role to count_sites.py for section 5f.
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

REPORT = Path(__file__).resolve().parents[2] / "docs" / "research" / \
    "M116-promotion.md"
FLAT = re.sub(r"\s+", " ", REPORT.read_text(encoding="utf-8"))
NUMTOK = re.compile(r"^[-+]?[0-9]")

TOKENS = """26.660 2.911 0.034 467.24 32.78 53.321 0.00127 14.3 116.617
99.00 36.00 0.1339 0.3377 0.5502 21.00
0.00738 0.02029 2.750 0.05908 0.05811 0.983 0.00380 0.00499 0.06323 0.05786
393.11 164.53 1580.66 1649.91
0.7932 0.00618 +0.00358 +0.00119 3.000
0.02026 0.01392 0.01855 0.16382 0.16431 0.16406 0.00488 0.00476 0.687
0.01733
-0.01868 -0.02173 -0.01118 +0.00733 0.00132 66.7 46.2 557 154""".split()


def sites(tok):
    if not NUMTOK.match(tok):
        return len(re.findall(re.escape(tok), FLAT))
    before = r"(?<![0-9.])" if tok[0] in "+-" else r"(?<![-+0-9.])"
    return len(re.findall(before + re.escape(tok) + r"(?![0-9])", FLAT))


out, line = [], "    "
for t in TOKENS:
    n = sites(t)
    if n == 0:
        print(f"WARNING: {t!r} occurs 0 times", file=sys.stderr)
    frag = f'"{t}": {n}, '
    if len(line) + len(frag) > 76:
        out.append(line.rstrip())
        line = "    "
    line += frag
out.append(line.rstrip().rstrip(","))
print("SITE_COUNTS = {")
print("\n".join(out))
print("}")
