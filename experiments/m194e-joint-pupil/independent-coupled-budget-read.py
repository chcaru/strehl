"""Read frozen full3 refusal and reconstruct its two complete frontiers, no render."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path, digest):
    if sha(path) != digest:
        raise ValueError("external binding differs: " + str(path))
    return json.loads(path.read_text())


def triangle_area(t):
    a, b, c = t
    return abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2


def child(t, bit):
    j = max(range(3), key=lambda k: math.dist(t[k], t[(k+1)%3]))
    a, b, c = t[j], t[(j+1)%3], t[(j+2)%3]
    mid = tuple((v+w)/2 for v, w in zip(a, b))
    return (a, mid, c) if bit == 0 else (mid, b, c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("refuse replacing prior evidence")
    result = dict(status="RUNNING", command=sys.orig_argv, executable=sys.executable, xoptions=sys._xoptions,
                  python=sys.version, numpy=np.__version__, source_sha256=sha(Path(__file__)), checks=[])
    def check(name, passed, **values):
        result["checks"].append(dict(name=name, passed=bool(passed), **values))
        if not passed:
            raise ValueError(name)
    try:
        run_path = HERE / "float-run-3/result.json"
        diagnostic_path = HERE / "cell-diagnosis-3/result.json"
        reference_path = HERE / "independent-reference-1/result.json"
        run = read(run_path, "38e691f130e830f9bfb2b21176049cbd98b15a2134b638a03ee8f6363566c89f")
        diagnostic = read(diagnostic_path, "49902496359b6976776bb765e2228b36409d1df2e20bd405a11d8ece1732093f")
        reference = read(reference_path, "8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc")
        check("author-source-design-unchanged", run["sources_before"] == run["sources_after"] and run["designs_before"] == run["designs_after"])
        check("diagnostic-source-unchanged", diagnostic["sources_before"] == diagnostic["sources_after"])
        check("diagnostic-not-admitted", diagnostic["status"] == "DIAGNOSTIC_ONLY_NO_ADMISSION" and diagnostic["frame"] == 2 and diagnostic["xy"] == [4, 0] and diagnostic["eligible"] == 0)
        for name, digest in diagnostic["sources_before"].items():
            scoped_name = "experiments/m194e-joint-pupil/" + name
            check("snapshot-source-" + name, sha(HERE / "float-run-3/source" / name) == digest and run["sources_before"][scoped_name]["sha256"] == digest)
        ref_record = next(v for v in reference["frames"] if v["arm"] == "refined" and v["index"] == 2)
        ref_file = reference_path.parent / ref_record["array"]["path"]
        check("frozen-reference-array", sha(ref_file) == ref_record["array"]["sha256"])
        ref_value = float(np.load(ref_file, allow_pickle=False)[0, 4])
        result["reference_value_e"] = ref_value
        corners = ((3.5, -.5), (4.5, -.5), (4.5, .5), (3.5, .5))
        roots = ((corners[0], corners[1], corners[2]), (corners[0], corners[2], corners[3]))
        result["frontiers"] = {}
        for stage, depth in (("initial", 0), ("terminal", 6)):
            leaves = diagnostic[stage + "_leaves"]
            paths = [tuple(v["path"]) for v in leaves]
            expected_paths = {(root, *bits) for root in range(2) for bits in itertools.product((0, 1), repeat=depth)}
            check(stage + "-complete-depth-frontier", len(paths) == len(set(paths)) and set(paths) == expected_paths)
            for v in leaves:
                path = tuple(v["path"])
                tri = roots[path[0]]
                for bit in path[1:]:
                    tri = child(tri, bit)
                if tuple(map(tuple, v["triangle"])) != tri or v["area"] != triangle_area(tri) or v["depth"] != depth:
                    raise ValueError(stage + "-incorrect-partition-at-" + str(path))
                values = (v["low_e"], v["high_e"], v["pupil_low_e"], v["pupil_high_e"], v["indicator_e"])
                if not all(math.isfinite(x) for x in values) or min(values[2:]) < 0:
                    raise ValueError("invalid leaf numerical terms")
                delta = abs(v["high_e"] - v["low_e"])
                if delta != v["delta_e"] or delta + v["pupil_low_e"] + v["pupil_high_e"] != v["indicator_e"]:
                    raise ValueError("leaf term mismatch")
            check(stage + "-every-leaf-geometry-and-terms", True, leaves=len(leaves))
            ordered = sorted(leaves, key=lambda v: tuple(v["path"]))
            totals = dict(area=math.fsum(v["area"] for v in ordered), value=math.fsum(v["high_e"] for v in ordered),
                          cell_delta=math.fsum(abs(v["high_e"]-v["low_e"]) for v in ordered),
                          sum_low_pupil_e=math.fsum(v["pupil_low_e"] for v in ordered), pupil_error=math.fsum(v["pupil_high_e"] for v in ordered),
                          cell_error=math.fsum(abs(v["high_e"]-v["low_e"])+v["pupil_low_e"]+v["pupil_high_e"] for v in ordered))
            totals["signed_truth_error_e"] = totals["value"]-ref_value
            check(stage + "-all-reported-sums", totals == diagnostic[stage + "_sums"], totals=totals)
            check(stage + "-cell-fails-pupil-passes", totals["cell_error"] > .0001875 and totals["pupil_error"] < .00025)
            check(stage + "-pupil-terms-alone-exceed-cell-bar", totals["sum_low_pupil_e"] + totals["pupil_error"] > .0001875 and totals["cell_delta"] < 1e-10)
            result["frontiers"][stage] = totals
        result["inputs"] = {str(p.relative_to(HERE)): sha(p) for p in (run_path, diagnostic_path, reference_path)}
        result["status"] = "DIAGNOSTIC_VERIFIED_NO_ADMISSION"
    except Exception as exc:
        result["status"] = "DIAGNOSTIC_INVALID"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps(dict(status=result["status"], checks=len(result["checks"]), error=result.get("error"))))
    return 0 if result["status"] == "DIAGNOSTIC_VERIFIED_NO_ADMISSION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
