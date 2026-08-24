"""Scan M110's artefacts for control characters (corpus_lint S7 class).

Covers what S7 does not: git commit message bodies. Both of tonight's M110
commit messages were built in a PowerShell @"..."@ here-string, which is the
exact hazard -- a backtick escape eats itself AND the following letter.

Reports the eaten letter's likely identity from context so a repair restores
it rather than deleting the byte, which would silently shorten an identifier.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
# 0x08 backspace, 0x1B escape, 0x0C formfeed, 0x07 bell, 0x0B vtab, 0x00 nul
BAD = {0x00, 0x07, 0x08, 0x0B, 0x0C, 0x1B}
ESCAPES = {0x00: "`0", 0x07: "`a", 0x08: "`b", 0x0B: "`v", 0x0C: "`f",
           0x1B: "`e", 0x0D: "`r", 0x09: "`t"}


def scan(label: str, data: bytes) -> list[str]:
    hits = []
    for i, byte in enumerate(data):
        if byte in BAD:
            ctx = data[max(0, i - 30):i + 30].decode("utf-8", "replace")
            ctx = ctx.replace("\n", "\\n")
            hits.append(f"  {label}: offset {i} byte 0x{byte:02X} "
                        f"(was {ESCAPES.get(byte, '?')}) ctx: ...{ctx}...")
    return hits


def odd_backticks(label: str, data: bytes) -> list[str]:
    """Detect the class that leaves NO control character.

    Measured on PowerShell 5.1: in @"..."@, an UNRECOGNISED escape such as
    `e (added in PS 6) or a backtick before a space is deleted silently and the
    following letter survives. `experiments/` came out as experiments/ -- a
    markdown code span downgraded to plain text with zero forensic trace.

    corpus_lint S7 cannot see this: there is no control character to find. The
    detectable residue is an ODD number of backticks, because code spans come
    in pairs.

    COUNT PER PARAGRAPH, NOT PER LINE. Code spans wrap across line breaks in
    this corpus, so a line-oriented count reports every wrapped span as a
    defect -- it flagged two such lines in M110-track-jitter.md on its first
    run. Fenced blocks are skipped by tracking the fence state across the file.
    """
    hits = []
    lines = data.split(b"\n")
    fenced = False
    para: list[bytes] = []
    start = 1
    out: list[tuple[int, list[bytes]]] = []
    for n, line in enumerate(lines, 1):
        if line.strip().startswith(b"```"):
            fenced = not fenced
            if para:
                out.append((start, para))
                para = []
            continue
        if fenced:
            continue
        if not line.strip():
            if para:
                out.append((start, para))
                para = []
            continue
        if not para:
            start = n
        para.append(line)
    if para:
        out.append((start, para))

    for n, block in out:
        joined = b" ".join(block)
        unmatched = unmatched_runs(joined)
        if unmatched:
            txt = joined.decode("utf-8", "replace").strip()[:90]
            hits.append(f"  {label}:{n}: {unmatched} unmatched backtick run(s) "
                        f"in paragraph -- possible eaten span: {txt}")
    return hits


def unmatched_runs(text: bytes) -> int:
    """Count backtick runs that never find a closing run of equal length.

    A raw count of backticks is not enough. CommonMark closes a run of N
    backticks with a run of exactly N, so markdown's own way of writing a
    LITERAL backtick -- ``  `e  `` -- makes a paragraph's raw count odd while
    being perfectly well formed. Counting raw backticks flagged two such
    paragraphs in this very report.

    Nor is pairing runs by length enough: everything between a matched pair is
    CONTENT and must be consumed, including inner runs. Treating the inner
    single backtick of ``  `e  `` as its own run flagged the same paragraphs a
    second time. Scan left to right, and for each run look ahead for the next
    run of exactly equal length, consuming everything between.
    """
    runs: list[tuple[int, int]] = []      # (start, length)
    i = 0
    while i < len(text):
        if text[i:i + 1] == b"`":
            j = i
            while text[j:j + 1] == b"`":
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1

    unmatched = 0
    k = 0
    while k < len(runs):
        _, n = runs[k]
        close = next((q for q in range(k + 1, len(runs)) if runs[q][1] == n), None)
        if close is None:
            unmatched += 1
            k += 1
        else:
            k = close + 1                 # everything between was content
    return unmatched


