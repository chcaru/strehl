"""M194f independent WB handoff controls; only the downstream child is stubbed.

Prospective falsifiers, before first execution: ignored/defaulted red-double;
ambient WB overriding explicit/default argv; mutated child test/cwd/settings;
omitted WB in command evidence; exposure1 silently changed to0 or child failure
credited as success; unknown WB spelling accepted by actual argparse. Valid
baseline/default/red-double plan and render companions prevent refusal-only
coverage. These fixtures grant no compiler, Rust, image or optical authority.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
DRIVER = HERE / "consumer-run.py"
TEST = "merge_cmd::known_scene_benchmark::joint_pupil_bridge::m194f_production_bridge"
PIN = "2dad7d6699492f17eb8610820763fad73f54a06b2d1f358c1c765ee4f553310b"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    out = parser.parse_args().output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = {p.name: sha(p) for p in (Path(__file__), DRIVER)}
    if before[DRIVER.name] != PIN:
        raise ValueError("reviewed driver source changed")
    for path in (Path(__file__), DRIVER):
        (out / path.name).write_bytes(path.read_bytes())
    spec = importlib.util.spec_from_file_location("m194f_wb_handoff_subject", DRIVER)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    copied = out / "private-copied.bin"
    original = out / "private-compiler.bin"
    copied.write_bytes(b"PRIVATE STUB ONLY: NEVER EXECUTED")
    original.write_bytes(copied.read_bytes())
    ref = lambda path: dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))
    bindings = {"private-source-witness.rs": "1" * 64}
    build = {"schema": "m194f-consumer-build-v1", "pass": True,
             "sources_before": bindings, "sources_after": bindings,
             "driver_sha256": PIN, "copy_matches_compiler_artifact": True,
             "rebuilt_cli": True, "exit_code": 0,
             "compiler_artifact": ref(original), "test_executable": ref(copied),
             "compiler_artifact_message": {"reason": "compiler-artifact",
                 "target": {"name": "strehl"}, "profile": {"test": True},
                 "executable": str(original)}}
    build_path = out / "private-build.json"
    write(build_path, build)
    rows = []
    cases = [
        ("plan-default", "plan", None, 0, "baseline", False),
        ("plan-baseline", "plan", "baseline", 0, "baseline", False),
        ("plan-red-double", "plan", "red-double", 0, "red-double", False),
        ("render-default", "render", None, 0, "baseline", False),
        ("render-baseline", "render", "baseline", 0, "baseline", False),
        ("render-red-double", "render", "red-double", 0, "red-double", False),
        ("plan-exposure-one-child-refusal", "plan", "baseline", 1, "baseline", False),
        ("render-exposure-one-child-refusal", "render", "red-double", 1, "red-double", False),
        ("plan-unknown-choice", "plan", "RedDouble", 0, None, True),
        ("render-unknown-choice", "render", "red_double", 0, None, True),
    ]
    for name, mode, selected, exposure, expected, parser_refusal in cases:
        folder = out / name
        folder.mkdir()
        plan, receipt = folder / "plan.json", folder / "receipt.json"
        target = plan if mode == "plan" else receipt
        log = folder / "child.log"
        argv = [str(DRIVER), mode, "--build-record", str(build_path),
                "--build-sha256", sha(build_path), "--manifest", str(folder / "manifest.json"),
                "--manifest-sha256", "2" * 64, "--cfa-commission", str(folder / "gate.json"),
                "--cfa-commission-sha256", "3" * 64, "--plan", str(plan),
                "--observer", "count", "--exposure", str(exposure), "--log", str(log)]
        if selected is not None:
            argv += ["--wb-mode", selected]
        if mode == "render":
            write(plan, {"private_input_plan": True})
            argv += ["--plan-sha256", sha(plan), "--output", str(folder / "never-written.tif"),
                     "--receipt", str(receipt)]
        calls = []

        def child(command, **kwargs):
            env = kwargs["env"]
            calls.append(dict(command=command, cwd=str(kwargs["cwd"]),
                              environment=driver.relevant_env(env)))
            assert command == [str(copied), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
            assert kwargs["cwd"] == driver.ROOT and kwargs["check"] is False
            assert env["STREHL_M194F_WB_MODE"] == expected
            assert env["STREHL_M194F_EXPOSURE"] == str(exposure)
            assert env["STREHL_M194F_MODE"] == mode
            assert env["STREHL_M194F_CONFIDENCE"] == "0"
            assert env["STREHL_M194F_OBSERVER"] == "count"
            assert env["KEEP_WB_CONTROL"] == "retained"
            assert "RUSTFLAGS" not in env and "STREHL_FIXTURE_FORGED" not in env
            assert env["STREHL_FULLRES_GATHER"] == "1" and env["RAYON_NUM_THREADS"] == "2"
            if exposure:
                return subprocess.CompletedProcess(command, 101, stdout=b"", stderr=b"PRIVATE stub refusal for forwarded exposure1\n")
            write(target, {"fixture_only": True, "stub": "no Rust or image execution",
                           "wb_mode_received": env["STREHL_M194F_WB_MODE"]})
            raw = b"test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 3 filtered out; finished in 0.01s\n"
            return subprocess.CompletedProcess(command, 0, stdout=raw, stderr=b"")

        capture = io.StringIO()
        hostile = {"STREHL_M194F_WB_MODE": "forged-ambient", "STREHL_M194F_EXPOSURE": "99",
                   "STREHL_FIXTURE_FORGED": "1", "RUSTFLAGS": "forged",
                   "KEEP_WB_CONTROL": "retained"}
        error = None
        with patch.object(driver, "sources", return_value=bindings), \
                patch.object(driver.subprocess, "run", side_effect=child), \
                patch.dict(os.environ, hostile, clear=True), patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            try:
                exit_code = driver.main()
            except SystemExit as exc:
                exit_code = exc.code
            except Exception as exc:
                exit_code, error = -1, repr(exc)
        command_path = log.with_suffix(".json")
        command_record = json.loads(command_path.read_text()) if command_path.exists() else None
        if parser_refusal:
            passed = exit_code == 2 and not calls and command_record is None and not target.exists()
        else:
            passed = (len(calls) == 1 and command_record is not None and error is None
                      and command_record["environment"] == calls[0]["environment"]
                      and command_record["command"] == calls[0]["command"]
                      and command_record["sources_unchanged"] is True
                      and exit_code == (1 if exposure else 0)
                      and command_record["passed"] is (not exposure)
                      and command_record["exit_code"] == (101 if exposure else 0)
                      and target.exists() is (not exposure))
        (folder / "driver-console.log").write_text(capture.getvalue(), encoding="utf-8")
        row = dict(name=name, passed=passed, driver_argv=argv, exit_code=exit_code,
                   error=error, child_calls=calls, command_record=command_record)
        rows.append(row)
        write(folder / "result.json", row)
        print(json.dumps(dict(name=name, passed=passed, child_calls=len(calls))), flush=True)
    after = {p.name: sha(p) for p in (Path(__file__), DRIVER)}
    passed = all(row["passed"] for row in rows) and before == after
    result = dict(schema="m194f-independent-wb-driver-controls-v1", passed=passed,
                  fixture_only=True, scope="actual Python argv/environment handoff with private recording child; no native execution",
                  check_count=len(rows), cases=rows, sources_before=before, sources_after=after,
                  interpreter_argv=sys.orig_argv, xoptions=sys._xoptions, executable=sys.executable,
                  cwd=str(Path.cwd()))
    write(out / "result.json", result)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
