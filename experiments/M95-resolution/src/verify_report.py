"""Every number in the report must be one this session's code printed.

Same design as arm 2's verifier, with the two defects that verifier found in
itself already fixed:

  * digit-boundary matching, because a corrupted '0.9998' can match inside an
    unrelated '0.99934' and produce a false pass;
  * ranges checked as ONE string, because corrupting one endpoint of a range can
    land exactly on the other endpoint.

Two passes. PRESENCE: every expected string appears in the report. MUTATION:
corrupting each expected string must make the check fail -- otherwise the check
is not discriminating and proves nothing.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
REPORT = os.path.join(ROOT, "docs", "research", "M95-resolution.md")


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def norm(t):
    return (t.replace("\u2212", "-").replace("\u00d7", "x").replace("\u00a0", " ")
             .replace("\u2013", "-").replace("*", ""))


def present(text, s):
    """Digit-boundary aware: a numeric needle must not match inside a longer
    number. Anchors on a non-digit (or string edge) either side."""
    pat = r"(?<![0-9.])" + re.escape(s) + r"(?![0-9])"
    return re.search(pat, text) is not None


def build():
    """Return [(label, needle)]. Every needle is derived from a JSON file that
    a script in this directory wrote, never typed from memory."""
    e = []
    s1 = load("s1_measure.json")
    for k in sorted(s1["tiles"]):
        e.append(("s1 E %s" % k, "%.3f" % s1["tiles"][k]["E"]))
        e.append(("s1 Eshot %s" % k, "%.3f" % s1["tiles"][k]["E_shotnorm"]))
    e.append(("s1 K2 mean", "%.3f" % s1["controls"]["K2_mean"]))
    e.append(("s1 K1 mean", "%.3f" % s1["controls"]["K1_mean"]))

    s2 = load("s2_controls.json")
    e.append(("K1' floor", "%.4f" % s2["K1prime_floor"]))
    e.append(("K1' worst err", "%.2f" % s2["K1prime_worst_pred_err_pct"]))

    s3 = load("s3_merge.json")
    for tag in ("demo-noalign", "demo-align"):
        for t in sorted(s3[tag]):
            e.append(("s3 keep %s %s" % (tag, t), "%.3f" % s3[tag][t]["keep"]))

    s4 = load("s4_spectral.json")
    for r in s4:
        e.append(("s4 high %s" % r["label"], "%.2f" % r["high_ratio"]))

    s5 = load("s5_signal.json")
    e.append(("s5 V1 biased", "%.3f" % s5["controls"]["V1"]))
    v3 = sorted(g for _p, g in s5["controls"]["V3"])
    # The report quotes this as a RANGE. Check the endpoints, not the interior:
    # citing a value the report does not contain is a defect in the verifier.
    e.append(("s5 V3 range low", "%.3f" % v3[0]))
    e.append(("s5 V3 range high", "%.3f" % v3[-1]))

    s6 = load("s6_signal.json")
    e.append(("V1'", "%.5f" % s6["controls"]["V1"]))
    e.append(("V2'", "%.5f" % s6["controls"]["V2"]))
    # Grouped as whole table rows. Individually, '6.0' mutates to '6.1' which is
    # the value of the NEXT tile in the same row, so a per-value check cannot
    # discriminate. Same defect class arm 2's verifier found in itself.
    ts = sorted(s6["render"])
    for tag, key, fmt in (("top octave", "destroyed_top_octave", "%.1f"),
                          ("upper half", "destroyed_upper_half", "%.1f"),
                          ("all bands", "destroyed_all", "%.2f")):
        vals = [fmt % (100 * s6["render"][t][key]) for t in ts]
        e.append(("s6 %s row" % tag, " | ".join(v + " %" for v in vals)))
        if tag == "all bands":
            # The report quotes this one as a min-max range, not in tile order.
            e.append(("s6 all bands range",
                      "%s-%s" % (min(vals, key=float), max(vals, key=float))))
        else:
            e.append(("s6 %s slashes" % tag, " / ".join(vals)))
    sep6 = s6["controls"]["V2"] / s6["controls"]["V1"]
    # Separations carry their 'x' so the needle cannot be shadowed: a bare '21.6'
    # mutates to '21.1', which is a crop percentage elsewhere in the report.
    e.append(("V1'/V2' separation", "%.0fx" % sep6))

    s7 = load("s7_bias.json")
    e.append(("s7 worst hf snr", "%.3f" % min(r["hf_snr"] for r in s7["rows"])))
    e.append(("s7 recovered", repr(s7["rows"][0]["recovered"])))

    s8 = load("s8_alias.json")
    e.append(("s8 max fmax", "%.2f" % max(r["fmax"] for r in s8["rows"])))

    s9 = load("s9_sensitivity.json")
    e.append(("s9 worst pp", "%.2f" % s9["worst_pp"]))
    for row in s9["rows"]:
        vals = ["%.1f" % v for v in row["top_octave_pct"]]
        e.append(("s9 row d=%.2f" % row["d"], " | ".join(v + " %" for v in vals)))

    s10 = load("s10_optics.json")
    e.append(("pitch um", "%.4f" % s10["pitch_um"]))
    e.append(("nyq sensor", "%.2f" % s10["nyquist_sensor"]))
    e.append(("nyq binned", "%.2f" % s10["nyquist_binned"]))
    e.append(("optics MTF binNyq row",
              " / ".join("%.1f" % (100 * r["mtf_at_binned_nyquist"]) for r in s10["rows"])))
    cuts = [r["cutoff_cy_mm"] for r in s10["rows"]]
    # Report quotes the cutoff SPAN, highest to lowest, not every rung.
    e.append(("optics cutoff span", "%.1f-%.1f" % (max(cuts), min(cuts))))
    e.append(("optics N_eff max", "%.2f" % max(r["n_eff"] for r in s10["rows"])))
    worst = min(s10["rows"], key=lambda r: r["mtf_at_sensor_nyquist"])
    e.append(("optics worst MTF binNyq", "%.1f" % (100 * worst["mtf_at_binned_nyquist"])))

    f1 = load("f1_figure.json")
    e.append(("binned MP", "%.2f" % f1["binned_mp"]))
    e.append(("demosaic MP", "%.2f" % f1["demosaic_mp"]))
    for c in f1["crops"]:
        e.append(("crop C%d row" % c["crop"],
                  "%d, %d | %.1f %%" % (c["y"], c["x"], c["destroyed_top_octave_pct"])))
    e.append(("crops sorted", " / ".join(
        "%.1f" % v for v in sorted(c["destroyed_top_octave_pct"] for c in f1["crops"]))))

    f2 = load("f2_boxcontrol.json")
    e.append(("f2 median", "%.2f" % f2["agree"]["median_abs"]))
    e.append(("f2 p99", "%.2f" % f2["agree"]["p99_abs"]))
    e.append(("f2 corr", "%.6f" % f2["agree"]["corr"]))
    e.append(("f2 ctl median", "%.2f" % f2["positive_control"]["median_abs"]))
    e.append(("f2 separation", "%.1fx" % f2["separation"]))
    e.append(("f2 pct of scale", "%.4f" % (100 * f2["agree"]["median_abs"] / 65535)))

    f3 = load("f3_election.json")
    e.append(("f3 g0 frac", "%.4f" % (100 * f3["gate0"]["frac_gt_1000"])))
    e.append(("f3 g2 frac", "%.4f" % (100 * f3["gate2"]["frac_gt_1000"])))
    e.append(("f3 ctl frac", "%.4f" % (100 * f3["positive_control"]["frac_gt_1000"])))
    e.append(("f3 separation", "%.1fx" % f3["separation_frac_gt_1000"]))
    e.append(("f3 g0 p99", "%.2f" % f3["gate0"]["p99_abs"]))
    e.append(("f3 ctl p99", "%.2f" % f3["positive_control"]["p99_abs"]))
    return e


def mutate(s):
    """Change the last digit, avoiding a collision with the original."""
    for i in range(len(s) - 1, -1, -1):
        if s[i].isdigit():
            d = "1" if s[i] != "1" else "7"
            return s[:i] + d + s[i + 1:]
    return s + "0"


def main():
    text = norm(open(REPORT, encoding="utf-8").read())
    exp = build()
    print("checking %d numbers against JSON written by this session's code\n" % len(exp))

    missing = [(lab, s) for lab, s in exp if not present(text, s)]
    print("PRESENCE : %d/%d found" % (len(exp) - len(missing), len(exp)))
    for lab, s in missing:
        print("   MISSING  %-34s %s" % (lab, s))

    dead = []
    for lab, s in exp:
        if not present(text, s):
            continue
        m = mutate(s)
        if present(text, m):
            dead.append((lab, s, m))
    print("MUTATION : %d/%d discriminate" % (len(exp) - len(missing) - len(dead), len(exp) - len(missing)))
    for lab, s, m in dead:
        print("   NOT DISCRIMINATING  %-26s %s -> %s also present" % (lab, s, m))

    ok = not missing and not dead
    print("\n   verdict: %s" % ("ALL NUMBERS VERIFIED" if ok else "FAILED"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
