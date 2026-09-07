"""Validate the fixed two-mode experiment and compare actual delivered TIFFs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import importlib.util


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


R = module("m194d_run", HERE / "run-experiment.py")
SB = module("m194d_score", HERE / "score-benchmark.py")
S, SP = SB.S, SB.SP
C = module("m194d_consumer_driver", HERE / "consumer-run.py")
LEGACY = module("m194d_legacy_comparison", ROOT / "experiments/m194c-probe-layout/compare-candidate.py")


def bound(ref):
    return SB.read_bound(Path(ref["path"]), ref["sha256"])


def validate_controller(path, digest):
    record = SB.read_bound(path, digest)
    SB.require(record["schema"] == "m194d-experiment-controller-v1" and record["status"] == "complete",
               "experiment incomplete or wrong schema")
    SB.require(record["baseline_commit"] == R.BASELINE_COMMIT
               and record["preregistration_commit"] == R.PREREG_COMMIT
               and record["baseline_index"] == dict(path=str(R.BASELINE), sha256=R.BASELINE_SHA),
               "wrong M194c baseline")
    prior = bound(record["baseline_index"])
    old_build = bound(prior["build_record"])
    build_ref = record["build_record"]
    build = bound(build_ref)
    SB.require(record["source_delta"] == R.source_delta(build["sources_after"], old_build["sources_after"]),
               "false product source delta")
    SB.require(record["frozen_m194b"] == R.frozen_artifacts(), "wrong fixed historical artifact set")
    expected_sources = C.sources() | R.fixed_sources() | R.frozen_artifacts()
    R.validate_external_includes(C.sources())
    SB.require(record["sources_before"] == record["sources_after"] == expected_sources,
               "missing, extra or changed experiment source binding")
    snapshot_root = Path(record["source_snapshots_root"])
    for name, expected in expected_sources.items():
        SB.require(S.sha256(snapshot_root / name) == expected, "experiment source snapshot differs")
    SB.require(set(record["modes"]) == set(R.MODES), "incomplete or unexpected mode matrix")
    expected_commands = [[sys.executable, "-X", "utf8", str(HERE / "consumer-run.py"),
                          "build", "--build-record", build_ref["path"]]]
    scores, indices = {}, {}
    for mode in R.MODES:
        refs = record["modes"][mode]
        index = bound(refs["index"])
        SB.require(index["admission"] == mode and index["build_record"] == build_ref,
                   "mode or shared binary changed")
        for name in ("producer_result", "producer_commission"):
            SB.require(index[name] == prior[name], "different original producer inputs")
        argv = [sys.executable, "-X", "utf8", str(HERE / "run-matrix.py"),
                "--admission", mode, "--build-record", build_ref["path"],
                "--build-record-sha", build_ref["sha256"]]
        for flag, key in (("producer-result", "producer_result"), ("producer-commission", "producer_commission")):
            argv += ["--" + flag, prior[key]["path"], "--" + flag + "-sha", prior[key]["sha256"]]
        argv += ["--out", str(Path(refs["index"]["path"]).parent)]
        expected_commands.append(argv)
        expected_commands.append([sys.executable, "-X", "utf8", str(HERE / "score-benchmark.py"),
                                  "--index", refs["index"]["path"],
                                  "--expected-index-sha", refs["index"]["sha256"],
                                  "--out", refs["score"]["path"]])
        scored = bound(refs["score"])
        replay = SB.score_run(Path(refs["index"]["path"]), refs["index"]["sha256"])
        SB.require(scored == json.loads(json.dumps(replay, allow_nan=False)),
                   "recorded score differs from actual bound TIFFs")
        scores[mode], indices[mode] = scored, index
    commands = record["commands"]
    SB.require([c["command"] for c in commands] == expected_commands
               and all(c["exit_code"] == 0 for c in commands), "incorrect/incomplete outer execution chain")
    for command in commands:
        SB.require(S.sha256(Path(command["log"])) == command["log_sha256"], "outer command log changed")
    return record, scores, indices, prior


def actual_old_outputs(index):
    result = {}
    for case in index["cases"]:
        for arm in case["arms"]:
            ref = {"path": str(R.BASELINE.parent / arm["receipt_path"]), "sha256": arm["receipt_sha256"]}
            receipt = bound(ref)
            rgb, info = S.read_tiff(Path(receipt["output"]["path"]))
            SB.require(info["file_sha256"] == receipt["output"]["sha256"], "historical TIFF changed")
            key = (case["scene"], case["repeat"], arm["name"])
            SB.require(key not in result, "duplicate historical output")
            result[key] = (rgb, info)
    SB.require(len(result) == 40, "incomplete historical output matrix")
    return result


def compare(path, digest):
    record, scores, indices, prior = validate_controller(path, digest)
    old_mode, new_mode = R.MODES
    off, on = scores[old_mode], scores[new_mode]
    SB.require(off["domain"] == on["domain"], "mode domains differ")
    crop, size, offset = off["domain"]
    x, y = S.canonical_grid(*size, crop["x"], crop["y"])
    mask = S.main_mask(x, y)
    key = lambda row: (row["scene"], row["repeat"], row["arm"])
    old_rows, new_rows = ({key(row): row for row in score["rows"]} for score in (off, on))
    historical = actual_old_outputs(prior)
    SB.require(set(old_rows) == set(new_rows) == set(historical) and len(old_rows) == 40,
               "comparison matrices differ")
    rows, arrays, triggers, off_identity = [], {}, [], []
    for k, old in old_rows.items():
        new = new_rows[k]
        a, info_a = S.read_tiff(Path(new["tiff"]["path"]))
        b, info_b = S.read_tiff(Path(old["tiff"]["path"]))
        original, original_info = historical[k]
        for actual, expected in ((info_a, new["tiff"]), (info_b, old["tiff"])):
            SB.require(actual["file_sha256"] == expected["file_sha256"], "mode TIFF changed")
        identity = info_b["file_sha256"] == original_info["file_sha256"] and np.array_equal(b, original)
        off_identity.append(dict(case=list(k), whole_tiff_and_pixels_identical=identity))
        SB.require(identity, f"hard-floor differs from committed M194c: {k}")
        SB.require(new["mask_sha256"] == old["mask_sha256"] == S.array_hash(mask), "different score mask")
        row = dict(scene=k[0], repeat=k[1], arm=k[2],
                   pixels=LEGACY.pixel_delta(a, b, mask),
                   whole_tiff_identical=info_a["file_sha256"] == info_b["file_sha256"])
        for kind in ("ideal", "observation") if k[0] in ("flat", "plane") else ("ideal",):
            truth = S.target(k[0], x, y, kind)
            SB.require(new[kind]["reference_sha256"] == old[kind]["reference_sha256"] == S.array_hash(truth),
                       "different truth target")
            delta = np.asarray(new[kind]["error"]["rmse_dn"]) - old[kind]["error"]["rmse_dn"]
            row[kind + "_rmse_change_dn"] = delta.tolist()
            row[kind + "_sparse_change"] = SP.compare(a, b, truth, mask, x, y)
            if np.max(delta) > 1:
                triggers.append(dict(case=list(k), target=kind, reason="channel RMSE increase >1 DN", values=delta.tolist()))
        if k[0] == "plane":
            waves = []
            for nw, ow in zip(new["output_wave_response"]["waves"], old["output_wave_response"]["waves"], strict=True):
                delta = np.asarray(nw["amplitude_dn"]) - ow["amplitude_dn"]
                waves.append(delta.tolist())
                if k[1] is None and np.min(delta) < -1:
                    triggers.append(dict(case=list(k), reason="noise-off wave loss >1 DN", values=delta.tolist()))
            row["wave_amplitude_change_dn"] = waves
        rows.append(row)
        arrays[k] = (a, b)
    paired = []
    for scene in ("flat", "plane"):
        for arm in ("full9", "single4"):
            values = [arrays[(scene, seed, arm)] for seed in SB.SEEDS[1:]]
            aa, bb = np.stack([v[0] for v in values]), np.stack([v[1] for v in values])
            ratio = np.asarray(on["summary"][scene]["ideal"][arm]["temporal_variance_dn2"]) / off["summary"][scene]["ideal"][arm]["temporal_variance_dn2"]
            if np.max(ratio) > 1.02:
                triggers.append(dict(scene=scene, arm=arm, reason="temporal variance increase >2%", ratio=ratio.tolist()))
            for kind in ("ideal", "observation"):
                result = S.paired_error(aa, bb, S.target(scene, x, y, kind), mask)
                result["direction"] = "floor-pedestal-v1 minus hard-floor, same inputs and arm"
                paired.append(dict(scene=scene, arm=arm, target=kind,
                                   variance_ratio_candidate_to_baseline=ratio.tolist(), difference=result))
    return dict(schema="m194d-mode-comparison-v1", controller_sha256=digest,
                output_pairs=len(rows), off_identity=off_identity, rows=rows, paired=paired,
                mode_scores={mode: record["modes"][mode]["score"] for mode in R.MODES},
                engineering_review_triggers=triggers,
                scope="fixed software fixture experiment; no statistical calibration, physical, default or SOTA admission")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--controller-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    SB.require(not args.out.exists(), "preserve existing comparison")
    result = compare(args.controller.resolve(), args.controller_sha)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result["comparison_reader"] = {"path": str(Path(__file__).resolve()), "sha256": S.sha256(Path(__file__)), "predecessor_sha256": S.sha256(HERE / "compare-experiment.py"), "change": "Wrap the JSON command log string as Path for the unchanged hash API; no scoring change."}
    R.write(args.out, result)
    print(json.dumps(dict(output_pairs=result["output_pairs"],
                          review_triggers=result["engineering_review_triggers"], sha256=S.sha256(args.out))))


if __name__ == "__main__":
    main()
