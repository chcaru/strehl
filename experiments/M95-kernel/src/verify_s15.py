"""Verify M95-kernel.md section 15 against the JSON its runs wrote.

Same two-pass PRESENT / DISCRIMINATE discipline as verify_s14.py, and the same
two defects already paid for once: the section is sliced with a line-anchored
regex (splitting on "## 15." also matches every "### 15.N" subheading and
silently truncates the section to its first paragraph), and short tokens
discriminate on a context anchor rather than on the bare digits.

REWRITTEN after K19/K19b refuted section 15.1's headline. This gate previously
asserted "no true-1 arm read 0", which is true of k11_exitcode.json and FALSE
of the shell. It now asserts three things instead:

  * the K11 rows still quoted in 15.1 match k11_exitcode.json exactly;
  * 15.1 carries the RETRACTION and no longer asserts the refuted mechanism;
  * 15.3's table is reconstructed cell-by-cell from k19b_seeds.json.

Row reconstruction from the artifact is used rather than presence-checking
individual values: a bare "1" or "0" occurs everywhere in this prose, so a
presence check on a short token is worthless here (weak-check failure mode 1),
and a value stated twice can pass while one copy is wrong (failure mode 6).
"""

import json
import os
import re
import sys
import traceback
from pathlib import Path

# Discipline 702: this gate reports through stdout and its exit code is read as
# a claim. Python picks the ANSI codepage for piped stdout, which is every agent
# tool call and every CI log, and cp1252 cannot encode the minus signs and arrows
# this corpus uses. Without this, print() raises mid-run and the process exits 1:
# indistinguishable from a real failure. Measured in k18_gate702.py.
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


def _broke(exc_type, exc, tb):
    traceback.print_exception(exc_type, exc, tb)
    print("\nVERIFIER BROKE (exit 2) -- this is NOT a claim about the report.")
    sys.stdout.flush()
    os._exit(2)


sys.excepthook = _broke

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
OUT = ROOT / "experiments" / "M95-kernel" / "out"

k11 = json.loads((OUT / "k11_exitcode.json").read_text(encoding="utf-8"))
k19 = json.loads((OUT / "k19_preclear.json").read_text(encoding="utf-8"))
k19b = json.loads((OUT / "k19b_seeds.json").read_text(encoding="utf-8"))

raw = REPORT.read_text(encoding="utf-8", errors="replace")
m = re.search(r"^## 15\. ", raw, re.M)
if not m:
    raise SystemExit("section 15 not found")
nxt = re.search(r"^## 16\. ", raw[m.start():], re.M)
sec = raw[m.start(): m.start() + nxt.start()] if nxt else raw[m.start():]
if len(sec.splitlines()) < 40:
    raise SystemExit(f"section 15 implausibly short ({len(sec.splitlines())} lines)")
flat = re.sub(r"\s+", " ", sec)


def decoy(s: str) -> str:
    mm = re.search(r"\d(?=[^\d]*$)", s)
    if not mm:
        return s + "0"
    i = mm.start()
    return s[:i] + str((int(s[i]) + 1) % 10) + s[i + 1:]


ok = True
print("=" * 82)
print("verify M95-kernel.md section 15  (PRESENT / DISCRIMINATE)")
print("=" * 82)

# ---- pass 1: K11 values still quoted in 15.1 -------------------------------
claims = []
shells = k11["shells"]
for name, blk in shells.items():
    claims.append((f"version {name}", blk["version"], blk["version"]))
total_arms = sum(len(b["rows"]) for b in shells.values())
claims.append(("total arms", str(total_arms), f"{total_arms} arms"))

quoted = [
    ("pwsh (7.x)", "slow exit1  no pipeline"),
    ("pwsh (7.x)", "slow exit1  | -First 3 of 10"),
    ("pwsh (7.x)", "slow exit0  | -First 3 of 10"),
    ("pwsh (7.x)", "slow exit1  | -First 99"),
    ("powershell (5.1)", "slow exit1  | -First 3 of 10"),
    ("powershell (5.1)", "slow exit0  | -First 3 of 10"),
    ("powershell (5.1)", "fast exit1  | -First 3 of 10"),
]
for shell, arm in quoted:
    row = next(r for r in shells[shell]["rows"] if r["arm"] == arm)
    claims.append((f"{shell[:4]} {arm[:22]} secs", f"{row['seconds']:.1f}", None))
    if row["read_code"] is not None and row["read_code"] < 0:
        # A bare "-1" cannot discriminate: its decoy "-2" occurs by chance in
        # the ISO date "2026-08-24" added by the retraction note. Anchor the
        # value on its neighbouring cell instead (weak-check failure mode 1).
        claims.append((f"{shell[:4]} {arm[:22]} code", str(row["read_code"]),
                       f"**{row['read_code']}** | {row['seconds']:.1f}"))

