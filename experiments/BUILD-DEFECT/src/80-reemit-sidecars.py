"""Re-emit the delivered corpus's 26 sidecars under the corrected contract.

WHY REWRITE RATHER THAN RE-RENDER
----------------------------------
The 26 masters in acceptance/SHIP-V4 are sealed: each carries a `.ok` sentinel
holding the binary hash, and accept.py compares arms by those files. Re-rendering
to regenerate a sidecar would replace the sealed artifact in order to correct a
text file beside it. The fix is purely textual and the masters are not in
question, so the sidecars are rewritten in place and the images are not touched.

WHAT THE NEW LINE IS BUILT FROM
--------------------------------
Not by inverting the substitution -- by reading the invocation the run actually
recorded. Every sidecar prints the real command line, `--out` and all, before its
binary self-report. Replacing the concrete output path with the `<OUT>` token
yields, by construction, "what was run". Inverting `--exposure +2.60` back to
`--auto-exposure` would instead reconstruct the intent from its own corruption.

The two are cross-checked against each other anyway: the stops recovered from the
defective repro line must equal the stops in the binary's self-report, or the
file is left alone and counted as UNRESOLVED.

HOW THIS IS KNOWN TO PRODUCE THE SAME TEXT AS THE FIXED SCRIPT
---------------------------------------------------------------
It is not asserted, it is measured, and it runs BEFORE any delivered file is
opened for writing. 79-negcontrol-finalpass.py left two sidecars on disk for the
same subject and flags: one written by the PRE-FIX script and one by the FIXED
script. This script rewrites the pre-fix one and requires the result to be
byte-identical, from "REPRODUCE THIS EXACT FILE:" to end of file, to the fixed
one. If that fails, nothing is written and the run aborts -- a re-emitter that
has not been shown to agree with the emitter is just a second opinion.
"""
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DELIVERED = r"C:\dev\strehl-out\acceptance\SHIP-V4"
BACKUP = r"D:\strehl-out\BUILD-DEFECT\sidecar-backup"
NEGRED = r"D:\strehl-out\BUILD-DEFECT\repro\negred\109MSDCF"
NEGGREEN = r"D:\strehl-out\BUILD-DEFECT\repro\neggreen\109MSDCF"

MARK = "REPRODUCE THIS EXACT FILE:"
OLD_NOTE = "  (--auto-exposure replaced by the gain it CHOSE; re-running with"

log = []


def say(s=""):
    print(s)
    log.append(s)


def read_text(p):
    b = open(p, "rb").read()
    bom = b.startswith(b"\xef\xbb\xbf")
    t = b[3:].decode("utf-8") if bom else b.decode("utf-8")
    crlf = "\r\n" in t
    return t, bom, crlf


def write_text(p, t, bom, crlf):
    if crlf:
        t = t.replace("\r\n", "\n").replace("\n", "\r\n")
    b = t.encode("utf-8")
    if bom:
        b = b"\xef\xbb\xbf" + b
    tmp = p + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(b)
    os.replace(tmp, p)


def observed_block(stops):
    return [
        "  OBSERVED, NOT AN INSTRUCTION: --auto-exposure chose %s stops" % stops,
        "   for this file. It is recorded so the choice is auditable; it is",
        "   deliberately NOT substituted into the command above. Replaying",
        "   this file's own chosen gain as --exposure %s on a binary" % stops,
        "   where --exposure is load-bearing clips 85% of the frame to white",
        "   (measured, docs/research/BUILD-DEFECT.md section 22). The command",
        "   above is bit-exact with the binary it names, and preserves this",
        "   file's exposure on binaries that post-date it.",
    ]


def rewrite(text):
    """Return (new_text, outcome). Never raises; the caller counts outcomes."""
    lines = text.split("\r\n") if "\r\n" in text else text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip() == MARK]
    if len(idx) != 1:
        return None, "no-unique-REPRODUCE-marker"
    i = idx[0]
    cmd_i = next((j for j in range(i + 1, len(lines)) if lines[j].strip()), None)
    if cmd_i is None:
        return None, "no-command-after-marker"
    cmd = lines[cmd_i]
    m = re.search(r"--exposure[= ](\+?-?\d+\.\d+)", cmd)
    if not m:
        return None, "no-substitution-present"
    stops_from_cmd = m.group(1)

    # Ground truth: the invocation the run actually recorded.
    inv = [l for l in lines[:i]
           if "strehl.exe stack" in l and "--out " in l and "<OUT>" not in l]
    if len(inv) != 1:
        return None, "invocation-not-unique(%d)" % len(inv)
    true_cmd = re.sub(r'--out\s+"[^"]*"', "--out <OUT>", inv[0]).strip()
    if "--out <OUT>" not in true_cmd:
        return None, "could-not-tokenise-out-path"
    if "--auto-exposure" not in true_cmd:
        return None, "recorded-invocation-had-no-auto-exposure"

    # Cross-check against the binary's own self-report.
    sr = [l for l in lines if "reproduce this exact file with --exposure=" in l]
    if len(sr) == 1:
        v = re.search(r"--exposure=(\+?-?\d+\.\d+)", sr[0]).group(1)
        if float(v) != float(stops_from_cmd):
            return None, "stops-disagree(cmd %s vs self-report %s)" % (
                stops_from_cmd, v)

    indent = cmd[:len(cmd) - len(cmd.lstrip())] or "  "
    out = lines[:cmd_i] + [indent + true_cmd]
    j = cmd_i + 1
    while j < len(lines):
        if lines[j] == OLD_NOTE:
            j += 2  # drop the two-line note
            out += observed_block(stops_from_cmd)
            continue
        out.append(lines[j])
        j += 1
    if not any("OBSERVED, NOT AN INSTRUCTION" in l for l in out):
        return None, "old-note-anchor-not-found"
    sep = "\r\n" if "\r\n" in text else "\n"
    return sep.join(out), "rewritten"


