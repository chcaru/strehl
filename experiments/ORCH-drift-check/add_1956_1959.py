"""Append facts 1956-1959 to the SYNTHESIS fact table (lanes DELIVER-V6, BUILD-DEFECT)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1955

ROWS = [
    (1956, "DELIVER-V6", "MEASURED", (
        "Two independent render runs of the same seven subjects produced byte-for-byte identical "
        "output, 7 of 7 on whole-file SHA256, across different concurrency, different cache "
        "directories and different hours. That BOUNDS fact 1886: the 33,003,417-pixel drift "
        "recorded there cannot be pipeline nondeterminism, because the pipeline is here shown "
        "deterministic across exactly the axes that differed. The remaining explanation is that "
        "the source tree moved under the build. This is the second independent lane to land on "
        "fact 1886 from a different direction -- a green-channel lane reached the same doubt via "
        "identical warpmap hashes -- and neither lane was measuring drift when it found it. "
        "The measurement was taken minutes before the duplicate renders were deleted for disk, "
        "so it exists only because banking preceded purging."
    )),
    (1957, "DELIVER-V6", "MEASURED", (
        "A directory of NTFS hardlinks inflates every recursive size query while occupying no "
        "blocks of its own, so deleting it reclaims approximately nothing. A lane measured a "
        "2.5793 GB reduction and reported 1.29 GB after running `fsutil hardlink list` and "
        "finding each file in the 1.2895 GB `view-new7` tree carried 2 links into the shipping "
        "masters. The correction was against the lane's own favour. Two disciplines follow. "
        "First, before claiming reclaimed space, check link counts: logical bytes are not "
        "on-disk bytes. Second, volume free-space delta is NOT attributable to one lane during a "
        "concurrent purge -- the same lane measured a 1.646 GB free-space rise, larger than it "
        "had itself freed, because sixteen other lanes were purging in the same window. "
        "Deleting hardlinks that share inodes with a deliverable is also a silent-destruction "
        "risk if the direction is confused, and it was closed by re-hashing all 33 masters "
        "afterwards: 0 mismatch, 0 missing, independently reconfirmed by the orchestrator."
    )),
    (1958, "BUILD-DEFECT", "MEASURED", (
        "The dust corrector's effect on a rendered master is LOCAL, not global, and its location "
        "independently confirms the disputed photosite from a second direction. Re-deriving the "
        "corrector-on/corrector-off pair before deletion: 16,039 pixels changed out of the full "
        "frame, which is 0.0487%, the changed/unchanged partition sums to the total, maximum "
        "absolute difference 3974 DN, and the changed pixels fall into 15 disjoint clusters "
        "rather than a diffuse field. Cluster 7's centre at (6869,4611) lands ONE pixel from the "
        "photosite derived for quad (3434,2305) by a different lane working from flat fields. "
        "Two lanes, two instruments, two data sources, agreement to a single pixel. This does "
        "NOT resolve the 25-quad dispute, and the lane said so."
    )),
    (1959, "BUILD-DEFECT", "MEASURED", (
        "A retry loop that discards stderr cannot distinguish `busy` from `refused`, and will "
        "convert a deterministic refusal into N identical silent failures. A lane's `git add` "
        "was refused by an ignore rule and retried five times looking exactly like `index.lock` "
        "contention, because the loop piped stderr to `Out-Null`. The fix is to capture stderr, "
        "inspect it, and retry ONLY on the specific contention signature -- everything else is a "
        "hard error. The same lane declined to force a PNG exhibit past the ignore rule, "
        "which the orchestrator then verified as correct rather than as excessive caution: "
        "`git ls-files` matching common image extensions returns 0 across the whole repository, "
        "so the exhibit would have been the first tracked image in the tree. Binary exhibits are "
        "banked instead as a full 64-character SHA256 plus a regeneration command, with the file "
        "itself copied to the out-of-tree gallery."
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
