"""Final-array transport controls only; never float-model authority."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    reader = module("independent_reader_control_subject", HERE / "independent-compare.py")
    maths = module("independent_reader_control_math", HERE / "independent-comparison-math.py")
    result = dict(schema="m194e-independent-reader-controls-v1", status="RUNNING", command=sys.argv, sources={}, checks=[])
    for name in ("independent-reader-controls.py", "independent-reader-preregister.md", "independent-compare.py", "independent-comparison-math.py"):
        shutil.copyfile(HERE / name, args.output / name)
        result["sources"][name] = reader.sha(HERE / name)

    def check(name, passed):
        result["checks"].append(dict(name=name, passed=bool(passed)))
        if not passed:
            raise ValueError("control failed: " + name)

    def refuses(name, function):
        try:
            function()
        except (ValueError, OSError):
            check(name, True)
        else:
            check(name, False)

    try:
        reference = reader.read_json(HERE / "independent-reference-1/result.json", reader.PINS["reference"][1])
        source = next(r["array"] for r in reference["frames"] if r["arm"] == "refined" and r["index"] == 2)
        original = reader.array(source, HERE / "independent-reference-1")
        null = args.output / "null.npy"
        shutil.copyfile(HERE / "independent-reference-1" / source["path"], null)
        check("byte-copy-null", np.array_equal(reader.array(reader.file_ref(null, args.output), args.output), original))
        relocated = args.output / "relocated"
        relocated.mkdir()
        shutil.copyfile(null, relocated / "null.npy")
        check("identical-relocated-null", np.array_equal(reader.array(reader.file_ref(relocated / "null.npy", relocated), relocated), original))
        false_digest = dict(reader.file_ref(null, args.output), sha256="0" * 64)
        refuses("false-digest", lambda: reader.array(false_digest, args.output))
        trailing = args.output / "trailing.npy"
        trailing.write_bytes(null.read_bytes() + b"retained-trailer")
        refuses("bound-trailing-payload", lambda: reader.array(reader.file_ref(trailing, args.output), args.output))
        for name, value in (("float32", original.astype("<f4")), ("shape", original[:-1]), ("nan", original.copy())):
            if name == "nan":
                value[24, 32] = np.nan
            path = args.output / (name + ".npy")
            np.save(path, value, allow_pickle=False)
            refuses(name, lambda p=path: reader.array(reader.file_ref(p, args.output), args.output))
        duplicate = args.output / "duplicate.json"
        duplicate.write_text('{"value":1,"value":2}', encoding="utf8")
        refuses("duplicate-keys", lambda: reader.read_json(duplicate))
        changed = original.copy()
        changed[24, 32] += .005
        path = args.output / "finite-changed.npy"
        np.save(path, changed, allow_pickle=False)
        read = reader.array(reader.file_ref(path, args.output), args.output)
        stats = maths.compare(read, original)
        check("bound-finite-change-reads-but-maximum-rejects", not stats["whole"]["maximum_pass"] and stats["whole"]["rms_pass"])
        result["mutation_statistics"] = stats
        result["status"] = "PASS_READER_CONTROLS_ONLY"
    except Exception as exc:
        result["status"] = "READER_UNCOMMISSIONED"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    result["source_unchanged"] = all(reader.sha(HERE / k) == v for k, v in result["sources"].items())
    if not result["source_unchanged"]:
        result["status"] = "READER_UNCOMMISSIONED"
    reader.write(args.output / "result.json", result)
    print(json.dumps(dict(status=result["status"], checks=len(result["checks"]), error=result.get("error"))))
    return 0 if result["status"] == "PASS_READER_CONTROLS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
