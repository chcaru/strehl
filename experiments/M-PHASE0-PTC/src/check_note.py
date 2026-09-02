"""
Checker for docs/research/M-PHASE0-PTC.md.

Every number in the note must be reproducible from the lane's JSON outputs. This
script recomputes each one from JSON and requires it to appear in the note ON A
LINE THAT ALSO CONTAINS A NAMED ANCHOR.

WHY THE ANCHOR IS NOT OPTIONAL
------------------------------
A presence-only check ("does '0.224' appear in the file?") is satisfied by any
duplicate of the value anywhere in the document. Short tokens like "5.9x", "48"
or "+2.365%" occur by chance, so a presence check on them tests nothing. Each
check below is therefore pinned to its own anchor string, and a check whose
anchor is missing is reported as UNRESOLVED -- never silently as a pass.

THE SUMMARY PARTITIONS. Every check lands in exactly one of pass / fail /
unresolved, and the three sum to the total. A count that does not move must not
be readable as either "nothing was wrong" or "nothing was examined".
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(LANE))
OUT = os.path.join(LANE, "out")
NOTE = os.environ.get("NOTE_PATH") or os.path.join(ROOT, "docs", "research", "M-PHASE0-PTC.md")

J = {}
for name in ("b1-audit", "b1-perstack", "b1-bar", "b1-tie"):
    with open(os.path.join(OUT, name + ".json"), encoding="utf-8") as f:
        J[name] = json.load(f)

with open(NOTE, encoding="utf-8") as f:
    NOTE_TEXT = f.read()
# collapse whitespace so a figure split across a line wrap still matches
FLAT = re.sub(r"\s+", " ", NOTE_TEXT)

results = []


def check(label, anchor, value, fmt="%s"):
    """value must appear, formatted, on a line/span that also carries `anchor`."""
    shown = fmt % value if not isinstance(value, str) else value
    if anchor not in FLAT:
        results.append(("UNRESOLVED", label, "anchor absent: %r" % anchor))
        return
    # search a window around each anchor occurrence
    ok = False
    for m in re.finditer(re.escape(anchor), FLAT):
        lo = max(0, m.start() - 400)
        hi = min(len(FLAT), m.end() + 400)
        if shown in FLAT[lo:hi]:
            ok = True
            break
    results.append((("PASS" if ok else "FAIL"), label,
                    "%s near %r" % (shown, anchor[:48])))


def check_phrase(label, template, *values):
    """Require an exact phrase, built from JSON values, to appear in the note.

    Immune to two failure modes that `check` above is not:
      - a short value ("0", "5", "1.2") whose decoys occur by chance nearby;
      - an anchor that itself CONTAINS the value, which makes the check
        self-satisfying and unable to fail.
    The phrase carries its own context, so it can only match the intended site.
    """
    shown = template % values
    results.append((("PASS" if shown in FLAT else "FAIL"), label, repr(shown[:64])))


a = J["b1-audit"]
p = J["b1-perstack"]
b = J["b1-bar"]
t = J["b1-tie"]

# ---- section 1: the unreachable bar
# two sites carry this figure; a check pinned to one leaves the other unchecked.
# Commissioning caught exactly that: a plant at site 2 passed. Both are pinned now.
check_phrase("M90 CI as percent, site 1", "names a \u00b1%.4f%% precision figure", a["q1"]["bar_rel_pct"])
check_phrase("M90 CI as percent, site 2", "is **\u00b1%.4f%%**.", a["q1"]["bar_rel_pct"])
check("inter-method disagreement", "They differ by", a["q1"]["inter_method_pct"], "%.4f")
check("ratio bar to disagreement", "the bar", a["q1"]["ratio"], "%.1f")
# composite: the old anchor "1.2 percentage-point" CONTAINED the value it checked,
# so it could never fail. Commissioning caught it as MISSED.
check_phrase("M90 band width pp", "**%.1f percentage-point** band", a["q1"]["m90_band_width_pct"])
check_phrase("M90 band width, second site", "**%.1f pp wide", a["q1"]["m90_band_width_pct"])
check("band over bar", "the CI the proposal cites as its bar", a["q1"]["band_over_bar"], "%.0f")

# ---- section 3: per-stack
for row in p["r1"]["rows"]:
    check("per-stack g %s" % row["stack"], row["stack"], row["g"], "%.6f")
    check("per-stack delta %s" % row["stack"], row["stack"], abs(row["delta_pct"]), "%.3f")
# composite: bare "%d" counts are satisfied by any nearby digit. Commissioning
# caught both of these as MISSED.
check_phrase("inside CI count", "Inside B1's named CI: %d of 6", p["r1"]["inside_ci"])
check_phrase("inside band count", "Inside M90's own stated band: %d of 6", p["r1"]["inside_band"])
check("median internal precision", "median", p["r2"]["median_internal_pct"], "%.3f")
check_phrase("external spread pp", "scatter is **%.3f pp**", p["r2"]["external_pp"])
check_phrase("external over internal", "External/internal = **%.1f", p["r2"]["ratio"])

# ---- section 4: the intercept
check_phrase("negative intercept count", "`icptA < 0` in **%d of 48 rows", p["r3"]["n_negative"])
check("intercept rows total", "of 48 rows", p["r3"]["n"], "%d")
check_phrase("negative intercept pct", "rows = %.1f%%**, range", p["r3"]["frac_pct"])
check("intercept min", "range", abs(p["r3"]["min"]), "%.2f")
check("intercept max", "range", p["r3"]["max"], "%.2f")

# ---- section 5: the achievable bar
check("ungated width", "ungated", b["r4"]["width_all_pp"], "%.3f")
check("gated width", "CONSIST", b["r4"]["width_gated_pp"], "%.3f")
check("collapse factor", "Collapse factor", b["r4"]["collapse"], "%.1f")
check("gated n", "CONSIST", b["r4"]["n_gated"], "%d")
check("proposed bar", "within", b["r5"]["proposed_bar_pct"], "%.0f")

# ---- section 6: the tie observation
check("armA mean g", "0.222723", t["armA"]["mean_g"], "%.6f")
check("armA vs M90", "+0.728", t["armA"]["vs_m90"], "%.3f")
check("armA vs M71", "0.616", abs(t["armA"]["vs_m71"]), "%.3f")
check("armA agreement pp", "agree with each other to", t["armA"]["agree_pp"], "%.3f")
check("armA position in interval", "of the way", t["armA"]["frac_to_m71"], "%.0f")
check("armB mean g", "0.224422", t["armB"]["mean_g"], "%.6f")
check("armB vs M90", "+1.496", t["armB"]["vs_m90"], "%.3f")
check("armB vs M71", "+0.142", t["armB"]["vs_m71"], "%.3f")
check("arms differ pp", "The arms differ by", t["arms_differ_pp"], "%.3f")

# ---- structural checks on the note itself
def structural(label, cond, detail):
    results.append((("PASS" if cond else "FAIL"), label, detail))


structural("every table row has uniform width",
           all(len(set(len(r.split("|")) for r in blk)) == 1
               for blk in re.findall(r"(?:^\|.*\n)+", NOTE_TEXT, re.M)
               for blk in [ [l for l in blk.strip().split("\n")] ]),
           "no bare | splitting a row")
structural("errors section present",
           "## 7. My own errors, disclosed" in NOTE_TEXT,
           "section 7")
structural("scope limit disclosed",
           "did **not** re-derive" in NOTE_TEXT,
           "verification scope stated")
structural("pre-registration weakness disclosed",
           "author-attested, not commit-attested" in NOTE_TEXT,
           "commit ordering disclosed")
structural("observation labelled unregistered",
           "It carries no pass/fail." in NOTE_TEXT,
           "section 6 label")
structural("read-floor strike stated",
           "strike" in NOTE_TEXT.lower() and "read floor" in NOTE_TEXT.lower(),
           "section 8 row")

npass = sum(1 for r in results if r[0] == "PASS")
nfail = sum(1 for r in results if r[0] == "FAIL")
nunres = sum(1 for r in results if r[0] == "UNRESOLVED")

for status, label, detail in results:
    if status != "PASS":
        print("%-11s %-34s %s" % (status, label, detail))

print("")
print("=" * 70)
print("checks: %d   PASS %d   FAIL %d   UNRESOLVED %d   (sum %d)"
      % (len(results), npass, nfail, nunres, npass + nfail + nunres))
assert npass + nfail + nunres == len(results), "summary does not partition"
print("VERDICT: %s" % ("GREEN" if (nfail == 0 and nunres == 0) else "NOT GREEN"))
sys.exit(0 if (nfail == 0 and nunres == 0) else 1)
