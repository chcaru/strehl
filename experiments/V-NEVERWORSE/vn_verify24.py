"""Re-derive every load-bearing number in RESULT.md section 9.24 from the
split-half records.

Same rules as `vn_verify9.py`. Two of them matter more here than usual, both
because of failures ORCH propagated across the fleet tonight:

  1. NOTHING IS COMPARED AGAINST A CONSTANT WRITTEN IN THIS FILE. A checker
     that ran 37/37 green elsewhere tonight then caught 5 of 13 plants, because
     eight of its checks compared the artifact against its own copy of the
     answer. Every expected value below is computed from the JSON records by
     code that does not read the document, and every actual value is parsed
     out of the document.

  2. THE PARTITION SELF-SUMS. The summary prints resolved / mismatched /
     unparsed and their total equals the number of claims attempted, so a
     claim that was silently skipped cannot read as a claim that passed.

Section 9.24 is unusual in that many of its statistics are REFUSED. A refused
statistic must appear in the document as the literal token REFUSED, and this
checker verifies that too -- a refusal quietly replaced by a number is exactly
the failure the refusal exists to prevent.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "RESULT.md")
SPLIT = r"C:\dev\strehl-out\V-NEVERWORSE\split"
SUBJ = ("coffee-bubbles", "119MSDCF", "112MSDCF")

sys.path.insert(0, HERE)
import vn_splitrep as R  # noqa: E402

ok_n, bad, unparsed = 0, [], []


def sec():
    t = io.open(DOC, encoding="utf-8").read()
    i = t.index("### 9.24 ")
    j = t.index("\n## 10. Files")
    return t[i:j]


BODY = sec()
FLAT = re.sub(r"\s+", " ", BODY)


def claim(label, expect, pattern, tol=None, rel=True):
    """Parse ONE number out of the document and compare to an oracle.

    `pattern` must contain exactly one capture group and must match exactly
    once in the section, so a check cannot be satisfied by a duplicate of its
    own value somewhere else in the text -- the presence-check defect recorded
    as fact 882 in SYNTHESIS.md.

    TOLERANCE IS DERIVED FROM THE DOCUMENT, NOT CHOSEN. When `tol` is None the
    number is accepted iff it is the correct rounding of the oracle to the
    number of decimal places the document actually prints. A fixed epsilon
    either rejects an honestly rounded 48.9 or accepts an edited 48.7,
    depending on which epsilon was picked; half a unit in the last printed
    place is the only threshold that means "this is what rounding would have
    produced".
    """
    global ok_n
    ms = re.findall(pattern, FLAT)
    if len(ms) != 1:
        unparsed.append("%s: pattern matched %d times" % (label, len(ms)))
        return
    got = ms[0]
    if isinstance(expect, str):
        if got.strip() != expect.strip():
            bad.append("%s: doc %r oracle %r" % (label, got, expect))
        else:
            ok_n += 1
        return
    try:
        g = float(got)
    except ValueError:
        unparsed.append("%s: %r is not a number" % (label, got))
        return
    if tol is None:
        dec = len(got.split(".")[1]) if "." in got else 0
        if abs(g - round(expect, dec)) > 10.0 ** (-dec) / 2.0:
            bad.append("%s: doc %s, oracle %.6g rounds to %s at %d dp"
                       % (label, got, expect, round(expect, dec), dec))
        else:
            ok_n += 1
        return
    d = abs(g - expect)
    if rel and abs(expect) > 0:
        d /= abs(expect)
    if d > tol:
        bad.append("%s: doc %.6g oracle %.6g (delta %.3g)"
                   % (label, g, expect, d))
    else:
        ok_n += 1


def table_claim(label, lines):
    """Every generated table must appear in the document verbatim.

    This is the strongest available check and it covers far more cells than
    naming them one at a time: the generator is re-run here against the same
    records and its output must be present, so a single edited digit anywhere
    in the table fails.
    """
    global ok_n
    want = re.sub(r"\s+", " ", "\n".join(lines)).strip()
    if want not in FLAT:
        head = want[:110]
        bad.append("%s: generated table not present; starts %r" % (label,
                                                                   head))
    else:
        ok_n += 1


def main():
    ds = [R.load(s) for s in SUBJ]
    cb, s119, s112 = ds

    # --- every generated table, cell for cell -----------------------------
    table_claim("table hardspread", R.table_hardspread(ds))
    table_claim("table orch", R.table_orch(s119))
    table_claim("table metric", R.table_metric(cb))
    table_claim("table margins", R.table_margins(ds))
    table_claim("table blur", R.table_blur(cb))
    table_claim("table ladder", R.table_ladder(cb))
    table_claim("table manufactured", R.table_manufactured(cb))
    table_claim("table corpus", R.table_corpus(ds))
    table_claim("table ceiling", R.table_ceiling(cb))
    table_claim("table fix", R.table_fix(ds))
    table_claim("table antiblur", R.table_antiblur(ds))

    H = [R.headline(d) for d in ds]

    # --- the exponent-invariance finding ----------------------------------
    # The recorded spread must agree with the arms it was computed from. A
    # stale or edited spread is a detected inconsistency and therefore a
    # MISMATCH, not a crash: refusing here would let a corrupted record exit
    # with the same code as an unreadable one.
    for d, tag in zip(ds, SUBJ):
        a = d["commission"]["arms"]
        hs = [a[t]["disc"]["disc_step"] for t in ("improve", "base", "defect")]
        if abs((max(hs) - min(hs)) - a["hard_spread"]) > 1e-15:
            bad.append("%s: recorded hard_spread %.3g disagrees with its own "
                       "arms %.3g" % (tag, a["hard_spread"], max(hs) - min(hs)))
        elif a["hard_spread"] != 0.0:
            bad.append("%s: hard spread is %.3g, not exactly zero; 9.24.1 is "
                       "wrong" % (tag, a["hard_spread"]))
        else:
            ok_n_add()
    claim("hard winner value quoted for 119", H[1]["hard_ship"],
          r"three arms read `([0-9.]+)` to every digit")
    claim("hard shipping minus fix", H[1]["hard_ship_minus_fix"],
          r"hard\(shipping\) - hard\(fix\)` is `([0-9.]+)` exactly",
          tol=1e-12, rel=False)
    claim("fine cost quoted beside it", 100 * H[1]["fix_fine_cost"],
          r"removes ([0-9.]+)% of the fine band\. \*\*The build lane")

    # --- the naive statistic on a perfect input ---------------------------
    claim("naive on perfect input",
          cb["commission"]["metric"]["naive_on_perfect_input"],
          r"statistic scores \*\*([0-9.]+)\*\* on it")

    # --- soft margins quoted in prose -------------------------------------
    claim("soft margins triple",
          ", ".join("%.1f%%" % (100 * d["commission"]["arms"]["margins"]
                                ["soft"][0]) for d in ds),
          r"same pixels moves ([0-9.%, ]+?)\. The same monotonicity")

    # --- the focus-offset null --------------------------------------------
    m = cb["commission"]["metric"]
    claim("noise-free textured L2 recoh", m["noisefree_textured_L2"]["recoh"],
          r"reproducibility there is ([0-9.]+) and")
    claim("noise-free textured L3 recoh", m["noisefree_textured_L3"]["recoh"],
          r"reproducibility there is [0-9.]+ and ([0-9.]+),")

    # --- the refused reproducibility statistics ---------------------------
    recohs = ("recoh_all", "recoh_flat", "recoh_detail")
    wrong = sum(1 for d in ds for k in recohs
                if d["commission"]["arms"]["margins"][k][0] < 0)
    claim("wrong-way defect readings", float(wrong),
          r"on ([0-9]+) of the [0-9]+ defect-side readings", tol=0, rel=False)
    claim("wrong-way denominator", float(len(ds) * len(recohs)),
          r"on [0-9]+ of the ([0-9]+) defect-side readings", tol=0, rel=False)
    for d, tag in zip(ds, SUBJ):
        for k in recohs:
            if R.admit(d).get(k, False):
                bad.append("%s/%s: admitted, but 9.24.4 says refused"
                           % (tag, k))
            else:
                ok_n_add()

    # the two readings the coin-flip gate reported as opposite verdicts
    a_cb = cb["commission"]["arms"]
    a_112 = s112["commission"]["arms"]
    claim("cb whole-frame recoh base", a_cb["base"]["stats"]["recoh_all"],
          r"`coffee-bubbles` \(([0-9.]+) ->")
    claim("cb whole-frame recoh defect", a_cb["defect"]["stats"]["recoh_all"],
          r"`coffee-bubbles` \([0-9.]+ -> ([0-9.]+), PASS\)")
    claim("112 whole-frame recoh base", a_112["base"]["stats"]["recoh_all"],
          r"`112MSDCF` \(([0-9.]+) ->")
    claim("112 whole-frame recoh defect",
          a_112["defect"]["stats"]["recoh_all"],
          r"`112MSDCF` \([0-9.]+ -> ([0-9.]+), FAIL\)")

    # --- blotch refused on 119 --------------------------------------------
    if R.admit(s119).get("blotch", True):
        bad.append("119/blotch: admitted, but 9.24.4 says refused")
    else:
        ok_n_add()
    claim("119 blotch margin",
          100 * s119["commission"]["arms"]["margins"]["blotch"][0],
          r"statistic moves ([0-9.]+)% under a 4x exponent range there")
    claim("119 flatvar margin",
          100 * s119["commission"]["arms"]["margins"]["flatvar"][0],
          r"on the same render moves ([0-9.]+)%", tol=2e-2)

    # --- the swept blur plant ---------------------------------------------
    sw = a_cb["margins"]["blur_sweep"]
    big = [s for s in sw if s["sigma"] == 1.20][0]
    claim("over-strong plant fine loss", -100 * big["d_fine"],
          r"It removed ([0-9.]+)% of the\s*fine band", tol=1e-3)
    claim("blur breakdown sigma", a_cb["margins"]["blur_breakdown_sigma"],
          r"It fires from `sigma = ([0-9.]+) px`")
    fires = [s for s in sw if s["fires"]][0]
    claim("fine fall at breakdown", -100 * fires["d_fine"],
          r"where `fine` falls ([0-9.]+)%", tol=2e-2)

    # --- the conviction ---------------------------------------------------
    claim("excess triple", ", ".join("%.2fx" % h["excess"] for h in H),
          r"mid-band variance is ([0-9.x, ]+?) the plain mean")
    for d, tag in zip(ds, SUBJ):
        lad = R.headline(d)["excess_ladder"]
        if not (lad == sorted(lad) and lad[-1] > lad[0]):
            bad.append("%s: excess ladder does not rise with N: %s"
                       % (tag, lad))
        else:
            ok_n_add()
        if min(lad) <= 1.0:
            bad.append("%s: excess not above unity: %s" % (tag, lad))
        else:
            ok_n_add()

    # the plain mean's flat variance is N-independent (the floor argument)
    claim("mean floor triple",
          ", ".join("%.1f" % R.derived(cb, "mean", N)["flatvar"]
                    for N in sorted(cb["ks"])),
          r"\(([0-9.,  ]+?) at N = 4, 9, 19\)")

    # --- the twin ---------------------------------------------------------
    claim("twin ratio triple",
          ", ".join("%.3f" % h["twin_ratio"] for h in H),
          r"observed-to-twin ratio is \*\*([0-9.,  ]+?)\*\*")
    claim("119 twin share", 100.0 / H[1]["twin_ratio"],
          r"noise alone accounts for at most ([0-9]+)% of", tol=1.0,
          rel=False)

    # --- the fix's ceiling ------------------------------------------------
    claim("fix variance triple",
          ", ".join("%.1f%%" % (100 * h["fix_removes_variance"]) for h in H),
          r"stack depth -- ([0-9.%,  ]+?) -- so")
    claim("fix fine triple",
          ", ".join("%.1f%%" % (100 * h["fix_fine_cost"]) for h in H),
          r"rises monotonically with depth -- ([0-9.%,  ]+?) -- so")
    claim("fix efficiency shallow", 100 * H[0]["fix_efficiency_gain"],
          r"ratio goes from \+([0-9.]+)% on the")
    claim("fix efficiency mid", -100 * H[1]["fix_efficiency_gain"],
          r"to \*\*-([0-9.]+)%\*\* and")
    claim("fix efficiency deep", -100 * H[2]["fix_efficiency_gain"],
          r"and \*\*-([0-9.]+)%\*\* on the 32- and")
    for h, tag in zip(H, SUBJ):
        if h["fix_removes_variance"] >= 0.5:
            bad.append("%s: fix removes >=50%%, 'about a third' is wrong"
                       % tag)
        else:
            ok_n_add()
    claim("argmax efficiency ratio", H[0]["argmax_efficiency_ratio"],
          r"reads ([0-9.]+) on the blur-immune ratio")

    # --- the anti-blur demonstration --------------------------------------
    claim("mean efficiency triple",
          ", ".join("%.2fx" % h["mean_efficiency_ratio"] for h in H),
          r"blur-immune ratio by \*\*([0-9.x,  ]+?)\*\*")
    claim("mean fine retained triple",
          ", ".join("%.2f%%" % (100 * h["mean_fine_retained"]) for h in H),
          r"retaining ([0-9.%,  ]+?) of the fine band")
    for h, tag in zip(H, SUBJ):
        if h["mean_efficiency_ratio"] <= 1.0:
            bad.append("%s: plain mean does not lose var/fine" % tag)
        else:
            ok_n_add()

    # --- counts self-sum on every subject ---------------------------------
    for d, tag in zip(ds, SUBJ):
        c = d["counts"]
        if c["measured"] + c["refused"] != c["examined"]:
            bad.append("%s: counts do not self-sum: %s" % (tag, c))
        else:
            ok_n_add()

    # --- refusals must be present as refusals -----------------------------
    for tok, n_expected in (("REFUSED", None),):
        if FLAT.count(tok) < 10:
            bad.append("REFUSED appears only %d times; the refused "
                       "statistics are not visible in the tables"
                       % FLAT.count(tok))
        else:
            ok_n_add()

    # --- the negative control's own reach ---------------------------------
    # Parsed out of vn_negctl24.py, never hardcoded here. The document claims
    # a plant count; the only honest oracle for it is the tool that runs them.
    src = io.open(os.path.join(HERE, "vn_negctl24.py"), encoding="utf-8").read()
    ns = {}
    exec(compile(re.search(r"^DOC_PLANTS = \[.*?^\]", src,
                           re.S | re.M).group(0), "p", "exec"), ns)
    n_doc = len(ns["DOC_PLANTS"])
    n_oracle = len(re.search(r"^ORACLE_PLANTS = \[(.*?)^\]", src,
                             re.S | re.M).group(1).strip().splitlines())
    claim("negative control total plants", n_doc + n_oracle,
          r"runs \*\*(\d+) plants\*\*")
    words = {2: "Two", 7: "Seven", 8: "Eight", 9: "Nine", 30: "Thirty",
             31: "Thirty-one", 32: "Thirty-two", 33: "Thirty-three",
             34: "Thirty-four", 35: "Thirty-five", 36: "Thirty-six"}
    claim("negative control document plants", words.get(n_doc, str(n_doc)),
          r"(Thirty[\w-]*|Forty[\w-]*|\d+) edit the document")
    claim("negative control oracle plants", words.get(n_oracle, str(n_oracle)),
          r"\*\*(\w+) edit the record\*\*")

    total = ok_n + len(bad) + len(unparsed)
    print("section 9.24 verification")
    print("  verified   : %d" % ok_n)
    print("  MISMATCH   : %d" % len(bad))
    print("  UNPARSED   : %d" % len(unparsed))
    print("  ---------------")
    print("  total      : %d claims attempted" % total)
    for b in bad:
        print("  MISMATCH  %s" % b)
    for u in unparsed:
        print("  UNPARSED  %s" % u)
    return 1 if (bad or unparsed) else 0


def ok_n_add():
    global ok_n
    ok_n += 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # a crash is a refusal, never a pass
        print("REFUSED: %s: %s" % (type(e).__name__, e))
        sys.exit(2)
