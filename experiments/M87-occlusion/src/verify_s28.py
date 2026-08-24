# -*- coding: utf-8 -*-
"""Re-derive every figure in section 28 (and facts P98-P104) from the JSON
operands, and verify every quoted M99 figure against M99's own report.

Percentages are recomputed from full-precision operands, never from the
5-dp display values -- that error produced three wrong figures in section 27.
"""
import io
import json
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[3]
DATA = ROOT / "experiments" / "M87-occlusion" / "data"
REPORT = ROOT / "docs" / "research" / "M87-occlusion.md"
M99 = ROOT / "docs" / "research" / "M99-photometric.md"

problems = []
checked = 0


def sec28():
    t = REPORT.read_text(encoding="utf-8")
    i = t.index("\n## 28. ")
    return t[i:]


def facts():
    t = REPORT.read_text(encoding="utf-8")
    out = []
    for fid in ("P98", "P99", "P100", "P101", "P102", "P103", "P104"):
        m = re.search(r"^\| " + fid + r" \|.*$", t, re.M)
        if not m:
            problems.append(f"fact {fid} missing from the fact table")
        else:
            out.append(m.group(0))
    return "\n".join(out)


def norm(s):
    return re.sub(r"\s+", " ", s.replace("**", "").replace("\u2212", "-")
                  .replace("\u00a0", " ").replace("\u2011", "-"))


def check(label, text, value, fmt):
    """Assert the value, formatted by fmt, appears literally in text."""
    global checked
    checked += 1
    want = fmt.format(value)
    if want not in norm(text):
        problems.append(f"{label}: re-derived {want!r} is NOT in the prose")


def literal(label, text, want):
    """Assert an already-formatted literal appears in text."""
    global checked
    checked += 1
    if want not in norm(text):
        problems.append(f"{label}: {want!r} is NOT in the prose")


