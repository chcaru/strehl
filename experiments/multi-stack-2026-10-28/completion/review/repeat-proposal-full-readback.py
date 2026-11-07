"""Independent checks added without changing the already-frozen render driver."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
import tifffile

spec = importlib.util.spec_from_file_location("render_driver", Path(__file__).with_name("repeat-proposal-full.py"))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
ROOT, BASE, DEST, sha = driver.ROOT, driver.BASE, driver.DEST, driver.sha
PLAN = DEST / "readback-plan.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def freeze():
    paths = [Path(__file__), Path(driver.__file__),
             BASE / "inspection/equal/receipt.json", DEST / "plan.json"]
    paths += [BASE / "equal" / name for name in
              ["master.tiff", "photograph.tiff", "render-report.json", "completed.json",
               "render-completion.json", "source-identities.json", "session.json",
               "alignment.json", "calibration.json"]]
    binding = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    with PLAN.open("x", encoding="utf-8") as out:
        json.dump({"schema": "strehl.repeat-proposal-readback-plan.v1",
                   "frozen_unix": time.time(), "bindings": binding,
                   "scope": "Frozen during rendering before new photograph/master inspection. Baseline identity, complete published bindings, source/geometry/calibration identity, full pixel finite/equality checks and crop bounds."}, out, indent=2)
        out.write("\n")
    print("Frozen readback bindings:", len(binding))


def bindings(directory):
    completion = read(directory / "completed.json")
    assert completion["schema"] == "strehl.session-completion.v1"
    assert completion["frames"] == 32 and completion["passes"] == 2
    assert completion["outputs"] == 1 and completion["primary_pass"] is None
    assert list(completion["render_bindings"]) == ["render-completion.json"]
    assert sha(directory / "render-completion.json") == completion["render_bindings"]["render-completion.json"]
    sealed = read(directory / "render-completion.json")
    assert sealed["schema"] == "strehl.session-render-completion.v1"
    assert sealed["geometry_kind"] == "session-alignment"
    assert set(sealed["files"]) == {"master.tiff", "photograph.tiff", "render-report.json"}
    assert set(sealed["session_files"]) == {"session.json", "source-identities.json", "alignment.json"}
    for group in ["files", "session_files"]:
        for name, expected in sealed[group].items():
            assert sha(directory / name) == expected, (directory, name)
    return sealed


def pixel_check(first, second):
    a, b = [tifffile.memmap(p, mode="r") for p in [first, second]]
    assert a.shape == b.shape and a.dtype == b.dtype
    hashes = [hashlib.sha256(), hashlib.sha256()]
    equal = True
    for y in range(0, a.shape[0], 128):
        x, z = a[y:y+128], b[y:y+128]
        assert np.isfinite(x).all() and np.isfinite(z).all()
        equal &= np.array_equal(x.view(np.uint8), z.view(np.uint8))
        hashes[0].update(x.tobytes())
        hashes[1].update(z.tobytes())
    return {"shape": list(a.shape), "dtype": str(a.dtype), "finite": True,
            "pixels_bit_identical": bool(equal),
            "pixel_sha256": [h.hexdigest() for h in hashes]}


def verify():
    for path, expected in read(PLAN)["bindings"].items():
        assert sha(ROOT / path) == expected, path
    baseline = BASE / "equal"
    bindings(baseline)
    original_witnesses = read(BASE / "inspection/equal/receipt.json")["witnesses"]
    protocol = read(BASE / "inputs/protocol.json")
    full = read(BASE / "alignment.json")["report"]["geometry_plane_pixels"]
    result = {"readback_plan_sha256": sha(PLAN), "arms": {}}
    for arm in driver.ARMS:
        directory = DEST / arm
        sealed = bindings(directory)
        run = read(DEST / (arm + "-run") / "receipt.json")
        assert run["state"] == "complete" and run["exit_code"] == 0
        assert run["command"] == read(DEST / "plan.json")["arms"][arm]
        identities = {}
        for name in ["source-identities.json", "alignment.json", "calibration.json", "session.json"]:
            identities[name] = sha(directory / name)
            assert identities[name] == sha(baseline / name), (arm, name)
        report = read(directory / "render-report.json")
        groups = report["proposed_groups"]
        assert sorted(i for group in groups for i in group) == list(range(32))
        assert sum(len(group) == 2 for group in groups) == {"legacy": 4, "proposals": 16, "singletons": 0}[arm]
        assert all(1 <= len(group) <= 2 for group in groups)
        images = {name: pixel_check(baseline / name, directory / name)
                  for name in ["master.tiff", "photograph.tiff"]}
        assert images["master.tiff"]["dtype"] == "float32"
        assert images["photograph.tiff"]["dtype"] == "uint16"
        assert images["master.tiff"]["shape"] == images["photograph.tiff"]["shape"] == [4668, 7004, 3]
        if arm == "legacy":
            assert all(v["pixels_bit_identical"] for v in images.values())
        canvas = report["canvas"]
        for witness, previous in zip(protocol["witnesses"], original_witnesses, strict=True):
            x, y = [int(np.floor(f * 2 * n - 192))
                    for f, n in zip(witness["active_fraction_center"], full)]
            x, y = max(0, min(2*full[0]-384, x)), max(0, min(2*full[1]-384, y))
            xx, yy = x - 2*canvas[0], y - 2*canvas[1]
            assert 0 <= xx <= 7004-384 and 0 <= yy <= 4668-384
            assert [xx, yy] == previous["origin_output_sensor"]
            assert [x, y] == previous["origin_full_sensor"]
            assert witness["id"] == previous["id"] and previous["dimensions"] == [384, 384]
        result["arms"][arm] = {"complete_bindings_verified": sealed,
                              "identical_source_geometry_calibration": identities,
                              "full_images": images, "witness_bounds_and_identity": True}
    with (DEST / "complete-readback.json").open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    driver.inspect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "verify"])
    args = parser.parse_args()
    {"freeze": freeze, "verify": verify}[args.action]()
