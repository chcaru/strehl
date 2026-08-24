"""Verify every number in docs/research/M95-coverage.md against the JSON the
instruments wrote this session, and prove each check discriminates.

Two passes:
  PRESENT      the string appears in the report
  DISCRIMINATE perturbing the last digit makes the check fail

A check that passes PRESENT but not DISCRIMINATE is matching something else in
the document -- arms 3 and 4 both hit this, with 0.6434 colliding with 0.6435 in
an adjacent table row. Anchors carry surrounding context where a bare value
would collide.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-coverage.md"
OUT = Path(__file__).resolve().parents[1] / "out"


def load(n):
    return json.loads((OUT / n).read_text(encoding="utf-8"))


def norm(s):
    """Canonicalise typography so a check compares data, not glyphs.

    The report uses U+2212 MINUS SIGN and U+00D7 MULTIPLICATION SIGN where the
    JSON emits ASCII. Folding those is not a weakening: digits are untouched,
    so the mutation pass still has to discriminate on value.
    """
    s = s.replace("\u2212", "-").replace("\u00d7", "x").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s)


def main():
    w0, x7, x7b = load("w0_warpstats.json"), load("x7_scale.json"), load("x7b_scale_field.json")
    x8, x10c, x11 = load("x8_fix.json"), load("x10c_planeres.json"), load("x11_alias.json")
    text = REPORT.read_text(encoding="utf-8")
    flat = norm(text)

    checks = []

    def add(label, s):
        checks.append((label, s))

    lad = x7b["B1_ladder"]
    for k, v in lad.items():
        kf = float(k)
        e = (1 / kf - 1) * 100 if kf else 0.0
        add(f"ladder row k={k}", f"| {kf:.4f} | {e:.2f}% | {v:+.4f} |")

    add("NOW cost", f"**{x8['NOW']['cost_dex']:+.4f} dex** (sem {x8['NOW']['sem']:.4f})")
    add("FIX cost", f"**{x8['FIX']['cost_dex']:+.4f} dex** (sem {x8['FIX']['sem']:.4f})")
    add("SNAP cost", f"**{x8['SNAP']['cost_dex']:+.4f} dex** (sem {x8['SNAP']['sem']:.4f})")
    add("recovery", f"recovers **{x8['fix_recovery_dex']:+.4f} dex**")
    add("snap again", f"costs {x8['SNAP']['cost_dex']:+.4f} dex (sem {x8['SNAP']['sem']:.4f})")
    add("n pairs", f"n = {x8['NOW']['n']} tile-frame pairs")
    add("cover alone", f"costs **{x8['K6_cover_alone']:+.6f} dex**")
    add("x8 null", f"K1 null, x8 identity warp | {x8['K1_null']:+.6f}")

    c, m = w0["centre"], w0["mid-radius"]
    add("frac mean", f"mean {c['fx_mean']:.4f} with sd {c['fx_sd']:.4f}")
    add("near int", f"only {100 * c['frac_within_0p05_px']:.1f}% of frames")
    add("scale min", f"from {w0['scale_minus_1_min']:.3e}")
    add("scale max", f"to {w0['scale_minus_1_max']:+.3e}")

    add("x7 defect", f"read **{x7['B1_ladder']['0.997']:+.4f} dex** at k = 0.997")
    add("x7b at .997", f"reads **{lad['0.997']:+.4f}**")
    add("spread", f"spread is {x7b['B1_spread_dex']:.4f} against 0.04")
    add("B3 bias", f"bias is **{x7b['B3_bias_dex']:+.4f} dex**")

    add("K1 null x7b", f"K1 null, scale 1.0 offset 0 | {x7b['K1_null']:+.6f}")
    add("K4 x7b", f"K4 integer shift, 1.0 px | {x7b['K4_integer_shift']:+.6f}")
    add("K5", f"Lanczos-8 at k = 0.9315 | {x7b['K5_bandmatch_lanczos8']:+.4f}")
    add("K3", f"σ = 0.30 px | {x7b['K3_planted_sigma0p30']:+.4f}")
    add("K1 x10c", f"x10c full and planes | {x10c['K1_null_full']:+.6f}")
    add("K4 x10c", f"2 mosaic px | {x10c['K4_integer_plane_shift']:+.6f}")

    a = x10c["arms"]["0.9974"]
    b = x10c["arms"]["0.9315"]
    add("penalty a", f"reads **{a['planes'] - a['full']:+.4f} dex** at k = 0.9974")
    add("penalty b", f"**{b['planes'] - b['full']:+.4f} dex** at k = 0.9315")

    add("suppression", f"band by **{x11['suppression']:.3e}x**")
    add("alias ratio", f"emits **{x11['plane_over_full']:.2f}x** what")

    print(f"report: {REPORT}")
    print(f"checks: {len(checks)}\n")

    missing = []
    for label, s in checks:
        needle = norm(s)
        if needle not in flat:
            missing.append((label, needle))
    print(f"PRESENT      : {len(checks) - len(missing)}/{len(checks)}")
    for label, n in missing:
        print(f"   MISSING  {label}: {n!r}")

    nondisc = []
    for label, s in checks:
        needle = norm(s)
        if needle in flat:
            digits = [i for i, ch in enumerate(needle) if ch.isdigit()]
            if not digits:
                continue
            i = digits[-1]
            mut = needle[:i] + str((int(needle[i]) + 1) % 10) + needle[i + 1:]
            if mut in flat:
                nondisc.append((label, needle, mut))
    print(f"DISCRIMINATE : {len(checks) - len(missing) - len(nondisc)}/{len(checks)}")
    for label, n, mu in nondisc:
        print(f"   COLLIDES {label}: {n!r} -> {mu!r} also present")

    facts = re.findall(r"^\*\*(P\d+)\.\*\*", text, re.M)
    labels = re.findall(r"^\*Label:\* (MEASURED|DERIVED|ARGUED)\.$", text, re.M)
    print(f"\ncandidate facts : {len(facts)} ({', '.join(facts)})")
    print(f"labelled facts  : {len(labels)}")
    ok_facts = len(facts) == len(labels) and len(facts) > 0

    if missing or nondisc or not ok_facts:
        print("\nVERIFICATION FAILED")
        return 1
    print("\nALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
