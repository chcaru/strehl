"""Re-derive every number Amendment 6 quotes, straight from out/snr-w2.json.

Rule 35: a checker that carries its own answer tests nothing. So this recomputes
each figure from the survey's saved records and compares it to the literal text
parsed out of PREREGISTRATION.md. Nothing is hardcoded on both sides.

Exit code 0 only if every quoted figure reproduces.
"""

import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
DOC = os.path.join(HERE, "PREREGISTRATION.md")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "m5-diffraction"))
import m5_lib as _m5  # noqa: E402

TOL = 0.02   # 2% relative, or half a unit in the last quoted place


def med(recs, tag, band, key="snr"):
    v = [r["bands"][band][key] for r in recs if r["aperture"] == tag]
    return float(np.median(v))


def rows_after(text, heading, n):
    """The n table rows following a heading, as lists of stripped cells."""
    i = text.index(heading)
    out, seen = [], 0
    for line in text[i:].splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("- :") for c in cells):
            continue
        seen += 1
        if seen == 1:      # header
            continue
        out.append(cells)
        if len(out) == n:
            break
    return out


class Q(float):
    """A number parsed from the document, carrying the precision it was quoted at.

    A document that says "-0.44%" has committed to two decimals, so a recomputed
    -0.4449 agrees with it exactly as well as the text allows. Judging that by a
    relative tolerance calls it a 1.1% error; judging it by half a unit in the last
    quoted place calls it agreement, which is what it is. Carrying the precision on
    the value means every comparison gets the right tolerance automatically instead
    of a blanket constant that is too loose for some figures and too tight for
    others -- the blanket 0.02 previously in use silently passed a 6% error on the
    between-aperture spread.
    """

    __slots__ = ("ulp",)


def _q(s):
    txt = str(s).replace("**", "").replace("~~", "")
    m = re.search(r"-?\d+\.?\d*", txt)
    if not m:
        q = Q("nan")
        q.ulp = 0.0
        return q
    tok = m.group()
    q = Q(tok)
    d = len(tok.split(".")[1]) if "." in tok else 0
    q.ulp = 0.5 * 10.0 ** (-d)
    return q


def qf(s):
    """Parse a regex-captured literal, keeping its quoted precision."""
    return _q(s)


def num(cell):
    return _q(cell)


def check(name, got, want, tol=TOL, atol=None):
    rel = abs(got - want) / max(abs(want), 1e-9)
    # atol defaults to half a unit in the last place the DOCUMENT quoted, read off
    # the literal itself, so nothing about the tolerance is hardcoded here.
    if atol is None:
        atol = getattr(want, "ulp", 0.0)
    ok = rel <= tol or (atol > 0.0 and abs(got - want) <= atol)
    print(f"  {'ok ' if ok else 'FAIL'} {name:44s} doc {want:10.3f}  "
          f"recomputed {got:10.3f}")
    return ok


