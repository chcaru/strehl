r"""Does the reproduction command in a provenance sidecar actually reproduce?

THE DEFECT. finalpass.ps1 rewrote `--auto-exposure` into `--exposure <stops>`
when it emitted the sidecar's REPRODUCE line. That substitution was invented
while `--exposure` was inert, when it could not do harm. It is not inert any
more.

WHY THIS IS TESTED ON PIXELS AND NOT ON HASHES. This lane withdrew a true
accusation once by comparing two renders on their file hashes: they differed,
so the flag looked live. It was not -- 0 of 98,898,048 samples differed and the
11 differing bytes were the embedded tone record, i.e. the file describing its
own argv. A hash is sensitive to any change and specific to none. Every verdict
here is a per-sample comparison, and the reported quantities are clipped
fraction, median and max |delta| in DN.

WHAT "VERBATIM" MEANS HERE. The sidecar's REPRODUCE line is parsed out of the
emitted file and executed as argv, with only the `<OUT>` placeholder replaced.
Nothing else is normalised, re-quoted or helpfully corrected, because the thing
under test is what a reader would actually type.

THE SUBJECTS ARE CHOSEN TO DISAGREE. 109MSDCF's auto gain is strongly positive
and mis-replaying it CLIPS, which is a loud failure. foam's is negative and
mis-replaying it DARKENS, which is a quiet one. A harness that only ever sees
blowouts cannot distinguish a test that detects mis-exposure from a test that
detects saturation, so the quiet case is not optional.

THE GATE. PASS requires max |delta| == 0 over every sample: a reproduction
command either reproduces the file or does not, and there is no tolerance band
in which a "REPRODUCE THIS EXACT FILE" line is partially true. UNDEFINED is a
distinct outcome from FAIL and is counted separately, so a subject whose render
or replay errored can never be read as a subject that passed.
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
SCRIPT = os.path.join(ROOT, "scripts", "finalpass.ps1")
EXE_DEFAULT = os.path.join(ROOT, ".cargo-target-defect", "release", "strehl.exe")


def _exe():
    """Binary under test, overridable -- but a typo must refuse, not fall back.

    The substitution defect at finalpass.ps1:529 is only reachable with a binary
    that PRINTS a chosen exposure, because the branch is guarded on `$expoStops`
    being non-empty. HEAD prints nothing (auto-exposure is superseded), so HEAD
    cannot reach it; the pin 9b05d0b7 does print stops and is what emitted the
    26 delivered sidecars. Selecting the binary is therefore load-bearing for
    the control, and silently rendering with the wrong one would produce a
    green that means nothing.
    """
    ov = os.environ.get("STREHL_REPRO_EXE")
    if ov is None:
        return EXE_DEFAULT
    if not os.path.isfile(ov):
        raise SystemExit(
            "STREHL_REPRO_EXE is set to %r which is not a file. Refusing to "
            "fall back to %s -- a control that renders with a binary other "
            "than the one named is not a control." % (ov, EXE_DEFAULT))
    return ov


EXE = _exe()
WORK = r"D:\strehl-out\BUILD-DEFECT\repro"
LIBRARY = r"D:\personal\macro"

SUBJECTS = ["109MSDCF", "foam"]
FLAGS = "--srgb --auto-exposure --limit 8"
ARM = "REPROTEST"

# Windows PowerShell 5.1 on this machine cannot autoload Microsoft.PowerShell.
# Utility: `powershell -NoProfile -Command Get-FileHash <file>` exits 1 with
# CommandNotFoundException, with PSModulePath both inherited and cleared, while
# `pwsh` returns the hash. finalpass.ps1 calls Get-FileHash to record the
# binary's sha256, so driving it through 5.1 fails inside the script and yields
# no sidecar at all. Measured: 2/2 subjects UNDEFINED under `powershell`.
SHELL = "pwsh"

log = []


def say(s=""):
    print(s)
    log.append(s)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def emit_sidecar(subject, outroot):
    """Drive the real finalpass.ps1 -- not a copy of its logic."""
    os.makedirs(outroot, exist_ok=True)
    cmd = [SHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-File", SCRIPT,
           "-Arm", ARM,
           "-Only", subject,
           "-Flags", FLAGS,
           "-Exe", EXE,
           "-Library", LIBRARY,
           "-OutRoot", outroot,
           "-NoPresent"]
    p = run(cmd, cwd=ROOT)
    side = None
    for d, _, fs in os.walk(outroot):
        for f in fs:
            if f.endswith(".provenance.txt") and subject in f:
                side = os.path.join(d, f)
    return side, p


def repro_line(side):
    """Pull the REPRODUCE line out of the sidecar exactly as written."""
    txt = io.open(side, encoding="utf-8-sig", errors="replace").read()
    m = re.search(r"^REPRODUCE THIS EXACT FILE:\s*\n(.+)$", txt, re.M)
    if not m:
        raise SystemExit("no REPRODUCE line in %s" % side)
    return m.group(1).strip()


def execute_repro(line, out_path):
    """Execute the printed command verbatim, substituting only <OUT>."""
    parts = shlex.split(line, posix=False)
    parts = [p[1:-1] if len(p) > 1 and p[0] == '"' and p[-1] == '"' else p
             for p in parts]
    argv = [out_path if p == "<OUT>" else p for p in parts]
    if out_path not in argv:
        raise SystemExit("the REPRODUCE line carried no <OUT> placeholder: %r" % line)
    return run(argv, cwd=ROOT), argv


def compare(a_path, b_path):
    a = np.asarray(tifffile.imread(a_path))
    b = np.asarray(tifffile.imread(b_path))
    if a.shape != b.shape:
        return dict(shape_mismatch=True, a=str(a.shape), b=str(b.shape))
    ai, bi = a.astype(np.int64), b.astype(np.int64)
    d = np.abs(ai - bi)
    return dict(shape_mismatch=False,
                clip_a=float(np.count_nonzero(a >= 65535)) / a.size,
                clip_b=float(np.count_nonzero(b >= 65535)) / b.size,
                med_a=float(np.median(ai)), med_b=float(np.median(bi)),
                max_abs=int(d.max()), n_diff=int(np.count_nonzero(d)),
                n=int(a.size))


def contract_violation(line):
    """The sidecar must instruct what was RUN, not a transform of it.

    Bit-exactness alone cannot express this defect. Measured: driven with the
    pin 44C2F2CD2E5B2894, the pre-fix script substituted `--exposure +2.61` and
    the replay was still bit-exact, 0 DN over 98,898,048 samples, because
    `--exposure` is inert in that binary. A gate that compared only pixels read
    PASS on the defective script -- it was a constant, not an instrument. So the
    contract is tested directly, in addition to the pixels, and a substituted
    line FAILS even when it happens to reproduce.
    """
    if "--auto-exposure" not in FLAGS:
        return None
    if "--auto-exposure" not in line:
        return "flags carried --auto-exposure but the repro line dropped it"
    m = re.search(r"--exposure[\s=]", line)
    if m:
        return "repro line substituted %r for --auto-exposure" % line[m.start():m.start() + 20]
    return None


def phase(tag, outroot):
    say("=== %s ===" % tag)
    rows, passed, failed, undefined = [], 0, 0, 0
    for s in SUBJECTS:
        side, p = emit_sidecar(s, os.path.join(outroot, s))
        if side is None:
            say("  %-12s UNDEFINED -- no sidecar emitted (exit %d)" % (s, p.returncode))
            say("     %s" % (p.stderr or p.stdout or "")[-300:].replace("\n", " ")[:280])
            undefined += 1
            rows.append(dict(subject=s, verdict="UNDEFINED", why="no sidecar"))
            continue
        master = side[:-len(".provenance.txt")]
        line = repro_line(side)
        replay = os.path.join(outroot, s, "%s--REPLAY.tiff" % s)
        r, argv = execute_repro(line, replay)
        if r.returncode != 0 or not os.path.exists(replay):
            say("  %-12s UNDEFINED -- replay did not produce a file (exit %d)"
                % (s, r.returncode))
            undefined += 1
            rows.append(dict(subject=s, verdict="UNDEFINED", why="replay failed",
                             repro=line))
            continue
        c = compare(master, replay)
        viol = contract_violation(line)
        ok = (not c["shape_mismatch"]) and c["max_abs"] == 0 and viol is None
        v = "PASS" if ok else "FAIL"
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        say("  %-12s %s" % (s, v))
        say("     repro flags : %s" % line.split("--out <OUT>")[-1].strip())
        if viol:
            say("     CONTRACT    : %s" % viol)
        if not c["shape_mismatch"]:
            say("     original    : clipped %7.4f%%  median %8.1f" % (100 * c["clip_a"], c["med_a"]))
            say("     replay      : clipped %7.4f%%  median %8.1f" % (100 * c["clip_b"], c["med_b"]))
            say("     difference  : max |delta| %5d DN over %d of %d samples"
                % (c["max_abs"], c["n_diff"], c["n"]))
        rows.append(dict(subject=s, verdict=v, repro=line, contract=viol, **c))
    say("  %d declared = %d passed + %d failed + %d undefined"
        % (len(SUBJECTS), passed, failed, undefined))
    if passed + failed + undefined != len(SUBJECTS):
        raise SystemExit("partition does not sum")
    say()
    return rows, passed, failed, undefined


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "before"
    say("=== does the sidecar's REPRODUCE command reproduce the file? ===")
    say("binary under test : %s" % EXE)
    import hashlib
    h = hashlib.sha256(open(EXE, "rb").read()).hexdigest().upper()
    say("sha256            : %s" % h[:16])
    say("flags             : %s" % FLAGS)
    say()
    rows, p, f, u = phase("PHASE %s" % which.upper(),
                          os.path.join(WORK, which))
    if u:
        # A run that could not execute is not evidence either way. Reporting it
        # as RED would let a broken harness masquerade as a negative control
        # that fired, which is the same error as letting UNDEFINED read as PASS.
        verdict = "BLOCKED"
    elif p == len(SUBJECTS):
        verdict = "GREEN"
    else:
        verdict = "RED"
    say("VERDICT: %s  (%d/%d reproduce bit-exactly, %d failed, %d undefined)"
        % (verdict, p, len(SUBJECTS), f, u))
    od = os.path.join(HERE, "..", "out")
    os.makedirs(od, exist_ok=True)
    io.open(os.path.join(od, "77-repro-contract-%s.json" % which), "w",
            encoding="utf-8").write(json.dumps(
                dict(phase=which, binary=EXE, sha=h[:16], flags=FLAGS,
                     rows=rows, passed=p, failed=f, undefined=u,
                     verdict=verdict), indent=1, sort_keys=True, default=str))
    io.open(os.path.join(od, "77-repro-contract-%s.log" % which), "w",
            encoding="utf-8").write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
