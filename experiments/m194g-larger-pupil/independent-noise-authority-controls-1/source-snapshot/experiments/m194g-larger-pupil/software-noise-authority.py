"""Consumer of the externally pinned full-float authority; no optical imports."""
import ast
import hashlib
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FIXTURE_SHA = "e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb"
SCHEMA_SHA = "3097142b76a796838a2b9ed50d8dcda972ba9945bbc0df75906901abe0e2c606"
SCHEMA_PATH = HERE / "independent-full-float-authority-schema.md"
AUTH_KEYS = {"schema", "status", "ref_root", "fixture", "component_verification", "comparison",
             "width", "height", "cell", "units", "reference_index", "primary_frames"}
PROJECTION = AUTH_KEYS - {"schema", "status", "comparison"}
ROLES = ("author-primary", "author-angle-refined", "author-cell-refined",
         "reference-primary", "reference-refined")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def relative_path(base, value):
    need(type(value) is str and value and "\\" not in value and ":" not in value,
         "invalid relative reference")
    parts = value.split("/")
    need(all(part not in ("", ".", "..") for part in parts) and not value.startswith("/"),
         "noncanonical relative reference")
    base = Path(base).resolve(strict=True)
    target = (base / value).resolve(strict=True)
    need(target.is_relative_to(base) and target.is_file(), "reference escapes root or is not a file")
    return target


class Reads:
    def __init__(self, core, budget):
        self.core, self.budget = core, budget
        self.observed = {}

    def reference(self, ref, base=ROOT, *, array=False):
        keys = {"path", "sha256", "bytes"} | ({"dtype", "shape"} if array else set())
        need(type(ref) is dict and set(ref) == keys, "reference keys mismatch")
        need(type(ref["bytes"]) is int and ref["bytes"] > 0 and self.core.valid_hash(ref["sha256"]),
             "reference byte/hash types mismatch")
        if array:
            need(ref["dtype"] == "<f8" and type(ref["shape"]) is list
                 and all(type(x) is int for x in ref["shape"]) and ref["shape"] == [240, 320],
                 "primary scalar reference dtype/shape mismatch")
        return relative_path(base, ref["path"])

    def raw(self, path, expected_sha, expected_bytes=None, *, maximum=4_194_304):
        self.budget.check()
        path = Path(path).resolve(strict=True)
        need(path.is_file() and self.core.valid_hash(expected_sha), "file/hash required")
        with path.open("rb") as stream:
            raw = stream.read(maximum + 1)
        digest = hashlib.sha256(raw).hexdigest()
        need(len(raw) <= maximum and digest == expected_sha
             and (expected_bytes is None or len(raw) == expected_bytes), "bound input bytes changed")
        binding = {"sha256": digest, "bytes": len(raw)}
        key = str(path)
        need(key not in self.observed or self.observed[key] == binding, "input changed between reads")
        self.observed[key] = binding
        self.budget.check()
        return raw

    def json_ref(self, ref, base=ROOT):
        path = self.reference(ref, base)
        return self.core.strict_json(self.raw(path, ref["sha256"], ref["bytes"])), path

    def repo_ref(self, path, ref):
        return {**ref, "path": Path(path).resolve().relative_to(ROOT).as_posix()}

    def scalar(self, ref):
        path = self.reference(ref, array=True)
        raw = self.raw(path, ref["sha256"], ref["bytes"], maximum=700_000)
        need(raw[:6] == b"\x93NUMPY", "NPY magic mismatch")
        version = raw[6:8]
        if version == b"\x01\x00":
            need(len(raw) >= 10, "short NPY header")
            length, prefix = struct.unpack("<H", raw[8:10])[0], 10
        elif version == b"\x02\x00":
            need(len(raw) >= 12, "short NPY header")
            length, prefix = struct.unpack("<I", raw[8:12])[0], 12
        else:
            raise ValueError("unsupported NPY version")
        need(length <= 65536 and prefix + length <= len(raw), "NPY header exceeds bound")
        header_ast = ast.parse(raw[prefix:prefix + length].decode("latin1").strip(), mode="eval")
        need(isinstance(header_ast.body, ast.Dict), "NPY header is not a literal dictionary")
        header_keys = [ast.literal_eval(key) for key in header_ast.body.keys]
        need(all(type(key) is str for key in header_keys) and len(set(header_keys)) == len(header_keys),
             "duplicate/nonstring NPY header key")
        header = ast.literal_eval(header_ast)
        need(type(header) is dict and set(header) == {"descr", "fortran_order", "shape"}, "NPY header keys")
        need(header["descr"] == "<f8" and header["fortran_order"] is False
             and type(header["shape"]) is tuple and all(type(x) is int for x in header["shape"])
             and header["shape"] == (240, 320), "NPY primary scalar header mismatch")
        offset = prefix + length
        need(len(raw) == offset + 240 * 320 * 8, "NPY payload extent mismatch")
        self.budget.check_allocation((240, 320), "<f8")
        array = self.core.np.frombuffer(raw, dtype="<f8", count=240 * 320, offset=offset).reshape((240, 320))
        self.core.checked_array(array, self.budget, shape=(240, 320), name="admitted primary scalar", nonnegative=True)
        return array

    def finish(self):
        for path, wanted in self.observed.items():
            actual = self.core.file_binding(path)
            need({key: actual[key] for key in ("sha256", "bytes")} == wanted, "authority/input changed before completion")
            self.budget.check()
        return dict(self.observed)


