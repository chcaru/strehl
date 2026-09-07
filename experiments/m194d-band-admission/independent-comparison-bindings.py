"""Rehashed new-boundary contradictions; original pixels and evidence untouched."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
READER_SHA = "9cc3fd5652a4e17d9036e6b69300b4e0bef50089893c3ba0fa40424e15b00fb1"


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def write(path, value):
    with Path(path).open("x", encoding="utf8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
    return dict(path=str(path.resolve()), sha256=sha(path))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--controller", type=Path, required=True)
    p.add_argument("--controller-sha", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    reader = HERE / "compare-experiment-v2.py"
    assert sha(reader) == READER_SHA and sha(args.controller) == args.controller_sha
    original_source = (HERE / "compare-experiment.py").read_text(encoding="utf8")
    first = 'S.sha256(command["log"])'
    assert original_source.count(first) == 1
    expected = original_source.replace(first, 'S.sha256(Path(command["log"]))')
    anchor = '    R.write(args.out, result)\n'
    addition = '    result["comparison_reader"] = {"path": str(Path(__file__).resolve()), "sha256": S.sha256(Path(__file__)), "predecessor_sha256": S.sha256(HERE / "compare-experiment.py"), "change": "Wrap the JSON command log string as Path for the unchanged hash API; no scoring change."}\n'
    assert expected.count(anchor) == 1
    expected = expected.replace(anchor, addition + anchor)
    assert reader.read_text(encoding="utf8") == expected, "reader change exceeds the declared repair"
    spec = importlib.util.spec_from_file_location("m194d_independent_bound_subject", reader)
    subject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    original = load(args.controller)
    validated = subject.validate_controller(args.controller.resolve(), args.controller_sha)
    cases = []

    def trial(name, value, validator, expected_pass=False):
        ref = write(out / (name + ".json"), value)
        try:
            validator(Path(ref["path"]), ref["sha256"])
        except Exception as exc:
            accepted = False
            error = f"{type(exc).__name__}: {exc}"
        else:
            accepted, error = True, None
        cases.append(dict(name=name, accepted=accepted, expected_pass=expected_pass,
                          pass_=accepted == expected_pass, error=error, **ref))
        print(("PASS " if accepted == expected_pass else "FAIL ") + name + (": " + error if error else ""), flush=True)

    trial("unchanged-complete-controller", original, subject.validate_controller, True)

    def remove_input(record):
        path = "experiments/m194d-band-admission/independent-consumer-tests.rs"
        for key in ("sources_before", "sources_after"):
            assert path in record[key]
            record[key].pop(path)

    def changed_reader(record):
        path = "experiments/m194d-band-admission/score-benchmark.py"
        for key in ("sources_before", "sources_after"):
            record[key][path] = "0" * 64

    outer = {
        "missing-candidate-mode": lambda r: r["modes"].pop("floor-pedestal-v1"),
        "duplicate-mode-index": lambda r: r["modes"].update({"floor-pedestal-v1": copy.deepcopy(r["modes"]["hard-floor"])}),
        "missing-new-included-source": remove_input,
        "coherently-changed-reader-source": changed_reader,
        "false-registered-source-delta": lambda r: r["source_delta"]["changed"].append("crates/strehl-cli/src/image_out.rs"),
        "failed-final-score-command": lambda r: r["commands"][-1].update(exit_code=1),
    }
    for name, change in outer.items():
        record = copy.deepcopy(original)
        change(record)
        trial(name, record, subject.validate_controller)

    index_ref = original["modes"]["floor-pedestal-v1"]["index"]
    original_index_path = Path(index_ref["path"])
    assert sha(original_index_path) == index_ref["sha256"]
    index = load(original_index_path)
    # Resolve existing metadata references, keeping original artifacts untouched.
    # This gives private index copies a real valid absolute-path companion.
    for case in index["cases"]:
        for name in ("manifest_path", "plan_path"):
            case[name] = str((original_index_path.parent / case[name]).resolve())
        for arm in case["arms"]:
            arm["receipt_path"] = str((original_index_path.parent / arm["receipt_path"]).resolve())
    for command in index["commands"]:
        command["log"] = str((original_index_path.parent / command["log"]).resolve())
        command["consumer_evidence"]["path"] = str((original_index_path.parent / command["consumer_evidence"]["path"]).resolve())
    for source in index["source_snapshots"]:
        source["path"] = str((original_index_path.parent / source["path"]).resolve())
    trial("unchanged-complete-absolute-index", index, subject.SB.score_run, True)

    def change_plan(record, name, mutate):
        case = record["cases"][0]
        value = load(case["plan_path"])
        mutate(value)
        ref = write(out / (name + "-plan.json"), value)
        case.update(plan_path=ref["path"], plan_sha256=ref["sha256"])

    def change_receipt(record, name, mutate):
        arm = record["cases"][0]["arms"][0]
        value = load(arm["receipt_path"])
        mutate(value)
        ref = write(out / (name + "-receipt.json"), value)
        arm.update(receipt_path=ref["path"], receipt_sha256=ref["sha256"])

    def wrong_child_environment(record):
        command = record["commands"][0]
        value = load(command["consumer_evidence"]["path"])
        value["environment"]["STREHL_M194D_ADMISSION"] = "hard-floor"
        command["consumer_evidence"] = write(out / "wrong-child-mode-evidence.json", value)

    nested = {
        "unknown-index-mode": lambda r: r.update(admission="floor-pedestal-v2"),
        "rehashed-legacy-plan-schema": lambda r: change_plan(r, "legacy-schema", lambda v: v.update(schema="m194b-consumer-plan-v1")),
        "rehashed-plan-mode": lambda r: change_plan(r, "wrong-mode", lambda v: v["config"].update(admission="HardFloor")),
        "rehashed-plan-formula": lambda r: change_plan(r, "wrong-formula", lambda v: v["config"].update(admission_formula="hard-floor-v1")),
        "rehashed-plan-environment": lambda r: change_plan(r, "wrong-environment", lambda v: v["environment"].update(STREHL_M194D_ADMISSION="hard-floor")),
        "rehashed-legacy-receipt-schema": lambda r: change_receipt(r, "legacy-schema", lambda v: v.update(schema="m194b-consumer-receipt-v1")),
        "rehashed-receipt-mode": lambda r: change_receipt(r, "wrong-mode", lambda v: v["plan"]["config"].update(admission="HardFloor")),
        "missing-paired-output": lambda r: r["cases"][0]["arms"].pop(),
        "duplicate-paired-output": lambda r: r["cases"][0]["arms"].__setitem__(1, copy.deepcopy(r["cases"][0]["arms"][0])),
        "rehashed-child-mode-environment": wrong_child_environment,
    }
    for name, change in nested.items():
        record = copy.deepcopy(index)
        change(record)
        trial(name, record, subject.SB.score_run)
    again = subject.validate_controller(args.controller.resolve(), args.controller_sha)
    result = dict(schema="m194d-independent-comparison-bindings-v1", pass_=all(c["pass_"] for c in cases),
                  command=sys.argv, script_sha256=sha(__file__), comparison_reader_sha256=READER_SHA,
                  predecessor_sha256=sha(HERE / "compare-experiment.py"), exact_reader_repair_verified=True,
                  controller_sha256=args.controller_sha, cases=cases,
                  unchanged_final_controller=again[0] == validated[0] and sha(args.controller) == args.controller_sha,
                  original_mode_index_unchanged=sha(original_index_path) == index_ref["sha256"],
                  subject_source_unchanged=sha(reader) == READER_SHA,
                  scope="private rehashed metadata contradictions; no output generation or original evidence edits; not authentication of wholly forged histories")
    result["pass_"] &= result["unchanged_final_controller"] and result["original_mode_index_unchanged"] and result["subject_source_unchanged"]
    write(out / "result.json", result)
    print(json.dumps(dict(pass_=result["pass_"], cases=len(cases), refusals=sum(not c["expected_pass"] for c in cases))), flush=True)
    assert result["pass_"]


if __name__ == "__main__":
    main()
