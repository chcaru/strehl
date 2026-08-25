"""M95 x20 - audit ORCH's discipline 768 (prefix-anchored edits) against M95's own reports.

WHY THIS EXISTS
---------------
ORCH 19:29: "anchor every edit on a COMPLETE LINE, never on a sentence prefix. A
prefix-anchored replacement silently grafts the unmatched remainder of the line onto
the end of your new text - no error, no failed match, no lint violation."

M95 made at least one anchored edit to docs/research/M95-kernel.md this session (a
hash cell widened from 8 to 16 hex digits inside the section 24 results table). If that
edit was prefix-anchored, the tail of the original row was grafted on and would read
as plausible markdown. No gate M95 owns would necessarily catch it: verify_s24 checks
that VALUES are present, not that no extra text trails them.

Concretely, a prefix graft on a table row looks like this. Original:

    | C1 | 2FD11694 | B548E321 | DIFFER |

anchored on the prefix "| C1 | 2FD11694" and replaced with the widened row, yields:

    | C1 | 2FD1169422E6A6F1 | B548E32162522F4E | DIFFER | | B548E321 | DIFFER |

which has too many cells (check A) and repeats a long token (check B).

CHECKS
  A  table cell-count consistency within each contiguous table block
  B  intra-line repeated substring of length >= REPEAT_MIN (the graft signature)
  C  every hash cell in the section 24 results table is exactly 16 uppercase hex

V2 CHANGES, AND WHY EACH NEEDED ITS OWN CONTROL
-----------------------------------------------
v1 reported 21 candidates. Triage showed two distinct instrument defects, and fixing
an instrument to be quieter is exactly the move that manufactures a green, so each fix
carries a control that proves the check still fires afterwards.

  A-DEFECT: cells() split on every "|", including the ESCAPED "\\|" that markdown
  requires inside a table cell. A row like "| pwsh | `SS \\| -First 3` | ..." counted
  two phantom cells, which both flagged that row AND corrupted the block majority so
  that CORRECT rows were flagged instead. All 9 v1 check-A hits trace to this.
  Fix: unescape "\\|" before splitting. Control A2 plants a graft in a table that also
  contains escaped pipes, and requires the check to still fire.

  B-IS-A-HEURISTIC: a long repeated run inside one line is only a HINT of a graft.
  Legitimate causes exist in this corpus: a table row whose columns genuinely repeat a
  value (the section 24 result rows repeat a hash precisely BECAUSE pre == post, which
  is the finding), and deliberate parallel prose. Those cannot be pattern-excluded
  without also excluding real grafts, so they are allowlisted INDIVIDUALLY by SHA-1 of
  the line's stripped content. Keying on content, not line number, means the entry
  stops matching the moment the line is edited, so an allowlisted line that later grows
  a graft re-surfaces. Control B2 mutates an allowlisted line and requires it back.

BARS, PRE-REGISTERED
--------------------
PASS requires: zero non-allowlisted hits on both owned reports, AND every positive
control fires. If any control fails, this tool reports ITSELF as blind for that check
and makes no claim about the report - an unfired detector is not evidence of absence
(discipline 594, which came from M95's own predecessor and binds M95).

EXIT
  0  clean AND all positive controls fired
  1  a graft candidate was found in a report
  2  a positive control failed to fire (this tool is blind; no claim made)
"""

import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OWNED = [
    REPO / "docs" / "research" / "M95-kernel.md",
    REPO / "docs" / "research" / "M95-merge-vs-frame-sharpness.md",
]
REPEAT_MIN = 18

