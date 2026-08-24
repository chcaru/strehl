"""Registered bandwidth diagnostic: does F depend on the high-pass radius?

PREREGISTRATION-rho.md registers the exit condition: if the clean-region F moves
by more than 20% between two high-pass radii, F is a property of the filter and
not of the sensor, and the milestone stops.
"""

import pathlib
import re

OUT = pathlib.Path("experiments/M90-prnu/out")
RES = ("Nearest", "Bilinear", "CatmullRom")
BAR = 0.20


def pooled(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    out = {}
    for block in re.split(r"^--- solver ", text, flags=re.M)[1:]:
        solver = block.split(":", 1)[0].strip()
        parts = block.split("POOLED OVER VALID BINS ONLY:")
        if len(parts) < 2:
            continue
        d = {}
        for line in parts[1].splitlines():
            f = line.split()
            if len(f) == 6 and f[0] in RES:
                d[f[0]] = {"W": float(f[1]), "F": float(f[2])}
        mask = re.search(r"bins kept = \[([^\]]*)\]", block)
        if d:
            out[solver] = (d, len(mask.group(1).split()) if mask else 0)
    return out


hdr = (
    f"{'case':<20}{'solver':>12}{'resampler':>12}"
    f"{'F(hp=30)':>10}{'F(hp=8)':>10}{'change':>10}{'bar 20%':>9}"
)
print("registered bandwidth diagnostic: hp = 30 px vs hp = 8 px")
print(f"  kappa(green luma): hp=30 -> 0.252937%, hp=8 -> 0.216469%")
print()
print(hdr)
print("-" * len(hdr))

worst = 0.0
worst_where = ""
fails = 0
rows = 0
for p8 in sorted(OUT.glob("hp8-*.txt")):
    case = p8.name[len("hp8-") : -len(".txt")]
    p30 = OUT / f"rho2-{case}.txt"
    if not p30.exists():
        print(f"  {case}: no hp=30 counterpart")
        continue
    a, b = pooled(p30), pooled(p8)
    for solver in sorted(set(a) & set(b)):
        da, na = a[solver]
        db, nb = b[solver]
        if na != nb:
            note = f" (bins {na} vs {nb})"
        else:
            note = ""
        for r in RES:
            if r not in da or r not in db:
                continue
            ch = db[r]["F"] / da[r]["F"] - 1.0
            rows += 1
            if abs(ch) > worst:
                worst, worst_where = abs(ch), f"{case}/{solver}/{r}"
            ok = abs(ch) <= BAR
            fails += 0 if ok else 1
            print(
                f"{case:<20}{solver:>12}{r:>12}"
                f"{da[r]['F']:>10.4f}{db[r]['F']:>10.4f}"
                f"{ch * 100:>+9.2f}%{'PASS' if ok else 'FAIL':>9}{note}"
            )

print()
print(f"  comparisons: {rows}, failing the 20% bar: {fails}")
print(f"  worst move: {worst * 100:.2f}% at {worst_where}")
print(
    "  VERDICT: "
    + (
        "F is NOT a property of the high-pass radius; the measurement stands."
        if fails == 0
        else "F depends on the filter; take the unidentifiability exit."
    )
)
