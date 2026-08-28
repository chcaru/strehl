"""Does the SUBSTITUTED reproduction command survive a binary change?

WHY THIS SCRIPT EXISTS, AND WHAT 77 COULD NOT SETTLE
----------------------------------------------------
`finalpass.ps1:529-533` rewrites `--auto-exposure` into `--exposure <stops>`
before printing the reproduction command into every master's sidecar. ORCH
charged that this ships "an instruction that destroys the image".

77-repro-contract.py measured the end-to-end contract twice and both were GREEN:

  HEAD binary 13D6B39160E38F82 : no substitution occurs at all (auto-exposure is
      superseded at HEAD and prints no stops, so `$expoStops` is empty and the
      branch is never entered). Repro line came out verbatim. 0 DN over
      98,898,048 samples, both subjects.
  Pin binary 44C2F2CD2E5B2894  : substitution DOES occur (`--exposure +2.61`,
      `--exposure +1.90`) and the replay is STILL bit-exact, 0 DN over
      98,898,048 samples, both subjects.

So under verbatim execution -- which is what the sidecar instructs, since it
names its binary by absolute path -- the substitution is not wrong. It is
ACCIDENTALLY RIGHT: right because `--exposure` happens to be inert at the pin,
not because the substituted command means what the original meant.

That is the claim this script tests. A command that is correct for a reason
unrelated to what it says is one binary away from being wrong, and the sidecar's
whole purpose is to survive exactly that. So: execute both candidate contracts
with a DIFFERENT binary and measure which one still lands on the image.

  ARM A  substituted, as the script prints it today, run on HEAD
  ARM B  verbatim `--auto-exposure`, as the fix will print it, run on HEAD

ARM B is the IMPROVEMENT arm the project's commissioning standard requires. A
suite that only ever plants degradations cannot tell a blind metric from a
perverse one, so the fix must be shown to move the number the RIGHT way, not
merely to avoid moving it the wrong way.

COMMISSIONING, RUN BEFORE ANY OF THAT IS REPORTED
--------------------------------------------------
The gate in 77 has only ever read GREEN. A gate that has never read RED is not
an instrument, it is a constant. Two arms run first and both must land:

  C_PLANTED  the pin command with `--limit 8` changed to `--limit 6`, run on the
             pin. Fewer frames is a guaranteed pixel change, so this MUST FAIL.
             If it passes, the comparison is not reading the files and every
             other verdict here is void.
  D_NULL     the pin command unchanged, run on the pin. This MUST PASS. If it
             fails, the gate is charging for something other than the contract
             (nondeterminism, a path mixup) and again nothing else is readable.

Both are TESTED, not merely printed: the script exits non-zero and reports
nothing further if either lands the wrong way.

Every string mutation below is anchored on a unique full token sequence and
hard-errors if it does not land, because a mutation that silently fails to apply
turns a positive control into a second null and reads as a pass.
"""
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
HEAD_EXE = os.path.join(ROOT, ".cargo-target-defect", "release", "strehl.exe")
PIN_EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
WORK = r"D:\strehl-out\BUILD-DEFECT\repro"
PIN_PHASE = os.path.join(WORK, "pin")
SUBJECTS = ["109MSDCF", "foam"]

log = []


def say(s=""):
    print(s)
    log.append(s)


def sha16(p):
    import hashlib
    return hashlib.sha256(open(p, "rb").read()).hexdigest().upper()[:16]


def mutate(line, old, new, label):
    """Replace `old` with `new`, refusing if it is absent or not unique."""
    n = line.count(old)
    if n != 1:
        raise SystemExit(
            "control %s: anchor %r occurs %d times in %r; a mutation that does "
            "not land turns a positive control into a null."
            % (label, old, n, line))
    return line.replace(old, new)


def find_sidecar(subject):
    d = os.path.join(PIN_PHASE, subject)
    if not os.path.isdir(d):
        raise SystemExit(
            "%s does not exist. Run `python 77-repro-contract.py pin` with "
            "STREHL_REPRO_EXE set to the pin first -- this script measures "
            "against that phase's masters and will not silently invent them."
            % d)
    hits = []
    for dd, _, fs in os.walk(d):
        for f in fs:
            if f.endswith(".provenance.txt"):
                hits.append(os.path.join(dd, f))
    if len(hits) != 1:
        raise SystemExit("expected exactly 1 sidecar under %s, found %d"
                         % (d, len(hits)))
    return hits[0]


