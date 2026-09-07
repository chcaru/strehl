"""Private commission of the final reader, never a scientific CFA authority."""
import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("m194e_final_reader_under_test", HERE / "independent-verify-cfa.py")
V = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = V
spec.loader.exec_module(V)
A, E, O = V.A, V.A.E, V.O


def sources():
    return {name: V.sha(HERE / name) for name in ("independent-verify-cfa.py", Path(__file__).name,
            "independent-cfa-oracle.py", "independent-emission-api-controls.py", "schema.py", "emit-cfa.py", "model.py", "render.py")}


def fixture(folder):
    bp, gp = A.make_fixture(folder / "fixture-only-no-optical-authority")
    base = bp.parent
    bundle = A.read(bp)
    records = []
    refs = base / "reference-arrays"
    refs.mkdir()
    for arm in ("primary", "refined"):
        for i, frame in enumerate(bundle["frames"]):
            value = np.load(base / frame["expected_scalar"]["path"], allow_pickle=False)
            # This deliberately crosses some exact rounding ties, within the
            # registered optical allowance. It is not an optical reference.
            value = value + .0002
            p = refs / f"{arm}-{i}.npy"
            np.save(p, value, allow_pickle=False)
            records.append(dict(arm=arm, index=i, array=A.ref(p, base)))
    A.write(base / "fixture-only-reference.json", dict(status="FIXTURE_ONLY_REFERENCE", source_unchanged=True, frames=records))
    for name in ("controls", "author_api"):
        A.write(base / f"fixture-only-{name}.json", dict(status="FIXTURE_ONLY_" + name.upper(), source_unchanged=True))
    comparison = dict(status="FIXTURE_ONLY_COMPARISON", source_unchanged=True,
                      inputs=dict(bundle=A.ref(bp, V.REPO)), frames=[],
                      independent_refinement=[dict(index=i, passed=True) for i in range(5)],
                      author_refinement=[dict(arm=a, index=i, passed=True) for a in V.ARMS[1:] for i in range(5)])
    refmap = {(r["arm"], r["index"]): r for r in records}
    for arm in V.ARMS:
        frames = bundle["frames"] if arm == "primary" else bundle["refinements"][arm]
        for i, f in enumerate(frames):
            comparison["frames"].append(dict(arm=arm, index=i, actual=f["expected_scalar"],
                                             reference=refmap[("refined", i)]["array"], statistics={"pass": True}))
    A.write(base / "fixture-only-comparison.json", comparison)
    gp = A.authority(base, bundle)
    emitted = folder / "private-emission"
    mp = E.emit_cfa_bundle(bp, gp, V.sha(gp), emitted)
    return bp, gp, mp


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = sources()
    (out / "sources").mkdir()
    for name in before:
        shutil.copyfile(HERE / name, out / "sources" / name)
    (out / "README.md").write_text("# Private final-reader controls\n\nAll numerical floats, references and gates are fixture-only. No scientific CFA commission is issued.\n", encoding="utf-8")
    bp, gp, mp = fixture(out / "valid-fixture")
    original = A.tree(out / "valid-fixture")
    checks = []

    def check(name, fn, refused=False):
        try:
            detail = fn()
            passed = not refused
            if refused:
                detail = "WRONG: accepted declared invalid input"
        except Exception as exc:
            passed = refused
            detail = dict(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        checks.append(dict(name=name, expected="refuse" if refused else "pass", passed=passed, detail=detail))
        A.write(out / "progress.json", dict(scope="FIXTURE_ONLY", checks=checks))
        print(("PASS " if passed else "FAIL ") + name, flush=True)

    def valid():
        r = V.verify(mp, V.sha(mp), gp, V.sha(gp), fixture_only=True)
        assert r["status"] == "PASS_FIXTURE_READER_ONLY" and r["sample_count"] == 15360
        differences = [f["reference_discrepancy"]["rounded_reference_code_differences"] for f in r["frames"]]
        assert all(d > 0 for d in differences), "near-tie actual difference occurrence"
        A.write(out / "valid-fixture-result.json", r)
        return dict(status=r["status"], sample_count=r["sample_count"], rounded_reference_code_differences=differences)

    check("valid-five-frame-and-live-rounding-tie-companion", valid)
    check("fixture-gate-cannot-pass-genuine-mode", lambda: V.verify(mp, V.sha(mp), gp, V.sha(gp)), True)
    check("wrong-external-manifest-digest", lambda: V.verify(mp, "0" * 64, gp, V.sha(gp), fixture_only=True), True)
    check("wrong-external-gate-digest", lambda: V.verify(mp, V.sha(mp), gp, "0" * 64, fixture_only=True), True)

    def mutated(name, mutate):
        root = out / ("mutant-" + name)
        shutil.copytree(mp.parent, root)
        manifest = A.read(root / "manifest.json")
        run = A.read(root / "emission-run.json")
        mutate(root, manifest, run)
        run["frames"] = deepcopy(manifest["frames"])
        A.write(root / "emission-run.json", run)
        manifest["producer"]["emission_receipt"] = A.ref(root / "emission-run.json", root)
        A.write(root / "manifest.json", manifest)
        return V.verify(root / "manifest.json", V.sha(root / "manifest.json"), gp, V.sha(gp), fixture_only=True)

    def code_change(root, m, r):
        f = m["frames"][0]
        p = root / f["cfa"]["path"]
        a = O.read_raw(p)
        a[31, 42] += 1
        p.write_bytes(a.tobytes())
        f["cfa"] = dict(**A.ref(p, root), dtype="<u2", shape=[48, 64])

    def electron_change(root, m, r):
        f = m["frames"][0]
        p = root / f["expected_cfa"]["path"]
        a = np.load(p, allow_pickle=False)
        a[31, 42] += 2 ** -20
        np.save(p, a, allow_pickle=False)
        f["expected_cfa"] = A.ref(p, root, True)

    cases = [
        ("nonterminal", lambda d, m, r: r.update(status="running")),
        ("refused-completion", lambda d, m, r: r.update(status="EMISSION_REFUSED")),
        ("gate-binding", lambda d, m, r: r.update(trusted_float_sha256="0" * 64)),
        ("source-after", lambda d, m, r: r.update(sources_after={})),
        ("missing-command", lambda d, m, r: r.update(command=[])),
        ("unknown-receipt", lambda d, m, r: r.update(extra=True)),
        ("unknown-manifest", lambda d, m, r: m.update(extra=True)),
        ("wrong-cfa-units", lambda d, m, r: m["frames"][0]["cfa"].update(dtype="<f8")),
        ("noise", lambda d, m, r: m["sensor"].update(noise=True)),
        ("bool-index", lambda d, m, r: m["frames"][0].update(index=False)),
        ("missing-expected", lambda d, m, r: m["frames"][0].pop("expected_cfa")),
        ("incomplete-five", lambda d, m, r: m["frames"].pop()),
        ("rehashed-cfa-value", code_change), ("rehashed-electron-value", electron_change),
        ("missing-cfa-file", lambda d, m, r: m["frames"][0]["cfa"].update(path="missing.cfa")),
    ]
    for name, fn in cases:
        check("rebound-" + name, lambda name=name, fn=fn: mutated(name, fn), True)

    def bad_gate():
        dest = out / "private-failed-gate.json"
        g = A.read(gp)
        g["status"] = "FAIL"
        A.write(dest, g)
        return V.verify(mp, V.sha(mp), dest, V.sha(dest), fixture_only=True)
    check("failed-gate-current-hash", bad_gate, True)
    # Registered uncertainty limits and a location-independent shifted truth.
    scalar = np.full((48, 64), 12000., dtype="<f8")
    _, codes, _ = O.convert(scalar)
    check("reference-discrepancy-valid", lambda: V.reference_diagnostic(scalar, scalar + .0002, codes))
    check("reference-discrepancy-live-maximum", lambda: V.reference_diagnostic(scalar, scalar + .005, codes), True)
    check("reference-discrepancy-live-rms", lambda: V.reference_diagnostic(scalar, scalar + .001, codes), True)
    check("unchanged-final-valid-companion", valid)
    unchanged = before == sources() and original == A.tree(out / "valid-fixture")
    result = dict(status="PASS_FIXTURE_READER_ONLY" if unchanged and all(c["passed"] for c in checks) else "FAIL_FIXTURE_READER_ONLY",
                  fixture_only=True, genuine_cfa_commission_issued=False, checks=checks,
                  passed=sum(c["passed"] for c in checks), total=len(checks), pass_=unchanged and all(c["passed"] for c in checks),
                  source_unchanged=unchanged, sources=before, sources_after=sources(),
                  command=sys.argv, interpreter_argv=sys.orig_argv, xoptions=sys._xoptions, python=sys.version, numpy=np.__version__)
    A.write(out / "result.json", result)
    print(json.dumps({k: result[k] for k in ("status", "passed", "total", "source_unchanged")}))
    return 0 if result["pass_"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
