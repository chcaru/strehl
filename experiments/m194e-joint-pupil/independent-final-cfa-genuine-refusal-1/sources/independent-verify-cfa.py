"""Verify five emitted CFA files against external float and manifest authority.

Exact conversion and approximate optical-reference discrepancy are separate.
The private fixture entry point cannot issue a genuine CFA commission.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import schema as S

PINS = {
    "schema.py": "0bcc546634a748ee31fbd5095b6aae3a1eab18899a557dbed8aeeb8af102a82c",
    "independent-cfa-oracle.py": "1b23d656481752fc3c34384c489fc6556e78a74925d8cd717f4faa350040d48a",
    "independent-emission-api-controls.py": "8231589e6e7d9ae9c16411ebe22675da794b60fc5755d8a0264e8a38164df58e",
}
REFERENCE_SHA = "8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc"
API_RESULT = HERE / "independent-emission-api-3/result.json"
API_RESULT_SHA = "d37270e2a3f1b990a69607e122b2c95beaa33238c0a1a6b77c721406e46e53f2"
ARMS = ("primary", "angle-refined", "cell-refined")


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


for _name, _hash in PINS.items():
    if sha(HERE / _name) != _hash:
        raise ValueError("independent commissioned dependency changed: " + _name)
O = module("m194e_final_cfa_oracle", "independent-cfa-oracle.py")
A = module("m194e_final_cfa_lineage", "independent-emission-api-controls.py")


def need(value, message):
    if not value:
        raise ValueError(message)


def keys(value, names, message):
    need(type(value) is dict and set(value) == set(names), message)


def digest(value):
    need(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None, "lowercase64-character digest required")


def json_read(path):
    return S.strict_json_loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def source_state():
    names = set(S.AUTHOR_SOURCES + S.DESIGNS + tuple(PINS) + (Path(__file__).name, "independent-emission-design.md"))
    return {name: sha(HERE / name) for name in sorted(names)}


class Reads:
    """Small per-file before/after ledger, not an experiment authentication layer."""

    def __init__(self):
        self.observed = {}

    def remember(self, path):
        path = Path(path).resolve()
        value = dict(sha256=sha(path), bytes=path.stat().st_size)
        if str(path) in self.observed:
            need(self.observed[str(path)] == value, "bound file changed between reads")
        self.observed[str(path)] = value
        return path

    def bound(self, ref, root, array=False):
        keys(ref, ("path", "sha256", "bytes", "dtype", "shape") if array else ("path", "sha256", "bytes"), "closed file reference required")
        digest(ref["sha256"])
        need(type(ref["bytes"]) is int and ref["bytes"] >= 0, "integer length required")
        path = S.relative_path(ref["path"], root)
        self.remember(path)
        need(self.observed[str(path)]["sha256"] == ref["sha256"] and self.observed[str(path)]["bytes"] == ref["bytes"], "actual length/hash differs")
        if array:
            need(ref["dtype"] in ("<f8", "<u2") and ref["shape"] == [48, 64]
                 and all(type(d) is int for d in ref["shape"]), "fixed actual array interpretation required")
        return path

    def external(self, path, trusted):
        digest(trusted)
        path = self.remember(path)
        need(self.observed[str(path)]["sha256"] == trusted, "external digest differs")
        return json_read(path)

    def float_array(self, ref, root, *, array=False):
        path = self.bound(ref, root, array)
        need(path.stat().st_size <= 48 * 64 * 8 + 4096, "bounded float file required before allocation")
        value = O.read_float(path)
        need(value.flags.c_contiguous, "row-major float required")
        return value

    def finish(self):
        need(all(Path(p).stat().st_size == v["bytes"] and sha(p) == v["sha256"] for p, v in self.observed.items()), "input bytes changed during verification")


def reference_diagnostic(actual, reference, codes):
    """Same registered scalar bars; rounding differences are not optical error."""
    delta = actual - reference
    maximum = float(np.abs(delta).max())
    rms = float(np.sqrt(np.mean(delta * delta)))
    need(maximum <= .004 and rms <= .0008, "admitted scalar/reference discrepancy exceeds existing bars")
    _, reference_codes, _ = O.convert(reference)
    mismatches = codes != reference_codes
    rows = []
    for channel in range(3):
        positions = [(x, y) for y in range(48) for x in range(64) if O.channel(x, y) == channel]
        allowance = .004 * .25 * O.FACTORS[channel]
        near = different = outside = 0
        max_dn_error = 0.0
        min_margin = math.inf
        for x, y in positions:
            dn = 512. + .25 * (float(actual[y, x]) * O.FACTORS[channel])
            ref_dn = 512. + .25 * (float(reference[y, x]) * O.FACTORS[channel])
            margin = abs(dn - math.floor(dn) - .5)
            # Only a few floating-operation ulps; never the model tolerance again.
            ulp_guard = 8 * math.ulp(max(abs(dn), abs(ref_dn), 1.))
            near += int(margin <= allowance + ulp_guard)
            different += int(mismatches[y, x])
            outside += int(mismatches[y, x] and margin > allowance + ulp_guard)
            min_margin = min(min_margin, margin)
            max_dn_error = max(max_dn_error, abs(dn - ref_dn))
        need(outside == 0, "reference code mismatch outside declared rounding allowance")
        rows.append(dict(channel=("R", "G", "B")[channel], maximum_unquantized_reference_difference_dn=max_dn_error,
                         minimum_half_integer_margin_dn=min_margin, registered_float_allowance_dn=allowance,
                         sites_within_rounding_allowance=near, rounded_reference_code_differences=different,
                         code_differences_outside_allowance=outside))
    need(int(np.abs(codes.astype(np.int64) - reference_codes.astype(np.int64)).max()) <= 1,
         "approximate reference code difference exceeds one DN")
    return dict(maximum_scalar_discrepancy_e=maximum, rms_scalar_discrepancy_e=rms,
                rounded_reference_code_differences=int(mismatches.sum()), channels=rows,
                interpretation="Approximate reference; its rounded CFA is not the exact conversion authority")


def verify(manifest_path, manifest_sha, commission_path, commission_sha, *, fixture_only=False):
    manifest_path, commission_path = Path(manifest_path).resolve(), Path(commission_path).resolve()
    reads, before = Reads(), source_state()
    manifest = reads.external(manifest_path, manifest_sha)
    gate = reads.external(commission_path, commission_sha)
    keys(manifest, ("schema", "status", "producer", "sensor", "scene", "ray_model", "numerical_contract", "frames"), "closed emitted manifest required")
    need(manifest["schema"] == "m194e-joint-pupil-v1" and manifest["status"] == "float-commissioned-cfa-unverified", "unreviewed terminal emission required")
    receipt_path = reads.bound(manifest["producer"]["emission_receipt"], manifest_path.parent)
    run = json_read(receipt_path)
    keys(run, ("schema", "status", "command", "started_utc", "python", "numpy", "input_bundle", "float_commission", "trusted_float_sha256", "sources_before", "frames", "sources_after", "ended_utc"), "closed terminal emission receipt required")
    need(run["schema"] == "m194e-emission-run-v1" and run["status"] == "CFA_COMPLETE_AWAITING_INDEPENDENT_REVIEW", "emission incomplete or refused")
    need(run["trusted_float_sha256"] == commission_sha, "emission used different external float authority")
    recorded_gate = reads.bound(run["float_commission"], REPO)
    need(recorded_gate.read_bytes() == commission_path.read_bytes(), "emission gate bytes differ from external gate")
    bundle_path = reads.bound(run["input_bundle"], REPO)
    bundle, _ = S.validate_commission(bundle_path, commission_path, commission_sha)
    for name in ("sensor", "scene", "ray_model", "numerical_contract"):
        S.same_shape_value(manifest[name], bundle[name], "emitted " + name)
    keys(manifest["producer"], set(bundle["producer"]) | {"emission_receipt"}, "closed emission producer required")
    S.same_shape_value({k: manifest["producer"][k] for k in bundle["producer"]}, bundle["producer"], "emitted producer")
    need(type(manifest["frames"]) is list and len(manifest["frames"]) == 5, "five emitted frames required")
    for actual, original in zip(manifest["frames"], bundle["frames"]):
        geometry = ("index", "inverse_focus", "K", "forward_similarity")
        S.same_shape_value({k: actual[k] for k in geometry}, {k: original[k] for k in geometry}, "emitted frame geometry")
    need(run["sources_before"] == run["sources_after"] == gate["producer_sources"] == S.source_bindings(), "source provenance differs")
    S.same_shape_value(run["frames"], manifest["frames"], "completion frames")
    need(type(run["command"]) is list and run["command"] and all(type(v) is str for v in run["command"]), "recorded command missing")
    started, ended = (datetime.fromisoformat(run[k]) for k in ("started_utc", "ended_utc"))
    need(started.tzinfo is not None and ended.tzinfo is not None and ended >= started, "terminal chronology invalid")
    for k in ("python", "numpy"):
        need(type(run[k]) is str and bool(run[k]), "runtime provenance missing")
    for collection in (bundle["frames"], *bundle["refinements"].values()):
        for frame in collection:
            reads.bound(frame["expected_scalar"], bundle_path.parent, True)
            p = reads.bound(frame["numerical_receipt"], bundle_path.parent)
            nr = json_read(p)
            reads.bound(nr["expected_scalar"], p.parent, True)
            reads.bound(nr["error_indicator"], p.parent, True)
    for name, value in bundle["producer"]["sources"].items():
        reads.bound(dict(path=name, **value), REPO)
    reads.bound(bundle["producer"]["author_controls"], REPO)
    for name, value in bundle["producer"]["designs"].items():
        reads.bound(dict(path=name, **value), HERE)

    evidence = {}
    evidence_paths = {}
    for name, ref in gate["independent_evidence"].items():
        p = reads.bound(ref, REPO)
        evidence[name], evidence_paths[name] = json_read(p), p
    expected_status = dict(controls="PASS_REFERENCE_INSTRUMENT_ONLY", author_api="PASS_AUTHOR_API_ONLY",
                           reference="PASS_COMPLETE_REFERENCE_ONLY", comparison="PASS_FLOAT_MODEL")
    for name, record in evidence.items():
        status = "FIXTURE_ONLY_" + name.upper() if fixture_only else expected_status[name]
        need(record.get("status") == status and record.get("source_unchanged") is True, "independent predecessor nonterminal or fixture/genuine mode mismatch: " + name)
    if not fixture_only:
        need(sha(evidence_paths["reference"]) == REFERENCE_SHA, "genuine fixed independent reference differs")
    reference, comparison = evidence["reference"], evidence["comparison"]
    need(type(reference["frames"]) is list and len(reference["frames"]) == 10, "ten primary/refined reference frames required")
    references = {(r["arm"], r["index"]): r for r in reference["frames"]}
    need(set(references) == {(a, i) for a in ("primary", "refined") for i in range(5)}
         and all(type(r["index"]) is int for r in reference["frames"]), "distinct ordered reference population required")
    need(type(comparison["frames"]) is list and len(comparison["frames"]) == 15, "fifteen complete numerical comparisons required")
    comparisons = {(r["arm"], r["index"]): r for r in comparison["frames"]}
    need(set(comparisons) == {(a, i) for a in ARMS for i in range(5)}
         and all(type(r["index"]) is int for r in comparison["frames"]), "distinct numerical comparison population required")
    need(reads.bound(comparison["inputs"]["bundle"], REPO) == bundle_path, "comparison evaluated another float bundle")
    for name, expected_count in (("independent_refinement", 5), ("author_refinement", 10)):
        need(type(comparison[name]) is list and len(comparison[name]) == expected_count and all(r["passed"] is True for r in comparison[name]), "numerical refinement did not pass")
    for arm in ARMS:
        frames = bundle["frames"] if arm == "primary" else bundle["refinements"][arm]
        for i, frame in enumerate(frames):
            row = comparisons[(arm, i)]
            need(row["actual"] == frame["expected_scalar"] and row["reference"] == references[("refined", i)]["array"]
                 and row["statistics"]["pass"] is True, "float comparison binding/admission differs")

    # The already commissioned whole-file lineage reader is reused unchanged.
    actual = A.actual_output(manifest_path, bundle_path)
    frames = []
    for i, f in enumerate(manifest["frames"]):
        scalar = reads.float_array(f["expected_scalar"], manifest_path.parent, array=True)
        reads.float_array(f["expected_cfa"], manifest_path.parent, array=True)
        code_path = reads.bound(f["cfa"], manifest_path.parent, True)
        codes = O.read_raw(code_path)
        nr_path = reads.bound(f["numerical_receipt"], manifest_path.parent)
        nr = json_read(nr_path)
        reads.bound(nr["expected_scalar"], nr_path.parent, True)
        reads.bound(nr["error_indicator"], nr_path.parent, True)
        ref_value = reads.float_array(references[("refined", i)]["array"], evidence_paths["reference"].parent)
        optical = reference_diagnostic(scalar, ref_value, codes)
        frames.append(dict(index=i, exact_conversion=actual[i], reference_discrepancy=optical))
    api = reads.external(API_RESULT, API_RESULT_SHA)
    need(api["pass_"] is True and api["passed"] == api["total"] == 109 and api["invariance"] is True, "emitter/API predecessor failed")
    reads.finish()
    after = source_state()
    need(before == after, "verifier source changed")
    return dict(schema="m194e-independent-cfa-verification-v1",
                status="PASS_FIXTURE_READER_ONLY" if fixture_only else "PASS_CFA_CONVERSION_AND_PROVENANCE",
                fixture_only=fixture_only, source_before=before, source_after=after, source_unchanged=True,
                externally_trusted_manifest_sha256=manifest_sha, externally_trusted_float_commission_sha256=commission_sha,
                input_bindings=reads.observed, frames=frames, sample_count=5 * 48 * 64,
                units=dict(scalar="electrons", expected_cfa="electrons with site channel factor", cfa="little-endian u16 DN",
                           black_dn=512, white_exclusive_dn=15360, gain_dn_per_e=.25, noise=False, wb_applied=False),
                scope="Exact noiseless CFA conversion and recorded provenance of the admitted geometric model; no camera calibration, diffraction, production merge, quality or SOTA claim")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--manifest-sha256", required=True)
    ap.add_argument("--float-commission", type=Path, required=True)
    ap.add_argument("--float-commission-sha256", required=True)
    ap.add_argument("--reader-controls", type=Path, required=True)
    ap.add_argument("--reader-controls-sha256", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194e-independent-cfa-verification-v1", status="UNCOMMISSIONED_CFA")
    try:
        controls = Reads().external(args.reader_controls, args.reader_controls_sha256)
        need(controls["status"] == "PASS_FIXTURE_READER_ONLY" and controls["pass_"] is True
             and controls["source_unchanged"] is True and all(c["passed"] for c in controls["checks"]), "final reader controls failed")
        for name, value in controls["sources"].items():
            need(sha(HERE / name) == value, "commissioned final reader changed")
        result = verify(args.manifest, args.manifest_sha256, args.float_commission, args.float_commission_sha256)
        result["reader_controls"] = dict(path=str(args.reader_controls.resolve()), sha256=args.reader_controls_sha256)
    except Exception as exc:
        result.update(error=repr(exc), traceback=traceback.format_exc())
    result.update(command=sys.argv, interpreter_argv=sys.orig_argv, executable=sys.executable,
                  cwd=os.getcwd(), xoptions=sys._xoptions, python=sys.version, numpy=np.__version__,
                  completed_utc=datetime.now(timezone.utc).isoformat())
    (args.output / "sources").mkdir()
    for name in source_state():
        shutil.copyfile(HERE / name, args.output / "sources" / name)
    write(args.output / "result.json", result)
    if result["status"] == "PASS_CFA_CONVERSION_AND_PROVENANCE":
        write(args.output / "cfa-commission.json", dict(schema="m194e-cfa-commission-v1", status="PASS",
              manifest=dict(path=str(args.manifest.resolve()), sha256=args.manifest_sha256),
              float_commission=dict(path=str(args.float_commission.resolve()), sha256=args.float_commission_sha256),
              independent_verification=dict(path="result.json", sha256=sha(args.output / "result.json")),
              sample_count=result["sample_count"], scope=result["scope"]))
    print(json.dumps({k: result.get(k) for k in ("status", "sample_count", "error")}))
    return 0 if result["status"] == "PASS_CFA_CONVERSION_AND_PROVENANCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
