"""Fixed saved-NCC-residual stability test; no RAW reads or warp changes."""
from pathlib import Path
from dataclasses import asdict, dataclass
import argparse
import collections
import csv
import hashlib
import json
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SITES = (15, 41, 56)
ALL_SPANS = (1, 2, 4, 8, 16, 32, 64, 96, 128)
INTERVALS = {"train": (0, 95), "held": (112, 207), "replication": (224, 298)}
STATUSES = ("Ok", "LowContrast", "LowPeak", "Border", "Oob", "not-attempted")
PAIRS = tuple(sorted((i, i + span) for span in ALL_SPANS for i in range(299 - span)))
EXPECTED_KEYS = frozenset((i, j, site) for i, j in PAIRS for site in SITES)


def require(ok, message):
    if not ok:
        raise ValueError(message)


@dataclass(frozen=True)
class Row:
    i: int
    j: int
    site: int
    status: str
    rx: float | None
    ry: float | None
    mad_outlier: bool | None


def validate_disjoint(intervals):
    owners = {}
    for name, limits in intervals.items():
        require(len(limits) == 2 and all(type(x) is int for x in limits), "interval schema")
        lo, hi = limits
        require(0 <= lo <= hi < 299, "interval outside frozen acquisition population")
        for source in range(lo, hi + 1):
            require(source not in owners, f"shared acquisition {source}: {name}/{owners.get(source)}")
            owners[source] = name


def validate_rows(rows):
    validate_disjoint(INTERVALS)
    seen = set()
    for r in rows:
        require(isinstance(r, Row) and all(type(v) is int for v in (r.i, r.j, r.site)), "row identity schema")
        key = (r.i, r.j, r.site)
        require(key in EXPECTED_KEYS and key not in seen, "unexpected or duplicated row identity")
        seen.add(key)
        require(r.status in STATUSES, "unknown measurement status")
        require((r.rx is None) == (r.ry is None), "partial residual vector")
        require(r.rx is None or (r.status == "Ok" and math.isfinite(r.rx) and math.isfinite(r.ry)), "invalid residual")
        require(r.mad_outlier is None or type(r.mad_outlier) is bool, "MAD status schema")
        require(r.status == "Ok" or (r.rx is None and r.mad_outlier is None), "refused tile has fitted data")
    require(seen == EXPECTED_KEYS, "missing frozen pair/site rows; incomplete input is not a smaller population")


def inside(r, limits):
    lo, hi = limits
    return lo <= r.i <= hi and lo <= r.j <= hi


def usable(r):
    return r.status == "Ok" and r.rx is not None


def fit_rows(rows):
    """Exactly six scalars, from all available span8 training vectors, including MAD outliers."""
    validate_rows(rows)
    result = {}
    for site in SITES:
        selected = [r for r in rows if r.site == site and r.j - r.i == 8
                    and inside(r, INTERVALS["train"]) and usable(r)]
        result[site] = (math.fsum(r.rx / 8 for r in selected) / len(selected),
                        math.fsum(r.ry / 8 for r in selected) / len(selected)) if selected else None
    return result


def stats(values):
    n = len(values)
    if not n:
        return {"n": 0, "mean": None, "scatter_rms_vector": None, "rms_vector": None}
    mean = [math.fsum(v[k] for v in values) / n for k in (0, 1)]
    return {"n": n, "mean": mean,
            "scatter_rms_vector": math.sqrt(math.fsum((v[0] - mean[0]) ** 2 + (v[1] - mean[1]) ** 2 for v in values) / n),
            "rms_vector": math.sqrt(math.fsum(v[0] ** 2 + v[1] ** 2 for v in values) / n)}


