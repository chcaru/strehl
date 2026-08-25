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
         "exitcode-repeat.json",
         "exitcode-quota-child-host.json", "exitcode-quota-agent-shell.json",
         "exitcode-quota-pwsh7-child.json", "exitcode-quota-ps51-dotsource.json",
         "exitcode-race-ps51-child.json", "exitcode-race-pwsh7-child.json",
         "cachekey-probe.json", "rho-null.json",
         "exitcode-sentinel-ps7.json", "exitcode-sentinel-ps5.json",
         "110-crosscheck.json",
         "provenance-74.json", "launder-direction.json",
         "113-rankphase.json", "114-phaseperiod.json"]


SRCS = ["verify_s29.py", "control_s29.py", "verify_s32.py", "probe_cachekey.py"]


def backup():
    shutil.copy2(DOC, TMP / "m87-s34-doc.bak")
    for j in JSONS:
        shutil.copy2(DATA / j, TMP / f"m87-s34-{j}.bak")
    # P143's checks read these two instruments from disk, so the arms that
    # exercise them have to be able to mutate and restore source too.
    for s in SRCS:
        shutil.copy2(HERE / s, TMP / f"m87-s34-{s}.bak")


def restore():
    shutil.copy2(TMP / "m87-s34-doc.bak", DOC)
    for j in JSONS:
        shutil.copy2(TMP / f"m87-s34-{j}.bak", DATA / j)
    for s in SRCS:
        shutil.copy2(TMP / f"m87-s34-{s}.bak", HERE / s)


def mutate_src(name, old, new):
    """Mutate one instrument's source, asserting the anchor is unique first."""
    f = HERE / name
    t = f.read_text(encoding="utf-8")
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"SRC MUTATION TARGET {old!r} occurs {n}x in {name}, need 1")
    f.write_text(t.replace(old, new, 1), encoding="utf-8")


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
        if not _addressable(node, k):
            raise SystemExit(f"JSON KEY NOT FOUND: {path} (missing {k!r})")
        node = node[k]
    if not _addressable(node, path[-1]):
        raise SystemExit(f"JSON KEY NOT FOUND: {path} (missing {path[-1]!r})")
    node[path[-1]] = value
    f.write_text(json.dumps(d, indent=1), encoding="utf-8")


def _addressable(node, k):
    """True if k addresses an existing slot in node, list or dict.

    `k not in node` is wrong for a list: it tests membership of the VALUE k
    among the elements, not whether k is a valid index. N56 targets
    grid[6]["rho_median"] and tripped the hard error because 6 is not one of
    the stored correlations. The hard error was right to fire -- a mutation
    that silently addresses nothing would have produced a GREEN arm and
    certified a check that was never exercised.
    """
    if isinstance(node, list):
        return isinstance(k, int) and -len(node) <= k < len(node)
    return k in node


