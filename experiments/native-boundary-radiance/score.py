"""Thin scorer for the fixed boundary-radiance comparison; root executes.

Failure inputs are fixed before outputs: missing/duplicate/wrong-seed pairs,
changed baseline bytes, wrong receipt/geometry/units, or changed admitted TIFFs
refuse scoring. On flat, increased temporal variance or ideal MSE fails even
when the other improves; a constant biased output is not a noise win. Existing
readout reductions are reused, with explicit off/apply labels. No fit consumes
this scorer's ideal target or wave metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OLD = ROOT / "experiments/m194g-larger-pupil"
SEEDS = (701, 709, 719, 727, 733, 739, 743, 751)
MODES = ("off", "apply")
GEOMETRY = {"output_native": [300, 226], "canonical_native_offset": [10, 8]}
ADMISSION_SHA = "088272bfbeca6d00a816a5de72eeaf7aac8f8ca6e0ef68941ab236655fa298e7"
TARGET_SHA = "91fbd5bf692f9411c4394d4a60e805d998eec0061553c5fcba2059f2e505e795"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, OLD / filename)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def path_for(value, base):
    need(type(value) is str, "binding path must be text")
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    if path.parts and path.parts[0] == "experiments":
        return (ROOT / path).resolve()
    return (base / path).resolve()


def bound_bytes(ref, base, limit=2 * 1024**2):
    need(type(ref) is dict and all(k in ref for k in ("path", "sha256", "bytes")), "file binding fields")
    need(type(ref["bytes"]) is int and 0 <= ref["bytes"] <= limit, "bounded file size")
    path = path_for(ref["path"], base)
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    need(len(raw) == ref["bytes"] and digest(raw) == ref["sha256"], "file binding mismatch: " + str(path))
    return path, raw


def fixed_decision(readout, scene):
    """Pure prospective predicate; uncertainty never overrides an observed loss."""
    checks = []

    def record(name, channel, region, before, after, strict=False):
        checks.append({"metric": name, "channel": channel, "region": region,
                       "baseline": before, "candidate": after,
                       "comparison": "<" if strict else "<=",
                       "passed": after < before if strict else after <= before})

    def one(rows, **wanted):
        found = [row for row in rows if all(row.get(k) == v for k, v in wanted.items())]
        need(len(found) == 1, "missing/duplicate decision operand " + str(wanted))
        return found[0]

    for channel in ("R", "G", "B"):
        for region in ("window", "boundary"):
            if scene == "flat":
                row = one(readout["paired_variance"], channel=channel, region=region)
                record("temporal_variance_dn2", channel, region,
                       row["baseline_variance_dn2"], row["candidate_variance_dn2"])
            for population, table, column in (
                ("noise-off", "individual_errors", "mse_dn2"),
                ("eight-repeat-mean", "temporal", "mean_image_mse_dn2"),
            ):
                wanted = dict(channel=channel, region=region, reference="ideal")
                if population == "noise-off":
                    wanted["seed"] = None
                before = one(readout[table], mode="off", **wanted)[column]
                after = one(readout[table], mode="apply", **wanted)[column]
                record(population + "_ideal_mse_dn2", channel, region, before, after,
                       strict=scene == "textured" and region == "boundary")
        if scene == "textured":
            for population in ("individual", "eight-repeat-mean"):
                row = one(readout["sparse"], channel=channel, region="window", seed=None,
                          population=population)
                for metric in ("maximum_absolute_error_dn", "p999_absolute_error_dn"):
                    record(population + "_" + metric, channel, "window",
                           row["before_" + metric], row["after_" + metric])
            for region in ("surface-background", "surface-foreground"):
                before = one(readout["noise_off_waves"], mode="off", channel=channel, region=region)
                after = one(readout["noise_off_waves"], mode="apply", channel=channel, region=region)
                need(len(before["differences"]) == len(after["differences"]) == 2, "wave population")
                for i, (a, b) in enumerate(zip(before["differences"], after["differences"], strict=True)):
                    record("noise-off_wave_" + str(i) + "_complex_error_dn", channel, region,
                           a["complex_error_dn"], b["complex_error_dn"])
    return {"status": ("FLAT_CONTROLS_PASS" if scene == "flat" else "TEXTURED_METRIC_CONTROLS_PASS")
            if all(row["passed"] for row in checks) else "REJECT_CANDIDATE",
            "checks": checks, "failed_checks": [row for row in checks if not row["passed"]],
            "scope": "fixed finite-population decision; no physical calibration, default promotion or SOTA claim",
            "next": "Only a flat pass permits the fixed textured comparison; shifted geometry and colour identity remain separate required controls."}


def run(args):
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    output_dir = args.output_dir.resolve()
    need(not output_dir.exists(), "preserve existing scorer output")
    input_dir = args.input_dir.resolve()
    qio = module("boundary_quality_io", "independent-quality-io.py")
    metrics = module("boundary_quality_metrics", "independent-quality-metrics.py")
    reader = module("boundary_rgb_tiff", "independent-rgb-tiff.py")
    readout = module("boundary_quality_readout", "independent-quality-readout.py")
    # This private module instance changes labels only, not numerical code/files.
    readout.MODES = MODES
    budget = metrics.Budget("score", start_cpu=start_cpu, start_wall=start_wall)
    index_path = input_dir / "run-index.json"
    index_raw = index_path.read_bytes()
    need(len(index_raw) <= 4 * 1024**2, "bounded run index")
    index = qio.strict_json(index_raw)
    need(index.get("schema") == "native-boundary-radiance-fixed-pairs-v1"
         and index.get("status") == "COMPLETE_UNSCORED", "completed fixed-pair index required")
    if args.scene == "textured":
        need(args.flat_decision is not None, "textured scoring requires the prior bound flat decision")
        flat_decision = qio.strict_json(args.flat_decision.read_bytes())
        need(flat_decision.get("proceed_to_textured") is True, "flat gate did not release textured comparison")
        bound_bytes(flat_decision["flat_run_index"], ROOT, 4 * 1024**2)
    need(type(index.get("rows")) is list and len(index["rows"]) == 18, "exact eighteen scene rows")
    rows, identities, evidence = {}, set(), []
    for row in index["rows"]:
        need(row.get("scene") == args.scene and row.get("mode") in MODES, "scene/mode mismatch")
        seed = row.get("seed")
        need(seed is None or type(seed) is int and seed in SEEDS, "fixed seed population")
        key = (seed, row["mode"])
        need(key not in rows, "duplicate scene/seed/mode")
        receipt_path, raw = bound_bytes(row["receipt"], input_dir)
        receipt = qio.strict_json(raw)
        need(receipt.get("schema") == "native-boundary-radiance-consumer-v1"
             and receipt.get("status") == "COMPLETE_UNVERIFIED", "completed boundary receipt required")
        need((receipt.get("scene"), receipt.get("seed"), receipt.get("mode")) ==
             (args.scene, seed, row["mode"]), "receipt tuple mismatch")
        need(receipt.get("noise_admission_sha256") == ADMISSION_SHA
             and receipt.get("decode_counts") == [1] * 5
             and receipt.get("inputs_unchanged") is True, "admitted original inputs")
        need(receipt["geometry"]["native"] == [320, 240]
             and receipt["geometry"]["crop_offset_native"] == [10, 8]
             and receipt["geometry"]["model_offset"] == 142, "fixed consumer coordinates")
        out_path, _ = bound_bytes(row["output"], input_dir)
        need(out_path.is_relative_to(input_dir) and out_path not in identities, "distinct current-scene output files")
        identities.add(out_path)
        need(receipt["output"]["sha256"] == row["output"]["sha256"]
             and receipt["output"]["bytes"] == row["output"]["bytes"]
             and receipt["output"]["width"] == 300 and receipt["output"]["height"] == 226,
             "receipt/TIFF association")
        log_path, log_raw = bound_bytes(row["log"], input_dir)
        diagnostic = [qio.strict_json(line.split(b": ", 1)[1]) for line in log_raw.splitlines()
                      if line.startswith(b"boundary radiance: ")]
        if row["mode"] == "apply":
            need(len(diagnostic) == 1 and diagnostic[0].get("source_frames") == 5, "actual treatment diagnostic")
            d = diagnostic[0]
            need(type(d.get("accepted")) is int and d["accepted"] >= 0
                 and d["accepted"] + sum(d["refusals"]) == d["targets"], "treatment population")
        else:
            need(not diagnostic, "feature-off unexpectedly treated")
        rows[key] = row
        evidence.append({"scene": args.scene, "seed": seed, "mode": row["mode"],
                         "output": row["output"], "receipt": row["receipt"], "log": row["log"],
                         "treatment": diagnostic, "consumer_wall_seconds": receipt["consumer_wall_seconds"]})
    need(set(rows) == {(seed, mode) for seed in (None, *SEEDS) for mode in MODES}, "complete fixed pairs")
    old_index = qio.strict_json((OLD / "production-matrix-1/run-index.json").read_bytes())
    old_rows = {(r["seed"], r["scene"]): r for r in old_index["entries"]
                if r["admission"] == "hard-floor" and r["subset"] == "all-five"}
    baseline_checks = []
    for seed in (None, *SEEDS):
        old = old_rows[(seed, args.scene)]
        _, saved = bound_bytes(old["tiff"], ROOT)
        _, current = bound_bytes(rows[(seed, "off")]["output"], input_dir)
        need(current == saved, "current-off baseline differs from saved admitted HardFloor")
        baseline_checks.append({"seed": seed, "saved": old["tiff"], "current": rows[(seed, "off")]["output"], "byte_identical": True})

    decoded_pixel_hashes = {}

    def load_rgb(row):
        path = path_for(row["output"]["path"], row.get("base", input_dir))
        rgb, decoded = reader.read_rgb_tiff(path, (226, 300, 3), row["output"]["sha256"], budget)
        decoded_pixel_hashes[str(path.resolve())] = decoded["pixel_sha256"]
        result = budget.empty((226, 300, 3), "<f8", "post-WB DN RGB")
        metrics.np.multiply(rgb, 14848.0 / 65535.0, out=result)
        return result

    scalar_raw = (OLD / "independent-quality-target-1/scalar.npy").read_bytes()
    need(digest(scalar_raw) == TARGET_SHA, "saved ideal target changed")
    scalar = budget.watch(metrics.np.load(io.BytesIO(scalar_raw), allow_pickle=False), "saved ideal scalar")
    del scalar_raw
    fixture = qio.strict_json((OLD / "fixture.json").read_bytes())
    endpoints = {}
    if args.scene == "textured":
        for index_value in (0, 4):
            matches = [r for r in old_index["entries"] if r["scene"] == "textured"
                       and r["subset"] == "endpoint-" + str(index_value)]
            need(len(matches) == 1, "existing endpoint diagnostic missing")
            endpoints[index_value] = {"output": matches[0]["tiff"], "base": ROOT}
    result = readout.scene_readout(args.scene, rows, scalar, endpoints, GEOMETRY, fixture,
                                  metrics=metrics, budget=budget, load_rgb=load_rgb)
    decision = fixed_decision(result, args.scene)
    accepted = sum(d["accepted"] for row in evidence for d in row["treatment"])
    changed_pairs = sum(decoded_pixel_hashes[str(path_for(rows[(seed, "off")]["output"]["path"], input_dir))]
                        != decoded_pixel_hashes[str(path_for(rows[(seed, "apply")]["output"]["path"], input_dir))]
                        for seed in (None, *SEEDS))
    for name, count in (("accepted_site_events", accepted), ("changed_decoded_pixel_pairs", changed_pairs)):
        decision["checks"].append({"metric": name, "baseline": 0, "candidate": count,
                                   "comparison": ">", "passed": count > 0})
    decision["failed_checks"] = [row for row in decision["checks"] if not row["passed"]]
    if decision["failed_checks"]:
        decision["status"] = "REJECT_CANDIDATE"
    result.update({"schema": "native-boundary-radiance-score-v1", "decision": decision,
                   "mode_labels": {"off": "current HardFloor, feature off", "apply": "fixed shared-pupil affine candidate"},
                   "candidate_accepted_site_events": accepted,
                   "no_demonstrated_treatment": accepted == 0 or changed_pairs == 0,
                   "changed_decoded_pixel_pairs": changed_pairs,
                   "baseline_identity": baseline_checks, "input_rows": evidence,
                   "run_index": {"path": str(index_path), "bytes": len(index_raw), "sha256": digest(index_raw)},
                   "failure_modes": {"variance": "can reward blur or bias; paired ideal errors are required",
                                     "mse": "can reward smoothing; textured complex-wave errors and extremes remain required",
                                     "amplitude": "can reward wrong phase or overshoot; use complex coefficient error",
                                     "uncertainty": "descriptive fixed-seed sampling limits; never excuses a measured increase"},
                   "work": budget.receipt(),
                   "scope": "Existing reader/reductions, fixed software truth. Target is scorer-only. No native or SOTA claim."})
    decision["proceed_to_textured"] = args.scene == "flat" and decision["status"] == "FLAT_CONTROLS_PASS"
    decision["flat_run_index" if args.scene == "flat" else "textured_run_index"] = result["run_index"]
    decision["schema"] = "native-boundary-radiance-decision-v1"
    output_dir.mkdir(parents=True)
    with (output_dir / "result.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    with (output_dir / "decision.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(decision, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": decision["status"], "failed_checks": len(decision["failed_checks"]),
                      "result": str(output_dir / "result.json")}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True, choices=("flat", "textured"))
    parser.add_argument("--flat-decision", type=Path)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
