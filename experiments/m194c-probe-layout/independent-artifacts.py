"""Audit actual layout TIFFs independently of other test-group failures."""
import argparse
import json
from pathlib import Path
import re
import runpy

HERE = Path(__file__).resolve().parent
API = runpy.run_path(str(HERE / "independent-run.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for gather in ["0", "1"]:
        record = API["load"](args.run / f"gather-{gather}.json")
        if API["sha"](record["log"]) != record["log_sha256"]:
            raise ValueError("saved source log changed")
        directories = {Path(value).resolve() for value in
                       re.findall(r" dir=(.+)", Path(record["log"]).read_text(encoding="utf-8"))}
        if len(directories) != 1:
            raise ValueError("actual output directory not unique")
        tiffs = API["check_tiffs"](directories.pop())
        records.append(dict(gather=gather, source_exit_code=record["exit_code"],
                            source_log_sha256=record["log_sha256"],
                            tiffs=tiffs, artifact_checks_pass=True))
    output = dict(schema="m194c-independent-artifact-audit-v1", source_run=str(args.run.resolve()),
                  source_run_sha256=API["sha"](args.run / "result.json"),
                  runner_sha256=API["sha"](__file__), reader_sha256=API["sha"](HERE / "independent-run.py"),
                  scope="actual layout/power/observer TIFFs only; other test-group failures remain",
                  checks=records, artifact_checks_pass=True)
    API["write"](args.output, output)
    print(json.dumps(dict(path=str(args.output), sha256=API["sha"](args.output),
                          actual_tiffs=sum(len(r["tiffs"]) for r in records), pass_=True)))


if __name__ == "__main__":
    main()
