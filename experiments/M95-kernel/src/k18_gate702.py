"""Discipline 702 applied to my own verifier: does it work in the mode its callers use?

The orchestrator measured that scripts/corpus_lint.py could not print the
violations it found, because Python selects the ANSI codepage (cp1252) for
REDIRECTED or PIPED stdout, and this corpus is full of characters cp1252
cannot encode. print() raised mid-loop, the list truncated to nothing, and the
process exited 1 -- the same code the linter uses for "violations found". A
green run and a broken run became the same observation.

Every one of my 45 harness scripts reports through stdout and none of them
reconfigure it. verify_s20.py ends with `sys.exit(1 if bad else 0)`, so it has
the identical colliding contract. I have never seen it fail only because I set
PYTHONIOENCODING=utf-8 by habit before every call -- a convention announced,
not a convention enforced. This measures the exposure instead of assuming it,
in both directions, BEFORE the fix.

The subject is verify_s20.py, the verifier behind section 20's headline.

--------------------------------------------------------------------------
BARS, REGISTERED BEFORE THE FIRST RUN
--------------------------------------------------------------------------

C0  POWER CONTROL, and the whole experiment is void without it.
    A canary that prints the offending characters must FAIL under the cp1252
    arm and SUCCEED under the utf-8 arm. If the canary survives cp1252 then
    this harness is not reproducing the caller mode at all, every "not
    exposed" reading below is vacuous, and I must report that instead of a
    null. This is the instrument saying otherwise.

B1  EXPOSURE. verify_s20.py under cp1252 with stdout captured, versus utf-8.
      EXPOSED      if the two arms disagree on printed result lines, or the
                   cp1252 arm emits a UnicodeEncodeError.
      NOT EXPOSED  if both arms print the same number of ok/BAD lines and the
                   same verdict.

B2  COLLISION, only meaningful if B1 is EXPOSED.
      COLLIDING    if the tool-failure exit code equals the subject-failure
                   exit code (1), so a caller cannot tell them apart.
      DISTINCT     otherwise.

B3  DOES THE NEGATIVE CONTROL FAIL SAFE? This is the one that can invalidate
    section 20. negctl_s20.py scores a mutation CAUGHT on `rc != 0 and bad > 0`.
    Apply that exact predicate, copied from the file and asserted to still be
    present, to a run that failed as a TOOL rather than on its subject.
      UNSOUND      if the predicate reads CAUGHT on a tool failure, because
                   then the 5/5 counted crashes as catches and proves nothing.
      FAILS SAFE   if it reads MISSED.

B4  POST-FIX, checked by re-running this file after the repair.
      FIXED        cp1252 and utf-8 arms agree line for line AND a tool
                   failure exits with a code that is not 1.
      NOT FIXED    otherwise.

I expect B1 EXPOSED and B3 FAILS SAFE. I am recording that expectation here so
that if B3 comes back UNSOUND I cannot quietly rewrite what I predicted: it
would mean section 20's negative control counted crashes as catches and the
5/5 has to be withdrawn and retaken.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

SRC = Path(__file__).resolve().parent
OUT = SRC.parent / "out"
ROOT = SRC.parents[2]
VERIFY = SRC / "verify_s20.py"
NEGCTL = SRC / "negctl_s20.py"

# The characters the corpus uses that cp1252 cannot encode.
HOSTILE = "\u0394 \u2212 \u2192 \u2264"  # delta, minus, arrow, less-or-equal


def run(script, encoding, extra_env=None):
    """Run a script exactly as an agent tool call does: stdout to a PIPE."""
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    if encoding is None:
        env.pop("PYTHONIOENCODING", None)
    else:
        env["PYTHONIOENCODING"] = encoding
    if extra_env:
        env.update(extra_env)
    r = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        cwd=str(ROOT),
        env=env,
    )
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    okc = sum(1 for ln in out.splitlines() if ln.strip().startswith("ok "))
    badc = sum(1 for ln in out.splitlines() if ln.strip().startswith("BAD"))
    return {
        "rc": r.returncode,
        "stdout_chars": len(out),
        "stderr_chars": len(err),
        "ok_lines": okc,
        "bad_lines": badc,
        "unicode_error": "UnicodeEncodeError" in err,
        "verdict": ("GREEN" if "GREEN" in out else "RED" if "RED" in out else "NONE"),
        "env": ("PYTHONIOENCODING=" + encoding) if encoding else "PYTHONIOENCODING unset",
    }


def show(label, r):
    print(
        f"  {label:<26} rc={r['rc']:<3} stdout={r['stdout_chars']:<6} "
        f"stderr={r['stderr_chars']:<5} ok={r['ok_lines']:<3} BAD={r['bad_lines']:<3} "
        f"verdict={r['verdict']:<6} UnicodeEncodeError={r['unicode_error']}"
    )


print("=" * 78)
print("k18 -- discipline 702 on my own verifier: tested in the caller's mode")
print("=" * 78)
print(f"python   {sys.version.split()[0]}")
print(f"subject  {VERIFY.relative_to(ROOT)}")
print(f"hostile  {HOSTILE!r}")

# ---------------------------------------------------------------- C0 canary
print("\n-- C0 power control: can this harness reproduce the failure at all? --")
canary = Path(tempfile.gettempdir()) / "m95_canary702.py"
canary.write_text(
    "print('canary start')\nprint('" + HOSTILE + "')\nprint('canary end')\n",
    encoding="utf-8",
)
c_cp = run(canary, "cp1252")
c_utf = run(canary, "utf-8")
show("canary cp1252", c_cp)
show("canary utf-8", c_utf)
c0 = "PASS" if (c_cp["rc"] != 0 and c_cp["unicode_error"] and c_utf["rc"] == 0) else "FAIL"
print(f"  C0 = {c0}  (cp1252 must break the canary, utf-8 must not)")
if c0 != "PASS":
    canary.unlink(missing_ok=True)
    sys.exit(
        "C0 FAILED: this harness is not reproducing the caller mode, so every "
        "reading below would be vacuous. Refusing to report a null."
    )
print(f"  canary rc under cp1252 = {c_cp['rc']}, and that rc is "
      f"{'THE SAME AS' if c_cp['rc'] == 1 else 'different from'} a subject failure's 1")

# ------------------------------------------------------------------ B1/B2
print("\n-- B1 exposure: verify_s20.py in both modes, stdout piped --")
v_cp = run(VERIFY, "cp1252")
v_utf = run(VERIFY, "utf-8")
v_unset = run(VERIFY, None)
show("verify cp1252", v_cp)
show("verify utf-8", v_utf)
show("verify (unset)", v_unset)

agree = (
    v_cp["ok_lines"] == v_utf["ok_lines"]
    and v_cp["bad_lines"] == v_utf["bad_lines"]
    and v_cp["verdict"] == v_utf["verdict"]
    and not v_cp["unicode_error"]
)
b1 = "NOT EXPOSED" if agree else "EXPOSED"
print(f"  B1 = {b1}")
print(f"     utf-8  printed {v_utf['ok_lines']} ok / {v_utf['bad_lines']} BAD, verdict {v_utf['verdict']}")
print(f"     cp1252 printed {v_cp['ok_lines']} ok / {v_cp['bad_lines']} BAD, verdict {v_cp['verdict']}")
print(f"     lost {v_utf['ok_lines'] - v_cp['ok_lines']} ok lines and "
      f"{v_utf['stdout_chars'] - v_cp['stdout_chars']} characters of report")

if b1 == "EXPOSED":
    b2 = "COLLIDING" if v_cp["rc"] == 1 else "DISTINCT"
    print(f"  B2 = {b2}  (tool failure rc={v_cp['rc']}, subject failure rc=1)")
else:
    b2 = "N/A"
    print("  B2 = N/A (nothing to collide)")

# ---------------------------------------------------------------------- B3
print("\n-- B3 does negctl_s20's CAUGHT predicate fail safe on a tool failure? --")
neg_src = NEGCTL.read_text(encoding="utf-8")
PREDICATES = {
    "if rc != 0 and bad > 0:": lambda rc, bad: rc != 0 and bad > 0,
    "if rc == 1 and bad > 0:": lambda rc, bad: rc == 1 and bad > 0,
}
found = [p for p in PREDICATES if p in neg_src]
if len(found) != 1:
    sys.exit(
        f"CAUGHT PREDICATE NOT IDENTIFIED in negctl_s20.py (matched {len(found)}) "
        "-- B3 would be testing a predicate the control does not use"
    )
PREDICATE = found[0]
scores = PREDICATES[PREDICATE]
print(f"  predicate read from negctl_s20.py: {PREDICATE!r}")

# Two independent ways to break the tool. The codepage route stops working once
# the verifier reconfigures its own stdout -- which is the repair -- so the
# artifact route is what keeps this arm alive afterwards.
JSONP = ROOT / "experiments" / "M95-kernel" / "out" / "k17_crop.json"
_stash = JSONP.read_bytes()
try:
    JSONP.unlink()
    v_noart = run(VERIFY, "utf-8")
finally:
    JSONP.write_bytes(_stash)
art_restored = JSONP.read_bytes() == _stash

inductions = [
    ("codepage, PYTHONIOENCODING unset", v_unset),
    ("required artifact removed", v_noart),
]
any_caught = False
tool_rcs = []
for how, r in inductions:
    caught_it = scores(r["rc"], r["bad_lines"])
    any_caught = any_caught or caught_it
    tool_rcs.append(r["rc"])
    print(
        f"  {how:<36} rc={r['rc']}  BAD={r['bad_lines']}  "
        f"-> predicate scores {'CAUGHT' if caught_it else 'MISSED'}"
    )
print(f"  artifact restored byte-identical: {art_restored}")
b3 = "UNSOUND" if any_caught else "FAILS SAFE"
print(f"  B3 = {b3}")
if b3 == "UNSOUND":
    print("  ** section 20's negative control counted crashes as catches; withdraw the 5/5 **")
else:
    print("  the predicate requires a POSITIVE signal (BAD>0) parsed from stdout,")
    print("  so a crash that prints no BAD line cannot be counted as a catch.")

# ---------------------------------------------------------------------- B4
agree_lines = (
    v_cp["ok_lines"] == v_utf["ok_lines"]
    and v_cp["bad_lines"] == v_utf["bad_lines"]
    and v_cp["verdict"] == v_utf["verdict"]
    and not v_cp["unicode_error"]
)
rc_distinct = all(rc != 1 for rc in tool_rcs)
b4 = "FIXED" if (agree_lines and rc_distinct) else "NOT FIXED"
print(f"\n-- B4 post-fix agreement --")
print(f"  arms agree line for line: {agree_lines}")
print(f"  every induced tool failure exits with a code that is not 1: {rc_distinct} "
      f"(codes seen: {tool_rcs})")
print(f"  B4 = {b4}")

canary.unlink(missing_ok=True)

res = {
    "python": sys.version.split()[0],
    "C0": c0,
    "B1": b1,
    "B2": b2,
    "B3": b3,
    "B4": b4,
    "canary_cp1252": c_cp,
    "canary_utf8": c_utf,
    "verify_cp1252": v_cp,
    "verify_utf8": v_utf,
    "verify_unset": v_unset,
    "verify_artifact_removed": v_noart,
    "tool_failure_exit_codes": tool_rcs,
    "artifact_restored": art_restored,
    "predicate": PREDICATE,
}
OUT.mkdir(exist_ok=True)
(OUT / "k18_gate702.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
print("\nwrote out/k18_gate702.json")
print("=" * 78)
