"""Source-prepared M193b coverage invocation on nine admitted native derivatives.

An external release is mandatory. No image/process dependency is loaded on import.
The frozen registrar is copied byte-for-byte; its first refusal is never repaired.
"""
import time

STARTED = time.monotonic()

import argparse
import copy
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MIB = 1 << 20
NATIVE = HERE / "native-derivative-run.py"
CONSUMER = ROOT / "experiments/m193b-geometry-consumer/consumer.py"
REFERENCE = ROOT / "experiments/M193-cover-overlap/reference.py"
FIXTURES = REFERENCE.with_name("fixtures.json")
CONTRACT = REFERENCE.with_name("contract-v1.json")
SELF = Path(__file__).resolve()
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
CONTROL_IDS = (
    "frozen-three-input-manifest", "identity-retention", "crop-retention-destroyer",
    "rehashed-denominator-destroyer", "restored-identity-retention",
    "complementary-self-registration", "complementary-first-refusal", "exact-gauge-direction-and-order",
)
PINS = {
    NATIVE: "94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a",
    CONSUMER: "41e087797866505cc30384888ed83cd7a94dbcd7b757054433186003b37d2b26",
    REFERENCE: "c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790",
    FIXTURES: "8f5ebcba9688f0d08e71d74f1e8c881702c932ba7d3386e1f9131ffa882ac693",
    CONTRACT: "19421729ac39273a5f61cda5068026f3458ba08c98f0aa954de7c219cbfabf47",
    HERE / "bounded-process.py": "47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b",
    ROOT / "experiments/m12-scorecard/m12-harness.py":
        "6cfb408992f37b225f102da4d62ba836f9c5b67c92bdd418ff460987866a1bb9",
}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def strict(raw):
    def pairs(items):
        answer = {}
        for key, value in items:
            need(key not in answer, "duplicate JSON key")
            answer[key] = value
        return answer

    def finite(value):
        if type(value) is float:
            need(math.isfinite(value), "nonfinite JSON")
        elif type(value) in (dict, list):
            for child in value.values() if type(value) is dict else value:
                finite(child)
    result = json.loads(raw, object_pairs_hook=pairs,
                        parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    finite(result)
    return result


def raw_read(path, cap):
    with Path(path).open("rb") as stream:
        raw = stream.read(cap + 1)
    need(0 < len(raw) <= cap, "bounded bootstrap read")
    return raw


def bound(raw):
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def execute_bytes(path, raw, name):
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def replacement(command, release_sha, request_sha=None):
    need(type(command) is list and command and all(type(x) is str for x in command), "released argv")
    return [release_sha if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else
            request_sha if x == "ACTUAL_COVERAGE_REQUEST_SHA256" else x for x in command]


def boot(args):
    raw = raw_read(args.release, 4 * MIB)
    need(bound(raw)["sha256"] == args.sha256, "external coverage release SHA")
    release = strict(raw)
    need(type(release) is dict and set(release) == set(
        "schema scope source_bindings inputs commands python_executable native prior_work".split()),
        "closed coverage release")
    need(release["schema"] == "m193c-coverage-release-v1" and release["scope"] == "native-nine-coverage",
         "coverage release scope")
    need(set(release["commands"]) == {"parent", "worker"}, "two released commands")
    for path in (*PINS, SELF, HERE / "coverage-run-preregister.md"):
        item = release["source_bindings"].get(path.relative_to(ROOT).as_posix())
        need(type(item) is dict and set(item) == {"sha256", "bytes"}, "required source closure")
        if path in PINS:
            need(item["sha256"] == PINS[path], "frozen dependency source identity")
    need(bound(raw_read(SELF, 4 * MIB)) == release["source_bindings"][SELF.relative_to(ROOT).as_posix()],
         "actual executed coverage source")
    native_raw = raw_read(NATIVE, MIB)
    need(bound(native_raw) == release["source_bindings"][NATIVE.relative_to(ROOT).as_posix()],
         "executed utility source identity")
    n = execute_bytes(NATIVE, native_raw, "m193c_coverage_native_utilities")
    command = replacement(release["commands"]["worker" if args.worker else "parent"],
                          args.sha256, args.request_sha256)
    need(command == sys.orig_argv and Path(command[0]).resolve() == Path(sys.executable).resolve() and
         Path.cwd().resolve() == ROOT, "actual original coverage argv/cwd")
    need(sys.dont_write_bytecode and sys._xoptions.get("faulthandler") is True and
         set(sys._xoptions) == {"faulthandler", "pycache_prefix"}, "exact interpreter options")
    cache = Path(sys._xoptions["pycache_prefix"]).resolve()
    output = Path(args.output).resolve()
    need(output.is_relative_to(HERE) and cache.is_relative_to(output if not args.worker else output.parent),
         "owned output/cache")
    need(not output.exists(), "fresh coverage output; no retry")
    return n, release, output, dict(path=str(Path(args.release).resolve()), **bound(raw))


def make_budget(n, output, prior):
    class CoverageBudget(n.Budget):
        def __init__(self):
            super().__init__(output, prior, STARTED, 0.0)
            self.snapshot_reservation = 0
            self.snapshot_directory = output / "worker/registrar/m193b-geometry-consumer"
            self.cpu_accounting_complete = True
            self.child_cpu_observed = None

        def scan(self):
            if self.output.exists():
                for base, directories, names in os.walk(self.output, followlinks=False):
                    for name in directories:
                        need(not (Path(base) / name).stat(follow_symlinks=False).st_file_attributes & 0x400,
                             "output reparse directory")
                    for name in names:
                        path = Path(base) / name
                        value = n.plain_file(path)
                        if path.parent == self.snapshot_directory and name != "consumer.py":
                            need(name.startswith("tmp"), "only reserved consumer TemporaryFile entries")
                            continue
                        self.extents[str(path)] = max(value.st_size, self.extents.get(str(path), 0))
                        if path.suffix.lower() in (".tif", ".tiff"):
                            self.binary.add(str(path))
            self.last_scan = time.monotonic()

        def work(self):
            value = super().work()
            value["file_bytes"] += self.snapshot_reservation
            return value

        def accounting(self):
            return dict(cpu_accounting_complete=self.cpu_accounting_complete,
                        observed_child_cpu_seconds=self.child_cpu_observed,
                        cpu_scope="terminal Job plus parent" if self.cpu_accounting_complete else
                                  "parent plus observed partial child; total unavailable",
                        snapshot_bytes_reserved_upper_bound=self.snapshot_reservation,
                        retained_output_bytes_measured=sum(self.extents.values()),
                        work_observed_or_lower_bound=self.work())

        def observe_child(self, value):
            accounting = value.get("job_accounting")
            if type(accounting) is dict and n.integer(accounting.get("total_cpu_100ns")):
                self.child_cpu_observed = accounting["total_cpu_100ns"] / 1e7
                self.child_cpu = self.child_cpu_observed
                self.cpu_accounting_complete = value.get("terminal_job_accounting") is True and \
                    n.integer(accounting.get("active_processes")) and accounting["active_processes"] == 0
            self.check(True)
    return CoverageBudget()


def checked_raw(n, files, ref, cap, absolute=False):
    path = files.verify(ref, cap, absolute)
    raw = raw_read(path, cap)
    need(bound(raw) == {k: ref[k] for k in ("sha256", "bytes")}, "same bounded input bytes")
    return raw


def native_authority(n, release, files):
    entry = release["native"]
    n.closed(entry, ("result", "console", "exit", "outer"), "root observed native authority")
    value = files.read(entry["result"])
    need(value.get("schema") == "m193c-native-derivative-run-v1" and
         value.get("status") == "COMPLETE_NINE_DERIVATIVES_AWAITING_COVERAGE" and
         value.get("error") is None and value.get("finalization_errors") == [] and
         value.get("first_refusal") is None and value.get("unvisited") == [], "complete native nine prerequisite")
    outer = files.read(entry["outer"])
    n.closed(outer, ("scope", "command", "release_sha256", "exit_code", "elapsed_wall_seconds",
                     "dependency_before", "dependency_after", "dependency_error", "dependency_supplement_sha256",
                     "admissible_parent_exit"), "root outer")
    need(type(outer["scope"]) is str and outer["scope"] and outer["command"] == value["invocation"] and
         outer["release_sha256"] == value["execution_release"]["sha256"] and
         type(outer["exit_code"]) is int and outer["exit_code"] == 0 and n.number(outer["elapsed_wall_seconds"]) and
         outer["admissible_parent_exit"] is True and outer["dependency_error"] is None,
         "actual native outer association/exit")
    need(checked_raw(n, files, entry["exit"], 64).strip() == b"0", "actual native exit file")
    lines = checked_raw(n, files, entry["console"], 16 * MIB).splitlines()
    lines = [line for line in lines if line.strip()]
    need(lines, "native final stdout present")
    final = n.strict(lines[-1])
    n.closed(final, ("status", "result", "work_through_final_checks", "error", "finalization_errors"),
             "actual native final stdout")
    need(final["status"] == value["status"] and final["error"] is None and final["finalization_errors"] == [] and
         type(final["result"]) is str and Path(final["result"]).is_absolute() and
         Path(final["result"]).resolve() == files.path(entry["result"]), "native terminal result path association")
    prior = files.read(release["prior_work"])
    n.Budget(Path("unused"), prior, STARTED, 0.0)  # Type-check four carried quantities only.
    n.closed(final["work_through_final_checks"], prior.keys(), "native final work")
    for key in prior:
        observed = final["work_through_final_checks"][key]
        need((n.integer(observed) if key.endswith("bytes") else n.number(observed)) and prior[key] >= observed,
             "root carry covers actual native final work: " + key)
    need(prior["wall_seconds"] >= value["prior_work"]["wall_seconds"] + outer["elapsed_wall_seconds"],
         "carry includes actual outer native elapsed")
    native_release = files.read(value["execution_release"], absolute=True)
    supplements = [item for item in native_release["inputs"]
                   if item["sha256"] == outer["dependency_supplement_sha256"]]
    need(n.hash_form(outer["dependency_supplement_sha256"]) and len(supplements) == 1 and
         supplements[0] in release["inputs"], "actual native adjacent-dependency supplement")
    supplement = files.read(supplements[0])
    n.closed(supplement, ("schema", "scope", "required_observation", "files", "runtime_sha256"),
             "adjacent dependency supplement")
    need(supplement["schema"] == "m193c-adjacent-dependency-observation-v1" and
         supplement["runtime_sha256"] == native_release["reader"]["runtime"]["sha256"] and
         type(supplement["files"]) is list and len(supplement["files"]) == 2 and
         outer["dependency_before"] == outer["dependency_after"] == supplement["files"],
         "actual native dependency endpoint observations")
    dependencies = [files.verify(item, 32*MIB, True) for item in supplement["files"]]
    need({path.name for path in dependencies} == {"raw_r.dll", "vcomp140.dll"} and
         dependencies[0].parent == dependencies[1].parent,
         "exact adjacent rawpy dependency pair; no loaded-module claim")
    need(value["sources_before"] == value["sources_after"] == native_release["source_bindings"] and
         value["inputs_before"] == value["inputs_after"] == native_release["inputs"], "native actual source/input stability")
    need(all(release["source_bindings"].get(k) == v for k, v in value["sources_before"].items()),
         "coverage closure includes exercised native sources")
    rows = value["rows"]
    need(type(rows) is list and len(rows) == 9, "complete nine native rows")
    admitted, identities = [], set()
    for ordinal, (row, (index, name, _)) in enumerate(zip(rows, n.POPULATION)):
        need(row["ordinal"] == ordinal and type(row["original_index"]) is int and row["original_index"] == index and
             row["name"] == name and row["error"] is None and row["snapshot_deleted"] is True,
             "exact native original population")
        primary = files.read(row["primary_receipt"], absolute=True)
        reader = files.read(row["independent_read"], absolute=True)
        need(reader.get("schema") == "m193c-native-derivative-independent-frame-v1" and
             reader.get("status") == "PASS_NATIVE_DERIVATIVE_FRAME_ONLY" and reader.get("error") is None and
             reader.get("finalization_errors") == [] and type(reader["original_index"]) is int and
             reader["original_index"] == index, "each actual independent native admission")
        for key in ("snapshot", "primary_receipt", "tiff"):
            need(reader[key] == row[key], "independent row file association: " + key)
        need(reader["request"] == row["read_request"] and
             reader["active_sha256_u16_le"] == primary["source"]["active_sha256_u16_le"] and
             n.hash_form(reader["tiff_pixel_sha256_u16_le"]), "actual independent raw/TIFF identities")
        need(type(reader["checks"]) is list and len(reader["checks"]) == len(n.CHECKS), "eleven native checks")
        for check, expected in zip(reader["checks"], n.CHECKS):
            need(check["id"] == expected and check["pass"] is True, "actual native check: " + expected)
        command = row["independent_launch"]["command"]
        need(reader["invocation"]["orig_argv"] == command, "actual independent original argv")
        for key in ("primary_launch", "independent_launch"):
            n.successful_process(row[key]["observation"], row[key]["command"])
            files.verify(row[key]["observation"]["log"], 16 * MIB, True)
        files.read(row["read_request"], absolute=True)
        tiff = files.verify(row["tiff"], n.TIFF_CAP, True)
        st = n.plain_file(tiff)
        identity = (st.st_dev, st.st_ino)
        need(identity not in identities, "nine distinct actual derivative files")
        identities.add(identity)
        admitted.append(dict(ordinal=ordinal, original_index=index, name=name, tiff=row["tiff"],
                             primary_receipt=row["primary_receipt"], independent_read=row["independent_read"],
                             active_sha256_u16_le=reader["active_sha256_u16_le"],
                             tiff_pixel_sha256_u16_le=reader["tiff_pixel_sha256_u16_le"]))
    return prior, admitted, final


def refusal_observation(exc, consumer_path):
    """Read exception metadata, never modify frames or resume an interrupted loop."""
    frames, loop = [], None
    cursor = exc.__traceback__
    while cursor is not None:
        frame = cursor.tb_frame
        frames.append(dict(file=frame.f_code.co_filename, function=frame.f_code.co_name, line=cursor.tb_lineno))
        if Path(frame.f_code.co_filename).resolve() == consumer_path and frame.f_code.co_name == "construct_overlap_paths":
            loop = frame.f_locals
        cursor = cursor.tb_next
    result = dict(type=type(exc).__name__, code=getattr(exc, "code", None), message=str(exc),
                  traceback="".join(traceback.format_exception(exc)), frames=frames,
                  failure_phase=next((row["function"] for row in reversed(frames) if row["function"] in
                      {"register_to_reference", "extract_features", "decode_input_path", "_scan", "_copy_checked",
                       "maximal_rectangle", "common_row_intervals", "_validate_manifest_structure"}),
                      "constructor-or-library-see-traceback"),
                  constructor_index=None, committed_sources=[], ordered_groups=None, ordered_groups_complete=False,
                  failing_input=None, unvisited_inputs=None)
    if loop is not None:
        result["committed_sources"] = copy.deepcopy(loop.get("sources", []))
        unique = loop.get("unique")
        result["ordered_groups_complete"] = "supports" in loop and "sources" in loop
        if type(unique) is list:
            result["ordered_groups"] = [dict(path=str(item.path.resolve()), sha256=item.digest.hex(),
                                             bytes=item.length, multiplicity=multiplicity)
                                        for item, multiplicity in unique]
            index = loop.get("index")
            # A full prefix followed by overlap refusal is not a failed input.
            if result["ordered_groups_complete"] and type(index) is int and len(result["committed_sources"]) < len(unique):
                result["constructor_index"] = index
                result["failing_input"] = result["ordered_groups"][index]
                result["unvisited_inputs"] = result["ordered_groups"][index + 1:]
            elif result["ordered_groups_complete"] and len(result["committed_sources"]) == len(unique):
                result["unvisited_inputs"] = []
    return result


def associate_refusal(result, rows):
    """Observed prefix association only; no failed row is promoted to a manifest."""
    def aliases(sha, length):
        return [row["original_index"] for row in rows
                if (row["tiff"]["sha256"], row["tiff"]["bytes"]) == (sha, length)]
    for group in result.get("ordered_groups") or []:
        group["original_indices"] = aliases(group["sha256"], group["bytes"])
    for source in result["committed_sources"]:
        source["original_indices"] = aliases(source["source_sha256"], source["byte_length"])
    # failing_input and unvisited_inputs share the group objects above. Do not
    # infer a stage/identity when an earlier scan never constructed these groups.
    return result


def inverse_then(left, right):
    """Exact left^-1 composed with right; Q32 inputs, rational output."""
    q = 1 << 32
    a, b, tx, ty = (Fraction(left[k], q) for k in ("a", "b", "tx", "ty"))
    c, d, ux, uy = (Fraction(right[k], q) for k in ("a", "b", "tx", "ty"))
    den = a*a + b*b
    need(den > 0, "nonsingular gauge conversion")
    values = ((a*c+b*d)/den, (a*d-b*c)/den,
              (a*(ux-tx)+b*(uy-ty))/den, (-b*(ux-tx)+a*(uy-ty))/den)
    return {key: dict(numerator=x.numerator, denominator=x.denominator)
            for key, x in zip(("a", "b", "tx", "ty"), values)}


def gauge_rows(manifest, rows):
    by_hash = {}
    for row in rows:
        by_hash.setdefault((row["tiff"]["sha256"], row["tiff"]["bytes"]), []).append(row)
    result = []
    for source in manifest["sources"]:
        aliases = by_hash.get((source["source_sha256"], source["byte_length"]), [])
        need(len(aliases) == source["multiplicity"], "manifest source-to-original association")
        result.extend(dict(original_index=row["original_index"], tiff=row["tiff"],
                           reference=source["reference"], source_to_reference_q32=source["source_to_reference_q32"],
                           registration=source["registration"], valid_center_guard_q8=source["valid_center_guard_q8"])
                      for row in aliases)
    need(len(result) == 9 and {r["original_index"] for r in result} == {r["original_index"] for r in rows},
         "all original associations retained")
    anchor = next(row["source_to_reference_q32"] for row in result if row["original_index"] == 52)

    for row in result:
        row["source_to_original_52_exact_derived"] = inverse_then(anchor, row["source_to_reference_q32"])
        row["original_52_to_source_pull_exact_derived"] = inverse_then(row["source_to_reference_q32"], anchor)
    return sorted(result, key=lambda row: row["original_index"])


def runtime(consumer):
    v1 = consumer.v1
    return dict(python=platform.python_version(), numpy=consumer.np.__version__,
                opencv=v1.cv2.__version__,
                opencv_build_information_sha256=hashlib.sha256(v1.cv2.getBuildInformation().encode()).hexdigest(),
                tifffile=consumer.tifffile.__version__)


def private_controls(n, c, directory, save, result, check):
    v1, np, cv2 = c.v1, c.np, c.v1.cv2
    fixtures = n.strict(raw_read(FIXTURES, MIB))

    def record(name, ok, evidence):
        row = dict(id=name, passed=bool(ok), evidence=evidence)
        result["controls"].append(row)
        save(directory / ("control-" + name + ".json"), row)
        need(ok, "coverage control: " + name)
        check()

    def write(index, pixels):
        path = directory / f"fixture-{index}.tiff"
        raw = v1.encode_tiff(pixels)
        need(len(raw) <= MIB, "fixed small TIFF bound")
        with path.open("xb") as stream:
            need(stream.write(raw) == len(raw), "full private TIFF write")
        result["fixtures"].append(dict(path=str(path), **bound(raw)))
        check()
        return path

    base = v1.synthetic_rgb()
    paths = [write(0, base), write(1, v1.warp_synthetic(base, scale=.985, rotation_degrees=.35, tx=3.25, ty=-2.5)),
             write(2, v1.warp_synthetic(base, scale=1.018, rotation_degrees=-.25, tx=-4., ty=3.))]
    del base
    manifest, binding = c.construct_overlap_paths(paths)
    record(CONTROL_IDS[0], manifest == fixtures["synthetic_overlap"], manifest)

    def descriptor(m, crop=False):
        return v1.make_output_grid(m, arm_id="cropped-grid" if crop else "identity-grid",
            expected_width=m["native_width"] - (12 if crop else 0),
            expected_height=m["native_height"] - (10 if crop else 0),
            derivation_kind="predeclared_program_grid" if crop else "identity_reference_grid")
    identity = c.output_retention(manifest, descriptor(manifest), binding)
    record(CONTROL_IDS[1], identity == fixtures["output_retention"]["identity"], identity)
    crop = c.output_retention(manifest, descriptor(manifest, True), binding)
    record(CONTROL_IDS[2], crop == fixtures["output_retention"]["cropped"], crop)
    bad = copy.deepcopy(manifest)
    box = bad["common_overlap"]
    box.update(x=box["x"] + 2, y=box["y"] + 2, width=20, height=20, area_pixels=400)
    bad["manifest_sha256"] = v1.manifest_digest(bad)
    bad_grid = descriptor(bad, True)
    old = v1.output_retention(bad, bad_grid)
    refused = None
    try:
        c.output_retention(bad, bad_grid, binding)
    except c.ContractError as exc:
        refused = dict(code=exc.code, message=str(exc))
    record(CONTROL_IDS[3], old["field_of_view_verdict"] == "PASS" and old["retained_pixels"] == 400 and
           old["denominator_pixels"] == 400 and refused is not None and
           refused["code"] == "UNMEASURED_DENOMINATOR_UNDEFINED", dict(old=old, actual_refusal=refused))
    restored = c.output_retention(manifest, descriptor(manifest), binding)
    record(CONTROL_IDS[4], restored == identity, restored)
    rng = np.random.default_rng(731943)
    texture = cv2.GaussianBlur(rng.uniform(3000, 62000, (288, 384)).astype(np.float32), (0, 0), .7)
    defocused = cv2.GaussianBlur(texture, (0, 0), 12.)
    left, right = defocused.copy(), defocused.copy()
    left[:, :184], right[:, 200:] = texture[:, :184], texture[:, 200:]
    rgb = lambda a: np.repeat(np.clip(np.rint(a), 0, 65535).astype(np.uint16)[..., None], 3, axis=2)
    first = rgb(left)
    focus_paths = [write(3, first), write(4, rgb(right))]
    features = v1.extract_features(first)
    matched = v1.register_to_reference(features, features)[1]
    record(CONTROL_IDS[5], matched["mutual_match_count"] == 256 and
           matched["heldout_rms_reference_px"] == "0.000000000", matched)
    del first, features, texture, defocused, left, right
    failure = None
    try:
        c.construct_overlap_paths(focus_paths)
    except c.ContractError as exc:
        failure = refusal_observation(exc, Path(c.__file__).resolve())
    record(CONTROL_IDS[6], failure is not None and failure["code"] == "UNMEASURED_INPUT_REGISTRATION_INADEQUATE" and
           failure["constructor_index"] == 1 and len(failure["committed_sources"]) == 1 and
           len(failure["ordered_groups"]) == 2 and failure["ordered_groups_complete"] is True and
           failure["unvisited_inputs"] == [], failure)
    q = 1 << 32
    anchor = dict(a=3*q//2, b=q//2, tx=7*q, ty=-3*q)
    source = dict(a=q, b=-q//2, tx=-2*q, ty=5*q)
    forward, pull = inverse_then(anchor, source), inverse_then(source, anchor)
    def literal(values):
        return {key: dict(numerator=num, denominator=den)
                for key, (num, den) in zip(("a", "b", "tx", "ty"), values)}
    expected_forward = literal(((1, 2), (-1, 2), (-19, 5), (33, 5)))
    expected_pull = literal(((1, 1), (1, 1), (52, 5), (-14, 5)))
    # Active wrong-order map is S composed with A^-1, not the reverse pull.
    ai = inverse_then(anchor, dict(a=q, b=0, tx=0, ty=0))
    ia, ib, itx, ity = (Fraction(ai[k]["numerator"], ai[k]["denominator"])
                        for k in ("a", "b", "tx", "ty"))
    sa, sb, stx, sty = (Fraction(source[k], q) for k in ("a", "b", "tx", "ty"))
    wrong_values = (sa*ia - sb*ib, sa*ib + sb*ia, sa*itx - sb*ity + stx, sb*itx + sa*ity + sty)
    wrong_order = literal(tuple((x.numerator, x.denominator) for x in wrong_values))
    wrong_sign = dict(source, b=-source["b"])
    record(CONTROL_IDS[7], forward == expected_forward and pull == expected_pull and
           wrong_order == literal(((1, 2), (-1, 2), (-4, 1), (10, 1))) and wrong_order != expected_forward and
           inverse_then(anchor, wrong_sign) != expected_forward,
           dict(scope="exact arithmetic reporting control; not observed native placement truth",
                anchor_q32=anchor, source_q32=source, forward=forward, pull=pull,
                reversed_order=wrong_order,
                reversed_rotation_sign=inverse_then(anchor, wrong_sign)))
    need([r["id"] for r in result["controls"]] == list(CONTROL_IDS), "complete fixed eight controls")


def publish(n, path, result, save, final_checks, summary, after_stdout):
    """Retain first positive bytes, revoke canonical success on any late failure."""
    try:
        save(path, result)
        final_checks()
        text = json.dumps(summary(), allow_nan=False)
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
        after_stdout()
    except BaseException:
        original = traceback.format_exc()
        if result.get("error") is None:
            result["error"] = original
        else:
            result["finalization_errors"].append(original)
        result["status"] = "REFUSED"
        try:
            if path.exists():
                first = path.with_name(path.stem + "-first-publication.json")
                need(not first.exists(), "fresh retained first publication")
                path.rename(first)
            save(path, result)
        except BaseException:
            result["finalization_errors"].append(traceback.format_exc())
        try:
            sys.stderr.write(json.dumps(dict(error=result["error"], finalization_errors=result["finalization_errors"]),
                                        allow_nan=False) + "\n")
            sys.stderr.flush()
        except BaseException:
            pass
        return False
    return result["status"] not in ("REFUSED", "REGISTRAR_REFUSED")


def worker(n, release, output, release_ref, args):
    output.mkdir()
    result = dict(schema="m193c-coverage-worker-v1", status="REFUSED", command=sys.orig_argv,
                  execution_release=release_ref, request=None, runtime_before=None, runtime_after=None,
                  controls=[], fixtures=[], native_manifest=None, original_gauges=None, first_refusal=None,
                  native_stage="unvisited", error=None, finalization_errors=[])
    # Parent owns CPU/whole-tree accounting. This callback enforces only the
    # released remaining wall locally; the encompassing Job has the same clock ceiling.
    remaining = None

    def check():
        if remaining is not None:
            need(time.monotonic() - STARTED <= remaining["wall_seconds"], "worker remaining wall")

    def save(path, value):
        raw = n.json_bytes(value)
        need(len(raw) <= 4 * MIB, "bounded worker metadata")
        with path.open("xb") as stream:
            need(stream.write(raw) == len(raw), "worker metadata write")
            stream.flush(); os.fsync(stream.fileno())
        check()

    consumer = None
    try:
        raw = raw_read(args.request, MIB)
        need(bound(raw)["sha256"] == args.request_sha256, "external worker request SHA")
        request = n.strict(raw)
        n.closed(request, ("schema", "execution_release", "native_rows", "remaining_limits", "snapshot_reservation_bytes"),
                 "coverage worker request")
        need(request["schema"] == "m193c-coverage-request-v1" and request["execution_release"] == release_ref,
             "actual worker request/release association")
        result["request"] = dict(path=str(Path(args.request).resolve()), **bound(raw))
        remaining = request["remaining_limits"]
        need(type(request["native_rows"]) is list and len(request["native_rows"]) == 9 and
             request["snapshot_reservation_bytes"] == sum(r["tiff"]["bytes"] for r in request["native_rows"]) + 5*MIB,
             "fixed snapshot reservation")
        need({k: os.environ.get(k) for k in THREADS} == dict.fromkeys(THREADS, "2"), "pre-import thread settings")
        for source, expected in release["source_bindings"].items():
            need(n.file_digest(n.repo_path(source), 32*MIB, check) == expected, "worker current source closure")
        for original in (CONSUMER, REFERENCE):
            destination = output / "registrar" / original.parent.name / original.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            raw = raw_read(original, MIB)
            need(bound(raw) == release["source_bindings"][n.relative(original)], "exact copied registrar bytes")
            with destination.open("xb") as stream:
                need(stream.write(raw) == len(raw), "registrar copy write")
        copied = output / "registrar/m193b-geometry-consumer/consumer.py"
        consumer = execute_bytes(copied, raw_read(copied, MIB), "m193c_actual_frozen_consumer")
        result["runtime_before"] = runtime(consumer)
        expected = n.strict(raw_read(CONTRACT, MIB))["reference_environment"]
        need(result["runtime_before"] == expected, "exact frozen registrar runtime; no fallback")
        private_controls(n, consumer, output, save, result, check)
        result["native_stage"] = "running"
        try:
            manifest, binding = consumer.construct_overlap_paths([Path(r["tiff"]["path"]) for r in request["native_rows"]])
        except consumer.ContractError as exc:
            result["first_refusal"] = associate_refusal(refusal_observation(exc, copied.resolve()),
                                                       request["native_rows"])
            result["native_stage"] = "refused"
            result["status"] = "REGISTRAR_REFUSED"
            result["error"] = result["first_refusal"]["traceback"]
        else:
            need(consumer.validate_overlap(manifest, binding) == manifest, "actual complete in-process binding")
            result["native_manifest"] = manifest
            result["original_gauges"] = gauge_rows(manifest, request["native_rows"])
            result["native_stage"] = "complete"
            result["status"] = "COMPLETE_NINE_INPUT_REGISTRATION_ONLY"
    except BaseException:
        result["error"] = traceback.format_exc()

    def final_checks():
        if consumer is not None:
            result["runtime_after"] = runtime(consumer)
            need(result["runtime_after"] == result["runtime_before"], "registrar runtime unchanged")
        for source, expected in release["source_bindings"].items():
            need(n.file_digest(n.repo_path(source), 32*MIB, check) == expected, "final source closure")
        if consumer is not None:
            for original in (CONSUMER, REFERENCE):
                path = output / "registrar" / original.parent.name / original.name
                need(n.file_digest(path, MIB, check) == release["source_bindings"][n.relative(original)],
                     "saved registrar source unchanged")
        check()
    try:
        final_checks()
    except BaseException:
        result["finalization_errors"].append(traceback.format_exc())
        result["status"] = "REFUSED"
    ok = publish(n, output / "result.json", result, save, final_checks,
                 lambda: dict(status=result["status"], result=str(output / "result.json"), error=result["error"],
                              finalization_errors=result["finalization_errors"]), check)
    return 0 if ok else 1


def parent(n, release, output, release_ref, args):
    # Authenticate the explicit carry before creating outputs; an absent carry is
    # a launch refusal, never permission to substitute zero prior work.
    prior_ref = release["prior_work"]
    n.closed(prior_ref, ("path", "sha256", "bytes"), "prior-work FileRef")
    prior_raw = raw_read(n.repo_path(prior_ref["path"]), MIB)
    need(bound(prior_raw) == {k: prior_ref[k] for k in ("sha256", "bytes")}, "root prior-work bytes")
    prior = n.strict(prior_raw)
    budget = make_budget(n, output, prior)
    output.mkdir()
    files = n.Files(budget)
    result = dict(schema="m193c-coverage-run-v1", status="REFUSED", command=sys.orig_argv,
                  execution_release=release_ref, native=release["native"], prior_work=prior,
                  sources_before=release["source_bindings"], sources_after=None,
                  inputs_before=release["inputs"], inputs_after=None, native_final_stdout=None,
                  admitted_inputs=None, request=None, child=None, environment=None, removed_environment=None,
                  worker_result=None, first_refusal=None, work=None, error=None, finalization_errors=[])
    try:
        budget.check(True)
        n.binding_map(release["source_bindings"], files)
        need(type(release["inputs"]) is list, "release input list")
        for ref in release["inputs"]:
            files.verify(ref, n.TIFF_CAP)
        for ref in (*release["native"].values(), release["prior_work"]):
            need(ref in release["inputs"], "required native/prior authority in release inputs")
        exe = files.verify(release["python_executable"], 32*MIB, True)
        need(exe == Path(sys.executable).resolve(), "actual pinned Python executable")
        actual_prior, rows, final = native_authority(n, release, files)
        need(actual_prior == prior, "prior work parsed from same bytes")
        result["native_final_stdout"], result["admitted_inputs"] = final, rows
        budget.snapshot_reservation = sum(row["tiff"]["bytes"] for row in rows) + 5*MIB
        budget.check(True)  # Entire reservation is charged before any TIFF constructor.
        limits = budget.limits()
        request = dict(schema="m193c-coverage-request-v1", execution_release=release_ref,
                       native_rows=rows, remaining_limits=limits,
                       snapshot_reservation_bytes=budget.snapshot_reservation)
        request_path = output / "request.json"
        budget.save(request_path, request)
        request_ref = files.bind(request_path, MIB, True)
        result["request"] = request_ref
        command = replacement(release["commands"]["worker"], args.sha256, request_ref["sha256"])
        need(command[0] == str(exe) and command.count("--worker") == 1 and
             command[command.index("--request") + 1] == str(request_path) and
             command[command.index("--output") + 1] == str(output / "worker"), "actual worker paths")
        process, api = n.load_process(release, files)
        env, removed = process.clean_environment()
        removed += [key for key in env if key.upper().startswith("PYTHON")]
        env = {key: value for key, value in env.items() if key not in removed}
        env.update(dict.fromkeys(THREADS, "2"))
        result["environment"], result["removed_environment"] = env, sorted(set(removed))
        # Recompute after preparation; do not give preparation time back to child.
        fresh_limits = budget.limits()
        actual_limits = {key: min(limits[key], fresh_limits[key]) for key in limits}
        budget.cpu_accounting_complete = False
        observation = process.run(command, env, ROOT, output / "worker.log", api=api,
                                  check=budget.check, **actual_limits)
        result["child"] = observation
        budget.observe_child(observation)
        worker_path = output / "worker/result.json"
        if worker_path.exists():
            result["worker_result"] = files.bind(worker_path, 4*MIB, True)
            outcome = files.read(result["worker_result"], absolute=True)
            result["first_refusal"] = outcome.get("first_refusal")
        n.successful_process(observation, command)
        need(budget.cpu_accounting_complete and result["worker_result"] is not None,
             "complete actual worker accounting/result")
        need(outcome["schema"] == "m193c-coverage-worker-v1" and
             outcome["status"] == "COMPLETE_NINE_INPUT_REGISTRATION_ONLY" and
             outcome["command"] == command and outcome["request"] == request_ref and
             outcome["execution_release"] == release_ref and outcome["error"] is None and
             outcome["finalization_errors"] == [] and outcome["native_stage"] == "complete" and
             [c["id"] for c in outcome["controls"]] == list(CONTROL_IDS) and
             all(c["passed"] is True for c in outcome["controls"]), "actual complete controlled coverage")
        need(len(outcome["original_gauges"]) == 9 and outcome["native_manifest"]["input_count"] == 9,
             "all nine actual coverage rows")
        result["status"] = "COMPLETE_NINE_INPUT_REGISTRATION_ONLY"
    except BaseException:
        result["error"] = traceback.format_exc()

    def final_checks():
        files.recheck()
        budget.check(True)
        need(result["status"] != "COMPLETE_NINE_INPUT_REGISTRATION_ONLY" or budget.cpu_accounting_complete,
             "success requires complete terminal CPU")
    try:
        final_checks()
        result["sources_after"], result["inputs_after"] = release["source_bindings"], release["inputs"]
    except BaseException:
        result["finalization_errors"].append(traceback.format_exc())
        result["status"] = "REFUSED"
    result["work"] = budget.accounting()
    ok = publish(n, output / "result.json", result, budget.save, final_checks,
                 lambda: dict(status=result["status"], result=str(output / "result.json"),
                              work_through_final_checks=budget.accounting(), error=result["error"],
                              finalization_errors=result["finalization_errors"]), lambda: budget.check(True))
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--request")
    parser.add_argument("--request-sha256")
    args = parser.parse_args()
    need(bool(args.worker) == (args.request is not None and args.request_sha256 is not None), "worker request only")
    n, release, output, ref = boot(args)
    return worker(n, release, output, ref, args) if args.worker else parent(n, release, output, ref, args)


if __name__ == "__main__":
    raise SystemExit(main())
