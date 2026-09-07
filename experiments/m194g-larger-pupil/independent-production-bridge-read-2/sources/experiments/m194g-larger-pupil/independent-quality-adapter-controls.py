"""Actual12 metadata companions and private complete-reducer instruments."""
import copy
import math
import traceback


def initial_result():
    return {"schema": "m194g-quality-adapter-controls-v1", "status": "UNCOMMISSIONED_QUALITY_ADAPTER",
            "checks": [], "genuine_subjects": [], "private_load_counts": [], "work_before": None,
            "work_after": None, "error": None,
            "scope": "actual12 metadata association; pure private schema faults and private full18-row flat reductions; no38 quality scores"}


def run_controls(subjects, context, *, io, reads, adapter, metrics, readout, budget, result):
    """The caller attaches result=initial_result() before this call.

    All attempted checks survive a refusal. The caller must require the final
    PASS status before twelve real TIFF decodes or final bridge admission.
    """
    a, m, np = adapter, metrics, metrics.np
    def check(name, passed, **details):
        io.need(not any(row["id"] == name for row in result["checks"]), "duplicate adapter control")
        result["checks"].append({"id": name, "passed": bool(passed), "details": details})
        io.need(bool(passed), "quality adapter control " + name)
    def refuses(name, call, exception, fragment):
        try: call()
        except exception as exc:
            check(name, fragment in str(exc), exception_type=type(exc).__name__, message=str(exc))
        else: check(name, False)
    try:
        io.need(result == initial_result(), "fresh attached adapter-control result")
        result["work_before"] = budget.receipt()
        expected = {(scene, seed, mode, "all-five", "off") for scene in ("flat", "textured")
                    for seed in (None, 701) for mode in a.MODES}
        expected |= {("textured", 701, a.MODES[0], "all-five", observer) for observer in ("count", "placebo")}
        expected |= {("textured", None, a.MODES[0], "endpoint-" + str(index), "off") for index in (0, 4)}
        identities = [(s["row"]["scene"], s["row"]["seed"], s["row"]["admission"], s["row"]["subset"], s["observer"]) for s in subjects]
        check("actual12-population", len(subjects) == 12 and len(set(identities)) == 12 and set(identities) == expected,
              population=[list(item) for item in identities])
        working = dict(context)
        base = endpoint = None
        for ordinal, subject in enumerate(subjects):
            checked = a.read_entry(subject["row"], io=io, reads=reads, context=working, observer=subject["observer"], decode=False)
            if working.get("common_geometry") is None: working["common_geometry"] = checked["geometry"]
            check("actual12-entry-" + str(ordinal), True, plan=subject["row"]["plan"], receipt=subject["row"]["receipt"], floor=checked["floor"])
            result["genuine_subjects"].append({"row": subject["row"], "observer": subject["observer"]})
            if identities[ordinal] == ("flat", None, a.MODES[0], "all-five", "off"): base = checked
            if subject["row"]["subset"] == "endpoint-4": endpoint = checked
        io.need(base is not None and endpoint is not None, "private controls actual base/endpoint companions")
        row, plan = base["row"], base["plan"]
        def validate(value, selected_row=row):
            return a.validate_plan(value, selected_row, authority=context["authority"], authority_sha=context["noise_admission"]["sha256"],
                                   selected_frames=base["plan"]["selected"]["frames"], executable=context["executable"], observer="off")
        mutations = (
            ("exposure", ("config", "exposure_stops"), 1, "production config"),
            ("admission", ("config", "admission"), "FloorPedestalV1", "production config"),
            ("gate", ("config", "gate"), 1., "production config"),
            ("read-noise", ("injected_noise", "read_noise_e", 0), 0., "algorithm noise"),
            ("red-wb", ("wb_f32", 0), 1., "represented WB"),
            ("frame-blue-wb", ("frame_wb_f32", 2), 1., "frame WB"),
            ("second-black", ("normalization", "second_black_subtraction"), True, "normalization"),
            ("white-rail", ("sensor", "white", 0), 16383, "injected sensor"),
            ("float-width", ("geometry", "full_native", 0), 320., "full native"),
            ("false-native-origin", ("geometry", "canonical_native_offset", 0), 99, "native crop origin"),
            ("wrong-level-size", ("geometry", "level_sizes", 2, 0), 999, "level sizes"),
            ("bool-local-index", ("geometry", "placements", 1, "local_index"), True, "placements"),
            ("wrong-probe", ("geometry", "placements", 4, "probe_seed_index"), 0, "placements"),
            ("wrong-reference", ("geometry", "reference_coordinate_gauge"), 4, "reference gauge"),
            ("selected-seed", ("selected", "seed"), 701, "source tuple"),
            ("source-hash", ("selected", "frames", 0, "cfa", "sha256"), "0" * 64, "source tuple"),
        )
        for name, path, value, reason in mutations:
            changed = copy.deepcopy(plan)
            node = changed
            for key in path[:-1]: node = node[key]
            node[path[-1]] = value
            refuses("plan-" + name, lambda v=changed: validate(v), a.Refusal, reason)
        changed = copy.deepcopy(plan); changed["extra"] = True
        refuses("plan-unknown-key", lambda: validate(changed), a.Refusal, "keys")
        validate(plan)
        check("actual-plan-restored", True, original_plan_sha256=base["row"]["plan"]["sha256"])
        ep = copy.deepcopy(endpoint["plan"]); ep["geometry"]["placements"][0]["probe_seed_index"] = 4
        refuses("endpoint-original-versus-local-probe", lambda: a.validate_plan(ep, endpoint["row"], authority=context["authority"],
                authority_sha=context["noise_admission"]["sha256"], selected_frames=endpoint["plan"]["selected"]["frames"],
                executable=context["executable"], observer="off"), a.Refusal, "placements")

        log = reads.raw(reads.ref(row["log"]), row["log"]["sha256"], row["log"]["bytes"], cap=16 * 1024**2)
        floor_line = next(line for line in log.splitlines() if line.startswith(b"measured floor  :"))
        floor_values = floor_line.split(b":", 1)[1].split()
        negative_line = b"measured floor  : " + b" ".join([b"-1.0000", *floor_values[1:]])
        mutations = (
            ("missing", log.replace(b"measured floor  :", b"missing floor   :", 1), "banner"),
            ("duplicate", log + b"\nmeasured floor  : 1.0000\n", "banner"),
            ("empty", log.replace(next(line for line in log.splitlines() if line.startswith(b"measured floor  :")), b"measured floor  : ", 1), "prefix"),
            ("nonfinite", log.replace(b"measured floor  :", b"measured floor  : nan ", 1), "prefix"),
            ("negative", log.replace(floor_line, negative_line, 1), "nonnegative"),
            ("wrong-count", log.replace(b"averaged over 5 warped", b"averaged over 4 warped", 1), "frame count"),
        )
        for name, changed, reason in mutations:
            refuses("floor-" + name, lambda v=changed: a.floor_log(v, 5), a.Refusal, reason)
        check("actual-floor-restored", a.floor_log(log, 5) == base["floor"])

        # Complete38 objects below are deliberately private pure-validator
        # fixtures, not parent-observed output records or genuine authority.
        private = {"schema": "m194g-production-matrix-v1", "status": "COMPLETE_38_RGB_OUTPUTS_UNSCORED",
                   "ref_root": "repository", "noise_admission": {}, "bridge_commission": {}, "instrument_commission": {},
                   "execution_release": {}, "invocation": [], "sources_before": {"fixture": 1}, "sources_after": {"fixture": 1},
                   "inputs_before": {"fixture": 1}, "inputs_after": {"fixture": 1}, "entries": [], "work": {},
                   "error": None, "finalization_errors": []}
        for item in a.expected_rows():
            private["entries"].append({**item, **{name: {"path": f"private-only/{item['ordinal']}/{name}.json", "sha256": "0" * 64, "bytes": 1}
                                      for name in ("plan", "plan_launch", "receipt", "tiff", "log", "launch")}})
        check("private38-schema-companion", len(a.validate_population(private)) == 38, fixture_only=True)
        mutations = []
        changed = copy.deepcopy(private); changed["entries"].pop(); mutations.append(("missing", changed, "population"))
        changed = copy.deepcopy(private); changed["entries"][1] = copy.deepcopy(changed["entries"][0]); mutations.append(("duplicate", changed, "ordinal"))
        changed = copy.deepcopy(private); changed["entries"][2]["seed"] = 701.; mutations.append(("float-seed", changed, "seed"))
        changed = copy.deepcopy(private); changed["entries"][1]["ordinal"] = True; mutations.append(("bool-ordinal", changed, "ordinal"))
        changed = copy.deepcopy(private); changed["entries"][18]["admission"] = a.MODES[0]; mutations.append(("global-state-order", changed, "admission"))
        changed = copy.deepcopy(private); changed["entries"][37]["original_indices"] = [0]; mutations.append(("endpoint-original", changed, "original_indices"))
        changed = copy.deepcopy(private); changed["entries"][1]["tiff"] = changed["entries"][0]["tiff"]; mutations.append(("alias", changed, "aliases"))
        changed = copy.deepcopy(private); changed["inputs_after"] = {"changed": 2}; mutations.append(("changed-input", changed, "inputs"))
        changed = copy.deepcopy(private); changed["error"] = "failed"; mutations.append(("terminal-error", changed, "error"))
        for name, changed, reason in mutations:
            refuses("private38-" + name, lambda v=changed: a.validate_population(v), a.Refusal, reason)
        check("private38-restored", len(a.validate_population(private)) == 38, fixture_only=True)

        # Use exact represented per-channel flat ideals, then add the fixed
        # offsets. This preserves the literal temporal/MSE oracle despite WB.
        scalar = budget.empty((240, 320), "<f8", "private complete-reducer scalar")
        scalar.fill(12000.)
        offsets = dict(zip(readout.SEEDS, (-7., -5., -3., -1., 1., 3., 5., 7.), strict=True))
        rows = {(seed, mode): {"seed": seed, "mode": mode} for seed in (None, *readout.SEEDS) for mode in readout.MODES}
        fixture = {"scene": {}}  # Flat reduction never invokes wave or optical helpers.
        geom = {"output_native": [320, 240], "canonical_native_offset": [0, 0]}
        def reduction(kind):
            calls = []
            def load(item):
                calls.append((item["seed"], item["mode"]))
                array = budget.empty((240, 320, 3), "<f8", "private complete-reducer RGB")
                noise = 0. if item["seed"] is None else offsets[item["seed"]]
                if item["mode"] == readout.MODES[1]: noise = 9. if kind == "bias" else noise / 2
                for c in range(3): array[:, :, c].fill(12000. * .25 * readout.FACTORS[c] * readout.WB[c] + noise)
                if kind == "spike" and item["seed"] == 751 and item["mode"] == readout.MODES[1]: array[19, 23, 1] += 64.
                return array
            value = readout.scene_readout("flat", rows, scalar, {}, geom, fixture, metrics=m, budget=budget, load_rgb=load)
            result["private_load_counts"].append({"case": kind, "calls": len(calls)})
            check("complete18-" + kind + "-population", len(calls) == 34 and len(value["individual_errors"]) == 378
                  and len(value["paired_variance"]) == 21 and len(value["sparse"]) == 60, loader_calls=len(calls))
            return value
        full = reduction("half-noise")
        check("complete18-literal-variances", all(abs(r["baseline_variance_dn2"] - 24.) <= 1e-10
                  and abs(r["candidate_variance_dn2"] - 6.) <= 1e-10 for r in full["paired_variance"]))
        check("complete18-literal-mse", all(abs(r["mean_repeat_mse_dn2"] - (21. if r["mode"] == a.MODES[0] else 5.25)) <= 1e-7
                  for r in full["temporal"] if r["reference"] == "ideal"))
        expected_differences = [-.75 * offsets[seed]**2 for seed in readout.SEEDS]
        check("complete18-paired-repeat-differences", all(max(abs(x - y) for x, y in zip(r["candidate_minus_baseline"]["values"], expected_differences, strict=True)) <= 1e-7
                  for r in full["paired_mse"]))
        biased = reduction("bias")
        check("complete18-bias-versus-noise", all(r["candidate_variance_dn2"] == 0. for r in biased["paired_variance"])
                  and all(abs(r["mean_repeat_mse_dn2"] - 81.) <= 1e-7 for r in biased["temporal"]
                          if r["reference"] == "ideal" and r["mode"] == a.MODES[1]))
        spiked = reduction("spike")
        rows_spike = [r for r in spiked["sparse"] if r["population"] == "individual" and r["seed"] == 751 and r["channel"] == "G" and r["region"] == "whole"]
        check("complete18-actual-spike-consumed", len(rows_spike) == 1 and rows_spike[0]["after_maximum_absolute_error_dn"] == 67.5
                  and rows_spike[0]["after_worst_site"]["native_xy"] == [23, 19] and rows_spike[0]["worsening_gt10_dn_count"] == 1,
                  sparse=rows_spike)
        missing = dict(rows); missing.pop((751, a.MODES[1]))
        refuses("complete18-missing-repeat", lambda: readout.scene_readout("flat", missing, scalar, {}, geom, fixture,
                metrics=m, budget=budget, load_rgb=lambda _: (_ for _ in ()).throw(AssertionError("unexpected load"))), m.Refusal, "population")
        # Expected count is fixed from the literal source before execution.
        io.need(len(result["checks"]) == 59 and all(row["passed"] for row in result["checks"]), "complete59 adapter-control population")
        result["work_after"] = budget.receipt()
        result["status"] = "PASS_QUALITY_MATRIX_ADAPTER_INSTRUMENTS"
    except Exception:
        result["error"] = traceback.format_exc()
        result["status"] = "UNCOMMISSIONED_QUALITY_ADAPTER"
        try: result["work_after"] = budget.receipt()
        except Exception: pass
    return result