class FloatAuthority:
    def __init__(self, path, external_sha, core, budget):
        self.reads = Reads(core, budget)
        self.core, self.budget = core, budget
        schema = self.reads.raw(SCHEMA_PATH, SCHEMA_SHA)
        need(schema.startswith(b"# Prospective full-float authority schema"), "wrong authority schema source")
        path = Path(path).resolve(strict=True)
        raw = self.reads.raw(path, external_sha)
        self.reference = {"path": path.relative_to(ROOT).as_posix(), "sha256": external_sha, "bytes": len(raw)}
        authority = core.strict_json(raw)
        need(type(authority) is dict and set(authority) == AUTH_KEYS, "float authority closed keys mismatch")
        need(authority["schema"] == "m194g-float-commission-v1"
             and authority["status"] == "PASS_COMPLETE_FLOAT_MODEL" and authority["ref_root"] == "repository",
             "complete genuine float authority required")
        for key, expected in (("width", 320), ("height", 240), ("reference_index", 2)):
            need(type(authority[key]) is int and authority[key] == expected, "authority integer mismatch: " + key)
        need(authority["cell"] == "integer-centre-unit-square" and authority["units"] == "expected-electrons",
             "authority cell/units mismatch")
        fixture, fixture_path = self.reads.json_ref(authority["fixture"])
        need(authority["fixture"]["sha256"] == FIXTURE_SHA
             and fixture_path == (HERE / "fixture.json").resolve(), "registered fixture required")
        self.fixture = fixture
        component, _ = self.reads.json_ref(authority["component_verification"])
        need(component.get("schema") == "m194g-independent-component-reader-command-v1"
             and component.get("status") == "PASS_COMPONENTS_AND_OBSERVER_ONLY"
             and component["exception"] is None and component["traceback"] is None
             and component.get("inputs_unchanged") is True, "independent component command failed")
        nested = component.get("result")
        need(type(nested) is dict and nested.get("schema") == "m194g-independent-component-verification-v1"
             and nested.get("status") == "PASS_COMPONENTS_AND_OBSERVER_ONLY", "component child failed")
        comparison, _ = self.reads.json_ref(authority["comparison"])
        need(comparison.get("schema") == "m194g-independent-full-array-verification-v1"
             and comparison.get("status") == "PASS_COMPLETE_FLOAT_MODEL"
             and comparison["error"] is None and comparison["finalization_errors"] == [],
             "full comparison child failed")
        projection = {key: authority[key] for key in PROJECTION}
        need(type(comparison.get("admitted_inputs")) is dict
             and core.canonical_bytes(comparison["admitted_inputs"]) == core.canonical_bytes(projection),
             "comparison admission projection differs from authority")
        roles = comparison.get("render_results")
        need(type(roles) is dict and set(roles) == set(ROLES), "five complete render roles required")
        renders = {}
        for role in ROLES:
            value, value_path = self.reads.json_ref(roles[role])
            arm = role.split("-", 1)[1]
            author = role.startswith("author-")
            need(value.get("schema") == ("m194g-author-render-v1" if author else "m194g-independent-reference-arm-v1")
                 and value.get("status") == ("COMPLETE_AUTHOR_FLOATS_UNCOMMISSIONED" if author
                                              else "PASS_COMPLETE_REFERENCE_ARM_ONLY")
                 and value.get("arm") == arm and len(value.get("frames", [])) == 5,
                 "render role incomplete or mislabeled: " + role)
            need((value["error"] is None and value["source_capture_error"] is None
                  and type(value["sources_before"]) is dict and bool(value["sources_before"])
                  and value["sources_before"] == value["sources_after"]) if author else
                 (value["exception"] is None and value["traceback"] is None
                  and value["sources_unchanged"] is True and value["finalization_errors"] == []),
                 "failed terminal render")
            renders[role] = (value, value_path)
        primary, primary_path = renders["author-primary"]
        self.frames = authority["primary_frames"]
        need(type(self.frames) is list and len(self.frames) == 5, "exact five primary frames required")
        paths, identities = set(), set()
        for index, row in enumerate(self.frames):
            need(type(row) is dict and set(row) == {"index", "inverse_focus", "author_receipt", "scalar"},
                 "primary frame keys mismatch")
            need(type(row["index"]) is int and row["index"] == index, "primary frame order/type mismatch")
            need(type(row["inverse_focus"]) in (int, float)
                 and row["inverse_focus"] == fixture["inverse_foci"][index], "focus mismatch")
            frame_row = primary["frames"][index]
            need(type(frame_row) is dict and set(frame_row) == {"frame_index", "receipt"}
                 and type(frame_row["frame_index"]) is int and frame_row["frame_index"] == index,
                 "primary result frame list mismatch")
            saved_receipt_path = self.reads.reference(frame_row["receipt"], primary_path.parent)
            need(self.reads.repo_ref(saved_receipt_path, frame_row["receipt"]) == row["author_receipt"],
                 "authority receipt is not the primary result's actual receipt")
            receipt, receipt_path = self.reads.json_ref(row["author_receipt"])
            expected_inputs = {"scene": fixture["scene"], "frame": {"index": index,
                               "inverse_focus": fixture["inverse_foci"][index], "K": fixture["K"],
                               "forward_similarity": fixture["forward_similarity"]},
                               "width": 320, "height": 240, "arm": "primary", "method": "analytic-enabled"}
            need(receipt.get("schema") == "m194g-author-frame-v1"
                 and receipt.get("status") == "complete-uncommissioned"
                 and core.canonical_bytes(receipt.get("inputs")) == core.canonical_bytes(expected_inputs)
                 and type(receipt.get("completed_cells")) is int and receipt["completed_cells"] == 76800,
                 "primary receipt input/coverage mismatch")
            scalar_ref = receipt.get("arrays", {}).get("scalar")
            scalar_path = self.reads.reference(scalar_ref, receipt_path.parent, array=True)
            need(self.reads.repo_ref(scalar_path, scalar_ref) == row["scalar"], "authority scalar/receipt association mismatch")
            for unique in (receipt_path, scalar_path):
                folded = str(unique).casefold()
                info = unique.stat()
                identity = (info.st_dev, info.st_ino)
                need(folded not in paths and identity not in identities, "aliased primary file identity")
                paths.add(folded)
                identities.add(identity)
            array = self.reads.scalar(row["scalar"])
            del array
        self.authority = authority
        self.reads.finish()

    def scalar(self, index):
        need(type(index) is int and 0 <= index < 5, "primary scalar index out of range")
        return self.reads.scalar(self.frames[index]["scalar"])

    def finish(self):
        return self.reads.finish()
