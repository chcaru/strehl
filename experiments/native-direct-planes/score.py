"""Fixed M194b direct-plane readout. Source-frozen before image scoring.

Failing inputs: biased constant/blurred waves, phase shifts, chroma erasure,
isolated outliers, changed rounded floats, ignored mode, and incomplete/bad
bindings. Variance alone rewards blur; all frozen fidelity bars accompany it.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "experiments/m194b-known-scene"
SEEDS = (None, 701, 709, 719, 727, 733, 739, 743, 751)
MODES = ("off", "rounded", "float")
PRODUCER_SHA = "544d47dbc0fdebcf220094ca53434ca49abfee62f55febec27b36f58c24087cc"
COMMISSION_SHA = "0a8eb43a53d8f44a6e803f531fd2e83d12b7a59e280440e730dc6ea6523b50d5"
DESIGN_SHA = "9783e7c269c7902c75323d04b7f0e965317ad576fd6236e6a8951d95e6f5c47c"
CONTROL_SHA = "3aea26e0faf519a48ad2f6638b6bfb3531d345c60452ec0d3272fe622b47d1b3"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


B = module("direct_m194b_benchmark", OLD / "score-benchmark.py")
S = B.S
need = B.require


def resolve(value, base):
    p = Path(value)
    if p.is_absolute():
        return p
    return (ROOT if p.parts and p.parts[0] == "experiments" else base) / p


def binding(path):
    return {"path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": S.sha256(path)}


def bound(ref, base, *, json_file=True):
    need(isinstance(ref, dict) and {"path", "bytes", "sha256"} <= set(ref), "missing file binding")
    p = resolve(ref["path"], base)
    need(type(ref["bytes"]) is int and 0 < ref["bytes"] <= 4 * 1024 * 1024, "invalid bounded file size")
    need(p.stat().st_size == ref["bytes"], f"file size changed: {p}")
    sha = ref["sha256"]
    need(isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), "invalid digest")
    need(S.sha256(p) == sha, f"file content changed: {p}")
    if not json_file:
        return p
    return p, json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=B.unique_object,
                         parse_constant=B.bad_constant)


def check_plan(plan, manifest, manifest_sha, mode):
    # Only this declared extension is removed before the existing exact checker.
    p = copy.deepcopy(plan)
    need(p.pop("direct_planes_mode") == mode, "plan has wrong direct-plane mode")
    need(p.pop("direct_planes_observer") is True, "primary output lacks direct observer")
    need(p["schema"] == "native-direct-planes-consumer-plan-v1", "wrong direct plan schema")
    p["schema"] = "m194b-consumer-plan-v1"
    need(p["environment"].pop("STREHL_DIRECT_PLANES") == mode, "plan mode/environment disagree")
    return B.validate_plan(p, manifest, manifest_sha)


def check_evidence(receipt, mode):
    e = receipt["direct_planes_evidence"]
    need(e["observer_enabled"] is True and e["dimensions_quad"] == [142, 106] and
         e["site_order"] == ["R", "G1", "G2", "B"], "wrong observed domain/order")
    need(e["hash_encoding"] == "ordered IEEE754 f32 bits, little endian; labels/dimensions in receipt", "wrong float hash encoding")
    hits = (e["actual_direct_calls"], e["probe_direct_calls"])
    need(all(type(v) is int and v >= 0 for v in hits), "invalid branch counts")
    need(hits == (0, 0) if mode == "off" else all(v > 0 for v in hits), "actual/probe mode was not live")
    need(e["input_captures"] == len(e["inputs"]) == 9 and
         [v["original_index"] for v in e["inputs"]] == list(range(9)), "incomplete/reordered input observation")
    need(e["collapsed_captures"] == len(e["collapsed"]) == 1, "missing or duplicate collapsed result")
    def record(r, label, count):
        need(r["label"] == label and r["values"] == count and
             r["finite_values"] == count and type(r["fractional_values"]) is int and
             0 <= r["fractional_values"] <= count, "invalid/nonfinite consumed value record")
        h = r["sha256_f32_le"]
        need(isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h), "invalid float digest")
    def planes(records):
        need(len(records) == 4, "missing consumed CFA plane")
        for p, label in zip(records, ("R", "G1", "G2", "B")):
            record(p, label, 142 * 106)
    for observed in e["inputs"]:
        planes(observed["planes"])
        record(observed["luma"], "luma", 142 * 106)
        beta = observed["beta"]
        need(beta is not None and type(beta["values"]) is int and 1 <= beta["values"] <= 3,
             "missing measured probe beta")
        record(beta, "beta", beta["values"])
    planes(e["collapsed"][0])
    return e


def check_placebo(index, base, primary_receipt, primary_info):
    refs = index["observer_placebo"]
    _, plan = bound(refs["plan"], base)
    expected = copy.deepcopy(primary_receipt["plan"])
    expected["direct_planes_observer"] = False
    need(plan == expected, "observer placebo changed anything except observer enablement")
    rp, receipt = bound(refs["receipt"], base)
    for field in ("schema", "manifest_sha256", "frame_subset_original", "reference_original_index",
                  "reference_local_index", "decode_counts", "confidence", "direct_planes_mode"):
        need(receipt[field] == primary_receipt[field], f"observer placebo changed {field}")
    need(receipt["plan"] == plan and receipt["plan_sha256"] == refs["plan"]["sha256"], "placebo plan binding")
    e = receipt["direct_planes_evidence"]
    need(e["observer_enabled"] is False and all(e[k] == 0 for k in
         ("actual_direct_calls", "probe_direct_calls", "input_captures", "collapsed_captures")) and
         e["inputs"] == e["collapsed"] == [], "disabled observer captured values or counters")
    op = bound(refs["output"], base, json_file=False)
    out = receipt["output"]
    need(op.samefile(resolve(out["path"], rp.parent)) and
         out["sha256"] == refs["output"]["sha256"], "placebo output binding")
    _, info = S.read_tiff(op)
    for tk, rk in (("file_sha256", "sha256"), ("pixel_sha256", "pixel_sha256_le"), ("bytes", "bytes")):
        need(info[tk] == out[rk], "placebo actual TIFF differs from receipt")
    need(not op.samefile(Path(primary_info["path"])), "placebo reused primary output path")
    return {"bindings": refs, "whole_tiff_equal": info["file_sha256"] == primary_info["file_sha256"],
            "decoded_pixels_equal": info["pixel_sha256"] == primary_info["pixel_sha256"]}


def load_population(index_path, scene):
    index_ref = binding(index_path)
    _, index = bound(index_ref, index_path.parent)
    need(index["schema"] == "native-direct-planes-fixed-pairs-v1" and
         index["status"] == "COMPLETE_UNSCORED", "incomplete/wrong render index")
    need(index["scene"] == scene, "wrong scoring phase")
    need(S.sha256(HERE / "design.md") == DESIGN_SHA, "prospective design changed")
    _, controls = bound(index["controls"], index_path.parent)
    need(index["controls"]["sha256"] == CONTROL_SHA, "different required control population")
    need(controls["status"] == "TWELVE_DIRECT_PLANES_CONTROLS_PASS", "required native controls failed")
    producer_path = OLD / "producer-output-1/producer-result.json"
    producer = B.read_bound(producer_path, PRODUCER_SHA)
    need(producer["status"] == "complete" and producer["commission_sha256"] == COMMISSION_SHA,
         "uncommissioned saved source population")
    declared = {str((producer_path.parent / p["path"]).resolve()): p["sha256"] for p in producer["manifests"]}
    flat = None
    if scene == "flat":
        expected = {("flat", seed, mode) for seed in SEEDS for mode in MODES}
    else:
        flat_path, flat = bound(index["flat_decision"], index_path.parent)
        need(flat["schema"] == "native-direct-planes-decision-v1" and flat["phase"] == "flat", "wrong flat decision")
        bound(flat["run_index"], flat_path.parent)
        need(flat["controls"]["sha256"] == CONTROL_SHA and flat["design_sha256"] == DESIGN_SHA,
             "detail release differs from frozen flat controls/design")
        need(flat["scorer_sha256"] == S.sha256(Path(__file__)), "scorer changed after flat release")
        need(type(flat["proceed_to_precision_detail"]) is bool, "invalid flat release")
        modes = MODES if flat["proceed_to_precision_detail"] else MODES[:2]
        expected = {(s, None, mode) for s in ("plane", "color") for mode in modes}
    rows = index["rows"]
    need(len(rows) == len(expected), "wrong fixed output count")
    outputs, evidence, infos, checked_sources, used = {}, {}, {}, set(), set()
    primary_receipt = None
    for row in rows:
        key = (row["scene"], row["seed"], row["mode"])
        need(key in expected and key not in outputs, "unexpected or duplicate scene/seed/mode")
        need(row["seed"] is None or type(row["seed"]) is int, "noninteger seed")
        mp, manifest = bound(row["manifest"], index_path.parent)
        bundle = "noise-off" if key[1] is None else f"seed-{key[1]}"
        wanted = (producer_path.parent / key[0] / bundle / "manifest.json").resolve()
        need(mp.resolve() == wanted and declared[str(wanted)] == row["manifest"]["sha256"], "wrong saved manifest")
        need(manifest["schema"] == "m194b-known-scene-v1" and
             (manifest["scene"], manifest["repeat"]) == key[:2] and
             manifest["noise_enabled"] is (key[1] is not None), "wrong source scene/noise label")
        if str(wanted) not in checked_sources:
            need(len(manifest["frames"]) == 9, "incomplete original frame population")
            for i, source in enumerate(manifest["frames"]):
                p = (mp.parent / source["path"]).resolve()
                need(p.is_relative_to(mp.parent.resolve()) and source["index"] == i and
                     source["bytes"] == 153600 and p.stat().st_size == 153600 and
                     S.sha256(p) == source["sha256"], "changed/misindexed original CFA source")
            checked_sources.add(str(wanted))
        _, plan = bound(row["plan"], index_path.parent)
        x, y, mask = check_plan(plan, manifest, row["manifest"]["sha256"], key[2])
        rp, receipt = bound(row["receipt"], index_path.parent)
        need(receipt["schema"] == "native-direct-planes-consumer-receipt-v1" and
             receipt["direct_planes_mode"] == key[2] and receipt["plan"] == plan and
             receipt["manifest_sha256"] == row["manifest"]["sha256"] and
             receipt["plan_sha256"] == row["plan"]["sha256"], "receipt differs from bound plan/input")
        need(receipt["frame_subset_original"] == list(range(9)) and
             receipt["reference_original_index"] == receipt["reference_local_index"] == 4 and
             receipt["decode_counts"] == [1] * 9 and receipt["confidence"] is None, "wrong consumer subset/gauge/reads")
        out = receipt["output"]
        op = bound(row["output"], index_path.parent, json_file=False)
        need(op.samefile(resolve(out["path"], rp.parent)) and
             out["sha256"] == row["output"]["sha256"], "output/receipt binding differs")
        need(str(op.resolve()) not in used, "same delivered path reused")
        used.add(str(op.resolve()))
        rgb, info = S.read_tiff(op)  # Already post-WB DN; no second conversion.
        for tk, rk in (("file_sha256", "sha256"), ("pixel_sha256", "pixel_sha256_le"),
                       ("bytes", "bytes"), ("width", "width"), ("height", "height"),
                       ("channels", "channels"), ("software", "software")):
            need(info[tk] == out[rk], f"actual TIFF differs from receipt: {tk}")
        need(out["sample_type"] == "u16" and out["software"] == "strehl 0.0.0" and
             [info["width"], info["height"]] == plan["output_native"], "wrong delivered format/geometry")
        need(not any(info["rail_zero_by_channel"] + info["rail_max_by_channel"]), "unexpected delivered rails")
        outputs[key], evidence[key], infos[key] = rgb, check_evidence(receipt, key[2]), info
        if key == ("flat", None, "off"):
            primary_receipt = receipt
    need(set(outputs) == expected, "missing fixed pair")
    placebo = (check_placebo(index, index_path.parent, primary_receipt, infos[("flat", None, "off")])
               if scene == "flat" else flat["observer_placebo"])
    return index, index_ref, outputs, evidence, infos, x, y, mask, flat, placebo


def comparisons(checks, name, candidate, baseline, *, absolute=False):
    a, b = S.finite_array(candidate, name), S.finite_array(baseline, name)
    need(a.shape == b.shape and a.shape[-1] == 3, "comparison shape")
    if absolute:
        a, b = np.abs(a), np.abs(b)
    for index in np.ndindex(a.shape):
        checks.append({"metric": name, "component": list(index),
                       "off": float(b[index]), "float": float(a[index]),
                       "difference": float(a[index] - b[index]), "pass": bool(a[index] <= b[index])})


def tails(output, reference, mask):
    d = np.sort(np.abs(output[mask] - reference[mask]), axis=0)
    return {"p99_9_abs_error_dn": d[math.ceil(.999 * len(d)) - 1].tolist(),
            "max_abs_error_dn": d[-1].tolist(), "quantile": "nearest rank on fixed native mask"}


def complex_waves(output, reference):
    need(len(output["waves"]) == len(reference["waves"]), "wave count changed")
    errors = []
    for a, b in zip(output["waves"], reference["waves"]):
        need(a["frequency_native"] == b["frequency_native"], "wave frequencies changed")
        av = np.asarray(a["amplitude_dn"]) * np.exp(1j * np.asarray(a["phase_rad"]))
        bv = np.asarray(b["amplitude_dn"]) * np.exp(1j * np.asarray(b["phase_rad"]))
        errors.append(np.abs(av - bv).tolist())
    return errors


def rounded_pairs(outputs, evidence, infos):
    pairs = []
    for scene, seed, mode in outputs:
        if mode != "rounded":
            continue
        off, rounded = (scene, seed, "off"), (scene, seed, "rounded")
        a, b = evidence[off], evidence[rounded]
        exact = {"whole_tiff": infos[off]["file_sha256"] == infos[rounded]["file_sha256"],
                 "decoded_pixels": infos[off]["pixel_sha256"] == infos[rounded]["pixel_sha256"],
                 "consumed_planes_luma_beta_f32": a["inputs"] == b["inputs"],
                 "collapsed_f32": a["collapsed"] == b["collapsed"]}
        pairs.append({"scene": scene, "seed": seed, "equal": exact,
                      "pass": all(exact.values())})
    return pairs


def fractional_witnesses(evidence):
    witnesses = []
    for (scene, seed, mode), candidate in evidence.items():
        if mode != "float":
            continue
        baseline = evidence[(scene, seed, "off")]
        for a, b in zip(candidate["inputs"], baseline["inputs"]):
            for ap, bp in zip(a["planes"], b["planes"]):
                # At integer black512 the old extracted planes are integral;
                # a changed digest with genuinely fractional consumed values
                # witnesses omitted quantization at the actual consumer.
                if ap["fractional_values"] > 0 and bp["fractional_values"] == 0 and ap["sha256_f32_le"] != bp["sha256_f32_le"]:
                    witnesses.append({"scene": scene, "seed": seed, "original_index": a["original_index"],
                                      "plane": ap["label"], "fractional_values": ap["fractional_values"]})
    return witnesses


def flat_metrics(outputs, x, y, mask):
    ref = S.target("flat", x, y)
    stacks = {mode: np.stack([outputs[("flat", seed, mode)] for seed in SEEDS[1:]]) for mode in MODES}
    repeat = {mode: S.repeat_error(stack, ref, mask) for mode, stack in stacks.items()}
    noiseoff = {mode: S.error(outputs[("flat", None, mode)], ref, mask) for mode in MODES}
    paired = S.paired_error(stacks["float"], stacks["off"], ref, mask)
    paired["direction"] = "direct precision (float) minus current off; negative error/variance differences favor float"
    checks = []
    for metric, absolute in (("temporal_variance_dn2", False), ("repeat_mean_mse_dn2", False),
                             ("bias_of_repeat_mean_dn", True)):
        comparisons(checks, "flat.repeat." + metric, repeat["float"][metric], repeat["off"][metric], absolute=absolute)
    for metric, absolute in (("mse_dn2", False), ("bias_dn", True)):
        comparisons(checks, "flat.noiseoff." + metric, noiseoff["float"][metric], noiseoff["off"][metric], absolute=absolute)
    v, base = np.asarray(repeat["float"]["temporal_variance_dn2"]), np.asarray(repeat["off"]["temporal_variance_dn2"])
    delta = np.asarray(paired["temporal_variance_difference_dn2"])
    se = np.asarray(paired["variance_difference_jackknife_se_dn2"])
    material = (base > 0) & (v <= .99 * base) & (delta + 2 * se < 0)
    return {"repeat": repeat, "noiseoff": noiseoff, "paired": paired,
            "noiseoff_tails": {m: tails(outputs[("flat", None, m)], ref, mask) for m in MODES},
            "reference_sha256": S.array_hash(ref)}, checks, material.tolist()


def detail_metrics(outputs, x, y, mask):
    rows, checks, material = [], [], []
    for scene in ("plane", "color"):
        modes = [m for m in MODES if (scene, None, m) in outputs]
        frequencies = [(v[1], v[2]) for v in (S.PLANE_WAVES if scene == "plane" else S.COLOR_WAVES)]
        waves = {m: S.wave_response(outputs[(scene, None, m)], x, y, mask, frequencies) for m in modes}
        for kind in (("ideal", "observation") if scene == "plane" else ("ideal",)):
            ref = S.target(scene, x, y, kind)
            ref_wave = S.wave_response(ref, x, y, mask, frequencies)
            arms = {}
            for mode in modes:
                output = outputs[(scene, None, mode)]
                arms[mode] = dict(S.error(output, ref, mask), **tails(output, ref, mask),
                                  complex_wave_error_dn=complex_waves(waves[mode], ref_wave),
                                  wave_response=waves[mode])
            if "float" in modes:
                name = f"{scene}.{kind}."
                for metric in ("rmse_dn", "bias_dn", "p99_9_abs_error_dn", "max_abs_error_dn", "complex_wave_error_dn"):
                    comparisons(checks, name + metric, arms["float"][metric], arms["off"][metric], absolute=metric == "bias_dn")
                reductions = np.asarray(arms["off"]["rmse_dn"]) - np.asarray(arms["float"]["rmse_dn"])
                threshold = .400776 if scene == "plane" else 14848 / 65535
                material.append({"scene": scene, "target": kind, "rmse_reduction_dn": reductions.tolist(),
                                 "threshold_dn": threshold, "pass_by_channel": (reductions >= threshold).tolist()})
            rows.append({"scene": scene, "target": kind, "reference_sha256": S.array_hash(ref),
                         "reference_wave_response": ref_wave, "arms": arms})
    return {"rows": rows}, checks, material


def run(scene, input_dir):
    index, index_ref, outputs, evidence, infos, x, y, mask, flat, placebo = load_population(input_dir / "run-index.json", scene)
    rounded = rounded_pairs(outputs, evidence, infos)
    placebo_ok = placebo["whole_tiff_equal"] and placebo["decoded_pixels_equal"]
    rounded_ok = all(p["pass"] for p in rounded) and placebo_ok
    if flat is not None:
        rounded_ok = rounded_ok and flat["rounded_exact_pass"]
    fractional = fractional_witnesses(evidence)
    changed = [dict(scene=s, seed=seed) for s, seed, mode in outputs if mode == "float" and
               infos[(s, seed, mode)]["pixel_sha256"] != infos[(s, seed, "off")]["pixel_sha256"]]
    if scene == "flat":
        measurements, checks, material = flat_metrics(outputs, x, y, mask)
        precision_pass = all(c["pass"] for c in checks)
        proceed = rounded_ok and precision_pass and bool(fractional)
        status = "ROUNDED_REJECT" if not rounded_ok else ("FLAT_PASS" if proceed else "FLAT_REJECT")
        material_flat, material_detail = material, []
    else:
        measurements, checks, material_detail = detail_metrics(outputs, x, y, mask)
        material_flat = flat["material_flat_variance_by_channel"]
        precision_pass = flat["proceed_to_precision_detail"] and all(c["pass"] for c in checks)
        live_pixels = bool(changed) or bool(flat["changed_float_pixel_pairs"])
        live_fractional = bool(fractional) or bool(flat["fractional_consumed_witnesses"])
        material_any = any(material_flat) or any(any(r["pass_by_channel"]) for r in material_detail)
        proceed = False
        if not rounded_ok:
            status = "ROUNDED_REJECT"
        elif not precision_pass:
            status = "PRECISION_REJECT"
        elif not live_pixels or not live_fractional or not material_any:
            status = "NO_DEMONSTRATED_BENEFIT"
        else:
            status = "PRECISION_FIXED_TARGETS_PASS"
    decision = {"schema": "native-direct-planes-decision-v1", "phase": scene, "status": status,
                "run_index": index_ref, "controls": index["controls"], "design_sha256": DESIGN_SHA,
                "scorer_sha256": S.sha256(Path(__file__)), "rounded_exact_pass": rounded_ok,
                "precision_nonregression_pass": precision_pass,
                "proceed_to_precision_detail": proceed,
                "material_flat_variance_by_channel": material_flat,
                "material_detail": material_detail, "changed_float_pixel_pairs": changed,
                "fractional_consumed_witnesses": fractional, "observer_placebo": placebo,
                "prior_flat_decision": index.get("flat_decision"),
                "failed_checks": [c for c in checks if not c["pass"]]}
    result = {"schema": "native-direct-planes-score-v1", "decision": decision,
              "output_count": len(outputs), "mask_pixels": int(mask.sum()), "mask_sha256": S.array_hash(mask),
              "units": "post-WB DN from actual RGB16 * 14848/65535; no second black subtraction",
              "measurements": measurements, "checks": checks, "rounded_pairs": rounded,
              "tiffs": [{"scene": k[0], "seed": k[1], "mode": k[2], "info": v} for k, v in infos.items()],
              "reader_sha256": S.sha256(OLD / "score.py"), "plan_checker_sha256": S.sha256(OLD / "score-benchmark.py"),
              "failure_directions": ["Variance and noisy MSE can reward blur or biased flattening; fixed noise-off and repeat-mean fidelity must also pass.",
                  "RMSE averages can hide local outliers; nearest-rank p99.9 and literal max are separate nonregression bars.",
                  "Amplitude alone can reward sharpening and miss phase shifts; fixed complex-wave error compares both amplitude and phase.",
                  "A TIFF identity cannot establish collapsed f32 identity; the latter is compared from direct pre-writer evidence."],
              "scope": "MEASURED under saved synthetic photon model; no physical calibration, native speed or SOTA claim",
              "color_wb_convention": "producer exact-rational inverse WB versus consumed f32 gains retains a small finite-arithmetic discrepancy",
              "plane_materiality_floor": "0.400776 DN is inherited engineering ranking floor, not rigorous target-error propagation"}
    return result, decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", choices=("flat", "detail"), required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    need(not args.output_dir.exists(), "preserve prior score; output directory exists")
    result, decision = run(args.scene, args.input_dir.resolve())
    args.output_dir.mkdir(parents=True)
    for name, value in (("result.json", result), ("decision.json", decision)):
        (args.output_dir / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": decision["status"], "proceed_to_precision_detail": decision["proceed_to_precision_detail"]}))


if __name__ == "__main__":
    main()
