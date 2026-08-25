"""M114 r27 -- verify every non-trivial number in docs/research/M114-ca-verify.md
against the committed JSON artefacts, or against the source file that owns it.

ORCH's fold gate rejects numbers that exist only in a script docstring. This
re-derives each claimed value from the artefact and requires it to appear in the
report NEAR AN ANCHOR, so that a decoy occurrence elsewhere in the document
cannot satisfy the check. A missing anchor is a hard error, not a pass.
"""
import io
import json
import os
import re
import sys

import numpy as np
import tifffile

B = r"C:\dev\strehl-out\M114-ca-verify"
REP = r"docs\research\M114-ca-verify.md"
raw = io.open(REP, encoding="utf-8").read()
# the report uses thin thousands separators: 21 380 -> 21380
txt = re.sub(r"(?<=\d) (?=\d\d\d\b)", "", raw)

d24 = json.load(open(os.path.join(B, "r24.json")))
d24d = json.load(open(os.path.join(B, "r24d.json")))
d25 = json.load(open(os.path.join(B, "r25.json")))
d26 = json.load(open(os.path.join(B, "r26.json")))
d26b = json.load(open(os.path.join(B, "r26b.json")))
d23 = json.load(open(os.path.join(B, "r21", "r23.json")))

checks, fails, noanchor = [], 0, 0


def ck(label, value, anchor, span=260):
    global fails, noanchor
    i = txt.find(anchor)
    if i < 0:
        print("  ANCHOR MISSING  %-46s anchor=%r" % (label, anchor[:40]))
        noanchor += 1
        return
    win = txt[max(0, i - 40):i + span]
    ok = value in win
    if not ok:
        fails += 1
    print("  %-4s %-46s %-14s" % ("ok" if ok else "FAIL", label, value))


print("== r24, the narrowing audit ==")
a = d24["A_16bit_RGB"]; g = d24["A_16bit_grey"]
ck("A rgb source levels", str(a["levels_source"]), "16-bit RGB |")
ck("A rgb PIL levels", str(a["levels_pil"]), "16-bit RGB |")
ck("A rgb loss factor", "%gx" % a["level_loss_factor"], "16-bit RGB |")
ck("A grey levels", str(g["levels_pil"]), "16-bit greyscale |")
ck("B tif count", str(d24["B_n_tifs"]), "TIFFs read by M114 probes")
hay = tifffile.imread(r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif")
ck("haystack realised levels", str(int(np.unique(hay).size)), "self-inflicted")
for r in d24d["rows"]:
    nm = r["needle"].replace("ZOOM-bee-3-cpl-", "").replace(".png", "")
    ck("r24d %s pos" % nm, "(%d, %d)" % (r["x16"], r["y16"]), "`" + nm + "`")
    ck("r24d %s tile" % nm, "%dx%d" % (r["tile"][1], r["tile"][0]), "`" + nm + "`")

print("== r25, the matrix ==")
for nm, row in zip("RGB", d25["crate"]):
    for v in row:
        ck("crate %s row %s" % (nm, v), "%.6f" % v, "CRATE  inv(rownorm", 420)
for k, v in d25["crate_leaks"].items():
    ck("crate leak %s" % k, "%.4f" % v, "| " + k.replace("->", " -> ") + " |", 80)
for k in ("green->red", "red->green", "blue->green"):
    ck("corpus leak %s" % k, "%.4f" % d25["corpus_leaks"][k],
       "| " + k.replace("->", " -> ") + " |", 80)
ck("E2 maxabs", "%.6f" % d25["crate_vs_doc_maxabs"], "**E2**")
ck("E3 maxabs", "%.6f" % d25["corpus_vs_doc_maxabs"], "**E3**")
ck("E5 fixture vs capture", "2e-8", "**E5**")

print("== r26 / r26b, the dose-response ==")
for n in ("fringe", "hairs", "neutral", "specular", "wing"):
    rs = [r for r in d26["rows"] if n in r["needle"]]
    ck("r26 %s realised@256" % n, str([r["realised"] for r in rs if r["nominal"] == 256][0]),
       "| `" + n + "` |", 70)
sp = [r for r in d26["rows"] if "specular" in r["needle"]]
fr = [r for r in d26["rows"] if "fringe" in r["needle"]]
ck("specular nom3 err", "%.2f px" % [r["err"] for r in sp if r["nominal"] == 3][0],
   "| `specular` | 3 |", 60)
ck("fringe nom2 err", "%.2f px" % [r["err"] for r in fr if r["nominal"] == 2][0],
   "| `fringe` | 2 |", 60)
# `| `specular` |` occurs first in the section 5.1 and 5.2 tables, which carry
# different quantities. Anchor on phrases unique to the two sites that state
# these values, and check BOTH renderings the report uses ("3 / 8" in the table,
# "3 of 8" in the fact), so a fix to one site cannot silently orphan the other.
for key in d26b:
    nm = re.search(r"cpl-([a-z]+)-", key).group(1)
    v = d26b[key]
    two = [r for r in v["rows"] if r["realised"] == 2]
    worst = max(r["err"] for r in two if not r["exact"])
    ck("r26b %s ratio (table)" % nm, "%d / %d" % (v["two_ok"], v["two_n"]),
       "worst failure at realised", 400)
    ck("r26b %s worst (table)" % nm, "%.2f px" % worst, "worst failure at realised", 400)
    ck("r26b %s ratio (fact)" % nm, "%d of %d" % (v["two_ok"], v["two_n"]),
       "threshold placement alone", 340)
    ck("r26b %s worst (fact)" % nm, "%.2f px" % worst, "threshold placement alone", 340)
areas = sorted({r["tile"][0] * r["tile"][1] for r in d24d["rows"]})
# anchor on the equals sign: bare "130x130" also occurs in the section 3 table,
# and str.find would resolve there -- a decoy site that carries no area.
ck("min template area", str(areas[0]), "130x130 = ", 40)
ck("max template area", str(areas[-1]), "170x170 = ", 40)

print("== section 2 cross-references ==")
ratio = abs(d23["119MSDCF"]["native"] / d23["bee-3-cpl"]["native"])
ck("scene ratio", "%.3f" % ratio, "scene-to-scene ratio")
ck("scene pct", "%.1f" % ((ratio - 1) * 100), "scene-to-scene ratio", 320)
m107 = io.open(r"docs\research\M107b-lateral-correction.md", encoding="utf-8").read()
for v in ("0.950", "0.541"):
    src = v in m107
    inrep = v in txt
    print("  %-4s L4 %s present in M107b=%s report=%s"
          % ("ok" if (src and inrep) else "FAIL", v, src, inrep))
    if not (src and inrep):
        fails += 1

print()
print("FAILS=%d  ANCHORS MISSING=%d" % (fails, noanchor))
sys.exit(1 if (fails or noanchor) else 0)
