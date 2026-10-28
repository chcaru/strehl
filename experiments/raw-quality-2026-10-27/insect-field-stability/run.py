"""Root-only bounded fixed measured-field discriminator; no RAW inputs."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-27"
HELPERS = AREA.parent / "insect-placement-observer/run.py"
spec = importlib.util.spec_from_file_location("field_stability_root_helpers", HELPERS)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
b, ref, save, check_refs = prior.b, prior.ref, prior.save, prior.check_refs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("controls", "actual"))
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--controls-iteration", type=int, default=1)
    args = parser.parse_args()
    assert min(args.iteration, args.controls_iteration) > 0
    out = CAMPAIGN / f"insect-field-{args.stage}-{args.iteration}"
    out.mkdir(parents=True, exist_ok=False)
    source_paths = [AREA / name for name in ("run.py", "analyze.py", "controls.py", "brief.md")]
    source_paths += [p for p in (AREA / "controls-protocol.md", AREA / "source-review.md") if p.is_file()]
    source_paths += [HELPERS, prior.PRIOR, prior.prior.HELPER, b.HARNESS]
    sources = [ref(p) for p in source_paths]
    operator = ref(AREA / "analyze.py")
    save(out / "source-bindings.json", sources)
    command = [sys.executable, "-B", "-X", "faulthandler",
               str(AREA / ("controls.py" if args.stage == "controls" else "analyze.py")),
               "--out", str(out / "output")]
    dependencies = []
    if args.stage == "actual":
        control = CAMPAIGN / f"insect-field-controls-{args.controls_iteration}"
        completed = json.loads((control / "completion.json").read_text())
        assert completed["operator"] == operator
        check_refs(completed["reports"])
        check_refs(json.loads((control / "source-bindings.json").read_text()))
        dependencies += [ref(control / "completion.json")]
        for arg, name in (("observation", "observe"), ("summary", "summary"), ("support", "support")):
            job = CAMPAIGN / f"insect-placement-{name}-1"
            receipt = json.loads((job / "completion.json").read_text())
            check_refs(receipt["reports"])
            dependencies += [ref(job / "completion.json")]
            command += ["--" + arg, str(job)]
    fields = dict(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                  NUMEXPR_NUM_THREADS="1", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    env, removed = b.clean_environment(fields.items())
    bounds = dict(wall_seconds=120, cpu_seconds=120, committed_bytes=4 << 30, log_bytes=16 << 20)
    save(out / "invocation.json", dict(command=command, environment=fields,
         removed_environment=removed, bounds=bounds, executable=ref(sys.executable),
         operator=operator, dependencies=dependencies, runner=ref(__file__),
         scope="One frozen measured-residual hypothesis; no RAW read, warp, physical attribution or image-quality admission."))
    prior.observed_run(command, env, out, bounds)
    check_refs(sources + dependencies)
    receipt_path = out / "output" / ("controls.json" if args.stage == "controls" else "receipt.json")
    receipt = json.loads(receipt_path.read_text())
    if args.stage == "controls":
        assert receipt["status"] == "COMPLETE_INSECT_FIELD_CONTROLS"
        assert receipt["all_cases_completed"] is True and receipt["control_pass"] is True
    else:
        assert receipt["status"] == "COMPLETE_INSECT_FIELD_STABILITY" and receipt["mechanical_pass"] is True
    assert all(receipt[key] is False for key in ("attribution", "physical_claim", "quality_claim", "admission"))
    reports = [ref(p) for p in sorted((out / "output").rglob("*.json"))]
    assert reports, "child completion evidence missing"
    save(out / "completion.json", dict(reports=reports, operator=operator,
         source_bindings_unchanged=True, physical_placement_claim=False, photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
