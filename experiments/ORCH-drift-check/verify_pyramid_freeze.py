"""Independently verify the pyramid byte-freeze row landed without disturbing the controls.

Reads git blobs as BYTES via subprocess (never `git show > file`, which re-encodes on Windows).
"""
import subprocess
import sys

REPO = r"C:\dev\blog\death-of-software\projects\strehl"
TSV = "crates/strehl-cli/tests/byte-freezes.tsv"
COMMIT = "4c855f8d"

UNALIGNED = "coffee-bean-20-gate2-unaligned"
SIDECAR = "coffee-bean-20-gate2-sidecar"
PYRAMID = "coffee-bean-20-gate2-pyramid"

CLAIMED_SHA = "C6765BFA0D2FD203F65A7B02FE36920902B26A6706CCEAA8E87B76AC1CE5CD65"
CLAIMED_BYTES = "49450019"


def blob(rev):
    r = subprocess.run(["git", "show", "%s:%s" % (rev, TSV)],
                       cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise SystemExit("FATAL: git show %s failed: %s" % (rev, r.stderr.decode("utf-8", "replace")))
    return r.stdout.decode("utf-8")


def rows(text):
    out = {}
    header = None
    for line in text.split("\n"):
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if header is None:
            header = cells
            continue
        out[cells[0]] = dict(zip(header, cells))
    return header, out


def main():
    fails = []

    before_h, before = rows(blob(COMMIT + "~1"))
    after_h, after = rows(blob(COMMIT))

    print("header before : %s" % ",".join(before_h))
    print("header after  : %s" % ",".join(after_h))
    print("rows before   : %d   rows after: %d" % (len(before), len(after)))

    # 1. the merge column exists and is new
    if "merge" in before_h:
        fails.append("`merge` column already existed before the commit")
    if "merge" not in after_h:
        fails.append("`merge` column absent after the commit")
    else:
        print("\nmerge column added: OK")

    # 2. the new row exists, on pyramid, with the claimed identity
    if PYRAMID not in after:
        fails.append("new pyramid row absent")
    else:
        r = after[PYRAMID]
        print("new row merge=%s sha=%s bytes=%s" % (r.get("merge"), r.get("sha256"), r.get("bytes")))
        if r.get("merge") != "pyramid":
            fails.append("new row merge is %r, expected 'pyramid'" % r.get("merge"))
        if r.get("sha256") != CLAIMED_SHA:
            fails.append("new row sha %r != claimed %r" % (r.get("sha256"), CLAIMED_SHA))
        if r.get("bytes") != CLAIMED_BYTES:
            fails.append("new row bytes %r != claimed %r" % (r.get("bytes"), CLAIMED_BYTES))

    # 3. THE CONTROL: pre-existing rows unchanged in every field except the inserted column
    print("\n--- controls: every field except `merge` must be byte-identical ---")
    for rid in (UNALIGNED, SIDECAR):
        if rid not in before or rid not in after:
            fails.append("%s missing on one side" % rid)
            continue
        b, a = before[rid], after[rid]
        if a.get("merge") != "estimator":
            fails.append("%s backfilled merge=%r, expected 'estimator'" % (rid, a.get("merge")))
        drift = []
        for k, v in b.items():
            if a.get(k) != v:
                drift.append(k)
        if drift:
            fails.append("%s drifted in fields: %s" % (rid, ",".join(drift)))
            print("  %-32s DRIFT in %s" % (rid, ",".join(drift)))
        else:
            print("  %-32s unchanged (sha, bytes, why all identical)  merge=%s"
                  % (rid, a.get("merge")))

    # 4. both backends represented
    backends = sorted(set(r.get("merge") for r in after.values()))
    print("\nbackends present in registry: %s" % backends)
    if "pyramid" not in backends or "estimator" not in backends:
        fails.append("registry does not cover both backends")

    # 5. the coverage assertion exists in the harness
    src = subprocess.run(["git", "show", "%s:crates/strehl-cli/tests/byte-freeze.rs" % COMMIT],
                         cwd=REPO, stdout=subprocess.PIPE).stdout.decode("utf-8")
    hard = "pyramid" in src and "estimator" in src
    print("harness mentions both backends: %s" % hard)
    if not hard:
        fails.append("harness does not mention both backends")

    print("\n" + "=" * 60)
    if fails:
        print("VERIFY FAILED (%d)" % len(fails))
        for f in fails:
            print("  - %s" % f)
        return 1
    print("VERIFY OK - new pyramid row present, controls provably undisturbed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
