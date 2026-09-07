"""M194f private driver controls: stub children, never compilation or rendering."""
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
DRIVER = HERE / "consumer-run.py"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source_before = {p.name: sha(p) for p in (Path(__file__), DRIVER)}
    for p in (Path(__file__), DRIVER):
        (out / p.name).write_bytes(p.read_bytes())
    spec = importlib.util.spec_from_file_location("m194f_actual_driver", DRIVER)
    d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(d)
    rows = []

    def record(name, passed, detail):
        rows.append(dict(name=name, pass_=bool(passed), detail=detail))
        print(json.dumps(rows[-1]), flush=True)
        write(out / "checks.json", rows)

    # Clean-environment behavior is independent of source/build fixture records.
    hostile = {"STREHL_ALIGN": "1", "strehl_m194f_mode": "forged", "RUSTFLAGS": "bad",
               "CARGO_ENCODED_RUSTFLAGS": "bad", "CARGO_TARGET_DIR": "bad",
               "RAYON_NUM_THREADS": "99", "KEEP_ME": "retained"}
    with patch.dict(os.environ, hostile, clear=True):
        cleaned = d.controlled_env()
    required = dict(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1",
                    STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
    record("environment-clears-hostile-and-keeps-unrelated", cleaned == {**required, "KEEP_ME": "retained"}, cleaned)

    # Explicit source-include forms in a private tree; no Git operation executed.
    repo = out / "private-source-tree"
    parent = repo / "crates/strehl-cli/src/parent.rs"
    source = repo / "crates/strehl-cli/src/joint-pupil-bridge.rs"
    external = repo / "experiments/private/independent.rs"
    nested = external.with_name("nested.rs")
    external.parent.mkdir(parents=True)
    parent.parent.mkdir(parents=True)
    parent.write_text('#[path = "joint-pupil-bridge.rs"]\nmod bridge;\n', encoding="utf-8")
    source.write_text('include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/private/independent.rs"));\n', encoding="utf-8")
    external.write_text('#[path = "nested.rs"]\nmod nested;\n', encoding="utf-8")
    nested.write_text("// private fixture leaf\n", encoding="utf-8")
    tracked = b"crates/strehl-cli/src/parent.rs\0"
    with patch.object(d, "ROOT", repo), patch.object(d, "SOURCE", source), patch.object(d.subprocess, "check_output", return_value=tracked):
        observed = d.sources()
        record("explicit-include-closure-valid", set(observed) == {
            "crates/strehl-cli/src/parent.rs", "crates/strehl-cli/src/joint-pupil-bridge.rs",
            "experiments/private/independent.rs", "experiments/private/nested.rs"}, observed)
        nested.rename(nested.with_suffix(".held"))
        try:
            d.sources()
            record("missing-included-source-refuses", False, "accepted")
        except (ValueError, OSError) as exc:
            record("missing-included-source-refuses", True, str(exc))
        finally:
            nested.with_suffix(".held").rename(nested)

    def invoke_case(name, *, mutation=None, raw=b"test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n",
                    create_target=True, returncode=0, external_wrong=False, source_after=None,
                    after_driver=False, after_exe=False):
        folder = out / name
        folder.mkdir()
        exe = folder / "stub-executable.bin"
        exe.write_bytes(b"PRIVATE-NOT-EXECUTABLE-M194F")
        compiler = folder / "stub-compiler-artifact.bin"
        compiler.write_bytes(exe.read_bytes())
        current_sources = {"crates/strehl-cli/src/joint-pupil-bridge.rs": "a" * 64,
                           "experiments/m194f-production-bridge/independent-reader-controls.rs": "b" * 64}
        ref = lambda p: dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)
        build = dict(schema="m194f-consumer-build-v1", pass_=True,
                     sources_before=copy.deepcopy(current_sources), sources_after=copy.deepcopy(current_sources),
                     driver_sha256=source_before[DRIVER.name], test_executable=ref(exe),
                     compiler_artifact=ref(compiler), copy_matches_compiler_artifact=True,
                     compiler_artifact_message=dict(reason="compiler-artifact", target=dict(name="strehl"),
                                                    profile=dict(test=True), executable=str(compiler)),
                     exit_code=0, rebuilt_cli=True,
                     command=["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--target-dir", d.TARGET,
                              "--no-run", "--message-format=json-render-diagnostics"])
        build["pass"] = build.pop("pass_")
        if mutation:
            mutation(build)
        record_path = folder / "build.json"
        write(record_path, build)
        invoke_args = SimpleNamespace(build_record=record_path, build_sha256="0" * 64 if external_wrong else sha(record_path),
            mode="plan", manifest=folder / "private-manifest.json", manifest_sha256="c" * 64,
            cfa_commission=folder / "private-gate.json", cfa_commission_sha256="d" * 64,
            plan=folder / "plan.json", observer="off", confidence=False, exposure=0, wb_mode="baseline", log=folder / "child.log")
        invoked = []
        def child(command, **kwargs):
            invoked.append(dict(command=command, environment=d.relevant_env(kwargs["env"])))
            if create_target:
                write(invoke_args.plan, {"private_stub": True})
            if after_exe:
                exe.write_bytes(b"changed-after-stub")
            return subprocess.CompletedProcess(command, returncode, stdout=raw, stderr=b"")
        original_sha = d.sha
        def driver_sha(path):
            if after_driver and Path(path).resolve() == DRIVER.resolve() and invoked:
                return "f" * 64
            return original_sha(path)
        def source_reader():
            return source_after if invoked and source_after is not None else current_sources
        stream = io.StringIO()
        try:
            with patch.object(d, "sources", side_effect=source_reader), patch.object(d.subprocess, "run", side_effect=child), patch.object(d, "sha", side_effect=driver_sha), contextlib.redirect_stdout(stream):
                exit_code = d.invoke(invoke_args)
            accepted = exit_code == 0
            detail = dict(exit_code=exit_code, child_calls=len(invoked), calls=invoked)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            accepted = False
            detail = dict(refusal=type(exc).__name__ + ": " + str(exc), child_calls=len(invoked))
        (folder / "driver-output.log").write_text(stream.getvalue(), encoding="utf-8")
        return accepted, detail

    accepted, detail = invoke_case("valid-stub-companion")
    record("valid-stub-companion", accepted, detail)
    mutations = [
        ("wrong-external-build-pin", dict(external_wrong=True)),
        ("wrong-current-driver-pin", dict(mutation=lambda x: x.update(driver_sha256="0" * 64))),
        ("source-before-after-disagree", dict(mutation=lambda x: x["sources_before"].update(extra="0" * 64))),
        ("coherent-omitted-included-source", dict(mutation=lambda x: [x[k].pop("experiments/m194f-production-bridge/independent-reader-controls.rs") for k in ("sources_before", "sources_after")])),
        ("wrong-executable-copy-hash", dict(mutation=lambda x: x["test_executable"].update(sha256="0" * 64))),
        ("wrong-executable-copy-length", dict(mutation=lambda x: x["test_executable"].update(bytes=1))),
        ("false-compiler-copy-binding", dict(mutation=lambda x: x["compiler_artifact"].update(sha256="0" * 64))),
        ("false-compiler-length", dict(mutation=lambda x: x["compiler_artifact"].update(bytes=1))),
        ("failed-copy-admission", dict(mutation=lambda x: x.update(copy_matches_compiler_artifact=False))),
        ("zero-tests-with-file", dict(raw=b"test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.01s\n")),
        ("eleven-tests-with-file", dict(raw=b"test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n")),
        ("test-pass-text-without-summary", dict(raw=b"private sample says 1 passed; 0 failed, but no test summary\n")),
        ("no-result-with-one-test", dict(create_target=False)),
        ("child-nonzero-with-file", dict(returncode=101)),
        ("source-changed-after-child", dict(source_after={"changed": "f" * 64})),
        ("driver-changed-after-child", dict(after_driver=True)),
        ("executable-changed-after-child", dict(after_exe=True)),
        ("executable-length-bool", dict(mutation=lambda x: x["test_executable"].update(bytes=True))),
        ("executable-length-float", dict(mutation=lambda x: x["test_executable"].update(bytes=float(x["test_executable"]["bytes"])))),
        ("executable-reference-unknown-key", dict(mutation=lambda x: x["test_executable"].update(candidate=True))),
        ("compiler-exit-false", dict(mutation=lambda x: x.update(exit_code=False))),
        ("compiler-not-rebuilt", dict(mutation=lambda x: x.update(rebuilt_cli=False))),
        ("compiler-message-wrong-target", dict(mutation=lambda x: x["compiler_artifact_message"]["target"].update(name="wrong"))),
        ("compiler-message-profile-not-test", dict(mutation=lambda x: x["compiler_artifact_message"]["profile"].update(test=False))),
        ("compiler-message-wrong-executable", dict(mutation=lambda x: x["compiler_artifact_message"].update(executable=x["test_executable"]["path"]))),
        ("one-passed-plus-ignored", dict(raw=b"test result: ok. 1 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 0.01s\n")),
        ("duplicate-success-summaries", dict(raw=b"test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n" * 2)),
    ]
    for name, options in mutations:
        accepted, detail = invoke_case(name, **options)
        record(name, not accepted, detail)
    accepted, detail = invoke_case("valid-stub-final-companion")
    record("valid-stub-final-companion", accepted, detail)
    source_after = {p.name: sha(p) for p in (Path(__file__), DRIVER)}
    result = dict(schema="m194f-independent-driver-controls-v1", scope="private stub API; no real compile/render/authority",
                  pass_=all(r["pass_"] for r in rows) and source_before == source_after,
                  check_count=len(rows), checks=rows, source_before=source_before, source_after=source_after,
                  command=sys.argv, interpreter_argv=sys.orig_argv, xoptions=sys._xoptions, executable=sys.executable)
    write(out / "result.json", result)
    print(json.dumps(dict(pass_=result["pass_"], check_count=len(rows), result_sha256=sha(out / "result.json"))))
    return 0 if result["pass_"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
