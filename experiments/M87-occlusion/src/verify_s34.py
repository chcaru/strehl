"""M87 -- verify section 34.

Re-derives every figure in section 34 from the JSON operands rather than
comparing the document against itself, re-hashes the orchestrator's gate-4.00
arm, and re-reads at source the two section-25 claims that section 34's
argument rests on.

Run with --counts to print observed occurrence counts with context, so the
expected counts below are set from evidence.  Guessed counts were 13 of 14
first-run failures in verify_s33 and that is not repeated here.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = HERE.parents[0] / "data"
GATE = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
ARMS = ["4.00", "2.00", "0.7078", "0.00"]
SHA4 = "E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112"

fails = []
checks = [0]


def ck(cond, label):
    checks[0] += 1
    if not cond:
        fails.append(label)
        print(f"  FAIL {label}")


def close(a, b, tol, label):
    checks[0] += 1
    if not (abs(a - b) <= tol):
        fails.append(f"{label}: {a!r} vs {b!r} tol {tol}")
        print(f"  FAIL {label}: {a!r} vs {b!r} tol {tol}")


def ckn(hay, needle, n, label):
    """Exact occurrence count, not mere presence.

    control_s34's N10 proved the presence form is instance-blind: altering one
    of two prose instances of a figure left every `in` check green.  Counts are
    taken from `--counts` output and each site is annotated below, so a figure
    duplicated by a typo cannot pass as a legitimate second mention.
    """
    checks[0] += 1
    got = hay.count(needle)
    if got != n:
        fails.append(f"{label}: {needle!r} appears {got}x, expected {n}x")
        print(f"  FAIL {label}: {needle!r} appears {got}x, expected {n}x")


def norm(s):
    """Collapse whitespace and normalise the two minus signs to ASCII."""
    return re.sub(r"\s+", " ", s.replace("\u2212", "-"))


def scope(raw):
    """Section 34 body plus its own fact rows P133-P141.

    The body ends at the next top-level section if one exists.  Section 34 is
    currently last, so this is EOF today, but an unterminated slice is the
    exact defect that made verify_s33 miscount when section 34 was appended
    beneath it: the scope silently widens and every count in it is wrong.
    """
    i = raw.index("## 34.")
    nxt = re.search(r"^## 3[5-9]\.", raw[i + 6:], re.M)
    body = raw[i:i + 6 + nxt.start()] if nxt else raw[i:]
    rows = []
    for pid in range(133, 142):
        m = re.search(rf"^\| P{pid} \|.*$", raw, re.M)
        if m:
            rows.append(m.group(0))
    return body + "\n" + "\n".join(rows)


def spearman(x, y):
    import numpy as np
    rx = np.argsort(np.argsort(np.asarray(x, float)))
    ry = np.argsort(np.argsort(np.asarray(y, float)))
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    return float((rx * ry).sum() / (((rx * rx).sum() * (ry * ry).sum()) ** 0.5))


def main():
    raw = DOC.read_bytes().decode("utf-8")
    sc = norm(scope(raw))
    d100 = json.loads((DATA / "100-gate-veildepth.json").read_text(encoding="utf-8"))
    d101 = json.loads((DATA / "101-attrib.json").read_text(encoding="utf-8"))
    d102 = json.loads((DATA / "102-robust.json").read_text(encoding="utf-8"))
    arms = d100["arms"]

    # ---------------------------------------------------------- provenance
    print("== provenance ==")
    h = hashlib.sha256()
    with open(GATE / "pin-bee-3-cpl-gate-4.00.tif", "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 22), b""):
            h.update(blk)
    ck(h.hexdigest().upper() == SHA4, "gate-4.00 arm sha256 unchanged")
    ck(d100["provenance"]["gate_4_sha256"] == SHA4, "json records the same sha")

    # ------------------------------------------- section 25 read at source
    print("== section 25 claims, re-read at source ==")
    n_raw = norm(raw)
    ck("| gate-0 merge | -6.6810% |" in n_raw,
       "s25.7 tabulates -6.6810% as the GATE-0 merge")
    ck("-25.8547" in n_raw, "s25 random-election figure present")
    v70 = (HERE / "70-veil.py").read_bytes().decode("utf-8")
    ck('"  merge (gate 0):' in v70 or "merge (gate 0)" in v70,
       "70-veil.py labels its -6.6810% row as gate 0")
    ck("bee3-leg-sel.npy" in v70, "70-veil.py computes it on the gate-0 merge")
    ck("V_merge" in v70 and "pct_veil_removed" in v70,
       "70-veil.py is the script that produced the removal figure")

    # ------------------------------------------------------- V re-derivation
    print("== V re-derived from near/far ==")
    for g in ARMS:
        v = 100.0 * (arms[g]["near_dn"] / arms[g]["far_dn"] - 1.0)
        close(v, arms[g]["V_pct"], 1e-9, f"V({g}) re-derived")
        ck(f"{arms[g]['near_dn']:.1f}" in sc, f"near DN {g} in prose")
        ck(f"{arms[g]['far_dn']:.1f}" in sc, f"far DN {g} in prose")

    b19 = d100["bars"]["B19"]
    dV = arms["0.00"]["V_pct"] - arms["4.00"]["V_pct"]
    close(dV, b19["dV_pp"], 1e-9, "dV re-derived")
    close(b19["frac_of_predicted"], 100 * dV / b19["predicted_pp"], 1e-9,
          "frac_of_predicted re-derived")
    close(spearman([float(g) for g in ARMS], [arms[g]["V_pct"] for g in ARMS]),
          b19["spearman_rho"], 1e-9, "spearman re-derived")
    branch = ("B19-ORCH-CONFIRMED" if dV <= -9.90 else
              "B19-PARTIAL" if dV <= -3.00 else
              "B19-FLAT" if abs(dV) < 3.00 else "B19-REVERSED")
    ck(branch == b19["branch"], f"B19 branch follows the registered thresholds")
    ck(b19["branch"] in sc, "B19 branch named in prose")
    ck(dV > 0, "dV sign is POSITIVE, opposite to the prediction")

    # ---------------------------------------------------------- decomposition
    print("== decomposition re-derived ==")
    n0, f0 = arms["4.00"]["near_dn"], arms["4.00"]["far_dn"]
    n1, f1 = arms["0.00"]["near_dn"], arms["0.00"]["far_dn"]
    near_only = 100.0 * (n1 / f0 - n0 / f0)
    far_only = 100.0 * (n0 / f1 - n0 / f0)
    cross = dV - near_only - far_only
    b21 = d101["bars"]["B21"]
    close(near_only, b21["near_only"], 1e-9, "near-only re-derived")
    close(far_only, b21["far_only"], 1e-9, "far-only re-derived")
    close(cross, b21["cross"], 1e-9, "cross re-derived")
    close(b21["closure"], 0.0, 1e-9, "closure is exact")
    ck(abs(b21["near_only"]) < abs(b21["far_only"]),
       "the reference term dominates the veil term")

    near = {g: arms[g]["near_dn"] for g in ARMS}
    far = {g: arms[g]["far_dn"] for g in ARMS}
    nspan = 100.0 * (max(near.values()) / min(near.values()) - 1)
    fspan = 100.0 * (max(far.values()) / min(far.values()) - 1)
    close(nspan, d101["near_span_pct"], 1e-9, "near span re-derived")
    close(fspan, d101["far_span_pct"], 1e-9, "far span re-derived")
    ck(f"{nspan:.4f}%" in sc, "near span in prose")
    ck(f"{fspan:.4f}%" in sc, "far span in prose")

    b20 = d101["bars"]["B20"]
    vpin = {g: 100.0 * (near[g] - far["4.00"]) / far["4.00"] for g in ARMS}
    for g in ARMS:
        close(vpin[g], b20["V_pinned"][g], 1e-9, f"pinned V({g}) re-derived")
    rng = max(vpin.values()) - min(vpin.values())
    close(rng, b20["range_pp"], 1e-9, "pinned range re-derived")
    b20b = ("B20-CONFIRMED-AVERAGING" if rng >= 9.90 else
            "B20-MATERIAL" if rng >= 3.00 else "B20-NEGLIGIBLE")
    ck(b20b == b20["branch"], "B20 branch follows the registered thresholds")
    ck(b20["branch"] in sc, "B20 branch named in prose")
    close(b20["frac_of_predicted_pct"], 100 * rng / b20["predicted_pp"], 1e-9,
          "B20 fraction re-derived")
    ck(f"{rng:.4f} pp" in sc, "pinned range in prose")
    ck(f"{b20['frac_of_predicted_pct']:.3f}%" in sc, "B20 fraction in prose")

    # ----------------------------------------------------------- robustness
    print("== robustness re-derived ==")
    for tag in ("A1", "A2", "A3"):
        a = d102["arms"][tag]
        ns = 100.0 * (max(a["near"].values()) / min(a["near"].values()) - 1)
        fs = 100.0 * (max(a["far"].values()) / min(a["far"].values()) - 1)
        close(ns, a["near_span_pct"], 1e-9, f"{tag} near span re-derived")
        close(fs, a["far_span_pct"], 1e-9, f"{tag} far span re-derived")
        vp = {g: 100.0 * (a["near"][g] - a["far"]["4.00"]) / a["far"]["4.00"]
              for g in ARMS}
        close(max(vp.values()) - min(vp.values()), a["pinned_range_pp"], 1e-9,
              f"{tag} pinned range re-derived")
        ck(a["pass"] == (ns < 0.5 and a["pinned_range_pp"] < 3.00),
           f"{tag} verdict follows the registered bars")
        ck(f"{a['near_span_pct']:.4f}" in sc, f"{tag} near span in prose")
        ck(f"{a['pinned_range_pp']:.4f}" in sc, f"{tag} pinned range in prose")
        ck(a["near_px"] >= 200 and a["far_px"] >= 200, f"{tag} bands populated")
    ck(d102["bars"]["B22"]["branch"] in sc, "B22 branch named in prose")

    # ------------------------------------------------------------- controls
    print("== controls ==")
    cdf = d100["controls"]["C_DRIFT_FORM"]
    r = cdf["rows"][-1]
    close(r["far_pct"], 100 * (far["0.00"] / far["4.00"] - 1), 1e-9,
          "drift far percent re-derived")
    close(cdf["mult_mismatch_pp"], abs(r["subj_pct"] - r["far_pct"]), 1e-9,
          "drift percent mismatch re-derived")
    close(cdf["add_mismatch_dn"], abs(r["subj_dn_delta"] - r["far_dn_delta"]),
          1e-9, "drift absolute mismatch re-derived")
    ck(cdf["form"] == "NEITHER", "drift form is NEITHER")
    ck(cdf["form"] in sc, "drift form named in prose")
    ck(abs(r["subj_pct"]) < abs(r["far_pct"]) / 10,
       "the drift is confined to the bright background")

    cmu = d100["controls"]["C_MULT"]
    ck(cmu["pass"] and cmu["err"] < 1e-12, "C-MULT passes its 1e-12 bar")
    ck(f"{cmu['err']:.3e}" in sc, "C-MULT error in prose")
    cad = d100["controls"]["C_ADD"]
    ck(cad["responsive"], "C-ADD moves, so V is not blind to an offset")
    cpos = d100["controls"]["C_POS"]
    ck(cpos["pass"] and cpos["err_pp"] < 0.5, "C-POS calibrated")
    planted = abs(cpos["V_planted"] - arms["4.00"]["V_pct"])
    ck(planted > 5.0, "C-POS plants a swing of the predicted order")
    ck(f"{cpos['err_pp']:.4f} pp" in sc, "C-POS error in prose")
    cfr = d100["controls"]["C_FROZEN"]
    close(cfr["dV_frozen"], dV, 1e-9, "C-FROZEN frozen dV matches")
    ck(abs(cfr["dV_per_arm"]) < 3.00,
       "C-FROZEN: verdict does not depend on freezing")

    # ------------------------------------------------- instance-aware counts
    print("== occurrence counts (instance-aware, see control_s34 N10) ==")
    ckn(sc, f"{nspan:.4f}%", 3, "near span sites")          # 34.4, 34.8, P135
    ckn(sc, f"{fspan:.4f}%", 2, "far span sites")           # 34.4, P135
    ckn(sc, f"{rng:.4f} pp", 2, "pinned range sites")       # 34.4, P135
    ckn(sc, b19["branch"], 2, "B19 branch sites")           # 34.3, P134
    ckn(sc, b20["branch"], 2, "B20 branch sites")           # 34.4, P135

    # --------------------------------------------------------------- limits
    print("== limits disclosed ==")
    ck(f"{100 * d100['provenance']['mask_iou_vs_s25']:.2f}%" in sc,
       "mask IoU against s25 disclosed")
    ck("7032x4688" in sc or "7032" in sc, "unbinned arm geometry disclosed")
    ck("99-probe.py" in sc, "the probe that caught the wrong crop is cited")
    ck("E(d)" in sc.replace("`", ""), "the E(d) limitation is stated")
    ck("instance-blind" in sc, "control_s34's N10 defect is disclosed")

    # P140: both verifier defects are RE-DERIVED here, not asserted.
    # This must replicate verify_s33's REAL scope -- body plus its own
    # P127-P132 fact rows -- because the 2 -> 3 claim is about that scope.
    # Slicing the body alone reads 1 -> 2 and would misreport the document.
    print("== P140: verifier defects re-derived ==")
    i33 = raw.index("## 33.")
    i34 = raw.index("## 34.", i33)
    s33rows = " ".join(l for l in raw.splitlines()
                       if re.match(r"^\| P1(2[789]|3[012]) \|", l))
    wide = re.sub(r"\s+", " ", raw[i33:] + " " + s33rows).count("55.321")
    narrow = re.sub(r"\s+", " ", raw[i33:i34] + " " + s33rows).count("55.321")
    leak = re.sub(r"\s+", " ", raw[i34:]).count("55.321")
    ck(narrow == 2, f"s33's corrected scope reads exactly 2 (saw {narrow})")
    ck(wide > narrow, "the scope-to-EOF defect really does over-count")
    # Exact identity rather than a pinned literal: the broken scope reads the
    # correct count plus whatever section 34 cites.  It stood at 3 when the
    # failure occurred and is higher now because P140 itself quotes the
    # figure -- which is why the literal is recorded as history in the prose
    # and re-derived as an identity here.
    ck(wide - narrow == leak, f"over-count {wide - narrow} == s34 citations {leak}")
    ck("2 to 3" in sc, "the 2 -> 3 miscount is stated in prose")
    ck("cites the figure again" in sc, "the self-demonstration is stated")

    src = pathlib.Path(__file__).resolve().parent
    allp = sorted(src.glob("*.py"))
    meas = [p for p in allp if not p.name.startswith(
        ("append", "verify", "control", "fix"))]
    lim, inv = [], []
    for p in meas:
        t = p.read_text(encoding="utf-8")
        if re.search(r"--limit\b", t):
            lim.append(p.name)
        if "subprocess" in t and re.search(r"strehl[-\w]*\.exe", t):
            inv.append(p.name)
    ck(not lim, f"P124's zero re-derives as zero (found {lim})")
    ck(not inv, f"the binary-invocation zero re-derives as zero (found {inv})")
    aud = json.loads((DATA / "93-audit.json").read_text(encoding="utf-8"))
    ck(aud["scripts_measurement"] == len(meas),
       f"audit denominator {aud['scripts_measurement']} vs disk {len(meas)}")
    ck(aud["scripts_total"] == len(allp),
       f"audit total {aud['scripts_total']} vs disk {len(allp)}")
    ck(f"97 to {len(meas)}" in sc, "the denominator move is stated in prose")
    ck(raw.count(f"**{len(allp)}**") == 1,
       "the script total has exactly one live site, and it is not in s34")
    ck(f"**{len(allp)}**" not in sc, "s34 does not restate the script total")

    # P141: re-derived from the probe's own aggregate, not transcribed.
    print("== P141: exit-code shape re-derived ==")
    xp = json.loads((DATA / "exitcode-repeat.json").read_text(encoding="utf-8-sig"))
    ck(xp["safe_ok_total"] == xp["safe_observations"],
       f"safe shapes {xp['safe_ok_total']}/{xp['safe_observations']}")
    ck(xp["runs_with_safe_loss"] == 0, "no run lost the code on a safe shape")
    ck(xp["runs_with_a_trap"] == xp["repeats"],
       "the positive control fired in every run, so the probe is commissioned")
    ck(xp["nondeterministic"], "corrupted-arm count really does vary run to run")
    ck(xp["corrupt_values"] == [-1],
       f"the corrupted value is -1 and only -1 (saw {xp['corrupt_values']})")
    ck(0 not in xp["corrupt_values"], "the trap never reported 0 on this host")
    ck(f"{xp['safe_ok_total']} of {xp['safe_observations']}" in sc,
       "the safe-observation tally is stated in prose")
    ck(f"{xp['runs_with_a_trap']} of {xp['repeats']}" in sc,
       "the commissioning tally is stated in prose")
    ck(f"{xp['trap_hit_min']} to {xp['trap_hit_max']} of {xp['trap_arms_per_run']}"
       in sc, "the run-to-run variation is stated in prose")
    ck(xp["ps_version"] in sc, "the PowerShell version is recorded")
    ck(str(xp["repeats"]) in sc, "the repeat count is stated in prose")

    for pid in range(133, 142):
        ck(f"| P{pid} |" in raw, f"fact P{pid} present")

    print(f"\nverify_s34: {checks[0]} checks, {len(fails)} failures")
    for f in fails:
        print(f"  - {f}")
    return 1 if fails else 0


def counts():
    raw = DOC.read_bytes().decode("utf-8")
    sc = norm(scope(raw))
    d100 = json.loads((DATA / "100-gate-veildepth.json").read_text(encoding="utf-8"))
    d101 = json.loads((DATA / "101-attrib.json").read_text(encoding="utf-8"))
    for label, s in [("near span", f"{d101['near_span_pct']:.4f}%"),
                     ("far span", f"{d101['far_span_pct']:.4f}%"),
                     ("pinned range", f"{d101['bars']['B20']['range_pp']:.4f} pp"),
                     ("B19 branch", d100["bars"]["B19"]["branch"]),
                     ("B20 branch", d101["bars"]["B20"]["branch"])]:
        print(f"{label!r:24s} -> {sc.count(s)} occurrence(s) of {s!r}")


if __name__ == "__main__":
    if "--counts" in sys.argv:
        counts()
        raise SystemExit(0)
    raise SystemExit(main())
