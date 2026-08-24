"""M76 Q2 -- close the constant-|z| escape without changing frozen b6_rollup."""
import ast
import os
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import spec_v1 as S

REGISTERED = "f1da8e5e9a95e2765ca0bd23eccc9b34a4d322a2"
ORIGINAL = "c37010c317a4526822ce502848bcd574b66d1816"


def function_source(source, name):
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)


def cell(stack, roi, z=9.0, passed=True):
    return dict(ref=1.0, test=0.9, d=0.1, status="Ok", status_test="Ok",
                z=z, z_pass=True, detected=passed, wrong_sign=False,
                passed=passed, stack=stack, roi=roi)


def build(varied=False):
    cells = []
    for si, stack in enumerate(S.HELD_OUT):
        for roi in range(S.TH["b6_min_rois"]):
            z = 4.0 + 0.7 * (roi * len(S.HELD_OUT) + si) if varied else 9.0
            cells.append(cell(stack, roi, z=z))
    return cells


def main():
    current_path = os.path.join(HERE, "spec_v1.py")
    with open(current_path, encoding="utf-8") as handle:
        current = handle.read()
    registered = subprocess.run(
        ["git", "show", f"{ORIGINAL}:experiments/M55-acceptance-spec/src/spec_v1.py"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    source_same = function_source(current, "b6_rollup") == \
        function_source(registered, "b6_rollup")

    module = types.ModuleType("registered_spec")
    exec(compile(registered, "<registered_spec>", "exec"), module.__dict__)
    bytecode_same = S.b6_rollup.__code__.co_code == module.b6_rollup.__code__.co_code

    constant = build(varied=False)
    varied = build(varied=True)
    planted = build(varied=True)
    target = next(c for c in planted if S.SUBJECT_OF[c["stack"]] == "coffee-bean")
    target["passed"] = target["detected"] = False

    old_constant = module.b6_rollup([dict(c) for c in constant])
    primitive_constant = S.b6_rollup([dict(c) for c in constant])
    strict_constant = S.b6_acceptance([dict(c) for c in constant])
    strict_varied = S.b6_acceptance([dict(c) for c in varied])
    strict_planted = S.b6_acceptance([dict(c) for c in planted])
    checks = [
        ("registered constant fixture passed", old_constant["verdict"] == "ACCEPT"),
        ("frozen primitive still passes it", primitive_constant["verdict"] == "ACCEPT"),
        ("normative wrapper blocks it", strict_constant["verdict"] == "CANNOT-ACCEPT"
         and not strict_constant["passed"]),
        ("distinct-z fixture remains passable", strict_varied["verdict"] == "ACCEPT"),
        ("ordinary B6 failure still rejects", strict_planted["verdict"] == "REJECT"),
        ("b6_rollup source unchanged", source_same),
        ("b6_rollup bytecode unchanged", bytecode_same),
    ]

    print("=" * 78)
    print("M76 E18 -- constant-|z| normative-wrapper property test")
    print(f"original frozen source: {ORIGINAL}")
    print(f"old constant={old_constant['verdict']}  "
          f"primitive constant={primitive_constant['verdict']}  "
          f"normative constant={strict_constant['verdict']}")
    print(f"normative varied={strict_varied['verdict']}  "
          f"normative planted={strict_planted['verdict']}")
    bad = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL':4s} {name}")
        bad += int(not ok)
    print(f"  -> {len(checks)-bad}/{len(checks)} assertions hold")
    if bad:
        raise SystemExit(f"{bad} assertion(s) failed")


if __name__ == "__main__":
    main()
