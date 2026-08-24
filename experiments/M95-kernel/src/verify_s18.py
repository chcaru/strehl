"""Verify M95-kernel.md section 18 against primary sources, not against my notes.

Deliberately does NOT read a JSON that k15 wrote. Every claim in section 18 is
re-derived here from the primary artifacts -- the quarantined sidecar itself and
k10's committed JSON -- so a transcription error in k15 cannot be laundered into
a green. Section slice is line-anchored (splitting on "## 18." also matches
"### 18.N"); short tokens discriminate on a context anchor.
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
QUAR = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars")
BEE = QUAR / "bee-3-cpl--warpmap.txt"

raw = REPORT.read_text(encoding="utf-8", errors="replace")
m = re.search(r"^## 18\. ", raw, re.M)
if not m:
    raise SystemExit("section 18 not found")
sec = raw[m.start() :]
if len(sec.splitlines()) < 50:
    raise SystemExit(f"section 18 implausibly short ({len(sec.splitlines())} lines)")
flat = re.sub(r"\s+", " ", sec)


def decoy(s):
    mm = re.search(r"\d(?=[^\d]*$)", s)
    if not mm:
        return s + "0"
    i = mm.start()
    return s[:i] + str((int(s[i]) + 1) % 10) + s[i + 1 :]


ok = True
print("=" * 78)
print("verify M95-kernel.md section 18  (re-derived from primary sources)")
print("=" * 78)

t = BEE.read_text(encoding="utf-8")
frames = int(re.search(r"^frames (\d+)", t, re.M).group(1))
end = int(re.search(r"^end (\d+)", t, re.M).group(1))
ref = int(re.search(r"^reference (\d+)", t, re.M).group(1))
dig = re.search(r"^stack-digest (\w+)", t, re.M).group(1)
rows = re.findall(r"^\d+ placed", t, re.M)
size = BEE.stat().st_size

per = []
for f in QUAR.glob("*.txt"):
    tt = f.read_text(encoding="utf-8", errors="replace")
    mm = re.search(r"^frames (\d+)", tt, re.M)
    if mm and int(mm.group(1)) > 20:
        per.append(f.stat().st_size / int(mm.group(1)))
med = sorted(per)[len(per) // 2]

k10 = json.loads((ROOT / "experiments" / "M95-kernel" / "out"
                  / "k10_resampler_field.json").read_text(encoding="utf-8"))

checks = [
    ("bee sidecar frames == 8", frames == 8, "`frames 8`"),
    ("end field == 8", end == 8, "`end 8`"),
    ("placement rows == 8", len(rows) == 8, "8 placement"),
    ("reference == 4", ref == 4, "`reference 4`"),
    ("reference == merge_reference(8)", ref == 8 // 2, "merge_reference(8)"),
    ("digest quoted", True, dig),
    ("size == 1560 B", size == 1560, "1560 B"),
    ("size != 40-frame size", size < 6000, "6000 B"),
    ("median B/frame", abs(med - 137.5) < 0.05, "137.5 B/frame"),
    ("k10 legacy_exists is false", k10["closing"]["legacy_exists"] is False,
     '"legacy_exists": false'),
    ("53.1412% re-derived", abs(k10["H4"]["differing_frac"] * 100 - 53.1412) < 1e-4,
     "53.1412%"),
    ("bee-2 size quoted", (QUAR / "bee-2-cpl--warpmap.txt").stat().st_size == 40807,
     "40807 B"),
    ("lavendar size quoted", (QUAR / "lavendar-cpl--warpmap.txt").stat().st_size == 40812,
     "40812 B"),
]
for label, derived, token in checks:
    present = token in flat
    dec = decoy(token)
    disc = dec not in flat if dec != token else True
    good = derived and present and disc
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<34} derived={derived} present={present} disc={disc}")

structural = [
    ("own claim tested first", "the one most likely to be wrong"),
    ("probe verified sound", "The probe was not blind"),
    ("second instrument", "two instruments of different kinds"),
    ("copied not written", "copied in with timestamps preserved"),
    ("frame count corrected", "holds 8 frames, not 40"),
    ("not the align story", "not** by `strehl align`"),
    ("guard fires", "refused, rc=1"),
    ("real hazard restated", "validated by nothing"),
    ("override used", "sidecar-override"),
    ("arm 9 never rendered", "never rendered at all"),
    ("watershed cleared", "No number here needs retaking"),
    ("gate recorded explicitly", "--gate 0"),
]
print("-" * 78)
flat_ci = flat.lower()
for label, token in structural:
    good = token.lower() in flat_ci
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<34} {token!r}")

print("=" * 78)
print(f"verdict: {'GREEN' if ok else 'RED'}")
print("=" * 78)
sys.exit(0 if ok else 1)
