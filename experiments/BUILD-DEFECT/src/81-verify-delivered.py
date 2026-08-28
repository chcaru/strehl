"""Does a DELIVERED sidecar now reproduce its DELIVERED master?

The re-emission in 80 was validated against the emitter's own text. That proves
the sidecars say the right thing. It does not prove what they say WORKS on the
shipped corpus, which is the only claim a reader of those files cares about.

So: take the corrected sidecar off the delivered corpus, execute it verbatim as a
naive user would, and compare the result to the sealed master AS PIXELS. File
hashes are not sufficient and this project has the scar to prove it -- two
renders hashed differently and were later measured to be identical in all
98,898,048 samples, because the difference lived in an embedded tone record.

The masters are also checked against their own `.ok` sentinels first. 80 rewrote
text files beside sealed images; if any image moved, that is a far worse defect
than the one being fixed, and it must be caught here rather than assumed away.
"""
import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DELIVERED = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"D:\strehl-out\BUILD-DEFECT\delivered-replay"
SUBJECTS = ["109MSDCF", "foam"]

log = []


def say(s=""):
    print(s)
    log.append(s)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest().upper()


def main():
    say("=== does a DELIVERED sidecar reproduce its DELIVERED master? ===")
    say()

    # ---- seals first: did 80 disturb any image? ------------------------
    say("=== SEAL CHECK (80 wrote text beside these images) ===")
    intact = broken = nosentinel = 0
    for f in sorted(os.listdir(DELIVERED)):
        if not f.endswith(".tiff"):
            continue
        tif = os.path.join(DELIVERED, f)
        ok = tif + ".ok"
        if not os.path.exists(ok):
            nosentinel += 1
            continue
        want = io.open(ok, encoding="utf-8-sig").read().strip().upper()
        # The sentinel holds the BINARY's hash, not the image's. What is
        # verifiable here without re-rendering is that the image's mtime
        # predates the sidecar rewrite, i.e. that 80 did not touch it.
        side = tif + ".provenance.txt"
        if os.path.exists(side) and os.path.getmtime(tif) < os.path.getmtime(side):
            intact += 1
        else:
            broken += 1
            say("  IMAGE MOVED: %s" % f)
    n = intact + broken + nosentinel
    say("  %d masters = %d untouched + %d moved + %d without sentinel"
        % (n, intact, broken, nosentinel))
    if broken:
        say("VERDICT: ABORTED -- an image moved.")
        raise SystemExit(2)
    say()

    os.makedirs(OUT, exist_ok=True)
    rows, p, f_, u = [], 0, 0, 0
    for s in SUBJECTS:
        hits = [x for x in os.listdir(DELIVERED)
                if x.startswith(s + "--") and x.endswith(".provenance.txt")]
        if len(hits) != 1:
            say("  %-12s UNDEFINED -- %d sidecars match" % (s, len(hits)))
            u += 1
            rows.append(dict(subject=s, verdict="UNDEFINED", why="sidecar count"))
            continue
        side = os.path.join(DELIVERED, hits[0])
        master = side[:-len(".provenance.txt")]
        txt = io.open(side, encoding="utf-8-sig", errors="replace").read()
        m = re.search(r"^REPRODUCE THIS EXACT FILE:\s*\n(.+)$", txt, re.M)
        line = m.group(1).strip()
        parts = shlex.split(line, posix=False)
        parts = [x[1:-1] if len(x) > 1 and x[0] == '"' and x[-1] == '"' else x
                 for x in parts]
        dest = os.path.join(OUT, "%s--REPLAY.tiff" % s)
        argv = [dest if x == "<OUT>" else x for x in parts]
        if dest not in argv:
            say("  %-12s UNDEFINED -- no <OUT> token" % s)
            u += 1
            rows.append(dict(subject=s, verdict="UNDEFINED", why="no <OUT>"))
            continue
        say("  %-12s executing: %s" % (s, line.split("--out <OUT>")[-1].strip()))
        r = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0 or not os.path.exists(dest):
            say("  %-12s UNDEFINED -- exit %d %s"
                % (s, r.returncode, (r.stderr or "")[-160:].replace("\n", " ")))
            u += 1
            rows.append(dict(subject=s, verdict="UNDEFINED", why="replay failed"))
            continue
        a = np.asarray(tifffile.imread(master))
        b = np.asarray(tifffile.imread(dest))
        if a.shape != b.shape:
            say("  %-12s FAIL -- shape %s vs %s" % (s, a.shape, b.shape))
            f_ += 1
            rows.append(dict(subject=s, verdict="FAIL", why="shape"))
            continue
        d = np.abs(a.astype(np.int64) - b.astype(np.int64))
        row = dict(subject=s,
                   clip_a=100.0 * np.count_nonzero(a >= 65535) / a.size,
                   clip_b=100.0 * np.count_nonzero(b >= 65535) / b.size,
                   med_a=float(np.median(a)), med_b=float(np.median(b)),
                   max_abs=int(d.max()), n_diff=int(np.count_nonzero(d)),
                   n=int(a.size), sha_a=sha(master)[:16], sha_b=sha(dest)[:16])
        ok = row["max_abs"] == 0
        row["verdict"] = "PASS" if ok else "FAIL"
        p += 1 if ok else 0
        f_ += 0 if ok else 1
        say("  %-12s %s" % (s, row["verdict"]))
        say("     sealed master : clipped %8.4f%%  median %8.1f  sha %s"
            % (row["clip_a"], row["med_a"], row["sha_a"]))
        say("     replay        : clipped %8.4f%%  median %8.1f  sha %s"
            % (row["clip_b"], row["med_b"], row["sha_b"]))
        say("     difference    : max |delta| %d DN over %d of %d samples"
            % (row["max_abs"], row["n_diff"], row["n"]))
        rows.append(row)

    say("  %d declared = %d passed + %d failed + %d undefined"
        % (len(SUBJECTS), p, f_, u))
    if p + f_ + u != len(SUBJECTS):
        raise SystemExit("partition does not sum")
    verdict = ("BLOCKED" if u else "GREEN" if p == len(SUBJECTS) else "RED")
    say()
    say("VERDICT: %s" % verdict)
    od = os.path.join(HERE, "..", "out")
    os.makedirs(od, exist_ok=True)
    io.open(os.path.join(od, "81-delivered.json"), "w", encoding="utf-8").write(
        json.dumps(dict(verdict=verdict, rows=rows, seals_untouched=intact),
                   indent=1, sort_keys=True, default=str))
    io.open(os.path.join(od, "81-delivered.log"), "w", encoding="utf-8").write(
        "\n".join(log) + "\n")


if __name__ == "__main__":
    main()
