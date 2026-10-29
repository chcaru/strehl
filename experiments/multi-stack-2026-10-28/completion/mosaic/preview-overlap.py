"""Bounded embedded-JPEG overlap discovery; never decodes RAW pixel arrays."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import time

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "4"
import cv2
import numpy as np

cv2.setNumThreads(4)
cv2.setRNGSeed(310528)
EXIFTOOL = Path(r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe")
GROUPS = {
    "grid-1-sw1": ["b05"], "grid-1-sw10": ["b06"],
    "grid-1-sw4": ["b07"], "grid-2-sw10": ["b08"],
    "grid-2-sw4": ["b09"], "marigold-2": ["b31", "b32"],
    "marigold-3": ["b33", "b34"], "marigold-offcenter": ["b35", "b36"],
    "peacock-100": ["b37"], "peacock-102": ["b38"],
}
CFG = dict(max_side=1280, features=3000, ratio=.70, ransac_px=3.,
           training_inliers=25, holdout_matches=10, occupied_cells=4,
           hull_fraction=.02, holdout_p90_px=3., quantiles=5, threads=4,
           seed=310528, spatial_grid=[6, 4])


def describe(gray):
    sift = cv2.SIFT_create(nfeatures=CFG["features"], contrastThreshold=.02)
    keypoints, descriptors = sift.detectAndCompute(gray, None)
    points = np.array([kp.pt for kp in keypoints], np.float32).reshape(-1, 2)
    return {"gray": gray, "points": points, "descriptors": descriptors,
            "responses": np.array([kp.response for kp in keypoints], np.float32),
            "shape": gray.shape}


def ratio_matches(a, b):
    if a is None or b is None or len(a) < 2 or len(b) < 2:
        return {}
    bf = cv2.BFMatcher(cv2.NORM_L2)
    return {first.queryIdx: first.trainIdx for first, second in bf.knnMatch(a, b, k=2)
            if first.distance < CFG["ratio"] * second.distance}


def cells(points, shape):
    h, w = shape
    gx = np.clip((points[:, 0] * 6 / w).astype(int), 0, 5)
    gy = np.clip((points[:, 1] * 4 / h).astype(int), 0, 3)
    return gx, gy


def hull_fraction(points, shape):
    return float(cv2.contourArea(cv2.convexHull(points))) / np.prod(shape) if len(points) >= 3 else 0.


def compare(a, b):
    ab = ratio_matches(a["descriptors"], b["descriptors"])
    ba = ratio_matches(b["descriptors"], a["descriptors"])
    ids = [(i, j) for i, j in ab.items() if ba.get(j) == i]
    p = a["points"][[i for i, _ in ids]]
    q = b["points"][[j for _, j in ids]]
    result = {"reciprocal_matches": len(ids), "global_screen": False,
              "training_inliers": 0, "holdout_count": 0}
    if len(ids) < 8:
        return result, (p, q, None)
    gx, gy = cells(p, a["shape"])
    hold = (gx + gy) % 3 == 0
    if sum(~hold) < 8:
        return result, (p, q, None)
    cv2.setRNGSeed(CFG["seed"])
    matrix, fitted = cv2.findHomography(p[~hold], q[~hold], cv2.RANSAC,
                                     CFG["ransac_px"], maxIters=4000, confidence=.999)
    if matrix is None or not np.isfinite(matrix).all():
        return result, (p, q, None)
    fitted = fitted.ravel().astype(bool)
    train_p, train_q = p[~hold][fitted], q[~hold][fitted]
    predicted = cv2.perspectiveTransform(p[None], matrix)[0]
    error = np.linalg.norm(predicted - q, axis=1)
    cx, cy = cells(train_p, a["shape"])
    hold_errors = error[hold]
    result.update(matrix_a_to_b=matrix.tolist(), training_inliers=int(sum(fitted)),
                  holdout_count=int(sum(hold)),
                  holdout_p50_px=float(np.median(hold_errors)) if len(hold_errors) else None,
                  holdout_p90_px=float(np.quantile(hold_errors, .9)) if len(hold_errors) else None,
                  training_p90_px=float(np.quantile(error[~hold][fitted], .9)),
                  hull_fraction_a=hull_fraction(train_p, a["shape"]),
                  hull_fraction_b=hull_fraction(train_q, b["shape"]),
                  occupied_cells=len(set(zip(cx.tolist(), cy.tolist()))),
                  all_residual_p90_px=float(np.quantile(error, .9)))
    result["global_screen"] = bool(
        result["training_inliers"] >= CFG["training_inliers"] and
        result["holdout_count"] >= CFG["holdout_matches"] and
        result["occupied_cells"] >= CFG["occupied_cells"] and
        min(result["hull_fraction_a"], result["hull_fraction_b"]) >= CFG["hull_fraction"] and
        result["holdout_p90_px"] <= CFG["holdout_p90_px"])
    return result, (p, q, error)


def texture(seed, shape=(480, 640)):
    rng = np.random.default_rng(seed)
    base = np.zeros(shape, np.float32)
    for sigma, weight in ((.7, 1), (2., 2), (6., 4), (14., 8)):
        base += cv2.GaussianBlur(rng.standard_normal(shape).astype(np.float32),
                                 (0, 0), sigma) * weight
    return np.uint8(np.clip((base - base.min()) / np.ptp(base) * 255, 0, 255))


def controls():
    source = texture(12)
    matrix = np.array([[1., 0, 81.25], [0, 1., -17.5]], np.float32)
    shifted = cv2.warpAffine(source, matrix, (640, 480))
    positive, _ = compare(describe(source), describe(shifted))
    assert positive["global_screen"], positive
    points = np.array([[[100., 100.], [300., 300.], [500., 250.]]], np.float32)
    recovered = cv2.perspectiveTransform(points, np.array(positive["matrix_a_to_b"]))
    planted = points + np.array([81.25, -17.5])
    positive["plant_max_error_px"] = float(np.max(np.linalg.norm(recovered - planted, axis=2)))
    assert positive["plant_max_error_px"] < .5, positive
    wrong, _ = compare(describe(source), describe(texture(97)))
    blank, _ = compare(describe(np.full((480, 640), 127, np.uint8)), describe(source))
    yy, xx = np.indices(source.shape)
    periodic = np.uint8(((xx // 24 + yy // 24) % 2) * 255)
    grid, _ = compare(describe(periodic), describe(np.roll(periodic, 24, axis=1)))
    assert not wrong["global_screen"] and not blank["global_screen"] and not grid["global_screen"]
    # Two large depth strata have contradictory translation; enough features exist
    # in both. This checks the held-out metric, not a preselected inlier subset.
    depth = shifted.copy()
    other = cv2.warpAffine(source, np.array([[1., 0, 104.25], [0, 1., -17.5]], np.float32), (640, 480))
    depth[:, 320:] = other[:, 320:]
    discontinuity, _ = compare(describe(source), describe(depth))
    assert discontinuity["reciprocal_matches"] > 100, discontinuity
    assert not discontinuity["global_screen"], discontinuity
    return {"translated": positive, "unrelated": wrong, "blank": blank,
            "periodic_alias": grid, "depth_discontinuity": discontinuity}


def extract(group, index, bracket, file, out):
    raw = Path(bracket["directory"]) / file["name"]
    stamp = raw.stat()
    assert stamp.st_size == file["bytes"] and stamp.st_mtime_ns == file["mtime_ns"], str(raw)
    jpg = out / "previews" / f"{group}-{index:04d}.jpg"
    jpg.parent.mkdir(parents=True, exist_ok=True)
    if not jpg.exists():
        decoded = subprocess.run([str(EXIFTOOL), "-b", "-PreviewImage", str(raw)],
                                 capture_output=True, check=True)
        assert decoded.stdout[:2] == b"\xff\xd8", str(raw)
        jpg.write_bytes(decoded.stdout)
    content = jpg.read_bytes()
    gray = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_GRAYSCALE)
    assert gray is not None
    scale = min(1., CFG["max_side"] / max(gray.shape))
    if scale != 1.:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    value = describe(gray)
    value["receipt"] = {"group": group, "acquisition_index": index, "path": str(raw),
                        "bytes": stamp.st_size, "mtime_ns": stamp.st_mtime_ns,
                        "preview_sha256": hashlib.sha256(content).hexdigest(),
                        "preview": str(jpg), "analysis_shape": list(gray.shape),
                        "analysis_scale": scale, "feature_count": len(value["points"])}
    assert raw.stat().st_mtime_ns == stamp.st_mtime_ns and raw.stat().st_size == stamp.st_size
    return value


def visualize(a, b, points, out):
    p, q, error = points
    h = max(a["gray"].shape[0], b["gray"].shape[0])
    w = a["gray"].shape[1]
    canvas = np.zeros((h, w + b["gray"].shape[1], 3), np.uint8)
    canvas[:a["gray"].shape[0], :w] = cv2.cvtColor(a["gray"], cv2.COLOR_GRAY2BGR)
    canvas[:b["gray"].shape[0], w:] = cv2.cvtColor(b["gray"], cv2.COLOR_GRAY2BGR)
    for i in np.linspace(0, len(p) - 1, min(80, len(p))).astype(int) if len(p) else []:
        color = (30, 230, 30) if error is not None and error[i] <= 3 else (30, 30, 230)
        cv2.line(canvas, tuple(p[i].astype(int)), tuple((q[i] + [w, 0]).astype(int)), color, 1)
    cv2.imwrite(str(out), canvas)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=Path("experiments/multi-stack-2026-10-28/corpus/inventory.json"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--quantiles", type=int, default=5)
    parser.add_argument("--families", nargs="+", default=["grid", "marigold", "peacock"])
    args = parser.parse_args()
    assert 3 <= args.quantiles <= 17
    assert set(args.families) <= {"grid", "marigold", "peacock"}
    CFG["quantiles"] = args.quantiles
    started = time.time()
    args.out.mkdir(parents=True, exist_ok=True)
    commissioned = controls()
    report = {"schema": "strehl.mosaic-preview-overlap.v1", "configuration": CFG,
              "controls": commissioned, "command": sys.argv,
              "versions": {"python": sys.version, "opencv": cv2.__version__, "numpy": np.__version__},
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "claim_scope": "Embedded-JPEG candidate discovery; no native placement or photographic quality claim."}
    (args.out / "controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Controls passed: translation, wrong pair, blank, periodic alias, depth discontinuity", flush=True)
    if args.controls_only:
        return
    brackets = {b["id"]: b for b in json.loads(args.inventory.read_text())["brackets"]}
    data = {}
    for name, ids in GROUPS.items():
        if name.split("-")[0] not in args.families:
            continue
        files = [(brackets[key], file) for key in ids for file in brackets[key]["files"]]
        chosen = sorted(set(np.linspace(0, len(files) - 1, CFG["quantiles"]).round().astype(int)))
        data[name] = [extract(name, int(i), *files[i], args.out) for i in chosen]
        print(name, "features", [len(v["points"]) for v in data[name]], flush=True)
    report["sources"] = [v["receipt"] for group in data.values() for v in group]
    report["pairs"] = []
    for name_a, name_b in itertools.combinations(data, 2):
        if name_a.split("-")[0] != name_b.split("-")[0]:
            continue
        comparisons = []
        for a, b in itertools.product(data[name_a], data[name_b]):
            result, points = compare(a, b)
            result.update(index_a=a["receipt"]["acquisition_index"], index_b=b["receipt"]["acquisition_index"])
            comparisons.append((result, a, b, points))
        comparisons.sort(key=lambda row: (row[0]["global_screen"], row[0]["training_inliers"]), reverse=True)
        best, a, b, points = comparisons[0]
        report["pairs"].append({"pass_a": name_a, "pass_b": name_b,
                                 "best": best, "comparisons": [r[0] for r in comparisons],
                                 "grid_ambiguity_requires_distinctive_witness": name_a.startswith("grid")})
        visualize(a, b, points, args.out / f"matches-{name_a}--{name_b}.png")
        print(name_a, name_b, "best", best["index_a"], best["index_b"],
              "matches", best["reciprocal_matches"], "inliers", best["training_inliers"],
              "holdp90", best.get("holdout_p90_px"), "screen", best["global_screen"], flush=True)
        report["seconds_nonbenchmark"] = time.time() - started
        (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
