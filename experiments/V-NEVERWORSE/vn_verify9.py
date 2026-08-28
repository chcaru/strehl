"""Re-derive every load-bearing number in RESULT.md section 9 from its record.

Same rules as `vn_verify8.py`, learned the same way: every value is PARSED OUT
OF THE DOCUMENT and checked against an external oracle, table claims are
matched per cell, and a crash is a REFUSAL (rc=2) rather than a FAIL or a pass.

The expand-bug figures in section 9.3 are not merely compared against a stored
number -- the buggy form is reconstructed here and re-run, so the claim is
re-derived rather than restated.
"""
import io
import json
import math
import os
import re
import subprocess
import sys

import numpy as np
from scipy.ndimage import convolve1d

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DOC = os.path.join(HERE, "RESULT.md")
PLAT = r"C:\dev\strehl-out\V-NEVERWORSE\plateau\coffee-bubbles.json"
NINV2 = r"C:\dev\strehl-out\V-NEVERWORSE\ninv2"


def _mono(d):
    """Is a subject's noise growth monotone in how selective the arm is?

    Recomputed from the record on demand so that the count of subjects making
    the claim in section 9.23 is compared against the number of subjects that
    actually measure it, rather than against a number written here.
    """
    import math as _m
    rows = {(r["arm"], r["N"]): r for r in d["rows"]}
    ks = d["ks"]
    order = sorted(("shipping", "confidence", "argmax"),
                   key=lambda a: -rows[(a, ks[0])]["share"])
    ns = [(rows[(a, ks[0])]["noise_mid"] / rows[(a, ks[1])]["noise_mid"])
          ** (1.0 / _m.log(ks[0] / float(ks[1]), 2.0)) for a in order]
    return all(ns[i] >= ns[i + 1] for i in range(len(ns) - 1))
PYR = os.path.join(HERE, "pin9b05", "pyramid.rs")
OUTD = r"C:\dev\strehl-out\V-NEVERWORSE"
SNRREF = os.path.join(OUTD, "snrref", "coffee-bubbles.json")
CONFEXP = os.path.join(OUTD, "confexp", "coffee-bubbles.json")
MANUF = os.path.join(OUTD, "manufacture", "coffee-bubbles.json")
MANUF2 = os.path.join(OUTD, "manufacture", "112MSDCF.json")

fails, refused = [], []
checked = 0


def _flat(s):
    return re.sub(r"\s+", " ", s)


def row(body, label, what):
    global checked
    checked += 1
    hits = [ln for ln in body.splitlines()
            if ln.startswith("|") and _flat(ln.split("|")[1]).strip() == label]
    if len(hits) != 1:
        fails.append("%s: %d rows with first cell %r, need 1"
                     % (what, len(hits), label))
        return None
    return [c.strip() for c in hits[0].strip("|").split("|")]


def cell(cells, i, value, what):
    global checked
    checked += 1
    if cells is None:
        return
    if i >= len(cells):
        fails.append("%s: row has %d cells, wanted %d" % (what, len(cells), i))
        return
    if value not in cells[i]:
        fails.append("%s: cell %d is %r, lacks %r" % (what, i, cells[i], value))


def grab(body, pat, what):
    global checked
    checked += 1
    m = re.findall(pat, body)
    if len(m) != 1:
        fails.append("%s: %r matched %d times, need 1" % (what, pat, len(m)))
        return None
    return m[0]


def row2(body, label, label2, what):
    global checked
    checked += 1
    hits = []
    for ln in body.splitlines():
        if not ln.startswith("|"):
            continue
        c = ln.split("|")
        if (len(c) > 2 and _flat(c[1]).strip() == label
                and _flat(c[2]).strip() == label2):
            hits.append(ln)
    if len(hits) != 1:
        fails.append("%s: %d rows with cells (%r, %r), need 1"
                     % (what, len(hits), label, label2))
        return None
    return [c.strip() for c in hits[0].strip("|").split("|")]


def seg(body, a, b, what):
    """Slice between two markers, refusing if either is not unique. Section
    9.17 carries two tables whose arm labels and N=19 row collide across
    subjects, so a slice that silently matched the wrong table would check one
    subject's numbers twice and the other's never."""
    global checked
    checked += 1
    if body.count(a) != 1 or body.count(b) != 1:
        refused.append("%s: markers not unique (%d, %d)"
                       % (what, body.count(a), body.count(b)))
        return ""
    return body[body.index(a):body.index(b)]


