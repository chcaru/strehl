"""Re-run the exact historical M115 split controls inside this lane.

The historical sources are read directly from Git and executed in memory.  The
only permitted source edit redirects M115's output directory into this lane.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LANE = Path(__file__).resolve().parent
OUT = LANE / "out" / "m115-rerun"
COMMISSION_RECORD = LANE / "out" / "m115-rerun-loader-commission.json"
COMMIT = "77c8d5e9ac6ed342cdc841e541c98f87e5c743f8"
BASE = "experiments/M115-deconv-headroom/src"
ORIGINAL_OUT = r'OUT = r"C:\dev\strehl-out\M115-deconv-headroom\out"'
EXPECTED_BLOBS = {
    "m115lib.py": "32ef59f026572ceb1d4b951254d693c4d3aaf94a",
    "s01_rois.py": "dd8e7319848753312f5d847dab4b1bb92c87b174",
    "s02_controls_a.py": "250ec013764c8efe75ffe1091b508972fc508e21",
    "s03_instrument.py": "efa37273f1bbde8cff20a8d014c95f3454178e04",
}


def git_text(name: str, *, wrong_blob: bool = False) -> tuple[str, str]:
    spec = f"{COMMIT}:{BASE}/{name}"
    oid = subprocess.check_output(
        ["git", "rev-parse", spec], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()
    expected = "0" * 40 if wrong_blob and name == "m115lib.py" else EXPECTED_BLOBS[name]
    if oid != expected:
        raise RuntimeError(f"historical source mismatch for {name}: {oid} != {expected}")
    raw = subprocess.check_output(["git", "show", spec], cwd=ROOT)
    return raw.decode("utf-8"), oid


def reroot(source: str, *, disabled: bool = False) -> str:
    marker = ORIGINAL_OUT + ("-PLANTED-MISS" if disabled else "")
    if source.count(marker) != 1:
        raise RuntimeError(
            f"historical output-root marker count is {source.count(marker)}, expected 1"
        )
    replacement = f'OUT = r"{OUT.resolve()}"'
    changed = source.replace(marker, replacement)
    if ORIGINAL_OUT in changed or replacement not in changed:
        raise RuntimeError("historical output root was not uniquely redirected")
    return changed


def load_module(name: str, source: str) -> types.ModuleType:
    stem = Path(name).stem
    module = types.ModuleType(stem)
    module.__file__ = str(LANE / "_historical_m115" / name)
    module.__package__ = ""
    sys.modules[stem] = module
    exec(compile(source, f"git:{COMMIT}:{BASE}/{name}", "exec"), module.__dict__)
    return module


def extract(log: dict, *, corrupt: bool = False) -> dict[str, object]:
    c2 = log["C2"]["109MSDCF"]["res"]
    recoveries = [
        float(value)
        for arm in ("MEAN", "FRAME*")
        for value in c2[arm]["recovery"]
    ]
    c3 = log["C3"]["109MSDCF"]["rows"]
    c9 = log["C9"]["109MSDCF"]["rows"]
    null_arms = log["C1p"]["arms"]
    if corrupt:
        recoveries[0] += 0.125
    return {
        "blur_recovery_min": min(recoveries),
        "blur_recovery_max": max(recoveries),
        "blur_recovery_count": len(recoveries),
        "blur_monotone": all(bool(c2[arm]["monotone"]) for arm in ("MEAN", "FRAME*")),
        "filter_snr_ratios": {
            name: float(row["snr_ratio"]) for name, row in c3.items()
        },
        "filter_max_fractional_move": max(
            abs(float(row["snr_ratio"]) - 1.0) for row in c3.values()
        ),
        "null_max_snr": {
            name: float(row["mx"]) for name, row in null_arms.items()
        },
        "null_failed_arms": sorted(
            name for name, row in null_arms.items() if float(row["mx"]) >= 0.25
        ),
        "identity_min": min(float(row["consistency"]) for row in c9.values()),
        "identity_max": max(float(row["consistency"]) for row in c9.values()),
    }


def self_test(plant: str | None) -> None:
    source, _ = git_text("m115lib.py", wrong_blob=plant == "H1")
    patched = reroot(source, disabled=plant == "H2")
    assert str(OUT.resolve()) in patched

    fixture = {
        "C2": {
            "109MSDCF": {
                "res": {
                    "MEAN": {"recovery": [0.95] * 4, "monotone": True},
                    "FRAME*": {"recovery": [1.05] * 4, "monotone": True},
                }
            }
        },
        "C3": {
            "109MSDCF": {
                "rows": {
                    "fixed-a": {"snr_ratio": 0.99},
                    "fixed-b": {"snr_ratio": 1.01},
                }
            }
        },
        "C1p": {
            "arms": {
                "PASS": {"mx": 0.1},
                "FAIL": {"mx": 0.3},
            }
        },
        "C9": {
            "109MSDCF": {
                "rows": {
                    "fixed-a": {"consistency": 1.0},
                    "fixed-b": {"consistency": 1.0},
                }
            }
        },
    }
    got = extract(fixture, corrupt=plant == "H3")
    assert got["blur_recovery_count"] == 8
    assert got["blur_recovery_min"] == 0.95
    assert got["blur_recovery_max"] == 1.05
    assert got["filter_max_fractional_move"] == 0.010000000000000009
    assert got["null_failed_arms"] == ["FAIL"]
    assert got["identity_min"] == got["identity_max"] == 1.0
    print("M115 RERUN LOADER SELF-TEST GREEN")


def capture_manifest() -> dict[str, object]:
    directories = [
        Path(r"D:\personal\macro\109MSDCF"),
        Path(r"D:\personal\macro\119MSDCF"),
        Path(r"D:\personal\macro\flat-fields\flat-fields"),
    ]
    result: dict[str, object] = {}
    for directory in directories:
        files = sorted(directory.glob("*.ARW"))
        digest = hashlib.sha256()
        for path in files:
            stat = path.stat()
            digest.update(path.name.encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
        result[str(directory)] = {
            "files": len(files),
            "filename_size_digest": digest.hexdigest(),
            "read_only_input": True,
        }
    return result


def run_historical() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    started = time.time()
    sources: dict[str, str] = {}
    blobs: dict[str, str] = {}
    for name in EXPECTED_BLOBS:
        sources[name], blobs[name] = git_text(name)
    sources["m115lib.py"] = reroot(sources["m115lib.py"])

    load_module("m115lib.py", sources["m115lib.py"])
    s01 = load_module("s01_rois.py", sources["s01_rois.py"])
    s01.main()
    load_module("s02_controls_a.py", sources["s02_controls_a.py"])
    s03 = load_module("s03_instrument.py", sources["s03_instrument.py"])
    s03.main()

    output = OUT / "s03_instrument.json"
    if not output.is_file():
        raise RuntimeError("historical run did not create a fresh s03_instrument.json")
    log = json.loads(output.read_text(encoding="utf-8"))
    manifest = {
        "status": "HISTORICAL_M115_RERUN_COMPLETE",
        "historical_commit": COMMIT,
        "source_blobs": blobs,
        "sole_source_edit": {
            "from": ORIGINAL_OUT,
            "to": f'OUT = r"{OUT.resolve()}"',
        },
        "captures": capture_manifest(),
        "elapsed_seconds": time.time() - started,
        "extracted": extract(log),
    }
    (OUT / "rerun-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


def commission_loader() -> None:
    command = [sys.executable, str(Path(__file__).resolve()), "--self-test"]

    def invoke(extra: str | None = None) -> int:
        args = command + ([extra] if extra else [])
        return subprocess.run(args, cwd=ROOT, check=False).returncode

    clean = invoke()
    plants = {plant: invoke(plant) for plant in ("H1", "H2", "H3")}
    if clean != 0 or any(code != 1 for code in plants.values()):
        raise RuntimeError(f"loader commissioning failed: clean={clean}, plants={plants}")
    result = {
        "status": "COMMISSIONED_GREEN",
        "clean_exit": clean,
        "plants": plants,
        "all_plants_red": True,
        "external_predicate": "fixed Git blob object IDs at historical commit",
        "command": command,
    }
    COMMISSION_RECORD.parent.mkdir(parents=True, exist_ok=True)
    COMMISSION_RECORD.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


def main() -> int:
    if "--self-test" in sys.argv:
        plant = next((arg for arg in ("H1", "H2", "H3") if arg in sys.argv), None)
        self_test(plant)
        return 0
    if "--commission" in sys.argv:
        commission_loader()
        return 0
    run_historical()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
