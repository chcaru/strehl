"""Re-derive section 32 of docs/research/M87-occlusion.md.

The claim that matters here is a NEGATIVE one -- "M87 never passed --limit"
-- and a negative recorded as a number in a JSON file is worth nothing,
because the file records what I believed when I wrote it. So this verifier
re-counts `--limit` across the script tree from disk rather than reading
`93-audit.json`'s zero, and cross-checks the two against each other.

Everything else is re-derived from `51-zoomnull.json`, and the frozen binary
is re-hashed rather than quoted.
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
SRC = pathlib.Path(__file__).resolve().parent
DATA = SRC.parent / "data"
BIN = pathlib.Path(r"C:\dev\strehl-out\M87-bee\bin\strehl-m87.exe")

fails, checks = [], 0
doc = DOC.read_bytes().decode("utf-8")
i = doc.index("## 32. Two hazards")
facts = [l for l in doc.split("\r\n") if re.match(r"\| P12[456] \|", l)]
flat = re.sub(r"\s+", " ", doc[i:] + "\r\n" + "\r\n".join(facts))


def chk(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)


def count(text, n, msg):
    global checks
    checks += 1
    got = flat.count(text)
    if got != n:
        fails.append(f"{msg}: expected {n}x {text!r}, found {got}")


z = json.loads((DATA / "51-zoomnull.json").read_text(encoding="utf-8"))
a = json.loads((DATA / "93-audit.json").read_text(encoding="utf-8"))

# ---- the negative claim, re-counted from disk -------------------------
# P124 rests on two zeros. Both are re-counted here rather than read from
# 93-audit.json, because a negative recorded in a file records only what I
# believed when I wrote it. The scan is scoped to MEASUREMENT scripts: the
# append/verify/control/fix harness quotes both `--limit` and the binary
# name in prose and plant payloads, and counting those measures nothing.
scripts = sorted(SRC.glob("*.py"))
harness = ("append", "verify", "control", "fix")
measure = [p for p in scripts if not p.name.startswith(harness)]
hits, invoke = [], []
for p in measure:
    t = p.read_text(encoding="utf-8")
    for k, line in enumerate(t.splitlines(), 1):
        if re.search(r"--limit\b", line):
            hits.append(f"{p.name}:{k}")
    if "subprocess" in t and re.search(r"strehl[-\w]*\.exe", t):
        invoke.append(p.name)
chk(not hits, f"--limit found in measurement scripts, contradicting P124: {hits[:5]}")
chk(not invoke, f"a measurement script invokes the binary: {invoke[:5]}")
chk(a["limit_flags_in_m87"] == 0, "93-audit.json disagrees with the re-count")
chk(a["scripts_total"] == len(scripts),
    f"audit records {a['scripts_total']} scripts, disk has {len(scripts)}")
chk(a["scripts_measurement"] == len(measure),
    f"audit records {a['scripts_measurement']} measurement, disk has {len(measure)}")
chk(a["scripts_invoking_binary"] == len(invoke), "audit invoke count stale")
count(f"**0** times in the {len(measure)} measurement scripts", 1, "script count")
count(f"**{len(scripts)}**", 1, "total scripts")

# ---- the watershed bound ---------------------------------------------
un, al = z["ZOOMNULL"]["before"], z["ALIGNED"]["before"]
share = 100.0 * (un - al) / un
chk(abs(share - a["align_share_of_halo_pct"]) < 1e-9, "audit share not re-derived")
chk(abs(share - 6.86) < 0.005, f"align share {share}")
chk(abs(z["ratio"] - z["ZOOMNULL"]["delta_pct"] / z["ALIGNED"]["delta_pct"])
    < 1e-9, "ratio is not the quotient of the two deltas")
chk(abs(z["ratio"] - 1.135) < 5e-4, f"ratio {z['ratio']}")
chk(abs(un - 0.06878) < 5e-6, f"unaligned {un}")
chk(abs(al - 0.06406) < 5e-6, f"aligned {al}")
chk(abs(z["ZOOMNULL"]["delta_pct"] - 82.76) < 0.005, "unaligned delta")
chk(abs(z["ALIGNED"]["delta_pct"] - 72.93) < 0.005, "aligned delta")
chk(abs(100 - share - 93.1) < 0.05, "intact share")
count("**6.86%**", 1, "align share, bolded in 32.2")
count("6.86%", 3, "align share, all sites (32.2 heading, body, P125)")
count("**0.06878**", 2, "unaligned ISO")
count("**0.06406**", 2, "aligned ISO")
count("**82.76%**", 2, "unaligned removal")
count("**72.93%**", 2, "aligned removal")
count("**1.135**", 2, "ratio")
count("93.1%", 1, "intact")
count("27 of M87's data files", 2, "pre-align file count")
count("2026-08-24 03:15:23", 2, "watershed timestamp")
chk(a["pre_align_data_files"] == 27, "audit pre-align count")
chk(a["watershed"].startswith("2026-08-24T03:15:23"), "audit watershed")

# ---- the provenance repair -------------------------------------------
h = hashlib.sha256(BIN.read_bytes()).hexdigest()[:24]
chk(h == a["binary_sha24"], f"binary hash moved: {h} vs {a['binary_sha24']}")
chk(doc.count(h) == 1, f"binary hash appears {doc.count(h)}x, want 1")
chk(a["default_gate"] == 4.0, "recorded default gate")
prov = doc[doc.index("### 31.1"):doc.index("### 31.2")]
chk("--srgb --auto-exposure" in prov, "31.1 lost the invocation")
chk("gate           : 4.0" in prov, "31.1 does not record the gate value")
chk("merge.rs:297" in prov, "31.1 does not cite the gate's source")
chk(h in prov, "31.1 does not record the binary hash")
chk("no --gate flag was passed" in prov, "31.1 hides that the gate defaulted")

# ---- the gate default, re-read from the Rust source ------------------
merge = (ROOT / "crates" / "strehl-core" / "src" / "merge.rs").read_text(
    encoding="utf-8", errors="replace")
m = re.search(r"pub const DEFAULT_GATE: f32 = ([\d.]+);", merge)
chk(m is not None, "DEFAULT_GATE not found in merge.rs")
if m:
    chk(float(m.group(1)) == 4.0,
        f"DEFAULT_GATE is now {m.group(1)}; 31.1's record is stale")

# ---- structure and hygiene -------------------------------------------
chk("## 32. Two hazards audited against this milestone" in doc, "s32 missing")
for sub in ("32.1", "32.2", "32.3", "32.4"):
    count(f"### {sub}", 1, "subsection")
for fid in ("P124", "P125", "P126"):
    rows = [l for l in doc.split("\r\n") if l.startswith(f"| {fid} |")]
    chk(len(rows) == 1, f"{fid}: {len(rows)} fact rows")
    if rows:
        n = len(re.findall(r"(?<!\\)\|", rows[0]))
        chk(n == 5, f"{fid}: {n} unescaped pipes, want 5")
        chk(rows[0].count("`") % 2 == 0, f"{fid}: unbalanced backticks")
        chk(rows[0].rstrip().endswith("| MEASURED |"), f"{fid}: status")
bad = [hex(ord(c)) for c in doc if ord(c) < 0x20 and c not in "\r\n"]
chk(not bad, f"C0 control characters: {bad[:5]}")
chk(doc.count("\n") == doc.count("\r\n"), "mixed line endings")

print(f"{checks} checks, {len(fails)} failures")
for f in fails:
    print(f"  FAIL {f}")
sys.exit(1 if fails else 0)
