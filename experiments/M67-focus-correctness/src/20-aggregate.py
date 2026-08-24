"""M67 -- aggregate the instrument's SUMMARY lines and score the pre-registration.

Reads every ``out/*.log`` written by
``cargo run --release -p strehl-cli --example m67-focus-correctness``, groups
runs into *cells* (the plant name with its ``-seedN`` suffix removed), and
computes across-seed means and standard deviations.

The controls C1--C3 and the decisions D1--D3, D5 are then scored **in the words
the pre-registration used**, including their registered consequences.  This
script decides nothing; it only applies bars that were fixed before any number
existed.

Across-seed SD is the *population* SD over the seeds actually present.  With
three seeds that is a coarse estimate and the report says so; the alternative --
inventing a variance model -- would be worse.  Where the SD rounds to zero the
"10x SD" bar is satisfied trivially and the printed verdict says which bar was
actually binding, so a reader is never shown a pass that rests on a degenerate
denominator.

Usage:
    python -u src\\20-aggregate.py [--out out] [--gate 4]
"""
from __future__ import annotations

import glob
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_RE = re.compile(r"-seed\d+$")


def _read_text(path: str) -> str:
    """Read a log whatever encoding PowerShell's Tee-Object chose.

    Windows PowerShell 5.1 writes UTF-16LE with a BOM; pwsh and Python write
    UTF-8.  Sniff the BOM rather than guessing.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def parse_summaries(outdir: str) -> list[dict]:
    runs = []
    for path in sorted(glob.glob(os.path.join(outdir, "*.log"))):
        for line in _read_text(path).splitlines():
            if not line.startswith("SUMMARY "):
                continue
            rec: dict = {"_log": os.path.basename(path)}
            for tok in line.split()[1:]:
                if "=" not in tok:
                    continue
                k, v = tok.split("=", 1)
                # The line carries `plant=<run name>` first and then the meta
                # block's own `plant=<scene kind>`.  Keep the run name.
                if k == "plant" and "_name" not in rec:
                    rec["_name"] = v
                    continue
                try:
                    rec[k] = float(v)
                except ValueError:
                    rec[k] = v
            runs.append(rec)
    return runs


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def cell_of(name: str) -> str:
    return SEED_RE.sub("", name)


def fmt(x: float, nd: int = 5) -> str:
    if x != x:
        return "   n/a"
    return f"{x:.{nd}f}"


def bar10(diff: float, s: float) -> tuple[bool, str]:
    """Is |diff| at least 10x the across-seed SD?  Say which bar bound."""
    if s != s:
        return (True, "single seed: no SD; 10xSD bar not evaluable")
    if s == 0.0:
        return (True, "SD = 0 exactly; 10xSD bar degenerate, satisfied trivially")
    ok = abs(diff) >= 10.0 * s
    return (ok, f"|diff| {abs(diff):.5f} vs 10xSD {10.0 * s:.5f}")


def main() -> int:
    outdir = os.path.join(HERE, "out")
    gate = "4"
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--out":
            outdir = argv[i + 1]
        elif a == "--gate":
            gate = argv[i + 1]

    runs = [r for r in parse_summaries(outdir) if r.get("truth_mirror") != "true"]
    mirrored = [r for r in parse_summaries(outdir) if r.get("truth_mirror") == "true"]
    if not runs:
        print(f"no SUMMARY lines under {outdir}")
        return 1

    g = gate.replace(".", "p")
    kH_E, kH_Su = f"H_E_{g}", f"H_Su_{g}"
    kH_Sb, kD_E = f"H_Sb_{g}", f"D_E_{g}"
    kD_Su, kD_Sb = f"D_Su_{g}", f"D_Sb_{g}"
    kM_E, kM_Sb = f"M_E_{g}", f"M_Sb_{g}"
    kn, krho, kdev = f"n_{g}", f"rho_{g}", f"devmax_{g}"

    cells: dict[str, list[dict]] = {}
    for r in runs:
        cells.setdefault(cell_of(str(r["_name"])), []).append(r)

    print(f"M67 -- aggregate over {len(runs)} runs, {len(cells)} cells, gate {gate}")
    print(f"(and {len(mirrored)} mirrored-truth negative-control runs)")
    print()

    hdr = (f"{'cell':46s} {'n':>2s} {'K':>3s} {'SNR':>6s} {'n_eff':>6s} "
           f"{'H(E)':>7s} {'H(A)':>7s} {'H(Su)':>7s} {'H(Sb)':>7s} "
           f"{'D(E)':>6s} {'D(A)':>6s} {'D(Sb)':>6s} {'rho':>8s} {'dev':>6s} "
           f"{'winH':>7s}")
    print(hdr)
    print("-" * len(hdr))
    order = sorted(cells, key=lambda c: (0 if "s1024" in c else 1, c))
    for c in order:
        rs = cells[c]
        print(f"{c:46s} {len(rs):2d} {int(rs[0]['frames']):3d} "
              f"{mean([r['infocus_band_snr'] for r in rs]):6.3f} "
              f"{mean([r[kn] for r in rs]):6.3f} "
              f"{mean([r[kH_E] for r in rs]):7.5f} "
              f"{mean([r['H_A'] for r in rs]):7.5f} "
              f"{mean([r[kH_Su] for r in rs]):7.5f} "
              f"{mean([r[kH_Sb] for r in rs]):7.5f} "
              f"{mean([r[kD_E] for r in rs]):6.3f} "
              f"{mean([r['D_A'] for r in rs]):6.3f} "
              f"{mean([r[kD_Sb] for r in rs]):6.3f} "
              f"{mean([r[krho] for r in rs]):8.5f} "
              f"{mean([r[kdev] for r in rs]):6.3f} "
              f"{mean([r['winH_E'] for r in rs]):7.5f}")
    print()

    # ---- the headline cell -------------------------------------------------
    head = [c for c in cells if "s1024" in c]
    if len(head) != 1:
        print(f"expected exactly one s1024 headline cell, found {head}")
        return 1
    hc = head[0]
    rs = cells[hc]
    K = int(rs[0]["frames"])
    print(f"headline cell : {hc}   ({len(rs)} seeds, K={K})")
    print()

    def ms(key: str) -> tuple[float, float]:
        xs = [r[key] for r in rs]
        return mean(xs), sd(xs)

    hE, sE = ms(kH_E)
    hSu, _ = ms(kH_Su)
    hSb, _ = ms(kH_Sb)
    hA, sA = ms("H_A")
    dE, _ = ms(kD_E)
    dSb, _ = ms(kD_Sb)
    dSu, _ = ms(kD_Su)
    dA, sDA = ms("D_A")
    mE, sME = ms(kM_E)
    mA, sMA = ms("M_A")
    rho, _ = ms(krho)
    dev, _ = ms(kdev)

    print(f"H(E({gate}))  = {fmt(hE)}  sd {fmt(sE)}")
    print(f"H(A)      = {fmt(hA)}  sd {fmt(sA)}")
    print(f"H(Su({gate})) = {fmt(hSu)}")
    print(f"H(Sb({gate})) = {fmt(hSb)}")
    print(f"D(E)      = {fmt(dE, 4)}   D(A) = {fmt(dA, 4)}   "
          f"D(Su) = {fmt(dSu, 4)}   D(Sb) = {fmt(dSb, 4)}")
    print(f"M(E)      = {fmt(mE, 4)}   M(A) = {fmt(mA, 4)}")
    print(f"rho_col   = {fmt(rho)}   devmax = {fmt(dev, 4)} frames")
    print()

    verdicts: list[tuple[str, str, str]] = []

    # C1
    d = hE - hSu
    ok10, why = bar10(d, sE)
    c1 = (abs(d) >= 0.10) and ok10
    verdicts.append(("C1", "MET" if c1 else "NOT MET",
                     f"|H(E)-H(Su)| = {abs(d):.5f} >= 0.10 -> "
                     f"{abs(d) >= 0.10}; {why}"))

    # C2: separation on at least one of H, D, M vs 10x that statistic's SD
    c2parts = []
    for label, diff, s in (("H", hE - hA, sE if sE == sE else sA),
                           ("D", dE - dA, sDA),
                           ("M", mE - mA, sME if sME == sME else sMA)):
        ok, w = bar10(diff, s)
        c2parts.append(f"{label}: diff {diff:+.5f} {'OK' if ok else 'no'} ({w})")
    c2 = any(p.split()[2] == "OK" or " OK " in p for p in c2parts)
    verdicts.append(("C2", "MET" if c2 else "NOT MET", "; ".join(c2parts)))

    # C3
    d3 = hA - 1.0 / K
    ok10, why = bar10(d3, sA)
    c3 = ok10 and d3 > 0
    verdicts.append(("C3", "MET" if c3 else "NOT MET",
                     f"H(A) - 1/K = {hA:.5f} - {1.0 / K:.5f} = {d3:+.5f}; {why}"))

    # D1
    d1 = hE >= 0.50
    verdicts.append(("D1", "H >= 0.50" if d1 else "H < 0.50",
                     f"H(E({gate})) = {hE:.5f} on the headline cell"))

    # D2
    d2a, d2b = hE - hSb, (dSb / dE if dE else float("nan"))
    d2 = (d2a >= 0.10) and (d2b >= 1.10)
    verdicts.append(("D2", "MET" if d2 else "NOT MET",
                     f"H(E)-H(Sb) = {d2a:+.5f} >= 0.10 -> {d2a >= 0.10}; "
                     f"D(Sb)/D(E) = {d2b:.4f} >= 1.10 -> {d2b >= 1.10}"))

    # D3
    d3m = (abs(rho) >= 0.95) and (dev <= 1.0)
    verdicts.append(("D3", "MET" if d3m else "NOT MET",
                     f"|rho_col| = {abs(rho):.5f} >= 0.95 -> {abs(rho) >= 0.95}; "
                     f"devmax = {dev:.4f} <= 1.0 -> {dev <= 1.0}"))

    print("--- pre-registered verdicts, headline cell ---")
    for i, (k, v, w) in enumerate(verdicts):
        print(f"{k:3s} {v:12s} {w}")
    print()

    # D4 (no direction registered), gated by C2
    print("--- D4 selector vs estimator (no direction was registered) ---")
    print(f"H(E) - H(A) = {hE - hA:+.5f}")
    print(f"M(E) - M(A) = {mE - mA:+.5f} frames")
    print(f"D(E) - D(A) = {dE - dA:+.5f} frames   (D(A)/D(E) = {dA / dE:.4f})")
    print()

    # D5: the gate ladder on the headline cell
    print("--- D5 gate ladder, headline cell, across-seed means ---")
    print(f"{'gate':>5s} {'n_eff':>7s} {'H(E)':>8s} {'H(Su)':>8s} {'H(Sb)':>8s} "
          f"{'D(E)':>7s} {'D(Sb)':>7s} {'M(E)':>7s} {'rho':>8s} {'dev':>7s}")
    for gg, tag in ((0.5, "0p5"), (1.0, "1"), (2.0, "2"), (4.0, "4")):
        try:
            print(f"{gg:5.1f} "
                  f"{mean([r[f'n_{tag}'] for r in rs]):7.3f} "
                  f"{mean([r[f'H_E_{tag}'] for r in rs]):8.5f} "
                  f"{mean([r[f'H_Su_{tag}'] for r in rs]):8.5f} "
                  f"{mean([r[f'H_Sb_{tag}'] for r in rs]):8.5f} "
                  f"{mean([r[f'D_E_{tag}'] for r in rs]):7.4f} "
                  f"{mean([r[f'D_Sb_{tag}'] for r in rs]):7.4f} "
                  f"{mean([r[f'M_E_{tag}'] for r in rs]):7.4f} "
                  f"{mean([r[f'rho_{tag}'] for r in rs]):8.5f} "
                  f"{mean([r[f'devmax_{tag}'] for r in rs]):7.4f}")
        except KeyError:
            pass
    print()

    # ---- per-cell C1/C3 so no sweep cell is quoted without its own controls -
    print("--- per-cell controls (C1 absolute bar, C3 solvability) ---")
    print(f"{'cell':46s} {'n_eff/K':>7s} {'M64':>4s} {'H(E)-H(Su)':>11s} {'C1abs':>6s} "
          f"{'H(A)-1/K':>9s} {'C3':>4s} {'devmax':>7s} {'D3':>4s}")
    for c in order:
        rr = cells[c]
        kk = int(rr[0]["frames"])
        d1c = mean([r[kH_E] for r in rr]) - mean([r[kH_Su] for r in rr])
        d3c = mean([r["H_A"] for r in rr]) - 1.0 / kk
        frac = mean([r[kn] for r in rr]) / kk
        dvm = mean([r[kdev] for r in rr])
        rhoc = mean([r[krho] for r in rr])
        d3ok = (abs(rhoc) >= 0.95) and (dvm <= 1.0)
        # M64's shipped degeneracy guard: n_eff/N >= 0.95 means the merge is
        # averaging essentially every frame, which is already a FAIL there.
        print(f"{c:46s} {frac:7.4f} {'FAIL' if frac >= 0.95 else 'ok':>4s} "
              f"{d1c:+11.5f} {'yes' if abs(d1c) >= 0.10 else 'NO':>6s} "
              f"{d3c:+9.5f} {'yes' if d3c > 0 else 'NO':>4s} "
              f"{dvm:7.3f} {'yes' if d3ok else 'NO':>4s}")
    print()

    if mirrored:
        print("--- instrument negative control: truth mirrored in x ---")
        for r in mirrored:
            print(f"{r['_name']:46s} H(E)={r[kH_E]:.5f} H(A)={r['H_A']:.5f} "
                  f"H(Su)={r[kH_Su]:.5f} H(E)-H(Su)={r[kH_E] - r[kH_Su]:+.5f} "
                  f"winH={r['winH_E']:.5f}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
