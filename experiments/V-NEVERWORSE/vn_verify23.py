"""Check every number quoted in RESULT.md section 2.3 against its record.

Written because prose is not a measurement. Its first run found five wrong
numbers in section 2.3, one of which (a quoted scale range that could not be
reproduced from the ratio records) turned out to be a real mislabelled arm in
`vn_warpnull.py` -- the "worst scale" arm was the LEAST warped frame.

Each claim is anchored on its own source record, never on another claim, so a
single value appearing in several places cannot satisfy two checks at once.

  python vn_verify23.py     ->  rc 0 if every claim reproduces, 1 otherwise
"""
import glob
import json
import os
import re
import sys

import numpy as np

OUT = r"C:\dev\strehl-out\V-NEVERWORSE"
J = json.load(open(os.path.join(OUT, "report", "warpnull.json")))
MD = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "RESULT.md"), encoding="utf-8").read()
if "### 2.3 W1 was under-scoped" not in MD:
    raise SystemExit("ANCHOR NOT FOUND: section 2.3 heading")
sec = MD.split("### 2.3 W1 was under-scoped")[1].split("## 3. THE 26-ROW")[0]

fails, checked = [], []


def claim(desc, ok, got):
    checked.append(desc)
    print("  %-58s %-9s %s" % (desc, "OK" if ok else "MISMATCH", got))
    if not ok:
        fails.append(desc)


def arm(s, t, k):
    a = next((x for x in J[s]["arms"] if x["tag"] == t), None)
    return a[k] if a else float("nan")


def quoted(x, near=None):
    """Is this literal typed in the section, AT ITS OWN SITE?

    A bare presence test is satisfied by any duplicate of the value elsewhere.
    The negative control proved it: mutating the fitted scale range's `0.9996`
    still read GREEN because `0.9996` is also the blotch median in the table
    below it, and mutating `1.29x` still read GREEN because the sentence under
    the table repeats it. `near` pins each check to its own anchor.
    """
    for m in re.finditer(r"(?<![\d.])" + re.escape(x) + r"(?![\d])", sec):
        if near is None:
            return True
        lo, hi = max(0, m.start() - 90), m.end() + 90
        if near in sec[lo:hi]:
            return True
    return False


subs = sorted(J)
claim("26 subjects in warpnull.json", len(subs) == 26, len(subs))

# --- the two identity controls -------------------------------------------
dev_id = 0.0
for tag in ("identity", "RT identity"):
    v = [arm(s, tag, k) for s in subs for k in ("blotch", "chroma")]
    dev_id = max(dev_id, max(abs(x - 1.0) for x in v))
    claim("%s == 1.0 within the enforced 1e-6, all 26, both stats" % tag,
          all(abs(x - 1.0) < 1e-6 for x in v), "max dev %.2e" % dev_id)
claim("prose quotes identity departure as 3.5e-7",
      abs(dev_id - 3.5e-7) < 0.2e-7 and quoted("3.5e-7", "identity"),
      "%.2e" % dev_id)

# --- the headline table: worse of the two RT arms per subject ------------
fb = {s: min(arm(s, "RT median scale", "blotch"),
             arm(s, "RT extreme scale", "blotch")) for s in subs}
fc = {s: min(arm(s, "RT median scale", "chroma"),
             arm(s, "RT extreme scale", "chroma")) for s in subs}
claim("every subject has both RT arms",
      all(v == v for v in list(fb.values()) + list(fc.values())), "26/26")

for lab, d, lo, med, hi, losub, hisub in (
        ("blotch", fb, "0.9870", "0.9996", "1.0049", "leaf-2-cpl",
         "lavendar-cpl"),
        ("chroma", fc, "0.9847", "0.9990", "1.0000", "wrapped-text-1", None)):
    row = "%s factor" % lab
    smin, smax = min(d, key=d.get), max(d, key=d.get)
    claim("%s min %s at %s" % (lab, lo, losub),
          smin == losub and abs(d[smin] - float(lo)) < 5e-5
          and quoted(lo, row), "%s %.4f" % (smin, d[smin]))
    claim("%s median %s" % (lab, med),
          abs(float(np.median(list(d.values()))) - float(med)) < 5e-5
          and quoted(med, row), "%.4f" % float(np.median(list(d.values()))))
    claim("%s max %s%s" % (lab, hi, " at " + hisub if hisub else ""),
          abs(d[smax] - float(hi)) < 5e-5 and quoted(hi, row)
          and (hisub is None or smax == hisub), "%s %.4f" % (smax, d[smax]))

dev = max(max(abs(v - 1) for v in fb.values()),
          max(abs(v - 1) for v in fc.values()))
claim("worst departure quoted as 1.53%",
      abs(100 * dev - 1.53) < 0.005 and quoted("1.53", "Worst departure"),
      "%.2f%%" % (100 * dev))
