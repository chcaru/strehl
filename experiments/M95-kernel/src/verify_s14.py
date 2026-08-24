"""Verify every number in M95-kernel.md section 14 against the JSON the runs wrote.

Same two-pass discipline as verify_report.py: a claim must be PRESENT in the
report, and the report must DISCRIMINATE -- a decoy formed by perturbing the
last digit must NOT appear. Text is whitespace-collapsed because claims wrap
across line breaks and a raw grep gives false negatives on reflowed prose.
"""

import json
import re
import sys
from pathlib import Path

# Discipline 702: this gate reports through stdout and its exit code is read as
# a claim. Python picks the ANSI codepage for piped stdout, which is every agent
# tool call and every CI log, and cp1252 cannot encode the minus signs and arrows
# this corpus uses. Without this, print() raises mid-run and the process exits 1:
# indistinguishable from a real failure. Measured in k18_gate702.py.
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
OUT = ROOT / "experiments" / "M95-kernel" / "out"

k9 = json.loads((OUT / "k9_sidecar.json").read_text(encoding="utf-8"))
k10 = json.loads((OUT / "k10_resampler_field.json").read_text(encoding="utf-8"))

raw = REPORT.read_text(encoding="utf-8", errors="replace")
# NOT `split("## 14.")`: that substring also occurs inside every `### 14.N`
# subheading, so [1] silently truncates the section to its first paragraph.
# Caught by this verifier reporting BAD on claims that were plainly present.
m = re.search(r"^## 14\. ", raw, re.M)
if not m:
    raise SystemExit("section 14 not found")
sec = raw[m.start() :]
if len(sec.splitlines()) < 50:
    raise SystemExit(f"section 14 implausibly short ({len(sec.splitlines())} lines)")
flat = re.sub(r"\s+", " ", sec)


def decoy(s: str) -> str:
    m = re.search(r"\d(?=[^\d]*$)", s)
    if not m:
        return s + "0"
    i = m.start()
    return s[:i] + str((int(s[i]) + 1) % 10) + s[i + 1 :]


claims = []


def claim(label, text, ctx=None):
    claims.append((label, text, ctx))


d = k10["H4"]
claim("differing bytes", f"{d['differing_bytes']:,}".replace(",", " "), "26 278 128")
claim("compared bytes", f"{d['compared_bytes']:,}".replace(",", " "), "49 449 626")
claim("differing pct", f"{d['differing_frac'] * 100:.4f}%", "53.1412")
claim("sha catmull-rom", d["sha_catmull_rom"][:8], "f049786a")
claim("sha lanczos3", d["sha_lanczos3"][:8], "9f309ca9")
claim("bytes", f"{k10['H4c']['bytes']:,}".replace(",", " "), "49 449 626")

claim("legacy count", str(k9["H0"]["legacy_count_under_library"]), "0 files")
for name, e in k9["H0"]["cache_entries_before"].items():
    claim(f"cache bytes {name[:12]}", f"{e['bytes']:,}".replace(",", " "), None)

ok = True
print("=" * 74)
print("verify M95-kernel.md section 14  (PRESENT / DISCRIMINATE)")
print("=" * 74)
for label, text, ctx in claims:
    present = text in flat
    # Discriminate on the context anchor when one is given: a bare short token
    # like "0" has a last-digit decoy ("1") that occurs elsewhere by pure
    # coincidence, which is a false RED rather than a real defect.
    target = ctx if ctx else text
    dec = decoy(target)
    discriminates = dec not in flat if dec != target else True
    if ctx and ctx not in flat:
        present = False
    good = present and discriminates
    ok &= good
    print(
        f"  {'OK ' if good else 'BAD'}  {label:<28} {text!r:>18}"
        f"  present={present} discriminates={discriminates}"
    )

structural = [
    ("premise refuted stated", "does not exist"),
    ("commit named", "8118dd7"),
    ("STREHL_CACHE_DIR named", "STREHL_CACHE_DIR"),
    ("power control reported", "refused, rc=1"),
    ("determinism control reported", "PASS"),
    ("hazard is resampler", "resampler"),
    ("owns the consequence", "unguarded field easier to vary"),
    ("did not fix", "reporting rather than fixing"),
    ("merge_cmd untouched", "contended"),
    ("not the writer", "not the agent writing that file"),
    ("residual disclosed", "honest residual"),
]
print("-" * 74)
for label, text in structural:
    good = text in flat
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<28} {text!r}")

print("=" * 74)
print(f"verdict: {'GREEN -- every number transcribed from the JSON' if ok else 'RED'}")
print("=" * 74)
sys.exit(0 if ok else 1)
