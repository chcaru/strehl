"""Released private noise schedule or authority-gated90-file generation.

Source preparation only until exact commands and runtime inputs are released.
No integrator imports, independent statistics or success CFA gate live here.
"""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import traceback
import weakref

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
INTERFACE = HERE / "software-noise-interface.md"
INTERFACE_SHA = "98048ba64d9f984e6dbba17607b40d6c5899057aa88708b9354e98a40fa131c2"
CORE_SHA = "abe9d712cbf9caf07f8dfc276a0e0ab4474366db039fd3b1fc2f25cb7a057292"
PREFIX = "experiments/m194g-larger-pupil/"
REQUIRED = ("software-noise.py", "software-noise-run.py", "software-noise-authority.py",
            "independent-noise-reader.py", "software-noise-interface.md", "next-noise-contract.md",
            "independent-full-float-authority-schema.md")
FAULT_LEVELS = (("c-after-poisson", 12000), ("gain-double", 4096), ("omit-read", 0),
                ("reuse-repeat-zero", 0), ("clone-green", 4096), ("read-lag2-mix", 0),
                ("clamp-black", 0))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def early_check():
    need(time.process_time() - ENTRY_CPU <= 120 and time.perf_counter() - ENTRY_WALL <= 240,
         "noise entry/setup time budget exceeded")


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def finite(value):
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        elif isinstance(value, list):
            for item in value:
                finite(item)
        elif isinstance(value, float):
            need(math.isfinite(value), "nonfinite JSON value")
    result = json.loads(raw, object_pairs_hook=pairs,
                        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON " + value)))
    finite(result)
    return result


def canonical(value):
    return (json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def relative(path):
    need(type(path) is str and path and "\\" not in path and ":" not in path,
         "invalid release path")
    need(all(part not in ("", ".", "..") for part in path.split("/")), "noncanonical release path")
    result = (ROOT / path).resolve(strict=True)
    need(result.is_relative_to(ROOT) and result.is_file(), "release path escapes repository")
    return result


def bound(path, expected=None, size=None, maximum=4_194_304):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    need(len(raw) <= maximum, "input extent exceeds bound")
    ref = {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    need(expected is None or ref["sha256"] == expected, "external input hash mismatch")
    need(size is None or len(raw) == size, "external input byte count mismatch")
    return raw, ref


def authorize(args):
    early_check()
    raw, ref = bound(args.execution_release, args.execution_release_sha256)
    release = strict(raw)
    need(type(release) is dict and set(release) == {"schema", "scope", "source_bindings", "inputs", "commands"},
         "exact noise execution-release fields required")
    need(release["schema"] == "m194g-numerical-execution-release-v1"
         and release["scope"] == ("noise-commission" if args.mode == "commission" else "noise-emission"),
         "wrong noise execution scope")
    need(type(release["commands"]) is list and release["commands"], "released command list required")
    commands = []
    for command in release["commands"]:
        need(type(command) is list and all(type(v) is str for v in command)
             and command.count("ACTUAL_EXECUTION_RELEASE_SHA256") == 1, "invalid exact released command")
        commands.append([args.execution_release_sha256 if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in command])
    need(list(sys.orig_argv) in commands, "actual interpreter argv differs from released command")
    sources = release["source_bindings"]
    need(type(sources) is dict and all(PREFIX + name in sources for name in REQUIRED), "incomplete source closure")
    for path, binding in sources.items():
        need(type(binding) is dict and set(binding) == {"sha256", "bytes"}
             and type(binding["bytes"]) is int and binding["bytes"] > 0, "source binding fields/types")
        bound(relative(path), binding["sha256"], binding["bytes"], maximum=1_048_576)
        early_check()
    need(sources[PREFIX + "software-noise.py"]["sha256"] == CORE_SHA, "committed core required")
    need(sources[PREFIX + "software-noise-interface.md"]["sha256"] == INTERFACE_SHA, "frozen noise interface required")
    inputs = {}
    need(type(release["inputs"]) is list and release["inputs"], "released runtime inputs required")
    for entry in release["inputs"]:
        need(type(entry) is dict and set(entry) == {"path", "sha256", "bytes"}
             and type(entry["bytes"]) is int and entry["bytes"] > 0, "release input fields/types")
        path = relative(entry["path"])
        key = str(path).casefold()
        need(key not in inputs, "duplicate released input")
        bound(path, entry["sha256"], entry["bytes"])
        inputs[key] = entry
        early_check()
    required = [(args.runtime, args.runtime_sha256)]
    if args.mode == "intended":
        required += [(args.float_commission, args.float_commission_sha256),
                     (args.noise_commission, args.noise_commission_sha256)]
    for path, sha in required:
        need(path is not None and sha is not None, "required stage prerequisite missing")
        need(inputs.get(str(Path(path).resolve()).casefold(), {}).get("sha256") == sha,
             "actual prerequisite is not externally released")
    return release, ref


def load_module(name, module_name, release):
    path = HERE / name
    expected = release["source_bindings"][PREFIX + name]
    raw, _ = bound(path, expected["sha256"], expected["bytes"], maximum=1_048_576)
    spec = importlib.util.spec_from_loader(module_name, loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[module_name] = module
    try:
        exec(compile(raw, str(path), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


def snapshot(release, store, phase):
    bindings = {}
    for rel, expected in sorted(release["source_bindings"].items()):
        raw, ref = bound(relative(rel), expected["sha256"], expected["bytes"], maximum=1_048_576)
        store._write(phase + "/" + rel, lambda writer, data=raw: writer.write(data))
        bindings[rel] = {"sha256": ref["sha256"], "bytes": ref["bytes"]}
    return bindings


def recheck_bindings(release, input_reads=None):
    sources, inputs = {}, {}
    for rel, expected in release["source_bindings"].items():
        _, ref = bound(relative(rel), expected["sha256"], expected["bytes"], maximum=1_048_576)
        sources[rel] = {"sha256": ref["sha256"], "bytes": ref["bytes"]}
    for ref in release["inputs"]:
        bound(relative(ref["path"]), ref["sha256"], ref["bytes"])
        inputs[ref["path"]] = {"sha256": ref["sha256"], "bytes": ref["bytes"]}
    if input_reads is not None:
        for path, binding in input_reads.finish().items():
            inputs[Path(path).relative_to(ROOT).as_posix()] = binding
    return sources, inputs


def schedule():
    rows = []
    def add(call_id, group, level, scene, seed, frame, phase="baseline", fault=None, mode="off"):
        rows.append({"call_id": call_id, "group": group, "level": level, "scene": scene,
                     "seed": seed, "frame": frame, "phase": phase, "fault": fault, "observer": mode})
    for level in (0, 64, 4096, 12000):
        for r in range(64):
            group = f"baseline-s{level}"
            add(f"{group}-r{r:02d}", group, level, f"control-s{level}", 100000 + r, 0)
    for fault, level in FAULT_LEVELS:
        for phase in ("fault", "restored"):
            for r in range(64):
                group = phase + "-" + fault
                add(f"{group}-r{r:02d}", group, level, f"control-s{level}", 100000 + r, 0, phase, fault)
    for seed in (701, 709):
        for frame in range(5):
            add(f"live-a-s{seed}-f{frame}", "live", 12000, "control-live-a", seed, frame)
    add("live-b-s701-f0", "live", 12000, "control-live-b", 701, 0)
    for mode in ("count", "placebo"):
        add("observer-" + mode, "observer", 12000, "control-live-a", 701, 0, "replay", mode=mode)
    for frame in range(4, -1, -1):
        add(f"replay-f{frame}", "replay", 12000, "control-live-a", 701, frame, "replay")
    for frame in range(5):
        add(f"dark-f{frame}", "dark", 0, "control-s0", 701, frame)
    for phase in ("fault", "restored"):
        group = "shared-read-frame" + ("-restored" if phase == "restored" else "")
        for frame in range(5):
            add(f"{group}-f{frame}", group, 0, "control-s0", 701, frame, phase, "shared-read-frame")
    add("component-key-restored", "component-key-restored", 12000, "control-live-a", 701, 0,
        "restored", "omit-component-key")
    need(len(rows) == 1186 and len({r["call_id"] for r in rows}) == 1186, "private schedule cardinality")
    return rows


def deterministic(core, context, store):
    np, budget = core.np, context.budget
    records = []
    def record(call_id, kind, inp=None, q=None, witness=None, exception=None, details=None):
        out = {"call_id": call_id, "kind": kind, "input": inp, "q": q, "witness": witness,
               "status": "REFUSED" if exception else "VALUE", "exception": exception, "details": details or {}}
        records.append(out)
    def array(name, value):
        budget.watch(value, "deterministic fixture")
        return store.array("deterministic/" + name + ".npy", value)
    x = budget.empty((10,), "<f8", "rounding fixture")
    x[:] = [-1.5, -.5, .5, 1.5, 511.5, 512.5, 513.5, 15359.5, 15360.5, 15361.5]
    xref = array("round-input", x)
    for name, half in (("round-baseline", False), ("round-half-up", True), ("round-restored", False)):
        observer = core.Observer("off")
        q, _ = core.encode_dn(x, budget, observer, half_up=half)
        record(name, "rounding", xref, array(name, q), observer.receipt())
        del q
    del x
    for name, value in (("reject-nan", math.nan), ("reject-posinf", math.inf), ("reject-neginf", -math.inf)):
        x = budget.empty((1,), "<f8", "deliberate nonfinite fixture")
        x.fill(value)
        ref = array(name + "-input", x)
        try:
            core.encode_dn(x, budget, core.Observer("off"))
        except ValueError as exc:
            need(type(exc) is ValueError and str(exc) == "encoder input contains nonfinite values",
                 "wrong nonfinite refusal")
            record(name, "nonfinite", ref, exception={"type": type(exc).__name__, "message": str(exc)})
        else:
            raise ValueError("nonfinite encoder input was accepted")
        del x
    scalar = budget.empty((4, 6), "<f8", "tagged scalar")
    for y in range(4):
        for x in range(6):
            scalar[y, x] = 1600 + 80 * x + 160 * y
    ref = array("tag-input", scalar)
    for name, fault, phase in (("tag-baseline", None, "baseline"), ("tag-swap-rb", "swap-rb", "fault"),
                                ("tag-rb-restored", "swap-rb", "restored"),
                                ("tag-swap-green", "swap-green", "fault"),
                                ("tag-green-restored", "swap-green", "restored")):
        sampled = core.sample_frame(scalar, core.FrameSpec("control-live-a", None, 0, 6, 4), context,
                                    fault_id=fault, phase=phase)
        record(name, "tag", ref, array(name, sampled.q), sampled.observer.receipt())
        del sampled
    del scalar
    scalar = budget.empty((96, 128), "<f8", "noise-off scalar")
    scalar.fill(12000)
    ref = array("noise-off-input", scalar)
    previous = core._new_generator
    forbidden_calls = 0
    def forbidden(*args, **kwargs):
        nonlocal forbidden_calls
        forbidden_calls += 1
        raise ValueError("noise-off attempted Generator construction")
    core._new_generator = forbidden
    try:
        for mode in ("off", "count", "placebo"):
            before_g, before_v = budget.generators, sum(budget.requested.values())
            sampled = core.sample_frame(scalar, core.FrameSpec("control-s12000", None, 0, 128, 96, 12000),
                                        context, observer_mode=mode)
            name = "noise-off-" + mode
            details = {"generator_delta": budget.generators - before_g,
                       "requested_delta": sum(budget.requested.values()) - before_v,
                       "forbidden_sampler_calls": forbidden_calls, "audit": sampled.audit_record()}
            record(name, "noise-off", ref, array(name, sampled.q), sampled.observer.receipt(), details=details)
            del sampled
    finally:
        core._new_generator = previous
    del scalar
    return records


def omitted_key(core, context, scalar):
    budget = context.budget
    spec = core.FrameSpec("control-live-a", 701, 0, 128, 96, 12000)
    before_g, before_v = budget.generators, sum(budget.requested.values())
    try:
        core.sample_frame(scalar, spec, context, phase="fault", fault_id="omit-component-key")
    except ValueError as exc:
        need(type(exc) is ValueError and str(exc) == "RNG key bytes mismatch", "wrong omitted-key refusal")
        exception = {"type": type(exc).__name__, "message": str(exc)}
    else:
        raise ValueError("omitted component key was accepted")
    details = {"spec": dict(vars(spec)), "generator_delta": budget.generators - before_g,
               "requested_delta": sum(budget.requested.values()) - before_v}
    need(details["generator_delta"] == details["requested_delta"] == 0, "omitted-key refusal sampled")
    return {"call_id": "component-key-omitted", "kind": "omitted-key", "input": None, "q": None,
            "witness": None, "status": "REFUSED", "exception": exception, "details": details}


def resource_control(core, budget):
    dead = budget.empty((3, 7), "<f8", "expiring resource control")
    old = weakref.ref(dead)
    del dead
    need(old() is None, "resource control did not expire owner")
    before = budget._live_bytes()
    budget.check_allocation((5, 8), "<f8")
    live = core.np.empty((5, 8), dtype="<f8")
    live.fill(0.0)
    # Force the stale-weak-entry condition deterministically, without allocator luck.
    budget._arrays[id(live)] = (old, 168, {"deliberately stale owner"})
    budget.watch(live, "replacement live owner")
    entry = budget._arrays[id(live)]
    live_delta = budget._live_bytes() - before
    alias = live[:, 2:5]
    alias_before = budget._live_bytes()
    budget.watch(alias, "same-backing alias")
    alias_delta = budget._live_bytes() - alias_before
    refused = False
    try:
        budget.check_allocation((budget.limits["live_array_bytes"] // 8 + 1,), "<f8")
    except core.BudgetError:
        refused = True
    need(refused, "oversize allocation request accepted")
    budget.watch(alias, "restored alias")
    details = {"expired_owner_dead": old() is None, "live_shape": [5, 8], "live_nbytes": int(live.nbytes),
               "registered_owner_is_live": entry[0]() is live, "registered_bytes": entry[1],
               "live_delta_bytes": live_delta, "alias_delta_bytes": alias_delta,
               "oversize_refused": refused, "restored_alias_same_bytes": budget._live_bytes() == alias_before}
    need(details["registered_owner_is_live"] and details["registered_bytes"] == live_delta == 320
         and alias_delta == 0 and details["restored_alias_same_bytes"], "stale-owner/alias resource control failed")
    del live, alias
    budget.check()
    return {"call_id": "resource-stale-owner", "kind": "resource", "input": None, "q": None,
            "witness": None, "status": "VALUE", "exception": None, "details": details}


def commission(core, reader, context, store, contract_ref, runtime_ref, sources, progress, evidence):
    budget = context.budget
    deterministic_rows = deterministic(core, context, store)
    records = []
    original = core._new_generator
    checked_keys = 0
    def checked_factory(spec, component, *args, **kwargs):
        nonlocal checked_keys
        generator, record = original(spec, component, *args, **kwargs)
        expected, words = reader.independent_key(dict(vars(spec)), component)
        need(record["key"].encode("ascii") == expected and record["entropy_words"] == words,
             "independent actual forwarded key/entropy disagreement")
        checked_keys += 1
        return generator, record
    core._new_generator = checked_factory
    try:
        for row in schedule():
            progress["call_id"] = row["call_id"]
            scalar = budget.empty((96, 128), "<f8", "private expected scalar")
            scalar.fill(row["level"])
            if row["call_id"] == "component-key-restored":
                deterministic_rows.append(omitted_key(core, context, scalar))
            spec = core.FrameSpec(row["scene"], row["seed"], row["frame"], 128, 96, row["level"])
            sampled = core.sample_frame(scalar, spec, context, fault_id=row["fault"], phase=row["phase"],
                                        observer_mode=row["observer"])
            _, ref = core.write_private_trace(sampled, store, "traces/" + row["call_id"],
                                               call_id=row["call_id"], group=row["group"])
            records.append({"call_id": row["call_id"], "record": ref})
            del sampled, scalar
            if len(records) % 64 == 0:
                print(f"private noise: {len(records)}/1186 calls persisted", flush=True)
    finally:
        core._new_generator = original
    deterministic_rows.append(resource_control(core, budget))
    need(checked_keys == 2372 and sum(budget.requested.values()) == 29_147_136, "exact sampling/key schedule mismatch")
    deterministic_rows.append({"call_id": "independent-key-preflight", "kind": "key-preflight", "input": None,
                               "q": None, "witness": None, "status": "VALUE", "exception": None,
                               "details": {"component_keys_checked": checked_keys, "key_bytes_checked": True,
                                           "entropy_words_checked": True}})
    index = {"schema": "m194g-software-noise-private-index-v1", "status": "COMPLETE_PRIVATE_TRACES_UNCOMMISSIONED",
             "contract": contract_ref, "runtime": runtime_ref, "source_bindings": sources,
             "records": records, "deterministic": deterministic_rows, "work": budget.receipt()}
    index_ref = store.json("private-index.json", index)
    evidence["index"] = index_ref
    progress["call_id"] = "independent-full-private-reader"
    independent = reader.read_commission(store.root / index_ref["path"], index_ref["sha256"], budget=budget)
    independent_ref = store.json("independent-private-read.json", independent)
    need(independent.get("schema") == "m194g-independent-software-noise-reader-v1"
         and independent.get("status") == "PASS_SOFTWARE_NOISE_PRIVATE_TRACES", "independent private noise reader failed")
    controls = reader.run_reader_controls(store.root / index_ref["path"], index_ref["sha256"],
                                          budget=budget, store=store,
                                          write_bytes=lambda relative, raw: store._write(relative, lambda stream: stream.write(raw)),
                                          genuine_result=independent)
    controls_ref = store.json("independent-reader-controls.json", controls)
    need(controls.get("schema") == "m194g-independent-noise-reader-controls-v1"
         and controls.get("status") == "PASS_INDEPENDENT_NOISE_READER_CONTROLS", "independent reader controls failed")
    command = {"schema": "m194g-software-noise-reader-command-v1", "status": "PASS_SOFTWARE_NOISE_PRIVATE_TRACES",
               "read": independent_ref, "controls": controls_ref}
    command_ref = store.json("independent-reader-command.json", command)
    evidence["independent_reader"] = command_ref
    return index_ref, command_ref


def intended_plan(fixture, seeds):
    need(all(type(seed) is int for seed in seeds)
         and tuple(seeds) == (701, 709, 719, 727, 733, 739, 743, 751), "exact intended seed order required")
    need(canonical(fixture["frame_indices"]) == canonical([0, 1, 2, 3, 4])
         and canonical(fixture["inverse_foci"]) == canonical([0.5, 0.625, 0.75, 0.875, 1.0]),
         "exact intended frame/focus order required")
    plan = [(scene, seed, list(enumerate(fixture["inverse_foci"])))
            for scene in ("textured", "flat") for seed in (None, *seeds)]
    identities = [(scene, seed, index) for scene, seed, frames in plan for index, _ in frames]
    need(len(plan) == 18 and len(identities) == len(set(identities)) == 90,
         "exact unique90-entry intended matrix required before sampling/writes")
    return plan


def intended(core, authority_module, args, context, store, contract_ref, runtime_ref, sources, progress):
    budget = context.budget
    authority = authority_module.FloatAuthority(args.float_commission, args.float_commission_sha256, core, budget)
    reads = authority.reads
    noise_raw = reads.raw(args.noise_commission, args.noise_commission_sha256)
    noise = core.strict_json(noise_raw)
    need(noise.get("schema") == "m194g-software-noise-run-v1" and noise.get("mode") == "commission"
         and noise.get("status") == "PASS_SOFTWARE_NOISE_COMMISSION" and noise.get("error") is None
         and noise.get("finalization_errors") == []
         and noise.get("sources_before") == noise.get("sources_after")
         and noise.get("sources_before") == sources
         and noise.get("inputs_before") == noise.get("inputs_after"), "complete independent noise commission required")
    noise_child, _ = reads.json_ref(noise["independent_reader"], Path(args.noise_commission).resolve().parent)
    need(set(noise_child) == {"schema", "status", "read", "controls"}
         and noise_child["schema"] == "m194g-software-noise-reader-command-v1"
         and noise_child["status"] == "PASS_SOFTWARE_NOISE_PRIVATE_TRACES", "noise commission child failed")
    noise_parent = Path(args.noise_commission).resolve().parent
    actual_read, _ = reads.json_ref(noise_child["read"], noise_parent)
    actual_controls, _ = reads.json_ref(noise_child["controls"], noise_parent)
    need(actual_read.get("schema") == "m194g-independent-software-noise-reader-v1"
         and actual_read.get("status") == "PASS_SOFTWARE_NOISE_PRIVATE_TRACES"
         and actual_controls.get("schema") == "m194g-independent-noise-reader-controls-v1"
         and actual_controls.get("status") == "PASS_INDEPENDENT_NOISE_READER_CONTROLS", "independent noise child status mismatch")
    noise_index, noise_index_path = reads.json_ref(noise["index"], noise_parent)
    expected_index = {**noise["index"], "path": str(noise_index_path)}
    need(core.canonical_bytes(actual_read.get("index")) == core.canonical_bytes(expected_index)
         and noise_index.get("schema") == "m194g-software-noise-private-index-v1"
         and noise_index.get("status") == "COMPLETE_PRIVATE_TRACES_UNCOMMISSIONED"
         and noise_index.get("source_bindings") == sources,
         "independent noise result is not associated with the commissioned index")
    need(actual_controls.get("actual_full_entry_companion_sha256") ==
         core.digest_bytes(core.canonical_bytes(actual_read)), "reader controls bind a different actual full read")
    old_runtime, _ = reads.json_ref(noise["runtime"], noise_parent)
    need(core.canonical_bytes(old_runtime) == core.canonical_bytes(context.before), "commissioned runtime changed")
    plan = intended_plan(authority.fixture, core.SEEDS)
    bundles = []
    for scene, seed, frame_plan in plan:
        state = "noise-off" if seed is None else f"seed-{seed}"
        frames = []
        for index, focus in frame_plan:
            progress["call_id"] = f"{scene}-{state}-frame-{index}"
            if scene == "textured":
                scalar = authority.scalar(index)
            else:
                scalar = budget.empty((240, 320), "<f8", "flat expected scalar")
                scalar.fill(12000)
            spec = core.FrameSpec(scene, seed, index, 320, 240, 12000 if scene == "flat" else None)
            sampled = core.sample_frame(scalar, spec, context)
            stem = f"{scene}/{state}/frame-{index}"
            emitted = core.write_cfa(sampled, store, stem + ".cfa")
            audit_ref = store.json(stem + "-audit.json", emitted["audit"])
            frames.append({"index": index, "inverse_focus": focus, "cfa": emitted["file"], "audit": audit_ref})
            del sampled, scalar
        bundles.append({"scene": scene, "noise_enabled": seed is not None, "seed": seed, "frames": frames})
        print(f"intended noise: {scene}/{state}, five CFA files persisted", flush=True)
    need(len(bundles) == 18 and sum(len(b["frames"]) for b in bundles) == 90
         and sum(budget.requested.values()) == 12_288_000, "exact intended population/work mismatch")
    completed_plan = [(b["scene"], b["seed"], [(f["index"], f["inverse_focus"]) for f in b["frames"]]) for b in bundles]
    need(core.canonical_bytes(completed_plan) == core.canonical_bytes(plan), "completed intended matrix differs from pre-draw plan")
    noise_ref = {"path": Path(args.noise_commission).resolve().relative_to(ROOT).as_posix(),
                 "sha256": args.noise_commission_sha256, "bytes": len(noise_raw)}
    manifest = {"schema": "m194g-software-noise-manifest-v1", "status": "COMPLETE_NOISE_FILES_UNCOMMISSIONED",
                "ref_root": "manifest-parent", "upstream_ref_root": "repository", "contract": contract_ref,
                "float_commission": authority.reference, "noise_commission": noise_ref, "runtime": runtime_ref,
                "source_bindings": sources,
                "geometry": {"width": 320, "height": 240, "cfa_origin": [0, 0], "reference_index": 2,
                             "frame_indices": list(range(5)), "inverse_foci": authority.fixture["inverse_foci"],
                             "forward_similarity": authority.fixture["forward_similarity"]},
                "sensor": {"cfa": "RGGB", "factors_f64": list(core.FACTORS), "gain_dn_per_e": [.25] * 4,
                           "read_noise_e": [4] * 4, "black": [512] * 4, "white": [15360] * 4,
                           "quantization": "ties-even-then-clip-[0,15360]",
                           "wb_rgb_f32": [1.3333333730697632, 1.0, 1.6666666269302368]},
                "bundles": bundles}
    ref = store.json("noise-manifest.json", manifest)
    authority.finish()
    return ref, reads


def partial_work(budget):
    if budget is None:
        return None
    return {"stage": budget.stage, "limits": budget.limits,
            "cpu_seconds": time.process_time() - ENTRY_CPU, "wall_seconds": time.perf_counter() - ENTRY_WALL,
            "requested_variates": sum(budget.requested.values()), "requested_by_component": dict(budget.requested),
            "generator_constructions": budget.generators, "started_frames": budget.started_frames,
            "completed_frames": budget.completed_frames, "output_bytes": budget.output_bytes,
            "live_array_bytes": budget._live_bytes(), "peak_live_array_bytes": budget.peak_array_bytes,
            "tracked_scope": "unique backing ndarrays; includes caller scalar, named scratch and casts; not RSS"}


def recheck_outputs(core, authority_module, store, result):
    """Hash the consumed output references after required payload persistence."""
    def read(ref):
        path = authority_module.relative_path(store.root, ref["path"])
        raw, _ = bound(path, ref["sha256"], ref["bytes"], maximum=1_048_576)
        store.budget.check()
        return raw
    if result["independent_reader"] is not None:
        command = core.strict_json(read(result["independent_reader"]))
        read(command["read"])
        read(command["controls"])
    if result["manifest"] is not None:
        manifest = core.strict_json(read(result["manifest"]))
        read(manifest["contract"])
        read(manifest["runtime"])
        for bundle in manifest["bundles"]:
            for frame in bundle["frames"]:
                read(frame["cfa"])
                read(frame["audit"])


def terminal_write(path, result, budget):
    """Terminal error persistence remains possible after a time refusal; never a success waiver."""
    raw = canonical(result)
    need(len(raw) <= 1_048_576, "terminal result exceeds1MiB")
    old = path.stat().st_size if path.exists() else 0
    if budget is not None:
        need(budget.output_bytes - old + len(raw) <= budget.limits["output_bytes"], "terminal output space exhausted")
    primary = None
    opened = False
    try:
        with path.open("wb") as stream:
            opened = True
            need(stream.write(raw) == len(raw), "short terminal write")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as exc:
        primary = exc
        raise
    finally:
        if budget is not None and opened:
            try:
                # Include partial terminal writes even when flush/fsync refuses.
                budget.output_bytes += path.stat().st_size - old
            except BaseException as exc:
                if primary is None:
                    raise
                primary.add_note("secondary terminal extent capture failure: " + repr(exc))


def secondary_failure(result, where, exc):
    result["status"] = "UNCOMMISSIONED_SOFTWARE_NOISE"
    result["finalization_errors"].append({"type": type(exc).__name__, "message": where + ": " + str(exc)})


def finish_terminal(output, result, budget, store, release, input_reads, context):
    target = output / "result.json"
    try:
        terminal_write(target, result, budget)
    except Exception as exc:
        secondary_failure(result, "terminal persistence", exc)
    else:
        try:
            if budget is not None:
                if result["error"] is None and not result["finalization_errors"]:
                    after, inputs_after = recheck_bindings(release, input_reads)
                    need(after == result["sources_after"] and inputs_after == result["inputs_after"],
                         "source/input closure changed through terminal persistence")
                    context.finish()
                budget.check()
                if store is not None:
                    store.check()
            return
        except Exception as exc:
            secondary_failure(result, "post-terminal check", exc)
    # Keep first persisted bytes under an explicit rejected name before trying
    # the failed terminal record. Neither cleanup nor a second I/O failure may
    # replace result.error or the original post-terminal exception above.
    try:
        if target.exists():
            rejection = output / "result-rejected.json"
            need(not rejection.exists() and target.resolve().parent == output
                 and rejection.resolve().parent == output, "rejected terminal must remain inside new output")
            target.rename(rejection)
    except Exception as exc:
        secondary_failure(result, "retain rejected terminal", exc)
    try:
        result["work"] = partial_work(budget)
        terminal_write(target, result, budget)
    except Exception as exc:
        secondary_failure(result, "failed-status persistence", exc)
    # The released launcher retains stderr even when the filesystem cannot save
    # the final record; this carries both original and secondary error objects.
    print(canonical(result).decode("utf-8"), file=sys.stderr, flush=True)


def run(args):
    result = {"schema": "m194g-software-noise-run-v1", "mode": args.mode,
              "status": "UNCOMMISSIONED_SOFTWARE_NOISE", "invocation": list(sys.orig_argv),
              "execution_release": None, "runtime": None, "sources_before": None, "sources_after": None,
              "inputs_before": None, "inputs_after": None, "index": None, "manifest": None,
              "independent_reader": None, "work": None, "error": None, "finalization_errors": []}
    output = Path(args.output).resolve()
    need(not output.exists(), "new output directory required")
    release = core = reader = budget = context = store = input_reads = None
    progress = {"call_id": "entry"}
    try:
        release, result["execution_release"] = authorize(args)
        core = load_module("software-noise.py", "m194g_software_noise_core", release)
        authority_module = load_module("software-noise-authority.py", "m194g_software_noise_authority", release)
        reader = load_module("independent-noise-reader.py", "m194g_independent_noise_reader", release)
        budget = core.Budget(args.mode, start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
        store = core.OutputStore(output, budget)
        expected_raw, runtime_input = bound(args.runtime, args.runtime_sha256)
        context = core.RuntimeGuard(core.strict_json(expected_raw), budget)
        result["sources_before"] = snapshot(release, store, "sources-before")
        result["inputs_before"] = {r["path"]: {"sha256": r["sha256"], "bytes": r["bytes"]} for r in release["inputs"]}
        runtime_ref = store._write("runtime.json", lambda stream: stream.write(expected_raw))
        result["runtime"] = runtime_ref
        contract_rel = "sources-before/" + PREFIX + "next-noise-contract.md"
        contract_bytes = release["source_bindings"][PREFIX + "next-noise-contract.md"]
        contract_ref = {"path": contract_rel, **contract_bytes}
        if args.mode == "commission":
            result["index"], result["independent_reader"] = commission(
                core, reader, context, store, contract_ref, runtime_ref, result["sources_before"], progress, result)
            result["status"] = "PASS_SOFTWARE_NOISE_COMMISSION"
        else:
            result["manifest"], input_reads = intended(core, authority_module, args, context, store,
                                                       contract_ref, runtime_ref, result["sources_before"], progress)
            for path, binding in input_reads.observed.items():
                rel = Path(path).relative_to(ROOT).as_posix()
                need(rel not in result["inputs_before"] or result["inputs_before"][rel] == binding,
                     "conflicting first-observed prerequisite binding")
                result["inputs_before"][rel] = binding
            result["status"] = "COMPLETE_NOISE_FILES_UNCOMMISSIONED"
    except Exception as exc:
        result["error"] = {"call_id": progress["call_id"], "type": type(exc).__name__,
                           "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        if store is None:
            # OutputStore may create its directory and then refuse its initial
            # clock check. Preserve that original exception in the owned directory.
            try:
                if budget is not None and budget._output_root == output:
                    need(output.is_dir(), "partially initialized output is not a directory")
                else:
                    output.mkdir(parents=True, exist_ok=False)
            except Exception as exc:
                secondary_failure(result, "create failure output", exc)
        if release is not None:
            try:
                after, inputs_after = recheck_bindings(release, input_reads)
                result["sources_after"], result["inputs_after"] = after, inputs_after
                need(after == result["sources_before"] and inputs_after == result["inputs_before"], "source/input closure changed")
                if context is not None:
                    context.finish()
                    if input_reads is not None:
                        input_reads.finish()
                    snapshot(release, store, "sources-after")
                    store.check()
                    if args.mode == "commission" and result["index"] is not None:
                        # Read actual saved trace/array/runtime bytes after the
                        # independent read and all controls have been persisted.
                        reader.recheck_commission_files(store.root / result["index"]["path"],
                                                        result["index"]["sha256"], budget=budget)
                    recheck_outputs(core, authority_module, store, result)
                    budget.check()
            except Exception as exc:
                result["finalization_errors"].append({"type": type(exc).__name__, "message": str(exc)})
        if result["error"] is not None or result["finalization_errors"]:
            result["status"] = "UNCOMMISSIONED_SOFTWARE_NOISE"
        result["work"] = partial_work(budget)
        finish_terminal(output, result, budget, store, release, input_reads, context)
    print(result["status"], flush=True)
    return 0 if result["status"] in ("PASS_SOFTWARE_NOISE_COMMISSION", "COMPLETE_NOISE_FILES_UNCOMMISSIONED") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("commission", "intended"), required=True)
    parser.add_argument("--output", required=True)
    for argument in ("runtime", "execution-release", "float-commission", "noise-commission"):
        required = argument in ("runtime", "execution-release")
        parser.add_argument("--" + argument, required=required)
        parser.add_argument("--" + argument + "-sha256", required=required)
    raise SystemExit(run(parser.parse_args()))
