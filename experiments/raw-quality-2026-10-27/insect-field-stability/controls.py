"""Independent fixed controls for the literal saved-residual stationarity scorer."""
from pathlib import Path
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import math
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
SITES = (15, 41, 56)
SPANS = (1, 2, 4, 8, 16, 32, 64, 96, 128)
INTERVALS = {"train": (0, 95), "held": (112, 207), "replication": (224, 298)}
VECTORS = {15: (.045, .015), 41: (-.020, .040), 56: (.010, -.050)}
SIGMA = .002
ACQUISITION_SEED = 0x6387A1D4
PAIR_SEED = 0xC29E4B17


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def file_ref(path):
    path = Path(path).resolve(strict=True)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


class Noise:
    def __init__(self, seed):
        self.state = seed

    def draw(self):
        value = -6.0
        for _ in range(12):
            self.state = (1664525 * self.state + 1013904223) & 0xFFFFFFFF
            value += (self.state + .5) / 4294967296.0
        return SIGMA * value


def held_pair(i, j):
    return any(lo <= i <= j <= hi for name, (lo, hi) in INTERVALS.items() if name != "train")


def fixtures(model):
    acquisition_rng, pair_rng = Noise(ACQUISITION_SEED), Noise(PAIR_SEED)
    acquisition = {(i, site): (acquisition_rng.draw(), acquisition_rng.draw())
                   for i in range(299) for site in SITES}
    pairs = sorted((i, i + span) for span in SPANS for i in range(299 - span))
    result = {name: [] for name in ("zero", "noise-only", "stable", "held-reversal")}
    for i, j in pairs:
        for site in SITES:
            extra = (pair_rng.draw(), pair_rng.draw())
            noise = tuple(acquisition[j, site][k] - acquisition[i, site][k] + extra[k] for k in range(2))
            signal = tuple((j - i) * v for v in VECTORS[site])
            sign = -1 if held_pair(i, j) else 1
            values = {
                "zero": (0.0, 0.0),
                "noise-only": noise,
                "stable": tuple(signal[k] + noise[k] for k in range(2)),
                "held-reversal": tuple(sign * signal[k] + noise[k] for k in range(2)),
            }
            # Independent deterministic flags: the scorer must use all rows.
            outlier = (i + j + site) % 13 == 0
            for name, xy in values.items():
                result[name].append(model.Row(i, j, site, "Ok", *xy, outlier))
    require(all(len(rows) == 7020 for rows in result.values()), "fixed generated inventory")
    result["missing-primary"] = [
        dataclasses.replace(r, status="Border", rx=None, ry=None, mad_outlier=None)
        if (r.i, r.j, r.site) == (112, 113, 15) else r for r in result["stable"]]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists(), "fresh workspace output required")
    out.mkdir(parents=True, exist_ok=False)
    paths = (AREA / "analyze.py", Path(__file__), AREA / "controls-protocol.md", AREA / "brief.md")
    before = [file_ref(path) for path in paths]
    spec = importlib.util.spec_from_file_location("insect_field_frozen_analyzer", paths[0])
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)
    require(tuple(model.SITES) == SITES and tuple(model.ALL_SPANS) == SPANS
            and model.INTERVALS == INTERVALS, "frozen sites/spans/intervals changed")
    populations = fixtures(model)
    fixture_refs = {}
    for name, rows in populations.items():
        path = out / (name + "-rows.json")
        save(path, [dataclasses.asdict(row) for row in rows])
        fixture_refs[name] = file_ref(path)
    results = {}
    checks = {}

    def analyze(name, rows):
        value = model.analyze_rows(rows)
        save(out / (name + "-result.json"), value)
        results[name] = value
        checks[name + "-non-attribution"] = all(value.get(key) is False for key in
                                                ("attribution", "physical_claim", "quality_claim"))
        return value

    # Exact zero and noise-only must precede the structured positive.
    zero = analyze("zero", populations["zero"])
    checks["zero-refuses"] = not zero["stability_pass"]
    checks["zero-null-energy-explicit"] = all(c["mse_zero"] == 0.0 and
        c["relative_mse_reduction"] is None and not c["pass"] for c in zero["primary_cells"])
    noise = analyze("noise-only", populations["noise-only"])
    checks["noise-refuses"] = not noise["stability_pass"]
    stable = analyze("stable", populations["stable"])
    coefficients = model.fit_rows(populations["stable"])
    checks["stable-positive-passes"] = stable["stability_pass"] and all(c["pass"] for c in stable["primary_cells"])
    checks["known-components-recovered"] = all(abs(coefficients[s][k] - VECTORS[s][k]) <= .001
                                                for s in SITES for k in range(2))
    literal_means = {s: tuple(math.fsum((r.rx, r.ry)[k] / 8 for r in populations["stable"]
                        if r.site == s and r.j - r.i == 8 and 0 <= r.i <= r.j <= 95) / 88
                        for k in range(2)) for s in SITES}
    checks["all-correlated-training-mean"] = all(abs(coefficients[s][k] - literal_means[s][k]) <= 1e-12
                                                   for s in SITES for k in range(2))
    counts = {"held": {1: 95, 8: 88}, "replication": {1: 74, 8: 67}}
    checks["full-primary-counts"] = len(stable["primary_cells"]) == 12 and all(
        c["expected_pairs"] == c["present_pairs"] == c["valid_residuals"] == counts[c["interval"]][c["span"]]
        for c in stable["primary_cells"])
    reverse = analyze("held-reversal", populations["held-reversal"])
    checks["held-reversal-rejected-every-cell"] = not reverse["stability_pass"] and all(
        not c["pass"] for c in reverse["primary_cells"])

    wrong_site = {s: coefficients[SITES[(index + 1) % len(SITES)]] for index, s in enumerate(SITES)}
    wrong_span = {s: tuple(8 * value for value in coefficients[s]) for s in SITES}
    for name, wrong in (("wrong-site", wrong_site), ("wrong-span", wrong_span)):
        value = model.score_rows(populations["stable"], wrong)
        save(out / (name + "-result.json"), value)
        results[name] = value
        checks[name + "-rejected-every-cell"] = not value["stability_pass"] and all(
            not c["pass"] for c in value["primary_cells"])
    missing = analyze("missing-primary", populations["missing-primary"])
    checks["missing-primary-refuses"] = not missing["stability_pass"] and any(
        c["interval"] == "held" and c["site"] == 15 and c["span"] == 1
        and not c["complete"] and not c["pass"] for c in missing["primary_cells"])

    exceptions = {}
    for name, action in (
        ("omitted-row", lambda: model.analyze_rows(populations["stable"][1:])),
        ("acquisition-overlap", lambda: model.validate_disjoint({**INTERVALS, "held": (95, 190)})),
    ):
        try:
            action()
        except ValueError as exc:
            exceptions[name] = dict(rejected=True, exception=type(exc).__name__, message=str(exc))
        else:
            exceptions[name] = dict(rejected=False)
        checks[name + "-rejected"] = exceptions[name]["rejected"]

    bias = analyze("persistent-bias-lookalike", populations["stable"])
    checks["bias-lookalike-same-passing-observations"] = bias == stable and bias["stability_pass"]
    lookalike = dict(rows=fixture_refs["stable"], numeric_observations_identical=True,
                    hypothetical_physical_movement=0,
                    cause="persistent focus-dependent matching bias equal to the known per-step field",
                    interpretation="Identical observations cannot identify whether the predictable residual is physical movement.")
    after = [file_ref(path) for path in paths]
    checks["source-bindings-unchanged"] = before == after
    report = dict(status="COMPLETE_INSECT_FIELD_CONTROLS", all_cases_completed=True,
                  control_pass=all(checks.values()), checks=checks, exceptions=exceptions,
                  fixtures=fixture_refs, result_files={name: file_ref(out / (name + "-result.json")) for name in results},
                  coefficients=coefficients, literal_all_correlated_means=literal_means,
                  wrong_site_coefficients=wrong_site, wrong_span_coefficients=wrong_span,
                  persistent_bias_lookalike=lookalike, source_bindings=before,
                  sources_unchanged=before == after, acquisition_seed=ACQUISITION_SEED, pair_seed=PAIR_SEED,
                  acquisition_sigma=SIGMA, pair_sigma=SIGMA, vector_truth=VECTORS,
                  synthetic_rows_per_population=7020, actual_saved_data_reads=0, RAW_reads=0,
                  command=getattr(sys, "orig_argv", [sys.executable, *sys.argv]), python_version=sys.version,
                  attribution=False, physical_claim=False, quality_claim=False, admission=False)
    save(out / "controls.json", report)
    require(report["control_pass"], "fixed control failure; saved controls.json and all results retained")
    print(json.dumps(dict(status=report["status"], control_pass=True, out=str(out))))


if __name__ == "__main__":
    main()
