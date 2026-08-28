r"""Verify Part 16 -- numbers AND conclusions.

Commissioned against conclusion-flipping mutations in bg_commission_verifier.py.
The previous version missed 4 of 6 because every conclusion check was a PRESENCE
test and the dose column was matched as `[^|]*`, i.e. not checked at all.

The rule now: a conclusion is RECOMPUTED from the data, the expected sentence is
BUILT from that recomputation, and the document must carry it verbatim exactly
once at its canonical site. Flipping the text then disagrees with the data and
reads RED, which a presence test cannot do.
"""
import glob, io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-GATHER.md"
LOGS = r"C:\dev\strehl-out\V-BANDFLOOR"
txt = io.open(DOC, encoding="utf-8").read()
part16 = txt[txt.index("## Part 16"):]

ok = fail = skip = 0
def rep(name, good, detail=""):
    global ok, fail
    if good: ok += 1
    else: fail += 1
    print("  %-56s %s  %s" % (name, "PASS" if good else "**FAIL**", detail))
SKIPS = []
# Declared, permanent skips. coffee-bubbles is REFUSED on the rim axis at the
# instrument floor, so it has no bg_<subject>.json to check. Declaring it lets
# the baseline be green WITHOUT letting a skip read as a pass: an UNDECLARED
# skip still fails the run, and the partition still prints every outcome.
EXPECTED_SKIPS = {"coffee-bubbles"}

def skipped(name, why):
    global skip
    skip += 1
    SKIPS.append(name)
    print("  %-56s SKIPPED  %s" % (name, why))

SUBS = ["coffee-bubbles", "119MSDCF", "dry-erase-marker-head-cpl",
        "bee-2-cpl", "leaf-2-cpl", "wrapped-text-1"]

def row(sub):
    m = re.search(r"^\| %s \|([^|]*)\|([^|]*)\|([^|]*)\|" % re.escape(sub), part16, re.M)
    return m

print("A. rim delta and CI re-derived from bg_<subject>.json")
spans = {}
for sub in SUBS:
    jf = os.path.join(HERE, "bg_%s.json" % sub)
    m = row(sub)
    if not os.path.exists(jf):
        skipped(sub, "no json (subject is REFUSED on this axis)"); continue
    if not m: skipped(sub, "row not matched"); continue
    d = json.load(io.open(jf, encoding="utf-8"))["arms"]["B coarse8 TREATMENT"]
    got = re.findall(r"[-+][0-9.]+", m.group(2) + " " + m.group(3))
    want = [100*d["d_corr_bright"], 100*d["ci_bright"][1], 100*d["ci_bright"][2]]
    good = len(got) >= 3 and all(abs(float(a)-b) < 0.0006 for a, b in zip(got[:3], want))
    spans[sub] = (d["ci_bright"][1] <= 0.0 <= d["ci_bright"][2])
    rep(sub, good, "report %s json %s" % (got[:3], [round(v,3) for v in want]))

print("\nB. the dose column re-derived from V-BANDFLOOR's render banners")
def band1(sub, arm):
    p = os.path.join(LOGS, "%s__%s.log" % (sub, arm))
    if not os.path.exists(p): return None
    for line in io.open(p, encoding="utf-8", errors="replace"):
        mm = re.match(r"\s*averaged\s*:\s*(.*)$", line)
        if mm:
            vals = re.findall(r"([0-9.]+)%", mm.group(1))
            return float(vals[1]) if len(vals) > 1 else None
    return None

for sub in SUBS:
    m = row(sub)
    if not m: skipped(sub, "row not matched"); continue
    a, b = band1(sub, "A-unset"), band1(sub, "B-coarse8")
    if a is None or b is None: skipped(sub, "banner not found in logs"); continue
    dm = re.search(r"([0-9.]+)%?\s*->\s*([0-9.]+)%", m.group(1))
    if not dm: rep(sub, False, "dose cell unparseable: %r" % m.group(1)); continue
    good = abs(float(dm.group(1))-a) < 0.05 and abs(float(dm.group(2))-b) < 0.05
    rep(sub, good, "report %s->%s  banner %.1f->%.1f" % (dm.group(1), dm.group(2), a, b))

