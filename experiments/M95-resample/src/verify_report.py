"""M95 arm 4 - verify every number in the report against the JSON that produced it.

Two checks per number:

  PRESENT      the exact string appears in the report
  DISCRIMINATE mutating the last digit makes it DISAPPEAR

The second matters more than the first. A check that still passes after the number is
mutated is not testing the number; it collided with a different value elsewhere in the
document. Arm 3's verifier caught three of those and one substantive science defect.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(os.path.dirname(HERE), "out")
REPORT = os.path.join(ROOT, "docs", "research", "M95-resample.md")


def norm(s):
    return (
        s.replace("\u2212", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00d7", "x")
        .replace("*", "")
    )


def load(n):
    return json.load(open(os.path.join(OUT, n)))


x2, x3, x4, x5 = load("x2_pairs.json"), load("x3_kernel.json"), load("x4_endtoend.json"), load("x5_ringing.json")
kern = x4["results"]["catmull-rom"]["delta"] - x4["results"]["nearest"]["delta"]
tot = abs(x2["deltas"]["B0->C"])

checks = []


def add(label, s, anchor=None):
    """`anchor` is the string actually searched for. Where a bare value can collide with
    a neighbouring one -- arm 3 hit three of these -- the anchor carries enough
    surrounding context that mutating the value's last digit cannot land on a real number
    somewhere else in the document."""
    checks.append((label, norm(str(anchor if anchor is not None else s))))


# --- the decomposition -------------------------------------------------------------
for k, v in x2["per_image"].items():
    add(f"x2 {k} mean", f"{v['mean']:+.4f}")
    # sd collides across rows (A is 0.6434, B1 is 0.6435), so anchor on mean|sd
    add(f"x2 {k} sd", f"{v['sd']:.4f}", f"{v['mean']:+.4f} | {v['sd']:.4f}")
    add(f"x2 {k} cc", f"{v['mean_cc']:.4f}", f"| {v['mean_cc']:.4f} |")
for k, v in x2["deltas"].items():
    add(f"x2 delta {k}", f"{v:+.4f}")
    add(f"x2 power {k}", f"{10**abs(v):.3f}x", f"{v:+.4f} | {10**abs(v):.3f}x")
    add(f"x2 amp {k}", f"{10**(abs(v)/2):.3f}x", f"{10**abs(v):.3f}x | {10**(abs(v)/2):.3f}x")

# --- controls ----------------------------------------------------------------------
for s, v in x2["planted"].items():
    add(f"K6 sigma={s}", f"{v:+.4f}")
add("K8 anchor separation", f"{x2['anchor_sep']:.4f}")
add("K7 null", "+0.000000")

# --- end to end --------------------------------------------------------------------
for k in ("nearest", "catmull-rom", "bilinear"):
    v = x4["results"][k]
    add(f"x4 {k} delta", f"{v['delta']:+.4f}")
    add(f"x4 {k} power", f"{10**abs(v['delta']):.3f}x")
    add(f"x4 {k} amp", f"{10**(abs(v['delta'])/2):.3f}x")
add("kernel alone dex", f"{kern:+.4f}")
add("kernel alone power", f"{10**abs(kern):.3f}x")
add("kernel alone amp", f"{10**(abs(kern)/2):.3f}x")

# --- kernels -----------------------------------------------------------------------
for n in ("catmullrom", "mitchell", "lanczos3", "bspline"):
    add(f"x3 {n} phase-avg", f"{x3['results'][n]['phase_avg']:+.4f}")
    add(f"x3 {n} worst", f"{x3['results'][n]['worst']:+.4f}")
add("x3 mitchell identity", f"{x3['results']['mitchell']['identity']:+.6f}")
cr = x3["results"]["catmullrom"]["phase_avg"]
for n in ("lanczos3", "bspline"):
    g = x3["results"][n]["phase_avg"] - cr
    add(f"x3 {n} gain", f"{g:+.4f}")
    add(f"x3 {n} gain power", f"{10**abs(g):.3f}x")
    # amplitude collides with the end-to-end power ratios, so anchor on the pair
    add(f"x3 {n} gain amp", f"{10**(abs(g)/2):.3f}x", f"{10**abs(g):.3f}x power, {10**(abs(g)/2):.3f}x amplitude")
add("x3 gap strehl vs independent", f"{x3['strehl_b0_b1'] - cr:+.4f}")

# --- ringing -----------------------------------------------------------------------
for n, v in x5["results"].items():
    if v["mean_overshoot"] > 0:
        add(f"x5 {n} mean overshoot", f"{v['mean_overshoot']:.6f}")
        add(f"x5 {n} p99.9", f"{v['p999']:.6f}")
crr = x5["results"]["catmullrom"]["mean_overshoot"]
for n in ("lanczos3", "bspline"):
    add(f"x5 {n} ratio", f"{x5['results'][n]['mean_overshoot']/crr:.3f}x")

# --- shares ------------------------------------------------------------------------
add("share kernel", f"{100*abs(kern)/tot:.1f}%")
add("share gather-not-kernel", f"{100*abs(x4['results']['nearest']['delta'])/tot:.1f}%")
add("share remainder", f"{100*(tot-abs(kern)-abs(x4['results']['nearest']['delta']))/tot:.1f}%")

# --- blur equivalents --------------------------------------------------------------
p25, p50 = x2["planted"]["0.25"], x2["planted"]["0.5"]
slope = __import__("numpy").log(p50 / p25) / __import__("numpy").log(2.0)
for lab, d in (("gather", x2["deltas"]["B0->B1"]), ("kernel", kern), ("total", x2["deltas"]["B0->C"])):
    add(f"sigma equiv {lab}", f"{0.25*(abs(d)/abs(p25))**(1.0/slope):.3f} px")

# --- kernel-change ratios quoted in prose ------------------------------------------
lg = x3["results"]["lanczos3"]["phase_avg"] - cr
bg = x3["results"]["bspline"]["phase_avg"] - cr
add("bspline share of lanczos gain", f"{100*bg/lg:.1f}%")
add("bspline share of lanczos ringing", f"{100*x5['results']['bspline']['mean_overshoot']/x5['results']['lanczos3']['mean_overshoot']:.1f}%")

# --- in-crate M86b corroboration (printed by `align --resampler-cost` this session) --
for s in ("9.8367e9", "9.8346e9", "0.9998", "3.2395e9", "0.3293", "5.0553e9", "0.5139"):
    add(f"M86b {s}", s)

# --- rustc standalone check --------------------------------------------------------
for s in ("2.384e-7", "6.199e-6", "2.6332e7", "4.0695e7", "1.545x", "9.155e-5"):
    add(f"rustc {s}", s)

# --- x1 defect numbers -------------------------------------------------------------
for s in ("124 px", "279 px", "-0.0011", "0.4717", "0.99932"):
    add(f"x1 defect {s}", s)


def mutate(s):
    """Change the LAST digit, keeping every other character. A suffix such as 'x' or
    '%' is preserved so the mutation cannot escape by changing the token's shape."""
    idx = [i for i, c in enumerate(s) if c.isdigit()]
    if not idx:
        return None
    i = idx[-1]
    d = int(s[i])
    return s[:i] + str((d + 1) % 10) + s[i + 1 :]


