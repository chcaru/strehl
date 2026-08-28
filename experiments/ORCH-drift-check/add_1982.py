"""Append fact 1982 to the SYNTHESIS fact table (byte-freeze pyramid coverage closed)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1981

ROWS = [
    (1982, "BUILD-FREEZE-PYRAMID", "MEASURED", (
        "THE BYTE-FREEZE BLIND SPOT ON THE DEFAULT MERGE BACKEND IS CLOSED, and the new row was "
        "commissioned by a plant the row's author did not choose. `--merge` became a registry "
        "column, both existing rows were backfilled `estimator`, and a third row "
        "`coffee-bean-20-gate2-pyramid` now freezes the default backend at "
        "C6765BFA0D2FD203F65A7B02FE36920902B26A6706CCEAA8E87B76AC1CE5CD65, 49450019 bytes. THE "
        "CONTROLS ARE PROVABLY UNDISTURBED, checked by reading both git blobs as bytes rather "
        "than by trusting the report: every field of both pre-existing rows -- sha256, bytes and "
        "the whole `why` prose -- is byte-identical across the commit, with only the new "
        "column's value inserted. TEETH WERE PROVEN TWICE BY TWO DIFFERENT MECHANISMS. The "
        "author planted `significance_scale_default()` 0.0 to 1.0 and measured "
        "A4B699DA7FE32E70ED35002720539460C43EFEC093BA68191A9E7A4C14479547. The orchestrator then "
        "planted a DIFFERENT constant, SNR_REF 64.0 to 32.0 at `pyramid.rs:2502`, anchored on a "
        "unique full line with a hard error if it failed to land, and measured rc=101 with the "
        "row moving to CCAC0A72E46ACBAF865D07EDA9F72006CFA28F3D524232A1FC6D0E358642E73B -- a "
        "different hash from the author's, which is what independent sabotage should produce. "
        "Restoring from a $env:TEMP copy rather than `git checkout` returned 5 passed with all "
        "three rows HOLDING, and the `Compiling strehl-core` line proves the binary was actually "
        "rebuilt rather than a stale artifact re-tested, which is the trap AGENTS.md rule 33 "
        "names. A new assertion requires at least one row on each backend, so deleting the "
        "pyramid row now fails the suite."
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
    print("OK facts %s appended  rows %d -> %d"
          % (", ".join(str(r[0]) for r in ROWS), n_before, len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