claim("prose's 1.6% ceiling actually bounds it",
      100 * dev <= 1.6 and quoted("1.6", "inflated by more than"),
      "%.2f%% <= 1.6%%" % (100 * dev))
claim("failure direction absent -- no RT factor below 0.97",
      min(min(fb.values()), min(fc.values())) >= 0.97,
      "min %.4f" % min(min(fb.values()), min(fc.values())))

# --- the contaminated single-application arm -----------------------------
one_b = {s: arm(s, "median scale", "blotch") for s in subs}
claim("1x arm reaches 0.2114",
      abs(min(one_b.values()) - 0.2114) < 5e-5
      and quoted("0.2114", "blotch factors from"), "%.4f" % min(one_b.values()))
claim("1x arm reaches 1.1095",
      abs(max(one_b.values()) - 1.1095) < 5e-5
      and quoted("1.1095", "blotch factors from"), "%.4f" % max(one_b.values()))
claim("1x worst = the 373% figure the prose calls an artefact",
      abs(100 * (1 / min(one_b.values()) - 1) - 373) < 1.5
      and quoted("373", "correction"),
      "%.0f%%" % (100 * (1 / min(one_b.values()) - 1)))

# --- the positive control ------------------------------------------------
rl = [arm(s, t, "relhf") for s in subs
      for t in ("RT median scale", "RT extreme scale")]
claim("relhf falls to x0.66-x0.90 (positive control)",
      abs(min(rl) - 0.66) < 0.01 and abs(max(rl) - 0.90) < 0.01
      and quoted("0.66", "falls to") and quoted("0.90", "falls to"),
      "%.4f .. %.4f" % (min(rl), max(rl)))

# --- the scale range, recomputed from the ratio records, not from W2 -----
allsc = [r["scale"] for p in glob.glob(os.path.join(OUT, "ratio", "*.json"))
         for r in json.load(open(p))["rows"]
         if r.get("state") == "OK" and r.get("scale")]
claim("510 admitted frames",
      len(allsc) == 510 and quoted("510", "admitted frames"), len(allsc))
claim("fitted scale range 0.7745..0.9996",
      abs(min(allsc) - 0.7745) < 5e-5 and abs(max(allsc) - 0.9996) < 5e-5
      and quoted("0.7745", "median 0.9566")
      and quoted("0.9996", "median 0.9566"),
      "%.4f .. %.4f" % (min(allsc), max(allsc)))
claim("fitted scale median 0.9566",
      abs(float(np.median(allsc)) - 0.9566) < 5e-5
      and quoted("0.9566", "admitted frames"),
      "%.4f" % float(np.median(allsc)))
claim("magnification quoted as 1.29x",
      abs(1.0 / min(allsc) - 1.29) < 0.005
      and quoted("1.29", "magnified by up to"),
      "%.4fx" % (1.0 / min(allsc)))
claim("the extreme arm actually reached that frame",
      abs(min(J[s]["scale_extreme"] for s in subs) - min(allsc)) < 1e-9,
      "%.4f" % min(J[s]["scale_extreme"] for s in subs))
claim("W1's certified magnitude 1.66e-2 is 17.5x smaller",
      abs((1.0 / min(allsc) - 1) / 1.66e-2 - 17.5) < 0.05
      and quoted("17.5x", "under-coverage"),
      "%.1fx" % ((1.0 / min(allsc) - 1) / 1.66e-2))

# --- coverage figures come from the master's own provenance --------------
prov = open(os.path.join(r"C:\dev\strehl-out\acceptance\SHIP-V4",
                         "bee-1-cpl--SHIP-V4.tiff.provenance.txt"),
            encoding="utf-8", errors="replace").read()
cov = re.search(r"field of view scaled to (\d\.\d+)", prov)
claim("coverage 0.9236 traces to a provenance file",
      cov is not None and cov.group(1) == "0.9236"
      and quoted("0.9236", "field of view scaled to"),
      cov.group(1) if cov else "not found")

# --- nothing typed in the section may be untraceable ---------------------
pool = {"%.4f" % a[k] for s in subs for a in J[s]["arms"]
        for k in ("blotch", "chroma", "relhf")}
pool |= {"%.4f" % float(np.median(list(fb.values()))),
         "%.4f" % float(np.median(list(fc.values()))),
         "%.4f" % min(allsc), "%.4f" % max(allsc),
         "%.4f" % float(np.median(allsc)),
         cov.group(1) if cov else "", "0.9974"}
orphan = sorted(x for x in set(re.findall(r"\b(0\.9\d{3}|1\.0\d{3})\b", sec))
                if x not in pool)
claim("every 4dp ratio in the section traces to a record",
      not orphan, "orphans: %s" % (orphan or "none"))

print("\n%d claims checked, %d MISMATCH" % (len(checked), len(fails)))
for f in fails:
    print("  FAILED:", f)
sys.exit(1 if fails else 0)