def main():
    if not os.path.exists(REPORT):
        print(f"MISSING REPORT {REPORT}")
        return 2
    body = norm(open(REPORT, encoding="utf-8").read())

    missing, nondisc = [], []
    for label, s in checks:
        if s not in body:
            missing.append((label, s))
            continue
        m = mutate(s)
        if m is not None and m in body:
            nondisc.append((label, s, m))

    print(f"checks           : {len(checks)}")
    print(f"present          : {len(checks) - len(missing)}/{len(checks)}")
    print(f"discriminating   : {len(checks) - len(missing) - len(nondisc)}/{len(checks) - len(missing)}")
    if missing:
        print("\nMISSING:")
        for label, s in missing:
            print(f"  {label:38s} {s!r}")
    if nondisc:
        print("\nNON-DISCRIMINATING (mutation still found in the document):")
        for label, s, m in nondisc:
            print(f"  {label:38s} {s!r} -> {m!r}")

    # the report must also carry its own structure
    need = ["## Candidate facts", "## 9. Verbatim patch", "Falsifiers", "### Failed, with diagnosis"]
    struct = [n for n in need if norm(n) not in body]
    if struct:
        print("\nMISSING SECTIONS:", struct)

    facts = re.findall(r"\*\*P(\d+)\.\*\*", open(REPORT, encoding="utf-8").read())
    print(f"\ncandidate facts  : {len(facts)}  ({'P' + facts[0]}..{'P' + facts[-1]})" if facts else "\nNO CANDIDATE FACTS")
    labels = ["MEASURED", "DERIVED", "ARGUED"]
    n_lab = sum(body.count(f"**{l}.**".replace("*", "")) for l in labels)
    print(f"labelled facts   : {n_lab}")
    if len(facts) != n_lab:
        print(f"  *** {len(facts)} facts but {n_lab} labels ***")

    ok = not missing and not nondisc and not struct and len(facts) == n_lab
    print("\n" + ("ALL CHECKS PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
