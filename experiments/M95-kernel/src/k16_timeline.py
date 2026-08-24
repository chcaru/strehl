"""K16 -- do the returning sidecars post-date the fix, or a stale binary?

The orchestrator reports coffee-bean/warpmap.txt returning three times
(10:27:37, 10:31:11, 10:33:42) and concludes "quarantining is not remediation;
the file returns within minutes", asking for a code fix. But the code fix
landed at 8118dd7. This decides whether current source can still produce those
files, because the remedy differs: if current source is clean, the remaining
route is STALE PER-AGENT BINARIES, and no further source change stops them.

BARS, REGISTERED BEFORE THE RUN
-------------------------------
T1 WHEN DID THE FIX LAND. Read 8118dd7's author time from git, not from notes.

T2 IS CURRENT SOURCE CLEAN. sidecar_path() at HEAD must resolve under
   cache_root() and must not join the stack dir. Checked by reading the HEAD
   blob as bytes via subprocess -- never via a shell redirect, which re-encodes.

T3 CLASSIFY THE THREE TIMES. Each cited timestamp is either BEFORE the fix
   (explained by old code) or AFTER (needs another explanation).

T4 CONTROL, and it can fail: if ALL three post-date the fix, T2 is either wrong
   or irrelevant and I must say the fix is incomplete. This bar is what stops
   T2 from being a foregone conclusion.
"""

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
QUAR = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True).stdout.decode(
        "utf-8", errors="replace")


print("=" * 78)
print("K16  are the returning sidecars explained by current source?")
print("=" * 78)

iso = git("log", "-1", "--format=%ad", "--date=iso", "8118dd7").strip()
fix = datetime.fromisoformat(iso)
print(f"\nT1  fix 8118dd7 landed : {iso}")
print(f"    subject             : {git('log', '-1', '--format=%s', '8118dd7').strip()}")

blob = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:crates/strehl-cli/src/align_cmd.rs"],
                      capture_output=True).stdout.decode("utf-8")
m = re.search(r"pub fn sidecar_path\(.*?\n\}", blob, re.S)
body = m.group(0) if m else ""
uses_cache = "cache_root()" in body
joins_dir = bool(re.search(r"dir\.join\(", body))
print(f"\nT2  HEAD sidecar_path uses cache_root() : {uses_cache}")
print(f"    HEAD sidecar_path joins the stack dir: {joins_dir}")
t2 = uses_cache and not joins_dir
print(f"    T2 {'PASS -- current source cannot write into the stack dir' if t2 else 'FAIL'}")

cited = ["10:27:37", "10:31:11", "10:33:42"]
print("\nT3  the three cited coffee-bean timestamps")
after = 0
for c in cited:
    h, mi, s = (int(x) for x in c.split(":"))
    t = fix.replace(hour=h, minute=mi, second=s, microsecond=0)
    delta = (t - fix).total_seconds()
    tag = "AFTER the fix" if delta > 0 else "BEFORE the fix"
    if delta > 0:
        after += 1
    print(f"    {c}  {delta:>+8.0f} s vs the fix   {tag}")

t4 = after < len(cited)
print(f"\nT4  control: not all three post-date the fix -> "
      f"{'PASS' if t4 else 'FAIL -- the fix would be incomplete and I must say so'}")
print(f"    {after}/{len(cited)} post-date it")

print("\n--- quarantined coffee-bean files, mtimes read from disk ---")
now = datetime.now().astimezone()
for f in sorted(QUAR.glob("*coffee-bean*")):
    mt = datetime.fromtimestamp(f.stat().st_mtime).astimezone()
    mm = re.search(r"^frames (\d+)", f.read_text(encoding="utf-8", errors="replace"), re.M)
    age = (now - mt).total_seconds() / 60.0
    print(f"    {f.name:<46} {mt:%H:%M:%S}  frames {mm.group(1) if mm else '?':>3}"
          f"  {age:6.0f} min old")

print("\n--- CONCLUSION ---")
if t2 and t4:
    print("    Current source is clean and at least one cited file predates the fix.")
    print("    The remaining route is STALE PER-AGENT BINARIES built before 8118dd7.")
    print("    No further source change stops those; the target-*/ trees must be rebuilt.")
else:
    print("    The fix does not account for the observations; report it as incomplete.")
sys.exit(0 if (t2 and t4) else 1)
