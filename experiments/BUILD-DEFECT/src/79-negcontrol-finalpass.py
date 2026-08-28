"""Negative control: prove the contract test can express the defect.

The gate in 77-repro-contract.py must be shown to read RED on the script as it
shipped before this fix, or a green after the fix means nothing. That is the
whole of this script.

It does NOT hand-edit anything. It takes the pre-fix bytes from the git object
store, writes them over scripts/finalpass.ps1, runs the real gate, and restores
the fixed file from a copy taken before it started.

THREE HAZARDS THIS PROJECT HAS BEEN BITTEN BY, ALL GUARDED HERE
---------------------------------------------------------------
1. `git checkout -- <path>` reverts to HEAD and has destroyed uncommitted work
   on this machine. The restore is from a byte copy in %TEMP%, taken first,
   verified after, in a `finally` so an exception cannot skip it.
2. `git show HEAD:path > file` in PowerShell re-encodes the stream. The blob is
   read as BYTES through subprocess and written as bytes.
3. A mutation that does not land turns a positive control into a second null and
   reads as a pass. The pre-fix blob is asserted to contain the exact defective
   line, and the restored file is asserted byte-identical to the backup.

Not a hazard here, but worth recording: the sibling trap is `Copy-Item`
preserving an older mtime so a build system skips the rebuild and a control runs
stale bytes. finalpass.ps1 is interpreted, so there is nothing to rebuild and
nothing to go stale.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REL = "scripts/finalpass.ps1"
LIVE = os.path.join(ROOT, "scripts", "finalpass.ps1")
PIN = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"

DEFECT_ANCHOR = b"        ($Flags -replace '--auto-exposure', \"--exposure $expoStops\")"
FIX_ANCHOR = b"    $repro = $Flags"

log = []


def say(s=""):
    print(s)
    log.append(s)


def git_blob(rev, rel):
    p = subprocess.run(["git", "show", "%s:%s" % (rev, rel)],
                       capture_output=True, cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit("git show %s:%s failed: %s" % (rev, rel, p.stderr[:200]))
    return p.stdout


def run_gate(phase):
    env = dict(os.environ)
    env["STREHL_REPRO_EXE"] = PIN
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, os.path.join(HERE, "77-repro-contract.py"),
                        phase], capture_output=True, text=True, cwd=HERE, env=env)
    out = p.stdout or ""
    verdict = "UNPARSEABLE"
    for ln in out.splitlines():
        if ln.startswith("VERDICT:"):
            verdict = ln.split()[1]
    return verdict, out


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()
    say("=== negative control: can the contract gate express the defect? ===")
    say("repo HEAD (holds the PRE-FIX script) : %s" % head[:8])
    say()

    fixed = open(LIVE, "rb").read()
    if FIX_ANCHOR not in fixed:
        raise SystemExit(
            "the working copy does not contain the fix anchor %r. Refusing to "
            "run: this control only means something if it starts from the fixed "
            "file and returns to it." % FIX_ANCHOR)

    backup = os.path.join(tempfile.gettempdir(), "finalpass.fixed.backup.ps1")
    with open(backup, "wb") as fh:
        fh.write(fixed)
    if open(backup, "rb").read() != fixed:
        raise SystemExit("backup at %s is not byte-identical" % backup)
    say("backup taken : %s (%d bytes, verified identical)" % (backup, len(fixed)))

    prefix = git_blob(head, REL)
    if DEFECT_ANCHOR not in prefix:
        raise SystemExit(
            "the %s blob of %s does NOT contain the defective substitution line "
            "%r. The control cannot plant a defect that is not there; aborting "
            "rather than reporting a green that means the mutation missed."
            % (head[:8], REL, DEFECT_ANCHOR))
    say("pre-fix blob : %d bytes, defective substitution line PRESENT" % len(prefix))
    say()

    red = green = "NOT-RUN"
    try:
        with open(LIVE, "wb") as fh:
            fh.write(prefix)
        assert open(LIVE, "rb").read() == prefix
        say("--- ARM RED: gate run against the PRE-FIX script ---")
        red, out = run_gate("negred")
        for ln in out.splitlines():
            if ln.strip().startswith(("109MSDCF", "foam", "repro flags",
                                      "CONTRACT", "2 declared", "VERDICT")):
                say("   %s" % ln.strip())
    finally:
        with open(LIVE, "wb") as fh:
            fh.write(fixed)
        restored = open(LIVE, "rb").read()
        if restored != fixed:
            raise SystemExit("RESTORE FAILED -- %s is not the fixed file. "
                             "Copy is at %s." % (LIVE, backup))
        say("restored     : working copy is byte-identical to the backup")

    say()
    say("--- ARM GREEN: gate run against the FIXED script ---")
    green, out = run_gate("neggreen")
    for ln in out.splitlines():
        if ln.strip().startswith(("109MSDCF", "foam", "repro flags", "CONTRACT",
                                  "OBSERVED", "2 declared", "VERDICT")):
            say("   %s" % ln.strip())

    say()
    say("=== RESULT ===")
    say("  pre-fix script : %s   (must be RED)" % red)
    say("  fixed script   : %s   (must be GREEN)" % green)
    ok = (red == "RED" and green == "GREEN")
    say("  commissioned   : %s" % ok)
    say()
    say("VERDICT: %s" % ("COMMISSIONED" if ok else "NOT-COMMISSIONED"))
    od = os.path.join(HERE, "..", "out")
    os.makedirs(od, exist_ok=True)
    io.open(os.path.join(od, "79-negcontrol.log"), "w",
            encoding="utf-8").write("\n".join(log) + "\n")
    if not ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
