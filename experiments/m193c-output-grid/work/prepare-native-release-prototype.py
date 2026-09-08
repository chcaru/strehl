"""Prepare one exact native release after root pins its actual prerequisites.

SOURCE ONLY until root separately authorizes this preparation command. This
script imports only the standard library: no subject/helper, subprocess, RAW,
TIFF, or numerical call. It does not capture runtime or launch the native run.
All supplied hashes are external root observations, never inferred successes.

The separate runtime-capture command is the pinned Python followed by:
  -B -X faulthandler -X pycache_prefix=<HERE>/cache-derivative-runtime-1
  <HERE>/independent-derivative-read.py
  --capture-runtime <HERE>/derivative-runtime-1.json
Use absolute Windows paths and cwd ROOT. Clear ambient PYTHON*, STREHL*,
Rayon/OpenMP/BLAS/NumExpr and Rust target/flags overrides as for native children.
The reader itself sets the four recorded numerical thread caps to '2' before
NumPy/rawpy import. Capture records dependency bytes only; it must be separately
source/command-frozen and have an actual successful parent-observed record.

Required CLI: --campaign-result-sha256 SHA --private-admission-sha256 SHA
--runtime-sha256 SHA --runtime-capture-record ABS --runtime-capture-record-sha256
SHA --prior-work ABS --prior-work-sha256 SHA. Add --no-earlier-real-work only
when root affirms that the current native/coverage stage has spent no real work.
The two variable record paths must be repository-contained JSON metadata.
The capture record is pinned as opaque root-reviewed evidence: its schema is
owned by the later capture release, not invented by this preparation script.
"""
import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
PYTHON = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
OUTPUT = HERE / "native-derivative-1"
DESTINATION = HERE / "native-derivative-release-1.json"
BUILD = HERE / "bridge-build-2/result.json"
CAMPAIGN = HERE / "private-campaign-1/result.json"
PRIVATE = HERE / "private-campaign-1/derivative-private-admission.json"
RUNTIME = HERE / "derivative-runtime-1.json"
TEST = "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native"
MIB = 1 << 20
POPULATION = (
    (0, "DSC00016.ARW", 39030784), (13, "DSC00029.ARW", 39878656),
    (26, "DSC00042.ARW", 40873984), (39, "DSC00055.ARW", 40669184),
    (52, "DSC00068.ARW", 39497728), (65, "DSC00081.ARW", 39235584),
    (78, "DSC00094.ARW", 39096320), (91, "DSC00107.ARW", 39018496),
    (104, "DSC00120.ARW", 38969344),
)
HELD = {
    "native-derivative-run.py": "94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a",
    "native-derivative-run-preregister.md": "de30439f509404df8a2d304536ae1f0c88e62db7d4114eae94184c6d671872a0",
    "independent-derivative-read.py": "8c571654667f8ef66520aedfd1bddceb991c8a86d1a7355a4ed21cf2ba85eced",
    "independent-derivative-tiff.py": "9acceb498568967bb02ce01389441da09de7502f3a51faebbed8fed61943a5ae",
    "independent-derivative-reader-preregister.md": "bf8a6c2a13b109fb8e5cb8e3c1a9f1ce47931ded220de909118636645bd8a990",
    "bounded-process.py": "1dba8d87c8818aecf98078d1a926e5ff9c059a7d242cf5c46fcc962f14dfc5ab",
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha_form(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def repo(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), "repository-contained preparation input")
    # No image/capture payload may enter this metadata/source preparation.
    need(path.suffix.lower() not in (".arw", ".raw", ".tif", ".tiff", ".npy"), "no image/capture access")
    return path


def path_ref(ref):
    need(type(ref) is dict and set(ref) == {"path", "sha256", "bytes"}, "closed FileRef")
    need(type(ref["path"]) is str and sha_form(ref["sha256"]) and type(ref["bytes"]) is int and
         0 <= ref["bytes"] <= 128 * MIB, "typed bounded FileRef")
    path = Path(ref["path"])
    if not path.is_absolute():
        name = PurePosixPath(ref["path"])
        need(str(name) == ref["path"] and ".." not in name.parts and "\\" not in ref["path"], "POSIX relative ref")
        path = ROOT / path
    return repo(path)


def binding(path):
    path = repo(path)
    before = path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and not before.st_file_attributes & 0x400 and
         before.st_size <= 128 * MIB, "ordinary bounded source/metadata/artifact file")
    count, digest = 0, hashlib.sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        need((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "opened identity")
        while chunk := stream.read(MIB):
            count += len(chunk)
            need(count <= 128 * MIB, "file growth cap")
            digest.update(chunk)
    after = path.stat(follow_symlinks=False)
    attributes = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_file_attributes")
    need(all(getattr(before, k) == getattr(after, k) for k in attributes) and count == before.st_size,
         "preparation input changed")
    return dict(sha256=digest.hexdigest(), bytes=count)


def ref(path, expected_sha=None):
    path = repo(path)
    result = dict(path=path.relative_to(ROOT).as_posix(), **binding(path))
    if expected_sha is not None:
        need(sha_form(expected_sha) and result["sha256"] == expected_sha, "external prerequisite pin: " + str(path))
    return result


def verify(item):
    need(binding(path_ref(item)) == {k: item[k] for k in ("sha256", "bytes")}, "bound prerequisite changed")


def read(item):
    path = path_ref(item)
    need(path.suffix == ".json" and item["bytes"] <= 4 * MIB, "bounded JSON prerequisite")
    with path.open("rb") as stream:
        raw = stream.read(4 * MIB + 1)
    need(len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], "same-byte JSON binding")
    def pairs(rows):
        value = {}
        for key, child in rows:
            need(key not in value, "duplicate JSON key")
            value[key] = child
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    def finite(child):
        if type(child) is float:
            need(math.isfinite(child), "overflowed JSON float")
        elif type(child) is list:
            for part in child: finite(part)
        elif type(child) is dict:
            for part in child.values(): finite(part)
    finite(value)
    return value