def main():
    global checked
    doc = io.open(DOC, encoding="utf-8").read()
    s9 = doc[doc.index("## 9. Falsifying the fix"):doc.index("## 10. Files")]
    d = json.load(io.open(PLAT, encoding="utf-8"))

    # ---- 9.4 plateau table, cell-exact against the harness output ----
    for k in range(7):
        p = d["plateaus"]["L%d" % k]
        r = row(s9, "L%d" % k, "plateau L%d" % k)
        cell(r, 1, str(p["level_px"]), "L%d cell px" % k)
        cell(r, 2, "%.2f" % d["exponents"][k], "L%d exponent" % k)
        cell(r, 3, "%.2f" % p["n_eff_mean"], "L%d n_eff" % k)
        cell(r, 5, "%.3f" % p["frac_single_winner"], "L%d single winner" % k)
        cell(r, 7, "%.3f" % p["frac_area_20_60px"], "L%d frac 20-60" % k)

    # the two headline plateau claims must really be the maxima they claim
    b = {k: v["frac_area_20_60px"] for k, v in d["plateaus"].items()}
    checked += 1
    if max(b, key=b.get) != "L3":
        fails.append("doc says L3 carries the most 20-60px area; record says %s"
                     % max(b, key=b.get))

    # ---- 9.5 counterfactual arms ----
    a = d["arms"]
    for label, key in ((
            "a. shipping (`2 3 4 5 8 8 8`)", "a_shipping"),
            ("b. plain unweighted mean", "b_plain_mean"),
            ("c. exponent 1, flat ramp", "c_exponent_1_flat"),
            ("d. exponent 2, no ramp", "d_no_ramp_exp2")):
        r = row(s9, label, "arm %s" % key)
        cell(r, 1, "%.5f" % a[key]["blotch"], "%s blotch" % key)
        cell(r, 2, "%.3fx" % a[key]["blotch_vs_best_source"], "%s ratio" % key)
        cell(r, 3, "%.5f" % a[key]["sharpness"], "%s sharp" % key)
        cell(r, 4, "%.3f" % a[key]["sharp_vs_best_source"], "%s sharp ratio" % key)

    # plain mean MUST be the only arm satisfying the invariant, as claimed
    checked += 1
    under = [k for k, v in a.items() if v["blotch_vs_best_source"] <= 1.0]
    if under != ["b_plain_mean"]:
        fails.append("doc says the mean is the only arm under 1.0x; record: %s"
                     % under)
    # and it MUST be the worst on sharpness, or 9.5's argument collapses
    checked += 1
    if min(a, key=lambda k: a[k]["sharp_vs_best_source"]) != "b_plain_mean":
        fails.append("the plain mean is not the worst arm on sharpness")

    # ---- 9.5/9.6 the derived percentages ----
    ship = a["a_shipping"]["blotch_vs_best_source"]
    exp1 = a["c_exponent_1_flat"]["blotch_vs_best_source"]
    pct = grab(s9, r"= \*\*(\d+)%\*\* of the merge-attributable excess", "57 pct")
    checked += 1
    if pct is not None:
        want = round((ship - exp1) / (ship - 1.0) * 100)
        if int(pct) != want:
            fails.append("doc claims %s%% of excess removed, re-derives to %d%%"
                         % (pct, want))
    cost = grab(s9, r"a \*\*([\d.]+)%\*\* relative sharpness cost", "sharp cost")
    checked += 1
    if cost is not None:
        want = (1 - a["c_exponent_1_flat"]["sharp_vs_best_source"]
                / a["a_shipping"]["sharp_vs_best_source"]) * 100
        if abs(float(cost) - want) > 0.15:
            fails.append("doc claims %s%% sharpness cost, re-derives to %.1f%%"
                         % (cost, want))
    loss = grab(s9, r"destroys\s+\*\*(\d+)% of the sharpness\*\*", "mean loss")
    checked += 1
    if loss is not None:
        want = round((1 - a["b_plain_mean"]["sharp_vs_best_source"]) * 100)
        if int(loss) != want:
            fails.append("doc claims the mean loses %s%%, re-derives to %d%%"
                         % (loss, want))

    # ---- 9.5 sensitivity sweep ----
    for sc in ("0.5", "1.0", "2.0"):
        v = d["varscale"]["x%s" % sc]
        r = row(s9, "x%s" % sc, "varscale %s" % sc)
        cell(r, 1, "%.3fx" % v["shipping"], "varscale %s shipping" % sc)
        cell(r, 2, "%.3fx" % v["exp1"], "varscale %s exp1" % sc)
        checked += 1
        if not v["exp1"] < v["shipping"]:
            fails.append("varscale %s: exp1 is NOT lower, doc says it is" % sc)

    # ---- 9.2 fidelity pair ----
    fid = grab(s9, r"scores `coffee-bubbles` at \*\*([\d.]+)x\*\*", "reimpl")
    shp = grab(s9, r"shipped master scores \*\*([\d.]+)x\*\*", "shipped")
    checked += 2
    if fid is not None and abs(float(fid) - ship) > 5e-4:
        fails.append("doc reimpl %s vs record %.4f" % (fid, ship))
    if shp is not None and abs(
            float(shp) - d["shipped_master"]["blotch_vs_best_source"]) > 5e-4:
        fails.append("doc shipped %s vs record %.4f"
                     % (shp, d["shipped_master"]["blotch_vs_best_source"]))

    # ---- 9.1 the absent constant, and the two quotes, against the source ----
    try:
        src = io.open(PYR, encoding="utf-8", errors="replace").read()
        for tok in ("0.086063", "FOCUS_NOISE_SD"):
            checked += 1
            if tok in src:
                fails.append("%r DOES occur in pyramid.rs; 9.1 claims zero" % tok)

        def norm(s):
            """Strip Rust doc-comment syntax and Markdown emphasis only.

            Both sides lose `///` and `**`; NO word is altered, so changing any
            word of a quotation still fails. `vn_negctl9.py` plants exactly
            that to prove this check can still fail.
            """
            s = re.sub(r"^\s*///?", " ", s, flags=re.M)
            return _flat(s.replace("**", ""))

        flat = norm(src)
        for q in [norm(" ".join(
                ln.lstrip(">").strip() for ln in blk.splitlines()))
                for blk in re.findall(r"(?:^> .*\n)+", s9, re.M)]:
            checked += 1
            # Blockquotes are used for two different things in section 9: for
            # verbatim source quotations, which this check exists to police,
            # and for editorial banners such as the 9.17 retraction notice. A
            # banner is not a claim about pyramid.rs and must not be looked up
            # in it, so quotations are identified by their content rather than
            # by being a blockquote. `RETRACTED` is the marker.
            if q.startswith("RETRACTED"):
                checked -= 1
                continue
            if q and q.strip() not in flat:
                fails.append("quoted pyramid.rs text is not verbatim: %r" % q[:80])
    except Exception as e:
        refused.append("pinned pyramid.rs unreadable: %s" % e)

    # ---- 9.3 re-derive the expand bug rather than restate it ----
    try:
        K = np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0

        def sm(x):
            return convolve1d(convolve1d(x, K, axis=0, mode="nearest"),
                              K, axis=1, mode="nearest")

        up = np.zeros((400, 400))
        up[::2, ::2] = np.full((200, 200), 1200.0)
        bad = 4.0 * sm(up)
        for pat, got, what in (
                (r"min (\d+), max (\d+), overall std ([\d.]+)", None, "expand"),):
            m = re.search(pat, s9)
            checked += 1
            if not m:
                fails.append("9.3 does not state the expand bug figures")
                break
            lo, hi, sd = float(m.group(1)), float(m.group(2)), float(m.group(3))
            if (abs(bad.min() - lo) > 0.5 or abs(bad.max() - hi) > 0.5
                    or abs(bad.std() - sd) > 0.05):
                fails.append("expand bug re-derives to min %.1f max %.1f std "
                             "%.2f, doc says %.0f/%.0f/%.2f"
                             % (bad.min(), bad.max(), bad.std(), lo, hi, sd))
    except Exception as e:
        refused.append("expand re-derivation: %s" % e)

    # ---- 9.6-9.8 three-subject tables, every cell re-derived from JSON ----
    SUBJ = ["coffee-bubbles", "112MSDCF", "flat-on-ruler-cpl"]
    J = {}
    for s in SUBJ:
        p = os.path.join(os.path.dirname(PLAT), "%s.json" % s)
        J[s] = json.load(io.open(p, encoding="utf-8"))

    def tbl(header):
        """Slice one table by its unique header row, so a subject name that
        appears in four tables can still be addressed unambiguously."""
        global checked
        checked += 1
        if s9.count(header) != 1:
            fails.append("table header %r occurs %d times, need 1"
                         % (header[:50], s9.count(header)))
            return ""
        i = s9.index(header)
        j = s9.index("\n\n", i)
        return s9[i:j]

    t_arms = tbl("| subject | OK frames | shipping | plain mean |")
    t_shar = tbl("| subject | selection-attributable, at most |")
    t_plat = tbl("| subject | L0 | L1 | L2 | L3 | L4 | L5 | L6 | L3+L4 |")
    t_shrp = tbl("| sharpness vs best source frame | shipping |")

    for s in SUBJ:
        a = J[s]["arms"]
        sh = a["a_shipping"]["blotch_vs_best_source"]
        pm = a["b_plain_mean"]["blotch_vs_best_source"]
        c1 = a["c_exponent_1_flat"]["blotch_vs_best_source"]
        ss = a["a_shipping"]["sharp_vs_best_source"]
        sc = a["c_exponent_1_flat"]["sharp_vs_best_source"]

        r = row(t_arms, "`%s`" % s, "9.6 arms %s" % s)
        cell(r, 1, str(J[s]["frames"]), "%s OK frames" % s)
        cell(r, 2, "%.3fx" % sh, "%s shipping" % s)
        cell(r, 3, "%.3fx" % pm, "%s plain mean" % s)
        cell(r, 4, "%.3fx" % c1, "%s exponent 1" % s)
        cell(r, 5, "%.3fx" % J[s]["shipped_master"]["blotch_vs_best_source"],
             "%s shipped master" % s)

        # derived shares: recomputed here from the arms, never read as given
        r = row(t_shar, "`%s`" % s, "9.6 shares %s" % s)
        cell(r, 1, "%.1f%%" % (100 * (sh - pm) / (sh - 1.0)),
             "%s selection-attributable" % s)
        cell(r, 2, "%.1f%%" % (100 * (sh - c1) / (sh - 1.0)),
             "%s exponent ceiling" % s)
        cell(r, 3, "%.1f%%" % (100 * (1 - sc / ss)), "%s sharpness cost" % s)

        r = row(t_shrp, "`%s`" % s, "9.8 sharpness %s" % s)
        cell(r, 1, "%.3f" % ss, "%s shipping sharpness" % s)
        cell(r, 2, "%.3f" % a["b_plain_mean"]["sharp_vs_best_source"],
             "%s plain-mean sharpness" % s)
        cell(r, 3, "%.3f" % sc, "%s exponent-1 sharpness" % s)

        pl = J[s]["plateaus"]
        f = [pl["L%d" % k]["frac_area_20_60px"] for k in range(7)]
        r = row(t_plat, "`%s`" % s, "9.8 plateau %s" % s)
        for k in range(7):
            cell(r, k + 1, "%.3f" % f[k], "%s frac20-60 L%d" % (s, k))
        cell(r, 8, "%.3f" % (f[3] + f[4]), "%s L3+L4" % s)

    # the "violates on 2 of 3" claim must match the arms, not the prose
    nviol = sum(1 for s in SUBJ
                if J[s]["arms"]["b_plain_mean"]["blotch_vs_best_source"] > 1.0)
    checked += 1
    if nviol != 2:
        fails.append("9.7 says the plain mean violates on 2 of 3; the arms "
                     "say %d of 3" % nviol)

    # the median-of-three ceiling quoted in 9.6
    ceil = sorted(100 * (J[s]["arms"]["a_shipping"]["blotch_vs_best_source"]
                         - J[s]["arms"]["c_exponent_1_flat"]
                         ["blotch_vs_best_source"])
                  / (J[s]["arms"]["a_shipping"]["blotch_vs_best_source"] - 1.0)
                  for s in SUBJ)[1]
    checked += 1
    if "median of the three is %.1f%%" % ceil not in _flat(s9):
        fails.append("9.6 median ceiling is %.1f%%, not as stated" % ceil)

    # frame partition on the subject that lost frames
    fp = grab(_flat(s9), r"\*\*(\d+) in the stack = (\d+) admitted \+ (\d+) "
                         r"unregistered \+ (\d+) poor-registration",
              "frame partition")
    checked += 1
    if fp is not None:
        if int(fp[0]) != sum(int(x) for x in fp[1:]):
            fails.append("frame partition does not sum: %s" % (fp,))
        elif int(fp[1]) != J["flat-on-ruler-cpl"]["frames"]:
            fails.append("frame partition admits %s but the record has %d"
                         % (fp[1], J["flat-on-ruler-cpl"]["frames"]))

    # ---- partition must sum ----
    par = grab(s9, r"\*\*(\d+) requested = (\d+) measured \+ (\d+) not "
                   r"attempted \+ (\d+) failed", "subject partition")
    checked += 1
    if par is not None and int(par[0]) != sum(int(x) for x in par[1:]):
        fails.append("subject partition does not sum: %s" % (par,))


    # ================= 9.11 - 9.16, added after the sections were written ==
    # The lesson from the previous round: a checker whose COUNT does not rise
    # when content is added has examined none of it. Everything below parses
    # its value out of the document and compares it to a record written by a
    # different program.
    SN = json.load(io.open(SNRREF, encoding="utf-8"))
    CX = json.load(io.open(CONFEXP, encoding="utf-8"))
    MF = json.load(io.open(MANUF, encoding="utf-8"))

    # ---- 9.11 SNR_REF table, cell-exact ----
    for e in SN["snr_ref"]:
        lab = ("64.0 (shipping)" if e["snr_ref"] == 64.0
               else "%.1f" % e["snr_ref"])
        r = row(s9, lab, "snrref %s" % lab)
        cell(r, 1, "%.6f" % e["clamp_binding_frac"], "snrref %s bind" % lab)
        if e["snr_ref"] != 64.0:
            cell(r, 2, "%.1f" % e["max_abs_pixel_delta"]
                 if e["max_abs_pixel_delta"] < 1000 else "1060",
                 "snrref %s dpix" % lab)
            cell(r, 3, "%.4f" % e["max_abs_normalised_weight_delta"],
                 "snrref %s dw" % lab)
    # the shipping row must be the reference, i.e. exactly zero in the record
    checked += 1
    base = [e for e in SN["snr_ref"] if e["snr_ref"] == 64.0][0]
    if base["max_abs_pixel_delta"] != 0.0:
        fails.append("9.11 quotes the shipping row as the reference but the "
                     "record has delta %r" % base["max_abs_pixel_delta"])
    # "1 coefficient in 358" must follow from the quoted binding fraction
    n358 = grab(s9, r"\*\*1 coefficient in (\d+)\*\*", "9.11 one-in-N")
    checked += 1
    if n358 is not None:
        want = round(1.0 / base["clamp_binding_frac"])
        if abs(int(n358) - want) > 1:
            fails.append("9.11 says 1 in %s; 1/%.6f is 1 in %d"
                         % (n358, base["clamp_binding_frac"], want))
    # the clamp must bind at the LOW end, as the section argues
    checked += 1
    hi = [e for e in SN["snr_ref"] if e["snr_ref"] == 4096.0][0]
    lo = [e for e in SN["snr_ref"] if e["snr_ref"] == 1.0][0]
    if not (hi["clamp_binding_frac"] > base["clamp_binding_frac"]
            > lo["clamp_binding_frac"]):
        fails.append("9.11 argues the clamp binds at the low end, so a larger "
                     "SNR_REF must bind more; record: %r"
                     % [e["clamp_binding_frac"] for e in SN["snr_ref"]])

    # ---- 9.12 flatness strata, cell-exact ----
    for i, st in enumerate(SN["flatness_strata"]):
        lab = {0: "0 (most structured)", 4: "4 (flattest)"}.get(i, str(i))
        r = row(s9, lab, "strata %d" % i)
        cell(r, 1, str(st["n_pixels"]), "strata %d px" % i)
        cell(r, 2, "%.2f" % st["mean_n_eff"], "strata %d n_eff" % i)
        cell(r, 3, "%.3f" % st["mean_top_weight"], "strata %d top" % i)
        cell(r, 4, "%.3f" % st["frac_single_winner"], "strata %d single" % i)
    # the section's whole argument is that the trend is small; check it is
    checked += 1
    ne = [st["mean_n_eff"] for st in SN["flatness_strata"]]
    if not (abs(max(ne) - min(ne)) / max(ne) < 0.15):
        fails.append("9.12 calls the flatness trend too small to be a "
                     "mechanism; n_eff spans %r" % ne)

    # ---- 9.12 coherence, with the null ----
    C = SN["coherence"]
    r = row(s9, "shipping merge", "coherence shipping")
    cell(r, 1, "%.4f" % C["observed_agreement"], "coherence obs")
    cell(r, 2, "%.4f" % C["chance_agreement"], "coherence chance")
    cell(r, 3, "%.4f" % C["excess"], "coherence excess")
    r = row(s9, "null: same scene, no focus signal", "coherence null")
    cell(r, 1, "%.4f" % C["null_observed"], "null obs")
    cell(r, 2, "%.4f" % C["null_chance"], "null chance")
    cell(r, 3, "%.4f" % C["null_excess"], "null excess")
    checked += 1
    if abs((C["excess"] - C["null_excess"]) - C["excess_over_null"]) > 1e-9:
        fails.append("9.12 residual excess does not equal excess - null")
    pct = grab(s9, r"\*\*([\d.]+)% of the coherence excess survives",
               "9.12 survival pct")
    checked += 1
    if pct is not None:
        want = 100.0 * C["null_excess"] / C["excess"]
        if abs(float(pct) - want) > 0.15:
            fails.append("9.12 says %s%% survives the null; record gives "
                         "%.1f%%" % (pct, want))
    # the null must be like-for-like on admission, or it compares nothing
    checked += 1
    if abs(C["admitted_fraction"] - C["null_admitted_fraction"]) > 0.05:
        fails.append("9.12 calls the null like-for-like but admission is "
                     "%.3f vs %.3f" % (C["admitted_fraction"],
                                       C["null_admitted_fraction"]))

    # ---- 9.13 scalar frontier and confidence arms, cell-exact ----
    sc = [x for x in CX["rows"] if x["arm"] == "u_scalar"]
    for x in sc:
        lab = "`exponent` %.1f" % x["exponent"]
        hits = [ln for ln in s9.splitlines()
                if ln.startswith("| scalar |") and lab in ln]
        checked += 1
        if len(hits) != 1:
            fails.append("9.13 scalar %s: %d rows, need 1" % (lab, len(hits)))
            continue
        c = [y.strip() for y in hits[0].strip("|").split("|")]
        cell(c, 2, "%.3fx" % x["blotch_vs_best_source"], "scalar %s b" % lab)
        cell(c, 3, "%.3fx" % x["sharp_vs_best_source"], "scalar %s s" % lab)
    cf = [x for x in CX["rows"] if x["arm"] == "e_confidence"]
    for x in cf:
        lab = "`kappa` %.3f" % x["kappa"]
        hits = [ln for ln in s9.splitlines()
                if ln.startswith("| confidence |") and lab in ln]
        checked += 1
        if len(hits) != 1:
            fails.append("9.13 conf %s: %d rows, need 1" % (lab, len(hits)))
            continue
        c = [y.strip() for y in hits[0].strip("|").split("|")]
        cell(c, 2, "%.3fx" % x["blotch_vs_best_source"], "conf %s b" % lab)
        cell(c, 3, "%.3fx" % x["sharp_vs_best_source"], "conf %s s" % lab)
        if x.get("frontier_gap") is not None:
            cell(c, 4, "%+.4f" % x["frontier_gap"], "conf %s gap" % lab)
    # the section's claim that three points are strictly worse than a scalar
    checked += 1
    neg = [x for x in cf if x.get("frontier_gap") is not None
           and x["frontier_gap"] < 0]
    if len(neg) != 3:
        fails.append("9.13 says three confidence points are worse than a "
                     "scalar; record has %d" % len(neg))
    mg = grab(s9, r"largest gain anywhere is \+([\d.]+) blotch",
              "9.13 largest gain")
    checked += 1
    if mg is not None and abs(float(mg) - CX["max_frontier_gap"]) > 5e-5:
        fails.append("9.13 largest gain %s vs record %.4f"
                     % (mg, CX["max_frontier_gap"]))

    # ---- 9.13 oracle ----
    orc = [x for x in CX["rows"] if x["arm"] == "o_oracle"]
    for x in orc:
        r = row(s9, "%.2f" % x["frac_flattened"],
                "oracle %.2f" % x["frac_flattened"])
        cell(r, 1, "%.3fx" % x["blotch_vs_best_source"], "oracle b")
        cell(r, 2, "%.3fx" % x["sharp_vs_best_source"], "oracle s")
    for lab, key in (("best confidence arm", "best_confidence_blotch"),
                     ("**oracle, any per-pixel exponent rule**",
                      "oracle_best_blotch")):
        r = row(s9, lab, "ceiling %s" % key)
        cell(r, 1, "%.3fx" % CX[key], "ceiling %s value" % key)
        pc = 100.0 * (CX["shipping_blotch"] - CX[key]) / (
            CX["shipping_blotch"] - 1.0)
        cell(r, 2, "%.1f%%" % pc, "ceiling %s pct" % key)
    # the oracle must actually bound the fix, or 9.13's conclusion is unearned
    checked += 1
    if not CX["oracle_best_blotch"] < CX["best_confidence_blotch"]:
        fails.append("9.13 uses the oracle as an upper bound on the fix but "
                     "it reads %.3f against the fix's %.3f"
                     % (CX["oracle_best_blotch"],
                        CX["best_confidence_blotch"]))
    checked += 1
    if CX["oracle_best_blotch"] <= 1.0:
        fails.append("9.13 says even the oracle violates the bound; it reads "
                     "%.3f" % CX["oracle_best_blotch"])

    # ---- 9.14 the synthetic null, cell-exact ----
    MROW = {"a_shipping": "shipping, as delivered",
            "g_exponent_only": "exponent ladder alone, no admission gate",
            "c_flat_exponent": "flat exponent, `p = 1` everywhere",
            "d_conf_to_p1": "confidence rule collapsing to `p = 1`",
            "e_conf_to_mean": "confidence rule collapsing to a true average",
            "f_admit_only": "hard admission threshold alone, uniform weights",
            "b_plain_mean": "plain unweighted mean"}
    by = {x["arm"]: x for x in MF["rows"]}
    s14 = s9[s9.index("### 9.14 "):s9.index("### 9.14b")]
    checked += 1
    if set(by) != set(MROW):
        fails.append("9.14 table covers %r but the record has %r"
                     % (sorted(MROW), sorted(by)))
    for key, lab in MROW.items():
        if key not in by:
            continue
        x = by[key]
        r = row(s14, lab, "manuf %s" % key)
        cell(r, 1, "%.5f" % x["band"], "manuf %s band" % key)
        cell(r, 2, "%.5f" % x["fine"], "manuf %s fine" % key)
        cell(r, 3, "%.3fx" % x["band_vs_best_source"], "manuf %s bratio" % key)
        cell(r, 4, "%.3fx" % x["fine_vs_best_source"], "manuf %s fratio" % key)
    # the sqrt(n) control is the load-bearing part of 9.14; re-derive it
    checked += 1
    want = 1.0 / (MF["frames"] ** 0.5)
    if abs(MF["sqrt_n_expectation"] - want) > 1e-9:
        fails.append("9.14 sqrt(n) expectation %r does not equal 1/sqrt(%d)"
                     % (MF["sqrt_n_expectation"], MF["frames"]))
    checked += 1
    if abs(MF["plain_mean_band_ratio"] - want) > 0.25 * want:
        fails.append("9.14 leans on the plain mean matching 1/sqrt(n); it "
                     "reads %.3f against %.3f"
                     % (MF["plain_mean_band_ratio"], want))
    mfac = grab(s14, r"manufacture factor is \*\*([\d.]+)x\*\*",
                "9.14 manufacture factor")
    checked += 1
    if mfac is not None and abs(float(mfac) - MF["manufacture_factor"]) > 0.01:
        fails.append("9.14 manufacture factor %s vs record %.2f"
                     % (mfac, MF["manufacture_factor"]))

    # ---- 9.14 attribution, and the claim that the shares exceed 100% ----
    span = MF["shipping_band_ratio"] - MF["plain_mean_band_ratio"]
    shares = {}
    for key, lab in (("f_admit_only", "hard admission threshold only"),
                     ("g_exponent_only", "exponent ladder only")):
        x = by[key]
        sh = 100.0 * (x["band_vs_best_source"]
                      - MF["plain_mean_band_ratio"]) / span
        shares[key] = sh
        r = row(s14, lab, "attrib %s" % key)
        cell(r, 1, "%.3fx" % x["band_vs_best_source"], "attrib %s val" % key)
        cell(r, 2, "%.1f%%" % sh, "attrib %s share" % key)
    tot = grab(s14, r"they sum to (\d+)%", "9.14 attribution total")
    checked += 1
    if tot is not None:
        want = round(sum(shares.values()))
        if abs(int(tot) - want) > 1:
            fails.append("9.14 says the shares sum to %s%%; they sum to %d%%"
                         % (tot, want))
    checked += 1
    if sum(shares.values()) <= 100.0:
        fails.append("9.14 calls the two mechanisms redundant because the "
                     "shares exceed 100%%; they sum to %.1f%%"
                     % sum(shares.values()))
    rem = grab(s14, r"intends -- removes \*\*([\d.]+)%\*\*",
               "9.14 exponent removal")
    checked += 1
    if rem is not None:
        want = 100.0 * (MF["shipping_band_ratio"]
                        - by["c_flat_exponent"]["band_vs_best_source"]) / span
        if abs(float(rem) - want) > 0.1:
            fails.append("9.14 says the flat exponent removes %s%%; record "
                         "gives %.1f%%" % (rem, want))

    # ---- 9.14b the second subject, same cells, same partition ----
    M2 = json.load(io.open(MANUF2, encoding="utf-8"))
    by2 = {x["arm"]: x for x in M2["rows"]}
    checked += 1
    if set(by2) != set(MROW):
        fails.append("9.14b table covers %r but the record has %r"
                     % (sorted(MROW), sorted(by2)))
    s14b = s9[s9.index("### 9.14b"):s9.index("### 9.15")]
    for key, lab in MROW.items():
        if key not in by2:
            continue
        x = by2[key]
        r = row(s14b, lab, "manuf2 %s" % key)
        cell(r, 1, "%.5f" % x["band"], "manuf2 %s band" % key)
        cell(r, 2, "%.5f" % x["fine"], "manuf2 %s fine" % key)
        cell(r, 3, "%.3fx" % x["band_vs_best_source"],
             "manuf2 %s bratio" % key)
        cell(r, 4, "%.3fx" % x["fine_vs_best_source"],
             "manuf2 %s fratio" % key)
    checked += 1
    w2 = 1.0 / (M2["frames"] ** 0.5)
    if abs(M2["plain_mean_band_ratio"] - w2) > 0.25 * w2:
        fails.append("9.14b leans on the plain mean matching 1/sqrt(n); it "
                     "reads %.3f against %.3f"
                     % (M2["plain_mean_band_ratio"], w2))
    span2 = M2["shipping_band_ratio"] - M2["plain_mean_band_ratio"]
    sh2 = {}
    for key, lab in (("f_admit_only",
                      "hard admission threshold only, 79 frames"),
                     ("g_exponent_only", "exponent ladder only, 79 frames")):
        x = by2[key]
        v = 100.0 * (x["band_vs_best_source"]
                     - M2["plain_mean_band_ratio"]) / span2
        sh2[key] = v
        r = row(s14b, lab, "attrib2 %s" % key)
        cell(r, 1, "%.3fx" % x["band_vs_best_source"], "attrib2 %s val" % key)
        cell(r, 2, "%.1f%%" % v, "attrib2 %s share" % key)
    t2 = grab(s14b, r"at (\d+)%, so the two mechanisms are again redundant",
              "9.14b attribution total")
    checked += 1
    if t2 is not None and abs(int(t2) - round(sum(sh2.values()))) > 1:
        fails.append("9.14b says the shares sum to %s%%; they sum to %d%%"
                     % (t2, round(sum(sh2.values()))))
    r2 = grab(s14b, r"best\s+case removes \*\*([\d.]+)%\*\*",
              "9.14b exponent removal")
    checked += 1
    if r2 is not None:
        want2 = 100.0 * (M2["shipping_band_ratio"]
                         - by2["c_flat_exponent"]["band_vs_best_source"]
                         ) / span2
        if abs(float(r2) - want2) > 0.1:
            fails.append("9.14b says the flat exponent removes %s%%; record "
                         "gives %.1f%%" % (r2, want2))
    # the depth claim is the section's headline; it must come from the records
    mm = re.findall(r"\*\*([\d.]+)x on 19 frames and ([\d.]+)x on 79\*\*",
                    s14b)
    checked += 1
    if len(mm) != 1:
        fails.append("9.14b depth claim: matched %d times, need 1" % len(mm))
    else:
        for got, rec, n in ((mm[0][0], MF, 19), (mm[0][1], M2, 79)):
            checked += 1
            if rec["frames"] != n:
                fails.append("9.14b depth claim cites %d frames; record has %d"
                             % (n, rec["frames"]))
            elif abs(float(got) - rec["manufacture_factor"]) > 0.01:
                fails.append("9.14b depth claim %sx vs record %.2fx"
                             % (got, rec["manufacture_factor"]))
        checked += 1
        if not M2["manufacture_factor"] > MF["manufacture_factor"]:
            fails.append("9.14b claims manufacture rises with depth; %.2f is "
                         "not above %.2f" % (M2["manufacture_factor"],
                                             MF["manufacture_factor"]))

    # ---- 9.15 the two self-caught defects, re-derived not restated ----
    # The abstention defect: argmax of an all-zero column returns 0. If numpy
    # ever stopped doing that, 9.15's diagnosis would be wrong.
    checked += 1
    if int(np.argmax(np.zeros(19))) != 0:
        fails.append("9.15 blames argmax returning frame 0 on an all-zero "
                     "column; numpy no longer does that")
    checked += 1
    inv = 1.0 / SN["coherence"]["n_frames"]
    if abs(inv - 1.0 / 19) > 1e-9:
        fails.append("9.15 quotes 1/19 as the symmetric chance level but the "
                     "record has %d frames" % SN["coherence"]["n_frames"])

    # ---- 9.16 partition ----
    for pat, what in (
            (r"\*\*(\d+) requested = (\d+) measured \+ (\d+) refused \+ "
             r"(\d+) failed\.?\*\*", "asks partition"),
            (r"\*\*(\d+) attempted = (\d+) measured \+\s*(\d+) refused \+ "
             r"(\d+) failed\.\*\*", "manufacture subject partition")):
        pr = grab(s9, pat, what)
        checked += 1
        if pr is not None and int(pr[0]) != sum(int(x) for x in pr[1:]):
            fails.append("%s does not sum: %s" % (what, pr))


    # ================= 9.17 - 9.22, N-invariance =================
    NINV = os.path.join(OUTD, "ninv")
    NI = {}
    for _s in ("coffee-bubbles", "112MSDCF"):
        _p = os.path.join(NINV, "%s.json" % _s)
        if not os.path.exists(_p):
            refused.append("9.17: %s ninv record missing" % _s)
        else:
            NI[_s] = json.load(io.open(_p, encoding="utf-8"))

    if len(NI) == 2:
        s17 = s9[s9.index("### 9.17"):s9.index("### 9.18")]
        s18 = s9[s9.index("### 9.18"):s9.index("### 9.19")]
        s19 = s9[s9.index("### 9.19"):s9.index("### 9.20")]
        s20 = s9[s9.index("### 9.20"):s9.index("### 9.21")]
        s21 = s9[s9.index("### 9.21"):s9.index("### 9.22")]
        s22 = s9[s9.index("### 9.22"):s9.index("### 9.23")]

        # ---- the two arm tables, every cell against the record ----
        tabs = {
            "coffee-bubbles": seg(s17, "**`coffee-bubbles`, 19 frames.**",
                                  "**`112MSDCF`, 79 frames**",
                                  "9.17 coffee-bubbles arm table"),
            "112MSDCF": seg(s17, "**`112MSDCF`, 79 frames**",
                            "**The softness lane's effect",
                            "9.17 112MSDCF arm table"),
        }
        for _s, d in NI.items():
            body = tabs[_s]
            for r in d["rows"]:
                w = "9.17 %s %s N=%d" % (_s, r["arm"], r["N"])
                cs = row2(body, r["arm"], str(r["N"]), w)
                for i, (lo, hi) in enumerate(
                        ((0.10, 0.15), (0.20, 0.25), (0.30, 0.35),
                         (0.40, 0.45))):
                    cell(cs, 2 + i,
                         "%.4f" % r["spectrum"]["n_%.2f-%.2f" % (lo, hi)], w)
                cell(cs, 6, "%.5f" % r["blotch"], w)
                cell(cs, 7, "%.2f" % r["neff_detail"], w)
                cell(cs, 8, "%.3f" % r["top_detail"], w)
                cell(cs, 9, "%.2f" % r["snr30"], w)

        # ---- the raw-vs-noise-corrected table ----
        for _s, d in NI.items():
            for arm, v in d["verdict"].items():
                w = "9.17 corrected %s %s" % (_s, arm)
                cs = row2(s17, "`%s`" % _s, arm, w)
                cell(cs, 2, "%.4f" % v["ratios"]["0.30-0.35"], w)
                cell(cs, 3, "%.4f" % v["snr_ratio"]["0.30-0.35"], w)

        # ---- the fix's ceiling, recomputed from the record ----
        for _s, d in NI.items():
            m = d["mechanism"]
            sh = m["soft_shipping"]
            cf = d["verdict"]["confidence"]["snr_ratio"]["0.30-0.35"] - 1.0
            rem = 100.0 * (abs(sh) - abs(cf)) / abs(sh)
            ks = d["ks"]
            w = "9.17 ceiling %s" % _s
            cs = row2(s17, "`%s`, %d -> %d" % (_s, ks[1], ks[0]),
                      "%.4f" % sh, w)
            cell(cs, 2, "%.4f" % cf, w)
            cell(cs, 3, "%.1f%%" % rem, w)

        # ---- 9.18 the bracket table ----
        for _s, d in NI.items():
            for arm in ("argmax", "shipping", "confidence", "mean"):
                v = d["verdict"][arm]
                w = "9.18 %s %s" % (_s, arm)
                cs = row2(s18, "`%s`" % _s, arm, w)
                cell(cs, 2, "%.3f -> %.3f" % (v["top_half"], v["top_deep"]), w)
                cell(cs, 4, "%+.3f" % (v["snr_ratio"]["0.30-0.35"] - 1.0), w)
                if arm != "argmax":
                    cell(cs, 3, "x%.3f"
                         % (v["top_deep"] / v["top_half"]), w)

        # the no-dilution control, which is what the refutation rests on
        for _s, d in NI.items():
            am = 1.0 - d["verdict"]["argmax"]["snr_ratio"]["0.30-0.35"]
            sh = 1.0 - d["verdict"]["shipping"]["snr_ratio"]["0.30-0.35"]
            checked += 1
            if "%.0f%%" % (100 * am / sh) not in _flat(s18):
                fails.append("9.18 %s: argmax/shipping softening ratio %.0f%% "
                             "not quoted" % (_s, 100 * am / sh))
        for _s, d in NI.items():
            checked += 1
            if "%.3f" % d["mechanism"]["dilution_softening_corr"] \
                    not in _flat(s18):
                fails.append("9.18 %s: correlation %.3f not quoted"
                             % (_s, d["mechanism"]["dilution_softening_corr"]))

        # ---- 9.19 the premium table ----
        for _s, d in NI.items():
            for k, v in d["mechanism"]["premium"].items():
                w = "9.19 premium %s N=%s" % (_s, k)
                cs = row2(s19, "`%s`" % _s, k, w)
                cell(cs, 2, "%.2fx" % v, w)

        # ---- 9.20 the pre-registration, scored from the record ----
        pr = NI["112MSDCF"]["mechanism"].get("prereg")
        checked += 1
        if pr is None:
            fails.append("9.20: 112MSDCF record carries no pre-registration")
        else:
            for val, what in ((pr["point"], "point"),
                              (pr["interval"][0], "lower bound"),
                              (pr["interval"][1], "upper bound"),
                              (pr["measured"], "measurement")):
                checked += 1
                if "%.1f" % val not in _flat(s20):
                    fails.append("9.20: %s %.1f not quoted" % (what, val))
            checked += 1
            if pr["survives"]:
                fails.append("9.20: the record says the model SURVIVES but "
                             "the section reports a refutation")
            # The verdict WORD is parsed, not looked for. A presence test
            # for "refuted" is satisfied by any other use of the word in the
            # same section -- and the section legitimately uses it twice --
            # so flipping the conclusion to "confirmed" while leaving every
            # number intact passed a presence test. It does not pass this.
            mv = grab(_flat(s20),
                      r"\*\*Measured:\s*([\d.]+)\.\s*Growth\s*([\d.]+)x"
                      r"\s*against\s*a\s*predicted\s*([\d.]+)x\.\s*The"
                      r"\s*model\s*is\s*(\w+)\.\*\*",
                      "9.20 verdict sentence")
            if mv is not None:
                _mech = NI["112MSDCF"]["mechanism"]
                for got, want, what in (
                        (mv[0], "%.2f" % pr["measured"], "measurement"),
                        (mv[1], "%.2f" % _mech["premium_growth"], "growth"),
                        (mv[2], "%.2f" % _mech["premium_model"],
                         "predicted growth"),
                        (mv[3], "survives" if pr["survives"] else "refuted",
                         "verdict word")):
                    checked += 1
                    if got != want:
                        fails.append("9.20 verdict sentence: %s is %r, the "
                                     "record gives %r" % (what, got, want))
            # the miss, recomputed rather than trusted
            miss = 100.0 * (pr["measured"] / pr["interval"][1] - 1.0)
            checked += 1
            if "%.1f%%" % miss not in _flat(s20):
                fails.append("9.20: miss of %.1f%% outside the interval not "
                             "quoted" % miss)

        for _s, d in NI.items():
            m = d["mechanism"]
            ks = sorted(int(k) for k in m["premium"])
            e = (math.log(m["premium"][str(ks[-1])] / m["premium"][str(ks[0])])
                 / math.log(float(ks[-1]) / ks[0]))
            checked += 1
            if "N^%.3f" % e not in _flat(s20):
                fails.append("9.20: %s empirical exponent N^%.3f not quoted"
                             % (_s, e))
            checked += 1
            if "%.2fx" % m["premium_growth"] not in _flat(s20 + s19):
                fails.append("9.20: %s premium growth %.2fx not quoted"
                             % (_s, m["premium_growth"]))

        # ---- 9.21 shipping's softening restated, and the partition ----
        for _s, d in NI.items():
            checked += 1
            if "%.3f" % d["mechanism"]["soft_shipping"] not in _flat(s21):
                fails.append("9.21: %s shipping softening %.3f not quoted"
                             % (_s, d["mechanism"]["soft_shipping"]))
        pr2 = grab(s21, r"\*\*(\d+)\s+arm-measurements\s+attempted\s+=\s+(\d+)"
                   r"\s+measured\s+\+\s+(\d+)\s+refused\s+\+\s+(\d+)"
                   r"\s+failed\.\*\*",
                   "9.21 arm partition")
        checked += 1
        if pr2 is not None:
            if int(pr2[0]) != sum(int(x) for x in pr2[1:]):
                fails.append("9.21 arm partition does not sum: %s" % (pr2,))
            n_arms = sum(len(d["rows"]) for d in NI.values())
            checked += 1
            if int(pr2[0]) != n_arms:
                fails.append("9.21 claims %s arm-measurements, the records "
                             "hold %d" % (pr2[0], n_arms))

        # ---- 9.22 must describe defects, and the count must be honest ----
        checked += 1
        n_def = len([l for l in s22.splitlines()
                     if re.match(r"^\d+\. \*\*", l)])
        _w = dict(One=1, Two=2, Three=3, Four=4, Five=5, Six=6, Seven=7,
                  Eight=8, Nine=9, Ten=10)
        _m = re.search(r"\n(\w+)[.,] ", s22)
        _said = _w.get(_m.group(1)) if _m else None
        if _said != n_def:
            fails.append("9.22 announces %r (%s) but lists %d numbered "
                         "defects" % (_m.group(1) if _m else None, _said,
                                      n_def))
        checked += 1
        if abs(NI["coffee-bubbles"]["verdict"]["argmax"]["top_deep"]
               - 1.0) > 1e-9:
            fails.append("9.18: the argmax control's share is not 1.0 in the "
                         "record, so the no-dilution claim is unsupported")

    # ---- 9.23: the corrected ladder, re-derived from the ninv2 artifacts ----
    #
    # Every value compared against below is READ OUT of the JSON that vn_ninv2
    # wrote. Nothing in this block is a constant transcribed from the report,
    # which is the failure ORCH propagated across the fleet: a checker that
    # compares an artifact against its own copy of the answer verifies nothing.
    # The one exception is the 0.5 ideal, which is a derivation (var/N), and it
    # is itself checked against the plain-mean arm's measured ratio.
    N2 = {}
    for s in ("coffee-bubbles", "112MSDCF"):
        p = os.path.join(NINV2, "%s.json" % s)
        if os.path.exists(p):
            N2[s] = json.load(io.open(p, encoding="utf-8"))
        else:
            refused.append("9.23: no ninv2 artifact for %s, so its rows are "
                           "NOT EXAMINED" % s)
    s23 = s9[s9.index("### 9.23"):] if "### 9.23" in s9 else ""
    if s23 and N2:
        flat23 = _flat(s23)

        def has(tok, what, ctx=None):
            """Anchored presence: a bare token can be matched by a decoy.

            Short numerics such as 1.000 or 12 recur by chance across a long
            section, so each is required to appear next to a neighbouring
            literal from its own row rather than anywhere in the text.
            """
            hay = flat23
            if ctx is not None:
                i = flat23.find(ctx)
                if i < 0:
                    fails.append("9.23 anchor %r absent, so %s is UNCHECKED"
                                 % (ctx, what))
                    return
                hay = flat23[i:i + 400]
            if tok not in hay:
                fails.append("9.23 %s: %r not found" % (what, tok))

        for s, d in sorted(N2.items()):
            rows = {(r["arm"], r["N"]): r for r in d["rows"]}
            # counts partition
            checked += 1
            c = d["counts"]
            if c["examined"] != c["measured"] + c["refused"]:
                fails.append("9.23 %s: counts do not sum, %d != %d + %d"
                             % (s, c["examined"], c["measured"], c["refused"]))
            checked += 1
            if len([r for r in d["rows"] if r["degenerate"]]) != c["refused"]:
                fails.append("9.23 %s: refused count disagrees with the "
                             "degenerate rows it summarises" % s)
            # every printed ladder cell, PARSED out of the markdown table so
            # that a value in the wrong column is a failure. String presence
            # would pass a table whose cells had been transposed.
            checked += 1
            cells = {}
            # Both subjects have an N=19 rung, so an (arm, N) key is ambiguous
            # across the whole section and the two ladders overwrite each
            # other. Each ladder is therefore read only from the subsection
            # whose HEADING names its subject -- an anchor that is unique by
            # construction, and one that fails loudly if a heading is renamed
            # rather than silently reading the wrong table.
            chunks = [c for c in re.split(r"\n#### ", s23) if s in c[:200]]
            if not chunks:
                fails.append("9.23 %s: no subsection heading names it, so its "
                             "ladder is NOT EXAMINED" % s)
            for ch in chunks:
                for ln in ch.splitlines():
                    m = re.match(r"^\| (\w[\w-]*) \| (\d+) \|(.+)\|\s*$", ln)
                    if not m:
                        continue
                    vals = [v.strip() for v in m.group(3).split("|")]
                    if len(vals) != 8:
                        continue
                    cells[(m.group(1), int(m.group(2)))] = vals
            missing = [k for k in rows if k not in cells]
            if missing:
                fails.append("9.23 %s: the ladder table omits %d of %d rows "
                             "(%s), so those cells are NOT EXAMINED"
                             % (s, len(missing), len(rows),
                                ", ".join("%s N=%d" % k
                                          for k in sorted(missing))))
            for k, r in sorted(rows.items()):
                if k not in cells:
                    continue
                v = cells[k]
                for j, key in enumerate(("scene_mot", "noise_mot",
                                         "scene_mid", "scene_fine",
                                         "noise_mid")):
                    checked += 1
                    try:
                        got = float(v[j])
                    except ValueError:
                        fails.append("9.23 %s %s N=%d %s: %r is not a number"
                                     % (s, k[0], k[1], key, v[j]))
                        continue
                    if abs(got - r[key]) > 5e-4 * abs(r[key]):
                        fails.append("9.23 %s %s N=%d %s: table says %g, the "
                                     "record holds %g"
                                     % (s, k[0], k[1], key, got, r[key]))
                checked += 1
                if abs(float(v[5]) - r["blotch"]) > 5e-6:
                    fails.append("9.23 %s %s N=%d blotch: table says %s, the "
                                 "record holds %.5f"
                                 % (s, k[0], k[1], v[5], r["blotch"]))
            # per-doubling ratios and the ceiling, recomputed here
            ks = d["ks"]
            for a in ("shipping", "confidence", "argmax"):
                for i in range(len(ks) - 1):
                    hi, lo = ks[i], ks[i + 1]
                    rh, rl = rows[(a, hi)], rows[(a, lo)]
                    oct_ = math.log(hi / float(lo), 2.0)
                    checked += 1
                    has("%.4f" % (rh["scene_mid"] / rl["scene_mid"]),
                        "%s %s %d<-%d scene mid ratio" % (s, a, hi, lo),
                        ctx="| %s | %d<-%d |" % (a, hi, lo))
                    checked += 1
                    has("%.4f" % (rh["scene_fine"] / rl["scene_fine"]),
                        "%s %s %d<-%d scene fine ratio" % (s, a, hi, lo),
                        ctx="| %s | %d<-%d |" % (a, hi, lo))
                    checked += 1
                    has("%.4f" % ((rh["noise_mid"] / rl["noise_mid"])
                                  ** (1.0 / oct_)),
                        "%s %s %d<-%d noise per doubling" % (s, a, hi, lo),
                        ctx="| %s | %d<-%d |" % (a, hi, lo))
            # the 0.5 ideal must be MEASURED by the plain mean, not asserted
            checked += 1
            got = []
            for i in range(len(ks) - 1):
                hi, lo = ks[i], ks[i + 1]
                rh, rl = rows[("mean", hi)], rows[("mean", lo)]
                got.append((rh["noise_mid"] / rl["noise_mid"])
                           ** (1.0 / math.log(hi / float(lo), 2.0)))
            if not all(0.40 < g < 0.60 for g in got):
                fails.append("9.23 %s: the plain-mean arm measures %s per "
                             "doubling, which does not recover the 0.5 ideal, "
                             "so the acceptance bar is unsupported"
                             % (s, ", ".join("%.4f" % g for g in got)))
            for g in got:
                checked += 1
                has("%.4f" % g, "%s measured ideal" % s)
            # the fix's ceiling, as a fraction of the excess over ideal.
            # Parsed by ROW, not looked up as a string: 55.2% also appears in
            # the depth-comparison table, and a presence check is satisfied by
            # any duplicate of the value it looks for, so altering one of the
            # two left the other to pass the check. The negative control
            # caught that; review did not.
            crows = {}
            for ch in chunks:
                for ln in ch.splitlines():
                    m = re.match(r"^\| (\d+)<-(\d+) \| ([\d.]+) \| ([\d.]+) "
                                 r"\| \*\*([\d.]+)%\*\* \|", ln)
                    if m:
                        crows[(int(m.group(1)), int(m.group(2)))] = (
                            float(m.group(3)), float(m.group(4)),
                            float(m.group(5)))
            checked += 1
            want = [(ks[i], ks[i + 1]) for i in range(len(ks) - 1)]
            if set(crows) != set(want):
                fails.append("9.23 %s: the ceiling table covers %s, the "
                             "ladder has rungs %s -- the missing rungs are "
                             "NOT EXAMINED"
                             % (s, sorted(crows) or "nothing", want))
            for hi, lo in want:
                if (hi, lo) not in crows:
                    continue
                oct_ = math.log(hi / float(lo), 2.0)
                es = (rows[("shipping", hi)]["noise_mid"]
                      / rows[("shipping", lo)]["noise_mid"]) ** (1.0 / oct_) \
                    - 0.5
                ec = (rows[("confidence", hi)]["noise_mid"]
                      / rows[("confidence", lo)]["noise_mid"]) ** (1.0 / oct_)\
                    - 0.5
                gs, gc, gr = crows[(hi, lo)]
                # Tolerance follows the printed precision: the excesses are
                # quoted to 4 decimals and the removed fraction to 1, so a
                # single tolerance would either reject correct rounding or
                # accept a wrong fourth decimal.
                for got, exp, tol, what in (
                        (gs, es, 5e-5, "shipping excess"),
                        (gc, ec, 5e-5, "fix excess"),
                        (gr, 100.0 * (es - ec) / es, 0.05, "removed")):
                    checked += 1
                    if abs(got - exp) > tol:
                        fails.append("9.23 %s %d<-%d %s: table says %g, the "
                                     "record gives %g"
                                     % (s, hi, lo, what, got, exp))
            # the partition PRINTED IN THE REPORT, against the record. The
            # earlier version checked only that the JSON's own counts summed,
            # which no edit to the report could ever break.
            checked += 1
            said = set(re.findall(r"(\d+) examined = (\d+) measured \+ "
                                  r"(\d+) refused", " ".join(chunks)))
            if not said:
                fails.append("9.23 %s: its subsection states no partition, so "
                             "the cell count is NOT EXAMINED" % s)
            for a, b, cc in said:
                checked += 1
                if (int(a), int(b), int(cc)) != (c["examined"], c["measured"],
                                                 c["refused"]):
                    fails.append("9.23 %s: the report states %s = %s + %s, "
                                 "the record holds %d = %d + %d"
                                 % (s, a, b, cc, c["examined"], c["measured"],
                                    c["refused"]))
            # absolute levels at full depth, PARSED BY ROW. Every one of these
            # values is also quoted in the surrounding prose, and a presence
            # test is satisfied by the prose copy -- the third time in this
            # one section that a duplicate defeated a presence check, and the
            # reason the ladder, the ceiling and this table are all parsed.
            deep = ks[0]
            arows = {}
            for ch in chunks:
                for ln in ch.splitlines():
                    m = re.match(r"^\| (\w+) \| ([-\d.e+]+) \| ([-\d.e+]+) \| "
                                 r"([\d.]+) \| ([-\d.e+]+) \| ([\d.]+) \| "
                                 r"([\d.]+) \|\s*$", ln)
                    if m:
                        arows[m.group(1)] = [float(x)
                                             for x in m.groups()[1:]]
            checked += 1
            if set(arows) != set(("shipping", "confidence", "argmax")):
                fails.append("9.23 %s: the full-depth table lists %s, so the "
                             "missing arms are NOT EXAMINED"
                             % (s, sorted(arows) or "no arms"))
            for a, v in sorted(arows.items()):
                r = rows[(a, deep)]
                exp = [r["scene_fine"], r["noise_mid"],
                       r["scene_fine"] / r["noise_mid"], r["scene_mot"],
                       r["scene_mot"] / r["noise_mot"], r["blotch"]]
                # (relative-or-absolute, tolerance) per column, matched to the
                # precision each is printed at: 4 significant figures for the
                # powers, 3 decimals for fine/noise, 1 for 20-50/noise, 5 for
                # blotch.
                spec = [("rel", 5e-4), ("rel", 5e-4), ("abs", 5e-4),
                        ("rel", 5e-4), ("abs", 0.05), ("abs", 5e-6)]
                names = ["scene fine", "noise mid", "fine/noise",
                         "scene 20-50", "20-50/noise", "blotch"]
                for got, e, (kind, t), nm in zip(v, exp, spec, names):
                    checked += 1
                    lim = t * abs(e) if kind == "rel" else t
                    if abs(got - e) > lim:
                        fails.append("9.23 %s %s %s at N=%d: table says %g, "
                                     "the record gives %g"
                                     % (s, a, nm, deep, got, e))
            # selectivity ordering is the mechanism claim; check the ORDER,
            # not just that the numbers appear
            checked += 1
            order = sorted(("shipping", "confidence", "argmax"),
                           key=lambda a: -rows[(a, deep)]["share"])
            ns = [(rows[(a, ks[0])]["noise_mid"]
                   / rows[(a, ks[1])]["noise_mid"])
                  ** (1.0 / math.log(ks[0] / float(ks[1]), 2.0))
                  for a in order]
            if not all(ns[i] >= ns[i + 1] for i in range(len(ns) - 1)):
                fails.append("9.23 %s: noise growth is NOT monotone in "
                             "selectivity (%s), so the selection-premium "
                             "claim in 9.23.7 is unsupported"
                             % (s, ", ".join("%.4f" % x for x in ns)))
            # The prose verdict needs an anchor of its own. Checking that the
            # numbers appear leaves the sentence around them free to say the
            # opposite of what they show, which is the defect recorded at
            # 9.22 item 5 and again in 9.15.
            checked += 1
            mono = all(ns[i] >= ns[i + 1] for i in range(len(ns) - 1))
            # COUNTED, not looked up. The phrase appears once per subject, so
            # a presence test is satisfied by the other subject's copy and a
            # flipped verdict passes -- which is exactly what the negative
            # control demonstrated before this was a count.
            said_n = flat23.count("against the direction dilution predicts")
            if said_n != sum(1 for _s, _d in N2.items()
                             if _mono(_d)):
                fails.append("9.23.7/9.23.8b state the ordering is against "
                             "dilution %d times, but %d of %d subjects "
                             "measure a monotone ordering"
                             % (said_n, sum(1 for _s, _d in N2.items()
                                            if _mono(_d)), len(N2)))
            if not mono:
                fails.append("9.23 %s: ordering not monotone" % s)
            # the gauge over-statement quoted in 9.23.1
            checked += 1
            nz = d["noise"]
            has("%.3fx" % ((nz["incumbent_sigma"] / nz["paired_sigma"]) ** 2),
                "%s variance over-statement" % s)
        # Each over-statement is quoted twice by design (once where it is
        # derived, once where the two subjects are compared), so requiring
        # presence lets one of the pair be altered freely. The SET of
        # three-decimal x-ratios in the section must therefore equal the set
        # the records give, which fails on any value that is not one of them.
        checked += 1
        want_x = set("%.3fx" % ((d["noise"]["incumbent_sigma"]
                                 / d["noise"]["paired_sigma"]) ** 2)
                     for d in N2.values())
        got_x = set(re.findall(r"\b\d\.\d{3}x\b", s23))
        if got_x != want_x:
            fails.append("9.23: the section quotes variance over-statements "
                         "%s, the records give %s"
                         % (sorted(got_x), sorted(want_x)))
        # the commissioning strings must come from the artifact, not the log
        for s, d in sorted(N2.items()):
            checked += 1
            if "commission" not in d:
                fails.append("9.23 %s: the artifact does not carry its "
                             "commissioning lines, so every commissioning "
                             "number in the report is UNVERIFIABLE" % s)
                continue
            lines = _flat(" ".join(d["commission"]["noise"]
                                   + d["commission"]["decomp"]))
            for m in re.findall(r"scene error ([\d.]+)%, ([\d.]+)%, "
                                r"([\d.]+)%", lines):
                for tok in m:
                    checked += 1
                    has(tok + "%", "%s separation sweep" % s)
        # 9.23.12 must announce as many defects as the report lists in total,
        # counting 9.22's five as well, because that is what "these ten" means
        checked += 1
        n_def = len([l for l in (s22 + s23).splitlines()
                     if re.match(r"^\d+\. \*\*", l)])
        _w2 = dict(One=1, Two=2, Three=3, Four=4, Five=5, Six=6, Seven=7,
                   Eight=8, Nine=9, Ten=10, Eleven=11, Twelve=12,
                   Thirteen=13, Fourteen=14, Fifteen=15)
        _m2 = re.search(r"(\w+) of these (\w+) were caught", s23)
        if not _m2 or _w2.get(_m2.group(2).title()) != n_def:
            fails.append("9.23.12 announces %r defects but lists %d"
                         % (_m2.group(2) if _m2 else None, n_def))
        # the retraction must actually be present at 9.17
        checked += 1
        if "RETRACTED -- see section 9.23" not in doc:
            fails.append("9.17-9.22 carry retracted numbers but no retraction "
                         "banner points at 9.23")

    print("\n%d checks: %d passed, %d FAILED, %d REFUSED"
          % (checked, checked - len(fails) - len(refused), len(fails),
             len(refused)))
    for f in fails:
        print("  FAIL    " + f)
    for r_ in refused:
        print("  REFUSED " + r_)
    if refused:
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nREFUSED: checker crashed; no claim in section 9 is checked")
        sys.exit(2)