def selftest() -> int:
    """Negative control: green -> RED -> green with a byte-identical restore.

    A scanner that has only ever passed is not known to fire. Planted bytes are
    the two this project has actually seen: 0x08 from `b and 0x0C from `f.
    """
    good = b"subject `bee-3-cpl` and `foam` are fine\n"
    planted = b"subject \x08ee-3-cpl` and \x0coam` are fine\n"
    steps = []

    n0 = len(scan("selftest", good))
    steps.append(("green before", n0 == 0, f"{n0} hits on clean text"))

    n1 = len(scan("selftest", planted))
    steps.append(("RED on plant", n1 == 2, f"{n1} hits, want 2 (0x08 and 0x0C)"))

    n2 = len(scan("selftest", good))
    steps.append(("green after", n2 == 0, f"{n2} hits after restore"))

    # the silent class, which the control-character scan CANNOT see.
    # Delete exactly ONE backtick: deleting both ends of a span leaves an EVEN
    # count and the plant produces no signal. The first version of this control
    # did exactly that and failed, which is the plant being wrong, not the
    # check.
    silent = b"subject bee-3-cpl` and `foam` are fine\n"
    n3 = len(scan("selftest", silent))
    n4 = len(odd_backticks("selftest", silent))
    steps.append(("silent class invisible to ctrl scan", n3 == 0,
                  f"{n3} control chars in text whose backtick was deleted"))
    steps.append(("odd-backtick check catches it", n4 == 1,
                  f"{n4} unmatched-run paragraph(s), want 1"))

    # and it must NOT fire on a span legitimately wrapped across a line break,
    # which is how this corpus is written and how the check first failed.
    wrapped = b"logged `alignment : ON (sidecar-override), reference\nframe 0`.\n"
    n5 = len(odd_backticks("selftest", wrapped))
    steps.append(("no false positive on wrapped span", n5 == 0,
                  f"{n5} hits on a code span split across two lines, want 0"))

    # nor on markdown's own way of writing a LITERAL backtick, ``  `e  ``,
    # which makes a paragraph's RAW backtick count odd while being well formed,
    # AND whose inner single backtick must be consumed as content rather than
    # counted as its own run. Both mistakes flagged real paragraphs of this
    # report, one after the other.
    literal = b"the escape `` `e `` became live in PowerShell 6, unlike `` `b ``.\n"
    n6 = len(odd_backticks("selftest", literal))
    steps.append(("no false positive on `` `e `` form", n6 == 0,
                  f"{n6} hits on double-backtick literal spans, want 0"))

    # the exact shape that defeated the previous two versions: a `` `` span
    # whose content is a single backtick, followed later by an ordinary span.
    real = (b"1. **Shell-version dependent.** `` `e `` became an escape in PS 6,\n"
            b"   so the backtick is dropped and the `e` survives -- `` `x/` `` came\n"
            b"   out as text. The 0x1B in `M105b.md` was written under 7.x.\n")
    n8 = len(odd_backticks("selftest", real))
    steps.append(("no false positive on the real paragraph", n8 == 0,
                  f"{n8} hits on the §12.2 paragraph shape, want 0"))

    # and it must still fire when a double-backtick span loses one delimiter.
    broken = b"the escape `` `e ` became live in PowerShell 6.\n"
    n7 = len(odd_backticks("selftest", broken))
    steps.append(("still fires on a broken double span", n7 == 1,
                  f"{n7} hits on an unclosed `` run, want 1"))

    ok = all(s[1] for s in steps)
    for name, good_, detail in steps:
        print(f"  {name:<38} {'PASS' if good_ else 'FAIL':<5} {detail}")
    print(f"\nselftest: {sum(1 for s in steps if s[1])}/{len(steps)} "
          f"-- scanner is {'known to fire' if ok else 'NOT VALIDATED'}")
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    hits: list[str] = []

    # 1. Commit message bodies -- read as BYTES via subprocess, never through
    #    a PowerShell redirect, which would re-encode the stream.
    shas = subprocess.run(["git", "-C", str(REPO), "log", "-12", "--format=%H"],
                          capture_output=True).stdout.decode().split()
    n_msg = 0
    for sha in shas:
        raw = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%B", sha],
                             capture_output=True).stdout
        subj = raw.decode("utf-8", "replace").splitlines()[0][:60]
        if "M110" not in subj:
            continue
        n_msg += 1
        hits += scan(f"commit {sha[:8]} ({subj})", raw)

    # 2. Every TEXT file I own. Binary artefacts (.pyc, .tif) are full of these
    #    bytes legitimately and would drown the signal.
    TEXT = {".py", ".json", ".md", ".ps1", ".txt", ".tsv", ".toml", ".rs"}
    n_file = 0
    targets = sorted((REPO / "experiments" / "M110-sheet").rglob("*"))
    targets += sorted((REPO / "docs" / "research").glob("M110-*.md"))
    for p in targets:
        if not p.is_file() or p.suffix.lower() not in TEXT:
            continue
        if "__pycache__" in p.parts:
            continue
        n_file += 1
        hits += scan(str(p.relative_to(REPO)), p.read_bytes())
        if p.suffix.lower() == ".md":
            hits += odd_backticks(str(p.relative_to(REPO)), p.read_bytes())

    print(f"scanned {n_msg} M110 commit message(s) and {n_file} file(s)")
    if hits:
        print(f"\n*** {len(hits)} CONTROL CHARACTER(S) FOUND ***")
        print("\n".join(hits))
        print("\nRepair by RESTORING THE EATEN LETTER, never by deleting the byte:")
        print("a deleted byte leaves a plausible-looking shorter identifier.")
        return 1
    print("clean -- no control characters")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