def literal(path, name):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    values = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    need(len(values) == 1, "unique held literal " + name)
    return values[0]


def main():
    parser = argparse.ArgumentParser()
    for name in ("campaign-result-sha256", "private-admission-sha256", "runtime-sha256",
                 "runtime-capture-record-sha256", "prior-work-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--runtime-capture-record", type=Path, required=True)
    parser.add_argument("--prior-work", type=Path, required=True)
    parser.add_argument("--no-earlier-real-work", action="store_true")
    args = parser.parse_args()
    need(os.name == "nt" and Path.cwd().resolve() == ROOT, "actual Windows repository preparation")
    need(not OUTPUT.exists() and not DESTINATION.exists(), "fresh fixed native output and release")
    # Every prerequisite must exist before the only write below; no missing-input substitute.
    inputs = {}
    def add(item):
        verify(item)
        name = path_ref(item).relative_to(ROOT).as_posix()
        normalized = dict(path=name, sha256=item["sha256"], bytes=item["bytes"])
        need(inputs.setdefault(name, normalized) == normalized, "conflicting prerequisite references")
        return normalized
    build_ref = add(ref(BUILD, "05154982aefcab418427c5311fb27ea499a42f1a1c6e9f714d9c46cb8e45c907"))
    campaign_ref = add(ref(CAMPAIGN, args.campaign_result_sha256))
    private_ref = add(ref(PRIVATE, args.private_admission_sha256))
    runtime_ref = add(ref(RUNTIME, args.runtime_sha256))
    capture_ref = add(ref(args.runtime_capture_record, args.runtime_capture_record_sha256))
    prior_ref = add(ref(args.prior_work, args.prior_work_sha256))
    build, campaign, gate, runtime, prior = map(read, (build_ref, campaign_ref, private_ref, runtime_ref, prior_ref))
    need(build["schema"] == "m193c-bridge-build-v1" and build["status"] == "COMPLETE_COMPILED_TESTS_ONLY" and
         type(build["exit_code"]) is int and build["exit_code"] == 0 and build["rebuilt_cli"] is True and
         build["error"] is None and build["finalization_errors"] == [] and
         build["sources_before"] == build["sources_after"], "actual stable build2")
    need(campaign["schema"] == "m193c-private-campaign-v1" and campaign["status"] == "PASS_M193C_PRIVATE_STAGE_ONLY" and
         campaign["error"] is None and campaign["finalization_errors"] == [] and campaign["build"] == build_ref and
         campaign["derivative_admission"] == private_ref, "actual complete private campaign/gate association")
    need(gate["schema"] == "m193c-derivative-private-admission-v1" and
         gate["status"] == "PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY" and gate["build"] == build_ref and
         gate["independent_read"] == campaign["derivative_read"] and gate["error"] is None and
         gate["finalization_errors"] == [], "actual independent derivative private admission")
    for item in (build["execution_release"], campaign["execution_release"], gate["private_result"],
                 gate["independent_read"], campaign["grid_read"], campaign["worker_result"]):
        add(item)
    build_release = read(build["execution_release"])
    for item in build_release["inputs"]:
        add(item)
    for name in ("test_executable", "compiler_artifact", "compiler_log", "test_listing"):
        add(build[name])
    exe = path_ref(build["test_executable"])
    need(exe == HERE / "bridge-build-2/output-grid-tests.exe" and
         build["test_executable"]["sha256"] == "8ecf5dfbb9270eef5ab99a9306bd1edb8cd0180e6128e86ad1bb18420b09b0e1" and
         build["test_executable"]["bytes"] == 29488640, "exact copied build2 executable")
    need(TEST + ": test" in path_ref(build["test_listing"]).read_text(encoding="utf8").splitlines(), "actual native test name")
    need(runtime["schema"] == "m193c-derivative-reader-runtime-v1" and
         Path(runtime["python_executable"]["path"]).resolve() == PYTHON and
         runtime["rawpy_version"] is not None and runtime["libraw_version"] is not None and
         runtime["thread_environment"] == {k: "2" for k in
         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}, "actual native runtime capture")
    need(capture_ref["path"] != runtime_ref["path"], "separate root-observed capture record")
    need(type(prior) is dict and set(prior) == {"cpu_seconds", "wall_seconds", "file_bytes", "metadata_bytes"} and
         all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in prior.values()) and
         all(type(prior[k]) is int for k in ("file_bytes", "metadata_bytes")), "explicit prior real-stage work")
    zero = all(v == 0 for v in prior.values())
    need(args.no_earlier_real_work == zero, "zero prior work requires explicit no-earlier-real-work statement")
    if zero:
        need(not any(p.is_dir() for p in HERE.glob("native-derivative-*")), "existing native attempt prevents zero work")
    sources = dict(build["sources_before"])
    for name, expected in HELD.items():
        item = ref(HERE / name, expected)
        sources[item["path"]] = {k: item[k] for k in ("sha256", "bytes")}
    for path in (HERE / "charter.md", HERE / "bridge-build.py", Path(__file__),
                 ROOT / "experiments/m12-scorecard/m12-harness.py",
                 ROOT / "experiments/m194g-larger-pupil/independent-rgb-tiff.py"):
        item = ref(path)
        sources[item["path"]] = {k: item[k] for k in ("sha256", "bytes")}
    need(sources["experiments/m194g-larger-pupil/independent-rgb-tiff.py"]["sha256"] ==
         "d01a74aefcfa15b2146256b54ea51876715ab203b7de123b3cff2b0af4a1b19c", "held original TIFF dependency")
    for name in ("native-derivative-run-preregister.md", "independent-native-parent-source-review.md",
                 "independent-derivative-reader-preregister.md", "independent-derivative-reader-source-review.md",
                 "independent-derivative-source-repair-review.md", "independent-private-campaign-review.md"):
        add(ref(HERE / name))
    need(literal(HERE / "native-derivative-run.py", "POPULATION") == POPULATION and
         literal(HERE / "independent-derivative-read.py", "ORIGINALS") == POPULATION,
         "all nine literal historical inputs agree; no RAW access")
    script = ref(HERE / "independent-derivative-read.py", HELD["independent-derivative-read.py"])
    reader_commands = []
    for ordinal, _ in enumerate(POPULATION):
        base = OUTPUT / f"frame-{ordinal:02d}"
        reader_commands.append([str(PYTHON), "-B", "-X", "faulthandler", "-X",
            "pycache_prefix=" + str(base / "reader-cache"), str(HERE / "independent-derivative-read.py"),
            "--request", str(base / "read-request.json"), "--request-sha256", "ACTUAL_FRAME_REQUEST_SHA256",
            "--output", str(base / "independent")])
    command = [str(PYTHON), "-B", "-X", "faulthandler", "-X", "pycache_prefix=" + str(OUTPUT / "parent-cache"),
               str(HERE / "native-derivative-run.py"), "--release", str(DESTINATION), "--release-sha256",
               "ACTUAL_EXECUTION_RELEASE_SHA256", "--output", str(OUTPUT)]
    release = dict(schema="m193c-native-derivative-release-v1", scope="native-nine", source_bindings=sources,
                   inputs=list(inputs.values()), commands=[command], build=build_ref, private_admission=private_ref,
                   reader=dict(script=script, runtime=runtime_ref, commands=reader_commands), prior_work=prior)
    for name, expected in sources.items():
        need(binding(ROOT / name) == expected, "current complete source closure: " + name)
    for item in inputs.values(): verify(item)
    raw = (json.dumps(release, indent=2, allow_nan=False) + "\n").encode("utf8")
    need(len(raw) <= 4 * MIB and not OUTPUT.exists(), "bounded release and still-fresh output")
    with DESTINATION.open("xb") as stream:
        need(stream.write(raw) == len(raw), "complete release write")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(dict(status="PREPARED_RELEASE_ONLY", release=ref(DESTINATION), source_count=len(sources),
                          input_count=len(inputs), original_indices=[row[0] for row in POPULATION]), indent=2), flush=True)


if __name__ == "__main__":
    main()
