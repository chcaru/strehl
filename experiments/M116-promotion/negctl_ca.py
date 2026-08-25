"""negctl_ca.py — commission verify_ca.py by breaking section 5f on purpose.

A verifier that has only ever printed GREEN is not evidence. It might be
checking nothing: a stale anchor, a threshold that cannot see the effect, or a
comparison against a field that already holds the answer all look exactly like
a clean pass. So each plant below introduces ONE specific defect and asserts
that verify_ca goes RED **and names the check that was supposed to catch it**.

Two design rules, both learned from failures recorded in this corpus:

  * Every mutation is anchored on a UNIQUE FULL string and this script hard-
    errors if the anchor does not land exactly once. A bare replace(x, y, 1)
    silently edits the first coincidental match somewhere else in the file and
    then reports a GREEN that means nothing.
  * An inert plant is included -- a change that must NOT trip the verifier.
    A detector that fires on everything is as useless as one that fires on
    nothing (discipline 797).

Nothing here touches the real report or the real artefacts. Everything runs
against a private copy under %TEMP%, and the originals are never written to,
so there is no path by which this script can damage the campaign. In
particular it never uses `git checkout --`, which reverts to HEAD and has
destroyed uncommitted work on this machine before.

Run:  python experiments/M116-promotion/negctl_ca.py
Exit: 0 = every plant caught and the inert plant ignored.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT_SRC = ROOT / "docs" / "research" / "M116-promotion.md"
CA_SRC = pathlib.Path(r"C:\dev\strehl-out\M116\ca")
VERIFY = HERE / "verify_ca.py"


def fatal(msg):
    print(f"negctl_ca: FATAL — {msg}")
    sys.exit(2)


# --------------------------------------------------------------------------
# mutations
# --------------------------------------------------------------------------

def edit_report(old, new):
    def apply(sandbox):
        p = sandbox / "M116-promotion.md"
        text = p.read_text(encoding="utf-8")
        n = text.count(old)
        if n != 1:
            fatal(f"report anchor occurs {n} times, need exactly 1:\n  {old!r}\n"
                  f"An unanchored mutation would edit the wrong site and the "
                  f"resulting GREEN or RED would both be meaningless.")
        p.write_text(text.replace(old, new), encoding="utf-8")
    return apply


def edit_json(fname, path, value):
    def apply(sandbox):
        p = sandbox / "ca" / fname
        blob = json.loads(p.read_text(encoding="utf-8"))
        node = blob
        for key in path[:-1]:
            if key not in node:
                fatal(f"{fname}: no such key {key!r} on the path {path}. "
                      f"The plant would land nowhere.")
            node = node[key]
        if path[-1] not in node:
            fatal(f"{fname}: no such leaf {path[-1]!r} on the path {path}")
        before = node[path[-1]]
        if before == value:
            fatal(f"{fname}: {path} is already {value!r}; this plant is inert "
                  f"by accident and would prove nothing.")
        node[path[-1]] = value
        p.write_text(json.dumps(blob), encoding="utf-8")
    return apply


def both(*fns):
    def apply(sandbox):
        for f in fns:
            f(sandbox)
    return apply


DISP = "scores-ca-disp.json"
CAL = "calibration.json"
CHROMA = "scores-ca.json"
FERN = "flower-bud-with-background-fern-cpl"

PLANTS = [
    # id, description, mutation, check id that must fire
    #
    # NOTE ON THE THREE `S[...]` EXPECTATIONS BELOW. D1, D2 and D11 were first
    # registered against C8, C7 and H1 -- the anchored proximity checks for
    # those claims. All three MISSED, and the reason is the finding that
    # produced check_exact: section 5f's headline numbers are restated in the
    # section 1 summary, so falsifying section 5f's own table leaves the
    # proximity check satisfied by the surviving duplicate. The expectation is
    # updated to name the detector that actually catches a single-site
    # falsification. This is a correction to my description of the instrument,
    # not a relaxation of the plant: the mutation is unchanged and it must
    # still turn the verifier RED.
    ("D1", "headline 90.1 % silently inflated in the report",
     edit_report("| **−0.7478 px** | **+0.0741 px** | **90.1 %** | 1.099× |",
                 "| **−0.7478 px** | **+0.0741 px** | **93.1 %** | 1.099× |"),
     "S[90.1 %]"),

    ("D2", "tweezers RD_on overstated in the report",
     edit_report("| **−0.6861 px** | **+0.0332 px** | **95.2 %** | 1.048× |",
                 "| **−0.6861 px** | **+0.0132 px** | **95.2 %** | 1.048× |"),
     "S[+0.0332 px]"),

    ("D3", "calibration drifts under the report's stated +0.440",
     edit_json(CAL, ["subjects", "tweezers-cpl", "translation_recovered_dx"],
               0.46),
     "B1[tweezers-cpl]"),

    ("D4", "a DEAD subject is quietly promoted to CALIBRATED",
     edit_json(CAL, ["subjects", "bee-3-cpl", "translation_pass"], True),
     "B5"),

    ("D5", "blue stops being an exact no-op",
     edit_json(DISP, ["subjects", "bee-3-cpl", "D_B"], 1e-9),
     "E5[bee-3-cpl]"),

    ("D6", "the correction makes CA worse but CD4 is still claimed",
     edit_json(DISP, ["subjects", "tweezers-cpl", "support_rd_on"], -0.9),
     "C9[tweezers-cpl]"),

    ("D7", "the null is broken: the two OFF renders differ",
     edit_json(CHROMA, ["subjects", "bee-3-cpl", "CB1_identical"], False),
     "F3[bee-3-cpl]"),

    ("D8", "the ON arm is dead — identical bytes to OFF",
     edit_json(CHROMA, ["subjects", "bee-3-cpl", "sha_on"],
               "478387EF2F9A15DB63FD39F7B2C032861FCA5B1D8BE003113C09E37554E57015"),
     "F4[bee-3-cpl]"),

    ("D9", "the void readings lose their VOID marking",
     edit_report("**not small effects — they are VOID**",
                 "**not small effects — they are modest**"),
     "G1"),

    ("D10", "artefacts came from a build other than the pinned one",
     edit_json(DISP, ["pinned_sha"], "0" * 40),
     "A0"),

    ("D11", "CD1's universal quantifier is dropped from 5g",
     edit_report(
         "Its text is `PASS = ... within +/-0.10 px of the planted\n+0.50 px, **on every subject scored**`.",
         "Its text sets a tolerance of `+/-0.10 px` around the planted\n`+0.50 px`."),
     "S[on every subject scored]"),

    ("D12", "fern's do-no-harm figure is overstated in the CD7 table",
     edit_report("| `flower-bud-…-fern-cpl` | −0.00184 | +0.00000 | +0.00067 | −0.00184 | **PASS** |",
                 "| `flower-bud-…-fern-cpl` | −0.00084 | +0.00000 | +0.00067 | −0.00084 | **PASS** |"),
     "E3[flower-bud-with-background-fern-cpl]"),

    ("D13", "Q no longer follows from the displacements it is derived from",
     edit_json(DISP, ["subjects", "flat-on-ruler-cpl", "support_Q"], 0.75),
     "C4[flat-on-ruler-cpl]"),
]

# The trap: a real edit that changes the report without touching any claim
# section 5f makes. verify_ca MUST stay GREEN. If it goes RED here it is
# reacting to the document rather than to the evidence.
INERT = ("N1", "a prose-only edit in section 5d, far from any 5f claim",
         edit_report("Lead with the failures, because there are two and they are mine.",
                     "Lead with the failures. There are two, and both are mine."))


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------

def build_sandbox(tmp):
    sandbox = tmp / "sandbox"
    (sandbox / "ca").mkdir(parents=True)
    shutil.copy2(REPORT_SRC, sandbox / "M116-promotion.md")
    for f in [DISP, CAL, CHROMA]:
        src = CA_SRC / f
        if not src.exists():
            fatal(f"artefact missing, cannot commission: {src}")
        shutil.copy2(src, sandbox / "ca" / f)
    return sandbox


def run_verify(sandbox):
    env = dict(os.environ)
    env["M116_REPORT"] = str(sandbox / "M116-promotion.md")
    env["M116_CA_OUT"] = str(sandbox / "ca")
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       env=env)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def main():
    if not VERIFY.exists():
        fatal(f"verify_ca.py not found at {VERIFY}")

    with tempfile.TemporaryDirectory(prefix="m116-negctl-") as td:
        tmp = pathlib.Path(td)

        # Baseline: the untouched copy must be GREEN, or every RED below is
        # ambiguous between the plant and a pre-existing fault.
        rc, out = run_verify(build_sandbox(tmp))
        if rc != 0:
            print(out)
            fatal("baseline sandbox is already RED. Commission is impossible "
                  "until the unmutated copy passes.")
        print("negctl_ca: baseline GREEN on an unmutated copy\n")

        caught, missed = [], []
        for pid, desc, mutate, want in PLANTS:
            shutil.rmtree(tmp / "sandbox")
            sandbox = build_sandbox(tmp)
            mutate(sandbox)
            rc, out = run_verify(sandbox)
            if rc == 0:
                missed.append((pid, desc, want, "verifier stayed GREEN"))
                print(f"  {pid:4} MISSED  {desc}")
            elif want not in out:
                # RED, but not for the registered reason. That is a partial
                # credit this script refuses to give: a verifier that goes red
                # for the wrong reason will go green for the wrong reason too.
                missed.append((pid, desc, want,
                               f"RED but {want} did not fire"))
                print(f"  {pid:4} WRONG   {desc}  (RED, but {want} silent)")
            else:
                caught.append(pid)
                print(f"  {pid:4} caught  {desc}  -> {want}")

        # The inert plant.
        pid, desc, mutate = INERT
        shutil.rmtree(tmp / "sandbox")
        sandbox = build_sandbox(tmp)
        mutate(sandbox)
        rc, out = run_verify(sandbox)
        inert_ok = (rc == 0)
        print(f"\n  {pid:4} {'ok      ' if inert_ok else 'FIRED   '}{desc}"
              f"  -> must stay GREEN")
        if not inert_ok:
            print(out)

    print()
    print(f"negctl_ca: {len(caught)}/{len(PLANTS)} planted defects caught; "
          f"inert plant {'ignored' if inert_ok else 'WRONGLY FIRED'}")
    if missed or not inert_ok:
        print("\nnegctl_ca: FAILED — verify_ca is not commissioned.")
        for pid, desc, want, why in missed:
            print(f"  {pid}: {desc}\n     expected {want}; {why}")
        return 1
    print("negctl_ca: PASS — verify_ca detects every registered defect and "
          "ignores a change that is not one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
