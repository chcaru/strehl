"""Assemble the positive-control delta sweep into one table.

Discipline 594: the milestone's headline is that the election is decisive, so
the instrument must be shown reporting the opposite on a stack constructed to be
arbitrary. `delta` is the blur-per-frame of the synthetic ramp; sweeping it down
flattens the through-focus peak continuously.
"""

import pathlib
import re

OUT = pathlib.Path("experiments/M94-election-margin/out")

FILES = [
    ("1.0", "c2-plant-synth-d1.0.txt"),
    ("0.5", "c4-plant-synth-d0.5.txt"),
    ("0.25", "c4-plant-synth-d0.25.txt"),
    ("0.1", "c4-plant-synth-d0.1.txt"),
    ("0.05", "c4-plant-synth-d0.05.txt"),
    ("0.02", "c4-plant-synth-d0.02.txt"),
]

PATS = {
    "B1": re.compile(r"B1 median rho / N\s+:\s+([\d.]+)\s+->\s+(.*?)\s*$"),
    "B2": re.compile(r"B2 frac gap > 0 \(%\)\s+:\s+([\d.]+)\s+->\s+(.*?)\s*$"),
    "B3": re.compile(r"B3 median q_8\s+:\s+([\d.]+)\s+->\s+(.*?)\s*$"),
    "B5": re.compile(r"B5 speckle / iid\s+:\s+([\d.]+)\s+->\s+(.*?)\s*$"),
}
RE_SP = re.compile(r"real election\s*:\s+([\d.]+)%")
RE_Q8 = re.compile(r"^\s+d=8\s+n=\s*\d+\s+q med\s+([\d.]+)")

print("POSITIVE CONTROL -- synthetic band-limited texture, 60 frames, 512x512,")
print("blur radius grows `delta` px per frame off the pixel's own in-focus frame.")
print()
print(f"{'delta':<7}{'B1 rho/N':>10}{'B2 gap%':>10}{'B3 q_8':>10}{'B5':>10}"
      f"{'speckle%':>10}   verdicts B1/B2/B3/B5")
for d, fn in FILES:
    p = OUT / fn
    if not p.exists():
        print(f"MISSING {p}")
        continue
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    cut = next((i for i, l in enumerate(lines) if l.startswith("=== PAIRED")), len(lines))
    lines = lines[:cut]
    vals, verds = {}, {}
    for l in lines:
        for k, rx in PATS.items():
            m = rx.search(l)
            if m:
                vals[k], verds[k] = float(m.group(1)), m.group(2)
        m = RE_SP.search(l)
        if m and "speck" not in vals:
            vals["speck"] = float(m.group(1))
    v = [verds.get(k, "?")[0:4] for k in ("B1", "B2", "B3", "B5")]
    print(f"{d:<7}{vals.get('B1', float('nan')):>10.5f}{vals.get('B2', float('nan')):>10.3f}"
          f"{vals.get('B3', float('nan')):>10.5f}{vals.get('B5', float('nan')):>10.5f}"
          f"{vals.get('speck', float('nan')):>10.4f}   {' / '.join(v)}")

print()
print("DEC = DECISIVE, INTE = INTERMEDIATE, NEAR = NEARLY ARBITRARY")
