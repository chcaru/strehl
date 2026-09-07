"""Independent actual consumer trust, padding, curvature and TIFF controls."""
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
import uuid
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return path


def main():
    build = HERE / "consumer-build-1.json"
    build_sha = sha(build)
    work = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "work" / ("independent-consumer-" + uuid.uuid4().hex[:10])
    work.mkdir(parents=True, exist_ok=True)
    source = HERE / "producer-output-1/plane/noise-off"
    base = work / "baseline"
    if not base.exists(): shutil.copytree(source, base)
    manifest = base / "manifest.json"
    original = load(manifest)
    commands = []
    checks = {}
    spec = importlib.util.spec_from_file_location("independent_consumer_scorer", HERE / "score.py")
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)

    def invoke(name, mode, m=manifest, p=None, trusted_m=None, trusted_p=None, subset="all", confidence=False):
        directory = work / name
        directory.mkdir(parents=True, exist_ok=True)
        p = p or directory / "plan.json"
        argv = [sys.executable, "-B", str(HERE / "consumer-run.py"), mode,
                "--build-record", str(build), "--build-sha256", build_sha,
                "--manifest", str(m), "--manifest-sha256", trusted_m or sha(m),
                "--plan", str(p), "--log", str(directory / "command.log")]
        if mode == "render":
            argv += ["--plan-sha256", trusted_p or sha(p), "--subset", subset,
                     "--output", str(directory / "output.tiff"), "--receipt", str(directory / "receipt.json")]
            if confidence:
                argv += ["--confidence", str(directory / "confidence.tiff")]
        evidence_path = directory / "command.json"
        if evidence_path.exists():
            evidence = load(evidence_path)
            commands.append(dict(name=name, argv=argv, exit_code=evidence["exit_code"],
                                 log=str(directory / "driver.log"), log_sha256=sha(directory / "driver.log"), reused_preserved_invocation=True))
            return evidence["exit_code"] == 0, p, directory
        run = subprocess.run(argv, cwd=ROOT, capture_output=True)
        (directory / "driver.log").write_bytes(run.stdout + run.stderr)
        commands.append(dict(name=name, argv=argv, exit_code=run.returncode,
                             log=str(directory / "driver.log"), log_sha256=sha(directory / "driver.log")))
        return run.returncode == 0, p, directory

    okay, plan_path, _ = invoke("plan", "plan")
    checks["actual-plan"] = okay
    assert okay
    plan = load(plan_path)
    checks["plan-before-pixels"] = not list((work / "plan").glob("*.tiff")) and (work / "plan/plan.json").stat().st_mtime_ns < min((p.stat().st_mtime_ns for p in work.rglob("*.tiff")), default=2**63)
    checks["registered-actual-crop"] = plan["crop_quad"] == dict(x=9, y=7, width=142, height=106)
    # Recompute every pull-map's native landmarks directly, independently of
    # Similarity::from_params and receipt-generation code.
    max_landmark_error = 0.
    for row, placement in zip(original["geometry"]["frames"], plan["placements"]):
        s = row["scale"]
        for x, y in [(0., 0.), (319., 239.), (71., 149.)]:
            expected = np.array([183., 101.]) + s * (np.array([x, y]) - [183., 101.])
            q = np.array([x/2-80, y/2-60])
            t = placement["quad_similarity"]
            got = 2*(np.array([t["a_re"]*q[0]-t["a_im"]*q[1]+t["b_re"],
                               t["a_im"]*q[0]+t["a_re"]*q[1]+t["b_im"]])+[80,60])
            max_landmark_error = max(max_landmark_error, float(np.max(abs(got-expected))))
    checks["independent-native-landmarks"] = max_landmark_error < 1e-12
    outputs = {}
    for name, subset, confidence in [("full", "all", False), ("repeat", "all", False),
                                      ("best", "best", False), ("confidence", "all", True)]:
        okay, _, directory = invoke(name, "render", p=plan_path, subset=subset, confidence=confidence)
        checks[name + "-renders"] = okay
        assert okay
        receipt = load(directory / "receipt.json")
        rgb, info = scorer.read_tiff(directory / "output.tiff")
        checks[name + "-actual-TIFF-binding"] = info["file_sha256"] == receipt["output"]["sha256"] and info["pixel_sha256"] == receipt["output"]["pixel_sha256_le"]
        checks[name + "-original-crop-and-gauge"] = receipt["plan"] == plan and receipt["reference_original_index"] == 4 and receipt["reference_local_index"] == (0 if subset == "best" else 4)
        checks[name + "-decode-counts"] = receipt["decode_counts"] == [2 if confidence else 1] * (1 if subset == "best" else 9)
        outputs[name] = dict(info=info, rgb=rgb)
    checks["repeat-byte-invariance"] = outputs["full"]["info"]["file_sha256"] == outputs["repeat"]["info"]["file_sha256"]
    checks["confidence-byte-invariance"] = outputs["full"]["info"]["file_sha256"] == outputs["confidence"]["info"]["file_sha256"]

    # Re-hashing a candidate plan does not bypass recomputation against inputs.
    mutations = {}
    q = copy.deepcopy(plan); q["crop_quad"]["x"] += 1; q["canonical_native_offset"][0] += 2
    mutations["coherent-same-size-crop"] = q
    q = copy.deepcopy(plan); q["crop_quad"]["width"] -= 2; q["output_native"][0] -= 4
    mutations["smaller-valid-crop"] = q
    q = copy.deepcopy(plan); q["placements"][3]["quad_similarity"]["a_re"] += .01
    mutations["interior-map"] = q
    q = copy.deepcopy(plan); q["scale_centre_native"][0] -= 8
    mutations["scale-center"] = q
    q = copy.deepcopy(plan); q["noise"]["gain_dn_per_e"] *= 2
    mutations["noise-model"] = q
    q = copy.deepcopy(plan); q["config"]["space"] = "LinearSrgb"
    mutations["writer-space"] = q
    for name, changed in mutations.items():
        path = write(work / (name + ".json"), changed)
        okay, _, directory = invoke("reject-" + name, "render", p=path)
        checks["refuse-rehashed-" + name] = not okay and not (directory / "output.tiff").exists()
    okay, _, directory = invoke("reject-stale-plan", "render", p=work / "coherent-same-size-crop.json", trusted_p=sha(plan_path))
    checks["refuse-stale-plan"] = not okay and not (directory / "output.tiff").exists()

    invalid = {}
    q = copy.deepcopy(original); q["sensor"]["noise_gain_dn_per_e"] = .5
    invalid["gain"] = q
    q = copy.deepcopy(original); q["sensor"]["width"] = True
    invalid["bool-dimension"] = q
    q = copy.deepcopy(original); q["sensor"]["width"] = 320.0
    invalid["float-dimension"] = q
    q = copy.deepcopy(original); q["geometry"]["reference_index"] = 0
    invalid["foreign-reference"] = q
    q = copy.deepcopy(original); q["frames"][1]["path"] = q["frames"][0]["path"]
    invalid["duplicate-path"] = q
    q = copy.deepcopy(original); q["frames"][0]["path"] = "../frame.cfa"
    invalid["escape-path"] = q
    q = copy.deepcopy(original); q["geometry"]["frames"][2]["scale"] = None
    invalid["null-scale"] = q
    q = copy.deepcopy(original); q["geometry"]["extra"] = 1
    invalid["unknown-field"] = q
    for name, changed in invalid.items():
        path = write(base / ("bad-" + name + ".json"), changed)
        okay, _, _ = invoke("reject-manifest-" + name, "plan", m=path)
        checks["refuse-manifest-" + name] = not okay
    for name, text in [("duplicate-json", manifest.read_text().replace('"schema":', '"schema": "duplicate", "schema":', 1)),
                       ("nonfinite-json", manifest.read_text().replace('1.0561223412120058', 'NaN', 1))]:
        path = base / (name + ".json"); path.write_text(text)
        okay, _, _ = invoke("reject-" + name, "plan", m=path)
        checks["refuse-" + name] = not okay

    # A separately authorized valid storage layout is inert. Original active
    # samples and CFA convention are unchanged, including odd absolute origin.
    padded = copy.deepcopy(original)
    padded["sensor"].update(active_origin=[7, 3], stride=339, buffer_height=251)
    padded_path = write(base / "padding.json", padded)
    okay, padded_plan, _ = invoke("padding-plan", "plan", m=padded_path)
    checks["padding-plans"] = okay
    okay, _, directory = invoke("padding-render", "render", m=padded_path, p=padded_plan)
    checks["padding-byte-invariance"] = okay and sha(directory / "output.tiff") == outputs["full"]["info"]["file_sha256"]

    # Explicitly changed trusted inputs are legitimate alternate fixtures, not
    # accepted baseline descriptors. Keep endpoints/reference unchanged so a
    # consumer using only the endpoints would miss this live control.
    curve = copy.deepcopy(original)
    for i in [1, 2, 3, 5, 6, 7]:
        curve["geometry"]["frames"][i]["scale"] += .025
    curve_path = write(base / "changed-interior.json", curve)
    okay, curve_plan, _ = invoke("curve-plan", "plan", m=curve_path)
    checks["changed-curve-plans"] = okay
    okay, _, directory = invoke("curve-render", "render", m=curve_path, p=curve_plan)
    checks["changed-interior-actually-changes-pixels"] = okay and sha(directory / "output.tiff") != outputs["full"]["info"]["file_sha256"]
    checks["changed-interior-endpoints-reference-preserved"] = all(curve["geometry"]["frames"][i] == original["geometry"]["frames"][i] for i in [0, 4, 8])
    changed_rgb, changed_info = scorer.read_tiff(directory / "output.tiff")
    changed_plan = load(curve_plan)
    x, y = scorer.canonical_grid(*plan["output_native"], plan["crop_quad"]["x"], plan["crop_quad"]["y"])
    mask = scorer.main_mask(x, y)
    error = {name: scorer.error(item["rgb"], scorer.target("plane", x, y, "observation"), mask) for name, item in outputs.items()}
    cx, cy = scorer.canonical_grid(*changed_plan["output_native"], changed_plan["crop_quad"]["x"], changed_plan["crop_quad"]["y"])
    cmask = scorer.main_mask(cx, cy)
    checks["changed-interior-same-canonical-ROI"] = np.array_equal(np.stack([x[mask], y[mask]]), np.stack([cx[cmask], cy[cmask]]))
    checks["changed-interior-actual-ROI-pixel-change"] = not np.array_equal(changed_rgb[cmask], outputs["full"]["rgb"][mask])
    error["changed-interior"] = scorer.error(changed_rgb, scorer.target("plane", cx, cy, "observation"), cmask)
    checks["changed-interior-error-readout"] = max(abs(np.array(error["changed-interior"]["mse_dn2"])-error["full"]["mse_dn2"])) > 1

    frame = base / original["frames"][4]["path"]
    before = frame.read_bytes()
    pixels = np.frombuffer(before, dtype="<u2").copy().reshape(240, 320)
    pixels[90:122, 100:132] += 4000
    frame.write_bytes(pixels.tobytes())
    okay, _, _ = invoke("reject-actual-frame", "plan")
    checks["refuse-actual-frame-stale-hash"] = not okay
    altered = copy.deepcopy(original); altered["frames"][4]["sha256"] = sha(frame)
    altered_path = write(base / "changed-content.json", altered)
    okay, _, _ = invoke("reject-rehashed-content-old-plan", "render", m=altered_path, p=plan_path)
    checks["refuse-rehashed-content-old-plan"] = not okay
    okay, altered_plan, _ = invoke("content-plan", "plan", m=altered_path)
    okay, _, directory = invoke("content-render", "render", m=altered_path, p=altered_plan)
    checks["authorized-changed-input-changes-pixels"] = okay and sha(directory / "output.tiff") != outputs["full"]["info"]["file_sha256"]
    frame.write_bytes(before)
    checks["copied-input-restored"] = sha(frame) == original["frames"][4]["sha256"]
    checks["build-record-unchanged"] = sha(build) == build_sha
    checks = {k: bool(v) for k, v in checks.items()}
    result = dict(schema="m194b-independent-consumer-v1", pass_=all(checks.values()),
                  checks=checks, build_sha256=build_sha, work=str(work), commands=commands,
                  max_landmark_error_native=max_landmark_error,
                  outputs={k: v["info"] for k, v in outputs.items()}, error=error,
                  scope="private synthetic adapter; changed trusted fixtures are controls, not admitted baseline")
    write(HERE / "independent-consumer.json", result)
    print(json.dumps(dict(pass_=result["pass_"], checks=checks, errors=error)))
    if not result["pass_"]: raise SystemExit(1)


if __name__ == "__main__":
    main()
