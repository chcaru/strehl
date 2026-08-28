"""Append facts 1953-1955 to the SYNTHESIS fact table (lane V-MOTE)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1952

ROWS = [
    (1953, "V-MOTE", "MEASURED", (
        "The advertised 17x dust-defect ratio does not exist: it was a comparison across two "
        "different subjects. `DELIVER-V5` logs `highly-angled-ruler-mm-cpl` at -13.88%, which is "
        "the same subject a second lane independently read at -13.28% -- the two lanes agree. "
        "The 17x came from dividing that against -0.78% measured on a DIFFERENT subject "
        "entirely. Two related coordinate errors fell out of the same adjudication: "
        "`6776_4322` is a clamped 256-px crop ORIGIN and not a mote coordinate, proved by "
        "executing the clamp, which resolves it to 6776 for w=7032 and 6784 for w=7040 -- two "
        "x-values, which no mote can have; and the disputed location is quad (3434,2305), while "
        "(7008,4450) is empty background 215 px away. The control ring at that background site "
        "reads -0.051% corrector-off and -0.046% on, i.e. it does not move when the mote is "
        "removed, which is why the second lane could not reproduce the defect: it was measuring "
        "clean sky. Depth is -2.94% +/- 0.06% on the flats and -3.4% to -5.7% on masters."
    )),
    (1954, "V-MOTE", "MEASURED", (
        "A defect corrector handed deliberately WRONG coordinates rendered byte-identical to the "
        "corrector-off arm (one exe `0F4ACD7E...FCDA`, 205 frames, shared stretch [54837, 59154] "
        "DN16). That arm bounds the DOWNSIDE -- enabling the correction cannot damage a good "
        "render -- and it is a real bound on a disputed coordinate. It does NOT demonstrate the "
        "UPSIDE, because a do-nothing implementation passes it identically. The upside is a "
        "separate measurement: the A/B pair moves -4.644% to +0.019% with a residual roughly 40x "
        "smaller. Both arms are required and neither substitutes for the other. Scope stated "
        "rather than buried: the byte-identity arm ran on ONE subject and establishes no "
        "corpus-wide false-positive rate."
    )),
    (1955, "V-MOTE", "MEASURED", (
        "A verifier lane recorded a fact AGAINST its own evidence, which is the behaviour the "
        "corpus wants and should be cited as precedent. V-MOTE's arm C1, testing which block "
        "wears the CPL, FAILED, and the lane published that failure as its own local F13 in the "
        "assumed-or-not-mine partition rather than dropping the arm. Its report partitions every "
        "claim into 15 itemised verified groups plus an explicit not-verified list covering the "
        "cache key (flagged `check before default-on ships`), another lane's 26-stack tally, the "
        "Laplacian explanation for the sub-2 DN16 halo, and a subject at -0.34% showing the "
        "defect does not reach every master. The lane's standing recommendation is that the dust "
        "corrector default to ON, with the cache-key question resolved first."
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
