"""Actual tile-boundary and optional-hook byte controls, not float authority."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent
EXPECTED = {"model.py": "a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8",
            "render.py": "ef52c45d28ec2dda5aa897cfd57dacc4b4a3e300d3a581c35f305c76e2dd03f8"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194e-independent-observer-v1", status="RUNNING", command=sys.argv, sources={}, arms=[], checks=[])
    try:
        for name in (*EXPECTED, "independent-observer-check.py", "independent-observer-preregister.md"):
            if name in EXPECTED and sha(HERE / name) != EXPECTED[name]:
                raise ValueError("final externally bound author source differs")
            shutil.copyfile(HERE / name, args.output / name)
            result["sources"][name] = sha(HERE / name)
        sys.path.insert(0, str(args.output.resolve()))
        import model as m
        import render as r

        def check(name, passed):
            result["checks"].append(dict(name=name, passed=bool(passed)))
            if not passed:
                raise ValueError("control failed: " + name)

        scene = m.Scene(m.Field(12000, waves=(m.Wave(900, (.073, .019), .41),)),
                        m.Field(10000, waves=(m.Wave(700, (-.031, .087), 1.13),)),
                        (1.25, 2.5), (12 / 13, 5 / 13), 9.3)
        frame = m.Frame(0, .53, 11.)
        sensor = dict(width=19, height=11)
        config = r.Integrator()
        real_cell = r.render_cell
        traces = {}
        for name, observer, tile, tracing, changed in (
                ("native-off-8", "off", 8, False, False),
                ("native-count-8", "count", 8, False, False),
                ("native-placebo-8", "placebo", 8, False, False),
                ("native-count-16", "count", 16, False, False),
                ("trace-count-8", "count", 8, True, False),
                ("trace-count-16", "count", 16, True, False),
                ("changed-foreground", "count", 8, False, True)):
            trace = []

            def traced_cell(scene_arg, frame_arg, xy, *positional, **keywords):
                trace.append(tuple(xy))
                return real_cell(scene_arg, frame_arg, xy, *positional, **keywords)

            r.render_cell = traced_cell if tracing else real_cell
            actual_scene = replace(scene, foreground=replace(scene.foreground, constant=12017)) if changed else scene
            meter = r.Meter(config, observer)
            record = r.render_frame(actual_scene, frame, sensor, config, args.output / name, meter=meter, tile=tile)
            receipt = json.loads((args.output / name / record["numerical_receipt"]["path"]).read_text())
            item = dict(name=name, observer=observer, tile=tile, record=record, indicator=receipt["error_indicator"], work=meter.receipt())
            result["arms"].append(item)
            traces[name] = trace
        r.render_cell = real_cell
        nulls = result["arms"][:6]
        check("all-native-and-traced-scalar-bytes-identical", len({a["record"]["expected_scalar"]["sha256"] for a in nulls}) == 1)
        check("all-native-and-traced-indicator-bytes-identical", len({a["indicator"]["sha256"] for a in nulls}) == 1)
        for a in nulls:
            w = a["work"]
            check(a["name"] + "-optional-hook-powered", (w["optional_hook_calls"] == 0) == (a["observer"] == "off"))
            check(a["name"] + "-count-only-events", (w["observer_events"] > 0) == (a["observer"] == "count"))
            check(a["name"] + "-one-scalar-frame", w["peak_live_scalar_frames"] == 1)
        cells = {(x, y) for y in range(11) for x in range(19)}
        for name in ("trace-count-8", "trace-count-16"):
            check(name + "-each-cell-exactly-once", len(traces[name]) == 209 and set(traces[name]) == cells)
        check("actual-traversal-orders-differ", traces["trace-count-8"] != traces["trace-count-16"])
        result["actual_traversals"] = {k: v for k, v in traces.items() if v}
        baseline = np.load(args.output / "native-count-8/frame-00-scalar.npy", allow_pickle=False)
        changed = np.load(args.output / "changed-foreground/frame-00-scalar.npy", allow_pickle=False)
        check("null-output-has-spatial-variation", np.ptp(baseline) > 100)
        check("changed-source-is-live", np.max(np.abs(changed - baseline)) > 1 and result["arms"][-1]["record"]["expected_scalar"]["sha256"] != nulls[0]["record"]["expected_scalar"]["sha256"])
        result["maximum_live_change_e"] = float(np.max(np.abs(changed - baseline)))
        result["status"] = "PASS_OBSERVER_TRAVERSAL_ONLY"
    except Exception as exc:
        result["status"] = "UNCOMMISSIONED_OBSERVER"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    result["source_unchanged"] = all(sha(HERE / name) == digest for name, digest in result["sources"].items())
    if not result["source_unchanged"]:
        result["status"] = "UNCOMMISSIONED_OBSERVER"
    (args.output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps(dict(status=result["status"], checks=len(result["checks"]), error=result.get("error"))))
    return 0 if result["status"] == "PASS_OBSERVER_TRAVERSAL_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
