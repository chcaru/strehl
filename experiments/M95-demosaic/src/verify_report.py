"""Verify every number in docs/research/M95-demosaic.md against the JSON the
instruments wrote this session, and prove each check discriminates.

Two passes:
  PRESENT      the string appears in the report
  DISCRIMINATE perturbing the last digit makes the check fail

A check that passes PRESENT but not DISCRIMINATE is matching something else in
the document. Arms 3, 4 and 5 all hit that (0.6434 colliding with 0.6435; 0.9999
with 0.9990), so anchors carry surrounding context where a bare value would
collide.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-demosaic.md"
OUT = Path(__file__).resolve().parents[1] / "out"


def load(n):
    return json.loads((OUT / n).read_text(encoding="utf-8"))


def norm(s):
    """Canonicalise typography so a check compares data, not glyphs.

    The report uses U+2212 MINUS SIGN and U+00D7 MULTIPLICATION SIGN where the
    JSON emits ASCII. Folding those is not a weakening: digits are untouched, so
    the mutation pass still has to discriminate on value.
    """
    s = s.replace("\u2212", "-").replace("\u00d7", "x").replace("\u00a0", " ")
    s = s.replace("\u2013", "-")
    return re.sub(r"\s+", " ", s)


def main():
    cert, lad, sc = load("d1_certify.json"), load("d2_ladder.json"), load("d3_scale.json")
    text = REPORT.read_text(encoding="utf-8")
    flat = norm(text)

    checks = []

    def add(label, s):
        checks.append((label, s))

    A = lad["ladder_AHD"]
    mhc, bil, nea = A["MHC"]["luma"], A["BILINEAR"]["luma"], A["NEAREST"]["luma"]

    # ------------------------------------------------- ladder table rows
    # Anchored on the full row including its bold markers. A bare
    # "| p | s | a |" for MHC silently matched the LUMA row of the
    # per-channel table instead, which is the same data in a different table --
    # a passing check that was not checking what it claimed to.
    add("ladder MHC",
        f"| **{mhc['power']:+.4f}** | **{mhc['signal']:+.4f}** | {mhc['artifact']:+.4f}"
        f" | **{mhc['artifact_share']:.4f}** |")
    add("ladder BILINEAR",
        f"| {bil['power']:+.4f} | {bil['signal']:+.4f} | {bil['artifact']:+.4f}"
        f" | {bil['artifact_share']:.4f} |")
    add("ladder NEAREST",
        f"| **{nea['power']:+.4f}** | {nea['signal']:+.4f} | {nea['artifact']:+.4f}"
        f" | **{nea['artifact_share']:.4f}** |")

    # ------------------------------------------------------ per channel
    for c in ["luma", "R", "G", "B"]:
        s = A["MHC"][c]
        add(f"chan {c}",
            f"| {c} | {s['power']:+.4f} | {s['signal']:+.4f} | {s['artifact']:+.4f} |"
            f" {s['artifact_share']:.4f} |")

    # ------------------------------------------------------------- B1/B2
    add("B1 louder", f"**{nea['power'] - mhc['power']:+.4f} dex louder than MHC**")
    add("B1 less detail", f"**{mhc['signal'] - nea['signal']:.4f} dex less real detail**")
    add("B1 share", f"**{nea['artifact_share'] * 100:.1f}%** of what it emits")
    add("B2 deficit", f"**{lad['B2_mhc_signal_deficit_dex']:.4f} dex less true detail**")
    add("MHC power match", f"to **{mhc['power']:+.4f} dex**")
    add("MHC fabricated",
        f"**{mhc['artifact_share'] * 100:.1f}% of that power is fabricated**")

    # ---------------------------------------------------------- controls
    k1 = lad["K1"]["luma"]
    add("K1 row",
        f"power {k1['power']:.3e}, signal {k1['signal']:.3e},"
        f" alpha {k1['alpha_mean_abs']:.10f}, artifact share {k1['artifact_share']:.3e}")
    add("K1 value again", f"is\n{k1['signal']:.3e}, float64 round-off")
    k3 = lad["K3"]["rows"]
    add("K3 row",
        "signal " + " / ".join(f"{r['signal']:+.4f}" for r in k3))
    k4 = lad["K4"]["rows"]
    add("K4 row",
        "artifact " + " / ".join(f"{r['artifact']:+.4f}" for r in k4))
    add("K4 drive", f"from {k4[0]['artifact']:+.4f} to {k4[-1]['artifact']:+.4f}")
    add("K5 dev", f"moves at most {lad['K5']['mhc_max_dev']:+.4f} dex")
    add("K6 worst", f"worst disagreement {cert['worst_max_abs_diff']:.3e}")
    add("K6 planted", f"moves the output by\n{cert['planted_tap_delta']:.3e}")
    add("K6 tolerance", f"tolerance {cert['tolerance']:.0e}")

    # --------------------------------------------------------------- d3
    add("d3 real", f"per-bin power ratio : {sc['real']['ratio']:.5f}"
                   f"   ({sc['real']['ratio_dex']:+.4f} dex)")
    add("d3 truth", f"per-bin power ratio : {sc['truth']['ratio']:.5f}"
                    f"   ({sc['truth']['ratio_dex']:+.4f} dex)")
    add("d3 overdrive", f"demosaic {sc['overdrive']:.2f}x as hard")

    # ------------------------------------------------------ tiles / band
    add("tiles", f"{lad['count']} tiles of {lad['tile']} x {lad['tile']}")
    add("band", f"band {lad['band'][0]:.2f}-{lad['band'][1]:.2f} cyc/px")

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
