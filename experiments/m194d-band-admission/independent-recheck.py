"""Reread original retained controls after the disclosed libtest-prefix reader fix."""
import argparse
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = runpy.run_path(str(HERE / "independent-run.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--run-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.run.resolve()
    A["require"](A["sha"](source / "result.json") == args.run_sha256, "original run digest changed")
    original = A["load"](source / "result.json")
    A["require"](original["sources_unchanged"] and original["executables_unchanged"], "original run not source stable")
    A["require"](A["sha"](HERE / "independent-run-v1.py") == original["runner_sha256"], "original failed reader not preserved")
    A["bind_build"](original["core_build"], original["core_build_sha256"], "core")
    A["bind_build"](original["cli_build"], original["cli_build_sha256"], "cli")
    core = A["load"](source / "core.json")
    A["require"](core["pass"] and A["sha"](core["log"]) == core["log_sha256"], "core evidence failed or changed")
    results = []
    for gather in ["0", "1"]:
        child = A["load"](source / f"gather-{gather}.json")
        A["require"](child["exit_code"] == 0 and A["sha"](child["log"]) == child["log_sha256"], "actual Rust run failed or changed")
        text = Path(child["log"]).read_text(encoding="utf-8")
        A["require"]("1 passed; 0 failed" in text, "actual Rust test incomplete")
        tiffs = A["check_tiffs"](source / f"gather-{gather}-tiffs", text, gather)
        results.append(dict(gather=gather, source_log_sha256=child["log_sha256"], tiffs=tiffs, pass_=True))
    record = dict(schema="m194d-independent-recheck-v1", source_run=str(source), source_run_sha256=args.run_sha256,
                  original_reader_sha256=original["runner_sha256"], reader_sha256=A["sha"](HERE / "independent-run.py"),
                  recheck_sha256=A["sha"](__file__), correction="accept the exact libtest test-name preamble on its first stdout JSON line",
                  product_or_fixture_changes=False, new_native_execution=False, core_pass=True, checks=results, pass_=True)
    A["write"](args.output, record)
    print(dict(path=str(args.output), sha256=A["sha"](args.output), tiffs=sum(len(r["tiffs"]) for r in results), pass_=True))


if __name__ == "__main__":
    main()
