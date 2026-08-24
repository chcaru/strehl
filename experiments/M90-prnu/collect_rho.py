"""Collect the pooled clean-bin results from every rho-*.txt run into one table.

Deliberately a separate parser from the Rust that produced the numbers: a
transcription error in the report is then a disagreement between two programs
rather than a silent copy.
"""

import pathlib
import re
import sys

OUT = pathlib.Path("experiments/M90-prnu/out")
RES = ("Nearest", "Bilinear", "CatmullRom")


def parse(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    n_frames = None
    m = re.search(r"=== rho: (\S+) \| (\d+) frames", text)
    if not m:
        return None
    case, n_frames = m.group(1), int(m.group(2))
    out = []
    for block in re.split(r"^--- solver ", text, flags=re.M)[1:]:
        solver = block.split(":", 1)[0].strip()
        step = re.search(
            r"centre ([\d.]+) px, corner ([\d.]+) px", block
        )
        mask = re.search(r"bins kept = \[([^\]]*)\]", block)
        pooled = {}
        pb = block.split("POOLED OVER VALID BINS ONLY:")
        if len(pb) < 2:
            continue
        for line in pb[1].splitlines():
            f = line.split()
            if len(f) == 6 and f[0] in RES:
                pooled[f[0]] = tuple(float(v) for v in f[1:5]) + (int(f[5]),)
        if not pooled:
            continue
        out.append(
            {
                "case": case,
                "n": n_frames,
                "solver": solver,
                "step_c": float(step.group(1)) if step else float("nan"),
                "step_e": float(step.group(2)) if step else float("nan"),
                "bins": len(mask.group(1).split()) if mask else 0,
                "pooled": pooled,
            }
        )
    return out


rows = []
for p in sorted(OUT.glob("rho2-*.txt")):
    if "controls" in p.name or "prnu" in p.name:
        continue
    got = parse(p)
    if got:
        rows.extend(got)

if not rows:
    sys.exit("no parseable runs")

hdr = (
    f"{'case':<20}{'n':>5}{'solver':>12}{'bins':>5}"
    f"{'stepC':>8}{'stepE':>8}{'W_near':>8}"
    f"{'F_CR':>9}{'n_prnu_CR':>10}{'rho_CR':>9}{'over_x':>8}"
)
print(hdr)
print("-" * len(hdr))
for r in sorted(rows, key=lambda r: (r["n"], r["case"], r["solver"])):
    w_near = r["pooled"]["Nearest"][0]
    f_cr, n_cr, rho_cr = (
        r["pooled"]["CatmullRom"][1],
        r["pooled"]["CatmullRom"][2],
        r["pooled"]["CatmullRom"][3],
    )
    print(
        f"{r['case']:<20}{r['n']:>5}{r['solver']:>12}{r['bins']:>5}"
        f"{r['step_c']:>8.3f}{r['step_e']:>8.3f}{w_near:>8.4f}"
        f"{f_cr:>9.4f}{n_cr:>10.2f}{rho_cr:>9.4f}{1.0 / f_cr**0.5:>8.2f}"
    )

print()
print("per-resampler W, pooled over valid bins, every run:")
print(f"{'resampler':>12}{'mean W':>10}{'sd':>10}{'min':>10}{'max':>10}{'runs':>7}")
for name in RES:
    vals = [r["pooled"][name][0] for r in rows if name in r["pooled"]]
    mean = sum(vals) / len(vals)
    sd = (sum((v - mean) ** 2 for v in vals) / max(len(vals) - 1, 1)) ** 0.5
    print(
        f"{name:>12}{mean:>10.4f}{sd:>10.4f}{min(vals):>10.4f}"
        f"{max(vals):>10.4f}{len(vals):>7}"
    )

print()
print("solver sensitivity: max |F(S4-poly4)/F(S3-ba-unit) - 1| per case")
by_case = {}
for r in rows:
    by_case.setdefault(r["case"], {})[r["solver"]] = r["pooled"]
worst = 0.0
for case, s in sorted(by_case.items()):
    if len(s) < 2:
        print(f"  {case:<20} only one solver solved")
        continue
    a, b = s.get("S3-ba-unit"), s.get("S4-poly4")
    d = max(abs(b[k][1] / a[k][1] - 1.0) for k in RES if k in a and k in b)
    worst = max(worst, d)
    print(f"  {case:<20} {d * 100:>7.2f}%")
print(f"  worst across all cases: {worst * 100:.2f}%")
