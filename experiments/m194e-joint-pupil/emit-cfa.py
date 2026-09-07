"""Noiseless CFA emission from externally commissioned, exact scalar inputs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import traceback

import numpy as np

from model import file_ref, sensor_record, write_json
import schema


def convert_cfa(scalar, sensor=None):
    """Return expected CFA electrons and tightly packed little-endian u16 DN."""
    sensor = sensor_record() if sensor is None else sensor
    schema.same_shape_value(sensor, sensor_record(), "conversion sensor")
    if not isinstance(scalar, np.ndarray) or scalar.dtype.str != "<f8" or scalar.shape != (48, 64):
        raise ValueError("conversion requires the fixed48x64 float64 scalar array")
    if not np.isfinite(scalar).all() or np.any(scalar < 0):
        raise ValueError("finite nonnegative scalar electrons required")
    expected = np.array(scalar, dtype="<f8", order="C", copy=True)
    expected[0::2, 0::2] *= sensor["channel_factors"][0]
    expected[1::2, 1::2] *= sensor["channel_factors"][2]
    # The two operations are deliberately separate. No WB, noise or clipping.
    dn = expected * sensor["gain_dn_per_e"]
    dn += sensor["black"]
    if not np.isfinite(dn).all() or np.any(dn < sensor["black"]) or np.any(dn >= sensor["white"]):
        raise ValueError("unquantized DN must be within [black,white)")
    rounded = np.rint(dn)
    if np.any(rounded >= sensor["white"]):
        raise ValueError("ties-to-even code reaches excluded white rail")
    return expected, rounded.astype("<u2")


def read_bound_bytes(ref, root, *, array=False):
    path = schema.validate_ref(ref, root, array)
    data = path.read_bytes()
    if len(data) != ref["bytes"] or hashlib.sha256(data).hexdigest() != ref["sha256"]:
        raise ValueError("bytes changed while reading admitted input")
    return data


def write_new(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)


def array_ref(path, root, dtype):
    return dict(**file_ref(path, root), dtype=dtype, shape=[48, 64])


def copy_input_bytes(source_path, input_root, output, data):
    target = output / "input" / Path(source_path).relative_to(input_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError("two admitted references collide with different bytes")
    else:
        write_new(target, data)
    return target


def emit_cfa_bundle(bundle_path, commission_path, trusted_sha256, output):
    bundle_path, commission_path, output = (Path(p).resolve() for p in (bundle_path, commission_path, output))
    bundle, commission = schema.validate_commission(bundle_path, commission_path, trusted_sha256)
    # Receipt references use the already declared repository source/evidence base.
    input_ref = file_ref(bundle_path, schema.REPOSITORY)
    gate_ref = file_ref(commission_path, schema.REPOSITORY)
    before_sources = schema.source_bindings()
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    run = dict(schema="m194e-emission-run-v1", status="running", command=list(sys.argv),
               started_utc=started, python=sys.version, numpy=np.__version__,
               input_bundle=input_ref, float_commission=gate_ref, trusted_float_sha256=trusted_sha256,
               sources_before=before_sources, frames=[])
    write_json(output / "emission-run.json", run)
    try:
        for frame in bundle["frames"]:
            index = frame["index"]
            scalar_ref = frame["expected_scalar"]
            # A verified byte buffer is the conversion input and the archived copy:
            # a later source-file change cannot alter the array being converted.
            scalar_bytes = read_bound_bytes(scalar_ref, bundle_path.parent, array=True)
            stream = io.BytesIO(scalar_bytes)
            scalar = np.load(stream, allow_pickle=False)
            if stream.tell() != len(scalar_bytes):
                raise ValueError("scalar NPY has trailing payload")
            expected, codes = convert_cfa(scalar, bundle["sensor"])
            scalar_path = copy_input_bytes(schema.relative_path(scalar_ref["path"], bundle_path.parent),
                                           bundle_path.parent, output, scalar_bytes)

            numerical_ref = frame["numerical_receipt"]
            numerical_path = schema.relative_path(numerical_ref["path"], bundle_path.parent)
            numerical_bytes = read_bound_bytes(numerical_ref, bundle_path.parent)
            numerical = schema.strict_json_loads(numerical_bytes.decode("utf-8"))
            indicator_ref = numerical["error_indicator"]
            indicator_bytes = read_bound_bytes(indicator_ref, numerical_path.parent, array=True)
            copy_input_bytes(schema.relative_path(indicator_ref["path"], numerical_path.parent),
                             bundle_path.parent, output, indicator_bytes)
            copied_numerical = copy_input_bytes(numerical_path, bundle_path.parent, output, numerical_bytes)

            expected_path = output / f"frame-{index:02d}-expected-cfa.npy"
            code_path = output / f"frame-{index:02d}.cfa"
            with expected_path.open("xb") as dest:
                np.save(dest, expected, allow_pickle=False)
            write_new(code_path, codes.tobytes(order="C"))
            record = {k: frame[k] for k in ("index", "inverse_focus", "K", "forward_similarity")}
            record.update(expected_scalar=array_ref(scalar_path, output, "<f8"),
                          numerical_receipt=file_ref(copied_numerical, output),
                          expected_cfa=array_ref(expected_path, output, "<f8"),
                          cfa=array_ref(code_path, output, "<u2"))
            run["frames"].append(record)
            write_json(output / "emission-run.json", run)
            del scalar_bytes, stream, scalar, expected, codes, indicator_bytes

        # No complete manifest is published unless all admitted evidence still
        # binds and every output sample has been formed from those admitted bytes.
        after_bundle, after_commission = schema.validate_commission(bundle_path, commission_path, trusted_sha256)
        if after_bundle != bundle or after_commission != commission or schema.source_bindings() != before_sources:
            raise ValueError("source/authority changed during emission")
        run.update(status="CFA_COMPLETE_AWAITING_INDEPENDENT_REVIEW", sources_after=schema.source_bindings(),
                   ended_utc=datetime.now(timezone.utc).isoformat())
        write_json(output / "emission-run.json", run)
        manifest = {k: bundle[k] for k in ("sensor", "scene", "ray_model", "numerical_contract")}
        manifest.update(schema="m194e-joint-pupil-v1", status="float-commissioned-cfa-unverified",
                        producer=dict(bundle["producer"], emission_receipt=file_ref(output / "emission-run.json", output)),
                        frames=run["frames"])
        write_new(output / "manifest.json", (json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
        return output / "manifest.json"
    except Exception as exc:
        run.update(status="EMISSION_REFUSED", error=repr(exc), traceback=traceback.format_exc(),
                   ended_utc=datetime.now(timezone.utc).isoformat())
        write_json(output / "emission-run.json", run)
        raise


def author_conversion_controls(check, refuses):
    scalar = np.full((48, 64), 20.0, dtype="<f8")
    expected, codes = convert_cfa(scalar)
    check("cfa-four-parity-dn", codes[:2, :2].tolist() == [[516, 517], [517, 515]])
    check("cfa-four-parity-electrons", expected[:2, :2].tolist() == [[15.0, 20.0], [20.0, 12.0]])
    for electrons, expected_code in ((2.0, 512), (6.0, 514), (10.0, 514)):
        scalar[0, 1] = electrons
        _, rounded = convert_cfa(scalar)
        check(f"green-tie-{electrons}", int(rounded[0, 1]) == expected_code)
    for value in (-1.0, float("nan"), float("inf"), 59392.0, 59391.0):
        bad = np.full((48, 64), value, dtype="<f8")
        refuses(f"cfa-refuse-{value}", lambda bad=bad: convert_cfa(bad))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--float-commission", type=Path, required=True)
    parser.add_argument("--trusted-float-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = emit_cfa_bundle(args.bundle, args.float_commission, args.trusted_float_sha256, args.output)
        print(result)
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
