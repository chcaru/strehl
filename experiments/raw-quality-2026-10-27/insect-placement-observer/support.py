"""Conditional footprint transport for all fixed-span observer tile slots; no fit."""
from pathlib import Path
import argparse
import collections
import csv
import hashlib
import importlib.util
import json
import math
import struct
import sys
import time

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
HELPER = AREA / "summarize.py"
HELPER_SHA = "8bf5b849bacd1107ae6e7d780e0fb52e670815e7abf2cc5f3cf3d1dafe97030b"
if hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA:
    raise RuntimeError("frozen saved-data helper changed")
spec = importlib.util.spec_from_file_location("insect_support_frozen_helpers", HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
require, ref, save, read_json = h.require, h.ref, h.save, h.read_json
SPANS = (1, 8, 32)
ANCHOR_PAIR = (149, 150)
TILES = 96


def parse_map(path):
    headers, maps = {}, {}
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    require(lines[0] == "strehl-warpmap 1", "map version")
    for line in lines[1:]:
        tokens = line.split("#", 1)[0].split()
        if not tokens:
            continue
        if tokens[0].isdigit():
            index = int(tokens[0])
            require(index not in maps, "duplicate map index")
            if tokens[1] == "placed":
                require(len(tokens) == 6, "placed map schema")
                values = tuple(struct.unpack("<d", int(x, 16).to_bytes(8, "little"))[0] for x in tokens[2:])
                require(all(math.isfinite(x) for x in values) and values[0] ** 2 + values[1] ** 2 > 0,
                        "invalid map similarity")
                maps[index] = values
            else:
                require(tokens[1] == "refused", "unknown placement state")
                maps[index] = None
        else:
            headers[tokens[0]] = tokens[1:]
    require(headers["reference"] == ["149"] and headers["frames"] == ["299"]
            and headers["end"] == ["299"] and set(maps) == set(range(299)), "complete map gauge/population")
    width, height = (int(v) for v in headers["plane"][0].split("x"))
    require((width, height) == (3516, 2344), "held guide geometry")
    return maps, (width / 2, height / 2)


def inverse_point(point, transform, center):
    ar, ai, br, bi = transform
    den = ar * ar + ai * ai
    x, y = point[0] - center[0] - br, point[1] - center[1] - bi
    return center[0] + (ar * x + ai * y) / den, center[1] + (ar * y - ai * x) / den


def forward_point(point, transform, center):
    ar, ai, br, bi = transform
    x, y = point[0] - center[0], point[1] - center[1]
    return center[0] + ar * x - ai * y + br, center[1] + ai * x + ar * y + bi


def footprint(tx, ty, size):
    # Union bounding square of the guide sample cells, not the fit-center
    # convention tx+size/2. Native guide centroid is 2*u+0.5.
    left, top, right, bottom = tx - .5, ty - .5, tx + size - .5, ty + size - .5
    return [(left, top), (right, top), (right, bottom), (left, bottom)]


def area(poly):
    if len(poly) < 3:
        return 0.0
    # Shift to the first vertex to avoid cancellation of large absolute coords.
    ox, oy = poly[0]
    return abs(sum((poly[k][0] - ox) * (poly[k + 1][1] - oy)
                   - (poly[k][1] - oy) * (poly[k + 1][0] - ox)
                   for k in range(1, len(poly) - 1))) / 2


def cross(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def intersection(subject, clip):
    # Sutherland-Hodgman for CCW convex polygons. A complex similarity has
    # positive determinant, so transport preserves the declared corner order.
    result = list(subject)
    for a, b in zip(clip, clip[1:] + clip[:1]):
        previous, result = result, []
        if not previous:
            break
        s = previous[-1]
        ds = cross(a, b, s)
        for e in previous:
            de = cross(a, b, e)
            if (ds >= 0) != (de >= 0):
                t = ds / (ds - de)
                result.append((s[0] + t * (e[0] - s[0]), s[1] + t * (e[1] - s[1])))
            if de >= 0:
                result.append(e)
            s, ds = e, de
    return result


def overlap(a, b):
    aa, ab, ai = area(a), area(b), area(intersection(a, b))
    require(aa > 0 and ab > 0 and math.isfinite(ai), "invalid polygon area")
    # Numerical sanity only. Do not clamp/threshold the reported overlap.
    require(0 <= ai <= min(aa, ab) + 1e-8 * max(aa, ab), "intersection exceeds footprint")
    return dict(source_area=aa, anchor_template_area=ab, intersection_area=ai,
                source_fraction=ai / aa, template_fraction=ai / ab,
                iou=ai / (aa + ab - ai))


def controls(out):
    square = footprint(10, 20, 4)
    center = (32.0, 24.0)
    identity = [inverse_point(p, (1, 0, 0, 0), center) for p in square]
    require(identity == square and overlap(identity, square)["iou"] == 1, "identity control")
    translated = [inverse_point(p, (1, 0, 1, 0), center) for p in square]
    result = overlap(translated, square)
    require(result["intersection_area"] == 12 and result["source_fraction"] == .75
            and result["iou"] == .6, "known translated inverse overlap")
    require(overlap(footprint(100, 100, 4), square)["intersection_area"] == 0, "disjoint control")
    known = (1.25, .25, 3.0, -2.0)
    source_point, expected_anchor = (48.5, 19.5), (42.0, 20.0)
    good = inverse_point(source_point, known, center)
    good_error = math.dist(good, expected_anchor)
    wrong_direction_error = math.dist(forward_point(source_point, known, center), expected_anchor)
    wrong_center_error = math.dist(inverse_point(source_point, known, (32.5, 24.5)), expected_anchor)
    require(good_error <= 1e-12 and wrong_direction_error > 1e-3 and wrong_center_error > 1e-3,
            "inverse/center foils failed to distinguish literal known point")
    restored = [inverse_point(forward_point(p, known, center), known, center) for p in square]
    require(max(math.dist(a, b) for a, b in zip(restored, square)) <= 1e-12, "polygon corner roundtrip")
    require(tuple(sum(p[k] for p in square) / 4 for k in (0, 1)) == (11.5, 21.5), "sample support centroid")
    save(out / "controls.json", dict(identity_exact=True, translated_overlap=result,
         disjoint_exact=True, known_inverse_error=good_error, wrong_direction_error=wrong_direction_error,
         wrong_center_error=wrong_center_error, foils_rejected=True,
         scope="Exact geometry controls only; not calibration of the photographic warp."))


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    observation, summary_job = args.observation.resolve(strict=True), args.summary.resolve(strict=True)
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists(), "fresh workspace output required")
    out.mkdir(parents=True, exist_ok=False)
    controls(out)
    bindings = {}
    def bind(row):
        observed = h.check_ref(row)
        bindings[observed["path"]] = observed
    for job in (observation, summary_job):
        complete = read_json(job / "completion.json")
        process = read_json(job / "process.json")
        require(complete["source_bindings_unchanged"] and not complete["photographic_improvement_claimed"], "root completion authority")
        require(process["exit_code"] == 0 and process["error"] is None
                and process["terminal_job_accounting"] and not process["cleanup_errors"], "terminal successful parent job")
        for row in complete["reports"]:
            bind(row)
        bind(complete["build_completion"])
        for name in ("completion.json", "process.json", "invocation.json"):
            bind(ref(job / name))
    saved_summary = read_json(summary_job / "output/summary.json")
    require(saved_summary["status"] == "COMPLETE_DESCRIPTIVE_INSECT_PLACEMENT_CENSUS"
            and saved_summary["complete"] and saved_summary["bindings_unchanged"], "completed summary")
    summary_inputs = read_json(summary_job / "output/input-bindings.json")["files"]
    require(str((observation / "output/receipt.json").resolve()) in {str(Path(r["path"]).resolve()) for r in summary_inputs},
            "summary belongs to another observation")
    for row in summary_inputs:
        bind(row)
    for row in read_json(summary_job / "output/completion.json")["reports"]:
        bind(row)
    output = observation / "output"
    receipt = read_json(output / "receipt.json")
    require(receipt["status"] == "COMPLETE299_INSECT_PLACEMENT_OBSERVATION"
            and receipt["mechanical_pass"] and receipt["input_preservation"]
            and receipt["historical_map_placements_exact"] and receipt["all_pairs_retained"], "actual complete observation")
    require(receipt["align_config"]["fine_iters"] == 1 and receipt["align_config"]["fine_grid"] == [12, 8]
            and receipt["align_config"]["fine_tile"] == 128, "frozen normal tile population")
    for row in receipt["artifacts"]:
        bind(row)
    input_record = read_json(output / "inputs-before.json")
    bind(input_record["held_map"])
    maps, center = parse_map(input_record["held_map"]["path"])
    observed_maps, observed_center = parse_map(output / "alignment.txt")
    require(observed_maps == maps and observed_center == center, "parsed historical and observed placements differ")
    require(maps[149] is not None and receipt["reference"] == 149 and receipt["source_count"] == 299, "anchor gauge")
    for path in (Path(__file__), HELPER, Path(sys.executable)):
        bind(ref(path))
    trace_path = output / "pairs.jsonl"
    require(str(trace_path.resolve()) in bindings
            and str((output / "receipt.json").resolve()) in bindings, "summary/observation binding join")
    # First pass retains only the predeclared literal anchor template. No
    # search for a better reference pair, status, or crop is allowed.
    anchor = None
    with trace_path.open("rb") as stream:
        for line in stream:
            row = json.loads(line)
            if (row["i"], row["j"]) == ANCHOR_PAIR:
                require(row["core"] is not None and len(row["core"]["fine_passes"]) == 1,
                        "fixed anchor pair has no complete single fine attempt")
                anchor = row["core"]["fine_passes"][0]["tiles"]
                break
    require(anchor is not None and len(anchor) == TILES
            and [t["ordinal"] for t in anchor] == list(range(TILES)), "fixed anchor96 geometry")
    templates = []
    for tile in anchor:
        poly = footprint(*tile["origin"], tile["size"])
        templates.append(dict(ordinal=tile["ordinal"], origin=tile["origin"], size=tile["size"],
             actual_anchor_pair_status=tile["status"], source_guide_corners=poly,
             anchor_guide_corners=[inverse_point(p, maps[149], center) for p in poly]))
    save(out / "anchor-templates.json", dict(pair=ANCHOR_PAIR, map149=maps[149], templates=templates))
    census = {span: collections.Counter() for span in SPANS}
    continuous = {span: {k: dict(n=0, sum=0.0, min=None, max=None)
                        for k in ("source_fraction", "template_fraction", "iou")} for span in SPANS}
    per_ordinal = {(span, ordinal): collections.Counter() for span in SPANS for ordinal in range(TILES)}
    expected_all = sorted({(i, i + s) for s in h.SPANS for i in range(299 - s)})
    csv_path = out / "tile-support.csv"
    count = 0
    with csv_path.open("x", newline="", encoding="utf-8") as f, trace_path.open("rb") as stream:
        writer = csv.writer(f)
        writer.writerow(("pair_ordinal", "i", "j", "span", "tile_ordinal", "pair_state", "pair_reason", "tile_status", "survived",
                         "actual_geometry", "geometry_unavailable_reason", "tx", "ty", "size", "source_centroid_guide_x", "source_centroid_guide_y",
                         "anchor_centroid_guide_x", "anchor_centroid_guide_y", "anchor_centroid_active_native_x", "anchor_centroid_active_native_y",
                         "anchor_guide_corners_json", "source_area_guide2", "anchor_template_area_guide2", "intersection_area_guide2",
                         "source_fraction", "template_fraction", "iou"))
        for ordinal, line in enumerate(stream):
            row = json.loads(line)
            require(ordinal < len(expected_all) and row["ordinal"] == ordinal
                    and (row["i"], row["j"]) == expected_all[ordinal], "complete canonical trace")
            count += 1
            i, j = row["i"], row["j"]
            span = j - i
            if span not in SPANS:
                continue
            c = census[span]
            c["pairs"] += 1
            core = row["core"]
            pair_state = "unavailable" if core is None else core["result"]["state"]
            reason = row["unavailable"] if core is None else core["result"].get("reason")
            c["pair_" + pair_state] += 1
            passes = [] if core is None else core["fine_passes"]
            require(len(passes) <= 1, "frozen normal fine_iters1 changed")
            tiles = None if not passes else passes[0]["tiles"]
            if tiles is not None:
                require(len(tiles) == TILES and [t["ordinal"] for t in tiles] == list(range(TILES)), "all96 actual tile attempts")
            for tile_ordinal in range(TILES):
                c["tile_slots"] += 1
                oc = per_ordinal[span, tile_ordinal]
                oc["slots"] += 1
                tile = None if tiles is None else tiles[tile_ordinal]
                status = "not-attempted" if tile is None else tile["status"]
                c["status_" + status] += 1
                oc["status_" + status] += 1
                survived = "unavailable"
                if tile is not None and tile["observation_index"] is not None and passes[0]["keep"] is not None:
                    survived = passes[0]["keep"][tile["observation_index"]]
                    c["survivors" if survived else "outliers"] += 1
                    oc["survivors" if survived else "outliers"] += 1
                prefix = (ordinal, i, j, span, tile_ordinal, pair_state, reason, status, survived)
                if tile is None or maps[i] is None:
                    missing = "fine-stage-not-reached" if tile is None else "source-placement-refused"
                    c["geometry_unavailable"] += 1
                    oc["geometry_unavailable"] += 1
                    writer.writerow((*prefix, False, missing, *([None] * 16)))
                    continue
                require(tile["origin"] == templates[tile_ordinal]["origin"]
                        and tile["size"] == templates[tile_ordinal]["size"], "same ordinal grid schema changed")
                tx, ty = tile["origin"]
                size = tile["size"]
                source_poly = footprint(tx, ty, size)
                poly = [inverse_point(p, maps[i], center) for p in source_poly]
                target = templates[tile_ordinal]["anchor_guide_corners"]
                values = overlap(poly, target)
                source_centroid = (tx + (size - 1) / 2, ty + (size - 1) / 2)
                centroid = inverse_point(source_centroid, maps[i], center)
                c["geometry_available"] += 1
                oc["geometry_available"] += 1
                c["positive_intersection" if values["intersection_area"] > 0 else "zero_intersection"] += 1
                oc["positive_intersection" if values["intersection_area"] > 0 else "zero_intersection"] += 1
                for key, record in continuous[span].items():
                    value = values[key]
                    record["n"] += 1
                    record["sum"] += value
                    record["min"] = value if record["min"] is None else min(record["min"], value)
                    record["max"] = value if record["max"] is None else max(record["max"], value)
                writer.writerow((*prefix, True, None, tx, ty, size, *source_centroid, *centroid,
                                 2 * centroid[0] + .5, 2 * centroid[1] + .5,
                                 json.dumps(poly, separators=(",", ":")),
                                 *(values[k] for k in ("source_area", "anchor_template_area", "intersection_area", "source_fraction", "template_fraction", "iou"))))
    require(count == 2340, "all original pair rows consumed")
    for span in SPANS:
        require(census[span]["pairs"] == 299 - span and census[span]["tile_slots"] == (299 - span) * TILES, "fixed span/ordinal population")
        for ordinal in range(TILES):
            require(per_ordinal[span, ordinal]["slots"] == 299 - span, "ordinal population")
        for record in continuous[span].values():
            record["mean"] = record.pop("sum") / record["n"] if record["n"] else None
    for row in bindings.values():
        h.check_ref(row)
    save(out / "input-bindings.json", dict(files=list(bindings.values()), unchanged=True, original_RAW_reads=0))
    save(out / "support.json", dict(status="COMPLETE_CONDITIONAL_ANCHOR_SUPPORT_CENSUS", complete=True,
         spans=SPANS, tile_ordinals=list(range(TILES)), requested_pairs=sum(299 - s for s in SPANS),
         requested_tile_slots=sum(299 - s for s in SPANS) * TILES, anchor_pair=ANCHOR_PAIR, reference=149,
         pair_and_tile_census={str(s): dict(c) for s, c in census.items()},
         by_ordinal=[dict(span=s, ordinal=t, **c) for (s, t), c in per_ordinal.items()],
         continuous_overlap_by_span=continuous, tile_support=ref(csv_path),
         transport="Exact inverse of held anchor149-to-source centered similarity: center + (source-center-b)/a. Center=(W/2,H/2) guide pixels. Anchor template also inverse149 transported; no identity coercion.",
         footprint="Actual reference-i guide sample-cell support corners tx-0.5 through tx+size-0.5. Centroid tx+(size-1)/2, distinct from fit center tx+size/2. Active-native coordinates=2*guide+0.5; no delivered-master crop offset.",
         interpretation="Conditional image-coordinate overlap under the held map. Neither common physical object nor matched focus is established.",
         status_meaning="Border means the NCC peak reached the search-window boundary; it is not missing image footprint or Oob. All tile statuses remain present regardless of overlap.",
         missing_geometry="Coarse/preflight refusals retain96 not-attempted slots with null actual geometry, not fabricated tile observations.",
         acceptance_threshold=None, focus_support="UNASSESSED", physical_common_support="UNESTABLISHED",
         no_fit=True, RAW_reads=0, warp_changed=False, admission=False, quality_claim=False,
         bindings_unchanged=True, command=getattr(sys, "orig_argv", [sys.executable, *sys.argv]),
         elapsed_seconds=time.monotonic() - started))
    save(out / "completion.json", dict(status="COMPLETE_CONDITIONAL_ANCHOR_SUPPORT_CENSUS", complete=True,
         reports=[ref(out / name) for name in ("controls.json", "anchor-templates.json", "tile-support.csv", "input-bindings.json", "support.json")],
         bindings_unchanged=True, physical_placement_claim=False, quality_claim=False))
    print(json.dumps(dict(status="COMPLETE_CONDITIONAL_ANCHOR_SUPPORT_CENSUS", out=str(out))))


if __name__ == "__main__":
    main()
