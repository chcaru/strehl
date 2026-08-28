"""Append facts 1949-1951 to the SYNTHESIS fact table (lane V-GREEN)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1948

ROWS = [
    (1949, "V-GREEN", "MEASURED", (
        "Fact 1867 CLOSED: the green-channel difference is not a CA defect, it is the output "
        "path refusing to be channel-local. A ladder that adds one output stage at a time "
        "measures the CA-on vs CA-off green difference as 0 of 8,250,880 px and 0 DN while "
        "binned and camera-linear, 45.2088% after MHC demosaic, and 93.4810% after the sRGB "
        "matrix and tone curve, bracketing the original pair's 93.5445%. The decisive line is "
        "the CFA-site partition of the demosaic rung: R sites 7,511,352 plus B sites 7,409,159 "
        "plus G1 sites 0 plus G2 sites 0 equals 14,920,511 exactly, so all 16,501,760 MEASURED "
        "greens are bit-identical and only INTERPOLATED greens move. The partition sums with no "
        "residue, which makes it a partition rather than a sample. Three candidate explanations "
        "were refuted -- CA touching green (a planted `Some(0.0)` drove the check RED at exit "
        "101 and the restore drove it GREEN), channel election, and a confounded original pair "
        "-- and the surviving cause was not on the list the lane was given; it found it by "
        "elimination plus code reading."
    )),
    (1950, "V-GREEN", "MEASURED", (
        "The CA coefficient reaches the GATHER only and never the SOLVE: all seven arms of the "
        "V-GREEN matrix produced warpmaps hashing identically to "
        "`522C2E94B96F95417BFBE744D4B977D3EA3FA07F8E2CF4743659B71BED4D4B70`. This is a positive "
        "identity across seven arms rather than an absence of observed difference, which is why "
        "it is load-bearing where a null result would not be. The determinism control in the "
        "same matrix holds byte-identically, so the shared hash is not an artefact of a "
        "non-deterministic pipeline collapsing to a constant."
    )),
    (1951, "V-GREEN", "MEASURED", (
        "A negative control that restores a mutated source file with `Copy-Item` can silently "
        "re-run the mutant, because `Copy-Item` preserves `LastWriteTime` and cargo therefore "
        "skips the rebuild. The restored arm then reports the MUTANT's behaviour under the "
        "RESTORED label. It failed safe in the lane that found it because of the ordering used; "
        "the mirrored ordering yields a false GREEN, which is the direction that ships a defect. "
        "This has reach beyond one lane: any commissioning harness in this tree that restores by "
        "copying back is suspect until the rebuild is proved to have happened, and proving it "
        "means checking that the binary changed, not that the source file did."
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
