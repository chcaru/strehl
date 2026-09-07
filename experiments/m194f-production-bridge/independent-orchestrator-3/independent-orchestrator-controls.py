"""Private M194f orchestration API controls; all render/build children are stubs."""
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CONTROLLER = HERE / "run-commission.py"
SUMMARY1 = b"test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n"
SUMMARY7 = b"test result: ok. 7 passed; 0 failed; 2 ignored; 0 measured; 139 filtered out; finished in 0.01s\n"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def ref(path):
    return dict(path=str(path), sha256=sha(path), bytes=Path(path).stat().st_size)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    names = [Path(__file__), CONTROLLER, HERE / "consumer-run.py"]
    before = {p.name: sha(p) for p in names}
    for path in names:
        (out / path.name).write_bytes(path.read_bytes())
    spec = importlib.util.spec_from_file_location("m194f_actual_orchestrator", CONTROLLER)
    r = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r)
    rows = []
    source_map = {"private-source.rs": "a" * 64}
    fake_build = dict(sources_after=source_map, test_executable=dict(path=str(out / "never-executed.bin"), sha256="b" * 64, bytes=1))
    (out / "never-executed.bin").write_bytes(b"x")
    fake_build["test_executable"]["sha256"] = sha(out / "never-executed.bin")

    def record(name, passed, detail):
        rows.append(dict(name=name, passed=bool(passed), detail=detail))
        print(json.dumps(rows[-1]), flush=True)
        write(out / "checks.json", rows)

    def private_value(folder, status="complete", schema="m194f-private-controls-v1"):
        bindings = {}
        for index, name in enumerate(("constant", "affine", "mutation", "rank", "sentinel")):
            path = folder / f"{name}.private-bin"
            path.write_bytes(bytes([index, 19, 71]))
            bindings[name] = ref(path)
        return dict(schema=schema, status=status, fixture_only=True,
                    rgb={name: bindings[name] for name in ("constant", "affine", "mutation")},
                    gray={name: bindings[name] for name in ("rank", "sentinel")})

    def private_case(name, *, status="complete", malformed=False, schema="m194f-private-controls-v1", make_result=True, raw=SUMMARY1, exit_code=0):
        folder = out / name
        folder.mkdir()
        output = folder / "private"
        ns = SimpleNamespace(output=output, build_record=folder / "stub-build.json", build_sha256="c" * 64)
        def child(command, **kwargs):
            if make_result:
                output.mkdir()
                target = output / "private-controls.json"
                if malformed:
                    target.write_text("{broken", encoding="utf-8")
                else:
                    write(target, private_value(output, status=status, schema=schema))
            return subprocess.CompletedProcess(command, exit_code, stdout=raw, stderr=b"")
        try:
            stream = io.StringIO()
            with patch.object(r, "admitted_build", return_value=fake_build), patch.object(r.D, "sources", return_value=source_map), patch.object(r.subprocess, "run", side_effect=child), contextlib.redirect_stdout(stream):
                code = r.private(ns)
            accepted = code == 0
            detail = dict(exit_code=code)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            accepted = False
            detail = dict(refusal=type(exc).__name__ + ": " + str(exc))
        (folder / "controller.log").write_text(stream.getvalue(), encoding="utf-8")
        return accepted, detail

    accepted, detail = private_case("private-valid-stub")
    record("private-valid-stub", accepted, detail)
    for name, options in [
        ("private-failed-result", dict(status="failed")),
        ("private-wrong-schema", dict(schema="unrelated")),
        ("private-malformed-result", dict(malformed=True)),
        ("private-missing-result", dict(make_result=False)),
        ("private-zero-test", dict(raw=SUMMARY1.replace(b"1 passed", b"0 passed"))),
        ("private-nonzero-child", dict(exit_code=101)),
    ]:
        accepted, detail = private_case(name, **options)
        record(name, not accepted, detail)

    def renders_case(name, *, mutate=None, failed_invocation=None, source_changed=False, pin_wrong=False):
        folder = out / name
        folder.mkdir()
        private_result = folder / "private-controls.json"
        write(private_result, private_value(folder))
        plog, clog = folder / "private.log", folder / "controls.log"
        plog.write_bytes(SUMMARY1)
        clog.write_bytes(SUMMARY7)
        children = []
        for i in range(6):
            child = folder / f"input-{i}.json"
            write(child, dict(schema="m194f-independent-input-controls-v1", pass_=True, check_count=1,
                             checks=[dict(name="private-stub", passed=True)]))
            value = json.loads(child.read_bytes())
            value["pass"] = value.pop("pass_")
            value["checks"][0]["pass"] = value["checks"][0].pop("passed")
            write(child, value)
            children.append(ref(child))
        common = dict(passed=True, exit_code=0, build_sha256="c" * 64,
                      sources_before=source_map, sources_after=source_map,
                      test_executable=fake_build["test_executable"], environment=r.D.relevant_env(r.D.controlled_env()))
        private = dict(**common, schema="m194f-private-command-v1", result=str(private_result), result_sha256=sha(private_result),
                       command=[fake_build["test_executable"]["path"], "--exact", r.PRIVATE_TEST, "--ignored", "--test-threads=1", "--nocapture"],
                       log=str(plog), log_sha256=sha(plog), driver_before=r.drivers(), driver_after=r.drivers())
        controls = dict(**common, schema="m194f-controls-command-v1", independent_results=children,
                        command=[fake_build["test_executable"]["path"], "merge_cmd::known_scene_benchmark::joint_pupil_bridge::", "--test-threads=1", "--nocapture"],
                        log=str(clog), log_sha256=sha(clog), unchanged=True)
        if mutate:
            mutate(private, controls, folder)
        ppath, cpath = folder / "private-command.json", folder / "controls-command.json"
        write(ppath, private)
        write(cpath, controls)
        ns = SimpleNamespace(output=folder / "renders", build_record=folder / "stub-build.json", build_sha256="c" * 64,
            private_command_record=ppath, private_command_sha256="0" * 64 if pin_wrong else sha(ppath),
            controls_command_record=cpath, controls_command_sha256=sha(cpath))
        ns.build_record.write_bytes(b"private stub build reference")
        calls = []
        def child(invocation):
            calls.append(dict(mode=invocation.mode, observer=invocation.observer, confidence=invocation.confidence, exposure=invocation.exposure))
            if failed_invocation == len(calls):
                return 1
            target = invocation.plan if invocation.mode == "plan" else invocation.receipt
            write(target, dict(private_stub=True))
            write(target.with_suffix(".command.json"), dict(private_stub=True))
            return 0
        def sources():
            return {"changed": "f" * 64} if source_changed and len(calls) == 10 else source_map
        stream = io.StringIO()
        try:
            with patch.object(r, "admitted_build", return_value=fake_build), patch.object(r.D, "sources", side_effect=sources), patch.object(r.D, "checked_executable", return_value=Path(fake_build["test_executable"]["path"])), patch.object(r.D, "invoke", side_effect=child), contextlib.redirect_stdout(stream):
                code = r.renders(ns)
            accepted = code == 0
            detail = dict(exit_code=code, calls=calls)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            accepted = False
            detail = dict(refusal=type(exc).__name__ + ": " + str(exc), calls=calls)
        detail["completed_index_exists"] = (ns.output / "run-index.json").exists()
        (folder / "controller.log").write_text(stream.getvalue(), encoding="utf-8")
        return accepted, detail

    accepted, detail = renders_case("renders-valid-stub")
    expected = [dict(mode=mode, observer=o, confidence=c, exposure=e) for _, o, c, e in r.RUNS for mode in ("plan", "render")]
    record("renders-valid-fixed-five-schedule", accepted and detail["calls"] == expected and detail["completed_index_exists"], detail)
    def fail_child(p, c, folder):
        child = Path(c["independent_results"][3]["path"])
        value = json.loads(child.read_bytes())
        value["pass"] = False
        value["checks"][0]["pass"] = False
        write(child, value)
        c["independent_results"][3] = ref(child)
    def mutate_child(c, edit):
        child = Path(c["independent_results"][4]["path"])
        value = json.loads(child.read_bytes())
        edit(value)
        write(child, value)
        c["independent_results"][4] = ref(child)
    def mutate_private(p, edit):
        path = Path(p["result"])
        value = json.loads(path.read_bytes())
        edit(value)
        write(path, value)
        p["result_sha256"] = sha(path)
    for name, options in [
        ("wrong-dependency-external-pin", dict(pin_wrong=True)),
        ("failed-controls-record", dict(mutate=lambda p, c, f: c.update(passed=False))),
        ("omitted-six-independent-results", dict(mutate=lambda p, c, f: c.pop("independent_results"))),
        ("rehashed-failed-independent-child", dict(mutate=fail_child)),
        ("controls-zero-tests-rebound-log", dict(mutate=lambda p, c, f: ((f / "controls.log").write_bytes(SUMMARY7.replace(b"7 passed", b"0 passed")), c.update(log_sha256=sha(f / "controls.log"))))),
        ("controls-wrong-filter", dict(mutate=lambda p, c, f: c["command"].__setitem__(1, "unknown_test"))),
        ("controls-wrong-copied-executable", dict(mutate=lambda p, c, f: c.update(test_executable={**c["test_executable"], "sha256": "0" * 64}))),
        ("private-wrong-test-command", dict(mutate=lambda p, c, f: p["command"].__setitem__(2, "unknown_test"))),
        ("first-plan-refusal", dict(failed_invocation=1)),
        ("third-render-refusal", dict(failed_invocation=6)),
        ("last-render-refusal", dict(failed_invocation=10)),
        ("source-changed-after-population", dict(source_changed=True)),
        ("duplicate-independent-child-path", dict(mutate=lambda p, c, f: c["independent_results"].__setitem__(5, c["independent_results"][0]))),
        ("empty-independent-checks-rebound", dict(mutate=lambda p, c, f: mutate_child(c, lambda v: v.update(check_count=0, checks=[])))),
        ("false-check-with-pass-status-rebound", dict(mutate=lambda p, c, f: mutate_child(c, lambda v: v["checks"][0].update({"pass": False})))),
        ("missing-private-gray-rebound", dict(mutate=lambda p, c, f: mutate_private(p, lambda v: v["gray"].pop("sentinel")))),
        ("duplicate-private-output-paths-rebound", dict(mutate=lambda p, c, f: mutate_private(p, lambda v: v["rgb"].update(affine=v["rgb"]["constant"])))),
    ]:
        accepted, detail = renders_case(name, **options)
        record(name, not accepted and not detail["completed_index_exists"], detail)
    after = {p.name: sha(p) for p in names}
    result = dict(schema="m194f-independent-orchestrator-controls-v1", passed=all(x["passed"] for x in rows) and before == after,
                  check_count=len(rows), checks=rows, source_before=before, source_after=after,
                  interpreter_argv=sys.orig_argv, xoptions=sys._xoptions, command=sys.argv,
                  scope="private stub orchestration only; no real build, tests, pixels or optical authority")
    write(out / "result.json", result)
    print(json.dumps(dict(passed=result["passed"], check_count=len(rows), result_sha256=sha(out / "result.json"))))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