for label, text, ctx in claims:
    present = text in flat
    target = ctx if ctx else text
    dec = decoy(target)
    discriminates = dec not in flat if dec != target else True
    if ctx and ctx not in flat:
        present = False
    good = present and discriminates
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<36} {text!r:>12}  present={present} disc={discriminates}")

# ---- pass 2: the disconfirming K11 row must be acknowledged ----------------
print("-" * 82)
pwsh_fast = next(r for r in shells["pwsh (7.x)"]["rows"]
                 if r["arm"] == "fast exit1  | -First 3 of 10")
good = pwsh_fast["read_code"] is None and "wrong (None)" in flat
ok &= good
print(f"  {'OK ' if good else 'BAD'}  {'K11 disconfirming row cited':<36} "
      f"pwsh fast -First read_code={pwsh_fast['read_code']!r}")

# ---- pass 3: 15.3 table reconstructed from k19b ----------------------------
print("-" * 82)
triples = {}
for sname, blk in k19b["shells"].items():
    for row in blk["rows"]:
        t = tuple(row["cells"][str(s)] for s in k19b["seeds"])
        triples[t] = triples.get(t, 0) + 1

for t, n in sorted(triples.items()):
    pat = r"\|\s*\**" + r"\**\s*\|\s*\**".join(re.escape(c) for c in t) + r"\**\s*\|"
    found = len(re.findall(pat, flat))
    good = found == n
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {'15.3 row cells ' + str(t):<36} "
          f"expected {n} occurrence(s), found {found}")

# ---- pass 4: verdicts and the retraction -----------------------------------
print("-" * 82)
structural = [
    ("K19b verdict stated", k19b["verdict"]),
    ("K19 verdict stated", "VERDICT-STAND"),
    ("15.1 headline retracted", "RETRACTED"),
    ("orchestrator vindicated", "ORIGINAL REPORT WAS RIGHT"),
    ("wrong mechanism struck", "STRUCK"),
    ("real mechanism named", "never assigns"),
    ("fresh session measured unset", "Isolation holds"),
    ("seed discriminates 4 outcomes", "a pre-clear to 0 cannot"),
    ("pwsh quota condition", "N \u2264 objects"),
    ("5.1 is the race", "genuine race"),
    ("5.1 fails closed", "fails closed"),
    ("operative rule restated",
     "never read `$LASTEXITCODE` after a pipeline containing `-First`"),
    ("safe list measured", "`-Last` and `Out-String` are measured safe"),
    ("self-criticism recorded", "not a positive control for the conclusion"),
    ("excerpt-not-artifact named", "rather than from the artifact I had generated"),
    ("remedy endorsed", "capture first, then filter"),
    ("output half confirmed", "3 of 10 lines"),
    ("own gates audited", "subprocess.run"),
    ("library still clean", "count = 0"),
    ("frames-40 file identified", "112MSDCF-A"),
    ("stale binary residual", "8118dd7"),
    ("15.4 pre-registered", "committed at `817038d` before the"),
    ("15.4 boundary confirmed on pwsh", "Quota confirmed"),
    ("15.4 5.1 non-determinism", "a coin flip"),
    ("15.4 Select-String protects on 5.1", "PROTECTS on 5.1 and does nothing on pwsh"),
    ("15.4 M104c vindicated", "M104c was\nmost likely right and measuring 5.1"),
    ("15.4 -File is a real variable", "the invocation\nmode is a real variable"),
    ("15.4 prediction scored", "which was half wrong"),
    ("15.4 rule unchanged", "The operative rule is untouched"),
    ("15.4 rationale warning", "a mechanism stated more confidently than it was"),
]
for label, text in structural:
    good = re.sub(r"\s+", " ", text) in flat
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<36} {text[:46]!r}")

# ---- pass 5: the refuted claims must not be ASSERTED any more --------------
# House practice is to retract in place, not to delete, so "absent" is the
# wrong test: a struck claim is still visible and must stay visible. The
# correct test is that any surviving copy sits inside a ~~strikethrough~~.
print("-" * 82)
struck_spans = " ".join(re.sub(r"\s+", " ", s)
                        for s in re.findall(r"~~(.+?)~~", sec, re.S))
