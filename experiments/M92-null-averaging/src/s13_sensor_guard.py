"""M92b S13 -- the mechanical fix: assert per-stack sensor constants, and a
tree checker that goes red when a script asserts one that EXIF refutes.

WHY THIS SHAPE
--------------
M92 phase 1 found `ISO = 500` applied to an ISO-160 stack in three m57
scripts. That is not a typo, it is a *class*: a per-stack quantity written as
a module constant. Review cannot catch it, because the constant is correct for
some stack -- just not the one the script opens. The fix has to make the
mistake impossible to write, not easier to spot (M78b's precedent: a bounds
check proven by a falsifying control).

Two halves, and both are needed:

  (1) `sensor_for(stack)` -- the constant becomes unnecessary. A script asks
      the capture what its ISO is instead of declaring it. Costs one EXIF read,
      cached. A script that uses this CANNOT have the defect.

  (2) `check_tree()` -- the guard, for scripts that still declare. It re-runs
      S10's scan and fails on any MISMATCH whose S12 role is SENSOR, i.e. that
      actually reaches a sensor model over real pixels. OPERATOR-role
      constants (rule 15 freezes them) and PLANT-role constants (they define a
      synthetic, there is no truth to disagree with) are deliberately NOT
      failed -- a guard that fires on those would be turned off within a week.

The guard is calibrated so that it is RED on the tree as it stands today, on
exactly the three known-defective m57 assignments and nothing else. An
allowlist carries those as accepted history so the guard can be adopted green;
`--no-allowlist` shows the raw state.

Run:
  python experiments/M92-null-averaging/src/s13_sensor_guard.py
  python experiments/M92-null-averaging/src/s13_sensor_guard.py --no-allowlist
"""
import ast
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import m57lib as M57  # noqa: E402
import s10_const_scan as S10  # noqa: E402
import s12_use_sites as S12  # noqa: E402

# Instances that predate the guard and are recorded rather than fixed. Each
# entry must name the SYNTHESIS fact that documents it, so the allowlist
# cannot quietly absorb a new defect.
ALLOWLIST = {
    ("experiments/m57-shape-metric/src/s5_real_nulls.py", "ISO"):
        "fact 1242 -- M57 S5, ISO 500 on an ISO-160 stack, corrected by M92",
    ("experiments/m57-shape-metric/src/s6_debias.py", "ISO"):
        "fact 1242 -- M57 S6, same defect, source of the 0.34310 px bound",
    ("experiments/m57-shape-metric/src/s7_bias_or_variance.py", "ISO"):
        "fact 1242 -- M57 S7, same defect, hidden in a tuple unpacking",
}

_CACHE = None


def _truth():
    global _CACHE
    if _CACHE is None:
        _CACHE, _ = S10.load_truth()
    return _CACHE


class SensorMismatch(AssertionError):
    pass


def sensor_for(stack, root=None):
    """(iso, gain_dn_per_e, read_noise_e) for `stack`, from its own EXIF.

    Refuses a bare name that resolves to two different sensors. `119MSDCF`
    exists under both capture roots at ISO 50 and ISO 400 respectively; a
    bare name is not an identifier and silently picking one is the same
    class of defect this module exists to prevent.
    """
    by_name, collisions = S10.load_truth()
    if stack in collisions and root is None:
        raise SensorMismatch(
            f"{stack!r} is ambiguous: capture root has ISO "
            f"{collisions[stack]['capture']}, dark root has ISO "
            f"{collisions[stack]['dark']}. Pass root= to disambiguate.")
    if stack not in by_name:
        raise SensorMismatch(f"{stack!r} is not a known stack")
    iso = by_name[stack]["iso"]
    return iso, M57.gain_dn_per_e(iso), M57.read_noise_e(iso)


def assert_sensor(stack, iso=None, g=None, rn_e=None, tol=1e-4):
    """Registration-time assertion. Call once, at the top of a script.

    Raises unless every value supplied matches the stack's own EXIF. Returns
    the authoritative triple so the caller can use it directly.
    """
    t_iso, t_g, t_rn = sensor_for(stack)
    bad = []
    if iso is not None and float(iso) != float(t_iso):
        bad.append(f"ISO {iso} declared, EXIF says {t_iso}")
    if g is not None and abs(float(g) - t_g) > tol:
        bad.append(f"gain {g:.5f} declared, EXIF implies {t_g:.5f}")
    if rn_e is not None and abs(float(rn_e) - t_rn) > tol:
        bad.append(f"read noise {rn_e:g} declared, EXIF implies {t_rn:g}")
    if bad:
        raise SensorMismatch(f"{stack}: " + "; ".join(bad))
    return t_iso, t_g, t_rn


def check_tree(extra_dirs=(), use_allowlist=True):
    """Scan the experiment tree; return the list of SENSOR-role MISMATCHes."""
    by_name, _ = S10.load_truth()
    names = sorted(by_name, key=len, reverse=True)
    roots = [S10.EXP] + list(extra_dirs)
    findings = []
    for base in roots:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in ("out", "__pycache__", ".git")]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, S10.REPO).replace("\\", "/")
                if "/build-head/" in rel:
                    continue
                try:
                    src = open(p, encoding="utf-8", errors="replace").read()
                    tree = ast.parse(src)
                except (OSError, SyntaxError):
                    continue
                hits = S10.scan_file(p)
                if not hits:
                    continue
                lits = S10.path_literals(tree)
                used = [s for s in names if s in lits]
                used = [s for s in used
                        if not any(s != o and s in o for o in used)]
                for h in hits:
                    if h["name"] in S10.RIG:
                        continue
                    r = dict(file=rel, stacks=used, **h)
                    verdict, why = S10.classify(r, by_name)
                    if verdict != "MISMATCH":
                        continue
                    calls, arith = S12.use_sites(tree, h["name"])
                    roles = S12.role_of(calls, arith)
                    if "SENSOR" not in roles:
                        continue
                    key = (rel, h["name"])
                    if use_allowlist and key in ALLOWLIST:
                        continue
                    findings.append(dict(file=rel, line=h["line"],
                                         name=h["name"], value=h["value"],
                                         roles=roles, why=why))
    return findings


def main():
    use_allow = "--no-allowlist" not in sys.argv
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log("M92b S13 -- sensor-constant guard")
    log(f"  allowlist: {'ON' if use_allow else 'OFF'}"
        f" ({len(ALLOWLIST)} accepted historical instance(s))")
    log("=" * 78)

    findings = check_tree(use_allowlist=use_allow)
    for f in findings:
        log(f"  FAIL  {f['file']}:{f['line']}  {f['name']} = {f['value']:g}")
        log(f"        {f['why']}")
    if not findings:
        log("  PASS -- no SENSOR-role constant in the experiment tree is")
        log("  refuted by its own stack's EXIF.")

    with open(os.path.join(M92.OUT, "s13_sensor_guard.json"), "w",
              encoding="utf-8") as fh:
        json.dump(dict(allowlist=use_allow,
                       n_allowlisted=len(ALLOWLIST),
                       findings=findings), fh, indent=1)
    with open(os.path.join(M92.OUT,
                           f"s13_sensor_guard{'' if use_allow else '_raw'}"
                           ".log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