def main():
    global checked
    d79 = json.loads((DATA / "79-sign-test.json").read_text(encoding="utf-8"))
    d80 = json.loads((DATA / "80-sign-repaired.json").read_text(encoding="utf-8"))
    d77 = json.loads((DATA / "77-decompose.json").read_text(encoding="utf-8"))
    body = norm(sec28() + "\n" + facts())
    m99 = norm(M99.read_text(encoding="utf-8"))

    # ---- 28.1 the drift shape, re-derived from the raw per-frame levels ----
    lvl = d79["level"]
    argmax = max(range(len(lvl)), key=lambda k: lvl[k])
    maxmin = max(lvl) / min(lvl)
    check("S0 argmax frame", body, argmax, "frame {}")
    check("S0 max/min", body, maxmin, "{:.4f}")
    check("S0 endpoint", body, d79["endpoint"], "{:.4f}")
    check("S0 rho vs k", body, d79["rho_level_vs_k"], "{:+.4f}")
    check("S0 rho vs k (80, same cube)", body, d80["rho_drift"], "{:+.4f}")
    if abs(d79["rho_level_vs_k"] - d80["rho_drift"]) > 1e-9:
        problems.append("79 and 80 disagree on the drift rho")
    if abs(maxmin - d79["maxmin"]) > 1e-9:
        problems.append("re-derived max/min disagrees with the stored value")

    # ---- 28.2 the failed plant ----
    check("plant ramp rho", body, d79["plant_ramp_rho"], "{:+.4f}")
    check("C-POS-RAMP slope (79)", body, d79["S2"]["pos_ramp"]["slope"], "{:+.4f}")
    check("C-POS-HUMP slope (79)", body, d79["S2"]["pos_hump"]["slope"], "{:+.4f}")
    if not (d79["plant_ramp_rho"] > 0 > d79["rho_level_vs_k"]):
        problems.append("the cancellation claim needs ramp rho > 0 > drift rho")
    if d79["S2"]["pos_ramp"]["slope"] >= 0:
        problems.append("the ramp control is claimed to have failed with the "
                        "wrong SIGN, but its slope is not negative")

    # ---- 28.3 the repaired estimator ----
    check("79 real R2 (hopeless fit)", body, d79["S2"]["real"]["r2"], "{:.4f}")
    for tag in ("C-EXACT", "C-POS-RAMP", "C-POS-HUMP", "C-NULL"):
        c = d80["T2"][tag]
        check(f"{tag} slope", body, c["slope"], "{:+.4f}")
        check(f"{tag} sign", body, 100 * c["sign"], "{:.2f}%")
        check(f"{tag} r2", body, c["r2"], "{:.4f}")
        if not c["pass"]:
            problems.append(f"{tag} is quoted as passing but pass=False")
    if not d80["controls_ok"]:
        problems.append("section 28 reads results, but controls_ok is False")

    # ---- 28.4 the amplitude, percentages re-derived from the DN operands ----
    for tag, label in (("whole band d(2,40)", "band"), ("veil peak d(8, 18)", "peak")):
        t3 = d80["T3"][tag]
        frac = t3["median_abs_photometric"] / t3["median_abs_observed"]
        # the stored quotient is a float32 division widened to double, so the
        # bar has to sit above float32 eps (1.19e-7) -- section 27.8's lesson,
        # which I had just repeated at a 1e-12 bar.
        if abs(frac - t3["fraction"]) > 1e-6 * max(1.0, abs(t3["fraction"])):
            problems.append(f"T3 {label}: stored fraction != photometric/observed")
        check(f"T3 {label} photometric DN", body, t3["median_abs_photometric"], "{:.2f}")
        check(f"T3 {label} observed DN", body, t3["median_abs_observed"], "{:.2f}")
        check(f"T3 {label} share", body, 100 * frac, "{:.2f}%")
    literal("n pairs", body, f"{d80['n_pairs']:,}".replace(",", " "))
    literal("n peak pairs", body, f"{d80['n_peak_pairs']:,}".replace(",", " "))
    if d80["T3"]["veil peak d(8, 18)"]["fraction"] >= 0.25:
        problems.append("the registered 25% bar is quoted as passed but is not")

    # ---- 28.5 the head to head ----
    t4 = d80["T4"]
    for k, lbl in (("band_veil", "band veil"), ("band_photometry", "band photometry"),
                   ("peak_veil", "peak veil"), ("peak_photometry", "peak photometry")):
        check(f"T4 {lbl}", body, 100 * t4[k], "{:.2f}%")
    if not (t4["peak_photometry"] < 0.50 < t4["peak_veil"]):
        problems.append("the 'photometry is below chance at the peak' claim fails")
    if t4["peak_veil"] <= t4["peak_photometry"]:
        problems.append("veil geometry is claimed to win at the peak but does not")

    # ---- 28.6 the 2x2 and the interaction ----
    t1 = d80["T1"]
    for cell in t1:
        check(f"T1 {cell} rho", body, t1[cell]["rho"], "{:+.4f}")
        check(f"T1 {cell} null", body, t1[cell]["null"], "{:+.4f}")
    pos = [c for c in t1 if t1[c]["rho"] > 0]
    if pos != ["M96 disconnected / M96 gap"]:
        problems.append(f"exactly one positive cell is claimed; found {pos}")
    base = t1["all band / 5x5 range"]["rho"]
    if not (t1["M96 disconnected / 5x5 range"]["rho"] < 0
            and t1["all band / M96 gap"]["rho"] < 0):
        problems.append("the interaction claim needs both single-factor moves "
                        "to stay negative")
    ps = abs(base - t1["M96 disconnected / 5x5 range"]["rho"])
    ss = abs(base - t1["all band / M96 gap"]["rho"])
    if abs(ps - d80["T1_pop_swing"]) > 1e-9 or abs(ss - d80["T1_stat_swing"]) > 1e-9:
        problems.append("re-derived T1 swings disagree with the stored values")
    # the disconnected-population rho must be the SAME statistic 79 measured
    if abs(t1["M96 disconnected / M96 gap"]["rho"] - d79["S1"]["disconnected"]["rho"]) > 1e-12:
        problems.append("79 and 80 disagree on the disconnected-population rho")
    # the ladder, quoted from 79's run
    for lo, hi, med in ((1, 5, 0.01330), (5, 20, -0.00410),
                        (20, 60, 0.06861), (60, 150, 0.07841)):
        checked += 1
        if f"{med:+.5f}" not in body:
            problems.append(f"ladder gap [{lo},{hi}) median {med:+.5f} is not in the prose")
    if not (0.01330 > -0.00410 < 0.06861):
        problems.append("the 'not monotone' claim needs a dip at [5,20)")

    # ---- section 27 figures re-quoted in 28 ----
    # E00 = baseline, E10 = photometry applied with the election frozen.
    rows = {r["feature"]: r for r in d77["rows"]}
    grew = 100 * (rows["BOX"]["E10"] / rows["BOX"]["E00"] - 1.0)
    removed = 100 * (1.0 - rows["SHELF"]["E10"] / rows["SHELF"]["E00"])
    check("cell 10 box growth", body, grew, "{:.2f}%")
    check("cell 10 shelf removal", body, removed, "{:.2f}%")
    if grew <= 0:
        problems.append("the box is claimed to get WORSE under photometry alone")
    if not (0 < removed < 100):
        problems.append("the shelf removal share is outside (0,100)%")

    # ---- every M99 figure quoted in 28 must be in M99's own report ----
    for q in ("20.64", "8.32", "1.1818", "1.0380", "103-120",
              "0.751", "0.883"):
        checked += 1
        if q not in m99:
            problems.append(f"M99 figure {q!r} quoted in section 28 is NOT in "
                            f"M99-photometric.md")
    checked += 1
    if "monotone" not in m99:
        problems.append("section 28 claims M99 12.3 discusses monotonicity, but "
                        "the word does not appear in M99-photometric.md")

    # ---- P24, cited by P104 ----
    t = REPORT.read_text(encoding="utf-8")
    m = re.search(r"^\| P24 \|.*$", t, re.M)
    checked += 1
    if not m:
        problems.append("P104 cites P24, which is not in the fact table")
    else:
        p24 = norm(m.group(0))
        for frag in ("49", "0.6%"):
            checked += 1
            if frag not in p24:
                problems.append(f"P104 quotes {frag!r} from P24, which P24 does "
                                f"not contain: {p24[:160]}")

    print(f"checked {checked} figures against the JSON operands and the "
          f"cited reports")
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print("  -", p)
        return 1
    print("all figures in section 28 re-derive exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
