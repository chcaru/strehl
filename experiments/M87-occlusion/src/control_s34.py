"""M87 -- negative controls for verify_s34.

verify_s34 passed 90 checks on its first run.  verify_s33 failed 14 on its
first run, so a clean first pass is a reason for suspicion, not comfort: a
green verifier is a claim about the instrument and the claim needs testing.

Each arm mutates ONE operand or ONE prose figure, runs verify_s34, and requires
the expected colour.  Every mutation is anchored on a string whose occurrence
count is asserted BEFORE the edit, and a miss is a hard error rather than a
silent no-op -- an unanchored mutation that never lands returns GREEN and would
be read as the verifier failing to notice, which is the exact inversion that
makes a control worthless.

N11 is GREEN-expected: it restores everything and re-runs, proving the harness
is not simply always red.

Backups go to %TEMP% and are restored from there.  `git checkout --` is never
used: it reverts to HEAD and has destroyed uncommitted work on this machine.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = HERE.parents[0] / "data"
TMP = pathlib.Path(tempfile.gettempdir())
JSONS = ["100-gate-veildepth.json", "101-attrib.json", "102-robust.json",
         "exitcode-repeat.json"]


def backup():
    shutil.copy2(DOC, TMP / "m87-s34-doc.bak")
    for j in JSONS:
        shutil.copy2(DATA / j, TMP / f"m87-s34-{j}.bak")


def restore():
    shutil.copy2(TMP / "m87-s34-doc.bak", DOC)
    for j in JSONS:
        shutil.copy2(TMP / f"m87-s34-{j}.bak", DATA / j)


def run():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "verify_s34.py")],
                       capture_output=True, text=True, env=env,
                       encoding="utf-8", errors="replace")
    return ("GREEN" if p.returncode == 0 else "RED"), (p.stdout or "")


def mutate_doc(old, new, expect_count=None):
    raw = DOC.read_bytes().decode("utf-8")
    n = raw.count(old)
    if n == 0:
        raise SystemExit(f"MUTATION TARGET NOT FOUND: {old!r}")
    if expect_count is not None and n != expect_count:
        raise SystemExit(f"MUTATION TARGET COUNT {n} != {expect_count}: {old!r}")
    DOC.write_bytes(raw.replace(old, new).encode("utf-8"))
    return n


def mutate_doc_once(old, new):
    raw = DOC.read_bytes().decode("utf-8")
    n = raw.count(old)
    if n == 0:
        raise SystemExit(f"MUTATION TARGET NOT FOUND: {old!r}")
    DOC.write_bytes(raw.replace(old, new, 1).encode("utf-8"))
    return n


def mutate_json(name, path, value):
    f = DATA / name
    # utf-8-sig: exitcode-repeat.json is written by PowerShell 5.1's
    # Set-Content -Encoding utf8, which emits a BOM.
    d = json.loads(f.read_text(encoding="utf-8-sig"))
    node = d
    for k in path[:-1]:
        if k not in node:
            raise SystemExit(f"JSON KEY NOT FOUND: {path} (missing {k!r})")
        node = node[k]
    if path[-1] not in node:
        raise SystemExit(f"JSON KEY NOT FOUND: {path} (missing {path[-1]!r})")
    node[path[-1]] = value
    f.write_text(json.dumps(d, indent=1), encoding="utf-8")


def main():
    backup()
    results = []

    colour, _ = run()
    print(f"baseline: {colour}")
    if colour != "GREEN":
        restore()
        raise SystemExit("baseline is not GREEN; aborting")

    arms = []

    def arm(tag, why, expect, fn):
        arms.append((tag, why, expect, fn))

    arm("N1", "gate-0.00 near_dn perturbed by 500 DN", "RED",
        lambda: mutate_json("100-gate-veildepth.json",
                            ["arms", "0.00", "near_dn"], 37010.5))
    arm("N2", "gate-4.00 far_dn perturbed by 500 DN", "RED",
        lambda: mutate_json("100-gate-veildepth.json",
                            ["arms", "4.00", "far_dn"], 43433.9))
    arm("N3", "B19 branch relabelled to the confirming branch", "RED",
        lambda: mutate_json("100-gate-veildepth.json",
                            ["bars", "B19", "branch"], "B19-ORCH-CONFIRMED"))
    arm("N4", "drift form relabelled MULTIPLICATIVE", "RED",
        lambda: mutate_json("100-gate-veildepth.json",
                            ["controls", "C_DRIFT_FORM", "form"],
                            "MULTIPLICATIVE"))
    arm("N5", "C-MULT error raised above its 1e-12 bar", "RED",
        lambda: mutate_json("100-gate-veildepth.json",
                            ["controls", "C_MULT", "err"], 1e-6))
    arm("N6", "101 near-only contribution inflated past far-only", "RED",
        lambda: mutate_json("101-attrib.json",
                            ["bars", "B21", "near_only"], 5.0))
    arm("N7", "102 A2 pinned range inflated past its 3.00 pp bar", "RED",
        lambda: mutate_json("102-robust.json",
                            ["arms", "A2", "pinned_range_pp"], 4.0))
    arm("N8", "s25.7's 'gate-0 merge' row relabelled 'gate-4 merge'", "RED",
        lambda: mutate_doc("| gate-0 merge |", "| gate-4 merge |"))
    arm("N9", "C-POS calibration error pushed past its 0.5 pp bar", "RED",
        lambda: mutate_json("100-gate-veildepth.json",
                            ["controls", "C_POS", "err_pp"], 0.9))
    arm("N10", "ONE prose instance of the pinned range altered "
        "(instance-blindness probe)", "RED",
        lambda: mutate_doc_once("0.0572", "0.9572"))

    # P141 operands.  N12 is the one that matters: it makes the probe's own
    # positive control silent, which is the state in which "every safe shape
    # passed" means nothing.  A harness that stays GREEN through N12 would be
    # certifying the exit-code claim on an uncommissioned instrument.
    arm("N11", "a safe pipeline shape recorded as having lost the code", "RED",
        lambda: mutate_json("exitcode-repeat.json", ["safe_ok_total"], 179))
    arm("N12", "the exit-code probe's positive control silenced", "RED",
        lambda: mutate_json("exitcode-repeat.json", ["runs_with_a_trap"], 0))
    arm("N13", "corrupted value relabelled 0, contradicting the -1 finding",
        "RED", lambda: mutate_json("exitcode-repeat.json",
                                   ["corrupt_values"], [0]))
    arm("N14", "run-to-run variation denied", "RED",
        lambda: mutate_json("exitcode-repeat.json", ["nondeterministic"], False))

    for tag, why, expect, fn in arms:
        restore()
        n = fn()
        colour, out = run()
        if expect == "?":
            verdict = f"OBSERVED {colour}"
            agree = True
        else:
            agree = (colour == expect)
            verdict = "ok" if agree else f"DISAGREES (wanted {expect})"
        nfail = ""
        for line in out.splitlines():
            if line.startswith("verify_s34:"):
                nfail = line.strip()
        print(f"  {tag:4s} {colour:5s} {verdict:24s} {why}"
              + (f"  [{n} site(s)]" if isinstance(n, int) else ""))
        if nfail:
            print(f"        {nfail}")
        results.append((tag, colour, expect, agree))

    restore()
    colour, out = run()
    print(f"  N15  {colour:5s} {'ok' if colour == 'GREEN' else 'DISAGREES'}"
          f"        restored, no mutation (GREEN-expected arm)")
    results.append(("N15", colour, "GREEN", colour == "GREEN"))

    bad = [r for r in results if not r[3]]
    print(f"\ncontrol_s34: {len(results)} arms, {len(bad)} disagreements")
    for t, c, e, _ in bad:
        print(f"  - {t}: got {c}, wanted {e}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
