"""Root-scheduled saved-trace census. No RAW reads, fitting, or warp changes."""
from pathlib import Path
import argparse
import collections
import csv
import hashlib
import json
import math
import struct
import sys
import time

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
SPANS = (1, 2, 4, 8, 16, 32, 64, 96, 128)
STATUSES = ("Ok", "LowContrast", "LowPeak", "Border", "Oob")
ORDER_SHA = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ref(path):
    path = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())


def check_ref(row):
    observed = ref(row["path"])
    require(observed["bytes"] == row["bytes"] and observed["sha256"] == row["sha256"],
            f"bound file changed: {row['path']}")
    return observed


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def exact_count(actual, expected, label):
    require(actual == expected, f"incomplete {label}: {actual} != {expected}")


def scalar(row, width):
    require(isinstance(row, dict) and set(row) == {"value", "bits"}, "float schema")
    bits = row["bits"]
    require(isinstance(bits, str) and len(bits) == width // 4, "float bit width")
    raw = int(bits, 16).to_bytes(width // 8, "little")
    fmt = "<f" if width == 32 else "<d"
    value = struct.unpack(fmt, raw)[0]
    if math.isfinite(value):
        require(row["value"] is not None and struct.pack(fmt, row["value"]) == raw,
                "readable float does not round-trip to retained bits")
    else:
        require(row["value"] is None, "nonfinite float must have readable null")
    return value


def decode_params(row):
    if row is None:
        return None
    result = tuple(scalar(row[k], 64) for k in ("ax", "ay", "g", "rot"))
    require(all(math.isfinite(v) for v in result), "nonfinite retained fit")
    return result


def residual(params, ux, uy, dx, dy):
    if params is None:
        return None
    ax, ay, g, rot = params
    # Explicit descriptive f64 recomputation from saved f32 observations and
    # saved f64 fit. This is not a retained vector, a new fit, or an anchor pull.
    return dx - (ax + g * ux - rot * uy), dy - (ay + rot * ux + g * uy)


def moments():
    return dict(n=0, sum_dx=0.0, sum_dy=0.0, sum_dx2=0.0, sum_dy2=0.0,
                max_abs_dx=0.0, max_abs_dy=0.0)


def add_moment(target, value):
    if value is None:
        return
    x, y = value
    require(math.isfinite(x) and math.isfinite(y), "nonfinite recomputed residual")
    target["n"] += 1
    target["sum_dx"] += x
    target["sum_dy"] += y
    target["sum_dx2"] += x * x
    target["sum_dy2"] += y * y
    target["max_abs_dx"] = max(target["max_abs_dx"], abs(x))
    target["max_abs_dy"] = max(target["max_abs_dy"], abs(y))


def finish_moment(m):
    n = m["n"]
    return dict(n=n, mean_dx=m["sum_dx"] / n if n else None,
                mean_dy=m["sum_dy"] / n if n else None,
                rms_dx=math.sqrt(m["sum_dx2"] / n) if n else None,
                rms_dy=math.sqrt(m["sum_dy2"] / n) if n else None,
                max_abs_dx=m["max_abs_dx"] if n else None,
                max_abs_dy=m["max_abs_dy"] if n else None,
                unit="guide pixels in pair i-to-j displacement coordinates")


def stage_group():
    return dict(passes=0, tiles=collections.Counter(), correlated=0, survivors=0,
                outliers=0, keep_unavailable=0,
                residuals={f"{which}_{population}": moments()
                           for which in ("initial", "final")
                           for population in ("all_ok", "survivors")})


def controls(out):
    path = out / "binding-control.txt"
    path.write_bytes(b"fixed saved-trace binding control\n")
    good = ref(path)
    check_ref(good)
    exact_count(7, 7, "positive control")
    bad_hash_rejected = bad_count_rejected = False
    try:
        check_ref(dict(good, sha256="0" * 64))
    except ValueError:
        bad_hash_rejected = True
    try:
        exact_count(6, 7, "missing-row control")
    except ValueError:
        bad_count_rejected = True
    require(bad_hash_rejected and bad_count_rejected, "validator destroyer did not fail")
    result = dict(positive_binding_pass=True, positive_count_pass=True,
                  bad_hash_rejected=bad_hash_rejected, bad_count_rejected=bad_count_rejected)
    save(out / "controls.json", result)
    return result


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", required=True, type=Path,
                        help="Completed root job directory, containing output/receipt.json")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    job = args.observation.resolve(strict=True)
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists(),
            "fresh workspace output directory required")
    out.mkdir(parents=True, exist_ok=False)
    controls(out)
    output = job / "output"
    completion = read_json(job / "completion.json")
    process = read_json(job / "process.json")
    receipt = read_json(output / "receipt.json")
    require(completion["source_bindings_unchanged"] is True
            and completion["photographic_improvement_claimed"] is False, "root completion authority")
    require(process["exit_code"] == 0 and process["error"] is None
            and process["terminal_job_accounting"] and not process["cleanup_errors"], "completed owned job required")
    require(receipt["status"] == "COMPLETE299_INSECT_PLACEMENT_OBSERVATION"
            and receipt["mechanical_pass"] is True and receipt["all_pairs_retained"] is True
            and receipt["input_preservation"] is True and receipt["guides_unchanged"] is True
            and receipt["real_pair_on_off_exact"] is True, "complete actual observation required")
    require(all(receipt[k] is False for k in ("admission", "quality_claim", "photographic_admission", "physical_placement_claim")),
            "observation must not claim photographic/physical admission")
    require(receipt["source_count"] == 299 and receipt["reference"] == 149
            and tuple(receipt["spans"]) == SPANS and receipt["pair_count"] == 2340, "frozen population/gauge")
    require(receipt["jsonl_bytes"] <= 512 << 20 and receipt["retained_trace_bytes"] <= 256 << 20, "observation bounds")
    bindings = {}
    def bind(row):
        observed = check_ref(row)
        bindings[observed["path"]] = observed
    for row in completion["reports"] + receipt["artifacts"]:
        bind(row)
    for path in (job / "completion.json", job / "process.json", job / "invocation.json",
                 Path(__file__), Path(sys.executable)):
        bind(ref(path))
    bind(completion["build_completion"])
    bind(receipt["executable"])
    bind(receipt["config"])
    require(str((output / "receipt.json").resolve()) in bindings, "receipt missing from root completion")
    for filename in ("pairs.jsonl", "alignment.txt", "inputs-before.json", "inputs-after.json", "guides-before.json"):
        require(str((output / filename).resolve()) in bindings, f"missing actual artifact {filename}")
    before = read_json(output / "inputs-before.json")
    after = read_json(output / "inputs-after.json")
    guides = read_json(output / "guides-before.json")
    require(before["sources"] == after["sources"] and after["unchanged"] is True,
            "saved original identity evidence differs")
    require(len(before["sources"]) == 299 and [s["index"] for s in before["sources"]] == list(range(299)), "saved source order")
    require(guides["sha256"] == after["guide_sha256"] and len(guides["sha256"]) == 299, "saved guide identity evidence")
    require(before["order"]["sha256"] == ORDER_SHA, "frozen original order manifest")
    bind(before["order"])
    require(read_json(before["order"]["path"]) == before["sources"], "saved identities versus literal frozen source manifest")
    bind(before["held_map"])
    # Bind saved original identity evidence; deliberately do not re-open RAWs.
    save(out / "input-bindings.json", dict(files=list(bindings.values()), original_file_reads=0,
         original_preservation_scope="Saved before/after hash and metadata evidence from the bound observation job."))

    expected_pairs = sorted({(i, i + s) for s in SPANS for i in range(299 - s)})
    pair_census = {s: collections.Counter() for s in SPANS}
    groups = {(s, scope): stage_group() for s in SPANS for scope in ("all_attempts", "selected_pass")}
    totals = collections.Counter()
    csv_path = out / "signed-residuals.csv"
    fields = ("pair_ordinal", "i", "j", "span", "pass", "selected_pass", "tile_ordinal", "tx", "ty", "tile_size",
              "fit_center_i_guide_x", "fit_center_i_guide_y", "fit_center_i_active_native_x", "fit_center_i_active_native_y",
              "observation_index", "ux_f32", "uy_f32", "measured_dx_guide", "measured_dy_guide", "survived",
              "initial_residual_dx_guide", "initial_residual_dy_guide", "final_residual_dx_guide", "final_residual_dy_guide")
    with csv_path.open("x", newline="", encoding="utf-8") as csv_file, (output / "pairs.jsonl").open("rb") as stream:
        writer = csv.writer(csv_file)
        writer.writerow(fields)
        for ordinal, line in enumerate(stream):
            require(len(line) <= 8 << 20, "unexpected single-pair JSONL size")
            require(ordinal < len(expected_pairs), "extra requested pair")
            row = json.loads(line)
            i, j = expected_pairs[ordinal]
            require(row["ordinal"] == ordinal and (row["i"], row["j"]) == (i, j), "noncanonical/missing pair")
            span = j - i
            pc = pair_census[span]
            pc["requested"] += 1
            totals["pairs"] += 1
            core = row["core"]
            require((row["unavailable"] is None) != (core is None), "pair outcome exclusivity")
            if core is None:
                pc["unavailable:" + row["unavailable"]] += 1
                totals["unavailable_pairs"] += 1
                continue
            outcome = core["result"]
            require(outcome["state"] in ("fit", "refused"), "pair result state")
            pc[outcome["state"]] += 1
            totals["measured_edges" if outcome["state"] == "fit" else "core_refusals"] += 1
            if outcome["state"] == "refused":
                pc["refusal:" + outcome["reason"]] += 1
            pc["termination:" + core["termination"]] += 1
            passes = core["fine_passes"]
            selected = core["selected_fine_pass"]
            require(selected is None or selected in [p["index"] for p in passes], "invalid selected pass")
            if not passes:
                pc["fine_never_reached"] += 1
            for pass_ordinal, p in enumerate(passes):
                exact_count(p["index"], pass_ordinal, "fine-pass ordinal")
                totals["fine_passes"] += 1
                is_selected = p["index"] == selected
                require(not is_selected or p["result"]["state"] == "fit", "selected refused pass")
                active = [groups[span, "all_attempts"]]
                if is_selected:
                    active.append(groups[span, "selected_pass"])
                for g in active:
                    g["passes"] += 1
                initial = decode_params(p["initial_fit"])
                final = decode_params(p["final_fit"])
                keep = p["keep"]
                ok_count = 0
                status_counts = collections.Counter()
                for tile_ordinal, tile in enumerate(p["tiles"]):
                    exact_count(tile["ordinal"], tile_ordinal, "tile ordinal")
                    status = tile["status"]
                    require(status in STATUSES, "unknown tile status")
                    status_counts[status] += 1
                    totals["tiles"] += 1
                    for g in active:
                        g["tiles"][status] += 1
                    # Validate all actual tile float payloads, including NaNs.
                    for key in ("contrast", "dx", "dy", "peak"):
                        scalar(tile[key], 32)
                    obs = tile["observation"]
                    if status != "Ok":
                        require(obs is None and tile["observation_index"] is None, "rejected tile has an observation")
                        continue
                    require(obs is not None, "correlated tile lacks observation")
                    exact_count(tile["observation_index"], ok_count, "observation index")
                    ux, uy, dx, dy = (scalar(obs[k], 32) for k in ("ux", "uy", "dx", "dy"))
                    require(all(math.isfinite(v) for v in (ux, uy, dx, dy)), "nonfinite correlated observation")
                    require(dx == scalar(tile["dx"], 32) and dy == scalar(tile["dy"], 32), "measurement/observation displacement mismatch")
                    survived = None if keep is None else keep[ok_count]
                    require(survived is None or type(survived) is bool, "keep mask type")
                    ri, rf = residual(initial, ux, uy, dx, dy), residual(final, ux, uy, dx, dy)
                    cx, cy = (scalar(v, 64) for v in tile["fit_center"])
                    writer.writerow((ordinal, i, j, span, p["index"], is_selected, tile_ordinal,
                                     *tile["origin"], tile["size"], cx, cy, 2 * cx + .5, 2 * cy + .5,
                                     ok_count, ux, uy, dx, dy, "unavailable" if survived is None else survived,
                                     *(ri if ri is not None else (None, None)), *(rf if rf is not None else (None, None))))
                    totals["correlated_rows"] += 1
                    for g in active:
                        g["correlated"] += 1
                        g["keep_unavailable" if survived is None else "survivors" if survived else "outliers"] += 1
                        for name, vector in (("initial", ri), ("final", rf)):
                            add_moment(g["residuals"][name + "_all_ok"], vector)
                            if survived is True:
                                add_moment(g["residuals"][name + "_survivors"], vector)
                    ok_count += 1
                for name, status in (("low_contrast", "LowContrast"), ("low_peak", "LowPeak"), ("border", "Border"), ("oob", "Oob")):
                    exact_count(p["census"][name], status_counts[status], "stage " + name)
                if keep is not None:
                    exact_count(len(keep), ok_count, "keep population")
                    exact_count(p["census"]["outlier"], sum(v is False for v in keep), "outlier census")
                else:
                    exact_count(p["census"]["outlier"], 0, "unevaluated outlier census")
                for key, expected in (("initial_residuals", ok_count), ("final_residuals", sum(keep or []))):
                    if p[key] is not None:
                        exact_count(len(p[key]), expected, key)
                if p["result"]["state"] == "fit":
                    exact_count(p["result"]["raw_n"], ok_count, "fit raw_n")
                    exact_count(p["result"]["used"], sum(keep or []), "fit used")
                    exact_count(p["result"]["total"], len(p["tiles"]), "fit tile total")
    for observed, key in (("pairs", "pair_count"), ("fine_passes", "fine_pass_count"), ("tiles", "fine_tile_count"), ("measured_edges", "measured_edges")):
        exact_count(totals[observed], receipt[key], observed)
    exact_count(totals["core_refusals"] + totals["unavailable_pairs"], receipt["refused_pairs"], "refused pairs")
    for span in SPANS:
        exact_count(pair_census[span]["requested"], 299 - span, f"span {span}")
    for g in groups.values():
        g["tiles"] = {name: g["tiles"][name] for name in STATUSES}
        g["residuals"] = {k: finish_moment(v) for k, v in g["residuals"].items()}
    for row in bindings.values():
        check_ref(row)
    summary = dict(status="COMPLETE_DESCRIPTIVE_INSECT_PLACEMENT_CENSUS", complete=True,
                   no_fit=True, RAW_reads=0, physical_placement_claim=False,
                   quality_claim=False, admission=False, crossed_physical_support="UNASSESSED",
                   totals=dict(totals), pairs_by_span={str(k): dict(v) for k, v in pair_census.items()},
                   stages=[dict(span=s, scope=scope, **g) for (s, scope), g in groups.items()],
                   signed_residuals=ref(csv_path), bindings_unchanged=True,
                   command=getattr(sys, "orig_argv", [sys.executable, *sys.argv]),
                   python_version=sys.version, parallel_workers=1,
                   historical_map_placements_exact=receipt["historical_map_placements_exact"],
                   coordinate_contract="Measured dx/dy are reference frame i to moving frame j, in guide pixels; native displacement is twice guide displacement. Fit centers are actual tx+tile/2, not support centroids. Active-native fitting centers use 2*center+0.5. No anchor149 transport is performed.",
                   recomputation="CSV signed residuals are descriptive f64 measured-minus-saved-initial/final-similarity predictions using saved f32 Observation offsets. They were not retained vectors and are not decompositions of the saved scalar RMS.",
                   limitations=["A common grid ordinal across different source i does not identify the same physical structure.",
                                "NCC and its residuals can move under defocus, occlusion, illumination and texture changes without physical motion.",
                                "All correlated tiles, later outliers and surviving tiles are reported separately; no observations are removed from the producing population.",
                                "Crossed field/focus support and actual physical placement remain unestablished; no correction is selected.",
                                "Original source preservation is evidenced by the bound job's saved hashes, not a fresh RAW census."],
                   elapsed_seconds=time.monotonic() - started)
    save(out / "summary.json", summary)
    save(out / "completion.json", dict(status=summary["status"], complete=True,
         reports=[ref(out / name) for name in ("controls.json", "input-bindings.json", "summary.json", "signed-residuals.csv")],
         input_bindings_unchanged=True, physical_placement_claim=False, quality_claim=False))
    print(json.dumps(dict(status=summary["status"], totals=dict(totals), out=str(out))))


if __name__ == "__main__":
    main()
