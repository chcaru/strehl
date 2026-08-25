"""verify_patch.py — re-derive every number in section 5h from raw data.

Same construction as verify_ca.py, which was commissioned against negctl_ca.py
at 13/13:

  * every quantity is RE-DERIVED here from the scorer's JSON or from the raw
    n_eff map, never copied from the report;
  * every claim is located by PROXIMITY on whitespace-collapsed text, because
    the report is wrapped prose and line-anchored checks return false RED;
  * every claim additionally has a REGISTERED OCCURRENCE COUNT, because a
    presence check is satisfied by a duplicate and this report summarises
    itself in section 1 and section 11.

Run:  python experiments/M116-promotion/verify_patch.py
Env:  M116_REPORT, M116_PATCH_OUT  (used by negctl_patch.py to sandbox)
"""
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).resolve().parent
REPORT = Path(os.environ.get(
    "M116_REPORT",
    HERE.parents[1] / "docs" / "research" / "M116-promotion.md"))
OUTDIR = Path(os.environ.get("M116_PATCH_OUT", r"C:\dev\strehl-out\M116\patch"))
MAPS = Path(r"C:\dev\strehl-out\M116\maps")

RAW = REPORT.read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", RAW)

# Registered occurrence counts. A count that changes is a changed claim and
# must be updated deliberately; count_sites.py reports the current values.
SITE_COUNTS = {
    "26.660": 8, "2.911": 5, "0.034": 4, "467.24": 2, "32.78": 2,
    "53.321": 1, "0.00127": 3, "14.3": 5, "116.617": 1, "99.00": 5,
    "36.00": 1, "0.1339": 1, "0.3377": 1, "0.5502": 1, "21.00": 1,
    "0.00738": 4, "0.02029": 1, "2.750": 2, "0.05908": 2, "0.05811": 1,
    "0.983": 4, "0.00380": 2, "0.00499": 1, "0.06323": 1, "0.05786": 1,
    "393.11": 1, "164.53": 1, "1580.66": 1, "1649.91": 1, "0.7932": 1,
    "0.00618": 1, "+0.00358": 1, "+0.00119": 1, "3.000": 2, "0.02026": 4,
    "0.01392": 2, "0.01855": 2, "0.16382": 2, "0.16431": 1, "0.16406": 1,
    "0.00488": 3, "0.00476": 1, "0.687": 1, "0.01733": 1, "-0.01868": 3,
    "-0.02173": 2, "-0.01118": 1, "+0.00733": 1, "0.00132": 1, "66.7": 3,
    "46.2": 3, "557": 1, "154": 1, "28665": 1, "28582": 1, "28133": 1,
    "22219": 1, "22232": 1, "12597": 1, "231.4": 1, "229.2": 1, "129.9": 1,
    "17.049": 1, "17.538": 2, "1.729": 1, "-36.0": 1, "-40.6": 1,
    "+51609.9": 1, "1.029": 1, "808.6": 4, "0.109": 2, "0.101": 2,
    "0.996": 2, "-1.1": 1, "-14.3": 1, "1.669": 1, "1.830": 1, "0.344": 1,
    "0.608": 1,
}

fails, checks = [], 0

_NUMTOK = re.compile(r"^[-+]?[0-9]")


def sites(tok: str) -> int:
    """Boundary-aware occurrence count.

    A plain substring count is wrong for short numeric tokens: '154' matches
    inside '1541' and '0.0154', so a decoy occurs by chance and the registered
    count becomes unmaintainable. Numeric tokens are therefore counted only
    where they are not adjacent to another digit or to a decimal point.
    """
    if not _NUMTOK.match(tok):
        return len(re.findall(re.escape(tok), FLAT))
    before = r"(?<![0-9.])" if tok[0] in "+-" else r"(?<![-+0-9.])"
    return len(re.findall(before + re.escape(tok) + r"(?![0-9])", FLAT))


def bump():
    """Count a data-side guard, which asserts rather than locates a token."""
    global checks
    checks += 1


