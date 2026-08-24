"""M87 -- verify section 33.  Re-derives every figure from its operands.

This checker does not compare the document against itself.  Every number is
recomputed from the JSON an experiment wrote, or re-read from the
orchestrator's own artifacts, and only then looked for in the prose.  The
render is re-hashed from disk and the n_eff ladder is re-parsed from
`neff-ladder.txt` rather than from my transcription of it.

Counts are scoped to section 33 and its own fact rows.  A whole-document count
breaks the moment a later section cites one of these figures, and the usual
repair -- bumping the expected count -- ends in someone weakening it to a
presence check, which cannot see a figure that is wrong in one place and right
in another (`P105`).
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
GATE = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
MINUS = "\u2212"

fails, checks = [], 0


def ck(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)


def has(hay, needle, n=1, label=""):
    global checks
    checks += 1
    got = hay.count(needle)
    if got != n:
        fails.append(f"{label or needle!r}: found {got}x, expected {n}x")


def m(s):
    return s.replace("-", MINUS)


def main():
    raw = DOC.read_bytes().decode("utf-8")
    ck(raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF")
    flat = re.sub(r"\s+", " ", raw)

    i = raw.index("## 33.")
    sec = re.sub(r"\s+", " ", raw[i:])
    rows = "\n".join(l for l in raw.splitlines()
                     if re.match(r"^\| P1(2[789]|3[012]) \|", l))
    rowsf = re.sub(r"\s+", " ", rows)
    scope = sec + " " + rowsf
    ck(len([l for l in rows.splitlines()]) == 6, "expected 6 fact rows P127-P132")
    for pid in ("P127", "P128", "P129", "P130", "P131", "P132"):
        ck(f"| {pid} |" in raw, f"{pid} row missing")

    g96 = json.loads((DATA / "96-gate-final.json").read_text(encoding="utf-8"))
    g97 = json.loads((DATA / "97-gate-attrib.json").read_text(encoding="utf-8"))
    g98 = json.loads((DATA / "98-delta-form.json").read_text(encoding="utf-8"))
    g95 = json.loads((DATA / "95-control-diag.json").read_text(encoding="utf-8"))
    g94 = json.loads((DATA / "94-gate-veil.json").read_text(encoding="utf-8"))

    # ---- 1. the render is what section 31 measured ---------------------
    p4 = GATE / "pin-bee-3-cpl-gate-4.00.tif"
    h = hashlib.sha256(p4.read_bytes()).hexdigest()
    ck(h == g94["ref_sha"], "gate-4.00 hash != the hash 94 recorded")
    ck(h.upper().startswith("E400A63AA9F6AB1F1957940D7BD9D496"),
       f"gate-4.00 hash {h[:32]} != the value in 33.1")
    has(scope, "E400A63AA9F6AB1F1957940D7BD9D496", 1, "33.1 hash head")
    if (SCRATCH / "s31-bee3.tif").exists():
        ck(hashlib.sha256((SCRATCH / "s31-bee3.tif").read_bytes()
                          ).hexdigest() == h,
           "gate-4.00 arm is no longer byte-identical to s31-bee3.tif")
    ck(p4.stat().st_size == 197797874, "arm size != 197 797 874 bytes")
    has(scope, "197 797 874", 1, "arm byte count")

    # ---- 2. n_eff re-parsed from the orchestrator's own file -----------
    lad = (GATE / "neff-ladder.txt").read_text(encoding="utf-8", errors="replace")
    tab = {}
    for line in lad.splitlines():
        t = line.split()
        if len(t) >= 5 and re.fullmatch(r"\d+\.\d\d", t[0]):
            tab[t[0]] = (float(t[2]), t[3])
    ck(tab.get("4.00", (0,))[0] == 55.321, f"n_eff gate 4.00 = {tab.get('4.00')}")
    ck(tab.get("0.00", (0,))[0] == 1.000, f"n_eff gate 0.00 = {tab.get('0.00')}")
    ck(tab["4.00"][1] == "38.77%", f"n_eff=1 pct gate 4 = {tab['4.00'][1]}")
    ck(tab["0.00"][1] == "100.00%", f"n_eff=1 pct gate 0 = {tab['0.00'][1]}")
    ratio = tab["4.00"][0] / tab["0.00"][0]
    ck(abs(ratio - g97["neff"]["ratio"]) < 1e-9, "97's n_eff ratio disagrees")
    # counts below are set from count_s33.py, not guessed; each hit was
    # inspected in context so a duplicated typo cannot pass as a mention.
    has(scope, f"{ratio:.1f}\u00d7", 6, "55.3x")
    has(scope, "55.321", 2, "mean n_eff gate 4")
    has(scope, "38.77%", 2, "n_eff=1 pct")

    # ---- 3. B15, re-derived --------------------------------------------
    v4 = g96["arms"]["4.00"]["V"]
    v0 = g96["arms"]["0.00"]["V"]
    r = v0 / v4
    ck(abs(r - g96["bars"]["B15"]["r"]) < 1e-12, "96's own r disagrees")
    has(scope, f"{r:.4f}", 5, "r = 0.8833")
    has(scope, f"{v4:.5f}", 3, "V(4.00)")
    has(scope, f"{v0:.5f}", 4, "V(0.00)")
    has(scope, f"{100*(1-r):.1f}%", 6, "11.7% lost")
    has(scope, f"{100*r:.1f}%", 4, "88.3% retained")
    ck(g96["bars"]["B15"]["verdict"] == "PARTIAL", "B15 verdict changed")
    has(scope, "B15: PARTIAL", 1, "B15 verdict")
    for gate, amp in (("4.00", 4296), ("2.00", 3899), ("0.7078", 3712),
                      ("0.00", 3716)):
        ck(round(g96["arms"][gate]["amp"]) == amp,
           f"amp gate {gate} = {g96['arms'][gate]['amp']:.1f}, doc says {amp}")
        ck(g96["arms"][gate]["peak_d"] == 25, f"peak_d gate {gate} moved")
    has(scope, "4296", 5, "gate-4 amplitude")

    # ---- 4. controls ----------------------------------------------------
    c = g96["controls"]
    ck(c["all_pass"] is True, "96 controls do not all pass")
    ck(f"{c['C_AFFINE']['max']:.3e}" == "3.664e-15",
       f"C-AFFINE max = {c['C_AFFINE']['max']:.3e}")
    has(scope, m("3.664e-15"), 3, "C-AFFINE float64")
    ck(abs(c["C_DRIFT"]["dDN_pct"] - 2.14) < 1e-9,
       f"C-DRIFT DN = {c['C_DRIFT']['dDN_pct']}")
    ck(abs(c["C_DRIFT"]["dV_pct"]) < 1e-9, "C-DRIFT V moved")
    has(scope, "2.1400%", 2, "raw DN drift")
    has(scope, "0.000000%", 3, "V drift")
    ck(f"{c['C_ROT']['V_rot']:.6f}" == "-0.079502",
       f"C-ROT-A = {c['C_ROT']['V_rot']:.6f}")
    has(scope, m("0.079502"), 4, "C-ROT-A")
    ck(f"{c['C_ROT']['V_shift']:.6f}" == "-0.093960",
       f"C-ROT-C = {c['C_ROT']['V_shift']:.6f}")
    has(scope, m("0.093960"), 2, "C-ROT-C")
    ck(f"{c['C_ROT']['signblind_ratio']:.3f}" == "0.590", "sign-blind ratio")
    has(scope, "0.590", 2, "sign-blind reading")
    ck(round(c["C_ROT"]["rot_max_inner_dn"]) == -150,
       f"rotated inner max = {c['C_ROT']['rot_max_inner_dn']:.1f}")
    ck(c["C_POS"]["monotone"] and c["C_POS"]["calibrated"], "C-POS regressed")
    ck(sum(1 for A, v, p in c["C_POS"]["points"] if abs(v - p) == 0.0) == 3,
       "C-POS: expected exactly 3 levels with 0.00e+00 error")

    # ---- 5. the float32 diagnosis ---------------------------------------
    a = g95["C_AFFINE"]
    ck(f"{a['float32']['max_dV']:.3e}" == "2.451e-07",
       f"float32 err = {a['float32']['max_dV']:.3e}")
    has(scope, m("2.451e-07"), 2, "float32 error")
    ck(f"{a['improvement']:.2e}" == "6.69e+07",
       f"improvement = {a['improvement']:.2e}")
    has(scope, m("6.69e+07"), 2, "accumulator improvement")
    ck(a["verdict"].startswith("ROUND-OFF"), "float32 verdict changed")
    has(scope, "16 777 216", 2, "2^24")
    has(scope, "1.795e+09", 2, "accumulator peak")
    has(scope, f"{63001}".replace("63001", "63 001"), 2, "box sample count")

    # ---- 6. the C-ROT contamination -------------------------------------
    ro = g95["C_ROT"]
    ck(f"{100*ro['overlap_real_band']:.1f}" == "30.7",
       f"overlap = {100*ro['overlap_real_band']:.1f}%")
    has(scope, "30.7%", 2, "ring band overlap")
    ck(f"{100*ro['inside_real_subject']:.1f}" == "23.4",
       f"inside subject = {100*ro['inside_real_subject']:.1f}%")
    has(scope, "23.4%", 1, "inside real subject")

    # ---- 7. B16 / B17 ----------------------------------------------------
    b16 = g97["bars"]["B16"]
    ck(f"{b16['pearson']:.4f}" == "0.1569", f"pearson = {b16['pearson']:.4f}")
    ck(f"{b16['slope']:.4f}" == "0.0186", f"slope = {b16['slope']:.4f}")
    ck(b16["verdict"] == "NOT PROPORTIONAL", "B16 verdict changed")
    ck(b16["n_rings"] == 56, f"B16 rings = {b16['n_rings']}")
    has(scope, "0.1569", 2, "B16 pearson")
    has(scope, "0.0186", 2, "B16 slope")
    has(scope, "56 rings", 1, "B16 ring count")
    ck(abs((1 - r) - 0.1167) < 5e-5, "1 - r no longer 0.1167")
    has(scope, "0.1167", 2, "predicted slope")

    b17 = g97["bars"]["B17"]
    ck(b17["n"] == 27, f"B17 n = {b17['n']}")
    ck(f"{b17['min']:.4f}" == "0.8717", f"B17 min = {b17['min']:.4f}")
    ck(f"{b17['max']:.4f}" == "0.9843", f"B17 max = {b17['max']:.4f}")
    ck(f"{b17['median']:.4f}" == "0.9076", f"B17 median = {b17['median']:.4f}")
    ck(b17["verdict"] == "SOFT", "B17 verdict changed")
    ck(min(b17["all_r"]) > 0.70, "a setting reached the GATE-DEPENDENT branch")
    ck(max(b17["all_r"]) < 1.10, "a setting reached the REVERSED branch")
    has(scope, "0.8717", 2, "B17 min")
    has(scope, "0.9843", 2, "B17 max")
    has(scope, "0.9076", 2, "B17 median")
    has(scope, "27 settings", 2, "B17 sweep size")
    ck(g97["C_SWEEP_NULL"] is True, "C-SWEEP-NULL failed")

    # ---- 8. B18 ----------------------------------------------------------
    b18 = g98["B18"]
    ck(f"{b18['c']:.1f}" == "473.2", f"offset = {b18['c']:.1f}")
    ck(f"{b18['rms_const']:.1f}" == "148.4", f"RMS const = {b18['rms_const']:.1f}")
    ck(f"{b18['rms_prop']:.1f}" == "221.1", f"RMS prop = {b18['rms_prop']:.1f}")
    ck(f"{b18['k']:.4f}" == "0.1398", f"k = {b18['k']:.4f}")
    ck(f"{b18['ratio']:.3f}" == "0.671", f"ratio = {b18['ratio']:.3f}")
    ck(b18["verdict"] == "CONSTANT OFFSET", "B18 verdict changed")
    ck(b18["ratio"] < 0.70, "B18 no longer passes its own bar")
    has(scope, "473.2", 2, "the offset")
    has(scope, "148.4", 2, "RMS const")
    has(scope, "221.1", 2, "RMS prop")
    has(scope, "0.671", 2, "B18 ratio")
    cor = g98["corrected"]
    ck(f"{cor['r_corr']:.4f}" == "0.9958", f"r_corr = {cor['r_corr']:.4f}")
    has(scope, "0.9958", 2, "corrected r")
    ck(round(cor["amp0_corr"]) == 4189, f"corrected peak = {cor['amp0_corr']:.0f}")
    has(scope, "4189", 1, "corrected peak")
    ck(round(cor["offset_share_pct"]) == 96,
       f"offset share = {cor['offset_share_pct']:.1f}%")
    has(scope, "96%", 3, "offset share")
    ck(g98["controls"]["all_pass"] is True, "B18 controls do not all pass")
    ck(g98["controls"]["C_PLANT_CONST"] == "CONSTANT OFFSET",
       "positive plant mislabelled")
    ck(g98["controls"]["C_PLANT_PROP"] == "PROPORTIONAL",
       "positive plant mislabelled")

    # ---- 9. figures 33.7/33.8 cite from earlier sections ----------------
    for s, lbl in (("+100.59%", "P83 oracle alpha"),
                   ("38.000", "observations per band pixel"),
                   ("19.8%", "per-pixel coverage"),
                   ("12.5%", "global coverage"),
                   (m("-11.01%"), "thin quartile"),
                   (m("-32.80%"), "broad quartile"),
                   ("21.78", "the gap"), ("7.3", "null sd"),
                   ("0.1627", "amax thin"), ("0.3444", "amax broad"),
                   ("90.51%", "gate pass rate"),
                   ("+72.9%", "the erasing metric"),
                   ("6316", "tip contrast before"),
                   ("3739", "tip contrast after"),
                   ("33.1%", "tips destroyed"),
                   ("+0.6%", "P24 kernel move")):
        ck(s in sec, f"33.7/33.8 lost {lbl} ({s})")
    for s in ("P83", "P106", "P107", "P108", "P104", "B14"):
        ck(s in sec, f"33.7/33.8 lost the citation {s}")
    ck(m("-28.2%") in sec or m("-28.16%") in sec, "33.7 lost the unmix figure")

    # ---- 10. the claims that must not silently soften -------------------
    for s, lbl in (("NOT an admission artifact", "P128 headline"),
                   ("neither a model failure nor a support failure",
                    "P132 headline"),
                   ("sign-blind", "P130 self-disclosure"),
                   ("CONSTANT OFFSET", "B18 verdict"),
                   ("lower bound", "88.3% framing")):
        ck(s in scope, f"lost: {lbl} ({s!r})")
    ck("1375" in sec, "33.6 lost the resampler-invariance citation")

    print(f"verify_s33: {checks} checks, {len(fails)} failures")
    for f in fails:
        print(f"  FAIL {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