def mutate_arr(name, index, key, value):
    """Mutate one field of one element of a top-level JSON ARRAY.

    The quota and race probes write arrays of arm records, not the nested
    objects mutate_json walks.  Bounds and key existence are hard errors: a
    mutation that lands nowhere returns GREEN and reads as the verifier
    failing to notice.
    """
    f = DATA / name
    d = json.loads(f.read_text(encoding="utf-8-sig"))
    if not isinstance(d, list):
        raise SystemExit(f"NOT AN ARRAY: {name}")
    if not (0 <= index < len(d)):
        raise SystemExit(f"INDEX {index} OUT OF RANGE for {name} (len {len(d)})")
    if key not in d[index]:
        raise SystemExit(f"KEY NOT FOUND: {name}[{index}].{key}")
    if d[index][key] == value:
        raise SystemExit(f"NO-OP MUTATION: {name}[{index}].{key} is already {value!r}")
    d[index][key] = value
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

    def arm(tag, why, expect, fn, want=None):
        arms.append((tag, why, expect, fn, want))

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

    # ---- P142 operands: the engine 2x2 and the causal sleep ladder ----
    # Each of these carries a `want`, so the arm has to turn the specific
    # check it aims at red.  N1-N14 predate that facility.
    arm("N15", "one PowerShell 7.6.5 quota arm loses an observation, "
        "breaking the perfect 720/720", "RED",
        lambda: mutate_arr("exitcode-quota-pwsh7-child.json", 0, "lost", 39),
        want="7.6.5 strict quota")
    arm("N16", "the two 5.1 process styles made to disagree about which arm "
        "fails, which is the whole 'style contributes nothing' claim", "RED",
        lambda: mutate_arr("exitcode-quota-ps51-dotsource.json", 3,
                           "quota_agrees", False),
        want="both process styles fail the same arms")
    arm("N17", "a NON-quota arm (-First 51 over 50 objects) recorded as "
        "losing the code, which would break quota necessity", "RED",
        lambda: mutate_arr("exitcode-quota-child-host.json", 3, "lost", 1),
        want="non-quota arms lost")
    arm("N18", "7.6.5 relabelled as corrupting to -1, erasing the "
        "opposite-directions finding that makes the guard unsafe", "RED",
        lambda: mutate_arr("exitcode-quota-pwsh7-child.json", 0, "values", [-1]),
        want="pwsh7-child corrupts to")
    arm("N19", "5.1's 5-line arm set to 100% at sleep 0, which would make "
        "'sleep drives it to 100%' vacuously true", "RED",
        lambda: mutate_arr("exitcode-race-ps51-child.json", 0, "lost_pct", 100.0),
        want="is NOT already 100% at sleep 0")
    arm("N20", "7.6.5 made sleep-sensitive, which would mean the "
        "manipulation acts on both engines and localises nothing", "RED",
        lambda: mutate_arr("exitcode-race-pwsh7-child.json", 8, "lost_pct", 50.0),
        want="7.6.5 is 100% at every sleep")
    arm("N21", "a race negative control recorded as losing the code, so the "
        "sleep manipulation would not be selective", "RED",
        lambda: mutate_arr("exitcode-race-ps51-child.json", 2, "lost", 3),
        want="race negative controls lost")
    # N22 is deliberately a TWO-operand arm.  The claim under test is about a
    # SEQUENCE, and the measured ladder contains two independent inversions
    # (10 > 50 and 50 > 200), so no single-operand mutation can make it
    # monotone -- that is a property of the data, not a gap in the control.
    # It also shows why the monotonicity check has to exist at all: the swap
    # moves the 10-line and 200-line rates onto each other's values, so every
    # `"**76.25%**" appears in prose` presence check still passes.  Presence
    # alone would happily certify a ladder that had been reordered.
    arm("N22", "the 5.1 volume ladder reordered into a monotone one by "
        "swapping the 10-line and 200-line rates (two operands, see note)",
        "RED",
        lambda: (mutate_arr("exitcode-quota-ps51-dotsource.json", 6, "lost", 26),
                 mutate_arr("exitcode-quota-ps51-dotsource.json", 7, "lost", 34)),
        want="the volume ladder is NOT monotone")

    # ---- P143 operands: the s29 repair, read from disk ----
    arm("N23", "the s29 repair reverted to a single document-wide count of "
        "the full-coverage figure", "RED",
        lambda: mutate_src("verify_s29.py",
                           'chk("full coverage @ 29 table"',
                           'chk("full coverage",'),
        want="the bare document-wide full-coverage count is gone")
    arm("N24", "control_s29's collapse arm removed, so the repair would be "
        "certified by controls that never exercise it", "RED",
        lambda: mutate_src("control_s29.py", '"N11-COVER-COLLAPSE"',
                           '"N11-DISABLED"'),
        want="control_s29 carries the arm that collapses")
    arm("N25", "a second copy of one s29 anchor planted in the report, which "
        "is exactly how the original count was inflated", "RED",
        lambda: mutate_doc_once("Three limits, stated rather than buried.",
                                "It measured **100.00%** and printed PASS. "
                                "Three limits, stated rather than buried."),
        want="anchor is unique in the report")

    # ---- P144 operands: the cache-key exposure, from the probe's JSON ----
    arm("N26", "a measurement script is recorded as invoking the binary, "
        "which is the whole of ground (a)", "RED",
        lambda: mutate_json("cachekey-probe.json", ["scripts_invoking_binary"], 1),
        want="no measurement script invokes the binary")
    arm("N27", "the pinned gate-4 render no longer matches the digest this "
        "report recorded when it measured it", "RED",
        lambda: mutate_json("cachekey-probe.json", ["gate4_matches"], False),
        want="gate-4 on disk still matches the recorded digest")
    arm("N28", "two of the four gate arms collapse onto one hash, which is "
        "the cache serving one arm's bytes for another", "RED",
        lambda: mutate_json("cachekey-probe.json", ["pins_distinct"], 3),
        want="four arms, four hashes")
    arm("N29", "solve_config_key stops hashing the resampler -- the exact "
        "field fact 1446 names and M95 attributes high-band loss to", "RED",
        lambda: mutate_json("cachekey-probe.json",
                            ["solve_config_key_hashes", "resampler"], False),
        want="solve_config_key hashes resampler")
    arm("N30", "STREHL_WARPMAP stops bypassing discover-or-solve, which is "
        "the whole of ground (b)", "RED",
        lambda: mutate_json("cachekey-probe.json", ["warpmap_bypasses_solve"], False),
        want="STREHL_WARPMAP bypasses discover-or-solve")

    # ---- P145 operands: one owner for the harness split ----
    arm("N31", "verify_s32 loses the independent property check, leaving the "
        "audit and its verifier agreeing purely by shared constant", "RED",
        lambda: mutate_src("verify_s32.py",
                           'f"a harness-excluded script measures an image: {smuggled[:5]}"',
                           '"harness split ok"'),
        want="the independent property check exists in verify_s32")
    arm("N32", "the probe goes back to its own private copy of the split, "
        "which is the drift P145 is about", "RED",
        lambda: mutate_src("probe_cachekey.py", "HARNESS = fix_audit.HARNESS",
                           'HARNESS = ("verify_", "control_", "fix_")'),
        want="probe_cachekey.py imports the split rather than copying it")

    # ---- P146 operands: the enumerated rank null ----
    arm("N33", "the n=4 null is softened to a rarer value, which would make a "
        "four-point perfect reversal look like evidence", "RED",
        lambda: mutate_json("rho-null.json", ["4", "p_minus_one"], 0.0083),
        want="P(rho=-1) at n=4")
    arm("N34", "the enumeration is recorded as incomplete, so the exact null "
        "would silently become an estimate", "RED",
        lambda: mutate_json("rho-null.json", ["4", "permutations"], 20),
        want="all 24 permutations enumerated")
    arm("N35", "the disclosure is allowed to stand while the magnitude that "
        "actually carries the refutation is dropped from the section", "RED",
        lambda: mutate_doc("+2.3463 pp", "+2.3463 percentage points"),
        want="P146 itself restates the magnitude that refutes")

    # ---- P147 operands: the sentinel probe on both engines ----
    arm("N36", "7.6.5 is recorded as coercing to zero, which is exactly the "
        "artefact P147 corrects", "RED",
        lambda: mutate_arr("exitcode-sentinel-ps7.json", 0, "reads_zero", 10),
        want="7.6.5 does NOT coerce to zero")
    arm("N37", "5.1 is recorded as retaining the sentinel, collapsing the two "
        "engines onto one mechanism", "RED",
        lambda: mutate_arr("exitcode-sentinel-ps5.json", 0, "reads_sentinel", 9),
        want="5.1 does NOT retain the sentinel")
    arm("N38", "the prime is set equal to the true code, which is the design "
        "flaw that made P142's value claim undecidable", "RED",
        lambda: mutate_arr("exitcode-sentinel-ps7.json", 0, "sentinel", 1),
        want="the prime is a sentinel distinct from 0")
    arm("N39", "a safe shape is recorded as having retained the prime, which "
        "would break the independent reproduction of the safe-shape table",
        "RED",
        lambda: mutate_arr("exitcode-sentinel-ps5.json", 2, "reads_true", 4),
        want="5.1 selstr reads the live code 10/10")

    # ---- P148-P151 operands: the M121 cross-check ----
    arm("N41", "the merge's concentration ratio is dropped below its own "
        "registered bar, which must void the CONCENTRATED verdict", "RED",
        lambda: mutate_json("110-crosscheck.json", ["X1", "ratio"], 1.4),
        want="the merge clears the registered ratio bar")
    arm("N42", "the single-frame control is raised to the merge's ratio, which "
        "is the exact case where the statistic reads binning not election",
        "RED",
        lambda: mutate_json("110-crosscheck.json", ["X2", "single_ratio"], 2.20),
        want="C-SINGLE separates from the merge")
    arm("N43", "one frame is allowed above the merge, breaking the claim that "
        "EVERY single frame falls below it", "RED",
        lambda: mutate_json("110-crosscheck.json", ["X2", "per_frame_ratio_max"], 2.9),
        want="EVERY single frame falls below the merge")
    arm("N44", "the merge half-depth is pushed outside WINDOW_RADIUS, which is "
        "the geometric heart of the shared-mechanism claim", "RED",
        lambda: mutate_json("110-crosscheck.json", ["X3", "merge_half_depth_px"], 19),
        want="the merge's half-depth lies inside WINDOW_RADIUS")
    arm("N45", "edge removal is made better than window-radius removal, "
        "reversing the self-correction P149 exists to state", "RED",
        lambda: mutate_json("110-crosscheck.json", ["X4", "removal_d2"], 95.0),
        want="removal is genuinely worse at the edge")
    arm("N46", "the ARGUED status cell on the shared-root hypothesis is "
        "upgraded to MEASURED, which is the over-claim the label prevents",
        "RED",
        lambda: mutate_doc_once(
            "mechanism on either subject. | ARGUED |",
            "mechanism on either subject. | MEASURED |"),
        want="the shared-root hypothesis's STATUS CELL is ARGUED")

    arm("N47", "the headline's source closure is made to touch the laundered "
        "array, which is the exact thing P152 denies", "RED",
        lambda: mutate_json("provenance-74.json", ["R2", "overlap"],
                            ["45-locate.py"]),
        want="headline source closure does not touch ship-delta.npy")
    arm("N48", "the luma level count is dropped to an 8-bit-reachable value, "
        "destroying P152's positive test", "RED",
        lambda: mutate_json("provenance-74.json",
                            ["R1", "arrays", "bee3-leg-luma.npy",
                             "levels_slice"], 231),
        want="the level count actually exceeds what 8 bits can hold")
    arm("N49", "the amplitude factor is moved off the 16-to-8 quantisation "
        "ratio, breaking P153's mechanism claim", "RED",
        lambda: mutate_json("provenance-74.json", ["R3", "factor"], 180.0),
        want="the factor really is the 16-to-8 quantisation ratio")
    arm("N50", "Q2 is flipped to passing, i.e. my failed prediction is "
        "quietly recorded as having succeeded", "RED",
        lambda: mutate_json("launder-direction.json", ["Q2", "pass"], True),
        want="Q2 is recorded as FAILED, not quietly dropped")
    arm("N51", "the merge is made to move toward zero like frame 0, removing "
        "the opposite-directions finding P154 rests on", "RED",
        lambda: mutate_json("launder-direction.json", ["Q2", "v_laundered"],
                            -5.9),
        want="the merge veil really did deepen under laundering")
    arm("N52", "the changed-fraction ratio is inflated, turning P153's "
        "retraction back into the overstatement it retracts", "RED",
        lambda: mutate_json("provenance-74.json", ["R4", "ratio"], 3.4),
        want="the fraction ratio is small, which is what makes it a retraction")

    arm("N53", "the commuting result is broken, which would resurrect the "
        "rank framing P155 exists to retract", "RED",
        lambda: mutate_json("113-rankphase.json", ["T1", "mismatches"], 47),
        want="median commutes with the quantiser, 0 mismatches")
    arm("N54", "the sawtooth amplitude is pushed above half a quantum, "
        "breaking the bound P155 rests on", "RED",
        lambda: mutate_json("113-rankphase.json", ["T2", "max_abs_e"], 41.9),
        want="the amplitude really is bounded by half a quantum")
    arm("N55", "my failed decay prediction is quietly recorded as having "
        "passed", "RED",
        lambda: mutate_json("113-rankphase.json", ["T3", "pass"], True),
        want="the decay prediction is recorded as FAILED")
    arm("N56", "one half-integer separation is flipped positive, destroying "
        "the antiphase half of the periodicity claim", "RED",
        lambda: mutate_json("114-phaseperiod.json", ["grid", 6, "rho_median"],
                            0.31),
        want="all three half-integer separations are antiphase")
    arm("N57", "the phase-blind correlation is inflated, removing the "
        "result that speaks to a failed prediction elsewhere", "RED",
        lambda: mutate_json("114-phaseperiod.json", ["T7", "rho"], 0.77),
        want="the phase-blind bin really reads ~0")
    arm("N58", "the mean is made to behave differently from the median, "
        "reviving the discriminator P157 kills", "RED",
        lambda: mutate_json("114-phaseperiod.json", ["T8", "pass"], False),
        want="the mean shows the same periodicity, killing the discriminator")

    for tag, why, expect, fn, want in arms:
        restore()
        n = fn()
        colour, out = run()
        failed = [l.strip()[2:] for l in out.splitlines() if l.startswith("  - ")]
        if expect == "?":
            verdict = f"OBSERVED {colour}"
            agree = True
        else:
            agree = (colour == expect)
            verdict = "ok" if agree else f"DISAGREES (wanted {expect})"
            # A RED from an unrelated check is a FALSE PASS of the control: it
            # certifies a check that was never exercised.  Arms carrying a
            # `want` must turn the check they aim at red, not merely some check.
            if agree and want is not None:
                hit = [l for l in failed if want in l]
                if not hit:
                    agree = False
                    verdict = f"RED BUT NOT FROM {want!r}"
        nfail = ""
        for line in out.splitlines():
            if line.startswith("verify_s34:"):
                nfail = line.strip()
        print(f"  {tag:4s} {colour:5s} {verdict:34s} {why}"
              + (f"  [{n} site(s)]" if isinstance(n, int) else ""))
        if nfail:
            print(f"        {nfail}")
        results.append((tag, colour, expect, agree))

    restore()
    colour, out = run()
    green = "N%d" % (len(results) + 1)
    print(f"  {green:4s} {colour:5s} {'ok' if colour == 'GREEN' else 'DISAGREES'}"
          f"        restored, no mutation (GREEN-expected arm)")
    results.append((green, colour, "GREEN", colour == "GREEN"))

    bad = [r for r in results if not r[3]]
    print(f"\ncontrol_s34: {len(results)} arms, {len(bad)} disagreements")
    for t, c, e, _ in bad:
        print(f"  - {t}: got {c}, wanted {e}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