def cell(rows, coefficients, site, span, label, limits):
    selected = [r for r in rows if r.site == site and r.j - r.i == span and inside(r, limits)]
    available = [r for r in selected if usable(r)]
    expected = max(0, limits[1] - limits[0] + 1 - span)
    v = coefficients[site]
    complete = len(selected) == expected and len(available) == expected and expected > 0 and v is not None
    original = [(r.rx, r.ry) for r in available]
    errors = [(r.rx - span * v[0], r.ry - span * v[1]) for r in available] if v is not None else []
    zero = math.fsum(x*x + y*y for x, y in original) / len(original) if original else None
    predicted = math.fsum(x*x + y*y for x, y in errors) / len(errors) if errors else None
    delta = zero - predicted if zero is not None and predicted is not None else None
    reduction = delta / zero if delta is not None and zero > 0 else None
    return dict(interval=label, source_limits=list(limits), site=site, span=span,
                expected_pairs=expected, present_pairs=len(selected),
                status_counts=dict(sorted(collections.Counter(r.status for r in selected).items())),
                valid_residuals=len(available), correlated_missing_residual=sum(r.status == "Ok" and r.rx is None for r in selected),
                mad_outliers=sum(r.mad_outlier is True for r in selected),
                mad_unavailable=sum(r.status == "Ok" and r.mad_outlier is None for r in selected),
                mse_zero=zero, mse_prediction=predicted, mse_delta=delta, relative_mse_reduction=reduction,
                residual=stats(original), prediction_error=stats(errors), complete=complete,
                **{"pass": complete and zero > 0 and predicted <= 0.8 * zero})


def score_rows(rows, coefficients):
    """The producing scorer. Alternative coefficients are exposed only for independent foils."""
    validate_rows(rows)
    require(set(coefficients) == set(SITES), "coefficient site set")
    for v in coefficients.values():
        require(v is None or (len(v) == 2 and all(math.isfinite(x) for x in v)), "coefficient schema")
    training = [cell(rows, coefficients, site, 8, "train", INTERVALS["train"]) for site in SITES]
    primary, adverse, blocks = [], [], []
    for name in ("held", "replication"):
        limits = INTERVALS[name]
        for site in SITES:
            for span in (1, 8):
                primary.append(cell(rows, coefficients, site, span, name, limits))
            adverse.append(cell(rows, coefficients, site, 32, name, limits))
        for lo in range(limits[0], limits[1] + 1, 16):
            block = (lo, min(lo + 15, limits[1]))
            for site in SITES:
                for span in (1, 8, 32):
                    record = cell(rows, coefficients, site, span, name, block)
                    record.update(descriptive_only=True, last_short_block=block[1] - block[0] + 1 < 16)
                    blocks.append(record)
    census = {}
    for r in rows:
        assigned = next((name for name, limits in INTERVALS.items() if inside(r, limits)), None)
        if assigned is None:
            any_endpoint = any(lo <= k <= hi for lo, hi in INTERVALS.values() for k in (r.i, r.j))
            assigned = "cross-boundary" if any_endpoint else "unused-gap"
        key = f"{assigned}/site{r.site}/span{r.j-r.i}"
        counts = census.setdefault(key, collections.Counter())
        counts["rows"] += 1
        counts["status:" + r.status] += 1
        counts["valid_residual" if usable(r) else "missing_residual"] += 1
        counts["mad_outlier" if r.mad_outlier is True else "mad_survivor" if r.mad_outlier is False else "mad_unavailable"] += 1
    train_complete = all(c["complete"] for c in training)
    return dict(stability_pass=train_complete and all(c["pass"] for c in primary),
                train_complete=train_complete, training=training, primary_cells=primary,
                adverse_cells=adverse, subblocks=blocks, census=census,
                physical_claim=False, attribution=False, quality_claim=False)


def analyze_rows(rows):
    coefficients = fit_rows(rows)
    result = score_rows(rows, coefficients)
    result.update(coefficients={str(k): v for k, v in coefficients.items()},
                  fitted_scalar_count=6 if all(v is not None for v in coefficients.values()) else 2 * sum(v is not None for v in coefficients.values()),
                  coefficient_units="source-i-to-j guide pixels per bracket ordinal step",
                  residual_units="saved-summary f64 measured-minus-final-similarity guide pixels",
                  mse_units="squared guide pixels per vector; squared x+y norm, not per-component variance",
                  admission=False, IID_inference=False, camera_noise_calibration=False,
                  decision="STABLE_MEASURED_PATTERN" if result["stability_pass"] else "REFUSED_FIXED_PER_STEP_HYPOTHESIS")
    return result


