r"""Verify Part 16's numbers against the raw JSON the run wrote.

Each check is pinned to its OWN anchor line in the report, not to a bare value:
a presence test is satisfied by any duplicate of the number elsewhere in the
document. Outcomes are partitioned so a skipped check cannot read as a pass.
"""
import io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-GATHER.md"
txt = io.open(DOC, encoding="utf-8").read()
part16 = txt[txt.index("## Part 16"):]

ok = fail = skip = 0
def rep(name, good, detail):
    global ok, fail
    if good: ok += 1
    else: fail += 1
    print("  %-58s %s  %s" % (name, "PASS" if good else "**FAIL**", detail))

ROWS = {
 "119MSDCF": "119MSDCF",
 "dry-erase-marker-head-cpl": "dry-erase-marker-head-cpl",
 "bee-2-cpl": "bee-2-cpl",
 "leaf-2-cpl": "leaf-2-cpl",
 "wrapped-text-1": "wrapped-text-1",
}
print("A. section 16.6 table rows re-derived from bg_<subject>.json")
for sub, rowkey in ROWS.items():
    jf = os.path.join(HERE, "bg_%s.json" % sub)
    if not os.path.exists(jf):
        skip += 1
        print("  %-58s SKIPPED (no json)" % sub)
        continue
    d = json.load(io.open(jf, encoding="utf-8"))["arms"]["B coarse8 TREATMENT"]
    # anchor: the table row that STARTS with this subject inside part 16
    m = re.search(r"^\| %s \| [^|]*\| *([-+][0-9.]+)%% \| \[([-+][0-9.]+)%%, ?([-+][0-9.]+)%%\] \|"
                  % re.escape(rowkey), part16, re.M)
    if not m:
        skip += 1
        print("  %-58s SKIPPED (row not matched)" % sub)
        continue
    got = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
    want = (100*d["d_corr_bright"], 100*d["ci_bright"][1], 100*d["ci_bright"][2])
    good = all(abs(a-b) < 0.0006 for a, b in zip(got, want))
    rep(sub, good, "report %s  json %s" % (
        tuple(round(v,3) for v in got), tuple(round(v,3) for v in want)))

print("\nB. the null really is exactly zero (not merely small)")
for sub in ("leaf-2-cpl", "119MSDCF"):
    jf = os.path.join(HERE, "bg_%s.json" % sub)
    d = json.load(io.open(jf, encoding="utf-8"))["arms"]
    key = [k for k in d if k.startswith("NULL")]
    if not key:
        skip += 1; print("  %-58s SKIPPED (no null arm)" % sub); continue
    n = d[key[0]]
    rep("%s null == 0.0 exactly" % sub,
        n["d_corr_bright"] == 0.0 and n["ci_bright"][1] == 0.0
        and n["ci_bright"][2] == 0.0,
        "d=%r ci=%r" % (n["d_corr_bright"], n["ci_bright"][1:]))

print("\nC. per-subject USM potency values quoted in 16.5")
want_usm = {"leaf-2-cpl": 14.377, "wrapped-text-1": 7.399, "bee-2-cpl": 2.165,
            "dry-erase-marker-head-cpl": 2.140, "119MSDCF": 0.184}
for sub, v in want_usm.items():
    jf = os.path.join(HERE, "bg_%s.json" % sub)
    d = json.load(io.open(jf, encoding="utf-8"))["arms"]
    k = [x for x in d if x.startswith("USM")][0]
    got = 100*d[k]["d_corr_bright"]
    inrep = ("`+%.3f%%`" % v) in part16
    rep("USM %s" % sub, abs(got - v) < 0.001 and inrep,
        "json %+.3f%% report-quotes-it=%s" % (got, inrep))

print("\nD. claims that must NOT appear as passes")
rep("coffee-bubbles is marked REFUSED, not given a number",
    "*REFUSED*" in part16 and "coffee-bubbles | 3.1 -> 60.6% | *REFUSED*" in part16,
    "")
rep("the width column is explicitly disclaimed",
    "not evidence and must not be read as" in part16, "")
rep("section 15.3 correction is present",
    "My §15.3 is corrected" in part16, "")

total = ok + fail + skip
print("\npartition: %d checks = %d PASS + %d FAIL + %d SKIPPED" % (total, ok, fail, skip))
raise SystemExit(1 if (fail or skip) else 0)