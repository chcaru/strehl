"""Whose failure is `every_writer_develop_carries_the_exposure_gain`?

The test counts two needles in merge_cmd.rs's OWN source. It is therefore a
function of that one file and nothing else -- pyramid.rs cannot reach it. This
settles the attribution by counting the same two needles in the committed blob
and in the working tree.

git blobs are read as BYTES via subprocess. `git show HEAD:path > tmp` re-encodes
the stream on Windows and has produced false readings in this project before.
"""
import subprocess
import sys

PATH = "crates/strehl-cli/src/merge_cmd.rs"
DEV = "." + "develop("
GAIN = "." + "with_exposure_gain("
TEST = "every_writer_develop_carries_the_" + "exposure_gain"


def blob(rev):
    r = subprocess.run(["git", "show", "%s:%s" % (rev, PATH)],
                       capture_output=True)
    if r.returncode != 0:
        raise SystemExit("git show %s failed: %s" % (rev, r.stderr.decode("utf-8", "replace")))
    return r.stdout.decode("utf-8")


def worktree():
    with open(PATH, "rb") as fh:
        return fh.read().decode("utf-8")


def main():
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True).stdout.decode().strip()
    rows = [("HEAD (%s)" % head, blob("HEAD")),
            ("working tree", worktree())]
    # A count is only a verdict where the test EXISTS. At HEAD the test may not
    # have been written yet, in which case "2 develop, 0 gain" is not a failing
    # state -- it is a state the guard was later added to forbid. Scoring it as
    # FAIL mis-attributes another lane's new guard as a pre-existing break.
    print("%-18s %-9s %-10s %-10s %s"
          % ("source", "has test", ".develop(", ".with_ex..", "test verdict"))
    verdicts = {}
    for name, src in rows:
        d, c = src.count(DEV), src.count(GAIN)
        present = TEST in src
        ok = None if not present else ((d > 0) and (d == c))
        verdicts[name] = ok
        print("%-18s %-9s %-10d %-10d %s"
              % (name, "yes" if present else "NO", d, c,
                 "n/a (guard absent)" if ok is None else ("PASS" if ok else "FAIL")))

    print()
    h = verdicts["HEAD (%s)" % head]
    w = verdicts["working tree"]
    if h is None:
        print("ATTRIBUTION: the guard does not exist at HEAD. Both the guard and the")
        print("  second develop site are another lane's uncommitted work; the failure I")
        print("  saw was a snapshot of that edit mid-flight, and the working tree now")
        print("  reads %s. Nothing here is reachable from pyramid.rs: the test"
              % ("PASS" if w else "FAIL"))
        print("  reads only its own file via include_str!.")
        sys.exit(0)
    if h and not w:
        print("ATTRIBUTION: the committed file PASSES and the working tree FAILS.")
        print("  The failure is carried by uncommitted edits to merge_cmd.rs, which")
        print("  `git status` shows as another lane's in-flight change (+65/-2).")
        print("  It is not reachable from pyramid.rs: the test reads only its own file.")
        sys.exit(0)
    if not h:
        print("ATTRIBUTION: the failure is ALREADY IN THE COMMITTED FILE at HEAD.")
        print("  Pre-existing; still not mine, but not an in-flight edit either.")
        sys.exit(0)
    print("ATTRIBUTION: both pass -- the failure did not reproduce. Re-run the suite.")
    sys.exit(1)


if __name__ == "__main__":
    main()