def check(name, token, anchor, window=900):
    """Token must occur near the anchor phrase, on collapsed text.

    EVERY occurrence of the anchor is searched, not the first. Using find()
    alone silently pins the check to whichever occurrence happens to come
    first in the document, which for a common phrase is not the one the claim
    lives at -- it produced a false RED on '14.3' near 'factor of' on the
    first run of this verifier.
    """
    global checks
    checks += 1
    a = re.sub(r"\s+", " ", anchor)
    idxs = [m.start() for m in re.finditer(re.escape(a), FLAT)]
    if not idxs:
        fails.append(f"{name}: ANCHOR NOT FOUND: {anchor!r}")
        return
    for i in idxs:
        seg = FLAT[max(0, i - window):i + window + len(a)]
        if token in seg:
            return
    fails.append(f"{name}: {token!r} not within {window} chars of any of "
                 f"{len(idxs)} occurrence(s) of {anchor!r}")


def check_exact(name, token, anchor, expected_sites, window=900):
    """As check, plus the registered occurrence count over the whole report."""
    check(name, token, anchor, window)
    global checks
    checks += 1
    got = sites(token)
    if got != expected_sites:
        fails.append(f"{name}: {token!r} occurs {got}x, registered "
                     f"{expected_sites}x")


def num(name, value, places, anchor, window=900, signed=False):
    """Re-derived value must appear at its DISPLAYED precision near anchor."""
    tok = f"{value:+.{places}f}" if signed else f"{value:.{places}f}"
    exp = SITE_COUNTS.get(tok)
    if exp is None:
        fails.append(f"{name}: {tok!r} has no registered site count")
        return
    check_exact(name, tok, anchor, exp, window)


