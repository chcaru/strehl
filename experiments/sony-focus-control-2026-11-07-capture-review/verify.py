"""Verify untouched inputs, analysis identities and report structure without camera access."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "outputs/sony-focus-control-capture-review"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    inventory = json.loads((OUT / "inventory.json").read_text())
    source = Path(inventory["input"])
    expected = {r["path"] for r in inventory["files"]}
    actual = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()}
    assert actual == expected, "Input file inventory changed"
    for index, record in enumerate(inventory["files"], 1):
        path = source / record["path"]
        stat = path.stat()
        assert (stat.st_size, stat.st_mtime_ns, sha(path)) == (record["bytes"], record["mtime_ns"], record["sha256"]), path
        if index % 40 == 0:
            print(f"Preservation checked: {index}/{len(expected)} files", flush=True)

    # Resolve the SDK enum rather than treating every 'warning' as an error.
    header = ROOT / "outputs/sony-control/sdk-2.02.00/app/CRSDK/CrError.h"
    contents = re.sub(r"/\*.*?\*/|//[^\n]*", "", header.read_text(), flags=re.S)
    fragment = contents[contents.index("CrWarning_Unknown"):contents.index("CrWarning_FocusPosition_Result_NG")]
    value, enums = -1, {}
    for item in fragment.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            name, expression = map(str.strip, item.split("=", 1))
            value = enums[expression] if expression in enums else int(expression, 0)
        else:
            name = item
            value += 1
        enums[name] = value
    assert enums["CrWarning_FocusPosition_Result_OK"] == 131180
    native_endpoints = []
    for run in inventory["sessions"]:
        for field in ["ExposureTime", "ISO", "FNumber", "WB_RGGBLevels", "ColorTemperature", "ImageStabilization"]:
            assert len({f["metadata"][field] for f in run["frames"]}) == 1, (run["name"], field)
        assert run["restoration"]["warnings"] == [enums["CrWarning_FocusPosition_Result_OK"]]
        manifest = json.loads((source / run["name"] / "manifest.json").read_text())
        for capture in manifest["captures"]:
            if capture["phase"] == "native-width-1":
                before = capture["before"]["properties"]["FocusPositionCurrentValue"]["value"]
                after = capture["after"]["properties"]["FocusPositionCurrentValue"]["value"]
                assert after - before == -70
                native_endpoints.append({"session": run["name"], "sequence": capture["sequence"],
                                         "before": before, "after": after})

    identities = {}
    for path in sorted(HERE.glob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        identities[path.name] = sha(path)
    identities["raw-check.rs"] = sha(HERE / "raw-check.rs")
    for filename, script in [("decode.json", "decode.py"), ("band-results.json", "focus-band.py"),
                             ("pair-response.json", "pair-response.py"), ("review.json", "review.py")]:
        result = json.loads((OUT / filename).read_text())
        assert result["source_sha256"] == identities[script], (filename, script)
    assert inventory["environment"]["source_sha256"] == identities["inventory.py"]
    checked_links = []
    for path in [HERE / "brief.md", HERE / "results.md"]:
        body = path.read_text(encoding="utf-8")
        assert body.endswith("\n") and not body.endswith("\n\n"), path
        for target in re.findall(r"\]\(([^)]+)\)", body):
            if "://" not in target:
                assert (path.parent / target.split("#")[0]).exists(), (path, target)
                checked_links.append(target)
        tables = []
        active = []
        for line in body.splitlines() + [""]:
            if line.startswith("|"):
                active.append(line.count("|"))
            elif active:
                assert len(set(active)) == 1, (path, active)
                tables.append(len(active))
                active = []
    report = {"input_files": len(expected), "input_bytes": sum(r["bytes"] for r in inventory["files"]),
              "input_names_sizes_mtimes_and_sha256_unchanged": True,
              "analysis_source_sha256": identities, "markdown_links_checked": checked_links,
              "runtime_versions": {name: importlib.metadata.version(name)
                                   for name in ["numpy", "scipy", "Pillow", "matplotlib", "rawpy"]},
              "native_endpoints": native_endpoints,
              "restoration_warning": {"code": 131180, "sdk_name": "CrWarning_FocusPosition_Result_OK"},
              "decoder_dependency_sha256": sha(ROOT / "target/release/deps/libstrehl_raw-2282d540d2cb317d.rlib"),
              "report_sha256": sha(HERE / "results.md"), "workers": 1}
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Verified: 158 unchanged input files, within-run settings, source hashes and report links/tables", flush=True)


if __name__ == "__main__":
    main()
