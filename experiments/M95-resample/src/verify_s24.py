"""Verify every number in section 24 against out/x18_cachectl.json.

Same discipline as verify_s23.py, and it inherits that gate's two measured
holes as design constraints:

  * a PRESENCE check is satisfied by any duplicate of the value, so every
    check here is anchored on a neighbouring literal and the whole row is
    reconstructed where a bare number would be ambiguous; and
  * a document-wide check can be satisfied by the WRONG SITE, so section 24
    is sliced out with a heading regex before anything is searched.

Normalisations, each of which was required by a measured failure in this
corpus: U+2212 vs ASCII hyphen, line-leading blockquote markers surviving
whitespace collapse, and line wrapping breaking plain-string phrase matches.

Exit 0 = all green, 1 = a claim in the report is not supported by the
artifact, 2 = the gate itself could not run.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
ART = ROOT / "experiments" / "M95-resample" / "out" / "x18_cachectl.json"


def die(msg: str) -> None:
    print(f"TOOL FAILURE: {msg}", file=sys.stderr)
    sys.exit(2)


def flat(s: str) -> str:
    """Collapse to a single line the way this corpus needs."""
    s = s.replace("\u2212", "-")  # U+2212 MINUS SIGN -> ASCII hyphen
    s = s.replace("\u2014", "--").replace("\u2013", "-")
    s = s.replace("\u2026", "...")
    s = re.sub(r"(?m)^\s*>\s?", " ", s)  # blockquote markers
    s = re.sub(r"[|`*]", " ", s)  # table pipes, code ticks, emphasis
    return re.sub(r"\s+", " ", s)


if not REPORT.exists():
    die(f"missing report {REPORT}")
if not ART.exists():
    die(f"missing artifact {ART}")

body = REPORT.read_text(encoding="utf-8")
m = re.search(r"^## 24\. ", body, re.M)
if not m:
    die("section 24 heading not found in the report")
raw = body[m.start():]
sec = flat(raw)
art = json.loads(ART.read_text(encoding="utf-8"))
res = art["results"]

checks: list[tuple[str, str, bool]] = []


def check(label: str, needle: str, anchor: str | None = None) -> None:
    """Assert `needle` appears in section 24, near `anchor` if given.

    The anchor must occur EXACTLY ONCE. A non-unique anchor silently windows
    onto the wrong site, which is how the section 23 gate's D5 hole worked:
    the check passes or fails for reasons unrelated to the claim. Measured
    here on the first run -- the anchor "| C0 |" flattens to " C0 " and its
    first hit was the prose "If C0 had failed", 2 KB from the table.
    """
    hay = sec
    if anchor is not None:
        a = flat(anchor)
        n = sec.count(a)
        if n != 1:
            die(f"ANCHOR OCCURS {n} TIMES (need exactly 1) for {label!r}: {anchor!r}")
        i = sec.index(a)
        hay = sec[max(0, i - 400): i + len(a) + 400]
    checks.append((label, needle, flat(needle) in hay))


def table_row(bar: str) -> str:
    """The one line in section 24 that begins the results row for `bar`.

    Matched structurally on the raw text rather than by anchoring inside the
    flattened blob, because a table row is a line and prose is not.
    """
    hits = [ln for ln in raw.splitlines() if ln.startswith(f"| {bar} |")]
    if len(hits) != 1:
        die(f"expected exactly 1 results row for {bar}, found {len(hits)}")
    return hits[0]


# --- the five bars, each reconstructed as a whole table row -----------------
ROWS = {
    "C0": ("POST", "plain, **nothing between**", "same", "identical -- PASS"),
    "C1": ("**PRE**", "plain, align between", "**DIFFER**", "`A != B` -- PASS"),
    "C2": ("POST", "plain, align between", "same", "identical -- PASS"),
    "C3": ("**PRE**", "**override**, align between", "same", "identical -- PASS"),
    "C4": ("POST", "override, align between", "same", "identical -- PASS"),
}
for bar, (binname, arm, sameness, verdict) in ROWS.items():
    a16 = res[bar]["A"][:16]
    b16 = res[bar]["B"][:16]
    row = f"| {bar} | {binname} | {arm} | `{a16}` | `{b16}` | {sameness} | {verdict} |"
    checks.append((f"{bar} whole row", row, flat(row) == flat(table_row(bar))))
    # the artifact must agree with the sameness word the report prints
    same_in_art = res[bar]["A"] == res[bar]["B"]
    want_same = sameness == "same"
    checks.append(
        (f"{bar} artifact identical={same_in_art} matches report {sameness!r}",
         "(from JSON)", same_in_art == want_same)
    )
    if not art["verdicts"][bar]:
        checks.append((f"{bar} verdict PASS in artifact", "(from JSON)", False))

# C1 is the power control: it MUST have differed, or the report's whole
# argument is void. Assert it against the artifact, not against the prose.
checks.append(
    ("C1 power control actually differed in the artifact", "(from JSON)",
     res["C1"]["A"] != res["C1"]["B"])
)
checks.append(
    ("C0 determinism actually held in the artifact", "(from JSON)",
     res["C0"]["A"] == res["C0"]["B"])
)
checks.append(
    ("C3 override actually held in the artifact", "(from JSON)",
     res["C3"]["A"] == res["C3"]["B"])
)
checks.append(("artifact reports blind=False", "(from JSON)", art["blind"] is False))

# --- the internal consistency claim ----------------------------------------
same_triple = res["C1"]["A"] == res["C3"]["A"] == res["C3"]["B"]
checks.append(("C1.A == C3.A == C3.B in the artifact", "(from JSON)", same_triple))
check(
    "the triple is quoted",
    f"C1's A, C3's A and C3's B are all `{res['C1']['A'][:16]}`",
    anchor="internal consistency check",
)
check(
    "PRE and POST differ from each other",
    f"`{res['C1']['A'][:16]}` vs `{res['C0']['A'][:16]}`",
    anchor="PRE and POST differ from each other",
)

# --- the fixed inputs -------------------------------------------------------
check("bracket and frame count",
      f"`{art['bracket']}`, {art['frames']} frames, merge reference {art['merge_reference']}",
      anchor="The measurement")
check("intervening reference",
      f"`align --reference {art['intervened_reference']}`",
      anchor="merge reference")
check("PRE provenance",
      f"PRE `{art['pre_commit']}`, sha256 `{art['pre_exe_sha256'][:16]}",
      anchor="recorded by sha256")

# The POST binary's worktree commit is NOT in this artifact: it was written by
# the pre-rename version of the script, whose `post_commit` field actually held
# the repository HEAD at write time. That is the very defect section 24.5
# discloses, so the gate must not paper over it. Take the binary's provenance
# from the committed script's own constant, and take the stale value from the
# artifact, and require the report to state both.
SRC = ROOT / "experiments" / "M95-resample" / "src" / "x18_cachectl.py"
if not SRC.exists():
    die(f"missing {SRC}")
src = SRC.read_text(encoding="utf-8")
mm = re.search(r'^POST_COMMIT\s*=\s*"([0-9a-f]+)"', src, re.M)
if not mm:
    die("POST_COMMIT constant not found in x18_cachectl.py")
post_commit = mm.group(1)
mp = re.search(r'^PRE_COMMIT\s*=\s*"([0-9a-f]+)"', src, re.M)
if not mp:
    die("PRE_COMMIT constant not found in x18_cachectl.py")
if mp.group(1) != art["pre_commit"]:
    die(f"PRE_COMMIT {mp.group(1)} disagrees with artifact {art['pre_commit']}")

check("POST provenance",
      f"POST `{post_commit}`, sha256 `{art['post_exe_sha256'][:16]}",
      anchor="recorded by sha256")

stale = art.get("repo_head_at_write_time", art["post_commit"])
if stale == post_commit:
    die("expected the artifact's stale field to differ from the pinned POST commit; "
        "if it now agrees, section 24.5's disclosure is stale and must be rewritten")
check("the stale post_commit field is disclosed",
      f"records `{stale[:7]}`",
      anchor="misleadingly named")

# --- claims about the fix, checked as whole phrases -------------------------
check("fix commit and time", "`69f7b4c`, at 13:41:53 today", anchor="The fix already landed")
check("PRE is nine seconds earlier", "committed at 13:41:44, **nine seconds before the fix**",
      anchor="Discipline 594")
# ANCHOR RULE, measured: an anchor must be prose scaffolding, never a value the
# report also claims. This check used to anchor on "nine seconds before the
# fix" -- the very phrase the check above asserts. The negative control's D3
# mutated that phrase and the gate exited 2 (tool failure) instead of 1
# (subject failure), because the anchor vanished. The gate noticed, but it
# reported "I cannot run" when the truth was "the report is wrong", and those
# are different claims.
check("PRE has no solve_config_key", "verified it contains zero `fn solve_config_key` definitions",
      anchor="So I built a binary from")
check("registration commits", "committed at `3d00a3e`", anchor="before the script had ever been run")
check("amendment commit", "amended at `448e5b3`", anchor="before the script had ever been run")
check("capture dir untouched", "held 19 files before the control and 19 after",
      anchor="capture library was asserted untouched")
# Quote the meaningful tail of the tool's own alignment line, derived from the
# artifact rather than retyped. The leading "alignment      :" label is the
# tool's column padding, not a measurement.
token = res["C3"]["alignment_line"].split(":", 1)[1].strip()
check("sidecar-override token is quoted", token, anchor="says why on its own")

# --- report --------------------------------------------------------------
bad = [c for c in checks if not c[2]]
for label, _needle, ok in checks:
    print(f"  {'ok  ' if ok else 'BAD '} {label}")
print(f"\n{len(checks) - len(bad)}/{len(checks)} section 24 claims verified", end="  ")
print("GREEN" if not bad else "RED")
sys.exit(1 if bad else 0)
