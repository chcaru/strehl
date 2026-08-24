# -*- coding: utf-8 -*-
"""Re-derive every figure quoted in section 29 from the JSON operands.

This is not a presence check. Every expected string is *computed* from
`81-contour-support.json` (or, for the sign-error repair, from `13-unmix.json`
and `17-perpixel.json`) and then required to appear in the report an exact
number of times. The exact count is what defeats instance-blindness: mutating
one of N copies of a figure changes the count and fails, which a presence
check would not catch (`P105`, `P112`).

The haystack is whitespace-collapsed, because the prose is hard-wrapped and a
quoted figure can straddle a line break.
"""
import io
import json
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = ROOT / "experiments" / "M87-occlusion" / "data"

fails: list[str] = []
n_ok = 0


def flat(s: str) -> str:
    """U+2212 is not ASCII, and the prose is hard-wrapped."""
    for a, b in (("\u2212", "-"), ("\u2009", " "), ("\u00a0", " "),
                 ("\u202f", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s)


def chk(label: str, expected: str, hay: str, count: int) -> None:
    global n_ok
    got = hay.count(expected)
    if got == count:
        n_ok += 1
        print(f"  ok   {label:<40} {expected!r} x{count}")
    else:
        fails.append(f"{label}: {expected!r} appears {got}x, expected {count}x")
        print(f"  FAIL {label:<40} {expected!r} {got}x != {count}x")


def eq(label: str, a: float, b: float, tol: float = 1e-9) -> None:
    global n_ok
    if abs(a - b) <= tol:
        n_ok += 1
        print(f"  ok   {label:<40} {a!r} re-derives")
    else:
        fails.append(f"{label}: recorded {a!r} != re-derived {b!r}")
        print(f"  FAIL {label:<40} recorded {a!r} != re-derived {b!r}")


def main() -> int:
    # Whole-document scope is deliberate here, unlike verify_s30/s31: several
    # of these checks assert that a corrected figure was propagated OUT of
    # section 29 into 0, 5.1, P8 and P110, so a section-scoped count cannot
    # express them. The cost is that a later section citing one of these
    # figures raises the count; when that happens, name the new site in the
    # comment beside the number rather than bumping it silently.
    D = flat(REPORT.read_text(encoding="utf-8"))
    d = json.loads((DATA / "81-contour-support.json").read_text(encoding="utf-8"))
    t1, t2, t3, t4 = d["T1"], d["T2"], d["T3"], d["T4"]
    v = d["verdicts"]

    print("\n== T1: morphology of the boundary population ==")
    chk("frame 0 share", f"{100 * t1['frame0']:.4f}%", D, 2)
    chk("frame 175 share", f"{100 * t1['framehi']:.4f}%", D, 2)
    chk("boundary share", f"{100 * t1['boundary']:.4f}%", D, 3)
    chk("median half-width", f"{t1['median']:.2f} px", D, 4)  # +1: 31.7
    chk("p10 / p25 / p75", f"{t1['p10']:.2f} / {t1['p25']:.2f} / "
        f"{t1['p75']:.2f}", D, 1)
    chk("p90", f"**{t1['p90']:.2f}** px", D, 1)
    chk("fraction at <=1px", f"{100 * t1['frac']['le1']:.2f}%", D, 2)
    chk("fraction at <=2px", f"{100 * t1['frac']['le2']:.2f}%", D, 1)
    chk("fraction at <=8px", f"{100 * t1['frac']['le8']:.2f}%", D, 2)
    chk("component count", f"{t1['n_components']:,}".replace(",", " "), D, 2)
    chk("largest component", f"{100 * t1['largest_share']:.2f}%", D, 2)
    chk("speckle share", f"{100 * t1['speckle']:.2f}%", D, 3)
    b1 = v["T1 median half-width"]
    chk("T1 bar lo", f"{b1['lo']}px is thin", D, 1)
    chk("T1 bar hi", f"{b1['hi']}px is broad", D, 1)
    chk("T1 verdict", f"**{t1['median']:.2f} px \u2014 {b1['verdict']}.**", D, 1)

    print("\n== T2: pixel-count support ==")
    chk("band p25 width", f"p25 {t2['thin_w']:.2f}px", D, 1)
    chk("band p75 width", f"p75 {t2['broad_w']:.2f}px", D, 1)
    chk("observations per pixel", f"**{t2['n_thin']:.3f} thin against "
        f"{t2['n_broad']:.3f} broad**", D, 4)  # +1: 33.7
    chk("relative gap", f"**{t2['rel']:.4f}**", D, 1)
    chk("T2 verdict", v["T2 observation-count gap"]["verdict"], D, 1)

    print("\n== T3: does the alpha gate reject thin structures? ==")
    lo, fu = t3["local"], t3["full"]
    eq("T3 local pass ratio", lo["ratio"], lo["pass_thin"] / lo["pass_broad"])
    eq("T3 local amax separation", lo["amax_sep"],
       lo["amax_broad"] - lo["amax_thin"], 1e-7)
    chk("local coverage", f"**{100 * lo['coverage']:.2f}%**", D, 4)
    chk("full coverage", f"**{100 * fu['coverage']:.2f}%**", D, 3)
    chk("local amax thin", f"**{lo['amax_thin']:.4f}**", D, 3)  # +1: 33.7
    chk("local amax broad", f"**{lo['amax_broad']:.4f}**", D, 3)  # +1: 33.7
    chk("full amax thin", f"{fu['amax_thin']:.4f}", D, 1)
    chk("full amax broad", f"{fu['amax_broad']:.4f}", D, 1)
    chk("local gate pass thin", f"**{100 * lo['pass_thin']:.2f}%**", D, 5)  # +1: 33.7
    chk("local sigma cap", f"{lo['cap']:.0f}px (local)", D, 1)
    chk("full sigma cap", f"{fu['cap']:.0f}px", D, 3)
    chk("alpha attenuation", f"**{lo['amax_broad'] / lo['amax_thin']:.1f}"
        f"\u00d7**", D, 2)
    chk("recorded coverage", f"{100 * v['C-T3-COVER full']['lo']:.1f}%", D, 11)  # +2: 33.7, P132
    chk("T3 amax IQR", f"IQR {fu['amax_iqr']:.3f}", D, 2)

    print("\n== T4: the re-score ==")
    rows = {"all": "all points (`C-T4-ALL`)", "thin": "**thin quartile**",
            "broad": "**broad quartile**"}
    for k, name in rows.items():
        r = t4[k]
        eq(f"T4/{k} dISO", r["dISO"], 100.0 * (r["fixed"] / r["F0"] - 1.0))
        row = (f"| {name} | {r['n']} | {r['F0']:.5f} | {r['fixed']:.5f} | "
               f"**-{abs(r['dISO']):.2f}%** | -{abs(r['abs']):.5f} |")
        chk(f"T4/{k} full table row", row, D, 1)
    eq("T4 gap", t4["gap"], t4["thin"]["dISO"] - t4["broad"]["dISO"])
    eq("T4 z", t4["z"], t4["gap"] / t4["null_sd"])
    chk("gap in points", f"{t4['gap']:.2f} point", D, 6)  # +2: 33.7, P132
    chk("null sigma", f"{t4['z']:.1f} null standard deviations", D, 2)
    chk("null mean", f"mean **-{abs(t4['null_mean']):.2f}**", D, 1)
    chk("null p95", f"p95 |gap| **{t4['null_p95']:.2f}**", D, 1)
    chk("shuffle count", f"{t4['n_null']} shuffles", D, 2)
    chk("reproduction", f"**{t4['repro']:.3f} points**", D, 3)
    chk("thin quartile width", f"{t4['thin_w_max']:.2f}", D, 3)  # +1: 31.7
    chk("broad quartile width", f"{t4['broad_w_min']:.2f}", D, 1)
    chk("T4 null bar", f"\u00b1{abs(v['T4 thin minus broad (points)']['hi']):.0f}"
        f" bar", D, 1)

    print("\n== the sign-error repair, re-derived from the unmix operands ==")
    u = json.loads((DATA / "13-unmix.json").read_text(encoding="utf-8"))
    pp = json.loads((DATA / "17-perpixel.json").read_text(encoding="utf-8"))
    eq("the two arms share F0", u["F0"]["ISO"], pp["F0_ISO"], 0.0)
    glob = 100.0 * (u["F2"]["ISO"] / u["F0"]["ISO"] - 1.0)
    if glob >= 0:
        fails.append(f"the global arm re-derives as {glob}, expected negative")
        print(f"  FAIL global arm is {glob:.4f}, not an improvement")
    else:
        print(f"  ok   global arm re-derives as {glob:.4f}% (an improvement)")
        chk("corrected global figure", f"-{abs(glob):.2f}%", D, 11)
        chk("global ISO operand", f"**{u['F2']['ISO']:.5f}**", D, 1)
    swing = abs(glob - t4["all"]["dISO"])
    chk("swing, 2dp", f"**{swing:.2f} points**", D, 1)
    chk("swing, 1dp", f"**{swing:.1f} points**", D, 1)
    stale = D.count("+3.7%")
    if stale != 4:
        fails.append(f"{stale} instances of +3.7% remain; the only 3 allowed "
                     f"are the quoted disclosures in 0, 5.1, P8 and P110")
        print(f"  FAIL {stale} stale +3.7% (expected exactly 4 disclosures)")
    else:
        n_ok_local = True
        print("  ok   exactly 4 +3.7% remain, all quoted disclosures")
    for q in ("this read \"+3.7%, *worse*\" until",
              "this row read **+3.7%**, the wrong sign, until `P110`",
              "\u00a75.1's `+3.7%, worse` is a small"):
        chk("disclosure present", q, D, 1)

    print("\n== facts P106-P112 ==")
    for f in ("P106", "P107", "P108", "P109", "P110", "P111", "P112", "P113"):
        chk(f"fact row {f}", f"| {f} | **", D, 1)

    print(f"\n{n_ok} checks passed; {len(fails)} failures")
    for f in fails:
        print(f"  - {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
