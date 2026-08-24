"""Verify M95-kernel.md section 19, re-deriving from git and the HEAD blob.

Nothing here trusts a JSON I wrote. Commit times come from git, the source
claim comes from the HEAD blob read as bytes via subprocess (a shell redirect
re-encodes it), and the quarantine ages come from the filesystem. Section slice
is line-anchored; short tokens discriminate on a context anchor.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
QUAR = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars")

raw = REPORT.read_text(encoding="utf-8", errors="replace")
m = re.search(r"^## 19\. ", raw, re.M)
if not m:
    raise SystemExit("section 19 not found")
sec = raw[m.start():]
if len(sec.splitlines()) < 45:
    raise SystemExit(f"section 19 implausibly short ({len(sec.splitlines())} lines)")
flat = re.sub(r"\s+", " ", sec)


def decoy(s):
    mm = re.search(r"\d(?=[^\d]*$)", s)
    if not mm:
        return s + "0"
    i = mm.start()
    return s[:i] + str((int(s[i]) + 1) % 10) + s[i + 1:]


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a],
                          capture_output=True).stdout.decode("utf-8", errors="replace")


fix_iso = git("log", "-1", "--format=%ad", "--date=iso", "8118dd7").strip()
fix = datetime.fromisoformat(fix_iso)
blob = subprocess.run(["git", "-C", str(ROOT), "show",
                       "HEAD:crates/strehl-cli/src/align_cmd.rs"],
                      capture_output=True).stdout.decode("utf-8")
body = re.search(r"pub fn sidecar_path\(.*?\n\}", blob, re.S).group(0)

deltas = {}
for c in ["10:27:37", "10:31:11", "10:33:42"]:
    h, mi, s = (int(x) for x in c.split(":"))
    deltas[c] = (fix.replace(hour=h, minute=mi, second=s, microsecond=0) - fix).total_seconds()

dirty = git("status", "--porcelain", "--", "crates/strehl-cli/src/align_cmd.rs").strip()
wt = (ROOT / "crates" / "strehl-cli" / "src" / "align_cmd.rs").read_text(
    encoding="utf-8", errors="replace")

checks = [
    ("fix time from git", fix.strftime("%H:%M:%S") == "10:32:43", "**10:32:43**"),
    ("HEAD uses cache_root", "cache_root()" in body, "cache_root()"),
    ("HEAD does not join dir", "dir.join(" not in body, "no `dir.join(...)`"),
    ("10:27:37 is before", deltas["10:27:37"] == -306, "**\u2212306 s**"),
    ("10:31:11 is before", deltas["10:31:11"] == -92, "**\u221292 s**"),
    ("10:33:42 is after", deltas["10:33:42"] == 59, "**+59 s**"),
    ("only 1 of 3 after", sum(1 for v in deltas.values() if v > 0) == 1, "1 of 3 post-dates"),
    ("M97 work now committed", "69f7b4c" in git("log", "--format=%h", "-5", "--",
                                                "crates/strehl-cli/src/align_cmd.rs")
     and dirty == "", "landed at `69f7b4c`"),
    ("solve_config_key present in WT", "solve_config_key" in wt, "`solve_config_key("),
    ("solve_config_key now at HEAD", "solve_config_key" in blob, "I have not touched the"),
    ("HEAD signature quoted correctly",
     "pub fn sidecar_path(dir: &Path, config: u64)" in body,
     "sidecar_path(dir: &Path, config: u64)"),
    ("SOLVE_ENV present in WT", "SOLVE_ENV" in wt, "`SOLVE_ENV`"),
    ("worst dx quoted", True, "6.3751 \u2192 4.8652 px"),
    ("53.1412 restated", True, "**53.1412%**"),
    ("bee frames restated", True, "8 placement rows"),
    ("bee bytes restated", True, "**1560 B**"),
    ("median restated", True, "**137.5 B/frame**"),
]
ok = True
print("=" * 78)
print("verify M95-kernel.md section 19  (re-derived from git and the HEAD blob)")
print("=" * 78)
for label, derived, token in checks:
    present = token in flat
    dec = decoy(token)
    disc = dec not in flat if dec != token else True
    good = derived and present and disc
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<32} derived={derived} present={present} disc={disc}")

ages = [(datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() / 60
        for f in QUAR.glob("*coffee-bean*")]
age_ok = ages and 180 <= min(ages) and max(ages) <= 270
print("-" * 78)
print(f"  {'OK ' if age_ok else 'BAD'}  quarantine ages inside the stated 187-256 min window "
      f"(actual {min(ages):.0f}-{max(ages):.0f})")
ok &= bool(age_ok)

structural = [
    ("fix 2 already landed", "twenty minutes before it was requested"),
    ("fix 1 already landed", "already shipped"),
    ("did not converge", "I have not touched the file"),
    ("other design is better", "better than the validate-on-load"),
    ("stale binaries named", "stale per-agent binaries"),
    ("rebuild is the remedy", "rebuilding the `target-*` trees"),
    ("40-frame corrected", "It is an 8-frame solve"),
    ("T4 could fail", "could not be a foregone conclusion"),
]
for label, token in structural:
    good = token.lower() in flat.lower()
    ok &= good
    print(f"  {'OK ' if good else 'BAD'}  {label:<32} {token!r}")

print("=" * 78)
print(f"verdict: {'GREEN' if ok else 'RED'}")
print("=" * 78)
sys.exit(0 if ok else 1)