def main():
    doc_path = sys.argv[1] if len(sys.argv) > 1 else DOC
    with open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    with open(doc_path, encoding="utf-8") as fh:
        text = fh.read()
    recs = d["records"]
    tags = ["f5.6", "f8", "f11", "f14", "f18"]
    ok = True
    # Prose regexes run against a whitespace-collapsed copy. A quoted phrase that
    # happens to straddle a line break is invisible to a plain pattern, and the
    # resulting "sentence not found" reads exactly like a legitimate failure.
    flat = re.sub(r"\s+", " ", text)

    print("Amendment 6, the non-monotone SNR table")
    band_rows = rows_after(text, "**The measured spectral SNR is not monotone", 2)
    for row, band in zip(band_rows, ["knee", "low"]):
        for t, cell in zip(tags, row[1:]):
            ok &= check(f"{band} band, {t}", med(recs, t, band), num(cell))

    print("\nAmendment 6, the equalisation cost table")
    eq = d["equalise"]
    cost_rows = rows_after(text, "**What equalisation then costs, measured.**", 6)
    for row in cost_rows:
        i = row[0]
        e = eq[i]
        for t, cell in (("f11", row[1]), ("f14", row[2])):
            got = (e[t]["floor"] + e[t]["add_var"]) / e[t]["floor"]
            ok &= check(f"ROI {i} {t} floor multiplier", got, num(cell))
        before = [e[t]["knee_before"] for t in ("f11", "f14", "f18")]
        after = [e[t]["knee_after"] for t in ("f11", "f14", "f18")]
        ok &= check(f"ROI {i} knee ratio before",
                    max(before) / min(before), num(row[3]))
        ok &= check(f"ROI {i} knee ratio after",
                    max(after) / min(after), num(row[4]))

    print("\nAmendment 6, the units table")
    prim = ["f11", "f14", "f18"]
    for band, label in (("low", "low band, the artefact alone"),
                        ("knee", "knee band, contaminated by the signal")):
        per = []
        for i in sorted({r["roi"] for r in recs}):
            v = [r["bands"][band]["snr"] for r in recs
                 if r["roi"] == i and r["aperture"] in prim]
            per.append(max(v) / min(v))
        ratio = float(np.median(per))
        row = rows_after(text, "| read from | ratio | differential bias |", 2)
        which = 0 if band == "low" else 1
        ok &= check(f"{band} primary-arm ratio", ratio, num(row[which][1]))
        ok &= check(f"{band} differential points", 5.7 * np.log(ratio),
                    num(row[which][2]), tol=0.05)

    print("\nAmendment 6a, the A4 table")
    a4 = rows_after(text, "### Amendment 6a", 1)
    for t, cell in zip(tags, a4[0]):
        ok &= check(f"high band, {t}", med(recs, t, "high"), num(cell), tol=0.03)

    print("\nAmendment 6, ranges quoted in prose (parsed from the doc, not hardcoded)")
    m = re.search(r"The floor rises by ([\d.]+)x to ([\d.]+)x", flat)
    if not m:
        print("  FAIL floor-multiplier prose sentence not found")
        ok = False
    else:
        mults = [(eq[i][t]["floor"] + eq[i][t]["add_var"]) / eq[i][t]["floor"]
                 for i in eq for t in ("f11", "f14")]
        ok &= check("min floor multiplier", min(mults), qf(m.group(1)))
        ok &= check("max floor multiplier", max(mults), qf(m.group(2)))
    m = re.search(r"knee-band ratio of ([\d.]+)x to ([\d.]+)x", flat)
    if not m:
        print("  FAIL residual-ratio prose sentence not found")
        ok = False
    else:
        afters = []
        for i in eq:
            a = [eq[i][t]["knee_after"] for t in ("f11", "f14", "f18")]
            afters.append(max(a) / min(a))
        ok &= check("min residual knee ratio", min(afters), qf(m.group(1)))
        ok &= check("max residual knee ratio", max(afters), qf(m.group(2)))

    print("\nAmendment 6b, the equalisation commissioning")
    eqp = os.path.join(OUT, "equalise-selftest.json")
    if not os.path.exists(eqp):
        print("  FAIL out/equalise-selftest.json missing; run src/equalise.py")
        ok = False
    else:
        with open(eqp, encoding="utf-8") as fh:
            e6 = json.load(fh)
        lin_rows = rows_after(text, "**(a) The arithmetic.**", 3)
        for row, rec in zip(lin_rows, e6["variance_linearity"]):
            ok &= check(f"added v {rec['v']:.0f}, rise", rec["rise"], num(row[1]))
            ok &= check(f"added v {rec['v']:.0f}, rise/v", rec["ratio"],
                        num(row[2]), tol=0.01)
        arm_rows = rows_after(text, "*same* planted cutoff, degraded to low-band", 4)
        for row, key in zip(arm_rows, ("quiet_raw", "loud_raw", "quiet_eq",
                                       "loud_eq")):
            a = e6["arms"][key]
            ok &= check(f"{key} snr", a["snr"], num(row[1]), tol=0.01)
            ok &= check(f"{key} bias", a["bias"], num(row[2]), tol=0.01)
            ok &= check(f"{key} sd", a["sd"], num(row[3]), tol=0.01)
        m2 = re.search(r"falls from ([\d.]+) points to ([\d.]+) points", flat)
        if not m2:
            print("  FAIL differential-bias sentence not found")
            ok = False
        else:
            ok &= check("gap before", e6["gap_raw"], qf(m2.group(1)), tol=0.01)
            ok &= check("gap after", e6["gap_eq"], qf(m2.group(2)), tol=0.01)
        m3 = re.search(r"([\d.]+)\s+points\s+across\s+a\s+([\d.]+)x\s+power\s+ratio"
                       r"\s+is\s+\*\*([\d.]+)\s+points\s+per\s+e-fold", flat)
        if not m3:
            print("  FAIL slope sentence not found")
            ok = False
        else:
            ok &= check("slope, gap", e6["gap_raw"], qf(m3.group(1)), tol=0.01)
            ok &= check("slope, snr ratio", e6["snr_ratio"], qf(m3.group(2)),
                        tol=0.02)
            ok &= check("slope, points/e-fold", e6["points_per_efold_power"],
                        qf(m3.group(3)), tol=0.02)
        m4 = re.search(r"real ladder's ([\d.]+)x, the expected differential bias is\s*"
                       r"\*\*([\d.]+) points", flat)
        if not m4:
            print("  FAIL applied-slope sentence not found")
            ok = False
        else:
            r_low = qf(m4.group(1))
            ok &= check("applied differential",
                        e6["points_per_efold_power"] * np.log(r_low),
                        qf(m4.group(2)), tol=0.03)

    print("\nAmendment 7, the measured texture slope")
    sp = os.path.join(OUT, "slope-w2.json")
    if not os.path.exists(sp):
        print("  FAIL out/slope-w2.json missing; run src/slope_survey.py")
        ok = False
    else:
        with open(sp, encoding="utf-8") as fh:
            s7 = json.load(fh)
        srows = rows_after(text, "**The fabric's MEASURED low-band slope is alpha =",
                           5)
        for row in srows:
            t = row[0].strip().replace("f/", "f").replace("f5.6", "f5.6")
            t = {"f5.6": "f5.6", "f8": "f8", "f11": "f11",
                 "f14": "f14", "f18": "f18"}[t]
            ok &= check(f"slope, {t}", s7["per_aperture_mean"][t], num(row[1]))
        m5 = re.search(r"MEASURED low-band slope is alpha = (\d+\.\d+), "
                       r"ROI-to-ROI sd\s+(\d+\.\d+)", flat)
        if not m5:
            print("  FAIL slope headline sentence not found")
            ok = False
        else:
            ok &= check("slope, overall mean", s7["overall_mean"],
                        qf(m5.group(1)), tol=0.005)
            ok &= check("slope, overall sd", s7["overall_sd"],
                        qf(m5.group(2)), tol=0.005)
        m6 = re.search(r"Between-aperture spread of the mean slope is \*\*([\d.]+)\*\*;"
                       r" within-aperture, ROI to ROI, it is \*\*([\d.]+)\*\*; ratio"
                       r" \*\*([\d.]+)\*\*", flat)
        if not m6:
            print("  FAIL aperture-independence sentence not found")
            ok = False
        else:
            ok &= check("between-aperture spread", s7["between"],
                        qf(m6.group(1)), tol=0.005)
            ok &= check("within-aperture spread", s7["within"],
                        qf(m6.group(2)), tol=0.005)
            ok &= check("spread ratio", s7["between"] / s7["within"],
                        qf(m6.group(3)), tol=0.01)
        m7 = re.search(r"standard deviation of only \*\*([\d.]+)\*\* times its span",
                       flat)
        if not m7:
            print("  FAIL ramp sd-to-span sentence not found")
            ok = False
        else:
            # ddof MUST match slope_survey.py, which uses numpy's default ddof=0
            # throughout (ramp.std(), per_ap[t].std(), means.std()). Using the
            # sample sd here would compare 0.395 against the code's 0.354 and
            # report a failure in the document when the disagreement is the
            # checker's own convention.
            ramp = np.linspace(0.0, 1.0, 5)
            ok &= check("ramp sd / span", float(np.std(ramp)),
                        qf(m7.group(1)), tol=0.01)
        if not s7["potent"]:
            print("  FAIL slope survey reports its potency control did not pass")
            ok = False

    print("\nAmendment 7, bias against slope")
    bp = os.path.join(OUT, "slope-bias.json")
    if not os.path.exists(bp):
        print("  FAIL out/slope-bias.json missing; run src/slope_bias.py")
        ok = False
    else:
        with open(bp, encoding="utf-8") as fh:
            b7 = json.load(fh)
        brows = rows_after(text, "reaches the floor at a lower frequency.", 7)
        for row, rec in zip(brows, b7["rows"]):
            ok &= check(f"alpha {rec['alpha']:.3f}, alpha", rec["alpha"],
                        num(row[0]), tol=0.005)
            ok &= check(f"alpha {rec['alpha']:.3f}, bias", rec["bias"],
                        num(row[1]), tol=0.01)
            ok &= check(f"alpha {rec['alpha']:.3f}, sd", rec["sd"],
                        num(row[2]), tol=0.01)
        # Each number is anchored on its own neighbouring literal. A single regex
        # with lazy .*? between the captures can match a TRUNCATED number -- lazy
        # expansion stops at the shortest match, so "-1.53%" can be captured as
        # "3%" with the rest absorbed by the .*?. That reads as a pass.
        m8a = re.search(r"\*\*(-?\d+\.\d+) points per unit of alpha\.\*\*", flat)
        m8b = re.search(r"At 2\.2, [^:*]*: (-?\d+\.\d+)%", flat)
        m8c = re.search(r"At 3\.126, [^:*]*: (-?\d+\.\d+)%", flat)
        for label, m in (("points per alpha", m8a), ("bias at 2.2", m8b),
                         ("bias at fabric", m8c)):
            if not m:
                print(f"  FAIL Amendment 7 slope sentence '{label}' not found")
                ok = False
        if m8a:
            ok &= check("points per unit alpha", b7["points_per_alpha"],
                        qf(m8a.group(1)), tol=0.01)
        if m8b:
            ok &= check("bias at alpha 2.2", b7["bias_at_2p2"],
                        qf(m8b.group(1)), tol=0.01)
        if m8c:
            ok &= check("bias at fabric alpha", b7["bias_at_fabric"],
                        qf(m8c.group(1)), tol=0.01)
        m9 = re.search(r"optimistic by about (\d+\.\d+) points", flat)
        if not m9:
            print("  FAIL optimistic-by sentence not found")
            ok = False
        else:
            ok &= check("2.2 vs fabric difference", abs(b7["difference"]),
                        qf(m9.group(1)), tol=0.02)
        if not b7["prediction_confirmed"]:
            print("  FAIL slope_bias reports its registered prediction was refuted")
            ok = False

    print("\nAmendment 7, quantisation")
    qp = os.path.join(OUT, "slope-quantisation.json")
    if not os.path.exists(qp):
        print("  FAIL out/slope-quantisation.json missing; run src/slope_quant.py")
        ok = False
    else:
        with open(qp, encoding="utf-8") as fh:
            q7 = json.load(fh)
        m10 = re.search(r"one radial bin is \*\*([\d.]+)%\*\* of `f_c`", flat)
        m11 = re.search(r"distinct bias values is \*\*([\d.]+)\*\* points", flat)
        m12 = re.search(r"endpoint difference of ([\d.]+) points is \*\*([\d.]+)\s*"
                        r"sigma\*\*", flat)
        m13 = re.search(r"hypotheses lie ([\d.]+)\s*bins apart", flat)
        for label, m in (("bin %", m10), ("gap", m11), ("endpoint", m12),
                         ("separation", m13)):
            if not m:
                print(f"  FAIL Amendment 7 quantisation sentence '{label}' not found")
                ok = False
        if m10:
            ok &= check("one bin, % of f_c", q7["bin_points"],
                        qf(m10.group(1)), tol=0.005)
        if m11:
            ok &= check("smallest gap", q7["bin_points"] / b7["nrep"],
                        qf(m11.group(1)), tol=0.01)
        if m12:
            ok &= check("endpoint difference", q7["range_points"],
                        qf(m12.group(1)), tol=0.01)
            ok &= check("endpoint sigma", q7["endpoint_sigma"],
                        qf(m12.group(2)), tol=0.02)
        if m13:
            ok &= check("hypotheses, bins apart", q7["separation_bins"],
                        qf(m13.group(1)), tol=0.02)

    print("\nAmendment 7, threat T6")
    wp = os.path.join(OUT, "weave-w2.json")
    if not os.path.exists(wp):
        print("  FAIL out/weave-w2.json missing; run src/weave_peaks.py")
        ok = False
    else:
        with open(wp, encoding="utf-8") as fh:
            w7 = json.load(fh)
        wrows = rows_after(text, "H2 and H3 candidates at f/14 and f/18.", 4)
        want = [w7["bins_tested"], w7["expected_false"], w7["total_peaks"],
                w7["max_shared_frequency"]]
        names = ["bins examined", "expected false positives", "bins observed",
                 "max shared frequency"]
        for row, v, nm in zip(wrows, want, names):
            ok &= check(f"T6, {nm}", float(v), num(row[1]), tol=0.02)
        if not w7["control_pass"]:
            print("  FAIL weave_peaks reports its own control did not pass")
            ok = False
        if not w7["clean"]:
            print("  FAIL weave_peaks reports a harmonic in the danger zone")
            ok = False

    print("\nAmendment 7a, the paired aperture test")
    pp = os.path.join(OUT, "slope-paired.json")
    if not os.path.exists(pp):
        print("  FAIL out/slope-paired.json missing; run src/slope_paired.py")
        ok = False
    else:
        with open(pp, encoding="utf-8") as fh:
            p7 = json.load(fh)
        prows = rows_after(text, "Removing the ROI\nmain effect first:", 5) or \
            rows_after(text, "| aperture | mean alpha | effect | t |", 5)
        for row, t in zip(prows, tags):
            ok &= check(f"7a effect, {t}", p7["effects"][t], num(row[2]), tol=0.01)
            ok &= check(f"7a t, {t}", p7["effects"][t] / p7["se"], num(row[3]),
                        tol=0.02)
        m14 = re.search(r"Residual sd (\d+\.\d+) on (\d+) df, standard error of each"
                        r"\s*effect (\d+\.\d+)", flat)
        m15 = re.search(r"f/18 minus f/11 is positive in (\d+) of (\d+) ROIs\*\*,"
                        r" mean\s*difference \+(\d+\.\d+), sign-test \*\*p = "
                        r"(\d+\.\d+)\*\*", flat)
        for label, m in (("residual sd", m14), ("sign test", m15)):
            if not m:
                print(f"  FAIL Amendment 7a sentence '{label}' not found")
                ok = False
        if m14:
            ok &= check("7a residual sd", p7["resid_sd"], qf(m14.group(1)),
                        tol=0.01)
            ok &= check("7a residual df", float(p7["dof"]), qf(m14.group(2)))
            ok &= check("7a effect se", p7["se"], qf(m14.group(3)), tol=0.01)
        if m15:
            ok &= check("7a sign positives", float(p7["sign_npos"]),
                        qf(m15.group(1)))
            ok &= check("7a sign n", float(p7["sign_n"]), qf(m15.group(2)))
            ok &= check("7a mean difference", p7["mean_diff_f18_f11"],
                        qf(m15.group(3)), tol=0.01)
            ok &= check("7a sign p", p7["sign_p"], qf(m15.group(4)), tol=0.02)
        m16 = re.search(r"predicts \+(\d+\.\d+) \(H3\) to \+(\d+\.\d+) \(H2\)", flat)
        if not m16:
            print("  FAIL Amendment 7a predicted-steepening sentence not found")
            ok = False
        else:
            ok &= check("7a predicted arm H2", p7["predicted_arm"],
                        qf(m16.group(2)), tol=0.01)
        m17 = re.search(r"tilts one end relative to the other by \*\*(\d+\.\d+)x\*\*,"
                        r".{0,80}?level ratio of \*\*(\d+\.\d+)x\*\*", flat)
        m18 = re.search(r"shape error is about\s*\*\*(\d+)%\*\* of the level "
                        r"difference", flat)
        for label, m in (("tilt", m17), ("shape percent", m18)):
            if not m:
                print(f"  FAIL Amendment 7a sentence '{label}' not found")
                ok = False
        if m17:
            ok &= check("7a band tilt", p7["band_tilt"], qf(m17.group(1)),
                        tol=0.01)
        if m18:
            ok &= check("7a shape vs level %", p7["shape_vs_level_pct"],
                        qf(m18.group(1)), tol=0.03)

    print("\nAmendment 7a, the object slope")
    op = os.path.join(OUT, "slope-object.json")
    if not os.path.exists(op):
        print("  FAIL out/slope-object.json missing; run src/slope_object.py")
        ok = False
    else:
        with open(op, encoding="utf-8") as fh:
            o7 = json.load(fh)
        strows = rows_after(text, "| aperture | f_c H2 | steepening H2 |", 5)
        # Steepening is quoted relative to a planted object slope of 3.000.
        for row, t in zip(strows, tags):
            for hyp, ci in (("H2", 2), ("H3", 4)):
                ne = {"H2": 3.0763, "H3": 2.4020}[hyp] * \
                    {"f5.6": 5.6, "f8": 8.0, "f11": 11.0,
                     "f14": 14.0, "f18": 18.0}[t]
                fcol = 1 if hyp == "H2" else 3
                ok &= check(f"7a f_c {hyp}, {t}",
                            float(_m5.f_cutoff_sensor(ne)), num(row[fcol]),
                            tol=0.01)
        orows = rows_after(text, "| aperture | measured | object H2 | object H3 |", 5)
        for row, t in zip(orows, tags):
            ok &= check(f"7a object H2, {t}", o7["object"]["H2"][t], num(row[2]),
                        tol=0.01)
            ok &= check(f"7a object H3, {t}", o7["object"]["H3"][t], num(row[3]),
                        tol=0.01)
        m19 = re.search(r"Mean object slope \*\*(\d+\.\d+)\*\* under H2, "
                        r"\*\*(\d+\.\d+)\*\* under H3", flat)
        if not m19:
            print("  FAIL Amendment 7a mean-object sentence not found")
            ok = False
        else:
            ok &= check("7a object mean H2", o7["object_mean"]["H2"],
                        qf(m19.group(1)), tol=0.005)
            ok &= check("7a object mean H3", o7["object_mean"]["H3"],
                        qf(m19.group(2)), tol=0.005)
        m20 = re.search(r"within \*\*(\d+\.\d+)\*\* of the\s*long-assumed 2\.2", flat)
        if not m20:
            print("  FAIL Amendment 7a distance-from-2.2 sentence not found")
            ok = False
        else:
            ok &= check("7a distance from 2.2",
                        abs(o7["object_mean"]["H2"] - 2.2),
                        qf(m20.group(1)), tol=0.05)
        m21 = re.search(r"applicable bias is\s*about \*\*-(\d+\.\d+)%\*\*", flat)
        if not m21:
            print("  FAIL Amendment 7a applicable-bias sentence not found")
            ok = False
        else:
            # Bias at the inferred object slope, read off slope_bias's fitted line
            # anchored at its own alpha 2.2 measurement. Nothing is hardcoded.
            a_obj = o7["object_mean"]["H2"]
            predicted = b7["bias_at_2p2"] + b7["points_per_alpha"] * (a_obj - 2.2)
            ok &= check("7a applicable bias", abs(predicted),
                        qf(m21.group(1)), tol=0.12)
        if o7["collapsed"]:
            print("  FAIL slope_object reports the spread collapsed, but Amendment")
            print("       7a states a residual confound remains")
            ok = False

    print()
    print("all Amendment 6, 7 and 7a figures reproduce" if ok
          else "SOME FIGURES DO NOT REPRODUCE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