def tail(p):
    t, _, _ = read_text(p)
    k = t.find(MARK)
    if k < 0:
        raise SystemExit("no %s in %s" % (MARK, p))
    return t[k:].replace("\r\n", "\n").rstrip("\n")


def only_sidecar(d):
    hits = []
    for dd, _, fs in os.walk(d):
        for f in fs:
            if f.endswith(".provenance.txt"):
                hits.append(os.path.join(dd, f))
    if len(hits) != 1:
        raise SystemExit("expected 1 sidecar under %s, found %d" % (d, len(hits)))
    return hits[0]


def equivalence():
    """The re-emitter must agree with the emitter, measured, before any write."""
    say("=== EQUIVALENCE: does this rewriter produce the fixed script's text? ===")
    red, green = only_sidecar(NEGRED), only_sidecar(NEGGREEN)
    t, _, _ = read_text(red)
    new, outcome = rewrite(t)
    if new is None:
        say("  rewrite of the pre-fix sidecar returned %s" % outcome)
        return False
    got = new[new.find(MARK):].replace("\r\n", "\n").rstrip("\n")
    want = tail(green)
    same = got == want
    say("  pre-fix sidecar  : %s" % red)
    say("  fixed sidecar    : %s" % green)
    say("  rewritten tail == fixed tail : %s" % same)
    if not same:
        import difflib
        for d in list(difflib.unified_diff(want.split("\n"), got.split("\n"),
                                           "emitted", "rewritten", lineterm=""))[:30]:
            say("    %s" % d)
    return same


def main():
    say("=== re-emit delivered sidecars under the corrected contract ===")
    say()
    if not equivalence():
        say()
        say("VERDICT: ABORTED -- rewriter does not reproduce the emitter's text. "
            "No delivered file was opened for writing.")
        dump("ABORTED", [])
        raise SystemExit(2)
    say()

    found = []
    for dd, _, fs in os.walk(DELIVERED):
        for f in fs:
            if f.endswith(".provenance.txt"):
                found.append(os.path.join(dd, f))
    found.sort()
    say("=== APPLY (%d sidecars found) ===" % len(found))
    os.makedirs(BACKUP, exist_ok=True)
    counts, rows = {}, []
    for p in found:
        t, bom, crlf = read_text(p)
        new, outcome = rewrite(t)
        if new is not None:
            shutil.copy2(p, os.path.join(BACKUP, os.path.basename(p)))
            write_text(p, new, bom, crlf)
        counts[outcome] = counts.get(outcome, 0) + 1
        rows.append(dict(file=os.path.basename(p), outcome=outcome))
    for k in sorted(counts):
        say("  %-40s %d" % (k, counts[k]))
    say("  %d found = %s" % (len(found), " + ".join(
        "%d %s" % (counts[k], k) for k in sorted(counts))))
    if sum(counts.values()) != len(found):
        raise SystemExit("partition does not sum")
    say()

    # Post-verify by re-reading from disk, not by trusting the write.
    say("=== VERIFY (re-read from disk) ===")
    ok = bad = 0
    for p in found:
        t, _, _ = read_text(p)
        k = t.find(MARK)
        cmd = [l for l in t[k:].split("\n")[1:] if l.strip()][0]
        good = ("--auto-exposure" in cmd
                and not re.search(r"--exposure[= ]", cmd)
                and "OBSERVED, NOT AN INSTRUCTION" in t[k:])
        ok += 1 if good else 0
        bad += 0 if good else 1
        if not good:
            say("  STILL WRONG: %s" % os.path.basename(p))
            say("     %s" % cmd.strip()[:150])
    say("  %d found = %d correct + %d still wrong" % (len(found), ok, bad))
    verdict = "RE-EMITTED" if (bad == 0 and ok == len(found)) else "INCOMPLETE"
    say()
    say("VERDICT: %s   (backups in %s)" % (verdict, BACKUP))
    dump(verdict, rows)
    if verdict != "RE-EMITTED":
        raise SystemExit(2)


def dump(verdict, rows):
    od = os.path.join(HERE, "..", "out")
    os.makedirs(od, exist_ok=True)
    io.open(os.path.join(od, "80-reemit.json"), "w", encoding="utf-8").write(
        json.dumps(dict(verdict=verdict, rows=rows, delivered=DELIVERED,
                        backup=BACKUP), indent=1, sort_keys=True))
    io.open(os.path.join(od, "80-reemit.log"), "w", encoding="utf-8").write(
        "\n".join(log) + "\n")


if __name__ == "__main__":
    main()