def repro_line(side):
    txt = io.open(side, encoding="utf-8-sig", errors="replace").read()
    m = re.search(r"^REPRODUCE THIS EXACT FILE:\s*\n(.+)$", txt, re.M)
    if not m:
        raise SystemExit("no REPRODUCE line in %s" % side)
    return m.group(1).strip()


def execute(line, out_path):
    parts = shlex.split(line, posix=False)
    parts = [p[1:-1] if len(p) > 1 and p[0] == '"' and p[-1] == '"' else p
             for p in parts]
    argv = [out_path if p == "<OUT>" else p for p in parts]
    if out_path not in argv:
        raise SystemExit("no <OUT> placeholder in %r" % line)
    r = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
    return r, argv


def compare(a_path, b_path):
    if os.path.abspath(a_path) == os.path.abspath(b_path):
        raise SystemExit(
            "refusing to compare %s with itself -- a self-comparison reads 0 DN "
            "for any input and would make every arm here pass." % a_path)
    a = np.asarray(tifffile.imread(a_path))
    b = np.asarray(tifffile.imread(b_path))
    if a.shape != b.shape:
        return dict(shape_mismatch=True, max_abs=-1)
    ai, bi = a.astype(np.int64), b.astype(np.int64)
    d = np.abs(ai - bi)
    return dict(shape_mismatch=False,
                clip_a=100.0 * np.count_nonzero(a >= 65535) / a.size,
                clip_b=100.0 * np.count_nonzero(b >= 65535) / b.size,
                med_a=float(np.median(ai)), med_b=float(np.median(bi)),
                max_abs=int(d.max()), n_diff=int(np.count_nonzero(d)),
                n=int(a.size))


def arm(label, subject, line, out_name):
    master = find_sidecar(subject)[:-len(".provenance.txt")]
    out = os.path.join(PIN_PHASE, subject, out_name)
    r, argv = execute(line, out)
    if r.returncode != 0 or not os.path.exists(out):
        return dict(label=label, subject=subject, verdict="UNDEFINED",
                    why="exit %d" % r.returncode,
                    err=(r.stderr or r.stdout or "")[-200:])
    c = compare(master, out)
    v = "PASS" if (not c["shape_mismatch"] and c["max_abs"] == 0) else "FAIL"
    row = dict(label=label, subject=subject, verdict=v, cmd=line, **c)
    return row


def show(row):
    if row["verdict"] == "UNDEFINED":
        say("  %-22s %-10s UNDEFINED  %s" % (row["label"], row["subject"],
                                             row.get("err", "")[:80]))
        return
    say("  %-22s %-10s %s" % (row["label"], row["subject"], row["verdict"]))
    if not row["shape_mismatch"]:
        say("       reference clipped %8.4f%%  median %8.1f" % (row["clip_a"], row["med_a"]))
        say("       replay    clipped %8.4f%%  median %8.1f" % (row["clip_b"], row["med_b"]))
        say("       max |delta| %6d DN over %d of %d samples"
            % (row["max_abs"], row["n_diff"], row["n"]))


