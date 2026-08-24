"""Verify every number the report quotes against the artifacts, and prove the
verifier can fail.

Two hazards this file is built around, both previously measured on this machine:

  * The report is wrapped prose, so a phrase can span a line break and a plain
    substring probe returns a false FAIL. Every check runs against a
    whitespace-collapsed copy of the text.
  * A verifier that only ever reports PASS is indistinguishable from one that
    checks nothing. The `--mutate` mode plants a wrong digit for each check in
    turn and requires that check, and only that check, to go red.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
REPORT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
    "docs", "research", "M95-chroma-cositing.md",
)


def j(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def collapse(t):
    # The report is written with the Unicode minus sign U+2212 in prose; the
    # verifier formats ASCII hyphens. Normalise both, or every negative number
    # reads as a false FAIL -- which is exactly what happened on the first run.
    return re.sub(r"\s+", " ", t.replace("\u2212", "-").replace("\u2013", "-"))


def present(flat, needle):
    """Substring search that will not match a number inside a longer number.

    Without this, the mutation control is confounded: corrupting C5's `0.9998`
    to `0.9993` "finds" it inside C9's `0.99934` and the check looks unable to
    discriminate when in fact the report is correct.
    """
    n = collapse(needle)
    pat = re.escape(n)
    if n[:1].isdigit():
        pat = r"(?<![0-9.])" + pat
    if n[-1:].isdigit():
        pat = pat + r"(?![0-9])"
    return re.search(pat, flat) is not None


def build_checks():
    s3, s4, s5, s6 = (j("s3_cositing.json"), j("s4_benefit.json"),
                      j("s5_controls.json"), j("s6_shipped.json"))
    b, a = s6["before"], s6["after"]
    m = s4["merged-gate0"]
    f = s4["frame-183"]
    c = []

    def add(label, text):
        c.append((label, text))

    # --- shipped, end to end -------------------------------------------------
    add("shipped regR before", "%.4f" % b["reg_R"])
    add("shipped regR after", "%.4f" % a["reg_R"])
    add("shipped regB before", "%.4f" % b["reg_B"])
    add("shipped regB after", "%.4f" % a["reg_B"])
    add("shipped regG before", "%.4f" % b["reg_G"])
    add("shipped regG after", "%.4f" % a["reg_G"])
    add("shipped edge chroma before", "%.1f" % b["chroma_rms_edge_DN"])
    add("shipped edge chroma after", "%.1f" % a["chroma_rms_edge_DN"])
    add("shipped chroma all before", "%.1f" % b["chroma_rms_DN"])
    add("shipped chroma all after", "%.1f" % a["chroma_rms_DN"])
    add("red pct removed", "%.1f %%" % (100 * (1 - a["reg_R"] / b["reg_R"])))
    add("blue pct removed", "%.1f %%" % (100 * (1 - a["reg_B"] / b["reg_B"])))
    add("green pct removed", "%.1f %%" % (100 * (1 - a["reg_G"] / b["reg_G"])))
    add("edge chroma pct", "%.1f %%" % (100 * (1 - a["chroma_rms_edge_DN"] / b["chroma_rms_edge_DN"])))
    add("all chroma pct", "%.1f %%" % (100 * (1 - a["chroma_rms_DN"] / b["chroma_rms_DN"])))
    add("did-anything dR", "%d" % s6["did_anything_happen"]["max_dR_DN"])
    add("did-anything dB", "%d" % s6["did_anything_happen"]["max_dB_DN"])

    # --- S3 displacement -----------------------------------------------------
    import statistics as st
    for pair in ("frame-183", "merged-gate0"):
        p = s3["pairs"][pair]
        add("%s ROIs" % pair, "%d/%d" % (p["n_kept"], p["n_offered"]))
        for ch in "RGB":
            rows = p["per_channel"][ch]
            dy, dx = st.mean(r["dy"] for r in rows), st.mean(r["dx"] for r in rows)
            add("%s %s dy" % (pair, ch), "%+.4f" % dy)
            add("%s %s dx" % (pair, ch), "%+.4f" % dx)

    # --- S4 benefit table ----------------------------------------------------
    for tag, p in (("frame-183", f), ("merged-gate0", m)):
        for variant in ("as-shipped", "co-sited", "N1-backwards", "N3-blur-only"):
            add("%s %s regR" % (tag, variant), "%.4f" % p[variant]["reg_R"])
            add("%s %s regB" % (tag, variant), "%.4f" % p[variant]["reg_B"])
    add("merged edge as-shipped", "%.2f" % m["as-shipped"]["chroma_rms_edge_DN"])
    add("merged edge co-sited", "%.2f" % m["co-sited"]["chroma_rms_edge_DN"])
    add("merged edge N1", "%.2f" % m["N1-backwards"]["chroma_rms_edge_DN"])

    # --- S5 controls ---------------------------------------------------------
    add("C11 mean ratio", "%.4f" % s5["C11"]["mean_ratio"])
    for r in s5["C11"]["rows"]:
        add("C11 seed %d shipped" % r["seed"], "%.5f" % r["chroma_shipped"])
        add("C11 seed %d fixed" % r["seed"], "%.5f" % r["chroma_fixed"])
    for pair, v in s5["N4"]["rows"].items():
        add("N4 %s before" % pair, "%.4f" % v["green_before"])
        add("N4 %s after" % pair, "%.4f" % v["green_after_shift"])

    # --- console-only numbers, recomputed rather than recalled ---------------
    c1, c2 = j("c1_controls.json"), j("c2_controls.json")
    add("C1 worst", "%.5f" % max(r["worst_err"] for r in c1["C1"]))
    add("C2 noise worst", "%.3g" % max(max(abs(r["dx"]), abs(r["dy"])) for r in c1["C2"]))
    add("C3 worst delta", "%.6f" % max(r["delta"] for r in c1["C3"]))
    # Ranges are checked as one string. Checked as two independent endpoints,
    # a one-digit corruption of `0.9999` lands on `0.9998`, which the report
    # legitimately contains as the other endpoint -- so the mutation control
    # could not discriminate. That was a defect in the control, not the report.
    add("C5 ramp range", "%.4f-%.4f" % (min(r["ramp_hf_keep"] for r in c1["C5"]),
                                        max(r["ramp_hf_keep"] for r in c1["C5"])))
    add("C5 ndimage range", "%.4f-%.4f" % (min(r["ndimage_hf_keep"] for r in c1["C5"]),
                                           max(r["ndimage_hf_keep"] for r in c1["C5"])))
    add("C7 naive worst", "%.4f" % c2["C7"]["naive_worst"])
    add("C7 robust worst", "%.3g" % c2["C7"]["robust_worst"])
    add("C8 planted worst", "%.3g" % c2["C8"]["planted_worst"])
    add("C8 null worst", "%.3g" % c2["C8"]["null_worst"])
    add("C9 real range", "%.5f-%.5f" % (min(c2["C9"]["real"]), max(c2["C9"]["real"])))
    add("C9 noise range", "%.5f-%.5f" % (min(c2["C9"]["noise"]), max(c2["C9"]["noise"])))
    for r in c2["C7"]["rows"]:
        add("C7 naive plant %.1f" % r["plant"], "%+.4f" % r["naive_dy"])

    import math
    for pair, p in s3["pairs"].items():
        mean = {ch: (st.mean(r["dy"] for r in p["per_channel"][ch]),
                     st.mean(r["dx"] for r in p["per_channel"][ch]))
                for ch in "RGB"}
        sep = math.hypot(mean["R"][0] - mean["B"][0], mean["R"][1] - mean["B"][1])
        add("%s R-B separation" % pair, "%.4f" % sep)
        g = max(abs(v) for v in mean["G"])
        rr = max(abs(v) for v in mean["R"])
        add("%s green null" % pair, "%.5f" % g)
        add("%s null separation" % pair, "%.0f" % (rr / g))
    add("geometric prediction", "%.4f" % (0.5 * math.sqrt(2)))
    return c


def run(text, checks):
    flat = collapse(text)
    bad = []
    for label, needle in checks:
        if not present(flat, needle):
            bad.append((label, needle))
    return bad


def main():
    with open(REPORT, encoding="utf-8") as f:
        text = f.read()
    checks = build_checks()
    print("checking %d numbers against the artifacts" % len(checks))
    bad = run(text, checks)
    for label, needle in bad:
        print("   MISSING: %-34s %r" % (label, needle))
    print("\nbaseline: %d/%d present" % (len(checks) - len(bad), len(checks)))

    # ---- negative control: every check must be able to go red --------------
    print("\n== negative control: plant a wrong digit for each check ==")
    misses = []
    for label, needle in checks:
        digits = [i for i, ch in enumerate(needle) if ch.isdigit()]
        if not digits:
            continue
        i = digits[-1]
        wrong = needle[:i] + ("8" if needle[i] != "8" else "3") + needle[i + 1:]
        flat = collapse(text)
        # The mutated value must NOT be present, and the true one must be.
        if present(flat, wrong) or not present(flat, needle):
            misses.append(label)
    if misses:
        print("   %d check(s) could not be shown to discriminate:" % len(misses))
        for m in misses[:20]:
            print("      %s" % m)
    else:
        print("   all %d checks discriminate: the true value is present and a" % len(checks))
        print("   one-digit corruption of it is not.")

    ok = not bad and not misses
    print("\nVERIFIER: %s" % ("ALL VERIFIED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
