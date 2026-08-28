"""Append facts 1962-1964 to the SYNTHESIS fact table (lanes V-BANDFLOOR, ORCH)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1961

ROWS = [
    (1962, "V-BANDFLOOR", "MEASURED", (
        "The orchestrator's own banking-verification instrument was BLIND, and a lane caught it "
        "by running a negative control on the orchestrator. The prescribed procedure was `git "
        "grep -F <value> across HEAD and report the hit count`, and one lane had certified its "
        "banking 12-of-12 with it. Tested with three numbers INVENTED on the spot and never "
        "published anywhere: they scored 332, 46 and 46 hits corpus-wide, against 792, 1618 and "
        "439 for three genuinely published findings -- the same order of magnitude, so the "
        "instrument does not separate a real result from a fabricated one. The cause is that "
        "`git grep -F` substring-matches short decimals across hundreds of float CSVs. Every "
        "N-of-N banked certification produced this way proves nothing and must be re-run. The "
        "replacement, `experiments/ORCH-drift-check/verify_banked.ps1`, makes two independent "
        "changes -- scope to one NAMED committed file, and require digit boundaries so 1603 "
        "cannot satisfy a claim about 16039 -- and refuses to report at all if its own controls "
        "hit. Commissioned 4-of-4: positive 3-of-3 BANKED rc=0, invented rc=2, boundary rc=2, "
        "uncommitted-file refusal rc=1. Commissioning also caught a defect in the shipped "
        "script itself: `powershell -File s.ps1 -Values a,b,c` binds ONE comma-containing "
        "string rather than a 3-element array, which turned the positive control into a "
        "0-of-1 failure until the script was hardened to split on commas."
    )),
    (1963, "V-BANDFLOOR", "MEASURED", (
        "The per-band gate floor knob DOES NOT HELP and its default must not be flipped. Arm "
        "`1,8,8,8,8,8,8` was refuted on 0 of 6 subjects for N-scaling, and the band-0 variant "
        "destroys reproducible edge content. The commissioned null `1,1,1,1,1,1,1` renders "
        "byte-identical to unset on `leaf-2-cpl` (both `498CFC4AE7D6CEF2DF5140DA`), which "
        "confirms fact 1809. The lane RETRACTED its own halo refutation and its flat-site "
        "signal recoveries on its own initiative. Three gaps it published against itself: "
        "`widehalo.py` and `widehalo2.py` are committed while FAILING their own commissioning "
        "at 4-of-5 and 3-of-5 and will print plausible lighting-confounded halo tables, so they "
        "must not be trusted; `mutate.py` misses 2 of 5 conclusion-flips, so no green from this "
        "lane is audited through the shipped CLI entry point; and `bandqual.py` is committed "
        "but was never executed. Its computed verdicts are marked EVIDENCE GONE rather than "
        "reconstructed from memory, because they were printed to stdout and never written to "
        "disk -- their INPUTS survive as banked SHA256 entries, so the cheapest path back is 4 "
        "renders at roughly 10 minutes and 190 MB, not a re-run of the lane."
    )),
    (1964, "ORCH", "MEASURED", (
        "A broadcast measurement is stale by the time an asynchronous recipient acts on it, and "
        "the orchestrator shipped one without a timestamp. A disk-footprint table was sent to "
        "fifteen concurrent lanes with the words `I ran this myself just now` but no capture "
        "time and no instruction to re-measure before deleting. It was accurate when sent and "
        "stale when read, because the same fifteen lanes were concurrently shrinking the tree "
        "it described. One lane then read the post-purge tree, found 13.98 GB against the "
        "broadcast 139.3 GB, and concluded the orchestrator's instrument was wrong by 10x. "
        "Both parties were measuring correctly at different times. The orchestrator's claim "
        "was upheld on evidence the challenging lane itself had banked -- the index header "
        "reads root `C:\\dev\\strehl-out\\V-H2H2` and `bytes 75656527456 (70.46 GB)` with a "
        "timestamp, its paths are root-relative so all 67.57 GB was C-resident, every file was "
        "read end-to-end to compute a SHA256, and NTFS hardlinks cannot span volumes, so "
        "C-resident copies of D-resident sources were independent blocks. The lane's proposed "
        "mechanism was separately refuted: the tree holds exactly 2 reparse points, both under "
        "one 8.66 GB lane, and PowerShell 7.6.5 does not follow them on recursion. The process "
        "fix is the orchestrator's: a purge directive must carry the capture time of its "
        "measurement and require each recipient to re-measure its own subtree and skip if "
        "already clear. The cost of omitting it was reproducible scratch that lanes deleted "
        "under false urgency."
    )),
]


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()
    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows matched")
    if max(ids) != EXPECTED_TAIL:
        raise SystemExit("FATAL: tail is %d, expected %d" % (max(ids), EXPECTED_TAIL))

    n_before = len(ids)
    cur_tail = EXPECTED_TAIL
    for new_id, lane, kind, body in ROWS:
        if new_id in ids:
            raise SystemExit("FATAL: fact %d already present" % new_id)
        if body.count("*") % 2 != 0:
            raise SystemExit("FATAL: odd '*' count in fact %d" % new_id)
        if "|" in body:
            raise SystemExit("FATAL: '|' in body of fact %d" % new_id)
        anchor = None
        for m in re.finditer(r"^\| %d \|.*$" % cur_tail, src, re.M):
            anchor = m
        if anchor is None:
            raise SystemExit("FATAL: could not locate row %d" % cur_tail)
        src = src[: anchor.end()] + "\n" + ("| %d | %s | %s | %s |" % (new_id, lane, kind, body)) + src[anchor.end():]
        cur_tail = new_id

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(src)

    back = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", back, re.M)]
    if max(ids2) != ROWS[-1][0]:
        raise SystemExit("FATAL: post-write tail is %d" % max(ids2))
    if len(ids2) != n_before + len(ROWS):
        raise SystemExit("FATAL: row count went %d -> %d" % (n_before, len(ids2)))
    for new_id, _l, _k, _b in ROWS:
        if new_id not in ids2:
            raise SystemExit("FATAL: fact %d missing after write" % new_id)
    print("OK facts %s appended  rows %d -> %d"
          % (", ".join(str(r[0]) for r in ROWS), n_before, len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
