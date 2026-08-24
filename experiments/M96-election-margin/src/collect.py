"""Collect M96's corpus runs into the tables the report quotes.

Every number in `docs/research/M96-election-margin.md` that is not a raw console
line comes from here, so the report cannot quote a figure no code printed.
"""

import pathlib
import re

OUT = pathlib.Path("experiments/M96-election-margin/out")

STACKS = ["109MSDCF", "119MSDCF", "112MSDCF", "foam", "coffee-bean",
          "wrapped-text-1", "bee-3-cpl"]

RE_FRAMES = re.compile(r"^frames\s+:\s+(\d+)")
RE_BAR = re.compile(r"^\s+(B\d) [^:]*:\s+([-\d.]+|NaN)\s*(?:->\s*(.*?))?\s*$")
RE_D = re.compile(
    r"^\s+d=(\d+)\s+n=\s*(\d+)\s+q med\s+([\d.]+)")
RE_S = re.compile(
    r"^\s+s_d med\s+([\d.]+)\s+frac\(m_d < 1 sigma_F\)\s+([\d.]+)%\s+"
    r"frac\(m_d < gate tol\)\s+([\d.]+)%")
RE_PAIR = re.compile(
    r"^\s+d=(\d+)\s+n=\s*(\d+)\s+real-wins\s+([\d.]+)%\s+ties\s+([\d.]+)%\s+"
    r"w/\(w\+l\)\s+([\d.]+)%\s+\| arbitrary: real\s+([\d.]+)%\s+permuted\s+([\d.]+)%")
RE_RHO = re.compile(
    r"^\s+c=([\d.]+)\s+tol\s+([\d.]+)\s+n_eff\s+([\d.]+)\s+rho med\s+(\d+)\s+"
    r"\(\s*([\d.]+) N\)\s+p90\s+(\d+)\s+p99\s+(\d+)\s+gap>0\s+([\d.]+)%")
RE_SPECK = re.compile(r"^\s+(real election|N1 i\.i\.d\..*?|N2 uniform random)\s*:\s+([\d.]+)%")