def main():
    k = json.loads((OUTDIR / "scores-patch.json").read_text(encoding="utf-8"))
    f = json.loads((OUTDIR / "scores-patch2.json").read_text(encoding="utf-8"))
    kb = k["subjects"]["bee-3-cpl"]
    fb = f["subjects"]["bee-3-cpl"]

    # ---------- P62: the first plant ----------
    KA0 = kb["arms"]["A0"]["K"]
    KA2 = kb["arms"]["A2"]["K"]
    KM0 = kb["arms"]["M0"]["K"]
    SD0 = kb["arms"]["A0"]["lap_sd"]
    SDM = kb["arms"]["M0"]["lap_sd"]
    a_plant = "`G1` was the plant"
    num("P62 K(A0)", KA0, 3, a_plant)
    num("P62 K(A2)", KA2, 3, a_plant)
    num("P62 K(M0)", KM0, 3, a_plant)
    num("P62 lap_sd(A0)", SD0, 2, a_plant)
    num("P62 lap_sd(M0)", SDM, 2, a_plant)
    num("P62 G1 bar", 2.0 * KA0, 3, a_plant)
    num("P62 sd ratio", SDM / SD0, 1, "in the correct direction")

    if not (KM0 < 2.0 * KA0):
        fails.append("P62: G1 is reported FAILED but the data would PASS it")
    check("P62 verdict", "FAILED, with the sign reversed", a_plant, 1400)

    # ---------- P63: the void headline ----------
    num("P63 ratio", KA2 / KA0, 5, "Had the plant not been registered")
    if KA2 / KA0 >= 0.01:
        fails.append("P63: 99.9 % reduction claim does not follow from the data")
    check("P63 void", "VOID", "Had the plant not been registered", 1200)

    # ---------- P64: n_eff, re-derived from the RAW map ----------
    import tifffile
    n = tifffile.imread(MAPS / "bee-3-cpl__T1-neff.tif")
    n = (n[..., 0] if n.ndim == 3 else n).astype(np.float32)
    a_neff = "the effective number of frames the gate admits"
    num("P64 median", float(np.median(n)), 2, a_neff)
    num("P64 frac<2", float((n < 2).mean()), 4, a_neff)
    num("P64 frac<10", float((n < 10).mean()), 4, a_neff)
    num("P64 frac<50", float((n < 50).mean()), 4, a_neff)
    num("P64 bg", kb["neff_A0"]["bg_median"], 2, a_neff)
    num("P64 detail", kb["neff_A0"]["detail_median"], 2, a_neff)

    # ---------- P66: the second plant ----------
    W = fb["named"]["ROI-W"]["arms"]
    N = fb["named"]["ROI-N"]["arms"]
    a_h1 = "`H1` was the plant"
    num("P66 F4(A0) W", W["A0"]["F4"], 5, a_h1)
    num("P66 F4(M0) W", W["M0"]["F4"], 5, a_h1)
    num("P66 ratio W", W["M0"]["F4"] / W["A0"]["F4"], 3, a_h1)
    num("P66 F4(A0) N", N["A0"]["F4"], 5, a_h1)
    num("P66 F4(M0) N", N["M0"]["F4"], 5, a_h1)
    num("P66 ratio N", N["M0"]["F4"] / N["A0"]["F4"], 3, a_h1)
    if W["M0"]["F4"] / W["A0"]["F4"] < 1.5:
        fails.append("P66: ROI-W is reported PASS but the ratio is below 1.5")
    if N["M0"]["F4"] / N["A0"]["F4"] >= 1.5:
        fails.append("P66: ROI-N is reported FAIL but the ratio clears 1.5")
    check("P66 verdict", "`H1` FAILED as registered", a_h1, 1600)

    # ROI-N span, the "nothing moves" claim
    allf = [v["F4"] for v in N.values()]
    alll = [v["L995"] for v in N.values()]
    a_span = "At ROI-N nothing moves for any arm"
    num("P66 span lo", min(allf), 5, a_span)
    num("P66 span hi", max(allf), 5, a_span)
    num("P66 L995 lo", min(alll), 2, a_span)
    num("P66 L995 hi", max(alll), 2, a_span)

    # ---------- P67: controls exactly quiet ----------
    global checks
    for sname, sub in f["subjects"].items():
        for roi in sub.get("named", {}).values():
            for arm in ("N1", "P1", "T2"):
                checks += 1
                if roi["arms"][arm]["F4"] != roi["arms"]["A0"]["F4"]:
                    fails.append(f"P67: {sname} {arm} F4 differs from A0")
        med = sub["auto"].get("median_F4")
        if med:
            for arm in ("N1", "P1", "T2"):
                checks += 1
                if med[arm] != med["A0"]:
                    fails.append(f"P67: {sname} auto {arm} differs from A0")
    for sname in ("bee-3-cpl", "foam", "tweezers-cpl"):
        ka = k["subjects"][sname]["arms"]
        for arm in ("N1", "P1", "T2"):
            checks += 1
            if ka[arm]["K"] != ka["A0"]["K"]:
                fails.append(f"P67: {sname} {arm} K differs from A0")
    a_ctl = "Not \"within tolerance\""
    num("P67 auto bee", f["subjects"]["bee-3-cpl"]["auto"]["median_F4"]["A0"],
        5, a_ctl)
    num("P67 auto foam", f["subjects"]["foam"]["auto"]["median_F4"]["A0"], 5,
        a_ctl)
    num("P67 auto twz", f["subjects"]["tweezers-cpl"]["auto"]["median_F4"]["A0"],
        5, a_ctl)
    num("P67 K foam", k["subjects"]["foam"]["arms"]["A0"]["K"], 3, a_ctl)

    # ---------- P68: the blur control ----------
    B = fb["named"]["ROI-W"]["blur"]
    a_blur = "At **ROI-W**"
    num("P68 sigma", B["sigma"], 4, a_blur)
    num("P68 F4 blur", B["F4"], 5, a_blur)
    num("P68 gain soft", B["gain_soft"], 5, a_blur, signed=True)
    num("P68 gain blur", B["gain_blur"], 5, a_blur, signed=True)
    num("P68 ratio", B["ratio"], 3, a_blur)
    if B["ratio"] < 2.0:
        fails.append("P68: H5 reported PASS but ratio is below 2.0")
    drop = 100.0 * (1.0 - W["A2"]["L995"] / W["A0"]["L995"])
    checks += 1
    if not (57.5 <= drop < 58.5):
        fails.append(f"P68: L995 drop {drop:.2f} % is not the reported 58 %")

    # ---------- P69: cost, prevalence, H8 ----------
    a_cost = "the detail cost, on the identical oriented-highpass"
    for arm, places in (("A1", 5), ("A2", 5), ("A3", 5), ("A4", 5)):
        v = fb["D"][arm]
        num(f"P69 D {arm} bee", v, places, a_cost, signed=(v > 0))
    num("P69 headroom", 0.02 + fb["D"]["A2"], 5, a_cost)
    if fb["D"]["A3"] >= -0.02:
        fails.append("P69: A3 reported FAIL on the cost bar but it clears -0.02")
    if fb["D"]["A2"] < -0.02:
        fails.append("P69: A2 reported PASS on the cost bar but it fails")

    a_prev = "the prevalence bar, on ROI-AUTO"
    for s, arms_ in (("bee-3-cpl", ("A0", "A2", "M0")),
                     ("foam", ("A0", "A2", "M0")),
                     ("tweezers-cpl", ("A0", "A2"))):
        med = f["subjects"][s]["auto"]["median_F4"]
        for a in arms_:
            num(f"P69 auto {s} {a}", med[a], 5, a_prev)
        checks += 1
        if f["subjects"][s]["auto"]["n_tiles"] < 1:
            fails.append(f"P69: {s} has no ROI-AUTO tiles")
    mb = f["subjects"]["bee-3-cpl"]["auto"]["median_F4"]
    num("P69 auto ratio", mb["A2"] / mb["A0"], 3, a_prev)
    checks += 1
    if not (mb["M0"] < mb["A0"]):
        fails.append("P69: plant is reported not to fire on ROI-AUTO, but it does")

    a_h8 = "`H8` was a registered prediction"
    frac_w = (W["A0"]["F4"] - W["A1"]["F4"]) / (W["A0"]["F4"] - W["A2"]["F4"])
    frac_a = (mb["A0"] - mb["A1"]) / (mb["A0"] - mb["A2"])
    num("P69 H8 W", 100 * frac_w, 1, a_h8)
    num("P69 H8 auto", 100 * frac_a, 1, a_h8)
    num("P69 A1 W", W["A1"]["F4"], 5, a_h8)
    num("P69 A1 auto", mb["A1"], 5, a_h8)

    ew = fb["named"]["ROI-W"]["election_components_A0"]
    en = fb["named"]["ROI-N"]["election_components_A0"]
    check_exact("P69 election W", str(ew), "NOT VERIFIED", SITE_COUNTS[str(ew)])
    check_exact("P69 election N", str(en), "NOT VERIFIED", SITE_COUNTS[str(en)])

    # ---------- P70: verdict integrity ----------
    check("P70 verdict", "NO WORKING INSTRUMENT", "Campaign 5 verdict", 400)
    check("P70 no promo", "No promotion recommendation", "Campaign 5 verdict", 400)
    check("s1 table", "NO INSTRUMENT", "soft gate, re-asked on the", 600)

    # ---------- section 5i: the PIL 16-bit truncation audit ----------
    ap = OUTDIR / "pil16-audit.json"
    if not ap.exists():
        fails.append("5i: pil16-audit.json missing — run pil16_audit.py")
    else:
        pa = json.loads(ap.read_text(encoding="utf-8"))

        # P72: exposure, re-derived from the static scan rather than restated.
        n_open = sum(r["Image.open"] for r in pa["part_a"])
        n_tf = sum(r["tifffile.imread"] for r in pa["part_a"])
        n_pil = sum(1 for r in pa["part_a"] if r["imports_PIL"])
        n_from = sum(r["Image.fromarray"] for r in pa["part_a"]
                     if r["imports_PIL"])
        bump()
        if n_open != 0:
            fails.append(f"P72: report claims zero exposure but the scan "
                         f"found {n_open} Image.open call(s)")
        a72 = "static scan of all"
        check("P72 files", str(len(pa["part_a"])), a72, 400)
        check("P72 open", "**0** calls", a72, 400)
        check("P72 tifffile", f"**{n_tf}** calls", a72, 400)
        check("P72 pil files", f"**{n_pil}** files import PIL", a72, 700)
        check("P72 fromarray", f"make {n_from} `Image.fromarray", a72, 700)
        check("P72 hashes", "raw file bytes", a72, 1800)

        # P73: the level table, re-derived from the audit.
        for r in pa["part_b"]:
            arm = r["arm"]
            num(f"P73 {arm} max", r["tifffile_max"], 0, "mode `RGB`", 900)
            num(f"P73 {arm} levels", r["tifffile_levels"], 0, "mode `RGB`", 900)
            num(f"P73 {arm} loss", r["level_loss_factor"], 1, "mode `RGB`", 900)
            if r["pil_dtype"] != "uint8" or r["pil_mode"] != "RGB":
                fails.append(f"P73 {arm}: the hazard did not reproduce "
                             f"({r['pil_dtype']}, mode {r['pil_mode']})")
            bump()

        # P74: the manufactured-signal result, and its headline consequence.
        kc = pa["part_c"]["kurtosis_G1"]
        a74 = "MANUFACTURES the signal"
        for arm in ("A0", "A2", "M0"):
            num(f"P74 {arm} pilK", kc[arm]["pil_K"], 3, a74, 1400)
            num(f"P74 {arm} chg",
                (kc[arm]["pil_K"] / kc[arm]["true_K"] - 1.0) * 100.0, 1,
                a74, 1400, signed=True)
        r_true = kc["A2"]["true_K"] / kc["A0"]["true_K"]
        r_pil = kc["A2"]["pil_K"] / kc["A0"]["pil_K"]
        num("P74 pil ratio", r_pil, 3, "would have been", 400)
        num("P74 fold", r_pil / r_true, 1, "a factor of", 400)
        bump()
        if not (r_pil > 10.0 * r_true):
            fails.append("P74: claims a change of kind, but the two ratios "
                         "are within a factor of ten")
        bump()
        if kc["A2"]["pil_K"] <= kc["A2"]["true_K"]:
            fails.append("P74: claims truncation MANUFACTURES structure, but "
                         "the treated arm's kurtosis did not rise")

        # P75: the verdict must survive the hazard, checked not asserted.
        g1_pil = kc["M0"]["pil_K"] / kc["A0"]["pil_K"]
        h1_pil = (pa["part_c"]["f4_ROI-N"]["M0"]["pil_F4"] /
                  pa["part_c"]["f4_ROI-N"]["A0"]["pil_F4"])
        num("P75 G1 pil", g1_pil, 3, "robust to the", 1200)
        num("P75 H1 pil", h1_pil, 3, "robust to the", 1200)
        bump()
        if g1_pil >= 2.0 or h1_pil >= 1.5:
            fails.append("P75: claims both plants fail under PIL too, but at "
                         f"least one passes (G1 {g1_pil:.3f}, H1 {h1_pil:.3f})")
        moves = [(v["pil_F4"] / v["true_F4"] - 1.0) * 100.0
                 for roi in ("f4_ROI-W", "f4_ROI-N")
                 for v in pa["part_c"][roi].values() if v["true_F4"]]
        num("P75 F4 least", max(moves), 1, "moves by between", 400, signed=True)
        num("P75 F4 most", min(moves), 1, "moves by between", 400, signed=True)
        num("P75 F4 worst", abs(min(moves)), 1, "at most", 400)
        bump()
        k_moves = [abs(kc[a]["pil_K"] / kc[a]["true_K"] - 1.0) * 100.0
                   for a in kc]
        if abs(min(moves)) >= min(k_moves):
            fails.append("P75: claims F4 is comparatively robust, but its "
                         "worst move is not smaller than K's smallest")

        # P76: the post-hoc probe is reported as failed, in both directions.
        d = {(r["arm"], r["roi"]): r for r in pa["part_d"]}
        a76 = "FAILED IN MY FAVOUR"
        for roi in ("ROI-W", "ROI-N"):
            lev = d[("A0", roi)]["levels"] / d[("M0", roi)]["levels"]
            flt = d[("M0", roi)]["flat_frac"] / d[("A0", roi)]["flat_frac"]
            num(f"P76 lev {roi}", lev, 3, a76, 1800)
            num(f"P76 flat {roi}", flt, 3, a76, 1800)
            bump()
            if lev <= 1.0 or flt >= 1.0:
                fails.append(f"P76 {roi}: the report describes the two probes "
                             "as pointing in opposite directions; the data "
                             "no longer does")
        check("P76 unusable", "Neither number is usable", a76, 1800)
        check("P76 picture", "rest on the picture", a76, 2200)

    print(f"checks: {checks}")
    if fails:
        print(f"\nRED — {len(fails)} failure(s):")
        for x in fails:
            print(f"  {x}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
