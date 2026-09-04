#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    source_lines = args.source.read_text(encoding="utf-8").splitlines()
    for row in report["mutations"]:
        if row["outcome"] != "KILLED":
            row["red_check"] = None
            continue
        matches = re.findall(
            r"adjudicate\.py.*line (\d+), in run_self_test", row["observed_stderr"]
        )
        if matches:
            line = int(matches[-1])
            statement = source_lines[line - 1].strip()
            row["red_check"] = "run_self_test_line_{}:{}".format(line, statement)
        elif row["observed_stdout"].strip():
            try:
                payload = json.loads(row["observed_stdout"])
                reason = str(payload.get("reason", "unexpected stdout"))
            except json.JSONDecodeError:
                reason = "nonbaseline_stdout"
            row["red_check"] = "main_self_test_refusal:{}".format(reason)
        else:
            row["red_check"] = "self_test_completion_banner_exact"
    report["named_red_checks"] = sum(
        row["red_check"] is not None for row in report["mutations"]
    )
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "mutated": report["mutated"],
                "named_red_checks": report["named_red_checks"],
                "survived": report["survived"],
                "inert_control_survived": report["inert_control_survived"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
