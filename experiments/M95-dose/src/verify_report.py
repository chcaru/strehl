"""Verify every number in docs/research/M95-dose.md against the JSON the
instruments wrote this session, and prove each check discriminates.

Same two-pass shape as the arm 7 verifier: PRESENT that the string is in the
report, then DISCRIMINATE that a one-digit perturbation of it is not. An anchor
that survives perturbation is matching something other than the value it claims
to check.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-dose.md"
OUT = Path(__file__).resolve().parents[1] / "out"


def norm(s):
    """Canonicalise typography so a check compares data, not glyphs."""
    s = (s.replace("\u2212", "-").replace("\u00d7", "x")
          .replace("\u00a0", " ").replace("\u2013", "-"))
    return re.sub(r"\s+", " ", s)


def main():
    y1 = json.loads((OUT / "y1_dose.json").read_text(encoding="utf-8"))
    y2 = json.loads((OUT / "y2_combined.json").read_text(encoding="utf-8"))
    raw = REPORT.read_text(encoding="utf-8")
    flat = norm(raw)

    checks = []

    def add(label, s):
        checks.append((label, norm(s)))

    # ------------------------------------------------- the sweep table (§1)
    BOLD = {"0.9315", "1.0"}
    for k in y1["sweep"]:
        key = f"{k}"
        i = y1["ISO"][key]["mean"]
        c = y1["COMP"][key]["mean"]
        if key in BOLD:
            add(f"sweep k={k}",
                f"| **{k:.4f}** | **{i:+.4f}** | **{c:+.4f}** |")
        else:
            add(f"sweep k={k}", f"| {k:.4f} | {i:+.4f} | {c:+.4f} |")

    # the two readings the headline actually rests on
    add("ISO at unity",
        f"At **k = 1.0000 it is {y1['ISO']['1.0']['mean']:+.4f} dex")
    add("ISO at 0.98",
        f"**k = 0.9800, a 2% scale, it is {y1['ISO']['0.98']['mean']:+.4f}**")
    pct = 100.0 * y1["ISO"]["0.98"]["mean"] / y1["ISO"]["0.9315"]["mean"]
    add("98 percent", f"that is **{pct:.1f}%** of what the")
    add("COMP at unity",
        f"it still costs {y1['COMP']['1.0']['mean']:+.4f} dex")
    add("COMP unity sem",
        f"`COMP(1.0) = {y1['COMP']['1.0']['mean']:+.4f} "
        f"\u00b1 {y1['COMP']['1.0']['sem']:.4f}`")

    b1 = y1["bars"]
    add("recovery", f"**{b1['recovery_dex']:+.4f} dex, {b1['recovery_pct']:.1f}%**")
    add("comp spread", f"measured spread is **{b1['comp_spread']:.4f}**")

    # -------------------------------------------------- the cross table (§2)
    for name in ("TODAY", "NOK", "KERN", "BOTH"):
        a = y2[name]
        add(f"cross {name}",
            f"| {name} | {a['k']:.4f} | {a['kernel']} | {a['cost_dex']:+.4f} |"
            f" {a['sem']:.4f} |")
    b2 = y2["bars"]
    add("rec coverage", f"| coverage scale removed | **{b2['recovery_coverage']:+.4f} dex** |")
    add("rec kernel", f"| kernel only | **{b2['recovery_kernel']:+.4f} dex** |")
    add("rec both", f"| both | **{b2['recovery_both']:+.4f} dex** |")
    add("rec extra",
        f"| what coverage adds on top of the kernel | **{b2['coverage_on_top']:+.4f} dex** |")
    add("kernel transfers", f"at\n**{b2['recovery_kernel']:+.4f}**")
    add("extra restated", f"extra is **{b2['coverage_on_top']:+.4f}**")

    # ---------------------------------------------------------- controls (§4)
    add("K12", f"| **{y1['K12_null']['mean']:+.6f} dex** |")
    add("K13", f"| **{y1['K13_response']['mean']:+.6f} dex** |")
    add("K14", f"| **{y1['K14_separation']['sep']:.6f} dex** |")
    add("K16", f"| **{y2['K16_null_lanczos']:+.6f} dex** |")
    add("K13 restated", f"and **{y1['K13_response']['mean']:+.6f}** when a known")
    add("K14 margin",
        f"cleared its 0.10 bar by **{y1['K14_separation']['sep'] - 0.10:.6f} dex**")

    # ------------------------------------------------------------- ADD (§3.2)
    add("ADD", f"**{y1['ADD']['mean']:+.4f} \u00b1 {y1['ADD']['sem']:.4f} dex**")

    # ----------------------------------------------------------- scope (§8)
    add("placed frames", f"only **{y1['n_placed']} placed frames**")

    # --------------------------------------------------------- run the passes
    present = [(lab, s, s in flat) for lab, s in checks]
    npres = sum(1 for _, _, ok in present if ok)
    print(f"PRESENT       {npres}/{len(present)}")
    for lab, s, ok in present:
        if not ok:
            print(f"  MISSING  {lab}: {s[:110]}")

    ndisc = 0
    for lab, s, ok in present:
        if not ok:
            continue
        mut = re.sub(r"(\d)(?=\d*\s*(?:dex|%|\||\*|\u00b1|$))",
                     lambda m: str((int(m.group(1)) + 5) % 10), s, count=1)
        if mut == s:
            mut = s[:-1] + ("9" if s[-1] != "9" else "1")
        if mut not in flat:
            ndisc += 1
        else:
            print(f"  NON-DISCRIMINATING  {lab}")
    print(f"DISCRIMINATE  {ndisc}/{npres}")

    facts = len(re.findall(r"^- \*\*P\d+\.\*\*", raw, re.M))
    labels = len(re.findall(r"`(?:MEASURED|ARGUED|ASSUMED)`", raw))
    print(f"facts {facts} / labels {labels}")

    ok = (npres == len(present) and ndisc == npres and facts == labels
          and facts > 0)
    print("VERIFY PASSED" if ok else "VERIFY FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