def ref(path):
    path = Path(path).resolve(strict=True)
    require(path.suffix.lower() != ".arw", "this saved-data analysis must not read original RAW files")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def load_rows(observation, summary, support):
    """Join authoritative saved CSV vectors to all original statuses, without recalculating residuals."""
    bindings = {}
    def bind(record):
        actual = ref(record["path"])
        require(actual["bytes"] == record["bytes"] and actual["sha256"] == record["sha256"], "bound artifact changed: " + actual["path"])
        previous = bindings.setdefault(actual["path"], actual)
        require(previous == actual, "conflicting artifact authorities")
    for job in (observation, summary, support):
        completion, process = read_json(job / "completion.json"), read_json(job / "process.json")
        require(completion["source_bindings_unchanged"] and not completion["photographic_improvement_claimed"], "root completion authority")
        require(process["exit_code"] == 0 and process["error"] is None and process["terminal_job_accounting"] and not process["cleanup_errors"], "completed successful input job required")
        for record in completion["reports"]:
            bind(record)
        bind(completion["build_completion"])
        for name in ("completion.json", "process.json", "invocation.json"):
            bind(ref(job / name))
    observed = read_json(observation / "output/receipt.json")
    summarized = read_json(summary / "output/summary.json")
    supported = read_json(support / "output/support.json")
    require(observed["status"] == "COMPLETE299_INSECT_PLACEMENT_OBSERVATION" and observed["mechanical_pass"]
            and observed["all_pairs_retained"] and observed["input_preservation"] and observed["guides_unchanged"]
            and observed["real_pair_on_off_exact"] and observed["source_count"] == 299 and observed["reference"] == 149
            and observed["pair_count"] == len(PAIRS) and tuple(observed["spans"]) == ALL_SPANS
            and observed["align_config"]["fine_iters"] == 1, "frozen complete observer required")
    require(summarized["status"] == "COMPLETE_DESCRIPTIVE_INSECT_PLACEMENT_CENSUS" and summarized["complete"]
            and summarized["bindings_unchanged"], "frozen summary required")
    require(supported["status"] == "COMPLETE_CONDITIONAL_ANCHOR_SUPPORT_CENSUS" and supported["complete"]
            and supported["bindings_unchanged"] and supported["spans"] == [1, 8, 32]
            and supported["requested_pairs"] == 856 and supported["requested_tile_slots"] == 82176, "frozen conditional support required")
    for record in observed["artifacts"]:
        bind(record)
    for job in (summary, support):
        saved = read_json(job / "output/input-bindings.json")
        files = saved["files"]
        paths = {str(Path(r["path"]).resolve()) for r in files}
        require(str((observation / "output/receipt.json").resolve()) in paths, "input job belongs to another observation")
        if job == support:
            require(str((summary / "output/summary.json").resolve()) in paths, "support belongs to another summary")
        for record in files:
            bind(record)
        for record in read_json(job / "output/completion.json")["reports"]:
            bind(record)
    csv_path = Path(summarized["signed_residuals"]["path"]).resolve()
    require(csv_path == (summary / "output/signed-residuals.csv").resolve(), "summary vector path")
    bind(summarized["signed_residuals"])
    vectors = {}
    with csv_path.open(newline="", encoding="utf-8") as stream:
        for r in csv.DictReader(stream):
            site = int(r["tile_ordinal"])
            if site not in SITES:
                continue
            key = (int(r["i"]), int(r["j"]), site)
            require(key in EXPECTED_KEYS and key not in vectors and int(r["pass"]) == 0, "duplicate/unexpected vector")
            require(int(r["span"]) == key[1] - key[0] and PAIRS[int(r["pair_ordinal"])] == key[:2], "CSV pair identity")
            rx, ry = r["final_residual_dx_guide"], r["final_residual_dy_guide"]
            require(bool(rx) == bool(ry), "partial saved vector")
            require(r["survived"] in ("True", "False", "unavailable"), "saved MAD status")
            vectors[key] = (None if not rx else float(rx), None if not ry else float(ry),
                            None if r["survived"] == "unavailable" else r["survived"] == "False")
    rows, pair_states = [], collections.Counter()
    trace_path = observation / "output/pairs.jsonl"
    require(str(trace_path.resolve()) in bindings, "trace binding missing")
    seen_pairs = 0
    with trace_path.open("r", encoding="utf-8") as stream:
        for ordinal, line in enumerate(stream):
            require(ordinal < len(PAIRS) and len(line) <= 8 << 20, "unexpected trace size/population")
            trace = json.loads(line)
            i, j = PAIRS[ordinal]
            require((trace["ordinal"], trace["i"], trace["j"]) == (ordinal, i, j), "trace pair order")
            core = trace["core"]
            require((core is None) != (trace["unavailable"] is None), "pair outcome exclusivity")
            pair_states["unavailable:" + trace["unavailable"] if core is None else core["result"]["state"]] += 1
            passes = [] if core is None else core["fine_passes"]
            require(len(passes) <= 1, "frozen one-pass observer required")
            stage = passes[0] if passes else None
            if stage:
                require(stage["index"] == 0 and len(stage["tiles"]) == 96, "fine pass population")
            for site in SITES:
                key = (i, j, site)
                tile = None if stage is None else stage["tiles"][site]
                status = "not-attempted" if tile is None else tile["status"]
                if tile:
                    require(tile["ordinal"] == site, "trace tile ordinal")
                if status == "Ok":
                    require(key in vectors, "correlated trace row missing from summary")
                    rx, ry, outlier = vectors.pop(key)
                    keep = stage["keep"]
                    expected_outlier = None if keep is None else not keep[tile["observation_index"]]
                    require(outlier == expected_outlier and (rx is None) == (stage["final_fit"] is None), "summary/trace mask or final-fit mismatch")
                else:
                    require(key not in vectors, "summary vector for uncorrelated tile")
                    rx, ry, outlier = None, None, None
                rows.append(Row(i, j, site, status, rx, ry, outlier))
            seen_pairs += 1
    require(seen_pairs == len(PAIRS) and not vectors, "incomplete trace/vector join")
    validate_rows(rows)
    # Support is an authority for conditional footprints only, never a predictor
    # scale or a filter on which correlated residuals enter the scorer.
    support_path = Path(supported["tile_support"]["path"]).resolve()
    require(support_path == (support / "output/tile-support.csv").resolve(), "support table path")
    bind(supported["tile_support"])
    selected = {(r.i, r.j, r.site): r for r in rows if r.j - r.i in (1, 8, 32)}
    with support_path.open(newline="", encoding="utf-8") as stream:
        for r in csv.DictReader(stream):
            site = int(r["tile_ordinal"])
            if site not in SITES:
                continue
            key = (int(r["i"]), int(r["j"]), site)
            require(key in selected, "unexpected or duplicate selected support row")
            actual = selected.pop(key)
            require(actual.status == r["tile_status"], "support/trace status mismatch")
    require(not selected, "missing selected support population")
    return rows, list(bindings.values()), dict(pair_states)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("observation", "summary", "support", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists(), "fresh workspace output required")
    jobs = [getattr(args, name).resolve(strict=True) for name in ("observation", "summary", "support")]
    rows, bindings, pair_states = load_rows(*jobs)
    bindings += [ref(Path(__file__)), ref(sys.executable)]
    out.mkdir(parents=True, exist_ok=False)
    save(out / "rows.json", dict(schema=1, rows=[asdict(r) for r in rows], pair_states=pair_states,
                                residual_quantity="summary f64 measured minus saved final similarity; no new vector recomputation"))
    decision = analyze_rows(rows)
    for record in bindings:
        require(ref(record["path"]) == record, "input changed during analysis")
    save(out / "input-bindings.json", dict(files=bindings, unchanged=True, RAW_reads=0))
    receipt = dict(status="COMPLETE_INSECT_FIELD_STABILITY", complete=True, mechanical_pass=True,
                   **decision, rows_count=len(rows), source_intervals=INTERVALS, sites=SITES,
                   all_spans=ALL_SPANS, primary_spans=[1, 8], adverse_span=32,
                   improvement_required=0.20, source_disjoint=True, RAW_reads=0, warp_changed=False,
                   input_bindings_unchanged=True, elapsed_seconds=time.monotonic() - started,
                   workers=1, command=getattr(sys, "orig_argv", [sys.executable, *sys.argv]),
                   limitations=["A persistent defocus-sensitive matcher bias can pass this test.",
                                "Bracket ordinal is not physical depth; guide frames differ across sources.",
                                "Conditional reference-footprint overlap does not prove identical matched structures.",
                                "Shared-source subblocks are descriptive, not IID tests or confidence intervals."])
    save(out / "receipt.json", receipt)
    save(out / "completion.json", dict(status=receipt["status"], complete=True,
         reports=[ref(out / name) for name in ("rows.json", "input-bindings.json", "receipt.json")],
         bindings_unchanged=True, physical_claim=False, quality_claim=False))
    print(json.dumps({k: receipt[k] for k in ("status", "stability_pass", "decision", "elapsed_seconds")}))


if __name__ == "__main__":
    main()
