"""Run every fixed float arm. This author run cannot commission itself."""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "2"

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil
import sys
import traceback

import numpy as np

from model import RAY_MODEL, file_ref, primary_frames, primary_scene, scene_record, sensor_record, write_json
from render import Meter, integrator_for, render_frame
import schema


def prefix_frame(record, prefix):
    # Child references in a numerical receipt remain relative to that receipt.
    result = dict(record)
    for field in ("expected_scalar", "numerical_receipt"):
        result[field] = dict(record[field], path=f"{prefix}/{record[field]['path']}")
    return result


def run(output, controls):
    output = output.resolve()
    controls = controls.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    sources = schema.source_bindings()
    record = dict(schema="m194e-author-float-run-v1", status="running", command=sys.argv, started_utc=started,
                  environment=dict(python=sys.version, numpy=np.__version__, platform=platform.platform(), numerical_threads=2),
                  sources_before=sources, arms={}, comparisons={})
    write_json(output / "result.json", record)
    snapshot = output / "source"
    snapshot.mkdir()
    for name in schema.AUTHOR_SOURCES + schema.DESIGNS:
        shutil.copyfile(schema.HERE / name, snapshot / name)
    try:
        control = schema.json_read(controls)
        if control.get("schema") != "m194e-author-controls-v1" or control.get("status") != "PASS" or not control.get("checks") or any(c.get("pass_") is not True for c in control["checks"]):
            raise ValueError("complete passing author controls required before intended arrays")
        for name in schema.AUTHOR_SOURCES:
            key = (schema.HERE / name).relative_to(schema.REPOSITORY).as_posix()
            for side in ("sources_before", "sources_after"):
                if control.get(side, {}).get(name) != sources[key]["sha256"]:
                    raise ValueError("controls do not bind current source: " + name)
        scene, sensor = primary_scene(), sensor_record()
        for arm in schema.ARMS:
            config = integrator_for(arm)
            meter = Meter(config, "count")
            records = []
            record["arms"][arm] = dict(status="running", frames=records)
            write_json(output / "result.json", record)
            for frame in primary_frames():
                print(json.dumps(dict(event="frame-start", arm=arm, index=frame.index, inverse_focus=frame.inverse_focus)), flush=True)
                produced = render_frame(scene, frame, sensor, config, output / arm, meter=meter, tile=8)
                records.append(prefix_frame(produced, arm))
                write_json(output / "result.json", record)
                print(json.dumps(dict(event="frame-complete", arm=arm, index=frame.index, work=meter.receipt())), flush=True)
            record["arms"][arm]["status"] = "complete"
            record["arms"][arm]["work"] = meter.receipt()
            write_json(output / "result.json", record)
        # Only one primary/refinement pair is loaded at once for readout; the
        # renderer itself retained exactly one scalar frame during production.
        for arm in ("angle-refined", "cell-refined"):
            rows = []
            for i in range(5):
                primary = np.load(output / "primary" / f"frame-{i:02d}-scalar.npy", allow_pickle=False)
                other = np.load(output / arm / f"frame-{i:02d}-scalar.npy", allow_pickle=False)
                delta = other - primary
                rows.append(dict(index=i, max_abs_e=float(np.abs(delta).max()), rms_e=float(np.sqrt(np.mean(delta * delta)))))
                del primary, other, delta
            record["comparisons"][arm] = rows
        if any(r["max_abs_e"] > .001 for rows in record["comparisons"].values() for r in rows):
            raise ValueError("UNCOMMISSIONED_NUMERICS: author refinement exceeds .001e")
        if schema.source_bindings() != sources:
            raise ValueError("source changed during float run")
        bundle = dict(schema="m194e-float-bundle-v1", status="uncommissioned",
                      producer=dict(source_base="repository", sources=sources, designs=schema.design_bindings(), command=sys.argv,
                                    author_controls=file_ref(controls, schema.REPOSITORY)),
                      sensor=sensor, scene=scene_record(scene), ray_model=RAY_MODEL, numerical_contract=schema.numerical_contract(),
                      frames=record["arms"]["primary"]["frames"],
                      refinements={a: record["arms"][a]["frames"] for a in ("angle-refined", "cell-refined")})
        write_json(output / "float-bundle.json", bundle)
        schema.validate_bundle(output / "float-bundle.json")
        record["bundle"] = file_ref(output / "float-bundle.json", output)
        record["status"] = "FLOATS_COMPLETE_UNCOMMISSIONED"
    except Exception as exc:
        record["status"] = "UNCOMMISSIONED_NUMERICS"
        record["error"] = repr(exc)
        record["traceback"] = traceback.format_exc()
        traceback.print_exc()
    record["sources_after"] = schema.source_bindings()
    record["ended_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "result.json", record)
    print(json.dumps(dict(status=record["status"], output=str(output))), flush=True)
    return 0 if record["status"] == "FLOATS_COMPLETE_UNCOMMISSIONED" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--controls", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.controls))
