"""Check every number in section 9.25 against the records it came from.

The pattern is section 9.24's and the reason is the same. A checker that
carries its own copy of the answer passes every document plant and catches
nothing, so the oracle here is `vn_rep25.py` re-run against the JSON records,
and `vn_negctl25.py` plants defects in BOTH the document and the records.

Every table is checked whole rather than cell by cell: the generator is
re-run and its exact output must be present in the section, so a single
edited digit anywhere in a table fails. Standalone numbers are checked with a
pattern that must match EXACTLY ONCE in the section, because a presence check
is satisfied by any duplicate of the value elsewhere in the text.

Exit codes: 0 all green, 1 a check failed, 2 the records could not be read
(refusal, not a pass and not a failure).
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "RESULT.md")
sys.path.insert(0, HERE)
import vn_rep25 as R  # noqa: E402

ok_n, bad, unparsed = 0, [], []


def section():
    t = io.open(DOC, encoding="utf-8").read()
    i = t.index("### 9.25 ")
    j = t.index("\n## 10. Files")
    return t[i:j]


def table_claim(label, lines, flat):
    global ok_n
    want = re.sub(r"\s+", " ", "\n".join(lines)).strip()
    if want not in flat:
        bad.append("%s: generated table not present; starts %r"
                   % (label, want[:110]))
    else:
        ok_n += 1


def text_claim(label, want, flat):
    global ok_n
    w = re.sub(r"\s+", " ", want).strip()
    n = flat.count(w)
    if n != 1:
        bad.append("%s: generated text appears %d times, want exactly 1: %r"
                   % (label, n, w[:110]))
    else:
        ok_n += 1


def claim(label, expect, pattern, flat):
    """One number, parsed out of the section, compared to the oracle at the
    precision the document actually prints. A fixed epsilon either rejects an
    honestly rounded value or accepts an edited one; half a unit in the last
    printed place is the only threshold that means "this is what rounding
    would have produced"."""
    global ok_n
    ms = re.findall(pattern, flat)
    if len(ms) != 1:
        unparsed.append("%s: pattern matched %d times" % (label, len(ms)))
        return
    got = ms[0]
    try:
        g = float(got)
    except ValueError:
        unparsed.append("%s: %r is not a number" % (label, got))
        return
    dec = len(got.split(".")[1]) if "." in got else 0
    if abs(g - round(expect, dec)) > 10.0 ** (-dec) / 2.0:
        bad.append("%s: doc %s, oracle %.6g rounds to %s at %d dp"
                   % (label, got, expect, round(expect, dec), dec))
    else:
        ok_n += 1