def parse(path: pathlib.Path):
    """Split a run log into the real arm, the permuted arm and the paired block."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    cut = next((i for i, l in enumerate(lines) if l.startswith("=== PAIRED PLACEBO")),
               len(lines))
    pcut = next((i for i, l in enumerate(lines) if l.startswith("=== PAIRED real")),
                len(lines))
    return lines[:cut], lines[cut:pcut], lines[pcut:]


def scan(lines, regex, key=1):
    out = {}
    for l in lines:
        m = regex.match(l)
        if m:
            out[m.group(key)] = m.groups()
    return out


def frames(lines):
    for l in lines:
        m = RE_FRAMES.match(l)
        if m:
            return int(m.group(1))
    return 0


rows = []
for s in STACKS:
    p = OUT / f"r4-{s}.txt"
    if not p.exists():
        print(f"MISSING {p}")
        continue
    real, perm, pair = parse(p)
    rows.append((s, frames(real), real, perm, pair))

print("=" * 108)
print("TABLE 1 -- pre-registered bars, real arm vs its own paired permutation placebo")
print("=" * 108)
print(f"{'stack':<15}{'N':>5}  {'B1 rho/N':>10}{'B2 gap%':>10}{'B3 q_8':>10}"
      f"{'B3 perm':>10}{'B3 ratio':>10}{'B5':>9}  verdict(B3)")
for s, n, real, perm, _ in rows:
    br = scan(real, RE_BAR)
    bp = scan(perm, RE_BAR)
    b3r, b3p = float(br["B3"][1]), float(bp["B3"][1])
    print(f"{s:<15}{n:>5}  {float(br['B1'][1]):>10.5f}{float(br['B2'][1]):>10.3f}"
          f"{b3r:>10.5f}{b3p:>10.5f}{b3r / max(b3p, 1e-12):>10.2f}"
          f"{float(br['B5'][1]):>9.5f}  {br['B3'][2]}")

print()
print("=" * 108)
print("TABLE 2 -- fraction of pixels whose margin is below 1 sigma_F, real vs permuted")
print("           The permuted column is NOT flat: excluding more frames at larger d")
print("           shrinks the rival set and grows m_d combinatorially, for ANY ordering.")
print("           That drift is exactly what the same-scale placebo is for (discipline 596):")
print("           what focus explains is the real column's EXCESS drop over the permuted one.")
print("=" * 108)
print(f"{'stack':<15}{'arm':<10}" + "".join(f"{'d=' + d:>9}" for d in
                                            ["0", "1", "2", "4", "8", "16", "32"]))
for s, n, real, perm, _ in rows:
    for name, lines in (("real", real), ("permuted", perm)):
        sd = [m.groups() for l in lines if (m := RE_S.match(l))]
        cells = "".join(f"{float(g[1]):>8.2f}%" for g in sd)
        print(f"{s:<15}{name:<10}{cells}")

print()
print("=" * 108)
print("TABLE 3 -- the paired test: same pixels, same multiset, frame ORDER destroyed")
print("           null = 50% wins and equal arbitrary fractions")
print("=" * 108)
print(f"{'stack':<15}{'d':>4}{'n':>10}{'w/(w+l)':>10}{'ties':>9}"
      f"{'arb real':>10}{'arb perm':>10}")
for s, n, _, _, pair in rows:
    for l in pair:
        m = RE_PAIR.match(l)
        if m and m.group(1) in ("1", "8", "32"):
            print(f"{s:<15}{m.group(1):>4}{int(m.group(2)):>10}{float(m.group(5)):>9.3f}%"
                  f"{float(m.group(4)):>8.2f}%{float(m.group(6)):>9.3f}%{float(m.group(7)):>9.3f}%")

print()
print("=" * 108)
print("TABLE 4 -- confusion radius at the shipped gate (c=4), real arm")
print("=" * 108)
print(f"{'stack':<15}{'N':>5}{'n_eff':>9}{'rho med':>9}{'rho/N':>8}"
      f"{'rho p90':>9}{'rho p99':>9}{'gap>0':>9}")
for s, n, real, _, _ in rows:
    r = scan(real, RE_RHO)
    if "4" in r:
        g = r["4"]
        print(f"{s:<15}{n:>5}{float(g[2]):>9.3f}{int(g[3]):>9}{float(g[4]):>8.3f}"
              f"{int(g[5]):>9}{int(g[6]):>9}{float(g[7]):>8.2f}%")

print()
print("=" * 108)
print("TABLE 5 -- elected-index speckle, real vs the two spatial nulls (descriptive)")
print("=" * 108)
print(f"{'stack':<15}{'real':>10}{'N1 iid':>10}{'N2 unif':>10}{'real/iid':>10}"
      f"{'perm arm':>10}")
for s, n, real, perm, _ in rows:
    a = scan(real, RE_SPECK)
    b = scan(perm, RE_SPECK)
    keys = list(a)
    rv = float(a[keys[0]][1])
    iid = float([v for k, v in a.items() if k.startswith("N1")][0][1])
    uni = float([v for k, v in a.items() if k.startswith("N2")][0][1])
    pv = float(list(b.values())[0][1]) if b else float("nan")
    print(f"{s:<15}{rv:>9.4f}%{iid:>9.4f}%{uni:>9.4f}%{rv / max(iid, 1e-12):>10.5f}"
          f"{pv:>9.4f}%")

print()
print("=" * 108)
print("TABLE 6 -- B4 detail-decile vectors of median q_8 (independent axis, low -> high)")
print("=" * 108)
for s, n, real, _, _ in rows:
    for l in real:
        if l.strip().startswith("A independent luma sd"):
            v = [float(x) for x in l.split()[4:]]
            print(f"{s:<15}N={n:<4} " + " ".join(f"{x:.4f}" for x in v)
                  + f"   max/min {max(v) / max(min(v), 1e-12):.2f}x  d9/d0 {v[9] / v[0]:.2f}x")
