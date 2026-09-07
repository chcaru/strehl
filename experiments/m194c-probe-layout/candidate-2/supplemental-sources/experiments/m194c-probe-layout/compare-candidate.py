"""Read the fixed baseline and candidate TIFFs and report all version differences."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/m194b-known-scene"


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


S = module(BASE / "score.py", "m194c_frozen_score")
SB = module(BASE / "score-benchmark.py", "m194c_frozen_benchmark_score")
C = module(HERE / "run-candidate.py", "m194c_candidate_controller")


def pixel_delta(candidate, baseline, mask):
    a, b = np.asarray(candidate, dtype=np.float64), np.asarray(baseline, dtype=np.float64)
    m = np.asarray(mask, dtype=bool)
    if a.shape != b.shape or a.ndim != 3 or a.shape[-1] != 3 or m.shape != a.shape[:2]:
        raise ValueError("pixel comparison requires matching RGB and spatial mask")
    if not m.any() or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("pixel comparison requires finite images and nonempty mask")
    d = a - b
    return dict(changed_components=int(np.count_nonzero(d)), components=int(d.size),
                max_abs_dn_by_channel=np.abs(d).max(axis=(0, 1)).tolist(),
                roi_changed_components=int(np.count_nonzero(d[m])),
                roi_rms_delta_dn_by_channel=np.sqrt(np.mean(d[m] ** 2, axis=0)).tolist(),
                roi_mean_delta_dn_by_channel=d[m].mean(axis=0).tolist())


def version_paired(candidate, baseline, reference, mask):
    result = S.paired_error(candidate, baseline, reference, mask)
    result["direction"] = "M194c candidate minus M194b baseline, same arm and input repeats"
    return result


def bound(path, digest):
    if S.sha256(path) != digest:
        raise ValueError(f"trusted artifact changed: {path}")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_controller(path, digest):
    record = bound(path, digest)
    if record["schema"] != "m194c-candidate-controller-v1" or record["status"] != "complete":
        raise ValueError("candidate controller did not complete")
    if record["supplemental_before"] != record["supplemental_after"]:
        raise ValueError("candidate supplemental source changed")
    C.check_supplemental(record["supplemental_before"])
    for p, h in record["supplemental_before"].items():
        if S.sha256(Path(record["supplemental_snapshots_root"]) / p) != h:
            raise ValueError("supplemental snapshot changed")
    if len(record["commands"]) != 3 or any(c["exit_code"] != 0 for c in record["commands"]):
        raise ValueError("candidate build/render/score chain incomplete")
    directory = path.parent
    prior_index = BASE / "baseline-1/run-index.json"
    prior = bound(prior_index, "37f99736bd32dfb4891bd8fa2b033cacc2c58e9265515fa53cb5921dd80d9c08")
    if record["baseline_index_sha256"] != S.sha256(prior_index):
        raise ValueError("wrong original benchmark index")
    build_path = directory / "build.json"
    build = bound(build_path, record["build_sha256"])
    index_path = directory / "run/run-index.json"
    index = bound(index_path, record["index_sha256"])
    if index["build_record"] != {"path": str(build_path), "sha256": record["build_sha256"]}:
        raise ValueError("candidate index belongs to a different build")
    for key in ("producer_result", "producer_commission"):
        if index[key] != prior[key]:
            raise ValueError("candidate substituted original inputs")
    old_build = bound(Path(prior["build_record"]["path"]), prior["build_record"]["sha256"])
    changed = sorted(p for p in set(build["sources_after"]) | set(old_build["sources_after"])
                     if build["sources_after"].get(p) != old_build["sources_after"].get(p))
    if changed != [C.GATE.relative_to(ROOT).as_posix()] or record["changed_compiler_inputs"] != changed:
        raise ValueError("candidate compiler inputs differ outside gatefloor")
    expected = [[sys.executable, "-X", "utf8", str(BASE / "consumer-run.py"),
                 "build", "--build-record", str(build_path)]]
    render = [sys.executable, "-X", "utf8", str(BASE / "run-baseline.py"),
              "--build-record", str(build_path), "--build-record-sha", record["build_sha256"]]
    for flag, key in (("producer-result", "producer_result"), ("producer-commission", "producer_commission")):
        render += ["--" + flag, prior[key]["path"], "--" + flag + "-sha", prior[key]["sha256"]]
    expected.append(render + ["--out", str(directory / "run")])
    expected.append([sys.executable, "-X", "utf8", str(BASE / "score-benchmark.py"),
                     "--index", str(index_path), "--expected-index-sha", record["index_sha256"],
                     "--out", str(directory / "score.json")])
    if [c["command"] for c in record["commands"]] != expected:
        raise ValueError("candidate controller argv differs from fixed build/render/score operations")
    for c in record["commands"]:
        if S.sha256(Path(c["log"])) != c["log_sha256"]:
            raise ValueError("candidate controller log changed")
    if set(record["frozen_m194b_files"]) != {"consumer-run.py", "run-baseline.py", "score.py", "score-benchmark.py",
                                         "producer-output-1/producer-result.json", "producer-commission-1/commission.json"}:
        raise ValueError("fixed benchmark source set differs")
    for p, h in record["frozen_m194b_files"].items():
        if S.sha256(BASE / p) != h:
            raise ValueError("fixed benchmark source changed")
    # Reopen the complete bound package with the unchanged commissioned reader.
    # A coherently altered score summary must not substitute for actual pixels.
    scored = bound(directory / "score.json", record["score_sha256"])
    replay = SB.score_run(index_path, record["index_sha256"])
    # JSON serializes the reader's domain tuple as a list. Compare identical
    # serialized values; this changes no numerical tolerance or score field.
    if scored != json.loads(json.dumps(replay, allow_nan=False)):
        raise ValueError("candidate recorded score differs from actual bound TIFF read")
    return record


def compare(controller_path, controller_sha):
    record = validate_controller(controller_path, controller_sha)
    directory = controller_path.parent
    baseline_path = BASE / "baseline-score-v3.json"
    # Resolve from the already committed immutable result.
    import subprocess
    import hashlib
    baseline_score_sha = hashlib.sha256(subprocess.check_output(
        ["git", "show", "444eb759:experiments/m194b-known-scene/baseline-score-v3.json"], cwd=ROOT)).hexdigest()
    baseline = bound(baseline_path, baseline_score_sha)
    candidate = bound(directory / "score.json", record["score_sha256"])
    if baseline["index_sha256"] != record["baseline_index_sha256"] or candidate["index_sha256"] != record["index_sha256"]:
        raise ValueError("version scores belong to different indices")
    if candidate["domain"] != baseline["domain"] or candidate["output_count"] != 40 or baseline["output_count"] != 40:
        raise ValueError("version domain or complete matrix differs")
    expected = {(scene, seed, arm) for scene in ("flat", "plane")
                for seed in (None, 701, 709, 719, 727, 733, 739, 743, 751)
                for arm in ("full9", "single4")}
    expected |= {(scene, None, arm) for scene in ("color", "color-null") for arm in ("full9", "single4")}
    key = lambda row: (row["scene"], row["repeat"], row["arm"])
    lookup = {key(r): r for r in baseline["rows"]}
    if len(lookup) != 40 or len(candidate["rows"]) != 40 or set(lookup) != expected or {key(r) for r in candidate["rows"]} != expected:
        raise ValueError("version matrix is incomplete or mismatched")
    crop, size, native_offset = candidate["domain"]
    if [2 * crop["x"], 2 * crop["y"]] != native_offset:
        raise ValueError("quad crop differs from canonical native offset")
    x, y = S.canonical_grid(*size, crop["x"], crop["y"])
    mask = (x >= 64) & (x < 256) & (y >= 64) & (y < 176)
    arrays, rows, triggers = {}, [], []
    for row in candidate["rows"]:
        k = key(row)
        old = lookup[k]
        a, info_a = S.read_tiff(Path(row["tiff"]["path"]))
        b, info_b = S.read_tiff(Path(old["tiff"]["path"]))
        for info, expected_info in ((info_a, row["tiff"]), (info_b, old["tiff"])):
            if info["file_sha256"] != expected_info["file_sha256"]:
                raise ValueError("version TIFF changed")
        if row["mask_sha256"] != old["mask_sha256"] or row["mask_sha256"] != S.array_hash(mask):
            raise ValueError("version score mask differs")
        delta = dict(scene=k[0], repeat=k[1], arm=k[2], pixels=pixel_delta(a, b, mask),
                     whole_tiff_identical=info_a["file_sha256"] == info_b["file_sha256"])
        for kind in ("ideal", "observation") if k[0] in ("flat", "plane") else ("ideal",):
            if row[kind]["reference_sha256"] != old[kind]["reference_sha256"]:
                raise ValueError("version target differs")
            error_delta = np.asarray(row[kind]["error"]["rmse_dn"]) - old[kind]["error"]["rmse_dn"]
            delta[kind + "_rmse_change_dn"] = error_delta.tolist()
            if np.max(error_delta) > 1:
                triggers.append(dict(case=list(k), kind=kind, reason="channel RMSE increase >1 DN", values=error_delta.tolist()))
        if k[0] == "plane":
            waves = []
            for new_wave, old_wave in zip(row["output_wave_response"]["waves"], old["output_wave_response"]["waves"], strict=True):
                d = np.asarray(new_wave["amplitude_dn"]) - old_wave["amplitude_dn"]
                waves.append(d.tolist())
                if k[1] is None and np.min(d) < -1:
                    triggers.append(dict(case=list(k), reason="noise-off wave loss >1 DN", values=d.tolist()))
            delta["wave_amplitude_change_dn"] = waves
        rows.append(delta)
        arrays[k] = (a, b)
    paired = []
    for scene in ("flat", "plane"):
        for arm in ("full9", "single4"):
            values = [arrays[(scene, seed, arm)] for seed in (701, 709, 719, 727, 733, 739, 743, 751)]
            aa = np.stack([v[0] for v in values])
            bb = np.stack([v[1] for v in values])
            ratio = np.asarray(candidate["summary"][scene]["ideal"][arm]["temporal_variance_dn2"]) / baseline["summary"][scene]["ideal"][arm]["temporal_variance_dn2"]
            if np.max(ratio) > 1.02:
                triggers.append(dict(scene=scene, arm=arm, reason="temporal variance increase >2%", ratio=ratio.tolist()))
            for kind in ("ideal", "observation"):
                paired.append(dict(scene=scene, arm=arm, target=kind,
                                   variance_ratio_candidate_to_baseline=ratio.tolist(),
                                   difference=version_paired(aa, bb, S.target(scene, x, y, kind), mask)))
    return dict(schema="m194c-version-comparison-v1", controller_sha256=controller_sha,
                baseline_score_sha256=baseline_score_sha, candidate_score_sha256=record["score_sha256"],
                output_pairs=len(rows), rows=rows, paired=paired, engineering_review_triggers=triggers,
                scope="fixed synthetic software comparison; no physical or SOTA quality admission")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--controller", type=Path, required=True)
    p.add_argument("--controller-sha", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = compare(args.controller.resolve(), args.controller_sha)
    C.write(args.out, result, new=True)
    print(json.dumps(dict(output_pairs=result["output_pairs"],
                          review_triggers=result["engineering_review_triggers"], output_sha256=S.sha256(args.out))))


if __name__ == "__main__":
    main()