def main():
    say("=== does the SUBSTITUTED repro command survive a binary change? ===")
    say("pin  (reference, emitted the sidecars) : %s" % sha16(PIN_EXE))
    say("head (the substituted binary)          : %s" % sha16(HEAD_EXE))
    say()

    subj = SUBJECTS[0]
    side = find_sidecar(subj)
    line = repro_line(side)
    say("sidecar line as printed today:")
    say("  %s" % line)
    say()

    # ---- COMMISSIONING -------------------------------------------------
    say("=== COMMISSIONING (both must land or nothing below is readable) ===")
    planted = mutate(line, "--limit 8", "--limit 6", "C_PLANTED")
    c_row = arm("C_PLANTED limit8->6", subj, planted, "commission-planted.tiff")
    d_row = arm("D_NULL unchanged", subj, line, "commission-null.tiff")
    show(c_row)
    show(d_row)
    ok_c = c_row["verdict"] == "FAIL"
    ok_d = d_row["verdict"] == "PASS"
    say("  planted defect reads FAIL : %s" % ok_c)
    say("  known-clean reads PASS    : %s" % ok_d)
    if not (ok_c and ok_d):
        say()
        say("VERDICT: BLOCKED -- the gate is not commissioned, so it cannot be "
            "quoted for or against the fix.")
        dump("blocked")
        raise SystemExit(2)
    say()

    # ---- THE ACTUAL QUESTION -------------------------------------------
    say("=== BINARY SUBSTITUTION: substituted vs verbatim, both run on HEAD ===")
    rows = []
    for s in SUBJECTS:
        ln = repro_line(find_sidecar(s))
        a = mutate(ln, PIN_EXE, HEAD_EXE, "A_SUBSTITUTED")
        stops = re.search(r"--exposure \+?-?[0-9.]+", a)
        if not stops:
            raise SystemExit(
                "%s: the pin sidecar carries no `--exposure` token, so the "
                "substitution this script exists to test did not happen. "
                "Line was: %r" % (s, ln))
        b = mutate(a, stops.group(0), "--auto-exposure", "B_VERBATIM")
        ra = arm("A_SUBSTITUTED on HEAD", s, a, "cross-substituted.tiff")
        rb = arm("B_VERBATIM on HEAD", s, b, "cross-verbatim.tiff")
        show(ra)
        show(rb)
        rows += [ra, rb]
        say()

    # ---- GATE (printed AND conditioned on) ------------------------------
    say("=== GATE ===")
    verdicts = []
    for s in SUBJECTS:
        a = [r for r in rows if r["subject"] == s and r["label"].startswith("A_")][0]
        b = [r for r in rows if r["subject"] == s and r["label"].startswith("B_")][0]
        if a["verdict"] == "UNDEFINED" or b["verdict"] == "UNDEFINED":
            verdicts.append((s, "UNDEFINED", 0, 0))
            continue
        better = b["max_abs"] < a["max_abs"]
        destroyed = a["clip_b"] > 10.0 * max(a["clip_a"], 1e-4)
        say("  %-10s substituted max|d| %6d DN, clip %7.4f%% -> %7.4f%%"
            % (s, a["max_abs"], a["clip_a"], a["clip_b"]))
        say("  %-10s verbatim    max|d| %6d DN, clip %7.4f%% -> %7.4f%%"
            % ("", b["max_abs"], b["clip_a"], b["clip_b"]))
        say("             verbatim closer to reference : %s" % better)
        say("             substituted destroys highlights (>10x clip) : %s" % destroyed)
        verdicts.append((s, "IMPROVED" if better else "NOT-IMPROVED",
                         a["max_abs"], b["max_abs"]))
    imp = sum(1 for v in verdicts if v[1] == "IMPROVED")
    ni = sum(1 for v in verdicts if v[1] == "NOT-IMPROVED")
    un = sum(1 for v in verdicts if v[1] == "UNDEFINED")
    say("  %d declared = %d improved + %d not-improved + %d undefined"
        % (len(SUBJECTS), imp, ni, un))
    if imp + ni + un != len(SUBJECTS):
        raise SystemExit("partition does not sum")
    verdict = ("BLOCKED" if un else
               "SUBSTITUTION-IS-WORSE" if imp == len(SUBJECTS) else
               "NO-DIFFERENCE")
    say()
    say("VERDICT: %s" % verdict)
    dump(verdict, rows, c_row, d_row)


def dump(verdict, rows=None, c_row=None, d_row=None):
    od = os.path.join(HERE, "..", "out")
    os.makedirs(od, exist_ok=True)
    io.open(os.path.join(od, "78-crossbinary.json"), "w", encoding="utf-8").write(
        json.dumps(dict(verdict=verdict, rows=rows, commission_planted=c_row,
                        commission_null=d_row, pin=sha16(PIN_EXE),
                        head=sha16(HEAD_EXE)),
                   indent=1, sort_keys=True, default=str))
    io.open(os.path.join(od, "78-crossbinary.log"), "w", encoding="utf-8").write(
        "\n".join(log) + "\n")


if __name__ == "__main__":
    main()