retracted = [
    ("failure never read as success",
     "A failing command was never read as success"),
    ("gate never executes", "never executes"),
    ("fast arms all correct",
     "Every fast-probe arm is correct on both shells"),
]
for label, text in retracted:
    t = re.sub(r"\s+", " ", text)
    present = t in flat
    struck = t in struck_spans
    good = (not present) or struck
    ok &= good
    state = "deleted" if not present else ("struck" if struck else "STILL ASSERTED")
    print(f"  {'OK ' if good else 'BAD'}  {label:<36} {state}")

# ---- pass 5b: 15.4 tables reconstructed row-by-row from k19c ---------------
print("-" * 82)
k19c = json.loads((OUT / "k19c_quota.json").read_text(encoding="utf-8"))
by_version = {b["version"]: b for b in k19c["shells"].values()}
HOSTNAME = {"pwsh 7.6.5": "7.6.5", "powershell 5.1": "5.1.26100.9168"}


def cells_of(line):
    parts = [c.strip().replace("**", "") for c in re.split(r"(?<!\\)\|", line)]
    return [c for c in parts[1:-1]] if len(parts) >= 3 else []


main_rows, file_rows = 0, 0
for line in sec.splitlines():
    line = line.strip()
    if not line.startswith("| pwsh 7.6.5 |") and not line.startswith("| powershell 5.1 |"):
        continue
    c = cells_of(line)
    if len(c) == 7 and c[2].isdigit():
        host, arm, objs, n, s0, s7, verdict = c
        shape = "ss" if "SS" in arm else ("last" if "-Last" in arm else "direct")
        blk = by_version[HOSTNAME[host]]
        match = [r for r in blk["rows"]
                 if r["objects"] == int(objs) and r["N"] == int(n) and r["shape"] == shape]
        good = (len(match) == 1
                and ",".join(match[0]["seed0"]) == s0
                and ",".join(match[0]["seed7"]) == s7
                and match[0]["verdict"].split(" (")[0] in verdict)
        ok &= good
        main_rows += 1
        if not good:
            print(f"  BAD  15.4 row {host} {arm} objs={objs} N={n}: report {s0}/{s7}/{verdict!r} "
                  f"vs artifact {match[0] if len(match) == 1 else match}")
    elif len(c) == 5:
        host, f0, f7, c0, c7 = c
        fm = k19c["file_mode"][next(k for k, v in k19c["shells"].items()
                                    if v["version"] == HOSTNAME[host])]
        good = (",".join(fm["File"]["0"]) == f0 and ",".join(fm["File"]["7"]) == f7
                and ",".join(fm["Command"]["0"]) == c0 and ",".join(fm["Command"]["7"]) == c7)
        ok &= good
        file_rows += 1
        if not good:
            print(f"  BAD  15.4 -File row {host}: report {f0}/{f7}/{c0}/{c7} vs artifact {fm}")

good = main_rows == 13 and file_rows == 2
ok &= good
print(f"  {'OK ' if good else 'BAD'}  {'15.4 rows reconstructed':<36} "
      f"{main_rows} quota rows (expect 13), {file_rows} -File rows (expect 2)")

quota = {n: b["quota"] for n, b in k19c["shells"].items()}
good = quota.get("pwsh 7.x") == "HOLDS" and quota.get("powershell 5.1") == "REFUTED"
ok &= good
print(f"  {'OK ' if good else 'BAD'}  {'15.4 artifact verdicts':<36} {quota}")

# ---- pass 6: the artifacts must actually support 15.3 ----------------------
print("-" * 82)
fg = k19b["false_green"]
good = len(fg) > 0 and k19b["verdict"] == "FALSE-GREEN-CONFIRMED"
ok &= good
print(f"  {'OK ' if good else 'BAD'}  {'k19b artifact holds the false green':<36} "
      f"{len(fg)} arm(s): {[a for _, a in fg]}")

unset_all = all(b["arm0_unset"] for b in k19["shells"].values())
good = unset_all and k19["verdict"] == "STAND"
ok &= good
print(f"  {'OK ' if good else 'BAD'}  {'k19 artifact: fresh session unset':<36} "
      f"arm0_unset={unset_all} verdict={k19['verdict']}")

print("=" * 82)
print(f"verdict: {'GREEN' if ok else 'RED'}")
print("=" * 82)
sys.exit(0 if ok else 1)