# Check-B allowlist: SHA-1 of the stripped line, with the reason it repeats.
# Keyed by content so any later edit to the line drops it out of the allowlist.
BENIGN_B = {
    # Two distinct filenames sharing a directory prefix.
    "f325cb5cb94a1e51d0beaeb310d46486aa225c7d": "prose names k1_radius.py and k5_port.py in one sentence",
    # The measured excess-extrema rows: these kernels genuinely produced 0.0000
    # in every column. The repetition IS the datum.
    "b9f1ed93886829da715b3b6f04e957f2e86f4072": "nearest row: 0.0000 in all 7 columns, measured",
    "152ead42ebb2e33e910d39b205860ec0b80f95c5": "bilinear row: 0.0000 in all 7 columns, measured",
    # Deliberate parallel prose.
    "228758740272379cd48467c87b5cfdd483c9c3fd": "parallel list: 'a wrong number in X, a wrong number in Y'",
    "2d888f8bd3c8deca4ef70eda52dead454cbc94d6": "discipline sentence: 'positive control for the stimulus / for the value'",
    "c897bf0dc2a1528c755fc0da031c39c5a80d55b9": "table header with parallel -File / -Command seed columns",
    # Section 24 result rows. Each repeats a hash BECAUSE pre == post, which is the
    # finding; removing the repetition would destroy the result. Cross-checked by
    # check A (cell counts consistent) and check C (every cell exactly 16 upper hex),
    # and gated independently by verify_s24.py against out/x18_cachectl.json.
    "e393c775a37008ce633952f3af5ccda8d09ae584": "s24 row C0: A == B, identical -- PASS",
    "77d5c1151f05a3ba510df0a54865340c6d01ed31": "s24 row C2: A == B, identical -- PASS",
    "416ace827fcfc997ee5a62d5504c31d9f89010b7": "s24 row C3: A == B, identical -- PASS (the clearance)",
    "c502518ee850d974c97d28876b95c69e1168f6d1": "s24 row C4: A == B, identical -- PASS",
    # Code dir and image dir share the milestone slug; ratio-of-ratios repeats its term.
    "1adca5d8949c3d4900f6960fde676d07f834ea73": "experiments/ and strehl-out/ paths share the M95-merge-vs-frame slug",
    "900006a7359c27dcab619adc146c6664709d39b3": "anisotropy formula is a ratio of two [P_diag/P_axis] terms",
}

PIPE_SENTINEL = "\x00"


def read(p):
    return p.read_bytes().decode("utf-8")