def main():
    try:
        tabs = R.tables()
        vals = R.values()
        d = R.load("subgate.json")
        lad = R.load("subgate-ladder.json")
        g = R.load("rogue.json")
        m = R.load("rogue46.json")
    except (IOError, OSError, ValueError, KeyError) as e:
        print("REFUSED: records unreadable (%s: %s)" % (type(e).__name__, e))
        return 2
    body = section()
    flat = re.sub(r"\s+", " ", body)

    for k in sorted(tabs):
        table_claim("table:%s" % k, tabs[k], flat)
    for k in sorted(vals):
        text_claim("value:%s" % k, vals[k], flat)

    # --- claims the tables do not carry, checked against the records -----
    c = d["commission"]
    claim("s2 worst absolute error",
          max(abs(s["r_med"] - s["r_pred"]) for s in c["S2_sweep"]),
          r"recovers the closed form to within ([0-9.]+) at every rung", flat)
    claim("s4 interior peak signal fraction",
          c["S4_selection_cost"]["argmax_sig_frac"],
          r"peak sits at signal fraction ([0-9.]+)", flat)

    x = max(abs(R.band_of(d["subjects"][s]["rows"], 0)["r_subgate"])
            for s in R.SUBJ)
    claim("max |r_subgate| over subjects", x,
          r"at most ([0-9.]+) on any subject measured", flat)
    lo = min(R.band_of(d["subjects"][s]["rows"], 0)["px_dead"]
             for s in R.SUBJ)
    hi = max(R.band_of(d["subjects"][s]["rows"], 0)["px_dead"]
             for s in R.SUBJ)
    claim("min sub-gate pixel count", lo,
          r"pixel counts from ([0-9,]+) to [0-9,]+",
          flat.replace(",", ""))
    claim("max sub-gate pixel count", hi,
          r"pixel counts from [0-9,]+ to ([0-9,]+)",
          flat.replace(",", ""))

    bee = lad["subjects"]["bee-2-cpl@registered"]["rungs"][-1]
    il = R.band_of(bee["rows"], 5)["sel_cost"]
    pr = R.band_of(bee["rows_pair"], 5)["sel_cost"]
    claim("interleave L5 at top rung", il,
          r"against ([0-9.]+) interleaved", flat)
    claim("split agreement", abs(il - pr),
          r"two agree to ([0-9.]+) at the\s*top rung", flat)
    rg = {r["band"]: r for r in g["rogue"]}
    claim("shipping L5 multiple of entitlement",
          rg[5]["shipping"] * g["n"],
          r"of L5\*\* -- ([0-9]+) times its entitlement", flat)
    claim("entitlement", 1.0 / g["n"], r"1/N =\s*([0-9.]+)", flat)
    claim("rmax amplification at L6", rg[6]["rmax0.75"] / rg[6]["shipping"],
          r"a \*\*([0-9.]+)x amplification\*\*", flat)
    claim("shipping L6 multiple", rg[6]["shipping"] * g["n"],
          r"([0-9]+)x to [0-9]+x its entitlement, a", flat)
    claim("rmax L6 multiple", rg[6]["rmax0.75"] * g["n"],
          r"[0-9]+x to ([0-9]+)x its entitlement, a", flat)

    br = {b["band"]: b for b in g["f46"]["bands"]}
    claim("f46 coarse energy low", min(br[k]["ratio"] for k in (4, 5, 6)),
          r"coarse-band energy is ([0-9]+)x to\s*[0-9]+x the stack median",
          flat)
    claim("f46 coarse energy high", max(br[k]["ratio"] for k in (4, 5, 6)),
          r"coarse-band energy is [0-9]+x to\s*([0-9]+)x the stack median",
          flat)

    ib = {b["band"]: b for b in m["band_rms"]}
    claim("image L4 ratio", ib[4]["ratio"],
          r"amplitude by \*\*([0-9.]+)x at L4\*\*", flat)
    claim("image L6 ratio", ib[6]["ratio"],
          r"and \*\*([0-9.]+)x at L6\*\*", flat)
    claim("image L0-L2 stability",
          100.0 * max(abs(ib[k]["ratio"] - 1.0) for k in (0, 1, 2)),
          r"unchanged to within ([0-9.]+)%", flat)
    claim("frac over 100 DN", 100.0 * m["frac_px_over_100dn"],
          r"\*\*([0-9.]+)% of the\s*image moves by more than 100 DN\*\*",
          flat)
    claim("mean level", m["mean_dn_with"],
          r"on a mean level of ([0-9,]+) DN", flat.replace(",", ""))

    n_dense = len(g["dense"])
    agree = sum(1 for r in g["dense"]
                if r["rogue_present"] == (r["sel_cost"]["5"] > 0.4))
    claim("dense correspondence", agree,
          r"([0-9]+) of %d rungs" % n_dense, flat)

    tot = ok_n + len(bad) + len(unparsed)
    print("section 9.25 verifier")
    print("  passed        %d" % ok_n)
    print("  FAILED        %d" % len(bad))
    print("  unparsed      %d" % len(unparsed))
    print("  total checks  %d" % tot)
    for b in bad:
        print("  FAIL %s" % b)
    for u in unparsed:
        print("  UNPARSED %s" % u)
    if bad or unparsed:
        return 1
    print("  GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
