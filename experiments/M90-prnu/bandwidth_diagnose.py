"""Diagnose the failed bandwidth bar.

The pooled comparison confounds two things: a genuine spectral dependence of F,
and the fact that the two radii admit different bin sets, with the extra bin
being the low-F outer one. This compares bin by bin on the bins both runs
admitted, and separately checks whether W -- a pure property of the resampling
kernel -- is stable across the two radii.
"""

import pathlib
import re

OUT = pathlib.Path("experiments/M90-prnu/out")
RES = ("Nearest", "Bilinear", "CatmullRom")


def blocks(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    for block in re.split(r"^--- solver ", text, flags=re.M)[1:]:
        solver = block.split(":", 1)[0].strip()
        tables = {}
        for label, key in (
            (r"radially resolved, F \(", "F"),
            (r"radially resolved, W \(", "W"),
        ):
            m = re.search(label + r"[^\n]*\n((?:\s+\w+(?:\s+[-\d.]+)+\n)+)", block)
            if not m:
                continue
            d = {}
            for line in m.group(1).splitlines():
                f = line.split()
                if f and f[0] in RES:
                    d[f[0]] = [None if v == "-" else float(v) for v in f[1:]]
            tables[key] = d
        mask = re.search(r"bins kept = \[([^\]]*)\]", block)
        kept = set()
        if mask:
            for tok in mask.group(1).split():
                kept.add(int(round(float(tok) * 8 - 0.5)))
        if tables:
            yield solver, tables, kept


print("bandwidth failure, diagnosed bin by bin (only bins BOTH radii admitted)")
print()
hdr = f"{'case':<18}{'solver':>12}{'res':>11}{'bins':>16}{'F(30)':>9}{'F(8)':>9}{'change':>9}"
print(hdr)
print("-" * len(hdr))

all_ch = []
w_pairs = {r: [] for r in RES}
for p8 in sorted(OUT.glob("hp8-*.txt")):
    case = p8.name[len("hp8-") : -len(".txt")]
    p30 = OUT / f"rho2-{case}.txt"
    if not p30.exists():
        continue
    a = {s: (t, k) for s, t, k in blocks(p30)}
    b = {s: (t, k) for s, t, k in blocks(p8)}
    for solver in sorted(set(a) & set(b)):
        (ta, ka), (tb, kb) = a[solver], b[solver]
        common = sorted(ka & kb)
        for r in RES:
            fa = [ta["F"][r][i] for i in common]
            fb = [tb["F"][r][i] for i in common]
            # Pool by inverse-F weighting is wrong; compare the mean of the
            # per-bin ratios, which is what "does the bin move" asks.
            ch = sum(y / x - 1.0 for x, y in zip(fa, fb)) / len(common)
            all_ch.append(abs(ch))
            wa = [ta["W"][r][i] for i in common]
            wb = [tb["W"][r][i] for i in common]
            w_pairs[r].append(
                (sum(wa) / len(wa), sum(wb) / len(wb))
            )
            print(
                f"{case:<18}{solver:>12}{r:>11}"
                f"{str(common):>16}{sum(fa) / len(fa):>9.4f}"
                f"{sum(fb) / len(fb):>9.4f}{ch * 100:>+8.2f}%"
            )

print()
print(f"  common-bin comparisons: {len(all_ch)}")
print(f"  mean |change|: {sum(all_ch) / len(all_ch) * 100:.2f}%")
print(f"  worst |change|: {max(all_ch) * 100:.2f}%")
print(f"  over the registered 20% bar: {sum(1 for c in all_ch if c > 0.20)}/{len(all_ch)}")

print()
print("W across the two radii (W is a kernel property; it must NOT move):")
print(f"{'resampler':>12}{'W(hp=30)':>11}{'W(hp=8)':>11}{'change':>10}")
for r in RES:
    xs = [x for x, _ in w_pairs[r]]
    ys = [y for _, y in w_pairs[r]]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    print(f"{r:>12}{mx:>11.4f}{my:>11.4f}{(my / mx - 1) * 100:>+9.2f}%")
