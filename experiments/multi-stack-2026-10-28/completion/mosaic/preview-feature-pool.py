"""Search shared detail across focus positions without a stacked-pixel image.

Only embedded JPEG feature descriptors and direct pair measurements are used.
This is a candidate finder, never a production alignment or sharpness measure.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import time

spec = importlib.util.spec_from_file_location("overlap", Path(__file__).with_name("preview-overlap.py"))
overlap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlap)
cv2, np = overlap.cv2, overlap.np


def load(receipt):
    data = Path(receipt["preview"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == receipt["preview_sha256"]
    gray = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
    scale = receipt["analysis_scale"]
    if scale != 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    value = overlap.describe(gray)
    value["receipt"] = receipt
    return value


def normalize(frames):
    n = len(frames)
    edges = []
    for i, j in itertools.combinations(range(n), 2):
        a, b = frames[i], frames[j]
        ab = overlap.ratio_matches(a["descriptors"], b["descriptors"])
        ba = overlap.ratio_matches(b["descriptors"], a["descriptors"])
        ids = [(a, b) for a, b in ab.items() if ba.get(b) == a]
        if len(ids) < 8:
            continue
        p = a["points"][[a for a, _ in ids]]
        q = b["points"][[b for _, b in ids]]
        cv2.setRNGSeed(310528)
        transform, inliers = cv2.estimateAffinePartial2D(p, q, method=cv2.RANSAC,
            ransacReprojThreshold=2., maxIters=2000, confidence=.999, refineIters=10)
        if transform is None:
            continue
        inliers = inliers.ravel().astype(bool)
        scale = np.hypot(transform[0, 0], transform[1, 0])
        angle = np.arctan2(transform[1, 0], transform[0, 0])
        if sum(inliers) < 8 or not .85 < scale < 1.18 or abs(angle) > .08:
            continue
        p, q = p[inliers], q[inliers]
        # A bounded spatial subsample prevents one richly textured focus slice
        # dominating the global fit simply because it supplied more descriptors.
        if len(p) > 60:
            keep = np.linspace(0, len(p) - 1, 60).astype(int)
            p, q = p[keep], q[keep]
        edges.append((i, j, p, q))
    adjacency = [set() for _ in frames]
    for i, j, _, _ in edges:
        adjacency[i].add(j); adjacency[j].add(i)
    reference = max(range(n), key=lambda i: (len(adjacency[i]), -abs(i - n // 2)))
    connected = {reference}
    while True:
        expanded = connected | set().union(*(adjacency[i] for i in connected))
        if expanded == connected:
            break
        connected = expanded
    unknown = {frame: 4 * i for i, frame in enumerate(sorted(connected - {reference}))}
    if not unknown:
        raise RuntimeError("preview focus graph disconnected from every other source")
    width, height = frames[reference]["shape"][1], frames[reference]["shape"][0]
    center = np.array([width / 2, height / 2])
    matrix, rhs = [], []
    used_edges = []
    for i, j, p, q in edges:
        if i not in connected or j not in connected:
            continue
        used_edges.append((i, j))
        for pa, pb in zip(p - center, q - center):
            for axis in [0, 1]:
                row = np.zeros(len(unknown) * 4)
                target = 0.
                for frame, point, sign in ((i, pa, 1), (j, pb, -1)):
                    if frame == reference:
                        target -= sign * point[axis]
                    else:
                        start = unknown[frame]
                        coeff = [point[0], -point[1], 1, 0] if axis == 0 else [point[1], point[0], 0, 1]
                        row[start:start + 4] = sign * np.array(coeff)
                matrix.append(row); rhs.append(target)
    matrix, rhs = np.array(matrix), np.array(rhs)
    weights = np.ones(len(rhs))
    for _ in range(6):
        parameters, _, rank, _ = np.linalg.lstsq(matrix * np.sqrt(weights[:, None]), rhs * np.sqrt(weights), rcond=None)
        assert rank == len(unknown) * 4
        residual = matrix @ parameters - rhs
        pair_error = np.hypot(residual[0::2], residual[1::2])
        weights = np.repeat(np.minimum(1., 2. / np.maximum(pair_error, 1e-6)), 2)
    transforms = {}
    for frame in connected:
        values = np.array([1, 0, 0, 0]) if frame == reference else parameters[unknown[frame]:unknown[frame] + 4]
        a, b, tx, ty = values
        transforms[frame] = np.array([[a, -b, tx + center[0] - a * center[0] + b * center[1]],
                                      [b, a, ty + center[1] - b * center[0] - a * center[1]]])
    return transforms, {"reference_position": reference, "placed_positions": sorted(connected),
        "unplaced_positions": sorted(set(range(n)) - connected), "direct_edges": len(used_edges),
        "cycle_rank": len(used_edges) - len(connected) + 1,
        "fit_p90_preview_px": float(np.quantile(pair_error, .9)),
        "transforms": {str(k): v.tolist() for k, v in transforms.items()}}


def pool(frames, transforms):
    observations = []
    for frame, transform in transforms.items():
        value = frames[frame]
        points = cv2.transform(value["points"][None], transform)[0]
        for i, point in enumerate(points):
            observations.append((float(value["responses"][i]), point, value["descriptors"][i],
                {"frame_position": frame, "acquisition_index": value["receipt"]["acquisition_index"],
                 "source_path": value["receipt"]["path"], "source_preview_point": value["points"][i].tolist()}))
    observations.sort(key=lambda row: row[0], reverse=True)
    bins = {}
    selected = []
    for row in observations:
        p = row[1]
        cell = tuple(np.floor(p / 6).astype(int))
        nearby = [q for x in range(cell[0] - 1, cell[0] + 2) for y in range(cell[1] - 1, cell[1] + 2)
                  for q in bins.get((x, y), [])]
        if any(np.linalg.norm(p - q) < 6. for q in nearby):
            continue
        selected.append(row)
        bins.setdefault(cell, []).append(p)
    result = {"gray": frames[len(frames) // 2]["gray"], "shape": frames[0]["shape"],
              "points": np.array([r[1] for r in selected], np.float32),
              "descriptors": np.array([r[2] for r in selected], np.float32),
              "witnesses": [r[3] for r in selected]}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    args.out.mkdir(parents=True, exist_ok=True)
    source = json.loads(args.input.read_text())
    report = {"schema": "strehl.preview-feature-pool.v1", "command": sys.argv,
              "source_report_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "worker_threads": 4, "normalization": {}, "matches": []}
    overlap.controls()
    report["candidate_controls"] = "passed exact same controls as preview-overlap.py"
    groups = {}
    for name in sorted(set(r["group"] for r in source["sources"])):
        frames = [load(r) for r in source["sources"] if r["group"] == name]
        transforms, receipt = normalize(frames)
        groups[name] = pool(frames, transforms)
        receipt["pooled_features"] = len(groups[name]["points"])
        report["normalization"][name] = receipt
        print(name, "placed", len(transforms), "pooled", receipt["pooled_features"],
              "p90", receipt["fit_p90_preview_px"], flush=True)
    for a, b in itertools.combinations(groups, 2):
        if a.split("-")[0] != b.split("-")[0]:
            continue
        result, points = overlap.compare(groups[a], groups[b])
        ab = overlap.ratio_matches(groups[a]["descriptors"], groups[b]["descriptors"])
        ba = overlap.ratio_matches(groups[b]["descriptors"], groups[a]["descriptors"])
        result["witnesses"] = [{"a": groups[a]["witnesses"][i], "b": groups[b]["witnesses"][j],
            "point_a": groups[a]["points"][i].tolist(), "point_b": groups[b]["points"][j].tolist()}
            for i, j in ab.items() if ba.get(j) == i]
        result.update(pass_a=a, pass_b=b)
        report["matches"].append(result)
        overlap.visualize(groups[a], groups[b], points, args.out / f"pool-{a}--{b}.png")
        print(a, b, "matches", result["reciprocal_matches"], "train", result["training_inliers"],
            "holdp90", result.get("holdout_p90_px"), "screen", result["global_screen"], flush=True)
    report["seconds_nonbenchmark"] = time.time() - started
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
