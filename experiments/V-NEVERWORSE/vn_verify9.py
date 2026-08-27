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
PYR = os.path.join(HERE, "pin9b05", "pyramid.rs")

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