print("\nC. the null is exactly zero, and the USM potency arms")
for sub in ("leaf-2-cpl", "119MSDCF"):
    d = json.load(io.open(os.path.join(HERE, "bg_%s.json" % sub), encoding="utf-8"))["arms"]
    n = d[[k for k in d if k.startswith("NULL")][0]]
    rep("%s null == 0.0 exactly" % sub,
        n["d_corr_bright"] == 0.0 and n["ci_bright"][1] == 0.0 and n["ci_bright"][2] == 0.0)
for sub, v in {"leaf-2-cpl":14.377, "wrapped-text-1":7.399, "bee-2-cpl":2.165,
               "dry-erase-marker-head-cpl":2.140, "119MSDCF":0.184}.items():
    d = json.load(io.open(os.path.join(HERE, "bg_%s.json" % sub), encoding="utf-8"))["arms"]
    got = 100*d[[x for x in d if x.startswith("USM")][0]]["d_corr_bright"]
    rep("USM potency %s" % sub, abs(got-v) < 0.001 and ("`+%.3f%%`" % v) in part16,
        "%+.3f%%" % got)

print("\nD. CONCLUSIONS -- recomputed from the data, then required verbatim")
n_meas = len(spans)
n_span = sum(1 for v in spans.values() if v)
unmoved = n_span >= n_meas - 1 and n_meas >= 4
print("     recomputed: %d of %d measurable subjects have a CI spanning zero"
      " -> rim %s" % (n_span, n_meas, "UNMOVED" if unmoved else "MOVED"))

exp = ("**The first condition fired. Rim is unmoved**" if unmoved
       else "**No condition fired. Rim moved materially**")
rep("D1 headline verdict matches the recomputation", part16.count(exp) == 1,
    "expected %r x1, found %d" % (exp[:46], part16.count(exp)))

exp2 = ("So **rim is not a coarse-scale selection artifact" if unmoved
        else "So **rim IS a coarse-scale selection artifact")
rep("D2 mechanism conclusion matches the recomputation", part16.count(exp2) == 1,
    "found %d" % part16.count(exp2))

det = [float(x) for x in re.findall(r"^\| [^|]+ \| \*{0,2}[0-9.]+\*{0,2} \| ([0-9.]+) \|$",
                                    part16, re.M)]
flat = [float(x) for x in re.findall(r"^\| [^|]+ \| \*{0,2}([0-9.]+)\*{0,2} \| [0-9.]+ \|$",
                                     part16, re.M)]
if len(det) != 6 or len(flat) != 6:
    skipped("D3 third-condition verdict", "split table parsed %d/%d rows" % (len(flat), len(det)))
    skipped("D4 prose agrees with the split table", "split table not parsed")
else:
    no_soften = min(det) >= 1.0
    exp3 = ("The third condition - the trap - **does not arise**" if (unmoved and no_soften)
            else "The third condition - the trap - **fired**")
    rep("D3 third-condition verdict matches the recomputation",
        part16.count(exp3) == 1, "min detail %.4f, unmoved=%s" % (min(det), unmoved))
    rep("D4 prose's detail floor equals the table's minimum",
        ("detail energy is >= %.4f everywhere" % min(det)) in part16,
        "table min %.4f" % min(det))
    rep("D5 prose's noise figure equals the table's minimum",
        ("falls by up to %.1f%%" % (100*(1-min(flat)))) in part16,
        "table min flat %.4f -> %.1f%%" % (min(flat), 100*(1-min(flat))))

print("\nE. verdict tokens that must not soften into a pass")
rep("E1 coffee-bubbles carries REFUSED, not a number",
    "| coffee-bubbles | 3.1 -> 60.6% | *REFUSED*" in part16)
rep("E2 the width column is disclaimed",
    "not evidence and must not be read as" in part16)
rep("E3 my own \u00a715.3 correction is present",
    "My \u00a715.3 is corrected" in part16)

total = ok + fail + skip
print("\npartition: %d checks = %d PASS + %d FAIL + %d SKIPPED" % (total, ok, fail, skip))
unexpected = sorted(set(SKIPS) - EXPECTED_SKIPS)
missing = sorted(EXPECTED_SKIPS - set(SKIPS))
if unexpected:
    print("UNDECLARED SKIP(S): %s -- a skip that was not predicted is a failure" % unexpected)
if missing:
    print("DECLARED SKIP DID NOT OCCUR: %s -- the declaration is stale" % missing)
print("verdict: %s" % ("GREEN" if not (fail or unexpected or missing) else "RED"))
raise SystemExit(1 if (fail or unexpected or missing) else 0)