def sha(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def table_blocks(lines):
    """Yield (start_index, [(index, line)]) for each run of consecutive table rows."""
    block, start = [], None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            if start is None:
                start = i
            block.append((i, ln))
        else:
            if len(block) >= 2:
                yield start, block
            block, start = [], None
    if len(block) >= 2:
        yield start, block


def cells(row):
    """Split a markdown table row, honouring the escaped pipe '\\|'."""
    protected = row.replace("\\|", PIPE_SENTINEL)
    return [c.replace(PIPE_SENTINEL, "\\|") for c in protected.strip().strip("|").split("|")]


def check_a(name, text):
    hits = []
    lines = text.splitlines()
    for _, block in table_blocks(lines):
        counts = {}
        for i, ln in block:
            counts.setdefault(len(cells(ln)), []).append((i, ln))
        if len(counts) > 1:
            majority = max(counts, key=lambda k: len(counts[k]))
            for k, rows in counts.items():
                if k == majority:
                    continue
                for i, ln in rows:
                    hits.append((name, i + 1, f"cell count {k} vs block majority {majority}", ln.strip()))
    return hits


def longest_internal_repeat(s):
    for L in range(len(s) // 2, REPEAT_MIN - 1, -1):
        for a in range(0, len(s) - 2 * L + 1):
            sub = s[a : a + L]
            if sub.strip(" |-") == "":
                continue
            if s.find(sub, a + L) != -1:
                return sub
    return None


def check_b(name, text, collect=None):
    hits = []
    for i, ln in enumerate(text.splitlines()):
        s = ln.strip()
        if len(s) < REPEAT_MIN * 2:
            continue
        if re.fullmatch(r"[|\-: +=_*#~.]+", s):
            continue
        found = longest_internal_repeat(s)
        if not found:
            continue
        d = sha(s)
        if d in BENIGN_B:
            continue
        if collect is not None:
            collect.append((d, s))
        hits.append((name, i + 1, f"repeated {len(found)}-char run {found!r}", s))
    return hits


HASH_ROW = re.compile(r"^\|\s*(C[0-4])\s*\|")
HEX16 = re.compile(r"^[0-9A-F]{16}$")


def check_c(name, text):
    hits = []
    for i, ln in enumerate(text.splitlines()):
        if not HASH_ROW.match(ln.strip()):
            continue
        for c in cells(ln):
            t = c.strip().strip("*` ")
            if re.fullmatch(r"[0-9A-Fa-f]{6,}", t) and not HEX16.match(t):
                hits.append((name, i + 1, f"hash cell {t!r} is not 16 upper hex", ln.strip()))
    return hits


def positive_controls():
    """Every check must be shown firing. Returns list of (tag, fired)."""
    out = []

    # A1 / B1 / C1: naive graft, no escaped pipes
    plain = "\n".join(
        [
            "| bar | pre | post | verdict |",
            "| --- | --- | --- | --- |",
            "| C0 | 2FD1169422E6A6F1 | 2FD1169422E6A6F1 | identical |",
            "| C1 | 2FD11694 | B548E32162522F4E | DIFFER | | B548E321 | DIFFER |",
        ]
    )
    out.append(("G-A1 plain graft", len(check_a("<ctrl>", plain)) > 0))
    out.append(("G-B1 plain graft", len(check_b("<ctrl>", plain)) > 0))
    out.append(("G-C1 short hash cell", len(check_c("<ctrl>", plain)) > 0))

    # A2: the v1 defect's shape - a graft in a table that ALSO uses escaped pipes.
    # If the unescape fix silenced check A rather than correcting it, this reads clean.
    escaped = "\n".join(
        [
            "| host | arm | reading |",
            "| --- | --- | --- |",
            "| pwsh 7.6.5 | `SS \\| -First 3` | LOST |",
            "| powershell 5.1 | `SS \\| -First 3` | preserved |",
            "| pwsh 7.6.5 | `SS \\| -Last 3` | preserved | GRAFTED TAIL | extra |",
        ]
    )
    out.append(("G-A2 graft amid escaped pipes", len(check_a("<ctrl>", escaped)) > 0))

    # A3 negative: the SAME table with no graft must be clean, or A2 proves nothing.
    clean_escaped = "\n".join(
        [
            "| host | arm | reading |",
            "| --- | --- | --- |",
            "| pwsh 7.6.5 | `SS \\| -First 3` | LOST |",
            "| powershell 5.1 | `SS \\| -First 3` | preserved |",
            "| pwsh 7.6.5 | `SS \\| -Last 3` | preserved |",
        ]
    )
    out.append(("G-A3 escaped pipes, NO graft -> must be silent", len(check_a("<ctrl>", clean_escaped)) == 0))

    return out


def control_b2():
    """Mutate an allowlisted line; it must leave the allowlist and re-surface."""
    if not BENIGN_B or list(BENIGN_B) == ["1b1e0f0e2e0dcb0b1b3a"]:
        return None
    for p in OWNED:
        text = read(p)
        for ln in text.splitlines():
            s = ln.strip()
            if sha(s) in BENIGN_B:
                mutated = s + " GRAFTED"
                doc = "\n".join(["| a | b |", "| --- | --- |", mutated])
                return len(check_b("<ctrl>", doc)) > 0
    return None


def main():
    survey = "--survey" in sys.argv
    print("=" * 78)
    print("M95 x20 v2 - prefix-graft audit (ORCH discipline 768)")
    print("=" * 78)

    print("\n-- positive controls --")
    blind = []
    for tag, fired in positive_controls():
        print(f"  {tag:44s} {'FIRED' if fired else 'DID NOT FIRE'}")
        if not fired:
            blind.append(tag)
    b2 = control_b2()
    if b2 is None:
        print(f"  {'G-B2 mutated allowlisted line re-surfaces':44s} SKIPPED (allowlist empty)")
    else:
        print(f"  {'G-B2 mutated allowlisted line re-surfaces':44s} {'FIRED' if b2 else 'DID NOT FIRE'}")
        if not b2:
            blind.append("G-B2")
    if blind:
        print(f"\nPOSITIVE CONTROL FAILED for {blind}. This tool is BLIND; it makes no claim.")
        return 2
    print("  -> every check is known to fire, not merely known to pass")

    total = 0
    collect = []
    for p in OWNED:
        if not p.exists():
            print(f"\nMISSING: {p}")
            return 2
        text = read(p)
        res = {
            "A": check_a(p.name, text),
            "B": check_b(p.name, text, collect),
            "C": check_c(p.name, text),
        }
        n = sum(len(v) for v in res.values())
        total += n
        print(f"\n-- {p.name}  ({len(text.splitlines())} lines) --")
        for tag in ("A", "B", "C"):
            print(f"  check {tag}: {len(res[tag])} hit(s)")
            for name, lineno, why, ln in res[tag][:20]:
                print(f"     {name}:{lineno}  {why}")
                print(f"       {ln[:150]}")

    if survey and collect:
        print("\n-- SHA-1 digests for allowlist triage (check B) --")
        for d, s in collect:
            print(f'    "{d}": "",  # {s[:90]}')

    print("\n" + "=" * 78)
    if total == 0:
        print("CLEAN - no prefix-graft candidate in either M95-owned report")
        print("(detector proven live by the positive controls above)")
        return 0
    print(f"{total} CANDIDATE(S) - triage each; re-run with --survey for allowlist digests")
    return 1


if __name__ == "__main__":
    sys.exit(main())
