"""M92b S14 -- falsifying control for the S13 sensor guard.

S13 is green on the tree with its allowlist on. A green check that has never
been made to fail is not a check, and this project has been bitten by exactly
that (M92 phase 1's NC1; the orchestrator's own lint that passed its planted
duplicate). So: plant real defects into the real tree, in a directory the real
guard really walks, and require the real guard to go red -- then remove them
and require green again.

Five plants, each isolating one property the guard must have:

  P1  ISO 500 on 109MSDCF (ISO 160), reaching noise_var_dn
        -> RED. The literal M92 defect, in a file the allowlist has never
           heard of. If this passes, the guard is decorative.
  P2  the same defect hidden in a TUPLE UNPACKING
        -> RED. m57's s7 is written this way; a guard that only sees
           `Name = value` would ship green over the real thing.
  P3  ISO 160 on 109MSDCF, reaching noise_var_dn
        -> GREEN. The guard must not fire on a correct constant, or it will
           be switched off.
  P4  ISO 500 on 109MSDCF, reaching ONLY focus_fields
        -> GREEN. Rule 15 freezes the operator's constants; firing here would
           demand a change that breaks cross-milestone comparability.
  P5  no constant at all -- uses assert_sensor(stack)
        -> GREEN, and the assertion itself must pass. This is the half of the
           fix that removes the constant rather than policing it.

And two direct tests of the helper, because a helper that cannot refuse is
not a check either:

  H1  assert_sensor("109MSDCF", iso=500) must RAISE
  H2  sensor_for("119MSDCF") must RAISE -- ambiguous across capture roots

Run:
  python experiments/M92-null-averaging/src/s14_guard_control.py
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import s13_sensor_guard as S13  # noqa: E402

PLANTDIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "control-fixtures")

HDR = 'import os\nSTACK = os.path.join(r"D:\\personal\\macro", "109MSDCF")\n'

P1 = HDR + '''
ISO = 500
import m57lib as K
v = K.noise_var_dn(250.0, K.gain_dn_per_e(ISO), K.read_noise_e(ISO))
'''

P2 = HDR + '''
PAD, G, RN_E, ISO = 32, 1.14469, 1.47, 500
import m57lib as K
v = K.noise_var_dn(250.0, K.gain_dn_per_e(ISO), K.read_noise_e(ISO))
'''

P3 = HDR + '''
ISO = 160
import m57lib as K
v = K.noise_var_dn(250.0, K.gain_dn_per_e(ISO), K.read_noise_e(ISO))
'''

P4 = HDR + '''
G, RN_E = 1.14469, 1.47
import m41lib as L
fields = L.focus_fields(None, G, RN_E)
'''

P5 = HDR + '''
import s13_sensor_guard as SG
ISO_, G_, RN_ = SG.assert_sensor("109MSDCF")
'''

PLANTS = [("P1_plain", P1, "RED"), ("P2_tuple", P2, "RED"),
          ("P3_correct", P3, "GREEN"), ("P4_operator_only", P4, "GREEN"),
          ("P5_uses_helper", P5, "GREEN")]


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log("M92b S14 -- falsifying control for the sensor guard")
    log("  plants land in experiments/M92-null-averaging/control-fixtures/,")
    log("  inside the tree the real guard really walks.")
    log("=" * 78)

    base = len(S13.check_tree(use_allowlist=True))
    log(f"  baseline (no plants, allowlist ON): {base} finding(s) "
        f"-- expect 0")
    ok = (base == 0)
    if not ok:
        log("  BASELINE DIRTY -- the control cannot distinguish its own")
        log("  plants from pre-existing findings. Aborting.")

    rows = [dict(case="baseline", want="GREEN",
                 got="GREEN" if base == 0 else "RED", passed=base == 0)]

    if os.path.isdir(PLANTDIR):
        shutil.rmtree(PLANTDIR)

    try:
        for nm, body, want in PLANTS:
            os.makedirs(PLANTDIR, exist_ok=True)
            p = os.path.join(PLANTDIR, nm + ".py")
            open(p, "w", encoding="utf-8").write(body)
            found = [f for f in S13.check_tree(use_allowlist=True)
                     if nm in f["file"]]
            got = "RED" if found else "GREEN"
            good = (got == want)
            ok &= good
            rows.append(dict(case=nm, want=want, got=got, passed=good))
            log(f"  {'PASS' if good else 'FAIL'}  plant {nm:18s} "
                f"want={want:6s} got={got}")
            os.remove(p)
    finally:
        if os.path.isdir(PLANTDIR):
            shutil.rmtree(PLANTDIR)

    after = len(S13.check_tree(use_allowlist=True))
    good = (after == 0)
    ok &= good
    rows.append(dict(case="after_cleanup", want="GREEN",
                     got="GREEN" if good else "RED", passed=good))
    log(f"  {'PASS' if good else 'FAIL'}  after cleanup: {after} finding(s)"
        f" -- expect 0")

    log("")
    log("  helper refusals:")
    for nm, fn, want_raise in (
            ("H1_assert_wrong_iso",
             lambda: S13.assert_sensor("109MSDCF", iso=500), True),
            ("H2_ambiguous_name",
             lambda: S13.sensor_for("119MSDCF"), True),
            ("H3_assert_right_iso",
             lambda: S13.assert_sensor("109MSDCF", iso=160), False)):
        try:
            fn()
            raised, detail = False, "returned"
        except S13.SensorMismatch as e:
            raised, detail = True, str(e)[:74]
        good = (raised == want_raise)
        ok &= good
        rows.append(dict(case=nm, want="RAISE" if want_raise else "RETURN",
                         got="RAISE" if raised else "RETURN", passed=good))
        log(f"  {'PASS' if good else 'FAIL'}  {nm:22s} "
            f"want={'RAISE' if want_raise else 'RETURN':6s} "
            f"got={'RAISE' if raised else 'RETURN'}")
        if raised:
            log(f"         {detail}")

    log("")
    log(f"  CONTROL {'PASSED' if ok else 'FAILED'} "
        f"({sum(r['passed'] for r in rows)}/{len(rows)} cases)")

    with open(os.path.join(M92.OUT, "s14_guard_control.json"), "w",
              encoding="utf-8") as fh:
        json.dump(dict(cases=rows, passed=bool(ok)), fh, indent=1)
    with open(os.path.join(M92.OUT, "s14_guard_control.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log("wrote out/s14_guard_control.{json,log}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
