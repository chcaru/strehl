"""Read-only saved-flat comparison using the existing actual-baseline/guard code.

No operator import, prepare, fit, RAW read or reconstructed-field modification.
Root owns invocation and process bounds. Output is fresh display/receipt data only.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

import controls as c
import fixtures as fx


def completed_job(root):
    root = Path(root).resolve()
    process = c.load_json(root/"process.json")
    if (process.get("exit_code") != 0 or process.get("error") is not None
            or process.get("cleanup_errors") or not process.get("terminal_job_accounting")
            or process.get("job_accounting", {}).get("active_processes") != 0):
        raise ValueError("input job is not cleanly complete")
    completion = c.load_json(root/"completion.json")
    for ref in completion["reports"]:
        c.verify_ref(ref)
    return dict(process=fx.file_ref(root/"process.json"),
                completion=fx.file_ref(root/"completion.json"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cost-dir", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    begin = time.perf_counter()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    cost = Path(args.cost_dir).resolve()
    baseline = Path(args.baseline).resolve()
    cost_job = completed_job(cost)
    baseline_job = completed_job(baseline.parent.parent)
    started = c.load_json(cost/"output"/"started.json")
    # Only the actual Python producing files are required to remain current;
    # later serialization-only Rust baseline repairs do not change this fit.
    for ref in started["sources"]:
        c.verify_ref(ref)
    manifest_path = c.verify_ref(started["fixture_manifest"])
    manifest = c.load_json(manifest_path)
    fx.ICC = c.verify_ref(manifest["display_icc"]).read_bytes()
    screen = c.load_json(cost/"output"/"screen.json")
    if (screen.get("status") != "COMPLETE_BAND_RESIDUAL_COST_DIAGNOSTIC"
            or screen.get("all_cases_completed") is not True
            or len(screen.get("cases", [])) != 1):
        raise ValueError("expected exact one-case completed cost artifact")
    old = screen["cases"][0]
    if old["case_id"] != "flat-neutral" or old["mode"] != "candidate":
        raise ValueError("unexpected saved candidate")
    master = old["complete_field"]["output"]
    latent_master = old["complete_field"]["latent"]
    rgb = np.load(c.verify_ref(master), allow_pickle=False)
    latent = np.load(c.verify_ref(latent_master), allow_pickle=False)
    if rgb.shape != (128, 128, 3) or rgb.dtype != np.float32 or not np.isfinite(rgb).all():
        raise ValueError("saved field differs from complete finite128²RGB")
    row, originals = fx.load_case(manifest, "flat-neutral")
    baselines, baseline_evidence = c.read_baselines(baseline, manifest, out)
    baseline_rgb = baselines["flat-neutral"]
    score = c.image_score(row, rgb)
    if score != old["score"]:
        raise ValueError("saved-field scoring does not reproduce the cost receipt")
    baseline_score = c.image_score(row, baseline_rgb)
    guard = c.quality_guard("flat-neutral", score, baseline_score)
    truth = c.read_truth(row)
    displays = dict(truth_complete=fx.preview(out/"truth-complete.png", truth),
        candidate_complete=fx.preview(out/"candidate-complete.png", rgb),
        baseline_complete=fx.preview(out/"baseline-complete.png", baseline_rgb),
        truth_same_cells=fx.preview(out/"truth-score-region.png", truth[16:112, 16:112]),
        candidate_same_cells=fx.preview(out/"candidate-score-region.png", rgb[16:112, 16:112]),
        latent_coefficients=fx.preview(out/"latent-coefficients.png", latent))
    bindings = [fx.file_ref(cost/"output"/"screen.json"),
        fx.file_ref(cost/"output"/"started.json"), fx.file_ref(baseline),
        started["fixture_manifest"], master, latent_master,
        fx.file_ref(Path(__file__)), fx.file_ref(Path(c.__file__)), fx.file_ref(Path(fx.__file__))]
    for ref in bindings:
        c.verify_ref(ref)
    for item in manifest["cases"]:
        for source in item["sources"]:
            c.verify_ref(source)
    result = dict(status="COMPLETE_SAVED_FLAT_ACTUAL_BASELINE_REVIEW",
        command=[sys.executable, *sys.argv], seconds=time.perf_counter()-begin,
        cost_job=cost_job, actual_baseline_job=baseline_job, bindings=bindings,
        actual_baseline=baseline_evidence, case_id="flat-neutral",
        candidate_master=master, latent_master=latent_master,
        candidate_status=old["status"], candidate_numerical_converged=old["converged"],
        candidate_iterations=old["iterations"], candidate_score=score,
        actual_baseline_score=baseline_score, existing_quality_guard=guard,
        displays=displays, all_inputs_unchanged=True,
        compared_reference_cells_xywh=[16, 16, 96, 96],
        boundary_caveat="actual96²MHC crop reflects at its edge; candidate96²score is interior of128²",
        re_fit=False, operator_imported=False, RAW_reads=0,
        admission=False, photographic_admission=False, full_design_qualified=False)
    fx.save_json(out/"review.json", result)
    print(json.dumps(dict(status=result["status"], quality_pass=guard["pass_guard"],
                         re_fit=False, admission=False)))


if __name__ == "__main__":
    main()
